"""Pemeriksaan kesiapan sebelum web dibuka ke internet.

    python -m metta.preflight                 -> periksa semua, tampilkan OK / PERINGATAN / GAGAL
    python -m metta.preflight --remove-demo   -> hapus akun demo yang password-nya masih yang diketahui, lalu periksa

Kode keluar 0 bila tidak ada yang GAGAL, 1 bila ada. Aman dijalankan kapan saja (hanya membaca, kecuali --remove-demo)."""
import os, sqlite3, sys, time
from .db import db_path, DB
from .security import verify_password, production, secure_cookie
from .seed import DEMO

OK, WARN, FAIL = "OK", "PERINGATAN", "GAGAL"


def remove_demo(d):
    """Hapus akun demo hanya bila password-nya MASIH password demo (akun asli dengan email yang sama tidak disentuh)."""
    gone = []
    for email, _, _, pw in DEMO:
        u = d.one("SELECT id,password_hash FROM users WHERE email=?", email)
        if u and verify_password(pw, u["password_hash"]):
            d.run("DELETE FROM users WHERE id=?", u["id"]); gone.append(email)
    if gone: d.run("INSERT INTO audit_log(actor_id,action,detail) VALUES(NULL,'demo_removed',?)", ",".join(gone)); d.commit()
    return gone


def check_db_file(path):
    """Cek integritas file SQLite (bisa dipakai juga untuk berkas cadangan). Mengembalikan daftar masalah."""
    probs = []
    try:
        c = sqlite3.connect("file:" + path + "?mode=ro", uri=True)
        try:
            r = [x[0] for x in c.execute("PRAGMA integrity_check").fetchall()]
            if r != ["ok"]: probs.append("integrity_check: " + "; ".join(r[:3]))
            fk = c.execute("PRAGMA foreign_key_check").fetchall()
            if fk: probs.append(f"foreign_key_check: {len(fk)} baris menunjuk data yang tidak ada")
            if not c.execute("SELECT 1 FROM sqlite_master WHERE name='users'").fetchone(): probs.append("tabel users tidak ada")
        finally: c.close()
    except sqlite3.Error as e: probs.append("tidak bisa dibuka: " + str(e))
    return probs


def run(remove=False):
    out = []
    add = lambda s, t: out.append((s, t))
    env = os.environ.get
    add(OK if production() else FAIL, "METTA_ENV=production" + ("" if production() else " belum diatur"))
    add(OK if secure_cookie() else FAIL, "METTA_SECURE_COOKIE=1 (cookie hanya lewat HTTPS)" + ("" if secure_cookie() else " belum diatur"))
    add(OK if env("METTA_ALLOWED_HOSTS") else FAIL, "METTA_ALLOWED_HOSTS" + (" diatur" if env("METTA_ALLOWED_HOSTS") else " belum diatur (tolak Host palsu)"))
    code = env("METTA_REGISTER_CODE", "")
    add(OK if len(code) >= 8 else FAIL, "METTA_REGISTER_CODE " + ("diatur" if len(code) >= 8 else "belum diatur atau kurang dari 8 karakter: siapa pun bisa membuat akun siswa"))
    add(FAIL if env("METTA_SEED_DEMO") == "1" else OK, "METTA_SEED_DEMO " + ("=1: AKUN DEMO AKAN DIBUAT. Hapus variabel ini" if env("METTA_SEED_DEMO") == "1" else "tidak aktif"))
    path = db_path()
    if not os.path.exists(path):
        add(FAIL, "database tidak ditemukan: " + path); return out
    if os.name == "posix":
        mode = os.stat(path).st_mode & 0o777
        add(OK if mode & 0o077 == 0 else FAIL, f"izin file database {oct(mode)}" + ("" if mode & 0o077 == 0 else " (harus 600: hanya pemilik yang boleh membaca)"))
        add(WARN if os.geteuid() == 0 else OK, "server dijalankan sebagai root (sebaiknya user biasa)" if os.geteuid() == 0 else "server tidak berjalan sebagai root")
    probs = check_db_file(path)
    add(FAIL if probs else OK, "integritas database: " + ("; ".join(probs) if probs else "baik"))
    d = DB()
    try:
        if remove:
            for e in remove_demo(d): add(OK, "akun demo dihapus: " + e)
        weak = [e for e, _, _, pw in DEMO if (u := d.one("SELECT password_hash FROM users WHERE email=?", e)) and verify_password(pw, u["password_hash"])]
        add(FAIL if weak else OK, "akun demo dengan password yang diketahui: " + (", ".join(weak) + " (jalankan dengan --remove-demo)" if weak else "tidak ada"))
        n = d.one("SELECT COUNT(*) n FROM users WHERE role='admin' AND active=1")["n"]
        add(OK if n else FAIL, f"admin aktif: {n}" + ("" if n else " (buat dengan python -m metta.create_user)"))
        must = d.one("SELECT COUNT(*) n FROM users WHERE must_change_password=1")["n"]
        if must: add(WARN, f"{must} akun masih harus mengganti password sementara")
    finally: d.close()
    bdir = env("METTA_BACKUP_DIR", "backups")
    files = sorted(f for f in os.listdir(bdir) if f.startswith("metta-") and f.endswith(".db")) if os.path.isdir(bdir) else []
    if not files: add(WARN, "belum ada cadangan database di folder " + bdir + " (jalankan python -m metta.backup)")
    else:
        age = (time.time() - os.path.getmtime(os.path.join(bdir, files[-1]))) / 3600
        add(OK if age < 48 else WARN, f"cadangan terbaru {age:.0f} jam lalu ({files[-1]})")
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    res = run("--remove-demo" in argv)
    for s, t in res: print(f"[{s:^10}] {t}")
    bad = sum(1 for s, _ in res if s == FAIL); warn = sum(1 for s, _ in res if s == WARN)
    print(f"\n{bad} GAGAL, {warn} peringatan." + (" Jangan dibuka ke internet dulu." if bad else " Siap."))
    return 1 if bad else 0


if __name__ == "__main__": sys.exit(main())
