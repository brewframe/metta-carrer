/* Halaman depan Metta Career: cerita yang bergerak mengikuti gulir (scrollytelling).

   Cara kerjanya: tiap "panggung" (.stage) tinggi sekali, dan isinya (.pin) menempel di layar. Saat halaman
   digulir, JS hanya menghitung seberapa jauh kita sudah berjalan di panggung itu (0 sampai 1) lalu menaruhnya
   di variabel CSS --p. Semua gerakan 3D (tangga M berputar, kartu melayang, lingkaran portal) dihitung CSS dari --p.
   Jadi JS-nya kecil, dan kalau JS gagal, teks tetap terbaca.

   Orang yang memilih "kurangi gerakan" di perangkatnya mendapat versi statis: semua bagian tersusun ke bawah. */
(function () {
  var h = M.h, btn = M.btn, tr = I18N.tr;
  var dispose = null;

  /* Teks dengan *kata* ditandai: dipecah jadi potongan biasa dan <em>. Styling em ditentukan CSS per bagian. */
  function rich(src) { return tr(src).split("*").map(function (t, i) { return i % 2 ? h("em", null, t) : t; }); }

  /* Foto: kalau file belum ada, tampil kotak pengganti supaya tata letak tidak rusak. */
  var WEBP = { ak: 1, alumni: 1, guru: 1 }, LATER = ["prestasi", "alumni", "ak", "tkj", "guru"];
  function photo(name, alt, w, hgt, eager) {
    var hero = name === "belajar", base = "static/photos/" + name;
    var img = h("img", { src: hero ? base + "-1200.jpg" : base + ".jpg", alt: alt, width: w, height: hgt, decoding: "async", loading: eager ? "eager" : "lazy", draggable: "false" });
    if (hero) { img.setAttribute("srcset", base + "-480.jpg 480w, " + base + "-800.jpg 800w, " + base + "-1200.jpg 1200w, " + base + "-1600.jpg 1600w, " + base + "-2400.jpg 2400w, " + base + "-3840.jpg 3840w"); img.setAttribute("sizes", "100vw"); }
    if (!hero) img.setAttribute("srcset", base + ".jpg 1x, " + base + "-2x.jpg 2x");
    if (eager) img.setAttribute("fetchpriority", "high");
    var out = img;
    if (hero || WEBP[name]) {            // WebP kalau browser mendukung (lebih kecil, lebih cepat), JPG sebagai cadangan
      var src = h("source", { type: "image/webp" });
      src.setAttribute("srcset", hero ? base + "-480.webp 480w, " + base + "-800.webp 800w, " + base + "-1200.webp 1200w, " + base + "-1600.webp 1600w, " + base + "-2400.webp 2400w, " + base + "-3840.webp 3840w" : base + ".webp " + "1x, " + base + "-2x.webp 2x"); if (hero) src.setAttribute("sizes", "100vw");
      out = h("picture", null, src, img);
    }
    img.addEventListener("error", function () {
      var ph = h("div", { class: "ph", role: "img", "aria-label": alt }, h("span", null, "Photo goes here"));
      if (out.parentNode) out.parentNode.replaceChild(ph, out);
    });
    return out;
  }
  /* Foto lain dimuat diam-diam setelah halaman siap, supaya tidak muncul terlambat saat di-scroll. */
  function warmPhotos() { var go = function () { LATER.forEach(function (n) { var i = new Image(); i.decoding = "async"; i.src = "static/photos/" + n + ".jpg"; if (WEBP[n]) { var j = new Image(); j.src = "static/photos/" + n + ".webp"; } }); };
    if (window.requestIdleCallback) requestIdleCallback(go, { timeout: 2500 }); else setTimeout(go, 1200); }
  if (document.readyState === "complete") warmPhotos(); else window.addEventListener("load", warmPhotos);

  /* Tangga "M" 3D dari balok. Tampak depan membentuk huruf M bertingkat seperti logo; saat digulir ia berputar. */
  function stairs() {
    /* [x, lebar, dasar, atas, penutup oranye?] dalam px. Dari depan: dua kaki, dua anak tangga, dan lembah tengah = huruf M di logo. */
    var cols = [[0, 59, 0, 231], [59, 30, 119, 185], [89, 86, 73, 139], [175, 30, 119, 185], [205, 59, 0, 185], [205, 59, 185, 231, "cap"]];
    var box = h("div", { class: "stairs", "aria-hidden": "true" });
    cols.forEach(function (c) {
      box.appendChild(h("div", { class: "blk " + (c[4] || ""), style: "--x:" + c[0] + "px;--w:" + c[1] + "px;--z0:" + c[2] + "px;--z1:" + c[3] + "px" }, h("i", { class: "t" }), h("i", { class: "f" }), h("i", { class: "r" })));
    });
    return h("div", { class: "stairs-wrap", "aria-hidden": "true" }, h("div", { class: "ground" }), box);
  }

  /* Kartu karier yang melayang di sekitar tangga. Hanya hiasan, jadi tanpa angka persentase buatan. */
  function floatCards() {
    var data = [
      ["Network Administrator", "Linux, Cisco, Security", "a"], ["Accountant", "Excel, Tax, Reports", "b"], ["Data Analyst", "SQL, Python, Charts", "c"],
      ["Cybersecurity Analyst", "Networks, Logs, Audit", "d"], ["UI Designer", "Layout, Color, Prototype", "e"]
    ];
    return data.map(function (d) {
      return h("div", { class: "fc " + d[2], "aria-hidden": "true" }, h("b", null, d[0]), h("span", null, d[1]));
    });
  }

  function chapter(i, step, title, text, name, alt, w, hgt) {
    return { copy: h("div", { class: "chap", style: "opacity:var(--a" + i + ");transform:translate3d(0,calc((1 - var(--a" + i + ")) * 36px),0)" },
        h("span", { class: "stepno", "aria-hidden": "true" }, step), h("h2", null, rich(title)), h("p", null, text)),
      pic: h("figure", { class: "shot", style: "--a:var(--a" + i + ")" }, photo(name, alt, w, hgt), h("figcaption", null, alt)) };
  }

  /* Bar atas yang sama dipakai halaman depan dan halaman masuk/daftar. */
  function header() {
    return h("header", { class: "lnav" },
      h("a", { href: "#/", class: "brand-link", "aria-label": "Metta Career" }, h("img", { src: "static/brand/logo-horizontal.svg", alt: "Metta Career by Next Steps", width: "170", height: "46" }), h("img", { class: "brand-mark", src: "static/brand/logo-mark.svg", alt: "", width: "36", height: "36" })),
      h("span", { class: "sp" }), M.langSwitch(),
      h("a", { class: "btn", href: "#/login" }, "Sign in"), h("a", { class: "btn p", href: "#/register" }, "Sign up"));
  }

  /* Versi file tampilan yang sedang dipakai browser (dari ?v= pada app.js). Membantu memastikan versi saat ada laporan bug. */
  function buildTag() { var el = document.querySelector('script[src*="static/app.js"]'), v = el && el.src.indexOf("v=") > 0 ? el.src.split("v=")[1] : "";
    var ok = window.M && typeof M.barChart === "function" && typeof M.countdown === "function";
    return v ? tr("Version {0}", v.slice(0, 6)) + (ok ? "" : " (!)") : tr("Old version: press F5"); }
  function footer(slim) {
    function col(title, items) {
      var d = h("details", { class: "fcol", open: window.innerWidth > 760 ? "" : null }, h("summary", null, title), h("ul", null, items.map(function (x) { return h("li", null, x); })));
      return d;
    }
    function link(text, to) { return h("a", { href: to }, text); }
    function act(text, fn) { return h("button", { type: "button", class: "linkbtn", onclick: fn }, text); }
    function info(title, lines) { return function () { M.modal.apply(null, [tr(title)].concat(lines.map(function (l) { return h("p", { class: "small", style: "margin:0" }, l); }))); }; }
    var help = info("Forgot your password?", ["Open Sign in, then Forgot your password, and send a request with your email. Your teacher or the school admin will confirm it is you and give you a one-time code.",
      "Bring your student card. Enter the code on the reset page and choose your own new password. Never share your password or your code in a chat group."]);
    var priv = info("Security & privacy", ["Passwords are stored as one-way hashes, never as plain text.", "Every sign-in attempt is limited and logged, and teachers and admins need longer passwords.",
      "This site loads no ads, trackers or outside scripts.", "Teachers can see their students' progress, and the school decides who gets an account.", "This is a development version. The official privacy policy still needs the school's approval."]);
    var about = info("About this project", ["Metta Career is a school project by Group 2 of SMK Metta Maitreya, with the Next Steps team.", "All numbers on this page come straight from the database."]);
    if (slim) return h("footer", { class: "appfoot" },
      h("span", null, "© 2026 Metta Career · SMK Metta Maitreya · Group 2", h("span", { class: "muted", style: "margin-left:8px;font-size:.78em" }, buildTag())),
      h("span", { class: "sp" }), act("Security & privacy", priv), act("About this project", about),
      h("button", { type: "button", class: "linkbtn", onclick: function () { window.scrollTo({ top: 0, behavior: "smooth" }); } }, "Back to top"));
    return h("footer", { class: "lfoot" },
      h("div", { class: "lfoot-in" },
        h("div", { class: "fbrand" }, h("img", { src: "static/brand/logo-horizontal-dark.svg", alt: "Metta Career by Next Steps", width: "190", height: "52" }),
          h("p", null, "Turning student potential into skills, proof of ability, portfolios and real opportunities."), M.langSwitch("on-dark")),
        col("Get started", [link("Sign up", "#/register"), link("Sign in", "#/login"), link("Forgot your password?", "#/forgot")]),
        col("Who it is for", [h("span", null, "Student"), h("span", null, "Teacher"), h("span", null, "Alumni")]),
        col("Help", [act("How to reset a password", help), act("Security & privacy", priv), act("About this project", about)])),
      h("div", { class: "lfoot-bar" }, h("span", null, "© 2026 Metta Career · SMK Metta Maitreya · Group 2"), h("span", null, "by Next Steps"), motionBtn(),
        h("button", { type: "button", class: "linkbtn", onclick: function () { window.scrollTo({ top: 0, behavior: "smooth" }); } }, "Back to top")));
  }

  function motionOff() { try { return localStorage.getItem("metta-motion") === "off"; } catch (e) { return false; } }
  function setMotion(off) { try { localStorage.setItem("metta-motion", off ? "off" : "on"); } catch (e) { /* tanpa penyimpanan: pilihan berlaku sampai halaman dimuat ulang */ } landing(); }
  function motionBtn() { return h("button", { type: "button", class: "linkbtn", onclick: function () { setMotion(!motionOff()); } }, motionOff() ? "Turn on animations" : "Turn off animations"); }

  function landing() {
    if (dispose) dispose();
    var app = document.getElementById("app"); app.textContent = "";
    /* Animasi selalu menyala. Pengaturan "kurangi gerakan" milik Windows/HP sengaja tidak dipakai di sini karena sering
       tidak sengaja aktif (mode hemat daya, pengaturan animasi mati) dan membuat halaman tampak "kehilangan animasi".
       Siapa pun yang butuh versi tenang bisa menekan tombol "Turn off animations" di footer (tersimpan di browser). */
    var reduce = motionOff();

    /* Angka dibaca dari database. Setiap tempat memakai node sendiri (satu node tidak bisa ada di dua tempat). */
    var numNodes = [];
    function num(key) { var n = h("b", null, "–"); numNodes.push([key, n]); return n; }
    M.api("/api/public/stats").then(function (s) { numNodes.forEach(function (x) { x[1].textContent = s[x[0]]; }); })
      .catch(function () { /* angka tetap strip: lebih baik kosong daripada salah */ });
    /* Kalimat dengan satu angka di tengah: kalimat diterjemahkan utuh, lalu angkanya disisipkan. */
    function withNum(src, node) { var parts = tr(src, "\u0001").split("\u0001"); return [parts[0], node, parts[1] || ""]; }

    var chaps = [
      chapter(0, "2", "Follow the roadmap", "See your skill gap and a step-by-step plan: study, practice, then apply in a mini project.", "tkj", "A TKJ student working with network cables", 736, 981),
      chapter(1, "3", "Prove it", "Submit projects as evidence. Your teacher verifies them and they flow into your portfolio.", "ak", "An AK student reviewing a financial report", 590, 394),
      chapter(2, "4", "Get it verified", "Your teacher reviews each project and leaves feedback. Verified work goes straight into your portfolio.", "guru", "A teacher guiding a student", 900, 900)
    ];

    var nav = header();

    var hero = h("section", { class: "stage hero", id: "top", "data-len": "4.2", "data-ph": "a" },
      h("div", { class: "pin" },
        h("div", { class: "hero-bg", "aria-hidden": "true" }),
        h("div", { class: "hero-grid" },
          h("div", { class: "hero-copy" },
            h("div", { class: "copy a" }, h("h1", null, rich("*Yes,* choosing a career feels confusing.")), h("p", null, "So we built a clearer path."),
              h("div", { class: "btns" }, h("a", { class: "btn p big", href: "#/register" }, "Start as a student"), h("a", { class: "btn big ghost", href: "#/login" }, "I already have an account")),
              h("span", { class: "hint" }, "Scroll to see how")),
            h("div", { class: "copy b" }, h("h2", null, rich("Skip the *confusion*.")), h("p", null, "We only show careers that fit you."))),
          h("div", { class: "scene" }, stairs(), floatCards())),
        h("div", { class: "portal" }, h("div", { class: "portal-mask" }, h("div", { class: "portal-inner" },
          h("div", { class: "portal-img" }, photo("belajar", "Four students studying together with laptops and notebooks", 1200, 800, true)),
          h("div", { class: "portal-cap" }, h("span", { class: "stepno", "aria-hidden": "true" }, "1"), h("h2", null, "Tell us what matters"),
            h("p", null, withNum("Answer {0} Self Discovery questions about your interests and strengths. The result is a suggestion, never a verdict.", num("questions")))))))));

    var how = h("section", { class: "stage how vnotch", "data-len": "4", "data-n": "3", id: "how" },
      h("div", { class: "pin" },
        h("div", { class: "how-grid" },
          h("div", { class: "how-copy" }, chaps.map(function (c) { return c.copy; })),
          h("div", { class: "how-pics" }, chaps.map(function (c) { return c.pic; })))));

    var proof = h("section", { class: "proof" },
      h("div", { class: "proof-in" },
        h("div", { class: "proof-txt" }, h("h2", null, "Proof you can show anyone."), h("p", null, "Verified projects, certificates and achievements are collected into one portfolio. Share it as a link when you apply.")),
        h("figure", { class: "tilt p1" }, photo("prestasi", "Student achievements", 735, 980), h("figcaption", null, "Student achievements")),
        h("figure", { class: "tilt p2" }, photo("alumni", "Graduates tossing their caps into the sky", 735, 981), h("figcaption", null, "Alumni stories are on the way")),
        h("div", { class: "proof-txt b" }, h("h2", null, "Learn from those who went before."), h("p", null, "Alumni will share how they started, what they learned and what they would do again. Read their stories inside the app."))));

    var stats = h("section", { class: "stats vnotch", id: "stats" },
      h("div", { class: "stats-in" }, h("h2", { class: "sr" }, "By the numbers"),
        h("p", { class: "bigline" }, num("careers"), " ", "careers to explore", ", ", num("questions"), " ", "Self Discovery questions", ", ", num("companies"), " ", "internship companies", ", ", num("majors"), " ", "majors: TKJ & AK", "."),
        h("p", { class: "note" }, "Numbers are read from the Metta Career database when this page opens.")));

    var close = h("section", { class: "closing", id: "closing" },
      h("div", { class: "closing-in" },
        h("img", { class: "community", src: "static/brand/community.png", alt: "", width: "132", height: "132", loading: "lazy" }),
        h("h2", null, rich("Choosing a career shouldn't be a *solo* job.")), h("p", null, "Metta Career is made for SMK Metta Maitreya students, guided by their teachers."),
        h("div", { class: "btns" }, h("a", { class: "btn p big", href: "#/register" }, "Start as a student"), h("a", { class: "btn big ghost", href: "#/login" }, "I already have an account"))));

    var sticky = h("a", { class: "sticky-cta", href: "#/register" }, "Start now");
    var root = h("div", { class: "lp" + (reduce ? " static" : "") }, nav, h("main", null, hero, how, proof, stats, close), footer(), sticky);
    app.appendChild(root);

    /* ---------- gerakan ---------- */
    var stages = [].map.call(root.querySelectorAll(".stage"), function (el) {
      var len = parseFloat(el.getAttribute("data-len")) || 3;
      return { el: el, pin: el.querySelector(".pin"), n: parseInt(el.getAttribute("data-n") || "0", 10), len: len, p: -1 };
    });
    var navH = nav.offsetHeight || 64;
    function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
    var raf = 0, closingIn = false;
    /* Gulir dihaluskan: nilai yang ditampilkan (cur) mengejar nilai sebenarnya (target) sedikit demi sedikit,
       jadi satu putaran roda mouse tidak membuat gerakan melompat. Saat sudah dekat, langsung berhenti (hemat daya). */
    var EASE = 0.2, DONE = 0.0006;
    function frame() {
      raf = 0;
      var vh = window.innerHeight, more = false;
      stages.forEach(function (s) {
        var r = s.el.getBoundingClientRect(), run = r.height - s.pin.offsetHeight;
        var target = run > 0 ? clamp((navH - r.top) / run, 0, 1) : 0;
        var p = s.p < 0 ? target : s.p + (target - s.p) * EASE;
        if (Math.abs(target - p) < DONE) p = target; else more = true;
        if (Math.abs(p - s.p) < 0.0002 && p === target) return;
        s.p = p; s.el.style.setProperty("--p", p.toFixed(4));
        if (s.el === hero) s.el.setAttribute("data-ph", target < 0.35 ? "a" : target < 0.66 ? "b" : "c");
        for (var k = 0; k < s.n; k++) {                       // seberapa aktif bab ke-k (1 di tengah jatahnya)
          var a = clamp(1.25 - Math.abs(p * s.n - (k + 0.5)) * 1.7, 0, 1);
          s.el.style.setProperty("--a" + k, a.toFixed(3));
        }
      });
      sticky.classList.toggle("on", window.scrollY > vh * 0.6 && !closingIn);
      if (more) ask();
    }
    function ask() { if (!raf) raf = requestAnimationFrame(frame); }
    var io = null;
    if (!reduce) {
      for (var k = 0; k < 3; k++) how.style.setProperty("--a" + k, k === 0 ? "1" : "0");
      stages.forEach(function (s) { s.el.style.height = "calc((100svh - " + navH + "px) * " + s.len + ")"; s.pin.style.height = "calc(100svh - " + navH + "px)"; s.pin.style.top = navH + "px"; });
      window.addEventListener("scroll", ask, { passive: true }); window.addEventListener("resize", ask);
      if ("IntersectionObserver" in window) { io = new IntersectionObserver(function (es) { closingIn = es[0].isIntersecting; ask(); }, { threshold: 0.25 }); io.observe(close); }
      frame();
    }
    /* Kemiringan foto mengikuti pointer (hanya perangkat dengan mouse). */
    if (!reduce && window.matchMedia && window.matchMedia("(hover:hover)").matches) {
      [].forEach.call(root.querySelectorAll(".tilt"), function (f) {
        f.addEventListener("pointermove", function (e) { var r = f.getBoundingClientRect(); f.style.setProperty("--rx", (((e.clientY - r.top) / r.height - 0.5) * -8).toFixed(2) + "deg"); f.style.setProperty("--ry", (((e.clientX - r.left) / r.width - 0.5) * 10).toFixed(2) + "deg"); });
        f.addEventListener("pointerleave", function () { f.style.setProperty("--rx", "0deg"); f.style.setProperty("--ry", "0deg"); });
      });
    }
    dispose = function () {
      window.removeEventListener("scroll", ask); window.removeEventListener("resize", ask); window.removeEventListener("hashchange", leave);
      if (io) io.disconnect(); if (raf) cancelAnimationFrame(raf); dispose = null;
    };
    function leave() { if (location.hash !== "#/" && location.hash !== "") { if (dispose) dispose(); } }
    window.addEventListener("hashchange", leave);
    window.scrollTo(0, 0);
  }

  M.landingView = landing;
  M.siteHeader = header;
  M.siteFooter = footer;
})();
