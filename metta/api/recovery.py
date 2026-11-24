"""Lupa password tanpa email.

Alur:  pengguna minta reset -> guru (untuk siswa) atau admin (semua) memeriksa orangnya -> menyetujui dan
membacakan KODE sekali pakai (berlaku 24 jam) -> pengguna memasukkan email + kode + password baru sendiri.

Keamanan:
- Halaman "lupa" selalu menjawab sama, ada atau tidak akunnya (tidak membocorkan siapa yang punya akun).
- Kode acak 8 karakter (tanpa huruf yang mirip), hanya hash-nya disimpan, berlaku 24 jam, maksimal 5 kali salah, sekali pakai.
- Semua percobaan dibatasi per alamat dan per email. Setelah reset, semua sesi lama pengguna diputus.
- Guru hanya bisa menangani siswa; admin tidak bisa menyetujui permintaannya sendiri.
"""
import hashlib, hmac, secrets
from pydantic import BaseModel, Field, field_validator
from ..core import api, HTTPError, bad, not_found, audit
from ..security import hash_password, check_password, rate_blocked, rate_hit, rate_clear
from .auth import clean_email, client_ip, too_many

STAFF = ["teacher", "admin"]
CODE_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"        # tanpa I, L, O, 0, 1
MAX_TRIES = 5

def new_code(): return "-".join("".join(secrets.choice(CODE_CHARS) for _ in range(4)) for _ in range(2))
def code_hash(code): return hashlib.sha256(code.replace("-", "").replace(" ", "").upper().encode()).hexdigest()

class ForgotIn(BaseModel):
    email: str = Field(max_length=120)
    @field_validator("email")
    @classmethod
    def _e(cls, v): return clean_email(v)

@api("/api/auth/forgot", "POST", model=ForgotIn, public=True)
def forgot(c, b):
    ip = client_ip(c)
    if rate_blocked(c.db, "forgot_ip", ip, 8, 900) or rate_blocked(c.db, "forgot_email", b.email, 3, 3600): raise too_many()
    rate_hit(c.db, "forgot_ip", ip); rate_hit(c.db, "forgot_email", b.email)
    u = c.db.one("SELECT id,active FROM users WHERE email=?", b.email)
    if u and u["active"] and not c.db.one("SELECT 1 x FROM password_requests WHERE user_id=? AND status='PENDING'", u["id"]):
        c.db.run("INSERT INTO password_requests(user_id) VALUES(?)", u["id"])
        c.db.run("INSERT INTO audit_log(actor_id,action,detail) VALUES(?,'password_request',?)", u["id"], ip)
    return {"ok": True}          # sama persis untuk akun yang ada maupun tidak

def _allowed(c, row):
    """Guru hanya boleh menangani siswa; admin tidak boleh menangani permintaannya sendiri."""
    if row["user_id"] == c.user["id"]: return False
    return c.user["role"] == "admin" or row["role"] == "student"

def _row(c, rid):
    r = c.db.one("""SELECT pr.*, u.name, u.email, u.role FROM password_requests pr JOIN users u ON u.id=pr.user_id WHERE pr.id=?""", rid)
    if not r or not _allowed(c, r): raise not_found("Request not found")
    return r

@api("/api/staff/password-requests", roles=STAFF)
def requests_list(c):
    rows = c.db.all("""SELECT pr.id, pr.status, pr.created_at, pr.handled_at, pr.expires_at, u.id user_id, u.name, u.email, u.role, sp.class_name
                       FROM password_requests pr JOIN users u ON u.id=pr.user_id LEFT JOIN student_profiles sp ON sp.user_id=u.id
                       WHERE pr.created_at > datetime('now','-30 days') ORDER BY CASE pr.status WHEN 'PENDING' THEN 0 WHEN 'APPROVED' THEN 1 ELSE 2 END, pr.id DESC""")
    return {"items": [r for r in rows if _allowed(c, r)]}

@api("/api/staff/password-requests/{rid:int}/approve", "POST", roles=STAFF)
def approve(c, rid):
    r = _row(c, rid)
    if r["status"] not in ("PENDING", "APPROVED"): raise bad("This request is already closed")
    code = new_code()
    c.db.run("UPDATE password_requests SET status='APPROVED', code_hash=?, expires_at=datetime('now','+1 day'), attempts=0, handled_by=?, handled_at=datetime('now') WHERE id=?", code_hash(code), c.user["id"], rid)
    audit(c, "password_request_approved", f"{rid}:{r['email']}")
    return {"code": code, "name": r["name"], "email": r["email"], "hours": 24}

@api("/api/staff/password-requests/{rid:int}/reject", "POST", roles=STAFF)
def reject(c, rid):
    r = _row(c, rid)
    if r["status"] not in ("PENDING", "APPROVED"): raise bad("This request is already closed")
    c.db.run("UPDATE password_requests SET status='REJECTED', code_hash=NULL, handled_by=?, handled_at=datetime('now') WHERE id=?", c.user["id"], rid)
    audit(c, "password_request_rejected", f"{rid}:{r['email']}")

class ResetIn(BaseModel):
    email: str = Field(max_length=120); code: str = Field(min_length=4, max_length=20); new_password: str = Field(min_length=1, max_length=200)
    @field_validator("email")
    @classmethod
    def _e(cls, v): return clean_email(v)

@api("/api/auth/reset", "POST", model=ResetIn, public=True)
def reset(c, b):
    ip = client_ip(c)
    if rate_blocked(c.db, "reset_ip", ip, 15, 900) or rate_blocked(c.db, "reset_email", b.email, 8, 900):
        c.db.commit(); raise too_many()
    u = c.db.one("SELECT * FROM users WHERE email=? AND active=1", b.email)
    r = u and c.db.one("SELECT * FROM password_requests WHERE user_id=? AND status='APPROVED' AND expires_at > datetime('now') AND attempts < ? ORDER BY id DESC LIMIT 1", u["id"], MAX_TRIES)
    ok = bool(r) and hmac.compare_digest(r["code_hash"] or "", code_hash(b.code))
    if not ok:
        rate_hit(c.db, "reset_ip", ip); rate_hit(c.db, "reset_email", b.email)
        if r: c.db.run("UPDATE password_requests SET attempts=attempts+1 WHERE id=?", r["id"])
        c.db.commit(); raise HTTPError(400, "The code is wrong or has expired. Ask your teacher or admin for a new code.")
    err = check_password(b.new_password, u["email"], u["name"], staff=u["role"] != "student")
    if err: raise bad(err)                                  # kode belum terpakai: pengguna boleh coba password lain
    c.db.run("UPDATE users SET password_hash=?, must_change_password=0 WHERE id=?", hash_password(b.new_password), u["id"])
    c.db.run("DELETE FROM sessions WHERE user_id=?", u["id"])
    c.db.run("UPDATE password_requests SET status='DONE', code_hash=NULL WHERE id=?", r["id"])
    rate_clear(c.db, "reset_email", b.email); c.user = u
    audit(c, "password_reset_done", ip)
    return {"ok": True}
