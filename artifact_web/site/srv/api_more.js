/* Metta Career — API: kursus, guru, ajuan tempat magang, admin, alumni, portfolio, file
   (padanan api/course.py, teacher.py, company_proposal.py, admin.py, alumni.py, portfolio.py, files.py). */
(function (root) {
  "use strict";
  var U = root.MU, S = root.MS, E = root.ME, CW = root.MCW, L = root.ML, X = root.MX, F = S.F, api = S.api, HTTPError = S.HTTPError;
  var ST = ["student"], T = ["teacher"], A = ["admin"], R = ["teacher", "admin"];
  function meta() { return E.DATA.meta; }

  /* ---------- file bukti (files.py): isi file disimpan di catatan operasi, dibaca ulang saat start ---------- */
  var FILES = root.MFILES = root.MFILES || {};          // stored_name -> base64
  var MAX_BYTES = 3 * 1024 * 1024, MAX_PER_ITEM = 3, MAX_PER_USER = 40, KINDS = { certificate: "certificates", achievement: "achievements", project: "projects" };
  X.filesMap = async function (db, kind, ids) {
    var out = {}; ids.forEach(function (i) { out[i] = []; }); if (!ids.length) return out;
    var rows = await db.all.apply(db, ["SELECT id,ref_id,original_name name,size,mime FROM uploads WHERE ref_kind=? AND ref_id IN (" + ids.map(function () { return "?"; }).join(",") + ") ORDER BY id", kind].concat(ids));
    rows.forEach(function (r) { var k = r.ref_id; delete r.ref_id; (out[k] = out[k] || []).push(r); }); return out;
  };
  async function purge(db, kind, refId) {
    (await db.all("SELECT id,stored_name FROM uploads WHERE ref_kind=? AND ref_id=?", kind, refId)).forEach(function (r) { delete FILES[r.stored_name]; });
    await db.run("DELETE FROM uploads WHERE ref_kind=? AND ref_id=?", kind, refId);
  }
  function sniff(d) {
    function st(sig) { for (var i = 0; i < sig.length; i++) if (d[i] !== sig[i]) return false; return true; }
    if (st([0x25, 0x50, 0x44, 0x46, 0x2d])) return ["application/pdf", ".pdf"];
    if (st([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])) return ["image/png", ".png"];
    if (st([0xff, 0xd8, 0xff])) return ["image/jpeg", ".jpg"];
    return [null, null];
  }
  function cleanName(name, ext) {
    var base = String(name || "file").replace(/\\/g, "/"); base = base.slice(base.lastIndexOf("/") + 1);
    base = base.replace(/[^\w .()\-]/gu, "_").replace(/^[ .]+|[ .]+$/g, "").slice(0, 80) || "file";
    return base.replace(/\.(pdf|png|jpe?g)$/i, "") + ext;
  }
  async function ownedRef(db, kind, refId, uid) { var t = KINDS[kind]; if (!t || !(await db.one("SELECT 1 x FROM " + t + " WHERE id=? AND user_id=?", refId, uid))) throw S.notFound("Item not found"); }
  api("/api/student/uploads", "POST", { roles: ST, model: { kind: F.str({ pattern: "^(certificate|achievement|project)$" }), ref_id: F.int({ ge: 1 }), filename: F.str({ min: 1, max: 200 }), data: F.str({ min: 8, max: 4400000 }) } },
  async function (c, b) {
    var uid = c.user.id; await ownedRef(c.db, b.kind, b.ref_id, uid);
    var data; try { data = U.b64decode(b.data); } catch (e) { throw S.bad("The file could not be read"); }
    if (data.length > MAX_BYTES) throw new HTTPError(413, "File is too large (max 3 MB)");
    if (c.live && root.MSTORE && root.MSTORE.maxFileBytes && data.length > root.MSTORE.maxFileBytes()) throw new HTTPError(413, "File is too large for the shared database (max 180 KB). Make the photo or PDF smaller, then try again.");
    var sn = sniff(data); if (!sn[0]) throw S.bad("Only PDF, PNG or JPG files are allowed");
    if ((await c.db.one("SELECT COUNT(*) n FROM uploads WHERE ref_kind=? AND ref_id=?", b.kind, b.ref_id)).n >= MAX_PER_ITEM) throw S.bad("Maximum 3 files per item");
    if ((await c.db.one("SELECT COUNT(*) n FROM uploads WHERE user_id=?", uid)).n >= MAX_PER_USER) throw S.bad("You have reached the file limit");
    var stored = c.det(function () { return U.tokenHex(16); });
    FILES[stored] = b.data;
    var fid = await c.db.run("INSERT INTO uploads(user_id,ref_kind,ref_id,stored_name,original_name,mime,size) VALUES(?,?,?,?,?,?,?)", uid, b.kind, b.ref_id, stored, cleanName(b.filename, sn[1]), sn[0], data.length);
    await S.audit(c, "file_upload", b.kind + ":" + b.ref_id);
    return { id: fid, name: cleanName(b.filename, sn[1]), size: data.length, mime: sn[0] };
  });
  api("/api/student/uploads/{fid:int}", "DELETE", { roles: ST }, async function (c, fid) {
    var r = await c.db.one("SELECT stored_name FROM uploads WHERE id=? AND user_id=?", fid, c.user.id); if (!r) throw S.notFound("File not found");
    delete FILES[r.stored_name]; await c.db.run("DELETE FROM uploads WHERE id=?", fid);
  });
  api("/api/files/{fid:int}", "GET", { roles: ["student", "teacher", "admin"] }, async function (c, fid) {
    var r = await c.db.one("SELECT * FROM uploads WHERE id=?", fid);
    if (!r || (c.user.role === "student" && r.user_id !== c.user.id)) throw S.notFound("File not found");
    var data = FILES[r.stored_name]; if (!data) throw S.notFound("File not found");
    if (c.user.role !== "student") await S.audit(c, "file_view", String(fid));
    return { __file: { mime: r.mime, name: r.original_name, b64: data } };
  });

  /* ---------- kursus karier (course.py) ---------- */
  var LEVEL = { A: "SMA", K: "SMK" };
  async function planCourse(c) {
    var plan = await E.activePlan(c.db, c.user.id);
    if (!plan || !CW.hasCourse(plan.career_id)) throw S.notFound("No course for this career yet");
    return [plan, plan.career_id, CW.course(plan.career_id)];
  }
  function perm(seed, pos, n) { var idx = [0, 1, 2, 3].slice(0, n); return U.rng(seed + ":" + pos).shuffle(idx); }
  async function chapterRow(c, cid, n, create) {
    var r = await c.db.one("SELECT * FROM course_progress WHERE user_id=? AND career_id=? AND chapter=?", c.user.id, cid, n);
    if (!r && create !== false) { await c.db.run("INSERT INTO course_progress(user_id,career_id,chapter) VALUES(?,?,?)", c.user.id, cid, n); r = await c.db.one("SELECT * FROM course_progress WHERE user_id=? AND career_id=? AND chapter=?", c.user.id, cid, n); }
    return r;
  }
  function cAttempts(c, cid, n) { return c.db.all("SELECT id,score,total,passed,created_at,finished_at FROM course_attempts WHERE user_id=? AND career_id=? AND chapter=? AND finished_at IS NOT NULL ORDER BY id DESC", c.user.id, cid, n); }
  function need(n) { return n === 6 ? meta().PASS_FINAL : meta().PASS_CHAPTER; }
  async function waitLeft(c, cid, n) {
    var r = await c.db.one("SELECT ? - (CAST(strftime('%s','now') AS INTEGER) - CAST(strftime('%s',finished_at) AS INTEGER)) w FROM course_attempts WHERE user_id=? AND career_id=? AND chapter=? AND finished_at IS NOT NULL AND passed=0 ORDER BY id DESC LIMIT 1", meta().COOLDOWN_SEC, c.user.id, cid, n);
    return r ? Math.max(0, r.w) : 0;
  }
  function maxScore(att) { return att.length ? Math.max.apply(null, att.map(function (a) { return a.score; })) : null; }
  api("/api/student/course", "GET", { roles: ST }, async function (c) {
    var uid = c.user.id, plan = await E.activePlan(c.db, uid);
    if (!plan) return { available: false, reason: "no_plan" };
    var cid = plan.career_id;
    if (!CW.hasCourse(cid)) return { available: false, reason: "no_course", career: plan.career_name };
    await CW.sync(c.db, uid, cid);
    var done = await CW.doneMap(c.db, uid, cid), ch = [], n, cnt = 0;
    for (n = 1; n <= 6; n++) { ch.push({ n: n, title: meta().CH_TITLES[n], done: done[n], locked: !CW.unlocked(done, n) }); if (done[n]) cnt++; }
    return { available: true, career: plan.career_name, chapters: ch, done: cnt, total: 6, pass_chapter: meta().PASS_CHAPTER, quiz_n: meta().QUIZ_N, pass_final: meta().PASS_FINAL, final_n: meta().FINAL_N };
  });
  api("/api/student/course/chapter/{n:int}", "GET", { roles: ST }, async function (c, n) {
    var pc = await planCourse(c), plan = pc[0], cid = pc[1], co = pc[2], uid = c.user.id;
    if (!(n >= 1 && n <= 6)) throw S.notFound("Chapter not found");
    var done = await CW.doneMap(c.db, uid, cid);
    if (!CW.unlocked(done, n)) throw S.bad("This chapter is locked. Finish the previous chapter first.");
    var row = await chapterRow(c, cid, n);
    var out = { n: n, title: meta().CH_TITLES[n], career: plan.career_name, done: done[n], sources: (co.sources || []).map(function (s) { return { t: s[0], u: s[1] }; }) };
    if (n <= 5) { var ch = co.chapters[n]; out.goals = ch.goals; out.sections = ch.sections.map(function (s) { return { h: s[0], t: s[1] }; }); }
    if (n === 1) { var left = (await c.db.one("SELECT ? - (CAST(strftime('%s','now') AS INTEGER) - CAST(strftime('%s',?) AS INTEGER)) w", meta().READ_MIN_SEC, row.opened_at)).w; out.read_wait = Math.max(0, left); }
    if (n >= 2 && n <= 5) {
      var att = await cAttempts(c, cid, n);
      Object.assign(out, { practice: co.chapters[n].practice, quiz_n: meta().QUIZ_N, pass: meta().PASS_CHAPTER, attempts: att.length, best: maxScore(att), passed: att.some(function (a) { return a.passed; }), wait: await waitLeft(c, cid, n) });
    }
    if (n === 6) {
      var pr = co.project, att6 = await cAttempts(c, cid, 6), pj = await CW.linkedProject(c.db, uid, cid);
      var mine = await c.db.all("SELECT id,title,status FROM projects WHERE user_id=? ORDER BY id DESC", uid);
      Object.assign(out, { project: { title: pr.title, brief: pr.brief, criteria: pr.criteria }, linked: pj, my_projects: mine, exam_n: meta().FINAL_N, pass: meta().PASS_FINAL,
        attempts: att6.length, best: maxScore(att6), passed: att6.some(function (a) { return a.passed; }), wait: await waitLeft(c, cid, 6) });
    }
    return out;
  });
  api("/api/student/course/chapter/{n:int}/read", "POST", { roles: ST }, async function (c, n) {
    var pc = await planCourse(c), cid = pc[1], uid = c.user.id;
    if (n !== 1) throw S.bad("Only chapter 1 is marked as read");
    var row = await chapterRow(c, cid, 1);
    var wait = (await c.db.one("SELECT ? - (CAST(strftime('%s','now') AS INTEGER) - CAST(strftime('%s',?) AS INTEGER)) w", meta().READ_MIN_SEC, row.opened_at)).w;
    if (wait > 0) throw S.bad("Read the material first. You can mark it as read after about a minute.");
    await c.db.run("UPDATE course_progress SET done_at=COALESCE(done_at,datetime('now')) WHERE user_id=? AND career_id=? AND chapter=1", uid, cid);
    return { ok: true };
  });
  function pick(co, n, seed) {
    var rnd = U.rng(seed), bank = co.bank, ids = [];
    function of(k) { var o = []; bank.forEach(function (q, i) { if (q[0] === k) o.push(i); }); return o; }
    if (n === 6) { [2, 3, 4, 5].forEach(function (k) { ids = ids.concat(rnd.sample(of(k), 3)); }); rnd.shuffle(ids); return ids; }
    return rnd.sample(of(n), meta().QUIZ_N);
  }
  function view(co, att) {
    var qids = JSON.parse(att.qids);
    return { attempt: att.id, chapter: att.chapter, total: att.total, pass: need(att.chapter),
      questions: qids.map(function (qi, pos) { var q = co.bank[qi], o = perm(att.seed, pos, 4); return { q: q[2], level: LEVEL[q[1]], options: o.map(function (j) { return q[3][j]; }) }; }) };
  }
  api("/api/student/course/chapter/{n:int}/quiz", "POST", { roles: ST }, async function (c, n) {
    var pc = await planCourse(c), cid = pc[1], co = pc[2], uid = c.user.id;
    if (!(n >= 2 && n <= 6)) throw S.bad("This chapter has no quiz");
    var done = await CW.doneMap(c.db, uid, cid);
    if (!CW.unlocked(done, n)) throw S.bad("This chapter is locked. Finish the previous chapter first.");
    if (n <= 5) await chapterRow(c, cid, n);
    if ((await waitLeft(c, cid, n)) > 0) throw S.bad("Please wait a minute before trying again");
    var old = await c.db.one("SELECT * FROM course_attempts WHERE user_id=? AND career_id=? AND chapter=? AND finished_at IS NULL AND CAST(strftime('%s','now') AS INTEGER) - CAST(strftime('%s',created_at) AS INTEGER) < 3600 ORDER BY id DESC LIMIT 1", uid, cid, n);
    if (old) return view(co, old);
    await c.db.run("UPDATE course_attempts SET finished_at=datetime('now') WHERE user_id=? AND career_id=? AND chapter=? AND finished_at IS NULL", uid, cid, n);
    var seed = c.det(function () { return U.tokenHex(8); }), ids = pick(co, n, seed);
    var aid = await c.db.run("INSERT INTO course_attempts(user_id,career_id,chapter,qids,seed,total) VALUES(?,?,?,?,?,?)", uid, cid, n, E.dumps(ids), seed, ids.length);
    return view(co, await c.db.one("SELECT * FROM course_attempts WHERE id=?", aid));
  });
  api("/api/student/course/attempt/{aid:int}/submit", "POST", { roles: ST, model: { answers: F.list(F.int(), { min: 1, max: 20 }) } }, async function (c, b, aid) {
    var pc = await planCourse(c), cid = pc[1], co = pc[2], uid = c.user.id;
    var att = await c.db.one("SELECT * FROM course_attempts WHERE id=? AND user_id=? AND career_id=?", aid, uid, cid);
    if (!att) throw S.notFound("Attempt not found");
    if (att.finished_at) throw S.bad("This attempt is already finished");
    var qids = JSON.parse(att.qids);
    if (b.answers.length !== qids.length || b.answers.some(function (a) { return !(a >= 0 && a < 4); })) throw S.bad("Answer every question");
    var score = 0, res = [], weak = new Set();
    qids.forEach(function (qi, pos) { var q = co.bank[qi], o = perm(att.seed, pos, 4), ok = o[b.answers[pos]] === q[4]; if (ok) score++; else weak.add(q[0]); res.push({ correct: ok, why: q[5], answer: q[3][q[4]] }); });
    var n = att.chapter, passed = score >= need(n);
    await c.db.run("UPDATE course_attempts SET score=?, passed=?, finished_at=datetime('now') WHERE id=?", score, passed ? 1 : 0, aid);
    var out = { score: score, total: qids.length, passed: passed, need: need(n), chapter: n, wait: passed ? 0 : meta().COOLDOWN_SEC };
    if (!passed) { out.results = []; if (n === 6) out.weak_chapters = Array.from(weak).sort(function (a, b2) { return a - b2; }); }
    else out.results = res;
    if (passed) { await CW.sync(c.db, uid, cid); await E.logReadiness(c.db, uid); }
    return out;
  });
  api("/api/student/course/project", "POST", { roles: ST, model: { project_id: F.int({ ge: 1 }) } }, async function (c, b) {
    var pc = await planCourse(c), cid = pc[1], uid = c.user.id;
    if (!CW.unlocked(await CW.doneMap(c.db, uid, cid), 6)) throw S.bad("This chapter is locked. Finish the previous chapter first.");
    var p = await c.db.one("SELECT * FROM projects WHERE id=? AND user_id=?", b.project_id, uid); if (!p) throw S.notFound("Project not found");
    var cur = await CW.linkedProject(c.db, uid, cid);
    if (cur && cur.status === "VERIFIED" && cur.id !== p.id) throw S.bad("This course already has a verified project");
    var hasProof = ["link", "demo_url", "repo_url", "doc_url"].some(function (k) { return U.strip(p[k]); }) || (await X.filesMap(c.db, "project", [p.id]))[p.id].length > 0;
    if (U.strip(p.problem).length < 40 || U.strip(p.solution).length < 40 || U.strip(p.result).length < 20 || !hasProof)
      throw S.bad("Complete the project first: problem (40+ characters), solution (40+), result (20+), and add a demo, repository, document, link or file");
    await c.db.run("INSERT INTO course_projects(user_id,career_id,project_id) VALUES(?,?,?) ON CONFLICT(user_id,career_id) DO UPDATE SET project_id=excluded.project_id", uid, cid, p.id);
    return { ok: true };
  });

  /* ---------- guru (teacher.py) ---------- */
  async function studentsList(c) {
    var rows = await c.db.all("SELECT u.id,u.name,u.email,u.last_active_at,sp.major,sp.class_name FROM users u LEFT JOIN student_profiles sp ON sp.user_id=u.id WHERE u.role='student' AND u.active=1 ORDER BY u.name");
    for (var i = 0; i < rows.length; i++) { var r = rows[i]; Object.assign(r, await E.studentStatus(c.db, r, c.nowMs)); var plan = await E.activePlan(c.db, r.id); r.target = plan ? plan.career_name : null; }
    return rows;
  }
  api("/api/teacher/summary", "GET", { roles: T }, async function (c) {
    var rows = await studentsList(c), n = function (f) { return rows.filter(f).length; };
    return { total: rows.length, on_track: n(function (r) { return r.flags.on_track; }), active: n(function (r) { return !r.flags.inactive; }), inactive: n(function (r) { return r.flags.inactive; }),
      needs_feedback: n(function (r) { return r.flags.needs_feedback; }), no_plan: n(function (r) { return r.flags.no_plan; }),
      attention: rows.filter(function (r) { return ["Inactive", "Needs feedback", "No plan yet"].indexOf(r.status) >= 0; }).slice(0, 8).map(function (r) { return { id: r.id, name: r.name, status: r.status, last_active_at: r.last_active_at }; }) };
  });
  api("/api/teacher/students", "GET", { roles: T }, async function (c) {
    var q = (c.query.get("q") || "").toLowerCase(), st = c.query.get("status") || "", mj = c.query.get("major") || "";
    return { items: (await studentsList(c)).filter(function (r) { return (!q || r.name.toLowerCase().indexOf(q) >= 0) && (!st || r.status === st) && (!mj || r.major === mj); }) };
  });
  async function courseProgress(c, sid, plan) { if (!plan || !CW.hasCourse(plan.career_id)) return null; return { career: plan.career_name, done: await CW.doneCount(c.db, sid, plan.career_id), total: 6 }; }
  async function withCourse(c, rows) {
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i], link = await c.db.one("SELECT career_id FROM course_projects WHERE project_id=?", r.id), co = link ? CW.course(link.career_id) : null;
      if (co) r.course = { career: c.db.tr("career", link.career_id, "name", co.name), title: co.project.title, criteria: co.project.criteria };
    }
    return rows;
  }
  api("/api/teacher/students/{sid:int}", "GET", { roles: T }, async function (c, sid) {
    var u = await c.db.one("SELECT id,name,email,last_active_at FROM users WHERE id=? AND role='student'", sid); if (!u) throw S.notFound("Student not found");
    var prof = (await c.db.one("SELECT school,major,class_name,goal FROM student_profiles WHERE user_id=?", sid)) || {}, plan = await E.activePlan(c.db, sid), tasks = [];
    if (plan) { var tr = await c.db.all("SELECT title,status,kind,skill_id,difficulty FROM tasks WHERE plan_id=? ORDER BY position", plan.id); for (var i = 0; i < tr.length; i++) tasks.push(await E.taskView(c.db, tr[i])); }
    var skills = (await c.db.all("SELECT s.id, s.name, ss.level FROM student_skills ss JOIN skills s ON s.id=ss.skill_id WHERE ss.user_id=? ORDER BY ss.level DESC", sid))
      .map(function (s) { return { name: c.db.tr("skill", s.id, "name", s.name), level: s.level, evidence: E.lvl(c.db, s.level) }; });
    var choices = await c.db.all("SELECT ic.rank, co.name FROM internship_choices ic JOIN companies co ON co.id=ic.company_id WHERE ic.user_id=? ORDER BY ic.rank", sid);
    var fb = await c.db.all("SELECT f.text,f.created_at,t.name teacher FROM feedback f JOIN users t ON t.id=f.teacher_id WHERE f.student_id=? ORDER BY f.id DESC LIMIT 10", sid);
    var ins = await E.insight(c.db, sid);
    return { student: Object.assign({}, u, prof), status: await E.studentStatus(c.db, u, c.nowMs), plan: plan ? { id: plan.id, career: plan.career_name, teacher_note: plan.teacher_note } : null,
      tasks: tasks, skills: skills, projects: await withCourse(c, await X.rowsProject(c, await c.db.all("SELECT * FROM projects WHERE user_id=? ORDER BY id DESC", sid))),
      course: await courseProgress(c, sid, plan), internship: choices, feedback: fb,
      insight: ins ? { interests: ins.interests, strengths: ins.strengths, interest_labels: ins.interest_labels, strength_labels: ins.strength_labels } : null };
  });
  api("/api/teacher/students/{sid:int}/feedback", "POST", { roles: T, model: { text: F.str({ min: 3, max: 1000 }) } }, async function (c, b, sid) {
    if (!(await c.db.one("SELECT 1 x FROM users WHERE id=? AND role='student'", sid))) throw S.notFound("Student not found");
    await c.db.run("INSERT INTO feedback(student_id,teacher_id,text) VALUES(?,?,?)", sid, c.user.id, b.text.trim());
    await S.notify(c.db, sid, S.msg(await S.userLang(c.db, sid), "note.feedback", { teacher: c.user.name, text: Array.from(b.text.trim()).slice(0, 120).join("") }));
  });
  api("/api/teacher/plans", "GET", { roles: T }, async function (c) {
    var rows = await c.db.all("SELECT p.id, u.name student, u.id student_id, ca.id career_id, ca.name career, p.teacher_note, p.created_at FROM plans p JOIN users u ON u.id=p.user_id JOIN careers ca ON ca.id=p.career_id WHERE p.status='ACTIVE' ORDER BY p.id DESC");
    rows.forEach(function (r) { r.career = c.db.tr("career", r.career_id, "name", r.career); }); return { items: rows };
  });
  api("/api/teacher/plans/{pid:int}/guidance", "PUT", { roles: T, model: { note: F.str({ min: 1, max: 1000 }) } }, async function (c, b, pid) {
    var p = await c.db.one("SELECT * FROM plans WHERE id=? AND status='ACTIVE'", pid); if (!p) throw S.notFound("Plan not found");
    await c.db.run("UPDATE plans SET teacher_note=? WHERE id=?", b.note.trim(), pid);
    await S.notify(c.db, p.user_id, S.msg(await S.userLang(c.db, p.user_id), "note.guidance", { teacher: c.user.name }));
  });
  api("/api/teacher/projects", "GET", { roles: T }, async function (c) { return { items: await withCourse(c, await X.rowsProject(c, await c.db.all("SELECT p.*, u.name student FROM projects p JOIN users u ON u.id=p.user_id ORDER BY p.id DESC"))) }; });
  api("/api/teacher/validation", "GET", { roles: T }, async function (c) { return { items: await withCourse(c, await X.rowsProject(c, await c.db.all("SELECT p.*, u.name student FROM projects p JOIN users u ON u.id=p.user_id WHERE p.status='SUBMITTED' ORDER BY p.id"))) }; });
  api("/api/teacher/projects/{pid:int}/review", "POST", { roles: T, model: { decision: F.str({ pattern: "^(VERIFIED|NEEDS_REVISION)$" }), note: F.str({ def: "", max: 1000 }) } }, async function (c, b, pid) {
    var p = await c.db.one("SELECT * FROM projects WHERE id=?", pid); if (!p) throw S.notFound("Project not found");
    if (p.status !== "SUBMITTED") throw S.bad("This project is not waiting for review");
    if (b.decision === "NEEDS_REVISION" && !b.note.trim()) throw S.bad("Revision notes are required");
    await c.db.run("UPDATE projects SET status=?, teacher_note=?, reviewed_by=?, updated_at=datetime('now') WHERE id=?", b.decision, b.note.trim(), c.user.id, pid);
    await c.db.run("INSERT INTO project_feedback(project_id,teacher_id,decision,note) VALUES(?,?,?,?)", pid, c.user.id, b.decision, b.note.trim());
    var lang = await S.userLang(c.db, p.user_id);
    if (b.decision === "VERIFIED") {
      var sids = JSON.parse(p.skill_ids); for (var i = 0; i < sids.length; i++) await E.raiseSkill(c.db, p.user_id, sids[i], E.TEACHER_VERIFIED);
      var lks = await c.db.all("SELECT career_id FROM course_projects WHERE project_id=?", pid); for (var j = 0; j < lks.length; j++) await CW.sync(c.db, p.user_id, lks[j].career_id);
      await S.notify(c.db, p.user_id, S.msg(lang, "note.verified", { title: p.title }));
    } else await S.notify(c.db, p.user_id, S.msg(lang, "note.revision", { title: p.title, note: Array.from(b.note.trim()).slice(0, 120).join("") }));
    await E.logReadiness(c.db, p.user_id); await S.audit(c, "project_review", pid + ":" + b.decision);
  });
  api("/api/teacher/internship", "GET", { roles: T }, async function (c) {
    var q = (c.query.get("q") || "").toLowerCase(), out = [];
    var rows = await c.db.all("SELECT u.id,u.name,sp.class_name,sp.major FROM users u LEFT JOIN student_profiles sp ON sp.user_id=u.id WHERE u.role='student' AND u.active=1 ORDER BY u.name");
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i], ch = {};
      (await c.db.all("SELECT ic.rank, co.name, ic.purpose FROM internship_choices ic JOIN companies co ON co.id=ic.company_id WHERE ic.user_id=?", r.id)).forEach(function (x) { ch[x.rank] = x; });
      r.choices = [1, 2, 3].map(function (k) { return ch[k] ? ch[k].name : ""; }); r.purposes = [1, 2, 3].map(function (k) { return ch[k] ? ch[k].purpose : ""; });
      r.friends = (await c.db.all("SELECT name,class_name FROM internship_friends WHERE user_id=? ORDER BY id", r.id)).map(function (f) { return f.name + (f.class_name ? " (" + f.class_name + ")" : ""); });
      if (!q || r.name.toLowerCase().indexOf(q) >= 0 || r.choices.some(function (x) { return x.toLowerCase().indexOf(q) >= 0; })) out.push(r);
    }
    return { items: out };
  });
  api("/api/teacher/analytics", "GET", { roles: T }, async function (c) {
    var rows = await studentsList(c), byClass = {}, byMajor = {};
    rows.forEach(function (r) { (byClass[r.class_name || "-"] = byClass[r.class_name || "-"] || []).push(r.readiness); (byMajor[r.major || "-"] = byMajor[r.major || "-"] || []).push(r.readiness); });
    function avg(d) { return Object.keys(d).sort().map(function (k) { return { label: k, avg_readiness: U.pyRound(U.sum(d[k]) / d[k].length), students: d[k].length }; }); }
    var status = ["On track", "Active", "Needs feedback", "No plan yet", "Inactive"].map(function (k) { return { key: k, value: rows.filter(function (r) { return r.status === k; }).length }; });
    var ids = rows.map(function (r) { return r.id; }), got = {};
    (await c.db.all.apply(c.db, ["SELECT status, COUNT(*) n FROM projects WHERE user_id IN (" + (ids.map(function () { return "?"; }).join(",") || "NULL") + ") GROUP BY status"].concat(ids))).forEach(function (x) { got[x.status] = x.n; });
    var tc = {}; rows.forEach(function (r) { if (r.target) tc[r.target] = (tc[r.target] || 0) + 1; });
    var careers = U.sortBy(Object.keys(tc), function (k) { return [-tc[k], k]; }).slice(0, 8).map(function (k) { return { label: k, value: tc[k] }; });
    return { by_class: avg(byClass), by_major: avg(byMajor), status: status, projects: ["SUBMITTED", "NEEDS_REVISION", "VERIFIED"].map(function (k) { return { key: k, value: got[k] || 0 }; }), careers: careers, total: rows.length };
  });

  /* ---------- ajuan tempat magang (company_proposal.py) ---------- */
  var MAX_PENDING = 3;
  api("/api/student/companies", "POST", { roles: ST, model: { name: F.str({ min: 3, max: 120 }), address: F.str({ min: 10, max: 300 }), sector: F.str({ min: 3, max: 80 }), about: F.str({ min: 40, max: 800 }),
      tasks: F.str({ min: 10, max: 500 }), majors: F.str({ def: "", max: 200 }), work_terms: F.str({ def: "", max: 300 }), phone: F.str({ def: "", max: 30 }), website: F.str({ def: "", max: 200 }),
      instagram: F.str({ def: "", max: 200 }), source: F.str({ min: 5, max: 200 }) } }, async function (c, b) {
    var name = U.collapse(b.name), phone = L.cleanPhone(b.phone), web = L.cleanWebsite(b.website), ig = L.cleanInstagram(b.instagram);
    if (!(phone || web || ig)) throw S.bad("Add at least one way to reach the place: phone, website or Instagram");
    if ((await c.db.one("SELECT COUNT(*) n FROM companies WHERE submitted_by=? AND status='pending'", c.user.id)).n >= MAX_PENDING) throw S.bad("You already have 3 places waiting for your teacher. Wait for a review first");
    if (await c.db.one("SELECT 1 x FROM companies WHERE lower(name)=lower(?) AND status<>'rejected'", name)) throw new HTTPError(409, "A place with this name already exists. Search for it in the list");
    if (await X.rateBlocked(c, "company_propose", c.user.id, 10, 3600)) throw new HTTPError(429, "Too many attempts. Please wait a few minutes and try again.");
    await X.rateHit(c, "company_propose", c.user.id);
    var cl = U.collapse;
    var cid = await c.db.run("INSERT INTO companies(name,address,sector,sector_id,about,about_id,source,verified,sector_guess,website,instagram,phone,tasks,majors,work_terms,status,submitted_by,submitted_at) VALUES(?,?,?,?,?,?,?,0,0,?,?,?,?,?,?,'pending',?,datetime('now'))",
      name, cl(b.address), cl(b.sector), cl(b.sector), cl(b.about), cl(b.about), cl(b.source), web, ig, phone, cl(b.tasks), cl(b.majors), cl(b.work_terms), c.user.id);
    var ts = await c.db.all("SELECT id FROM users WHERE role='teacher' AND active=1");
    for (var i = 0; i < ts.length; i++) await S.notify(c.db, ts[i].id, S.msg(await S.userLang(c.db, ts[i].id), "note.company_submitted", { student: c.user.name, company: name }));
    await S.audit(c, "company_propose", cid + ":" + name);
    return { id: cid, status: "pending" };
  });
  api("/api/student/companies/mine", "GET", { roles: ST }, async function (c) { return { items: (await c.db.all("SELECT * FROM companies WHERE submitted_by=? ORDER BY id DESC", c.user.id)).map(function (r) { return X.co(r, c.lang, c.user.id); }) }; });
  api("/api/student/companies/{cid:int}", "DELETE", { roles: ST }, async function (c, cid) {
    var row = await c.db.one("SELECT * FROM companies WHERE id=? AND submitted_by=?", cid, c.user.id); if (!row) throw S.notFound("Company not found");
    if (row.status === "approved") throw new HTTPError(403, "An approved place can no longer be deleted by you");
    await c.db.run("DELETE FROM companies WHERE id=?", cid); await S.audit(c, "company_propose_delete", String(cid)); return { ok: true };
  });
  api("/api/teacher/company-submissions", "GET", { roles: R }, async function (c) {
    var rows = await c.db.all("SELECT co.*, u.name student_name, sp.class_name student_class FROM companies co JOIN users u ON u.id=co.submitted_by LEFT JOIN student_profiles sp ON sp.user_id=u.id WHERE co.status IN ('pending','rejected') ORDER BY co.status DESC, co.id DESC");
    var out = rows.map(function (r) { var x = X.co(r, c.lang); Object.assign(x, { student: r.student_name, student_class: r.student_class || "", submitted_at: r.submitted_at || "", review_note: r.review_note || "" }); return x; });
    return { items: out, pending: out.filter(function (x) { return x.status === "pending"; }).length };
  });
  var opt = function (max) { return F.str({ def: null, nullable: true, max: max }); };
  api("/api/teacher/company-submissions/{cid:int}", "PUT", { roles: R, model: { decision: F.str({ pattern: "^(approve|reject)$" }), note: F.str({ def: "", max: 300 }), address: opt(300), about: opt(800), sector: opt(80), phone: opt(30), website: opt(200), instagram: opt(200) } },
  async function (c, b, cid) {
    var row = await c.db.one("SELECT * FROM companies WHERE id=?", cid);
    if (!row || row.submitted_by === null || row.status === "approved") throw S.notFound("Submission not found");
    var sid = row.submitted_by, note = b.note.trim(), lang = await S.userLang(c.db, sid);
    if (b.decision === "reject") {
      if (note.length < 5) throw S.bad("Write a reason of at least 5 characters so the student can fix it");
      await c.db.run("UPDATE companies SET status='rejected', review_note=? WHERE id=?", note, cid);
      await c.db.run("DELETE FROM internship_choices WHERE company_id=?", cid);
      await S.notify(c.db, sid, S.msg(lang, "note.company_rejected", { company: row.name, note: note.slice(0, 120) })); await S.audit(c, "company_reject", cid + ":" + note.slice(0, 60));
      return { ok: true, status: "rejected" };
    }
    function fix(nw, old) { return nw !== null && nw.trim() ? U.collapse(nw) : old; }
    var addr = fix(b.address, row.address), about = fix(b.about, row.about), sec = fix(b.sector, row.sector);
    var phone = b.phone !== null && b.phone.trim() ? L.cleanPhone(b.phone) : row.phone, web = b.website !== null && b.website.trim() ? L.cleanWebsite(b.website) : row.website,
      ig = b.instagram !== null && b.instagram.trim() ? L.cleanInstagram(b.instagram) : row.instagram;
    var num = ((await c.db.one("SELECT MAX(number) m FROM companies")).m || 0) + 1, src = ((row.source || "") + " | Diverifikasi guru: " + c.user.name).slice(0, 200);
    await c.db.run("UPDATE companies SET status='approved', verified=1, number=?, address=?, about=?, about_id=?, sector=?, sector_id=?, phone=?, website=?, instagram=?, source=?, review_note=? WHERE id=?",
      num, addr, about, about, sec, sec, phone, web, ig, src, note, cid);
    await S.notify(c.db, sid, S.msg(lang, "note.company_approved", { company: row.name })); await S.audit(c, "company_approve", String(cid));
    return { ok: true, status: "approved" };
  });

  /* ---------- admin (admin.py) ---------- */
  api("/api/admin/users", "GET", { roles: A }, async function (c) {
    var role = c.query.get("role") || "", sql = "SELECT u.id,u.name,u.email,u.role,u.active,u.created_at,sp.major,sp.class_name FROM users u LEFT JOIN student_profiles sp ON sp.user_id=u.id";
    return { items: role ? await c.db.all(sql + " WHERE u.role=? ORDER BY u.role,u.name", role) : await c.db.all(sql + " ORDER BY u.role,u.name") };
  });
  api("/api/admin/users", "POST", { roles: A, model: { name: F.str({ min: 2, max: 80 }), email: F.str({ check: X.cleanEmail }), role: F.str({ pattern: "^(student|teacher|alumni|admin)$" }), password: F.str({ min: 8, max: 200 }),
      major: F.str({ def: "", pattern: "^(AK|TKJ|)$" }), class_name: F.str({ def: "", max: 20 }) } }, async function (c, b) {
    if (await c.db.one("SELECT 1 x FROM users WHERE email=?", b.email)) throw new HTTPError(409, "This email is already registered");
    var err = X.checkPassword(c, b.password, b.email, b.name, b.role !== "student"); if (err) throw new HTTPError(422, err);
    var uid = await c.db.run("INSERT INTO users(email,name,password_hash,role) VALUES(?,?,?,?)", b.email, b.name.trim(), X.hashPassword(c, b.password), b.role);
    if (b.role === "student") await c.db.run("INSERT INTO student_profiles(user_id,school,major,class_name) VALUES(?,?,?,?)", uid, "SMK Metta Maitreya", b.major, b.class_name);
    if (b.role === "alumni") await c.db.run("INSERT OR IGNORE INTO alumni_profiles(user_id) VALUES(?)", uid);
    await S.audit(c, "user_create", uid + ":" + b.role); return { id: uid };
  });
  api("/api/admin/users/{uid:int}", "PATCH", { roles: A, model: { name: F.str({ def: null, nullable: true, min: 2, max: 80 }), active: F.bool({ def: null, nullable: true }), password: F.str({ def: null, nullable: true, min: 8, max: 200 }) } },
  async function (c, b, uid) {
    var u = await c.db.one("SELECT * FROM users WHERE id=?", uid); if (!u) throw S.notFound("User not found");
    if (b.active === false && uid === c.user.id) throw S.bad("You cannot deactivate your own account");
    if (b.password) { var err = X.checkPassword(c, b.password, u.email, b.name || u.name, u.role !== "student"); if (err) throw new HTTPError(422, err); }
    if (b.name) await c.db.run("UPDATE users SET name=? WHERE id=?", b.name.trim(), uid);
    if (b.active !== null) { await c.db.run("UPDATE users SET active=? WHERE id=?", b.active ? 1 : 0, uid); if (!b.active && !c.replay) S.sessions.removeUser(uid); }
    if (b.password) { await c.db.run("UPDATE users SET password_hash=? WHERE id=?", X.hashPassword(c, b.password), uid); if (!c.replay) S.sessions.removeUser(uid); }
    await S.audit(c, "user_update", String(uid));
  });
  var RA = "abcdefghjkmnpqrstuvwxyz", RD = "23456789";
  function tempPassword() {
    function kata() { var s = ""; for (var i = 0; i < 4; i++) s += U.choice(i % 2 === 0 ? RA : "aiueo"); return s; }
    return [kata(), kata(), kata()].join("-") + "-" + U.choice(RD) + U.choice(RD);
  }
  api("/api/admin/users/{uid:int}/reset-password", "POST", { roles: A }, async function (c, uid) {
    var u = await c.db.one("SELECT * FROM users WHERE id=?", uid); if (!u) throw S.notFound("User not found");
    if (uid === c.user.id) throw S.bad("Use Settings to change your own password");
    var staff = u.role !== "student", pw = null;
    var h = c.det(function () {                                  // hanya hash yang dicatat; password sementara hanya tampil sekali di layar admin
      for (var i = 0; i < 8; i++) { var cand = tempPassword(); if (!checkPw(cand, u.email, u.name, staff)) { pw = cand; return U.hashPassword(cand); } }
      return null;
    });
    if (!h) throw new HTTPError(500, "Could not make a temporary password, please try again");
    await c.db.run("UPDATE users SET password_hash=?, must_change_password=1 WHERE id=?", h, uid);
    if (!c.replay) S.sessions.removeUser(uid);
    await S.audit(c, "password_reset", uid + ":" + u.email);
    return { email: u.email, name: u.name, temp_password: pw };
  });
  function checkPw(pw, email, name, staff) { return X.checkPassword({ det: function (f) { return f(); } }, pw, email, name, staff); }
  var SKILL = { name: F.str({ min: 2, max: 60 }), category: F.str({ def: "technical", pattern: "^(technical|soft)$" }) };
  api("/api/admin/skills", "GET", { roles: A }, async function (c) { return { items: await c.db.all("SELECT id,name,category FROM skills ORDER BY category,name") }; });
  api("/api/admin/skills", "POST", { roles: A, model: SKILL }, async function (c, b) {
    if (await c.db.one("SELECT 1 x FROM skills WHERE lower(name)=lower(?)", b.name.trim())) throw new HTTPError(409, "This skill already exists");
    var sid = await c.db.run("INSERT INTO skills(name,category) VALUES(?,?)", b.name.trim(), b.category); await S.audit(c, "skill_create", b.name); return { id: sid };
  });
  api("/api/admin/skills/{sid:int}", "PUT", { roles: A, model: SKILL }, async function (c, b, sid) {
    if (!(await c.db.one("SELECT 1 x FROM skills WHERE id=?", sid))) throw S.notFound("Skill not found");
    await c.db.run("UPDATE skills SET name=?,category=? WHERE id=?", b.name.trim(), b.category, sid); await S.audit(c, "skill_update", String(sid));
  });
  api("/api/admin/skills/{sid:int}", "DELETE", { roles: A }, async function (c, sid) {
    if (await c.db.one("SELECT 1 x FROM career_skills WHERE skill_id=?", sid)) throw S.bad("This skill is used by a career. Remove it from the career first.");
    await c.db.run("DELETE FROM skills WHERE id=?", sid); await S.audit(c, "skill_delete", String(sid));
  });
  var CAREER = { name: F.str({ min: 2, max: 80 }), category: F.str({ def: "", max: 40 }), description: F.str({ def: "", max: 1000 }), responsibilities: F.str({ def: "", max: 1000 }),
    education_path: F.str({ def: "", max: 600 }), example_projects: F.str({ def: "", max: 600 }), growth: F.str({ def: "", max: 600 }), interest_tags: F.str({ def: "", max: 100 }),
    strength_tags: F.str({ def: "", max: 100 }), majors: F.str({ def: "", max: 20 }), skills: F.list(F.model({ skill_id: F.int(), importance: F.int({ def: 2, ge: 1, le: 3 }) }), { def: function () { return []; } }) };
  async function saveCareerSkills(c, cid, skills) {
    await c.db.run("DELETE FROM career_skills WHERE career_id=?", cid);
    for (var i = 0; i < skills.length; i++) {
      if (!(await c.db.one("SELECT 1 x FROM skills WHERE id=?", skills[i].skill_id))) throw S.bad("Unknown skill");
      await c.db.run("INSERT OR REPLACE INTO career_skills(career_id,skill_id,importance) VALUES(?,?,?)", cid, skills[i].skill_id, skills[i].importance);
    }
  }
  api("/api/admin/careers", "GET", { roles: A }, async function (c) {
    var rows = await c.db.all("SELECT * FROM careers ORDER BY name");
    for (var i = 0; i < rows.length; i++) rows[i].skills = await c.db.all("SELECT skill_id, importance FROM career_skills WHERE career_id=?", rows[i].id);
    return { items: rows };
  });
  api("/api/admin/careers", "POST", { roles: A, model: CAREER }, async function (c, b) {
    if (await c.db.one("SELECT 1 x FROM careers WHERE lower(name)=lower(?)", b.name.trim())) throw new HTTPError(409, "This career already exists");
    var cid = await c.db.run("INSERT INTO careers(name,category,description,responsibilities,education_path,example_projects,growth,interest_tags,strength_tags,majors) VALUES(?,?,?,?,?,?,?,?,?,?)",
      b.name.trim(), b.category, b.description, b.responsibilities, b.education_path, b.example_projects, b.growth, b.interest_tags, b.strength_tags, b.majors);
    await saveCareerSkills(c, cid, b.skills); await S.audit(c, "career_create", b.name); return { id: cid };
  });
  api("/api/admin/careers/{cid:int}", "PUT", { roles: A, model: CAREER }, async function (c, b, cid) {
    if (!(await c.db.one("SELECT 1 x FROM careers WHERE id=?", cid))) throw S.notFound("Career not found");
    await c.db.run("UPDATE careers SET name=?,category=?,description=?,responsibilities=?,education_path=?,example_projects=?,growth=?,interest_tags=?,strength_tags=?,majors=? WHERE id=?",
      b.name.trim(), b.category, b.description, b.responsibilities, b.education_path, b.example_projects, b.growth, b.interest_tags, b.strength_tags, b.majors, cid);
    await saveCareerSkills(c, cid, b.skills); await S.audit(c, "career_update", String(cid));
  });
  api("/api/admin/careers/{cid:int}", "DELETE", { roles: A }, async function (c, cid) {
    if (await c.db.one("SELECT 1 x FROM plans WHERE career_id=?", cid)) throw S.bad("Students have plans for this career, so it cannot be deleted.");
    await c.db.run("DELETE FROM careers WHERE id=?", cid); await S.audit(c, "career_delete", String(cid));
  });
  var COMPANY = { name: F.str({ min: 2, max: 120 }), address: F.str({ def: "", max: 300 }), number: F.int({ def: null, nullable: true, ge: 1, le: 9999 }), sector: F.str({ def: "", max: 80 }),
    sector_id: F.str({ def: "", max: 80 }), about: F.str({ def: "", max: 800 }), about_id: F.str({ def: "", max: 800 }), source: F.str({ def: "", max: 200 }), verified: F.bool({ def: false }),
    website: F.str({ def: "", max: 200 }), instagram: F.str({ def: "", max: 200 }), phone: F.str({ def: "", max: 30 }) };
  api("/api/admin/companies", "POST", { roles: A, model: COMPANY }, async function (c, b) {
    var num = b.number || (((await c.db.one("SELECT MAX(number) m FROM companies")).m || 0) + 1);
    var w = L.cleanWebsite(b.website), ig = L.cleanInstagram(b.instagram), ph = L.cleanPhone(b.phone);
    var cid = await c.db.run("INSERT INTO companies(number,name,address,sector,sector_id,about,about_id,source,verified,website,instagram,phone) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", num, b.name.trim(), b.address.trim(), b.sector.trim(), b.sector_id.trim(), b.about.trim(), b.about_id.trim(), b.source.trim(), b.verified ? 1 : 0, w, ig, ph);
    await S.audit(c, "company_create", b.name); return { id: cid };
  });
  api("/api/admin/companies/{cid:int}", "PUT", { roles: A, model: COMPANY }, async function (c, b, cid) {
    if (!(await c.db.one("SELECT 1 x FROM companies WHERE id=?", cid))) throw S.notFound("Company not found");
    var w = L.cleanWebsite(b.website), ig = L.cleanInstagram(b.instagram), ph = L.cleanPhone(b.phone);
    await c.db.run("UPDATE companies SET name=?,address=?,number=COALESCE(?,number),sector=?,sector_id=?,about=?,about_id=?,source=?,verified=?,website=?,instagram=?,phone=?,sector_guess=0 WHERE id=?", b.name.trim(), b.address.trim(), b.number, b.sector.trim(), b.sector_id.trim(), b.about.trim(), b.about_id.trim(), b.source.trim(), b.verified ? 1 : 0, w, ig, ph, cid);
    await S.audit(c, "company_update", String(cid));
  });
  api("/api/teacher/companies/{cid:int}", "PUT", { roles: T, model: { address: F.str({ def: "", max: 300 }), sector: F.str({ def: "", max: 80 }), sector_id: F.str({ def: "", max: 80 }), about: F.str({ def: "", max: 800 }),
      about_id: F.str({ def: "", max: 800 }), source: F.str({ min: 3, max: 200 }), website: F.str({ def: "", max: 200 }), instagram: F.str({ def: "", max: 200 }), phone: F.str({ def: "", max: 30 }) } }, async function (c, b, cid) {
    var row = await c.db.one("SELECT verified FROM companies WHERE id=?", cid); if (!row) throw S.notFound("Company not found");
    if (row.verified) throw new HTTPError(403, "This company is already verified. Ask the admin to change it");
    var w = L.cleanWebsite(b.website), i = L.cleanInstagram(b.instagram), p = L.cleanPhone(b.phone);
    if (!(b.address.trim() || b.about.trim() || b.sector.trim())) throw S.bad("Fill at least the address, the sector or a short description");
    await c.db.run("UPDATE companies SET address=?,sector=?,sector_id=?,about=?,about_id=?,source=?,website=CASE WHEN ?<>'' THEN ? ELSE website END,instagram=CASE WHEN ?<>'' THEN ? ELSE instagram END,phone=CASE WHEN ?<>'' THEN ? ELSE phone END,sector_guess=0 WHERE id=?",
      b.address.trim(), b.sector.trim(), b.sector_id.trim(), b.about.trim(), b.about_id.trim(), b.source.trim(), w, w, i, i, p, p, cid);
    await S.audit(c, "company_fill", String(cid)); return { ok: true };
  });
  api("/api/admin/companies/{cid:int}", "DELETE", { roles: A }, async function (c, cid) { await c.db.run("DELETE FROM companies WHERE id=?", cid); await S.audit(c, "company_delete", String(cid)); });
  api("/api/admin/companies/import", "POST", { roles: A, model: { text: F.str({ min: 3, max: 200000 }) } }, async function (c, b) {
    var added = 0, skipped = 0, lines = b.text.split(/\r\n|\r|\n/);
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i].trim(); if (!line) continue;
      var parts = line.split(/[;\t]/).map(function (p) { return p.trim(); }), num = null;
      if (parts.length && /^\d{1,4}$/.test(parts[0])) num = parseInt(parts.shift(), 10);
      if (!parts.length || parts[0].length < 2) { skipped++; continue; }
      var name = parts[0].slice(0, 120), addr = (parts.length > 1 ? parts[1] : "").slice(0, 300);
      if (await c.db.one("SELECT 1 x FROM companies WHERE lower(name)=lower(?)", name)) { skipped++; continue; }
      await c.db.run("INSERT INTO companies(number,name,address) VALUES(?,?,?)", num || (((await c.db.one("SELECT MAX(number) m FROM companies")).m || 0) + 1), name, addr); added++;
    }
    await S.audit(c, "company_import", "+" + added + "/-" + skipped); return { added: added, skipped: skipped };
  });
  async function summary(c) {
    var n = async function (sql) { return (await c.db.one(sql)).n; };
    return { users: await n("SELECT COUNT(*) n FROM users"), students: await n("SELECT COUNT(*) n FROM users WHERE role='student'"), companies: await n("SELECT COUNT(*) n FROM companies"),
      careers: await n("SELECT COUNT(*) n FROM careers"), students_with_choices: await n("SELECT COUNT(DISTINCT user_id) n FROM internship_choices"),
      assessments: await n("SELECT COUNT(DISTINCT user_id) n FROM assessments"), plans: await n("SELECT COUNT(*) n FROM plans WHERE status='ACTIVE'"),
      projects_pending: await n("SELECT COUNT(*) n FROM projects WHERE status='SUBMITTED'"), projects_verified: await n("SELECT COUNT(*) n FROM projects WHERE status='VERIFIED'") };
  }
  api("/api/admin/summary", "GET", { roles: A }, summary);
  api("/api/admin/analytics", "GET", { roles: A }, async function (c) {
    var d = c.db;
    var pop = (await d.all("SELECT ca.id, ca.name label, COUNT(*) value FROM plans p JOIN careers ca ON ca.id=p.career_id WHERE p.status='ACTIVE' GROUP BY ca.id ORDER BY value DESC, ca.name LIMIT 8")).map(function (x) { return { label: d.tr("career", x.id, "name", x.label), value: x.value }; });
    var topCo = await d.all("SELECT co.name label, COUNT(*) value FROM internship_choices ic JOIN companies co ON co.id=ic.company_id WHERE ic.rank=1 GROUP BY co.id ORDER BY value DESC LIMIT 8");
    var roles = {}; (await d.all("SELECT role, COUNT(*) n FROM users WHERE active=1 GROUP BY role")).forEach(function (x) { roles[x.role] = x.n; });
    var majors = await d.all("SELECT COALESCE(NULLIF(sp.major,''),'-') label, COUNT(*) value FROM users u LEFT JOIN student_profiles sp ON sp.user_id=u.id WHERE u.role='student' AND u.active=1 GROUP BY label ORDER BY label");
    var pst = {}; (await d.all("SELECT status, COUNT(*) n FROM projects GROUP BY status")).forEach(function (x) { pst[x.status] = x.n; });
    return { summary: await summary(c), popular_careers: pop, first_choice_companies: topCo, users_by_role: ["student", "teacher", "alumni", "admin"].map(function (k) { return { key: k, value: roles[k] || 0 }; }),
      students_by_major: majors, projects: ["SUBMITTED", "NEEDS_REVISION", "VERIFIED"].map(function (k) { return { key: k, value: pst[k] || 0 }; }) };
  });
  api("/api/admin/audit", "GET", { roles: A }, async function (c) { return { items: await c.db.all("SELECT a.id,a.action,a.detail,a.created_at,u.name actor FROM audit_log a LEFT JOIN users u ON u.id=a.actor_id ORDER BY a.id DESC LIMIT 100") }; });

  /* ---------- alumni (alumni.py) ---------- */
  var AL = ["alumni"], READ = ["student", "teacher", "admin"], KINDS_RX = "^(CAREER_STORY|EDUCATION|TIPS)$", MAX_ITEMS = 30;
  async function profileRow(db, uid) { return (await db.one("SELECT graduation_year,major,workplace,job_title,bio FROM alumni_profiles WHERE user_id=?", uid)) || { graduation_year: null, major: "", workplace: "", job_title: "", bio: "" }; }
  api("/api/alumni/profile", "GET", { roles: AL }, function (c) { return profileRow(c.db, c.user.id); });
  api("/api/alumni/profile", "PUT", { roles: AL, model: { graduation_year: F.int({ def: null, nullable: true, ge: 1990, le: 2100 }), major: F.str({ def: "", pattern: "^(AK|TKJ|)$" }), workplace: F.str({ def: "", max: 100 }),
      job_title: F.str({ def: "", max: 100 }), bio: F.str({ def: "", max: 500 }) } }, async function (c, b) {
    await c.db.run("INSERT INTO alumni_profiles(user_id,graduation_year,major,workplace,job_title,bio) VALUES(?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET graduation_year=excluded.graduation_year, major=excluded.major, workplace=excluded.workplace, job_title=excluded.job_title, bio=excluded.bio",
      c.user.id, b.graduation_year, b.major, b.workplace.trim(), b.job_title.trim(), b.bio.trim());
    return profileRow(c.db, c.user.id);
  });
  var CONTENT = { kind: F.str({ pattern: KINDS_RX }), title: F.str({ min: 4, max: 120 }), category: F.str({ def: "", max: 40 }), body: F.str({ min: 40, max: 5000 }),
    career_id: F.int({ def: null, nullable: true }), skill_id: F.int({ def: null, nullable: true }), submit: F.bool({ def: false }) };
  async function refs(db, b) {
    if (b.career_id !== null && !(await db.one("SELECT 1 x FROM careers WHERE id=?", b.career_id))) throw S.notFound("Career not found");
    if (b.skill_id !== null && !(await db.one("SELECT 1 x FROM skills WHERE id=?", b.skill_id))) throw S.notFound("Skill not found");
  }
  async function mineStory(c, cid) { var r = await c.db.one("SELECT * FROM alumni_content WHERE id=? AND author_id=?", cid, c.user.id); if (!r) throw S.notFound("Story not found"); return r; }
  api("/api/alumni/content", "GET", { roles: AL }, async function (c) {
    var counts = {}; (await c.db.all("SELECT status, COUNT(*) n FROM alumni_content WHERE author_id=? GROUP BY status", c.user.id)).forEach(function (r) { counts[r.status] = r.n; });
    return { items: await c.db.all("SELECT id,kind,title,category,body,career_id,skill_id,status,moderation_note,created_at,published_at FROM alumni_content WHERE author_id=? ORDER BY id DESC", c.user.id), counts: counts };
  });
  api("/api/alumni/content", "POST", { roles: AL, model: CONTENT }, async function (c, b) {
    if ((await c.db.one("SELECT COUNT(*) n FROM alumni_content WHERE author_id=?", c.user.id)).n >= MAX_ITEMS) throw S.bad("You have reached the limit of 30 stories");
    await refs(c.db, b);
    var st = b.submit ? "PENDING" : "DRAFT";
    var cid = await c.db.run("INSERT INTO alumni_content(author_id,kind,title,category,body,career_id,skill_id,status) VALUES(?,?,?,?,?,?,?,?)", c.user.id, b.kind, b.title.trim(), b.category.trim(), b.body.trim(), b.career_id, b.skill_id, st);
    await S.audit(c, "alumni_content_create", cid + ":" + st); return { id: cid };
  });
  api("/api/alumni/content/{cid:int}", "PUT", { roles: AL, model: CONTENT }, async function (c, b, cid) {
    var r = await mineStory(c, cid);
    if (r.status !== "DRAFT" && r.status !== "REJECTED") throw S.bad("Only drafts and rejected stories can be edited");
    await refs(c.db, b);
    var st = b.submit ? "PENDING" : "DRAFT";
    await c.db.run("UPDATE alumni_content SET kind=?,title=?,category=?,body=?,career_id=?,skill_id=?,status=?,moderation_note=CASE WHEN ? THEN '' ELSE moderation_note END WHERE id=?",
      b.kind, b.title.trim(), b.category.trim(), b.body.trim(), b.career_id, b.skill_id, st, b.submit ? 1 : 0, cid);
    await S.audit(c, "alumni_content_update", cid + ":" + st); return { id: cid };
  });
  api("/api/alumni/content/{cid:int}", "DELETE", { roles: AL }, async function (c, cid) {
    var r = await mineStory(c, cid); if (r.status === "PUBLISHED") throw S.bad("A published story can only be removed by the admin");
    await c.db.run("DELETE FROM alumni_content WHERE id=?", cid); await S.audit(c, "alumni_content_delete", String(cid));
  });
  api("/api/admin/content", "GET", { roles: A }, async function (c) {
    var st = c.query.get("status") || "PENDING";
    if (["PENDING", "PUBLISHED", "REJECTED", "DRAFT"].indexOf(st) < 0) throw S.bad("Unknown status");
    var rows = await c.db.all("SELECT ac.id,ac.kind,ac.title,ac.category,ac.body,ac.status,ac.moderation_note,ac.created_at,u.name author, ap.job_title, ap.workplace FROM alumni_content ac JOIN users u ON u.id=ac.author_id LEFT JOIN alumni_profiles ap ON ap.user_id=u.id WHERE ac.status=? ORDER BY ac.id", st);
    return { items: rows, pending: (await c.db.one("SELECT COUNT(*) n FROM alumni_content WHERE status='PENDING'")).n };
  });
  api("/api/admin/content/{cid:int}/moderate", "POST", { roles: A, model: { decision: F.str({ pattern: "^(PUBLISHED|REJECTED)$" }), note: F.str({ def: "", max: 500 }) } }, async function (c, b, cid) {
    var r = await c.db.one("SELECT * FROM alumni_content WHERE id=?", cid);
    if (!r || r.status === "DRAFT") throw S.notFound("Story not found");
    if (b.decision === "REJECTED" && b.note.trim().length < 5) throw S.bad("Write a short note so the author knows what to fix");
    await c.db.run("UPDATE alumni_content SET status=?, moderated_by=?, moderation_note=?, published_at=CASE WHEN ?='PUBLISHED' THEN datetime('now') ELSE NULL END WHERE id=?", b.decision, c.user.id, b.note.trim(), b.decision, cid);
    var lang = await S.userLang(c.db, r.author_id);
    await S.notify(c.db, r.author_id, S.msg(lang, b.decision === "PUBLISHED" ? "note.story_published" : "note.story_rejected", { title: r.title, note: Array.from(b.note.trim()).slice(0, 120).join("") }));
    await S.audit(c, "alumni_content_moderate", cid + ":" + b.decision);
  });
  api("/api/alumni-stories", "GET", { roles: READ }, async function (c) {
    var q = (c.query.get("q") || "").trim().toLowerCase(), kind = c.query.get("kind") || "";
    if (kind && ["CAREER_STORY", "EDUCATION", "TIPS"].indexOf(kind) < 0) throw S.bad("Unknown type");
    var rows = await c.db.all("SELECT ac.id,ac.kind,ac.title,ac.category,ac.body,ac.published_at,ac.career_id,u.name author,ap.job_title,ap.workplace,ap.graduation_year,ap.major FROM alumni_content ac JOIN users u ON u.id=ac.author_id AND u.active=1 LEFT JOIN alumni_profiles ap ON ap.user_id=u.id WHERE ac.status='PUBLISHED' AND (?='' OR ac.kind=?) ORDER BY ac.published_at DESC, ac.id DESC", kind, kind);
    rows = rows.filter(function (r) { return !q || (r.title + " " + r.body + " " + r.category + " " + r.author).toLowerCase().indexOf(q) >= 0; });
    rows.forEach(function (r) { var body = Array.from(r.body); if (body.length > 180) { var cut = body.slice(0, 180).join(""), sp = cut.lastIndexOf(" "); r.excerpt = (sp >= 0 ? cut.slice(0, sp) : cut) + "…"; } else r.excerpt = r.body; });
    return { items: rows };
  });

  /* ---------- portfolio (portfolio.py) ---------- */
  var PMAX = 50, DATE = "^(\\d{4}(-\\d{2}(-\\d{2})?)?)?$", SLUG = /^[A-Za-z0-9_-]{10,40}$/;
  function cleanUrl(u) { u = U.strip(u); X.validLink(u); return u.slice(0, 300); }
  async function items(db, uid) {
    var ach = await db.all("SELECT id,title,issuer,achieved_on,(verified_by IS NOT NULL) verified FROM achievements WHERE user_id=? ORDER BY id DESC", uid);
    var cer = await db.all("SELECT id,title,issuer,issued_on,url,(verified_by IS NOT NULL) verified FROM certificates WHERE user_id=? ORDER BY id DESC", uid);
    var fa = await X.filesMap(db, "achievement", ach.map(function (r) { return r.id; })), fc = await X.filesMap(db, "certificate", cer.map(function (r) { return r.id; }));
    ach.forEach(function (r) { r.verified = !!r.verified; r.files = fa[r.id]; }); cer.forEach(function (r) { r.verified = !!r.verified; r.files = fc[r.id]; });
    return [ach, cer];
  }
  async function shareState(db, uid) { return (await db.one("SELECT visibility,slug,headline FROM portfolios WHERE user_id=?", uid)) || { visibility: "PRIVATE", slug: null, headline: "" }; }
  async function extras(c) { var it = await items(c.db, c.user.id); return { achievements: it[0], certificates: it[1], share: await shareState(c.db, c.user.id) }; }
  api("/api/student/portfolio/extras", "GET", { roles: ST }, extras);
  api("/api/student/portfolio/share", "PUT", { roles: ST, model: { visibility: F.str({ pattern: "^(PRIVATE|LINK|PUBLIC)$" }), new_link: F.bool({ def: false }), headline: F.str({ def: "", max: 120 }) } }, async function (c, b) {
    var uid = c.user.id, cur = await c.db.one("SELECT slug FROM portfolios WHERE user_id=?", uid), slug = cur && cur.slug ? cur.slug : null;
    if (b.visibility !== "PRIVATE" && (!slug || b.new_link)) slug = c.det(U.slug);
    else if (b.new_link) slug = slug ? c.det(U.slug) : null;
    await c.db.run("INSERT INTO portfolios(user_id,visibility,slug,headline,updated_at) VALUES(?,?,?,?,datetime('now')) ON CONFLICT(user_id) DO UPDATE SET visibility=excluded.visibility, slug=excluded.slug, headline=excluded.headline, updated_at=datetime('now')",
      uid, b.visibility, slug, b.headline.trim());
    await S.audit(c, "portfolio_share", b.visibility + (b.new_link ? " new_link" : ""));
    return shareState(c.db, uid);
  });
  async function own(db, table, uid, iid) { if (!(await db.one("SELECT id FROM " + table + " WHERE id=? AND user_id=?", iid, uid))) throw S.notFound("Item not found"); }
  api("/api/student/achievements", "POST", { roles: ST, model: { title: F.str({ min: 2, max: 120 }), issuer: F.str({ def: "", max: 100 }), achieved_on: F.str({ def: "", pattern: DATE }) } }, async function (c, b) {
    if ((await c.db.one("SELECT COUNT(*) n FROM achievements WHERE user_id=?", c.user.id)).n >= PMAX) throw S.bad("You have reached the limit of 50 items");
    var nid = await c.db.run("INSERT INTO achievements(user_id,title,issuer,achieved_on) VALUES(?,?,?,?)", c.user.id, b.title.trim(), b.issuer.trim(), b.achieved_on);
    return Object.assign(await extras(c), { new_id: nid });
  });
  api("/api/student/achievements/{iid:int}", "DELETE", { roles: ST }, async function (c, iid) { await own(c.db, "achievements", c.user.id, iid); await purge(c.db, "achievement", iid); await c.db.run("DELETE FROM achievements WHERE id=?", iid); return extras(c); });
  api("/api/student/certificates", "POST", { roles: ST, model: { title: F.str({ min: 2, max: 120 }), issuer: F.str({ def: "", max: 100 }), issued_on: F.str({ def: "", pattern: DATE }), url: F.str({ def: "", max: 300 }) } }, async function (c, b) {
    if ((await c.db.one("SELECT COUNT(*) n FROM certificates WHERE user_id=?", c.user.id)).n >= PMAX) throw S.bad("You have reached the limit of 50 items");
    var nid = await c.db.run("INSERT INTO certificates(user_id,title,issuer,issued_on,url) VALUES(?,?,?,?,?)", c.user.id, b.title.trim(), b.issuer.trim(), b.issued_on, cleanUrl(b.url));
    return Object.assign(await extras(c), { new_id: nid });
  });
  api("/api/student/certificates/{iid:int}", "DELETE", { roles: ST }, async function (c, iid) { await own(c.db, "certificates", c.user.id, iid); await purge(c.db, "certificate", iid); await c.db.run("DELETE FROM certificates WHERE id=?", iid); return extras(c); });
  api("/api/teacher/students/{sid:int}/portfolio-items", "GET", { roles: T }, async function (c, sid) {
    if (!(await c.db.one("SELECT 1 x FROM users WHERE id=? AND role='student'", sid))) throw S.notFound("Student not found");
    var it = await items(c.db, sid); return { achievements: it[0], certificates: it[1] };
  });
  api("/api/teacher/portfolio-items/{kind}/{iid:int}/verify", "POST", { roles: T }, async function (c, kind, iid) {
    var table = { achievements: "achievements", certificates: "certificates" }[kind]; if (!table) throw S.notFound("Item not found");
    var r = await c.db.one("SELECT id,user_id,title FROM " + table + " WHERE id=?", iid); if (!r) throw S.notFound("Item not found");
    await c.db.run("UPDATE " + table + " SET verified_by=? WHERE id=?", c.user.id, iid);
    await S.audit(c, "portfolio_item_verified", kind + ":" + iid);
    await S.notify(c.db, r.user_id, S.msg(await S.userLang(c.db, r.user_id), "note.item_verified", { title: r.title }));
    return { ok: true };
  });
  api("/api/public/portfolio/{slug}", "GET", { pub: true }, async function (c, slug) {
    var ip = X.clientIp(c);
    if (await X.rateBlocked(c, "portfolio_miss", ip, 30, 600)) throw X.tooMany();
    var row = SLUG.test(slug) ? await c.db.one("SELECT user_id,headline FROM portfolios WHERE slug=? AND visibility IN('LINK','PUBLIC')", slug) : null;
    if (!row) { await X.rateHit(c, "portfolio_miss", ip); throw S.notFound("Portfolio not found"); }
    var uid = row.user_id, u = await c.db.one("SELECT name FROM users WHERE id=? AND active=1 AND role='student'", uid); if (!u) throw S.notFound("Portfolio not found");
    var prof = (await c.db.one("SELECT school,major,class_name FROM student_profiles WHERE user_id=?", uid)) || {}, plan = await E.activePlan(c.db, uid);
    var keep = ["title", "description", "skills", "link", "problem", "solution", "result", "technology", "demo_url", "repo_url", "doc_url"];
    var projects = (await X.rowsProject(c, await c.db.all("SELECT * FROM projects WHERE user_id=? AND status='VERIFIED' ORDER BY id DESC", uid))).map(function (p) { var o = {}; keep.forEach(function (k) { if (k in p) o[k] = p[k]; }); return o; });
    var skills = (await c.db.all("SELECT s.id, s.name, ss.level FROM student_skills ss JOIN skills s ON s.id=ss.skill_id WHERE ss.user_id=? AND ss.level>=2 ORDER BY ss.level DESC, s.name", uid))
      .map(function (s) { return { name: c.db.tr("skill", s.id, "name", s.name), level: s.level, evidence: E.lvl(c.db, s.level) }; });
    var it = await items(c.db, uid);
    return { name: u.name, headline: row.headline, school: prof.school || "", major: prof.major || "", class_name: prof.class_name || "", target: plan ? plan.career_name : null, projects: projects, skills: skills,
      courses: await CW.completedCourses(c.db, uid), achievements: it[0].map(function (a) { return { title: a.title, issuer: a.issuer, achieved_on: a.achieved_on, verified: a.verified }; }),
      certificates: it[1].map(function (a) { return { title: a.title, issuer: a.issuer, issued_on: a.issued_on, url: a.url, verified: a.verified }; }) };
  });
})(typeof window !== "undefined" ? window : globalThis);
