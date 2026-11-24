# Database Metta Career

SQLite, 33 tabel, dibuat otomatis saat server pertama kali jalan (`metta/db.py`). Database lama dimigrasi tanpa menghapus data
(kolom baru ditambah dengan `ALTER TABLE`, tabel baru dengan `CREATE TABLE IF NOT EXISTS`). Kunci asing (`FOREIGN KEY`) aktif,
dan nilai status dibatasi dengan `CHECK` sehingga data yang salah ditolak oleh database sendiri.

Status: **aktif** = dipakai fitur yang sudah jalan · **siap** = tabel sudah ada dan dijaga constraint, fiturnya menyusul.

## Dari spesifikasi proyek ke tabel

| Entitas di spesifikasi | Tabel | Status |
|---|---|---|
| User, Role | `users` (kolom `role`: student, teacher, alumni, admin; `lang` id/en), `sessions` | aktif |
| StudentProfile | `student_profiles` | aktif |
| TeacherProfile | `teacher_profiles` (jenis JURUSAN/BK, jurusan) | siap |
| AlumniProfile | `alumni_profiles` | siap |
| IndustryProfile | belum ada, lihat catatan di bawah | fase 2 |
| Assessment, AssessmentResult | `questions`, `assessments` (jawaban + skor per minat/kekuatan) | aktif |
| Career, Skill, CareerSkill | `careers`, `skills`, `career_skills` (bobot `importance`) | aktif |
| CareerPlan | `plans` (alasan rekomendasi disimpan sebagai kode, ditampilkan sesuai bahasa) | aktif |
| LearningRoadmap, Milestone, Task | `milestones`, `tasks`, `student_skills` (tingkat bukti 1 sampai 4) | aktif |
| Project, ProjectEvidence, ProjectFeedback | `projects`, `project_evidence`, `project_feedback`, `feedback` (masukan guru ke siswa) | aktif |
| Portfolio | `portfolios` (PRIVATE/LINK/PUBLIC + kode tautan acak) | aktif |
| Achievement, Certificate | `achievements`, `certificates` (`verified_by` terisi saat guru memverifikasi) | aktif |
| AlumniContent | `alumni_content` (CAREER_STORY/EDUCATION/TIPS; DRAFT, PENDING, PUBLISHED, REJECTED + catatan admin) | aktif |
| AlumniProfile | `alumni_profiles` (angkatan, pekerjaan, bio) | aktif |
| Lupa password | `password_requests` (PENDING, APPROVED, DONE, REJECTED; kode disimpan sebagai hash, kedaluwarsa 24 jam, maks 5 salah) | aktif |
| Notification | `notifications` | aktif |
| AuditLog | `audit_log` (login, ganti password, aksi admin, berbagi portfolio, verifikasi) | aktif |

Tambahan di luar spesifikasi: `companies` (kolom `website`, `instagram`, `phone`, `tasks`, `majors`, `work_terms`; `status` = approved / pending / rejected, `submitted_by` = siswa pengaju, `review_note` = alasan guru) + `internship_choices` (daftar DU/DI dan 3 pilihan magang siswa), `shortlist` (karier tersimpan),
`readiness_log` (riwayat kesiapan untuk Career Outcome), `rate_events` (pembatas percobaan login dan tebakan tautan),
`translations` (isi karier, skill, dan pertanyaan dalam bahasa Indonesia; kolom aslinya menyimpan teks sumber Inggris).

## Aturan penting

- **Dua bahasa.** Teks sumber disimpan di kolom aslinya. Terjemahan ada di `translations (entity, entity_id, field, lang)`; kalau belum ada,
  yang tampil teks sumber. Tugas belajar dan alasan rekomendasi dibentuk saat dibaca, jadi ikut bahasa yang dipilih. Notifikasi disimpan dalam bahasa penerima saat dibuat.
- **Siswa hanya menyentuh datanya sendiri.** Setiap query siswa memakai `user_id` dari sesi, bukan dari input. Diuji di `tests/test_security.py`.
- **Portfolio publik** hanya memuat project terverifikasi, skill, prestasi, dan sertifikat. Email, catatan guru, dan id tidak pernah ikut.
- **Skill tidak otomatis valid.** `student_skills.level`: 1 klaim sendiri, 2 belajar, 3 bukti project, 4 diverifikasi guru.
- **Password** disimpan sebagai hash scrypt, token sesi sebagai hash. File database berizin 600.

## Catatan fase 2

Peran **industry** belum ada karena `users.role` dibatasi `CHECK(role IN('student','teacher','alumni','admin'))`. Menambah peran di SQLite berarti
membangun ulang tabel `users`; itu dikerjakan bersama fitur Industry Portal supaya satu migrasi saja.

## Cadangan

`python -m metta.backup` membuat salinan konsisten database (aman saat server berjalan). Simpan di tempat terpisah dari server.

## Data karier (100)
`careers.category` = bidang (Technology, Finance, Business, Industry, Creative, Health, Energy, Service, Education).
`careers.trend` = 1 untuk "Tren global", `careers.is_new` = 1 untuk "Baru ditambahkan". `careers.majors` = AK, TKJ, atau keduanya
("Semua jurusan"). Sumber data ada di `metta/seed_careers.py`; terjemahan Indonesia disimpan di tabel `translations`.
Seed bersifat upsert: aman dijalankan berulang dan aman untuk database lama.

## Kursus karier (learning)
Tabel `course_progress` (kemajuan bab per siswa), `course_attempts` (percobaan kuis; soal, urutan pilihan, dan skor), `course_projects` (project yang ditautkan ke bab 6).
Isi kursus **tidak** disimpan di database. Isinya ada di `metta/course/c_*.py` (satu kursus per karier, kunci = id karier) supaya kunci jawaban tidak pernah keluar dari server dan setiap kursus bisa ditinjau seperti kode.
Aturan tiap kursus dijaga `metta.course.validate()` dan diuji `tests/test_course.py`: 5 bab materi, 3 latihan per bab, 26 sampai 32 soal, minimal 45% soal level SMK, proyek akhir dengan 6+ kriteria, dan minimal 2 sumber https yang benar-benar dibaca. Kursus tanpa sumber tidak ditampilkan ke siswa.
Status isi: 20 dari 100 karier sudah punya kursus bersumber (id 1, 2, 3, 4, 5, 6, 8, 9, 16, 19, 22, 23, 24, 54, 55, 56, 64, 65, 66, 96). Sisanya tampil sebagai "belum ada kursus", bukan diisi teks asal-asalan.

### Aturan soal supaya jawaban tidak bisa ditebak
- Siswa yang gagal kuis (bab, ujian akhir, atau kuis tugas) hanya melihat skor. Benar/salah per soal, jawaban, dan penjelasan baru dibuka setelah lulus. Ujian akhir yang gagal hanya menyebut bab yang perlu dibaca ulang.
- Kuis tugas punya jeda setelah gagal (kelipatan jeda dasar, naik bila sering gagal dalam 10 menit).
- `validate()` menolak kursus yang jawaban benarnya paling panjang sendirian di lebih dari 45% soal (secara kebetulan sekitar 25 sampai 30%).
- Urutan pilihan diacak di server pada setiap percobaan.
