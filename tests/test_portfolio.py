"""Tes portfolio: berbagi lewat tautan, prestasi, sertifikat, dan verifikasi guru.

Jalankan:  python -m unittest tests.test_portfolio -v
"""
import unittest
from .support import Server, Client, DEMO

PW = "Kopi-Susu-Enak-77"


class Portfolio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = Server(8793, METTA_SEED_DEMO=1, METTA_REGISTER_LIMIT=500).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.stop()

    def student(self, tag):
        c = Client(self.srv.base)
        st, _ = c.post("/api/auth/register", {"name": "Siswa " + tag, "email": tag + "@x.id", "password": PW, "major": "TKJ", "class_name": "XI TKJ"})
        self.assertEqual(st, 200)
        return c

    def teacher(self):
        c = Client(self.srv.base); self.assertEqual(c.login(*DEMO["teacher"], "teacher")[0], 200); return c

    def anon(self):
        return Client(self.srv.base)

    def test_private_by_default(self):
        s = self.student("pf1")
        st, d = s.get("/api/student/portfolio/extras")
        self.assertEqual((st, d["share"]["visibility"], d["share"]["slug"]), (200, "PRIVATE", None))

    def test_share_link_flow_and_privacy(self):
        s = self.student("pf2")
        st, sh = s.put("/api/student/portfolio/share", {"visibility": "LINK", "headline": "Calon admin jaringan"})
        self.assertEqual(st, 200); slug = sh["slug"]
        self.assertGreaterEqual(len(slug), 12)
        st, pub = self.anon().get("/api/public/portfolio/" + slug)           # tanpa login
        self.assertEqual(st, 200)
        self.assertEqual(pub["name"], "Siswa pf2"); self.assertEqual(pub["headline"], "Calon admin jaringan")
        text = str(pub).lower()
        for secret in ("pf2@x.id", "email", "password", "teacher_note", "user_id"):
            self.assertNotIn(secret, text, "halaman publik membocorkan " + secret)
        # kembali ke PRIVATE: tautan mati
        s.put("/api/student/portfolio/share", {"visibility": "PRIVATE"})
        self.assertEqual(self.anon().get("/api/public/portfolio/" + slug)[0], 404)
        # aktifkan lagi dengan tautan baru: tautan lama tetap mati
        st, sh2 = s.put("/api/student/portfolio/share", {"visibility": "PUBLIC", "new_link": True})
        self.assertNotEqual(sh2["slug"], slug)
        self.assertEqual(self.anon().get("/api/public/portfolio/" + slug)[0], 404)
        self.assertEqual(self.anon().get("/api/public/portfolio/" + sh2["slug"])[0], 200)

    def test_only_verified_projects_are_public(self):
        s = self.student("pf3")
        s.post("/api/student/projects", {"title": "Belum diverifikasi", "description": "x", "link": "https://e.com", "skill_ids": []})
        slug = s.put("/api/student/portfolio/share", {"visibility": "LINK"})[1]["slug"]
        self.assertEqual(self.anon().get("/api/public/portfolio/" + slug)[1]["projects"], [])

    def test_achievements_and_certificates(self):
        s = self.student("pf4"); other = self.student("pf5")
        st, d = s.post("/api/student/achievements", {"title": "Juara 1 Lomba Jaringan", "issuer": "SMK", "achieved_on": "2026-05"})
        self.assertEqual(st, 200); aid = d["achievements"][0]["id"]
        self.assertFalse(d["achievements"][0]["verified"])
        st, d = s.post("/api/student/certificates", {"title": "CCNA", "issuer": "Cisco", "issued_on": "2026", "url": "https://example.com/c"})
        self.assertEqual(st, 200); cid = d["certificates"][0]["id"]
        # input jahat ditolak
        self.assertEqual(s.post("/api/student/achievements", {"title": "x"})[0], 422)
        self.assertEqual(s.post("/api/student/achievements", {"title": "Valid", "achieved_on": "kemarin"})[0], 422)
        self.assertEqual(s.post("/api/student/certificates", {"title": "Valid", "url": "javascript:alert(1)"})[0], 400)
        self.assertEqual(s.post("/api/student/certificates", {"title": "Valid", "url": "https://a b.com"})[0], 400)
        # siswa lain tidak bisa menghapus
        self.assertEqual(other.delete(f"/api/student/achievements/{aid}")[0], 404)
        self.assertEqual(other.delete(f"/api/student/certificates/{cid}")[0], 404)
        self.assertEqual(s.delete(f"/api/student/achievements/{aid}")[0], 200)

    def test_teacher_verifies_and_student_is_notified(self):
        s = self.student("pf6"); t = self.teacher()
        d = s.post("/api/student/achievements", {"title": "Juara 2", "issuer": "SMK"})[1]; aid = d["achievements"][0]["id"]
        sid = [x for x in t.get("/api/teacher/students")[1]["items"] if x["email"] == "pf6@x.id"][0]["id"]
        self.assertEqual(t.get(f"/api/teacher/students/{sid}/portfolio-items")[1]["achievements"][0]["verified"], False)
        self.assertEqual(t.post(f"/api/teacher/portfolio-items/achievements/{aid}/verify")[0], 200)
        self.assertTrue(s.get("/api/student/portfolio/extras")[1]["achievements"][0]["verified"])
        self.assertEqual(t.post("/api/teacher/portfolio-items/passwords/1/verify")[0], 404)       # jenis tidak dikenal
        # siswa tidak boleh memverifikasi dirinya sendiri
        self.assertEqual(s.post(f"/api/teacher/portfolio-items/achievements/{aid}/verify")[0], 403)
        notes = s.get("/api/notifications")[1]["items"]
        self.assertTrue(any("Juara 2" in n["text"] for n in notes))

    def test_script_in_title_is_returned_as_data_only(self):
        s = self.student("pf7")
        s.post("/api/student/achievements", {"title": "<script>alert(1)</script>", "issuer": "x"})
        slug = s.put("/api/student/portfolio/share", {"visibility": "LINK"})[1]["slug"]
        r = self.anon().s.get(self.srv.base + "/api/public/portfolio/" + slug)
        self.assertIn("application/json", r.headers["content-type"])           # bukan HTML: tidak pernah dieksekusi browser
        self.assertEqual(r.headers.get("x-content-type-options"), "nosniff")


class SlugGuessing(unittest.TestCase):
    """Server sendiri, karena pembatasan tebakan dihitung per alamat IP dan akan mengganggu tes lain."""
    @classmethod
    def setUpClass(cls):
        cls.srv = Server(8794, METTA_SEED_DEMO=1).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.stop()

    def test_bad_slug_and_rate_limit(self):
        a = Client(self.srv.base)
        for bad in ("x", "a" * 80, "no%20such%20slug%20123", "%00", "abc.def.ghi.jkl"):
            self.assertEqual(a.get("/api/public/portfolio/" + bad)[0], 404, bad)
        codes = [a.get("/api/public/portfolio/guess%02d_abcdefgh" % i)[0] for i in range(40)]
        self.assertIn(429, codes, "tebakan tautan yang salah harus dibatasi")


if __name__ == "__main__":
    unittest.main()
