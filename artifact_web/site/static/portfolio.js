/* Portfolio: berbagi lewat tautan, prestasi, sertifikat, dan halaman publik. */
(function () {
  var h = M.h, api = M.api, btn = M.btn, chip = M.chip, card = M.card, tr = I18N.tr;

  function safeHref(u) { return /^https?:\/\/[^\s\\]+$/i.test(u || "") ? u : null; }
  function verifiedChip(v) { return chip(v ? "Verified" : "Self claimed", v ? "good" : ""); }
  var MAXB = 3 * 1024 * 1024;
  function readB64(file) {
    return new Promise(function (ok, no) {
      if (file.size > MAXB) return no(new Error(tr("File is too large (max 3 MB)")));
      var r = new FileReader(); r.onload = function () { ok(String(r.result).split(",")[1] || ""); }; r.onerror = function () { no(new Error(tr("The file could not be read"))); }; r.readAsDataURL(file);
    });
  }
  /* kind: certificate | achievement | project. Server re-checks the real file type, size and owner. */
  function uploadFile(kind, refId, file) {
    return readB64(file).then(function (b64) { return api("/api/student/uploads", "POST", { kind: kind, ref_id: refId, filename: file.name, data: b64 }); });
  }
  function fileLinks(files, onRemove) {
    return h("span", { class: "files" }, (files || []).map(function (f) {
      return h("span", { class: "filechip" }, h("a", { href: "#", onclick: function (e) { e.preventDefault(); window.MettaServer.openFile(f.id); } }, f.name),
        onRemove ? h("button", { type: "button", class: "x", "aria-label": "Remove file", title: "Remove file", onclick: function () { onRemove(f); } }, "×") : null);
    }));
  }
  function filePicker(id) { return h("input", { type: "file", accept: ".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg", id: id || null }); }
  M.uploadFile = uploadFile; M.fileLinks = fileLinks; M.filePicker = filePicker;
  function monthInput(v) { return h("input", { type: "month", value: v || "", "aria-label": "When" }); }

  /* Bagian bawah halaman Portfolio siswa: berbagi, prestasi, sertifikat. */
  function extras() {
    return api("/api/student/portfolio/extras").then(function (d) {
      var box = h("div", { class: "grid" });
      function redraw(next) { d = next; box.textContent = ""; build(); }

      function shareCard() {
        var vis = M.select([["PRIVATE", tr("Only me")], ["LINK", tr("Anyone with the link")]], d.share.visibility === "PRIVATE" ? "PRIVATE" : "LINK");
        var head = h("input", { value: d.share.headline || "", maxlength: "120", placeholder: "One line about you (optional)" }), err = M.errBox();
        var kids = [h("span", { class: "muted small" }, "Your portfolio is private until you choose to share it. A shared link shows only verified projects, skills, achievements and certificates. Your email is never shown."),
          M.field("Who can see it", vis), M.field("Headline", head), err];
        var link = null;
        if (d.share.visibility !== "PRIVATE" && d.share.slug) {
          var url = window.MettaServer.publicLink(d.share.slug);
          var inp = h("input", { value: url, readonly: true, "aria-label": "Your portfolio link" });
          inp.addEventListener("focus", function () { inp.select(); });
          link = h("div", { class: "pw-box" }, inp, btn("Copy", function () {
            if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(function () { M.toast("Link copied"); }, function () { inp.select(); M.toast("Press Ctrl+C to copy"); });
            else { inp.select(); M.toast("Press Ctrl+C to copy"); }
          }, "p"));
          kids.push(link);
        }
        function save(newLink) {
          err.classList.add("hide");
          api("/api/student/portfolio/share", "PUT", { visibility: vis.value, new_link: !!newLink, headline: head.value }).then(function (s) { d.share = s; M.toast("Saved"); redraw(d); }).catch(function (x) { M.showErr(err, x.message); });
        }
        var row = [btn("Save changes", function () { save(false); }, "p")];
        if (d.share.slug) row.push(btn("Create a new link", function () { if (window.confirm(tr("Create a new link? The old link will stop working."))) save(true); }, "g"));
        kids.push(h("div", { class: "btns" }, row));
        return card("Share your portfolio", kids);
      }

      function proofForm() {
        var type = "certificate", err = M.errBox();
        var t = h("input", { maxlength: "120", placeholder: "Example: Cisco Networking Basics" }), i = h("input", { maxlength: "100", placeholder: "Example: Cisco, school, or competition committee" }), w = monthInput(),
          u = h("input", { type: "url", maxlength: "300", placeholder: "https://" }), fp = filePicker(), urlField = M.field("Or paste a link (optional)", u);
        var bCert = btn("Certificate", function () { set("certificate"); }, "seg"), bAch = btn("Achievement", function () { set("achievement"); }, "seg");
        function set(k) { type = k; bCert.classList.toggle("on", k === "certificate"); bAch.classList.toggle("on", k === "achievement"); urlField.classList.toggle("hide", k !== "certificate"); }
        set("certificate");
        var go = btn("Send to my teacher", function () {
          err.classList.add("hide"); go.disabled = true; var file = fp.files && fp.files[0];
          if (file && file.size > MAXB) { go.disabled = false; return M.showErr(err, tr("File is too large (max 3 MB)")); }
          var path = type === "certificate" ? "/api/student/certificates" : "/api/student/achievements";
          var body = type === "certificate" ? { title: t.value, issuer: i.value, issued_on: w.value, url: u.value } : { title: t.value, issuer: i.value, achieved_on: w.value };
          api(path, "POST", body).then(function (n) { return file ? uploadFile(type, n.new_id, file).then(function () { return n; }) : n; })
            .then(function () { M.toast("Sent. Your teacher will check it."); M.route(); })
            .catch(function (x) { go.disabled = false; M.showErr(err, x.message); });
        }, "p");
        return h("div", { class: "pform" },
          h("div", { class: "pstep" }, h("span", { class: "pn" }, "1"), h("div", null, h("b", null, "What do you want to send?"), h("div", { class: "segs" }, bCert, bAch))),
          h("div", { class: "pstep" }, h("span", { class: "pn" }, "2"), h("div", { class: "grow" }, h("b", null, "Write the details"), h("div", { class: "grid g2" }, M.field("Name", t), M.field("Who gave it?", i), M.field("When", w)))),
          h("div", { class: "pstep" }, h("span", { class: "pn" }, "3"), h("div", { class: "grow" }, h("b", null, "Attach your proof"), M.field("Photo or scan (PDF, PNG or JPG, max 3 MB)", fp), urlField)),
          err, h("div", null, go));
      }
      function proofList() {
        var rows = d.certificates.map(function (r) { return { k: "certificate", path: "certificates", r: r, date: r.issued_on }; }).concat(d.achievements.map(function (r) { return { k: "achievement", path: "achievements", r: r, date: r.achieved_on }; }));
        if (!rows.length) return h("div", { class: "empty" }, h("b", null, "Nothing sent yet"), h("div", { class: "small muted" }, "Use the form above to send your first certificate or achievement."));
        return h("div", { class: "plist" }, rows.map(function (x) { var r = x.r, meta = [r.issuer, x.date].filter(Boolean).join(" · "), add = filePicker();
          add.classList.add("hide"); add.addEventListener("change", function () { if (!add.files[0]) return; uploadFile(x.k, r.id, add.files[0]).then(function () { M.toast("File added"); M.route(); }).catch(M.fail); });
          return h("div", { class: "pitem" }, h("div", { class: "grow" }, h("b", null, r.title), h("div", { class: "small muted" }, meta || "—"),
            h("div", { class: "chips" }, chip(x.k === "certificate" ? "Certificate" : "Achievement"), chip(r.verified ? "Verified" : "Waiting for teacher check", r.verified ? "good" : "")),
            fileLinks(r.files, function (f) { api("/api/student/uploads/" + f.id, "DELETE").then(function () { M.route(); }).catch(M.fail); }),
            r.url && safeHref(r.url) ? h("div", null, h("a", { href: r.url, target: "_blank", rel: "noopener noreferrer" }, "Open link")) : null),
            h("div", { class: "btns" }, (r.files || []).length < 3 ? btn("Add file", function () { add.click(); }, "g s") : null, add,
              btn("Delete", function () { if (window.confirm(tr("Delete this item and its files?"))) api("/api/student/" + x.path + "/" + r.id, "DELETE").then(function () { M.route(); }).catch(M.fail); }, "g s"))); }));
      }
      function build() {
        box.appendChild(card("Send a certificate or achievement", h("span", { class: "muted small" }, "Three easy steps. Your teacher checks it, then it shows as Verified in your portfolio. Files stay private: only you and your teachers can open them."), proofForm()));
        box.appendChild(card("My certificates and achievements", proofList()));
        box.appendChild(shareCard());
      }
      build();
      return box;
    });
  }

  /* Halaman publik: bisa dibuka tanpa login lewat tautan #/p/<kode>. */
  function publicView(slug) {
    var app = document.getElementById("app"); app.textContent = "";
    var body = h("main", { class: "pub-body" }, h("div", { class: "muted" }, "Loading..."));
    app.appendChild(h("div", { class: "pub" },
      h("header", { class: "pub-top" }, h("a", { href: "#/", class: "brand-link", "aria-label": "Metta Career" }, M.logoImg(34)), h("span", { class: "sp" }), M.langSwitch("compact"), h("a", { class: "btn", href: "#/login" }, "Sign in")), body));
    api("/api/public/portfolio/" + encodeURIComponent(slug)).then(function (d) {
      body.textContent = "";
      var sub = [d.major, d.class_name, d.school].filter(Boolean).join(" · ");
      body.appendChild(h("section", { class: "pub-hero" }, h("h1", null, d.name), d.headline ? h("p", { class: "pub-headline" }, d.headline) : null,
        h("p", { class: "muted" }, sub), d.target ? h("div", { class: "chips" }, chip(tr("Target: {0}", d.target), "good")) : null));
      var grid = h("div", { class: "grid g12" });
      grid.appendChild(card("Verified projects", d.projects.length ? d.projects.map(function (p) {
        return h("div", { class: "card soft" }, h("b", null, p.title), p.description ? h("span", { class: "small" }, p.description) : null,
          h("div", { class: "chips" }, (p.skills || []).map(function (s) { return chip(s); })),
          safeHref(p.link) ? h("a", { href: p.link, target: "_blank", rel: "noopener noreferrer" }, "Open link") : null); }) : h("span", { class: "muted" }, "No verified projects yet.")));
      grid.appendChild(card("Skills and evidence level", d.skills.length ? M.table(["Skill", "Evidence"], d.skills.map(function (s) { return [s.name, chip(s.evidence, s.level === 4 ? "good" : "")]; })) : h("span", { class: "muted" }, "None yet")));
      body.appendChild(grid);
      if (d.courses && d.courses.length) body.appendChild(M.coursesCard(d.courses));
      function pubList(title, rows, dateKey) {
        return card(title, rows.length ? h("ul", { class: "list small" }, rows.map(function (r) {
          var meta = [r.issuer, r[dateKey]].filter(Boolean).join(" · ");
          return h("li", null, h("b", null, r.title), meta ? h("span", { class: "muted" }, " · " + meta) : null, " ", verifiedChip(r.verified),
            safeHref(r.url) ? h("a", { href: r.url, target: "_blank", rel: "noopener noreferrer", style: "margin-left:8px" }, "Open link") : null); })) : h("span", { class: "muted" }, "None yet"));
      }
      body.appendChild(h("div", { class: "grid g2" }, pubList("Achievements", d.achievements, "achieved_on"), pubList("Certificates", d.certificates, "issued_on")));
      body.appendChild(h("div", { class: "card note small" }, "Skills marked Verified were checked by a teacher through a project. Items marked Self claimed are written by the student and not yet checked."));
    }).catch(function (e) {
      body.textContent = "";
      body.appendChild(h("div", { class: "card", style: "max-width:520px" }, h("h3", null, "Portfolio not found"),
        h("p", { class: "muted" }, "This portfolio is private, or the link is wrong. Ask the student for a new link."), h("a", { class: "btn p", href: "#/" }, "Back to home")));
    });
    window.scrollTo(0, 0);
  }

  M.portfolioExtras = extras; M.publicPortfolio = publicView;
})();
