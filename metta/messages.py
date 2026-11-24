"""Teks yang dibuat oleh server (alasan rekomendasi, isi tugas, jawaban asisten, notifikasi).

Dua bahasa: "id" (Indonesia) dan "en" (Inggris). Teks yang tampil di layar (tombol, judul, menu) ada di
metta/static/lang.js; file ini khusus untuk kalimat yang dirangkai server dari data siswa.

Cara pakai:  msg("id", "reason.major_path", major="TKJ")
Kunci yang tidak ada akan memunculkan KeyError di tes, supaya tidak ada teks kosong di layar.
"""
LANGS = ("id", "en")
DEFAULT = "id"


def clean_lang(value, fallback=DEFAULT):
    """Hanya 'id' atau 'en' yang diterima. Apa pun selain itu diganti ke bahasa cadangan."""
    v = (value or "").strip().lower()[:5]
    if v.startswith("id"): return "id"
    if v.startswith("en"): return "en"
    return fallback


TAGS = {   # minat dan kekuatan yang dipakai di tabel careers dan questions
    "technology": ("teknologi", "technology"), "finance": ("keuangan", "finance"), "business": ("bisnis", "business"),
    "design": ("desain", "design"), "data": ("data", "data"), "people": ("bidang yang berhubungan dengan orang", "working with people"),
    "analytical": ("analitis", "analytical"), "problem_solving": ("pemecahan masalah", "problem solving"), "detail": ("ketelitian", "attention to detail"),
    "logical": ("berpikir logis", "logical thinking"), "communication": ("komunikasi", "communication"), "creativity": ("kreativitas", "creativity"),
    "collaboration": ("kerja sama tim", "teamwork"), "technical": ("kemampuan teknis", "technical ability"),
}

LEVELS = {   # tingkat bukti skill (kode 1..4 di database)
    1: ("Klaim sendiri", "Self claimed"), 2: ("Sedang belajar", "Learning"),
    3: ("Bukti project", "Project evidence"), 4: ("Diverifikasi guru", "Teacher verified"),
}

# (id, en)
CATALOG = {
    # alasan rekomendasi karier
    "reason.interest_fit": ("Minatmu cocok dengan bidang ini ({tags}).", "Your interests fit this field ({tags})."),
    "reason.interest_mid": ("Minatmu pada bidang ini tergolong sedang.", "Your interest in this field is moderate."),
    "reason.strength_fit": ("Kekuatanmu sesuai dengan yang dibutuhkan karier ini ({tags}).", "Your strengths match what this career needs ({tags})."),
    "reason.major_path": ("Ini jalur yang umum untuk siswa {major}.", "It is a common path for {major} students."),
    "reason.have_skills": ("Kamu sudah punya titik awal di: {skills}.", "You already have a starting point in: {skills}."),
    "reason.build_skills": ("Skill yang perlu dibangun: {skills}.", "Skills to build: {skills}."),
    "reason.weak": ("Ini pilihan yang bisa dijelajahi, belum cocok kuat.", "This is a possible option to explore, not a strong match yet."),
    # tugas belajar (dibuat saat dibaca, jadi ikut bahasa yang sedang dipilih)
    "task.STUDY.title": ("Pelajari {skill}", "Learn {skill}"),
    "task.STUDY.desc": ("Baca atau tonton materi pemula tentang {skill}, lalu tulis 5 poin penting.", "Read or watch a beginner lesson on {skill} and write down 5 key points."),
    "task.PRACTICE.title": ("Latihan {skill}", "Practice {skill}"),
    "task.PRACTICE.desc": ("Kerjakan 3 latihan kecil tentang {skill} dan catat bagian yang sulit.", "Do 3 small exercises on {skill} and note what was hard."),
    "task.APPLY.title": ("Terapkan {skill} di mini project", "Apply {skill} in a mini project"),
    "task.APPLY.desc": ("Buat sesuatu yang kecil dengan {skill}, lalu kirim di menu Project sebagai bukti.", "Build something small that uses {skill}, then submit it under Projects as evidence."),
    "difficulty.Beginner": ("Pemula", "Beginner"), "difficulty.Intermediate": ("Menengah", "Intermediate"),
    # asisten AI
    "ai.unknown_you": ("Aku belum cukup mengenalmu. Mulai dari Self Discovery (sekitar 5 menit), lalu aku bisa menyarankan karier dan menjelaskan alasannya.",
                       "I do not know you well enough yet. Start with Self Discovery (about 5 minutes). Then I can suggest careers and explain why."),
    "ai.open_discovery": ("Buka Self Discovery", "Open Self Discovery"),
    "ai.why": ("Karier yang paling cocok denganmu adalah {name} ({match}%). Ini saran, bukan keputusan. Kamu yang memilih jalanmu.",
               "Your top match is {name} ({match}%). This is a suggestion, not a decision. You choose your path."),
    "ai.why_next": ("Bandingkan dengan karier lain di menu Jelajah", "Compare it with another career in Explore"),
    "ai.intern_some": ("Kamu sudah menyimpan {n} dari 3 pilihan magang.", "You have saved {n} of 3 internship choices."),
    "ai.intern_none": ("Kamu belum memilih tempat magang. Kamu bisa memilih sampai 3 perusahaan.", "You have not chosen an internship yet. You can choose up to 3 companies."),
    "ai.open_internship": ("Buka Magang", "Open Internship"),
    "ai.gap_noplan": ("Pilih target karier di Career Plan dulu, baru aku bisa menunjukkan skill gap-mu.", "Choose a target career in Career Plan first, then I can show your skill gap."),
    "ai.open_plan": ("Buka Career Plan", "Open Career Plan"),
    "ai.gap": ("Skill yang masih butuh bukti untuk {career}: {skills}", "Skills that still need evidence for {career}: {skills}"),
    "ai.gap_none": ("tidak ada, kerja bagus!", "none, great work!"),
    "ai.open_learning": ("Buka menu Belajar", "Open Learning"),
    "ai.ready": ("Kesiapan kariermu {value}%. Angkanya naik saat kamu menyelesaikan tugas dan skill-mu punya bukti project serta verifikasi guru.",
                 "Your career readiness is {value}%. It grows when you finish tasks and your skills get project evidence and teacher verification."),
    "ai.start_noplan": ("Langkah pertama yang bagus: jadikan {name} (atau karier lain yang kamu suka) targetmu di Career Plan.",
                        "A good first step: make {name} (or any career you like) your target in Career Plan."),
    "ai.next_task": ("Langkah berikutnya: {title}.", "Your next step: {title}."),
    "ai.all_done": ("Semua tugas di rencanamu sudah selesai. Kirim project sebagai bukti!", "You finished all tasks in your plan. Submit a project as evidence!"),
    "ai.fallback": ("Aku bisa membantu soal: kenapa sebuah karier cocok denganmu, skill gap, kemajuanmu, langkah berikutnya, atau pilihan magang. Coba tanyakan salah satunya.",
                    "I can help with: why a career fits you, your skill gap, your progress, your next step, or your internship choices. Try asking one of those."),
    "ai.next_prefix": ("Berikutnya: ", "Next: "),
    # notifikasi (disimpan sebagai teks, jadi bahasanya mengikuti saat dibuat)
    "note.welcome": ("Selamat datang di Metta Career! Mulai dari Self Discovery untuk menemukan karier yang cocok denganmu.",
                     "Welcome to Metta Career! Start with Self Discovery to find careers that fit you."),
    "note.company_submitted": ("{student} mengajukan tempat magang baru: {company}. Mohon diperiksa.", "{student} submitted a new internship place: {company}. Please review it."),
    "note.company_approved": ("Tempat magang yang kamu ajukan, {company}, sudah disetujui guru dan tampil di daftar.", "The internship place you submitted, {company}, was approved by your teacher and is now in the list."),
    "note.company_rejected": ("Ajuan tempat magang {company} belum bisa disetujui: {note}", "Your internship place {company} could not be approved yet: {note}"),
    "note.feedback": ("Masukan baru dari {teacher}: {text}", "New feedback from {teacher}: {text}"),
    "note.guidance": ("{teacher} menambahkan arahan di Career Plan-mu.", "{teacher} added guidance to your Career Plan."),
    "note.course_done": ("Kamu menyelesaikan kursus karier \"{career}\". Skill kariernya naik ke tingkat Belajar.", "You finished the career course \"{career}\". Its skills moved up to the Learning level."),
    "note.verified": ("Project \"{title}\" sudah diverifikasi. Sekarang tampil di portfolio-mu.", "Your project \"{title}\" was verified. It now appears in your portfolio."),
    "note.revision": ("Project \"{title}\" perlu direvisi: {note}", "Your project \"{title}\" needs revision: {note}"),
    "note.story_published": ("Ceritamu \"{title}\" sudah diterbitkan dan bisa dibaca siswa.", "Your story \"{title}\" is published and students can read it."),
    "note.story_rejected": ("Ceritamu \"{title}\" belum bisa diterbitkan. Catatan admin: {note}", "Your story \"{title}\" could not be published yet. Admin note: {note}"),
    "opp.company_title": ("PKL di {name}", "Internship at {name}"),
    "note.item_verified": ("\"{title}\" sudah diverifikasi guru dan tampil sebagai terverifikasi di portfolio-mu.", "\"{title}\" was verified by a teacher and now shows as verified in your portfolio."),
    # status siswa (kode tetap bahasa Inggris di API; ini hanya untuk teks yang dirangkai server)
}


def msg(lang, key, **kw):
    """Ambil teks dalam bahasa yang diminta. lang selain 'id'/'en' dianggap bahasa default."""
    pair = CATALOG[key]
    text = pair[0] if clean_lang(lang) == "id" else pair[1]
    return text.format(**kw) if kw else text


def tag_name(lang, tag):
    pair = TAGS.get(tag)
    if not pair: return tag.replace("_", " ")
    return pair[0] if clean_lang(lang) == "id" else pair[1]


def level_name(lang, level):
    pair = LEVELS[level]
    return pair[0] if clean_lang(lang) == "id" else pair[1]
