var tr = I18N.tr;
/* Teacher and admin views */
(function () {
  var h = M.h, api = M.api, btn = M.btn, chip = M.chip, card = M.card;
  var T = function (p, f) { M.view("teacher", p, f); }, A = function (p, f) { M.view("admin", p, f); };
  function stack() { return h("div", { class: "grid" }, Array.prototype.slice.call(arguments)); }
  function stat(label, v) { return card(label, h("div", { class: "big" }, String(v))); }
  function majorChip(m) { return m ? chip(m, m === "AK" ? "ak" : "tkj") : "—"; }
  /* ============ PASSWORD REQUESTS (teacher: students only, admin: everyone) ============ */
  function resets() { return api("/api/staff/password-requests").then(function (d) {
    var codeBox = h("div");
    function approve(r) { api("/api/staff/password-requests/" + r.id + "/approve", "POST").then(function (x) { codeBox.textContent = "";
      codeBox.appendChild(h("div", { class: "card good" }, h("b", null, tr("One-time code for {0}", x.name)), h("div", { class: "big", style: "letter-spacing:.14em" }, x.code),
        h("div", { class: "small" }, tr("Valid for {0} hours. Read it to the person only after you confirm it is really them. It is shown only once.", x.hours)),
        h("div", { class: "small muted" }, tr("They open Forgot your password, then I already have a code, and enter {0}, the code, and a new password.", x.email)))); window.scrollTo(0, 0); }).catch(M.fail); }
    function reject(r) { if (window.confirm(tr("Reject this request?"))) api("/api/staff/password-requests/" + r.id + "/reject", "POST").then(function () { M.route(); }).catch(M.fail); }
    var label = { PENDING: "Waiting", APPROVED: "Code given", DONE: "Password changed", REJECTED: "Rejected" };
    return stack(M.pageHead("Password requests", "Confirm who is asking, then give a one-time code. You never see their new password."), codeBox,
      d.items.length ? M.table(["Name", "Email", "Role", "Class", "Status", ""], d.items.map(function (r) { var open = r.status === "PENDING" || r.status === "APPROVED";
        return [r.name, r.email, r.role, r.class_name || "—", chip(label[r.status] || r.status, r.status === "DONE" ? "good" : ""), open ? h("div", { class: "btns" }, btn(r.status === "APPROVED" ? "New code" : "Approve and show code", function () { approve(r); }, "p s"), btn("Reject", function () { reject(r); }, "g s")) : "—"]; }))
        : h("div", { class: "card note" }, "No requests right now."));
  }); }
  T("#/resets", resets); A("#/resets", resets);

  /* ================= TEACHER ================= */
  T("#/dashboard", function () { return api("/api/teacher/summary").then(function (d) {
    return stack(M.pageHead("Teacher dashboard", "Students who need attention appear first"),
      h("div", { class: "grid g3" }, stat("On track", d.on_track), stat("Active", d.active), stat("Inactive", d.inactive), stat("Needs feedback", d.needs_feedback), stat("No plan yet", d.no_plan), stat("Total students", d.total)),
      card("Needs attention", M.table(["Student", "Status", "Last active"], d.attention.map(function (a) { return [a.name, M.statusChip(a.status), M.date(a.last_active_at)]; }), function (i) { M.go("#/students/" + d.attention[i].id); })));
  }); });
  T("#/students", function () {
    var q = h("input", { type: "search", placeholder: "Search student" }), st = M.select([["", "All status"], "On track", "Active", "Inactive", "Needs feedback", "No plan yet"]), mj = M.select([["", "All majors"], "AK", "TKJ"]), box = h("div");
    function load() { api("/api/teacher/students?q=" + encodeURIComponent(q.value) + "&status=" + encodeURIComponent(st.value) + "&major=" + mj.value).then(function (d) { box.textContent = "";
      box.appendChild(M.table(["Student", "Major", "Class", "Target", "Readiness", "Status"], d.items.map(function (s) { return [s.name, majorChip(s.major), s.class_name || "—", s.target || "—", s.readiness + "%", M.statusChip(s.status)]; }), function (i) { M.go("#/students/" + d.items[i].id); })); }).catch(M.fail); }
    q.addEventListener("input", function () { clearTimeout(q._t); q._t = setTimeout(load, 250); }); st.addEventListener("change", load); mj.addEventListener("change", load); load();
    return stack(M.pageHead("Students"), h("div", { class: "grid g3" }, M.field("Search", q), M.field("Status", st), M.field("Major", mj)), box);
  });
  T("#/students/(\\d+)", function (m) { return Promise.all([api("/api/teacher/students/" + m[1]), api("/api/teacher/students/" + m[1] + "/portfolio-items")]).then(function (res) { var d = res[0], pi = res[1];
    function itemList(rows, kind, dateKey) { return rows.length ? h("ul", { class: "list small" }, rows.map(function (r) { return h("li", null, h("b", null, r.title), r.issuer || r[dateKey] ? h("span", { class: "muted" }, " · " + [r.issuer, r[dateKey]].filter(Boolean).join(" · ")) : null, " ", M.fileLinks(r.files), " ", r.verified ? chip("Verified", "good") : btn("Mark Verified", function () { api("/api/teacher/portfolio-items/" + kind + "/" + r.id + "/verify", "POST").then(function () { M.toast("Marked as verified"); M.route(); }).catch(M.fail); }, "g s")); })) : h("span", { class: "muted" }, "None yet"); }
    var s = d.student, fb = h("textarea", { placeholder: "Write feedback for this student" }), err = M.errBox();
    return stack(M.pageHead(s.name, [s.major, s.class_name].filter(Boolean).join(" · ") + " · " + d.status.status, [btn("Back", function () { M.back("#/students"); }, "g")]),
      h("div", { class: "grid g3" }, stat("Readiness", d.status.readiness + "%"), card("Target career", h("b", null, d.plan ? d.plan.career : "No plan yet")), card("Interests / strengths", d.insight ? h("div", { class: "chips" }, (d.insight.interest_labels || d.insight.interests).concat(d.insight.strength_labels || d.insight.strengths).map(function (t) { return chip(t.replace(/_/g, " ")); })) : h("span", { class: "muted" }, "No assessment yet"))),
      h("div", { class: "grid g2" }, card("Progress", d.tasks.length ? h("ul", { class: "list small" }, d.tasks.map(function (t) { return h("li", null, t.title, " ", M.statusChip(t.status)); })) : h("span", { class: "muted" }, "No tasks yet")),
        card("Skills and evidence", M.table(["Skill", "Evidence"], d.skills.map(function (k) { return [k.name, chip(k.evidence, k.level === 4 ? "good" : "")]; })))),
      h("div", { class: "grid g2" }, card("Projects", d.projects.length ? M.table(["Title", "Status"], d.projects.map(function (p) { return [p.title, M.statusChip(p.status)]; })) : h("span", { class: "muted" }, "None yet")),
        card("Internship choices", M.table(["Choice", "Company"], d.internship.map(function (c) { return [String(c.rank), c.name]; })))),
      h("div", { class: "grid g2" }, card("Achievements", itemList(pi.achievements, "achievements", "achieved_on")), card("Certificates", itemList(pi.certificates, "certificates", "issued_on"))),
      h("div", { class: "grid g2" }, card("Send feedback", fb, err, h("div", null, btn("Save and send to student", function () { err.classList.add("hide"); api("/api/teacher/students/" + s.id + "/feedback", "POST", { text: fb.value }).then(function () { M.toast("Feedback sent"); M.route(); }).catch(function (x) { M.showErr(err, x.message); }); }, "p"))),
        card("Feedback history", d.feedback.length ? h("ul", { class: "list small" }, d.feedback.map(function (f) { return h("li", null, f.text, h("div", { class: "muted" }, f.teacher + " · " + M.date(f.created_at))); })) : h("span", { class: "muted" }, "None yet"))));
  }); });
  T("#/plans", function () { return api("/api/teacher/plans").then(function (d) {
    var sel = null, area = h("div");
    function show(p) { area.textContent = ""; var note = h("textarea", null, p.teacher_note || ""), err = M.errBox();
      area.appendChild(card(tr("Plan: {0} → {1}", p.student, p.career), M.field("Guidance notes", note), err, h("div", null, btn("Save notes", function () { api("/api/teacher/plans/" + p.id + "/guidance", "PUT", { note: note.value }).then(function () { M.toast("Notes saved"); p.teacher_note = note.value; }).catch(function (x) { M.showErr(err, x.message); }); }, "p")))); }
    return stack(M.pageHead("Career Plans"), h("div", { class: "grid g12" }, card("Plan list", M.table(["Student", "Target"], d.items.map(function (p) { return [p.student, p.career]; }), function (i) { show(d.items[i]); })), area));
  }); });
  T("#/projects", function () { return api("/api/teacher/projects").then(function (d) { return stack(M.pageHead("Student projects"), M.table(["Student", "Project", "Skills", "Files", "Status"], d.items.map(function (p) { return [p.student, p.title, p.skills.join(", "), p.files.length ? M.fileLinks(p.files) : "—", M.statusChip(p.status)]; }))); }); });
  T("#/validation", function () { return api("/api/teacher/validation").then(function (d) {
    return stack(M.pageHead("Validation", "Projects waiting for your decision"), d.items.length ? d.items.map(function (p) {
      var note = h("textarea", { placeholder: "Revision notes (required if you request a revision)" }), err = M.errBox();
      function decide(x) { err.classList.add("hide"); api("/api/teacher/projects/" + p.id + "/review", "POST", { decision: x, note: note.value }).then(function () { M.toast(x === "VERIFIED" ? "Marked as verified" : "Revision requested"); M.route(); }).catch(function (e) { M.showErr(err, e.message); }); }
      return card(p.title + " · " + p.student, p.description ? h("p", null, p.description) : null, p.link ? h("a", { href: p.link, target: "_blank", rel: "noopener noreferrer" }, "Open evidence link") : null,
        [["Problem", p.problem], ["Solution", p.solution], ["Result", p.result], ["Technology", p.technology]].map(function (x) { return x[1] ? h("div", { class: "small" }, h("b", null, tr(x[0]) + ": "), x[1]) : null; }),
        h("div", null, [["Demo", p.demo_url], ["Code", p.repo_url], ["Document", p.doc_url]].map(function (x) { return x[1] ? h("a", { href: x[1], target: "_blank", rel: "noopener noreferrer", style: "margin-right:12px" }, x[0]) : null; })), M.fileLinks(p.files),
        h("div", { class: "chips" }, p.skills.map(function (s) { return chip(s); })), note, err,
        h("div", { class: "btns" }, btn("Mark Verified", function () { decide("VERIFIED"); }, "p"), btn("Request revision", function () { decide("NEEDS_REVISION"); })));
    }) : h("div", { class: "card note" }, "Nothing waiting. Great!"));
  }); });
  T("#/internship", function () {
    var q = h("input", { type: "search", placeholder: "Search student or company" }), box = h("div");
    function load() { api("/api/teacher/internship?q=" + encodeURIComponent(q.value)).then(function (d) { box.textContent = ""; box.appendChild(M.table(["Student", "Class", "Choice 1", "Choice 2", "Choice 3", "Purpose (choice 1)", "Friends"], d.items.map(function (s) { return [s.name, s.class_name || "—", s.choices[0] || chip("Not chosen yet"), s.choices[1] || "—", s.choices[2] || "—", s.purposes[0] || "—", s.friends.length ? s.friends.join(", ") : "—"]; }))); }).catch(M.fail); }
    q.addEventListener("input", function () { clearTimeout(q._t); q._t = setTimeout(load, 250); }); load();
    return stack(M.pageHead("Internship choices", "Read only · companies chosen by students"), M.field("Search", q), box, h("div", { class: "small muted" }, "The company list itself is managed by the admin."));
  });
  var PROJ = { SUBMITTED: "Waiting for review", NEEDS_REVISION: "Needs revision", VERIFIED: "Verified" };
  var ROLE = { student: "Students", teacher: "Teachers", alumni: "Alumni", admin: "Admins" };
  function keyed(list, names) { return list.map(function (x) { return { label: tr(names ? names[x.key] : x.key), value: x.value }; }); }
  function readiness(list, head) { return M.barChart(list.map(function (c) { return { label: c.label, value: c.avg_readiness, note: tr("{0} students", c.students) }; }), { unit: "%", max: 100, vertical: true, labelHead: head, valueHead: "Average readiness" }); }
  T("#/analytics", function () { return api("/api/teacher/analytics").then(function (d) {
    return stack(M.pageHead("Analytics", tr("{0} students. Hover or tap a bar to see the details.", d.total)),
      h("div", { class: "grid charts2" },
        card("Average career readiness per class", readiness(d.by_class, "Class")),
        card("Average career readiness per major", readiness(d.by_major, "Major")),
        card("Student status", M.barChart(keyed(d.status), { vertical: true, labelHead: "Status", valueHead: "Students" })),
        card("Project status", M.barChart(keyed(d.projects, PROJ), { vertical: true, labelHead: "Status", valueHead: "Projects" }))),
      card("Target careers chosen by students", M.barChart(d.careers, { labelHead: "Career", valueHead: "Students" })));
  }); });

  /* ================= ADMIN ================= */
  A("#/dashboard", function () { return api("/api/admin/summary").then(function (d) {
    return stack(M.pageHead("Admin dashboard"), h("div", { class: "grid g3" }, stat("Users", d.users), stat("Students", d.students), stat("Internship companies", d.companies), stat("Careers", d.careers), stat("Projects to review", d.projects_pending), stat("Students with internship choices", d.students_with_choices)),
      card("Shortcuts", h("div", { class: "btns" }, btn("Users", function () { M.go("#/users"); }), btn("Internship Companies", function () { M.go("#/companies"); }), btn("Career Data", function () { M.go("#/careers"); }), btn("Analytics", function () { M.go("#/analytics"); }))));
  }); });
  A("#/users", function () {
    var role = "", box = h("div"), err = M.errBox(), f = { name: h("input"), email: h("input", { type: "email" }), role: M.select(["teacher", "student", "admin", "alumni"]), pw: h("input", { type: "password", autocomplete: "new-password" }), major: M.select([["", "—"], "TKJ", "AK"]), cls: h("input") };
    /* Reset password: tampilkan password sementara satu kali supaya admin bisa membacakannya
       ke pemilik akun. Setelah kotak ini ditutup, password itu tidak bisa dilihat lagi. */
    function resetPassword(u) {
      if (!window.confirm(tr("Create a new temporary password for {0} ({1})?\n\nThe old password stops working immediately and all their devices will be signed out.", u.name, u.email))) return;
      api("/api/admin/users/" + u.id + "/reset-password", "POST").then(function (r) {
        var pw = h("code", { class: "temp-pw" }, r.temp_password);
        var salin = btn("Copy", function () {
          var ok = function () { M.toast("Temporary password copied"); };
          if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(r.temp_password).then(ok, function () { M.toast("Copy it manually from the screen"); });
          else { var s = document.createSelection ? null : window.getSelection(); if (s) { var rg = document.createRange(); rg.selectNodeContents(pw); s.removeAllRanges(); s.addRange(rg); } M.toast("Press Ctrl+C to copy"); }
        }, "s");
        M.modal(tr("Temporary password for {0}", r.name),
          h("p", { class: "muted small", style: "margin:0" }, tr("Read it out or send it to {0}. This password is shown only once.", r.email)),
          h("div", { class: "pw-box" }, pw, salin),
          h("p", { class: "muted small", style: "margin:0" }, "When they sign in, they will be asked to create a new password of their own."));
        load();
      }).catch(M.fail);
    }
    function load() { api("/api/admin/users" + (role ? "?role=" + role : "")).then(function (d) { box.textContent = "";
      box.appendChild(M.table(["Name", "Email", "Role", "Major", "Status", ""], d.items.map(function (u) { return [u.name, u.email, u.role, majorChip(u.major), chip(u.active ? "Active" : "Inactive", u.active ? "good" : "bad"),
        h("div", { class: "btns" },
          btn(u.active ? "Deactivate" : "Activate", function () { api("/api/admin/users/" + u.id, "PATCH", { active: !u.active }).then(function () { M.toast("Updated"); load(); }).catch(M.fail); }, "s"),
          btn("Reset password", function () { resetPassword(u); }, "s"))]; }))); }).catch(M.fail); }
    load();
    return stack(M.pageHead("Users"), M.tabs(["All", "Students", "Teachers", "Alumni", "Admins"], 0, function (i) { role = ["", "student", "teacher", "alumni", "admin"][i]; var tb = document.querySelector(".tabs"); Array.prototype.forEach.call(tb.children, function (b, j) { b.className = j === i ? "on" : ""; }); load(); }),
      h("div", { class: "grid g21" }, card("User list", box), card("Create user", M.field("Name", f.name), M.field("Email", f.email), M.field("Role", f.role), M.field("Temporary password (min. 8)", f.pw), h("div", { class: "grid g2" }, M.field("Major (students)", f.major), M.field("Class (students)", f.cls)), err,
        h("div", null, btn("Save", function () { err.classList.add("hide"); api("/api/admin/users", "POST", { name: f.name.value, email: f.email.value.trim().toLowerCase(), role: f.role.value, password: f.pw.value, major: f.major.value, class_name: f.cls.value }).then(function () { M.toast("User created"); f.name.value = f.email.value = f.pw.value = ""; load(); }).catch(function (x) { M.showErr(err, x.message); }); }, "p")))));
  });
  A("#/skills", function () { return api("/api/admin/skills").then(function (d) {
    var name = h("input"), cat = M.select(["technical", "soft"]), err = M.errBox(), editId = null, title = h("h3", null, "Add skill");
    function reset() { editId = null; name.value = ""; title.textContent = "Add skill"; }
    return stack(M.pageHead("Skills"), h("div", { class: "grid g12" }, card("Skill list", M.table(["Skill", "Category", ""], d.items.map(function (s) { return [s.name, s.category, h("div", { class: "btns" }, btn("Edit", function () { editId = s.id; name.value = s.name; cat.value = s.category; title.textContent = "Edit skill"; }, "s"),
        btn("Delete", function () { if (confirm(tr("Delete {0}?", s.name))) api("/api/admin/skills/" + s.id, "DELETE").then(function () { M.route(); }).catch(M.fail); }, "g s"))]; }))),
      card(null, title, M.field("Name", name), M.field("Category", cat), err, h("div", { class: "btns" }, btn("Save", function () { err.classList.add("hide"); var body = { name: name.value, category: cat.value };
        (editId ? api("/api/admin/skills/" + editId, "PUT", body) : api("/api/admin/skills", "POST", body)).then(function () { M.toast("Saved"); M.route(); }).catch(function (x) { M.showErr(err, x.message); }); }, "p"), btn("Clear", reset, "g")))));
  }); });
  A("#/careers", function () { return Promise.all([api("/api/admin/careers"), api("/api/admin/skills")]).then(function (r) {
    var careers = r[0].items, skills = r[1].items, editId = null, err = M.errBox(), title = h("h3", null, "Add career"), pick = {};
    var f = {}; ["name", "category", "major"].forEach(function (k) { f[k] = h("input"); }); ["description", "responsibilities", "education_path", "example_projects", "growth"].forEach(function (k) { f[k] = h("textarea", { style: "min-height:56px" }); });
    f.interest = h("input", { placeholder: "technology, data" }); f.strength = h("input", { placeholder: "logical, analytical" }); var skillBox = h("div", { class: "grid g2" });
    function drawSkills() { skillBox.textContent = ""; skills.forEach(function (s) { var on = pick[s.id] !== undefined; var imp = M.select([[1, "Low"], [2, "Medium"], [3, "High"]], pick[s.id] || 2); imp.addEventListener("change", function () { pick[s.id] = Number(imp.value); });
      skillBox.appendChild(h("div", { class: "btns", style: "flex-wrap:nowrap" }, h("label", { style: "flex:1" }, h("input", { type: "checkbox", style: "width:auto;margin-right:6px", checked: on, onchange: function (e) { if (e.target.checked) pick[s.id] = Number(imp.value); else delete pick[s.id]; } }), s.name), h("div", { style: "width:100px" }, imp))); }); } drawSkills();
    function fill(c) { editId = c ? c.id : null; title.textContent = c ? "Edit career" : "Add career"; f.name.value = c ? c.name : ""; f.category.value = c ? c.category : ""; f.major.value = c ? c.majors : ""; f.interest.value = c ? c.interest_tags : ""; f.strength.value = c ? c.strength_tags : "";
      ["description", "responsibilities", "education_path", "example_projects", "growth"].forEach(function (k) { f[k].value = c ? c[k] : ""; }); pick = {}; if (c) c.skills.forEach(function (s) { pick[s.skill_id] = s.importance; }); drawSkills(); }
    function save() { err.classList.add("hide"); var body = { name: f.name.value, category: f.category.value, majors: f.major.value, interest_tags: f.interest.value, strength_tags: f.strength.value, skills: Object.keys(pick).map(function (k) { return { skill_id: Number(k), importance: pick[k] }; }) };
      ["description", "responsibilities", "education_path", "example_projects", "growth"].forEach(function (k) { body[k] = f[k].value; });
      (editId ? api("/api/admin/careers/" + editId, "PUT", body) : api("/api/admin/careers", "POST", body)).then(function () { M.toast("Career saved"); M.route(); }).catch(function (x) { M.showErr(err, x.message); }); }
    return stack(M.pageHead("Career Data", "Careers drive the recommendation engine. Tags: interests (technology, finance, business, design, data, people), strengths (analytical, problem_solving, detail, logical, communication, creativity, collaboration, technical)."),
      h("div", { class: "grid g12" }, card("Career list", M.table(["Career", "Category", "Skills", ""], careers.map(function (c) { return [c.name, c.category, String(c.skills.length), h("div", { class: "btns" }, btn("Edit", function () { fill(c); window.scrollTo(0, document.body.scrollHeight); }, "s"),
        btn("Delete", function () { if (confirm(tr("Delete {0}?", c.name))) api("/api/admin/careers/" + c.id, "DELETE").then(function () { M.route(); }).catch(M.fail); }, "g s"))]; }))),
        card(null, title, M.field("Name", f.name), M.field("Category", f.category), M.field("Description", f.description), M.field("Responsibilities", f.responsibilities), M.field("Education path", f.education_path), M.field("Example projects", f.example_projects), M.field("Career growth", f.growth),
          h("div", { class: "grid g2" }, M.field("Interest tags", f.interest), M.field("Strength tags", f.strength)), M.field("Majors (AK, TKJ)", f.major), h("b", null, "Required skills"), skillBox, err,
          h("div", { class: "btns" }, btn("Save", save, "p"), btn("New career", function () { fill(null); }, "g")))));
  }); });
  A("#/companies", function () { return api("/api/companies").then(function (d) {
    var q = h("input", { type: "search", placeholder: "Search company" }), box = h("div"), editId = null, title = h("h3", null, "Add company"), name = h("input"), addr = h("textarea", { style: "min-height:56px" }), num = h("input", { type: "number", min: 1 }), secEn = h("input"), secId = h("input"), abEn = h("textarea", { style: "min-height:56px" }), abId = h("textarea", { style: "min-height:56px" }), src = h("input"), ver = h("input", { type: "checkbox" }), err = M.errBox(), imp = h("textarea", { placeholder: "One company per line:\n7;PT Contoh Jaya;Jl. Sudirman 1, Pekanbaru\n8;Bank Contoh" }), impErr = M.errBox();
    function draw() { var ql = q.value.toLowerCase(); var rows = d.items.filter(function (c) { return !ql || c.name.toLowerCase().indexOf(ql) > -1; }); box.textContent = "";
      box.appendChild(M.table(["No", "Company", "Address", ""], rows.map(function (c) { return [String(c.number || ""), c.name, c.address || "—", h("div", { class: "btns" }, btn("Edit", function () { editId = c.id; title.textContent = "Edit company"; name.value = c.name; addr.value = c.address; num.value = c.number || ""; secEn.value = c.sector_en; secId.value = c.sector_id; abEn.value = c.about_en; abId.value = c.about_id; src.value = c.source; ver.checked = c.verified; }, "s"),
        btn("Delete", function () { if (confirm(tr("Delete {0}? Student choices for it will be removed.", c.name))) api("/api/admin/companies/" + c.id, "DELETE").then(function () { M.route(); }).catch(M.fail); }, "g s"))]; }))); }
    q.addEventListener("input", draw); draw();
    return stack(M.pageHead("Internship Companies", "The DU/DI list students choose from"), h("div", { class: "grid g12" }, card(tr("Company list ({0})", d.total), q, box),
      h("div", { class: "grid" }, card(null, title, M.field("Company name", name), M.field("Address", addr), M.field("Number (optional)", num), h("div", { class: "grid g2" }, M.field("Sector (English)", secEn), M.field("Sector (Indonesian)", secId)), M.field("What students do here (English)", abEn), M.field("What students do here (Indonesian)", abId), M.field("Source of information (website)", src), h("label", { class: "small" }, ver, " ", tr("Information is verified")), err, h("div", { class: "btns" }, btn("Save and show to students", function () { err.classList.add("hide"); var body = { name: name.value, address: addr.value, number: num.value ? Number(num.value) : null, sector: secEn.value, sector_id: secId.value, about: abEn.value, about_id: abId.value, source: src.value, verified: ver.checked };
        (editId ? api("/api/admin/companies/" + editId, "PUT", body) : api("/api/admin/companies", "POST", body)).then(function () { M.toast("Saved"); M.route(); }).catch(function (x) { M.showErr(err, x.message); }); }, "p"), btn("Clear", function () { editId = null; name.value = addr.value = num.value = secEn.value = secId.value = abEn.value = abId.value = src.value = ""; ver.checked = false; title.textContent = "Add company"; }, "g"))),
        card("Import list", h("span", { class: "small muted" }, "Paste many companies at once. Format: number;name;address (address is optional). Existing names are skipped."), imp, impErr,
          h("div", null, btn("Import list", function () { impErr.classList.add("hide"); api("/api/admin/companies/import", "POST", { text: imp.value }).then(function (r) { M.toast(tr("{0} added, {1} skipped", r.added, r.skipped)); M.route(); }).catch(function (x) { M.showErr(impErr, x.message); }); }))))));
  }); });
  A("#/analytics", function () { return Promise.all([api("/api/admin/analytics"), api("/api/admin/audit")]).then(function (r) {
    var d = r[0], s = d.summary;
    return stack(M.pageHead("Analytics"), h("div", { class: "grid g3" }, stat("Users", s.users), stat("Students took assessment", s.assessments), stat("Active career plans", s.plans), stat("Verified projects", s.projects_verified), stat("Students with internship choices", s.students_with_choices), stat("Projects to review", s.projects_pending)),
      h("div", { class: "grid charts2" },
        card("Active users per role", M.barChart(keyed(d.users_by_role, ROLE), { vertical: true, labelHead: "Role", valueHead: "Users" })),
        card("Students per major", M.barChart(d.students_by_major, { vertical: true, labelHead: "Major", valueHead: "Students" })),
        card("Project status", M.barChart(keyed(d.projects, PROJ), { vertical: true, labelHead: "Status", valueHead: "Projects" })),
        card("Students with internship choices", M.barChart([{ label: tr("Already chose"), value: d.summary.students_with_choices }, { label: tr("Not yet"), value: Math.max(0, d.summary.students - d.summary.students_with_choices) }], { vertical: true, labelHead: "Status", valueHead: "Students" }))),
      card("Popular target careers", M.barChart(d.popular_careers, { labelHead: "Career", valueHead: "Students" })),
      card("Most chosen first-choice companies", M.barChart(d.first_choice_companies, { labelHead: "Company", valueHead: "Students" })),
      card("Audit log (latest 100 admin actions)", M.table(["When", "Who", "Action", "Detail"], r[1].items.map(function (a) { return [a.created_at, a.actor || "—", a.action, a.detail]; }))));
  }); });
})();
