"""Tes tampilan: memastikan berkas statis tersaji benar dan halaman depan tidak kehilangan
bagiannya setelah ada perubahan CSS atau JavaScript.

Tes ini sengaja tidak memakai browser, supaya cepat dan bisa jalan di mana saja. Yang diperiksa:
berkas ada, tipe isinya benar, warna palet terpakai, dan bagian penting halaman depan masih tertulis
di dalam kode. Untuk memeriksa tampilan sebenarnya, buka web-nya di browser.

Jalankan:  python -m unittest tests.test_ui -v
"""
import os, re, socket, unittest

from .support import Server, Client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "metta", "static")

# Palet sekolah. Nilai di sini harus sama dengan yang ada di app.css.
PALETTE = {
    "teal-900": "#006D77",
    "teal-500": "#00AFB9",
    "orange": "#FF6B3D",
    "peach": "#FF9F68",
    "bg": "#F5F5F5",
    "ink": "#10282B",
}


PHOTOS = ("belajar", "tkj", "ak", "guru", "prestasi", "alumni")


def read(name):
    with open(os.path.join(STATIC, name), encoding="utf-8") as f:
        return f.read()


class Files(unittest.TestCase):
    """Berkas tampilan ada dan isinya masuk akal."""

    def test_static_files_exist(self):
        # start.js hanya satu baris pemanggil (M.start();), jadi batas ukurannya kecil.
        kecil = {"start.js": 5}
        for name in ("index.html", "app.css", "landing.css", "app.js", "i18n.js", "lang.js", "landing.js", "portfolio.js", "student.js", "staff.js", "start.js", "logo.png",
                     "fonts/poppins-500.woff", "fonts/poppins-700.woff", "brand/logo-mark.svg", "brand/logo-horizontal.svg", "brand/logo-horizontal-dark.svg",
                     "brand/logo-stacked.svg", "brand/logo-mark-32.png", "brand/logo-mark-192.png", "brand/community.png") + tuple("photos/%s.jpg" % n for n in PHOTOS):
            path = os.path.join(STATIC, name)
            self.assertTrue(os.path.isfile(path), name + " hilang dari metta/static")
            self.assertGreater(os.path.getsize(path), kecil.get(name, 100), name + " kosong")

    def test_photos_not_too_heavy(self):
        """Foto halaman depan harus ringan supaya cepat dibuka dengan data seluler."""
        for n in PHOTOS:
            size = os.path.getsize(os.path.join(STATIC, "photos", n + ".jpg"))
            self.assertLess(size, 250_000, "photos/%s.jpg lebih dari 250 KB, perkecil dulu" % n)

    def test_palette_defined_once(self):
        css = read("app.css")
        for name, hexcode in PALETTE.items():
            self.assertRegex(css, r"--" + name + r"\s*:\s*" + hexcode,
                             "warna --%s harus %s di app.css" % (name, hexcode))

    def test_no_leftover_old_palette(self):
        """Warna tema lama tidak boleh tertinggal."""
        css = read("app.css")
        for old in ("#F6F2EF", "#D9DFE3", "#B0C0CC", "#8EA39D", "#363E4F"):
            self.assertNotIn(old, css, "warna lama " + old + " masih ada di app.css")

    def test_css_braces_balanced(self):
        css = read("app.css")
        self.assertEqual(css.count("{"), css.count("}"), "kurung kurawal CSS tidak seimbang")

    def test_css_has_no_invalid_colour_token(self):
        """Nilai warna hex harus 3, 4, 6, atau 8 karakter.

        Yang diperiksa hanya nilai di dalam blok CSS (setelah tanda titik dua), bukan pemilih
        seperti #notifbtn yang juga diawali tanda pagar.
        """
        body = "\n".join(re.findall(r"\{([^{}]*)\}", read("app.css")))
        for token in re.findall(r"#[0-9A-Za-z]+", body):
            self.assertIn(len(token) - 1, (3, 4, 6, 8), "nilai warna tidak sah: " + token)
            self.assertRegex(token, r"^#[0-9A-Fa-f]+$", "nilai warna tidak sah: " + token)

    def test_motion_can_be_switched_off(self):
        """Pengguna yang mematikan animasi di perangkatnya harus dihormati."""
        self.assertIn("prefers-reduced-motion", read("app.css"))

    def test_landing_parts_present(self):
        """Bagian halaman depan masih dibuat oleh landing.js."""
        js = read("landing.js")
        for part in ("stairs()", "portal", "vnotch", "sticky-cta", "footer()", "langSwitch", "/api/public/stats", "metta-motion", "Turn off animations"):
            self.assertIn(part, js, "halaman depan kehilangan bagian: " + part)
        css = read("landing.css")
        for part in ("portal-mask", "perspective", "position:sticky", ".lp.static"):
            self.assertIn(part, css, "landing.css kehilangan: " + part)

    def test_landing_photos_have_alt_text(self):
        js = read("landing.js")
        for n in PHOTOS:
            m = re.search(r'"%s",\s*"([^"]{10,})"' % n, js)
            self.assertTrue(m, "foto %s tidak dipakai di halaman depan" % n)
            self.assertGreaterEqual(len(m.group(1)), 10, "teks alt foto %s terlalu pendek" % n)

    def test_landing_css_braces_balanced(self):
        css = read("landing.css")
        self.assertEqual(css.count("{"), css.count("}"))

    def test_landing_uses_only_palette_colours(self):
        """Warna hex di landing.css harus dari palet, turunannya, atau netral (putih/hitam bayangan)."""
        allowed = {"#006D77", "#00AFB9", "#FF6B3D", "#FF9F68", "#F5F5F5", "#10282B", "#FFFFFF", "#FFF", "#00545C", "#007E8A", "#008F99", "#D9501F", "#FFC2A3",
                   "#EAFBFC", "#003E44", "#D6EEF0", "#B7DDE0", "#C9DFE1", "#9FBEC1", "#E4F4F5", "#CFE3E5"}
        css = read("landing.css")
        body = "\n".join(re.findall(r"\{([^{}]*)\}", css))
        for token in set(re.findall(r"#[0-9A-Fa-f]{3,8}\b", body)):
            self.assertIn(token.upper(), allowed, "warna di luar palet: " + token)

    def test_no_heavy_third_party(self):
        """Tidak ada pustaka atau font dari luar: semua disajikan dari server sendiri (CSP script-src 'self')."""
        for name in ("index.html", "landing.css", "app.css", "landing.js"):
            self.assertNotRegex(read(name), r"https?://(?!www\.w3\.org)", name + " memuat sumber dari luar")


class Served(unittest.TestCase):
    """Server benar-benar menyajikan berkas tampilan."""

    @classmethod
    def setUpClass(cls):
        cls.srv = Server(8781, METTA_SEED_DEMO=1).start()
        cls.c = Client(cls.srv.base)

    @classmethod
    def tearDownClass(cls):
        cls.srv.stop()

    def test_index_served(self):
        code, _ = self.c.get("/")
        self.assertEqual(code, 200)

    def test_landing_numbers_come_from_database(self):
        """Angka di halaman depan harus diambil dari database, bukan ditulis tangan, supaya tidak
        pernah menjanjikan 100 karier padahal isinya baru 10."""
        js = read("landing.js")
        self.assertIn("/api/public/stats", js, "halaman depan tidak mengambil angka dari database")
        stats = js[js.find('class: "bigline"'):js.find('class: "note"')]
        self.assertNotRegex(stats, r'"\d{2,}"', "masih ada angka yang ditulis tangan di bagian angka")

    def test_public_stats_matches_database(self):
        code, data = self.c.get("/api/public/stats")          # tanpa login
        self.assertEqual(code, 200, "statistik halaman depan harus bisa dibuka tanpa login")
        for key in ("careers", "companies", "questions", "majors"):
            self.assertIsInstance(data.get(key), int, key + " harus angka")
            self.assertGreater(data[key], 0, key + " kosong")
        code, careers = self.c.get("/api/careers")
        if code == 200:                                        # kalau daftar karier publik, jumlahnya harus sama
            self.assertEqual(len(careers.get("careers", careers) if isinstance(careers, dict) else careers),
                             data["careers"], "jumlah karier di statistik beda dengan daftar karier")

    def test_public_stats_leaks_nothing_personal(self):
        _, data = self.c.get("/api/public/stats")
        for forbidden in ("email", "name", "password", "users", "students"):
            self.assertNotIn(forbidden, str(data).lower(), "statistik publik membocorkan " + forbidden)

    def test_assets_served_with_right_type(self):
        for path, kind in (("/static/app.css", "text/css"), ("/static/landing.css", "text/css"), ("/static/app.js", "javascript"),
                           ("/static/landing.js", "javascript"), ("/static/lang.js", "javascript"), ("/static/photos/belajar.jpg", "image/jpeg"),
                           ("/static/brand/logo-mark.svg", "image/svg+xml"), ("/static/fonts/poppins-700.woff", "font/woff"), ("/static/logo.png", "image/png")):
            r = self.c.s.get(self.srv.base + path, timeout=20)
            self.assertEqual(r.status_code, 200, path + " tidak tersaji")
            self.assertIn(kind, r.headers.get("content-type", ""), path + " tipe isinya salah")

    def test_static_cannot_escape_folder(self):
        """Permintaan nakal tidak boleh mengambil berkas di luar folder static.

        Permintaan dikirim lewat soket mentah, bukan lewat pustaka requests, karena requests
        merapikan sendiri alamat seperti /static/../metta.db menjadi /metta.db sebelum dikirim,
        sehingga yang teruji bukan servernya.
        """
        host, port = self.srv.base.split("//", 1)[1].split(":")
        for path in ("/static/../metta.db", "/static/..%2fapp.py", "/static/%2e%2e/metta.db",
                     "/static/../../etc/passwd", "/static/..\\metta.db"):
            s = socket.create_connection((host, int(port)), 20)
            try:
                s.sendall(("GET %s HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n\r\n" % (path, host)).encode())
                raw = b""
                while True:
                    chunk = s.recv(65536)
                    if not chunk:
                        break
                    raw += chunk
            finally:
                s.close()
            body = raw.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in raw else b""
            self.assertNotIn(b"SQLite format", body[:200], path + " membocorkan berkas database")
            self.assertNotIn(b"root:x:", body[:400], path + " membocorkan berkas sistem")
            self.assertNotIn(b"password_hash", body[:4000], path + " membocorkan kode program")


if __name__ == "__main__":
    unittest.main()
