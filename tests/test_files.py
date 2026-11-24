"""Tes unggah file: hanya PDF/PNG/JPG asli, batas ukuran, hak akses, dan penghapusan."""
import base64, unittest
from .support import Server, Client, DEMO

PW = "Kopi-Susu-Enak-77"
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
b64 = lambda b: base64.b64encode(b).decode()


class Files(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = Server(8795, METTA_SEED_DEMO=1, METTA_REGISTER_LIMIT=500).start(); cls.n = 0

    @classmethod
    def tearDownClass(cls):
        cls.srv.stop()

    def student(self):
        Files.n += 1; c = Client(self.srv.base)
        self.assertEqual(c.post("/api/auth/register", {"name": "Siswa File", "email": f"f{Files.n}@x.id", "password": PW, "major": "TKJ", "class_name": "XI TKJ"})[0], 200)
        return c

    def cert(self, c):
        return c.post("/api/student/certificates", {"title": "Sertifikat Jaringan", "issuer": "Cisco"})[1]["new_id"]

    def up(self, c, ref, data, name="x.png", kind="certificate"):
        return c.post("/api/student/uploads", {"kind": kind, "ref_id": ref, "filename": name, "data": b64(data)})

    def test_upload_download_and_headers(self):
        c = self.student(); cid = self.cert(c)
        st, f = self.up(c, cid, PNG, "../../etc/passwd.png"); self.assertEqual(st, 200); self.assertEqual(f["name"], "passwd.png"); self.assertEqual(f["mime"], "image/png")
        r = c.s.get(self.srv.base + f"/api/files/{f['id']}"); self.assertEqual(r.status_code, 200); self.assertEqual(r.content, PNG)
        self.assertEqual(r.headers["Content-Type"], "image/png"); self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("sandbox", r.headers["Content-Security-Policy"])
        st, f2 = self.up(c, cid, PDF, "scan.pdf"); self.assertEqual(st, 200)
        r = c.s.get(self.srv.base + f"/api/files/{f2['id']}"); self.assertTrue(r.headers["Content-Disposition"].startswith("attachment"))
        _, ex = c.get("/api/student/portfolio/extras"); self.assertEqual(len(ex["certificates"][0]["files"]), 2)

    def test_rejects_fake_and_oversize_files(self):
        c = self.student(); cid = self.cert(c)
        self.assertEqual(self.up(c, cid, b"<html><script>alert(1)</script></html>", "evil.png")[0], 400)
        self.assertEqual(self.up(c, cid, b"MZ\x90\x00 fake exe", "a.pdf")[0], 400)
        self.assertEqual(self.up(c, cid, b"GIF89a....", "a.png")[0], 400)
        self.assertEqual(c.post("/api/student/uploads", {"kind": "certificate", "ref_id": cid, "filename": "a.png", "data": "!!!not base64!!!"})[0], 400)
        self.assertEqual(self.up(c, cid, PNG + b"\0" * (3 * 1024 * 1024), "big.png")[0], 413)
        self.assertEqual(self.up(c, cid, PNG + b"\0" * (5 * 1024 * 1024), "huge.png")[0], 413)
        self.assertEqual(c.post("/api/student/uploads", {"kind": "../x", "ref_id": cid, "filename": "a.png", "data": b64(PNG)})[0], 422)

    def test_access_control_and_limits(self):
        a, b = self.student(), self.student(); cid = self.cert(a)
        st, f = self.up(a, cid, PNG)
        self.assertEqual(self.up(b, cid, PNG)[0], 404)                         # tidak bisa menempel ke item orang lain
        self.assertEqual(b.get(f"/api/files/{f['id']}")[0], 404)               # tidak bisa membuka file orang lain
        self.assertEqual(b.delete(f"/api/student/uploads/{f['id']}")[0], 404)
        self.assertEqual(Client(self.srv.base).get(f"/api/files/{f['id']}")[0], 401)
        t = Client(self.srv.base); t.login(*DEMO["teacher"]); self.assertEqual(t.get(f"/api/files/{f['id']}")[0], 200)
        self.assertEqual(t.post("/api/student/uploads", {"kind": "certificate", "ref_id": cid, "filename": "a.png", "data": b64(PNG)})[0], 403)
        self.up(a, cid, PNG); self.up(a, cid, PNG)
        self.assertEqual(self.up(a, cid, PNG)[0], 400)                         # maks 3 per item

    def test_never_in_public_portfolio_and_removed_with_item(self):
        c = self.student(); cid = self.cert(c); st, f = self.up(c, cid, PNG)
        _, sh = c.put("/api/student/portfolio/share", {"visibility": "PUBLIC"})
        _, pub = Client(self.srv.base).get("/api/public/portfolio/" + sh["slug"]); self.assertNotIn("files", str(pub)); self.assertNotIn(str(f["id"]) + "/", str(pub))
        self.assertEqual(c.delete(f"/api/student/certificates/{cid}")[0], 200)
        self.assertEqual(c.get(f"/api/files/{f['id']}")[0], 404)

    def test_project_files_and_fields(self):
        c = self.student()
        st, p = c.post("/api/student/projects", {"title": "Jaringan Lab", "description": "x", "problem": "Lab lambat", "solution": "Pasang switch", "result": "Lebih cepat",
                                                  "technology": "Mikrotik", "repo_url": "https://github.com/a/b"}); self.assertEqual(st, 200); self.assertEqual(p["problem"], "Lab lambat")
        self.assertEqual(c.post("/api/student/projects", {"title": "Jaringan Lab", "demo_url": "javascript:alert(1)"})[0], 400)
        st, f = self.up(c, p["id"], PDF, "laporan.pdf", kind="project"); self.assertEqual(st, 200)
        self.assertEqual(c.get("/api/student/projects")[1]["items"][0]["files"][0]["name"], "laporan.pdf")
        t = Client(self.srv.base); t.login(*DEMO["teacher"])
        self.assertTrue(any(x["files"] for x in t.get("/api/teacher/projects")[1]["items"] if x["id"] == p["id"]))


if __name__ == "__main__":
    unittest.main()
