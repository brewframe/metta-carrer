# Metta Career di artifact Claude

Versi web lengkap yang berjalan di dalam artifact Claude (tanpa server Python).

- `site/srv/` — backend: semua 106 rute API dari `metta/api/*.py` ditulis ulang dalam JavaScript, dengan aturan peran, validasi, dan pesan error yang sama.
- `site/data/base.db.txt` — database SQLite dasar (data contoh dan akun demo), dibuat oleh server Python asli lalu disimpan sebagai base64.
- `site/static/` — frontend asli (disalin dari `metta/static`, hanya jalur file dan pemanggil API yang diubah).
- Database: SQLite berjalan di browser (sql.js). Setiap perubahan dicatat sebagai "operasi"; keadaan = database dasar + semua operasi diputar ulang berurutan.
  Operasi disimpan di database bersama artifact (pengunjung yang login akun Claude dan boleh menulis) atau di browser itu sendiri (IndexedDB).
  Password, kode reset, dan password sementara tidak pernah ikut dicatat; yang dicatat hanya hasil hash-nya.

Uji:
- `node test/difftest.js` — skenario yang sama dijalankan ke server Python asli dan backend JS; jawaban API dan isi database akhir harus sama, lalu operasi diputar ulang dan harus identik.
- `node test/ui.js` — halaman dibuka di Chromium untuk semua peran (butuh Playwright).

Membangun ulang: jalankan `python3 build/assemble.py` setelah mengubah `metta/static`.
Keamanan: semua logika berjalan di browser pengunjung, jadi versi ini untuk demo, bukan untuk data sungguhan. Untuk dipakai sekolah, tetap gunakan server Python (run_dev.bat).
