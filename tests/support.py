"""Test helpers: start the real server on a throw-away database with a chosen environment."""
import os, subprocess, sys, tempfile, time
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOPROXY = {"http": None, "https": None}

class Server:
    def __init__(self, port, **env):
        self.port = port; self.base = f"http://127.0.0.1:{port}"; self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "t.db")
        self.env = dict(os.environ, METTA_DB=self.db, **{k: str(v) for k, v in env.items()})
        for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"): self.env.pop(k, None)
        self.proc = None
    def start(self, wait=True):
        self.proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "metta.app:app", "--port", str(self.port), "--log-level", "warning"],
                                     cwd=ROOT, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if not wait: return self
        for _ in range(80):
            if self.proc.poll() is not None: raise RuntimeError("server exited: " + self.proc.stdout.read().decode(errors="replace"))
            try:
                if requests.get(self.base + "/api/health", timeout=1, proxies=NOPROXY).ok: return self
            except Exception: time.sleep(0.25)
        raise RuntimeError("server did not start")
    def stop(self):
        if self.proc and self.proc.poll() is None: self.proc.terminate(); self.proc.wait(10)

class Client:
    def __init__(self, base):
        self.base = base; self.s = requests.Session(); self.s.trust_env = False
    def call(self, method, path, **kw):
        kw.setdefault("timeout", 20)
        r = self.s.request(method, self.base + path, **kw)
        try: data = r.json()
        except Exception: data = None
        return r.status_code, data
    def get(self, p, **kw): return self.call("GET", p, **kw)
    def post(self, p, j=None, **kw): return self.call("POST", p, json={} if j is None else j, **kw)
    def put(self, p, j, **kw): return self.call("PUT", p, json=j, **kw)
    def patch(self, p, j, **kw): return self.call("PATCH", p, json=j, **kw)
    def delete(self, p, **kw): return self.call("DELETE", p, **kw)
    def login(self, email, pw, role=""): return self.post("/api/auth/login", {"email": email, "password": pw, "role": role})

DEMO = {"student": ("student@metta.sch", "Student#2026!"), "teacher": ("teacher@metta.sch", "Teacher#2026!"), "admin": ("admin@metta.sch", "Admin#2026!")}
