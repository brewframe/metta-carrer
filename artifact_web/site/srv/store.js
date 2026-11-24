/* Metta Career — "server" di dalam halaman: SQLite (sql.js) + catatan operasi.
   Database dasar (data contoh) + semua operasi yang pernah ditulis, diputar ulang berurutan = keadaan sekarang.
   Catatan operasi disimpan di database bersama Claude (bila pengunjung login dan boleh menulis) atau di browser ini. */
(function (root) {
  "use strict";
  var U = root.MU, S = root.MS, E = root.ME;
  var SQLJS_URL = "https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/sql-asm-memory-growth.js";
  var ARTIFACT_URL = "https://claude.ai/artifact/HchajLqnUyXX7gnx9KTnmN";                      // diisi setelah artifact pertama kali dipublikasikan
  var SENSITIVE = { password: 1, current: 1, "new": 1, new_password: 1, code: 1 };
  var CLIENT_KEY = "metta_client_id", TOKEN_KEY = "metta_token";

  /* ---------- penyimpanan kecil di browser ---------- */
  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) { /* mode privat */ } }
  var CLIENT = lsGet(CLIENT_KEY); if (!CLIENT) { CLIENT = U.tokenHex(4); lsSet(CLIENT_KEY, CLIENT); }
  var memToken = null;
  function getToken() { return lsGet(TOKEN_KEY) || memToken; }
  function setToken(t) { memToken = t; lsSet(TOKEN_KEY, t); }

  /* ---------- adaptor SQLite ---------- */
  function SqlJsAdapter(SQL, bytes) { this.SQL = SQL; this.bytes = bytes; this.now = "2026-01-01 00:00:00"; this.open(); }
  SqlJsAdapter.prototype.open = function () {
    var self = this; if (this.db) try { this.db.close(); } catch (e) {}
    this.db = new this.SQL.Database(this.bytes);
    this.db.create_function("op_now", function () { return self.now; });
    this.db.exec("PRAGMA foreign_keys=ON");
  };
  SqlJsAdapter.prototype.exec = function (sql, params, isRun) {
    try {
      if (/^(BEGIN|COMMIT|ROLLBACK)$/.test(sql)) { this.db.exec(sql); return Promise.resolve({ rows: [], lastId: null }); }
      var st = this.db.prepare(sql), rows = [];
      try {
        st.bind((params || []).map(function (v) { return v === true ? 1 : v === false ? 0 : v === undefined ? null : v; }));
        while (st.step()) rows.push(st.getAsObject());
      } finally { st.free(); }
      var last = null;
      if (isRun) { var r = this.db.exec("SELECT last_insert_rowid() AS id"); last = r.length ? r[0].values[0][0] : null; }
      return Promise.resolve({ rows: rows, lastId: last });
    } catch (e) { return Promise.reject(e); }
  };
  /* adaptor uji (Playwright): SQLite dijalankan di Node lewat fungsi yang diekspos */
  function TestAdapter() { this.now = "2026-01-01 00:00:00"; }
  TestAdapter.prototype.open = function () { return root.__mettaTestExec("__open__", [], false, this.now); };
  TestAdapter.prototype.exec = function (sql, params, isRun) {
    return root.__mettaTestExec(sql, params || [], !!isRun, this.now).then(function (r) { if (r && r.error) throw new Error(r.error); return r; });
  };

  /* ---------- catatan operasi ---------- */
  var adapter = null, applied = [], appliedKeys = {}, seq = 0, mode = "loading", sharedDb = null, chipEl = null, pendingRemote = false;
  var IDB_NAME = "metta-career-ops-v1";
  function idb() {
    return new Promise(function (res, rej) {
      try { var r = indexedDB.open(IDB_NAME, 1); r.onupgradeneeded = function () { r.result.createObjectStore("ops", { keyPath: "k" }); }; r.onsuccess = function () { res(r.result); }; r.onerror = function () { rej(r.error); }; }
      catch (e) { rej(e); }
    });
  }
  var localOps = {
    all: function () { return idb().then(function (d) { return new Promise(function (res, rej) { var q = d.transaction("ops").objectStore("ops").getAll(); q.onsuccess = function () { res(q.result || []); }; q.onerror = function () { rej(q.error); }; }); }).catch(function () { return []; }); },
    put: function (op) { return idb().then(function (d) { return new Promise(function (res, rej) { var t = d.transaction("ops", "readwrite"); t.objectStore("ops").put(op); t.oncomplete = res; t.onerror = function () { rej(t.error); }; }); }).catch(function () { warnOnce("Penyimpanan browser tidak tersedia (mode privat?). Perubahan hanya bertahan sampai halaman ditutup."); }); },
    clear: function () { return idb().then(function (d) { return new Promise(function (res) { var t = d.transaction("ops", "readwrite"); t.objectStore("ops").clear(); t.oncomplete = res; t.onerror = res; }); }).catch(function () {}); }
  };
  function newKey() { seq++; return Date.now().toString(36).padStart(10, "0") + "-" + CLIENT + "-" + seq.toString(36).padStart(4, "0"); }
  function nowParts() { var d = new Date(); return { now: d.toISOString().slice(0, 19).replace("T", " "), ep: d.getTime() / 1000 }; }
  function sanitize(body) {
    if (!body || typeof body !== "object") return body === undefined ? null : body;
    var o = JSON.parse(JSON.stringify(body)); Object.keys(o).forEach(function (k) { if (SENSITIVE[k] && typeof o[k] === "string") o[k] = new Array(o[k].length + 1).join("*"); }); return o;
  }
  async function applyOp(op) {
    adapter.now = op.at;
    await S.dispatch(adapter, { replay: true, op: JSON.parse(JSON.stringify(op)), uid: op.uid, method: op.method, url: op.url, body: op.body === null ? undefined : op.body,
      lang: op.lang, now: op.at, nowEpoch: op.ep, ip: op.ip });
    applied.push(op); appliedKeys[op.k] = 1;
  }
  async function rebuild(ops) {
    await adapter.open(); applied = []; appliedKeys = {};
    Object.keys(root.MFILES || {}).forEach(function (k) { delete root.MFILES[k]; });
    ops = ops.slice().sort(function (a, b) { return a.k < b.k ? -1 : a.k > b.k ? 1 : 0; });
    for (var i = 0; i < ops.length; i++) await applyOp(ops[i]);
  }

  /* ---------- antrean: satu permintaan pada satu waktu (satu koneksi SQLite) ---------- */
  var lock = Promise.resolve();
  function serial(fn) { var p = lock.then(fn, fn); lock = p.catch(function () {}); return p; }

  async function persist(op) {
    if (mode === "shared") {
      try { await sharedDb.collection("ops").doc(op.k).set(op); return; }
      catch (e) {
        if (e && (e.code === "not_granted" || e.code === "permission_denied" || e.code === "not_writer")) {
          await localOps.put(op); await switchToLocal("Akunmu hanya bisa melihat artifact ini, jadi perubahanmu disimpan di browser ini saja.");
          return;
        }
        if (e && e.code === "quota_exceeded") { warnOnce("Database bersama sudah penuh. Perubahan ini hanya tersimpan sampai halaman ditutup."); return; }
        warnOnce("Perubahan belum terkirim ke database bersama (koneksi?). Coba lagi sebentar lagi.");
        return;
      }
    }
    await localOps.put(op);
  }
  async function live(method, url, body, lang) {
    var t = nowParts(); adapter.now = t.now;
    var op = { k: newKey(), at: t.now, ep: t.ep, uid: null, lang: lang || "id", ip: CLIENT, method: method, url: url, body: sanitize(body), rec: [] };
    var res = await S.dispatch(adapter, { method: method, url: url, body: body, token: getToken(), lang: lang, now: t.now, nowEpoch: t.ep, op: op, ip: CLIENT });
    if (res.ctx && res.ctx.setCookie) setToken(res.ctx.setCookie[0]);
    if (res.ctx && res.ctx.clearCookie) setToken(null);
    if (res.wrote) { op.uid = res.uid; applied.push(op); appliedKeys[op.k] = 1; await persist(op); }
    return res;
  }

  /* ---------- database bersama ---------- */
  function waitClaude() {
    return new Promise(function (res) {
      var n = 0; (function tick() { if (root.claude && typeof root.claude.use === "function") return res(root.claude); if (++n > 15) return res(null); setTimeout(tick, 100); })();
    });
  }
  function withTimeout(p, ms) { return Promise.race([p, new Promise(function (res) { setTimeout(function () { res(null); }, ms); })]); }
  async function tryShared() {
    var cl = await waitClaude(); if (!cl) return null;
    var db = await withTimeout(cl.use("db").catch(function () { return null; }), 10000); if (!db) return null;
    var user = await withTimeout(cl.use("user").catch(function () { return null; }), 5000);
    if (user) { var can = await user.can("data.write").catch(function () { return null; }); if (can === false) return { readOnly: true }; }
    return new Promise(function (res) {
      var first = true, timer = setTimeout(function () { if (first) { first = false; res(null); } }, 12000);
      db.collection("ops").orderBy("k").onSnapshot(function (snap) {
        var ops = snap.docs.map(function (d) { return d.data(); });
        if (first) { if (snap.metadata && snap.metadata.fromCache && !ops.length) return; first = false; clearTimeout(timer); res({ db: db, ops: ops }); return; }
        onRemote(ops);
      }, function () { if (first) { first = false; clearTimeout(timer); res(null); } else warnOnce("Sambungan ke database bersama terputus. Muat ulang halaman nanti."); });
    });
  }
  function onRemote(ops) {
    var fresh = ops.filter(function (o) { return !appliedKeys[o.k]; });
    if (!fresh.length) return;
    serial(async function () {
      fresh = fresh.filter(function (o) { return !appliedKeys[o.k]; }); if (!fresh.length) return;
      var last = applied.length ? applied[applied.length - 1].k : "";
      fresh.sort(function (a, b) { return a.k < b.k ? -1 : 1; });
      if (fresh[0].k > last) { for (var i = 0; i < fresh.length; i++) await applyOp(fresh[i]); }
      else await rebuild(applied.concat(fresh));
      pendingRemote = true; drawChip();
    });
  }
  async function switchToLocal(why) {
    mode = "local"; sharedDb = null;
    await rebuild(await localOps.all()); warnOnce(why); drawChip();
  }

  /* ---------- penanda status di pojok layar ---------- */
  var warned = {};
  function warnOnce(t) { if (warned[t]) return; warned[t] = 1; try { if (root.M && root.M.toast) root.M.toast(t); } catch (e) {} if (typeof console !== "undefined") console.warn("[metta]", t); }
  function drawChip() {
    if (typeof document === "undefined") return;
    if (!chipEl) { chipEl = document.createElement("div"); chipEl.className = "mstore"; document.body.appendChild(chipEl); }
    chipEl.textContent = "";
    var label = mode === "shared" ? "Database bersama" : mode === "local" ? "Data di browser ini" : "Menyiapkan data…";
    var b = document.createElement("button"); b.type = "button"; b.className = "mstore-b " + mode; b.textContent = label;
    b.title = mode === "shared" ? "Data tersimpan di database bersama artifact ini: semua orang yang diundang melihat data yang sama." : "Data tersimpan di browser ini saja. Login akun Claude di artifact ini untuk memakai database bersama.";
    b.addEventListener("click", info);
    chipEl.appendChild(b);
    if (pendingRemote) {
      var r = document.createElement("button"); r.type = "button"; r.className = "mstore-b fresh"; r.textContent = "Ada data baru · tampilkan";
      r.addEventListener("click", function () { pendingRemote = false; drawChip(); if (root.M && root.M.go) root.M.go(location.hash || "#/"); });
      chipEl.appendChild(r);
    }
  }
  function info() {
    if (!root.M || !root.M.modal) return;
    var h = root.M.h, body = [
      h("p", null, mode === "shared" ? "Semua perubahan (akun, rencana, project, validasi guru, dan lainnya) tersimpan di database bersama artifact ini. Siapa pun yang kamu undang dan login akun Claude melihat data yang sama."
        : "Semua perubahan tersimpan di browser ini saja. Orang lain dan perangkat lain tidak melihatnya. Login akun Claude dan buka artifact yang sudah dibagikan kepadamu untuk memakai database bersama."),
      h("p", { class: "small muted" }, "Server Python asli tetap ada di folder proyek (run_dev.bat). Versi ini menjalankan logika server yang sama di dalam browser, jadi keamanannya untuk demo, bukan untuk data sungguhan.")];
    if (mode === "local") {
      var sure = h("div", { class: "small", style: "display:none" }, "Yakin? Semua akun baru, project, dan progres di browser ini akan hilang. ", root.M.btn("Ya, hapus", function () { localOps.clear().then(function () { setToken(null); location.reload(); }); }, "s danger"));
      body.push(h("div", null, root.M.btn("Hapus data di browser ini", function () { sure.style.display = "block"; }, "g s")), sure);
    }
    root.M.modal(mode === "shared" ? "Database bersama" : "Data di browser ini", body);
  }

  /* ---------- start ---------- */
  function loadScript(src) { return new Promise(function (res, rej) { var s = document.createElement("script"); s.src = src; s.onload = res; s.onerror = function () { rej(new Error("load " + src)); }; document.head.appendChild(s); }); }
  function getText(u) { return fetch(u).then(function (r) { if (!r.ok) throw new Error(u + " " + r.status); return r.text(); }); }
  async function boot() {
    drawChipSoon();
    var jobs = [getText("data/courses.json"), getText("data/meta.json")];
    if (root.__mettaTestExec) { adapter = new TestAdapter(); await adapter.open(); }
    else {
      var b64 = getText("data/base.db.txt");
      if (typeof root.initSqlJs !== "function") await loadScript(SQLJS_URL);
      var SQL = await root.initSqlJs();
      adapter = new SqlJsAdapter(SQL, U.b64decode((await b64).trim()));
    }
    var data = await Promise.all(jobs);
    E.DATA.courses = JSON.parse(data[0]); E.DATA.meta = JSON.parse(data[1]);
    await S.loadTranslations(adapter);
    var sh = await tryShared();
    if (sh && sh.db) { mode = "shared"; sharedDb = sh.db; await rebuild(sh.ops); }
    else { mode = "local"; await rebuild(await localOps.all()); if (sh && sh.readOnly) warnOnce("Akunmu hanya bisa melihat artifact ini, jadi perubahanmu disimpan di browser ini saja."); }
    drawChip();
  }
  function drawChipSoon() { if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", drawChip); else drawChip(); }
  var ready = null;
  function whenReady() {
    if (!ready) ready = boot().catch(function (e) {
      if (typeof console !== "undefined") console.error("[metta] start gagal", e);
      var d = document.createElement("div"); d.className = "mstore-fail"; d.setAttribute("role", "alert");
      d.textContent = "Mesin database tidak bisa dimuat (" + (e && e.message ? e.message : "kesalahan") + "). Periksa koneksi internet lalu muat ulang halaman.";
      document.body.appendChild(d); throw e;
    });
    return ready;
  }

  /* ---------- pengganti fetch() untuk /api ---------- */
  function respond(status, body) { return { status: status, ok: status >= 200 && status < 300, json: function () { return Promise.resolve(body); } }; }
  var MettaServer = {
    fetch: function (path, opt) {
      opt = opt || {};
      var method = (opt.method || "GET").toUpperCase(), headers = opt.headers || {}, lang = headers["X-Lang"] || headers["x-lang"] || "id";
      var body; if (opt.body !== undefined && opt.body !== null) { try { body = JSON.parse(opt.body); } catch (e) { return Promise.resolve(respond(400, { error: "Request body must be valid JSON" })); } }
      return whenReady().then(function () { return serial(function () { return live(method, path, body, lang); }); })
        .then(function (r) { return respond(r.status, r.body); }, function () { return respond(503, { error: "Could not reach the server. Check your connection and try again." }); });
    },
    openFile: function (fid) {
      return MettaServer.fetch("/api/files/" + fid).then(function (r) { return r.json().then(function (d) {
        if (!r.ok || !d.__file) { if (root.M) root.M.toast(d.error || "File not found"); return; }
        var bytes = U.b64decode(d.__file.b64), blob = new Blob([bytes], { type: d.__file.mime });
        if (d.__file.mime.indexOf("image/") === 0) {
          var url = URL.createObjectURL(blob), img = root.M.h("img", { src: url, alt: d.__file.name, style: "max-width:100%;border-radius:10px" });
          root.M.modal(d.__file.name, img); return;
        }
        var cl = root.claude && root.claude.use ? root.claude.use("downloads") : Promise.resolve(null);
        cl.then(function (dl) {
          if (!dl) { root.M.toast("File PDF tidak bisa diunduh dari tampilan ini."); return; }
          dl.save({ filename: d.__file.name, data: blob }).catch(function (e) { if (e && e.code !== "declined") root.M.toast("File tidak bisa disimpan."); });
        });
      }); });
    },
    publicLink: function (slug) { return (ARTIFACT_URL || String(location.href).split("#")[0]) + "#p-" + slug; },
    maxFileBytes: function () { return mode === "shared" ? 180 * 1024 : null; },
    mode: function () { return mode; },
    ready: whenReady
  };
  root.MettaServer = MettaServer;
  root.MSTORE = MettaServer;
  /* tautan portfolio publik #p-KODE dari luar artifact -> rute aplikasi #/p/KODE */
  try { var m = /^#p-([A-Za-z0-9_-]{10,40})$/.exec(location.hash); if (m) history.replaceState(null, "", "#/p/" + m[1]); } catch (e) {}
  whenReady();
})(window);
