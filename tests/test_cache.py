"""Setelah update, browser tidak boleh memakai campuran file JS lama dan baru (contoh bug: "M.countdown is not a function")."""
import re, unittest
import requests
from tests.support import Server, NOPROXY


class CacheTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.srv = Server(8824).start()
    @classmethod
    def tearDownClass(cls): cls.srv.stop()

    def get(self, path, **kw): return requests.get(self.srv.base + path, proxies=NOPROXY, timeout=10, **kw)

    def test_every_script_and_stylesheet_is_versioned(self):
        html = self.get("/").text
        refs = re.findall(r'(?:src|href)="(/static/[^"]+\.(?:js|css)[^"]*)"', html)
        self.assertGreaterEqual(len(refs), 10)
        versions = {r.split("?v=")[1] if "?v=" in r else None for r in refs}
        self.assertEqual(len(versions), 1, refs); self.assertNotIn(None, versions)

    def test_pages_and_static_files_must_revalidate(self):
        for path in ("/", "/static/app.js", "/static/lang.js", "/static/app.css"):
            r = self.get(path); self.assertEqual(r.status_code, 200, path)
            self.assertEqual(r.headers.get("Cache-Control"), "no-cache", path)
        etag = self.get("/static/app.js").headers["ETag"]
        self.assertEqual(self.get("/static/app.js", headers={"If-None-Match": etag}).status_code, 304, "unchanged file must be a cheap 304")
        self.assertEqual(self.get("/api/health").headers.get("Cache-Control"), "no-store")

    def test_guard_loads_first(self):
        html = self.get("/").text
        first = re.findall(r'<script src="([^"]+)"', html)[0]
        self.assertTrue(first.startswith("/static/guard.js"), first)

    def test_stale_browser_is_told_to_clear_cache(self):
        r = self.get("/"); v = r.cookies.get("metta_v"); self.assertTrue(v)
        self.assertEqual(self.get("/api/health").headers.get("Clear-Site-Data"), '"cache"', "browser without the version cookie must clear its cache")
        self.assertIsNone(self.get("/api/health", cookies={"metta_v": v}).headers.get("Clear-Site-Data"), "up-to-date browser must keep its cache")
        self.assertEqual(self.get("/api/health", cookies={"metta_v": "old"}).headers.get("Clear-Site-Data"), '"cache"')


if __name__ == "__main__": unittest.main()
