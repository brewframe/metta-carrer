"""Salinan database yang aman (bisa dijalankan saat server hidup) dan DIPERIKSA setelah dibuat.
    python -m metta.backup            -> backups/metta-YYYYMMDD-HHMMSS.db (+ .sha256), simpan 14 terbaru
Salinan yang tidak lolos pemeriksaan integritas langsung dihapus dan perintah gagal (kode keluar 1),
jadi cadangan rusak tidak pernah menggantikan cadangan yang baik. Jadwalkan harian dan salin folder
backups/ ke tempat lain juga. Pemulihan: python -m metta.restore."""
import hashlib, os, sqlite3, sys
from datetime import datetime
from .db import db_path
from .preflight import check_db_file


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""): h.update(blok)
    return h.hexdigest()


def main(keep=14):
    src = db_path()
    if not os.path.exists(src): sys.exit("Database not found: " + src)
    out_dir = os.environ.get("METTA_BACKUP_DIR", "backups"); os.makedirs(out_dir, exist_ok=True)
    try: os.chmod(out_dir, 0o700)
    except OSError: pass
    out = os.path.join(out_dir, datetime.now().strftime("metta-%Y%m%d-%H%M%S.db"))
    a = sqlite3.connect(src); b = sqlite3.connect(out)
    with b: a.backup(b)
    a.close(); b.close()
    probs = check_db_file(out)
    if probs:
        os.remove(out); sys.exit("Backup FAILED and was deleted: " + "; ".join(probs))
    try: os.chmod(out, 0o600)
    except OSError: pass
    with open(out + ".sha256", "w") as f: f.write(sha256(out) + "  " + os.path.basename(out) + "\n")
    lama = sorted(f for f in os.listdir(out_dir) if f.startswith("metta-") and f.endswith(".db"))[:-keep]
    for old in lama:
        for suf in ("", ".sha256"):
            try: os.remove(os.path.join(out_dir, old + suf))
            except OSError: pass
    print("Backup written and verified:", out)


if __name__ == "__main__": main()
