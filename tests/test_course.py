"""Tes kursus karier: aturan bab berurutan, kuis acak di server, kunci jawaban tidak bocor, ujian akhir, proyek bab 6, kesiapan, dan portfolio."""
import json, random, sqlite3, time, unittest
from .support import Server, Client, DEMO
from metta import course as CRS

PW = "Kopi-Susu-Enak-77"
NOTE = "Saya mencoba semua latihan di simulator dan mencatat hasil setiap langkahnya dengan teliti."
ST = DEMO["student"]; TE = DEMO["teacher"]


class Course(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = Server(8803, METTA_SEED_DEMO=1, METTA_REGISTER_LIMIT=500, METTA_COURSE_READ_SEC=2, METTA_COURSE_COOLDOWN=2).start(); cls.n = 0

    @classmethod
    def tearDownClass(cls): cls.srv.stop()

    def student(self):
        Course.n += 1
        c = Client(self.srv.base); c.s.headers["X-Lang"] = "en"
        st, d = c.post("/api/auth/register", {"name": "Siswa Kursus", "email": f"kr{Course.n}@x.id", "password": PW, "major": "TKJ", "class_name": "XI TKJ"})
        self.assertEqual(st, 200); return c

    def answer(self, att, cid=1, wrong=False):
        """Pakai kunci dari bank soal + isi database untuk membaca urutan acak, seperti siswa yang tahu jawabannya."""
        db = sqlite3.connect(self.srv.db); db.row_factory = sqlite3.Row
        row = db.execute("SELECT * FROM course_attempts WHERE id=?", (att["attempt"],)).fetchone(); db.close()
        out = []
        for pos, qi in enumerate(json.loads(row["qids"])):
            q = CRS.COURSES[cid]["bank"][qi]; idx = list(range(4)); random.Random(f"{row['seed']}:{pos}").shuffle(idx)
            right = idx.index(q[4]); out.append((right + 1) % 4 if wrong else right)
        return out

    def finish_ch1(self, c):
        c.get("/api/student/course/chapter/1"); time.sleep(2.3); self.assertEqual(c.post("/api/student/course/chapter/1/read")[0], 200)

    def pass_chapter(self, c, n):
        st, q = c.post(f"/api/student/course/chapter/{n}/quiz"); self.assertEqual(st, 200)
        st, r = c.post(f"/api/student/course/attempt/{q['attempt']}/submit", {"answers": self.answer(q)}); self.assertEqual(st, 200); self.assertTrue(r["passed"]); return r

    def test_structure_is_valid(self):
        sourced = {k: v for k, v in CRS.COURSES.items() if len(v.get("sources") or []) >= 2}
        self.assertIn(1, sourced)
        # kursus tanpa sumber tidak boleh tampil ke siswa
        from metta import coursework as CW
        for k in CRS.COURSES: self.assertEqual(CW.has_course(k), k in sourced)
        self.assertEqual([m for m in CRS.validate() if not m.endswith("(judul, url https)")], [])
        for k in sourced:
            self.assertEqual([m for m in CRS.validate() if m.startswith(f"karier {k}:")], [])

    def test_no_plan_no_course_then_rules(self):
        c = self.student()
        self.assertFalse(c.get("/api/student/course")[1]["available"])
        self.assertEqual(c.get("/api/student/course/chapter/1")[0], 404)
        self.assertEqual(c.post("/api/student/plan", {"career_id": 1})[0], 200)
        st, s = c.get("/api/student/course"); self.assertTrue(s["available"]); self.assertEqual(s["done"], 0)
        self.assertEqual([x["locked"] for x in s["chapters"]], [False, True, True, True, True, True])
        self.assertEqual(c.get("/api/student/course/chapter/2")[0], 400)                    # terkunci
        self.assertEqual(c.get("/api/student/course/chapter/9")[0], 404)
        st, ch1 = c.get("/api/student/course/chapter/1"); self.assertEqual(st, 200)
        self.assertGreaterEqual(len(ch1["goals"]), 3); self.assertNotIn("correct", json.dumps(ch1)); self.assertEqual(set(ch1), {"n", "title", "career", "done", "sources", "goals", "sections", "read_wait"})
        self.assertEqual(c.post("/api/student/course/chapter/1/read")[0], 400)              # belum cukup lama membaca
        self.finish_ch1(c)
        self.assertEqual(c.get("/api/student/course/chapter/2")[0], 200)
        self.assertEqual(c.post("/api/student/course/chapter/3/quiz")[0], 400)             # bab 3 masih terkunci

    def test_quiz_rules_and_no_answer_leak(self):
        c = self.student(); c.post("/api/student/plan", {"career_id": 1}); self.finish_ch1(c)
        self.assertEqual(c.post("/api/student/course/chapter/2/note", {"note": "x"})[0], 405)   # catatan latihan sudah dihapus (rute tidak ada)
        st, q = c.post("/api/student/course/chapter/2/quiz"); self.assertEqual(st, 200)
        self.assertEqual(len(q["questions"]), CRS.QUIZ_N)
        raw = json.dumps(q); self.assertNotIn("correct", raw); self.assertNotIn("why", raw); self.assertNotIn("answer", raw.replace("attempt", ""))
        self.assertEqual(c.post(f"/api/student/course/attempt/{q['attempt']}/submit", {"answers": [0]})[0], 400)    # jumlah jawaban salah
        self.assertEqual(c.post(f"/api/student/course/attempt/{q['attempt']}/submit", {"answers": [9] * 6})[0], 400)
        st, r = c.post(f"/api/student/course/attempt/{q['attempt']}/submit", {"answers": self.answer(q, wrong=True)}); self.assertEqual(st, 200)
        self.assertFalse(r["passed"]); self.assertEqual(r["score"], 0)
        self.assertEqual(r["results"], [])                                  # gagal: tidak ada benar/salah, jawaban, atau penjelasan
        self.assertNotIn("weak_chapters", r)
        self.assertEqual(c.post(f"/api/student/course/attempt/{q['attempt']}/submit", {"answers": [0] * 6})[0], 400)  # sudah selesai
        self.assertEqual(c.post("/api/student/course/chapter/2/quiz")[0], 400)             # jeda setelah gagal
        time.sleep(2.3)
        st, q2 = c.post("/api/student/course/chapter/2/quiz"); self.assertEqual(st, 200); self.assertNotEqual(q2["attempt"], q["attempt"])
        st, r = c.post(f"/api/student/course/attempt/{q2['attempt']}/submit", {"answers": self.answer(q2)}); self.assertTrue(r["passed"]); self.assertEqual(r["score"], 6)
        self.assertTrue(all(x["correct"] for x in r["results"]))
        other = self.student(); other.post("/api/student/plan", {"career_id": 1})
        self.assertEqual(other.post(f"/api/student/course/attempt/{q2['attempt']}/submit", {"answers": [0] * 6})[0], 404)     # percobaan milik orang lain

    def test_full_course_final_exam_project_portfolio(self):
        c = self.student(); c.post("/api/student/plan", {"career_id": 1})
        before = c.get("/api/student/dashboard")[1]["readiness"]
        self.finish_ch1(c)
        for n in (2, 3, 4, 5): self.pass_chapter(c, n)
        self.assertEqual(c.get("/api/student/course")[1]["done"], 5)
        st, ex = c.post("/api/student/course/chapter/6/quiz"); self.assertEqual(st, 200); self.assertEqual(len(ex["questions"]), CRS.FINAL_N)
        st, r = c.post(f"/api/student/course/attempt/{ex['attempt']}/submit", {"answers": self.answer(ex, wrong=True)}); self.assertFalse(r["passed"])
        self.assertEqual(r["results"], []); self.assertTrue(r["weak_chapters"])             # ujian akhir gagal tidak membuka jawaban
        time.sleep(2.3)
        st, ex = c.post("/api/student/course/chapter/6/quiz")
        st, r = c.post(f"/api/student/course/attempt/{ex['attempt']}/submit", {"answers": self.answer(ex)}); self.assertTrue(r["passed"])
        self.assertEqual(c.get("/api/student/course")[1]["done"], 5)                       # belum selesai: proyek belum diverifikasi
        # proyek tidak lengkap ditolak
        st, p = c.post("/api/student/projects", {"title": "Jaringan kantor kecil", "description": "Proyek akhir", "skill_ids": []}); self.assertEqual(st, 200, p)
        self.assertEqual(c.post("/api/student/course/project", {"project_id": p["id"]})[0], 400)
        self.assertEqual(c.post("/api/student/course/project", {"project_id": 99999})[0], 404)
        st, p = c.post("/api/student/projects", {"title": "Jaringan kantor kecil lengkap", "description": "Proyek akhir", "skill_ids": [],
              "problem": "Kantor dengan 30 perangkat belum punya pembagian jaringan dan sering bentrok.", "solution": "Membagi jaringan menjadi tiga VLAN dengan routing, DHCP, NAT, dan aturan firewall.",
              "result": "Semua pengujian ping lulus dan jaringan Tamu terisolasi.", "repo_url": "https://example.com/proyek", "link": ""}); self.assertEqual(st, 200, p)
        self.assertEqual(c.post("/api/student/course/project", {"project_id": p["id"]})[0], 200)
        # guru melihat kriteria dan memverifikasi
        t = Client(self.srv.base); t.s.headers["X-Lang"] = "en"; self.assertEqual(t.login(*TE)[0], 200)
        items = t.get("/api/teacher/validation")[1]["items"]; mine = [i for i in items if i["id"] == p["id"]][0]
        self.assertGreaterEqual(len(mine["course"]["criteria"]), 6)
        self.assertEqual(t.post(f"/api/teacher/projects/{p['id']}/review", {"decision": "VERIFIED", "note": "Bagus"})[0], 200)
        st, s = c.get("/api/student/course"); self.assertEqual(s["done"], 6)
        after = c.get("/api/student/dashboard")[1]["readiness"]; self.assertGreater(after, before)
        pf = c.get("/api/student/portfolio")[1]; self.assertEqual(pf["courses"][0]["career"], "Network Engineer"); self.assertGreaterEqual(pf["courses"][0]["exam_percent"], 75)
        c.put("/api/student/portfolio/share", {"visibility": "LINK", "new_link": True, "headline": ""})
        slug = c.get("/api/student/portfolio/extras")[1]["share"]["slug"]
        pub = Client(self.srv.base).get(f"/api/public/portfolio/{slug}")[1]; self.assertEqual(pub["courses"][0]["career"], "Network Engineer")
        self.assertNotIn("note", json.dumps(pub["courses"]))

    def test_roles_cannot_use_student_course(self):
        t = Client(self.srv.base); t.login(*TE)
        for path in ("/api/student/course", "/api/student/course/chapter/1"): self.assertEqual(t.get(path)[0], 403)
        self.assertEqual(Client(self.srv.base).get("/api/student/course")[0], 401)
        self.assertEqual(t.post("/api/student/course/chapter/2/quiz")[0], 403)


if __name__ == "__main__":
    unittest.main()
