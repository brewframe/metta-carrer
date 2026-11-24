# Metta Career

Platform pengembangan karier untuk siswa SMK Metta Maitreya. Siswa menemukan arah karier, melihat skill gap, belajar lewat roadmap, mengerjakan project, mendapat validasi guru, lalu memiliki portfolio yang bisa dibagikan.

Proyek tim **NEXTSTEPS (Kelompok 2)**, SMK Metta Maitreya.

## Ringkasan untuk reviewer

| Aspek | Isi |
|---|---|
| Alur utama | Self Discovery → rekomendasi karier → Career Plan → belajar → project → validasi guru → portfolio |
| Peran | Siswa, Guru, Alumni, Admin |
| Data | 100 karier, 171 skill, 20 pertanyaan Self Discovery, 100 course, 55 perusahaan magang |
| Rekomendasi | Berbasis aturan yang bisa dijelaskan: 35% minat + 25% kekuatan + 25% skill berbukti + 15% jurusan |
| Teknologi | Python, Starlette, SQLite, JavaScript biasa (tanpa build), uvicorn |
| Keamanan | Hash password scrypt, kontrol akses per peran, batas percobaan login, cek Origin, audit log, CSP |
| Pengujian | 147 tes otomatis (alur aplikasi, keamanan, belajar, portfolio, alumni, bahasa) |
| Bahasa | Indonesia dan Inggris |

**Kontribusi saya:** *(isi bagian ini: tulis tugas yang kamu kerjakan, misalnya desain tampilan, bagian kode tertentu, pengujian, atau dokumentasi)*

Desain: [wireframe, mockup, dan moodboard](docs/desain/README.md).

Lihat juga: [SECURITY.md](SECURITY.md) untuk hasil audit dan batasannya, [deploy/DEPLOY.md](deploy/DEPLOY.md) untuk cara pasang di server, dan [docs/DATABASE.md](docs/DATABASE.md) untuk skema data.

---

## Tentang aplikasi

Siswa → Self Discovery → rekomendasi karier → Career Plan → Learning → Project → validasi guru → Portfolio, plus pilihan magang (maks. 3).

## Cara menjalankan (komputer sendiri, untuk belajar)

```bash
python -m venv .venv
.venv\Scripts\activate            # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
run_dev.bat                        # Mac/Linux: ./run_dev.sh
```
Buka http://127.0.0.1:8000

`run_dev` mengaktifkan **akun demo** (hanya untuk komputer sendiri):

| Role    | Email             | Password        |
|---------|-------------------|-----------------|
| Student | student@metta.sch | Student#2026!   |
| Teacher | teacher@metta.sch | Teacher#2026!   |
| Admin   | admin@metta.sch   | Admin#2026!     |

`run_dev` juga mengisi **data contoh untuk presentasi** secara otomatis (`python -m metta.demo_data`): siswa dengan Career Plan,
project terverifikasi dan yang menunggu guru, ajuan tempat magang, dua siswa tambahan, serta cerita alumni. Aman dijalankan berkali-kali.
Untuk kembali ke data bersih: `reset_demo.bat` (menghapus `metta.db` lokal). Naskah presentasi: **docs/PANDUAN_DEMO.md**.

Menjalankan `uvicorn metta.app:app` langsung (tanpa `run_dev`) **tidak** membuat akun demo.
Buat akun sendiri dengan `python -m metta.create_user --email ... --name "..." --role admin`.

**Sebelum online, baca [SECURITY.md](SECURITY.md).**

## Variabel environment

| Nama | Fungsi |
|------|--------|
| `METTA_DB` | lokasi file database (default `metta.db`) |
| `METTA_SEED_DEMO` | `1` = buat akun demo (hanya development) |
| `METTA_ENV` | `production` = tolak start bila pengaturan tidak aman |
| `METTA_SECURE_COOKIE` | `1` = cookie hanya lewat HTTPS + HSTS (wajib online) |
| `METTA_REGISTER_CODE` | kode sekolah yang harus diisi saat siswa mendaftar |
| `METTA_REGISTER_LIMIT` | batas pendaftaran per jam per alamat (default 10) |
| `METTA_ALLOWED_HOSTS` | daftar nama situs yang diterima, pisah koma |
| `METTA_ALLOWED_ORIGINS` | asal tambahan yang boleh mengirim request (jarang perlu) |
| `METTA_MAX_BODY` | batas ukuran request dalam byte (default 65536) |

## Struktur folder

```
metta/
  app.py        aplikasi Starlette, header keamanan, static + SPA
  core.py       decorator @api: login cookie, cek role, validasi, transaksi DB
  db.py         skema SQLite + class DB
  security.py   hash password (scrypt), session, batas percobaan login
  engine.py     mesin rekomendasi (rule-based), plan, readiness, status siswa
  seed.py       data awal: 100 karier (seed_careers.py), skill, 20 pertanyaan, 55 perusahaan
  api/          auth.py, student.py, teacher.py, admin.py
  create_user.py, backup.py   buat akun pertama, backup database
  static/       frontend (HTML/CSS/JS biasa, tanpa build)
tests/test_*.py          147 tes otomatis, mencakup semua fitur
tests/test_security.py   tes keamanan (hak akses, serangan, batas, header)
```

## Cara kerja rekomendasi (bisa dijelaskan, bukan "kotak hitam")

`skor = 35% minat + 25% kekuatan + 25% skill yang sudah punya bukti + 15% kecocokan jurusan`

Setiap hasil punya alasan tertulis. AI hanya menyarankan; keputusan tetap di siswa.
Readiness = 50% tugas selesai + 50% skill yang sudah punya bukti.
Tingkat bukti skill: Self claimed → Learning → Project evidence → Teacher verified.

## Keamanan (ringkas)

Password di-hash scrypt dengan kebijakan password; sesi disimpan sebagai hash, cookie HttpOnly + SameSite (+ Secure online);
cek peran di setiap endpoint; batas percobaan login 3 lapis; kode pendaftaran; batas ukuran request; cek Origin; validasi input;
audit log; CSP ketat; semua DOM dibuat dengan `textContent`. Detail, hasil audit, dan keterbatasannya: **SECURITY.md**.

## Tes

```bash
pip install requests
python -m unittest discover -s tests -t . -v
```

## Lupa password

Tidak ada pengiriman email. Admin membuka **Users → Reset password**, sistem membuat password
sementara yang mudah dibacakan (contoh `womo-zewu-name-33`), dan pengguna wajib menggantinya saat
masuk. Rinciannya di `SECURITY.md` bagian 4.

## Tampilan

- Warna mengikuti palet sekolah: teal tua `#006D77`, teal `#00AFB9`, oranye `#FF6B3D`,
  peach `#FF9F68`, putih abu `#F5F5F5`, teks gelap `#10282B`. Semuanya didefinisikan sekali di
  `:root` dalam `metta/static/app.css`; jangan menulis kode warna langsung di tempat lain.
- Halaman depan (`landing.js` + `landing.css`) berupa panggung bergulir: tangga M 3D yang berputar, lingkaran portal yang membuka foto, bab foto 3D, angka dari database, dan footer. Foto ada di `metta/static/photos/`, logo di `metta/static/brand/`. Versi statis otomatis dipakai bila perangkat memilih "kurangi gerakan".
- Dua bahasa (ID/EN): teks layar ada di `i18n.js` + `lang.js`; teks buatan server di `metta/messages.py`. Dokumentasi database: `docs/DATABASE.md`.
- Semua animasi otomatis mati untuk pengguna yang menyalakan "kurangi gerakan" di perangkatnya.
- Angka di halaman depan (jumlah karier, perusahaan, pertanyaan) diambil dari database lewat
  `/api/public/stats`, **bukan ditulis tangan**, supaya tidak pernah menjanjikan isi yang belum ada.

## Batasan saat ini

- Database berisi 100 karier (39 Teknologi, 27 Keuangan, 10 Bisnis, 6 Industri, 5 Kreatif, 4 Kesehatan, 4 Energi, 3 Layanan, 2 Pendidikan),
  55 perusahaan magang, dan 20 pertanyaan Self Discovery. Gambaran kerja ditulis dari pengetahuan umum: **mintalah guru mengeceknya**.
  Database lama otomatis ditambah 90 karier baru saat server dijalankan; data siswa dan edit admin tidak tertimpa.
- Asisten AI masih berbasis aturan (tanpa LLM). LLM bisa ditambah nanti lewat API key.
- 55 perusahaan magang dari daftar sekolah; data yang belum terverifikasi ditandai dan bisa dilengkapi guru atau admin.
- Dibuat dengan Starlette (inti FastAPI). Pindah ke FastAPI mudah: logika di `metta/api/*` murni fungsi.
- SQLite cukup untuk 1 sekolah; untuk skala besar pindah ke PostgreSQL.


## Magang: tautan info dan tempat usulan siswa

- Setiap tempat magang punya tombol **Detail** dengan tautan di sebelahnya: Website / Instagram (jika sudah diketahui), **Cari di Instagram**, **Cari di Google**, dan **Buka di Peta**. Semuanya tautan biasa ke tab baru.
- Tombol **Tambah tempat magang sendiri** (kanan atas daftar): siswa mengisi alamat, bidang usaha, uraian, tugas harian, kontak, dan dari mana ia tahu. Ajuan berstatus *Menunggu guru*; hanya pengaju dan guru yang melihatnya, dan pengaju sudah boleh memilihnya.
- Guru/admin memeriksa di menu **Ajuan tempat magang**: setujui (otomatis terverifikasi, siswa diberi notifikasi), perbaiki data dulu, atau tolak dengan alasan. Maksimal 3 ajuan menunggu per siswa; nama kembar ditolak.

## Fitur baru (belajar, magang, bukti, project)
- **Belajar**: tiap tugas punya halaman `#/learn/<id>` berisi tujuan, langkah (dicentang), latihan, dan kuis. Kuis dinilai di server (lulus >= 70%), jawaban benar tidak dikirim ke browser, urutan pilihan diacak tiap percobaan. Aturan selesai: STUDY = semua langkah dicentang; PRACTICE = lulus kuis (atau catatan latihan >= 20 huruf untuk skill tanpa kuis tertulis); APPLY = sudah ada project dengan skill itu. Materi tertulis: 24 skill awal (ID/EN); skill lain memakai panduan umum.
- **Magang**: 55 DU/DI dari daftar sekolah. Hanya data yang ditemukan dari sumber web yang diisi (alamat, kegiatan, sumber); sisanya ditandai "belum terverifikasi" dan bisa dilengkapi admin. Siswa menulis tujuan per pilihan dan mengajak sampai 3 teman (nama + kelas). Tautan peta hanya tautan ke Google Maps.
- **Sertifikat, prestasi, project**: unggah PDF/PNG/JPG (maks 3 MB, dicek dari isi file, nama acak, hanya pemilik/guru/admin yang bisa membuka, tidak pernah masuk portofolio publik). Project punya kolom masalah, solusi, hasil, teknologi, tautan demo/kode/dokumen, dan lampiran file.
- File unggahan disimpan di folder `uploads/` di samping file database (ikut dibackup bersama database).


## Masuk sebagai guru, alumni, admin
Halaman masuk punya tab Siswa / Guru / Alumni / Admin. Akun demo (hanya komputer sendiri, `METTA_SEED_DEMO=1`): `teacher@metta.sch`, `alumni@metta.sch`, `admin@metta.sch`, `student@metta.sch`.
Untuk pemakaian nyata, buat admin pertama: `python -m metta.create_user --email ... --name ... --role admin`, lalu admin membuat akun guru dan alumni di menu Pengguna.

## Lupa password (tanpa email)
Siswa minta di `#/forgot` → guru (untuk siswa) atau admin menyetujui di menu "Permintaan password" → kode sekali pakai XXXX-XXXX (24 jam, maks 5 salah) → siswa membuat password baru di `#/reset`; semua sesi lama dicabut.
Admin tunggal yang lupa password: `python -m metta.reset_password --email ...`.

## Cerita alumni
Alumni menulis di `#/write` → kirim → admin moderasi di `#/moderation` (tolak wajib beri catatan) → terbit → siswa membaca di Cerita Alumni.

## Data perusahaan magang
(Fitur Peluang dan Lamaran sudah dihapus dari sistem; pilihan magang tetap ada di menu Internship.)
- Guru melengkapi alamat DU/DI yang belum terverifikasi di menu **Data perusahaan** (wajib menulis sumber). Tanda "terverifikasi" tetap hanya dari admin.
