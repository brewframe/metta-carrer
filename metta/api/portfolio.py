"""Portfolio: prestasi, sertifikat, dan berbagi portfolio lewat tautan.

Aturan privasi:
- Portfolio selalu PRIVATE sampai siswa sendiri mengubahnya.
- Tautan memakai kode acak panjang (tidak bisa ditebak) dan bisa diganti kapan saja untuk mencabut tautan lama.
- Halaman publik hanya memuat yang memang untuk dipamerkan: nama, kelas, jurusan, target, project TERVERIFIKASI,
  skill, prestasi, dan sertifikat. Email, catatan guru, dan data akun tidak ikut.
- Prestasi dan sertifikat yang ditambah siswa tampil sebagai "klaim sendiri" sampai guru memverifikasi.
"""
import re, secrets
from typing import Optional
from pydantic import BaseModel, Field
from ..core import api, HTTPError, bad, not_found, notify, audit, user_lang
from ..messages import msg
from .. import engine as E
from .. import coursework as CW
from ..security import rate_blocked, rate_hit
from .auth import client_ip, too_many
from .student import project_row, valid_link

S = ["student"]; T = ["teacher"]
MAX_ITEMS = 50
DATE = r"^(\d{4}(-\d{2}(-\d{2})?)?)?$"          # kosong, 2026, 2026-05, atau 2026-05-17
SLUG = re.compile(r"^[A-Za-z0-9_-]{10,40}$")


def clean_url(u):
    u = (u or "").strip(); valid_link(u); return u[:300]


class ShareIn(BaseModel):
    visibility: str = Field(pattern="^(PRIVATE|LINK|PUBLIC)$")
    new_link: bool = False
    headline: str = Field("", max_length=120)

class AchievementIn(BaseModel):
    title: str = Field(min_length=2, max_length=120); issuer: str = Field("", max_length=100)
    achieved_on: str = Field("", pattern=DATE)

class CertificateIn(BaseModel):
    title: str = Field(min_length=2, max_length=120); issuer: str = Field("", max_length=100)
    issued_on: str = Field("", pattern=DATE); url: str = Field("", max_length=300)


def items(db, uid):
    ach = db.all("SELECT id,title,issuer,achieved_on,(verified_by IS NOT NULL) verified FROM achievements WHERE user_id=? ORDER BY id DESC", uid)
    cer = db.all("SELECT id,title,issuer,issued_on,url,(verified_by IS NOT NULL) verified FROM certificates WHERE user_id=? ORDER BY id DESC", uid)
    from .files import files_map
    fa = files_map(db, "achievement", [r["id"] for r in ach]); fc = files_map(db, "certificate", [r["id"] for r in cer])
    for r in ach: r["verified"] = bool(r["verified"]); r["files"] = fa[r["id"]]
    for r in cer: r["verified"] = bool(r["verified"]); r["files"] = fc[r["id"]]
    return ach, cer


def share_state(db, uid):
    r = db.one("SELECT visibility,slug,headline FROM portfolios WHERE user_id=?", uid)
    return r or {"visibility": "PRIVATE", "slug": None, "headline": ""}


@api("/api/student/portfolio/extras", roles=S)
def extras(c):
    ach, cer = items(c.db, c.user["id"]); return {"achievements": ach, "certificates": cer, "share": share_state(c.db, c.user["id"])}


@api("/api/student/portfolio/share", "PUT", roles=S, model=ShareIn)
def set_share(c, b):
    uid = c.user["id"]; cur = c.db.one("SELECT slug FROM portfolios WHERE user_id=?", uid)
    slug = cur["slug"] if cur and cur["slug"] else None
    if b.visibility != "PRIVATE" and (not slug or b.new_link): slug = secrets.token_urlsafe(12)
    elif b.new_link: slug = secrets.token_urlsafe(12) if slug else None
    c.db.run("""INSERT INTO portfolios(user_id,visibility,slug,headline,updated_at) VALUES(?,?,?,?,datetime('now'))
                ON CONFLICT(user_id) DO UPDATE SET visibility=excluded.visibility, slug=excluded.slug, headline=excluded.headline, updated_at=datetime('now')""",
             uid, b.visibility, slug, b.headline.strip())
    audit(c, "portfolio_share", b.visibility + (" new_link" if b.new_link else ""))
    return share_state(c.db, uid)


def own(db, table, uid, iid):
    r = db.one(f"SELECT id FROM {table} WHERE id=? AND user_id=?", iid, uid)       # nama tabel ditulis di kode, bukan dari pengguna
    if not r: raise not_found("Item not found")


@api("/api/student/achievements", "POST", roles=S, model=AchievementIn)
def add_achievement(c, b):
    if c.db.one("SELECT COUNT(*) n FROM achievements WHERE user_id=?", c.user["id"])["n"] >= MAX_ITEMS: raise bad("You have reached the limit of 50 items")
    nid = c.db.run("INSERT INTO achievements(user_id,title,issuer,achieved_on) VALUES(?,?,?,?)", c.user["id"], b.title.strip(), b.issuer.strip(), b.achieved_on)
    return dict(extras(c), new_id=nid)

@api("/api/student/achievements/{iid:int}", "DELETE", roles=S)
def del_achievement(c, iid):
    from .files import purge
    own(c.db, "achievements", c.user["id"], iid); purge(c.db, "achievement", iid); c.db.run("DELETE FROM achievements WHERE id=?", iid); return extras(c)

@api("/api/student/certificates", "POST", roles=S, model=CertificateIn)
def add_certificate(c, b):
    if c.db.one("SELECT COUNT(*) n FROM certificates WHERE user_id=?", c.user["id"])["n"] >= MAX_ITEMS: raise bad("You have reached the limit of 50 items")
    nid = c.db.run("INSERT INTO certificates(user_id,title,issuer,issued_on,url) VALUES(?,?,?,?,?)", c.user["id"], b.title.strip(), b.issuer.strip(), b.issued_on, clean_url(b.url))
    return dict(extras(c), new_id=nid)

@api("/api/student/certificates/{iid:int}", "DELETE", roles=S)
def del_certificate(c, iid):
    from .files import purge
    own(c.db, "certificates", c.user["id"], iid); purge(c.db, "certificate", iid); c.db.run("DELETE FROM certificates WHERE id=?", iid); return extras(c)


# ---------- guru memverifikasi ----------
@api("/api/teacher/students/{sid:int}/portfolio-items", roles=T)
def teacher_items(c, sid):
    if not c.db.one("SELECT 1 x FROM users WHERE id=? AND role='student'", sid): raise not_found("Student not found")
    ach, cer = items(c.db, sid); return {"achievements": ach, "certificates": cer}

@api("/api/teacher/portfolio-items/{kind}/{iid:int}/verify", "POST", roles=T)
def verify_item(c, kind, iid):
    table = {"achievements": "achievements", "certificates": "certificates"}.get(kind)
    if not table: raise not_found("Item not found")
    r = c.db.one(f"SELECT id,user_id,title FROM {table} WHERE id=?", iid)
    if not r: raise not_found("Item not found")
    c.db.run(f"UPDATE {table} SET verified_by=? WHERE id=?", c.user["id"], iid)
    audit(c, "portfolio_item_verified", f"{kind}:{iid}")
    notify(c.db, r["user_id"], msg(user_lang(c.db, r["user_id"]), "note.item_verified", title=r["title"]))
    return {"ok": True}


# ---------- halaman publik ----------
@api("/api/public/portfolio/{slug}", public=True)
def public_portfolio(c, slug):
    ip = client_ip(c)
    if rate_blocked(c.db, "portfolio_miss", ip, 30, 600): raise too_many()
    row = SLUG.match(slug) and c.db.one("SELECT user_id,headline FROM portfolios WHERE slug=? AND visibility IN('LINK','PUBLIC')", slug)
    if not row:
        rate_hit(c.db, "portfolio_miss", ip); c.db.commit(); raise not_found("Portfolio not found")
    uid = row["user_id"]
    u = c.db.one("SELECT name FROM users WHERE id=? AND active=1 AND role='student'", uid)
    if not u: raise not_found("Portfolio not found")
    prof = c.db.one("SELECT school,major,class_name FROM student_profiles WHERE user_id=?", uid) or {}
    plan = E.active_plan(c.db, uid)
    projects = [project_row(c, p) for p in c.db.all("SELECT * FROM projects WHERE user_id=? AND status='VERIFIED' ORDER BY id DESC", uid)]
    keep = ("title", "description", "skills", "link", "problem", "solution", "result", "technology", "demo_url", "repo_url", "doc_url")
    projects = [{k: p[k] for k in keep if k in p} for p in projects]
    skills = c.db.all("SELECT s.id, s.name, ss.level FROM student_skills ss JOIN skills s ON s.id=ss.skill_id WHERE ss.user_id=? AND ss.level>=2 ORDER BY ss.level DESC, s.name", uid)
    for s in skills: s["name"] = c.db.tr("skill", s.pop("id"), "name", s["name"]); s["evidence"] = E.lvl(c.db, s["level"])
    ach, cer = items(c.db, uid)
    return {"name": u["name"], "headline": row["headline"], "school": prof.get("school", ""), "major": prof.get("major", ""), "class_name": prof.get("class_name", ""),
            "target": plan["career_name"] if plan else None, "projects": projects, "skills": skills, "courses": CW.completed_courses(c.db, uid),
            "achievements": [{k: a[k] for k in ("title", "issuer", "achieved_on", "verified")} for a in ach],
            "certificates": [{k: a[k] for k in ("title", "issuer", "issued_on", "url", "verified")} for a in cer]}
