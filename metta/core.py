"""Tiny API framework on top of Starlette: auth, roles, validation, JSON errors, DB transaction per request."""
import json, os
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import Any, Callable, Optional
import anyio
from pydantic import BaseModel, ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from .db import DB
from .security import COOKIE, user_from_token, secure_cookie
from .messages import clean_lang, DEFAULT as DEFAULT_LANG

class HTTPError(Exception):
    def __init__(self, status: int, message: str): self.status = status; self.message = message

@dataclass
class Ctx:
    db: DB
    user: Optional[dict]
    request: Request
    set_cookie: Optional[tuple] = None
    clear_cookie: bool = False
    lang: str = "id"

def bad(msg="Bad request"): return HTTPError(400, msg)
def not_found(msg="Not found"): return HTTPError(404, msg)
def forbidden(msg="Not allowed"): return HTTPError(403, msg)

def request_lang(request, user):
    """Bahasa untuk permintaan ini: pilihan yang dikirim browser (header X-Lang), kalau tidak ada pakai
    bahasa tersimpan milik pengguna, kalau tidak ada pakai bahasa bawaan. Hanya 'id' atau 'en' yang lolos."""
    sent = request.headers.get("x-lang")
    if sent: return clean_lang(sent)
    if user is not None and "lang" in user.keys(): return clean_lang(user["lang"])
    return DEFAULT_LANG

def user_lang(db: DB, user_id: int) -> str:
    """Bahasa tersimpan milik seorang pengguna (dipakai untuk menulis notifikasi untuknya)."""
    r = db.one("SELECT lang FROM users WHERE id=?", user_id)
    return clean_lang(r["lang"]) if r else DEFAULT_LANG

def audit(c: Ctx, action: str, detail: str = ""):
    c.db.run("INSERT INTO audit_log(actor_id,action,detail) VALUES(?,?,?)", c.user["id"] if c.user else None, action, detail)

def notify(db: DB, user_id: int, text: str):
    db.run("INSERT INTO notifications(user_id,text) VALUES(?,?)", user_id, text)

ROUTES: list = []
ROUTE_META: list = []          # (path, method, roles, public, has_body) — used by the authorization test matrix

MAX_BODY = int(os.environ.get("METTA_MAX_BODY", "65536"))     # bytes; every legitimate request here is far smaller
SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

def _extra_origins():
    return {o.strip().lower().rstrip("/") for o in os.environ.get("METTA_ALLOWED_ORIGINS", "").split(",") if o.strip()}

def cross_site(request: Request) -> bool:
    """True when a browser says this state-changing request comes from another site (CSRF defence in depth on top of SameSite)."""
    origin = request.headers.get("origin")
    if origin:
        o = origin.lower().rstrip("/")
        return not (urlparse(o).netloc == request.headers.get("host", "").lower() or o in _extra_origins())
    fetch_site = request.headers.get("sec-fetch-site")
    return bool(fetch_site) and fetch_site not in ("same-origin", "none")

async def read_json(request: Request, limit: int = 0):
    """Read a small JSON body. Raises HTTPError for wrong type, too large or malformed bodies."""
    if not request.headers.get("content-type", "").lower().startswith("application/json"):
        raise HTTPError(415, "Send the body as application/json")
    try: declared = int(request.headers.get("content-length", "0") or 0)
    except ValueError: raise HTTPError(400, "Bad Content-Length")
    limit = limit or MAX_BODY
    if declared > limit: raise HTTPError(413, "Request is too large")
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit: raise HTTPError(413, "Request is too large")
        chunks.append(chunk)
    try: return json.loads(b"".join(chunks) or b"null")
    except Exception: raise HTTPError(400, "Request body must be valid JSON")

def api(path: str, method: str = "GET", roles: Optional[list] = None, model: Optional[type] = None, public=False, max_body: int = 0):
    def deco(fn: Callable):
        async def endpoint(request: Request):
            try:
                # 1) async part: cheap request checks and reading the body (no database here, so the event loop never blocks)
                if request.method not in SAFE_METHODS and cross_site(request): raise HTTPError(403, "Cross-site request blocked")
                raw = None
                if model is not None: raw = await read_json(request, max_body)
                elif int(request.headers.get("content-length", "0") or 0) > MAX_BODY: raise HTTPError(413, "Request is too large")
            except HTTPError as e:
                return JSONResponse({"error": e.message}, status_code=e.status)
            except ValueError:
                return JSONResponse({"error": "Bad Content-Length"}, status_code=400)
            token = request.cookies.get(COOKIE); kwargs = dict(request.path_params)

            # 2) sync part: all database work runs in a worker thread, in one transaction
            def work():
                db = DB()
                try:
                    user = user_from_token(db, token)
                    if not public:
                        if not user: raise HTTPError(401, "Please sign in")
                        if roles and user["role"] not in roles: raise HTTPError(403, "You do not have access to this")
                        db.run("UPDATE users SET last_active_at=datetime('now') WHERE id=? AND (last_active_at IS NULL OR last_active_at < datetime('now','-60 seconds'))", user["id"])
                    body = None
                    if model is not None:
                        try: body = model.model_validate(raw)
                        except ValidationError as e:
                            err = e.errors()[0]; loc = ".".join(str(x) for x in err["loc"])
                            raise HTTPError(422, f"{loc}: {err['msg']}")
                    ctx = Ctx(db, user, request, lang=request_lang(request, user)); db.lang = ctx.lang
                    result = fn(ctx, body, **kwargs) if model is not None else fn(ctx, **kwargs)
                    db.commit()
                    return ctx, result
                except Exception:
                    db.rollback(); raise
                finally:
                    db.close()
            try:
                ctx, result = await anyio.to_thread.run_sync(work)
                resp = result if isinstance(result, Response) else JSONResponse(result if result is not None else {"ok": True})
                if ctx.set_cookie:
                    resp.set_cookie(COOKIE, ctx.set_cookie[0], max_age=ctx.set_cookie[1], httponly=True, samesite="lax",
                                    secure=secure_cookie(), path="/")
                if ctx.clear_cookie: resp.delete_cookie(COOKIE, path="/", secure=secure_cookie(), httponly=True, samesite="lax")
                return resp
            except HTTPError as e:
                return JSONResponse({"error": e.message}, status_code=e.status)
            except Exception:
                import traceback; traceback.print_exc()
                return JSONResponse({"error": "Something went wrong on the server"}, status_code=500)
        ROUTES.append(Route(path, endpoint, methods=[method]))
        ROUTE_META.append((path, method, roles, public, model is not None))
        return fn
    return deco
