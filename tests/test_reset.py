"""Tes fitur reset password oleh admin.

Alur yang diuji: pengguna lupa password → admin membuatkan password sementara → sesi lama
pengguna diputus → pengguna masuk dengan password sementara → wajib menggantinya → setelah
diganti, tanda wajib ganti hilang dan password sementara tidak bisa dipakai lagi.

Setiap tes memakai akun sekali pakai yang dibuat admin, supaya tes tidak saling mengganggu dan
akun demo tidak ikut berubah.

Jalankan:  python -m unittest tests.test_reset -v
"""
import unittest

from .support import Server, Client, DEMO

PORT = 8791
PW_AWAL = "Kopi-Susu-Enak-77"


class ResetPassword(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = Server(PORT, METTA_SEED_DEMO=1, METTA_REGISTER_LIMIT=500).start()
        cls.nomor = 0

    @classmethod
    def tearDownClass(cls):
        cls.srv.stop()

    def admin(self):
        c = Client(self.srv.base)
        self.assertEqual(c.login(*DEMO["admin"])[0], 200, "admin gagal masuk")
        return c

    def akun_baru(self, admin, role="student"):
        """Buat satu akun sekali pakai lewat admin; kembalikan (id, email)."""
        ResetPassword.nomor += 1
        email = f"uji{ResetPassword.nomor}@metta.sch"
        body = {"email": email, "name": f"Uji Coba {ResetPassword.nomor}", "role": role, "password": PW_AWAL}
        if role == "student": body.update({"major": "TKJ", "class_name": "11 TKJ 1"})
        code, out = admin.post("/api/admin/users", body)
        self.assertEqual(code, 200, f"gagal membuat akun uji: {out}")
        return out["id"], email

    # ---------- alur utama ----------
    def test_full_reset_flow(self):
        admin = self.admin()
        uid, email = self.akun_baru(admin)

        lama = Client(self.srv.base)                      # pengguna sedang masuk di perangkat lain
        self.assertEqual(lama.login(email, PW_AWAL)[0], 200)
        self.assertEqual(lama.get("/api/me")[0], 200)

        code, out = admin.post(f"/api/admin/users/{uid}/reset-password")
        self.assertEqual(code, 200, "admin tidak bisa mereset password")
        temp = out["temp_password"]
        self.assertEqual(out["email"], email)
        self.assertGreaterEqual(len(temp), 12, "password sementara terlalu pendek")

        self.assertEqual(lama.get("/api/me")[0], 401, "sesi lama harus ikut diputus")
        self.assertEqual(Client(self.srv.base).login(email, PW_AWAL)[0], 401,
                         "password lama seharusnya sudah tidak berlaku")

        pengguna = Client(self.srv.base)
        code, me = pengguna.login(email, temp)
        self.assertEqual(code, 200, "password sementara tidak bisa dipakai masuk")
        self.assertTrue(me["must_change_password"], "pengguna harus ditandai wajib ganti password")

        baru = "Jalan-Kaki-Pagi-91"
        self.assertEqual(pengguna.post("/api/me/password", {"current": temp, "new": baru})[0], 200,
                         "pengguna tidak bisa mengganti password sementara")

        code, me = pengguna.get("/api/me")
        self.assertEqual(code, 200)
        self.assertFalse(me["must_change_password"], "tanda wajib ganti harus hilang setelah diganti")

        self.assertEqual(Client(self.srv.base).login(email, temp)[0], 401,
                         "password sementara masih bisa dipakai setelah diganti")
        self.assertEqual(Client(self.srv.base).login(email, baru)[0], 200)

    def test_reset_works_for_teacher_too(self):
        admin = self.admin()
        uid, email = self.akun_baru(admin, "teacher")
        code, out = admin.post(f"/api/admin/users/{uid}/reset-password")
        self.assertEqual(code, 200)
        # guru wajib password minimal 12 karakter, jadi password sementara harus lolos aturan itu
        c = Client(self.srv.base)
        code, me = c.login(email, out["temp_password"])
        self.assertEqual(code, 200, "password sementara guru ditolak saat masuk")
        self.assertTrue(me["must_change_password"])

    # ---------- hak akses ----------
    def test_only_admin_may_reset(self):
        admin = self.admin()
        uid, _ = self.akun_baru(admin)
        for peran in ("student", "teacher"):
            c = Client(self.srv.base)
            self.assertEqual(c.login(*DEMO[peran])[0], 200)
            code, _ = c.post(f"/api/admin/users/{uid}/reset-password")
            self.assertIn(code, (401, 403), peran + " seharusnya tidak boleh mereset password orang lain")

    def test_anonymous_may_not_reset(self):
        code, _ = Client(self.srv.base).post("/api/admin/users/1/reset-password")
        self.assertIn(code, (401, 403), "tamu tidak boleh mereset password")

    def test_admin_cannot_reset_own_password(self):
        admin = self.admin()
        _, me = admin.get("/api/me")
        code, _ = admin.post(f"/api/admin/users/{me['id']}/reset-password")
        self.assertEqual(code, 400, "admin tidak boleh mengunci dirinya sendiri lewat reset")

    def test_unknown_user_gives_404(self):
        code, _ = self.admin().post("/api/admin/users/99999/reset-password")
        self.assertEqual(code, 404)

    # ---------- mutu password sementara ----------
    def test_temp_passwords_are_different_every_time(self):
        admin = self.admin()
        uid, _ = self.akun_baru(admin)
        hasil = {admin.post(f"/api/admin/users/{uid}/reset-password")[1]["temp_password"] for _ in range(6)}
        self.assertEqual(len(hasil), 6, "password sementara berulang, berarti tidak acak")
        for pw in hasil:
            self.assertGreaterEqual(len(pw), 12)
            self.assertNotIn(" ", pw, "password sementara tidak boleh memuat spasi")

    def test_reset_is_written_to_audit_log(self):
        admin = self.admin()
        uid, email = self.akun_baru(admin)
        admin.post(f"/api/admin/users/{uid}/reset-password")
        code, data = admin.get("/api/admin/audit")
        self.assertEqual(code, 200)
        rows = data["items"] if isinstance(data, dict) else data
        cocok = [r for r in rows if r.get("action") == "password_reset" and email in str(r.get("detail", ""))]
        self.assertTrue(cocok, "reset password harus tercatat di audit log beserta akunnya")

    def test_temp_password_is_not_stored_as_plain_text(self):
        """Password sementara hanya ditampilkan sekali; tidak boleh tersimpan apa adanya."""
        admin = self.admin()
        uid, _ = self.akun_baru(admin)
        temp = admin.post(f"/api/admin/users/{uid}/reset-password")[1]["temp_password"]
        code, data = admin.get("/api/admin/users")
        self.assertEqual(code, 200)
        self.assertNotIn(temp, str(data), "password sementara ikut terkirim di daftar pengguna")
        code, audit = admin.get("/api/admin/audit")
        self.assertNotIn(temp, str(audit), "password sementara tercatat di audit log")


if __name__ == "__main__":
    unittest.main()
