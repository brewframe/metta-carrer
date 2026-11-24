"""Isi kursus karier. Satu kursus per karier (id karier = kunci).

Struktur satu kursus (lihat course/_tulis.py untuk cara menulis):
  bab 1  : tujuan belajar + materi (hanya bacaan)
  bab 2-5: tujuan + materi lanjutan + latihan mandiri + kuis (diambil dari bank soal)
  bab 6  : proyek akhir (harus diverifikasi guru) + ujian akhir
Kunci jawaban hanya ada di server. Konten berbahasa Indonesia.
"""
import importlib, os, pkgutil

COURSES = {}          # career_id -> dict
CH_TITLES = {1: "Learning goals and core material", 2: "Core concepts and practice", 3: "Guided practice",
             4: "Deeper understanding", 5: "Case study and problem solving", 6: "Final project and final exam"}
QUIZ_N = 6            # soal per kuis bab (diambil acak dari 7 soal bab itu)
FINAL_N = 12          # soal ujian akhir (3 dari tiap bab 2-5)
PASS_CHAPTER = 5      # benar minimal dari 6
PASS_FINAL = 9        # benar minimal dari 12
# Tanpa hitungan detik (keputusan sekolah): siswa boleh langsung mencoba lagi dan langsung menandai bab 1 dibaca.
# Perlindungan dari menebak tetap ada: soal & urutan pilihan diacak ulang tiap percobaan, dan pembahasan hanya muncul setelah lulus.
# Jeda masih bisa dinyalakan lewat variabel lingkungan (dipakai oleh tes).
COOLDOWN_SEC = int(os.environ.get("METTA_COURSE_COOLDOWN", "0"))
READ_MIN_SEC = int(os.environ.get("METTA_COURSE_READ_SEC", "0"))


def _load():
    for m in pkgutil.iter_modules(__path__):
        if m.name.startswith("c_"): importlib.import_module(f"{__name__}.{m.name}")
_load()


def validate():
    """Kembalikan daftar masalah struktur. Kosong = semua kursus sesuai aturan."""
    bad = []
    for cid, c in sorted(COURSES.items()):
        p = f"karier {cid}: "
        chs = c["chapters"]
        if sorted(chs) != [1, 2, 3, 4, 5]: bad.append(p + "bab 1-5 harus ada"); continue
        for n, ch in chs.items():
            if not (3 <= len(ch["goals"]) <= 5): bad.append(p + f"bab {n}: tujuan 3-5")
            words = sum(len((t or "").split()) for _, t in ch["sections"])
            if words < (180 if n == 1 else 110): bad.append(p + f"bab {n}: materi terlalu pendek ({words} kata)")
            if n >= 2 and len(ch["practice"]) != 3: bad.append(p + f"bab {n}: harus 3 latihan")
        src = c.get("sources") or []
        if len(src) < 2: bad.append(p + "butuh minimal 2 sumber (judul, url https)")
        for s in src:
            if len(s) != 2 or not s[0].strip() or not str(s[1]).startswith("https://"): bad.append(p + f"sumber tidak valid: {s}")
        pr = c["project"]
        if len(pr["criteria"]) < 6: bad.append(p + "kriteria proyek minimal 6")
        if len(pr["brief"].split()) < 40: bad.append(p + "uraian proyek terlalu pendek")
        bank = c["bank"]
        if not 26 <= len(bank) <= 32: bad.append(p + f"jumlah soal {len(bank)} (harus 26-32)")
        seen = set()
        for i, q in enumerate(bank):
            ch, lv, stem, opts, ok, why = q
            if ch not in (2, 3, 4, 5): bad.append(p + f"soal {i}: bab salah")
            if lv not in ("A", "K"): bad.append(p + f"soal {i}: level harus A atau K")
            if len(opts) != 4 or len(set(o.strip().lower() for o in opts)) != 4: bad.append(p + f"soal {i}: 4 pilihan berbeda")
            if not (isinstance(ok, int) and 0 <= ok < 4): bad.append(p + f"soal {i}: kunci salah")
            if len(stem) < 10 or len(why) < 25: bad.append(p + f"soal {i}: teks terlalu pendek")
            if stem in seen: bad.append(p + f"soal {i}: duplikat")
            seen.add(stem)
        for n in (2, 3, 4, 5):
            k = [q for q in bank if q[0] == n]
            if len(k) < 7: bad.append(p + f"bab {n}: butuh 7 soal, ada {len(k)}")
        if sum(1 for q in bank if q[1] == "K") < len(bank) * 0.45: bad.append(p + "soal level SMK kurang dari 45%")
        # jawaban benar tidak boleh bisa ditebak dari panjangnya: yang terpanjang sendirian paling banyak 45% soal (kebetulan sekitar 25-30%)
        def _longest(q):
            ls = sorted(len(o) for o in q[3]); return len(q[3][q[4]]) == ls[-1] and ls[-1] > ls[-2]
        n_long = sum(1 for q in bank if _longest(q))
        if n_long > len(bank) * 0.45: bad.append(p + f"jawaban benar paling panjang di {n_long} dari {len(bank)} soal (maksimal 45%)")
    return bad
