"""Rakit folder artifact: salin frontend asli, ubah jalur /static/ menjadi relatif, sambungkan api() ke server di dalam halaman."""
import os, re, shutil, sys
SRC = "/home/claude/metta-career-app/metta/static"
SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site")
OUT = os.path.join(SITE, "static")
if os.path.isdir(OUT): shutil.rmtree(OUT)
SKIP = {"index.html", "guard.js", "logo.png"}
for root, dirs, files in os.walk(SRC):
    for f in files:
        rel = os.path.relpath(os.path.join(root, f), SRC)
        if rel in SKIP or "__pycache__" in rel: continue
        dst = os.path.join(OUT, rel); os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(os.path.join(root, f), dst)

def edit(name, fn):
    p = os.path.join(OUT, name); s = open(p, encoding="utf-8").read(); n = fn(s)
    if n == s: sys.exit("tidak berubah: " + name)
    open(p, "w", encoding="utf-8").write(n)

for js in ("app.js", "landing.js", "student.js", "staff.js", "portfolio.js", "course.js", "alumni.js", "company_data.js", "start.js", "i18n.js", "lang.js"):
    p = os.path.join(OUT, js); s = open(p, encoding="utf-8").read()
    open(p, "w", encoding="utf-8").write(s.replace('"/static/', '"static/'))
for css in ("app.css", "landing.css"):
    p = os.path.join(OUT, css); s = open(p, encoding="utf-8").read()
    open(p, "w", encoding="utf-8").write(s.replace("url(/static/", "url("))

# api(): server di dalam halaman, bukan jaringan
edit("app.js", lambda s: s.replace("return fetch(path, opt).catch(", "return window.MettaServer.fetch(path, opt).catch("))
# tautan file bukti: dibuka lewat server di dalam halaman
edit("portfolio.js", lambda s: s.replace('h("a", { href: "/api/files/" + f.id, target: "_blank", rel: "noopener noreferrer" }, f.name)',
     'h("a", { href: "#", onclick: function (e) { e.preventDefault(); window.MettaServer.openFile(f.id); } }, f.name)'))
# tautan portfolio publik memakai alamat artifact
edit("portfolio.js", lambda s: s.replace('var url = location.origin + "/#/p/" + d.share.slug;', 'var url = window.MettaServer.publicLink(d.share.slug);'))
# penanda status penyimpanan
with open(os.path.join(OUT, "app.css"), "a", encoding="utf-8") as f:
    f.write("""
/* artifact: penanda tempat data disimpan */
.mstore{position:fixed;left:calc(12px + env(safe-area-inset-left,0px));bottom:calc(12px + env(safe-area-inset-bottom,0px));z-index:70;display:flex;gap:6px;flex-wrap:wrap;max-width:calc(100% - 24px)}
.mstore-b{border:1px solid #C4CFD0;background:#fff;color:#10282B;font:600 12px/1.2 "Plus Jakarta Sans",system-ui,sans-serif;padding:7px 11px;border-radius:99px;cursor:pointer;box-shadow:0 2px 8px rgba(16,40,43,.12)}
.mstore-b.shared::before,.mstore-b.local::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;background:#00AFB9;vertical-align:1px}
.mstore-b.local::before{background:#FF9F68}
.mstore-b.fresh{background:#006D77;border-color:#006D77;color:#fff}
.mstore-b:focus-visible{outline:3px solid #00AFB9;outline-offset:2px}
.mstore-fail{position:fixed;left:16px;right:16px;top:16px;z-index:80;background:#FDE8E8;color:#9B1C1C;border-radius:12px;padding:14px 16px;font:500 14px/1.5 system-ui,sans-serif}
.boot{min-height:60vh;display:grid;place-items:center;color:#4A5F62;font:500 15px/1.5 "Plus Jakarta Sans",system-ui,sans-serif}
""")

SCRIPTS = ["srv/util.js", "srv/core.js", "srv/engine.js", "srv/api_auth_student.js", "srv/api_more.js", "srv/store.js",
           "static/i18n.js", "static/lang.js", "static/app.js", "static/student.js", "static/course.js", "static/staff.js", "static/portfolio.js",
           "static/alumni.js", "static/company_data.js", "static/landing.js", "static/start.js"]
page = """<title>Metta Career</title>
<meta name="description" content="Metta Career: platform pengembangan karier siswa SMK Metta Maitreya, lengkap dengan backend dan database di dalam artifact.">
<meta name="theme-color" content="#006D77">
<link rel="stylesheet" href="static/app.css">
<link rel="stylesheet" href="static/landing.css">
<style>html,body{background:#F5F5F5}</style>
<div id="app"><div class="boot">Memuat Metta Career…</div></div>
<div id="toast" role="status" aria-live="polite"></div>
""" + "\n".join('<script src="%s"></script>' % s for s in SCRIPTS) + "\n"
open(os.path.join(SITE, "metta-career.html"), "w", encoding="utf-8").write(page)

# daftar file untuk dipublikasikan
files = []
for root, dirs, fs in os.walk(SITE):
    for f in fs:
        rel = os.path.relpath(os.path.join(root, f), SITE)
        if rel == "metta-career.html": continue
        files.append(rel)
files.sort()
import json
json.dump(files, open(os.path.join(SITE, "..", "build", "files.json"), "w"))
print(len(files), "file,", sum(os.path.getsize(os.path.join(SITE, f)) for f in files) // 1024, "KB")
