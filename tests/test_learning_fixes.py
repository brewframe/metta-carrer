"""Regresi sistem belajar: progres tidak boleh hilang saat Career Plan disimpan ulang / diganti lalu kembali,
satu siswa hanya punya satu rencana aktif, dan langkah tugas yang sudah selesai tidak bisa diubah."""
import sqlite3, unittest
from tests.support import Server, Client
import metta.course as CRS

PW = "Belajar-Karier-2026!"


class LearningFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.srv = Server(8825).start()
    @classmethod
    def tearDownClass(cls): cls.srv.stop()

    def student(self, email):
        c = Client(self.srv.base)
        self.assertEqual(c.post("/api/auth/register", {"name": "Siswa Penguji", "email": email, "password": PW, "major": "TKJ", "class_name": "XI TKJ"})[0], 200)
        return c

    def finish_study(self, c, tid):
        d = c.get(f"/api/student/learn/{tid}")[1]
        for i in range(len(d["steps"])): self.assertEqual(c.post(f"/api/student/learn/{tid}/step", {"idx": i, "done": True})[0], 200)
        self.assertEqual(c.patch(f"/api/student/tasks/{tid}", {"status": "COMPLETED"})[0], 200)

    def test_courses_untouched(self):
        self.assertGreaterEqual(len(CRS.COURSES), 100); self.assertEqual(CRS.validate(), [])

    def test_progress_survives_resave_and_switch_back(self):
        c = self.student("progres@x.id")
        p1 = c.post("/api/student/plan", {"career_id": 1})[1]
        tid = next(t["id"] for m in p1["milestones"] for t in m["tasks"] if t["kind"] == "STUDY")
        self.finish_study(c, tid)
        again = c.post("/api/student/plan", {"career_id": 1})[1]                      # simpan ulang karier yang sama
        self.assertEqual(again["plan"]["id"], p1["plan"]["id"], "same career must keep the same plan")
        other = c.post("/api/student/plan", {"career_id": 2})[1]                      # ganti karier
        self.assertNotEqual(other["plan"]["id"], p1["plan"]["id"])
        back = c.post("/api/student/plan", {"career_id": 1})[1]                       # kembali ke karier lama
        self.assertEqual(back["plan"]["id"], p1["plan"]["id"], "old plan must be reactivated")
        done = [t for m in back["milestones"] for t in m["tasks"] if t["status"] == "COMPLETED"]
        self.assertEqual([t["id"] for t in done], [tid], "completed task must still be completed")

    def test_one_active_plan_per_student(self):
        c = self.student("satu@x.id"); c.post("/api/student/plan", {"career_id": 1}); c.post("/api/student/plan", {"career_id": 2}); c.post("/api/student/plan", {"career_id": 3})
        uid = c.get("/api/me")[1]["id"]
        db = sqlite3.connect(self.srv.db)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM plans WHERE user_id=? AND status='ACTIVE'", (uid,)).fetchone()[0], 1)
        with self.assertRaises(sqlite3.IntegrityError):     # database sendiri menolak rencana aktif kedua
            db.execute("UPDATE plans SET status='ACTIVE' WHERE user_id=?", (uid,)); db.commit()
        db.close()

    def test_completed_task_steps_locked(self):
        c = self.student("kunci@x.id"); p = c.post("/api/student/plan", {"career_id": 1})[1]
        tid = next(t["id"] for m in p["milestones"] for t in m["tasks"] if t["kind"] == "STUDY")
        self.finish_study(c, tid)
        self.assertEqual(c.post(f"/api/student/learn/{tid}/step", {"idx": 0, "done": False})[0], 400)
        self.assertTrue(all(s["done"] for s in c.get(f"/api/student/learn/{tid}")[1]["steps"]))

    def test_step_response_has_fresh_state(self):
        """Tampilan memperbarui status di tempat dari jawaban ini, jadi jawabannya harus memuat ready/status terbaru."""
        c = self.student("segar@x.id"); p = c.post("/api/student/plan", {"career_id": 1})[1]
        tid = next(t["id"] for m in p["milestones"] for t in m["tasks"] if t["kind"] == "STUDY")
        n = len(c.get(f"/api/student/learn/{tid}")[1]["steps"])
        for i in range(n):
            st, r = c.post(f"/api/student/learn/{tid}/step", {"idx": i, "done": True}); self.assertEqual(st, 200)
            self.assertEqual(r["ready"], i == n - 1); self.assertEqual(r["status"], "IN_PROGRESS")


if __name__ == "__main__": unittest.main()
