"""Business logic: recommendation engine (rule-based, explainable), skill gap, plan generation, readiness, status.
The recommendation engine is separate from any LLM, as the project rules require."""
import json
from datetime import datetime, timezone
from .messages import msg, tag_name, level_name, CATALOG

# Evidence ladder (project rule: a claimed skill is not automatically valid)
SELF_CLAIMED, LEARNING, PROJECT_EVIDENCE, TEACHER_VERIFIED = 1, 2, 3, 4
LEVEL_NAME = {1: "Self claimed", 2: "Learning", 3: "Project evidence", 4: "Teacher verified"}   # nama bahasa Inggris (kode)
def lvl(db, level):
    """Nama tingkat bukti dalam bahasa permintaan ini."""
    return level_name(db.lang, level) if level in LEVEL_NAME else None
LEVEL_WEIGHT = {1: 0.25, 2: 0.5, 3: 0.8, 4: 1.0}
GAP_THRESHOLD = PROJECT_EVIDENCE   # a required skill below this level is still a gap

def jl(s):
    try: return json.loads(s) if s else []
    except Exception: return []
def csv(s): return [x.strip() for x in (s or "").split(",") if x.strip()]

# ---------------- assessment ----------------
def score_answers(questions, answers):
    """answers: {question_id: 1..5}. Returns {tag: 0..1} per kind."""
    acc = {}
    for q in questions:
        v = answers.get(str(q["id"]), answers.get(q["id"]))
        if v is None: continue
        acc.setdefault((q["kind"], q["tag"]), []).append((int(v) - 1) / 4)
    out = {"interest": {}, "strength": {}}
    for (kind, tag), vals in acc.items():
        out[kind][tag] = round(sum(vals) / len(vals), 3)
    return out

def latest_assessment(db, user_id, saved_only=False):
    sql = "SELECT * FROM assessments WHERE user_id=?" + (" AND saved=1" if saved_only else "") + " ORDER BY id DESC LIMIT 1"
    a = db.one(sql, user_id)
    if a: a["scores"] = json.loads(a["scores"]); a["answers"] = json.loads(a["answers"])
    return a

def student_skill_map(db, user_id):
    return {r["skill_id"]: r["level"] for r in db.all("SELECT skill_id, level FROM student_skills WHERE user_id=?", user_id)}

def raise_skill(db, user_id, skill_id, level):
    cur = db.one("SELECT level FROM student_skills WHERE user_id=? AND skill_id=?", user_id, skill_id)
    if cur is None: db.run("INSERT INTO student_skills(user_id,skill_id,level) VALUES(?,?,?)", user_id, skill_id, level)
    elif cur["level"] < level: db.run("UPDATE student_skills SET level=? WHERE user_id=? AND skill_id=?", level, user_id, skill_id)

def career_skills(db, career_id):
    rows = db.all("""SELECT s.id, s.name, s.category, cs.importance FROM career_skills cs
                     JOIN skills s ON s.id=cs.skill_id WHERE cs.career_id=? ORDER BY cs.importance DESC, s.name""", career_id)
    for r in rows: r["name"] = db.tr("skill", r["id"], "name", r["name"])
    return rows

def skill_name(db, skill_id, default=""):
    return db.tr("skill", skill_id, "name", default)

def career_text(db, row, fields=("name", "description", "responsibilities", "education_path", "example_projects", "growth")):
    """Salin baris karier dengan teks dalam bahasa permintaan ini."""
    out = dict(row)
    for f in fields:
        if f in out: out[f] = db.tr("career", row["id"], f, row[f])
    return out

# ---------------- teks yang dirangkai dari data ----------------
def render_reason(db, item):
    """item: teks lama (string, dilewatkan apa adanya) atau [kode, argumen]. Rencana lama menyimpan string Inggris."""
    if isinstance(item, str): return item
    code, arg = item[0], (item[1] if len(item) > 1 else None)
    L = db.lang
    if code == "interest_fit": return msg(L, "reason.interest_fit", tags=", ".join(tag_name(L, t) for t in arg))
    if code == "strength_fit": return msg(L, "reason.strength_fit", tags=", ".join(tag_name(L, t) for t in arg))
    if code == "major_path": return msg(L, "reason.major_path", major=arg)
    if code in ("have_skills", "build_skills"):
        return msg(L, "reason." + code, skills=", ".join(skill_name(db, i, str(i)) for i in arg))
    return msg(L, "reason." + code)

def render_reasons(db, items): return [render_reason(db, i) for i in items]

def task_view(db, t):
    """Judul dan deskripsi tugas dibuat saat dibaca, supaya ikut bahasa yang sedang dipilih."""
    out = dict(t)
    if t.get("kind") in ("STUDY", "PRACTICE", "APPLY") and t.get("skill_id"):
        base = db.one("SELECT name FROM skills WHERE id=?", t["skill_id"])
        name = skill_name(db, t["skill_id"], base["name"] if base else "")
        out["title"] = msg(db.lang, f"task.{t['kind']}.title", skill=name)
        out["description"] = msg(db.lang, f"task.{t['kind']}.desc", skill=name)
    if ("difficulty." + str(t.get("difficulty"))) in CATALOG: out["difficulty"] = msg(db.lang, "difficulty." + t["difficulty"])
    return out

# ---------------- recommendation ----------------
W_INTEREST, W_STRENGTH, W_SKILL, W_MAJOR = 0.35, 0.25, 0.25, 0.15

def _avg(tags, scores):
    vals = [scores[t] for t in tags if t in scores]
    return sum(vals) / len(vals) if vals else 0.0

def recommend(db, user_id, limit=None):
    a = latest_assessment(db, user_id)
    if not a: return None
    prof = db.one("SELECT major FROM student_profiles WHERE user_id=?", user_id) or {"major": ""}
    skills = student_skill_map(db, user_id)
    out = []
    for c in db.all("SELECT * FROM careers ORDER BY id"):
        i = _avg(csv(c["interest_tags"]), a["scores"]["interest"])
        s = _avg(csv(c["strength_tags"]), a["scores"]["strength"])
        req = career_skills(db, c["id"])
        tot = sum(r["importance"] for r in req) or 1
        have = sum(r["importance"] * LEVEL_WEIGHT.get(skills.get(r["id"], 0), 0) for r in req)
        sk = have / tot
        mjs = csv(c["majors"])   # jalur khusus satu jurusan lebih tepat daripada karier yang terbuka untuk semua jurusan
        mj = (1.0 if len(mjs) == 1 else 0.6) if prof["major"] and prof["major"] in mjs else 0.0
        score = W_INTEREST * i + W_STRENGTH * s + W_SKILL * sk + W_MAJOR * mj
        codes = []
        if i >= 0.6: codes.append(["interest_fit", [t for t in csv(c["interest_tags"]) if a["scores"]["interest"].get(t, 0) >= 0.6]])
        elif i >= 0.4: codes.append(["interest_mid"])
        if s >= 0.6: codes.append(["strength_fit", [t for t in csv(c["strength_tags"]) if a["scores"]["strength"].get(t, 0) >= 0.6]])
        if mj: codes.append(["major_path", prof["major"]])
        known = [r["id"] for r in req if r["id"] in skills]
        if known: codes.append(["have_skills", known[:3]])
        gaps = [r["id"] for r in req if skills.get(r["id"], 0) < GAP_THRESHOLD]
        if gaps: codes.append(["build_skills", gaps[:3]])
        if not codes: codes.append(["weak"])
        lc = career_text(db, c, ("name", "description"))
        out.append({"_s": score, "career_id": c["id"], "name": lc["name"], "category": c["category"], "description": lc["description"],
                    "match": round(score * 100), "reasons": render_reasons(db, codes), "reason_codes": codes,
                    "parts": {"interest": round(i * 100), "strength": round(s * 100), "skills": round(sk * 100), "major": round(mj * 100)}})
    out.sort(key=lambda r: (-r["_s"], r["name"]))   # skor tepat dulu, lalu nama: urutan stabil walau skor bulatnya sama
    for r in out: del r["_s"]
    return out[:limit] if limit else out

def insight(db, user_id):
    a = latest_assessment(db, user_id)
    if not a: return None
    top = lambda d: [k for k, v in sorted(d.items(), key=lambda kv: -kv[1]) if v >= 0.5][:3] or [k for k, v in sorted(d.items(), key=lambda kv: -kv[1])][:2]
    ints, strs = top(a["scores"]["interest"]), top(a["scores"]["strength"])
    careers = [{k: v for k, v in r.items() if k != "reason_codes"} for r in recommend(db, user_id, 3)]
    return {"assessment_id": a["id"], "saved": bool(a["saved"]), "interests": ints, "strengths": strs,
            "interest_labels": [tag_name(db.lang, t) for t in ints], "strength_labels": [tag_name(db.lang, t) for t in strs],
            "scores": a["scores"], "careers": careers}

# ---------------- plan ----------------
def plan_preview(db, user_id, career_id):
    c = db.one("SELECT * FROM careers WHERE id=?", career_id)
    if not c: return None
    skills = student_skill_map(db, user_id)
    req = career_skills(db, career_id)
    current = [{"id": r["id"], "name": r["name"], "level": lvl(db, skills[r["id"]])} for r in req if r["id"] in skills]
    gap = [r for r in req if skills.get(r["id"], 0) < GAP_THRESHOLD]
    milestones = []
    for n, r in enumerate(gap[:6], 1):
        milestones.append({"milestone": n, "skill_id": r["id"], "skill": r["name"], "tasks": make_tasks(r["name"], db.lang)})
    lc = career_text(db, c, ("name", "description", "example_projects"))
    return {"career": {"id": c["id"], "name": lc["name"], "description": lc["description"], "example_projects": lc["example_projects"]},
            "current_skills": current, "skill_gap": [{"id": r["id"], "name": r["name"], "importance": r["importance"]} for r in gap],
            "milestones": milestones}

def make_tasks(skill, lang="en"):
    spec = (("STUDY", "Beginner", 3), ("PRACTICE", "Beginner", 4), ("APPLY", "Intermediate", 6))
    return [{"kind": k, "title": msg(lang, f"task.{k}.title", skill=skill), "difficulty": d, "est_hours": h,
             "description": msg(lang, f"task.{k}.desc", skill=skill)} for k, d, h in spec]

def create_plan(db, user_id, career_id):
    prev = plan_preview(db, user_id, career_id)
    if not prev: return None
    cur = active_plan(db, user_id)
    if cur and cur["career_id"] == career_id: return cur["id"]          # karier yang sama: jangan buat ulang (progres tugas tetap)
    db.run("UPDATE plans SET status='ARCHIVED' WHERE user_id=? AND status='ACTIVE'", user_id)
    old = db.one("SELECT id FROM plans WHERE user_id=? AND career_id=? AND status='ARCHIVED' ORDER BY id DESC LIMIT 1", user_id, career_id)
    if old and db.one("SELECT 1 x FROM tasks WHERE plan_id=?", old["id"]):   # kembali ke karier lama: aktifkan lagi rencana lamanya, progres tidak hilang
        db.run("UPDATE plans SET status='ACTIVE' WHERE id=?", old["id"]); log_readiness(db, user_id); return old["id"]
    recs = recommend(db, user_id) or []
    reasons = next((r["reason_codes"] for r in recs if r["career_id"] == career_id), [])
    pid = db.run("INSERT INTO plans(user_id,career_id,reasons) VALUES(?,?,?)", user_id, career_id, json.dumps(reasons))
    pos = 0
    for m in prev["milestones"]:
        db.run("INSERT OR IGNORE INTO milestones(plan_id,number,skill_id) VALUES(?,?,?)", pid, m["milestone"], m["skill_id"])
        for t in make_tasks(db.one("SELECT name FROM skills WHERE id=?", m["skill_id"])["name"], "en"):
            pos += 1
            db.run("""INSERT INTO tasks(plan_id,skill_id,milestone,position,kind,title,description,difficulty,est_hours)
                      VALUES(?,?,?,?,?,?,?,?,?)""", pid, m["skill_id"], m["milestone"], pos, t["kind"], t["title"], t["description"], t["difficulty"], t["est_hours"])
    log_readiness(db, user_id)
    return pid

def active_plan(db, user_id):
    p = db.one("""SELECT p.*, c.name AS career_name FROM plans p JOIN careers c ON c.id=p.career_id
                  WHERE p.user_id=? AND p.status='ACTIVE' ORDER BY p.id DESC LIMIT 1""", user_id)
    if p: p["career_name"] = db.tr("career", p["career_id"], "name", p["career_name"])
    return p

# ---------------- readiness ----------------
def readiness(db, user_id):
    """Kesiapan: 50% tugas + 50% bukti skill; bila kariernya punya kursus: 35% tugas + 35% skill + 30% kursus."""
    plan = active_plan(db, user_id)
    if not plan: return 0
    t = db.one("SELECT COUNT(*) n, SUM(status='COMPLETED') d FROM tasks WHERE plan_id=?", plan["id"])
    task_part = (t["d"] or 0) / t["n"] if t["n"] else 0
    skills = student_skill_map(db, user_id)
    req = career_skills(db, plan["career_id"])
    tot = sum(r["importance"] for r in req) or 1
    skill_part = sum(r["importance"] * LEVEL_WEIGHT.get(skills.get(r["id"], 0), 0) for r in req) / tot
    from . import coursework as CW
    if CW.has_course(plan["career_id"]):      # ada kursus karier: 35% tugas, 35% bukti skill, 30% kemajuan kursus
        return round((0.35 * task_part + 0.35 * skill_part + 0.30 * CW.done_count(db, user_id, plan["career_id"]) / 6) * 100)
    return round((0.5 * task_part + 0.5 * skill_part) * 100)

def log_readiness(db, user_id):
    v = readiness(db, user_id)
    last = db.one("SELECT value FROM readiness_log WHERE user_id=? ORDER BY id DESC LIMIT 1", user_id)
    if not last or last["value"] != v:
        db.run("INSERT INTO readiness_log(user_id,value) VALUES(?,?)", user_id, v)
    return v

# ---------------- student status (for teachers) ----------------
INACTIVE_DAYS = 14
def student_status(db, u):
    """u: dict with id, last_active_at. Returns flags and one primary status label."""
    try: last = datetime.strptime(u["last_active_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception: last = datetime.now(timezone.utc)
    inactive = (datetime.now(timezone.utc) - last).days >= INACTIVE_DAYS
    plan = active_plan(db, u["id"])
    pending = db.one("SELECT COUNT(*) n FROM projects WHERE user_id=? AND status='SUBMITTED'", u["id"])["n"] > 0
    r = readiness(db, u["id"]) if plan else 0
    flags = {"inactive": inactive, "no_plan": plan is None, "needs_feedback": pending, "on_track": bool(plan) and r >= 50 and not inactive}
    label = ("Inactive" if inactive else "No plan yet" if plan is None else "Needs feedback" if pending
             else "On track" if flags["on_track"] else "Active")
    return {"flags": flags, "status": label, "readiness": r}
