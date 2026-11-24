/* Penjaga cache. Dimuat paling awal dengan nama file baru, jadi tidak pernah tertukar dengan versi lama.
   Bila browser ternyata memakai campuran file lama dan baru (contoh: "M.barChart is not a function"),
   semua file tampilan diunduh ulang dari server lalu halaman dimuat ulang SEKALI (dijaga sessionStorage agar tidak berulang). */
(function () {
  var KEY = "metta-cache-heal";
  var FILES = ["i18n.js", "lang.js", "app.js", "student.js", "course.js", "staff.js", "portfolio.js", "alumni.js", "company_data.js", "landing.js", "start.js", "app.css", "landing.css"];
  var NEED = ["h", "api", "view", "route", "countdown", "barChart", "pageHead", "statusChip"];
  function once() { try { if (sessionStorage.getItem(KEY)) return false; sessionStorage.setItem(KEY, String(Date.now())); return true; } catch (e) { return false; } }
  function heal() {
    if (!once()) return false;
    var urls = ["/"];
    FILES.forEach(function (f) { urls.push("/static/" + f); });
    Array.prototype.forEach.call(document.querySelectorAll("script[src],link[rel=stylesheet]"), function (el) { urls.push(el.src || el.href); });
    Promise.all(urls.map(function (u) { return fetch(u, { cache: "reload", credentials: "same-origin" }).catch(function () {}); }))
      .then(function () { location.reload(); });
    return true;
  }
  window.mettaHeal = function (msg) { return /is not a function|is not defined|Cannot read prop/i.test(String(msg || "")) ? heal() : false; };
  window.addEventListener("error", function (e) { window.mettaHeal(e && e.message); });
  window.addEventListener("load", function () {
    var M = window.M;
    if (!M || NEED.some(function (k) { return typeof M[k] !== "function"; })) { heal(); return; }
    setTimeout(function () { try { sessionStorage.removeItem(KEY); } catch (e) {} }, 10000);   // halaman sehat: izinkan perbaikan lagi di update berikutnya
  });
})();
