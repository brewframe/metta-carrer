"""Isi data contoh untuk PRESENTASI di komputer sendiri (bukan untuk server online).

    python -m metta.demo_data            # server harus sudah jalan di http://127.0.0.1:8000
    python -m metta.demo_data --wait     # tunggu server siap dulu (dipakai run_dev.bat)

Semua data dibuat lewat API aplikasi yang sama dengan yang dipakai browser, jadi aturan keamanan
dan validasi tetap berlaku. Aman dijalankan berkali-kali: bila Student Demo sudah punya Career Plan,
skrip berhenti tanpa mengubah apa pun. Nama tempat magang dan alumni ditandai "(contoh)" agar tidak
dikira data asli.
"""
import json, os, sys, time, urllib.request, urllib.error
from http.cookiejar import CookieJar

BASE = os.environ.get("METTA_DEMO_URL", "http://127.0.0.1:8000").rstrip("/")
PW = {"student": "Student#2026!", "teacher": "Teacher#2026!", "admin": "Admin#2026!", "alumni": "Alumni#2026!"}
EXTRA_PW = "Belajar-Karier-2026!"


class Client:
    def __init__(self):
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()), urllib.request.ProxyHandler({}))

    def call(self, method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with self.op.open(req, timeout=20) as r: return r.status, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            try: return e.code, json.loads(e.read() or b"null")
            except ValueError: return e.code, None

    def get(self, p): return self.call("GET", p)
    def post(self, p, b=None): return self.call("POST", p, {} if b is None else b)
    def put(self, p, b): return self.call("PUT", p, b)
    def patch(self, p, b): return self.call("PATCH", p, b)

    def login(self, role, email=None, pw=None):
        st, _ = self.post("/api/auth/login", {"email": email or role + "@metta.sch", "password": pw or PW[role], "role": role})
        if st != 200: raise SystemExit("Gagal login sebagai %s (%s). Apakah server dijalankan dengan run_dev.bat?" % (email or role, st))
        return self


def say(ok, text): print(("  [OK]    " if ok else "  [LEWATI] ") + text)


def wait_server(sec=90):
    for _ in range(sec):
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(BASE + "/api/health", timeout=2): return True
        except Exception: time.sleep(1)
    return False


def assess(s, prefer):
    _, q = s.get("/api/student/questions")
    ans = {str(x["id"]): (5 if x["tag"] in prefer else 2) for x in q["questions"]}
    skills = [k["id"] for k in q["skills"][:2]]
    st, _ = s.post("/api/student/assessment", {"answers": ans, "skill_ids": skills})
    return st == 200


def pick_career(s, want_course, prefer=()):
    """Pilih dari rekomendasi AI: utamakan karier di prefer, lalu yang sudah punya kursus."""
    from . import course as CRS
    _, rec = s.get("/api/student/recommendations")
    items = (rec or {}).get("items", [])
    for pid in prefer:
        for it in items:
            if it["career_id"] == pid: return it
    for pid in prefer[:1]:   # siswa boleh memilih sendiri di luar rekomendasi: AI hanya menyarankan
        st, d = s.get("/api/careers/%d" % pid)
        if st == 200: return {"career_id": pid, "name": (d.get("career") or d).get("name", "")}
    for it in items:
        if not want_course or it["career_id"] in CRS.COURSES: return it
    return items[0] if items else None


def finish_tasks(s, n):
    _, plan = s.get("/api/student/plan")
    done = 0
    for m in plan.get("milestones", []):
        for t in m.get("tasks", []):
            if done >= n: return done
            st, les = s.get("/api/student/learn/%d" % t["id"])
            if st == 200:
                for i in range(len(les.get("steps", []))): s.post("/api/student/learn/%d/step" % t["id"], {"idx": i, "done": True})
            if s.patch("/api/student/tasks/%d" % t["id"], {"status": "COMPLETED"})[0] == 200: done += 1
            else:
                s.patch("/api/student/tasks/%d" % t["id"], {"status": "IN_PROGRESS"}); return done
    return done


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if os.environ.get("METTA_ENV") == "production": raise SystemExit("demo_data hanya untuk komputer sendiri, tidak untuk production.")
    host = BASE.split("//", 1)[-1].split("/")[0].split(":")[0]
    if host not in ("127.0.0.1", "localhost"): raise SystemExit("demo_data hanya boleh mengisi server lokal (127.0.0.1).")
    if "--wait" in argv and not wait_server(): raise SystemExit("Server tidak menjawab di " + BASE)

    s = Client().login("student")
    if (s.get("/api/student/plan")[1] or {}).get("plan"):
        print("Data demo sudah ada. Tidak ada yang diubah."); return
    print("Mengisi data demo untuk presentasi ...")

    # 1. Siswa utama: Self Discovery, Career Plan, belajar, project, magang
    say(assess(s, ("technology", "analytical", "logical", "technical", "problem_solving")), "Student Demo mengisi Self Discovery")
    s.post("/api/student/insight/save")
    c = pick_career(s, want_course=True, prefer=(1, 2, 3))
    ok = bool(c) and s.post("/api/student/plan", {"career_id": c["career_id"]})[0] == 200
    say(ok, "Career Plan: " + (c["name"] if c else "-"))
    say(True, "Tugas belajar selesai: %d" % finish_tasks(s, 2))
    _, plan = s.get("/api/student/plan")
    skill = [g["id"] for g in plan.get("skill_gap", [])[:2]] or [x["id"] for x in plan.get("current_skills", [])[:1]]
    st, p1 = s.post("/api/student/projects", {"title": "Jaringan Lab Komputer Sekolah", "description": "Merancang ulang jaringan lab: pembagian IP, Wi-Fi tamu terpisah, dan dokumentasi.",
        "problem": "Internet lab sering lambat dan semua perangkat ada di satu jaringan.", "solution": "Membagi jaringan menjadi VLAN siswa, guru, dan tamu, lalu membatasi bandwidth.",
        "result": "Kecepatan lebih stabil dan jaringan tamu tidak bisa melihat komputer lab.", "technology": "MikroTik, Cisco Packet Tracer",
        "repo_url": "https://github.com/contoh/jaringan-lab", "skill_ids": skill})
    say(st == 200, "Project 1 dikirim (akan diverifikasi guru)")
    st, p2 = s.post("/api/student/projects", {"title": "Pemantau Suhu Ruang Server", "description": "Sensor suhu yang mengirim data ke dashboard sederhana dan memberi peringatan.",
        "problem": "Ruang server pernah terlalu panas tanpa ada yang tahu.", "solution": "Sensor suhu dengan mikrokontroler yang mengirim data setiap menit.",
        "result": "Peringatan muncul saat suhu di atas 30 derajat.", "technology": "ESP32, Python", "skill_ids": skill[:1]})
    say(st == 200, "Project 2 dikirim (dibiarkan menunggu validasi untuk demo guru)")
    _, co = s.get("/api/companies")
    ids = [x["id"] for x in (co or {}).get("items", []) if x.get("status", "approved") == "approved"][:3]
    say(s.put("/api/student/internship", {"class_name": "XI TKJ", "company_ids": ids})[0] == 200, "3 pilihan tempat magang disimpan")
    st, _ = s.post("/api/student/companies", {"name": "CV Teknik Nusantara (contoh)", "address": "Jl. Contoh No. 12, Pekanbaru, Riau",
        "sector": "Jaringan dan IT support", "about": "Usaha kecil yang memasang jaringan kantor, CCTV, dan merawat komputer untuk sekolah dan toko di sekitar Pekanbaru.",
        "tasks": "Membantu pemasangan kabel jaringan, konfigurasi router, dan perawatan komputer.", "majors": "TKJ",
        "work_terms": "Senin sampai Jumat, 08.00 sampai 16.00", "website": "https://example.com", "source": "Data contoh untuk presentasi"})
    say(st == 200, "Siswa mengajukan tempat magang baru (menunggu verifikasi guru)")

    # 2. Siswa tambahan agar dashboard guru tidak kosong
    for name, email, major, cls, prefer, plan_too in (
            ("Citra Lestari", "citra@metta.sch", "AK", "XI AK", ("business", "finance", "detail", "organized", "numeracy"), True),
            ("Budi Santoso", "budi@metta.sch", "TKJ", "XI TKJ", ("technology", "technical"), False)):
        x = Client()
        st, _ = x.post("/api/auth/register", {"name": name, "email": email, "password": EXTRA_PW, "major": major, "class_name": cls})
        if st != 200: x.login("student", email, EXTRA_PW)
        assess(x, prefer)
        if plan_too:
            cc = pick_career(x, want_course=True, prefer=(8, 22, 87))
            if cc: x.post("/api/student/plan", {"career_id": cc["career_id"]}); finish_tasks(x, 1)
        say(True, "Siswa tambahan: %s (%s)" % (name, "punya Career Plan" if plan_too else "belum memilih karier"))

    # 3. Guru: verifikasi project 1, beri masukan dan arahan
    t = Client().login("teacher")
    if p1 and p1.get("id"): say(t.post("/api/teacher/projects/%d/review" % p1["id"], {"decision": "VERIFIED", "note": "Dokumentasi rapi. Tambahkan diagram topologi di versi berikutnya."})[0] == 200, "Guru memverifikasi Project 1")
    sid = s.get("/api/me")[1]["id"]
    t.post("/api/teacher/students/%d/feedback" % sid, {"text": "Kemajuan bagus. Lanjutkan modul berikutnya minggu ini."})
    det = t.get("/api/teacher/students/%d" % sid)[1] or {}
    if det.get("plan"): t.put("/api/teacher/plans/%d/guidance" % det["plan"]["id"], {"note": "Fokus ke konfigurasi router dan dokumentasi jaringan."})
    say(True, "Guru memberi masukan dan arahan Career Plan")

    # 4. Alumni: satu cerita terbit, satu menunggu moderasi admin
    a = Client().login("alumni")
    a.put("/api/alumni/profile", {"graduation_year": 2022, "major": "TKJ", "workplace": "Penyedia internet lokal (contoh)", "job_title": "Teknisi Jaringan", "bio": "Lulusan TKJ yang sekarang bekerja di bidang jaringan."})
    body1 = ("Saya lulus TKJ tahun 2022. Saat magang saya belajar memasang kabel dan mengatur router. Hal terpenting yang saya pelajari: "
             "catat setiap konfigurasi, jangan malu bertanya, dan latihan di Packet Tracer sebelum menyentuh perangkat asli. Saran saya, mulai dari project kecil di sekolah.")
    st, r1 = a.post("/api/alumni/content", {"kind": "CAREER_STORY", "title": "Dari TKJ ke teknisi jaringan", "body": body1, "category": "Networking", "submit": True})
    body2 = "Tiga tips sebelum magang: siapkan portofolio sederhana, latih cara menjelaskan project dalam dua menit, dan pelajari dasar keselamatan kerja di lokasi."
    a.post("/api/alumni/content", {"kind": "TIPS", "title": "Tips sebelum magang", "body": body2, "category": "Magang", "submit": True})
    adm = Client().login("admin")
    if st == 200 and r1: adm.post("/api/admin/content/%d/moderate" % r1["id"], {"decision": "PUBLISHED"})
    say(True, "Alumni: 1 cerita terbit, 1 tips menunggu moderasi admin")

    print("\nSelesai. Buka %s lalu login:" % BASE)
    print("  Siswa  student@metta.sch / Student#2026!     Guru  teacher@metta.sch / Teacher#2026!")
    print("  Admin  admin@metta.sch   / Admin#2026!       Alumni alumni@metta.sch / Alumni#2026!")
    print("  Siswa tambahan: citra@metta.sch dan budi@metta.sch, password " + EXTRA_PW)


if __name__ == "__main__": main()
