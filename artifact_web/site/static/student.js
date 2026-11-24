var tr = I18N.tr;
/* Student views */
(function () {
  var h = M.h, api = M.api, btn = M.btn, chip = M.chip, card = M.card, V = function (p, f) { M.view("student", p, f); };
  var scaleLabels = ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"];
  function pretty(t) { return t.replace(/_/g, " ").replace(/^./, function (c) { return c.toUpperCase(); }); }
  function stack() { return h("div", { class: "grid" }, Array.prototype.slice.call(arguments)); }

  /* ---------- dashboard ---------- */
  V("#/dashboard", function () { return api("/api/student/dashboard").then(function (d) {
    var ch = [1, 2, 3].map(function (r) { var c = d.internship.filter(function (x) { return x.rank === r; })[0]; return [String(r), c ? c.name : "—", c ? chip("Saved", "good") : chip("Empty")]; });
    var task = d.today_task;
    return stack(
      M.pageHead(tr("Good morning, {0}", d.name.split(" ")[0]), d.target ? tr("Target: {0} · One step today", d.target) : tr("You have no target career yet · Start with Self Discovery")),
      !d.has_assessment ? h("div", { class: "card note" }, h("b", null, "Start here: "), "Take the Self Discovery assessment so we can suggest careers that fit you.", h("div", null, btn("Start Self Discovery", function () { M.go("#/discovery"); }, "p"))) : null,
      h("div", { class: "grid g3" },
        h("section", { class: "card hero" }, h("div", { class: "eyebrow" }, "Today task"),
          task ? [h("div", { class: "hero-t" }, task.title), h("span", { class: "hero-s" }, task.description), h("div", null, btn("Start task", function () { M.go("#/learning"); }, "w"))]
               : [h("div", { class: "hero-t" }, d.target ? "All tasks are done. Submit a project as evidence." : "Choose a target in Career Plan to get daily tasks."), h("div", null, btn("Open Career Plan", function () { M.go("#/plan"); }, "w"))]),
        card("Career readiness", h("div", { class: "big" }, d.readiness + "%"), M.bar(d.readiness)),
        card("Current milestone", h("span", null, d.milestone.total ? tr("{0} of {1} tasks done", d.milestone.done, d.milestone.total) : "No plan yet"), M.bar(d.milestone.total ? Math.round(100 * d.milestone.done / d.milestone.total) : 0))),
      h("div", { class: "grid g21" },
        card("My internship choices", M.table(["No", "Company", "Status"], ch), h("div", null, btn("Choose / edit", function () { M.go("#/internship"); }))),
        h("div", { class: "stack-col" },
          h("section", { class: "card ai" }, h("div", { class: "eyebrow ai-e" }, "AI recommendation"), d.recommendation ? [h("b", null, d.recommendation.name + " · " + d.recommendation.match + "%"), h("span", { class: "muted small" }, d.recommendation.reasons[0]), h("div", null, btn("See reasons", function () { M.go("#/plan"); }, "s"))] : h("span", { class: "muted" }, "Complete Self Discovery to see recommendations.")),
          card("Notifications", d.notifications.length ? h("ul", { class: "list" }, d.notifications.map(function (n) { return h("li", null, h("span", { class: n.read ? "muted" : "" }, n.text), " ", h("span", { class: "muted small" }, M.date(n.created_at))); })) : h("span", { class: "muted" }, "Nothing new."),
            d.notifications.length ? h("div", null, btn("Mark all as read", function () { api("/api/notifications/read", "POST").then(function () { M.route(); }); }, "s")) : null))));
  }); });

  /* ---------- self discovery ---------- */
  function insightView(i) {
    return stack(
      M.pageHead("Career Insight", "Several possible careers and the reasons. This is not a final decision.", [btn("Back", function () { M.back("#/dashboard"); }, "g"), btn(i.saved ? "Saved" : "Save", function (e) { api("/api/student/insight/save", "POST").then(function () { M.toast("Saved to your profile"); e.target.textContent = "Saved"; }).catch(M.fail); }, "p")]),
      h("div", { class: "grid g2" }, card("Interests", h("div", { class: "chips" }, (i.interest_labels || i.interests).map(function (t) { return chip(pretty(t), "on"); }))), card("Strengths", h("div", { class: "chips" }, (i.strength_labels || i.strengths).map(function (t) { return chip(pretty(t), "on"); })))),
      h("div", { class: "grid g3" }, i.careers.map(function (c, n) { return card(tr("Career {0}: {1}", n + 1, c.name), h("div", null, chip(tr("{0}% match", c.match))), h("ul", { class: "list small" }, c.reasons.map(function (r) { return h("li", null, r); })),
        h("div", { class: "btns" }, btn("Details", function () { M.go("#/career/" + c.career_id); }, "s"), btn("Make it my target", function () { M.go("#/plan/preview/" + c.career_id); }, "s"))); })),
      h("div", null, btn("Retake assessment", function () { M.go("#/discovery?retake=1"); })));
  }
  V("#/discovery", function (m, hash) {
    var retake = hash.indexOf("retake=1") > -1;
    return Promise.all([api("/api/student/insight").catch(function () { return null; }), api("/api/student/questions")]).then(function (r) {
      if (r[0] && !retake) return insightView(r[0]);
      var q = r[1], answers = {}, chosen = {}; (q.my_skills || []).forEach(function (s) { chosen[s] = true; });
      var err = M.errBox();
      function group(kind, title) { return card(title, q.questions.filter(function (x) { return x.kind === kind; }).map(function (x) {
        return h("div", { class: "q" }, h("div", null, x.text), h("div", { class: "scale", role: "radiogroup", "aria-label": x.text }, [1, 2, 3, 4, 5].map(function (v) {
          return h("label", null, h("input", { type: "radio", name: "q" + x.id, onchange: function () { answers[x.id] = v; } }), String(v) + " · " + tr(scaleLabels[v - 1])); }))); })); }
      var skillBox = card("Skills you already have (be honest, a teacher can verify later)", h("div", { class: "chips" }, q.skills.map(function (s) {
        return h("label", { class: "chip", style: "cursor:pointer" }, h("input", { type: "checkbox", style: "width:auto;margin-right:6px", checked: chosen[s.id], onchange: function (e) { chosen[s.id] = e.target.checked; } }), s.name); })));
      return stack(M.pageHead("Self Discovery", "Answer each part. Your result is a suggestion, not a final decision."), group("interest", "Your interests"), group("strength", "Your strengths"), skillBox, err,
        h("div", null, btn("Submit, AI builds Career Insight", function (e) { err.classList.add("hide");
          var total = q.questions.length, got = Object.keys(answers).length; if (got < total) return M.showErr(err, tr("Please answer all questions ({0}/{1}).", got, total));
          e.target.disabled = true; api("/api/student/assessment", "POST", { answers: answers, skill_ids: Object.keys(chosen).filter(function (k) { return chosen[k]; }).map(Number) }).then(function () { M.toast("Your Career Insight is ready"); M.go("#/discovery"); }).catch(function (x) { e.target.disabled = false; M.showErr(err, x.message); }); }, "p")));
    }); });

  /* ---------- explore ---------- */
  V("#/explore", function () {
    var picked = {}, cat = "", sel = null, total = 0;
    var q = h("input", { type: "search", placeholder: "Search careers or skills, e.g. tax, networking, Python", "aria-label": tr("Search career") });
    var chipsBox = h("div", { class: "chips fchips" }), list = h("div", { class: "ccards" }), count = h("div", { class: "muted small" }), side = h("aside", { class: "card cside" });
    var cmp = btn(tr("Compare ({0})", 0), function () { M.go("#/compare?ids=" + Object.keys(picked).join(",")); }, "", { disabled: true });
    function majorText(m) { return m.length >= 2 ? tr("All majors") : m.join(" & "); }
    function badges(c, big) { return h("span", { class: "chips" }, c.trend ? h("span", { class: "tag hot" }, "Global trend") : null, c.is_new ? h("span", { class: "tag fresh" }, "New") : null); }
    function drawSide() {
      side.textContent = ""; if (!sel) { side.appendChild(h("div", { class: "muted" }, "Pick a career on the left to see details.")); return; }
      api("/api/careers/" + sel.id).then(function (c) {
        side.textContent = "";
        side.appendChild(h("div", null, h("div", { class: "muted small" }, tr(c.category) + " · " + tr("Suitable for {0}", majorText(sel.majors))), h("h2", null, c.name)));
        if (sel.trend || sel.is_new) side.appendChild(badges(sel, true));
        side.appendChild(h("p", { class: "soft-t" }, c.description));
        side.appendChild(h("div", null, h("h3", null, "Skills needed"), h("div", { class: "chips" }, c.skills.map(function (s) { return h("span", { class: "chip ak" }, s.name); }))));
        side.appendChild(h("div", null, h("h3", null, "First step for grades 10 to 12"), h("p", { class: "soft-t" }, c.example_projects)));
        side.appendChild(h("div", { class: "card ai" }, h("h3", null, "Career path"), h("div", { class: "small" }, c.growth), h("div", { class: "small muted" }, "Descriptions are general; ask your teacher to check them.")));
        side.appendChild(h("div", { class: "btns" }, btn("Make it my target", function () { M.go("#/plan/preview/" + c.id); }, "p"), btn(sel.saved ? "Remove from shortlist" : "Save to shortlist", function () { api("/api/student/shortlist/" + c.id, sel.saved ? "DELETE" : "POST").then(function () { sel.saved = !sel.saved; M.toast(sel.saved ? "Added to shortlist" : "Removed from shortlist"); load(); drawSide(); }).catch(M.fail); }),
          btn("Details", function () { M.go("#/career/" + c.id); }, "g")));
      }).catch(M.fail);
    }
    function load() { api("/api/careers?q=" + encodeURIComponent(q.value) + "&category=" + encodeURIComponent(cat)).then(function (d) {
      total = d.total; chipsBox.textContent = "";
      [["", tr("All fields") + " · " + d.total]].concat(d.categories.map(function (k) { return [k, tr(k) + " · " + d.counts[k]]; })).forEach(function (k) {
        chipsBox.appendChild(h("button", { type: "button", class: "fchip" + (cat === k[0] ? " on" : ""), "aria-pressed": cat === k[0] ? "true" : "false", onclick: function () { cat = k[0]; load(); } }, k[1])); });
      count.textContent = tr("Showing {0} of {1} careers", d.items.length, d.total);
      list.textContent = ""; if (!d.items.length) list.appendChild(h("div", { class: "muted" }, "No careers match your search."));
      d.items.forEach(function (c) {
        if (sel && sel.id === c.id) sel = c;
        list.appendChild(h("div", { class: "ccard" + (sel && sel.id === c.id ? " on" : "") },
          h("button", { type: "button", class: "cbody", onclick: function () { sel = c; load(); drawSide(); } },
            h("span", { class: "muted small" }, tr(c.category) + " · " + majorText(c.majors)), h("b", null, c.name), h("span", { class: "muted small" }, c.skills.join(", ")), badges(c)),
          h("label", { class: "small cmpl" }, h("input", { type: "checkbox", style: "width:auto", checked: !!picked[c.id], onchange: function (e) { if (e.target.checked) { if (Object.keys(picked).length >= 3) { e.target.checked = false; return M.toast("You can compare up to 3 careers"); } picked[c.id] = 1; } else delete picked[c.id];
            var n = Object.keys(picked).length; cmp.textContent = tr("Compare ({0})", n); cmp.disabled = n < 2; } }), "Compare"))); });
    }).catch(M.fail); }
    q.addEventListener("input", function () { clearTimeout(q._t); q._t = setTimeout(load, 250); }); load(); drawSide();
    return stack(M.pageHead("Explore careers", "Search, compare up to 3, save to your shortlist", [cmp]), M.field("Search", q), chipsBox,
      h("div", { class: "explore" }, h("section", { class: "elist" }, count, list), side));
  });
  V("#/career/(\\d+)", function (m) { return api("/api/careers/" + m[1]).then(function (c) {
    return stack(M.pageHead(c.name, c.category, [btn("Back", function () { M.back("#/explore"); }, "g"), btn("Make it my target", function () { M.go("#/plan/preview/" + c.id); }, "p")]),
      card("Overview", h("p", null, c.description), h("b", null, "What you do"), h("p", null, c.responsibilities)),
      h("div", { class: "grid g2" }, card("Required skills", M.table(["Skill", "Importance", "Your evidence"], c.skills.map(function (s) { return [s.name, "★".repeat(s.importance), s.level ? chip(s.level, "good") : chip("Not yet")]; }))),
        card("Education path", h("p", null, c.education_path), h("b", null, "Example project"), h("p", null, c.example_projects), h("b", null, "Career growth"), h("p", null, c.growth))));
  }); });
  V("#/compare", function (m, hash) { var ids = (hash.split("ids=")[1] || "").split(",").map(Number).filter(Boolean);
    return api("/api/student/compare", "POST", { ids: ids }).then(function (d) {
      var rows = [["Required skills", function (c) { return c.skills.join(", "); }], ["Education path", function (c) { return c.education_path; }], ["Example project", function (c) { return c.example_projects; }], ["Career growth", function (c) { return c.growth; }]];
      return stack(M.pageHead("Career comparison", null, [btn("Back", function () { M.back("#/explore"); }, "g")]), M.table([""].concat(d.items.map(function (c) { return c.name; })), rows.map(function (r) { return [h("b", null, r[0])].concat(d.items.map(r[1])); })),
        h("div", { class: "btns" }, d.items.map(function (c) { return btn(tr("Save {0}", c.name), function () { api("/api/student/shortlist/" + c.id, "POST").then(function () { M.toast("Added to shortlist"); }).catch(M.fail); }); })));
    }).catch(function () { return stack(M.pageHead("Career comparison"), h("div", { class: "card note" }, "Pick 2 or 3 careers in Explore first."), h("div", null, btn("Go to Explore", function () { M.go("#/explore"); }))); }); });

  /* ---------- career plan ---------- */
  function planBody(d) {
    return [h("div", { class: "grid g2" }, card("Current skills", d.current_skills.length ? h("div", { class: "chips" }, d.current_skills.map(function (s) { return chip(s.name + " · " + s.level, "good"); })) : h("span", { class: "muted" }, "None yet")),
      card("Skill gap", h("div", { class: "chips" }, d.skill_gap.length ? d.skill_gap.map(function (s) { return chip(s.name, "warn"); }) : [chip("No gap, great!", "good")]))),
      card("Roadmap and milestones", h("div", { class: "grid g2" }, (d.milestones || []).map(function (ms) { return h("div", { class: "card soft" }, h("b", null, "M" + ms.milestone + ": " + ms.skill), h("ul", { class: "list small" }, ms.tasks.map(function (t) { return h("li", null, t.title, h("span", { class: "muted" }, " · " + t.est_hours + "h")); }))); })))];
  }
  V("#/plan", function () { return api("/api/student/plan").then(function (d) {
    if (!d.plan) return chooseView();
    return stack(M.pageHead(tr("Plan: {0}", d.plan.career), "Why this career: see below", [btn("Change target", function () { M.go("#/plan/choose"); }, "g"), btn("Learning", function () { M.go("#/learning"); }, "p")]),
      card("Why you got this recommendation", h("ul", { class: "list small" }, d.plan.reasons.map(function (r) { return h("li", null, r); }))),
      planBody(d), h("div", { class: "grid g2" }, card("Target project", h("p", null, d.plan.example_projects || "—")), card("Teacher guidance", h("p", null, d.plan.teacher_note || "No guidance yet. Your teacher can add notes here."))));
  }); });
  V("#/plan/choose", function () { return chooseView(); });
  function chooseView() { return api("/api/student/recommendations").then(function (d) {
    return stack(M.pageHead("Career Plan", "Choose a target career. You can change it any time.", [btn("Back", function () { M.back("#/plan"); }, "g")]),
      h("div", { class: "grid g3" }, d.items.map(function (c, n) { return card(tr("Career {0}: {1}", n + 1, c.name), h("div", null, chip(tr("{0}% match", c.match))), h("ul", { class: "list small" }, c.reasons.map(function (r) { return h("li", null, r); })),
        h("div", { class: "btns" }, btn("Details", function () { M.go("#/career/" + c.career_id); }, "s"), btn("Set as target", function () { M.go("#/plan/preview/" + c.career_id); }, "p", { class: "btn p s" }))); })));
  }).catch(function () { return stack(M.pageHead("Career Plan"), h("div", { class: "card note" }, "Take Self Discovery first so the AI can suggest careers."), h("div", null, btn("Start Self Discovery", function () { M.go("#/discovery"); }, "p"))); }); }
  V("#/plan/preview/(\\d+)", function (m) { return api("/api/student/plan/preview/" + m[1]).then(function (d) {
    return stack(M.pageHead(tr("Plan: {0}", d.career.name), "Preview. Nothing is saved until you press Save.", [btn("Change target", function () { M.go("#/plan/choose"); }, "g"), btn("Save Career Plan", function (e) { e.target.disabled = true; api("/api/student/plan", "POST", { career_id: d.career.id }).then(function () { M.toast("Career Plan saved"); M.go("#/plan"); }).catch(function (x) { e.target.disabled = false; M.fail(x); }); }, "p")]),
      planBody(d), card("Example project", h("p", null, d.career.example_projects)),
      h("div", { class: "card note" }, "Do you agree with this plan? Save it to start, or change the target. Your teacher can add guidance after you save."));
  }); });

  /* ---------- learning ---------- */
  V("#/learning", function () { return api("/api/student/plan").then(function (d) {
    if (!d.plan) return stack(M.pageHead("Learning"), h("div", { class: "card note" }, "Choose a target career first. Your learning tasks come from your Career Plan."), h("div", null, btn("Open Career Plan", function () { M.go("#/plan"); }, "p")));
    var total = 0, done = 0; d.milestones.forEach(function (ms) { ms.tasks.forEach(function (t) { total++; if (t.status === "COMPLETED") done++; }); });
    var pct = total ? Math.round(100 * done / total) : 0;
    var how = h("div", { class: "card soft" }, h("h3", null, "How learning works"), h("ol", { class: "small" },
      h("li", null, "Open a lesson and read its steps."), h("li", null, "Study: tick each step after you did it."), h("li", null, "Practice: do the exercise, then take the short quiz. You need 70% to pass."),
      h("li", null, "Apply: build a small project that uses the skill and submit it under Projects."), h("li", null, "When the lesson says Ready, press Mark as done.")));
    return M.courseCard().then(function (cc) { return stack(M.pageHead("Learning", tr("Target: {0} · {1} of {2} tasks done", d.plan.career, done, total)), M.bar(pct), cc, how,
      d.milestones.map(function (ms) { return card(tr("Milestone {0}: {1}", ms.milestone, ms.skill), ms.tasks.map(function (t) {
        return h("div", { class: "task " + (t.status === "COMPLETED" ? "done" : "") }, h("div", null, h("div", { class: "t" }, t.title), h("div", { class: "small muted" }, t.description + " · " + t.difficulty + " · " + t.est_hours + "h"), M.statusChip(t.status)),
          h("div", { class: "btns" }, btn(t.status === "COMPLETED" ? "Review lesson" : (t.status === "NOT_STARTED" ? "Start lesson" : "Continue lesson"), function () { M.go("#/learn/" + t.id); }, t.status === "COMPLETED" ? "g s" : "p s"),
            t.kind === "APPLY" && t.status !== "COMPLETED" ? btn("Submit project", function () { M.go("#/projects"); }, "s") : null)); })); })); });
  }); });
  /* Halaman pelajaran. Semua perubahan (centang langkah, kuis, status siap) diperbarui DI TEMPAT:
     tidak memanggil M.route(), jadi layar tidak berkedip dan posisi scroll tidak melompat ke atas. */
  V("#/learn/(\\d+)", function (m) { var tid = m[1]; return api("/api/student/learn/" + tid).then(function (d) {
    var kindHelp = { STUDY: "Read each step, do it, then tick it.", PRACTICE: d.has_quiz ? "Do the exercise below, then answer the quiz." : "Do the exercise below, then press Mark as done.",
      APPLY: "Build a small project that uses this skill, then submit it under Projects." };
    var err = M.errBox(), statusSlot = h("div"), quizSlot = h("div");
    function fresh() { return api("/api/student/learn/" + tid); }
    var lastKey = null;
    function drawStatus() { var key = d.status + "|" + (d.ready ? 1 : 0) + "|" + (d.ready ? "" : (d.blocked_reason || "")); if (key === lastKey) return; lastKey = key; statusSlot.textContent = "";
      if (d.status === "COMPLETED") return statusSlot.appendChild(h("div", { class: "card good" }, "This task is completed."));
      if (d.ready) { var fin = btn("Mark as done", function () { fin.disabled = true; err.classList.add("hide");
          api("/api/student/tasks/" + d.id, "PATCH", { status: "COMPLETED" }).then(function (r) { M.toast(tr("Readiness: {0}%", r.readiness)); M.go("#/learning"); })
            .catch(function (x) { fin.disabled = false; M.showErr(err, x.message); }); }, "p");
        return statusSlot.appendChild(h("div", { class: "card good" }, h("b", null, "Ready!"), h("div", null, fin))); }
      statusSlot.appendChild(h("div", { class: "card note" }, h("b", null, "Not ready yet"), h("div", { class: "small" }, tr(d.blocked_reason)))); }

    var steps, busy = false;
    if (d.kind === "STUDY") {
      var count = h("div", { class: "small muted" });
      function drawCount() { count.textContent = tr("{0} of {1} steps done", d.steps.filter(function (x) { return x.done; }).length, d.steps.length); }
      steps = card("Steps", count, d.steps.map(function (st, i) { var cb = h("input", { type: "checkbox" }); cb.checked = st.done; cb.disabled = d.status === "COMPLETED";
        cb.addEventListener("change", function () { var want = cb.checked; err.classList.add("hide"); if (busy) { cb.checked = !want; return; } busy = true;
          api("/api/student/learn/" + tid + "/step", "POST", { idx: i, done: want }).then(function (r) { busy = false; d = r; cb.checked = r.steps[i].done; cb.disabled = r.status === "COMPLETED"; drawCount(); drawStatus(); })
            .catch(function (x) { busy = false; cb.checked = !want; M.showErr(err, x.message); }); });
        return h("label", { class: "step" }, cb, " ", h("span", null, st.text)); }));
      drawCount();
    } else steps = card("Read first", h("ul", { class: "small" }, d.steps.map(function (st) { return h("li", null, st.text); })));

    var practice = d.kind === "PRACTICE" ? card("Practice", h("p", null, d.practice)) : (d.kind === "APPLY" ? card("Your mini project", h("p", null, d.practice), h("div", { class: "small muted" }, "Tip: write the problem, what you built, and the result. Add a link or a file as evidence."), h("div", null, btn("Go to Projects", function () { M.go("#/projects"); }, "p"))) : null);

    function drawQuiz() { quizSlot.textContent = "";
      if (!(d.kind === "PRACTICE" && d.has_quiz)) return;
      var answers = d.quiz.map(function () { return -1; }), resultBox = h("div"), qerr = M.errBox(), qs = h("div");
      d.quiz.forEach(function (q, qi) { var opts = h("div", { class: "opts" });
        q.options.forEach(function (o, oi) { var r = h("input", { type: "radio", name: "q" + tid + "_" + d.attempts + "_" + qi }); r.addEventListener("change", function () { answers[qi] = oi; }); opts.appendChild(h("label", { class: "opt" }, r, " ", h("span", null, o))); });
        qs.appendChild(h("div", { class: "qbox" }, h("b", null, (qi + 1) + ". " + q.q), opts)); });
      var check = btn("Check my answers", function () { qerr.classList.add("hide"); if (answers.some(function (a) { return a < 0; })) return M.showErr(qerr, "Answer every question");
        check.disabled = true;
        api("/api/student/learn/" + tid + "/quiz", "POST", { answers: answers }).then(function (r) { resultBox.textContent = ""; check.classList.add("hide");
          qs.querySelectorAll("input").forEach(function (x) { x.disabled = true; });
          var box = h("div", { class: "card " + (r.passed ? "good" : "note") }, h("b", null, tr("Score: {0}/{1} ({2}%)", r.score, r.total, r.percent)),
            h("div", null, r.passed ? "Passed! You can mark this task as done." : "Not yet. Read the steps again, then try again."),
            r.results.length ? h("ol", { class: "small" }, r.results.map(function (x) { return h("li", null, x.correct ? "Correct. " : "Wrong. ", x.why); })) : null);
          if (!r.passed) { var again = btn("Try again", function () { again.disabled = true; fresh().then(function (n) { d = n; drawQuiz(); drawStatus(); quizSlot.scrollIntoView({ block: "start", behavior: "smooth" }); })
              .catch(function (x) { again.disabled = false; M.showErr(qerr, x.message); }); }, "p");
            M.countdown(again, r.wait || 0, "Try again"); box.appendChild(h("div", null, again)); }
          resultBox.appendChild(box);
          if (r.passed) fresh().then(function (n) { d = n; drawStatus(); });
        }).catch(function (x) { check.disabled = false; M.showErr(qerr, x.message); }); }, "p");
      if (d.wait > 0) M.countdown(check, d.wait, "Check my answers");
      quizSlot.appendChild(card(tr("Quiz (pass at {0}%)", d.pass_percent), d.best !== null ? h("div", { class: "small muted" }, tr("Attempts: {0} · Best score: {1}%", d.attempts, d.best)) : null,
        d.passed ? h("div", { class: "small" }, chip("Passed", "good")) : null, qs, qerr, h("div", null, check), resultBox)); }

    drawQuiz(); drawStatus();
    return stack(M.pageHead(d.title, tr("{0} · {1} · about {2}h", d.skill, d.difficulty, d.est_hours)), h("div", { class: "card soft" }, h("b", null, "Goal"), h("p", null, d.goal), h("div", { class: "small muted" }, kindHelp[d.kind] || "")),
      steps, practice, quizSlot, err, statusSlot, h("div", null, btn("Back to Learning", function () { M.go("#/learning"); }, "g s")));
  }); });

  /* ---------- projects ---------- */
  V("#/projects", function () { return Promise.all([api("/api/student/projects"), api("/api/student/questions"), api("/api/student/plan")]).then(function (r) {
    var list = r[0].items, skills = r[1].skills, plan = r[2].plan, editing = null, err = M.errBox();
    var title = h("input", { maxlength: 120, placeholder: "Example: Office network design" }), desc = h("textarea", { maxlength: 2000, placeholder: "One or two sentences: what is this project?" }), picked = {},
      problem = h("textarea", { maxlength: 600, placeholder: "What problem did you want to solve?" }), solution = h("textarea", { maxlength: 600, placeholder: "What did you build or do?" }), result = h("textarea", { maxlength: 600, placeholder: "What was the result? Numbers help." }),
      tech = h("input", { maxlength: 200, placeholder: "Example: Mikrotik, Packet Tracer, Python" }), demo = h("input", { type: "url", placeholder: "https://... (demo or video)" }), repo = h("input", { type: "url", placeholder: "https://github.com/..." }), docu = h("input", { type: "url", placeholder: "https://... (report or document)" }),
      link = h("input", { type: "url", placeholder: "https://... (any other link)" }), fp = M.filePicker();
    var formTitle = h("h3", null, "New project"), submit = btn("Save and send to teacher", save, "p");
    function save() { err.classList.add("hide"); submit.disabled = true; var file = fp.files && fp.files[0];
      var body = { title: title.value, description: desc.value, link: link.value, skill_ids: Object.keys(picked).filter(function (k) { return picked[k]; }).map(Number), problem: problem.value, solution: solution.value, result: result.value, technology: tech.value, demo_url: demo.value, repo_url: repo.value, doc_url: docu.value };
      (editing ? api("/api/student/projects/" + editing, "PUT", body) : api("/api/student/projects", "POST", body))
        .then(function (p) { return file ? M.uploadFile("project", p.id, file) : null; }).then(function () { M.toast("Sent to your teacher"); M.route(); }).catch(function (x) { submit.disabled = false; M.showErr(err, x.message); }); }
    function edit(p) { editing = p.id; title.value = p.title; desc.value = p.description; link.value = p.link; problem.value = p.problem; solution.value = p.solution; result.value = p.result; tech.value = p.technology; demo.value = p.demo_url; repo.value = p.repo_url; docu.value = p.doc_url;
      picked = {}; JSON.parse(p.skill_ids).forEach(function (i) { picked[i] = true; });
      formTitle.textContent = "Revise project"; submit.textContent = "Resubmit to teacher"; drawSkills(); window.scrollTo(0, document.body.scrollHeight); }
    var skillBox = h("div", { class: "chips skillbox" }), skillQ = h("input", { type: "search", placeholder: "Search skills" });
    skillQ.addEventListener("input", function () { drawSkills(); });
    function drawSkills() { var ql = (skillQ.value || "").toLowerCase(); skillBox.textContent = ""; skills.forEach(function (s) { if (ql && s.name.toLowerCase().indexOf(ql) < 0 && !picked[s.id]) return; skillBox.appendChild(h("label", { class: "chip", style: "cursor:pointer" }, h("input", { type: "checkbox", style: "width:auto;margin-right:6px", checked: !!picked[s.id], onchange: function (e) { picked[s.id] = e.target.checked; } }), s.name)); }); } drawSkills();
    function line(label, text) { return text ? h("div", { class: "small" }, h("b", null, tr(label) + ": "), text) : null; }
    function linkOf(label, u) { return u ? h("a", { href: u, target: "_blank", rel: "noopener noreferrer", style: "margin-right:12px" }, label) : null; }
    function projectCard(p) { var add = M.filePicker(); add.classList.add("hide");
      add.addEventListener("change", function () { if (add.files[0]) M.uploadFile("project", p.id, add.files[0]).then(function () { M.toast("File added"); M.route(); }).catch(M.fail); });
      return h("div", { class: "card soft" }, h("div", { class: "head-row" }, h("b", null, p.title), M.statusChip(p.status)),
        p.description ? h("span", { class: "small" }, p.description) : null, line("Problem", p.problem), line("Solution", p.solution), line("Result", p.result), line("Technology", p.technology),
        h("div", null, linkOf("Open link", p.link), linkOf("Demo", p.demo_url), linkOf("Code", p.repo_url), linkOf("Document", p.doc_url)),
        M.fileLinks(p.files, function (f) { api("/api/student/uploads/" + f.id, "DELETE").then(function () { M.route(); }).catch(M.fail); }),
        h("div", { class: "chips" }, p.skills.map(function (s) { return chip(s); })), p.teacher_note ? h("div", { class: "err" }, tr("Teacher: {0}", p.teacher_note)) : null,
        h("div", { class: "btns" }, p.files.length < 3 ? btn("Add file", function () { add.click(); }, "g s") : null, add, p.status === "NEEDS_REVISION" ? btn("Revise in form", function () { edit(p); }, "s p") : null)); }
    var idea = plan && plan.example_projects ? h("div", { class: "card note small" }, h("b", null, "Idea for your career plan"), h("div", null, plan.example_projects), btn("Use this idea", function () { desc.value = plan.example_projects; title.focus(); }, "g s")) : null;
    return stack(M.pageHead("Projects", "Projects are your evidence. A teacher verifies them."),
      h("div", { class: "grid g12" }, card("My projects", list.length ? list.map(projectCard) : h("span", { class: "muted" }, "No projects yet. Finish an Apply task in Learning, then submit your work here.")),
        card(null, formTitle, idea,
          h("div", { class: "pstep" }, h("span", { class: "pn" }, "1"), h("div", { class: "grow" }, h("b", null, "Name your project"), M.field("Title", title), M.field("Description", desc))),
          h("div", { class: "pstep" }, h("span", { class: "pn" }, "2"), h("div", { class: "grow" }, h("b", null, "Tell the story"), M.field("Problem", problem), M.field("Solution", solution), M.field("Result", result))),
          h("div", { class: "pstep" }, h("span", { class: "pn" }, "3"), h("div", { class: "grow" }, h("b", null, "Tools and skills"), M.field("Technology", tech), h("div", { class: "small muted" }, "Skills used"), skillQ, skillBox)),
          h("div", { class: "pstep" }, h("span", { class: "pn" }, "4"), h("div", { class: "grow" }, h("b", null, "Add proof"), M.field("Photo, screenshot or report (PDF, PNG or JPG, max 3 MB)", fp), M.field("Demo link", demo), M.field("Code link", repo), M.field("Document link", docu), M.field("Other link", link))),
          err, submit)));
  }); });
  V("#/portfolio", function () { return Promise.all([api("/api/student/portfolio"), M.portfolioExtras()]).then(function (r) { var d = r[0], more = r[1];
    return stack(M.pageHead("Portfolio", d.name + (d.profile.class_name ? " · " + d.profile.class_name : "") + (d.target ? " · " + tr("Target: {0}", d.target) : ""), [btn("Career Outcome", function () { M.go("#/outcome"); }, "p")]),
      h("div", { class: "grid g12" }, card("Verified projects", d.projects.length ? d.projects.map(function (p) { return h("div", { class: "card soft" }, h("b", null, p.title), h("span", { class: "small" }, p.description), h("div", { class: "chips" }, p.skills.map(function (s) { return chip(s); }))); }) : h("span", { class: "muted" }, tr("No verified projects yet. ") + (d.pending_projects ? tr("{0} waiting for review or revision.", d.pending_projects) : ""))),
        card("Skills and evidence level", M.table(["Skill", "Evidence"], d.skills.map(function (s) { return [s.name, chip(s.evidence, s.level === 4 ? "good" : "")]; })))),
      M.coursesCard(d.courses),
      more,
      h("div", { class: "card note small" }, "A skill only counts as strong when it has project evidence and teacher verification. Claiming a skill is the first step, not the last."));
  }); });
  V("#/outcome", function () { return api("/api/student/outcome").then(function (d) {
    return stack(M.pageHead("Career Outcome", "What your projects and evidence changed", [btn("Update Career Plan", function () { M.go("#/plan"); }, "p")]),
      h("div", { class: "grid g3" }, card("Career readiness", h("div", { class: "big" }, d.before + "% → " + d.now + "%"), M.bar(d.now)), card("New verified skills", d.verified_skills.length ? h("div", { class: "chips" }, d.verified_skills.map(function (s) { return chip(s, "good"); })) : h("span", { class: "muted" }, "None yet")),
        card("Suggested next step", h("span", null, d.next_task || (d.has_plan ? "Submit a project as evidence." : "Choose a target career.")))));
  }); });

  /* ---------- internship ---------- */
  V("#/internship", function () { return Promise.all([api("/api/student/internship"), api("/api/companies")]).then(function (r) {
    var mine = r[0], all = r[1].items, slots = [null, null, null], purposes = ["", "", ""], byId = {}, friends = mine.friends.map(function (f) { return { name: f.name, class_name: f.class_name }; }), open = {};
    all.forEach(function (c) { byId[c.id] = c; });
    mine.choices.forEach(function (c) { slots[c.rank - 1] = byId[c.company_id] || { id: c.company_id, name: c.name }; purposes[c.rank - 1] = c.purpose || ""; });
    var q = h("input", { type: "search", placeholder: "Company name" }), loc = h("input", { type: "search", placeholder: "Location / address" }), list = h("div", { class: "stack-col intern-list" }), side = h("div", { class: "stack-col intern-side" }), cls = h("input", { value: mine.class_name, maxlength: 20 }), err = M.errBox();
    function save() { err.classList.add("hide"); var ids = [], pur = [];
      slots.forEach(function (s, i) { if (s) { ids.push(s.id); pur.push(purposes[i]); } });
      if (!slots[0]) return M.showErr(err, "Choice 1 is required.");
      var fr = friends.filter(function (f) { return f.name.trim(); });
      api("/api/student/internship", "PUT", { class_name: cls.value, company_ids: ids, purposes: pur, friends: fr }).then(function (d) { mine = d; M.toast("Choices saved"); drawSide(); }).catch(function (x) { M.showErr(err, x.message); }); }
    function drawSide() { side.textContent = "";
      var mineCard = h("div", { class: "card" }, h("h3", null, "My choices"), M.field("Full name", h("input", { value: mine.full_name, disabled: true })), M.field("Class", cls));
      slots.forEach(function (s, i) { var ta = h("textarea", { maxlength: 500, style: "min-height:64px", placeholder: "Why do you want to intern here? What do you want to learn or achieve?" }); ta.value = purposes[i]; ta.addEventListener("input", function () { purposes[i] = ta.value; });
        mineCard.appendChild(h("div", { class: "field" }, h("label", null, tr("Choice {0}", i + 1) + (i === 0 ? tr(" (required)") : tr(" (backup)"))),
          h("div", { class: "btns" }, h("input", { value: s ? s.name : "", placeholder: "Pick from the list", disabled: true, style: "flex:1" }), s ? btn("Remove", function () { slots[i] = null; purposes[i] = ""; drawSide(); drawList(); }, "g s") : null),
          s ? h("div", null, h("label", { class: "small muted" }, "My purpose for this place"), ta) : null)); });
      var fc = h("div", { class: "card" }, h("h3", null, "Invite friends"), h("div", { class: "small muted" }, "Want to intern together? Add up to 3 friends. Your teacher will see this."));
      friends.forEach(function (f, i) { var n = h("input", { value: f.name, maxlength: 80, placeholder: "Friend's full name" }), k = h("input", { value: f.class_name, maxlength: 20, placeholder: "Class, e.g. XI TKJ" });
        n.addEventListener("input", function () { f.name = n.value; }); k.addEventListener("input", function () { f.class_name = k.value; });
        fc.appendChild(h("div", { class: "field" }, h("label", null, tr("Friend {0}", i + 1)), n, h("label", { class: "small muted" }, "Friend's class"), k, btn("Remove", function () { friends.splice(i, 1); drawSide(); }, "g s"))); });
      if (friends.length < 3) fc.appendChild(btn("Add a friend", function () { friends.push({ name: "", class_name: "" }); drawSide(); }, "s"));
      side.appendChild(propCard); side.appendChild(mineCard); side.appendChild(fc); side.appendChild(err); side.appendChild(btn("Save choices", save, "p"));
      side.appendChild(h("div", { class: "small muted" }, "Maximum 3 choices. Status: ", chip(mine.choices.length ? "Saved" : "Not chosen", mine.choices.length ? "good" : ""))); }
    function drawList() { var ql = q.value.toLowerCase(), ll = loc.value.toLowerCase(); list.textContent = "";
      var rows = all.filter(function (c) { return (!ql || c.name.toLowerCase().indexOf(ql) > -1) && (!ll || (c.address || "").toLowerCase().indexOf(ll) > -1); });
      rows.forEach(function (c) { var used = slots.some(function (s) { return s && s.id === c.id; }), det = h("div", { class: open[c.id] ? "" : "hide" });
        function row(label, v) { if (v) det.appendChild(h("p", { class: "small" }, h("b", null, tr(label) + ": "), v)); }
        function lk(href, text) { return /^https?:\/\//.test(href || "") ? h("a", { class: "btn s g", href: href, target: "_blank", rel: "noopener noreferrer" }, text) : null; }
        if (c.about) det.appendChild(h("p", null, c.about));
        row("Phone", c.phone); row("Daily tasks", c.tasks); row("Accepted majors", c.majors); row("Hours, dress code, allowance", c.work_terms);
        if (c.status === "rejected") det.appendChild(h("p", { class: "small" }, h("b", null, tr("Reason it was not approved") + ": "), c.review_note || "—"));
        else if (c.verified) det.appendChild(h("div", { class: "small muted" }, tr("Source: {0}", c.source)));
        else if (c.status === "approved") { det.appendChild(h("p", { class: "small" }, "No verified information yet. Ask your teacher or visit the place. Questions to ask:"));
          var ul = h("ul", { class: "small" }); r[1].checklist.forEach(function (x) { ul.appendChild(h("li", null, x)); }); det.appendChild(ul); }
        else det.appendChild(h("div", { class: "small muted" }, "Your teacher is checking this place. You can already choose it."));
        if (c.mine && c.status !== "approved") det.appendChild(h("div", null, btn("Delete my submission", function () {
          api("/api/student/companies/" + c.id, "DELETE").then(function () { M.toast("Submission deleted"); M.route(); }).catch(M.fail); }, "g s")));
        var st = c.status === "pending" ? chip("Waiting for teacher", "warn") : c.status === "rejected" ? chip("Not approved", "bad") : chip(c.verified ? "Verified info" : "Not verified yet", c.verified ? "good" : "");
        var cluster = h("div", { class: "btns", style: "flex:1 1 220px" }, btn(open[c.id] ? "Hide details" : "Details", function () { open[c.id] = !open[c.id]; drawList(); }, "s"),
          lk(c.website, "Website"), lk(c.instagram ? c.instagram_url : c.ig_search_url, c.instagram ? "Instagram" : "Find on Instagram"), lk(c.google_url, "Search Google"), lk(c.maps_url, "Open in Maps"));
        list.appendChild(h("div", { class: "card" },
          h("div", { class: "btns", style: "justify-content:space-between" }, h("b", null, ((c.number ? c.number + ". " : "") + c.name)), st),
          h("div", { class: "small" }, c.sector ? (c.sector + (c.sector_guess ? " (" + tr("guessed from the name") + ")" : "")) : tr("Sector unknown")),
          h("div", { class: "small muted" }, c.address ? (c.address) : tr("Address not verified yet")),
          h("div", { class: "btns", style: "flex-wrap:nowrap;align-items:flex-start" }, cluster,
            btn(used ? "Added" : "Add", function () { var i = slots.indexOf(null); if (i < 0) return M.toast("You already have 3 choices. Remove one first."); slots[i] = c; drawSide(); drawList(); }, "p s", { disabled: used || c.status === "rejected" })), det)); });
      list.appendChild(h("div", { class: "small muted" }, tr("Showing {0} of {1}", rows.length, r[1].total) + " · " + tr("{0} with verified info", r[1].verified))); }
    q.addEventListener("input", drawList); loc.addEventListener("input", drawList); drawList();
    var propCard = (function () { var f = {}, er = M.errBox();
      function inp(k, label, ph, max, area) { var el = area ? h("textarea", { maxlength: max, style: "min-height:72px", placeholder: ph }) : h("input", { maxlength: max, placeholder: ph }); f[k] = el; return M.field(label, el); }
      var NEED = [["name", 3, "Company name"], ["address", 10, "Full address"], ["sector", 3, "Type of business"], ["about", 40, "Description"], ["tasks", 10, "Daily tasks"], ["source", 5, "How you know this place"]];
      function submit(e) { er.classList.add("hide"); var body = {}; Object.keys(f).forEach(function (k) { body[k] = f[k].value.trim(); });
        for (var i = 0; i < NEED.length; i++) { var n = NEED[i]; if (body[n[0]].length < n[1]) { f[n[0]].focus(); return M.showErr(er, tr("{0}: write at least {1} characters.", tr(n[2]), n[1])); } }
        if (!body.phone && !body.website && !body.instagram) { f.phone.focus(); return M.showErr(er, "Add at least one of phone, website or Instagram so your teacher can check this place."); }
        e.target.disabled = true;
        api("/api/student/companies", "POST", body).then(function () { Object.keys(f).forEach(function (k) { f[k].value = ""; }); M.toast("Submitted. Your teacher will review it."); M.route(); })
          .catch(function (x) { e.target.disabled = false; M.showErr(er, x.message); }); }
      return h("div", { class: "card", id: "add-place" }, h("h3", null, "Add my own internship place"),
        h("div", { class: "small muted" }, "Fill in what you know. Your teacher checks it before it counts as verified. You can choose it for your internship while you wait."),
        h("h4", null, "About the place"),
        inp("name", "Company name *", "Name of the company or shop", 120), inp("address", "Full address *", "Street, number, area, city", 300), inp("sector", "Type of business *", "e.g. Computer shop, hotel, tax consulting", 80),
        inp("about", "Description: what does this place do? (at least 40 characters) *", "Products or services, size, who the customers are", 800, true),
        h("h4", null, "About the internship"),
        inp("tasks", "What would an intern do each day? *", "Tasks you expect or were told about", 500, true),
        inp("majors", "Accepted majors (optional)", "e.g. TKJ, AK", 200), inp("work_terms", "Hours, dress code, allowance (optional)", "e.g. 08.00-16.00, uniform, no allowance", 300),
        h("h4", null, "Contact"),
        inp("phone", "Phone / WhatsApp", "08xxxxxxxxxx", 30), inp("website", "Website", "www.example.com", 200), inp("instagram", "Instagram", "@account or link", 200),
        h("div", { class: "small muted" }, "Add at least one of phone, website or Instagram so your teacher can check this place."),
        inp("source", "How do you know this place? Who did you talk to? *", "e.g. I visited and spoke with Mr. Budi (HRD)", 200),
        h("div", { class: "small muted" }, "* required"), er,
        h("div", null, btn("Submit for teacher review", submit, "p"))); })();
    drawSide();
    function openForm() { propCard.scrollIntoView({ behavior: "smooth", block: "start" }); var first = propCard.querySelector("input"); if (first) setTimeout(function () { first.focus({ preventScroll: true }); }, 400); }
    return stack(M.pageHead("Internship", "Pick up to 3 places, say why, and invite friends"), h("div", { class: "grid g12" }, card(tr("Company list ({0})", r[1].total), h("div", { class: "btns", style: "justify-content:flex-end" }, btn("Add my own internship place", openForm, "p s")), h("div", { class: "grid g2" }, M.field("Search", q), M.field("Location", loc)), list), side));
  }); });

  /* ---------- alumni stories ---------- */
  V("#/alumni", function () { var kind = "", q = h("input", { type: "search", placeholder: "Search stories, topics or people" }), box = h("div", { class: "grid" }), open = {};
    var KIND = { "": "All", CAREER_STORY: "Career story", EDUCATION: "Education", TIPS: "Tips" }, chips = h("div", { class: "chips" });
    function load() { api("/api/alumni-stories?kind=" + kind + "&q=" + encodeURIComponent(q.value)).then(function (d) { box.textContent = "";
      if (!d.items.length) return box.appendChild(h("div", { class: "empty" }, h("b", null, "No stories yet"), h("div", { class: "small muted" }, "Alumni are writing. Check again soon.")));
      d.items.forEach(function (x) { var full = !!open[x.id], who = [x.author, x.job_title, x.workplace].filter(Boolean).join(" · ");
        box.appendChild(h("div", { class: "card" }, h("div", { class: "head-row" }, h("b", null, x.title), chip(KIND[x.kind])), h("div", { class: "small muted" }, who + (x.graduation_year ? " · " + tr("Class of {0}", x.graduation_year) : "")),
          h("div", { class: "story-body" }, full ? x.body : x.excerpt), x.body.length > x.excerpt.length ? btn(full ? "Show less" : "Read the full story", function () { open[x.id] = !open[x.id]; load(); }, "g s") : null)); }); }).catch(M.fail); }
    function drawChips() { chips.textContent = ""; Object.keys(KIND).forEach(function (k) { chips.appendChild(h("button", { type: "button", class: "fchip" + (kind === k ? " on" : ""), onclick: function () { kind = k; drawChips(); load(); } }, KIND[k])); }); }
    var t; q.addEventListener("input", function () { clearTimeout(t); t = setTimeout(load, 250); }); drawChips(); load();
    return stack(M.pageHead("Alumni Stories", "Learn from people who walked the path before you"), h("div", { class: "card" }, M.field("Search", q), chips), box); });

  /* ---------- AI assistant ---------- */
  V("#/assistant", function () {
    var chat = h("div", { class: "chat", "aria-live": "polite" }), input = h("input", { placeholder: "Ask about your careers, skills, progress or internship", maxlength: 500 });
    chat.appendChild(h("div", { class: "msg" }, "Hi! I explain my reasons and you make the decisions. Try: \"Why this career?\", \"What is my skill gap?\" or \"What should I do next?\""));
    function send() { var t = input.value.trim(); if (t.length < 2) return; input.value = ""; chat.appendChild(h("div", { class: "msg me" }, t)); chat.scrollTop = chat.scrollHeight;
      api("/api/student/assistant", "POST", { question: t }).then(function (r) { var m = h("div", { class: "msg" }, h("div", null, r.answer), r.reasons.length ? h("ul", { class: "small" }, r.reasons.map(function (x) { return h("li", null, x); })) : null, r.next_action ? h("div", { class: "small muted" }, tr("Next: {0}", r.next_action)) : null); chat.appendChild(m); chat.scrollTop = chat.scrollHeight; }).catch(M.fail); }
    input.addEventListener("keydown", function (e) { if (e.key === "Enter") send(); });
    return stack(M.pageHead("AI Metta", "Answers come with reasons. The decision stays yours."), chat, h("div", { class: "btns", style: "flex-wrap:nowrap" }, h("div", { style: "flex:1" }, input), btn("Send", send, "p")));
  });
})();
