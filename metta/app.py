import glob, hashlib, os, re
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .core import ROUTES
from .security import production, secure_cookie, verify_password
from .db import DB
from .seed import seed, DEMO
from .api import auth, student, teacher, admin, portfolio, learn, files, recovery, alumni, course, company_proposal  # noqa: F401  (registers routes)

STATIC = os.path.join(os.path.dirname(__file__), "static")

CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; "
       "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")

class Headers(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        h = resp.headers
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "DENY"
        h["Referrer-Policy"] = "same-origin"
        if "content-security-policy" not in h: h["Content-Security-Policy"] = CSP
        h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"
        h["Cross-Origin-Opener-Policy"] = "same-origin"
        h["Cross-Origin-Resource-Policy"] = "same-origin"
        if secure_cookie(): h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if request.url.path.startswith("/api/"): h["Cache-Control"] = "no-store"
        # Halaman dan file statis: browser WAJIB menanyakan ulang ke server (ETag, jawaban 304 kecil) sebelum memakai cache.
        # Tanpa ini browser bisa memakai app.js lama bersama student.js baru setelah update (contoh: "M.countdown is not a function").
        elif "cache-control" not in h: h["Cache-Control"] = "no-cache"
        # Browser yang masih memegang file tampilan versi lama (cookie versi tidak cocok) diminta mengosongkan cache-nya.
        # Hanya "cache": sesi login dan data lain TIDAK ikut terhapus. Kunjungan berikutnya otomatis memakai file terbaru.
        if request.url.path.startswith("/api/") and request.cookies.get(VCOOKIE) != asset_v():
            h["Clear-Site-Data"] = '"cache"'
            h.append("Set-Cookie", f"{VCOOKIE}={asset_v()}; Path=/; HttpOnly; SameSite=Lax" + ("; Secure" if secure_cookie() else ""))
        return resp

def startup_checks():
    """Refuse to start in production with unsafe settings; warn loudly in development."""
    if production():
        if not secure_cookie(): raise RuntimeError("METTA_ENV=production needs METTA_SECURE_COOKIE=1 (the site must be served over HTTPS)")
        if os.environ.get("METTA_SEED_DEMO") == "1": raise RuntimeError("METTA_SEED_DEMO=1 creates demo accounts with known passwords; never use it in production")
    d = DB()
    try:
        weak = [e for e, _, _, pw in DEMO if (u := d.one("SELECT password_hash FROM users WHERE email=?", e)) and verify_password(pw, u["password_hash"])]
    finally: d.close()
    if weak:
        msg = "Demo accounts with KNOWN passwords exist: " + ", ".join(weak) + ". Delete them or change their passwords before going online."
        if production(): raise RuntimeError(msg)
        print("WARNING: " + msg)
    if production() and not os.environ.get("METTA_REGISTER_CODE"): print("WARNING: METTA_REGISTER_CODE is not set, so anyone on the internet can create a student account.")
    if production() and not os.environ.get("METTA_ALLOWED_HOSTS"): print("WARNING: METTA_ALLOWED_HOSTS is not set (example: metta.example.sch.id).")

def _asset_version():
    """Sidik jari isi semua JS/CSS. Berubah setiap kali ada file yang berubah, jadi URL ?v=... ikut berubah dan cache lama tidak terpakai."""
    sha = hashlib.sha256()
    for f in sorted(glob.glob(os.path.join(STATIC, "*.js")) + glob.glob(os.path.join(STATIC, "*.css"))):
        with open(f, "rb") as fh: sha.update(os.path.basename(f).encode()); sha.update(fh.read())
    return sha.hexdigest()[:12]

def _index_html():
    with open(os.path.join(STATIC, "index.html"), encoding="utf-8") as f: html = f.read()
    v = _asset_version()
    return re.sub(r'((?:src|href)="/static/[^"?]+\.(?:js|css))"', lambda m: m.group(1) + "?v=" + v + '"', html)

INDEX_HTML = None
ASSET_V = None
def asset_v():
    global ASSET_V
    if ASSET_V is None: ASSET_V = _asset_version()
    return ASSET_V

VCOOKIE = "metta_v"   # versi file tampilan yang terakhir dimuat browser ini (bukan data pribadi)
async def index(request):
    global INDEX_HTML
    if INDEX_HTML is None: INDEX_HTML = _index_html()
    resp = HTMLResponse(INDEX_HTML)
    resp.set_cookie(VCOOKIE, asset_v(), path="/", samesite="lax", httponly=True, secure=secure_cookie())
    return resp
async def health(request): return JSONResponse({"ok": True})

def create_app():
    seed(); startup_checks()
    routes = ROUTES + [Route("/api/health", health), Mount("/static", StaticFiles(directory=STATIC), name="static"), Route("/{path:path}", index)]
    app = Starlette(routes=routes)
    app.add_middleware(Headers)
    hosts = [h.strip() for h in os.environ.get("METTA_ALLOWED_HOSTS", "").split(",") if h.strip()]
    if hosts: app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)
    return app

app = create_app()
