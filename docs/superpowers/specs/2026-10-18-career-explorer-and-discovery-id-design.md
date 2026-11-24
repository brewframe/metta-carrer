# Spesifikasi: Self Discovery Bahasa Indonesia + Career Explorer 50 Karier

Tanggal: 2026-10-18 · Status: menunggu review pengguna · Bagian 1 dan 2 dari 3
(Bagian 3, Learning berbab dengan Gemini, punya spesifikasi sendiri setelah bagian ini selesai.)

## 1. Tujuan
Siswa mendapat rekomendasi dan informasi karier yang lebih luas, mendalam, dan berdasarkan data publik,
dalam bahasa Indonesia. Keberhasilan: (a) 50 karier tersedia dan semuanya lengkap, (b) setiap karier punya halaman detail
mendalam dengan sumber data yang bisa dicek, (c) Self Discovery dan hasilnya berbahasa Indonesia dan menghasilkan
rekomendasi yang beragam untuk jurusan AK maupun TKJ, (d) database lama pengguna ter-upgrade tanpa kehilangan data.

## 2. Keputusan yang sudah disepakati
- Total 50 karier = 10 lama + 40 baru, semua bidang di Indonesia, termasuk yang dekat dengan AK/TKJ.
- Bahasa Indonesia untuk: Self Discovery, Career Insight, Career Explorer (daftar, detail, bandingkan, shortlist),
  alasan rekomendasi dari mesin. Bagian lain tetap Inggris untuk sekarang. Halaman Learning menyusul di bagian 3.
- Tidak ada angka gaji per jabatan karena tidak ada sumber resmi terbuka. Yang ditampilkan: rata-rata upah **sektor** dari BPS,
  diberi label jelas bahwa itu rata-rata sektor, bukan gaji jabatan tersebut.
- Data permintaan hanya dari sumber yang sudah diriset (bagian 4.3). Karier tanpa data spesifik menampilkan
  "Belum ada data spesifik". Tidak ada angka yang dikarang.
- Isi deskriptif (gambaran kerja, tugas harian, jenjang) ditulis dari sumber umum dan **perlu dicek guru/alumni**. Halaman memuat catatan itu.

## 3. Di luar cakupan
Learning berbab dan Gemini (bagian 3), tombol bahasa ID/EN, halaman Learning/Plan berbahasa Indonesia, deadline tugas,
antarmuka admin untuk mengedit sinyal data dan sumber (cukup lewat seed pada tahap ini), gaji per jabatan.

## 4. Model data

### 4.1 Perubahan tabel `careers` (kolom baru, semua boleh kosong untuk data lama)
`slug` (unik), `day_in_life`, `soft_skills`, `tools`, `requirements` (syarat masuk untuk lulusan SMK), `certifications`,
`first_steps` (yang bisa dilakukan siswa kelas 11 sekarang), `career_path` (jenjang junior sampai senior), `challenges`,
`related` (nama karier terkait, dipisah koma), `sector` (kunci sektor BPS), `outlook` (`growing` | `stable` | `watch`),
`outlook_note`, `data_year`. Kolom lama (`description`, `responsibilities`, `education_path`, `example_projects`, `growth`,
`interest_tags`, `strength_tags`, `majors`) tetap dipakai.

### 4.2 Tabel baru (relasional)
- `data_sources(id, key unik, title, publisher, url, period)`
- `career_signals(id, career_id, source_id, label, value, match)` dengan `match` = `exact` (jabatan sama) atau `related` (bidang terkait)
- `sector_wages(sector unik, label, avg_wage_idr, source_id)` berisi 16 sektor BPS Februari 2026
- `questions` mendapat kolom `code` (unik) untuk upgrade yang aman

### 4.3 Sumber data yang boleh dipakai
Kemnaker lowongan s.d. Sep 2025 (Bisnis.com), WEF Future of Jobs 2025, BPS Sakernas Feb 2026 (upah sektor, via GoodStats),
BPS Mei 2026 pengangguran SMK (CNN Indonesia), proyeksi SERA Astra 2026 (ditandai "proyeksi, tanpa data angka"), OLX Q1 2026 (Okezone).
Setiap `career_signals.source_id` wajib menunjuk ke salah satu sumber ini.

### 4.4 Aturan outlook
`watch` bila ada sinyal WEF "menurun" (akuntan/auditor, asisten administrasi, kasir/klerikal). `growing` bila ada sinyal WEF "tumbuh cepat"
(exact atau related) atau proyeksi SERA. Selain itu `stable`. `outlook_note` menjelaskan alasannya dengan merujuk sinyal.

### 4.5 Kosakata tag (mesin rekomendasi)
Minat: `technology, finance, business, design, data, people` (lama) + `industry, service, health, education` (baru).
Kekuatan: `analytical, communication, creativity, detail, logical, problem_solving, technical` (lama) + `collaboration` (sudah ada di pertanyaan, dipakai juga di karier), `practical, empathy` (baru).
Jurusan: `AK`, `TKJ`, dan `ALL` (jalur SMK realistis untuk semua jurusan, dihitung cocok penuh).

## 5. Upgrade database lama (tanpa menghapus data)
- `migrate()` menambah kolom yang belum ada (cek `PRAGMA table_info`) dan membuat tabel baru. Aman dijalankan berulang.
- Seed berubah dari "isi jika kosong" menjadi **upsert**: skill berdasarkan nama, karier berdasarkan `slug`/nama, pertanyaan berdasarkan `code`.
- Karier lama: hanya kolom baru yang masih kosong yang diisi. Kolom yang sudah terisi (termasuk hasil edit admin) **tidak ditimpa**.
- Pertanyaan lama (20) dicocokkan lewat teks Inggris aslinya, diberi `code`, lalu teksnya diganti ke Indonesia. Jika teksnya sudah diedit admin, dibiarkan.
- Pertanyaan baru ditambah (total 30: 12 minat lama, 8 minat baru, 8 kekuatan lama, 2 kekuatan baru).
- Asesmen lama tetap valid. Jika ada pertanyaan yang belum dijawab, halaman hasil menampilkan ajakan "Ada pertanyaan baru, ulangi untuk hasil lebih akurat".

## 6. Konten seed
Paket `metta/seed_data/` dipecah per kelompok agar mudah dicek: `sources.py`, `skills.py`, `questions.py`, `legacy10.py`
(melengkapi 10 karier lama), `careers_tech.py`, `careers_finance.py`, `careers_business.py`, `careers_industry.py`, `careers_service.py`.
Skill bertambah dari 24 menjadi sekitar 60–80, dan setiap karier punya 4–7 skill dengan tingkat kepentingan 1–3.

## 7. API
- `GET /api/careers` menambah filter `outlook`, `major=me`, dan mengembalikan `outlook`, `sector` per kartu.
- `GET /api/careers/{id}` mengembalikan semua kolom baru, `signals` (dengan sumber), `sector_wage`, dan `sources`.
- Admin `POST/PUT /api/admin/careers` menerima kolom teks baru dan `outlook` (opsional). Sinyal dan sumber hanya lewat seed.
- `GET /api/student/insight` menambah `new_questions: bool`.

## 8. Antarmuka (Indonesia)
- **Self Discovery:** judul, petunjuk, skala 1–5 (Sangat tidak setuju … Sangat setuju), 30 pertanyaan, tombol, kotak skill. Progres "n dari 30".
- **Career Insight:** semua label, alasan rekomendasi dalam Indonesia.
- **Explorer:** pencarian, filter kategori, filter prospek (Tumbuh / Stabil / Perlu waspada), centang "Cocok dengan jurusan saya", badge prospek di kartu.
- **Detail karier** (urutan): ringkasan dan prospek; satu hari kerja; skill teknis (dengan level bukti siswa) dan non-teknis; tools; syarat masuk dan sertifikasi;
  langkah pertama untuk siswa; jenjang karier dan tantangan; panel data (sinyal + upah sektor + tautan sumber + tanggal);
  karier terkait; catatan "perlu dicek guru". Tombol: Jadikan target, Simpan shortlist.
- **Bandingkan** (maks. 3): menambah baris prospek, upah sektor, syarat masuk.

## 9. Pengujian dan kriteria selesai
1. Tes data: 50 karier unik; setiap karier punya semua kolom terisi dengan panjang minimum (ringkasan ≥ 300 karakter, satu hari kerja ≥ 200, jenjang ≥ 150);
   tag dalam kosakata; ≥ 4 skill valid; `related` menunjuk karier yang ada; semua sinyal merujuk sumber yang terdaftar;
   karier dengan sinyal WEF menurun berstatus `watch`.
2. Tes upgrade: DB versi lama (10 karier, 20 pertanyaan Inggris, ada siswa dan asesmen) di-upgrade: tidak ada data hilang, edit admin tidak tertimpa, pertanyaan jadi Indonesia, seed dua kali tidak menggandakan.
3. Tes mesin: jawaban sintetis per bidang menghasilkan karier teratas yang masuk akal (mis. minat finance + detail untuk jurusan AK memuat karier keuangan; minat industry + practical memuat karier teknik). Karier `ALL` tidak dirugikan.
4. Tes API dan hak akses: field baru ada; siswa tidak bisa mengubah karier; admin bisa.
5. Uji browser: Self Discovery 30 pertanyaan sampai hasil; Explorer filter; detail dengan panel data; bandingkan 3 karier; tampilan 1280px dan 390px tidak ada teks terpotong.
6. Tes lama (8 tes) tetap lolos.

## 10. Risiko
- Isi deskriptif ditulis dari pengetahuan umum dan bisa kurang tepat di konteks lokal. Mitigasi: label "perlu dicek", admin bisa mengedit, dan saya sarankan guru memeriksa per kelompok.
- Data sumber berubah. Mitigasi: setiap sinyal membawa periode data dan tautan.
- Dengan 50 karier dan tag baru, skor bisa terdistribusi rata. Mitigasi: tes mesin (bagian 9.3) dan penyesuaian bobot hanya bila tes gagal.
