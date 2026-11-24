/* Alumni: tulis cerita, profil; admin: moderasi; siswa: baca (lihat student.js untuk daftar baca). */
(function () {
  var h = M.h, api = M.api, btn = M.btn, chip = M.chip, card = M.card, tr = I18N.tr;
  var AL = function (p, f) { M.view("alumni", p, f); }, AD = function (p, f) { M.view("admin", p, f); };
  function stack() { return h("div", { class: "grid" }, Array.prototype.slice.call(arguments)); }
  var KIND = { CAREER_STORY: "Career story", EDUCATION: "Education", TIPS: "Tips" };
  var STATUS = { DRAFT: ["Draft", ""], PENDING: ["Waiting for admin", ""], PUBLISHED: ["Published", "good"], REJECTED: ["Needs changes", ""] };
  var TEMPLATE = "Background:\n\nEducation:\n\nFirst work experience:\n\nImportant skills:\n\nChallenges:\n\nCareer journey:\n\nLessons:\n\nAdvice for students:\n";

  AL("#/dashboard", function () { return Promise.all([api("/api/alumni/content"), api("/api/alumni/profile")]).then(function (r) {
    var d = r[0], prof = r[1], n = function (k) { return d.counts[k] || 0; };
    var need = !prof.job_title && !prof.workplace;
    return stack(M.pageHead("Alumni", "Share what you learned so students can learn from you", [btn("Write a story", function () { M.go("#/write"); }, "p")]),
      need ? h("div", { class: "card note" }, h("b", null, "Add your job and workplace"), h("div", { class: "small" }, "Students see them next to your story. It makes your advice easier to trust."), h("div", null, btn("Open my profile", function () { M.go("#/my-profile"); }, "s"))) : null,
      h("div", { class: "grid g4" }, card("Draft", h("div", { class: "big" }, String(n("DRAFT")))), card("Waiting for admin", h("div", { class: "big" }, String(n("PENDING")))), card("Published", h("div", { class: "big" }, String(n("PUBLISHED")))), card("Needs changes", h("div", { class: "big" }, String(n("REJECTED"))))),
      card("My stories", d.items.length ? d.items.map(function (x) { var st = STATUS[x.status];
        return h("div", { class: "card soft" }, h("div", { class: "head-row" }, h("b", null, x.title), chip(st[0], st[1])), h("div", { class: "small muted" }, KIND[x.kind] + (x.category ? " · " + x.category : "")),
          x.status === "REJECTED" && x.moderation_note ? h("div", { class: "err" }, tr("Admin note: {0}", x.moderation_note)) : null,
          h("div", { class: "btns" }, x.status === "DRAFT" || x.status === "REJECTED" ? btn("Edit", function () { M.go("#/write/" + x.id); }, "s") : null,
            x.status !== "PUBLISHED" ? btn("Delete", function () { if (window.confirm(tr("Delete this story?"))) api("/api/alumni/content/" + x.id, "DELETE").then(function () { M.route(); }).catch(M.fail); }, "g s") : null)); })
        : h("div", { class: "empty" }, h("b", null, "No stories yet"), h("div", { class: "small muted" }, "Start with something small: how you chose your major, or one tip you wish you knew in grade 11."))));
  }); });

  function writer(m) { var editId = m[1] ? Number(m[1]) : null;
    return Promise.all([api("/api/careers"), editId ? api("/api/alumni/content") : Promise.resolve(null)]).then(function (r) {
      var careers = r[0].items, cur = editId ? r[1].items.filter(function (x) { return x.id === editId; })[0] : null;
      if (editId && (!cur || (cur.status !== "DRAFT" && cur.status !== "REJECTED"))) return h("div", { class: "card note" }, "This story cannot be edited now.");
      var err = M.errBox(), kind = M.select([["CAREER_STORY", tr("Career story")], ["EDUCATION", tr("Education")], ["TIPS", tr("Tips")]], cur ? cur.kind : "CAREER_STORY"),
        title = h("input", { maxlength: 120, placeholder: "Example: From SMK TKJ to network engineer" }), cat = h("input", { maxlength: 40, placeholder: "Example: Networking" }),
        body = h("textarea", { maxlength: 5000, style: "min-height:260px", placeholder: "Write in your own words. At least 40 characters." }),
        career = M.select([["", tr("Not linked to a career")]].concat(careers.map(function (c) { return [String(c.id), c.name]; })), cur && cur.career_id ? String(cur.career_id) : "");
      if (cur) { title.value = cur.title; cat.value = cur.category; body.value = cur.body; }
      function send(submit) { err.classList.add("hide");
        var b = { kind: kind.value, title: title.value, category: cat.value, body: body.value, career_id: career.value ? Number(career.value) : null, submit: submit };
        (editId ? api("/api/alumni/content/" + editId, "PUT", b) : api("/api/alumni/content", "POST", b)).then(function () { M.toast(submit ? "Sent to the admin" : "Draft saved"); M.go("#/dashboard"); }).catch(function (x) { M.showErr(err, x.message); }); }
      return stack(M.pageHead(editId ? "Edit story" : "Write a story", "The admin reads it first. Once it is published, students can read it."),
        h("div", { class: "card" }, M.field("Type", kind), M.field("Title", title), M.field("Topic", cat), M.field("Related career (optional)", career), M.field("Your story", body),
          h("div", null, btn("Use the story outline", function () { if (!body.value.trim() || window.confirm(tr("Replace what you wrote with the outline?"))) body.value = TEMPLATE; }, "g s")),
          h("div", { class: "small muted" }, "Do not write private data such as phone numbers, addresses or other people's names."), err,
          h("div", { class: "btns" }, btn("Save draft", function () { send(false); }, "g"), btn("Send to admin", function () { send(true); }, "p"))));
    }); }
  AL("#/write", writer); AL("#/write/(\\d+)", writer);

  AL("#/my-profile", function () { return api("/api/alumni/profile").then(function (p) {
    var err = M.errBox(), year = h("input", { type: "number", min: 1990, max: 2100, value: p.graduation_year || "" }), major = M.select([["", tr("Not set")], ["TKJ", "TKJ"], ["AK", "AK"]], p.major),
      work = h("input", { maxlength: 100, value: p.workplace }), job = h("input", { maxlength: 100, value: p.job_title }), bio = h("textarea", { maxlength: 500 }); bio.value = p.bio;
    return stack(M.pageHead("My profile", "Shown next to your published stories"), h("div", { class: "card", style: "max-width:640px" },
      M.field("Graduation year", year), M.field("Major", major), M.field("Job title", job), M.field("Workplace", work), M.field("Short bio", bio), err,
      h("div", null, btn("Save profile", function () { err.classList.add("hide");
        api("/api/alumni/profile", "PUT", { graduation_year: year.value ? Number(year.value) : null, major: major.value, workplace: work.value, job_title: job.value, bio: bio.value }).then(function () { M.toast("Saved"); }).catch(function (x) { M.showErr(err, x.message); }); }, "p"))));
  }); });

  AD("#/moderation", function () { var tab = 0, st = ["PENDING", "PUBLISHED", "REJECTED"], box = h("div", { class: "grid" });
    function load() { api("/api/admin/content?status=" + st[tab]).then(function (d) { box.textContent = "";
      if (!d.items.length) return box.appendChild(h("div", { class: "card note" }, tab === 0 ? "Nothing waiting. Great!" : "Nothing here."));
      d.items.forEach(function (x) { var note = h("textarea", { maxlength: 500, placeholder: "Note for the author (required when you reject)" }), err = M.errBox();
        function decide(v) { err.classList.add("hide"); api("/api/admin/content/" + x.id + "/moderate", "POST", { decision: v, note: note.value }).then(function () { M.toast(v === "PUBLISHED" ? "Published" : "Sent back to the author"); load(); }).catch(function (e) { M.showErr(err, e.message); }); }
        box.appendChild(card(x.title, h("div", { class: "small muted" }, KIND[x.kind] + " · " + x.author + (x.job_title ? " · " + x.job_title : "") + (x.workplace ? " @ " + x.workplace : "")),
          h("div", { class: "story-body" }, x.body), x.moderation_note ? h("div", { class: "small muted" }, tr("Admin note: {0}", x.moderation_note)) : null, note, err,
          h("div", { class: "btns" }, x.status !== "PUBLISHED" ? btn("Publish", function () { decide("PUBLISHED"); }, "p") : null, x.status !== "REJECTED" ? btn(x.status === "PUBLISHED" ? "Unpublish" : "Send back", function () { decide("REJECTED"); }, "g") : null))); }); }).catch(M.fail); }
    load(); return stack(M.pageHead("Alumni content", "Read each story before students can see it. Check for private data and respectful words."), M.tabs(["Waiting", "Published", "Sent back"], 0, function (i) { tab = i; load(); }), box); });
})();
