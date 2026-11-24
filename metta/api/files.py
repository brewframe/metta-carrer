"""Unggah file bukti (sertifikat, prestasi, project) — aman dan tanpa pustaka tambahan.

Aturan keamanan:
- Hanya PDF, PNG, JPEG; jenisnya dicek dari ISI file (magic bytes), bukan dari nama atau tipe yang dikirim browser.
- Maks 3 MB per file, 3 file per item, 40 file per siswa. Dikirim sebagai JSON base64 (batas isi permintaan khusus rute ini).
- Disimpan dengan nama acak di folder di luar /static; nama asli hanya disimpan di database (sudah dibersihkan).
- Hanya pemilik, guru, dan admin yang bisa membuka. Respons memakai nosniff + CSP sandbox; PDF selalu diunduh, tidak dijalankan di situs ini.
- Tidak pernah ikut tampil di portofolio publik.
"""
import base64, binascii, os, re, secrets
from typing import Optional
from pydantic import BaseModel, Field
from starlette.responses import Response
from ..core import api, bad, not_found, audit, HTTPError
from ..db import db_path

S = ["student"]
MAX_BYTES = 3 * 1024 * 1024
MAX_PER_ITEM, MAX_PER_USER = 3, 40
KINDS = {"certificate": "certificates", "achievement": "achievements", "project": "projects"}
SIGS = [(b"%PDF-", "application/pdf", ".pdf"), (b"\x89PNG\r\n\x1a\n", "image/png", ".png"), (b"\xff\xd8\xff", "image/jpeg", ".jpg")]

def folder():
    d = os.path.join(os.path.dirname(os.path.abspath(db_path())), "uploads")
    os.makedirs(d, mode=0o700, exist_ok=True); return d

def sniff(data):
    for sig, mime, ext in SIGS:
        if data.startswith(sig): return mime, ext
    return None, None

def clean_name(name, ext):
    base = os.path.basename((name or "file").replace("\\", "/"))
    base = re.sub(r"[^\w .()\-]", "_", base, flags=re.UNICODE).strip(" .")[:80] or "file"
    base = re.sub(r"\.(pdf|png|jpe?g)$", "", base, flags=re.I)
    return base + ext

def owned_ref(db, kind, ref_id, uid):
    t = KINDS.get(kind)
    if not t or not db.one(f"SELECT 1 x FROM {t} WHERE id=? AND user_id=?", ref_id, uid): raise not_found("Item not found")   # nama tabel dari konstanta

def files_map(db, kind, ids):
    """{id item: [ {id,name,size,mime} ]} untuk daftar item."""
    out = {i: [] for i in ids}
    if not ids: return out
    q = ",".join("?" * len(ids))
    for r in db.all(f"SELECT id,ref_id,original_name name,size,mime FROM uploads WHERE ref_kind=? AND ref_id IN ({q}) ORDER BY id", kind, *ids):
        out[r.pop("ref_id")].append(r)
    return out

def purge(db, kind, ref_id):
    """Hapus semua file milik satu item (dipanggil saat item dihapus)."""
    for r in db.all("SELECT id,stored_name FROM uploads WHERE ref_kind=? AND ref_id=?", kind, ref_id):
        try: os.remove(os.path.join(folder(), r["stored_name"]))
        except OSError: pass
    db.run("DELETE FROM uploads WHERE ref_kind=? AND ref_id=?", kind, ref_id)

class UploadIn(BaseModel):
    kind: str = Field(pattern="^(certificate|achievement|project)$")
    ref_id: int = Field(ge=1)
    filename: str = Field(min_length=1, max_length=200)
    data: str = Field(min_length=8, max_length=4_400_000)      # base64

@api("/api/student/uploads", "POST", roles=S, model=UploadIn, max_body=4_600_000)
def upload(c, b):
    uid = c.user["id"]; owned_ref(c.db, b.kind, b.ref_id, uid)
    try: data = base64.b64decode(b.data, validate=True)
    except (binascii.Error, ValueError): raise bad("The file could not be read")
    if len(data) > MAX_BYTES: raise HTTPError(413, "File is too large (max 3 MB)")
    mime, ext = sniff(data)
    if not mime: raise bad("Only PDF, PNG or JPG files are allowed")
    if c.db.one("SELECT COUNT(*) n FROM uploads WHERE ref_kind=? AND ref_id=?", b.kind, b.ref_id)["n"] >= MAX_PER_ITEM: raise bad("Maximum 3 files per item")
    if c.db.one("SELECT COUNT(*) n FROM uploads WHERE user_id=?", uid)["n"] >= MAX_PER_USER: raise bad("You have reached the file limit")
    stored = secrets.token_hex(16)
    with open(os.path.join(folder(), stored), "wb") as f: f.write(data)
    fid = c.db.run("INSERT INTO uploads(user_id,ref_kind,ref_id,stored_name,original_name,mime,size) VALUES(?,?,?,?,?,?,?)", uid, b.kind, b.ref_id, stored, clean_name(b.filename, ext), mime, len(data))
    audit(c, "file_upload", f"{b.kind}:{b.ref_id}")
    return {"id": fid, "name": clean_name(b.filename, ext), "size": len(data), "mime": mime}

@api("/api/student/uploads/{fid:int}", "DELETE", roles=S)
def upload_delete(c, fid):
    r = c.db.one("SELECT stored_name FROM uploads WHERE id=? AND user_id=?", fid, c.user["id"])
    if not r: raise not_found("File not found")
    try: os.remove(os.path.join(folder(), r["stored_name"]))
    except OSError: pass
    c.db.run("DELETE FROM uploads WHERE id=?", fid)

@api("/api/files/{fid:int}", roles=["student", "teacher", "admin"])
def file_get(c, fid):
    r = c.db.one("SELECT * FROM uploads WHERE id=?", fid)
    if not r or (c.user["role"] == "student" and r["user_id"] != c.user["id"]): raise not_found("File not found")
    try:
        with open(os.path.join(folder(), r["stored_name"]), "rb") as f: data = f.read()
    except OSError: raise not_found("File not found")
    if c.user["role"] != "student": audit(c, "file_view", str(fid))
    inline = r["mime"].startswith("image/")
    safe = r["original_name"].encode("ascii", "replace").decode().replace('"', "")
    return Response(data, media_type=r["mime"], headers={
        "Content-Disposition": f'{"inline" if inline else "attachment"}; filename="{safe}"',
        "Content-Security-Policy": "default-src 'none'; sandbox", "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})
