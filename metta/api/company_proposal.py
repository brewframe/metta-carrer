"""Siswa mengajukan tempat magang sendiri; guru memeriksa lalu menyetujui atau menolak.

Alur:  siswa isi formulir -> status 'pending' (hanya terlihat oleh pemilik dan guru)
       -> guru periksa (telepon / web / Instagram / surat) -> 'approved' (tampil untuk semua siswa, ditandai terverifikasi)
          atau 'rejected' (disertai alasan, siswa bisa memperbaiki dan mengajukan lagi).
Siswa tidak bisa menyetujui ajuannya sendiri, dan hanya bisa menghapus ajuan miliknya yang belum disetujui."""
from typing import Optional
from pydantic import BaseModel, Field
from ..core import api, HTTPError, bad, not_found, notify, audit, user_lang
from ..security import rate_blocked, rate_hit
from ..links import clean_website, clean_instagram, clean_phone
from ..messages import msg
from .student import _co

S = ["student"]; R = ["teacher", "admin"]
MAX_PENDING = 3          # ajuan yang boleh menunggu sekaligus per siswa, agar guru tidak kebanjiran


class ProposalIn(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    address: str = Field(min_length=10, max_length=300)
    sector: str = Field(min_length=3, max_length=80)
    about: str = Field(min_length=40, max_length=800)
    tasks: str = Field(min_length=10, max_length=500)
    majors: str = Field("", max_length=200)
    work_terms: str = Field("", max_length=300)
    phone: str = Field("", max_length=30)
    website: str = Field("", max_length=200)
    instagram: str = Field("", max_length=200)
    source: str = Field(min_length=5, max_length=200)      # dari mana siswa tahu / sudah bicara dengan siapa


def _own(c, cid):
    row = c.db.one("SELECT * FROM companies WHERE id=? AND submitted_by=?", cid, c.user["id"])
    if not row: raise not_found("Company not found")
    return row


@api("/api/student/companies", "POST", roles=S, model=ProposalIn)
def proposal_create(c, b):
    name = " ".join(b.name.split())
    phone, web, ig = clean_phone(b.phone), clean_website(b.website), clean_instagram(b.instagram)
    if not (phone or web or ig): raise bad("Add at least one way to reach the place: phone, website or Instagram")
    if c.db.one("SELECT COUNT(*) n FROM companies WHERE submitted_by=? AND status='pending'", c.user["id"])["n"] >= MAX_PENDING:
        raise bad("You already have 3 places waiting for your teacher. Wait for a review first")
    if c.db.one("SELECT 1 x FROM companies WHERE lower(name)=lower(?) AND status<>'rejected'", name):
        raise HTTPError(409, "A place with this name already exists. Search for it in the list")
    if rate_blocked(c.db, "company_propose", c.user["id"], 10, 3600): raise HTTPError(429, "Too many attempts. Please wait a few minutes and try again.")   # cegah banjir ajuan lewat kirim-hapus berulang
    rate_hit(c.db, "company_propose", c.user["id"])
    clean = lambda t: " ".join(t.split())
    cid = c.db.run("""INSERT INTO companies(name,address,sector,sector_id,about,about_id,source,verified,sector_guess,website,instagram,phone,tasks,majors,work_terms,status,submitted_by,submitted_at)
                      VALUES(?,?,?,?,?,?,?,0,0,?,?,?,?,?,?,'pending',?,datetime('now'))""",
                   name, clean(b.address), clean(b.sector), clean(b.sector), clean(b.about), clean(b.about), clean(b.source), web, ig, phone,
                   clean(b.tasks), clean(b.majors), clean(b.work_terms), c.user["id"])
    for t in c.db.all("SELECT id FROM users WHERE role='teacher' AND active=1"):
        notify(c.db, t["id"], msg(user_lang(c.db, t["id"]), "note.company_submitted", student=c.user["name"], company=name))
    audit(c, "company_propose", f"{cid}:{name}")
    return {"id": cid, "status": "pending"}


@api("/api/student/companies/mine", roles=S)
def proposal_mine(c):
    rows = c.db.all("SELECT * FROM companies WHERE submitted_by=? ORDER BY id DESC", c.user["id"])
    return {"items": [_co(r, c.lang, c.user["id"]) for r in rows]}


@api("/api/student/companies/{cid:int}", "DELETE", roles=S)
def proposal_delete(c, cid):
    row = _own(c, cid)
    if row["status"] == "approved": raise HTTPError(403, "An approved place can no longer be deleted by you")
    c.db.run("DELETE FROM companies WHERE id=?", cid); audit(c, "company_propose_delete", str(cid))
    return {"ok": True}


# ---------- guru / admin ----------
@api("/api/teacher/company-submissions", roles=R)
def submissions(c):
    """Ajuan yang menunggu (dan ajuan yang baru ditolak, untuk dilihat ulang)."""
    rows = c.db.all("""SELECT co.*, u.name student_name, sp.class_name student_class FROM companies co JOIN users u ON u.id=co.submitted_by
                       LEFT JOIN student_profiles sp ON sp.user_id=u.id WHERE co.status IN ('pending','rejected') ORDER BY co.status DESC, co.id DESC""")
    out = []
    for r in rows:
        x = _co(r, c.lang); x.update({"student": r["student_name"], "student_class": r["student_class"] or "", "submitted_at": r["submitted_at"] or "", "review_note": r["review_note"] or ""})
        out.append(x)
    return {"items": out, "pending": sum(1 for x in out if x["status"] == "pending")}


class ReviewIn(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    note: str = Field("", max_length=300)
    # koreksi opsional dari guru sebelum disetujui (kosong = biarkan)
    address: Optional[str] = Field(None, max_length=300); about: Optional[str] = Field(None, max_length=800); sector: Optional[str] = Field(None, max_length=80)
    phone: Optional[str] = Field(None, max_length=30); website: Optional[str] = Field(None, max_length=200); instagram: Optional[str] = Field(None, max_length=200)


@api("/api/teacher/company-submissions/{cid:int}", "PUT", roles=R, model=ReviewIn)
def review(c, b, cid):
    row = c.db.one("SELECT * FROM companies WHERE id=?", cid)
    if not row or row["submitted_by"] is None or row["status"] == "approved": raise not_found("Submission not found")
    sid, note = row["submitted_by"], b.note.strip()
    lang = user_lang(c.db, sid)
    if b.decision == "reject":
        if len(note) < 5: raise bad("Write a reason of at least 5 characters so the student can fix it")
        c.db.run("UPDATE companies SET status='rejected', review_note=? WHERE id=?", note, cid)
        c.db.run("DELETE FROM internship_choices WHERE company_id=?", cid)      # pilihan magang yang memakai tempat ini dikosongkan
        notify(c.db, sid, msg(lang, "note.company_rejected", company=row["name"], note=note[:120])); audit(c, "company_reject", f"{cid}:{note[:60]}")
        return {"ok": True, "status": "rejected"}
    fix = lambda new, old: " ".join(new.split()) if new is not None and new.strip() else old
    addr, about, sec = fix(b.address, row["address"]), fix(b.about, row["about"]), fix(b.sector, row["sector"])
    phone = clean_phone(b.phone) if b.phone is not None and b.phone.strip() else row["phone"]
    web = clean_website(b.website) if b.website is not None and b.website.strip() else row["website"]
    ig = clean_instagram(b.instagram) if b.instagram is not None and b.instagram.strip() else row["instagram"]
    num = (c.db.one("SELECT MAX(number) m FROM companies")["m"] or 0) + 1
    src = ((row["source"] or "") + " | Diverifikasi guru: " + c.user["name"])[:200]
    c.db.run("UPDATE companies SET status='approved', verified=1, number=?, address=?, about=?, about_id=?, sector=?, sector_id=?, phone=?, website=?, instagram=?, source=?, review_note=? WHERE id=?",
             num, addr, about, about, sec, sec, phone, web, ig, src, note, cid)
    notify(c.db, sid, msg(lang, "note.company_approved", company=row["name"])); audit(c, "company_approve", str(cid))
    return {"ok": True, "status": "approved"}
