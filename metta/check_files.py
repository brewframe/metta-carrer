"""Periksa bahwa file aplikasi di komputer ini sudah versi terbaru dan lengkap.

    python -m metta.check_files

Menampilkan nomor versi (sama dengan "Versi ..." di bagian bawah halaman web) dan memeriksa
fungsi-fungsi penting di file tampilan. Kalau ada yang GAGAL, ekstrak ulang zip terbaru dan pilih Replace."""
import os, sys
from .app import STATIC, _asset_version

CHECKS = [("guard.js", "mettaHeal"), ("app.js", "function countdown"), ("app.js", "function barChart"), ("app.js", "barChart: barChart"),
          ("staff.js", "M.barChart"), ("course.js", "M.countdown"), ("student.js", "add-place"), ("index.html", "/static/guard.js"),
          ("lang.js", '"Show table": "Lihat tabel"')]


def main():
    bad = 0
    print("Folder aplikasi:", os.path.dirname(STATIC))
    for f, needle in CHECKS:
        p = os.path.join(STATIC, f)
        ok = os.path.exists(p) and needle in open(p, encoding="utf-8").read()
        bad += not ok
        print(("  OK    " if ok else "  GAGAL ") + f + " -> " + needle)
    print("Versi file tampilan:", _asset_version()[:6], "(harus sama dengan 'Versi ...' di bagian bawah halaman web)")
    if bad:
        print("\nAda", bad, "file lama. Matikan server, ekstrak ulang zip terbaru ke folder ini dan pilih Replace."); sys.exit(1)
    print("\nSemua file sudah versi terbaru.")


if __name__ == "__main__": main()
