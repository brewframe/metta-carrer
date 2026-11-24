"""Kursus karier: 6 bab per karier. Kunci jawaban tidak pernah dikirim ke browser.

Aturan (semuanya dijalankan di server):
- Bab dibuka berurutan. Bab 1 selesai setelah dibaca (ada waktu baca minimal).
- Bab 2-5: kerjakan latihan, lalu kuis 6 soal diambil acak dari 7 soal bab itu. Lulus bila benar >= 5.
- Bab 6: tautkan project yang lengkap lalu tunggu guru memverifikasi, dan lulus ujian akhir 12 soal (benar >= 9).
- Gagal: tunggu 1 menit sebelum mencoba lagi. Soal dan urutan pilihan diacak tiap percobaan.
"""
import json, random, secrets
from typing import List
from pydantic import BaseModel, Field
from ..core import api, bad, not_found
from .. import engine as E
from .. import course as CRS
from .. import coursework as CW
from .student import project_row

S = ["student"]
LEVEL = {"A": "SMA", "K": "SMK"}


def _plan_course(c):
    plan = E.active_plan(c.db, c.user["id"])
    if not plan or not CW.has_course(plan["career_id"]): raise not_found("No course for this career yet")
    return plan, plan["career_id"], CRS.COURSES[plan["career_id"]]


def _perm(seed, pos, n):
    idx = list(range(n)); random.Random(f"{seed}:{pos}").shuffle(idx); return idx


def _chapter_row(c, cid, n, create=True):
    r = c.db.one("SELECT * FROM course_progress WHERE user_id=? AND career_id=? AND chapter=?", c.user["id"], cid, n)
    if not r and create:
        c.db.run("INSERT INTO course_progress(user_id,career_id,chapter) VALUES(?,?,?)", c.user["id"], cid, n)
        r = c.db.one("SELECT * FROM course_progress WHERE user_id=? AND career_id=? AND chapter=?", c.user["id"], cid, n)
    return r


def _attempts(c, cid, n):
    return c.db.all("SELECT id,score,total,passed,created_at,finished_at FROM course_attempts WHERE user_id=? AND career_id=? AND chapter=? AND finished_at IS NOT NULL ORDER BY id DESC",
                    c.user["id"], cid, n)


def _need(n): return CRS.PASS_FINAL if n == 6 else CRS.PASS_CHAPTER


def _wait_left(c, cid, n):
    r = c.db.one("""SELECT ? - (CAST(strftime('%s','now') AS INTEGER) - CAST(strftime('%s',finished_at) AS INTEGER)) w FROM course_attempts
                    WHERE user_id=? AND career_id=? AND chapter=? AND finished_at IS NOT NULL AND passed=0 ORDER BY id DESC LIMIT 1""", CRS.COOLDOWN_SEC, c.user["id"], cid, n)
    return max(0, r["w"]) if r else 0


@api("/api/student/course", roles=S)
def course_summary(c):
    uid = c.user["id"]; plan = E.active_plan(c.db, uid)
    if not plan: return {"available": False, "reason": "no_plan"}
    cid = plan["career_id"]
    if not CW.has_course(cid): return {"available": False, "reason": "no_course", "career": plan["career_name"]}
    CW.sync(c.db, uid, cid)
    done = CW.done_map(c.db, uid, cid); co = CRS.COURSES[cid]
    ch = [{"n": n, "title": CRS.CH_TITLES[n], "done": done[n], "locked": not CW.unlocked(done, n)} for n in range(1, 7)]
    return {"available": True, "career": plan["career_name"], "chapters": ch, "done": sum(done.values()), "total": 6,
            "pass_chapter": CRS.PASS_CHAPTER, "quiz_n": CRS.QUIZ_N, "pass_final": CRS.PASS_FINAL, "final_n": CRS.FINAL_N}


@api("/api/student/course/chapter/{n:int}", roles=S)
def chapter_get(c, n):
    plan, cid, co = _plan_course(c); uid = c.user["id"]
    if not 1 <= n <= 6: raise not_found("Chapter not found")
    done = CW.done_map(c.db, uid, cid)
    if not CW.unlocked(done, n): raise bad("This chapter is locked. Finish the previous chapter first.")
    row = _chapter_row(c, cid, n)
    out = {"n": n, "title": CRS.CH_TITLES[n], "career": plan["career_name"], "done": done[n],
           "sources": [{"t": t, "u": u} for t, u in co.get("sources", [])]}
    if n <= 5:
        ch = co["chapters"][n]
        out.update({"goals": ch["goals"], "sections": [{"h": h, "t": t} for h, t in ch["sections"]]})
    if n == 1:
        left = c.db.one("SELECT ? - (CAST(strftime('%s','now') AS INTEGER) - CAST(strftime('%s',?) AS INTEGER)) w", CRS.READ_MIN_SEC, row["opened_at"])["w"]
        out["read_wait"] = max(0, left)
    if 2 <= n <= 5:
        att = _attempts(c, cid, n)
        out.update({"practice": co["chapters"][n]["practice"], "quiz_n": CRS.QUIZ_N, "pass": CRS.PASS_CHAPTER,
                    "attempts": len(att), "best": max((a["score"] for a in att), default=None), "passed": any(a["passed"] for a in att), "wait": _wait_left(c, cid, n)})
    if n == 6:
        pr = co["project"]; att = _attempts(c, cid, 6); pj = CW.linked_project(c.db, uid, cid)
        mine = [{"id": p["id"], "title": p["title"], "status": p["status"]} for p in c.db.all("SELECT id,title,status FROM projects WHERE user_id=? ORDER BY id DESC", uid)]
        out.update({"project": {"title": pr["title"], "brief": pr["brief"], "criteria": pr["criteria"]}, "linked": pj, "my_projects": mine,
                    "exam_n": CRS.FINAL_N, "pass": CRS.PASS_FINAL, "attempts": len(att), "best": max((a["score"] for a in att), default=None),
                    "passed": any(a["passed"] for a in att), "wait": _wait_left(c, cid, 6)})
    return out


@api("/api/student/course/chapter/{n:int}/read", "POST", roles=S)
def chapter_read(c, n):
    plan, cid, co = _plan_course(c); uid = c.user["id"]
    if n != 1: raise bad("Only chapter 1 is marked as read")
    row = _chapter_row(c, cid, 1)
    wait = c.db.one("SELECT ? - (CAST(strftime('%s','now') AS INTEGER) - CAST(strftime('%s',?) AS INTEGER)) w", CRS.READ_MIN_SEC, row["opened_at"])["w"]
    if wait > 0: raise bad("Read the material first. You can mark it as read after about a minute.")
    c.db.run("UPDATE course_progress SET done_at=COALESCE(done_at,datetime('now')) WHERE user_id=? AND career_id=? AND chapter=1", uid, cid)
    return {"ok": True}


def _pick(co, n, seed):
    rnd = random.Random(seed); bank = co["bank"]
    if n == 6:
        ids = []
        for k in (2, 3, 4, 5): ids += rnd.sample([i for i, q in enumerate(bank) if q[0] == k], 3)
        rnd.shuffle(ids); return ids
    ids = rnd.sample([i for i, q in enumerate(bank) if q[0] == n], CRS.QUIZ_N); return ids


def _view(co, att):
    qids = json.loads(att["qids"]); qs = []
    for pos, qi in enumerate(qids):
        q = co["bank"][qi]; order = _perm(att["seed"], pos, 4)
        qs.append({"q": q[2], "level": LEVEL[q[1]], "options": [q[3][j] for j in order]})
    return {"attempt": att["id"], "chapter": att["chapter"], "total": att["total"], "pass": _need(att["chapter"]), "questions": qs}


@api("/api/student/course/chapter/{n:int}/quiz", "POST", roles=S)
def quiz_start(c, n):
    plan, cid, co = _plan_course(c); uid = c.user["id"]
    if not 2 <= n <= 6: raise bad("This chapter has no quiz")
    done = CW.done_map(c.db, uid, cid)
    if not CW.unlocked(done, n): raise bad("This chapter is locked. Finish the previous chapter first.")
    if n <= 5: _chapter_row(c, cid, n)
    if _wait_left(c, cid, n) > 0: raise bad("Please wait a minute before trying again")
    old = c.db.one("""SELECT * FROM course_attempts WHERE user_id=? AND career_id=? AND chapter=? AND finished_at IS NULL
                      AND CAST(strftime('%s','now') AS INTEGER) - CAST(strftime('%s',created_at) AS INTEGER) < 3600 ORDER BY id DESC LIMIT 1""", uid, cid, n)
    if old: return _view(co, old)
    c.db.run("UPDATE course_attempts SET finished_at=datetime('now') WHERE user_id=? AND career_id=? AND chapter=? AND finished_at IS NULL", uid, cid, n)   # percobaan lama yang menggantung ditutup
    seed = secrets.token_hex(8); ids = _pick(co, n, seed)
    aid = c.db.run("INSERT INTO course_attempts(user_id,career_id,chapter,qids,seed,total) VALUES(?,?,?,?,?,?)", uid, cid, n, json.dumps(ids), seed, len(ids))
    return _view(co, c.db.one("SELECT * FROM course_attempts WHERE id=?", aid))


class AnswersIn(BaseModel):
    answers: List[int] = Field(min_length=1, max_length=20)


@api("/api/student/course/attempt/{aid:int}/submit", "POST", roles=S, model=AnswersIn)
def quiz_submit(c, b, aid):
    plan, cid, co = _plan_course(c); uid = c.user["id"]
    att = c.db.one("SELECT * FROM course_attempts WHERE id=? AND user_id=? AND career_id=?", aid, uid, cid)
    if not att: raise not_found("Attempt not found")
    if att["finished_at"]: raise bad("This attempt is already finished")
    qids = json.loads(att["qids"])
    if len(b.answers) != len(qids) or any(not 0 <= a < 4 for a in b.answers): raise bad("Answer every question")
    score, res, weak = 0, [], set()
    for pos, qi in enumerate(qids):
        q = co["bank"][qi]; order = _perm(att["seed"], pos, 4); ok = order[b.answers[pos]] == q[4]
        score += ok
        if not ok: weak.add(q[0])
        res.append({"correct": ok, "why": q[5], "answer": q[3][q[4]]})
    n = att["chapter"]; passed = score >= _need(n)
    c.db.run("UPDATE course_attempts SET score=?, passed=?, finished_at=datetime('now') WHERE id=?", score, int(passed), aid)
    out = {"score": score, "total": len(qids), "passed": passed, "need": _need(n), "chapter": n, "wait": 0 if passed else CRS.COOLDOWN_SEC}
    if not passed:                                  # gagal: tidak ada benar/salah per soal dan tidak ada penjelasan, supaya jawaban tidak bisa ditebak lewat percobaan berulang
        out["results"] = []
        if n == 6: out["weak_chapters"] = sorted(weak)      # ujian akhir: hanya bab mana yang perlu dibaca ulang
    else:
        out["results"] = res
    if passed: CW.sync(c.db, uid, cid); E.log_readiness(c.db, uid)
    return out


class ProjectIn(BaseModel):
    project_id: int = Field(ge=1)


@api("/api/student/course/project", "POST", roles=S, model=ProjectIn)
def link_project(c, b):
    plan, cid, co = _plan_course(c); uid = c.user["id"]
    if not CW.unlocked(CW.done_map(c.db, uid, cid), 6): raise bad("This chapter is locked. Finish the previous chapter first.")
    p = c.db.one("SELECT * FROM projects WHERE id=? AND user_id=?", b.project_id, uid)
    if not p: raise not_found("Project not found")
    cur = CW.linked_project(c.db, uid, cid)
    if cur and cur["status"] == "VERIFIED" and cur["id"] != p["id"]: raise bad("This course already has a verified project")
    from .files import files_map
    has_proof = any((p[k] or "").strip() for k in ("link", "demo_url", "repo_url", "doc_url")) or bool(files_map(c.db, "project", [p["id"]])[p["id"]])
    if len((p["problem"] or "").strip()) < 40 or len((p["solution"] or "").strip()) < 40 or len((p["result"] or "").strip()) < 20 or not has_proof:
        raise bad("Complete the project first: problem (40+ characters), solution (40+), result (20+), and add a demo, repository, document, link or file")
    c.db.run("INSERT INTO course_projects(user_id,career_id,project_id) VALUES(?,?,?) ON CONFLICT(user_id,career_id) DO UPDATE SET project_id=excluded.project_id", uid, cid, p["id"])
    return {"ok": True}
