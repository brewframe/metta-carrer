"""Tes alumni: tulis -> kirim -> moderasi admin -> dibaca siswa."""
import unittest
from .support import Server, Client

AL = ("alumni@metta.sch", "Alumni#2026!"); AD = ("admin@metta.sch", "Admin#2026!"); ST = ("student@metta.sch", "Student#2026!"); TE = ("teacher@metta.sch", "Teacher#2026!")
BODY = "Saya lulus dari SMK dan bekerja sebagai teknisi jaringan. Ini ceritanya secara singkat dan jujur."


class Alumni(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = Server(8798, METTA_SEED_DEMO=1).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.stop()

    def who(self, cred, role=""):
        c = Client(self.srv.base); c.s.headers["X-Lang"] = "en"; self.assertEqual(c.login(*cred, role)[0], 200); return c

    def test_flow(self):
        a, adm, s = self.who(AL, "alumni"), self.who(AD), self.who(ST)
        self.assertEqual(a.put("/api/alumni/profile", {"graduation_year": 2022, "major": "TKJ", "workplace": "PT Contoh", "job_title": "Network Technician", "bio": "Halo"})[0], 200)
        st, r = a.post("/api/alumni/content", {"kind": "CAREER_STORY", "title": "Dari TKJ ke teknisi jaringan", "body": BODY, "category": "Networking"}); self.assertEqual(st, 200); cid = r["id"]
        self.assertEqual(s.get("/api/alumni-stories")[1]["items"], [])                                     # draf tidak terlihat
        self.assertEqual(a.put(f"/api/alumni/content/{cid}", {"kind": "CAREER_STORY", "title": "Dari TKJ ke teknisi jaringan", "body": BODY, "submit": True})[0], 200)
        self.assertEqual(s.get("/api/alumni-stories")[1]["items"], [])                                     # menunggu moderasi: belum terlihat
        self.assertEqual(adm.get("/api/admin/content")[1]["pending"], 1)
        self.assertEqual(adm.post(f"/api/admin/content/{cid}/moderate", {"decision": "REJECTED", "note": ""})[0], 400)
        self.assertEqual(adm.post(f"/api/admin/content/{cid}/moderate", {"decision": "REJECTED", "note": "Tolong tambah bagian saran."})[0], 200)
        _, mine = a.get("/api/alumni/content"); self.assertEqual(mine["items"][0]["status"], "REJECTED"); self.assertIn("saran", mine["items"][0]["moderation_note"])
        self.assertEqual(a.put(f"/api/alumni/content/{cid}", {"kind": "CAREER_STORY", "title": "Dari TKJ ke teknisi jaringan", "body": BODY + " Saran saya: rajin latihan.", "submit": True})[0], 200)
        self.assertEqual(adm.post(f"/api/admin/content/{cid}/moderate", {"decision": "PUBLISHED"})[0], 200)
        _, ps = s.get("/api/alumni-stories"); self.assertEqual(len(ps["items"]), 1); it = ps["items"][0]
        self.assertEqual((it["author"], it["job_title"], it["workplace"]), ("Alumni Demo", "Network Technician", "PT Contoh")); self.assertNotIn("email", str(it))
        self.assertEqual(len(s.get("/api/alumni-stories?q=teknisi")[1]["items"]), 1); self.assertEqual(s.get("/api/alumni-stories?kind=TIPS")[1]["items"], [])
        self.assertEqual(a.put(f"/api/alumni/content/{cid}", {"kind": "TIPS", "title": "Judul baru lagi", "body": BODY})[0], 400)      # terbit tidak bisa diedit
        self.assertEqual(a.delete(f"/api/alumni/content/{cid}")[0], 400)
        self.assertTrue(any("diterbitkan" in n["text"] or "published" in n["text"] for n in a.get("/api/notifications")[1]["items"]))
        self.assertEqual(adm.post(f"/api/admin/content/{cid}/moderate", {"decision": "REJECTED", "note": "Ditarik sementara."})[0], 200)
        self.assertEqual(s.get("/api/alumni-stories")[1]["items"], [])

    def test_writer_page_can_load_careers(self):
        # halaman 'Write a story' memuat daftar karier; dulu ditolak 403 untuk alumni
        a = self.who(AL, "alumni"); st, r = a.get("/api/careers"); self.assertEqual(st, 200); self.assertTrue(r["items"])

    def test_permissions_and_validation(self):
        a, s, t = self.who(AL, "alumni"), self.who(ST), self.who(TE)
        self.assertEqual(s.post("/api/alumni/content", {"kind": "TIPS", "title": "Tips belajar", "body": BODY})[0], 403)
        self.assertEqual(t.get("/api/admin/content")[0], 403); self.assertEqual(a.get("/api/admin/content")[0], 403); self.assertEqual(a.get("/api/alumni-stories")[0], 403)
        self.assertEqual(a.post("/api/alumni/content", {"kind": "NOPE", "title": "Tips belajar", "body": BODY})[0], 422)
        self.assertEqual(a.post("/api/alumni/content", {"kind": "TIPS", "title": "Tips", "body": "pendek"})[0], 422)
        self.assertEqual(a.post("/api/alumni/content", {"kind": "TIPS", "title": "Tips belajar", "body": BODY, "career_id": 99999})[0], 404)
        _, r = a.post("/api/alumni/content", {"kind": "TIPS", "title": "<script>alert(1)</script>", "body": BODY})
        b = self.who(AL, "alumni"); other = Client(self.srv.base); self.assertEqual(other.get("/api/alumni/content")[0], 401)
        adm = self.who(AD); adm.post("/api/admin/users", {"name": "Alumni Dua", "email": "al2@x.id", "role": "alumni", "password": "Sangat-Panjang-Rahasia-55"})
        a2 = Client(self.srv.base); a2.login("al2@x.id", "Sangat-Panjang-Rahasia-55"); self.assertEqual(a2.put(f"/api/alumni/content/{r['id']}", {"kind": "TIPS", "title": "Curi punya orang", "body": BODY})[0], 404)
        self.assertEqual(a2.delete(f"/api/alumni/content/{r['id']}")[0], 404)


if __name__ == "__main__":
    unittest.main()
