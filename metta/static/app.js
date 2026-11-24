/* Metta Career front end: plain JavaScript, no build step. Views live in student.js and staff.js. */
var tr = I18N.tr;
var M = (function () {
  var me = null, prev = "", cur = "", notifTimer = null;
  var views = {};              // role -> list of [regex, handler]
  var NAV = {
    student: [["Dashboard", "#/dashboard"], ["Self Discovery", "#/discovery"], ["Explore", "#/explore"], ["Career Plan", "#/plan"], ["Learning", "#/learning"],
      ["Projects", "#/projects"], ["Portfolio", "#/portfolio"], ["Internship", "#/internship"], ["Alumni Stories", "#/alumni"], ["AI Career Assistant", "#/assistant"]],
    teacher: [["Dashboard", "#/dashboard"], ["Students", "#/students"], ["Career Plans", "#/plans"], ["Projects", "#/projects"], ["Validation", "#/validation"], ["Internship", "#/internship"], ["Company data", "#/companies"], ["Place requests", "#/company-review"], ["Password requests", "#/resets"], ["Analytics", "#/analytics"]],
    admin: [["Dashboard", "#/dashboard"], ["Users", "#/users"], ["Career Data", "#/careers"], ["Skills", "#/skills"], ["Internship Companies", "#/companies"], ["Place requests", "#/company-review"], ["Alumni content", "#/moderation"], ["Password requests", "#/resets"], ["Analytics", "#/analytics"]],
    alumni: [["Dashboard", "#/dashboard"], ["Write a story", "#/write"], ["My profile", "#/my-profile"]]
  };
  var ROLE = { student: "Student", teacher: "Teacher", admin: "Admin", alumni: "Alumni" };

  /* ---------- helpers ---------- */
  function h(tag, props) {
    var el = document.createElement(tag), kids = Array.prototype.slice.call(arguments, 2);
    for (var k in (props || {})) {
      var v = props[k]; if (v === null || v === undefined || v === false) continue;
      if (typeof v === "string" && (k === "placeholder" || k === "title" || k === "alt" || k === "aria-label")) v = tr(v);
      if (k.slice(0, 2) === "on" && typeof v === "function") el.addEventListener(k.slice(2), v);
      else if (k === "class") el.className = v; else if (k === "value") el.value = v;
      else if (k === "checked" || k === "disabled" || k === "selected") el[k] = !!v; else el.setAttribute(k, v === true ? "" : v);
    }
    (function add(list) { list.forEach(function (c) { if (c === null || c === undefined || c === false) return;
      if (Array.isArray(c)) add(c); else el.appendChild(c.nodeType ? c : document.createTextNode(typeof c === "string" ? tr(c) : String(c))); }); })(kids);
    return el;
  }
  function api(path, method, body) {
    var opt = { method: method || "GET", headers: { "X-Lang": I18N.lang() }, credentials: "same-origin" };
    if (body !== undefined) { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
    return fetch(path, opt).catch(function () { throw new Error(tr("Could not reach the server. Check your connection and try again.")); }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (r.status === 401 && me && path.indexOf("/api/auth/") !== 0) { me = null; go("#/login"); }
        if (!r.ok) { var e = new Error(d.error ? I18N.err(d.error) : tr("Request failed")); e.status = r.status; throw e; }
        return d;
      });
    });
  }
  function toast(msg) { var t = document.getElementById("toast"); t.textContent = tr(msg); t.classList.add("show"); clearTimeout(t._t); t._t = setTimeout(function () { t.classList.remove("show"); }, 2600); }
  /* Kotak pesan di tengah layar untuk hal yang harus dibaca dulu sebelum lanjut.
     Bisa ditutup dengan tombol Tutup, klik latar gelap, atau tombol Esc. */
  function modal(title) {
    var isi = Array.prototype.slice.call(arguments, 1);
    var tutup = function () { if (!wrap.parentNode) return; document.removeEventListener("keydown", onKey); wrap.parentNode.removeChild(wrap); if (fokusLama && fokusLama.focus) fokusLama.focus(); };
    var onKey = function (e) { if (e.key === "Escape") tutup(); };
    var fokusLama = document.activeElement;
    var tombol = btn("Close", tutup, "p");
    var kotak = h("div", { class: "modal", role: "dialog", "aria-modal": "true", "aria-label": title, onclick: function (e) { e.stopPropagation(); } },
      h("h3", null, title), isi, h("div", { class: "btns", style: "justify-content:flex-end" }, tombol));
    var wrap = h("div", { class: "modal-wrap", onclick: tutup }, kotak);
    document.body.appendChild(wrap);
    document.addEventListener("keydown", onKey);
    tombol.focus({ preventScroll: true });   // jangan menggulir kotak yang panjang ke tombol di dasar
    return tutup;
  }
  function go(hash) { if (location.hash === hash) route(); else location.hash = hash; }
  function back(fallback) { if (prev && prev !== cur) go(prev); else go(fallback || "#/dashboard"); }
  function fail(e) { toast(e.message || tr("Something went wrong")); }
  function errBox() { return h("div", { class: "err hide", role: "alert" }); }
  function showErr(box, msg) { box.textContent = tr(msg); box.classList.remove("hide"); }
  function field(label, input, id) { id = id || ("f" + Math.random().toString(36).slice(2, 8)); input.id = id; return h("div", { class: "field" }, h("label", { for: id }, label), input); }
  function btn(text, onclick, kind, extra) { var p = { class: "btn " + (kind || ""), type: "button", onclick: onclick }; for (var k in (extra || {})) p[k] = extra[k]; return h("button", p, text); }
  function chip(text, kind) { return h("span", { class: "chip " + (kind || "") }, text); }
  /* Hitung mundur pada tombol: tombol dimatikan, teks menunjukkan sisa waktu, lalu aktif lagi TANPA memuat ulang halaman.
     Berhenti sendiri bila tombol sudah tidak ada di halaman (siswa pindah halaman). */
  function countdown(b, sec, readyText, onDone) {
    var end = Date.now() + Math.max(0, sec) * 1000, seen = false;
    function fmt(s) { return s >= 60 ? Math.floor(s / 60) + ":" + ("0" + (s % 60)).slice(-2) : String(s); }
    function tick() {
      if (b.isConnected) seen = true; else if (seen) { clearInterval(t); return; }   // tombol sudah pernah tampil lalu hilang: siswa pindah halaman
      var left = Math.ceil((end - Date.now()) / 1000);
      if (left <= 0) { clearInterval(t); b.disabled = false; b.textContent = tr(readyText); if (onDone) onDone(); return; }
      b.disabled = true; b.textContent = tr(left >= 60 ? "Try again in {0}" : "Wait {0} s", fmt(left));
    }
    var t = setInterval(tick, 500); tick(); return function () { clearInterval(t); };
  }
  /* ---------- Diagram batang (satu seri, satu warna) ----------
     items: [{label, value, note}]  o: {unit:"%", max:100 (skala tetap), vertical:true/false}
     Skala selalu mulai dari 0. Persentase memakai 0-100 agar 7% tidak terlihat penuh. Ada tooltip (hover/fokus) dan tombol tabel. */
  function niceTicks(max) {
    if (max <= 0) return [0, 1];
    var raw = max / 4, mag = Math.pow(10, Math.floor(Math.log10(raw))), step = [1, 2, 5, 10].map(function (k) { return k * mag; }).filter(function (s) { return s >= raw; })[0];
    step = Math.max(1, step); var top = Math.ceil(max / step) * step, out = [];
    for (var v = 0; v <= top + 1e-9; v += step) out.push(Math.round(v)); return out;
  }
  function barChart(items, o) {
    o = o || {}; var unit = o.unit || "";
    if (!items || !items.length) return h("div", { class: "muted small" }, "No data yet.");
    var vmax = Math.max.apply(null, items.map(function (i) { return i.value; })), ticks = o.max ? [0, 25, 50, 75, 100].map(function (p) { return p * o.max / 100; }) : niceTicks(Math.max(vmax, 4)), top = ticks[ticks.length - 1];
    function f(v) { return top ? Math.max(0, Math.min(1, v / top)) : 0; }
    function fmt(v) { return v + unit; }
    var wrap = h("div", { class: "chart" }), tip = h("div", { class: "ch-tip", role: "status" }), plot;
    function show(el, it) { tip.textContent = ""; tip.appendChild(h("b", null, it.label)); tip.appendChild(h("span", null, fmt(it.value) + (it.note ? " · " + it.note : "")));
      var a = wrap.getBoundingClientRect(), r = el.getBoundingClientRect(); tip.style.display = "block";
      var x = r.left - a.left + r.width / 2, w = tip.offsetWidth; x = Math.max(w / 2, Math.min(a.width - w / 2, x));
      tip.style.left = x + "px"; tip.style.top = (r.top - a.top - tip.offsetHeight - 6) + "px"; }
    function hide() { tip.style.display = "none"; }
    function hover(el, it) { el.tabIndex = 0; el.setAttribute("aria-label", it.label + ": " + fmt(it.value) + (it.note ? ", " + it.note : ""));
      el.addEventListener("mouseenter", function () { show(el, it); }); el.addEventListener("focus", function () { show(el, it); });
      el.addEventListener("mouseleave", hide); el.addEventListener("blur", hide); }
    if (o.vertical) {
      var grid = h("div", { class: "ch-grid" }), bands = h("div", { class: "ch-bands" }), labs = h("div", { class: "ch-xlabs" });
      ticks.forEach(function (t) { var y = "calc((100% - 22px) * " + f(t) + ")"; grid.appendChild(h("i", { style: "bottom:" + y })); grid.appendChild(h("span", { class: "ch-yt", style: "bottom:" + y }, fmt(t))); });
      items.forEach(function (it) { var hgt = "calc((100% - 22px) * " + f(it.value) + ")";
        var band = h("div", { class: "ch-band" }, h("i", { class: "ch-col", style: "height:" + hgt }), h("b", { class: "ch-cap", style: "bottom:calc(" + hgt + " + 4px)" }, fmt(it.value)));
        hover(band, it); bands.appendChild(band); labs.appendChild(h("span", { title: it.label }, it.label)); });
      plot = h("div", { class: "ch-v" }, h("div", { class: "ch-plot" }, grid, bands), labs);
    } else {
      plot = h("div", { class: "ch-h" });
      items.forEach(function (it) { var w = "calc((100% - 52px) * " + f(it.value) + ")", track = h("div", { class: "ch-track" });
        ticks.forEach(function (t) { track.appendChild(h("i", { class: "ch-gl", style: "left:calc((100% - 52px) * " + f(t) + ")" })); });
        track.appendChild(h("i", { class: "ch-bar", style: "width:" + w })); track.appendChild(h("b", { class: "ch-val", style: "left:calc(" + w + " + 6px)" }, fmt(it.value)));
        var row = h("div", { class: "ch-row" }, h("span", { class: "ch-lab", title: it.label }, it.label), track); hover(row, it); plot.appendChild(row); });
      var axis = h("div", { class: "ch-track ch-axis" }); ticks.forEach(function (t) { axis.appendChild(h("span", { style: "left:calc((100% - 52px) * " + f(t) + ")" }, fmt(t))); });
      plot.appendChild(h("div", { class: "ch-row ch-axisrow", "aria-hidden": "true" }, h("span"), axis));
    }
    var tbl = table([o.labelHead || "Category", o.valueHead || "Value"], items.map(function (it) { return [it.label, fmt(it.value) + (it.note ? " (" + it.note + ")" : "")]; }));
    tbl.classList.add("hide");
    var toggle = h("button", { type: "button", class: "ch-toggle" }, "Show table");
    toggle.addEventListener("click", function () { var t = tbl.classList.toggle("hide"); plot.classList.toggle("hide", !t); toggle.textContent = tr(t ? "Show table" : "Show chart"); hide(); });
    wrap.appendChild(plot); wrap.appendChild(tbl); wrap.appendChild(tip); wrap.appendChild(h("div", { class: "ch-foot" }, toggle));
    return wrap;
  }
  function bar(p) { return h("div", { class: "bar", role: "progressbar", "aria-valuenow": p, "aria-valuemin": 0, "aria-valuemax": 100 }, h("i", { style: "width:" + Math.max(0, Math.min(100, p)) + "%" })); }
  function card(title) { var kids = Array.prototype.slice.call(arguments, 1); return h("div", { class: "card" }, title ? h("h3", null, title) : null, kids); }
  function table(heads, rows, onrow) {
    return h("div", { class: "tw" }, h("table", null, h("thead", null, h("tr", null, heads.map(function (x) { return h("th", null, x); }))),
      h("tbody", null, rows.length ? rows.map(function (r, i) { var tr = h("tr", { class: onrow ? "click" : "" }, r.map(function (c) { return h("td", null, c); }));
        if (onrow) { tr.tabIndex = 0; tr.addEventListener("click", function () { onrow(i); }); tr.addEventListener("keydown", function (e) { if (e.key === "Enter") onrow(i); }); } return tr; })
        : [h("tr", null, h("td", { colspan: heads.length, class: "muted" }, "Nothing here yet.")) ])));
  }
  function tabs(items, on, change) {
    var box = h("div", { class: "tabs", role: "tablist" });
    items.forEach(function (t, i) { box.appendChild(h("button", { class: i === on ? "on" : "", role: "tab", onclick: function () { change(i); } }, t)); }); return box;
  }
  function select(options, value) { return h("select", null, options.map(function (o) { var v = Array.isArray(o) ? o[0] : o, l = Array.isArray(o) ? o[1] : o; return h("option", { value: v, selected: String(v) === String(value) }, l); })); }
  function pageHead(title, sub, buttons) { return h("div", { class: "head-row" }, h("div", null, h("h1", null, title), sub ? h("div", { class: "muted" }, sub) : null), h("div", { class: "btns" }, buttons || [])); }
  function statusChip(s) { var m = { "On track": "good", "Active": "", "Inactive": "bad", "Needs feedback": "warn", "No plan yet": "warn", VERIFIED: "good", SUBMITTED: "warn", NEEDS_REVISION: "bad", COMPLETED: "good", IN_PROGRESS: "warn", NOT_STARTED: "" };
    return chip(String(s).replace(/_/g, " "), m[s] || ""); }
  function date(s) { return (s || "").slice(0, 10); }
  function loading() { return h("div", { class: "muted" }, "Loading..."); }

  /* ---------- shell ---------- */
  function logoImg(hgt) { return h("img", { src: "/static/brand/logo-horizontal.svg", alt: "Metta Career by Next Steps", class: "brand-logo", style: hgt ? "height:" + hgt + "px" : null }); }
  function authLogo() { return h("img", { class: "logo", src: "/static/brand/logo-stacked.svg", alt: "Metta Career by Next Steps" }); }
  /* Tombol ganti bahasa ID | EN. Dipakai di bar atas, halaman depan, dan footer. */
  function langSwitch(extra) {
    var box = h("div", { class: "langsw " + (extra || ""), role: "group", "aria-label": tr("Language") });
    [["id", "ID", "Bahasa Indonesia"], ["en", "EN", "English"]].forEach(function (l) {
      box.appendChild(h("button", { type: "button", class: I18N.lang() === l[0] ? "on" : "", lang: l[0], "aria-pressed": I18N.lang() === l[0] ? "true" : "false", title: l[2], "aria-label": l[2],
        onclick: function () { chooseLang(l[0]); } }, l[1]));
    });
    return box;
  }
  function chooseLang(l) {
    if (l === I18N.lang()) return;
    I18N.set(l);                                   // memicu render ulang lewat I18N.onChange
    if (me) api("/api/me/lang", "POST", { lang: l }).catch(function () { });
  }
  function shell(content) {
    var app = document.getElementById("app"); app.textContent = "";
    var menu = null;
    function closeMenu() { if (menu) { menu.remove(); menu = null; } }
    function openMenu(node) { closeMenu(); menu = node; document.body.appendChild(node); setTimeout(function () { document.addEventListener("click", closeMenu, { once: true }); }, 0); }
    var nbtn = null;
    {
      nbtn = h("button", { class: "pill", type: "button", id: "notifbtn", onclick: function (e) { e.stopPropagation(); api("/api/notifications").then(function (d) {
        var list = d.items.length ? d.items.slice(0, 8).map(function (n) { return h("div", { class: "head", style: "color:var(--ink)" }, n.text); }) : [h("div", { class: "head" }, "No notifications")];
        openMenu(h("div", { class: "dropdown", onclick: function (ev) { ev.stopPropagation(); } }, h("div", { class: "head" }, "Notifications"), list, h("hr"), h("button", { onclick: function () { api("/api/notifications/read", "POST").then(function () { closeMenu(); refreshNotif(); }); } }, "Mark all as read")));
      }).catch(fail); } }, "Notifications");
    }
    var top = h("header", { class: "tools" }, langSwitch("compact"), nbtn,
      h("button", { class: "menu-btn pill", type: "button", "aria-haspopup": "menu", onclick: function (e) { e.stopPropagation();
        openMenu(h("div", { class: "dropdown", role: "menu", onclick: function (ev) { ev.stopPropagation(); } }, h("div", { class: "head" }, me.name + " · " + ROLE[me.role]),
          h("a", { href: "#/profile", onclick: closeMenu }, "Profile"), h("a", { href: "#/settings", onclick: closeMenu }, "Settings"), h("hr"),
          h("button", { onclick: function () { closeMenu(); api("/api/auth/logout", "POST").then(function () { me = null; go("#/signedout"); }); } }, "Log out"))); } },
        h("span", null, me.name), h("span", { class: "avatar", "aria-hidden": "true" }, initials(me.name))));
    var brand = h("a", { href: "#/dashboard", class: "sb-brand", "aria-label": "Metta Career" }, h("img", { src: "/static/brand/logo-mark.svg", alt: "", width: 44, height: 44 }),
      h("span", { class: "sb-name" }, h("span", { class: "sb-t" }, rawText("span", "Metta", ""), rawText("span", "Career", "sb-c")), h("span", { class: "sb-role" }, ROLE[me.role])));
    var side = h("nav", { class: "side", "aria-label": "Main" }, brand, h("div", { class: "sb-list" }, NAV[me.role].map(function (n) { return h("a", { href: n[1], class: (cur === n[1] || cur.indexOf(n[1] + "/") === 0) ? "on" : "" }, h("span", { class: "dot", "aria-hidden": "true" }), n[0]); })));
    var slot = h("div", { class: "slot" }); slot.appendChild(content);
    var main = h("main", { class: "main" }, top, slot, M_.siteFooter ? M_.siteFooter(true) : null);
    app.appendChild(h("div", { class: "layout" }, side, main)); refreshNotif();
    return slot;
  }
  function rawText(tag, text, cls) { var e = document.createElement(tag); e.textContent = text; if (cls) e.className = cls; return e; }   // nama merek tidak diterjemahkan
  function initials(n) { var p = String(n || "?").trim().split(/\s+/); return ((p[0] || "?")[0] + (p.length > 1 ? p[p.length - 1][0] : "")).toUpperCase(); }
  function refreshNotif() { var b = document.getElementById("notifbtn"); if (!b) return;
    api("/api/notifications").then(function (d) { b.textContent = tr("Notifications") + (d.unread ? " · " + d.unread : ""); }).catch(function () {}); }
  function plain(node, wide) { var app = document.getElementById("app"); app.textContent = "";
    /* Halaman masuk/daftar memakai bar atas dan footer yang sama dengan halaman depan. */
    var head = M_.siteHeader ? M_.siteHeader() : null, foot = M_.siteFooter ? M_.siteFooter() : null;
    app.appendChild(h("div", { class: "lp plainpage" }, head, h("main", { class: "center" }, node), foot)); window.scrollTo(0, 0); }

  /* ---------- auth screens ---------- */
  function landing() { if (M_.landingView) return M_.landingView(); var app = document.getElementById("app"); app.textContent = ""; app.appendChild(h("div", { class: "center" }, btn("Sign in", function () { go("#/login"); }, "p"))); }
  function syncLang() { if (me && me.lang !== I18N.lang()) api("/api/me/lang", "POST", { lang: I18N.lang() }).catch(function () { }); }
  function login() {
    var role = "student", err = errBox(), email = h("input", { type: "email", autocomplete: "username", required: true }), pw = h("input", { type: "password", autocomplete: "current-password", required: true });
    var tabsBox = h("div"); var note = h("div", { class: "muted small", style: "text-align:center" });
    function draw() { tabsBox.textContent = ""; tabsBox.appendChild(tabs(["Student", "Teacher", "Alumni", "Admin"], ["student", "teacher", "alumni", "admin"].indexOf(role), function (i) { role = ["student", "teacher", "alumni", "admin"][i]; draw(); }));
      note.textContent = ""; if (role === "student") { note.appendChild(document.createTextNode(tr("No account yet? "))); note.appendChild(h("a", { href: "#/register" }, "Create account")); } else note.textContent = tr("Teacher, alumni and admin accounts are created by the admin."); }
    draw();
    var form = h("form", { class: "auth", onsubmit: function (e) { e.preventDefault(); err.classList.add("hide");
      api("/api/auth/login", "POST", { email: email.value, password: pw.value, role: role }).then(function (u) { me = u; syncLang(); go("#/dashboard"); }).catch(function (x) { showErr(err, x.message); }); } },
      authLogo(), h("h2", { style: "text-align:center" }, "Sign in to Metta Career"), tabsBox,
      field("Email", email), field("Password", pw), h("div", { style: "text-align:right" }, h("a", { href: "#/forgot", class: "small" }, "Forgot your password?")), err, h("button", { class: "btn p", type: "submit" }, "Sign in"), note);
    plain(form); email.focus();
  }
  function forgot() {
    var err = errBox(), email = h("input", { type: "email", autocomplete: "username", required: true }), box = h("div", { class: "auth" });
    function done() { box.textContent = ""; box.appendChild(authLogo()); box.appendChild(h("h2", { style: "text-align:center" }, "Request sent"));
      box.appendChild(h("p", { class: "small" }, "If this email is registered, your teacher or the school admin can now see your request."));
      box.appendChild(h("p", { class: "small" }, "Go to them in person with your student card. They will give you a one-time code. Then open the reset page and choose a new password."));
      box.appendChild(h("a", { class: "btn p", href: "#/reset" }, "I have a code")); box.appendChild(h("a", { href: "#/login", class: "small", style: "text-align:center" }, "Back to sign in")); }
    box.appendChild(authLogo()); box.appendChild(h("h2", { style: "text-align:center" }, "Forgot your password?"));
    box.appendChild(h("p", { class: "small muted" }, "Enter your email. Your teacher or the school admin will confirm it is you and give you a one-time code. Nobody can see your password."));
    box.appendChild(field("Email", email)); box.appendChild(err);
    box.appendChild(btn("Send request", function () { err.classList.add("hide"); api("/api/auth/forgot", "POST", { email: email.value }).then(done).catch(function (x) { showErr(err, x.message); }); }, "p"));
    box.appendChild(h("div", { class: "small", style: "text-align:center" }, h("a", { href: "#/reset" }, "I already have a code"), " · ", h("a", { href: "#/login" }, "Back to sign in")));
    plain(box); email.focus();
  }
  function resetView() {
    var err = errBox(), email = h("input", { type: "email", autocomplete: "username", required: true }), code = h("input", { autocomplete: "one-time-code", maxlength: 12, placeholder: "ABCD-EFGH", style: "text-transform:uppercase;letter-spacing:.12em" }),
      p1 = h("input", { type: "password", autocomplete: "new-password" }), p2 = h("input", { type: "password", autocomplete: "new-password" }), box = h("div", { class: "auth" });
    box.appendChild(authLogo()); box.appendChild(h("h2", { style: "text-align:center" }, "Choose a new password"));
    box.appendChild(field("Email", email)); box.appendChild(field("One-time code from your teacher or admin", code)); box.appendChild(field("New password", p1)); box.appendChild(field("Repeat the new password", p2)); box.appendChild(err);
    box.appendChild(btn("Save new password", function () { err.classList.add("hide");
      if (p1.value !== p2.value) return showErr(err, "The two new passwords do not match.");
      api("/api/auth/reset", "POST", { email: email.value, code: code.value, new_password: p1.value }).then(function () { toast("New password saved"); go("#/login"); }).catch(function (x) { showErr(err, x.message); }); }, "p"));
    box.appendChild(h("div", { class: "small", style: "text-align:center" }, h("a", { href: "#/forgot" }, "I do not have a code"), " · ", h("a", { href: "#/login" }, "Back to sign in")));
    plain(box); email.focus();
  }
  function register() {
    var step = 1, err = errBox(), needCode = false, d = { name: "", email: "", password: "", school: "SMK Metta Maitreya", major: "TKJ", class_name: "", goal: "", code: "" };
    api("/api/auth/config").then(function (cfg) { needCode = !!cfg.register_code_required; }).catch(function () { });
    var box = h("div", { class: "auth" });
    function draw() { box.textContent = ""; err.classList.add("hide");
      box.appendChild(authLogo());
      if (step === 1) {
        var n = h("input", { value: d.name, required: true, autocomplete: "name" }), e = h("input", { type: "email", value: d.email, required: true, autocomplete: "username" }), p = h("input", { type: "password", value: d.password, minlength: 8, required: true, autocomplete: "new-password" });
        box.appendChild(h("h2", { style: "text-align:center" }, "Create student account")); box.appendChild(field("Full name", n)); box.appendChild(field("Email", e)); box.appendChild(field("Password (min. 8 characters)", p)); box.appendChild(err);
        box.appendChild(btn("Continue", function () { d.name = n.value.trim(); d.email = e.value.trim(); d.password = p.value;
          if (d.name.length < 2 || !/^\S+@\S+\.\S+$/.test(d.email) || d.password.length < 8) return showErr(err, "Please enter your name, a valid email and a password of at least 8 characters."); step = 2; draw(); }, "p"));
        box.appendChild(h("div", { class: "muted small", style: "text-align:center" }, "Already have an account? ", h("a", { href: "#/login" }, "Sign in")));
      } else {
        var s = h("input", { value: d.school }), m = select(["TKJ", "AK"], d.major), c = h("input", { value: d.class_name, placeholder: "e.g. XI TKJ" }), g = h("textarea", { placeholder: "What would you like to become or learn? (optional)" }, d.goal);
        box.appendChild(h("h2", { style: "text-align:center" }, "Complete your profile")); box.appendChild(field("School", s)); box.appendChild(h("div", { class: "grid g2" }, field("Major (AK / TKJ)", m), field("Class", c)));
        box.appendChild(field("Initial goal", g));
        var code = h("input", { value: d.code, autocomplete: "off", placeholder: "Ask your teacher for the code" });
        if (needCode) box.appendChild(field("School registration code", code));
        box.appendChild(err);
        box.appendChild(h("div", { class: "btns" }, btn("Back", function () { step = 1; draw(); }, "g"), btn("Save and start assessment", function () { d.school = s.value; d.major = m.value; d.class_name = c.value.trim(); d.goal = g.value; d.code = code.value.trim();
          if (!d.class_name) return showErr(err, "Please enter your class.");
          if (needCode && !d.code) return showErr(err, "Please enter the school registration code.");
          api("/api/auth/register", "POST", d).then(function (u) { me = u; syncLang(); go("#/discovery"); }).catch(function (x) { showErr(err, x.message); if (x.status === 409 || x.status === 422) { } }); }, "p")));
      } }
    draw(); plain(box);
  }
  /* Layar wajib ganti password: muncul kalau admin baru saja membuatkan password sementara.
     Selama belum diganti, halaman lain tidak bisa dibuka. */
  function mustChange() {
    var err = errBox();
    var lama = h("input", { type: "password", autocomplete: "current-password", required: true });
    var baru = h("input", { type: "password", autocomplete: "new-password", required: true });
    var ulang = h("input", { type: "password", autocomplete: "new-password", required: true });
    var form = h("form", { class: "auth", onsubmit: function (e) { e.preventDefault(); err.classList.add("hide");
      if (baru.value !== ulang.value) return showErr(err, "The two new passwords do not match.");
      api("/api/me/password", "POST", { current: lama.value, new: baru.value })
        .then(function () { me.must_change_password = false; toast("New password saved"); go("#/dashboard"); })
        .catch(function (x) { showErr(err, x.message); }); } },
      authLogo(),
      h("h2", { style: "text-align:center" }, "Create a new password"),
      h("p", { class: "muted small", style: "text-align:center;margin:0" },
        "The admin created a temporary password for your account. Change it now so only you know it."),
      field("Temporary password from the admin", lama), field("New password", baru), field("Repeat the new password", ulang), err,
      h("button", { class: "btn p", type: "submit" }, "Save new password"),
      h("div", { class: "muted small", style: "text-align:center" }, "At least 8 characters, mix letters and numbers. Do not use your name."));
    plain(form); lama.focus();
  }

  function signedOut() {
    plain(h("div", { class: "auth wide" }, authLogo(), h("h2", null, "You have been signed out"), h("p", { class: "muted" }, "Your session has ended safely."),
      h("div", { class: "btns" }, btn("Sign in again", function () { go("#/login"); }, "p"), btn("Back to home", function () { go("#/"); }))));
  }

  /* ---------- shared views ---------- */
  function profileView() {
    var err = errBox(), name = h("input", { value: me.name }), p = me.profile || {};
    var school = h("input", { value: p.school || "" }), major = select(["TKJ", "AK"], p.major || "TKJ"), cls = h("input", { value: p.class_name || "" }), goal = h("textarea", null, p.goal || "");
    var kids = [pageHead("Profile"), h("div", { class: "card", style: "max-width:560px" }, field("Name", name), field("Email", h("input", { value: me.email, disabled: true })),
      me.role === "student" ? [field("School", school), h("div", { class: "grid g2" }, field("Major", major), field("Class", cls)), field("Goal", goal)] : null, err,
      btn("Save changes", function () { err.classList.add("hide");
        api("/api/me/profile", "PUT", { name: name.value, school: school.value, major: me.role === "student" ? major.value : "", class_name: cls.value, goal: goal.value }).then(function (u) { me = u; toast("Profile saved"); route(); }).catch(function (x) { showErr(err, x.message); }); }, "p"))];
    return h("div", { class: "grid" }, kids);
  }
  function settingsView() {
    var err = errBox(), cur_ = h("input", { type: "password", autocomplete: "current-password" }), nw = h("input", { type: "password", autocomplete: "new-password" });
    return h("div", { class: "grid" }, pageHead("Settings", "Manage your account"), h("div", { class: "card", style: "max-width:560px" }, h("h3", null, "Change password"),
      field("Current password", cur_), field("New password (min. 8 characters)", nw), err,
      btn("Change password", function () { err.classList.add("hide"); api("/api/me/password", "POST", { current: cur_.value, new: nw.value }).then(function () { cur_.value = nw.value = ""; toast("Password changed"); }).catch(function (x) { showErr(err, x.message); }); }, "p")));
  }
  function alumniHome() { return h("div", { class: "grid" }, pageHead("Alumni"), h("div", { class: "card note" }, "Alumni features (Write Content, My Stories) are planned for phase 2. Your account is ready.")); }

  /* ---------- router ---------- */
  function register_(role, pattern, fn) { (views[role] = views[role] || []).push([new RegExp("^" + pattern + "$"), fn]); }
  function route() {
    var hash = location.hash || "#/"; if (hash !== cur) { prev = cur; cur = hash; }
    var path = hash.split("?")[0];
    if (path === "#/" || path === "") { if (me) return go("#/dashboard"); return landing(); }
    if (path === "#/login") return me ? go("#/dashboard") : login();
    if (path === "#/register") return me ? go("#/dashboard") : register();
    if (path === "#/forgot") return me ? go("#/dashboard") : forgot();
    if (path === "#/reset") return me ? go("#/dashboard") : resetView();
    if (path === "#/signedout") return signedOut();
    if (path.indexOf("#/p/") === 0 && M_.publicPortfolio) return M_.publicPortfolio(path.slice(4));
    if (!me) return go("#/login");
    if (me.must_change_password) return mustChange();      // tidak boleh ke mana-mana sebelum diganti
    var list = (views[me.role] || []).concat(views.all || []);
    for (var i = 0; i < list.length; i++) { var m = list[i][0].exec(path); if (m) {
      var main = shell(loading()); var res; try { res = list[i][1](m, hash); } catch (e) { if (window.mettaHeal && window.mettaHeal(e.message)) return; return main.textContent = tr("Error: ") + e.message; }
      Promise.resolve(res).then(function (node) { main.textContent = ""; main.appendChild(node); window.scrollTo(0, 0); }).catch(function (e) { if (window.mettaHeal && window.mettaHeal(e && e.message)) return; main.textContent = ""; main.appendChild(h("div", { class: "err" }, e.message || "Could not load this page")); }); return; } }
    shell(h("div", { class: "card" }, "Page not found.")); 
  }
  function start() {
    window.addEventListener("hashchange", route);
    I18N.onChange(function () { route(); });
    api("/api/me").then(function (u) {
      me = u;
      if (I18N.chosen() && u.lang !== I18N.lang()) api("/api/me/lang", "POST", { lang: I18N.lang() }).catch(function () { });   // pilihan di perangkat ini yang dipakai
      else if (!I18N.chosen() && u.lang) I18N.set(u.lang);                                                                      // belum memilih: ikuti bahasa tersimpan
      route();
    }).catch(function () { me = null; route(); });
  }
  register_("all", "#/profile", function () { return profileView(); });
  register_("all", "#/settings", function () { return settingsView(); });

  var M_ = { h: h, api: api, toast: toast, modal: modal, go: go, back: back, fail: fail, errBox: errBox, showErr: showErr, field: field, btn: btn, chip: chip, bar: bar, card: card, table: table, tabs: tabs, select: select,
    pageHead: pageHead, statusChip: statusChip, countdown: countdown, barChart: barChart, date: date, loading: loading, view: register_, start: start, me: function () { return me; }, route: route,
    logoImg: logoImg, authLogo: authLogo, langSwitch: langSwitch, chooseLang: chooseLang, landingView: null };
  return M_;
})();
