# Panduan Demo Presentasi Metta Career

Untuk laptop Windows, dijalankan dari CMD. Total demo sekitar 10 menit.

## A. Malam sebelumnya (sekali saja, butuh internet)

1. Ekstrak `Metta-Career.zip`, buka CMD di folder `metta-career-app`.
2. Jalankan:
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   run_dev.bat
   ```
3. Tunggu sampai CMD menulis `Selesai. Buka http://127.0.0.1:8000`. Data demo sudah terisi otomatis.
4. Buka http://127.0.0.1:8000 dan **latih alur di bagian C minimal satu kali**.
5. Setelah latihan, jalankan `reset_demo.bat` (ketik `YA`) agar data kembali bersih untuk besok.

## B. 30 menit sebelum presentasi

1. Buka CMD di folder proyek, lalu:
   ```cmd
   .venv\Scripts\activate
   run_dev.bat
   ```
2. Buka **empat jendela browser**, satu per role, agar tidak perlu logout-login di depan juri:
   - Jendela biasa: **Siswa** `student@metta.sch` / `Student#2026!`
   - Jendela Incognito (Ctrl+Shift+N): **Guru** `teacher@metta.sch` / `Teacher#2026!`
   - Browser lain (misalnya Edge biasa): **Admin** `admin@metta.sch` / `Admin#2026!`
   - Edge InPrivate: **Alumni** `alumni@metta.sch` / `Alumni#2026!` (opsional)
3. Zoom browser 110% supaya tulisan terbaca dari belakang ruangan.
4. Matikan notifikasi Windows (Focus assist) dan tutup aplikasi lain.

## C. Alur demo (sekitar 10 menit)

### 1. Siswa: dari potensi ke rencana (4 menit)
| Klik | Yang ditunjukkan | Kalimat kunci |
|---|---|---|
| Dashboard | Target karier, kesiapan karier, tugas hari ini, pilihan magang | "Dashboard fokus ke aksi, bukan hanya angka." |
| Self Discovery | Hasil: beberapa kemungkinan karier dan alasannya | "AI tidak memutuskan. Ia memberi beberapa pilihan dan menjelaskan alasannya." |
| Jelajah, lalu buka satu karier | Skill, jalur pendidikan, contoh project | "Siswa bisa membandingkan karier sebelum memilih." |
| Career Plan | Skill gap, milestone, catatan guru | "Siswa memilih Network Engineer sendiri. Keputusan tetap di siswa." |
| Belajar, lalu Mulai kursus | Bab, materi, latihan, kuis, sumber (tanpa catatan wajib) | "Setiap kursus punya sumber yang bisa dicek, bukan karangan." |
| Project | Project 1 Terverifikasi, Project 2 Menunggu guru | "Skill tidak dianggap valid hanya karena diklaim." |
| Portfolio | Project terverifikasi terkumpul otomatis, bisa dibagikan | |
| Asisten Karier AI | Tanya: *Apa langkah saya berikutnya?* | "Jawabannya langkah konkret berdasarkan data siswa." |

### 2. Magang (2 menit)
| Klik | Yang ditunjukkan |
|---|---|
| Siswa: Magang | Tombol Detail, Situs web, Cari di Google/Instagram, Peta di tiap perusahaan |
| Siswa: kolom kanan **Tambah tempat magang sendiri** | Isi info tempat, deskripsi, tugas harian, dan kontak, lalu kirim. Tempat baru muncul di daftar dengan status "Menunggu guru" |
| Guru: Ajuan tempat magang | Ajuan "CV Teknik Nusantara (contoh)". Tunjukkan tombol cek Google/Instagram, lalu **Setujui dan verifikasi** |

Kalimat kunci: "Data perusahaan baru tidak langsung dipercaya. Guru memverifikasi dulu."

### 3. Guru (2 menit)
| Klik | Yang ditunjukkan |
|---|---|
| Dashboard | Siswa yang perlu perhatian tampil paling atas (Budi belum punya rencana) |
| Validasi | Project "Pemantau Suhu Ruang Server": isi catatan lalu **Tandai Terverifikasi** |
| Siswa, lalu buka Student Demo | Profil, Career Plan, progres, beri masukan |
| Analitik | Diagram batang: kesiapan karier per kelas dan jurusan (skala 0-100%), status siswa, status project, target karier. Arahkan kursor ke batang untuk detail; **Lihat tabel** untuk angka |

### 4. Admin dan keamanan (2 menit)
| Klik | Yang ditunjukkan |
|---|---|
| Konten alumni | "Tips sebelum magang" menunggu moderasi, lalu **Terbitkan** |
| Siswa (jendela siswa): Cerita Alumni | Konten yang baru terbit langsung muncul |
| Pengguna | Admin membuat akun guru/alumni; siswa mendaftar sendiri |
| Analitik | Diagram batang pengguna per peran, siswa per jurusan, status project, pilihan magang. Gulir ke **Log audit**: setiap tindakan tercatat |

Demo keamanan 10 detik: di jendela **siswa**, ketik alamat `http://127.0.0.1:8000/#/users` (halaman milik admin). Yang muncul hanya "Halaman tidak ditemukan", dan server menolak permintaan datanya (kode 403).

Kalimat keamanan (cukup sebut 3 hal):
1. Password disimpan dalam bentuk hash scrypt, bukan teks asli.
2. Setiap role hanya bisa membuka datanya sendiri. Contoh: siswa tidak bisa membuka halaman admin.
3. Ada batas percobaan login, log audit, dan pemeriksa keamanan sebelum online (`python -m metta.preflight`).

## D. Kalau ada masalah saat presentasi

| Masalah | Solusi cepat |
|---|---|
| Halaman blank, macet, atau muncul pesan "... is not a function" | Tekan F5 sekali. Aplikasi juga memperbaiki cache-nya sendiri secara otomatis. |
| Lupa logout atau salah akun | Pakai jendela browser lain yang sudah login (bagian B langkah 2). |
| CMD tertutup tidak sengaja | Buka CMD lagi, `.venv\Scripts\activate`, `run_dev.bat`. |
| Data berantakan setelah latihan | `reset_demo.bat`, ketik `YA`. |
| Kuis gagal saat demo | Wajar: tombol **Coba lagi** langsung aktif dan soal diacak ulang. Pembahasan hanya muncul setelah lulus, supaya jawaban tidak bisa ditebak. |
| Port 8000 dipakai | `set METTA_SEED_DEMO=1` lalu `python -m uvicorn metta.app:app --port 8001`, buka http://127.0.0.1:8001 |
| Tombol sudah ditekan saat latihan (misalnya ajuan sudah disetujui) | `reset_demo.bat` sebelum tampil. |

## E. Pertanyaan juri yang mungkin muncul (jawab jujur)

- **"AI-nya pakai apa?"** Rekomendasi memakai aturan yang bisa dijelaskan: 35% minat, 25% kekuatan, 25% skill yang sudah punya bukti, dan 15% kecocokan jurusan. Sengaja tidak memakai "kotak hitam" agar alasannya bisa dibaca siswa dan guru. Model bahasa bisa ditambahkan di fase berikutnya.
- **"Apakah semua karier sudah ada kursusnya?"** Ya. Semua 100 karier sudah punya kursus lengkap (5 bab, proyek, 28 soal, 12 tugas praktik, dan minimal 2 link sumber), mencakup jurusan TKJ, AK, kesehatan (perawat, asisten apoteker, analis lab, rekam medis), guru, teknik (listrik, otomotif, mesin, robotika, kendaraan listrik, energi terbarukan, panel surya, insinyur lingkungan), kuliner dan perhotelan, serta teknologi baru seperti AR/VR. Karier berisiko (listrik, otomotif, mesin, kendaraan listrik, panel surya, energi terbarukan, kesehatan) hanya diajarkan sebagai latihan di atas kertas atau dengan pengawasan guru. Isi kursus tetap sebaiknya diperiksa guru jurusan, dan sebagian sumber berasal dari luar negeri sehingga ditandai di tiap kursus.
- **"Data perusahaan dan alumni asli?"** 55 tempat PKL diambil dari daftar sekolah. Tempat yang datanya belum bisa dicek dari sumber publik ditandai "belum terverifikasi" dan bisa dilengkapi guru. Data bertanda "(contoh)" hanya data demo presentasi.
- **"Sudah bisa online?"** Belum dibuka ke publik. Sebelum online, akun demo dihapus, HTTPS diaktifkan, dan pemeriksa `preflight` harus lulus. Langkahnya ada di `deploy/DEPLOY.md`.
- **"Bagaimana privasi siswa?"** Guru hanya melihat data yang perlu untuk membimbing, dan semua tindakan admin tercatat di log audit.
