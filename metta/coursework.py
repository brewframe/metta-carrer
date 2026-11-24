"""Logika kursus karier (tanpa HTTP): siapa sudah sampai bab berapa, dan kapan kursus dianggap selesai.
Dipakai oleh api/course.py, engine.py (kesiapan karier), portfolio, dan guru."""
import json
from . import course as CRS



def has_course(career_id):
    c = CRS.COURSES.get(career_id)
    return bool(c and len(c.get("sources") or []) >= 2)   # kursus tanpa sumber tidak ditampilkan


def _passed(db, uid, cid, ch):
    return db.one("SELECT 1 x FROM course_attempts WHERE user_id=? AND career_id=? AND chapter=? AND passed=1", uid, cid, ch) is not None


def linked_project(db, uid, cid):
    return db.one("""SELECT p.id,p.title,p.status FROM course_projects cp JOIN projects p ON p.id=cp.project_id
                     WHERE cp.user_id=? AND cp.career_id=?""", uid, cid)


def done_map(db, uid, cid):
    """{1..6: True/False}. Bab 1 = sudah ditandai dibaca; bab 2-5 = lulus kuis dan catatan latihan cukup; bab 6 = lulus ujian akhir dan proyek VERIFIED."""
    r1 = db.one("SELECT done_at FROM course_progress WHERE user_id=? AND career_id=? AND chapter=1", uid, cid)
    out = {1: bool(r1 and r1["done_at"])}
    for n in (2, 3, 4, 5):
        out[n] = bool(_passed(db, uid, cid, n))
    pj = linked_project(db, uid, cid)
    out[6] = _passed(db, uid, cid, 6) and bool(pj and pj["status"] == "VERIFIED")
    return out


def done_count(db, uid, cid):
    return sum(done_map(db, uid, cid).values()) if has_course(cid) else 0


def unlocked(done, n):
    return all(done[k] for k in range(1, n))


def sync(db, uid, cid):
    """Dipanggil setiap kursus mungkin baru selesai. Aman dipanggil berulang: hanya bertindak sekali (saat penanda bab 6 belum ada)."""
    from . import engine as E
    from .core import notify
    from .messages import msg
    from .core import user_lang
    if not has_course(cid): return False
    if not all(done_map(db, uid, cid).values()): return False
    row = db.one("SELECT done_at FROM course_progress WHERE user_id=? AND career_id=? AND chapter=6", uid, cid)
    if row and row["done_at"]: return True
    db.run("""INSERT INTO course_progress(user_id,career_id,chapter,done_at) VALUES(?,?,6,datetime('now'))
              ON CONFLICT(user_id,career_id,chapter) DO UPDATE SET done_at=datetime('now')""", uid, cid)
    for s in E.career_skills(db, cid): E.raise_skill(db, uid, s["id"], E.LEARNING)      # belajar tuntas = tingkat "Belajar"; bukti project menaikkannya
    name = CRS.COURSES[cid]["name"]
    notify(db, uid, msg(user_lang(db, uid), "note.course_done", career=name))
    E.log_readiness(db, uid)
    return True


def completed_courses(db, uid):
    """Kursus yang sudah selesai (untuk portfolio): nama karier, tanggal, nilai ujian akhir terbaik (persen)."""
    out = []
    for r in db.all("""SELECT career_id, done_at FROM course_progress WHERE user_id=? AND chapter=6 AND done_at IS NOT NULL ORDER BY done_at DESC""", uid):
        if r["career_id"] not in CRS.COURSES: continue
        best = db.one("""SELECT MAX(100.0*score/total) p FROM course_attempts WHERE user_id=? AND career_id=? AND chapter=6 AND passed=1""", uid, r["career_id"])
        out.append({"career": db.tr("career", r["career_id"], "name", CRS.COURSES[r["career_id"]]["name"]), "completed_on": (r["done_at"] or "")[:10],
                    "exam_percent": round(best["p"]) if best and best["p"] is not None else None})
    return out
