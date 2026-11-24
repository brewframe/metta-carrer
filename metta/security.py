"""Security helpers: password hashing and policy, sessions, rate limits. No web code here, so it is easy to test."""
import hashlib, hmac, os, re, secrets, time
from datetime import datetime, timedelta, timezone

COOKIE = "metta_session"
STUDENT_SESSION_HOURS = 24 * 7          # students stay signed in for a week
STAFF_SESSION_HOURS = 12                # teachers, admins and alumni: shorter, their accounts can see more
MAX_SESSIONS_PER_USER = 5

def env_flag(name): return os.environ.get(name, "") == "1"
def secure_cookie(): return env_flag("METTA_SECURE_COOKIE")
def production(): return os.environ.get("METTA_ENV", "").lower() == "production"

# ---------------- passwords ----------------
def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${h.hex()}"

def verify_password(pw: str, stored: str) -> bool:
    try:
        _, salt, h = stored.split("$")
        calc = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(calc.hex(), h)
    except Exception:
        return False

# Used when the e-mail does not exist, so "unknown account" costs the same time as "wrong password".
_DUMMY_HASH = hash_password("not-a-real-password")
def burn_time(pw: str): verify_password(pw, _DUMMY_HASH)

COMMON = frozenset("""123456 1234567 12345678 123456789 1234567890 password password1 password123 passw0rd p@ssw0rd p@ssword qwerty qwertyui qwerty123
qwertyuiop abc123 abcd1234 abcdefgh 1q2w3e4r 1qaz2wsx zaq12wsx qazwsx asdfghjkl zxcvbnm 111111 11111111 000000 00000000 0000000000 987654321
12341234 12121212 123123123 88888888 77777777 iloveyou admin admin123 admin1234 welcome letmein monkey dragon sunshine princess football
baseball master login metta mettacareer metta123 metta2026 mettamaitreya sekolah smk smk123 rahasia indonesia bismillah sayang cintaku
kamu123 student student123 teacher teacher123 siswa123 guru123 rahasia123""".split())

def check_password(pw: str, email: str = "", name: str = "", staff: bool = False):
    """Return an error message, or None if the password is acceptable."""
    need = 12 if staff else 8
    if len(pw) < need: return f"Password must be at least {need} characters" + (" for teachers and admins" if staff else "")
    if len(pw) > 200: return "Password is too long"
    low = pw.lower(); base = re.sub(r"[\d\W_]+$", "", low)
    if low in COMMON or base in COMMON: return "This password is too common. Pick something harder to guess."
    if len(set(low)) < 4: return "Use more different characters"
    if low.isdigit(): return "Do not use only numbers"
    classes = sum(bool(re.search(p, pw)) for p in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]"))
    if len(pw) < 14 and classes < 2: return "Mix at least two kinds of characters (letters, numbers, symbols) or make it 14+ characters long"
    local = (email or "").split("@")[0].lower()
    if len(local) >= 4 and local in low: return "Password must not contain your e-mail name"
    for part in re.split(r"\s+", (name or "").lower()):
        if len(part) >= 4 and part in low: return "Password must not contain your name"
    return None

# ---------------- sessions ----------------
def _hash_token(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()

def now_iso(): return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def create_session(db, user_id: int, role: str):
    """Returns (token, lifetime_seconds). Cleans expired sessions and keeps at most 5 per user."""
    hours = STUDENT_SESSION_HOURS if role == "student" else STAFF_SESSION_HOURS
    token = secrets.token_urlsafe(32)
    exp = (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    db.run("DELETE FROM sessions WHERE expires_at<=?", now_iso())
    db.run("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)", _hash_token(token), user_id, exp)
    db.run("""DELETE FROM sessions WHERE user_id=? AND rowid NOT IN
              (SELECT rowid FROM sessions WHERE user_id=? ORDER BY rowid DESC LIMIT ?)""", user_id, user_id, MAX_SESSIONS_PER_USER)
    return token, hours * 3600

def user_from_token(db, token):
    if not token or len(token) > 100: return None
    return db.one("""SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
                     WHERE s.token_hash=? AND s.expires_at>? AND u.active=1""", _hash_token(token), now_iso())

def delete_session(db, token):
    if token: db.run("DELETE FROM sessions WHERE token_hash=?", _hash_token(token))

# ---------------- rate limits (stored in the database, so they survive restarts and work with several workers) ----------------
def rate_count(db, bucket, key, window):
    return db.one("SELECT COUNT(*) n FROM rate_events WHERE bucket=? AND key=? AND ts>?", bucket, key, time.time() - window)["n"]

def rate_blocked(db, bucket, key, limit, window): return rate_count(db, bucket, key, window) >= limit

def rate_hit(db, bucket, key):
    db.run("INSERT INTO rate_events(bucket,key,ts) VALUES(?,?,?)", bucket, key, time.time())
    if secrets.randbelow(50) == 0: db.run("DELETE FROM rate_events WHERE ts<?", time.time() - 86400)   # keep the table small

def rate_clear(db, bucket, key): db.run("DELETE FROM rate_events WHERE bucket=? AND key=?", bucket, key)
