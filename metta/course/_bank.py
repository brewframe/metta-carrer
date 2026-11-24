"""Pembantu penyusun bank soal: kunci jawaban diputar posisinya agar tidak selalu di huruf yang sama."""
import itertools
from ._tulis import Q


def banks(start, rows):
    """rows: (bab, level, soal, jawaban_benar, [3 pengecoh], alasan)."""
    pos = itertools.cycle(start)
    out = []
    for ch, lv, stem, ok, wrong, why in rows:
        p = next(pos)
        opts = list(wrong)
        opts.insert(p, ok)
        out.append(Q(ch, lv, stem, *opts, "abcd"[p], why))
    return out
