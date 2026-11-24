/* Data DU/DI: guru melengkapi alamat dan deskripsi tempat magang yang belum terverifikasi. */
(function () {
  var h = M.h, api = M.api, btn = M.btn, chip = M.chip, card = M.card, tr = I18N.tr;
  var TE = function (p, f) { M.view("teacher", p, f); };
  function stack() { return h("div", { class: "grid" }, Array.prototype.slice.call(arguments)); }

  /* ---------- guru: melengkapi data DU/DI yang belum terverifikasi ---------- */
  TE("#/companies", function () { return api("/api/companies").then(function (d) {
    var q = h("input", { type: "search", placeholder: "Search company" }), box = h("div", { class: "grid" }), onlyOpen = true;
    function load() { box.textContent = ""; var rows = d.items.filter(function (c) { return (!onlyOpen || !c.verified) && (!q.value || c.name.toLowerCase().indexOf(q.value.toLowerCase()) >= 0); });
      if (!rows.length) return box.appendChild(h("div", { class: "empty" }, h("b", null, "No companies found")));
      rows.forEach(function (c) { var ad = h("input", { maxlength: 300, value: c.address }), sec = h("input", { maxlength: 80, value: c.sector_en }), secId = h("input", { maxlength: 80, value: c.sector_id }), ab = h("textarea", { maxlength: 800, style: "min-height:56px" }, c.about_en), abId = h("textarea", { maxlength: 800, style: "min-height:56px" }, c.about_id), src = h("input", { maxlength: 200, placeholder: "Where did you get this? (required)" }), er = M.errBox(), open = h("div", { class: "hide" });
        function submit() { api("/api/teacher/companies/" + c.id, "PUT", { address: ad.value, sector: sec.value, sector_id: secId.value, about: ab.value, about_id: abId.value, source: src.value }).then(function () { M.toast("Saved. The admin will verify it."); M.route(); }).catch(function (x) { M.showErr(er, x.message); }); }
        open.appendChild(h("div", { class: "grid" }, M.field("Address", ad), M.field("Sector (English)", sec), M.field("Sector (Indonesian)", secId), M.field("Short description (English)", ab), M.field("Short description (Indonesian)", abId), M.field("Source", src), er, h("div", null, btn("Save", submit, "p"))));
        box.appendChild(h("div", { class: "card" }, h("div", { class: "head-row" }, h("b", null, (c.number ? c.number + ". " : "") + c.name), c.verified ? chip("Verified", "good") : chip("Not verified yet", "warn")), h("div", { class: "small muted" }, c.address || "—"),
          c.verified ? null : h("div", null, btn("Fill in details", function () { open.classList.toggle("hide"); }, "s")), open)); }); }
    var t; q.addEventListener("input", function () { clearTimeout(t); t = setTimeout(load, 200); }); load();
    return stack(M.pageHead("Company data", "Help complete the address and a short description of each internship place"), h("div", { class: "card" }, M.field("Search", q), h("label", { class: "chk" }, h("input", { type: "checkbox", checked: true, onchange: function (e) { onlyOpen = e.target.checked; load(); } }), "Only show companies not verified yet")), box); }); });

  /* ---------- guru / admin: memeriksa tempat magang yang diajukan siswa ---------- */
  function reviewView() { return api("/api/teacher/company-submissions").then(function (d) {
    var box = h("div", { class: "grid" });
    function lk(href, text) { return /^https?:\/\//.test(href || "") ? h("a", { class: "btn s g", href: href, target: "_blank", rel: "noopener noreferrer" }, text) : null; }
    function row(label, v, wrap) { return v ? h("div", { class: "small" }, h("b", null, tr(label) + ": "), v) : null; }
    if (!d.items.length) box.appendChild(h("div", { class: "empty" }, h("b", null, "No places waiting for review"), h("div", { class: "small muted" }, "When a student submits a new internship place, it shows up here.")));
    d.items.forEach(function (c) {
      var note = h("textarea", { maxlength: 300, style: "min-height:56px", placeholder: "Note for the student (required when you do not approve)" }), er = M.errBox(), fix = h("div", { class: "hide grid" }, null);
      var ad = h("input", { maxlength: 300, value: c.address }), ph = h("input", { maxlength: 30, value: c.phone }), wb = h("input", { maxlength: 200, value: c.website }), ig = h("input", { maxlength: 200, value: c.instagram ? "@" + c.instagram : "" });
      fix.appendChild(M.field("Address", ad)); fix.appendChild(M.field("Phone / WhatsApp", ph)); fix.appendChild(M.field("Website", wb)); fix.appendChild(M.field("Instagram", ig));
      function send(decision) { var body = { decision: decision, note: note.value };
        if (decision === "approve") { body.address = ad.value; body.phone = ph.value; body.website = wb.value; body.instagram = ig.value; }
        api("/api/teacher/company-submissions/" + c.id, "PUT", body).then(function () { M.toast(decision === "approve" ? "Approved. The student was notified." : "Sent back to the student."); M.route(); }).catch(function (x) { M.showErr(er, x.message); }); }
      var actions = c.status === "pending" ? h("div", { class: "btns" }, btn("Approve and verify", function () { send("approve"); }, "p s"), btn("Do not approve", function () { send("reject"); }, "g s"), btn("Correct details first", function () { fix.classList.toggle("hide"); }, "s")) : h("div", { class: "small muted" }, tr("Not approved") + ": " + (c.review_note || "—"));
      box.appendChild(h("div", { class: "card" },
        h("div", { class: "head-row" }, h("b", null, c.name), c.status === "pending" ? chip("Waiting for teacher", "warn") : chip("Not approved", "bad")),
        h("div", { class: "small muted" }, tr("Submitted by {0} ({1})", c.student, c.student_class || "—")),
        row("Address", c.address), row("Type of business", c.sector), h("p", null, c.about), row("Daily tasks", c.tasks), row("Accepted majors", c.majors), row("Hours, dress code, allowance", c.work_terms),
        row("Phone", c.phone), row("Website", c.website), row("Instagram", c.instagram ? "@" + c.instagram : ""), row("How the student knows this place", c.source),
        h("div", { class: "btns" }, lk(c.website, "Website"), lk(c.instagram_url, "Instagram"), lk(c.google_url, "Search Google"), lk(c.ig_search_url, "Find on Instagram"), lk(c.fb_search_url, "Find on Facebook"), lk(c.maps_url, "Open in Maps")),
        c.status === "pending" ? h("div", { class: "grid" }, fix, M.field("Note", note), er) : null, actions)); });
    return stack(M.pageHead("Place requests", tr("{0} waiting for your review", d.pending)), box);
  }); }
  TE("#/company-review", reviewView); M.view("admin", "#/company-review", reviewView);
})();
