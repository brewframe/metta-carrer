# Memasang Metta Career di server (Ubuntu/Debian)

Waktu sekitar 30 menit. Semua perintah sebagai `root` atau dengan `sudo`.

## 1. Siapkan server
```
apt update && apt install -y python3-venv caddy ufw
ufw default deny incoming && ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable
useradd --system --create-home --home-dir /var/lib/metta --shell /usr/sbin/nologin metta
mkdir -p /opt /etc/metta && chmod 700 /var/lib/metta
```
Port 8000 **tidak** dibuka ke luar; hanya Caddy (port 443) yang menghubunginya.

## 2. Pasang aplikasi
```
unzip Metta-Career.zip -d /opt && chown -R root:root /opt/metta-career-app
cd /opt/metta-career-app && python3 -m venv .venv && .venv/bin/pip install -r requirements-tested.txt
```

## 3. Pengaturan rahasia
```
cp deploy/metta.env.example /etc/metta/metta.env && chmod 600 /etc/metta/metta.env && nano /etc/metta/metta.env
```
Isi `METTA_ALLOWED_HOSTS` dengan alamat web sekolah dan `METTA_REGISTER_CODE` dengan kode acak (minimal 8 karakter). Jangan pakai `METTA_SEED_DEMO`.

## 4. Admin pertama
```
sudo -u metta bash -c 'set -a; . /etc/metta/metta.env; set +a; cd /opt/metta-career-app && .venv/bin/python -m metta.create_user --email kepala@namasekolah.sch.id --name "Nama Admin" --role admin'
```
Password minimal 12 karakter, tidak boleh yang umum.

## 5. Jalankan
```
cp deploy/metta.service deploy/metta-backup.service deploy/metta-backup.timer /etc/systemd/system/
cp deploy/Caddyfile /etc/caddy/Caddyfile && nano /etc/caddy/Caddyfile   # ganti alamat web
systemctl daemon-reload && systemctl enable --now metta metta-backup.timer && systemctl restart caddy
```

## 6. Periksa kesiapan (WAJIB sebelum diumumkan)
```
sudo -u metta bash -c 'set -a; . /etc/metta/metta.env; set +a; cd /opt/metta-career-app && .venv/bin/python -m metta.preflight'
```
Semua baris harus `OK` (peringatan boleh dibaca dulu). Jika ada `GAGAL`, perbaiki, jangan buka ke siswa.
Jika ada akun demo: tambahkan `--remove-demo`.

## 7. Cadangan dan pemulihan
- Cadangan otomatis tiap 02:30 ke `/var/lib/metta/backups` (14 terbaru, diperiksa integritasnya, ada checksum).
- **Salin folder itu ke tempat lain** (Drive sekolah / flashdisk) tiap minggu.
- Pulihkan: `systemctl stop metta`, lalu `python -m metta.restore <berkas> --yes`, lalu `systemctl start metta`.
- Uji pemulihan sekali di komputer lain **sebelum** butuh.

## 8. Rutin
- Tiap bulan: `pip install -r requirements-tested.txt --upgrade`, jalankan tes, restart.
- Tiap minggu: lihat menu Audit di admin (`login_blocked`, `login_fail` yang banyak = ada yang menebak password).
- Ganti `METTA_REGISTER_CODE` tiap tahun ajaran.
