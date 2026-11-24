/* Metta Career — logika bisnis (padanan engine.py, coursework.py, links.py). Rekomendasi berbasis aturan, bisa dijelaskan. */
(function (root) {
  "use strict";
  var U = root.MU, S = root.MS;
  var E = {}, CW = {}, L = {};
  E.SELF_CLAIMED = 1; E.LEARNING = 2; E.PROJECT_EVIDENCE = 3; E.TEACHER_VERIFIED = 4;
  var LEVEL_WEIGHT = { 1: 0.25, 2: 0.5, 3: 0.8, 4: 1.0 };
  E.GAP_THRESHOLD = 3;
  E.DATA = { courses: {}, meta: null };          // diisi saat start dari courses.json dan meta.json

  E.lvl = function (db, level) { return LEVEL_WEIGHT[level] ? S.levelName(db.lang, level) : null; };
  E.jl = function (s) { try { return s ? JSON.parse(s) : []; } catch (e) { return []; } };
  E.csv = function (s) { return String(s || "").split(",").map(function (x) { return x.trim(); }).filter(Boolean); };
  /* json.dumps gaya Python (", " dan ": ", ensure_ascii); floats=true menulis angka bulat sebagai 1.0 */
  E.dumps = function (o, floats) {
    function str(s) { return JSON.stringify(s).replace(/[\u007f-\uffff]/g, function (ch) { return "\\u" + ("000" + ch.charCodeAt(0).toString(16)).slice(-4); }); }
    function enc(v) {
      if (v === null || v === undefined) return "null";
      if (typeof v === "boolean") return v ? "true" : "false";
      if (typeof v === "number") { var t = String(v); return floats && Number.isInteger(v) ? t + ".0" : t; }
      if (typeof v === "string") return str(v);
      if (Array.isArray(v)) return "[" + v.map(enc).join(", ") + "]";
      return "{" + Object.keys(v).map(function (k) { return str(k) + ": " + enc(v[k]); }).join(", ") + "}";
    }
    return enc(o);
  };

  /* ---------- assessment ---------- */
  E.scoreAnswers = function (questions, answers) {
    var acc = {}, order = [];
    questions.forEach(function (q) {
      var v = answers[String(q.id)]; if (v === undefined || v === null) return;
      var k = q.kind + "\u0000" + q.tag; if (!acc[k]) { acc[k] = []; order.push(k); }
      acc[k].push((parseInt(v, 10) - 1) / 4);
    });
    var out = { interest: {}, strength: {} };
    order.forEach(function (k) { var p = k.split("\u0000"), vals = acc[k]; out[p[0]][p[1]] = U.pyRound(U.sum(vals) / vals.length, 3); });
    return out;
  };
  E.latestAssessment = async function (db, uid, savedOnly) {
    var a = await db.one("SELECT * FROM assessments WHERE user_id=?" + (savedOnly ? " AND saved=1" : "") + " ORDER BY id DESC LIMIT 1", uid);
    if (a) { a.scores = JSON.parse(a.scores); a.answers = JSON.parse(a.answers); }
    return a;
  };
  E.skillMap = async function (db, uid) { var m = {}; (await db.all("SELECT skill_id, level FROM student_skills WHERE user_id=?", uid)).forEach(function (r) { m[r.skill_id] = r.level; }); return m; };
  E.raiseSkill = async function (db, uid, sid, level) {
    var cur = await db.one("SELECT level FROM student_skills WHERE user_id=? AND skill_id=?", uid, sid);
    if (cur === null) await db.run("INSERT INTO student_skills(user_id,skill_id,level) VALUES(?,?,?)", uid, sid, level);
    else if (cur.level < level) await db.run("UPDATE student_skills SET level=? WHERE user_id=? AND skill_id=?", level, uid, sid);
  };
  E.careerSkills = async function (db, cid) {
    var rows = await db.all("SELECT s.id, s.name, s.category, cs.importance FROM career_skills cs JOIN skills s ON s.id=cs.skill_id WHERE cs.career_id=? ORDER BY cs.importance DESC, s.name", cid);
    rows.forEach(function (r) { r.name = db.tr("skill", r.id, "name", r.name); }); return rows;
  };
  E.skillName = function (db, sid, def) { return db.tr("skill", sid, "name", def === undefined ? "" : def); };
  E.careerText = function (db, row, fields) {
    fields = fields || ["name", "description", "responsibilities", "education_path", "example_projects", "growth"];
    var out = Object.assign({}, row); fields.forEach(function (f) { if (f in out) out[f] = db.tr("career", row.id, f, row[f]); }); return out;
  };
  E.renderReason = function (db, item) {
    if (typeof item === "string") return item;
    var code = item[0], arg = item.length > 1 ? item[1] : null, Lg = db.lang;
    if (code === "interest_fit") return S.msg(Lg, "reason.interest_fit", { tags: arg.map(function (t) { return S.tagName(Lg, t); }).join(", ") });
    if (code === "strength_fit") return S.msg(Lg, "reason.strength_fit", { tags: arg.map(function (t) { return S.tagName(Lg, t); }).join(", ") });
    if (code === "major_path") return S.msg(Lg, "reason.major_path", { major: arg });
    if (code === "have_skills" || code === "build_skills") return S.msg(Lg, "reason." + code, { skills: arg.map(function (i) { return E.skillName(db, i, String(i)); }).join(", ") });
    return S.msg(Lg, "reason." + code);
  };
  E.renderReasons = function (db, items) { return items.map(function (i) { return E.renderReason(db, i); }); };
  E.taskView = async function (db, t) {
    var out = Object.assign({}, t);
    if (["STUDY", "PRACTICE", "APPLY"].indexOf(t.kind) >= 0 && t.skill_id) {
      var base = await db.one("SELECT name FROM skills WHERE id=?", t.skill_id), name = E.skillName(db, t.skill_id, base ? base.name : "");
      out.title = S.msg(db.lang, "task." + t.kind + ".title", { skill: name }); out.description = S.msg(db.lang, "task." + t.kind + ".desc", { skill: name });
    }
    if (S.CATALOG["difficulty." + t.difficulty]) out.difficulty = S.msg(db.lang, "difficulty." + t.difficulty);
    return out;
  };

  /* ---------- rekomendasi ---------- */
  var W_INTEREST = 0.35, W_STRENGTH = 0.25, W_SKILL = 0.25, W_MAJOR = 0.15;
  function avg(tags, scores) { var v = tags.filter(function (t) { return t in scores; }).map(function (t) { return scores[t]; }); return v.length ? U.sum(v) / v.length : 0.0; }
  E.recommend = async function (db, uid, limit) {
    var a = await E.latestAssessment(db, uid); if (!a) return null;
    var prof = (await db.one("SELECT major FROM student_profiles WHERE user_id=?", uid)) || { major: "" };
    var skills = await E.skillMap(db, uid), out = [];
    var careers = await db.all("SELECT * FROM careers ORDER BY id");
    for (var ci = 0; ci < careers.length; ci++) {
      var c = careers[ci];
      var i = avg(E.csv(c.interest_tags), a.scores.interest), s = avg(E.csv(c.strength_tags), a.scores.strength);
      var req = await E.careerSkills(db, c.id), tot = U.sum(req.map(function (r) { return r.importance; })) || 1;
      var have = U.sum(req.map(function (r) { return r.importance * (LEVEL_WEIGHT[skills[r.id] || 0] || 0); })), sk = have / tot;
      var mjs = E.csv(c.majors), mj = prof.major && mjs.indexOf(prof.major) >= 0 ? (mjs.length === 1 ? 1.0 : 0.6) : 0.0;
      var score = W_INTEREST * i + W_STRENGTH * s + W_SKILL * sk + W_MAJOR * mj, codes = [];
      if (i >= 0.6) codes.push(["interest_fit", E.csv(c.interest_tags).filter(function (t) { return (a.scores.interest[t] || 0) >= 0.6; })]);
      else if (i >= 0.4) codes.push(["interest_mid"]);
      if (s >= 0.6) codes.push(["strength_fit", E.csv(c.strength_tags).filter(function (t) { return (a.scores.strength[t] || 0) >= 0.6; })]);
      if (mj) codes.push(["major_path", prof.major]);
      var known = req.filter(function (r) { return r.id in skills; }).map(function (r) { return r.id; });
      if (known.length) codes.push(["have_skills", known.slice(0, 3)]);
      var gaps = req.filter(function (r) { return (skills[r.id] || 0) < E.GAP_THRESHOLD; }).map(function (r) { return r.id; });
      if (gaps.length) codes.push(["build_skills", gaps.slice(0, 3)]);
      if (!codes.length) codes.push(["weak"]);
      var lc = E.careerText(db, c, ["name", "description"]);
      out.push({ _s: score, career_id: c.id, name: lc.name, category: c.category, description: lc.description, match: U.pyRound(score * 100), reasons: E.renderReasons(db, codes), reason_codes: codes,
        parts: { interest: U.pyRound(i * 100), strength: U.pyRound(s * 100), skills: U.pyRound(sk * 100), major: U.pyRound(mj * 100) } });
    }
    out = U.sortBy(out, function (r) { return [-r._s, r.name]; });
    out.forEach(function (r) { delete r._s; });
    return limit ? out.slice(0, limit) : out;
  };
  E.insight = async function (db, uid) {
    var a = await E.latestAssessment(db, uid); if (!a) return null;
    function top(d) {
      var srt = U.sortBy(Object.keys(d).map(function (k) { return [k, d[k]]; }), function (kv) { return [-kv[1]]; });
      var x = srt.filter(function (kv) { return kv[1] >= 0.5; }).map(function (kv) { return kv[0]; }).slice(0, 3);
      return x.length ? x : srt.map(function (kv) { return kv[0]; }).slice(0, 2);
    }
    var ints = top(a.scores.interest), strs = top(a.scores.strength);
    var careers = (await E.recommend(db, uid, 3)).map(function (r) { var o = Object.assign({}, r); delete o.reason_codes; return o; });
    return { assessment_id: a.id, saved: !!a.saved, interests: ints, strengths: strs, interest_labels: ints.map(function (t) { return S.tagName(db.lang, t); }),
      strength_labels: strs.map(function (t) { return S.tagName(db.lang, t); }), scores: a.scores, careers: careers };
  };

  /* ---------- rencana ---------- */
  E.makeTasks = function (skill, lang) {
    return [["STUDY", "Beginner", 3], ["PRACTICE", "Beginner", 4], ["APPLY", "Intermediate", 6]].map(function (x) {
      return { kind: x[0], title: S.msg(lang, "task." + x[0] + ".title", { skill: skill }), difficulty: x[1], est_hours: x[2], description: S.msg(lang, "task." + x[0] + ".desc", { skill: skill }) };
    });
  };
  E.planPreview = async function (db, uid, cid) {
    var c = await db.one("SELECT * FROM careers WHERE id=?", cid); if (!c) return null;
    var skills = await E.skillMap(db, uid), req = await E.careerSkills(db, cid);
    var current = req.filter(function (r) { return r.id in skills; }).map(function (r) { return { id: r.id, name: r.name, level: E.lvl(db, skills[r.id]) }; });
    var gap = req.filter(function (r) { return (skills[r.id] || 0) < E.GAP_THRESHOLD; });
    var milestones = gap.slice(0, 6).map(function (r, n) { return { milestone: n + 1, skill_id: r.id, skill: r.name, tasks: E.makeTasks(r.name, db.lang) }; });
    var lc = E.careerText(db, c, ["name", "description", "example_projects"]);
    return { career: { id: c.id, name: lc.name, description: lc.description, example_projects: lc.example_projects }, current_skills: current,
      skill_gap: gap.map(function (r) { return { id: r.id, name: r.name, importance: r.importance }; }), milestones: milestones };
  };
  E.activePlan = async function (db, uid) {
    var p = await db.one("SELECT p.*, c.name AS career_name FROM plans p JOIN careers c ON c.id=p.career_id WHERE p.user_id=? AND p.status='ACTIVE' ORDER BY p.id DESC LIMIT 1", uid);
    if (p) p.career_name = db.tr("career", p.career_id, "name", p.career_name);
    return p;
  };
  E.createPlan = async function (db, uid, cid) {
    var prev = await E.planPreview(db, uid, cid); if (!prev) return null;
    var cur = await E.activePlan(db, uid);
    if (cur && cur.career_id === cid) return cur.id;
    await db.run("UPDATE plans SET status='ARCHIVED' WHERE user_id=? AND status='ACTIVE'", uid);
    var old = await db.one("SELECT id FROM plans WHERE user_id=? AND career_id=? AND status='ARCHIVED' ORDER BY id DESC LIMIT 1", uid, cid);
    if (old && await db.one("SELECT 1 x FROM tasks WHERE plan_id=?", old.id)) { await db.run("UPDATE plans SET status='ACTIVE' WHERE id=?", old.id); await E.logReadiness(db, uid); return old.id; }
    var recs = (await E.recommend(db, uid)) || [], hit = recs.find(function (r) { return r.career_id === cid; });
    var pid = await db.run("INSERT INTO plans(user_id,career_id,reasons) VALUES(?,?,?)", uid, cid, E.dumps(hit ? hit.reason_codes : []));
    var pos = 0;
    for (var i = 0; i < prev.milestones.length; i++) {
      var m = prev.milestones[i];
      await db.run("INSERT OR IGNORE INTO milestones(plan_id,number,skill_id) VALUES(?,?,?)", pid, m.milestone, m.skill_id);
      var sname = (await db.one("SELECT name FROM skills WHERE id=?", m.skill_id)).name, ts = E.makeTasks(sname, "en");
      for (var j = 0; j < ts.length; j++) {
        pos += 1; var t = ts[j];
        await db.run("INSERT INTO tasks(plan_id,skill_id,milestone,position,kind,title,description,difficulty,est_hours) VALUES(?,?,?,?,?,?,?,?,?)", pid, m.skill_id, m.milestone, pos, t.kind, t.title, t.description, t.difficulty, t.est_hours);
      }
    }
    await E.logReadiness(db, uid);
    return pid;
  };

  /* ---------- kesiapan ---------- */
  E.readiness = async function (db, uid) {
    var plan = await E.activePlan(db, uid); if (!plan) return 0;
    var t = await db.one("SELECT COUNT(*) n, SUM(status='COMPLETED') d FROM tasks WHERE plan_id=?", plan.id);
    var taskPart = t.n ? (t.d || 0) / t.n : 0;
    var skills = await E.skillMap(db, uid), req = await E.careerSkills(db, plan.career_id), tot = U.sum(req.map(function (r) { return r.importance; })) || 1;
    var skillPart = U.sum(req.map(function (r) { return r.importance * (LEVEL_WEIGHT[skills[r.id] || 0] || 0); })) / tot;
    if (CW.hasCourse(plan.career_id)) return U.pyRound((0.35 * taskPart + 0.35 * skillPart + 0.30 * (await CW.doneCount(db, uid, plan.career_id)) / 6) * 100);
    return U.pyRound((0.5 * taskPart + 0.5 * skillPart) * 100);
  };
  E.logReadiness = async function (db, uid) {
    var v = await E.readiness(db, uid), last = await db.one("SELECT value FROM readiness_log WHERE user_id=? ORDER BY id DESC LIMIT 1", uid);
    if (!last || last.value !== v) await db.run("INSERT INTO readiness_log(user_id,value) VALUES(?,?)", uid, v);
    return v;
  };

  /* ---------- status siswa (untuk guru) ---------- */
  function parseTs(s) { var m = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$/.exec(s || ""); return m ? Date.UTC(+m[1], m[2] - 1, +m[3], +m[4], +m[5], +m[6]) : null; }
  E.parseTs = parseTs;
  E.studentStatus = async function (db, u, nowMs) {
    var last = parseTs(u.last_active_at); if (last === null) last = nowMs;
    var inactive = Math.floor((nowMs - last) / 86400000) >= 14;
    var plan = await E.activePlan(db, u.id);
    var pending = (await db.one("SELECT COUNT(*) n FROM projects WHERE user_id=? AND status='SUBMITTED'", u.id)).n > 0;
    var r = plan ? await E.readiness(db, u.id) : 0;
    var flags = { inactive: inactive, no_plan: plan === null, needs_feedback: pending, on_track: !!plan && r >= 50 && !inactive };
    var label = inactive ? "Inactive" : plan === null ? "No plan yet" : pending ? "Needs feedback" : flags.on_track ? "On track" : "Active";
    return { flags: flags, status: label, readiness: r };
  };

  /* ---------- kursus karier (coursework.py) ---------- */
  CW.course = function (cid) { return E.DATA.courses[String(cid)]; };
  CW.hasCourse = function (cid) { var c = CW.course(cid); return !!(c && (c.sources || []).length >= 2); };
  async function passed(db, uid, cid, ch) { return (await db.one("SELECT 1 x FROM course_attempts WHERE user_id=? AND career_id=? AND chapter=? AND passed=1", uid, cid, ch)) !== null; }
  CW.linkedProject = function (db, uid, cid) { return db.one("SELECT p.id,p.title,p.status FROM course_projects cp JOIN projects p ON p.id=cp.project_id WHERE cp.user_id=? AND cp.career_id=?", uid, cid); };
  CW.doneMap = async function (db, uid, cid) {
    var r1 = await db.one("SELECT done_at FROM course_progress WHERE user_id=? AND career_id=? AND chapter=1", uid, cid), out = { 1: !!(r1 && r1.done_at) };
    for (var n = 2; n <= 5; n++) out[n] = await passed(db, uid, cid, n);
    var pj = await CW.linkedProject(db, uid, cid);
    out[6] = (await passed(db, uid, cid, 6)) && !!(pj && pj.status === "VERIFIED");
    return out;
  };
  CW.doneCount = async function (db, uid, cid) { if (!CW.hasCourse(cid)) return 0; var d = await CW.doneMap(db, uid, cid), n = 0; for (var k = 1; k <= 6; k++) if (d[k]) n++; return n; };
  CW.unlocked = function (done, n) { for (var k = 1; k < n; k++) if (!done[k]) return false; return true; };
  CW.sync = async function (db, uid, cid) {
    if (!CW.hasCourse(cid)) return false;
    var d = await CW.doneMap(db, uid, cid); for (var k = 1; k <= 6; k++) if (!d[k]) return false;
    var row = await db.one("SELECT done_at FROM course_progress WHERE user_id=? AND career_id=? AND chapter=6", uid, cid);
    if (row && row.done_at) return true;
    await db.run("INSERT INTO course_progress(user_id,career_id,chapter,done_at) VALUES(?,?,6,datetime('now')) ON CONFLICT(user_id,career_id,chapter) DO UPDATE SET done_at=datetime('now')", uid, cid);
    var cs = await E.careerSkills(db, cid); for (var i = 0; i < cs.length; i++) await E.raiseSkill(db, uid, cs[i].id, E.LEARNING);
    await S.notify(db, uid, S.msg(await S.userLang(db, uid), "note.course_done", { career: CW.course(cid).name }));
    await E.logReadiness(db, uid);
    return true;
  };
  CW.completedCourses = async function (db, uid) {
    var out = [], rows = await db.all("SELECT career_id, done_at FROM course_progress WHERE user_id=? AND chapter=6 AND done_at IS NOT NULL ORDER BY done_at DESC", uid);
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i], co = CW.course(r.career_id); if (!co) continue;
      var best = await db.one("SELECT MAX(100.0*score/total) p FROM course_attempts WHERE user_id=? AND career_id=? AND chapter=6 AND passed=1", uid, r.career_id);
      out.push({ career: db.tr("career", r.career_id, "name", co.name), completed_on: (r.done_at || "").slice(0, 10), exam_percent: best && best.p !== null ? U.pyRound(best.p) : null });
    }
    return out;
  };

  /* ---------- tautan & kontak (links.py) ---------- */
  var HOST = /^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$/i, IG = /^[A-Za-z0-9._]{1,30}$/;
  L.cleanWebsite = function (s) {
    s = U.strip(s); if (!s) return "";
    if (s.length > 200 || /\s/.test(s)) throw S.bad("Website link is not valid");
    if (s.indexOf("://") < 0) s = "https://" + s;
    var u = U.urlparse(s), host = u.hostname || "";
    if ((u.scheme !== "http" && u.scheme !== "https") || !HOST.test(host) || host.indexOf(".") < 0 || u.username || u.password) throw S.bad("Website link is not valid");
    return s;
  };
  L.cleanInstagram = function (s) {
    s = U.strip(s); if (!s) return "";
    if (s.toLowerCase().indexOf("instagram.com") >= 0) {
      var u = U.urlparse(s.indexOf("://") >= 0 ? s : "https://" + s);
      if ((u.hostname || "").toLowerCase().replace("www.", "") !== "instagram.com") throw S.bad("Instagram account is not valid");
      var parts = u.path.split("/").filter(Boolean); s = parts.length ? parts[0] : "";
    }
    s = s.replace(/^@+/, "");
    if (!IG.test(s) || s[0] === "." || s[s.length - 1] === ".") throw S.bad("Instagram account is not valid");
    return s.toLowerCase();
  };
  L.cleanPhone = function (s) {
    s = U.strip(s); if (!s) return "";
    if (!/^[0-9+()\-\s]{6,25}$/.test(s) || s.replace(/\D/g, "").length < 6) throw S.bad("Phone number is not valid");
    return s;
  };
  L.searchLinks = function (name, address) {
    var q = (name + " " + (address ? "" : "Pekanbaru")).trim();
    return { google_url: "https://www.google.com/search?q=" + U.quotePlus(q), ig_search_url: "https://www.google.com/search?q=" + U.quotePlus("site:instagram.com " + q),
      fb_search_url: "https://www.google.com/search?q=" + U.quotePlus("site:facebook.com " + q) };
  };

  root.ME = E; root.MCW = CW; root.ML = L;
  if (typeof module !== "undefined") module.exports = { E: E, CW: CW, L: L };
})(typeof window !== "undefined" ? window : globalThis);
