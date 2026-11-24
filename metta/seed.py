"""Starter data. Safe to run many times (only fills empty tables).
Demo accounts (known passwords!) are created ONLY when METTA_SEED_DEMO=1, for local development."""
import os
from .db import DB, init_db
from .security import hash_password
from . import seed_careers, seed_companies

SKILLS = [("Networking basics","technical"),("Routing & switching","technical"),("Mikrotik","technical"),("Linux administration","technical"),
 ("Network security","technical"),("Troubleshooting","technical"),("Python","technical"),("SQL","technical"),("Excel","technical"),
 ("Data analysis","technical"),("HTML/CSS","technical"),("JavaScript","technical"),("Git","technical"),("Machine learning","technical"),
 ("Accounting basics","technical"),("Bookkeeping","technical"),("Tax regulations","technical"),("Financial reporting","technical"),
 ("Accounting software","technical"),("Communication","soft"),("Teamwork","soft"),("Problem solving","soft"),("Attention to detail","soft"),("Customer service","soft")]

# name, category, description, responsibilities, education, example projects, growth, interest tags, strength tags, majors, [(skill, importance)]
CAREERS = [
 ("Network Engineer","Technology","Designs, builds and maintains computer networks for offices and schools.","Install routers and switches; configure Mikrotik; monitor and fix network problems.","SMK TKJ, then D3/S1 Informatics or vendor certificates (MTCNA, CCNA).","Build a small office network with VLANs and a firewall.","Junior Network Engineer, Network Engineer, Senior Engineer, Network Architect.","technology","logical,technical,problem_solving","TKJ",[("Networking basics",3),("Routing & switching",3),("Mikrotik",2),("Troubleshooting",2),("Linux administration",1),("Network security",1)]),
 ("IT Support Technician","Technology","Helps people solve computer, printer and account problems.","Fix hardware and software issues; install software; answer user questions.","SMK TKJ, short IT courses, CompTIA A+.","Make a troubleshooting guide for common school computer problems.","IT Support, Senior Support, System Administrator.","technology,people","problem_solving,communication,technical","TKJ",[("Troubleshooting",3),("Networking basics",2),("Customer service",2),("Communication",1),("Linux administration",1)]),
 ("System Administrator","Technology","Keeps servers and company systems running safely.","Manage Linux servers; create user accounts; back up data; apply updates.","SMK TKJ, then D3/S1 Informatics, LPIC / RHCSA.","Set up a Linux file server with scheduled backups.","SysAdmin, DevOps / Cloud Engineer.","technology","logical,technical,detail","TKJ",[("Linux administration",3),("Networking basics",2),("Troubleshooting",2),("Network security",2),("Git",1)]),
 ("Cybersecurity Analyst","Technology","Protects systems and data from attacks.","Monitor alerts; find weaknesses; respond to incidents; teach safe habits.","SMK TKJ, then S1 Informatics / Security, certificates (Security+, CEH).","Run a safe vulnerability scan on your own home lab.","Security Analyst, Pentester, Security Engineer.","technology,data","analytical,detail,problem_solving","TKJ",[("Network security",3),("Networking basics",2),("Linux administration",2),("Troubleshooting",2),("Python",1)]),
 ("Junior Web Developer","Technology","Builds websites and web apps.","Write HTML/CSS/JavaScript; connect pages to databases; test and fix bugs.","SMK TKJ, bootcamp or S1 Informatics.","Build a small web app with login and a database.","Junior Developer, Developer, Senior / Lead.","technology,design","creativity,logical,problem_solving","TKJ",[("HTML/CSS",3),("JavaScript",3),("Git",2),("SQL",2),("Problem solving",2)]),
 ("Data Analyst","Data","Turns data into answers that help decisions.","Clean data; build reports and charts; explain findings to managers.","SMK AK or TKJ, then S1 Statistics, Informatics, Accounting.","Analyse a school survey and present a dashboard.","Data Analyst, Senior Analyst, Data Scientist.","data,finance,technology","analytical,detail,communication","AK,TKJ",[("Excel",3),("SQL",3),("Data analysis",3),("Python",2),("Communication",1)]),
 ("AI Engineer (Junior)","Data","Builds programs that learn from data.","Prepare data; train and test models; put models into small apps.","SMK TKJ, then S1 Informatics, self-study in Python and ML.","Build a simple chatbot or image classifier.","Junior AI Engineer, ML Engineer, Research Engineer.","technology,data","analytical,logical,problem_solving","TKJ",[("Python",3),("Machine learning",3),("SQL",2),("Git",2),("Data analysis",2)]),
 ("Accounting Staff","Finance","Records company money and prepares basic reports.","Record transactions; reconcile accounts; prepare simple financial reports.","SMK AK, then D3/S1 Accounting, certificates (Brevet, Accurate).","Prepare a full set of books for a small shop.","Accounting Staff, Senior Accountant, Finance Manager.","finance","detail,analytical,logical","AK",[("Accounting basics",3),("Bookkeeping",3),("Excel",2),("Accounting software",2),("Attention to detail",2)]),
 ("Tax Staff","Finance","Helps people and companies calculate and report taxes.","Calculate tax; fill tax forms; follow tax rules; advise clients.","SMK AK, then D3/S1 Tax or Accounting, Brevet A/B.","Prepare a mock monthly tax report for a small business.","Tax Staff, Tax Consultant, Tax Manager.","finance,business","detail,analytical,communication","AK",[("Tax regulations",3),("Accounting basics",2),("Excel",2),("Financial reporting",2),("Attention to detail",2)]),
 ("Fintech / Finance Analyst","Finance","Studies financial data and digital finance products.","Build financial reports; study customer and payment data; suggest improvements.","SMK AK or TKJ, then S1 Finance, Accounting, Informatics.","Build a spreadsheet model that tracks a small budget.","Finance Analyst, Fintech Product Analyst, Finance Lead.","finance,data,technology","analytical,logical,communication","AK,TKJ",[("Financial reporting",3),("Excel",3),("Data analysis",2),("SQL",1),("Communication",1)]),
]

QUESTIONS = [
 ("interest","technology","I enjoy setting up computers, networks or apps."),("interest","technology","I like learning how new technology works."),
 ("interest","finance","I like working with numbers, budgets or money records."),("interest","finance","I am curious how banks and businesses manage money."),
 ("interest","business","I enjoy organizing activities or helping a business run well."),("interest","business","I like understanding what customers need."),
 ("interest","design","I enjoy making things look good (posters, websites, videos)."),("interest","design","I like creating new ideas or concepts."),
 ("interest","data","I like finding patterns in data or information."),("interest","data","I enjoy research and testing ideas."),
 ("interest","people","I like explaining things to other people."),("interest","people","I enjoy helping people solve their problems."),
 ("strength","analytical","I can break a big problem into small steps."),("strength","problem_solving","When something breaks, I keep trying until it works."),
 ("strength","detail","I notice small mistakes that others miss."),("strength","logical","I enjoy puzzles and logical thinking."),
 ("strength","communication","People understand me when I explain something."),("strength","creativity","I come up with ideas others do not."),
 ("strength","collaboration","I work well in a team."),("strength","technical","I learn tools and devices quickly.")]

COMPANIES = [(1,"Asia Group"),(2,"Asuransi Sinar Mas Pekanbaru"),(3,"Bank Seraya"),(4,"Cstev Picture"),(5,"CV Sentral Utama Raya (Toko SUR)"),(6,"CV Solusi Pajak")]

# Terjemahan Indonesia untuk data awal. Kunci = nama/teks sumber (Inggris), nilai = teks Indonesia.
# Disimpan di tabel translations; teks sumber tetap di kolom aslinya. Admin bisa mengubahnya nanti.
SKILLS_ID = {"Networking basics": "Dasar jaringan komputer", "Routing & switching": "Routing & switching", "Mikrotik": "Mikrotik",
 "Linux administration": "Administrasi Linux", "Network security": "Keamanan jaringan", "Troubleshooting": "Troubleshooting (mencari dan memperbaiki masalah)",
 "Python": "Python", "SQL": "SQL", "Excel": "Excel", "Data analysis": "Analisis data", "HTML/CSS": "HTML/CSS", "JavaScript": "JavaScript", "Git": "Git",
 "Machine learning": "Machine learning", "Accounting basics": "Dasar akuntansi", "Bookkeeping": "Pembukuan", "Tax regulations": "Peraturan perpajakan",
 "Financial reporting": "Pelaporan keuangan", "Accounting software": "Software akuntansi", "Communication": "Komunikasi", "Teamwork": "Kerja sama tim",
 "Problem solving": "Pemecahan masalah", "Attention to detail": "Ketelitian", "Customer service": "Layanan pelanggan"}

# nama sumber -> (nama, deskripsi, tugas harian, jalur pendidikan, contoh project, perkembangan karier)
CAREERS_ID = {
 "Network Engineer": ("Network Engineer", "Merancang, membangun, dan merawat jaringan komputer untuk kantor dan sekolah.",
   "Memasang router dan switch; mengonfigurasi Mikrotik; memantau dan memperbaiki masalah jaringan.",
   "SMK TKJ, lalu D3/S1 Informatika atau sertifikat vendor (MTCNA, CCNA).", "Bangun jaringan kantor kecil dengan VLAN dan firewall.",
   "Junior Network Engineer, Network Engineer, Senior Engineer, Network Architect."),
 "IT Support Technician": ("Teknisi IT Support", "Membantu orang menyelesaikan masalah komputer, printer, dan akun.",
   "Memperbaiki masalah perangkat keras dan lunak; memasang software; menjawab pertanyaan pengguna.",
   "SMK TKJ, kursus IT singkat, CompTIA A+.", "Buat panduan troubleshooting untuk masalah komputer sekolah yang sering terjadi.",
   "IT Support, Senior Support, System Administrator."),
 "System Administrator": ("Administrator Sistem", "Menjaga server dan sistem perusahaan tetap berjalan dengan aman.",
   "Mengelola server Linux; membuat akun pengguna; mencadangkan data; memasang pembaruan.",
   "SMK TKJ, lalu D3/S1 Informatika, LPIC / RHCSA.", "Siapkan file server Linux dengan backup terjadwal.", "SysAdmin, DevOps / Cloud Engineer."),
 "Cybersecurity Analyst": ("Analis Keamanan Siber", "Melindungi sistem dan data dari serangan.",
   "Memantau peringatan; mencari celah; menanggapi insiden; mengajarkan kebiasaan aman.",
   "SMK TKJ, lalu S1 Informatika / Keamanan, sertifikat (Security+, CEH).", "Jalankan pemindaian kerentanan yang aman di lab rumahmu sendiri.",
   "Security Analyst, Pentester, Security Engineer."),
 "Junior Web Developer": ("Web Developer Junior", "Membuat situs web dan aplikasi web.",
   "Menulis HTML/CSS/JavaScript; menghubungkan halaman ke database; menguji dan memperbaiki bug.",
   "SMK TKJ, bootcamp, atau S1 Informatika.", "Buat aplikasi web kecil dengan login dan database.", "Junior Developer, Developer, Senior / Lead."),
 "Data Analyst": ("Analis Data", "Mengubah data menjadi jawaban yang membantu pengambilan keputusan.",
   "Membersihkan data; membuat laporan dan grafik; menjelaskan temuan kepada atasan.",
   "SMK AK atau TKJ, lalu S1 Statistika, Informatika, atau Akuntansi.", "Analisis survei sekolah dan presentasikan dalam dashboard.",
   "Data Analyst, Senior Analyst, Data Scientist."),
 "AI Engineer (Junior)": ("AI Engineer (Junior)", "Membuat program yang belajar dari data.",
   "Menyiapkan data; melatih dan menguji model; memasang model ke aplikasi kecil.",
   "SMK TKJ, lalu S1 Informatika, belajar mandiri Python dan ML.", "Buat chatbot sederhana atau pengklasifikasi gambar.",
   "Junior AI Engineer, ML Engineer, Research Engineer."),
 "Accounting Staff": ("Staf Akuntansi", "Mencatat keuangan perusahaan dan menyusun laporan dasar.",
   "Mencatat transaksi; merekonsiliasi akun; menyusun laporan keuangan sederhana.",
   "SMK AK, lalu D3/S1 Akuntansi, sertifikat (Brevet, Accurate).", "Susun pembukuan lengkap untuk sebuah toko kecil.",
   "Staf Akuntansi, Akuntan Senior, Manajer Keuangan."),
 "Tax Staff": ("Staf Perpajakan", "Membantu orang dan perusahaan menghitung dan melaporkan pajak.",
   "Menghitung pajak; mengisi formulir pajak; mengikuti aturan pajak; memberi saran kepada klien.",
   "SMK AK, lalu D3/S1 Perpajakan atau Akuntansi, Brevet A/B.", "Susun laporan pajak bulanan contoh untuk usaha kecil.",
   "Staf Pajak, Konsultan Pajak, Manajer Pajak."),
 "Fintech / Finance Analyst": ("Analis Fintech / Keuangan", "Mempelajari data keuangan dan produk keuangan digital.",
   "Menyusun laporan keuangan; mempelajari data pelanggan dan pembayaran; mengusulkan perbaikan.",
   "SMK AK atau TKJ, lalu S1 Keuangan, Akuntansi, atau Informatika.", "Buat model spreadsheet yang melacak anggaran kecil.",
   "Finance Analyst, Fintech Product Analyst, Finance Lead."),
}
CAREER_FIELDS = ("name", "description", "responsibilities", "education_path", "example_projects", "growth")

QUESTIONS_ID = {
 "I enjoy setting up computers, networks or apps.": "Aku senang memasang komputer, jaringan, atau aplikasi.",
 "I like learning how new technology works.": "Aku suka mempelajari cara kerja teknologi baru.",
 "I like working with numbers, budgets or money records.": "Aku suka bekerja dengan angka, anggaran, atau catatan keuangan.",
 "I am curious how banks and businesses manage money.": "Aku penasaran bagaimana bank dan bisnis mengelola uang.",
 "I enjoy organizing activities or helping a business run well.": "Aku senang mengatur kegiatan atau membantu bisnis berjalan dengan baik.",
 "I like understanding what customers need.": "Aku suka memahami apa yang dibutuhkan pelanggan.",
 "I enjoy making things look good (posters, websites, videos).": "Aku senang membuat sesuatu tampil menarik (poster, situs web, video).",
 "I like creating new ideas or concepts.": "Aku suka menciptakan ide atau konsep baru.",
 "I like finding patterns in data or information.": "Aku suka mencari pola di dalam data atau informasi.",
 "I enjoy research and testing ideas.": "Aku senang meneliti dan menguji ide.",
 "I like explaining things to other people.": "Aku suka menjelaskan sesuatu kepada orang lain.",
 "I enjoy helping people solve their problems.": "Aku senang membantu orang menyelesaikan masalahnya.",
 "I can break a big problem into small steps.": "Aku bisa memecah masalah besar menjadi langkah-langkah kecil.",
 "When something breaks, I keep trying until it works.": "Saat ada yang rusak, aku terus mencoba sampai berfungsi.",
 "I notice small mistakes that others miss.": "Aku melihat kesalahan kecil yang terlewat oleh orang lain.",
 "I enjoy puzzles and logical thinking.": "Aku senang teka-teki dan berpikir logis.",
 "People understand me when I explain something.": "Orang lain paham saat aku menjelaskan sesuatu.",
 "I come up with ideas others do not.": "Aku punya ide yang tidak terpikirkan orang lain.",
 "I work well in a team.": "Aku bisa bekerja baik dalam tim.",
 "I learn tools and devices quickly.": "Aku cepat mempelajari alat dan perangkat.",
}

EXTRA = seed_careers.build_extra()

def seed_translations(d):
    """Isi terjemahan Indonesia. INSERT OR IGNORE: tidak menimpa terjemahan yang sudah diubah admin,
    dan aman dijalankan pada database lama yang datanya sudah terisi."""
    all_skills_id = dict(SKILLS_ID); all_skills_id.update(EXTRA[3])
    all_careers_id = dict(CAREERS_ID); all_careers_id.update(EXTRA[1])
    for r in d.all("SELECT id,name FROM skills"):
        if r["name"] in all_skills_id: d.run("INSERT OR IGNORE INTO translations(entity,entity_id,field,lang,value) VALUES('skill',?,'name','id',?)", r["id"], all_skills_id[r["name"]])
    for r in d.all("SELECT id,name FROM careers"):
        if r["name"] in all_careers_id:
            for f, v in zip(CAREER_FIELDS, all_careers_id[r["name"]]):
                d.run("INSERT OR IGNORE INTO translations(entity,entity_id,field,lang,value) VALUES('career',?,?,'id',?)", r["id"], f, v)
    for r in d.all("SELECT id,text FROM questions"):
        if r["text"] in QUESTIONS_ID: d.run("INSERT OR IGNORE INTO translations(entity,entity_id,field,lang,value) VALUES('question',?,'text','id',?)", r["id"], QUESTIONS_ID[r["text"]])

DEMO = [("admin@metta.sch","Admin Metta","admin","Admin#2026!"),("teacher@metta.sch","Teacher Demo","teacher","Teacher#2026!"),
        ("student@metta.sch","Student Demo","student","Student#2026!"),
        ("alumni@metta.sch","Alumni Demo","alumni","Alumni#2026!")]

def seed():
    init_db(); d = DB()
    extra_c, extra_cid, extra_s, extra_sid, flags = seed_careers.build_extra()
    # Upsert: hanya menambah yang belum ada, jadi database lama tidak kehilangan data dan edit admin tidak tertimpa.
    for n, cat in SKILLS + [(k, v) for k, v in extra_s.items()]:
        d.run("INSERT OR IGNORE INTO skills(name,category) VALUES(?,?)", n, cat)
    sid = {r["name"]: r["id"] for r in d.all("SELECT id,name FROM skills")}
    for n, cat, desc, resp, edu, proj, growth, it, st, mj, sk in CAREERS + extra_c:
        if d.one("SELECT 1 x FROM careers WHERE name=?", n): continue
        cid = d.run("INSERT INTO careers(name,category,description,responsibilities,education_path,example_projects,growth,interest_tags,strength_tags,majors) VALUES(?,?,?,?,?,?,?,?,?,?)", n, cat, desc, resp, edu, proj, growth, it, st, mj)
        for s_, imp in sk: d.run("INSERT OR IGNORE INTO career_skills(career_id,skill_id,importance) VALUES(?,?,?)", cid, sid[s_], imp)
    for n, (field, trend, is_new) in flags.items():   # bidang, tren global, baru (juga untuk 10 karier lama)
        d.run("UPDATE careers SET category=?, trend=?, is_new=? WHERE name=?", field, trend, is_new, n)
    if not d.one("SELECT 1 x FROM questions LIMIT 1"):
        for k, t, x in QUESTIONS: d.run("INSERT INTO questions(kind,tag,text) VALUES(?,?,?)", k, t, x)
    for no, name, addr, sec, sec_id, ab, ab_id, src, ver, guess in seed_companies.ROWS:   # 55 DU/DI; data yang diisi admin tidak ditimpa
        row = d.one("SELECT id,address,verified FROM companies WHERE lower(name)=lower(?)", name)
        if not row: d.run("INSERT INTO companies(number,name,address,sector,sector_id,about,about_id,source,verified,sector_guess) VALUES(?,?,?,?,?,?,?,?,?,?)", no, name, addr, sec, sec_id, ab, ab_id, src, ver, guess)
        elif not row["verified"] and not row["address"]:
            d.run("UPDATE companies SET number=?,address=?,sector=?,sector_id=?,about=?,about_id=?,source=?,verified=?,sector_guess=? WHERE id=?", no, addr, sec, sec_id, ab, ab_id, src, ver, guess, row["id"])
    if os.environ.get("METTA_SEED_DEMO", "") == "1" and not d.one("SELECT 1 x FROM users LIMIT 1"):
        for email, name, role, pw in DEMO:
            uid = d.run("INSERT INTO users(email,name,password_hash,role) VALUES(?,?,?,?)", email, name, hash_password(pw), role)
            if role == "student": d.run("INSERT INTO student_profiles(user_id,school,major,class_name,goal) VALUES(?,?,?,?,?)", uid, "SMK Metta Maitreya", "TKJ", "XI TKJ", "Work in IT")
            if role == "alumni": d.run("INSERT INTO alumni_profiles(user_id,major) VALUES(?,?)", uid, "TKJ")
    seed_translations(d)
    d.commit(); d.close()

if __name__ == "__main__":
    seed(); print("Seed complete.")
