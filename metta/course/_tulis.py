"""Pembantu menulis kursus. Contoh pemakaian ada di c_tech_jaringan.py."""
from . import COURSES

def Q(ch, lv, stem, a, b, c, d, ok, why):
    """Satu soal. ch=2..5, lv='A' (tingkat SMA) atau 'K' (tingkat SMK), ok = huruf kunci 'a'..'d'."""
    return (ch, lv, stem, [a, b, c, d], "abcd".index(ok), why)

def bab(goals, *sections, practice=None):
    """sections: pasangan (judul, teks). Teks boleh beberapa paragraf dipisah baris kosong."""
    return {"goals": list(goals), "sections": list(sections), "practice": list(practice or [])}

def kursus(career_id, name, b1, b2, b3, b4, b5, project, bank, sumber=()):
    """sumber = [(judul, url https), ...] yang benar-benar dibaca saat menulis (wajib, minimal 2)."""
    COURSES[career_id] = {"name": name, "sources": [tuple(x) for x in sumber], "chapters": {1: b1, 2: b2, 3: b3, 4: b4, 5: b5}, "project": project, "bank": list(bank)}

def latihan(career_id, p2, p3, p4, p5):
    """Tiga latihan mandiri untuk tiap bab 2-5 (dipanggil sesudah kursus())."""
    for n, p in zip((2, 3, 4, 5), (p2, p3, p4, p5)):
        COURSES[career_id]["chapters"][n]["practice"] = list(p)
