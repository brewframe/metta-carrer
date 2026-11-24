import json
from urllib.parse import urlparse
from typing import List, Optional
from pydantic import BaseModel, Field
from ..core import api, HTTPError, bad, not_found, notify
from .. import engine as E
from .. import coursework as CW
from ..messages import msg

S = ["student"]

# ---------- dashboard ----------
@api("/api/student/dashboard", roles=S)
def dashboard(c):
    d, uid = c.db, c.user["id"]
    plan = E.active_plan(d, uid)
    task = None; target = None
    if plan:
        target = plan["career_name"]
        task = d.one("SELECT id,title,description,est_hours,kind,skill_id FROM tasks WHERE plan_id=? AND status<>'COMPLETED' ORDER BY position LIMIT 1", plan["id"])
        if task: task = E.task_view(d, task)
    ins = E.insight(d, uid)
    choices = d.all("""SELECT ic.rank, co.name FROM internship_choices ic JOIN companies co ON co.id=ic.company_id WHERE ic.user_id=? ORDER BY ic.rank""", uid)
    done = d.one("SELECT COUNT(*) n, SUM(status='COMPLETED') done FROM tasks WHERE plan_id=?", plan["id"]) if plan else {"n": 0, "done": 0}
    proj = d.one("SELECT COUNT(*) n, SUM(status='VERIFIED') v FROM projects WHERE user_id=?", uid)
    notes = d.all("SELECT id,text,read,created_at FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 5", uid)
    return {"name": c.user["name"], "target": target, "readiness": E.readiness(d, uid), "today_task": task,
            "milestone": {"done": done["done"] or 0, "total": done["n"]}, "has_assessment": ins is not None,
            "recommendation": (ins["careers"][0] if ins else None), "internship": choices,
            "projects": {"total": proj["n"], "verified": proj["v"] or 0}, "notifications": notes}

# ---------- self discovery ----------
@api("/api/student/questions", roles=S)
def questions(c):
    qs = c.db.all("SELECT id,kind,tag,text FROM questions ORDER BY id")
    for q in qs: q["text"] = c.db.tr("question", q["id"], "text", q["text"])
    sk = c.db.all("SELECT id,name,category FROM skills ORDER BY category,name")
    for x in sk: x["name"] = c.db.tr("skill", x["id"], "name", x["name"])
    sk.sort(key=lambda x: (x["category"], x["name"].lower()))
    return {"questions": qs, "skills": sk,
            "my_skills": [r["skill_id"] for r in c.db.all("SELECT skill_id FROM student_skills WHERE user_id=?", c.user["id"])]}

class AssessIn(BaseModel):
    answers: dict
    skill_ids: List[int] = []

@api("/api/student/assessment", "POST", roles=S, model=AssessIn)
def submit_assessment(c, b):
    qs = c.db.all("SELECT id,kind,tag FROM questions")
    ids = {str(q["id"]) for q in qs}
    ans = {}
    for k, v in b.answers.items():
        if str(k) not in ids: raise bad("Unknown question")
        try: v = int(v)
        except Exception: raise bad("Answers must be numbers 1 to 5")
        if not 1 <= v <= 5: raise bad("Answers must be 1 to 5")
        ans[str(k)] = v
    if len(ans) < len(qs): raise bad(f"Please answer all questions ({len(ans)}/{len(qs)})")
    scores = E.score_answers(qs, ans)
    valid = {r["id"] for r in c.db.all("SELECT id FROM skills")}
    for sid in set(b.skill_ids):
        if sid in valid: E.raise_skill(c.db, c.user["id"], sid, E.SELF_CLAIMED)
    c.db.run("INSERT INTO assessments(user_id,answers,scores) VALUES(?,?,?)", c.user["id"], json.dumps(ans), json.dumps(scores))
    return E.insight(c.db, c.user["id"])

@api("/api/student/insight", roles=S)
def get_insight(c):
    i = E.insight(c.db, c.user["id"])
    if not i: raise not_found("Take the Self Discovery assessment first")
    return i

@api("/api/student/insight/save", "POST", roles=S)
def save_insight(c):
    a = E.latest_assessment(c.db, c.user["id"])
    if not a: raise not_found("Nothing to save yet")
    c.db.run("UPDATE assessments SET saved=1 WHERE id=?", a["id"])

# ---------- explore ----------
def career_card(r): return {k: r[k] for k in ("id", "name", "category", "description")}

@api("/api/careers", roles=["student", "teacher", "admin", "alumni"])
def careers(c):
    q = (c.request.query_params.get("q") or "").strip().lower(); cat = c.request.query_params.get("category") or ""
    rows = [E.career_text(c.db, r, ("name", "description")) for r in c.db.all("SELECT id,name,category,description,majors,trend,is_new FROM careers")]
    top = {}   # tiga skill terpenting per karier (untuk kartu dan pencarian)
    for r in c.db.all("SELECT cs.career_id cid, s.id sid, s.name, cs.importance FROM career_skills cs JOIN skills s ON s.id=cs.skill_id ORDER BY cs.career_id, cs.importance DESC, s.name"):
        if len(top.setdefault(r["cid"], [])) < 3: top[r["cid"]].append(c.db.tr("skill", r["sid"], "name", r["name"]))
    for r in rows:
        r["skills"] = top.get(r["id"], []); r["trend"] = bool(r["trend"]); r["is_new"] = bool(r["is_new"])
        m = [x for x in (r.pop("majors") or "").split(",") if x]; r["majors"] = m
    rows.sort(key=lambda r: r["name"].lower())
    short = {r["career_id"] for r in c.db.all("SELECT career_id FROM shortlist WHERE user_id=?", c.user["id"])}
    counts = {}
    for r in rows: counts[r["category"]] = counts.get(r["category"], 0) + 1
    def hit(r): return not q or q in r["name"].lower() or q in r["description"].lower() or any(q in s.lower() for s in r["skills"])
    out = [dict(r, saved=r["id"] in short) for r in rows if hit(r) and (not cat or r["category"] == cat)]
    return {"items": out, "total": len(rows), "categories": sorted(counts, key=lambda k: (-counts[k], k)), "counts": counts}

@api("/api/careers/{cid:int}", roles=["student", "teacher", "admin"])
def career_detail(c, cid):
    r = c.db.one("SELECT * FROM careers WHERE id=?", cid)
    if not r: raise not_found("Career not found")
    r = E.career_text(c.db, r)
    r["skills"] = E.career_skills(c.db, cid)
    mine = E.student_skill_map(c.db, c.user["id"]) if c.user["role"] == "student" else {}
    for s in r["skills"]: s["level"] = E.lvl(c.db, mine.get(s["id"]))
    return r

class CompareIn(BaseModel):
    ids: List[int] = Field(min_length=2, max_length=3)

@api("/api/student/compare", "POST", roles=S, model=CompareIn)
def compare(c, b):
    out = []
    for cid in b.ids:
        r = c.db.one("SELECT id,name,education_path,example_projects,growth FROM careers WHERE id=?", cid)
        if not r: raise not_found("Career not found")
        r = E.career_text(c.db, r, ("name", "education_path", "example_projects", "growth"))
        r["skills"] = [s["name"] for s in E.career_skills(c.db, cid)]; out.append(r)
    return {"items": out}

@api("/api/student/shortlist/{cid:int}", "POST", roles=S)
def shortlist_add(c, cid):
    if not c.db.one("SELECT 1 x FROM careers WHERE id=?", cid): raise not_found("Career not found")
    c.db.run("INSERT OR IGNORE INTO shortlist(user_id,career_id) VALUES(?,?)", c.user["id"], cid)

@api("/api/student/shortlist/{cid:int}", "DELETE", roles=S)
def shortlist_del(c, cid): c.db.run("DELETE FROM shortlist WHERE user_id=? AND career_id=?", c.user["id"], cid)

# ---------- career plan ----------
@api("/api/student/recommendations", roles=S)
def recommendations(c):
    r = E.recommend(c.db, c.user["id"])
    if r is None: raise not_found("Take the Self Discovery assessment first")
    return {"items": [{k: v for k, v in x.items() if k != "reason_codes"} for x in r[:5]]}

@api("/api/student/plan/preview/{cid:int}", roles=S)
def plan_preview(c, cid):
    p = E.plan_preview(c.db, c.user["id"], cid)
    if not p: raise not_found("Career not found")
    return p

class PlanIn(BaseModel):
    career_id: int

@api("/api/student/plan", "POST", roles=S, model=PlanIn)
def plan_create(c, b):
    if E.create_plan(c.db, c.user["id"], b.career_id) is None: raise not_found("Career not found")
    return plan_get(c)

@api("/api/student/plan", roles=S)
def plan_get(c):
    p = E.active_plan(c.db, c.user["id"])
    if not p: return {"plan": None}
    prev = E.plan_preview(c.db, c.user["id"], p["career_id"])
    tasks = [E.task_view(c.db, t) for t in c.db.all("SELECT * FROM tasks WHERE plan_id=? ORDER BY position", p["id"])]
    ms = {}
    for t in tasks: ms.setdefault(t["milestone"], {"milestone": t["milestone"], "skill_id": t["skill_id"], "tasks": []})["tasks"].append(t)
    names = {r["id"]: c.db.tr("skill", r["id"], "name", r["name"]) for r in c.db.all("SELECT id,name FROM skills")}
    for m in ms.values(): m["skill"] = names.get(m["skill_id"], "")
    mine = E.student_skill_map(c.db, c.user["id"])
    current = [{"id": s["id"], "name": s["name"], "level": E.lvl(c.db, mine[s["id"]])} for s in E.career_skills(c.db, p["career_id"]) if s["id"] in mine]
    gap = [{"id": s["id"], "name": s["name"]} for s in E.career_skills(c.db, p["career_id"]) if mine.get(s["id"], 0) < E.GAP_THRESHOLD]
    return {"plan": {"id": p["id"], "career_id": p["career_id"], "career": p["career_name"], "reasons": E.render_reasons(c.db, json.loads(p["reasons"])),
                     "teacher_note": p["teacher_note"], "created_at": p["created_at"], "example_projects": prev["career"]["example_projects"] if prev else ""},
            "current_skills": current, "skill_gap": gap, "milestones": list(ms.values()), "readiness": E.readiness(c.db, c.user["id"])}

# ---------- learning ----------
class TaskIn(BaseModel):
    status: str = Field(pattern="^(NOT_STARTED|IN_PROGRESS|COMPLETED)$")

@api("/api/student/tasks/{tid:int}", "PATCH", roles=S, model=TaskIn)
def task_update(c, b, tid):
    t = c.db.one("""SELECT t.* FROM tasks t JOIN plans p ON p.id=t.plan_id WHERE t.id=? AND p.user_id=? AND p.status='ACTIVE'""", tid, c.user["id"])
    if not t: raise not_found("Task not found")
    if b.status == "COMPLETED":
        from .learn import completion_block
        why = completion_block(c, t)
        if why: raise bad(why)
    c.db.run("UPDATE tasks SET status=?, completed_at=CASE WHEN ?='COMPLETED' THEN datetime('now') ELSE NULL END WHERE id=?", b.status, b.status, tid)
    if b.status == "COMPLETED" and t["skill_id"] and t["kind"] in ("STUDY", "PRACTICE"):
        E.raise_skill(c.db, c.user["id"], t["skill_id"], E.LEARNING)
    return {"readiness": E.log_readiness(c.db, c.user["id"])}

# ---------- projects ----------
class ProjectIn(BaseModel):
    title: str = Field(min_length=3, max_length=120); description: str = Field("", max_length=2000)
    link: str = Field("", max_length=300); skill_ids: List[int] = []
    problem: str = Field("", max_length=600); solution: str = Field("", max_length=600); result: str = Field("", max_length=600)
    technology: str = Field("", max_length=200)
    demo_url: str = Field("", max_length=300); repo_url: str = Field("", max_length=300); doc_url: str = Field("", max_length=300)

PROJECT_TEXT = ("problem", "solution", "result", "technology")
PROJECT_URLS = ("demo_url", "repo_url", "doc_url")

def project_fields(b):
    """Nilai kolom tambahan project yang sudah dibersihkan; tautan harus http(s) biasa."""
    for k in PROJECT_URLS: valid_link(getattr(b, k))
    return [getattr(b, k).strip() for k in PROJECT_TEXT + PROJECT_URLS]

def project_row(c, p):
    from .files import files_map
    p["files"] = files_map(c.db, "project", [p["id"]])[p["id"]]
    names = {r["id"]: c.db.tr("skill", r["id"], "name", r["name"]) for r in c.db.all("SELECT id,name FROM skills")}
    ids = json.loads(p["skill_ids"]); p["skills"] = [names[i] for i in ids if i in names]; return p

@api("/api/student/projects", roles=S)
def projects(c):
    return {"items": [project_row(c, p) for p in c.db.all("SELECT * FROM projects WHERE user_id=? ORDER BY id DESC", c.user["id"])]}

def sync_evidence(c, pid, link):
    """Tautan bukti disimpan juga sebagai baris project_evidence, supaya satu project bisa punya banyak bukti nanti."""
    c.db.run("DELETE FROM project_evidence WHERE project_id=? AND kind='LINK'", pid)
    if link.strip(): c.db.run("INSERT INTO project_evidence(project_id,kind,url) VALUES(?,'LINK',?)", pid, link.strip())

def valid_link(link):
    """Evidence links end up in <a href>: allow only plain http(s) URLs with a host, no spaces, control characters or backslashes."""
    link = (link or "").strip()
    if not link: return
    if any(ord(ch) <= 32 or ord(ch) == 127 or ch == "\\" for ch in link): raise bad("The link must not contain spaces or special characters")
    u = urlparse(link)
    if u.scheme.lower() not in ("http", "https") or not u.hostname: raise bad("Link must start with http:// or https:// and include a website name")

@api("/api/student/projects", "POST", roles=S, model=ProjectIn)
def project_create(c, b):
    valid_link(b.link)
    ids = [r["id"] for r in c.db.all("SELECT id FROM skills") if r["id"] in set(b.skill_ids)]
    extra = project_fields(b)
    pid = c.db.run("INSERT INTO projects(user_id,title,description,link,skill_ids,problem,solution,result,technology,demo_url,repo_url,doc_url) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", c.user["id"], b.title.strip(), b.description.strip(), b.link.strip(), json.dumps(ids), *extra)
    sync_evidence(c, pid, b.link)
    for s in ids: E.raise_skill(c.db, c.user["id"], s, E.PROJECT_EVIDENCE)
    E.log_readiness(c.db, c.user["id"])
    return project_row(c, c.db.one("SELECT * FROM projects WHERE id=?", pid))

@api("/api/student/projects/{pid:int}", "PUT", roles=S, model=ProjectIn)
def project_resubmit(c, b, pid):
    p = c.db.one("SELECT * FROM projects WHERE id=? AND user_id=?", pid, c.user["id"])
    if not p: raise not_found("Project not found")
    if p["status"] != "NEEDS_REVISION": raise bad("Only projects that need revision can be edited")
    valid_link(b.link)
    ids = [r["id"] for r in c.db.all("SELECT id FROM skills") if r["id"] in set(b.skill_ids)]
    extra = project_fields(b)
    c.db.run("UPDATE projects SET title=?,description=?,link=?,skill_ids=?,problem=?,solution=?,result=?,technology=?,demo_url=?,repo_url=?,doc_url=?,status='SUBMITTED',updated_at=datetime('now') WHERE id=?", b.title.strip(), b.description.strip(), b.link.strip(), json.dumps(ids), *extra, pid)
    sync_evidence(c, pid, b.link)
    for s in ids: E.raise_skill(c.db, c.user["id"], s, E.PROJECT_EVIDENCE)
    return project_row(c, c.db.one("SELECT * FROM projects WHERE id=?", pid))

# ---------- portfolio & outcome ----------
@api("/api/student/portfolio", roles=S)
def portfolio(c):
    uid = c.user["id"]
    verified = [project_row(c, p) for p in c.db.all("SELECT * FROM projects WHERE user_id=? AND status='VERIFIED' ORDER BY id DESC", uid)]
    skills = c.db.all("""SELECT s.id, s.name, ss.level FROM student_skills ss JOIN skills s ON s.id=ss.skill_id WHERE ss.user_id=? ORDER BY ss.level DESC, s.name""", uid)
    for s in skills: s["name"] = c.db.tr("skill", s.pop("id"), "name", s["name"]); s["evidence"] = E.lvl(c.db, s["level"])
    prof = c.db.one("SELECT school,major,class_name FROM student_profiles WHERE user_id=?", uid) or {}
    plan = E.active_plan(c.db, uid)
    return {"name": c.user["name"], "profile": prof, "target": plan["career_name"] if plan else None, "projects": verified, "skills": skills, "courses": CW.completed_courses(c.db, uid),
            "pending_projects": c.db.one("SELECT COUNT(*) n FROM projects WHERE user_id=? AND status<>'VERIFIED'", uid)["n"]}

@api("/api/student/outcome", roles=S)
def outcome(c):
    uid = c.user["id"]; E.log_readiness(c.db, uid)
    log = c.db.all("SELECT value FROM readiness_log WHERE user_id=? ORDER BY id DESC LIMIT 2", uid)
    now = log[0]["value"] if log else 0; before = log[1]["value"] if len(log) > 1 else now
    verified = c.db.all("""SELECT s.id, s.name FROM student_skills ss JOIN skills s ON s.id=ss.skill_id WHERE ss.user_id=? AND ss.level=4""", uid)
    for v in verified: v["name"] = c.db.tr("skill", v["id"], "name", v["name"])
    plan = E.active_plan(c.db, uid)
    nxt = c.db.one("SELECT title,kind,skill_id FROM tasks WHERE plan_id=? AND status<>'COMPLETED' ORDER BY position LIMIT 1", plan["id"]) if plan else None
    if nxt: nxt = E.task_view(c.db, nxt)
    return {"before": before, "now": now, "verified_skills": [v["name"] for v in verified], "next_task": nxt["title"] if nxt else None, "has_plan": plan is not None}

# ---------- internship ----------
from urllib.parse import quote_plus
from .. import seed_companies
from ..links import search_links

def _co(r, lang, uid=None):
    """Satu baris perusahaan untuk tampilan: teks sesuai bahasa, plus tautan (hanya tautan, tanpa skrip pihak ketiga)."""
    idn = lang == "id"
    sector = (r["sector_id"] if idn else r["sector"]) or r["sector"]; about = (r["about_id"] if idn else r["about"]) or r["about"]
    q = quote_plus((r["name"] + " " + (r["address"] or "Pekanbaru")).strip())
    mine = uid is not None and r["submitted_by"] == uid
    ig = r["instagram"] or ""
    return {"id": r["id"], "number": r["number"], "name": r["name"], "address": r["address"], "sector": sector, "about": about,
            "sector_en": r["sector"], "sector_id": r["sector_id"], "about_en": r["about"], "about_id": r["about_id"], "source": r["source"], "verified": bool(r["verified"]), "sector_guess": bool(r["sector_guess"]),
            "maps_url": "https://www.google.com/maps/search/?api=1&query=" + q,
            "website": r["website"] or "", "instagram": ig, "instagram_url": ("https://www.instagram.com/" + ig + "/") if ig else "", "phone": r["phone"] or "",
            "tasks": r["tasks"] or "", "majors": r["majors"] or "", "work_terms": r["work_terms"] or "",
            "status": r["status"], "mine": mine, "review_note": (r["review_note"] or "") if mine else "",
            **search_links(r["name"], r["address"] or "")}

@api("/api/companies", roles=["student", "teacher", "admin"])
def companies(c):
    q = (c.request.query_params.get("q") or "").strip().lower(); loc = (c.request.query_params.get("location") or "").strip().lower()
    uid = c.user["id"] if c.user["role"] == "student" else None
    # daftar umum hanya berisi yang sudah disetujui; siswa juga melihat ajuan miliknya sendiri (menunggu / ditolak)
    rows = [r for r in c.db.all("SELECT * FROM companies ORDER BY number, name") if r["status"] == "approved" or (uid is not None and r["submitted_by"] == uid)]
    items = [_co(r, c.lang, uid) for r in rows if (not q or q in r["name"].lower()) and (not loc or loc in (r["address"] or "").lower())]
    ask = [(i if c.lang == "id" else e) for e, i in seed_companies.ASK]
    return {"items": items, "total": len(rows), "verified": sum(1 for r in rows if r["verified"]), "checklist": ask}

@api("/api/student/internship", roles=S)
def internship_get(c):
    ch = c.db.all("""SELECT ic.rank, ic.purpose, co.id company_id, co.name, co.address FROM internship_choices ic JOIN companies co ON co.id=ic.company_id WHERE ic.user_id=? ORDER BY ic.rank""", c.user["id"])
    prof = c.db.one("SELECT class_name FROM student_profiles WHERE user_id=?", c.user["id"]) or {}
    fr = c.db.all("SELECT name, class_name FROM internship_friends WHERE user_id=? ORDER BY id", c.user["id"])
    return {"full_name": c.user["name"], "class_name": prof.get("class_name", ""), "choices": ch, "friends": fr, "status": "Saved" if ch else "Not chosen"}

class FriendIn(BaseModel):
    name: str = Field(min_length=2, max_length=80); class_name: str = Field("", max_length=20)

class InternIn(BaseModel):
    class_name: str = Field(min_length=1, max_length=20)
    company_ids: List[int] = Field(min_length=1, max_length=3)
    purposes: List[str] = Field(default_factory=list, max_length=3)      # tujuan masuk, satu per pilihan (urut sama dengan company_ids)
    friends: List[FriendIn] = Field(default_factory=list, max_length=3)  # teman yang diajak

@api("/api/student/internship", "PUT", roles=S, model=InternIn)
def internship_put(c, b):
    if len(set(b.company_ids)) != len(b.company_ids): raise bad("Choose different companies for each choice")
    for cid in b.company_ids:
        co = c.db.one("SELECT status, submitted_by FROM companies WHERE id=?", cid)
        # boleh memilih tempat yang sudah disetujui, atau ajuan milik sendiri yang masih menunggu guru
        if not co or not (co["status"] == "approved" or (co["status"] == "pending" and co["submitted_by"] == c.user["id"])): raise not_found("Company not found")
    if any(len(p) > 500 for p in b.purposes): raise bad("Purpose is too long (max 500 characters)")
    c.db.run("DELETE FROM internship_choices WHERE user_id=?", c.user["id"])
    for rank, cid in enumerate(b.company_ids, 1):
        pur = (b.purposes[rank - 1] if rank - 1 < len(b.purposes) else "").strip()
        c.db.run("INSERT INTO internship_choices(user_id,rank,company_id,purpose) VALUES(?,?,?,?)", c.user["id"], rank, cid, pur)
    c.db.run("DELETE FROM internship_friends WHERE user_id=?", c.user["id"])
    for f in b.friends: c.db.run("INSERT INTO internship_friends(user_id,name,class_name) VALUES(?,?,?)", c.user["id"], f.name.strip(), f.class_name.strip())
    c.db.run("UPDATE student_profiles SET class_name=? WHERE user_id=?", b.class_name.strip(), c.user["id"])
    return internship_get(c)

# ---------- AI assistant (rule-based; an LLM can be plugged in later) ----------
class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)

@api("/api/student/assistant", "POST", roles=S, model=AskIn)
def assistant(c, b):
    q = b.question.lower(); uid = c.user["id"]; d = c.db; L = c.lang
    plan = E.active_plan(d, uid); recs = E.recommend(d, uid)
    def has(*w): return any(x in q for x in w)
    def say(key, reasons=None, next_key="", **kw):
        return {"answer": msg(L, key, **kw), "reasons": reasons or [], "next_action": msg(L, next_key) if next_key else ""}
    if recs is None: return say("ai.unknown_you", next_key="ai.open_discovery")
    if has("why", "reason", "recommend", "alasan", "kenapa", "cocok", "mengapa", "rekomendasi"):
        top = recs[0]
        return say("ai.why", top["reasons"], "ai.why_next", name=top["name"], match=top["match"])
    if has("internship", "magang", "pkl"):
        n = d.one("SELECT COUNT(*) n FROM internship_choices WHERE user_id=?", uid)["n"]
        return say("ai.intern_some" if n else "ai.intern_none", next_key="ai.open_internship", n=n)
    if has("gap", "skill", "kurang", "belajar", "learn", "keahlian"):
        if not plan: return say("ai.gap_noplan", next_key="ai.open_plan")
        mine = E.student_skill_map(d, uid)
        gap = [s["name"] for s in E.career_skills(d, plan["career_id"]) if mine.get(s["id"], 0) < E.GAP_THRESHOLD]
        return say("ai.gap", next_key="ai.open_learning", career=plan["career_name"], skills=", ".join(gap) or msg(L, "ai.gap_none"))
    if has("progress", "ready", "readiness", "kesiapan", "kemajuan", "perkembangan"):
        return say("ai.ready", next_key="ai.open_learning", value=E.readiness(d, uid))
    if has("start", "begin", "first", "mulai", "next", "what should", "selanjutnya", "berikutnya", "harus"):
        if not plan: return say("ai.start_noplan", recs[0]["reasons"], "ai.open_plan", name=recs[0]["name"])
        t = d.one("SELECT title,kind,skill_id FROM tasks WHERE plan_id=? AND status<>'COMPLETED' ORDER BY position LIMIT 1", plan["id"])
        if t: return say("ai.next_task", next_key="ai.open_learning", title=E.task_view(d, t)["title"])
        return say("ai.all_done", next_key="ai.open_learning")
    return say("ai.fallback")
