"""Tes alur belajar untuk SETIAP kursus yang punya sumber: rencana karier, bab 1-5, ujian akhir (gagal lalu lulus), proyek, dan verifikasi guru."""
import json, random, sqlite3, time, unittest
from .support import Server, Client, DEMO
from metta import course as CRS

PW = "Kopi-Susu-Enak-77"
NOTE = "Saya mencoba semua latihan di simulator dan mencatat hasil setiap langkahnya dengan teliti."
TE = DEMO["teacher"]


class EveryCourse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = Server(8811, METTA_SEED_DEMO=1, METTA_REGISTER_LIMIT=500, METTA_COURSE_READ_SEC=2, METTA_COURSE_COOLDOWN=2).start()
        cls.n = 0

    @classmethod
    def tearDownClass(cls):
        cls.srv.stop()

    def student(self):
        EveryCourse.n += 1
        c = Client(self.srv.base); c.s.headers["X-Lang"] = "en"
        st, _ = c.post("/api/auth/register", {"name": "Siswa Kursus", "email": f"ke{EveryCourse.n}@x.id", "password": PW, "major": "TKJ", "class_name": "XI TKJ"})
        self.assertEqual(st, 200); return c

    def answer(self, att, cid, wrong=False):
        db = sqlite3.connect(self.srv.db); db.row_factory = sqlite3.Row
        row = db.execute("SELECT * FROM course_attempts WHERE id=?", (att["attempt"],)).fetchone(); db.close()
        out = []
        for pos, qi in enumerate(json.loads(row["qids"])):
            q = CRS.COURSES[cid]["bank"][qi]; idx = list(range(4)); random.Random(f"{row['seed']}:{pos}").shuffle(idx)
            right = idx.index(q[4]); out.append((right + 1) % 4 if wrong else right)
        return out

    def run_course(self, cid):
        c = self.student()
        st, _ = c.post("/api/student/plan", {"career_id": cid}); self.assertEqual(st, 200, "rencana karier gagal")
        st, ch1 = c.get("/api/student/course/chapter/1"); self.assertEqual(st, 200)
        self.assertNotIn("correct", json.dumps(ch1))
        time.sleep(2.3); self.assertEqual(c.post("/api/student/course/chapter/1/read")[0], 200, "bab 1 gagal ditandai baca")
        for n in (2, 3, 4, 5):
            st, q = c.post(f"/api/student/course/chapter/{n}/quiz"); self.assertEqual(st, 200, f"kuis bab {n} gagal dibuka: {q}")
            st, r = c.post(f"/api/student/course/attempt/{q['attempt']}/submit", {"answers": self.answer(q, cid)}); self.assertEqual(st, 200, f"kirim kuis bab {n}")
            self.assertTrue(r["passed"], f"bab {n} tidak lulus dengan jawaban benar")
        self.assertEqual(c.get("/api/student/course")[1]["done"], 5)
        st, ex = c.post("/api/student/course/chapter/6/quiz"); self.assertEqual(st, 200, f"ujian akhir gagal dibuka: {ex}")
        self.assertEqual(len(ex["questions"]), CRS.FINAL_N)
        st, r = c.post(f"/api/student/course/attempt/{ex['attempt']}/submit", {"answers": self.answer(ex, cid, wrong=True)}); self.assertFalse(r["passed"])
        time.sleep(2.3)
        st, ex = c.post("/api/student/course/chapter/6/quiz"); self.assertEqual(st, 200)
        st, r = c.post(f"/api/student/course/attempt/{ex['attempt']}/submit", {"answers": self.answer(ex, cid)}); self.assertTrue(r["passed"], "ujian akhir tidak lulus")
        st, p = c.post("/api/student/projects", {"title": "Proyek kursus " + str(cid), "description": "Proyek akhir", "skill_ids": [],
              "problem": "Masalah rekaan yang dijelaskan dengan jelas untuk latihan proyek kursus ini.",
              "solution": "Solusi rekaan yang menjelaskan langkah kerja yang dipakai untuk menyelesaikan proyek.",
              "result": "Hasil rekaan yang dapat diperiksa guru dengan bukti yang jelas.", "repo_url": "https://example.com/proyek", "link": ""})
        self.assertEqual(st, 200, p)
        self.assertEqual(c.post("/api/student/course/project", {"project_id": p["id"]})[0], 200, "proyek gagal dikirim ke bab 6")
        t = Client(self.srv.base); t.s.headers["X-Lang"] = "en"; self.assertEqual(t.login(*TE)[0], 200)
        mine = [i for i in t.get("/api/teacher/validation")[1]["items"] if i["id"] == p["id"]]
        self.assertEqual(len(mine), 1, "proyek tidak muncul di antrean validasi guru")
        self.assertGreaterEqual(len(mine[0]["course"]["criteria"]), 6)
        self.assertEqual(t.post(f"/api/teacher/projects/{p['id']}/review", {"decision": "VERIFIED", "note": "Bagus"})[0], 200)
        self.assertEqual(c.get("/api/student/course")[1]["done"], 6, "kursus belum selesai setelah proyek diverifikasi")

    def test_every_course_runs_end_to_end(self):
        for cid in sorted(CRS.COURSES):
            if not CRS.COURSES[cid].get("sources") or len(CRS.COURSES[cid]["sources"]) < 2:
                continue
            with self.subTest(career=cid, name=CRS.COURSES[cid]["name"]):
                self.run_course(cid)
