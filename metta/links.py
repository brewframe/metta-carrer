"""Pembersih tautan dan kontak untuk data tempat magang.

Semua isian dari siswa/guru lewat sini sebelum disimpan, supaya yang tersimpan hanya tautan web yang wajar
(http/https), akun Instagram berupa nama saja, dan nomor telepon berupa angka. Tidak ada skrip pihak ketiga:
aplikasi hanya membuat tautan biasa yang dibuka di tab baru."""
import re
from urllib.parse import urlparse, quote_plus
from .core import bad

_HOST = re.compile(r"^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$", re.I)
_IG = re.compile(r"^[A-Za-z0-9._]{1,30}$")


def clean_website(s):
    """Alamat web. Boleh tanpa 'https://'. Hanya http/https, tanpa spasi, tanpa nama pengguna/sandi di dalam tautan."""
    s = (s or "").strip()
    if not s: return ""
    if len(s) > 200 or re.search(r"\s", s): raise bad("Website link is not valid")
    if "://" not in s: s = "https://" + s
    u = urlparse(s)
    host = u.hostname or ""
    if u.scheme not in ("http", "https") or not _HOST.match(host) or "." not in host or u.username or u.password:
        raise bad("Website link is not valid")
    return s


def clean_instagram(s):
    """Nama akun Instagram saja (tanpa @). Menerima '@nama', 'nama', atau tautan instagram.com/nama."""
    s = (s or "").strip()
    if not s: return ""
    if "instagram.com" in s.lower():
        u = urlparse(s if "://" in s else "https://" + s)
        if (u.hostname or "").lower().replace("www.", "") != "instagram.com": raise bad("Instagram account is not valid")
        parts = [p for p in u.path.split("/") if p]
        s = parts[0] if parts else ""
    s = s.lstrip("@")
    if not _IG.match(s) or s.startswith(".") or s.endswith("."): raise bad("Instagram account is not valid")
    return s.lower()


def clean_phone(s):
    s = (s or "").strip()
    if not s: return ""
    if not re.match(r"^[0-9+()\-\s]{6,25}$", s) or len(re.sub(r"\D", "", s)) < 6: raise bad("Phone number is not valid")
    return s


def search_links(name, address=""):
    """Tautan pencarian biasa (Google, Google untuk Instagram, Facebook) agar siswa mudah mencari info tempat ini."""
    q = (name + " " + ("Pekanbaru" if not address else "")).strip()
    return {"google_url": "https://www.google.com/search?q=" + quote_plus(q),
            "ig_search_url": "https://www.google.com/search?q=" + quote_plus("site:instagram.com " + q),
            "fb_search_url": "https://www.google.com/search?q=" + quote_plus("site:facebook.com " + q)}
