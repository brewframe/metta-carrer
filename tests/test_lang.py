"""Tes fitur dua bahasa (Indonesia / Inggris) dan tabel database tambahan.

Yang dijaga:
- bahasa dipilih lewat header X-Lang atau pilihan tersimpan pengguna, bukan dari input bebas;
- semua isi data awal punya terjemahan Indonesia (tidak ada teks Inggris yang tersisa di mode Indonesia);
- tugas dan alasan rekomendasi ikut bahasa saat dibaca, bukan saat dibuat;
- database lama bisa dimigrasi tanpa kehilangan data.

Jalankan:  python -m unittest tests.test_lang -v
"""
import json, os, sqlite3, sys, tempfile, unittest

from .support import Server, Client, ROOT

PW = "Kopi-Susu-Enak-77"
HEAD = {"id": {"X-Lang": "id"}, "en": {"X-Lang": "en"}}


class Bilingual(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = Server(8791, METTA_SEED_DEMO=1, METTA_REGISTER_LIMIT=500).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.stop()

    def student(self, tag, lang=None):
        """Siswa baru yang sudah mengisi Self Discovery (semua jawaban 5)."""
        c = Client(self.srv.base)
        h = HEAD[lang] if lang else {}
        st, _ = c.post("/api/auth/register", {"name": "Siswa " + tag, "email": tag + "@x.id", "password": PW, "major": "TKJ", "class_name": "XI TKJ"}, headers=h)
        self.assertEqual(st, 200)
        _, q = c.get("/api/student/questions", headers=HEAD["en"])
        st, ins = c.post("/api/student/assessment", {"answers": {str(x["id"]): 5 for x in q["questions"]}, "skill_ids": [q["skills"][0]["id"]]}, headers=HEAD["en"])
        self.assertEqual(st, 200)
        return c

    # ---------- pemilihan bahasa ----------
    def test_header_decides_language(self):
        c = Client(self.srv.base); c.login("student@metta.sch", "Student#2026!")
        _, en = c.get("/api/careers", headers=HEAD["en"])
        _, idn = c.get("/api/careers", headers=HEAD["id"])
        names_en = {x["id"]: x["name"] for x in en["items"]}; names_id = {x["id"]: x["name"] for x in idn["items"]}
        self.assertEqual(set(names_en), set(names_id))
        self.assertIn("Accounting Staff", names_en.values()); self.assertIn("Staf Akuntansi", names_id.values())
        self.assertNotIn("Accounting Staff", names_id.values())

    def test_invalid_language_is_ignored(self):
        c = Client(self.srv.base); c.login("student@metta.sch", "Student#2026!")
        for bad in ("fr", "../../etc", "id'; DROP TABLE users;--", "x" * 500, ""):
            st, data = c.get("/api/careers", headers={"X-Lang": bad})
            self.assertEqual(st, 200, bad)
            self.assertTrue(data["items"])
        _, me = c.get("/api/me", headers={"X-Lang": "zz"})
        self.assertIn(me["lang"], ("id", "en"))

    def test_saved_preference_is_used_without_header(self):
        c = self.student("pref1", "en")
        _, me = c.get("/api/me"); self.assertEqual(me["lang"], "en")             # tersimpan saat daftar
        self.assertEqual(c.post("/api/me/lang", {"lang": "id"})[1]["lang"], "id")
        _, careers = c.get("/api/careers")                                        # tanpa header: pakai pilihan tersimpan
        self.assertIn("Staf Akuntansi", [x["name"] for x in careers["items"]])
        _, careers = c.get("/api/careers", headers=HEAD["en"])                   # header menang
        self.assertIn("Accounting Staff", [x["name"] for x in careers["items"]])

    def test_language_endpoint_validation_and_auth(self):
        c = Client(self.srv.base)
        self.assertEqual(c.post("/api/me/lang", {"lang": "id"})[0], 401, "tamu tidak boleh mengubah bahasa")
        c.login("student@metta.sch", "Student#2026!")
        for bad in ("fr", "", "ID ", None, 5, "id;"):
            self.assertEqual(c.post("/api/me/lang", {"lang": bad})[0], 422, repr(bad))

    # ---------- isi data ----------
    def test_every_seed_row_has_indonesian_translation(self):
        import sqlite3
        db = sqlite3.connect(self.srv.db); db.row_factory = sqlite3.Row
        try:
            have = {(r["entity"], r["entity_id"], r["field"]) for r in db.execute("SELECT * FROM translations WHERE lang='id'")}
            for r in db.execute("SELECT id FROM skills"): self.assertIn(("skill", r["id"], "name"), have)
            for r in db.execute("SELECT id FROM questions"): self.assertIn(("question", r["id"], "text"), have)
            for r in db.execute("SELECT id FROM careers"):
                for f in ("name", "description", "responsibilities", "education_path", "example_projects", "growth"):
                    self.assertIn(("career", r["id"], f), have, "karier %s belum punya terjemahan %s" % (r["id"], f))
        finally:
            db.close()

    def test_questions_and_skills_follow_language(self):
        c = Client(self.srv.base); c.login("student@metta.sch", "Student#2026!")
        _, en = c.get("/api/student/questions", headers=HEAD["en"]); _, idn = c.get("/api/student/questions", headers=HEAD["id"])
        self.assertEqual(len(en["questions"]), len(idn["questions"]))
        self.assertTrue(en["questions"][0]["text"].startswith("I "))
        self.assertTrue(idn["questions"][0]["text"].startswith("Aku "))
        self.assertIn("Dasar jaringan komputer", [s["name"] for s in idn["skills"]])
        self.assertEqual({s["id"] for s in en["skills"]}, {s["id"] for s in idn["skills"]})

    # ---------- teks yang dirangkai server ----------
    def test_reasons_tasks_and_assistant_follow_language(self):
        c = self.student("lang2")
        _, rec_en = c.get("/api/student/recommendations", headers=HEAD["en"]); _, rec_id = c.get("/api/student/recommendations", headers=HEAD["id"])
        self.assertTrue(all(r["reasons"] for r in rec_en["items"]))
        self.assertTrue(any("Minatmu" in r or "Kekuatanmu" in r or "Skill yang perlu" in r or "Kamu sudah" in r or "jalur" in r for x in rec_id["items"] for r in x["reasons"]))
        self.assertFalse(any("Your interests" in r for x in rec_id["items"] for r in x["reasons"]))
        self.assertNotIn("reason_codes", rec_en["items"][0], "kode internal tidak boleh bocor ke browser")
        cid = rec_en["items"][0]["career_id"]
        self.assertEqual(c.post("/api/student/plan", {"career_id": cid}, headers=HEAD["en"])[0], 200)
        _, plan_en = c.get("/api/student/plan", headers=HEAD["en"]); _, plan_id = c.get("/api/student/plan", headers=HEAD["id"])
        t_en = plan_en["milestones"][0]["tasks"][0]; t_id = plan_id["milestones"][0]["tasks"][0]
        self.assertEqual(t_en["id"], t_id["id"], "tugas yang sama, hanya bahasanya beda")
        self.assertTrue(t_en["title"].startswith("Learn "))
        self.assertTrue(t_id["title"].startswith("Pelajari "))
        self.assertEqual(t_id["difficulty"], "Pemula"); self.assertEqual(t_en["difficulty"], "Beginner")
        self.assertEqual(plan_en["plan"]["reasons"][0] != plan_id["plan"]["reasons"][0], True, "alasan rencana harus ikut bahasa")
        _, a_en = c.post("/api/student/assistant", {"question": "What should I do next?"}, headers=HEAD["en"])
        _, a_id = c.post("/api/student/assistant", {"question": "Apa langkah selanjutnya?"}, headers=HEAD["id"])
        self.assertIn("next step", a_en["answer"].lower()); self.assertIn("langkah berikutnya", a_id["answer"].lower())
        self.assertTrue(a_id["next_action"].startswith("Buka"))
        self.assertEqual(a_en["next_action"], "Open Learning")

    def test_legacy_plan_reasons_still_render(self):
        """Rencana yang dibuat versi lama menyimpan alasan sebagai teks Inggris. Tidak boleh error atau hilang."""
        c = self.student("legacy1")
        cid = c.get("/api/student/recommendations", headers=HEAD["en"])[1]["items"][0]["career_id"]
        c.post("/api/student/plan", {"career_id": cid}, headers=HEAD["en"])
        db = sqlite3.connect(self.srv.db)
        try:
            db.execute("UPDATE plans SET reasons=? WHERE user_id=(SELECT id FROM users WHERE email='legacy1@x.id') AND status='ACTIVE'",
                       (json.dumps(["Your interests fit this field (technology)."]),))
            db.commit()
        finally:
            db.close()
        _, p = c.get("/api/student/plan", headers=HEAD["id"])
        self.assertEqual(p["plan"]["reasons"], ["Your interests fit this field (technology)."])

    def test_notifications_use_recipient_language(self):
        s_id = self.student("note_id", "id"); s_en = self.student("note_en", "en")
        _, n_id = s_id.get("/api/notifications"); _, n_en = s_en.get("/api/notifications")
        self.assertTrue(n_id["items"][-1]["text"].startswith("Selamat datang"))
        self.assertTrue(n_en["items"][-1]["text"].startswith("Welcome"))
        t = Client(self.srv.base); t.login("teacher@metta.sch", "Teacher#2026!")
        sid = next(x["id"] for x in t.get("/api/teacher/students")[1]["items"] if x["name"] == "Siswa note_id")
        t.post("/api/teacher/students/%d/feedback" % sid, {"text": "Bagus sekali, lanjutkan."}, headers=HEAD["en"])   # guru memakai Inggris
        _, n_id = s_id.get("/api/notifications")
        self.assertTrue(n_id["items"][0]["text"].startswith("Masukan baru"), "notifikasi mengikuti bahasa penerima, bukan pengirim")

    # ---------- tabel tambahan ----------
    def test_new_tables_exist_and_are_used(self):
        c = self.student("tbl1")
        cid = c.get("/api/student/recommendations", headers=HEAD["en"])[1]["items"][0]["career_id"]
        c.post("/api/student/plan", {"career_id": cid})
        _, pl = c.get("/api/student/plan")
        sk = pl["milestones"][0]["skill_id"]
        st, proj = c.post("/api/student/projects", {"title": "Jaringan kecil", "link": "https://github.com/x/y", "skill_ids": [sk]})
        self.assertEqual(st, 200)
        t = Client(self.srv.base); t.login("teacher@metta.sch", "Teacher#2026!")
        self.assertEqual(t.post("/api/teacher/projects/%d/review" % proj["id"], {"decision": "NEEDS_REVISION", "note": "Tambahkan diagram jaringan."})[0], 200)
        db = sqlite3.connect(self.srv.db)
        try:
            uid = db.execute("SELECT id FROM users WHERE email='tbl1@x.id'").fetchone()[0]
            ms = db.execute("SELECT COUNT(*) FROM milestones m JOIN plans p ON p.id=m.plan_id WHERE p.user_id=?", (uid,)).fetchone()[0]
            self.assertGreaterEqual(ms, 1, "rencana baru harus punya baris milestone")
            ev = db.execute("SELECT url FROM project_evidence WHERE project_id=?", (proj["id"],)).fetchall()
            self.assertEqual(ev, [("https://github.com/x/y",)], "tautan bukti harus ikut tersimpan sebagai project_evidence")
            fb = db.execute("SELECT decision,note FROM project_feedback WHERE project_id=?", (proj["id"],)).fetchall()
            self.assertEqual(fb, [("NEEDS_REVISION", "Tambahkan diagram jaringan.")])
            for table in ("teacher_profiles", "alumni_profiles", "achievements", "certificates", "portfolios", "translations"):
                db.execute("SELECT 1 FROM %s LIMIT 1" % table)           # tabelnya ada
        finally:
            db.close()

    def test_new_tables_reject_bad_values(self):
        db = sqlite3.connect(self.srv.db); db.execute("PRAGMA foreign_keys=ON")
        try:
            uid = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
            with self.assertRaises(sqlite3.IntegrityError): db.execute("INSERT INTO portfolios(user_id,visibility) VALUES(?, 'EVERYONE')", (uid,))
            with self.assertRaises(sqlite3.IntegrityError): db.execute("INSERT INTO translations(entity,entity_id,field,lang,value) VALUES('career',1,'name','fr','x')")
            with self.assertRaises(sqlite3.IntegrityError): db.execute("INSERT INTO teacher_profiles(user_id,kind) VALUES(?, 'KEPALA')", (uid,))
            with self.assertRaises(sqlite3.IntegrityError): db.execute("INSERT INTO achievements(user_id,title) VALUES(99999,'x')")   # pemilik harus ada
        finally:
            db.rollback(); db.close()


class Migration(unittest.TestCase):
    def test_old_database_is_upgraded_without_losing_data(self):
        """Database buatan versi sebelumnya (tanpa kolom lang dan tanpa tabel baru) harus naik versi dengan aman."""
        path = os.path.join(tempfile.mkdtemp(), "old.db")
        old = sqlite3.connect(path)
        old.executescript("""
          CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL, password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN('student','teacher','alumni','admin')), active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')), last_active_at TEXT NOT NULL DEFAULT (datetime('now')));
          CREATE TABLE skills(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, category TEXT NOT NULL DEFAULT 'technical');
          CREATE TABLE careers(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, category TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '',
            responsibilities TEXT NOT NULL DEFAULT '', education_path TEXT NOT NULL DEFAULT '', example_projects TEXT NOT NULL DEFAULT '',
            growth TEXT NOT NULL DEFAULT '', interest_tags TEXT NOT NULL DEFAULT '', strength_tags TEXT NOT NULL DEFAULT '', majors TEXT NOT NULL DEFAULT '');
          CREATE TABLE plans(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            career_id INTEGER NOT NULL REFERENCES careers(id), status TEXT NOT NULL DEFAULT 'ACTIVE', reasons TEXT NOT NULL DEFAULT '[]',
            teacher_note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT (datetime('now')));
          CREATE TABLE tasks(id INTEGER PRIMARY KEY, plan_id INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
            skill_id INTEGER REFERENCES skills(id), milestone INTEGER NOT NULL, position INTEGER NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '', difficulty TEXT NOT NULL DEFAULT 'Beginner', est_hours INTEGER NOT NULL DEFAULT 2,
            status TEXT NOT NULL DEFAULT 'NOT_STARTED', completed_at TEXT);
          INSERT INTO users(id,email,name,password_hash,role) VALUES(7,'lama@x.id','Siswa Lama','hash','student');
          INSERT INTO skills(id,name) VALUES(3,'Python'); INSERT INTO careers(id,name) VALUES(2,'Data Analyst');
          INSERT INTO plans(id,user_id,career_id,reasons) VALUES(5,7,2,'["Your interests fit this field (data)."]');
          INSERT INTO tasks(plan_id,skill_id,milestone,position,kind,title) VALUES(5,3,1,1,'STUDY','Study the basics of Python'),(5,3,1,2,'PRACTICE','Practice Python'),(5,3,2,3,'APPLY','Apply Python');
        """)
        old.commit(); old.close()
        code = ("import os,sys,sqlite3; sys.path.insert(0, %r); os.environ['METTA_DB']=%r\n"
                "from metta.db import init_db; init_db(); init_db()\n"          # dua kali: harus aman diulang
                "d=sqlite3.connect(%r)\n"
                "print([r[1] for r in d.execute('PRAGMA table_info(users)')])\n"
                "print(d.execute('SELECT email,name,lang,must_change_password FROM users').fetchall())\n"
                "print(d.execute('SELECT plan_id,number,skill_id FROM milestones ORDER BY number').fetchall())\n"
                "print(d.execute('SELECT COUNT(*) FROM tasks').fetchone(), d.execute('SELECT reasons FROM plans').fetchone())\n"
                % (ROOT, path, path))
        import subprocess
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        lines = out.stdout.strip().splitlines()
        self.assertIn("'lang'", lines[0]); self.assertIn("'must_change_password'", lines[0])
        self.assertEqual(lines[1], "[('lama@x.id', 'Siswa Lama', 'id', 0)]")
        self.assertEqual(lines[2], "[(5, 1, 3), (5, 2, 3)]", "milestone harus dibentuk dari tugas lama")
        self.assertIn("(3,)", lines[3]); self.assertIn("Your interests fit this field (data).", lines[3])


if __name__ == "__main__":
    unittest.main()
