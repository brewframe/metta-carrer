import hmac, os, re
from pydantic import BaseModel, Field, field_validator
from ..core import api, HTTPError, bad, audit, notify
from ..messages import msg, clean_lang
from ..security import (hash_password, verify_password, burn_time, check_password, create_session, delete_session, COOKIE,
                        rate_blocked, rate_hit, rate_clear)
from ..engine import raise_skill

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def clean_email(v):
    v = v.strip().lower()
    if not EMAIL.match(v) or len(v) > 120: raise ValueError("enter a valid email")
    return v

class LoginIn(BaseModel):
    email: str; password: str = Field(min_length=1, max_length=200); role: str = ""
    _e = field_validator("email")(clean_email)

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=80); email: str; password: str = Field(min_length=8, max_length=200)
    school: str = Field("SMK Metta Maitreya", max_length=100); major: str = Field(pattern="^(AK|TKJ)$")
    class_name: str = Field(min_length=1, max_length=20); goal: str = Field("", max_length=300); code: str = Field("", max_length=100)
    _e = field_validator("email")(clean_email)

class PwIn(BaseModel):
    current: str = Field(max_length=200); new: str = Field(min_length=8, max_length=200)

class LangIn(BaseModel):
    lang: str = Field(pattern="^(id|en)$")

class ProfileIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    school: str = Field("", max_length=100); major: str = Field("", pattern="^(AK|TKJ|)$")
    class_name: str = Field("", max_length=20); goal: str = Field("", max_length=300)

def me_payload(c):
    u = c.user
    out = {"id": u["id"], "name": u["name"], "email": u["email"], "role": u["role"], "lang": clean_lang(u["lang"]) if "lang" in u.keys() else "id",
           "must_change_password": bool(u["must_change_password"]) if "must_change_password" in u.keys() else False}
    if u["role"] == "student":
        out["profile"] = c.db.one("SELECT school,major,class_name,goal FROM student_profiles WHERE user_id=?", u["id"]) or {}
    return out

# Login limits (counted per failed attempt): 6 / 5 min per address+account, 10 / 15 min per account (any address), 30 / 15 min per address.
LOGIN_LIMITS = (("login_pair", 6, 300), ("login_email", 10, 900), ("login_ip", 30, 900))

def client_ip(c): return c.request.client.host if c.request.client else "?"

def too_many(): return HTTPError(429, "Too many attempts. Please wait a few minutes and try again.")

@api("/api/auth/config", public=True)
def auth_config(c): return {"register_code_required": bool(os.environ.get("METTA_REGISTER_CODE"))}

@api("/api/public/stats", public=True)
def public_stats(c):
    """Jumlah data untuk halaman depan. Hanya angka, tidak ada data pribadi, supaya halaman
    depan tidak pernah menjanjikan sesuatu yang tidak ada isinya di database."""
    n = lambda t: c.db.one(f"SELECT COUNT(*) x FROM {t}")["x"]       # nama tabel ditulis di sini, bukan dari pengguna
    return {"careers": n("careers"), "companies": n("companies"), "questions": n("questions"), "majors": 2}

@api("/api/auth/login", "POST", model=LoginIn, public=True)
def login(c, b):
    ip = client_ip(c); keys = {"login_pair": f"{ip}|{b.email}", "login_email": b.email, "login_ip": ip}
    if any(rate_blocked(c.db, k, keys[k], lim, win) for k, lim, win in LOGIN_LIMITS):
        c.db.run("INSERT INTO audit_log(actor_id,action,detail) VALUES(NULL,'login_blocked',?)", ip); c.db.commit(); raise too_many()
    u = c.db.one("SELECT * FROM users WHERE email=?", b.email)
    ok = bool(u) and bool(u["active"]) and verify_password(b.password, u["password_hash"])
    if not u: burn_time(b.password)                      # same cost whether or not the account exists
    if not ok or (b.role and b.role != u["role"]):
        for k, _, _ in LOGIN_LIMITS: rate_hit(c.db, k, keys[k])
        c.db.run("INSERT INTO audit_log(actor_id,action,detail) VALUES(?,'login_fail',?)", u["id"] if u else None, ip)
        c.db.commit()                                    # keep the counters even though we now raise an error
        raise HTTPError(401, "Wrong email or password")
    rate_clear(c.db, "login_pair", keys["login_pair"])
    token, ttl = create_session(c.db, u["id"], u["role"]); c.set_cookie = (token, ttl); c.user = u
    audit(c, "login_ok", ip)
    return me_payload(c)

@api("/api/auth/register", "POST", model=RegisterIn, public=True)
def register(c, b):
    ip = client_ip(c); limit = int(os.environ.get("METTA_REGISTER_LIMIT", "10"))
    if rate_blocked(c.db, "register_ip", ip, limit, 3600): raise too_many()
    need = os.environ.get("METTA_REGISTER_CODE", "")
    if need and not hmac.compare_digest(b.code.encode(), need.encode()):
        rate_hit(c.db, "register_ip", ip); c.db.commit(); raise HTTPError(403, "The school registration code is wrong")
    err = check_password(b.password, b.email, b.name)
    if err: raise HTTPError(422, err)
    if c.db.one("SELECT 1 x FROM users WHERE email=?", b.email): raise HTTPError(409, "This email is already registered")
    rate_hit(c.db, "register_ip", ip)
    uid = c.db.run("INSERT INTO users(email,name,password_hash,role,lang) VALUES(?,?,?,'student',?)", b.email, b.name.strip(), hash_password(b.password), c.lang)
    c.db.run("INSERT INTO student_profiles(user_id,school,major,class_name,goal) VALUES(?,?,?,?,?)", uid, b.school.strip(), b.major, b.class_name.strip(), b.goal.strip())
    notify(c.db, uid, msg(c.lang, "note.welcome"))
    c.user = c.db.one("SELECT * FROM users WHERE id=?", uid)
    c.set_cookie = create_session(c.db, uid, "student")
    audit(c, "register", ip)
    return me_payload(c)

@api("/api/auth/logout", "POST")
def logout(c):
    delete_session(c.db, c.request.cookies.get(COOKIE)); c.clear_cookie = True

@api("/api/me")
def me(c): return me_payload(c)

@api("/api/me/lang", "POST", model=LangIn)
def set_lang(c, b):
    """Simpan pilihan bahasa pengguna, supaya terbawa ke perangkat lain."""
    c.db.run("UPDATE users SET lang=? WHERE id=?", b.lang, c.user["id"])
    c.user = c.db.one("SELECT * FROM users WHERE id=?", c.user["id"]); return me_payload(c)

@api("/api/me/profile", "PUT", model=ProfileIn)
def update_profile(c, b):
    c.db.run("UPDATE users SET name=? WHERE id=?", b.name.strip(), c.user["id"])
    if c.user["role"] == "student":
        c.db.run("UPDATE student_profiles SET school=?,major=?,class_name=?,goal=? WHERE user_id=?", b.school.strip(), b.major, b.class_name.strip(), b.goal.strip(), c.user["id"])
    c.user = c.db.one("SELECT * FROM users WHERE id=?", c.user["id"]); return me_payload(c)

@api("/api/me/password", "POST", model=PwIn)
def change_password(c, b):
    uid = str(c.user["id"])
    if rate_blocked(c.db, "pw_change", uid, 5, 900): raise too_many()
    if not verify_password(b.current, c.user["password_hash"]):
        rate_hit(c.db, "pw_change", uid); c.db.commit(); raise HTTPError(400, "Current password is wrong")
    err = check_password(b.new, c.user["email"], c.user["name"], staff=c.user["role"] != "student")
    if err: raise HTTPError(422, err)
    c.db.run("UPDATE users SET password_hash=?, must_change_password=0 WHERE id=?", hash_password(b.new), c.user["id"])
    c.db.run("DELETE FROM sessions WHERE user_id=? AND token_hash<>?", c.user["id"], __import__("hashlib").sha256(c.request.cookies.get(COOKIE, "").encode()).hexdigest())
    rate_clear(c.db, "pw_change", uid)
    audit(c, "password_change")

@api("/api/notifications")
def notifications(c):
    rows = c.db.all("SELECT id,text,read,created_at FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 30", c.user["id"])
    return {"items": rows, "unread": sum(1 for r in rows if not r["read"])}

@api("/api/notifications/read", "POST")
def notifications_read(c):
    c.db.run("UPDATE notifications SET read=1 WHERE user_id=?", c.user["id"])
