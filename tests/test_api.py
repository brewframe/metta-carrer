"""End-to-end API tests. Starts the real server on a temporary database.
Run:  python -m unittest tests.test_api -v   (needs the `requests` package)"""
import os, subprocess, sys, tempfile, time, unittest
import requests

PORT = 8765; BASE = f"http://127.0.0.1:{PORT}"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Api:
    def __init__(self): self.s = requests.Session(); self.s.headers["X-Lang"] = "en"     # tes memeriksa teks Inggris
    def call(self, method, path, **kw):
        r = self.s.request(method, BASE + path, timeout=15, **kw)
        try: data = r.json()
        except Exception: data = None
        return r.status_code, data
    def get(self, p, **kw): return self.call("GET", p, **kw)
    def post(self, p, j=None): return self.call("POST", p, json=j if j is not None else {})
    def put(self, p, j): return self.call("PUT", p, json=j)
    def patch(self, p, j): return self.call("PATCH", p, json=j)
    def delete(self, p): return self.call("DELETE", p)
    def login(self, email, pw, role=""): return self.post("/api/auth/login", {"email": email, "password": pw, "role": role})

class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(); env = dict(os.environ, METTA_DB=os.path.join(cls.tmp, "t.db"), METTA_SEED_DEMO="1", METTA_REGISTER_LIMIT="500")
        env.pop("HTTPS_PROXY", None); env.pop("https_proxy", None)
        cls.proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "metta.app:app", "--port", str(PORT), "--log-level", "warning"], cwd=ROOT, env=env)
        for _ in range(60):
            try:
                if requests.get(BASE + "/api/health", timeout=1, proxies={"http": None, "https": None}).ok: break
            except Exception: time.sleep(0.25)
        else: raise RuntimeError("server did not start")
    @classmethod
    def tearDownClass(cls): cls.proc.terminate(); cls.proc.wait()

    def api(self):
        a = Api(); a.s.trust_env = False; return a

    # ---- auth & security ----
    def test_01_auth_and_roles(self):
        a = self.api()
        self.assertEqual(a.get("/api/me")[0], 401)
        self.assertEqual(a.login("student@metta.sch", "wrong")[0], 401)
        st, me = a.login("student@metta.sch", "Student#2026!", "student"); self.assertEqual(st, 200); self.assertEqual(me["role"], "student")
        self.assertEqual(a.get("/api/teacher/summary")[0], 403)
        self.assertEqual(a.get("/api/admin/users")[0], 403)
        self.assertEqual(a.login("student@metta.sch", "Student#2026!", "admin")[0], 401, "role tab must match")
        self.assertEqual(a.post("/api/auth/logout")[0], 200)
        self.assertEqual(a.get("/api/me")[0], 401)

    def test_02_register_validation(self):
        a = self.api()
        bad = {"name": "Budi", "email": "budi@x.id", "password": "short", "major": "TKJ", "class_name": "X TKJ"}
        self.assertEqual(a.post("/api/auth/register", bad)[0], 422)
        good = dict(bad, password="Kopi-Susu-Enak-77"); self.assertEqual(a.post("/api/auth/register", good)[0], 200)
        self.assertEqual(self.api().post("/api/auth/register", good)[0], 409)
        self.assertEqual(a.get("/api/me")[1]["profile"]["major"], "TKJ")
        self.assertEqual(self.api().post("/api/auth/register", dict(good, email="not-an-email"))[0], 422)

    def test_03_login_throttle(self):
        a = self.api()
        for _ in range(6): a.login("nobody@x.id", "bad")
        self.assertEqual(a.login("nobody@x.id", "bad")[0], 429)

    # ---- student journey ----
    def test_10_student_journey_with_teacher_validation(self):
        s = self.api(); t = self.api()
        s.post("/api/auth/register", {"name": "Sari", "email": "sari@x.id", "password": "Kopi-Susu-Enak-77", "major": "TKJ", "class_name": "XI TKJ"})
        self.assertEqual(s.get("/api/student/insight")[0], 404)
        _, q = s.get("/api/student/questions"); qs = q["questions"]; self.assertGreaterEqual(len(qs), 20)
        self.assertEqual(s.post("/api/student/assessment", {"answers": {"1": 5}})[0], 400)
        ans = {str(x["id"]): (5 if x["tag"] in ("technology", "analytical", "logical", "technical", "problem_solving") else 2) for x in qs}
        st, ins = s.post("/api/student/assessment", {"answers": ans, "skill_ids": [q["skills"][0]["id"]]}); self.assertEqual(st, 200)
        self.assertIn("technology", ins["interests"]); self.assertEqual(len(ins["careers"]), 3)
        top = ins["careers"][0]; self.assertTrue(top["reasons"]); self.assertEqual(top["category"], "Technology")
        self.assertEqual(s.post("/api/student/insight/save")[0], 200)
        # plan
        _, rec = s.get("/api/student/recommendations"); cid = rec["items"][0]["career_id"]
        _, prev = s.get(f"/api/student/plan/preview/{cid}"); self.assertTrue(prev["milestones"]); self.assertTrue(prev["skill_gap"])
        self.assertEqual(s.get("/api/student/plan")[1]["plan"], None)
        st, plan = s.post("/api/student/plan", {"career_id": cid}); self.assertEqual(st, 200); self.assertEqual(plan["readiness"], 0 if plan["current_skills"] == [] else plan["readiness"])
        tid = plan["milestones"][0]["tasks"][0]["id"]
        self.assertEqual(s.patch(f"/api/student/tasks/{tid}", {"status": "COMPLETED"})[0], 400)   # belum mencentang langkah belajar
        _, les = s.get(f"/api/student/learn/{tid}")
        for i in range(len(les["steps"])): s.post(f"/api/student/learn/{tid}/step", {"idx": i, "done": True})
        st, r = s.patch(f"/api/student/tasks/{tid}", {"status": "COMPLETED"}); self.assertEqual(st, 200); self.assertGreater(r["readiness"], plan["readiness"] - 1)
        self.assertEqual(s.patch(f"/api/student/tasks/{tid}", {"status": "NOPE"})[0], 422)
        # dashboard
        _, dash = s.get("/api/student/dashboard"); self.assertEqual(dash["target"], plan["plan"]["career"]); self.assertIsNotNone(dash["today_task"])
        # project -> teacher validation
        skill_id = plan["skill_gap"][0]["id"]
        self.assertEqual(s.post("/api/student/projects", {"title": "Bad", "link": "javascript:alert(1)"})[0], 400)
        st, proj = s.post("/api/student/projects", {"title": "Mini network", "description": "x", "link": "https://github.com/x/y", "skill_ids": [skill_id]}); self.assertEqual(st, 200)
        self.assertEqual(t.login("teacher@metta.sch", "Teacher#2026!")[0], 200)
        _, sm = t.get("/api/teacher/summary"); self.assertGreaterEqual(sm["needs_feedback"], 1)
        _, qu = t.get("/api/teacher/validation"); self.assertTrue(any(p["id"] == proj["id"] for p in qu["items"]))
        self.assertEqual(t.post(f"/api/teacher/projects/{proj['id']}/review", {"decision": "NEEDS_REVISION"})[0], 400, "revision needs a note")
        self.assertEqual(t.post(f"/api/teacher/projects/{proj['id']}/review", {"decision": "NEEDS_REVISION", "note": "Add a diagram"})[0], 200)
        self.assertTrue(any("needs revision" in n["text"] for n in s.get("/api/notifications")[1]["items"]))
        self.assertEqual(s.put(f"/api/student/projects/{proj['id']}", {"title": "Mini network v2", "skill_ids": [skill_id]})[0], 200)
        self.assertEqual(t.post(f"/api/teacher/projects/{proj['id']}/review", {"decision": "VERIFIED"})[0], 200)
        _, pf = s.get("/api/student/portfolio"); self.assertEqual(len(pf["projects"]), 1)
        self.assertTrue(any(x["evidence"] == "Teacher verified" for x in pf["skills"]))
        _, out = s.get("/api/student/outcome"); self.assertGreaterEqual(out["now"], out["before"]); self.assertTrue(out["verified_skills"])
        # feedback + guidance
        sid = s.get("/api/me")[1]["id"]
        self.assertEqual(t.post(f"/api/teacher/students/{sid}/feedback", {"text": "Great progress"})[0], 200)
        _, det = t.get(f"/api/teacher/students/{sid}"); self.assertEqual(det["feedback"][0]["text"], "Great progress"); self.assertEqual(det["plan"]["career"], plan["plan"]["career"])
        pid = det["plan"]["id"]; self.assertEqual(t.put(f"/api/teacher/plans/{pid}/guidance", {"note": "Focus on Mikrotik"})[0], 200)
        self.assertEqual(s.get("/api/student/plan")[1]["plan"]["teacher_note"], "Focus on Mikrotik")
        # assistant
        self.assertIn("next step", s.post("/api/student/assistant", {"question": "What should I do next?"})[1]["answer"].lower())
        self.assertTrue(s.post("/api/student/assistant", {"question": "why this career?"})[1]["reasons"])
        # data isolation: other student cannot see Sari's projects
        o = self.api(); o.login("student@metta.sch", "Student#2026!")
        self.assertEqual(o.get("/api/student/projects")[1]["items"], [])
        self.assertEqual(o.patch(f"/api/student/tasks/{tid}", {"status": "COMPLETED"})[0], 404)

    def test_20_internship(self):
        s = self.api(); s.login("student@metta.sch", "Student#2026!")
        _, co = s.get("/api/companies"); self.assertGreaterEqual(co["total"], 6)
        ids = [c["id"] for c in co["items"][:3]]
        self.assertEqual(s.put("/api/student/internship", {"class_name": "XI TKJ", "company_ids": [ids[0], ids[0]]})[0], 400)
        self.assertEqual(s.put("/api/student/internship", {"class_name": "XI TKJ", "company_ids": ids + [ids[0]]})[0], 422)
        self.assertEqual(s.put("/api/student/internship", {"class_name": "XI TKJ", "company_ids": [99999]})[0], 404)
        st, r = s.put("/api/student/internship", {"class_name": "XI TKJ", "company_ids": ids}); self.assertEqual(st, 200); self.assertEqual([c["rank"] for c in r["choices"]], [1, 2, 3])
        self.assertEqual(len(s.get("/api/companies?q=bank")[1]["items"]), 1)
        t = self.api(); t.login("teacher@metta.sch", "Teacher#2026!")
        row = next(x for x in t.get("/api/teacher/internship")[1]["items"] if x["name"] == "Student Demo"); self.assertEqual(len([c for c in row["choices"] if c]), 3)
        self.assertEqual(t.put("/api/student/internship", {"class_name": "x", "company_ids": [1]})[0], 403, "teacher is read only")

    # ---- admin ----
    def test_30_admin(self):
        a = self.api(); a.login("admin@metta.sch", "Admin#2026!")
        st, u = a.post("/api/admin/users", {"name": "Bu Rina", "email": "rina@metta.sch", "role": "teacher", "password": "Kopi-Susu-Enak-77"}); self.assertEqual(st, 200)
        self.assertEqual(self.api().login("rina@metta.sch", "Kopi-Susu-Enak-77", "teacher")[0], 200)
        self.assertEqual(a.patch(f"/api/admin/users/{u['id']}", {"active": False})[0], 200)
        self.assertEqual(self.api().login("rina@metta.sch", "Kopi-Susu-Enak-77")[0], 401, "deactivated users cannot log in")
        me = a.get("/api/me")[1]; self.assertEqual(a.patch(f"/api/admin/users/{me['id']}", {"active": False})[0], 400)
        st, r = a.post("/api/admin/companies/import", {"text": "7;PT Contoh Jaya;Jl. Sudirman 1, Pekanbaru\n8;Bank Seraya\n9\n"})
        self.assertEqual(st, 200); self.assertEqual(r["added"], 1); self.assertGreaterEqual(r["skipped"], 1)
        st, sk = a.post("/api/admin/skills", {"name": "Teknik uji skill baru", "category": "technical"}); self.assertEqual(st, 200)
        self.assertEqual(a.post("/api/admin/skills", {"name": "cloud basics"})[0], 409)
        st, ca = a.post("/api/admin/careers", {"name": "Teknik Uji Karier Baru", "category": "Technology", "interest_tags": "technology", "strength_tags": "logical", "majors": "TKJ", "skills": [{"skill_id": sk["id"], "importance": 3}]}); self.assertEqual(st, 200)
        self.assertEqual(a.delete(f"/api/admin/skills/{sk['id']}")[0], 400, "skill in use")
        self.assertTrue(any(c["name"] == "Teknik Uji Karier Baru" for c in a.get("/api/careers")[1]["items"]))
        self.assertEqual(a.delete(f"/api/admin/careers/{ca['id']}")[0], 200)
        _, an = a.get("/api/admin/analytics"); self.assertIn("summary", an)
        _, au = a.get("/api/admin/audit"); self.assertTrue(any(x["action"] == "company_import" for x in au["items"]))
        s = self.api(); s.login("student@metta.sch", "Student#2026!"); self.assertEqual(s.post("/api/admin/skills", {"name": "Hack"})[0], 403)

    def test_35_concurrent_requests(self):
        """Regression: parallel requests from one user must not hit 'database is locked'."""
        from concurrent.futures import ThreadPoolExecutor
        a = self.api(); a.login("student@metta.sch", "Student#2026!")
        cookies = a.s.cookies.get_dict()
        def hit(i):
            s = requests.Session(); s.trust_env = False; s.cookies.update(cookies)
            return s.get(BASE + ["/api/me", "/api/student/dashboard", "/api/careers", "/api/companies"][i % 4], timeout=15).status_code
        with ThreadPoolExecutor(16) as ex: codes = list(ex.map(hit, range(80)))
        self.assertEqual(set(codes), {200}, codes)

    def test_40_pages_and_headers(self):
        r = requests.get(BASE + "/", proxies={"http": None, "https": None}); self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["X-Frame-Options"], "DENY"); self.assertIn("default-src 'self'", r.headers["Content-Security-Policy"])
        self.assertEqual(requests.get(BASE + "/static/app.js", proxies={"http": None, "https": None}).status_code, 200)

if __name__ == "__main__": unittest.main()
