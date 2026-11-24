import re, secrets
from typing import List, Optional
from pydantic import BaseModel, Field
from ..core import api, HTTPError, not_found, bad, audit
from ..security import hash_password, check_password
from .auth import clean_email
from ..links import clean_website, clean_instagram, clean_phone
from pydantic import field_validator

A = ["admin"]

# ---------- users ----------
@api("/api/admin/users", roles=A)
def users(c):
    role = c.request.query_params.get("role") or ""
    sql = "SELECT u.id,u.name,u.email,u.role,u.active,u.created_at,sp.major,sp.class_name FROM users u LEFT JOIN student_profiles sp ON sp.user_id=u.id"
    rows = c.db.all(sql + (" WHERE u.role=?" if role else "") + " ORDER BY u.role,u.name", *([role] if role else []))
    return {"items": rows}

class UserIn(BaseModel):
    name: str = Field(min_length=2, max_length=80); email: str; role: str = Field(pattern="^(student|teacher|alumni|admin)$")
    password: str = Field(min_length=8, max_length=200); major: str = Field("", pattern="^(AK|TKJ|)$"); class_name: str = Field("", max_length=20)
    _e = field_validator("email")(clean_email)

@api("/api/admin/users", "POST", roles=A, model=UserIn)
def user_create(c, b):
    if c.db.one("SELECT 1 x FROM users WHERE email=?", b.email): raise HTTPError(409, "This email is already registered")
    err = check_password(b.password, b.email, b.name, staff=b.role != "student")
    if err: raise HTTPError(422, err)
    uid = c.db.run("INSERT INTO users(email,name,password_hash,role) VALUES(?,?,?,?)", b.email, b.name.strip(), hash_password(b.password), b.role)
    if b.role == "student": c.db.run("INSERT INTO student_profiles(user_id,school,major,class_name) VALUES(?,?,?,?)", uid, "SMK Metta Maitreya", b.major, b.class_name)
    if b.role == "alumni": c.db.run("INSERT OR IGNORE INTO alumni_profiles(user_id) VALUES(?)", uid)
    audit(c, "user_create", f"{uid}:{b.role}"); return {"id": uid}

class UserPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=80); active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, max_length=200)

@api("/api/admin/users/{uid:int}", "PATCH", roles=A, model=UserPatch)
def user_patch(c, b, uid):
    u = c.db.one("SELECT * FROM users WHERE id=?", uid)
    if not u: raise not_found("User not found")
    if b.active is False and uid == c.user["id"]: raise bad("You cannot deactivate your own account")
    if b.password:
        err = check_password(b.password, u["email"], b.name or u["name"], staff=u["role"] != "student")
        if err: raise HTTPError(422, err)
    if b.name: c.db.run("UPDATE users SET name=? WHERE id=?", b.name.strip(), uid)
    if b.active is not None:
        c.db.run("UPDATE users SET active=? WHERE id=?", int(b.active), uid)
        if not b.active: c.db.run("DELETE FROM sessions WHERE user_id=?", uid)
    if b.password: c.db.run("UPDATE users SET password_hash=? WHERE id=?", hash_password(b.password), uid); c.db.run("DELETE FROM sessions WHERE user_id=?", uid)
    audit(c, "user_update", str(uid))

RESET_ALPHABET = "abcdefghjkmnpqrstuvwxyz"      # tanpa i, l, o: mudah dibaca dan diketik ulang
RESET_DIGITS = "23456789"                        # tanpa 0 dan 1

def temp_password():
    """Password sementara yang mudah dibacakan guru ke siswa tapi tetap sulit ditebak.
    Bentuknya tiga suku kata + dua angka, contoh: tiru-paksa-doki-47 (sekitar 60 bit)."""
    kata = lambda: "".join(secrets.choice(RESET_ALPHABET if i % 2 == 0 else "aiueo") for i in range(4))
    return "-".join(kata() for _ in range(3)) + "-" + "".join(secrets.choice(RESET_DIGITS) for _ in range(2))

@api("/api/admin/users/{uid:int}/reset-password", "POST", roles=A)
def user_reset_password(c, uid):
    """Admin membuatkan password sementara untuk pengguna yang lupa password.

    Password hanya ditampilkan sekali di layar admin (tidak disimpan sebagai teks biasa), semua
    sesi pengguna itu diputus, dan pengguna wajib menggantinya saat masuk berikutnya.
    """
    u = c.db.one("SELECT * FROM users WHERE id=?", uid)
    if not u: raise not_found("User not found")
    if uid == c.user["id"]: raise bad("Use Settings to change your own password")
    staff = u["role"] != "student"
    for _ in range(8):      # ulangi kalau kebetulan hasil acaknya memuat nama atau email pengguna
        pw = temp_password()
        if not check_password(pw, u["email"], u["name"], staff=staff): break
    else:
        raise HTTPError(500, "Could not make a temporary password, please try again")
    c.db.run("UPDATE users SET password_hash=?, must_change_password=1 WHERE id=?", hash_password(pw), uid)
    c.db.run("DELETE FROM sessions WHERE user_id=?", uid)       # semua perangkat ikut keluar
    audit(c, "password_reset", f"{uid}:{u['email']}")
    return {"email": u["email"], "name": u["name"], "temp_password": pw}

# ---------- skills ----------
class SkillIn(BaseModel):
    name: str = Field(min_length=2, max_length=60); category: str = Field("technical", pattern="^(technical|soft)$")

@api("/api/admin/skills", roles=A)
def skills(c): return {"items": c.db.all("SELECT id,name,category FROM skills ORDER BY category,name")}

@api("/api/admin/skills", "POST", roles=A, model=SkillIn)
def skill_create(c, b):
    if c.db.one("SELECT 1 x FROM skills WHERE lower(name)=lower(?)", b.name.strip()): raise HTTPError(409, "This skill already exists")
    sid = c.db.run("INSERT INTO skills(name,category) VALUES(?,?)", b.name.strip(), b.category); audit(c, "skill_create", b.name); return {"id": sid}

@api("/api/admin/skills/{sid:int}", "PUT", roles=A, model=SkillIn)
def skill_update(c, b, sid):
    if not c.db.one("SELECT 1 x FROM skills WHERE id=?", sid): raise not_found("Skill not found")
    c.db.run("UPDATE skills SET name=?,category=? WHERE id=?", b.name.strip(), b.category, sid); audit(c, "skill_update", str(sid))

@api("/api/admin/skills/{sid:int}", "DELETE", roles=A)
def skill_delete(c, sid):
    if c.db.one("SELECT 1 x FROM career_skills WHERE skill_id=?", sid): raise bad("This skill is used by a career. Remove it from the career first.")
    c.db.run("DELETE FROM skills WHERE id=?", sid); audit(c, "skill_delete", str(sid))

# ---------- careers ----------
class CareerSkillIn(BaseModel):
    skill_id: int; importance: int = Field(2, ge=1, le=3)

class CareerIn(BaseModel):
    name: str = Field(min_length=2, max_length=80); category: str = Field("", max_length=40)
    description: str = Field("", max_length=1000); responsibilities: str = Field("", max_length=1000)
    education_path: str = Field("", max_length=600); example_projects: str = Field("", max_length=600); growth: str = Field("", max_length=600)
    interest_tags: str = Field("", max_length=100); strength_tags: str = Field("", max_length=100); majors: str = Field("", max_length=20)
    skills: List[CareerSkillIn] = []

def save_career_skills(c, cid, skills):
    c.db.run("DELETE FROM career_skills WHERE career_id=?", cid)
    for s in skills:
        if not c.db.one("SELECT 1 x FROM skills WHERE id=?", s.skill_id): raise bad("Unknown skill")
        c.db.run("INSERT OR REPLACE INTO career_skills(career_id,skill_id,importance) VALUES(?,?,?)", cid, s.skill_id, s.importance)

@api("/api/admin/careers", roles=A)
def careers(c):
    rows = c.db.all("SELECT * FROM careers ORDER BY name")
    for r in rows: r["skills"] = c.db.all("SELECT skill_id, importance FROM career_skills WHERE career_id=?", r["id"])
    return {"items": rows}

@api("/api/admin/careers", "POST", roles=A, model=CareerIn)
def career_create(c, b):
    if c.db.one("SELECT 1 x FROM careers WHERE lower(name)=lower(?)", b.name.strip()): raise HTTPError(409, "This career already exists")
    cid = c.db.run("INSERT INTO careers(name,category,description,responsibilities,education_path,example_projects,growth,interest_tags,strength_tags,majors) VALUES(?,?,?,?,?,?,?,?,?,?)",
        b.name.strip(), b.category, b.description, b.responsibilities, b.education_path, b.example_projects, b.growth, b.interest_tags, b.strength_tags, b.majors)
    save_career_skills(c, cid, b.skills); audit(c, "career_create", b.name); return {"id": cid}

@api("/api/admin/careers/{cid:int}", "PUT", roles=A, model=CareerIn)
def career_update(c, b, cid):
    if not c.db.one("SELECT 1 x FROM careers WHERE id=?", cid): raise not_found("Career not found")
    c.db.run("UPDATE careers SET name=?,category=?,description=?,responsibilities=?,education_path=?,example_projects=?,growth=?,interest_tags=?,strength_tags=?,majors=? WHERE id=?",
        b.name.strip(), b.category, b.description, b.responsibilities, b.education_path, b.example_projects, b.growth, b.interest_tags, b.strength_tags, b.majors, cid)
    save_career_skills(c, cid, b.skills); audit(c, "career_update", str(cid))

@api("/api/admin/careers/{cid:int}", "DELETE", roles=A)
def career_delete(c, cid):
    if c.db.one("SELECT 1 x FROM plans WHERE career_id=?", cid): raise bad("Students have plans for this career, so it cannot be deleted.")
    c.db.run("DELETE FROM careers WHERE id=?", cid); audit(c, "career_delete", str(cid))

# ---------- companies ----------
class CompanyIn(BaseModel):
    name: str = Field(min_length=2, max_length=120); address: str = Field("", max_length=300); number: Optional[int] = Field(None, ge=1, le=9999)
    sector: str = Field("", max_length=80); sector_id: str = Field("", max_length=80); about: str = Field("", max_length=800); about_id: str = Field("", max_length=800)
    source: str = Field("", max_length=200); verified: bool = False
    website: str = Field("", max_length=200); instagram: str = Field("", max_length=200); phone: str = Field("", max_length=30)

@api("/api/admin/companies", "POST", roles=A, model=CompanyIn)
def company_create(c, b):
    num = b.number or ((c.db.one("SELECT MAX(number) m FROM companies")["m"] or 0) + 1)
    cid = c.db.run("INSERT INTO companies(number,name,address,sector,sector_id,about,about_id,source,verified,website,instagram,phone) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", num, b.name.strip(), b.address.strip(), b.sector.strip(), b.sector_id.strip(), b.about.strip(), b.about_id.strip(), b.source.strip(), int(b.verified), clean_website(b.website), clean_instagram(b.instagram), clean_phone(b.phone)); audit(c, "company_create", b.name); return {"id": cid}

@api("/api/admin/companies/{cid:int}", "PUT", roles=A, model=CompanyIn)
def company_update(c, b, cid):
    if not c.db.one("SELECT 1 x FROM companies WHERE id=?", cid): raise not_found("Company not found")
    c.db.run("UPDATE companies SET name=?,address=?,number=COALESCE(?,number),sector=?,sector_id=?,about=?,about_id=?,source=?,verified=?,website=?,instagram=?,phone=?,sector_guess=0 WHERE id=?", b.name.strip(), b.address.strip(), b.number, b.sector.strip(), b.sector_id.strip(), b.about.strip(), b.about_id.strip(), b.source.strip(), int(b.verified), clean_website(b.website), clean_instagram(b.instagram), clean_phone(b.phone), cid); audit(c, "company_update", str(cid))

class CompanyFill(BaseModel):
    address: str = Field("", max_length=300); sector: str = Field("", max_length=80); sector_id: str = Field("", max_length=80)
    about: str = Field("", max_length=800); about_id: str = Field("", max_length=800); source: str = Field(min_length=3, max_length=200)
    website: str = Field("", max_length=200); instagram: str = Field("", max_length=200); phone: str = Field("", max_length=30)

@api("/api/teacher/companies/{cid:int}", "PUT", roles=["teacher"], model=CompanyFill)
def company_fill(c, b, cid):
    """Guru melengkapi data DU/DI yang belum terverifikasi (wajib menyebut sumbernya). Tanda 'terverifikasi' tetap hanya dari admin."""
    row = c.db.one("SELECT verified FROM companies WHERE id=?", cid)
    if not row: raise not_found("Company not found")
    if row["verified"]: raise HTTPError(403, "This company is already verified. Ask the admin to change it")
    w, i, p = clean_website(b.website), clean_instagram(b.instagram), clean_phone(b.phone)
    if not (b.address.strip() or b.about.strip() or b.sector.strip()): raise bad("Fill at least the address, the sector or a short description")
    c.db.run("UPDATE companies SET address=?,sector=?,sector_id=?,about=?,about_id=?,source=?,website=CASE WHEN ?<>'' THEN ? ELSE website END,instagram=CASE WHEN ?<>'' THEN ? ELSE instagram END,phone=CASE WHEN ?<>'' THEN ? ELSE phone END,sector_guess=0 WHERE id=?", b.address.strip(), b.sector.strip(), b.sector_id.strip(), b.about.strip(), b.about_id.strip(), b.source.strip(), w, w, i, i, p, p, cid)
    audit(c, "company_fill", str(cid)); return {"ok": True}

@api("/api/admin/companies/{cid:int}", "DELETE", roles=A)
def company_delete(c, cid):
    c.db.run("DELETE FROM companies WHERE id=?", cid); audit(c, "company_delete", str(cid))

class ImportIn(BaseModel):
    text: str = Field(min_length=3, max_length=200000)

@api("/api/admin/companies/import", "POST", roles=A, model=ImportIn)
def company_import(c, b):
    """One company per line:  number;name;address   (address optional). Existing names are skipped."""
    added = skipped = 0
    for line in b.text.splitlines():
        line = line.strip()
        if not line: continue
        parts = [p.strip() for p in re.split(r"[;\t]", line)]
        num = None
        if parts and re.fullmatch(r"\d{1,4}", parts[0]): num = int(parts.pop(0))
        if not parts or len(parts[0]) < 2: skipped += 1; continue
        name = parts[0][:120]; addr = (parts[1] if len(parts) > 1 else "")[:300]
        if c.db.one("SELECT 1 x FROM companies WHERE lower(name)=lower(?)", name): skipped += 1; continue
        c.db.run("INSERT INTO companies(number,name,address) VALUES(?,?,?)", num or ((c.db.one("SELECT MAX(number) m FROM companies")["m"] or 0) + 1), name, addr); added += 1
    audit(c, "company_import", f"+{added}/-{skipped}"); return {"added": added, "skipped": skipped}

# ---------- analytics & audit ----------
@api("/api/admin/summary", roles=A)
def summary(c):
    d = c.db; n = lambda sql: d.one(sql)["n"]
    return {"users": n("SELECT COUNT(*) n FROM users"), "students": n("SELECT COUNT(*) n FROM users WHERE role='student'"),
            "companies": n("SELECT COUNT(*) n FROM companies"), "careers": n("SELECT COUNT(*) n FROM careers"),
            "students_with_choices": n("SELECT COUNT(DISTINCT user_id) n FROM internship_choices"),
            "assessments": n("SELECT COUNT(DISTINCT user_id) n FROM assessments"), "plans": n("SELECT COUNT(*) n FROM plans WHERE status='ACTIVE'"),
            "projects_pending": n("SELECT COUNT(*) n FROM projects WHERE status='SUBMITTED'"), "projects_verified": n("SELECT COUNT(*) n FROM projects WHERE status='VERIFIED'")}

@api("/api/admin/analytics", roles=A)
def analytics(c):
    d = c.db
    pop = d.all("SELECT ca.id, ca.name label, COUNT(*) value FROM plans p JOIN careers ca ON ca.id=p.career_id WHERE p.status='ACTIVE' GROUP BY ca.id ORDER BY value DESC, ca.name LIMIT 8")
    pop = [{"label": d.tr("career", x["id"], "name", x["label"]), "value": x["value"]} for x in pop]
    top_co = d.all("SELECT co.name label, COUNT(*) value FROM internship_choices ic JOIN companies co ON co.id=ic.company_id WHERE ic.rank=1 GROUP BY co.id ORDER BY value DESC LIMIT 8")
    roles = {x["role"]: x["n"] for x in d.all("SELECT role, COUNT(*) n FROM users WHERE active=1 GROUP BY role")}
    majors = d.all("SELECT COALESCE(NULLIF(sp.major,''),'-') label, COUNT(*) value FROM users u LEFT JOIN student_profiles sp ON sp.user_id=u.id WHERE u.role='student' AND u.active=1 GROUP BY label ORDER BY label")
    pst = {x["status"]: x["n"] for x in d.all("SELECT status, COUNT(*) n FROM projects GROUP BY status")}
    return {"summary": summary(c), "popular_careers": pop, "first_choice_companies": top_co,
            "users_by_role": [{"key": k, "value": roles.get(k, 0)} for k in ("student", "teacher", "alumni", "admin")],
            "students_by_major": majors,
            "projects": [{"key": k, "value": pst.get(k, 0)} for k in ("SUBMITTED", "NEEDS_REVISION", "VERIFIED")]}

@api("/api/admin/audit", roles=A)
def audit_view(c):
    return {"items": c.db.all("SELECT a.id,a.action,a.detail,a.created_at,u.name actor FROM audit_log a LEFT JOIN users u ON u.id=a.actor_id ORDER BY a.id DESC LIMIT 100")}
