/* Menjalankan backend JS di Node (node:sqlite) supaya bisa dibandingkan dengan server Python asli. */
const fs = require("fs"), path = require("path");
const { DatabaseSync } = require("node:sqlite");
const SITE = path.join(__dirname, "..", "site");
const mem = new Map();
globalThis.localStorage = { getItem: k => (mem.has(k) ? mem.get(k) : null), setItem: (k, v) => mem.set(k, String(v)), removeItem: k => mem.delete(k) };
for (const f of ["util.js", "core.js", "engine.js", "api_auth_student.js", "api_more.js"]) require(path.join(SITE, "srv", f));
const S = globalThis.MS, E = globalThis.ME;
E.DATA.courses = JSON.parse(fs.readFileSync(path.join(SITE, "data", "courses.json"), "utf8"));
E.DATA.meta = JSON.parse(fs.readFileSync(path.join(SITE, "data", "meta.json"), "utf8"));

class NodeAdapter {
  constructor(file) { this.file = file; this.now = "2026-01-01 00:00:00"; this.open(); }
  open() {
    const tmp = this.file + ".work-" + process.pid + "-" + Math.random().toString(36).slice(2);
    fs.copyFileSync(this.file, tmp); this.tmp = tmp;
    this.db = new DatabaseSync(tmp); this.db.function("op_now", () => this.now); this.db.exec("PRAGMA foreign_keys=ON");
  }
  close() { try { this.db.close(); fs.unlinkSync(this.tmp); } catch (e) {} }
  async exec(sql, params, isRun) {
    if (/^(BEGIN|COMMIT|ROLLBACK)$/.test(sql)) { this.db.exec(sql); return { rows: [], lastId: null }; }
    const p = (params || []).map(v => (v === true ? 1 : v === false ? 0 : v === undefined ? null : v));
    const st = this.db.prepare(sql);
    if (isRun) { const r = st.run(...p); return { rows: [], lastId: Number(r.lastInsertRowid) }; }
    return { rows: st.all(...p).map(r => Object.assign({}, r)), lastId: null };
  }
}

function nowParts() { const d = new Date(); return { now: d.toISOString().slice(0, 19).replace("T", " "), ep: d.getTime() / 1000 }; }
const SENSITIVE = { password: 1, current: 1, "new": 1, new_password: 1, code: 1 };
function sanitize(body) { if (!body || typeof body !== "object") return body; const o = JSON.parse(JSON.stringify(body)); for (const k in o) if (SENSITIVE[k] && typeof o[k] === "string") o[k] = "*".repeat(o[k].length); return o; }

class JsServer {
  constructor(baseFile) { this.base = baseFile; this.a = new NodeAdapter(baseFile); this.ops = []; this.seq = 0; this.lock = Promise.resolve(); }
  async init() { await S.loadTranslations(this.a); return this; }
  request(token, method, url, body, lang) {
    const run = async () => {
      const t = nowParts(); this.a.now = t.now;
      const op = { k: String(Date.now()).padStart(15, "0") + "-" + String(++this.seq).padStart(6, "0"), at: t.now, ep: t.ep, uid: null, lang: lang || "id", ip: "browser", method, url, body: sanitize(body), rec: [] };
      const res = await S.dispatch(this.a, { method, url, body, token, lang: lang || "id", now: t.now, nowEpoch: t.ep, op, ip: "browser" });
      if (res.wrote) { op.uid = res.uid; this.ops.push(op); }
      return res;
    };
    const p = this.lock.then(run, run); this.lock = p.catch(() => {}); return p;
  }
  async replayFresh() {
    const a = new NodeAdapter(this.base);
    for (const op of this.ops) { a.now = op.at; await S.dispatch(a, { replay: true, op: JSON.parse(JSON.stringify(op)), uid: op.uid, method: op.method, url: op.url, body: op.body, lang: op.lang, now: op.at, nowEpoch: op.ep, ip: op.ip }); }
    return a;
  }
}
function dump(adapter) {
  const out = {};
  for (const { name } of adapter.db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('sessions','rate_events') ORDER BY name").all()) {
    out[name] = adapter.db.prepare("SELECT * FROM " + name + " ORDER BY rowid").all().map(r => Object.assign({}, r));
  }
  return out;
}
module.exports = { JsServer, NodeAdapter, dump, S, E };
