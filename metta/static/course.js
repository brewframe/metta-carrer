/* Kursus karier: 6 bab per karier. Isi bab (Bahasa Indonesia) selalu ditampilkan lewat textContent, tidak pernah sebagai HTML. */
var tr = I18N.tr;
(function () {
  var h = M.h, api = M.api, btn = M.btn, chip = M.chip, card = M.card;
  var V = function (p, f) { M.view("student", p, f); };
  function stack() { return h("div", { class: "grid" }, Array.prototype.slice.call(arguments)); }
  function paras(t) { return String(t).split(/\n\s*\n/).map(function (p) { return h("p", { class: "cbody" }, p); }); }

  /* Kartu ringkas untuk halaman Learning dan Dashboard. */
  M.courseCard = function () {
    return api("/api/student/course").then(function (d) {
      if (!d.available) return null;
      var pct = Math.round(100 * d.done / d.total);
      return card(tr("Career course: {0}", d.career), M.bar(pct), h("div", { class: "small muted" }, tr("{0} of {1} chapters done", d.done, d.total)),
        h("div", null, btn(d.done >= d.total ? "Review the course" : (d.done ? "Continue the course" : "Start the course"), function () { M.go("#/course"); }, "p")));
    }).catch(function () { return null; });
  };

  /* Kursus yang sudah selesai, untuk portfolio (siswa dan halaman publik). */
  M.coursesCard = function (rows) {
    if (!rows || !rows.length) return null;
    return card("Completed career courses", h("ul", { class: "list small" }, rows.map(function (r) {
      return h("li", null, h("b", null, r.career), h("span", { class: "muted" }, " · " + [r.completed_on, r.exam_percent !== null ? tr("Final exam: {0}%", r.exam_percent) : ""].filter(Boolean).join(" · ")), " ", chip("Teacher verified project", "good")); })));
  };

  V("#/course", function () { return api("/api/student/course").then(function (d) {
    if (!d.available) return stack(M.pageHead("Career course"), h("div", { class: "card note" }, d.reason === "no_plan" ? "Choose a target career first. The course follows your Career Plan." : "The course for this career is being prepared."),
      h("div", null, btn("Open Career Plan", function () { M.go("#/plan"); }, "p")));
    var next = d.chapters.filter(function (c) { return !c.done && !c.locked; })[0];
    return stack(M.pageHead(tr("Career course: {0}", d.career), tr("{0} of {1} chapters done", d.done, d.total)), M.bar(Math.round(100 * d.done / d.total)),
      h("div", { class: "card soft" }, h("h3", null, "How the course works"), h("ol", { class: "small" },
        h("li", null, "Chapter 1 is reading only: goals and core material."),
        h("li", null, tr("Chapters 2 to 5: do the practice, then take a quiz. You need {0} of {1} correct.", d.pass_chapter, d.quiz_n)),
        h("li", null, tr("Chapter 6: build a project that your teacher verifies, then pass the final exam ({0} of {1} correct).", d.pass_final, d.final_n)),
        h("li", null, "Questions are drawn at random each time. If you fail, read the chapter again and try once more."),
        h("li", null, "The course material is written in Indonesian.")),
      ),
      d.chapters.map(function (c) {
        var st = c.done ? chip("Done", "good") : (c.locked ? chip("Locked") : chip("Open", "warn"));
        return h("div", { class: "card soft" }, h("div", { class: "head-row" }, h("b", null, tr("Chapter {0}", c.n) + ": " + tr(c.title)), st),
          h("div", { class: "btns" }, c.locked ? null : btn(c.done ? "Review chapter" : (next && next.n === c.n ? "Start chapter" : "Open chapter"), function () { M.go("#/course/" + c.n); }, c.done ? "g s" : "p s")));
      }));
  }); });

  function quizBox(n, d) {
    var box = h("div"), err = M.errBox();
    function render(q) {
      var answers = q.questions.map(function () { return -1; }); box.textContent = "";
      var qs = h("div");
      q.questions.forEach(function (it, qi) { var opts = h("div", { class: "opts" });
        it.options.forEach(function (o, oi) { var r = h("input", { type: "radio", name: "cq" + qi }); r.addEventListener("change", function () { answers[qi] = oi; });
          opts.appendChild(h("label", { class: "opt" }, r, " ", h("span", { lang: "id" }, o))); });
        qs.appendChild(h("div", { class: "qbox" }, h("div", { class: "small muted" }, tr("Question {0} · level {1}", qi + 1, it.level)), h("b", { lang: "id" }, it.q), opts)); });
      box.appendChild(qs); box.appendChild(err);
      var check = btn("Check my answers", function () {
        err.classList.add("hide"); if (answers.some(function (a) { return a < 0; })) return M.showErr(err, "Answer every question");
        check.disabled = true;
        api("/api/student/course/attempt/" + q.attempt + "/submit", "POST", { answers: answers }).then(function (r) { result(r); }).catch(function (x) { check.disabled = false; M.showErr(err, x.message); });
      }, "p");
      box.appendChild(h("div", { class: "btns" }, check));
    }
    function result(r) {
      box.textContent = "";
      var res = h("div", { class: "card " + (r.passed ? "good" : "note") }, h("b", null, tr("Score: {0}/{1}", r.score, r.total)),
        h("div", null, r.passed ? tr("Passed! You needed {0}.", r.need) : tr("Not yet. You needed {0}. Read the chapter again, then try again.", r.need)));
      if (r.weak_chapters && r.weak_chapters.length) res.appendChild(h("div", { class: "small" }, tr("Read these chapters again: {0}", r.weak_chapters.join(", "))));
      if (r.results && r.results.length) res.appendChild(h("ol", { class: "small" }, r.results.map(function (x) { return h("li", { lang: "id" }, (x.correct ? tr("Correct.") : tr("Wrong.") + " " + tr("Answer:") + " " + x.answer + ".") + " " + x.why); })));
      var acts = h("div", { class: "btns" });
      if (r.passed) acts.appendChild(btn(n < 6 ? tr("Continue to chapter {0}", n + 1) : "Back to the course", function () { M.go(n < 6 ? "#/course/" + (n + 1) : "#/course"); }, "p"));
      else {
        var again = btn("Try again", startQuiz, "p"); M.countdown(again, r.wait || 0, "Try again");   // hitung mundur di tempat, tanpa memuat ulang halaman
        acts.appendChild(again); acts.appendChild(btn("Back to the chapter", function () { window.scrollTo({ top: 0, behavior: "smooth" }); }, "s"));
      }
      res.appendChild(acts);
      box.appendChild(res);
    }
    var info = n === 6 ? tr("Final exam: {0} questions, pass with {1} correct.", d.exam_n, d.pass) : tr("Quiz: {0} questions, pass with {1} correct.", d.quiz_n, d.pass);
    function startQuiz(e) {
      err.classList.add("hide"); if (e && e.target) e.target.disabled = true;
      api("/api/student/course/chapter/" + n + "/quiz", "POST").then(function (q) { start.classList.add("hide"); render(q); })
        .catch(function (x) { if (e && e.target) e.target.disabled = false; M.showErr(err, x.message); });
    }
    var start = btn(d.passed ? "Take it again" : "Start", startQuiz, "p");
    if (d.wait > 0) M.countdown(start, d.wait, d.passed ? "Take it again" : "Start");
    return card(n === 6 ? "Final exam" : "Quiz", h("div", { class: "small muted" }, info),
      d.attempts ? h("div", { class: "small muted" }, tr("Attempts: {0} · Best score: {1}", d.attempts, d.best === null ? "-" : d.best)) : null,
      d.passed ? h("div", { class: "card good" }, "You passed this part.") : null, h("div", null, start), box, err);
  }

  V("#/course/(\\d)", function (m) { var n = Number(m[1]); return api("/api/student/course/chapter/" + n).then(function (d) {
    var err = M.errBox(), parts = [];
    parts.push(M.pageHead(tr("Chapter {0}", n) + ": " + tr(d.title), d.career, [btn("All chapters", function () { M.go("#/course"); }, "g")]));
    if (d.goals) parts.push(h("div", { class: "card soft" }, h("h3", null, "Learning goals"), h("ul", { class: "small", lang: "id" }, d.goals.map(function (g) { return h("li", null, g); }))));
    if (d.sources && d.sources.length) parts.push(h("div", { class: "card soft" }, h("h3", null, "Sources"), h("div", { class: "small muted" }, "This course was written from the sources below. Open them to read more."),
      h("ul", { class: "small" }, d.sources.filter(function (s) { return /^https:\/\//.test(s.u); }).map(function (s) { return h("li", null, h("a", { href: s.u, target: "_blank", rel: "noopener noreferrer" }, s.t)); }))));
    if (d.sections) d.sections.forEach(function (s) { parts.push(h("div", { class: "card" }, h("h3", { lang: "id" }, s.h), h("div", { lang: "id" }, paras(s.t)))); });
    if (n === 1) {
      var b;
      if (d.done) b = btn(tr("Continue to chapter {0}", 2), function () { M.go("#/course/2"); }, "p");
      else { b = btn("Mark as read", function () { b.disabled = true; err.classList.add("hide");
          api("/api/student/course/chapter/1/read", "POST").then(function () { M.toast("Saved"); M.go("#/course/2"); }).catch(function (x) { b.disabled = false; M.showErr(err, x.message); }); }, "p");
        if (d.read_wait > 0) M.countdown(b, d.read_wait, "Mark as read"); }
      parts.push(h("div", { class: "card" }, h("div", { class: "small muted" }, d.done ? "You already read this chapter." : "Read the material above, then mark this chapter as read."), h("div", null, b), err));
    }
    if (n >= 2 && n <= 5) {
      parts.push(card("Practice", h("ol", { lang: "id" }, d.practice.map(function (p) { return h("li", null, p); }))));
      parts.push(err);
      parts.push(quizBox(n, d));
    }
    if (n === 6) {
      parts.push(card(d.project.title, h("p", { class: "cbody", lang: "id" }, d.project.brief), h("h4", null, "The teacher will check:"), h("ul", { class: "small", lang: "id" }, d.project.criteria.map(function (c) { return h("li", null, c); }))));
      var sel = M.select([["", tr("Choose one of your projects")]].concat(d.my_projects.map(function (p) { return [String(p.id), p.title + " (" + p.status + ")"]; })), d.linked ? String(d.linked.id) : "");
      var linkedMsg = h("div");
      function drawLinked(p) { linkedMsg.textContent = ""; linkedMsg.appendChild(p ? h("div", { class: "small" }, tr("Linked project: {0}", p.title), " ", M.statusChip(p.status)) : h("div", { class: "small muted" }, "No project linked yet.")); }
      drawLinked(d.linked);
      parts.push(card("Your project", h("div", { class: "small muted" }, "Create the project under Projects first. Fill in everything before you submit it: the problem, the solution and the result, and add a demo, link or file. A submitted project cannot be edited until your teacher asks for changes. Then link it here."),
        linkedMsg, d.my_projects.length ? sel : h("div", { class: "card note" }, "You have no project yet."),
        h("div", { class: "btns" }, (function () { var lb = btn("Link project", function () { err.classList.add("hide"); if (!sel.value) return M.showErr(err, "Choose a project first");
          lb.disabled = true; var pid = Number(sel.value);
          api("/api/student/course/project", "POST", { project_id: pid }).then(function () { lb.disabled = false; M.toast("Saved");
            var p = d.my_projects.filter(function (x) { return x.id === pid; })[0]; d.linked = p ? { id: p.id, title: p.title, status: p.status } : null; drawLinked(d.linked); })
            .catch(function (x) { lb.disabled = false; M.showErr(err, x.message); }); }, "p"); return lb; })(),
          btn("Open Projects", function () { M.go("#/projects"); }, "g s")), err));
      parts.push(quizBox(6, d));
    }
    return stack.apply(null, parts);
  }); });
})();
