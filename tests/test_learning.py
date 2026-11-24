"""Tes belajar (langkah, kuis) dan magang (55 tempat, tujuan, teman)."""
import unittest
from .support import Server, Client, DEMO
from metta import seed_learning as SL
from metta.api.learn import _order

PW = "Kopi-Susu-Enak-77"


class Learning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = Server(8794, METTA_SEED_DEMO=1, METTA_REGISTER_LIMIT=500, METTA_COURSE_COOLDOWN=2).start()
        cls.n = 0

    @classmethod
    def tearDownClass(cls):
        cls.srv.stop()

    def student(self):
        Learning.n += 1
        c = Client(self.srv.base); c.s.headers["X-Lang"] = "en"
        st, d = c.post("/api/auth/register", {"name": "Siswa Belajar", "email": f"lj{Learning.n}@x.id", "password": PW, "major": "TKJ", "class_name": "XI TKJ"})
        self.assertEqual(st, 200); c.uid = d.get("user", d).get("id")
        return c

    def plan_for(self, c, skill_name):
        _, cs = c.get("/api/careers?limit=200")
        for item in cs["items"]:
            _, det = c.get(f"/api/careers/{item['id']}")
            if any(s["name"] == skill_name for s in det["skills"]):
                st, p = c.post("/api/student/plan", {"career_id": item["id"]}); self.assertEqual(st, 200)
                return p
        self.fail("no career has skill " + skill_name)

    def task(self, plan, kind, skill):
        for m in plan["milestones"]:
            if m["skill"] == skill:
                return next(t for t in m["tasks"] if t["kind"] == kind)
        self.fail("task not found")

    def test_study_needs_all_steps(self):
        c = self.student(); p = self.plan_for(c, "Python"); t = self.task(p, "STUDY", "Python")
        self.assertEqual(c.patch(f"/api/student/tasks/{t['id']}", {"status": "COMPLETED"})[0], 400)
        _, les = c.get(f"/api/student/learn/{t['id']}"); self.assertFalse(les["ready"]); self.assertEqual(len(les["steps"]), 3)
        for i in range(2): c.post(f"/api/student/learn/{t['id']}/step", {"idx": i, "done": True})
        self.assertEqual(c.patch(f"/api/student/tasks/{t['id']}", {"status": "COMPLETED"})[0], 400)
        _, les = c.post(f"/api/student/learn/{t['id']}/step", {"idx": 2, "done": True}); self.assertTrue(les["ready"])
        self.assertEqual(c.post(f"/api/student/learn/{t['id']}/step", {"idx": 5, "done": True})[0], 400)
        self.assertEqual(c.patch(f"/api/student/tasks/{t['id']}", {"status": "COMPLETED"})[0], 200)
        other = self.student()
        self.assertEqual(other.get(f"/api/student/learn/{t['id']}")[0], 404)
        self.assertEqual(other.post(f"/api/student/learn/{t['id']}/step", {"idx": 0, "done": True})[0], 404)

    def test_quiz_is_graded_on_server_and_never_leaks_answers(self):
        c = self.student(); p = self.plan_for(c, "Python"); t = self.task(p, "PRACTICE", "Python")
        _, les = c.get(f"/api/student/learn/{t['id']}")
        self.assertTrue(les["has_quiz"]); self.assertEqual(len(les["quiz"]), 3)
        self.assertNotIn("correct", str(les).lower().replace("incorrect", ""))
        self.assertEqual(c.patch(f"/api/student/tasks/{t['id']}", {"status": "COMPLETED"})[0], 400)
        self.assertEqual(c.post(f"/api/student/learn/{t['id']}/quiz", {"answers": [0]})[0], 400)
        self.assertEqual(c.post(f"/api/student/learn/{t['id']}/quiz", {"answers": [0, 0, 9]})[0], 400)
        skill_id = c.get(f"/api/student/learn/{t['id']}")[1] and next(m["skill_id"] for m in p["milestones"] if m["skill"] == "Python")
        quiz = SL.L["Python"]["quiz"]
        def best(att):  # jawaban benar mengikuti urutan acak percobaan ke-att
            return [_order(c.uid, skill_id, qi, att, len(q[2])).index(q[3]) for qi, q in enumerate(quiz)]
        wrong = [(a + 1) % 3 for a in best(0)]
        st, r = c.post(f"/api/student/learn/{t['id']}/quiz", {"answers": wrong}); self.assertEqual(st, 200)
        self.assertFalse(r["passed"]); self.assertEqual(r["score"], 0)
        self.assertEqual(r["results"], [])                                  # gagal: tidak ada benar/salah per soal dan tidak ada penjelasan
        self.assertEqual(c.patch(f"/api/student/tasks/{t['id']}", {"status": "COMPLETED"})[0], 400)
        self.assertEqual(c.post(f"/api/student/learn/{t['id']}/quiz", {"answers": best(1)})[0], 400)    # jeda setelah gagal
        self.assertGreater(c.get(f"/api/student/learn/{t['id']}")[1]["wait"], 0)
        import time; time.sleep(2.3)
        st, r = c.post(f"/api/student/learn/{t['id']}/quiz", {"answers": best(1)}); self.assertTrue(r["passed"]); self.assertEqual(r["percent"], 100)
        self.assertEqual(len(r["results"]), 3)                              # lulus: penjelasan dibuka
        self.assertEqual(c.patch(f"/api/student/tasks/{t['id']}", {"status": "COMPLETED"})[0], 200)

    def test_apply_needs_project(self):
        c = self.student(); p = self.plan_for(c, "Python"); t = self.task(p, "APPLY", "Python")
        self.assertEqual(c.patch(f"/api/student/tasks/{t['id']}", {"status": "COMPLETED"})[0], 400)
        sid = next(m["skill_id"] for m in p["milestones"] if m["skill"] == "Python")
        self.assertEqual(c.post("/api/student/projects", {"title": "Kalkulator Python", "description": "Program hitung rata-rata", "skill_ids": [sid]})[0], 200)
        self.assertEqual(c.patch(f"/api/student/tasks/{t['id']}", {"status": "COMPLETED"})[0], 200)

    def test_skill_without_written_quiz_needs_no_note(self):
        c = self.student(); _, cs = c.get("/api/careers?limit=200")
        for item in cs["items"]:
            _, det = c.get(f"/api/careers/{item['id']}")
            names = [s["name"] for s in det["skills"] if s["name"] not in SL.L]
            if names: break
        else: self.skipTest("all skills authored")
        p = c.post("/api/student/plan", {"career_id": item["id"]})[1]
        t = next(t for m in p["milestones"] for t in m["tasks"] if t["kind"] == "PRACTICE" and m["skill"] not in SL.L)
        self.assertEqual(c.post(f"/api/student/learn/{t['id']}/note", {"note": "x"})[0], 405)   # catatan latihan sudah dihapus (rute tidak ada)
        self.assertEqual(c.patch(f"/api/student/tasks/{t['id']}", {"status": "COMPLETED"})[0], 200)

    def test_internship(self):
        c = self.student(); st, d = c.get("/api/companies"); self.assertEqual(st, 200)
        self.assertEqual(d["total"], 55); self.assertEqual(d["verified"], 12); self.assertEqual(len(d["checklist"]), 5)
        by = {x["number"]: x for x in d["items"]}
        self.assertTrue(by[21]["verified"]); self.assertIn("Rumbai", by[21]["address"]); self.assertTrue(by[21]["maps_url"].startswith("https://www.google.com/maps/search/"))
        self.assertFalse(by[1]["verified"]); self.assertEqual(by[1]["address"], "")        # tidak mengarang
        ids = [by[21]["id"], by[53]["id"]]
        body = {"class_name": "XI TKJ", "company_ids": ids, "purposes": ["Belajar jaringan kampus", "Belajar front office"], "friends": [{"name": "Budi Santoso", "class_name": "XI TKJ"}]}
        st, r = c.put("/api/student/internship", body); self.assertEqual(st, 200)
        self.assertEqual([x["purpose"] for x in r["choices"]], body["purposes"]); self.assertEqual(r["friends"][0]["name"], "Budi Santoso")
        self.assertEqual(c.put("/api/student/internship", dict(body, friends=[{"name": "Aa Bb"}] * 4))[0], 422)
        self.assertEqual(c.put("/api/student/internship", dict(body, purposes=["x" * 501]))[0], 400)
        self.assertEqual(c.put("/api/student/internship", dict(body, friends=[{"name": "<b>x</b>", "class_name": "y" * 40}]))[0], 422)
        t = Client(self.srv.base); t.login(*DEMO["teacher"])
        _, ti = t.get("/api/teacher/internship"); me = next(x for x in ti["items"] if x["name"] == "Siswa Belajar" and x["friends"])
        self.assertTrue(me["friends"][0].startswith("Budi")); self.assertEqual(me["purposes"][0], "Belajar jaringan kampus")
        self.assertEqual(t.get("/api/student/internship")[0], 403)
        a = Client(self.srv.base); a.login(*DEMO["admin"])
        cid = by[1]["id"]; st, _ = a.put(f"/api/admin/companies/{cid}", {"name": "Asia Group", "address": "Jl. Contoh 1", "about": "Test", "verified": True}); self.assertEqual(st, 200)
        self.assertTrue({x["id"]: x for x in c.get("/api/companies")[1]["items"]}[cid]["verified"])


if __name__ == "__main__":
    unittest.main()
