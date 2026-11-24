/* Uji pembanding: skenario yang sama dijalankan ke server Python asli dan ke backend JS.
   Jawaban API dan isi database akhir harus sama (kecuali waktu dan nilai acak). Lalu catatan operasi JS diputar ulang
   dari database dasar dan hasilnya harus identik dengan database live. */
const fs = require("fs"), path = require("path"), { spawn } = require("child_process");
const H = require("./harness.js");
const PORT = 8824, BASE = "http://127.0.0.1:" + PORT, DIR = __dirname;
const PYDB = path.join(DIR, "py.db");
const TS = /^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$/;
const RANDKEYS = new Set(["code", "temp_password", "slug", "seed", "password_hash", "code_hash", "stored_name", "qids", "questions", "token_hash", "attempt"]);
let fails = 0, checks = 0;

function norm(x, key) {
  if (RANDKEYS.has(key)) return x === null ? null : "<rand>";
  if (Array.isArray(x)) return x.map(v => norm(v));
  if (x && typeof x === "object") { const o = {}; Object.keys(x).sort().forEach(k => (o[k] = norm(x[k], k))); return o; }
  if (typeof x === "string" && TS.test(x)) return "<ts>";
  if (typeof x === "string" && /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/.test(x)) return "<ts>";
  return x;
}
function same(a, b) {
  a = JSON.parse(JSON.stringify(a || null).replace(/"127\.0\.0\.1"/g, '"browser"')); b = JSON.parse(JSON.stringify(b || null).replace(/"127\.0\.0\.1"/g, '"browser"'));
  const fixQ = x => { if (x && Array.isArray(x.quiz)) x.quiz = x.quiz.map(q => ({ q: q.q, options: q.options.slice().sort() })); return x; }; fixQ(a); fixQ(b); return JSON.stringify(norm(a)) === JSON.stringify(norm(b)); }
function firstDiff(a, b, p = "") {
  a = norm(JSON.parse(JSON.stringify(a === undefined ? null : a).replace(/"127\.0\.0\.1"/g, '"browser"'))); b = norm(JSON.parse(JSON.stringify(b === undefined ? null : b).replace(/"127\.0\.0\.1"/g, '"browser"')));
  if (JSON.stringify(a) === JSON.stringify(b)) return null;
  if (a && b && typeof a === "object" && typeof b === "object") {
    const ks = new Set([...Object.keys(a), ...Object.keys(b)]);
    for (const k of ks) { const d = firstDiff(a[k], b[k], p + "." + k); if (d) return d; }
  }
  return p + ": py=" + JSON.stringify(a).slice(0, 220) + " | js=" + JSON.stringify(b).slice(0, 220);
}

/* ---------- klien Python (cookie per pengguna) ---------- */
const jars = {};
async function py(who, method, url, body, lang) {
  const h = { "X-Lang": lang || "id" }; if (jars[who]) h.Cookie = jars[who];
  if (body !== undefined) h["Content-Type"] = "application/json";
  const r = await fetch(BASE + url, { method, headers: h, body: body === undefined ? undefined : JSON.stringify(body) });
  const sc = r.headers.getSetCookie ? r.headers.getSetCookie() : [];
  sc.forEach(c => { const m = /^metta_session=([^;]*)/.exec(c); if (m) jars[who] = m[1] ? "metta_session=" + m[1] : undefined; });
  const ct = r.headers.get("content-type") || ""; let data = null;
  if (ct.includes("json")) data = await r.json(); else data = { __binary: (await r.arrayBuffer()).byteLength };
  return { status: r.status, body: data };
}
/* ---------- klien JS ---------- */
let JS; const toks = {};
async function js(who, method, url, body, lang) {
  const r = await JS.request(toks[who] || null, method, url, body, lang || "id");
  if (r.ctx && r.ctx.setCookie) toks[who] = r.ctx.setCookie[0];
  if (r.ctx && r.ctx.clearCookie) toks[who] = null;
  return { status: r.status, body: r.body };
}
async function both(who, method, url, body, opt) {
  opt = opt || {};
  const a = await py(who, method, url, body, opt.lang), b = await js(who, method, url, body, opt.lang);
  checks++;
  let ok = a.status === b.status;
  if (ok && !opt.statusOnly) ok = same(a.body, b.body);
  if (!ok) { fails++; console.log("BEDA", who, method, url, "status py", a.status, "js", b.status, "\n   ", a.status === b.status ? firstDiff(a.body, b.body) : JSON.stringify(a.body).slice(0, 200) + " | " + JSON.stringify(b.body).slice(0, 200)); }
  if (opt.expect && b.status !== opt.expect) { fails++; console.log("STATUS", who, method, url, "harap", opt.expect, "dapat", b.status, JSON.stringify(b.body).slice(0, 200)); }
  return { py: a, js: b };
}

/* jawaban benar untuk kuis belajar dan kuis kursus (dicari dari kunci di data, berlaku di kedua server) */
const META = JSON.parse(fs.readFileSync(path.join(DIR, "..", "site", "data", "meta.json"), "utf8"));
const COURSES = JSON.parse(fs.readFileSync(path.join(DIR, "..", "site", "data", "courses.json"), "utf8"));
function lessonAnswers(view, lang) {
  const L = Object.values(META.LESSONS).find(l => l.quiz.some(q => (lang === "id" ? q[1] : q[0]) === view.quiz[0].q));
  return view.quiz.map(qv => {
    const q = L.quiz.find(q => (lang === "id" ? q[1] : q[0]) === qv.q), o = q[2][q[3]], i = o.indexOf("||");
    const txt = lang === "id" && i >= 0 && o.slice(i + 2) ? o.slice(i + 2) : (i >= 0 ? o.slice(0, i) : o);
    return qv.options.indexOf(txt);
  });
}
function courseAnswers(cid, view, wrong) {
  const bank = COURSES[String(cid)].bank;
  return view.questions.map((qv, i) => { const q = bank.find(q => q[2] === qv.q && q[3].every(o => qv.options.includes(o))); const right = qv.options.indexOf(q[3][q[4]]); return wrong && i < 4 ? (right + 1) % 4 : right; });
}

async function main() {
  fs.copyFileSync(path.join(DIR, "base.db"), PYDB); try { fs.unlinkSync(PYDB + "-wal"); } catch (e) {}
  const srv = spawn("python3", [path.join(DIR, "..", "build", "serve_base.py"), String(PORT)], { env: Object.assign({}, process.env, { METTA_DB: PYDB }), stdio: ["ignore", "ignore", "pipe"] });
  let errLog = ""; srv.stderr.on("data", d => (errLog += d));
  for (let i = 0; i < 60; i++) { try { await fetch(BASE + "/api/health"); break; } catch (e) { await new Promise(r => setTimeout(r, 300)); } }
  JS = await new H.JsServer(path.join(DIR, "base.db")).init();
  try { await scenario(); } catch (e) { fails++; console.log("SKENARIO ERROR", e); }
  /* bandingkan isi database akhir */
  const { DatabaseSync } = require("node:sqlite");
  const pdb = new DatabaseSync(PYDB); pdb.function("op_now", () => "2026-01-01 00:00:00");
  const pdump = H.dump({ db: pdb }), jdump = H.dump(JS.a);
  for (const t of Object.keys(pdump)) {
    checks++;
    if (t === "student_skills") { const k = r => r.slice().sort((x, y) => x.user_id - y.user_id || x.skill_id - y.skill_id); pdump[t] = k(pdump[t]); jdump[t] = k(jdump[t]); }
    if (t === "course_attempts") { const strip = r => r.map(x => Object.assign({}, x, { qids: 0, seed: 0 })); if (!same(strip(pdump[t]), strip(jdump[t]))) { fails++; console.log("DB BEDA", t, firstDiff(strip(pdump[t]), strip(jdump[t]))); } continue; }
    if (!same(pdump[t], jdump[t])) { fails++; console.log("DB BEDA", t, firstDiff(pdump[t], jdump[t])); }
  }
  /* putar ulang catatan operasi: harus identik persis dengan database live */
  const re = await JS.replayFresh(), rdump = H.dump(re); Object.assign(jdump, H.dump(JS.a)); [rdump, jdump].forEach(d => d.users.forEach(u => delete u.last_active_at));
  checks++;
  if (JSON.stringify(rdump) !== JSON.stringify(jdump)) { fails++; for (const t of Object.keys(jdump)) if (JSON.stringify(rdump[t]) !== JSON.stringify(jdump[t])) console.log("REPLAY BEDA", t, JSON.stringify(jdump[t]).length, JSON.stringify(rdump[t]).length); }
  console.log("ops tercatat:", JS.ops.length, "| sensitif bocor:", JSON.stringify(JS.ops).match(/Student#2026!|Teacher#2026!|Admin#2026!|Baru-Sandi/g) || "tidak ada");
  srv.kill(); re.close(); JS.a.close();
  console.log(`\nHASIL: ${checks} pemeriksaan, ${fails} beda`); if (errLog.includes("Traceback")) console.log("PYTHON ERROR LOG:\n" + errLog.slice(-1500));
  process.exit(fails ? 1 : 0);
}

const PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

async function scenario() {
  // publik & login
  await both("x", "GET", "/api/auth/config");
  await both("x", "GET", "/api/public/stats");
  await both("x", "GET", "/api/me", undefined, { expect: 401 });
  await both("x", "POST", "/api/auth/login", { email: "student@metta.sch", password: "salah-sandi", role: "student" }, { expect: 401 });
  await both("x", "POST", "/api/auth/login", { email: "bukan-email", password: "x" }, { expect: 422 });
  await both("x", "POST", "/api/auth/login", { email: "teacher@metta.sch", password: "Teacher#2026!", role: "student" }, { expect: 401 });
  for (const [who, pw] of [["student", "Student#2026!"], ["teacher", "Teacher#2026!"], ["admin", "Admin#2026!"], ["alumni", "Alumni#2026!"]])
    await both(who, "POST", "/api/auth/login", { email: who + "@metta.sch", password: pw, role: who }, { expect: 200 });
  await both("citra", "POST", "/api/auth/login", { email: "citra@metta.sch", password: "Belajar-Karier-2026!", role: "student" }, { expect: 200 });
  await both("student", "GET", "/api/teacher/summary", undefined, { expect: 403 });
  await both("student", "GET", "/api/me");

  // siswa: jelajah
  for (const u of ["/api/student/dashboard", "/api/student/questions", "/api/student/insight", "/api/student/recommendations", "/api/careers", "/api/careers?q=jaringan", "/api/careers?category=Data",
    "/api/careers/6", "/api/careers/999", "/api/student/plan", "/api/student/plan/preview/6", "/api/student/projects", "/api/student/portfolio", "/api/student/outcome", "/api/student/internship",
    "/api/companies", "/api/companies?q=bank", "/api/student/companies/mine", "/api/student/portfolio/extras", "/api/notifications", "/api/alumni-stories", "/api/alumni-stories?kind=TIPS&q=a", "/api/student/course"])
    await both("student", "GET", u);
  await both("student", "GET", "/api/careers", undefined, { lang: "en" });
  await both("student", "GET", "/api/student/dashboard", undefined, { lang: "en" });
  await both("student", "POST", "/api/student/compare", { ids: [1, 6] });
  await both("student", "POST", "/api/student/compare", { ids: [1] }, { expect: 422 });
  await both("student", "POST", "/api/student/shortlist/6"); await both("student", "GET", "/api/careers?q=data");
  await both("student", "DELETE", "/api/student/shortlist/6");
  for (const q of ["kenapa ini cocok?", "magang", "apa skill gap saya", "kesiapan saya", "mulai dari mana", "halo", "why"]) await both("student", "POST", "/api/student/assistant", { question: q });

  // citra: self discovery lengkap -> rencana -> belajar
  const qs = (await both("citra", "GET", "/api/student/questions")).js.body;
  const ans = {}; qs.questions.forEach(q => (ans[q.id] = q.tag === "technology" || q.tag === "data" || q.tag === "analytical" ? 5 : 2));
  await both("citra", "POST", "/api/student/assessment", { answers: { 1: 3 }, skill_ids: [] }, { expect: 400 });
  await both("citra", "POST", "/api/student/assessment", { answers: Object.assign({}, ans, { 1: 9 }), skill_ids: [] }, { expect: 400 });
  await both("citra", "POST", "/api/student/assessment", { answers: ans, skill_ids: [7, 8, 8, 9999] }, { expect: 200 });
  await both("citra", "POST", "/api/student/insight/save");
  await both("citra", "GET", "/api/student/recommendations");
  const plan = (await both("citra", "POST", "/api/student/plan", { career_id: 7 }, { expect: 200 })).js.body;
  await both("citra", "POST", "/api/student/plan", { career_id: 6 }); await both("citra", "POST", "/api/student/plan", { career_id: 7 });
  await both("citra", "GET", "/api/student/plan");
  const tasks = plan.milestones.flatMap(m => m.tasks);
  for (const t of tasks.slice(0, 6)) await both("citra", "GET", "/api/student/learn/" + t.id, undefined, { quiz: true });
  const study = tasks.find(t => t.kind === "STUDY"), prac = tasks.find(t => t.kind === "PRACTICE"), apply = tasks.find(t => t.kind === "APPLY");
  await both("citra", "PATCH", "/api/student/tasks/" + study.id, { status: "COMPLETED" }, { expect: 400 });
  const sv = (await both("citra", "GET", "/api/student/learn/" + study.id)).js.body;
  for (let i = 0; i < sv.steps.length; i++) await both("citra", "POST", "/api/student/learn/" + study.id + "/step", { idx: i, done: true });
  await both("citra", "POST", "/api/student/learn/" + study.id + "/step", { idx: 0, done: false });
  await both("citra", "POST", "/api/student/learn/" + study.id + "/step", { idx: 0, done: true });
  await both("citra", "POST", "/api/student/learn/" + study.id + "/step", { idx: 99, done: true }, { expect: 422 });
  await both("citra", "PATCH", "/api/student/tasks/" + study.id, { status: "COMPLETED" }, { expect: 200 });
  const pv = (await both("citra", "GET", "/api/student/learn/" + prac.id)).js.body;
  if (pv.has_quiz) {
    for (const right of [false, true]) {
      const v = await both("citra", "GET", "/api/student/learn/" + prac.id, undefined, { statusOnly: true });
      const ap = lessonAnswers(v.py.body, "id").map((a, i) => right ? a : (a + 1) % v.py.body.quiz[i].options.length);
      const aj = lessonAnswers(v.js.body, "id").map((a, i) => right ? a : (a + 1) % v.js.body.quiz[i].options.length);
      const rp = await py("citra", "POST", "/api/student/learn/" + prac.id + "/quiz", { answers: ap }), rj = await js("citra", "POST", "/api/student/learn/" + prac.id + "/quiz", { answers: aj });
      checks++; if (!same(rp.body, rj.body) || rj.body.passed !== right) { fails++; console.log("BEDA kuis belajar", firstDiff(rp.body, rj.body)); }
    }
  }
  await both("citra", "PATCH", "/api/student/tasks/" + prac.id, { status: "COMPLETED" });
  await both("citra", "PATCH", "/api/student/tasks/" + apply.id, { status: "COMPLETED" }, { expect: 400 });
  await both("citra", "PATCH", "/api/student/tasks/" + apply.id, { status: "IN_PROGRESS" });

  // project
  await both("citra", "POST", "/api/student/projects", { title: "AB" }, { expect: 422 });
  await both("citra", "POST", "/api/student/projects", { title: "Proyek data", link: "javascript:alert(1)" }, { expect: 400 });
  await both("citra", "POST", "/api/student/projects", { title: "Proyek data", demo_url: "ftp://x.y" }, { expect: 400 });
  const long = "Siswa di sekolah kami sering kesulitan memahami data nilai ujian dari tiap kelas.";
  const p1 = (await both("citra", "POST", "/api/student/projects", { title: "Dashboard nilai ujian", description: "Analisis nilai", link: "https://github.com/citra/nilai", skill_ids: [7, 8, apply.skill_id, 9999],
    problem: long, solution: "Saya membuat dashboard dengan Python dan SQL untuk merangkum nilai per kelas.", result: "Guru bisa melihat kelas yang perlu dibantu.", technology: "Python, SQL", repo_url: "https://github.com/citra/nilai" }, { expect: 200 })).js.body;
  const p2 = (await both("citra", "POST", "/api/student/projects", { title: "Proyek kedua", skill_ids: [8] }, { expect: 200 })).js.body;
  await both("citra", "PATCH", "/api/student/tasks/" + apply.id, { status: "COMPLETED" }, { expect: 200 });
  await both("citra", "PUT", "/api/student/projects/" + p1.id, { title: "Ubah" }, { expect: 400 });
  await both("citra", "POST", "/api/student/uploads", { kind: "project", ref_id: p1.id, filename: "bukti ../a.png", data: PNG }, { expect: 200 });
  await both("citra", "POST", "/api/student/uploads", { kind: "project", ref_id: p1.id, filename: "x.txt", data: "aGVsbG8gd29ybGQ=" }, { expect: 400 });
  await both("citra", "POST", "/api/student/uploads", { kind: "project", ref_id: 1, filename: "x.png", data: PNG }, { expect: 404 });
  await both("citra", "GET", "/api/student/projects");

  // kursus karier (citra: karier 7 harus punya kursus)
  let cs = (await both("citra", "GET", "/api/student/course")).js.body;
  if (cs.available) {
    await both("citra", "GET", "/api/student/course/chapter/2", undefined, { expect: 400 });
    await both("citra", "GET", "/api/student/course/chapter/1");
    await both("citra", "POST", "/api/student/course/chapter/2/quiz", undefined, { expect: 400 });
    await both("citra", "POST", "/api/student/course/chapter/1/read");
    for (const n of [2, 3, 4, 5]) {
      await both("citra", "GET", "/api/student/course/chapter/" + n);
      const r = await both("citra", "POST", "/api/student/course/chapter/" + n + "/quiz", undefined, { statusOnly: true });
      if (n === 2) {   // gagal dulu sekali
        const rp = await py("citra", "POST", "/api/student/course/attempt/" + r.py.body.attempt + "/submit", { answers: courseAnswers(7, r.py.body, true) });
        const rj = await js("citra", "POST", "/api/student/course/attempt/" + r.js.body.attempt + "/submit", { answers: courseAnswers(7, r.js.body, true) });
        checks++; if (rp.status !== rj.status || !same(rp.body, rj.body)) { fails++; console.log("BEDA submit gagal", firstDiff(rp.body, rj.body)); }
        const r2 = await both("citra", "POST", "/api/student/course/chapter/" + n + "/quiz", undefined, { statusOnly: true });
        r.py = r2.py; r.js = r2.js;
      }
      const sp = await py("citra", "POST", "/api/student/course/attempt/" + r.py.body.attempt + "/submit", { answers: courseAnswers(7, r.py.body) });
      const sj = await js("citra", "POST", "/api/student/course/attempt/" + r.js.body.attempt + "/submit", { answers: courseAnswers(7, r.js.body) });
      checks++;
      const strip = b => Object.assign({}, b, { results: (b.results || []).length });
      if (sp.status !== sj.status || !same(strip(sp.body), strip(sj.body)) || !sj.body.passed) { fails++; console.log("BEDA submit bab", n, sp.status, sj.status, firstDiff(strip(sp.body), strip(sj.body)), sj.body.passed); }
    }
    await both("citra", "GET", "/api/student/course/chapter/6");
    await both("citra", "POST", "/api/student/course/project", { project_id: p2.id }, { expect: 400 });
    await both("citra", "POST", "/api/student/course/project", { project_id: p1.id }, { expect: 200 });
    const ex = await both("citra", "POST", "/api/student/course/chapter/6/quiz", undefined, { statusOnly: true });
    const ep = await py("citra", "POST", "/api/student/course/attempt/" + ex.py.body.attempt + "/submit", { answers: courseAnswers(7, ex.py.body) });
    const ej = await js("citra", "POST", "/api/student/course/attempt/" + ex.js.body.attempt + "/submit", { answers: courseAnswers(7, ex.js.body) });
    checks++; const strip = b => Object.assign({}, b, { results: (b.results || []).length });
    if (!same(strip(ep.body), strip(ej.body))) { fails++; console.log("BEDA ujian akhir", firstDiff(strip(ep.body), strip(ej.body))); }
    await both("citra", "GET", "/api/student/course");
  } else console.log("PERINGATAN: karier 7 tidak punya kursus");

  // magang
  await both("citra", "PUT", "/api/student/internship", { class_name: "XI TKJ", company_ids: [1, 1] }, { expect: 400 });
  await both("citra", "PUT", "/api/student/internship", { class_name: "XI TKJ", company_ids: [1, 2, 3], purposes: ["Belajar jaringan", "", "x"], friends: [{ name: "Budi", class_name: "XI TKJ" }] }, { expect: 200 });
  await both("citra", "PUT", "/api/student/internship", { class_name: "XI TKJ", company_ids: [1, 2, 3, 4] }, { expect: 422 });
  await both("citra", "POST", "/api/student/companies", { name: "CV Uji", address: "Jl. Pendek", sector: "IT", about: "x", tasks: "y", source: "z" }, { expect: 422 });
  const base = { name: "CV Sinar Teknik Contoh", address: "Jl. Melati No. 5, Pekanbaru", sector: "Jaringan komputer", about: "Usaha pemasangan jaringan untuk rumah dan kantor kecil di sekitar sekolah.", tasks: "Pasang kabel dan router", source: "kakak kelas" };
  await both("citra", "POST", "/api/student/companies", base, { expect: 400 });
  await both("citra", "POST", "/api/student/companies", Object.assign({}, base, { instagram: "https://evil.com/x" }), { expect: 400 });
  await both("citra", "POST", "/api/student/companies", Object.assign({}, base, { website: "user:pw@evil.com" }), { expect: 400 });
  const prop = (await both("citra", "POST", "/api/student/companies", Object.assign({}, base, { instagram: "@Sinar.Teknik", phone: "0812-3456-789", website: "sinarteknik.id" }), { expect: 200 })).js.body;
  await both("citra", "POST", "/api/student/companies", Object.assign({}, base, { instagram: "@x2" }), { expect: 409 });
  const prop2 = (await both("citra", "POST", "/api/student/companies", Object.assign({}, base, { name: "Toko Komputer Contoh Dua", phone: "0761-12345" }), { expect: 200 })).js.body;
  const prop3 = (await both("citra", "POST", "/api/student/companies", Object.assign({}, base, { name: "Bengkel Contoh Tiga", phone: "0761-12346" }), { expect: 200 })).js.body;
  await both("citra", "POST", "/api/student/companies", Object.assign({}, base, { name: "Keempat Contoh", phone: "0761-12347" }), { expect: 400 });
  await both("citra", "DELETE", "/api/student/companies/" + prop3.id, undefined, { expect: 200 });
  await both("citra", "GET", "/api/student/companies/mine"); await both("citra", "GET", "/api/companies");
  await both("citra", "PUT", "/api/student/internship", { class_name: "XI TKJ", company_ids: [prop.id, 2] }, { expect: 200 });

  // portfolio
  await both("citra", "POST", "/api/student/achievements", { title: "Juara 2 LKS", issuer: "Dinas", achieved_on: "2026-05" }, { expect: 200 });
  await both("citra", "POST", "/api/student/achievements", { title: "X", achieved_on: "2026-5" }, { expect: 422 });
  const ce = (await both("citra", "POST", "/api/student/certificates", { title: "MTCNA", issuer: "Mikrotik", issued_on: "2026", url: "https://mikrotik.com/cert" }, { expect: 200 })).js.body;
  await both("citra", "POST", "/api/student/certificates", { title: "Bad", url: "javascript:x" }, { expect: 400 });
  await both("citra", "POST", "/api/student/uploads", { kind: "certificate", ref_id: ce.new_id, filename: "s.png", data: PNG }, { expect: 200 });
  const sh = await both("citra", "PUT", "/api/student/portfolio/share", { visibility: "LINK", headline: "Calon data analyst" }, { expect: 200 });
  await both("x", "GET", "/api/public/portfolio/abc", undefined, { expect: 404 });
  const pp = await py("x", "GET", "/api/public/portfolio/" + sh.py.body.slug), pj = await js("x", "GET", "/api/public/portfolio/" + sh.js.body.slug);
  checks++; if (!same(pp.body, pj.body)) { fails++; console.log("BEDA portfolio publik", firstDiff(pp.body, pj.body)); }
  await both("citra", "PUT", "/api/student/portfolio/share", { visibility: "PRIVATE", new_link: true }, { expect: 200 });
  await both("citra", "GET", "/api/student/portfolio"); await both("citra", "GET", "/api/student/portfolio/extras"); await both("citra", "GET", "/api/student/outcome");

  // guru
  for (const u of ["/api/teacher/summary", "/api/teacher/students", "/api/teacher/students?q=cit", "/api/teacher/students?status=On%20track", "/api/teacher/students/4", "/api/teacher/plans", "/api/teacher/projects",
    "/api/teacher/validation", "/api/teacher/internship", "/api/teacher/internship?q=bank", "/api/teacher/analytics", "/api/teacher/company-submissions", "/api/teacher/students/4/portfolio-items", "/api/staff/password-requests"])
    await both("teacher", "GET", u);
  const sid = (await both("teacher", "GET", "/api/teacher/students?q=citra")).js.body.items[0].id;
  await both("teacher", "GET", "/api/teacher/students/" + sid);
  await both("teacher", "POST", "/api/teacher/students/" + sid + "/feedback", { text: "Bagus, lanjutkan latihan SQL setiap hari." }, { expect: 200 });
  const plans = (await both("teacher", "GET", "/api/teacher/plans")).js.body.items;
  await both("teacher", "PUT", "/api/teacher/plans/" + plans[0].id + "/guidance", { note: "Fokus ke SQL dulu" }, { expect: 200 });
  await both("teacher", "POST", "/api/teacher/projects/" + p2.id + "/review", { decision: "NEEDS_REVISION" }, { expect: 400 });
  await both("teacher", "POST", "/api/teacher/projects/" + p2.id + "/review", { decision: "NEEDS_REVISION", note: "Tambahkan bukti" }, { expect: 200 });
  await both("teacher", "POST", "/api/teacher/projects/" + p1.id + "/review", { decision: "VERIFIED", note: "Rapi" }, { expect: 200 });
  await both("teacher", "POST", "/api/teacher/projects/" + p1.id + "/review", { decision: "VERIFIED" }, { expect: 400 });
  await both("citra", "PUT", "/api/student/projects/" + p2.id, { title: "Proyek kedua revisi", skill_ids: [8], link: "https://contoh.id/bukti" }, { expect: 200 });
  await both("citra", "GET", "/api/student/course"); await both("citra", "GET", "/api/notifications"); await both("citra", "POST", "/api/notifications/read");
  await both("teacher", "PUT", "/api/teacher/company-submissions/" + prop.id, { decision: "reject", note: "x" }, { expect: 400 });
  await both("teacher", "PUT", "/api/teacher/company-submissions/" + prop.id, { decision: "approve", note: "Sudah ditelepon", address: "Jl. Melati No. 5A, Pekanbaru", instagram: "sinarteknik" }, { expect: 200 });
  await both("teacher", "PUT", "/api/teacher/company-submissions/" + prop2.id, { decision: "reject", note: "Alamat tidak ditemukan" }, { expect: 200 });
  await both("teacher", "PUT", "/api/teacher/companies/5", { source: "Kunjungan guru", address: "Jl. Sudirman 1", website: "contoh.co.id" }, { expect: 200 });
  await both("teacher", "PUT", "/api/teacher/companies/" + prop.id, { source: "Telepon", address: "y" }, { expect: 403 });
  const items = (await both("teacher", "GET", "/api/teacher/students/" + sid + "/portfolio-items")).js.body;
  await both("teacher", "POST", "/api/teacher/portfolio-items/achievements/" + items.achievements[0].id + "/verify", undefined, { expect: 200 });
  await both("teacher", "POST", "/api/teacher/portfolio-items/nope/1/verify", undefined, { expect: 404 });
  await both("teacher", "GET", "/api/teacher/analytics"); await both("teacher", "GET", "/api/teacher/summary"); await both("teacher", "GET", "/api/teacher/company-submissions");
  await both("citra", "GET", "/api/student/course"); await both("citra", "GET", "/api/student/portfolio"); await both("citra", "GET", "/api/student/dashboard");

  // lupa password: budi minta reset, guru menyetujui, budi mengatur password baru
  await both("x", "POST", "/api/auth/forgot", { email: "budi@metta.sch" }, { expect: 200 });
  await both("x", "POST", "/api/auth/forgot", { email: "tidakada@metta.sch" }, { expect: 200 });
  const reqs = (await both("teacher", "GET", "/api/staff/password-requests")).js.body.items;
  const ap = await both("teacher", "POST", "/api/staff/password-requests/" + reqs[0].id + "/approve", undefined, { expect: 200 });
  await both("x", "POST", "/api/auth/reset", { email: "budi@metta.sch", code: "ZZZZ-ZZZZ", new_password: "Baru-Sandi-Kuat-77" }, { expect: 400 });
  const rp = await py("x", "POST", "/api/auth/reset", { email: "budi@metta.sch", code: ap.py.body.code, new_password: "Baru-Sandi-Kuat-77" });
  const rj = await js("x", "POST", "/api/auth/reset", { email: "budi@metta.sch", code: ap.js.body.code.toLowerCase(), new_password: "Baru-Sandi-Kuat-77" });
  checks++; if (rp.status !== 200 || rj.status !== 200) { fails++; console.log("RESET", rp, rj); }
  await both("budi", "POST", "/api/auth/login", { email: "budi@metta.sch", password: "Baru-Sandi-Kuat-77" }, { expect: 200 });
  await both("budi", "POST", "/api/me/password", { current: "salah", "new": "Baru-Sandi-Kuat-88" }, { expect: 400 });
  await both("budi", "POST", "/api/me/password", { current: "Baru-Sandi-Kuat-77", "new": "12345678" }, { expect: 422 });
  await both("budi", "POST", "/api/me/password", { current: "Baru-Sandi-Kuat-77", "new": "Baru-Sandi-Kuat-88" }, { expect: 200 });
  await both("budi", "POST", "/api/me/lang", { lang: "en" }); await both("budi", "PUT", "/api/me/profile", { name: "Budi Santoso", major: "AK", class_name: "XI AK" });
  await both("budi", "POST", "/api/auth/logout"); await both("budi", "GET", "/api/me", undefined, { expect: 401 });

  // daftar akun baru
  await both("new", "POST", "/api/auth/register", { name: "Dewi", email: "dewi@metta.sch", password: "password1", major: "AK", class_name: "X AK" }, { expect: 422 });
  await both("new", "POST", "/api/auth/register", { name: "Dewi", email: "dewi@metta.sch", password: "Dewi-Belajar-2026", major: "AK", class_name: "X AK" }, { expect: 422 });
  await both("new", "POST", "/api/auth/register", { name: "Dewi Lestari", email: "dewi@metta.sch", password: "Kopi-Susu-Enak-77", major: "RPL", class_name: "X AK" }, { expect: 422 });
  await both("new", "POST", "/api/auth/register", { name: "Dewi Lestari", email: "Dewi@Metta.sch ", password: "Kopi-Susu-Enak-77", major: "AK", class_name: "X AK" }, { expect: 200 });
  await both("new", "GET", "/api/student/dashboard"); await both("new", "GET", "/api/notifications");
  await both("new2", "POST", "/api/auth/register", { name: "Dewi Lestari", email: "dewi@metta.sch", password: "Kopi-Susu-Enak-77", major: "AK", class_name: "X AK" }, { expect: 409 });

  // admin
  for (const u of ["/api/admin/users", "/api/admin/users?role=student", "/api/admin/skills", "/api/admin/careers", "/api/admin/summary", "/api/admin/analytics", "/api/admin/audit", "/api/admin/content", "/api/admin/content?status=PUBLISHED", "/api/companies", "/api/teacher/company-submissions", "/api/staff/password-requests"])
    await both("admin", "GET", u);
  await both("admin", "GET", "/api/admin/content?status=X", undefined, { expect: 400 });
  await both("admin", "POST", "/api/admin/users", { name: "Guru Baru", email: "gurubaru@metta.sch", role: "teacher", password: "Pendek-12" }, { expect: 422 });
  const nu = (await both("admin", "POST", "/api/admin/users", { name: "Guru Baru", email: "gurubaru@metta.sch", role: "teacher", password: "Panjang-Sekali-Aman-2026" }, { expect: 200 })).js.body;
  await both("admin", "POST", "/api/admin/users", { name: "Alumni Baru", email: "alumni2@metta.sch", role: "alumni", password: "Panjang-Sekali-Aman-2026" }, { expect: 200 });
  await both("admin", "POST", "/api/admin/users", { name: "Siswa Baru", email: "siswa2@metta.sch", role: "student", password: "Kopi-Susu-Enak-99", major: "TKJ", class_name: "X TKJ" }, { expect: 200 });
  await both("admin", "PATCH", "/api/admin/users/" + nu.id, { name: "Guru Baru Sekali", active: false }, { expect: 200 });
  await both("admin", "PATCH", "/api/admin/users/1", { active: false }, { expect: 400 });
  await both("admin", "PATCH", "/api/admin/users/" + nu.id, { password: "abc" }, { expect: 422 });
  await both("admin", "POST", "/api/admin/users/1/reset-password", undefined, { expect: 400 });
  await both("admin", "POST", "/api/admin/users/3/reset-password", undefined, { expect: 200 });
  const sk = (await both("admin", "POST", "/api/admin/skills", { name: "Cloud computing", category: "technical" }, { expect: 200 })).js.body;
  await both("admin", "POST", "/api/admin/skills", { name: "cloud computing" }, { expect: 409 });
  await both("admin", "PUT", "/api/admin/skills/" + sk.id, { name: "Cloud dasar", category: "technical" }, { expect: 200 });
  await both("admin", "DELETE", "/api/admin/skills/1", undefined, { expect: 400 });
  const car = (await both("admin", "POST", "/api/admin/careers", { name: "Cloud Ops Contoh", category: "Technology", majors: "TKJ", interest_tags: "technology", strength_tags: "technical", skills: [{ skill_id: sk.id, importance: 3 }, { skill_id: 1 }] }, { expect: 200 })).js.body;
  await both("admin", "POST", "/api/admin/careers", { name: "X Career", skills: [{ skill_id: 99999 }] }, { expect: 400 });
  await both("admin", "PUT", "/api/admin/careers/" + car.id, { name: "Cloud Ops Contoh Junior", category: "Technology", skills: [{ skill_id: sk.id, importance: 2 }] }, { expect: 200 });
  await both("admin", "DELETE", "/api/admin/careers/7", undefined, { expect: 400 });
  await both("admin", "DELETE", "/api/admin/skills/" + sk.id, undefined, { expect: 400 });
  await both("admin", "DELETE", "/api/admin/careers/" + car.id, undefined, { expect: 200 });
  await both("admin", "DELETE", "/api/admin/skills/" + sk.id, undefined, { expect: 200 });
  const co = (await both("admin", "POST", "/api/admin/companies", { name: "PT Contoh Admin", address: "Jl. A", verified: true, website: "contoh-admin.id", phone: "0761 555 555" }, { expect: 200 })).js.body;
  await both("admin", "PUT", "/api/admin/companies/" + co.id, { name: "PT Contoh Admin 2", number: 300, instagram: "@contoh_admin" }, { expect: 200 });
  await both("admin", "POST", "/api/admin/companies/import", { text: "301;PT Impor Satu;Jl. Satu\nPT Impor Dua\n\nPT Contoh Admin 2\nx\n302\tPT Impor Tiga" }, { expect: 200 });
  await both("admin", "DELETE", "/api/admin/companies/" + co.id, undefined, { expect: 200 });
  await both("admin", "GET", "/api/admin/analytics"); await both("admin", "GET", "/api/admin/users");

  // alumni
  await both("alumni", "GET", "/api/alumni/profile"); await both("alumni", "GET", "/api/alumni/content");
  await both("alumni", "PUT", "/api/alumni/profile", { graduation_year: 1980 }, { expect: 422 });
  await both("alumni", "PUT", "/api/alumni/profile", { graduation_year: 2022, major: "TKJ", workplace: "ISP Contoh", job_title: "Teknisi", bio: "Suka jaringan" }, { expect: 200 });
  const story = "Saya mulai dari magang di ISP kecil. Yang paling membantu adalah rajin mencatat konfigurasi dan berani bertanya kepada senior.";
  await both("alumni", "POST", "/api/alumni/content", { kind: "TIPS", title: "Tips", body: "pendek" }, { expect: 422 });
  await both("alumni", "POST", "/api/alumni/content", { kind: "TIPS", title: "Tips magang", body: story, career_id: 99999 }, { expect: 404 });
  const st1 = (await both("alumni", "POST", "/api/alumni/content", { kind: "CAREER_STORY", title: "Dari TKJ ke ISP", body: story, career_id: 1, submit: true }, { expect: 200 })).js.body;
  const st2 = (await both("alumni", "POST", "/api/alumni/content", { kind: "TIPS", title: "Draf tips", body: story }, { expect: 200 })).js.body;
  await both("alumni", "PUT", "/api/alumni/content/" + st2.id, { kind: "TIPS", title: "Draf tips 2", body: story, submit: true }, { expect: 200 });
  await both("alumni", "PUT", "/api/alumni/content/" + st2.id, { kind: "TIPS", title: "Draf tips 3", body: story }, { expect: 400 });
  await both("admin", "GET", "/api/admin/content");
  await both("admin", "POST", "/api/admin/content/" + st1.id + "/moderate", { decision: "PUBLISHED" }, { expect: 200 });
  await both("admin", "POST", "/api/admin/content/" + st2.id + "/moderate", { decision: "REJECTED", note: "x" }, { expect: 400 });
  await both("admin", "POST", "/api/admin/content/" + st2.id + "/moderate", { decision: "REJECTED", note: "Tambahkan contoh nyata" }, { expect: 200 });
  await both("alumni", "PUT", "/api/alumni/content/" + st2.id, { kind: "TIPS", title: "Draf tips 4", body: story }, { expect: 200 });
  await both("alumni", "DELETE", "/api/alumni/content/" + st1.id, undefined, { expect: 400 });
  await both("alumni", "DELETE", "/api/alumni/content/" + st2.id, undefined, { expect: 200 });
  await both("alumni", "GET", "/api/alumni/content"); await both("alumni", "GET", "/api/notifications");
  await both("student", "GET", "/api/alumni-stories"); await both("teacher", "GET", "/api/alumni-stories?q=isp");
  await both("admin", "GET", "/api/admin/audit");
  await both("student", "GET", "/api/student/dashboard");      // sesi lama student sudah diputus oleh reset password admin
}
main();
