import json
from pydantic import BaseModel, Field
from ..core import api, not_found, bad, notify, audit, user_lang
from .. import engine as E
from ..messages import msg, tag_name
from .student import project_row

T = ["teacher"]

def students_list(c):
    rows = c.db.all("""SELECT u.id,u.name,u.email,u.last_active_at,sp.major,sp.class_name FROM users u
                       LEFT JOIN student_profiles sp ON sp.user_id=u.id WHERE u.role='student' AND u.active=1 ORDER BY u.name""")
    for r in rows:
        st = E.student_status(c.db, r); r.update(st)
        plan = E.active_plan(c.db, r["id"]); r["target"] = plan["career_name"] if plan else None
    return rows

@api("/api/teacher/summary", roles=T)
def summary(c):
    rows = students_list(c)
    n = lambda f: sum(1 for r in rows if f(r))
    return {"total": len(rows), "on_track": n(lambda r: r["flags"]["on_track"]), "active": n(lambda r: not r["flags"]["inactive"]),
            "inactive": n(lambda r: r["flags"]["inactive"]), "needs_feedback": n(lambda r: r["flags"]["needs_feedback"]),
            "no_plan": n(lambda r: r["flags"]["no_plan"]),
            "attention": [{"id": r["id"], "name": r["name"], "status": r["status"], "last_active_at": r["last_active_at"]}
                          for r in rows if r["status"] in ("Inactive", "Needs feedback", "No plan yet")][:8]}

@api("/api/teacher/students", roles=T)
def students(c):
    q = (c.request.query_params.get("q") or "").lower(); st = c.request.query_params.get("status") or ""; mj = c.request.query_params.get("major") or ""
    return {"items": [r for r in students_list(c) if (not q or q in r["name"].lower()) and (not st or r["status"] == st) and (not mj or r["major"] == mj)]}

@api("/api/teacher/students/{sid:int}", roles=T)
def student_detail(c, sid):
    u = c.db.one("SELECT id,name,email,last_active_at FROM users WHERE id=? AND role='student'", sid)
    if not u: raise not_found("Student not found")
    prof = c.db.one("SELECT school,major,class_name,goal FROM student_profiles WHERE user_id=?", sid) or {}
    plan = E.active_plan(c.db, sid)
    tasks = [E.task_view(c.db, t) for t in c.db.all("SELECT title,status,kind,skill_id,difficulty FROM tasks WHERE plan_id=? ORDER BY position", plan["id"])] if plan else []
    skills = c.db.all("SELECT s.id, s.name, ss.level FROM student_skills ss JOIN skills s ON s.id=ss.skill_id WHERE ss.user_id=? ORDER BY ss.level DESC", sid)
    for s in skills: s["name"] = c.db.tr("skill", s.pop("id"), "name", s["name"]); s["evidence"] = E.lvl(c.db, s["level"])
    choices = c.db.all("SELECT ic.rank, co.name FROM internship_choices ic JOIN companies co ON co.id=ic.company_id WHERE ic.user_id=? ORDER BY ic.rank", sid)
    fb = c.db.all("SELECT f.text,f.created_at,t.name teacher FROM feedback f JOIN users t ON t.id=f.teacher_id WHERE f.student_id=? ORDER BY f.id DESC LIMIT 10", sid)
    ins = E.insight(c.db, sid)
    return {"student": dict(u, **prof), "status": E.student_status(c.db, u), "plan": ({"id": plan["id"], "career": plan["career_name"], "teacher_note": plan["teacher_note"]} if plan else None),
            "tasks": tasks, "skills": skills, "projects": with_course(c, [project_row(c, p) for p in c.db.all("SELECT * FROM projects WHERE user_id=? ORDER BY id DESC", sid)]),
            "course": course_progress(c, sid, plan), "internship": choices, "feedback": fb, "insight": ({"interests": ins["interests"], "strengths": ins["strengths"], "interest_labels": ins["interest_labels"], "strength_labels": ins["strength_labels"]} if ins else None)}

class FeedbackIn(BaseModel):
    text: str = Field(min_length=3, max_length=1000)

@api("/api/teacher/students/{sid:int}/feedback", "POST", roles=T, model=FeedbackIn)
def feedback(c, b, sid):
    if not c.db.one("SELECT 1 x FROM users WHERE id=? AND role='student'", sid): raise not_found("Student not found")
    c.db.run("INSERT INTO feedback(student_id,teacher_id,text) VALUES(?,?,?)", sid, c.user["id"], b.text.strip())
    notify(c.db, sid, msg(user_lang(c.db, sid), "note.feedback", teacher=c.user["name"], text=b.text.strip()[:120]))

@api("/api/teacher/plans", roles=T)
def plans(c):
    rows = c.db.all("""SELECT p.id, u.name student, u.id student_id, ca.id career_id, ca.name career, p.teacher_note, p.created_at FROM plans p
        JOIN users u ON u.id=p.user_id JOIN careers ca ON ca.id=p.career_id WHERE p.status='ACTIVE' ORDER BY p.id DESC""")
    for r in rows: r["career"] = c.db.tr("career", r["career_id"], "name", r["career"])
    return {"items": rows}

class NoteIn(BaseModel):
    note: str = Field(min_length=1, max_length=1000)

@api("/api/teacher/plans/{pid:int}/guidance", "PUT", roles=T, model=NoteIn)
def guidance(c, b, pid):
    p = c.db.one("SELECT * FROM plans WHERE id=? AND status='ACTIVE'", pid)
    if not p: raise not_found("Plan not found")
    c.db.run("UPDATE plans SET teacher_note=? WHERE id=?", b.note.strip(), pid)
    notify(c.db, p["user_id"], msg(user_lang(c.db, p["user_id"]), "note.guidance", teacher=c.user["name"]))

def course_progress(c, sid, plan):
    from .. import coursework as CW
    if not plan or not CW.has_course(plan["career_id"]): return None
    return {"career": plan["career_name"], "done": CW.done_count(c.db, sid, plan["career_id"]), "total": 6}

def with_course(c, rows):
    """Project yang ditautkan ke bab 6 kursus karier membawa kriteria penilaian, supaya guru menilai dengan patokan yang sama."""
    from .. import course as CRS
    for r in rows:
        link = c.db.one("SELECT career_id FROM course_projects WHERE project_id=?", r["id"])
        if link and link["career_id"] in CRS.COURSES:
            co = CRS.COURSES[link["career_id"]]
            r["course"] = {"career": c.db.tr("career", link["career_id"], "name", co["name"]), "title": co["project"]["title"], "criteria": co["project"]["criteria"]}
    return rows

@api("/api/teacher/projects", roles=T)
def projects(c):
    rows = c.db.all("""SELECT p.*, u.name student FROM projects p JOIN users u ON u.id=p.user_id ORDER BY p.id DESC""")
    return {"items": with_course(c, [project_row(c, r) for r in rows])}

@api("/api/teacher/validation", roles=T)
def validation_queue(c):
    rows = c.db.all("""SELECT p.*, u.name student FROM projects p JOIN users u ON u.id=p.user_id WHERE p.status='SUBMITTED' ORDER BY p.id""")
    return {"items": with_course(c, [project_row(c, r) for r in rows])}

class ReviewIn(BaseModel):
    decision: str = Field(pattern="^(VERIFIED|NEEDS_REVISION)$"); note: str = Field("", max_length=1000)

@api("/api/teacher/projects/{pid:int}/review", "POST", roles=T, model=ReviewIn)
def review(c, b, pid):
    p = c.db.one("SELECT * FROM projects WHERE id=?", pid)
    if not p: raise not_found("Project not found")
    if p["status"] != "SUBMITTED": raise bad("This project is not waiting for review")
    if b.decision == "NEEDS_REVISION" and not b.note.strip(): raise bad("Revision notes are required")
    c.db.run("UPDATE projects SET status=?, teacher_note=?, reviewed_by=?, updated_at=datetime('now') WHERE id=?", b.decision, b.note.strip(), c.user["id"], pid)
    c.db.run("INSERT INTO project_feedback(project_id,teacher_id,decision,note) VALUES(?,?,?,?)", pid, c.user["id"], b.decision, b.note.strip())
    if b.decision == "VERIFIED":
        for sid in json.loads(p["skill_ids"]): E.raise_skill(c.db, p["user_id"], sid, E.TEACHER_VERIFIED)
        from .. import coursework as CW
        for lk in c.db.all("SELECT career_id FROM course_projects WHERE project_id=?", pid): CW.sync(c.db, p["user_id"], lk["career_id"])   # proyek bab 6 terverifikasi -> kursus bisa selesai
        notify(c.db, p["user_id"], msg(user_lang(c.db, p["user_id"]), "note.verified", title=p["title"]))
    else:
        notify(c.db, p["user_id"], msg(user_lang(c.db, p["user_id"]), "note.revision", title=p["title"], note=b.note.strip()[:120]))
    E.log_readiness(c.db, p["user_id"]); audit(c, "project_review", f"{pid}:{b.decision}")

@api("/api/teacher/internship", roles=T)
def internship(c):
    q = (c.request.query_params.get("q") or "").lower()
    rows = c.db.all("SELECT u.id,u.name,sp.class_name,sp.major FROM users u LEFT JOIN student_profiles sp ON sp.user_id=u.id WHERE u.role='student' AND u.active=1 ORDER BY u.name")
    out = []
    for r in rows:
        ch = {x["rank"]: x for x in c.db.all("SELECT ic.rank, co.name, ic.purpose FROM internship_choices ic JOIN companies co ON co.id=ic.company_id WHERE ic.user_id=?", r["id"])}
        r["choices"] = [ch[k]["name"] if k in ch else "" for k in (1, 2, 3)]
        r["purposes"] = [ch[k]["purpose"] if k in ch else "" for k in (1, 2, 3)]
        r["friends"] = [f["name"] + (" (" + f["class_name"] + ")" if f["class_name"] else "") for f in c.db.all("SELECT name,class_name FROM internship_friends WHERE user_id=? ORDER BY id", r["id"])]
        if not q or q in r["name"].lower() or any(q in x.lower() for x in r["choices"]): out.append(r)
    return {"items": out}

@api("/api/teacher/analytics", roles=T)
def analytics(c):
    rows = students_list(c); by_class = {}; by_major = {}
    for r in rows:
        by_class.setdefault(r["class_name"] or "-", []).append(r["readiness"]); by_major.setdefault(r["major"] or "-", []).append(r["readiness"])
    avg = lambda d: [{"label": k, "avg_readiness": round(sum(v) / len(v)), "students": len(v)} for k, v in sorted(d.items())]
    # sebaran status siswa (urutan tetap, kategori kosong tetap ditampilkan sebagai 0)
    status = [{"key": k, "value": sum(1 for r in rows if r["status"] == k)} for k in ("On track", "Active", "Needs feedback", "No plan yet", "Inactive")]
    ids = [r["id"] for r in rows]; q = ",".join("?" * len(ids)) or "NULL"
    got = {x["status"]: x["n"] for x in c.db.all(f"SELECT status, COUNT(*) n FROM projects WHERE user_id IN ({q}) GROUP BY status", *ids)}
    projects = [{"key": k, "value": got.get(k, 0)} for k in ("SUBMITTED", "NEEDS_REVISION", "VERIFIED")]
    tc = {}
    for r in rows:
        if r["target"]: tc[r["target"]] = tc.get(r["target"], 0) + 1
    careers = [{"label": k, "value": v} for k, v in sorted(tc.items(), key=lambda x: (-x[1], x[0]))[:8]]
    return {"by_class": avg(by_class), "by_major": avg(by_major), "status": status, "projects": projects, "careers": careers, "total": len(rows)}
