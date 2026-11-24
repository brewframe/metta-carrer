"""Tes alat operasional: pemeriksa kesiapan produksi, cadangan terverifikasi, pemulihan, hapus akun demo.

Jalankan:  python -m unittest tests.test_ops -v
"""
import os, shutil, sqlite3, tempfile, unittest
from unittest import mock


class Ops(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"METTA_DB": os.path.join(self.tmp, "m.db"), "METTA_BACKUP_DIR": os.path.join(self.tmp, "bk"), "METTA_SEED_DEMO": "1"}, clear=False)
        self.env.start()
        from metta.seed import seed; seed()
    def tearDown(self): self.env.stop(); shutil.rmtree(self.tmp, ignore_errors=True)

    def status(self, res, needle): return [s for s, t in res if needle in t]

    def test_preflight_flags_demo_and_missing_settings(self):
        from metta import preflight
        res = preflight.run()
        self.assertIn("GAGAL", self.status(res, "akun demo"))
        self.assertIn("GAGAL", self.status(res, "METTA_ENV"))
        self.assertIn("GAGAL", self.status(res, "METTA_REGISTER_CODE"))
        self.assertEqual(preflight.main([]), 1)

    def test_remove_demo_only_touches_known_passwords(self):
        from metta import preflight
        from metta.db import DB
        from metta.security import hash_password
        d = DB(); d.run("UPDATE users SET password_hash=? WHERE email='student@metta.sch'", hash_password("Sudah-Diganti-Aman-91")); d.commit(); d.close()
        d = DB()
        try: gone = preflight.remove_demo(d)
        finally: d.close()
        self.assertNotIn("student@metta.sch", gone)                      # password sudah diganti -> akun asli, tidak dihapus
        self.assertIn("admin@metta.sch", gone)
        d = DB()
        try:
            self.assertIsNotNone(d.one("SELECT 1 x FROM users WHERE email='student@metta.sch'"))
            self.assertIsNone(d.one("SELECT 1 x FROM users WHERE email='admin@metta.sch'"))
            self.assertTrue(d.one("SELECT 1 x FROM audit_log WHERE action='demo_removed'"))
        finally: d.close()

    def test_preflight_ok_when_configured(self):
        from metta import preflight
        from metta.db import DB
        from metta.security import hash_password
        d = DB(); preflight.remove_demo(d)
        d.run("INSERT INTO users(email,name,password_hash,role) VALUES('kepala@sekolah.sch.id','Kepala',?, 'admin')", hash_password("Kata-Sandi-Panjang-Aman-55")); d.commit(); d.close()
        with mock.patch.dict(os.environ, {"METTA_ENV": "production", "METTA_SECURE_COOKIE": "1", "METTA_ALLOWED_HOSTS": "metta.sekolah.sch.id", "METTA_REGISTER_CODE": "kode-rahasia-2026"}):
            os.environ.pop("METTA_SEED_DEMO", None)
            res = preflight.run()
        self.assertEqual([t for s, t in res if s == "GAGAL"], [])

    def test_backup_verified_and_restore(self):
        from metta import backup, restore
        from metta.db import DB
        backup.main(); bdir = os.environ["METTA_BACKUP_DIR"]
        files = [f for f in os.listdir(bdir) if f.endswith(".db")]; self.assertEqual(len(files), 1); self.assertTrue(os.path.exists(os.path.join(bdir, files[0] + ".sha256")))
        good = os.path.join(bdir, files[0])
        d = DB(); d.run("DELETE FROM users WHERE role='alumni'"); d.commit(); d.close()          # ubah database sesudah cadangan
        lama = restore.restore(good)
        self.assertTrue(os.path.exists(lama))                                                   # database sebelumnya disimpan
        d = DB()
        try: self.assertTrue(d.one("SELECT 1 x FROM users WHERE role='alumni'"))                   # alumni kembali
        finally: d.close()

    def test_restore_refuses_damaged_backup(self):
        from metta import backup, restore
        backup.main(); bdir = os.environ["METTA_BACKUP_DIR"]; f = [x for x in os.listdir(bdir) if x.endswith(".db")][0]; good = os.path.join(bdir, f)
        with open(good, "r+b") as fh: fh.seek(2000); fh.write(b"\x00\xff" * 50)                      # rusak, checksum tidak cocok
        with self.assertRaises(ValueError): restore.restore(good)
        junk = os.path.join(self.tmp, "junk.db"); open(junk, "wb").write(b"bukan database" * 100)
        with self.assertRaises(ValueError): restore.restore(junk)
        with self.assertRaises(ValueError): restore.restore(os.path.join(self.tmp, "tidak-ada.db"))
        self.assertTrue(os.path.exists(os.environ["METTA_DB"]))                                    # database asli tidak tersentuh

    def test_check_db_file_detects_problems(self):
        from metta.preflight import check_db_file
        p = os.path.join(self.tmp, "kosong.db"); sqlite3.connect(p).execute("CREATE TABLE x(a)").connection.close()
        self.assertTrue(any("users" in x for x in check_db_file(p)))
        self.assertEqual(check_db_file(os.environ["METTA_DB"]), [])


if __name__ == "__main__": unittest.main()
