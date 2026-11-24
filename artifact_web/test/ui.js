/* Uji tampilan: halaman artifact dibuka di Chromium, SQLite dijalankan di Node (pengganti sql.js yang tidak bisa diunduh di sini). */
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path"), http = require("http");
const { DatabaseSync } = require("node:sqlite");
const SITE = path.join(__dirname, "..", "site"), BASE_DB = path.join(__dirname, "base.db"), OUT = path.join(__dirname, "shots");
fs.mkdirSync(OUT, { recursive: true });
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".txt": "text/plain", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp", ".woff2": "font/woff2", ".woff": "font/woff" };
const PAGE = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>' + fs.readFileSync(path.join(SITE, "metta-career.html"), "utf8") + "</body></html>";
const srv = http.createServer((q, r) => {
  const u = decodeURIComponent(q.url.split("?")[0]);
  if (u === "/" ) { r.writeHead(200, { "content-type": "text/html" }); return r.end(PAGE); }
  const f = path.join(SITE, u); if (!f.startsWith(SITE) || !fs.existsSync(f)) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" }); fs.createReadStream(f).pipe(r);
}).listen(8830);

let db = null, now = "2026-01-01 00:00:00", tmp = path.join(__dirname, "ui-work.db");
function openDb() { try { db && db.close(); } catch (e) {} fs.copyFileSync(BASE_DB, tmp); db = new DatabaseSync(tmp); db.function("op_now", () => now); db.exec("PRAGMA foreign_keys=ON"); }
function execSql(sql, params, isRun, n) {
  now = n;
  try {
    if (sql === "__open__") { openDb(); return { rows: [], lastId: null }; }
    if (/^(BEGIN|COMMIT|ROLLBACK)$/.test(sql)) { db.exec(sql); return { rows: [], lastId: null }; }
    const st = db.prepare(sql), p = params.map(v => (v === true ? 1 : v === false ? 0 : v === undefined ? null : v));
    if (isRun) return { rows: [], lastId: Number(st.run(...p).lastInsertRowid) };
    return { rows: st.all(...p).map(x => Object.assign({}, x)), lastId: null };
  } catch (e) { return { error: e.message }; }
}

const problems = [];
async function newPage(ctx) {
  const p = await ctx.newPage();
  await p.exposeFunction("__mettaTestExec", execSql);
  p.on("pageerror", e => problems.push("pageerror: " + e.message));
  p.on("console", m => { if (m.type() === "error" && !/401|404 \(Not Found\)|Failed to load resource/.test(m.text())) problems.push("console: " + m.text()); });
  await p.route("https://cdnjs.cloudflare.com/**", r => r.abort());
  await p.addInitScript(() => { try { if (!localStorage.getItem("metta_lang")) localStorage.setItem("metta_lang", "en"); } catch (e) {} });
  return p;
}
async function check(p, label) {
  await p.waitForTimeout(250);
  for (let i = 0; i < 40; i++) { if (!(await p.locator(".skel, .loading").count())) break; await p.waitForTimeout(150); }
  const bad = await p.evaluate(() => {
    const t = document.querySelector("#app") ? document.querySelector("#app").innerText : "";
    const errs = Array.from(document.querySelectorAll(".err:not(.hide)")).map(e => e.innerText).filter(Boolean);
    return { errs, nf: /Page not found|Halaman tidak ditemukan|Error: |Something went wrong|Terjadi kesalahan di server|Could not load|Tidak bisa memuat/.test(t), w: document.documentElement.scrollWidth > innerWidth + 1, len: t.length };
  });
  if (bad.errs.length || bad.nf || bad.len < 40) problems.push(label + ": " + JSON.stringify(bad).slice(0, 300));
  return bad;
}
async function login(p, email, pw) {
  await p.goto("http://127.0.0.1:8830/#/login"); await p.waitForSelector("input[type=email]", { timeout: 20000 });
  const tab = { teacher: "Teacher", admin: "Admin", alumni: "Alumni" }[email.split("@")[0]];
  if (tab) await p.locator(".tabs button", { hasText: tab }).first().click();
  await p.fill("input[type=email]", email); await p.fill("input[type=password]", pw); await p.click("button[type=submit]");
  await p.waitForFunction(() => location.hash.indexOf("#/dashboard") === 0, null, { timeout: 20000 });
  await check(p, email + " dashboard");
}
async function visitNav(p, who) {
  const hrefs = await p.evaluate(() => Array.from(document.querySelectorAll("nav a[href^='#/'], .side a[href^='#/']")).map(a => a.getAttribute("href")));
  const uniq = Array.from(new Set(hrefs));
  for (const h of uniq) { await p.evaluate(x => (location.hash = x), h); await check(p, who + " " + h); }
  return uniq;
}

(async () => {
  openDb();
  const b = await chromium.launch(), ctx = await b.newContext({ viewport: { width: 1280, height: 860 } });
  let p = await newPage(ctx);
  const t0 = Date.now();
  await p.goto("http://127.0.0.1:8830/"); await p.waitForFunction(() => document.querySelector(".mstore-b.local"), null, { timeout: 30000 });
  console.log("boot lokal", Date.now() - t0, "ms");
  await check(p, "landing"); await p.screenshot({ path: OUT + "/landing.png" });

  // siswa: semua menu + aksi penting
  await login(p, "student@metta.sch", "Student#2026!");
  console.log("menu siswa:", (await visitNav(p, "siswa")).join(" "));
  await p.evaluate(() => (location.hash = "#/learning")); await check(p, "learning");
  const tid = await p.evaluate(async () => { const r = await (await window.MettaServer.fetch("/api/student/plan", { headers: { "X-Lang": "en" } })).json(); const t = r.milestones.flatMap(m => m.tasks).find(t => t.kind === "STUDY" && t.status !== "COMPLETED"); return t && t.id; });
  await p.evaluate(x => (location.hash = "#/learn/" + x), tid);
  console.log("tombol belajar:", await p.evaluate(() => Array.from(document.querySelectorAll("#app button")).map(x => x.textContent).slice(0, 30).join(" | ")));
  await p.waitForTimeout(600); await check(p, "learn task " + (await p.evaluate(() => location.hash)));
  const steps = p.locator(".step input"); const nSteps = await steps.count();
  for (let i = 0; i < nSteps; i++) { if (!(await steps.nth(i).isChecked())) { await steps.nth(i).click(); await p.waitForTimeout(250); } }
  console.log("langkah dicentang:", nSteps);
  await p.evaluate(() => (location.hash = "#/internship")); await check(p, "internship");
  const mag = await p.evaluate(() => { const t = document.querySelector("#app").innerText; return { google: (t.match(/Google/g) || []).length, ig: (t.match(/Instagram/g) || []).length, maps: (t.match(/Peta|Maps/g) || []).length, form: !!document.getElementById("add-place"), add: /Tambah tempat magang sendiri|Add my own internship place/.test(t) }; });
  console.log("magang:", JSON.stringify(mag));
  await p.screenshot({ path: OUT + "/magang.png" });
  // buat project lewat form
  await p.evaluate(() => (location.hash = "#/projects")); await check(p, "projects");
  const ti = p.locator("#app input[maxlength='120']").first(); await ti.fill("Proyek uji artifact");
  await p.evaluate(() => { const b = Array.from(document.querySelectorAll("#app button")).find(x => /^Save and send to teacher$/.test(x.textContent)); if (b) b.click(); });
  await p.waitForTimeout(800);
  console.log("pesan form project:", await p.evaluate(() => Array.from(document.querySelectorAll(".err:not(.hide)")).map(e => e.innerText).join(" | ")), await p.evaluate(() => Array.from(document.querySelectorAll("#app button")).map(x => x.textContent).join(" | ").slice(0, 400)));
  const madeProject = await p.evaluate(() => /Proyek uji artifact/.test(document.querySelector("#app").innerText));
  console.log("project dibuat:", madeProject);
  await p.evaluate(() => (location.hash = "#/assistant")); await check(p, "assistant");
  await p.evaluate(() => (location.hash = "#/portfolio")); await check(p, "portfolio"); await p.screenshot({ path: OUT + "/portfolio.png", fullPage: false });

  // muat ulang: data harus tetap ada (diputar ulang dari penyimpanan browser)
  await p.reload(); await p.waitForFunction(() => document.querySelector(".mstore-b.local"), null, { timeout: 30000 });
  await p.evaluate(() => (location.hash = "#/projects")); await p.waitForTimeout(800);
  console.log("project tetap ada setelah muat ulang:", await p.evaluate(() => /Proyek uji artifact/.test(document.querySelector("#app").innerText)));
  await p.evaluate(() => { const b = Array.from(document.querySelectorAll("button")).find(x => /Keluar|Sign out|Log out/.test(x.textContent)); if (b) b.click(); });
  await p.waitForTimeout(500);
  await ctx.clearCookies();
  await p.evaluate(() => { localStorage.removeItem("metta_token"); });

  for (const [email, pw, who] of [["teacher@metta.sch", "Teacher#2026!", "guru"], ["admin@metta.sch", "Admin#2026!", "admin"], ["alumni@metta.sch", "Alumni#2026!", "alumni"]]) {
    await p.evaluate(() => localStorage.removeItem("metta_token")); await p.goto("about:blank");
    await login(p, email, pw);
    console.log("menu " + who + ":", (await visitNav(p, who)).join(" "));
    if (who === "guru") { await p.evaluate(() => (location.hash = "#/validation")); await check(p, "validation"); console.log("antrean validasi memuat project uji:", await p.evaluate(() => /Proyek uji artifact/.test(document.querySelector("#app").innerText))); await p.screenshot({ path: OUT + "/guru-validasi.png" }); }
    if (who === "admin") { await p.evaluate(() => (location.hash = "#/analytics")); await check(p, "admin analytics"); await p.screenshot({ path: OUT + "/admin-analitik.png" }); }
  }
  // tampilan HP
  const m = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 }); const pm = await newPage(m);
  await pm.goto("http://127.0.0.1:8830/"); await pm.waitForFunction(() => document.querySelector(".mstore-b"), null, { timeout: 30000 }); await check(pm, "hp landing");
  await login(pm, "student@metta.sch", "Student#2026!"); await pm.evaluate(() => (location.hash = "#/internship")); await check(pm, "hp internship");
  const ov = await pm.evaluate(() => document.documentElement.scrollWidth); console.log("lebar halaman HP:", ov); await pm.screenshot({ path: OUT + "/hp-magang.png" });
  console.log("\nMASALAH:", problems.length ? "\n" + problems.join("\n") : "tidak ada");
  await b.close(); srv.close(); process.exit(0);
})().catch(e => { console.error(e); process.exit(1); });
