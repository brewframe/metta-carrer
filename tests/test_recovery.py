"""Tes lupa password: permintaan -> persetujuan guru/admin -> kode sekali pakai -> password baru."""
import unittest
from .support import Server, Client, DEMO

PW = "Kopi-Susu-Enak-77"; NEW = "Mangga-Manis-Sekali-91"


class Recovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = Server(8796, METTA_SEED_DEMO=1, METTA_REGISTER_LIMIT=500).start(); cls.n = 0

    @classmethod
    def tearDownClass(cls):
        cls.srv.stop()

    def new_student(self):
        Recovery.n += 1; email = f"lp{Recovery.n}@x.id"; c = Client(self.srv.base)
        self.assertEqual(c.post("/api/auth/register", {"name": "Siswa Lupa", "email": email, "password": PW, "major": "TKJ", "class_name": "XI TKJ"})[0], 200)
        return email

    def staff(self, who):
        c = Client(self.srv.base); self.assertEqual(c.login(*DEMO[who])[0], 200); return c

    def req_id(self, staff, email):
        return next(x["id"] for x in staff.get("/api/staff/password-requests")[1]["items"] if x["email"] == email and x["status"] in ("PENDING", "APPROVED"))

    def test_full_flow_teacher_approves_student(self):
        email = self.new_student(); anon = Client(self.srv.base)
        self.assertEqual(anon.post("/api/auth/forgot", {"email": email})[0], 200)
        t = self.staff("teacher"); rid = self.req_id(t, email)
        st, r = t.post(f"/api/staff/password-requests/{rid}/approve"); self.assertEqual(st, 200); code = r["code"]; self.assertRegex(code, r"^[A-Z0-9]{4}-[A-Z0-9]{4}$")
        # sesi lama harus putus setelah reset
        old = Client(self.srv.base); old.login(email, PW); self.assertEqual(old.get("/api/me")[0], 200)
        self.assertEqual(anon.post("/api/auth/reset", {"email": email, "code": "AAAA-BBBB", "new_password": NEW})[0], 400)
        self.assertEqual(anon.post("/api/auth/reset", {"email": email, "code": code, "new_password": "123"})[0], 400)      # password lemah: kode belum terpakai
        st, _ = anon.post("/api/auth/reset", {"email": email, "code": code.lower(), "new_password": NEW}); self.assertEqual(st, 200)
        self.assertEqual(old.get("/api/me")[0], 401)
        self.assertEqual(Client(self.srv.base).login(email, PW)[0], 401)
        self.assertEqual(Client(self.srv.base).login(email, NEW)[0], 200)
        self.assertEqual(anon.post("/api/auth/reset", {"email": email, "code": code, "new_password": NEW + "x"})[0], 400)   # sekali pakai

    def test_unknown_email_looks_the_same_and_creates_nothing(self):
        anon = Client(self.srv.base)
        self.assertEqual(anon.post("/api/auth/forgot", {"email": "tidakada@x.id"}), (200, {"ok": True}))
        self.assertEqual(anon.post("/api/auth/reset", {"email": "tidakada@x.id", "code": "AAAA-BBBB", "new_password": NEW})[0], 400)
        a = self.staff("admin"); self.assertFalse(any(x["email"] == "tidakada@x.id" for x in a.get("/api/staff/password-requests")[1]["items"]))

    def test_code_dies_after_5_wrong_tries(self):
        email = self.new_student(); anon = Client(self.srv.base); anon.post("/api/auth/forgot", {"email": email})
        a = self.staff("admin"); rid = self.req_id(a, email); code = a.post(f"/api/staff/password-requests/{rid}/approve")[1]["code"]
        for _ in range(5): anon.post("/api/auth/reset", {"email": email, "code": "ZZZZ-ZZZZ", "new_password": NEW})
        self.assertEqual(anon.post("/api/auth/reset", {"email": email, "code": code, "new_password": NEW})[0], 400)

    def test_permissions(self):
        email = self.new_student(); Client(self.srv.base).post("/api/auth/forgot", {"email": email})
        t = self.staff("teacher"); rid = self.req_id(t, email)
        s = Client(self.srv.base); s.login(email, PW)
        self.assertEqual(s.get("/api/staff/password-requests")[0], 403); self.assertEqual(s.post(f"/api/staff/password-requests/{rid}/approve")[0], 403)
        # guru tidak boleh menangani admin; admin tidak boleh menyetujui permintaannya sendiri
        Client(self.srv.base).post("/api/auth/forgot", {"email": DEMO["admin"][0]}); Client(self.srv.base).post("/api/auth/forgot", {"email": DEMO["teacher"][0]})
        self.assertFalse(any(x["role"] != "student" for x in t.get("/api/staff/password-requests")[1]["items"]))
        a = self.staff("admin"); items = a.get("/api/staff/password-requests")[1]["items"]
        self.assertFalse(any(x["email"] == DEMO["admin"][0] for x in items)); self.assertTrue(any(x["email"] == DEMO["teacher"][0] for x in items))
        # permintaan ditolak tidak bisa dipakai
        self.assertEqual(t.post(f"/api/staff/password-requests/{rid}/reject")[0], 200)
        self.assertEqual(t.post(f"/api/staff/password-requests/{rid}/approve")[0], 400)


class RecoveryRate(unittest.TestCase):
    def test_rate_limit_on_forgot(self):
        srv = Server(8797, METTA_SEED_DEMO=1).start()
        try:
            anon = Client(srv.base); codes = [anon.post("/api/auth/forgot", {"email": f"spam{i}@x.id"})[0] for i in range(12)]
            self.assertIn(429, codes); self.assertEqual(codes[0], 200)
        finally:
            srv.stop()


if __name__ == "__main__":
    unittest.main()
