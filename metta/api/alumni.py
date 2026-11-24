"""Alumni: menulis cerita karier / edukasi / tips. Admin memoderasi, siswa membaca yang sudah terbit.

Alur:  alumni menulis (DRAFT) -> mengirim (PENDING) -> admin menyetujui (PUBLISHED) atau menolak dengan catatan (REJECTED)
       -> alumni memperbaiki dan mengirim lagi.
Hanya yang PUBLISHED yang terlihat siswa. Isi teks selalu ditampilkan sebagai teks biasa (tidak ada HTML).
"""
from typing import Optional
from pydantic import BaseModel, Field
from ..core import api, bad, not_found, notify, audit, user_lang
from ..messages import msg

AL = ["alumni"]; A = ["admin"]; READ = ["student", "teacher", "admin"]
KINDS = "^(CAREER_STORY|EDUCATION|TIPS)$"
MAX_ITEMS = 30

class ProfileIn(BaseModel):
    graduation_year: Optional[int] = Field(None, ge=1990, le=2100); major: str = Field("", pattern="^(AK|TKJ|)$")
    workplace: str = Field("", max_length=100); job_title: str = Field("", max_length=100); bio: str = Field("", max_length=500)

def profile_row(db, uid):
    return db.one("SELECT graduation_year,major,workplace,job_title,bio FROM alumni_profiles WHERE user_id=?", uid) or {"graduation_year": None, "major": "", "workplace": "", "job_title": "", "bio": ""}

@api("/api/alumni/profile", roles=AL)
def profile_get(c): return profile_row(c.db, c.user["id"])

@api("/api/alumni/profile", "PUT", roles=AL, model=ProfileIn)
def profile_put(c, b):
    c.db.run("""INSERT INTO alumni_profiles(user_id,graduation_year,major,workplace,job_title,bio) VALUES(?,?,?,?,?,?)
                ON CONFLICT(user_id) DO UPDATE SET graduation_year=excluded.graduation_year, major=excluded.major, workplace=excluded.workplace, job_title=excluded.job_title, bio=excluded.bio""",
             c.user["id"], b.graduation_year, b.major, b.workplace.strip(), b.job_title.strip(), b.bio.strip())
    return profile_row(c.db, c.user["id"])

class ContentIn(BaseModel):
    kind: str = Field(pattern=KINDS); title: str = Field(min_length=4, max_length=120); category: str = Field("", max_length=40)
    body: str = Field(min_length=40, max_length=5000); career_id: Optional[int] = None; skill_id: Optional[int] = None; submit: bool = False

def _refs(db, b):
    if b.career_id is not None and not db.one("SELECT 1 x FROM careers WHERE id=?", b.career_id): raise not_found("Career not found")
    if b.skill_id is not None and not db.one("SELECT 1 x FROM skills WHERE id=?", b.skill_id): raise not_found("Skill not found")

def _mine(c, cid):
    r = c.db.one("SELECT * FROM alumni_content WHERE id=? AND author_id=?", cid, c.user["id"])
    if not r: raise not_found("Story not found")
    return r

@api("/api/alumni/content", roles=AL)
def my_content(c):
    return {"items": c.db.all("SELECT id,kind,title,category,body,career_id,skill_id,status,moderation_note,created_at,published_at FROM alumni_content WHERE author_id=? ORDER BY id DESC", c.user["id"]),
            "counts": {r["status"]: r["n"] for r in c.db.all("SELECT status, COUNT(*) n FROM alumni_content WHERE author_id=? GROUP BY status", c.user["id"])}}

@api("/api/alumni/content", "POST", roles=AL, model=ContentIn)
def content_create(c, b):
    if c.db.one("SELECT COUNT(*) n FROM alumni_content WHERE author_id=?", c.user["id"])["n"] >= MAX_ITEMS: raise bad("You have reached the limit of 30 stories")
    _refs(c.db, b)
    cid = c.db.run("INSERT INTO alumni_content(author_id,kind,title,category,body,career_id,skill_id,status) VALUES(?,?,?,?,?,?,?,?)",
                   c.user["id"], b.kind, b.title.strip(), b.category.strip(), b.body.strip(), b.career_id, b.skill_id, "PENDING" if b.submit else "DRAFT")
    audit(c, "alumni_content_create", f"{cid}:{'PENDING' if b.submit else 'DRAFT'}"); return {"id": cid}

@api("/api/alumni/content/{cid:int}", "PUT", roles=AL, model=ContentIn)
def content_update(c, b, cid):
    r = _mine(c, cid)
    if r["status"] not in ("DRAFT", "REJECTED"): raise bad("Only drafts and rejected stories can be edited")
    _refs(c.db, b)
    c.db.run("UPDATE alumni_content SET kind=?,title=?,category=?,body=?,career_id=?,skill_id=?,status=?,moderation_note=CASE WHEN ? THEN '' ELSE moderation_note END WHERE id=?",
             b.kind, b.title.strip(), b.category.strip(), b.body.strip(), b.career_id, b.skill_id, "PENDING" if b.submit else "DRAFT", int(b.submit), cid)
    audit(c, "alumni_content_update", f"{cid}:{'PENDING' if b.submit else 'DRAFT'}"); return {"id": cid}

@api("/api/alumni/content/{cid:int}", "DELETE", roles=AL)
def content_delete(c, cid):
    r = _mine(c, cid)
    if r["status"] == "PUBLISHED": raise bad("A published story can only be removed by the admin")
    c.db.run("DELETE FROM alumni_content WHERE id=?", cid); audit(c, "alumni_content_delete", str(cid))

# ---------- moderasi (admin) ----------
@api("/api/admin/content", roles=A)
def moderation_list(c):
    st = c.request.query_params.get("status") or "PENDING"
    if st not in ("PENDING", "PUBLISHED", "REJECTED", "DRAFT"): raise bad("Unknown status")
    rows = c.db.all("""SELECT ac.id,ac.kind,ac.title,ac.category,ac.body,ac.status,ac.moderation_note,ac.created_at,u.name author, ap.job_title, ap.workplace
                       FROM alumni_content ac JOIN users u ON u.id=ac.author_id LEFT JOIN alumni_profiles ap ON ap.user_id=u.id WHERE ac.status=? ORDER BY ac.id""", st)
    return {"items": rows, "pending": c.db.one("SELECT COUNT(*) n FROM alumni_content WHERE status='PENDING'")["n"]}

class ModerateIn(BaseModel):
    decision: str = Field(pattern="^(PUBLISHED|REJECTED)$"); note: str = Field("", max_length=500)

@api("/api/admin/content/{cid:int}/moderate", "POST", roles=A, model=ModerateIn)
def moderate(c, b, cid):
    r = c.db.one("SELECT * FROM alumni_content WHERE id=?", cid)
    if not r or r["status"] == "DRAFT": raise not_found("Story not found")
    if b.decision == "REJECTED" and len(b.note.strip()) < 5: raise bad("Write a short note so the author knows what to fix")
    c.db.run("UPDATE alumni_content SET status=?, moderated_by=?, moderation_note=?, published_at=CASE WHEN ?='PUBLISHED' THEN datetime('now') ELSE NULL END WHERE id=?",
             b.decision, c.user["id"], b.note.strip(), b.decision, cid)
    lang = user_lang(c.db, r["author_id"])
    notify(c.db, r["author_id"], msg(lang, "note.story_published" if b.decision == "PUBLISHED" else "note.story_rejected", title=r["title"], note=b.note.strip()[:120]))
    audit(c, "alumni_content_moderate", f"{cid}:{b.decision}")

# ---------- dibaca siswa ----------
def _public(c, r): 
    r["excerpt"] = (r["body"][:180].rsplit(" ", 1)[0] + "…") if len(r["body"]) > 180 else r["body"]
    return r

@api("/api/alumni-stories", roles=READ)
def stories(c):
    q = (c.request.query_params.get("q") or "").strip().lower(); kind = c.request.query_params.get("kind") or ""
    if kind and kind not in ("CAREER_STORY", "EDUCATION", "TIPS"): raise bad("Unknown type")
    rows = c.db.all("""SELECT ac.id,ac.kind,ac.title,ac.category,ac.body,ac.published_at,ac.career_id,u.name author,ap.job_title,ap.workplace,ap.graduation_year,ap.major
                       FROM alumni_content ac JOIN users u ON u.id=ac.author_id AND u.active=1 LEFT JOIN alumni_profiles ap ON ap.user_id=u.id
                       WHERE ac.status='PUBLISHED' AND (?='' OR ac.kind=?) ORDER BY ac.published_at DESC, ac.id DESC""", kind, kind)
    rows = [r for r in rows if not q or q in (r["title"] + " " + r["body"] + " " + r["category"] + " " + r["author"]).lower()]
    return {"items": [_public(c, r) for r in rows]}
