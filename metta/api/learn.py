"""Belajar: panduan langkah, latihan, dan kuis per tugas.

Aturan (dijalankan di server, bukan di tampilan):
- STUDY   selesai bila semua langkah dicentang.
- PRACTICE selesai bila lulus kuis (nilai >= 70%); skill tanpa kuis tertulis bisa langsung ditandai selesai setelah latihan.
- APPLY   selesai bila siswa sudah punya project yang memakai skill itu.
Jawaban benar kuis tidak pernah dikirim ke browser sebelum dijawab; urutan pilihan diacak berbeda tiap percobaan.
"""
import hashlib, json, random
from typing import List
from pydantic import BaseModel, Field
from ..core import api, bad, not_found
from .. import engine as E
from .. import seed_learning as SL

S = ["student"]

def _task(c, tid):
    t = c.db.one("""SELECT t.* FROM tasks t JOIN plans p ON p.id=t.plan_id WHERE t.id=? AND p.user_id=? AND p.status='ACTIVE'""", tid, c.user["id"])
    if not t: raise not_found("Task not found")
    return t

def _opt(o, lang):
    en, _, idn = o.partition("||")
    return (idn if (lang == "id" and idn) else en)

def _lesson(c, skill_name):
    L = SL.L.get(skill_name); i = c.lang == "id"
    if L:
        return {"goal": L["goal"][1 if i else 0], "steps": [s[1 if i else 0] for s in L["steps"]], "practice": L["practice"][1 if i else 0], "authored": True, "quiz": L["quiz"]}
    g = SL.generic("id" if i else "en")
    return {"goal": g["goal"], "steps": [s.format(s=skill_name) for s in g["steps"]], "practice": g["practice"].format(s=skill_name), "authored": False, "quiz": []}

def _attempts(c, skill_id):
    return c.db.all("SELECT score,total,passed,created_at FROM quiz_attempts WHERE user_id=? AND skill_id=? ORDER BY id DESC", c.user["id"], skill_id)

def _order(uid, skill_id, qi, n_attempt, n_opts):
    """Urutan pilihan diacak, tetap sama selama jumlah percobaan sama (jadi penilaian tanpa menyimpan keadaan)."""
    seed = int(hashlib.sha256(f"{uid}:{skill_id}:{qi}:{n_attempt}".encode()).hexdigest()[:12], 16)
    idx = list(range(n_opts)); random.Random(seed).shuffle(idx); return idx

def _state(c, t):
    """Apa yang sudah dipenuhi untuk tugas ini + alasan jika belum bisa selesai."""
    skill = c.db.one("SELECT id,name FROM skills WHERE id=?", t["skill_id"]) if t["skill_id"] else None
    name = skill["name"] if skill else ""
    L = _lesson(c, name)
    done = {r["idx"] for r in c.db.all("SELECT idx FROM task_steps WHERE task_id=?", t["id"])}
    att = _attempts(c, t["skill_id"]) if skill else []
    passed = any(a["passed"] for a in att)
    ready, why = True, ""
    if t["kind"] == "STUDY" and len(done) < len(L["steps"]): ready, why = False, "Tick every step first."
    elif t["kind"] == "PRACTICE":
        if L["authored"] and not passed: ready, why = False, "Pass the quiz first (score 70% or more)."
    elif t["kind"] == "APPLY":
        mine = c.db.all("SELECT skill_ids FROM projects WHERE user_id=?", c.user["id"])
        if not any(t["skill_id"] in json.loads(p["skill_ids"]) for p in mine): ready, why = False, "Submit a project that uses this skill first."
    return L, done, att, passed, ready, why

def completion_block(c, t):
    """Dipanggil saat siswa mencoba menandai COMPLETED. Mengembalikan pesan alasan, atau '' bila boleh."""
    if t["kind"] not in ("STUDY", "PRACTICE", "APPLY"): return ""
    return _state(c, t)[5]

def _quiz_wait(c, skill_id):
    """Detik yang harus ditunggu sebelum kuis boleh dicoba lagi. Makin sering gagal dalam 10 menit terakhir, makin lama (kelipatan jeda dasar)."""
    from .. import course as CRS
    uid = c.user["id"]
    last = c.db.one("SELECT CAST(strftime('%s','now') AS INTEGER) - CAST(strftime('%s',created_at) AS INTEGER) ago FROM quiz_attempts WHERE user_id=? AND skill_id=? AND passed=0 ORDER BY id DESC LIMIT 1", uid, skill_id)
    if not last: return 0
    fails = c.db.one("SELECT COUNT(*) n FROM quiz_attempts WHERE user_id=? AND skill_id=? AND passed=0 AND CAST(strftime('%s','now') AS INTEGER) - CAST(strftime('%s',created_at) AS INTEGER) < 600", uid, skill_id)["n"]
    return max(0, CRS.COOLDOWN_SEC * min(max(fails, 1), 5) - last["ago"])

@api("/api/student/learn/{tid:int}", roles=S)
def learn_get(c, tid):
    t = _task(c, tid); L, done, att, passed, ready, why = _state(c, t)
    sk = c.db.one("SELECT name FROM skills WHERE id=?", t["skill_id"]); view = E.task_view(c.db, t)
    quiz = []
    if L["authored"]:
        n = len(att)
        for qi, q in enumerate(L["quiz"]):
            order = _order(c.user["id"], t["skill_id"], qi, n, len(q[2]))
            quiz.append({"q": q[1] if c.lang == "id" else q[0], "options": [_opt(q[2][j], c.lang) for j in order]})
    return {"id": t["id"], "kind": t["kind"], "status": t["status"], "title": view["title"], "skill": c.db.tr("skill", t["skill_id"], "name", sk["name"]) if sk else "",
            "est_hours": t["est_hours"], "difficulty": view["difficulty"], "goal": L["goal"], "steps": [{"text": s, "done": i in done} for i, s in enumerate(L["steps"])],
            "practice": L["practice"], "has_quiz": L["authored"], "quiz": quiz, "pass_percent": int(SL.PASS * 100), "attempts": len(att),
            "best": max((round(100 * a["score"] / a["total"]) for a in att), default=None), "passed": passed,
            "ready": ready, "blocked_reason": why, "wait": _quiz_wait(c, t["skill_id"]) if L["authored"] else 0}

class StepIn(BaseModel):
    idx: int = Field(ge=0, le=20); done: bool

@api("/api/student/learn/{tid:int}/step", "POST", roles=S, model=StepIn)
def learn_step(c, b, tid):
    t = _task(c, tid)
    skill = c.db.one("SELECT name FROM skills WHERE id=?", t["skill_id"]); L = _lesson(c, skill["name"] if skill else "")
    if t["kind"] != "STUDY" or b.idx >= len(L["steps"]): raise bad("Step not found")
    if t["status"] == "COMPLETED": raise bad("This task is already completed")
    if b.done: c.db.run("INSERT OR IGNORE INTO task_steps(task_id,idx) VALUES(?,?)", tid, b.idx)
    else: c.db.run("DELETE FROM task_steps WHERE task_id=? AND idx=?", tid, b.idx)
    if t["status"] == "NOT_STARTED": c.db.run("UPDATE tasks SET status='IN_PROGRESS' WHERE id=?", tid)
    return learn_get(c, tid)

class QuizIn(BaseModel):
    answers: List[int] = Field(min_length=1, max_length=20)

@api("/api/student/learn/{tid:int}/quiz", "POST", roles=S, model=QuizIn)
def learn_quiz(c, b, tid):
    t = _task(c, tid)
    if t["kind"] != "PRACTICE": raise bad("This task has no quiz")
    sk = c.db.one("SELECT name FROM skills WHERE id=?", t["skill_id"]); L = _lesson(c, sk["name"] if sk else "")
    if not L["authored"]: raise bad("This task has no quiz")
    quiz = L["quiz"]
    if len(b.answers) != len(quiz): raise bad("Answer every question")
    wait = _quiz_wait(c, t["skill_id"])
    if wait > 0: raise bad("Please wait a moment before trying again")
    n = len(_attempts(c, t["skill_id"])); score = 0; res = []
    for qi, q in enumerate(quiz):
        order = _order(c.user["id"], t["skill_id"], qi, n, len(q[2])); a = b.answers[qi]
        if not 0 <= a < len(order): raise bad("Answer every question")
        ok = order[a] == q[3]; score += ok
        res.append({"correct": ok, "why": q[5] if c.lang == "id" else q[4]})
    passed = score / len(quiz) >= SL.PASS
    if not passed: res = []          # gagal: tidak ada benar/salah per soal dan tidak ada penjelasan, supaya jawaban tidak bisa ditebak lewat percobaan berulang
    c.db.run("INSERT INTO quiz_attempts(user_id,skill_id,score,total,passed) VALUES(?,?,?,?,?)", c.user["id"], t["skill_id"], score, len(quiz), int(passed))
    if t["status"] == "NOT_STARTED": c.db.run("UPDATE tasks SET status='IN_PROGRESS' WHERE id=?", tid)
    return {"score": score, "total": len(quiz), "percent": round(100 * score / len(quiz)), "passed": passed, "results": res,
            "wait": 0 if passed else _quiz_wait(c, t["skill_id"])}
