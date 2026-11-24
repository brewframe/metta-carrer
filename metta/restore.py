"""Pulihkan database dari cadangan, dengan pemeriksaan dulu.

    python -m metta.restore backups/metta-20261105-020000.db --yes

Langkah: (1) cek checksum .sha256 bila ada, (2) cek integritas SQLite, (3) simpan database sekarang
sebagai metta.db.sebelum-pulih-<waktu> (tidak ditimpa begitu saja), (4) salin cadangan, izin file 600.
HENTIKAN server dulu sebelum memulihkan."""
import os, shutil, sys
from datetime import datetime
from .db import db_path
from .preflight import check_db_file
from .backup import sha256


def restore(src, dest=None):
    """Mengembalikan jalur salinan database lama (atau None bila sebelumnya tidak ada). Melempar ValueError kalau cadangan tidak layak."""
    dest = dest or db_path()
    if not os.path.isfile(src): raise ValueError("Backup file not found: " + src)
    if os.path.exists(src + ".sha256"):
        with open(src + ".sha256") as f: want = f.read().split()[0]
        if sha256(src) != want: raise ValueError("Checksum does not match: the backup file is damaged or was changed")
    probs = check_db_file(src)
    if probs: raise ValueError("Backup is not healthy: " + "; ".join(probs))
    lama = None
    if os.path.exists(dest):
        lama = dest + ".sebelum-pulih-" + datetime.now().strftime("%Y%m%d-%H%M%S"); shutil.move(dest, lama)
    for suf in ("-wal", "-shm"):
        try: os.remove(dest + suf)
        except OSError: pass
    shutil.copyfile(src, dest)
    try: os.chmod(dest, 0o600)
    except OSError: pass
    return lama


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    files = [a for a in argv if not a.startswith("--")]
    if len(files) != 1 or "--yes" not in argv: sys.exit("Usage: python -m metta.restore <backup file> --yes   (stop the server first)")
    try: lama = restore(files[0])
    except ValueError as e: sys.exit(str(e))
    print("Restored from", files[0] + (". Previous database kept as " + lama if lama else "."))


if __name__ == "__main__": main()
