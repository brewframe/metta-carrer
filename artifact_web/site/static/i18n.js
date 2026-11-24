/* Dua bahasa: Indonesia (id) dan Inggris (en).

   Cara kerjanya: teks sumber di kode ditulis dalam bahasa Inggris, dibungkus tr("..."). Terjemahan
   Indonesianya ada di lang.js. Teks yang belum punya terjemahan tampil apa adanya (Inggris), jadi layar
   tidak pernah kosong. Tes di tests/test_lang_ui.py memastikan setiap tr("...") punya terjemahan.

   Tanda {0}, {1} diganti dengan argumen:  tr("Compare ({0})", 2)  ->  "Bandingkan (2)". */
var I18N = (function () {
  var ID = {}, ERR = {}, ERR_RULES = [], listeners = [], cur = "id";

  function stored() { try { var v = localStorage.getItem("metta_lang"); return v === "id" || v === "en" ? v : null; } catch (e) { return null; } }
  function guess() { var n = ((navigator.languages && navigator.languages[0]) || navigator.language || "id").toLowerCase(); return n.indexOf("en") === 0 ? "en" : "id"; }
  cur = stored() || guess();
  if (document.documentElement) document.documentElement.lang = cur;

  function has(src) { return Object.prototype.hasOwnProperty.call(ID, src); }
  function fmt(s, a) { return a.length ? s.replace(/\{(\d+)\}/g, function (m, i) { return a[i] !== undefined ? a[i] : m; }) : s; }
  function tr(src) {
    var a = Array.prototype.slice.call(arguments, 1);
    return fmt(cur === "id" && has(src) ? ID[src] : src, a);
  }
  /* Pesan error dari server (Inggris). Dicocokkan persis dulu, lalu dengan pola untuk pesan yang berisi angka. */
  function err(message) {
    var m = String(message || "");
    if (cur !== "id") return m;
    if (Object.prototype.hasOwnProperty.call(ERR, m)) return ERR[m];
    for (var i = 0; i < ERR_RULES.length; i++) { var r = ERR_RULES[i][0].exec(m); if (r) return ERR_RULES[i][1].apply(null, r.slice(1)); }
    return m;
  }
  function add(dict) { for (var k in dict) if (Object.prototype.hasOwnProperty.call(dict, k)) ID[k] = dict[k]; }
  function addErrors(dict, rules) { for (var k in dict) ERR[k] = dict[k]; (rules || []).forEach(function (r) { ERR_RULES.push(r); }); }
  function lang() { return cur; }
  function set(l) {
    if (l !== "id" && l !== "en") return;
    if (l === cur) return;
    cur = l;
    try { localStorage.setItem("metta_lang", l); } catch (e) { /* mode privat: pilihan tidak disimpan, tetap berfungsi */ }
    document.documentElement.lang = l;
    listeners.forEach(function (f) { f(l); });
  }
  function onChange(f) { listeners.push(f); }
  function keys() { return Object.keys(ID); }
  function chosen() { return stored(); }   // pilihan yang sengaja dibuat pengguna di perangkat ini (null kalau belum pernah memilih)

  return { tr: tr, err: err, add: add, addErrors: addErrors, lang: lang, set: set, onChange: onChange, has: has, keys: keys, chosen: chosen };
})();
