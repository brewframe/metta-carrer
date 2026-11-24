# Keamanan Metta Career

Dokumen ini menjelaskan apa yang sudah diamankan, apa yang **belum**, dan langkah wajib sebelum web dipakai online.
Tidak ada web yang 100% aman. Tujuannya: menutup celah umum, membatasi dampak kalau ada yang lolos, dan jujur soal batasnya.

## 1. Hasil audit (celah yang ditemukan lalu ditutup)

| # | Celah yang ditemukan | Risiko | Perbaikan |
|---|---|---|---|
| 1 | Akun demo dengan password yang diketahui aktif secara bawaan | **Kritis**: siapa pun bisa login sebagai admin | Akun demo hanya dibuat bila `METTA_SEED_DEMO=1`. Mode production menolak start bila akun demo ada. Admin pertama dibuat dengan `python -m metta.create_user` |
| 2 | Pendaftaran terbuka tanpa batas | Tinggi: orang luar membuat akun, spam, masuk daftar siswa guru | Kode pendaftaran sekolah (`METTA_REGISTER_CODE`) + batas 10 pendaftaran/jam per alamat |
| 3 | Body request 20 MB diterima penuh | Tinggi: server bisa dibuat kehabisan memori | Batas 64 KB, jawaban 413 |
| 4 | Tidak ada cek asal request (CSRF hanya mengandalkan SameSite) | Tinggi | Cek `Origin` dan `Sec-Fetch-Site`, wajib `Content-Type: application/json` |
| 5 | Batas percobaan login lemah (hanya alamat+email, di memori) | Tinggi: tebak password massal | 3 lapis di database: 6/5 menit per alamat+akun, 10/15 menit per akun, 30/15 menit per alamat. Berlaku juga untuk ganti password |
| 6 | Password lemah diterima (`12345678`) | Sedang | Kebijakan password: daftar password umum, tidak boleh mengandung nama/email, guru dan admin minimal 12 karakter |
| 7 | Waktu respons membedakan email yang terdaftar (37 ms vs 2 ms) | Sedang: akun bisa ditebak | Verifikasi tiruan agar waktunya sama |
| 8 | Header kurang (HSTS, Permissions-Policy, COOP/CORP), cookie tidak Secure | Sedang | Semua ditambahkan. CSP juga melarang `object`, `base`, `form` luar |
| 9 | Sesi kedaluwarsa menumpuk, tanpa batas jumlah | Sedang | Dibersihkan saat login, maksimal 5 sesi per akun, sesi guru/admin 12 jam |
| 10 | Link bukti proyek menerima spasi dan bentuk aneh | Rendah | Validasi URL (hanya http/https dengan nama situs) |
| 11 | Login tidak tercatat | Sedang | `login_ok`, `login_fail`, `login_blocked` masuk audit log (tanpa password) |
| 12 | File database bisa dibaca akun lain di server | Sedang | Izin file 600 |
| 13 | Versi paket tidak dibatasi | Rendah | Rentang versi + `requirements-tested.txt` |

**Yang sudah baik sejak awal dan tetap diuji:** pengecekan hak akses di setiap endpoint, siswa tidak bisa membuka data siswa lain (IDOR), password di-hash scrypt, token sesi disimpan sebagai hash, cookie HttpOnly + SameSite, semua query SQL memakai parameter, tampilan dibuat dengan `textContent` (anti XSS), CSP tanpa script inline, tidak ada upload file.

Semuanya diuji otomatis di `tests/test_security.py` (28 tes, termasuk matriks seluruh rute × peran).

### Tambahan: portfolio yang bisa dibagikan
- Portfolio **privat secara bawaan**. Tautan memakai kode acak 16 karakter (96 bit), bisa dicabut dengan membuat tautan baru.
- Halaman publik tidak memuat email, catatan guru, atau id. Hanya project terverifikasi, skill, prestasi, dan sertifikat.
- Tebakan tautan salah dibatasi (30 per 10 menit per alamat). Semua teks tampil lewat `textContent`; tautan hanya http/https.
- Prestasi dan sertifikat buatan siswa ditandai **Klaim sendiri** sampai guru memverifikasi.
- Diuji di `tests/test_portfolio.py`.

## 2. Yang BELUM ada (batas yang perlu Anda tahu)

- **Tidak ada verifikasi email.** Lupa password ditangani admin, bukan lewat email (lihat bagian 5).
- **Tidak ada 2FA** untuk admin dan guru. Gunakan password panjang dan unik.
- **Belum diuji penetration test oleh pihak luar.** Audit ini dilakukan oleh saya (kode + serangan uji), bukan pengganti ahli keamanan.
- **CSP masih mengizinkan `style` inline** karena tampilan memakai atribut style. Risiko kecil, tapi bukan nol.
- **Kunci Gemini** (nanti) hanya boleh di environment server, tidak pernah di kode atau browser.
- **Data pribadi siswa** (nama, kelas, hasil asesmen). Sebelum dipakai resmi, tanyakan ke sekolah soal izin orang tua/wali dan kewajiban perlindungan data pribadi (UU PDP). Saya bukan penasihat hukum.
- Guru melihat **semua** siswa (keputusan Anda). Bila nanti perlu dibatasi per kelas, itu perubahan terpisah.

## 3. Checklist sebelum online (wajib semua)

1. **Pakai HTTPS.** Cara termudah: Caddy (sertifikat otomatis). Isi `Caddyfile`:
   ```
   metta.namasekolah.sch.id {
       reverse_proxy 127.0.0.1:8000
   }
   ```
2. **Jalankan dengan pengaturan production** (Linux):
   ```
   export METTA_ENV=production
   export METTA_SECURE_COOKIE=1
   export METTA_ALLOWED_HOSTS=metta.namasekolah.sch.id
   export METTA_REGISTER_CODE="isi-kode-rahasia-sekolah"
   export METTA_DB=/var/lib/metta/metta.db
   python -m uvicorn metta.app:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips 127.0.0.1 --no-server-header --workers 2
   ```
   Server menolak start kalau `METTA_SECURE_COOKIE=1` tidak ada, atau akun demo masih ada.
3. **Buat admin pertama** dan jangan pernah memakai `METTA_SEED_DEMO=1` di server online:
   ```
   python -m metta.create_user --email kepala@namasekolah.sch.id --name "Nama Admin" --role admin
   ```
4. **Hapus akun demo** bila database lama pernah dibuat dengan demo (menu Users → Deactivate, atau mulai database baru).
5. **Firewall:** buka hanya port 80 dan 443. Port 8000 hanya untuk localhost.
6. **Jalankan sebagai user biasa**, bukan root. Folder database hanya bisa dibaca user itu.
7. **Backup harian:** `python -m metta.backup` dijadwalkan, lalu salin folder `backups/` ke tempat lain (flashdisk/Drive sekolah). Tes sekali: pulihkan salinan di komputer lain.
8. **Pembaruan:** `pip install -r requirements-tested.txt --upgrade` secara berkala, lalu jalankan semua tes.
9. **Bagikan kode pendaftaran hanya ke siswa** (lewat guru), dan ganti kodenya tiap tahun ajaran.

## 4. Lupa password (reset oleh admin)

Tidak ada pengiriman email, jadi akun yang lupa password dipulihkan admin lewat menu **Users →
Reset password**. Yang terjadi saat tombol itu ditekan:

1. Sistem membuat password sementara acak, contoh `womo-zewu-name-33` (3 suku kata + 2 angka,
   sekitar 60 bit; huruf `i`, `l`, `o` dan angka `0`, `1` tidak dipakai supaya tidak salah baca).
2. Password sementara **hanya tampil sekali** di layar admin. Yang disimpan di database hanya
   hash-nya, sama seperti password biasa.
3. Password lama langsung tidak berlaku dan **semua sesi pengguna itu diputus** di semua perangkat.
4. Saat masuk, pengguna **wajib** membuat password sendiri sebelum bisa membuka halaman lain.
5. Kejadiannya dicatat di audit log sebagai `password_reset` beserta email akunnya (bukan passwordnya).

Aturan yang dijaga: admin tidak bisa mereset password dirinya sendiri (pakai Settings), guru dan
siswa tidak bisa mereset password siapa pun, dan tamu tanpa login ditolak. Semua ini diuji di
`tests/test_reset.py`.

**Prosedur yang disarankan untuk sekolah:** siswa datang langsung ke guru/admin (bukan lewat chat),
admin mencocokkan wajah atau kartu pelajar dulu, baru membacakan password sementara. Jangan kirim
password sementara lewat grup WhatsApp.

## 5. Kalau terjadi masalah

- **Dicurigai ada yang masuk:** ganti `METTA_REGISTER_CODE`, minta semua guru/admin ganti password (semua sesi lain otomatis keluar), periksa menu audit untuk `login_fail` / `login_blocked` yang banyak, lalu restore dari backup bila data berubah.
- **Akun siswa disalahgunakan:** admin → Users → Deactivate (sesinya langsung dihapus).
- **Menemukan celah:** jangan umumkan dulu. Laporkan ke saya atau guru pembimbing, dengan langkah mengulanginya.

## 6. Alat operasional (ditambahkan kemudian)

| Alat | Fungsi |
|---|---|
| `python -m metta.preflight` | Memeriksa kesiapan produksi: pengaturan lingkungan, izin file, integritas database, akun demo, admin, umur cadangan. Kode keluar 1 bila ada yang GAGAL |
| `python -m metta.preflight --remove-demo` | Menghapus akun demo **hanya bila password-nya masih password demo** (akun asli dengan email sama tidak disentuh) |
| `python -m metta.backup` | Cadangan **diperiksa** (integrity_check) dan diberi checksum SHA-256. Cadangan rusak dihapus dan perintah gagal, jadi tidak menggantikan cadangan yang baik. Folder cadangan izin 700 |
| `python -m metta.restore <berkas> --yes` | Memeriksa checksum dan integritas dulu, menyimpan database sekarang sebagai `.sebelum-pulih-<waktu>`, baru memulihkan |
| `deploy/` | Caddyfile (HTTPS otomatis), unit systemd dengan pengerasan (tanpa hak istimewa, hanya boleh menulis `/var/lib/metta`), cadangan harian, dan `DEPLOY.md` langkah demi langkah |

Tambahan lain: ajuan tempat magang dari siswa dibatasi 10 per jam dan 3 yang menunggu; tautan, Instagram, dan telepon yang diisi dibersihkan di server (hanya http/https, tanpa nama pengguna di tautan). Diuji di `tests/test_ops.py` dan `tests/test_company_proposal.py`.

**Batas yang jujur:** database masih SQLite satu file. Untuk satu sekolah ini cukup (mode WAL, 2 proses), tetapi bila pemakai mencapai ribuan serentak, pindah ke PostgreSQL. Cadangan belum dienkripsi; simpan di tempat yang aman. Pemindaian kerentanan paket (`pip-audit`) belum dijalankan dari sini karena tidak ada akses jaringan ke database kerentanan; jalankan di server.
