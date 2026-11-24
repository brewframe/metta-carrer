/* Metta Career — backend di browser: kerangka API (rute, peran, validasi, transaksi, catatan operasi).
   Padanan metta/core.py + metta/messages.py. Handler ditulis di api_*.js dengan async/await. */
(function (root) {
  "use strict";
  var U = root.MU;
  var S = {};

  /* ---------- error ---------- */
  function HTTPError(status, message) { this.status = status; this.message = message; }
  S.HTTPError = HTTPError;
  S.bad = function (m) { return new HTTPError(400, m || "Bad request"); };
  S.notFound = function (m) { return new HTTPError(404, m || "Not found"); };
  S.forbidden = function (m) { return new HTTPError(403, m || "Not allowed"); };

  /* ---------- pesan (messages.py) ---------- */
  var LANG_DEFAULT = "id";
  S.cleanLang = function (v, fb) { v = String(v || "").trim().toLowerCase().slice(0, 5); if (v.indexOf("id") === 0) return "id"; if (v.indexOf("en") === 0) return "en"; return fb || LANG_DEFAULT; };
  var TAGS = { technology: ["teknologi", "technology"], finance: ["keuangan", "finance"], business: ["bisnis", "business"], design: ["desain", "design"], data: ["data", "data"],
    people: ["bidang yang berhubungan dengan orang", "working with people"], analytical: ["analitis", "analytical"], problem_solving: ["pemecahan masalah", "problem solving"],
    detail: ["ketelitian", "attention to detail"], logical: ["berpikir logis", "logical thinking"], communication: ["komunikasi", "communication"], creativity: ["kreativitas", "creativity"],
    collaboration: ["kerja sama tim", "teamwork"], technical: ["kemampuan teknis", "technical ability"] };
  var LEVELS = { 1: ["Klaim sendiri", "Self claimed"], 2: ["Sedang belajar", "Learning"], 3: ["Bukti project", "Project evidence"], 4: ["Diverifikasi guru", "Teacher verified"] };
  var CATALOG = {
    "reason.interest_fit": ["Minatmu cocok dengan bidang ini ({tags}).", "Your interests fit this field ({tags})."],
    "reason.interest_mid": ["Minatmu pada bidang ini tergolong sedang.", "Your interest in this field is moderate."],
    "reason.strength_fit": ["Kekuatanmu sesuai dengan yang dibutuhkan karier ini ({tags}).", "Your strengths match what this career needs ({tags})."],
    "reason.major_path": ["Ini jalur yang umum untuk siswa {major}.", "It is a common path for {major} students."],
    "reason.have_skills": ["Kamu sudah punya titik awal di: {skills}.", "You already have a starting point in: {skills}."],
    "reason.build_skills": ["Skill yang perlu dibangun: {skills}.", "Skills to build: {skills}."],
    "reason.weak": ["Ini pilihan yang bisa dijelajahi, belum cocok kuat.", "This is a possible option to explore, not a strong match yet."],
    "task.STUDY.title": ["Pelajari {skill}", "Learn {skill}"],
    "task.STUDY.desc": ["Baca atau tonton materi pemula tentang {skill}, lalu tulis 5 poin penting.", "Read or watch a beginner lesson on {skill} and write down 5 key points."],
    "task.PRACTICE.title": ["Latihan {skill}", "Practice {skill}"],
    "task.PRACTICE.desc": ["Kerjakan 3 latihan kecil tentang {skill} dan catat bagian yang sulit.", "Do 3 small exercises on {skill} and note what was hard."],
    "task.APPLY.title": ["Terapkan {skill} di mini project", "Apply {skill} in a mini project"],
    "task.APPLY.desc": ["Buat sesuatu yang kecil dengan {skill}, lalu kirim di menu Project sebagai bukti.", "Build something small that uses {skill}, then submit it under Projects as evidence."],
    "difficulty.Beginner": ["Pemula", "Beginner"], "difficulty.Intermediate": ["Menengah", "Intermediate"],
    "ai.unknown_you": ["Aku belum cukup mengenalmu. Mulai dari Self Discovery (sekitar 5 menit), lalu aku bisa menyarankan karier dan menjelaskan alasannya.",
      "I do not know you well enough yet. Start with Self Discovery (about 5 minutes). Then I can suggest careers and explain why."],
    "ai.open_discovery": ["Buka Self Discovery", "Open Self Discovery"],
    "ai.why": ["Karier yang paling cocok denganmu adalah {name} ({match}%). Ini saran, bukan keputusan. Kamu yang memilih jalanmu.",
      "Your top match is {name} ({match}%). This is a suggestion, not a decision. You choose your path."],
    "ai.why_next": ["Bandingkan dengan karier lain di menu Jelajah", "Compare it with another career in Explore"],
    "ai.intern_some": ["Kamu sudah menyimpan {n} dari 3 pilihan magang.", "You have saved {n} of 3 internship choices."],
    "ai.intern_none": ["Kamu belum memilih tempat magang. Kamu bisa memilih sampai 3 perusahaan.", "You have not chosen an internship yet. You can choose up to 3 companies."],
    "ai.open_internship": ["Buka Magang", "Open Internship"],
    "ai.gap_noplan": ["Pilih target karier di Career Plan dulu, baru aku bisa menunjukkan skill gap-mu.", "Choose a target career in Career Plan first, then I can show your skill gap."],
    "ai.open_plan": ["Buka Career Plan", "Open Career Plan"],
    "ai.gap": ["Skill yang masih butuh bukti untuk {career}: {skills}", "Skills that still need evidence for {career}: {skills}"],
    "ai.gap_none": ["tidak ada, kerja bagus!", "none, great work!"],
    "ai.open_learning": ["Buka menu Belajar", "Open Learning"],
    "ai.ready": ["Kesiapan kariermu {value}%. Angkanya naik saat kamu menyelesaikan tugas dan skill-mu punya bukti project serta verifikasi guru.",
      "Your career readiness is {value}%. It grows when you finish tasks and your skills get project evidence and teacher verification."],
    "ai.start_noplan": ["Langkah pertama yang bagus: jadikan {name} (atau karier lain yang kamu suka) targetmu di Career Plan.",
      "A good first step: make {name} (or any career you like) your target in Career Plan."],
    "ai.next_task": ["Langkah berikutnya: {title}.", "Your next step: {title}."],
    "ai.all_done": ["Semua tugas di rencanamu sudah selesai. Kirim project sebagai bukti!", "You finished all tasks in your plan. Submit a project as evidence!"],
    "ai.fallback": ["Aku bisa membantu soal: kenapa sebuah karier cocok denganmu, skill gap, kemajuanmu, langkah berikutnya, atau pilihan magang. Coba tanyakan salah satunya.",
      "I can help with: why a career fits you, your skill gap, your progress, your next step, or your internship choices. Try asking one of those."],
    "ai.next_prefix": ["Berikutnya: ", "Next: "],
    "note.welcome": ["Selamat datang di Metta Career! Mulai dari Self Discovery untuk menemukan karier yang cocok denganmu.", "Welcome to Metta Career! Start with Self Discovery to find careers that fit you."],
    "note.company_submitted": ["{student} mengajukan tempat magang baru: {company}. Mohon diperiksa.", "{student} submitted a new internship place: {company}. Please review it."],
    "note.company_approved": ["Tempat magang yang kamu ajukan, {company}, sudah disetujui guru dan tampil di daftar.", "The internship place you submitted, {company}, was approved by your teacher and is now in the list."],
    "note.company_rejected": ["Ajuan tempat magang {company} belum bisa disetujui: {note}", "Your internship place {company} could not be approved yet: {note}"],
    "note.feedback": ["Masukan baru dari {teacher}: {text}", "New feedback from {teacher}: {text}"],
    "note.guidance": ["{teacher} menambahkan arahan di Career Plan-mu.", "{teacher} added guidance to your Career Plan."],
    "note.course_done": ["Kamu menyelesaikan kursus karier \"{career}\". Skill kariernya naik ke tingkat Belajar.", "You finished the career course \"{career}\". Its skills moved up to the Learning level."],
    "note.verified": ["Project \"{title}\" sudah diverifikasi. Sekarang tampil di portfolio-mu.", "Your project \"{title}\" was verified. It now appears in your portfolio."],
    "note.revision": ["Project \"{title}\" perlu direvisi: {note}", "Your project \"{title}\" needs revision: {note}"],
    "note.story_published": ["Ceritamu \"{title}\" sudah diterbitkan dan bisa dibaca siswa.", "Your story \"{title}\" is published and students can read it."],
    "note.story_rejected": ["Ceritamu \"{title}\" belum bisa diterbitkan. Catatan admin: {note}", "Your story \"{title}\" could not be published yet. Admin note: {note}"],
    "opp.company_title": ["PKL di {name}", "Internship at {name}"],
    "note.item_verified": ["\"{title}\" sudah diverifikasi guru dan tampil sebagai terverifikasi di portfolio-mu.", "\"{title}\" was verified by a teacher and now shows as verified in your portfolio."]
  };
  S.CATALOG = CATALOG;
  S.msg = function (lang, key, kw) { var p = CATALOG[key]; if (!p) throw new Error("missing message " + key); var t = S.cleanLang(lang) === "id" ? p[0] : p[1]; return kw ? U.fmt(t, kw) : t; };
  S.tagName = function (lang, tag) { var p = TAGS[tag]; if (!p) return String(tag).replace(/_/g, " "); return S.cleanLang(lang) === "id" ? p[0] : p[1]; };
  S.levelName = function (lang, level) { var p = LEVELS[level]; return S.cleanLang(lang) === "id" ? p[0] : p[1]; };

  /* ---------- validasi (meniru pesan pydantic v2) ---------- */
  function VErr(loc, msg) { this.loc = loc; this.msg = msg; }
  var F = {};
  F.str = function (o) { o = o || {}; o.t = "str"; return o; };
  F.int = function (o) { o = o || {}; o.t = "int"; return o; };
  F.bool = function (o) { o = o || {}; o.t = "bool"; return o; };
  F.dict = function (o) { o = o || {}; o.t = "dict"; return o; };
  F.list = function (item, o) { o = o || {}; o.t = "list"; o.item = item; return o; };
  F.model = function (fields, o) { o = o || {}; o.t = "model"; o.fields = fields; return o; };
  S.F = F;
  function plural(n, w) { return n + " " + w + (n === 1 ? "" : "s"); }
  function vfield(spec, v, loc) {
    if (v === null && spec.nullable) return null;
    if (spec.t === "str") {
      if (typeof v !== "string") throw new VErr(loc, "Input should be a valid string");
      var n = Array.from(v).length;
      if (spec.min !== undefined && n < spec.min) throw new VErr(loc, "String should have at least " + plural(spec.min, "character"));
      if (spec.max !== undefined && n > spec.max) throw new VErr(loc, "String should have at most " + plural(spec.max, "character"));
      if (spec.pattern && !new RegExp(spec.pattern).test(v)) throw new VErr(loc, "String should match pattern '" + spec.pattern + "'");
      if (spec.check) { try { v = spec.check(v); } catch (e) { throw new VErr(loc, "Value error, " + e.message); } }
      return v;
    }
    if (spec.t === "int") {
      var x = v;
      if (typeof x === "string" && /^\s*[-+]?\d+\s*$/.test(x)) x = parseInt(x, 10);
      if (typeof x === "boolean" || typeof x !== "number" || !isFinite(x)) throw new VErr(loc, "Input should be a valid integer");
      if (Math.floor(x) !== x) throw new VErr(loc, "Input should be a valid integer, got a number with a fractional part");
      if (spec.ge !== undefined && x < spec.ge) throw new VErr(loc, "Input should be greater than or equal to " + spec.ge);
      if (spec.le !== undefined && x > spec.le) throw new VErr(loc, "Input should be less than or equal to " + spec.le);
      return x;
    }
    if (spec.t === "bool") {
      if (typeof v === "boolean") return v;
      if (v === 0 || v === 1) return !!v;
      if (typeof v === "string") { var s = v.toLowerCase(); if (["true", "1", "yes", "on", "t", "y"].indexOf(s) >= 0) return true; if (["false", "0", "no", "off", "f", "n"].indexOf(s) >= 0) return false; }
      throw new VErr(loc, "Input should be a valid boolean");
    }
    if (spec.t === "dict") { if (!v || typeof v !== "object" || Array.isArray(v)) throw new VErr(loc, "Input should be a valid dictionary"); return v; }
    if (spec.t === "list") {
      if (!Array.isArray(v)) throw new VErr(loc, "Input should be a valid list");
      var out = v.map(function (x, i) { return vfield(spec.item, x, loc.concat([i])); });
      if (spec.min !== undefined && out.length < spec.min) throw new VErr(loc, "List should have at least " + plural(spec.min, "item") + " after validation, not " + out.length);
      if (spec.max !== undefined && out.length > spec.max) throw new VErr(loc, "List should have at most " + plural(spec.max, "item") + " after validation, not " + out.length);
      return out;
    }
    if (spec.t === "model") return vmodel(spec.fields, v, loc);
    throw new Error("bad spec");
  }
  function vmodel(fields, v, loc) {
    if (!v || typeof v !== "object" || Array.isArray(v)) throw new VErr(loc, "Input should be a valid dictionary or instance of Model");
    var out = {};
    Object.keys(fields).forEach(function (k) {
      var spec = fields[k];
      if (!Object.prototype.hasOwnProperty.call(v, k) || v[k] === undefined) {
        if (Object.prototype.hasOwnProperty.call(spec, "def")) { out[k] = typeof spec.def === "function" ? spec.def() : spec.def; return; }
        throw new VErr(loc.concat([k]), "Field required");
      }
      out[k] = vfield(spec, v[k], loc.concat([k]));
    });
    return out;
  }
  S.validate = function (fields, raw) {
    try { return vmodel(fields, raw, []); }
    catch (e) { if (e instanceof VErr) throw new HTTPError(422, e.loc.join(".") + ": " + e.msg); throw e; }
  };

  /* ---------- akses database per permintaan ---------- */
  var LOCAL_TABLES = { sessions: 1, rate_events: 1 };
  function rewrite(sql) {
    return sql.replace(/datetime\('now'/g, "datetime(op_now()").replace(/date\('now'/g, "date(op_now()").replace(/strftime\('%s','now'\)/g, "strftime('%s',op_now())");
  }
  function writesShared(sql) {
    var m = /^\s*(INSERT(?:\s+OR\s+\w+)?\s+INTO|UPDATE|DELETE\s+FROM|REPLACE\s+INTO)\s+(\w+)/i.exec(sql);
    if (!m) return /^\s*(INSERT|UPDATE|DELETE|REPLACE|CREATE|DROP|ALTER)/i.test(sql);
    return !LOCAL_TABLES[m[2].toLowerCase()];
  }
  S.TR = { id: null, en: null };              // terjemahan isi data, dimuat sekali per bahasa
  function DB(adapter, lang) { this.a = adapter; this.lang = lang; this.dirty = false; this.keptDirty = false; }
  DB.prototype.all = function (sql) { var a = Array.prototype.slice.call(arguments, 1); return this.a.exec(rewrite(sql), a).then(function (r) { return r.rows; }); };
  DB.prototype.one = function (sql) { var a = Array.prototype.slice.call(arguments, 1); return this.a.exec(rewrite(sql), a).then(function (r) { return r.rows.length ? r.rows[0] : null; }); };
  DB.prototype.run = function (sql) {
    var a = Array.prototype.slice.call(arguments, 1), self = this;
    if (writesShared(sql)) self.dirty = true;
    return this.a.exec(rewrite(sql), a, true).then(function (r) { return r.lastId; });
  };
  DB.prototype.runQuiet = function (sql) { var a = Array.prototype.slice.call(arguments, 1); return this.a.exec(rewrite(sql), a, true).then(function (r) { return r.lastId; }); };
  /* commit() di tengah handler (sebelum melempar error) tetap menyimpan perubahan, sama seperti server Python */
  DB.prototype.commit = function () { var self = this; return this.a.exec("COMMIT", []).then(function () { if (self.dirty) self.keptDirty = true; return self.a.exec("BEGIN", []); }); };
  DB.prototype.tr = function (entity, eid, field, def) { var m = S.TR[this.lang]; if (!m) return def; var v = m.get(entity + "|" + eid + "|" + field); return v === undefined ? def : v; };
  S.loadTranslations = function (adapter) {
    return adapter.exec("SELECT entity,entity_id,field,lang,value FROM translations", []).then(function (r) {
      var id = new Map(), en = new Map();
      r.rows.forEach(function (x) { (x.lang === "id" ? id : en).set(x.entity + "|" + x.entity_id + "|" + x.field, x.value); });
      S.TR.id = id; S.TR.en = en;
    });
  };

  S.audit = function (c, action, detail) { return c.db.run("INSERT INTO audit_log(actor_id,action,detail) VALUES(?,?,?)", c.user ? c.user.id : null, action, detail || ""); };
  S.notify = function (db, uid, text) { return db.run("INSERT INTO notifications(user_id,text) VALUES(?,?)", uid, text); };
  S.userLang = async function (db, uid) { var r = await db.one("SELECT lang FROM users WHERE id=?", uid); return r ? S.cleanLang(r.lang) : LANG_DEFAULT; };

  /* ---------- sesi (disimpan di browser ini saja, tidak ikut database bersama) ---------- */
  var SESS_KEY = "metta_sessions_v1";
  function loadSess() { try { return JSON.parse(localStorage.getItem(SESS_KEY) || "{}") || {}; } catch (e) { return S._mem || (S._mem = {}); } }
  function saveSess(o) { try { localStorage.setItem(SESS_KEY, JSON.stringify(o)); } catch (e) { S._mem = o; } }
  S.sessions = {
    create: function (uid, role) {
      var hours = role === "student" ? 24 * 7 : 12, token = U.tokenUrlsafe(32), all = loadSess(), now = Date.now();
      Object.keys(all).forEach(function (k) { if (all[k].exp <= now) delete all[k]; });
      all[U.sha256hex(token)] = { uid: uid, exp: now + hours * 3600 * 1000 };
      var mine = Object.keys(all).filter(function (k) { return all[k].uid === uid; });
      while (mine.length > 5) delete all[mine.shift()];
      saveSess(all); return [token, hours * 3600];
    },
    lookup: function (token) { if (!token || token.length > 100) return null; var s = loadSess()[U.sha256hex(token)]; return s && s.exp > Date.now() ? s.uid : null; },
    remove: function (token) { if (!token) return; var all = loadSess(); delete all[U.sha256hex(token)]; saveSess(all); },
    removeUser: function (uid, exceptToken) { var all = loadSess(), keep = exceptToken ? U.sha256hex(exceptToken) : null; Object.keys(all).forEach(function (k) { if (all[k].uid === uid && k !== keep) delete all[k]; }); saveSess(all); }
  };

  /* ---------- rute ---------- */
  var ROUTES = [];
  S.ROUTES = ROUTES;
  S.api = function (path, method, opt, fn) {
    opt = opt || {};
    var names = [], rx = "^" + path.replace(/\{(\w+)(?::(\w+))?\}/g, function (m, n, t) { names.push([n, t]); return t === "int" ? "([0-9]+)" : "([^/]+)"; }) + "$";
    ROUTES.push({ path: path, method: method || "GET", rx: new RegExp(rx), names: names, roles: opt.roles || null, model: opt.model || null, pub: !!opt.pub, fn: fn });
  };

  /* Satu permintaan: transaksi, peran, validasi, handler. op = catatan operasi (diisi saat live, dibaca saat replay). */
  S.dispatch = async function (adapter, req) {
    var u = req.url, qi = u.indexOf("?"), path = qi >= 0 ? u.slice(0, qi) : u, query = new URLSearchParams(qi >= 0 ? u.slice(qi + 1) : "");
    var method = (req.method || "GET").toUpperCase(), route = null, params = null, pathHit = false;
    for (var i = 0; i < ROUTES.length; i++) {
      var m = ROUTES[i].rx.exec(path); if (!m) continue; pathHit = true;
      if (ROUTES[i].method !== method) continue;
      route = ROUTES[i]; params = {}; route.names.forEach(function (n, j) { params[n[0]] = n[1] === "int" ? parseInt(m[j + 1], 10) : decodeURIComponent(m[j + 1]); }); break;
    }
    if (!route) return { status: pathHit ? 405 : 404, body: { error: pathHit ? "Method Not Allowed" : "Not Found" } };
    if (route.model && req.body === undefined) return { status: 415, body: { error: "Send the body as application/json" } };
    var replay = !!req.replay, op = req.op || { rec: [] }, ri = 0;
    var db = new DB(adapter, "en");
    var c = { db: db, user: null, lang: LANG_DEFAULT, query: query, ip: req.ip || "browser", replay: replay, live: !replay, token: req.token || null,
      setCookie: null, clearCookie: false, now: req.now, nowEpoch: req.nowEpoch, nowMs: req.nowEpoch * 1000, op: op, forceLog: false };
    c.det = function (fn) { if (replay) return op.rec[ri++]; var v = fn(); op.rec.push(v === undefined ? null : v); return v; };
    await adapter.exec("BEGIN", []);
    var user = null;
    try {
      if (replay) { if (req.uid) user = await db.one("SELECT * FROM users WHERE id=? AND active=1", req.uid); }
      else { var uid = S.sessions.lookup(c.token); if (uid) user = await db.one("SELECT * FROM users WHERE id=? AND active=1", uid); }
      if (!route.pub) {
        if (!user) throw new HTTPError(401, "Please sign in");
        if (route.roles && route.roles.indexOf(user.role) < 0) throw new HTTPError(403, "You do not have access to this");
        var stale = await db.one("SELECT 1 x FROM users WHERE id=? AND (last_active_at IS NULL OR last_active_at < datetime('now','-3600 seconds'))", user.id);
        if (stale && !replay) c.forceLog = true;            // aktivitas siswa terlihat oleh guru di perangkat lain (paling sering sekali per jam)
        await db.runQuiet("UPDATE users SET last_active_at=datetime('now') WHERE id=? AND (last_active_at IS NULL OR last_active_at < datetime('now','-60 seconds'))", user.id);
      }
      c.user = user;
      var body = null;
      if (route.model) body = S.validate(route.model, req.body);
      c.lang = req.lang ? S.cleanLang(req.lang) : (user ? S.cleanLang(user.lang) : LANG_DEFAULT); db.lang = c.lang;
      var args = [c]; if (route.model) args.push(body); route.names.forEach(function (n) { args.push(params[n[0]]); });
      var result = await route.fn.apply(null, args);
      await adapter.exec("COMMIT", []);
      return { status: 200, body: result === undefined || result === null ? { ok: true } : result, ctx: c, wrote: db.dirty || db.keptDirty || c.forceLog, uid: user ? user.id : null };
    } catch (e) {
      try { await adapter.exec("ROLLBACK", []); } catch (x) { /* sudah tidak ada transaksi */ }
      if (e instanceof HTTPError) return { status: e.status, body: { error: e.message }, ctx: c, wrote: db.keptDirty, uid: user ? user.id : null };
      if (typeof console !== "undefined") console.error("[metta-server]", method, path, e);
      return { status: 500, body: { error: "Something went wrong on the server" }, ctx: c, wrote: false };
    }
  };

  root.MS = S;
  if (typeof module !== "undefined") module.exports = S;
})(typeof window !== "undefined" ? window : globalThis);
