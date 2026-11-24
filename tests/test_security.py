"""Security tests. Each test reproduces an attack found in the audit; all must be blocked.
Run: python -m unittest tests.test_security -v"""
import json, os, re, sqlite3, statistics, subprocess, sys, time, unittest
import requests
from .support import Server, Client, DEMO, ROOT, NOPROXY

STRONG = "Kopi-Susu-Enak-77"

def newuser(c, n, pw=STRONG, **kw):
    body = {"name": "Siswa Uji", "email": f"u{n}@x.id", "password": pw, "school": "SMK", "major": "TKJ", "class_name": "XI TKJ"}; body.update(kw)
    return c.post("/api/auth/register", body)

class Main(unittest.TestCase):
    """General server: demo accounts on, generous registration limit."""
    @classmethod
    def setUpClass(cls): cls.srv = Server(8771, METTA_SEED_DEMO=1, METTA_REGISTER_LIMIT=500).start()
    @classmethod
    def tearDownClass(cls): cls.srv.stop()
    def c(self): return Client(self.srv.base)
    def as_(self, role):
        c = self.c(); self.assertEqual(c.login(*DEMO[role], role)[0], 200); return c

    # ---- authorization ----
    def test_idor_between_students(self):
        a = self.as_("student"); b = self.c(); self.assertEqual(newuser(b, 1)[0], 200)
        q = a.get("/api/student/questions")[1]; a.post("/api/student/assessment", {"answers": {str(x["id"]): 4 for x in q["questions"]}, "skill_ids": []})
        cid = a.get("/api/student/insight")[1]["careers"][0]["career_id"]; a.post("/api/student/plan", {"career_id": cid})
        tid = a.get("/api/student/plan")[1]["milestones"][0]["tasks"][0]["id"]
        pid = a.post("/api/student/projects", {"title": "Victim project", "description": "d", "link": "https://e.com", "skill_ids": []})[1]["id"]
        self.assertEqual(b.patch(f"/api/student/tasks/{tid}", {"status": "COMPLETED"})[0], 404)
        self.assertEqual(b.put(f"/api/student/projects/{pid}", {"title": "hacked", "description": "", "link": "", "skill_ids": []})[0], 404)
        self.assertEqual(b.get("/api/student/portfolio")[1]["projects"], [])

    def test_unauthenticated_and_cross_role(self):
        anon = self.c()
        for p in ("/api/student/dashboard", "/api/teacher/students", "/api/admin/users", "/api/me", "/api/careers"): self.assertEqual(anon.get(p)[0], 401, p)
        s = self.as_("student")
        for p in ("/api/teacher/students", "/api/teacher/summary", "/api/admin/users", "/api/admin/audit"): self.assertEqual(s.get(p)[0], 403, p)
        t = self.as_("teacher"); self.assertEqual(t.get("/api/admin/users")[0], 403); self.assertEqual(t.get("/api/student/dashboard")[0], 403)

    def test_route_matrix(self):
        """Every registered route: anonymous -> 401, wrong role -> 403."""
        from metta.api import auth, student, teacher, admin   # noqa: F401  (importing registers the routes, no database is touched)
        from metta.core import ROUTE_META
        self.assertGreater(len(ROUTE_META), 60)
        clients = {r: self.as_(r) for r in ("student", "teacher", "admin")}; anon = self.c()
        bad = []
        for path, method, roles, public, has_body in ROUTE_META:
            if public or path in ("/api/auth/logout",): continue
            url = re.sub(r"\{[^}]+\}", "1", path); kw = {"json": {}} if has_body else {}
            st, _ = anon.call(method, url, **kw)
            if st != 401: bad.append((method, path, "anon", st))
            for role, cl in clients.items():
                st, _ = cl.call(method, url, **kw)
                if roles and role not in roles and st != 403: bad.append((method, path, role, st))
                if (not roles or role in roles) and st in (401, 403): bad.append((method, path, role, st, "should be allowed"))
        self.assertEqual(bad, [])

    # ---- request hardening ----
    def test_json_content_type_required(self):
        c = self.as_("student"); r = c.s.post(self.srv.base + "/api/me/password", data=json.dumps({"current": "x", "new": STRONG}), headers={"Content-Type": "text/plain"})
        self.assertEqual(r.status_code, 415)

    def test_cross_origin_state_change_blocked(self):
        c = self.as_("student")
        self.assertEqual(c.s.post(self.srv.base + "/api/student/insight/save", headers={"Origin": "https://evil.example"}).status_code, 403)
        self.assertEqual(c.s.post(self.srv.base + "/api/student/insight/save", headers={"Sec-Fetch-Site": "cross-site"}).status_code, 403)
        self.assertEqual(c.s.post(self.srv.base + "/api/auth/logout", headers={"Origin": "https://evil.example"}).status_code, 403)
        self.assertEqual(c.get("/api/me")[0], 200, "evil logout must not end the session")
        self.assertNotEqual(c.s.post(self.srv.base + "/api/student/insight/save", headers={"Origin": self.srv.base}).status_code, 403)

    def test_body_size_limit(self):
        c = self.as_("student"); big = '{"name":"' + "A" * 200_000 + '"}'
        r = c.s.put(self.srv.base + "/api/me/profile", data=big, headers={"Content-Type": "application/json"}); self.assertEqual(r.status_code, 413)
        r = c.s.put(self.srv.base + "/api/me/profile", data=big, headers={"Content-Type": "application/json", "Content-Length": "999999999"}); self.assertEqual(r.status_code, 413)

    def test_project_link_validation(self):
        c = self.c(); newuser(c, 2)
        for l in ("javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,x", "http://a b", "http://", "ftp://x.id", "https://x.id/\nx", "https://x.id\\evil", "//evil.com"):
            self.assertEqual(c.post("/api/student/projects", {"title": "abc", "description": "", "link": l, "skill_ids": []})[0], 400, l)
        for l in ("https://github.com/x/y", "http://example.com/a?b=1", "HTTPS://Example.com/x"):
            self.assertEqual(c.post("/api/student/projects", {"title": "abc", "description": "", "link": l, "skill_ids": []})[0], 200, l)

    def test_path_traversal_and_static(self):
        for p in ("/static/%2e%2e/db.py", "/static/..%2fdb.py", "/static/%2e%2e%2f%2e%2e%2fmetta.db"):
            r = requests.get(self.srv.base + p, proxies=NOPROXY); self.assertNotIn(b"CREATE TABLE", r.content, p); self.assertNotEqual(r.headers.get("content-type", "").split(";")[0], "application/octet-stream", p)
        self.assertNotIn(b"SQLite format", requests.get(self.srv.base + "/metta.db", proxies=NOPROXY).content)

    def test_security_headers(self):
        r = requests.get(self.srv.base + "/", proxies=NOPROXY); h = r.headers
        for k in ("Content-Security-Policy", "X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy", "Permissions-Policy", "Cross-Origin-Opener-Policy", "Cross-Origin-Resource-Policy"): self.assertIn(k, h, k)
        self.assertIn("script-src 'self'", h["Content-Security-Policy"]); self.assertIn("object-src 'none'", h["Content-Security-Policy"]); self.assertIn("base-uri 'self'", h["Content-Security-Policy"]); self.assertIn("form-action 'self'", h["Content-Security-Policy"])
        self.assertNotIn("Strict-Transport-Security", h, "HSTS only when HTTPS is declared")
        self.assertEqual(requests.get(self.srv.base + "/api/health", proxies=NOPROXY).headers.get("Cache-Control"), "no-store")

    # ---- passwords ----
    def test_password_policy(self):
        c = self.c()
        for i, pw in enumerate(("12345678", "password", "qwertyui", "11111111", "abcdefgh", "metta2026", "budi.santoso")):
            st, d = newuser(c, 100 + i, pw, email="budi.santoso@x.id" if pw == "budi.santoso" else f"w{i}@x.id"); self.assertEqual(st, 422, (pw, d))
        self.assertEqual(newuser(c, 120, STRONG)[0], 200)
        ad = self.as_("admin")
        self.assertEqual(ad.post("/api/admin/users", {"name": "Guru Baru", "email": "g1@x.id", "role": "teacher", "password": "Abc12345"})[0], 422, "staff need 12+ chars")
        self.assertEqual(ad.post("/api/admin/users", {"name": "Guru Baru", "email": "g1@x.id", "role": "teacher", "password": "Kopi-Susu-Enak-77"})[0], 200)
        uid = [u for u in ad.get("/api/admin/users")[1]["items"] if u["email"] == "g1@x.id"][0]["id"]
        self.assertEqual(ad.patch(f"/api/admin/users/{uid}", {"password": "12345678"})[0], 422)
        s = self.as_("student"); self.assertEqual(s.post("/api/me/password", {"current": DEMO["student"][1], "new": "12345678"})[0], 422)

    def test_login_timing_does_not_reveal_accounts(self):
        newuser(self.c(), 400)                      # a real account that is only used for failed logins here (stays under the lock-out limit)
        def med(emails):
            xs = []
            for e in emails:
                c = self.c(); t = time.perf_counter(); c.login(e, "wrong-pass-123"); xs.append(time.perf_counter() - t)
            return statistics.median(xs)
        real = med(["u400@x.id"] * 5); fake = med([f"ghost{i}@x.id" for i in range(5)])
        self.assertGreater(fake, real * 0.6, f"missing account answers much faster ({fake:.3f}s vs {real:.3f}s)")

    # ---- sessions and audit ----
    def test_session_cap_and_cleanup(self):
        first = self.c(); first.login(*DEMO["student"])
        for _ in range(6): self.c().login(*DEMO["student"])
        self.assertEqual(first.get("/api/me")[0], 401, "oldest session must be dropped after 5")
        con = sqlite3.connect(self.srv.db); uid = con.execute("select id from users where email='student@metta.sch'").fetchone()[0]
        con.execute("insert into sessions(token_hash,user_id,expires_at) values('dead',?,'2000-01-01 00:00:00')", (uid,)); con.commit(); con.close()
        self.c().login(*DEMO["student"])
        con = sqlite3.connect(self.srv.db); self.assertIsNone(con.execute("select 1 from sessions where token_hash='dead'").fetchone()); con.close()

    def test_password_change_ends_other_sessions(self):
        a = self.c(); b = self.c(); newuser(a, 300); b.login("u300@x.id", STRONG)
        self.assertEqual(a.post("/api/me/password", {"current": STRONG, "new": STRONG + "x"})[0], 200)
        self.assertEqual(b.get("/api/me")[0], 401); self.assertEqual(a.get("/api/me")[0], 200)

    def test_staff_sessions_are_shorter(self):
        self.as_("teacher"); con = sqlite3.connect(self.srv.db)
        hrs = con.execute("select (julianday(max(expires_at))-julianday('now'))*24 from sessions s join users u on u.id=s.user_id where u.role='teacher'").fetchone()[0]; con.close()
        self.assertLess(hrs, 13)

    def test_login_events_are_audited_without_passwords(self):
        self.c().login("teacher@metta.sch", "Sup3r-secret-guess"); ad = self.as_("admin")
        items = ad.get("/api/admin/audit")[1]["items"]; acts = {x["action"] for x in items}
        self.assertIn("login_fail", acts); self.assertIn("login_ok", acts)
        self.assertNotIn("Sup3r-secret-guess", json.dumps(items))

    def test_database_file_not_world_readable(self):
        if os.name != "posix": self.skipTest("posix only")
        self.assertEqual(os.stat(self.srv.db).st_mode & 0o077, 0)

class RateLimits(unittest.TestCase):
    """Own server so lock-outs do not disturb other tests."""
    @classmethod
    def setUpClass(cls): cls.srv = Server(8772, METTA_SEED_DEMO=1, METTA_REGISTER_LIMIT=5).start()
    @classmethod
    def tearDownClass(cls): cls.srv.stop()
    def c(self): return Client(self.srv.base)

    def test_a_per_account_lockout_even_with_new_sessions(self):
        codes = [self.c().login("admin@metta.sch", f"guess-{i}-xyz", "admin")[0] for i in range(14)]
        self.assertIn(429, codes); self.assertEqual(self.c().login(*DEMO["admin"], "admin")[0], 429, "correct password must also wait during lock-out")

    def test_b_password_guessing_on_change_is_limited(self):
        s = self.c(); self.assertEqual(s.login(*DEMO["student"], "student")[0], 200)
        codes = [s.post("/api/me/password", {"current": f"bad-{i}-guess", "new": STRONG})[0] for i in range(9)]
        self.assertIn(429, codes)

    def test_c_registration_limit(self):
        codes = [newuser(self.c(), 500 + i)[0] for i in range(9)]
        self.assertEqual(codes.count(200), 5, codes); self.assertIn(429, codes)

    def test_d_per_ip_limit_across_many_emails(self):
        codes = [self.c().login(f"nobody{i}@x.id", "whatever-123")[0] for i in range(45)]
        self.assertIn(429, codes)

class Strict(unittest.TestCase):
    """Production-like settings."""
    @classmethod
    def setUpClass(cls):
        cls.srv = Server(8773, METTA_ENV="production", METTA_SECURE_COOKIE=1, METTA_REGISTER_CODE="KODE-SEKOLAH-2026", METTA_ALLOWED_HOSTS="127.0.0.1,localhost", METTA_REGISTER_LIMIT=500).start()
        # no demo accounts here, so create the first admin the safe way
        p = subprocess.run([sys.executable, "-m", "metta.create_user", "--email", "kepala@x.id", "--name", "Kepala Sekolah", "--role", "admin", "--password-stdin"],
                           cwd=ROOT, env=cls.srv.env, input=STRONG + "\n", capture_output=True, text=True); assert p.returncode == 0, p.stderr
    @classmethod
    def tearDownClass(cls): cls.srv.stop()
    def c(self): return Client(self.srv.base)

    def test_no_demo_accounts(self):
        self.assertEqual(self.c().login("admin@metta.sch", "Admin#2026!")[0], 401)
        self.assertEqual(self.c().login("student@metta.sch", "Student#2026!")[0], 401)
        con = sqlite3.connect(self.srv.db); self.assertEqual(con.execute("select count(*) from users where email like '%@metta.sch'").fetchone()[0], 0); con.close()

    def test_secure_cookie_and_hsts(self):
        r = self.c().s.post(self.srv.base + "/api/auth/login", json={"email": "kepala@x.id", "password": STRONG}); self.assertEqual(r.status_code, 200)
        sc = r.headers["set-cookie"]; self.assertIn("Secure", sc); self.assertIn("HttpOnly", sc); self.assertRegex(sc.lower(), "samesite=(lax|strict)")
        self.assertIn("max-age=", requests.get(self.srv.base + "/", proxies=NOPROXY).headers["Strict-Transport-Security"].lower())

    def test_register_code_required(self):
        c = self.c(); self.assertEqual(c.get("/api/auth/config")[1]["register_code_required"], True)
        self.assertEqual(newuser(c, 700)[0], 403); self.assertEqual(newuser(c, 701, code="salah")[0], 403)
        self.assertEqual(newuser(c, 702, code="KODE-SEKOLAH-2026")[0], 200)

    def test_host_header_allowlist(self):
        r = requests.get(self.srv.base + "/api/health", headers={"Host": "evil.example"}, proxies=NOPROXY); self.assertEqual(r.status_code, 400)

class Startup(unittest.TestCase):
    def run_server(self, port, **env):
        s = Server(port, **env); p = s.start(wait=False)
        try: p.proc.wait(12)
        except subprocess.TimeoutExpired: s.stop(); return None, ""
        return p.proc.returncode, p.proc.stdout.read().decode(errors="replace")

    def test_demo_accounts_not_created_by_default(self):
        s = Server(8774).start()
        try: self.assertEqual(Client(s.base).login("admin@metta.sch", "Admin#2026!")[0], 401)
        finally: s.stop()

    def test_production_refuses_demo_accounts(self):
        code, out = self.run_server(8775, METTA_ENV="production", METTA_SECURE_COOKIE=1, METTA_SEED_DEMO=1)
        self.assertNotIn(code, (0, None), out); self.assertIn("demo", out.lower())

    def test_production_refuses_insecure_cookie(self):
        code, out = self.run_server(8776, METTA_ENV="production")
        self.assertNotIn(code, (0, None), out); self.assertIn("METTA_SECURE_COOKIE", out)

    def test_production_refuses_existing_demo_accounts(self):
        s = Server(8777, METTA_SEED_DEMO=1).start(); s.stop()          # first run creates demo accounts
        s2 = Server(8777, METTA_ENV="production", METTA_SECURE_COOKIE=1); s2.db = s.db; s2.env["METTA_DB"] = s.db
        p = s2.start(wait=False)
        try: p.proc.wait(12)
        except subprocess.TimeoutExpired: s2.stop(); self.fail("server started with known demo passwords")
        self.assertNotEqual(p.proc.returncode, 0)

if __name__ == "__main__": unittest.main()
