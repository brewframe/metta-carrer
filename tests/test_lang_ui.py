"""Tes terjemahan tampilan: setiap teks yang tampil di layar dan setiap pesan error dari server harus
punya terjemahan Indonesia, supaya mode Indonesia tidak tercampur teks Inggris.

Butuh Node.js (untuk menjalankan i18n.js dan lang.js apa adanya). Kalau Node tidak ada, tes dilewati.

Jalankan:  python -m unittest tests.test_lang_ui -v
"""
import json, os, re, shutil, subprocess, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "metta", "static")
NODE = shutil.which("node")


def read(path, base=STATIC):
    with open(os.path.join(base, path), encoding="utf-8") as f:
        return f.read()


def js_strings(src):
    """Isi semua literal "..." di JavaScript, dengan escape dasar dibuka."""
    out = []
    for m in re.finditer(r'"((?:[^"\\\n]|\\.)*)"', src):
        s = m.group(1)
        try: s = json.loads('"' + s + '"')
        except ValueError: continue
        out.append(s)
    return out


def node_eval(expr_json):
    """Jalankan i18n.js + lang.js di Node lalu hitung ekspresi yang diberikan (JSON stdin -> JSON stdout)."""
    script = r"""
global.document={documentElement:{}};global.localStorage={getItem(){return 'id'},setItem(){}};global.navigator={language:'id'};
const fs=require('fs');const d=process.argv[1];
eval(fs.readFileSync(d+'/i18n.js','utf8')+';global.I18N=I18N');eval(fs.readFileSync(d+'/lang.js','utf8'));
let input='';process.stdin.on('data',c=>input+=c).on('end',()=>{const q=JSON.parse(input);
 const out={keys:I18N.keys(),has:q.has.map(s=>I18N.has(s)),err:q.err.map(m=>I18N.err(m)),
  pairs:I18N.keys().map(k=>[k,I18N.tr(k,'A','B','C','D')])};
 console.log(JSON.stringify(out));});
"""
    r = subprocess.run([NODE, "-e", script, STATIC], input=json.dumps(expr_json), capture_output=True, text=True, timeout=30)
    if r.returncode: raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


@unittest.skipUnless(NODE, "Node.js tidak terpasang")
class Dictionary(unittest.TestCase):
    def test_every_tr_call_has_indonesian(self):
        """tr("...") di semua berkas tampilan harus ada di lang.js."""
        need = set()
        for name in ("app.js", "student.js", "staff.js", "landing.js", "portfolio.js", "alumni.js", "company_data.js", "course.js"):
            for m in re.finditer(r'\btr\(\s*"((?:[^"\\\n]|\\.)*)"', read(name)):
                need.add(json.loads('"' + m.group(1) + '"'))
        app = read("app.js")
        nav = app[app.index("var NAV"):app.index("function h(")]
        need.update(s for s in js_strings(nav) if re.search(r"[A-Za-z]{3}", s) and not s.startswith("#/") and s not in ("student", "teacher", "admin", "alumni"))
        res = node_eval({"has": sorted(need), "err": []})
        missing = [s for s, ok in zip(sorted(need), res["has"]) if not ok]
        self.assertEqual(missing, [], "teks belum diterjemahkan di lang.js: %r" % missing)

    def test_placeholders_kept(self):
        """Terjemahan harus memuat tanda {0}, {1}, ... yang sama dengan teks sumber."""
        src = read("lang.js")
        res = node_eval({"has": [], "err": []})
        # Ambil pasangan mentah dari lang.js supaya tanda {n} bisa dibandingkan.
        pairs = re.findall(r'"((?:[^"\\\n]|\\.)*)"\s*:\s*"((?:[^"\\\n]|\\.)*)"', src[:src.index("I18N.addErrors")])
        bad = []
        for k, v in pairs:
            if sorted(re.findall(r"\{\d+\}", k)) != sorted(re.findall(r"\{\d+\}", v)): bad.append(k)
        self.assertEqual(bad, [], "tanda {n} tidak sama: %r" % bad[:5])
        self.assertTrue(res["keys"])

    def test_no_empty_translation(self):
        src = read("lang.js")
        for k, v in re.findall(r'"((?:[^"\\\n]|\\.)*)"\s*:\s*"((?:[^"\\\n]|\\.)*)"', src[:src.index("I18N.addErrors")]):
            self.assertTrue(v.strip(), "terjemahan kosong untuk: " + k)

    def test_server_errors_translated(self):
        """Semua pesan error tetap dari server (HTTPError, bad, not_found, aturan password) punya padanan Indonesia."""
        msgs = set()
        for rel in ("core.py", "security.py", "api/auth.py", "api/admin.py", "api/student.py", "api/teacher.py", "api/alumni.py", "api/recovery.py"):
            p = os.path.join(ROOT, "metta", rel)
            if not os.path.exists(p): continue
            code = read(rel, os.path.join(ROOT, "metta"))
            for m in re.finditer(r'(?:HTTPError\(\d+,|bad\(|not_found\(|ValueError\()\s*"([^"{}]+)"', code):
                msgs.add(m.group(1))
        sec = read("security.py", os.path.join(ROOT, "metta"))
        for m in re.finditer(r'return\s+"([A-Z][^"{}]{8,})"', sec): msgs.add(m.group(1))
        msgs.discard("Not found"); msgs.discard("Bad request")
        res = node_eval({"has": [], "err": sorted(msgs)})
        untranslated = [m for m, t in zip(sorted(msgs), res["err"]) if t == m]
        self.assertEqual(untranslated, [], "pesan error server belum diterjemahkan: %r" % untranslated)

    def test_dynamic_error_patterns(self):
        res = node_eval({"has": [], "err": ["Please answer all questions (3/20)", "Password must be at least 8 characters",
                                            "Password must be at least 12 characters for teachers and admins", "body.name: String should have at least 2 characters"]})
        for src, out in zip(["a", "b", "c", "d"], res["err"]):
            self.assertNotRegex(out, r"^(Please answer|Password must|body\.name)", "pola pesan belum diterjemahkan: " + out)


class Wiring(unittest.TestCase):
    def test_script_order(self):
        html = read("index.html")
        order = [html.index(x) for x in ("i18n.js", "lang.js", "app.js", "student.js", "staff.js", "portfolio.js", "company_data.js", "landing.js", "start.js")]
        self.assertEqual(order, sorted(order), "urutan <script> salah: i18n.js dan lang.js harus sebelum app.js")

    def test_api_sends_language_header(self):
        self.assertIn('"X-Lang"', read("app.js"))

    def test_language_switch_present_on_all_entry_points(self):
        self.assertIn("langSwitch(", read("app.js"))      # bar atas aplikasi dan layar masuk
        self.assertIn("M.langSwitch(", read("landing.js"))  # halaman depan dan footer

    def test_no_inline_script_in_index(self):
        """CSP melarang script inline: index.html tidak boleh punya isi di dalam <script>."""
        for body in re.findall(r"<script[^>]*>(.*?)</script>", read("index.html"), re.S):
            self.assertEqual(body.strip(), "")


if __name__ == "__main__":
    unittest.main()
