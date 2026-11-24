"""Tes tempat magang yang diajukan siswa: formulir, validasi tautan, antrean guru, hak akses, dan notifikasi.

Jalankan:  python -m unittest tests.test_company_proposal -v
"""
import unittest
from .support import Server, Client

PW = "Kopi-Susu-Enak-77"
TE = ("teacher@metta.sch", "Teacher#2026!"); AD = ("admin@metta.sch", "Admin#2026!")
ABOUT = "Toko komputer yang menjual laptop, aksesoris, dan menerima servis perangkat untuk pelanggan umum."


def form(name, **kw):
    d = {"name": name, "address": "Jl. Contoh No. 12, Tampan, Pekanbaru", "sector": "Toko komputer", "about": ABOUT,
         "tasks": "Membantu servis dan mencatat stok", "phone": "0812-3456-7890", "source": "Saya datang langsung dan bicara dengan pemilik"}
    d.update(kw); return d


class Proposal(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.srv = Server(8801, METTA_SEED_DEMO=1, METTA_REGISTER_LIMIT=500).start()
    @classmethod
    def tearDownClass(cls): cls.srv.stop()

    def student(self, tag):
        c = Client(self.srv.base); c.s.headers["X-Lang"] = "en"
        st, _ = c.post("/api/auth/register", {"name": "Siswa " + tag, "email": tag + "@x.id", "password": PW, "major": "TKJ", "class_name": "XI TKJ"}); self.assertEqual(st, 200); return c

    def staff(self, cred):
        c = Client(self.srv.base); c.s.headers["X-Lang"] = "en"; self.assertEqual(c.login(*cred, "")[0], 200); return c

    def names(self, c): return {x["name"]: x for x in c.get("/api/companies")[1]["items"]}

    def test_search_links_for_every_company(self):
        s = self.student("lnk"); items = s.get("/api/companies")[1]["items"]; self.assertGreater(len(items), 50)
        for x in items[:60]:
            for k in ("google_url", "ig_search_url", "maps_url"): self.assertTrue(x[k].startswith("https://"), (x["name"], k))
            self.assertIn("instagram.com", x["ig_search_url"])

    def test_full_flow_approve(self):
        a, b, t = self.student("fa"), self.student("fb"), self.staff(TE)
        st, r = a.post("/api/student/companies", form("Toko Uji Maju", instagram="@tokoujimaju", website="tokoujimaju.id")); self.assertEqual(st, 200); cid = r["id"]
        mine = self.names(a)["Toko Uji Maju"]
        self.assertEqual(mine["status"], "pending"); self.assertFalse(mine["verified"]); self.assertTrue(mine["mine"])
        self.assertEqual(mine["instagram_url"], "https://www.instagram.com/tokoujimaju/"); self.assertEqual(mine["website"], "https://tokoujimaju.id")
        self.assertNotIn("Toko Uji Maju", self.names(b))                          # siswa lain belum melihatnya
        self.assertNotIn("Toko Uji Maju", self.names(t))                          # daftar umum guru juga belum
        q = t.get("/api/teacher/company-submissions")[1]; self.assertGreaterEqual(q["pending"], 1)
        item = [x for x in q["items"] if x["id"] == cid][0]; self.assertIn("Siswa fa", item["student"])
        self.assertEqual(a.put("/api/student/internship", {"class_name": "XI TKJ", "company_ids": [cid], "purposes": ["belajar"]})[0], 200)   # pemilik boleh memilihnya
        self.assertEqual(b.put("/api/student/internship", {"class_name": "XI TKJ", "company_ids": [cid]})[0], 404)                           # siswa lain tidak
        self.assertEqual(t.put(f"/api/teacher/company-submissions/{cid}", {"decision": "approve", "address": "Jl. Terkoreksi 5, Pekanbaru"})[0], 200)
        ok = self.names(b)["Toko Uji Maju"]; self.assertTrue(ok["verified"]); self.assertEqual(ok["status"], "approved"); self.assertEqual(ok["address"], "Jl. Terkoreksi 5, Pekanbaru")
        self.assertIn("Diverifikasi guru", ok["source"])
        self.assertEqual(b.put("/api/student/internship", {"class_name": "XI TKJ", "company_ids": [cid]})[0], 200)
        texts = [n["text"] for n in a.get("/api/student/dashboard")[1]["notifications"]]; self.assertTrue(any("Toko Uji Maju" in x for x in texts))
        self.assertEqual(a.delete(f"/api/student/companies/{cid}")[0], 403)                 # yang sudah disetujui tidak bisa dihapus siswa
        self.assertEqual(t.put(f"/api/teacher/company-submissions/{cid}", {"decision": "approve"})[0], 404)   # tidak bisa disetujui dua kali

    def test_reject_needs_reason_and_clears_choice(self):
        a, t = self.student("ra"), self.staff(TE)
        cid = a.post("/api/student/companies", form("Toko Tolak Dulu", instagram="tokotolak"))[1]["id"]
        a.put("/api/student/internship", {"class_name": "XI TKJ", "company_ids": [cid]})
        self.assertEqual(t.put(f"/api/teacher/company-submissions/{cid}", {"decision": "reject", "note": "x"})[0], 400)
        self.assertEqual(t.put(f"/api/teacher/company-submissions/{cid}", {"decision": "reject", "note": "Nomor telepon tidak bisa dihubungi"})[0], 200)
        me = self.names(a)["Toko Tolak Dulu"]; self.assertEqual(me["status"], "rejected"); self.assertIn("telepon", me["review_note"])
        self.assertEqual(a.get("/api/student/internship")[1]["choices"], [])                # pilihan yang memakai tempat ini dikosongkan
        self.assertEqual(a.delete(f"/api/student/companies/{cid}")[0], 200)                 # siswa boleh menghapus ajuan yang ditolak
        self.assertNotIn("Toko Tolak Dulu", self.names(a))

    def test_validation(self):
        a = self.student("va")
        post = lambda **kw: a.post("/api/student/companies", form("Toko Valid " + str(len(kw)), **kw))[0]
        self.assertEqual(post(phone="", instagram="", website=""), 400)                     # wajib ada satu cara menghubungi
        self.assertEqual(post(website="javascript:alert(1)"), 400)
        self.assertEqual(post(website="ftp://x.com"), 400)
        self.assertEqual(post(website="https://user:pw@x.com"), 400)
        self.assertEqual(post(website="tanpa titik"), 400)
        self.assertEqual(post(instagram="https://evil.com/akun"), 400)
        self.assertEqual(post(instagram="nama dengan spasi"), 400)
        self.assertEqual(post(phone="abc"), 400)
        self.assertEqual(a.post("/api/student/companies", form("X"))[0], 422)               # nama terlalu pendek
        self.assertEqual(a.post("/api/student/companies", form("Toko Pendek", about="terlalu pendek"))[0], 422)
        st, r = a.post("/api/student/companies", form("Toko Skrip <script>", website="", phone="", instagram="https://www.instagram.com/akun.sah/?hl=id"))
        self.assertEqual(st, 200)
        self.assertEqual(self.names(a)["Toko Skrip <script>"]["instagram"], "akun.sah")     # teks disimpan apa adanya; tampilan memakai textContent

    def test_duplicate_and_limit(self):
        a = self.student("dl")
        self.assertEqual(a.post("/api/student/companies", form("Kota Computer"))[0], 409)   # sudah ada di daftar sekolah
        for i in range(3): self.assertEqual(a.post("/api/student/companies", form(f"Toko Antre {i}"))[0], 200)
        self.assertEqual(a.post("/api/student/companies", form("Toko Antre 9"))[0], 400)    # maksimal 3 menunggu

    def test_rate_limit_on_submit_delete_cycle(self):
        a = self.student("rl"); codes = []
        for i in range(12):
            st, r = a.post("/api/student/companies", form(f"Toko Siklus {i}"))
            codes.append(st)
            if st == 200: a.delete(f"/api/student/companies/{r['id']}")
        self.assertEqual(codes[:10], [200] * 10); self.assertIn(429, codes[10:])             # maksimal 10 ajuan per jam per siswa

    def test_access_control(self):
        a, b = self.student("ac"), self.student("bc"); t = self.staff(TE)
        cid = a.post("/api/student/companies", form("Toko Hak Akses"))[1]["id"]
        self.assertEqual(a.put(f"/api/teacher/company-submissions/{cid}", {"decision": "approve"})[0], 403)   # siswa tidak bisa menyetujui sendiri
        self.assertEqual(a.get("/api/teacher/company-submissions")[0], 403)
        self.assertEqual(b.delete(f"/api/student/companies/{cid}")[0], 404)                 # siswa lain tidak bisa menghapus
        self.assertEqual(t.post("/api/student/companies", form("Toko Guru"))[0], 403)       # hanya siswa yang mengajukan
        self.assertEqual(Client(self.srv.base).post("/api/student/companies", form("Anon"))[0], 401)
        self.assertEqual(self.staff(AD).get("/api/teacher/company-submissions")[0], 200)

    def test_teacher_links_on_existing_company(self):
        t, a = self.staff(TE), self.student("tl")
        un = [c for c in t.get("/api/companies")[1]["items"] if not c["verified"]][0]
        self.assertEqual(t.put(f"/api/teacher/companies/{un['id']}", {"address": "Jl. Baru 9, Pekanbaru", "source": "Telepon ke pemilik", "instagram": "@akunresmi", "phone": "0761-123456", "website": "javascript:x"})[0], 400)
        self.assertEqual(t.put(f"/api/teacher/companies/{un['id']}", {"address": "Jl. Baru 9, Pekanbaru", "source": "Telepon ke pemilik", "instagram": "@akunresmi", "phone": "0761-123456"})[0], 200)
        after = [c for c in a.get("/api/companies")[1]["items"] if c["id"] == un["id"]][0]
        self.assertEqual(after["instagram_url"], "https://www.instagram.com/akunresmi/"); self.assertEqual(after["phone"], "0761-123456")


if __name__ == "__main__":
    unittest.main()
