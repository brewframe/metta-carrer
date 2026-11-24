"""Data demo presentasi: terisi lewat API, aman diulang, dan menolak server non-lokal / production."""
import os, subprocess, sys, unittest
from tests.support import Server, Client, ROOT, DEMO


def run_demo(base, **env):
    e = dict(os.environ, METTA_DEMO_URL=base, **env)
    for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"): e.pop(k, None)
    return subprocess.run([sys.executable, "-m", "metta.demo_data"], cwd=ROOT, env=e, capture_output=True, text=True, timeout=180)


class DemoDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.srv = Server(8823, METTA_SEED_DEMO=1).start()
    @classmethod
    def tearDownClass(cls): cls.srv.stop()

    def test_fill_once_and_idempotent(self):
        r = run_demo(self.srv.base); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("[LEWATI]", r.stdout, r.stdout)
        s = Client(self.srv.base); s.login(*DEMO["student"])
        self.assertEqual(s.get("/api/student/plan")[1]["plan"]["career"], "Network Engineer")
        self.assertEqual(len(s.get("/api/student/projects")[1]["items"]), 2)
        t = Client(self.srv.base); t.login(*DEMO["teacher"])
        self.assertEqual(len(t.get("/api/teacher/validation")[1]["items"]), 1)
        self.assertEqual(len(t.get("/api/teacher/company-submissions")[1]["items"]), 1)
        a = Client(self.srv.base); a.login(*DEMO["admin"])
        self.assertEqual(len(a.get("/api/admin/content?status=PUBLISHED")[1]["items"]), 1)
        self.assertEqual(len(a.get("/api/admin/content?status=PENDING")[1]["items"]), 1)
        an = t.get("/api/teacher/analytics")[1]
        self.assertEqual(sum(x["value"] for x in an["status"]), an["total"])
        self.assertEqual([x["key"] for x in an["projects"]], ["SUBMITTED", "NEEDS_REVISION", "VERIFIED"])
        self.assertEqual({x["key"]: x["value"] for x in an["projects"]}, {"SUBMITTED": 1, "NEEDS_REVISION": 0, "VERIFIED": 1})
        self.assertTrue(all(0 <= x["avg_readiness"] <= 100 for x in an["by_class"]))
        self.assertIn("Network Engineer", [x["label"] for x in an["careers"]])
        ad = a.get("/api/admin/analytics")[1]
        self.assertEqual({x["key"]: x["value"] for x in ad["users_by_role"]}["student"], 3)
        self.assertEqual(sum(x["value"] for x in ad["students_by_major"]), 3)
        self.assertEqual(t.get("/api/admin/analytics")[0], 403, "teacher cannot open admin analytics")
        r2 = run_demo(self.srv.base); self.assertEqual(r2.returncode, 0); self.assertIn("sudah ada", r2.stdout)
        self.assertEqual(len(s.get("/api/student/projects")[1]["items"]), 2, "second run must not add data")

    def test_refuses_remote_and_production(self):
        self.assertNotEqual(run_demo("http://example.com").returncode, 0)
        self.assertNotEqual(run_demo(self.srv.base, METTA_ENV="production").returncode, 0)


if __name__ == "__main__": unittest.main()
