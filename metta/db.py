"""Database layer: SQLite via the standard library (no ORM, easy to read).
Swap the connect() function to move to PostgreSQL later."""
import os, sqlite3

def db_path():
    return os.environ.get("METTA_DB", "metta.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
  password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN('student','teacher','alumni','admin')),
  active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT (datetime('now')),
  last_active_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS sessions(
  token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS student_profiles(
  user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  school TEXT NOT NULL DEFAULT '', major TEXT NOT NULL DEFAULT '', class_name TEXT NOT NULL DEFAULT '',
  goal TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS skills(
  id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, category TEXT NOT NULL DEFAULT 'technical');
CREATE TABLE IF NOT EXISTS careers(
  id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, category TEXT NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '', responsibilities TEXT NOT NULL DEFAULT '',
  education_path TEXT NOT NULL DEFAULT '', example_projects TEXT NOT NULL DEFAULT '',
  growth TEXT NOT NULL DEFAULT '', interest_tags TEXT NOT NULL DEFAULT '', strength_tags TEXT NOT NULL DEFAULT '',
  majors TEXT NOT NULL DEFAULT '', trend INTEGER NOT NULL DEFAULT 0, is_new INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS career_skills(
  career_id INTEGER NOT NULL REFERENCES careers(id) ON DELETE CASCADE,
  skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  importance INTEGER NOT NULL DEFAULT 2, PRIMARY KEY(career_id, skill_id));
CREATE TABLE IF NOT EXISTS questions(
  id INTEGER PRIMARY KEY, kind TEXT NOT NULL, tag TEXT NOT NULL, text TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS assessments(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  answers TEXT NOT NULL, scores TEXT NOT NULL, saved INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS shortlist(
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  career_id INTEGER NOT NULL REFERENCES careers(id) ON DELETE CASCADE, PRIMARY KEY(user_id, career_id));
CREATE TABLE IF NOT EXISTS plans(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  career_id INTEGER NOT NULL REFERENCES careers(id), status TEXT NOT NULL DEFAULT 'ACTIVE',
  reasons TEXT NOT NULL DEFAULT '[]', teacher_note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS tasks(
  id INTEGER PRIMARY KEY, plan_id INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  skill_id INTEGER REFERENCES skills(id), milestone INTEGER NOT NULL, position INTEGER NOT NULL,
  kind TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
  difficulty TEXT NOT NULL DEFAULT 'Beginner', est_hours INTEGER NOT NULL DEFAULT 2,
  status TEXT NOT NULL DEFAULT 'NOT_STARTED', completed_at TEXT);
CREATE TABLE IF NOT EXISTS student_skills(
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  level INTEGER NOT NULL, PRIMARY KEY(user_id, skill_id));
CREATE TABLE IF NOT EXISTS projects(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', link TEXT NOT NULL DEFAULT '',
  skill_ids TEXT NOT NULL DEFAULT '[]', status TEXT NOT NULL DEFAULT 'SUBMITTED',
  teacher_note TEXT NOT NULL DEFAULT '', reviewed_by INTEGER REFERENCES users(id),
  created_at TEXT NOT NULL DEFAULT (datetime('now')), updated_at TEXT NOT NULL DEFAULT (datetime('now')));
-- Permintaan lupa password: guru/admin menyetujui dan memberi KODE sekali pakai (hanya hash-nya disimpan).
-- Pengguna menyetel password barunya sendiri, jadi guru/admin tidak pernah tahu password akhirnya.
CREATE TABLE IF NOT EXISTS password_requests(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN('PENDING','APPROVED','DONE','REJECTED')),
  code_hash TEXT, expires_at TEXT, attempts INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')), handled_by INTEGER REFERENCES users(id), handled_at TEXT);
CREATE INDEX IF NOT EXISTS ix_pwreq_user ON password_requests(user_id, status);
-- File bukti yang diunggah siswa (isi file di folder uploads/ dengan nama acak).
CREATE TABLE IF NOT EXISTS uploads(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  ref_kind TEXT NOT NULL CHECK(ref_kind IN('certificate','achievement','project')), ref_id INTEGER NOT NULL,
  stored_name TEXT NOT NULL UNIQUE, original_name TEXT NOT NULL, mime TEXT NOT NULL, size INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE INDEX IF NOT EXISTS ix_uploads_ref ON uploads(ref_kind, ref_id);
-- Langkah belajar yang sudah dicentang dan hasil kuis.
CREATE TABLE IF NOT EXISTS task_steps(task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE, idx INTEGER NOT NULL, PRIMARY KEY(task_id, idx));
CREATE TABLE IF NOT EXISTS quiz_attempts(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  score INTEGER NOT NULL, total INTEGER NOT NULL, passed INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS companies(
  id INTEGER PRIMARY KEY, number INTEGER, name TEXT NOT NULL, address TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS internship_choices(
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, rank INTEGER NOT NULL CHECK(rank BETWEEN 1 AND 3),
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE, purpose TEXT NOT NULL DEFAULT '', PRIMARY KEY(user_id, rank));
-- Teman yang diajak magang bersama (maks. 3 per siswa).
CREATE TABLE IF NOT EXISTS internship_friends(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL, class_name TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS feedback(
  id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  teacher_id INTEGER NOT NULL REFERENCES users(id), text TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS notifications(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  text TEXT NOT NULL, read INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS readiness_log(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  value INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS rate_events(
  id INTEGER PRIMARY KEY, bucket TEXT NOT NULL, key TEXT NOT NULL, ts REAL NOT NULL);
CREATE INDEX IF NOT EXISTS ix_rate_events ON rate_events(bucket, key, ts);
CREATE TABLE IF NOT EXISTS audit_log(
  id INTEGER PRIMARY KEY, actor_id INTEGER, action TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE INDEX IF NOT EXISTS ix_tasks_plan ON tasks(plan_id);
CREATE INDEX IF NOT EXISTS ix_projects_user ON projects(user_id);
CREATE INDEX IF NOT EXISTS ix_notif_user ON notifications(user_id);
-- ===== Tambahan agar sesuai sistem Metta Career (lihat docs/DATABASE.md) =====
-- Terjemahan isi data (karier, skill, pertanyaan). Kolom asli = teks sumber, tabel ini = bahasa lain.
CREATE TABLE IF NOT EXISTS translations(
  entity TEXT NOT NULL, entity_id INTEGER NOT NULL, field TEXT NOT NULL,
  lang TEXT NOT NULL CHECK(lang IN('id','en')), value TEXT NOT NULL,
  PRIMARY KEY(entity, entity_id, field, lang));
-- Profil per peran
CREATE TABLE IF NOT EXISTS teacher_profiles(
  user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  kind TEXT NOT NULL DEFAULT 'JURUSAN' CHECK(kind IN('JURUSAN','BK')),
  major TEXT NOT NULL DEFAULT '' CHECK(major IN('','AK','TKJ')));
CREATE TABLE IF NOT EXISTS alumni_profiles(
  user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  graduation_year INTEGER, major TEXT NOT NULL DEFAULT '' CHECK(major IN('','AK','TKJ')),
  workplace TEXT NOT NULL DEFAULT '', job_title TEXT NOT NULL DEFAULT '', bio TEXT NOT NULL DEFAULT '');
-- Milestone per Career Plan (task.milestone menunjuk ke nomor di sini)
CREATE TABLE IF NOT EXISTS milestones(
  id INTEGER PRIMARY KEY, plan_id INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  number INTEGER NOT NULL, skill_id INTEGER REFERENCES skills(id), UNIQUE(plan_id, number));
-- Bukti dan masukan per project (satu project bisa punya banyak bukti dan banyak masukan)
CREATE TABLE IF NOT EXISTS project_evidence(
  id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  kind TEXT NOT NULL DEFAULT 'LINK' CHECK(kind IN('LINK','REPOSITORY','DEMO','DOCUMENT','OTHER')),
  url TEXT NOT NULL, label TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS project_feedback(
  id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  teacher_id INTEGER NOT NULL REFERENCES users(id), decision TEXT NOT NULL CHECK(decision IN('VERIFIED','NEEDS_REVISION','COMMENT')),
  note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT (datetime('now')));
-- Portfolio: prestasi, sertifikat, dan pengaturan siapa yang boleh melihat
CREATE TABLE IF NOT EXISTS achievements(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL, issuer TEXT NOT NULL DEFAULT '', achieved_on TEXT NOT NULL DEFAULT '',
  verified_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS certificates(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL, issuer TEXT NOT NULL DEFAULT '', issued_on TEXT NOT NULL DEFAULT '', url TEXT NOT NULL DEFAULT '',
  verified_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS portfolios(
  user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  visibility TEXT NOT NULL DEFAULT 'PRIVATE' CHECK(visibility IN('PRIVATE','LINK','PUBLIC')),
  slug TEXT UNIQUE, headline TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE INDEX IF NOT EXISTS ix_translations_lang ON translations(lang, entity);
CREATE INDEX IF NOT EXISTS ix_milestones_plan ON milestones(plan_id);
CREATE INDEX IF NOT EXISTS ix_evidence_project ON project_evidence(project_id);
CREATE INDEX IF NOT EXISTS ix_pfeedback_project ON project_feedback(project_id);
CREATE INDEX IF NOT EXISTS ix_achievements_user ON achievements(user_id);
CREATE INDEX IF NOT EXISTS ix_certificates_user ON certificates(user_id);
-- ===== Fase 2 (ekosistem): tabel sudah disiapkan supaya data tidak perlu dipindah nanti; fiturnya belum dibuka =====
-- Konten alumni: harus lewat moderasi admin sebelum tampil ke siswa.
CREATE TABLE IF NOT EXISTS alumni_content(
  id INTEGER PRIMARY KEY, author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK(kind IN('CAREER_STORY','EDUCATION','TIPS')),
  title TEXT NOT NULL, category TEXT NOT NULL DEFAULT '', body TEXT NOT NULL,
  career_id INTEGER REFERENCES careers(id) ON DELETE SET NULL, skill_id INTEGER REFERENCES skills(id) ON DELETE SET NULL,
  status TEXT NOT NULL DEFAULT 'DRAFT' CHECK(status IN('DRAFT','PENDING','PUBLISHED','REJECTED')),
  moderated_by INTEGER REFERENCES users(id), moderation_note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (datetime('now')), published_at TEXT);
CREATE INDEX IF NOT EXISTS ix_alumni_content_status ON alumni_content(status, kind);
-- Fitur Peluang dan Lamaran sudah dihapus dari sistem: bersihkan sisa tabel di database lama.
-- Kursus karier: 6 bab per karier (bab 1 materi, bab 2-5 latihan + kuis, bab 6 proyek + ujian akhir).
CREATE TABLE IF NOT EXISTS course_progress(
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, career_id INTEGER NOT NULL REFERENCES careers(id) ON DELETE CASCADE,
  chapter INTEGER NOT NULL CHECK(chapter BETWEEN 1 AND 6), opened_at TEXT NOT NULL DEFAULT (datetime('now')),
  note TEXT NOT NULL DEFAULT '', done_at TEXT, PRIMARY KEY(user_id, career_id, chapter));
CREATE TABLE IF NOT EXISTS course_attempts(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, career_id INTEGER NOT NULL REFERENCES careers(id) ON DELETE CASCADE,
  chapter INTEGER NOT NULL, qids TEXT NOT NULL, seed TEXT NOT NULL, score INTEGER, total INTEGER NOT NULL, passed INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')), finished_at TEXT);
CREATE INDEX IF NOT EXISTS ix_course_att ON course_attempts(user_id, career_id, chapter);
CREATE TABLE IF NOT EXISTS course_projects(
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, career_id INTEGER NOT NULL REFERENCES careers(id) ON DELETE CASCADE,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, PRIMARY KEY(user_id, career_id));
DROP TABLE IF EXISTS application_events;
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS opportunity_skills;
DROP TABLE IF EXISTS opportunities;
"""


class DB:
    def __init__(self, lang="en"):
        self.lang = lang; self._tr = None
        self.conn = sqlite3.connect(db_path(), check_same_thread=False, timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON"); self.conn.execute("PRAGMA busy_timeout=10000")
    def all(self, sql, *a): return [dict(r) for r in self.conn.execute(sql, a).fetchall()]
    def one(self, sql, *a):
        r = self.conn.execute(sql, a).fetchone(); return dict(r) if r else None
    def run(self, sql, *a): return self.conn.execute(sql, a).lastrowid
    def commit(self): self.conn.commit()
    def rollback(self): self.conn.rollback()
    def close(self): self.conn.close()
    def tr(self, entity, eid, field, default):
        """Teks dalam bahasa permintaan ini. Kalau belum ada terjemahannya, kembali ke teks sumber."""
        if self._tr is None:
            self._tr = {(r["entity"], r["entity_id"], r["field"]): r["value"]
                        for r in self.all("SELECT entity,entity_id,field,value FROM translations WHERE lang=?", self.lang)}
        return self._tr.get((entity, eid, field), default)

def migrate(d):
    """Tambahkan kolom baru ke database yang sudah berisi data, tanpa menghapus apa pun.
    Aman dijalankan berulang kali: kolom yang sudah ada dilewati."""
    tambahan = {
        # tabel: [(nama kolom, definisi SQL)]
        "careers": [("trend", "INTEGER NOT NULL DEFAULT 0"), ("is_new", "INTEGER NOT NULL DEFAULT 0")],   # tren global, baru ditambahkan
        "companies": [("sector", "TEXT NOT NULL DEFAULT ''"), ("sector_id", "TEXT NOT NULL DEFAULT ''"), ("about", "TEXT NOT NULL DEFAULT ''"),
                      ("about_id", "TEXT NOT NULL DEFAULT ''"), ("source", "TEXT NOT NULL DEFAULT ''"), ("verified", "INTEGER NOT NULL DEFAULT 0"),
                      ("sector_guess", "INTEGER NOT NULL DEFAULT 0"),
                      # tautan & info tambahan; status: approved (tampil), pending (diajukan siswa, menunggu guru), rejected
                      ("website", "TEXT NOT NULL DEFAULT ''"), ("instagram", "TEXT NOT NULL DEFAULT ''"), ("phone", "TEXT NOT NULL DEFAULT ''"),
                      ("tasks", "TEXT NOT NULL DEFAULT ''"), ("majors", "TEXT NOT NULL DEFAULT ''"), ("work_terms", "TEXT NOT NULL DEFAULT ''"),
                      ("status", "TEXT NOT NULL DEFAULT 'approved'"), ("submitted_by", "INTEGER"), ("review_note", "TEXT NOT NULL DEFAULT ''"),
                      ("submitted_at", "TEXT")],
        "projects": [("problem", "TEXT NOT NULL DEFAULT ''"), ("solution", "TEXT NOT NULL DEFAULT ''"), ("result", "TEXT NOT NULL DEFAULT ''"),
                     ("technology", "TEXT NOT NULL DEFAULT ''"), ("demo_url", "TEXT NOT NULL DEFAULT ''"), ("repo_url", "TEXT NOT NULL DEFAULT ''"),
                     ("doc_url", "TEXT NOT NULL DEFAULT ''")],
        "tasks": [("note", "TEXT NOT NULL DEFAULT ''")],
        "internship_choices": [("purpose", "TEXT NOT NULL DEFAULT ''")],
        "users": [("must_change_password", "INTEGER NOT NULL DEFAULT 0"),
                  ("lang", "TEXT NOT NULL DEFAULT 'id'")],           # bahasa tampilan pilihan pengguna: id / en
    }
    for tabel, kolom in tambahan.items():
        ada = {r[1] for r in d.conn.execute(f"PRAGMA table_info({tabel})")}
        for nama, definisi in kolom:
            if nama not in ada:
                d.conn.execute(f"ALTER TABLE {tabel} ADD COLUMN {nama} {definisi}")
    # Rencana lama belum punya baris milestone: bentuk dari tugas yang sudah ada (tidak mengubah tugasnya).
    d.conn.execute("""INSERT OR IGNORE INTO milestones(plan_id, number, skill_id)
                      SELECT plan_id, milestone, MIN(skill_id) FROM tasks GROUP BY plan_id, milestone""")
    # Sistem belajar: satu siswa hanya boleh punya SATU Career Plan aktif. Data lama yang terlanjur punya dua rencana aktif
    # dirapikan dulu (yang terbaru tetap aktif, sisanya diarsipkan, tidak ada yang dihapus), lalu dijaga oleh indeks unik.
    d.conn.execute("""UPDATE plans SET status='ARCHIVED' WHERE status='ACTIVE'
                      AND id NOT IN (SELECT MAX(id) FROM plans WHERE status='ACTIVE' GROUP BY user_id)""")
    d.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_plans_one_active ON plans(user_id) WHERE status='ACTIVE'")
    d.conn.execute("CREATE INDEX IF NOT EXISTS ix_plans_user ON plans(user_id, career_id, status)")
    d.conn.execute("CREATE INDEX IF NOT EXISTS ix_quiz_att ON quiz_attempts(user_id, skill_id)")

def init_db():
    d = DB(); d.conn.execute("PRAGMA journal_mode=WAL"); d.conn.executescript(SCHEMA); migrate(d); d.commit(); d.close()
    # the database holds personal data: only the account running the server may read it (no effect on Windows)
    for suffix in ("", "-wal", "-shm"):
        try: os.chmod(db_path() + suffix, 0o600)
        except OSError: pass
