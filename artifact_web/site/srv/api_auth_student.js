/* Metta Career — API: login, lupa password, siswa, belajar (padanan api/auth.py, api/recovery.py, api/student.py, api/learn.py). */
(function (root) {
  "use strict";
  var U = root.MU, S = root.MS, E = root.ME, CW = root.MCW, L = root.ML, F = S.F, api = S.api, HTTPError = S.HTTPError;
  var X = root.MX = root.MX || {};          // fungsi yang dipakai bersama antar-file API

  /* ---------- keamanan (security.py) ---------- */
  var COMMON = ("123456 1234567 12345678 123456789 1234567890 password password1 password123 passw0rd p@ssw0rd p@ssword qwerty qwertyui qwerty123 " +
    "qwertyuiop abc123 abcd1234 abcdefgh 1q2w3e4r 1qaz2wsx zaq12wsx qazwsx asdfghjkl zxcvbnm 111111 11111111 000000 00000000 0000000000 987654321 " +
    "12341234 12121212 123123123 88888888 77777777 iloveyou admin admin123 admin1234 welcome letmein monkey dragon sunshine princess football " +
    "baseball master login metta mettacareer metta123 metta2026 mettamaitreya sekolah smk smk123 rahasia indonesia bismillah sayang cintaku " +
    "kamu123 student student123 teacher teacher123 siswa123 guru123 rahasia123").split(" ");
  function checkPasswordRaw(pw, email, name, staff) {
    var need = staff ? 12 : 8;
    if (Array.from(pw).length < need) return "Password must be at least " + need + " characters" + (staff ? " for teachers and admins" : "");
    if (Array.from(pw).length > 200) return "Password is too long";
    var low = pw.toLowerCase(), base = low.replace(/[\d\W_]+$/, "");
    if (COMMON.indexOf(low) >= 0 || COMMON.indexOf(base) >= 0) return "This password is too common. Pick something harder to guess.";
    if (new Set(Array.from(low)).size < 4) return "Use more different characters";
    if (/^\d+$/.test(low)) return "Do not use only numbers";
    var classes = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter(function (r) { return r.test(pw); }).length;
    if (Array.from(pw).length < 14 && classes < 2) return "Mix at least two kinds of characters (letters, numbers, symbols) or make it 14+ characters long";
    var local = String(email || "").split("@")[0].toLowerCase();
    if (local.length >= 4 && low.indexOf(local) >= 0) return "Password must not contain your e-mail name";
    var parts = String(name || "").toLowerCase().split(/\s+/);
    for (var i = 0; i < parts.length; i++) if (parts[i].length >= 4 && low.indexOf(parts[i]) >= 0) return "Password must not contain your name";
    return null;
  }
  /* Semua yang memakai password asli lewat c.det: hasilnya dicatat, password-nya tidak pernah masuk catatan operasi. */
  X.checkPassword = function (c, pw, email, name, staff) { return c.det(function () { return checkPasswordRaw(pw, email, name, staff); }); };
  X.hashPassword = function (c, pw) { return c.det(function () { return U.hashPassword(pw); }); };
  X.verifyPassword = function (c, pw, stored) { return c.det(function () { return U.verifyPassword(pw, stored); }); };
  X.rateBlocked = async function (c, bucket, key, limit, window) {
    var n = (await c.db.one("SELECT COUNT(*) n FROM rate_events WHERE bucket=? AND key=? AND ts>?", bucket, String(key), c.nowEpoch - window)).n;
    return c.det(function () { return n >= limit; });
  };
  X.rateHit = async function (c, bucket, key) { if (c.replay) return; await c.db.runQuiet("INSERT INTO rate_events(bucket,key,ts) VALUES(?,?,?)", bucket, String(key), c.nowEpoch); };
  X.rateClear = async function (c, bucket, key) { if (c.replay) return; await c.db.runQuiet("DELETE FROM rate_events WHERE bucket=? AND key=?", bucket, String(key)); };
  X.clientIp = function (c) { return c.ip; };
  X.tooMany = function () { return new HTTPError(429, "Too many attempts. Please wait a few minutes and try again."); };
  var EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
  X.cleanEmail = function (v) { v = v.trim().toLowerCase(); if (!EMAIL.test(v) || v.length > 120) throw new Error("enter a valid email"); return v; };
  function newSession(c, uid, role) { if (c.replay) return; c.setCookie = S.sessions.create(uid, role); }

  /* ---------- auth ---------- */
  async function mePayload(c) {
    var u = c.user;
    var out = { id: u.id, name: u.name, email: u.email, role: u.role, lang: S.cleanLang(u.lang), must_change_password: !!u.must_change_password };
    if (u.role === "student") out.profile = (await c.db.one("SELECT school,major,class_name,goal FROM student_profiles WHERE user_id=?", u.id)) || {};
    return out;
  }
  X.mePayload = mePayload;
  var LOGIN_LIMITS = [["login_pair", 6, 300], ["login_email", 10, 900], ["login_ip", 30, 900]];

  api("/api/auth/config", "GET", { pub: true }, function () { return { register_code_required: false }; });
  api("/api/public/stats", "GET", { pub: true }, async function (c) {
    var n = async function (t) { return (await c.db.one("SELECT COUNT(*) x FROM " + t)).x; };
    return { careers: await n("careers"), companies: await n("companies"), questions: await n("questions"), majors: 2 };
  });
  api("/api/auth/login", "POST", { pub: true, model: { email: F.str({ check: X.cleanEmail }), password: F.str({ min: 1, max: 200 }), role: F.str({ def: "" }) } }, async function (c, b) {
    var ip = X.clientIp(c), keys = { login_pair: ip + "|" + b.email, login_email: b.email, login_ip: ip };
    for (var i = 0; i < LOGIN_LIMITS.length; i++) {
      var l = LOGIN_LIMITS[i];
      if (await X.rateBlocked(c, l[0], keys[l[0]], l[1], l[2])) { await c.db.run("INSERT INTO audit_log(actor_id,action,detail) VALUES(NULL,'login_blocked',?)", ip); await c.db.commit(); throw X.tooMany(); }
    }
    var u = await c.db.one("SELECT * FROM users WHERE email=?", b.email);
    var ok = !!u && !!u.active && X.verifyPassword(c, b.password, u.password_hash);
    if (!ok || (b.role && b.role !== u.role)) {
      for (var j = 0; j < LOGIN_LIMITS.length; j++) await X.rateHit(c, LOGIN_LIMITS[j][0], keys[LOGIN_LIMITS[j][0]]);
      await c.db.run("INSERT INTO audit_log(actor_id,action,detail) VALUES(?,'login_fail',?)", u ? u.id : null, ip);
      await c.db.commit();
      throw new HTTPError(401, "Wrong email or password");
    }
    await X.rateClear(c, "login_pair", keys.login_pair);
    newSession(c, u.id, u.role); c.user = u;
    await S.audit(c, "login_ok", ip);
    return mePayload(c);
  });
  api("/api/auth/register", "POST", { pub: true, model: { name: F.str({ min: 2, max: 80 }), email: F.str({ check: X.cleanEmail }), password: F.str({ min: 8, max: 200 }),
      school: F.str({ def: "SMK Metta Maitreya", max: 100 }), major: F.str({ pattern: "^(AK|TKJ)$" }), class_name: F.str({ min: 1, max: 20 }), goal: F.str({ def: "", max: 300 }), code: F.str({ def: "", max: 100 }) } },
  async function (c, b) {
    var ip = X.clientIp(c);
    if (await X.rateBlocked(c, "register_ip", ip, 10, 3600)) throw X.tooMany();
    var err = X.checkPassword(c, b.password, b.email, b.name); if (err) throw new HTTPError(422, err);
    if (await c.db.one("SELECT 1 x FROM users WHERE email=?", b.email)) throw new HTTPError(409, "This email is already registered");
    await X.rateHit(c, "register_ip", ip);
    var uid = await c.db.run("INSERT INTO users(email,name,password_hash,role,lang) VALUES(?,?,?,'student',?)", b.email, b.name.trim(), X.hashPassword(c, b.password), c.lang);
    await c.db.run("INSERT INTO student_profiles(user_id,school,major,class_name,goal) VALUES(?,?,?,?,?)", uid, b.school.trim(), b.major, b.class_name.trim(), b.goal.trim());
    await S.notify(c.db, uid, S.msg(c.lang, "note.welcome"));
    c.user = await c.db.one("SELECT * FROM users WHERE id=?", uid);
    newSession(c, uid, "student");
    await S.audit(c, "register", ip);
    return mePayload(c);
  });
  api("/api/auth/logout", "POST", {}, function (c) { if (!c.replay) S.sessions.remove(c.token); c.clearCookie = true; });
  api("/api/me", "GET", {}, function (c) { return mePayload(c); });
  api("/api/me/lang", "POST", { model: { lang: F.str({ pattern: "^(id|en)$" }) } }, async function (c, b) {
    await c.db.run("UPDATE users SET lang=? WHERE id=?", b.lang, c.user.id);
    c.user = await c.db.one("SELECT * FROM users WHERE id=?", c.user.id); return mePayload(c);
  });
  api("/api/me/profile", "PUT", { model: { name: F.str({ min: 2, max: 80 }), school: F.str({ def: "", max: 100 }), major: F.str({ def: "", pattern: "^(AK|TKJ|)$" }),
      class_name: F.str({ def: "", max: 20 }), goal: F.str({ def: "", max: 300 }) } }, async function (c, b) {
    await c.db.run("UPDATE users SET name=? WHERE id=?", b.name.trim(), c.user.id);
    if (c.user.role === "student") await c.db.run("UPDATE student_profiles SET school=?,major=?,class_name=?,goal=? WHERE user_id=?", b.school.trim(), b.major, b.class_name.trim(), b.goal.trim(), c.user.id);
    c.user = await c.db.one("SELECT * FROM users WHERE id=?", c.user.id); return mePayload(c);
  });
  api("/api/me/password", "POST", { model: { current: F.str({ max: 200 }), "new": F.str({ min: 8, max: 200 }) } }, async function (c, b) {
    var uid = String(c.user.id);
    if (await X.rateBlocked(c, "pw_change", uid, 5, 900)) throw X.tooMany();
    if (!X.verifyPassword(c, b.current, c.user.password_hash)) { await X.rateHit(c, "pw_change", uid); await c.db.commit(); throw new HTTPError(400, "Current password is wrong"); }
    var err = X.checkPassword(c, b["new"], c.user.email, c.user.name, c.user.role !== "student"); if (err) throw new HTTPError(422, err);
    await c.db.run("UPDATE users SET password_hash=?, must_change_password=0 WHERE id=?", X.hashPassword(c, b["new"]), c.user.id);
    if (!c.replay) S.sessions.removeUser(c.user.id, c.token);
    await X.rateClear(c, "pw_change", uid);
    await S.audit(c, "password_change");
  });
  api("/api/notifications", "GET", {}, async function (c) {
    var rows = await c.db.all("SELECT id,text,read,created_at FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 30", c.user.id);
    return { items: rows, unread: rows.filter(function (r) { return !r.read; }).length };
  });
  api("/api/notifications/read", "POST", {}, async function (c) { await c.db.run("UPDATE notifications SET read=1 WHERE user_id=?", c.user.id); });

  /* ---------- lupa password (recovery.py) ---------- */
  var STAFF = ["teacher", "admin"], CODE_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789", MAX_TRIES = 5;
  function newCode() { var p = []; for (var i = 0; i < 2; i++) { var s = ""; for (var j = 0; j < 4; j++) s += U.choice(CODE_CHARS); p.push(s); } return p.join("-"); }
  function codeHash(code) { return U.sha256hex(String(code).replace(/-/g, "").replace(/ /g, "").toUpperCase()); }
  api("/api/auth/forgot", "POST", { pub: true, model: { email: F.str({ max: 120, check: X.cleanEmail }) } }, async function (c, b) {
    var ip = X.clientIp(c);
    if ((await X.rateBlocked(c, "forgot_ip", ip, 8, 900)) || (await X.rateBlocked(c, "forgot_email", b.email, 3, 3600))) throw X.tooMany();
    await X.rateHit(c, "forgot_ip", ip); await X.rateHit(c, "forgot_email", b.email);
    var u = await c.db.one("SELECT id,active FROM users WHERE email=?", b.email);
    if (u && u.active && !(await c.db.one("SELECT 1 x FROM password_requests WHERE user_id=? AND status='PENDING'", u.id))) {
      await c.db.run("INSERT INTO password_requests(user_id) VALUES(?)", u.id);
      await c.db.run("INSERT INTO audit_log(actor_id,action,detail) VALUES(?,'password_request',?)", u.id, ip);
    }
    return { ok: true };
  });
  function allowed(c, row) { if (row.user_id === c.user.id) return false; return c.user.role === "admin" || row.role === "student"; }
  async function prow(c, rid) {
    var r = await c.db.one("SELECT pr.*, u.name, u.email, u.role FROM password_requests pr JOIN users u ON u.id=pr.user_id WHERE pr.id=?", rid);
    if (!r || !allowed(c, r)) throw S.notFound("Request not found"); return r;
  }
  api("/api/staff/password-requests", "GET", { roles: STAFF }, async function (c) {
    var rows = await c.db.all("SELECT pr.id, pr.status, pr.created_at, pr.handled_at, pr.expires_at, u.id user_id, u.name, u.email, u.role, sp.class_name FROM password_requests pr JOIN users u ON u.id=pr.user_id LEFT JOIN student_profiles sp ON sp.user_id=u.id WHERE pr.created_at > datetime('now','-30 days') ORDER BY CASE pr.status WHEN 'PENDING' THEN 0 WHEN 'APPROVED' THEN 1 ELSE 2 END, pr.id DESC");
    return { items: rows.filter(function (r) { return allowed(c, r); }) };
  });
  api("/api/staff/password-requests/{rid:int}/approve", "POST", { roles: STAFF }, async function (c, rid) {
    var r = await prow(c, rid);
    if (r.status !== "PENDING" && r.status !== "APPROVED") throw S.bad("This request is already closed");
    var code = c.live ? newCode() : null, h = c.det(function () { return codeHash(code); });      // hanya hash kode yang dicatat
    await c.db.run("UPDATE password_requests SET status='APPROVED', code_hash=?, expires_at=datetime('now','+1 day'), attempts=0, handled_by=?, handled_at=datetime('now') WHERE id=?", h, c.user.id, rid);
    await S.audit(c, "password_request_approved", rid + ":" + r.email);
    return { code: code, name: r.name, email: r.email, hours: 24 };
  });
  api("/api/staff/password-requests/{rid:int}/reject", "POST", { roles: STAFF }, async function (c, rid) {
    var r = await prow(c, rid);
    if (r.status !== "PENDING" && r.status !== "APPROVED") throw S.bad("This request is already closed");
    await c.db.run("UPDATE password_requests SET status='REJECTED', code_hash=NULL, handled_by=?, handled_at=datetime('now') WHERE id=?", c.user.id, rid);
    await S.audit(c, "password_request_rejected", rid + ":" + r.email);
  });
  api("/api/auth/reset", "POST", { pub: true, model: { email: F.str({ max: 120, check: X.cleanEmail }), code: F.str({ min: 4, max: 20 }), new_password: F.str({ min: 1, max: 200 }) } }, async function (c, b) {
    var ip = X.clientIp(c);
    if ((await X.rateBlocked(c, "reset_ip", ip, 15, 900)) || (await X.rateBlocked(c, "reset_email", b.email, 8, 900))) { await c.db.commit(); throw X.tooMany(); }
    var u = await c.db.one("SELECT * FROM users WHERE email=? AND active=1", b.email);
    var r = u ? await c.db.one("SELECT * FROM password_requests WHERE user_id=? AND status='APPROVED' AND expires_at > datetime('now') AND attempts < ? ORDER BY id DESC LIMIT 1", u.id, MAX_TRIES) : null;
    var given = c.det(function () { return codeHash(b.code); });
    var ok = !!r && (r.code_hash || "") === given;
    if (!ok) {
      await X.rateHit(c, "reset_ip", ip); await X.rateHit(c, "reset_email", b.email);
      if (r) await c.db.run("UPDATE password_requests SET attempts=attempts+1 WHERE id=?", r.id);
      await c.db.commit(); throw new HTTPError(400, "The code is wrong or has expired. Ask your teacher or admin for a new code.");
    }
    var err = X.checkPassword(c, b.new_password, u.email, u.name, u.role !== "student"); if (err) throw S.bad(err);
    await c.db.run("UPDATE users SET password_hash=?, must_change_password=0 WHERE id=?", X.hashPassword(c, b.new_password), u.id);
    if (!c.replay) S.sessions.removeUser(u.id);
    await c.db.run("UPDATE password_requests SET status='DONE', code_hash=NULL WHERE id=?", r.id);
    await X.rateClear(c, "reset_email", b.email); c.user = u;
    await S.audit(c, "password_reset_done", ip);
    return { ok: true };
  });

  /* ---------- siswa (student.py) ---------- */
  var ST = ["student"];
  api("/api/student/dashboard", "GET", { roles: ST }, async function (c) {
    var d = c.db, uid = c.user.id, plan = await E.activePlan(d, uid), task = null, target = null;
    if (plan) {
      target = plan.career_name;
      task = await d.one("SELECT id,title,description,est_hours,kind,skill_id FROM tasks WHERE plan_id=? AND status<>'COMPLETED' ORDER BY position LIMIT 1", plan.id);
      if (task) task = await E.taskView(d, task);
    }
    var ins = await E.insight(d, uid);
    var choices = await d.all("SELECT ic.rank, co.name FROM internship_choices ic JOIN companies co ON co.id=ic.company_id WHERE ic.user_id=? ORDER BY ic.rank", uid);
    var done = plan ? await d.one("SELECT COUNT(*) n, SUM(status='COMPLETED') done FROM tasks WHERE plan_id=?", plan.id) : { n: 0, done: 0 };
    var proj = await d.one("SELECT COUNT(*) n, SUM(status='VERIFIED') v FROM projects WHERE user_id=?", uid);
    var notes = await d.all("SELECT id,text,read,created_at FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 5", uid);
    return { name: c.user.name, target: target, readiness: await E.readiness(d, uid), today_task: task, milestone: { done: done.done || 0, total: done.n }, has_assessment: ins !== null,
      recommendation: ins ? ins.careers[0] : null, internship: choices, projects: { total: proj.n, verified: proj.v || 0 }, notifications: notes };
  });
  api("/api/student/questions", "GET", { roles: ST }, async function (c) {
    var qs = await c.db.all("SELECT id,kind,tag,text FROM questions ORDER BY id");
    qs.forEach(function (q) { q.text = c.db.tr("question", q.id, "text", q.text); });
    var sk = await c.db.all("SELECT id,name,category FROM skills ORDER BY category,name");
    sk.forEach(function (x) { x.name = c.db.tr("skill", x.id, "name", x.name); });
    sk = U.sortBy(sk, function (x) { return [x.category, x.name.toLowerCase()]; });
    return { questions: qs, skills: sk, my_skills: (await c.db.all("SELECT skill_id FROM student_skills WHERE user_id=?", c.user.id)).map(function (r) { return r.skill_id; }) };
  });
  api("/api/student/assessment", "POST", { roles: ST, model: { answers: F.dict(), skill_ids: F.list(F.int(), { def: function () { return []; } }) } }, async function (c, b) {
    var qs = await c.db.all("SELECT id,kind,tag FROM questions"), ids = {}, ans = {};
    qs.forEach(function (q) { ids[String(q.id)] = 1; });
    Object.keys(b.answers).forEach(function (k) {
      if (!ids[String(k)]) throw S.bad("Unknown question");
      var v = b.answers[k], n;
      if (typeof v === "number" && isFinite(v)) n = Math.trunc(v);
      else if (typeof v === "string" && /^\s*[-+]?\d+\s*$/.test(v)) n = parseInt(v, 10);
      else if (typeof v === "boolean") n = v ? 1 : 0;
      else throw S.bad("Answers must be numbers 1 to 5");
      if (!(n >= 1 && n <= 5)) throw S.bad("Answers must be 1 to 5");
      ans[String(k)] = n;
    });
    if (Object.keys(ans).length < qs.length) throw S.bad("Please answer all questions (" + Object.keys(ans).length + "/" + qs.length + ")");
    var scores = E.scoreAnswers(qs, ans), valid = {};
    (await c.db.all("SELECT id FROM skills")).forEach(function (r) { valid[r.id] = 1; });
    var seen = {};
    for (var i = 0; i < b.skill_ids.length; i++) { var sid = b.skill_ids[i]; if (seen[sid]) continue; seen[sid] = 1; if (valid[sid]) await E.raiseSkill(c.db, c.user.id, sid, E.SELF_CLAIMED); }
    await c.db.run("INSERT INTO assessments(user_id,answers,scores) VALUES(?,?,?)", c.user.id, E.dumps(ans), E.dumps(scores, true));
    return E.insight(c.db, c.user.id);
  });
  api("/api/student/insight", "GET", { roles: ST }, async function (c) { var i = await E.insight(c.db, c.user.id); if (!i) throw S.notFound("Take the Self Discovery assessment first"); return i; });
  api("/api/student/insight/save", "POST", { roles: ST }, async function (c) {
    var a = await E.latestAssessment(c.db, c.user.id); if (!a) throw S.notFound("Nothing to save yet");
    await c.db.run("UPDATE assessments SET saved=1 WHERE id=?", a.id);
  });

  api("/api/careers", "GET", { roles: ["student", "teacher", "admin", "alumni"] }, async function (c) {
    var q = (c.query.get("q") || "").trim().toLowerCase(), cat = c.query.get("category") || "";
    var rows = (await c.db.all("SELECT id,name,category,description,majors,trend,is_new FROM careers")).map(function (r) { return E.careerText(c.db, r, ["name", "description"]); });
    var top = {};
    (await c.db.all("SELECT cs.career_id cid, s.id sid, s.name, cs.importance FROM career_skills cs JOIN skills s ON s.id=cs.skill_id ORDER BY cs.career_id, cs.importance DESC, s.name")).forEach(function (r) {
      top[r.cid] = top[r.cid] || []; if (top[r.cid].length < 3) top[r.cid].push(c.db.tr("skill", r.sid, "name", r.name));
    });
    rows.forEach(function (r) { r.skills = top[r.id] || []; r.trend = !!r.trend; r.is_new = !!r.is_new; var m = String(r.majors || "").split(",").filter(Boolean); delete r.majors; r.majors = m; });
    rows = U.sortBy(rows, function (r) { return [r.name.toLowerCase()]; });
    var short = {}; (await c.db.all("SELECT career_id FROM shortlist WHERE user_id=?", c.user.id)).forEach(function (r) { short[r.career_id] = 1; });
    var counts = {}, corder = [];
    rows.forEach(function (r) { if (!(r.category in counts)) { counts[r.category] = 0; corder.push(r.category); } counts[r.category]++; });
    function hit(r) { return !q || r.name.toLowerCase().indexOf(q) >= 0 || r.description.toLowerCase().indexOf(q) >= 0 || r.skills.some(function (s) { return s.toLowerCase().indexOf(q) >= 0; }); }
    var out = rows.filter(function (r) { return hit(r) && (!cat || r.category === cat); }).map(function (r) { return Object.assign({}, r, { saved: !!short[r.id] }); });
    return { items: out, total: rows.length, categories: U.sortBy(corder, function (k) { return [-counts[k], k]; }), counts: counts };
  });
  api("/api/careers/{cid:int}", "GET", { roles: ["student", "teacher", "admin"] }, async function (c, cid) {
    var r = await c.db.one("SELECT * FROM careers WHERE id=?", cid); if (!r) throw S.notFound("Career not found");
    r = E.careerText(c.db, r); r.skills = await E.careerSkills(c.db, cid);
    var mine = c.user.role === "student" ? await E.skillMap(c.db, c.user.id) : {};
    r.skills.forEach(function (s) { s.level = E.lvl(c.db, mine[s.id]); });
    return r;
  });
  api("/api/student/compare", "POST", { roles: ST, model: { ids: F.list(F.int(), { min: 2, max: 3 }) } }, async function (c, b) {
    var out = [];
    for (var i = 0; i < b.ids.length; i++) {
      var r = await c.db.one("SELECT id,name,education_path,example_projects,growth FROM careers WHERE id=?", b.ids[i]); if (!r) throw S.notFound("Career not found");
      r = E.careerText(c.db, r, ["name", "education_path", "example_projects", "growth"]); r.skills = (await E.careerSkills(c.db, b.ids[i])).map(function (s) { return s.name; }); out.push(r);
    }
    return { items: out };
  });
  api("/api/student/shortlist/{cid:int}", "POST", { roles: ST }, async function (c, cid) {
    if (!(await c.db.one("SELECT 1 x FROM careers WHERE id=?", cid))) throw S.notFound("Career not found");
    await c.db.run("INSERT OR IGNORE INTO shortlist(user_id,career_id) VALUES(?,?)", c.user.id, cid);
  });
  api("/api/student/shortlist/{cid:int}", "DELETE", { roles: ST }, async function (c, cid) { await c.db.run("DELETE FROM shortlist WHERE user_id=? AND career_id=?", c.user.id, cid); });

  api("/api/student/recommendations", "GET", { roles: ST }, async function (c) {
    var r = await E.recommend(c.db, c.user.id); if (r === null) throw S.notFound("Take the Self Discovery assessment first");
    return { items: r.slice(0, 5).map(function (x) { var o = Object.assign({}, x); delete o.reason_codes; return o; }) };
  });
  api("/api/student/plan/preview/{cid:int}", "GET", { roles: ST }, async function (c, cid) { var p = await E.planPreview(c.db, c.user.id, cid); if (!p) throw S.notFound("Career not found"); return p; });
  async function planGet(c) {
    var p = await E.activePlan(c.db, c.user.id); if (!p) return { plan: null };
    var prev = await E.planPreview(c.db, c.user.id, p.career_id);
    var rows = await c.db.all("SELECT * FROM tasks WHERE plan_id=? ORDER BY position", p.id), tasks = [];
    for (var i = 0; i < rows.length; i++) tasks.push(await E.taskView(c.db, rows[i]));
    var ms = {}, morder = [];
    tasks.forEach(function (t) { if (!ms[t.milestone]) { ms[t.milestone] = { milestone: t.milestone, skill_id: t.skill_id, tasks: [] }; morder.push(t.milestone); } ms[t.milestone].tasks.push(t); });
    var names = {}; (await c.db.all("SELECT id,name FROM skills")).forEach(function (r) { names[r.id] = c.db.tr("skill", r.id, "name", r.name); });
    morder.forEach(function (k) { ms[k].skill = names[ms[k].skill_id] || ""; });
    var mine = await E.skillMap(c.db, c.user.id), cs = await E.careerSkills(c.db, p.career_id);
    return { plan: { id: p.id, career_id: p.career_id, career: p.career_name, reasons: E.renderReasons(c.db, JSON.parse(p.reasons)), teacher_note: p.teacher_note, created_at: p.created_at,
        example_projects: prev ? prev.career.example_projects : "" },
      current_skills: cs.filter(function (s) { return s.id in mine; }).map(function (s) { return { id: s.id, name: s.name, level: E.lvl(c.db, mine[s.id]) }; }),
      skill_gap: cs.filter(function (s) { return (mine[s.id] || 0) < E.GAP_THRESHOLD; }).map(function (s) { return { id: s.id, name: s.name }; }),
      milestones: morder.map(function (k) { return ms[k]; }), readiness: await E.readiness(c.db, c.user.id) };
  }
  api("/api/student/plan", "POST", { roles: ST, model: { career_id: F.int() } }, async function (c, b) {
    if ((await E.createPlan(c.db, c.user.id, b.career_id)) === null) throw S.notFound("Career not found");
    return planGet(c);
  });
  api("/api/student/plan", "GET", { roles: ST }, planGet);

  api("/api/student/tasks/{tid:int}", "PATCH", { roles: ST, model: { status: F.str({ pattern: "^(NOT_STARTED|IN_PROGRESS|COMPLETED)$" }) } }, async function (c, b, tid) {
    var t = await c.db.one("SELECT t.* FROM tasks t JOIN plans p ON p.id=t.plan_id WHERE t.id=? AND p.user_id=? AND p.status='ACTIVE'", tid, c.user.id);
    if (!t) throw S.notFound("Task not found");
    if (b.status === "COMPLETED") { var why = await X.completionBlock(c, t); if (why) throw S.bad(why); }
    await c.db.run("UPDATE tasks SET status=?, completed_at=CASE WHEN ?='COMPLETED' THEN datetime('now') ELSE NULL END WHERE id=?", b.status, b.status, tid);
    if (b.status === "COMPLETED" && t.skill_id && (t.kind === "STUDY" || t.kind === "PRACTICE")) await E.raiseSkill(c.db, c.user.id, t.skill_id, E.LEARNING);
    return { readiness: await E.logReadiness(c.db, c.user.id) };
  });

  /* ---------- project ---------- */
  var PROJECT_MODEL = { title: F.str({ min: 3, max: 120 }), description: F.str({ def: "", max: 2000 }), link: F.str({ def: "", max: 300 }), skill_ids: F.list(F.int(), { def: function () { return []; } }),
    problem: F.str({ def: "", max: 600 }), solution: F.str({ def: "", max: 600 }), result: F.str({ def: "", max: 600 }), technology: F.str({ def: "", max: 200 }),
    demo_url: F.str({ def: "", max: 300 }), repo_url: F.str({ def: "", max: 300 }), doc_url: F.str({ def: "", max: 300 }) };
  X.validLink = function (link) {
    link = U.strip(link); if (!link) return;
    for (var i = 0; i < link.length; i++) { var o = link.charCodeAt(i); if (o <= 32 || o === 127 || link[i] === "\\") throw S.bad("The link must not contain spaces or special characters"); }
    var u = U.urlparse(link);
    if ((u.scheme !== "http" && u.scheme !== "https") || !u.hostname) throw S.bad("Link must start with http:// or https:// and include a website name");
  };
  function projectFields(b) { ["demo_url", "repo_url", "doc_url"].forEach(function (k) { X.validLink(b[k]); }); return ["problem", "solution", "result", "technology", "demo_url", "repo_url", "doc_url"].map(function (k) { return b[k].trim(); }); }
  X.projectRow = async function (c, p) {
    p.files = (await X.filesMap(c.db, "project", [p.id]))[p.id];
    var names = {}; (await c.db.all("SELECT id,name FROM skills")).forEach(function (r) { names[r.id] = c.db.tr("skill", r.id, "name", r.name); });
    p.skills = JSON.parse(p.skill_ids).filter(function (i) { return i in names; }).map(function (i) { return names[i]; }); return p;
  };
  async function rows(c, list) { var out = []; for (var i = 0; i < list.length; i++) out.push(await X.projectRow(c, list[i])); return out; }
  X.rowsProject = rows;
  api("/api/student/projects", "GET", { roles: ST }, async function (c) { return { items: await rows(c, await c.db.all("SELECT * FROM projects WHERE user_id=? ORDER BY id DESC", c.user.id)) }; });
  async function syncEvidence(c, pid, link) {
    await c.db.run("DELETE FROM project_evidence WHERE project_id=? AND kind='LINK'", pid);
    if (link.trim()) await c.db.run("INSERT INTO project_evidence(project_id,kind,url) VALUES(?,'LINK',?)", pid, link.trim());
  }
  async function validSkills(c, ids) { var want = {}; ids.forEach(function (i) { want[i] = 1; }); return (await c.db.all("SELECT id FROM skills")).map(function (r) { return r.id; }).filter(function (i) { return want[i]; }); }
  api("/api/student/projects", "POST", { roles: ST, model: PROJECT_MODEL }, async function (c, b) {
    X.validLink(b.link);
    var ids = await validSkills(c, b.skill_ids), extra = projectFields(b);
    var pid = await c.db.run.apply(c.db, ["INSERT INTO projects(user_id,title,description,link,skill_ids,problem,solution,result,technology,demo_url,repo_url,doc_url) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
      c.user.id, b.title.trim(), b.description.trim(), b.link.trim(), E.dumps(ids)].concat(extra));
    await syncEvidence(c, pid, b.link);
    for (var i = 0; i < ids.length; i++) await E.raiseSkill(c.db, c.user.id, ids[i], E.PROJECT_EVIDENCE);
    await E.logReadiness(c.db, c.user.id);
    return X.projectRow(c, await c.db.one("SELECT * FROM projects WHERE id=?", pid));
  });
  api("/api/student/projects/{pid:int}", "PUT", { roles: ST, model: PROJECT_MODEL }, async function (c, b, pid) {
    var p = await c.db.one("SELECT * FROM projects WHERE id=? AND user_id=?", pid, c.user.id); if (!p) throw S.notFound("Project not found");
    if (p.status !== "NEEDS_REVISION") throw S.bad("Only projects that need revision can be edited");
    X.validLink(b.link);
    var ids = await validSkills(c, b.skill_ids), extra = projectFields(b);
    await c.db.run.apply(c.db, ["UPDATE projects SET title=?,description=?,link=?,skill_ids=?,problem=?,solution=?,result=?,technology=?,demo_url=?,repo_url=?,doc_url=?,status='SUBMITTED',updated_at=datetime('now') WHERE id=?",
      b.title.trim(), b.description.trim(), b.link.trim(), E.dumps(ids)].concat(extra, [pid]));
    await syncEvidence(c, pid, b.link);
    for (var i = 0; i < ids.length; i++) await E.raiseSkill(c.db, c.user.id, ids[i], E.PROJECT_EVIDENCE);
    return X.projectRow(c, await c.db.one("SELECT * FROM projects WHERE id=?", pid));
  });
  api("/api/student/portfolio", "GET", { roles: ST }, async function (c) {
    var uid = c.user.id, verified = await rows(c, await c.db.all("SELECT * FROM projects WHERE user_id=? AND status='VERIFIED' ORDER BY id DESC", uid));
    var skills = await c.db.all("SELECT s.id, s.name, ss.level FROM student_skills ss JOIN skills s ON s.id=ss.skill_id WHERE ss.user_id=? ORDER BY ss.level DESC, s.name", uid);
    skills = skills.map(function (s) { return { name: c.db.tr("skill", s.id, "name", s.name), level: s.level, evidence: E.lvl(c.db, s.level) }; });
    var prof = (await c.db.one("SELECT school,major,class_name FROM student_profiles WHERE user_id=?", uid)) || {}, plan = await E.activePlan(c.db, uid);
    return { name: c.user.name, profile: prof, target: plan ? plan.career_name : null, projects: verified, skills: skills, courses: await CW.completedCourses(c.db, uid),
      pending_projects: (await c.db.one("SELECT COUNT(*) n FROM projects WHERE user_id=? AND status<>'VERIFIED'", uid)).n };
  });
  api("/api/student/outcome", "GET", { roles: ST }, async function (c) {
    var uid = c.user.id; await E.logReadiness(c.db, uid);
    var log = await c.db.all("SELECT value FROM readiness_log WHERE user_id=? ORDER BY id DESC LIMIT 2", uid);
    var now = log.length ? log[0].value : 0, before = log.length > 1 ? log[1].value : now;
    var verified = await c.db.all("SELECT s.id, s.name FROM student_skills ss JOIN skills s ON s.id=ss.skill_id WHERE ss.user_id=? AND ss.level=4", uid);
    verified.forEach(function (v) { v.name = c.db.tr("skill", v.id, "name", v.name); });
    var plan = await E.activePlan(c.db, uid), nxt = plan ? await c.db.one("SELECT title,kind,skill_id FROM tasks WHERE plan_id=? AND status<>'COMPLETED' ORDER BY position LIMIT 1", plan.id) : null;
    if (nxt) nxt = await E.taskView(c.db, nxt);
    return { before: before, now: now, verified_skills: verified.map(function (v) { return v.name; }), next_task: nxt ? nxt.title : null, has_plan: plan !== null };
  });

  /* ---------- magang ---------- */
  X.co = function (r, lang, uid) {
    var idn = lang === "id", sector = (idn ? r.sector_id : r.sector) || r.sector, about = (idn ? r.about_id : r.about) || r.about;
    var q = U.quotePlus((r.name + " " + (r.address || "Pekanbaru")).trim()), mine = uid !== undefined && uid !== null && r.submitted_by === uid, ig = r.instagram || "";
    return Object.assign({ id: r.id, number: r.number, name: r.name, address: r.address, sector: sector, about: about, sector_en: r.sector, sector_id: r.sector_id, about_en: r.about, about_id: r.about_id,
      source: r.source, verified: !!r.verified, sector_guess: !!r.sector_guess, maps_url: "https://www.google.com/maps/search/?api=1&query=" + q,
      website: r.website || "", instagram: ig, instagram_url: ig ? "https://www.instagram.com/" + ig + "/" : "", phone: r.phone || "", tasks: r.tasks || "", majors: r.majors || "", work_terms: r.work_terms || "",
      status: r.status, mine: mine, review_note: mine ? (r.review_note || "") : "" }, L.searchLinks(r.name, r.address || ""));
  };
  api("/api/companies", "GET", { roles: ["student", "teacher", "admin"] }, async function (c) {
    var q = (c.query.get("q") || "").trim().toLowerCase(), loc = (c.query.get("location") || "").trim().toLowerCase(), uid = c.user.role === "student" ? c.user.id : null;
    var rows = (await c.db.all("SELECT * FROM companies ORDER BY number, name")).filter(function (r) { return r.status === "approved" || (uid !== null && r.submitted_by === uid); });
    var items = rows.filter(function (r) { return (!q || r.name.toLowerCase().indexOf(q) >= 0) && (!loc || (r.address || "").toLowerCase().indexOf(loc) >= 0); }).map(function (r) { return X.co(r, c.lang, uid); });
    return { items: items, total: rows.length, verified: rows.filter(function (r) { return r.verified; }).length, checklist: E.DATA.meta.ASK.map(function (p) { return c.lang === "id" ? p[1] : p[0]; }) };
  });
  async function internshipGet(c) {
    var ch = await c.db.all("SELECT ic.rank, ic.purpose, co.id company_id, co.name, co.address FROM internship_choices ic JOIN companies co ON co.id=ic.company_id WHERE ic.user_id=? ORDER BY ic.rank", c.user.id);
    var prof = (await c.db.one("SELECT class_name FROM student_profiles WHERE user_id=?", c.user.id)) || {};
    var fr = await c.db.all("SELECT name, class_name FROM internship_friends WHERE user_id=? ORDER BY id", c.user.id);
    return { full_name: c.user.name, class_name: prof.class_name !== undefined ? prof.class_name : "", choices: ch, friends: fr, status: ch.length ? "Saved" : "Not chosen" };
  }
  api("/api/student/internship", "GET", { roles: ST }, internshipGet);
  api("/api/student/internship", "PUT", { roles: ST, model: { class_name: F.str({ min: 1, max: 20 }), company_ids: F.list(F.int(), { min: 1, max: 3 }),
      purposes: F.list(F.str(), { def: function () { return []; }, max: 3 }), friends: F.list(F.model({ name: F.str({ min: 2, max: 80 }), class_name: F.str({ def: "", max: 20 }) }), { def: function () { return []; }, max: 3 }) } },
  async function (c, b) {
    if (new Set(b.company_ids).size !== b.company_ids.length) throw S.bad("Choose different companies for each choice");
    for (var i = 0; i < b.company_ids.length; i++) {
      var co = await c.db.one("SELECT status, submitted_by FROM companies WHERE id=?", b.company_ids[i]);
      if (!co || !(co.status === "approved" || (co.status === "pending" && co.submitted_by === c.user.id))) throw S.notFound("Company not found");
    }
    if (b.purposes.some(function (p) { return Array.from(p).length > 500; })) throw S.bad("Purpose is too long (max 500 characters)");
    await c.db.run("DELETE FROM internship_choices WHERE user_id=?", c.user.id);
    for (var r = 1; r <= b.company_ids.length; r++) await c.db.run("INSERT INTO internship_choices(user_id,rank,company_id,purpose) VALUES(?,?,?,?)", c.user.id, r, b.company_ids[r - 1], (r - 1 < b.purposes.length ? b.purposes[r - 1] : "").trim());
    await c.db.run("DELETE FROM internship_friends WHERE user_id=?", c.user.id);
    for (var f = 0; f < b.friends.length; f++) await c.db.run("INSERT INTO internship_friends(user_id,name,class_name) VALUES(?,?,?)", c.user.id, b.friends[f].name.trim(), b.friends[f].class_name.trim());
    await c.db.run("UPDATE student_profiles SET class_name=? WHERE user_id=?", b.class_name.trim(), c.user.id);
    return internshipGet(c);
  });

  api("/api/student/assistant", "POST", { roles: ST, model: { question: F.str({ min: 2, max: 500 }) } }, async function (c, b) {
    var q = b.question.toLowerCase(), uid = c.user.id, d = c.db, Lg = c.lang;
    var plan = await E.activePlan(d, uid), recs = await E.recommend(d, uid);
    function has() { for (var i = 0; i < arguments.length; i++) if (q.indexOf(arguments[i]) >= 0) return true; return false; }
    function say(key, reasons, nextKey, kw) { return { answer: S.msg(Lg, key, kw), reasons: reasons || [], next_action: nextKey ? S.msg(Lg, nextKey) : "" }; }
    if (recs === null) return say("ai.unknown_you", null, "ai.open_discovery");
    if (has("why", "reason", "recommend", "alasan", "kenapa", "cocok", "mengapa", "rekomendasi")) { var top = recs[0]; return say("ai.why", top.reasons, "ai.why_next", { name: top.name, match: top.match }); }
    if (has("internship", "magang", "pkl")) { var n = (await d.one("SELECT COUNT(*) n FROM internship_choices WHERE user_id=?", uid)).n; return say(n ? "ai.intern_some" : "ai.intern_none", null, "ai.open_internship", { n: n }); }
    if (has("gap", "skill", "kurang", "belajar", "learn", "keahlian")) {
      if (!plan) return say("ai.gap_noplan", null, "ai.open_plan");
      var mine = await E.skillMap(d, uid), gap = (await E.careerSkills(d, plan.career_id)).filter(function (s) { return (mine[s.id] || 0) < E.GAP_THRESHOLD; }).map(function (s) { return s.name; });
      return say("ai.gap", null, "ai.open_learning", { career: plan.career_name, skills: gap.join(", ") || S.msg(Lg, "ai.gap_none") });
    }
    if (has("progress", "ready", "readiness", "kesiapan", "kemajuan", "perkembangan")) return say("ai.ready", null, "ai.open_learning", { value: await E.readiness(d, uid) });
    if (has("start", "begin", "first", "mulai", "next", "what should", "selanjutnya", "berikutnya", "harus")) {
      if (!plan) return say("ai.start_noplan", recs[0].reasons, "ai.open_plan", { name: recs[0].name });
      var t = await d.one("SELECT title,kind,skill_id FROM tasks WHERE plan_id=? AND status<>'COMPLETED' ORDER BY position LIMIT 1", plan.id);
      if (t) return say("ai.next_task", null, "ai.open_learning", { title: (await E.taskView(d, t)).title });
      return say("ai.all_done", null, "ai.open_learning");
    }
    return say("ai.fallback");
  });

  /* ---------- belajar (learn.py) ---------- */
  async function task(c, tid) {
    var t = await c.db.one("SELECT t.* FROM tasks t JOIN plans p ON p.id=t.plan_id WHERE t.id=? AND p.user_id=? AND p.status='ACTIVE'", tid, c.user.id);
    if (!t) throw S.notFound("Task not found"); return t;
  }
  function opt(o, lang) { var i = o.indexOf("||"), en = i >= 0 ? o.slice(0, i) : o, idn = i >= 0 ? o.slice(i + 2) : ""; return lang === "id" && idn ? idn : en; }
  function lesson(c, skillName) {
    var Ls = E.DATA.meta.LESSONS[skillName], i = c.lang === "id";
    if (Ls) return { goal: Ls.goal[i ? 1 : 0], steps: Ls.steps.map(function (s) { return s[i ? 1 : 0]; }), practice: Ls.practice[i ? 1 : 0], authored: true, quiz: Ls.quiz };
    var g = E.DATA.meta.GENERIC[i ? "id" : "en"];
    return { goal: g.goal, steps: g.steps.map(function (s) { return U.fmt(s, { s: skillName }); }), practice: U.fmt(g.practice, { s: skillName }), authored: false, quiz: [] };
  }
  function attempts(c, sid) { return c.db.all("SELECT score,total,passed,created_at FROM quiz_attempts WHERE user_id=? AND skill_id=? ORDER BY id DESC", c.user.id, sid); }
  function order(uid, sid, qi, n, nOpts) { var idx = []; for (var i = 0; i < nOpts; i++) idx.push(i); return U.rng(uid + ":" + sid + ":" + qi + ":" + n).shuffle(idx); }
  async function state(c, t) {
    var skill = t.skill_id ? await c.db.one("SELECT id,name FROM skills WHERE id=?", t.skill_id) : null, name = skill ? skill.name : "", Ls = lesson(c, name);
    var done = new Set((await c.db.all("SELECT idx FROM task_steps WHERE task_id=?", t.id)).map(function (r) { return r.idx; }));
    var att = skill ? await attempts(c, t.skill_id) : [], passed = att.some(function (a) { return a.passed; }), ready = true, why = "";
    if (t.kind === "STUDY" && done.size < Ls.steps.length) { ready = false; why = "Tick every step first."; }
    else if (t.kind === "PRACTICE") { if (Ls.authored && !passed) { ready = false; why = "Pass the quiz first (score 70% or more)."; } }
    else if (t.kind === "APPLY") {
      var mine = await c.db.all("SELECT skill_ids FROM projects WHERE user_id=?", c.user.id);
      if (!mine.some(function (p) { return JSON.parse(p.skill_ids).indexOf(t.skill_id) >= 0; })) { ready = false; why = "Submit a project that uses this skill first."; }
    }
    return { L: Ls, done: done, att: att, passed: passed, ready: ready, why: why };
  }
  X.completionBlock = async function (c, t) { if (["STUDY", "PRACTICE", "APPLY"].indexOf(t.kind) < 0) return ""; return (await state(c, t)).why; };
  async function quizWait(c, sid) {
    var uid = c.user.id, cd = E.DATA.meta.COOLDOWN_SEC;
    var last = await c.db.one("SELECT CAST(strftime('%s','now') AS INTEGER) - CAST(strftime('%s',created_at) AS INTEGER) ago FROM quiz_attempts WHERE user_id=? AND skill_id=? AND passed=0 ORDER BY id DESC LIMIT 1", uid, sid);
    if (!last) return 0;
    var fails = (await c.db.one("SELECT COUNT(*) n FROM quiz_attempts WHERE user_id=? AND skill_id=? AND passed=0 AND CAST(strftime('%s','now') AS INTEGER) - CAST(strftime('%s',created_at) AS INTEGER) < 600", uid, sid)).n;
    return Math.max(0, cd * Math.min(Math.max(fails, 1), 5) - last.ago);
  }
  async function learnGet(c, tid) {
    var t = await task(c, tid), st = await state(c, t), Ls = st.L;
    var sk = await c.db.one("SELECT name FROM skills WHERE id=?", t.skill_id), view = await E.taskView(c.db, t), quiz = [];
    if (Ls.authored) {
      var n = st.att.length;
      Ls.quiz.forEach(function (q, qi) { var o = order(c.user.id, t.skill_id, qi, n, q[2].length); quiz.push({ q: c.lang === "id" ? q[1] : q[0], options: o.map(function (j) { return opt(q[2][j], c.lang); }) }); });
    }
    var best = st.att.length ? Math.max.apply(null, st.att.map(function (a) { return U.pyRound(100 * a.score / a.total); })) : null;
    return { id: t.id, kind: t.kind, status: t.status, title: view.title, skill: sk ? c.db.tr("skill", t.skill_id, "name", sk.name) : "", est_hours: t.est_hours, difficulty: view.difficulty,
      goal: Ls.goal, steps: Ls.steps.map(function (s, i) { return { text: s, done: st.done.has(i) }; }), practice: Ls.practice, has_quiz: Ls.authored, quiz: quiz,
      pass_percent: Math.trunc(E.DATA.meta.LPASS * 100), attempts: st.att.length, best: best, passed: st.passed, ready: st.ready, blocked_reason: st.why, wait: Ls.authored ? await quizWait(c, t.skill_id) : 0 };
  }
  api("/api/student/learn/{tid:int}", "GET", { roles: ST }, learnGet);
  api("/api/student/learn/{tid:int}/step", "POST", { roles: ST, model: { idx: F.int({ ge: 0, le: 20 }), done: F.bool() } }, async function (c, b, tid) {
    var t = await task(c, tid), skill = await c.db.one("SELECT name FROM skills WHERE id=?", t.skill_id), Ls = lesson(c, skill ? skill.name : "");
    if (t.kind !== "STUDY" || b.idx >= Ls.steps.length) throw S.bad("Step not found");
    if (t.status === "COMPLETED") throw S.bad("This task is already completed");
    if (b.done) await c.db.run("INSERT OR IGNORE INTO task_steps(task_id,idx) VALUES(?,?)", tid, b.idx);
    else await c.db.run("DELETE FROM task_steps WHERE task_id=? AND idx=?", tid, b.idx);
    if (t.status === "NOT_STARTED") await c.db.run("UPDATE tasks SET status='IN_PROGRESS' WHERE id=?", tid);
    return learnGet(c, tid);
  });
  api("/api/student/learn/{tid:int}/quiz", "POST", { roles: ST, model: { answers: F.list(F.int(), { min: 1, max: 20 }) } }, async function (c, b, tid) {
    var t = await task(c, tid); if (t.kind !== "PRACTICE") throw S.bad("This task has no quiz");
    var sk = await c.db.one("SELECT name FROM skills WHERE id=?", t.skill_id), Ls = lesson(c, sk ? sk.name : "");
    if (!Ls.authored) throw S.bad("This task has no quiz");
    var quiz = Ls.quiz; if (b.answers.length !== quiz.length) throw S.bad("Answer every question");
    if ((await quizWait(c, t.skill_id)) > 0) throw S.bad("Please wait a moment before trying again");
    var n = (await attempts(c, t.skill_id)).length, score = 0, res = [];
    quiz.forEach(function (q, qi) {
      var o = order(c.user.id, t.skill_id, qi, n, q[2].length), a = b.answers[qi];
      if (!(a >= 0 && a < o.length)) throw S.bad("Answer every question");
      var ok = o[a] === q[3]; if (ok) score++;
      res.push({ correct: ok, why: c.lang === "id" ? q[5] : q[4] });
    });
    var passed = score / quiz.length >= E.DATA.meta.LPASS; if (!passed) res = [];
    await c.db.run("INSERT INTO quiz_attempts(user_id,skill_id,score,total,passed) VALUES(?,?,?,?,?)", c.user.id, t.skill_id, score, quiz.length, passed ? 1 : 0);
    if (t.status === "NOT_STARTED") await c.db.run("UPDATE tasks SET status='IN_PROGRESS' WHERE id=?", tid);
    return { score: score, total: quiz.length, percent: U.pyRound(100 * score / quiz.length), passed: passed, results: res, wait: passed ? 0 : await quizWait(c, t.skill_id) };
  });
})(typeof window !== "undefined" ? window : globalThis);
