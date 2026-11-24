/* Metta Career — backend di browser: alat bantu (hash, scrypt, acak deterministik, pembulatan gaya Python).
   Semua fungsi di sini sinkron dan tidak bergantung pada DOM, jadi bisa dites juga di Node. */
(function (root) {
  "use strict";
  var U = {};

  /* ---------- teks <-> byte ---------- */
  U.utf8 = function (s) { return new TextEncoder().encode(String(s)); };
  U.hex = function (b) { var s = ""; for (var i = 0; i < b.length; i++) s += (b[i] < 16 ? "0" : "") + b[i].toString(16); return s; };
  U.unhex = function (h) { var o = new Uint8Array(h.length / 2); for (var i = 0; i < o.length; i++) o[i] = parseInt(h.substr(i * 2, 2), 16); return o; };
  U.b64decode = function (s) {
    if (!/^[A-Za-z0-9+/]*={0,2}$/.test(s) || s.length % 4 !== 0) throw new Error("bad base64");
    var bin = atob(s), o = new Uint8Array(bin.length); for (var i = 0; i < bin.length; i++) o[i] = bin.charCodeAt(i); return o;
  };
  U.b64encode = function (b) { var s = "", CH = 0x8000; for (var i = 0; i < b.length; i += CH) s += String.fromCharCode.apply(null, b.subarray(i, i + CH)); return btoa(s); };

  /* ---------- SHA-256 (sinkron) ---------- */
  var K = new Uint32Array([0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]);
  function sha256(msg) {
    if (typeof msg === "string") msg = U.utf8(msg);
    var l = msg.length, nb = ((l + 9 + 63) >> 6) << 6, m = new Uint8Array(nb);
    m.set(msg); m[l] = 0x80; var bits = l * 8;
    m[nb - 4] = (bits >>> 24) & 255; m[nb - 3] = (bits >>> 16) & 255; m[nb - 2] = (bits >>> 8) & 255; m[nb - 1] = bits & 255;
    m[nb - 5] = Math.floor(l / 0x20000000) & 255;
    var H = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19], w = new Uint32Array(64);
    for (var off = 0; off < nb; off += 64) {
      for (var i = 0; i < 16; i++) w[i] = (m[off + i * 4] << 24) | (m[off + i * 4 + 1] << 16) | (m[off + i * 4 + 2] << 8) | m[off + i * 4 + 3];
      for (i = 16; i < 64; i++) {
        var a = w[i - 15], b = w[i - 2];
        var s0 = ((a >>> 7) | (a << 25)) ^ ((a >>> 18) | (a << 14)) ^ (a >>> 3), s1 = ((b >>> 17) | (b << 15)) ^ ((b >>> 19) | (b << 13)) ^ (b >>> 10);
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0;
      }
      var A = H[0], B = H[1], C = H[2], D = H[3], E = H[4], F = H[5], G = H[6], HH = H[7];
      for (i = 0; i < 64; i++) {
        var S1 = ((E >>> 6) | (E << 26)) ^ ((E >>> 11) | (E << 21)) ^ ((E >>> 25) | (E << 7)), ch = (E & F) ^ (~E & G);
        var t1 = (HH + S1 + ch + K[i] + w[i]) | 0;
        var S0 = ((A >>> 2) | (A << 30)) ^ ((A >>> 13) | (A << 19)) ^ ((A >>> 22) | (A << 10)), mj = (A & B) ^ (A & C) ^ (B & C);
        var t2 = (S0 + mj) | 0;
        HH = G; G = F; F = E; E = (D + t1) | 0; D = C; C = B; B = A; A = (t1 + t2) | 0;
      }
      H[0] = (H[0] + A) | 0; H[1] = (H[1] + B) | 0; H[2] = (H[2] + C) | 0; H[3] = (H[3] + D) | 0; H[4] = (H[4] + E) | 0; H[5] = (H[5] + F) | 0; H[6] = (H[6] + G) | 0; H[7] = (H[7] + HH) | 0;
    }
    var out = new Uint8Array(32);
    for (i = 0; i < 8; i++) { out[i * 4] = H[i] >>> 24; out[i * 4 + 1] = (H[i] >>> 16) & 255; out[i * 4 + 2] = (H[i] >>> 8) & 255; out[i * 4 + 3] = H[i] & 255; }
    return out;
  }
  U.sha256 = sha256;
  U.sha256hex = function (s) { return U.hex(sha256(s)); };

  function hmac(key, msg) {
    if (key.length > 64) key = sha256(key);
    var k = new Uint8Array(64); k.set(key);
    var ip = new Uint8Array(64 + msg.length), op = new Uint8Array(96);
    for (var i = 0; i < 64; i++) { ip[i] = k[i] ^ 0x36; op[i] = k[i] ^ 0x5c; }
    ip.set(msg, 64); op.set(sha256(ip), 64); return sha256(op);
  }
  function pbkdf2(pw, salt, iters, dkLen) {
    var out = new Uint8Array(dkLen), blocks = Math.ceil(dkLen / 32);
    for (var b = 1; b <= blocks; b++) {
      var s = new Uint8Array(salt.length + 4); s.set(salt); s[salt.length] = b >>> 24; s[salt.length + 1] = (b >>> 16) & 255; s[salt.length + 2] = (b >>> 8) & 255; s[salt.length + 3] = b & 255;
      var u = hmac(pw, s), t = u.slice();
      for (var i = 1; i < iters; i++) { u = hmac(pw, u); for (var j = 0; j < 32; j++) t[j] ^= u[j]; }
      out.set(t.subarray(0, Math.min(32, dkLen - (b - 1) * 32)), (b - 1) * 32);
    }
    return out;
  }

  /* ---------- scrypt (sama dengan hashlib.scrypt di server Python: n=2^14, r=8, p=1, dklen=32) ---------- */
  function salsa(B) {
    var x = new Uint32Array(B), i;
    function R(a, b) { return (a << b) | (a >>> (32 - b)); }
    for (i = 0; i < 8; i += 2) {
      x[4] ^= R(x[0] + x[12], 7); x[8] ^= R(x[4] + x[0], 9); x[12] ^= R(x[8] + x[4], 13); x[0] ^= R(x[12] + x[8], 18);
      x[9] ^= R(x[5] + x[1], 7); x[13] ^= R(x[9] + x[5], 9); x[1] ^= R(x[13] + x[9], 13); x[5] ^= R(x[1] + x[13], 18);
      x[14] ^= R(x[10] + x[6], 7); x[2] ^= R(x[14] + x[10], 9); x[6] ^= R(x[2] + x[14], 13); x[10] ^= R(x[6] + x[2], 18);
      x[3] ^= R(x[15] + x[11], 7); x[7] ^= R(x[3] + x[15], 9); x[11] ^= R(x[7] + x[3], 13); x[15] ^= R(x[11] + x[7], 18);
      x[1] ^= R(x[0] + x[3], 7); x[2] ^= R(x[1] + x[0], 9); x[3] ^= R(x[2] + x[1], 13); x[0] ^= R(x[3] + x[2], 18);
      x[6] ^= R(x[5] + x[4], 7); x[7] ^= R(x[6] + x[5], 9); x[4] ^= R(x[7] + x[6], 13); x[5] ^= R(x[4] + x[7], 18);
      x[11] ^= R(x[10] + x[9], 7); x[8] ^= R(x[11] + x[10], 9); x[9] ^= R(x[8] + x[11], 13); x[10] ^= R(x[9] + x[8], 18);
      x[12] ^= R(x[15] + x[14], 7); x[13] ^= R(x[12] + x[15], 9); x[14] ^= R(x[13] + x[12], 13); x[15] ^= R(x[14] + x[13], 18);
    }
    for (i = 0; i < 16; i++) B[i] = (B[i] + x[i]) | 0;
  }
  function blockMix(B, Y, r) {
    var X = new Uint32Array(16), i, j;
    X.set(B.subarray((2 * r - 1) * 16, 2 * r * 16));
    for (i = 0; i < 2 * r; i++) {
      for (j = 0; j < 16; j++) X[j] ^= B[i * 16 + j];
      salsa(X);
      Y.set(X, ((i & 1) * r + (i >> 1)) * 16);
    }
  }
  function scrypt(pw, salt, N, r, p, dkLen) {
    var blen = 128 * r, B = pbkdf2(pw, salt, 1, p * blen), words = 32 * r;
    for (var pi = 0; pi < p; pi++) {
      var X = new Uint32Array(words), V = new Uint32Array(words * N), Y = new Uint32Array(words), i, j, off = pi * blen;
      for (i = 0; i < words; i++) X[i] = B[off + i * 4] | (B[off + i * 4 + 1] << 8) | (B[off + i * 4 + 2] << 16) | (B[off + i * 4 + 3] << 24);
      for (i = 0; i < N; i++) { V.set(X, i * words); blockMix(X, Y, r); X.set(Y); }
      for (i = 0; i < N; i++) {
        j = X[(2 * r - 1) * 16] & (N - 1);
        for (var k = 0; k < words; k++) X[k] ^= V[j * words + k];
        blockMix(X, Y, r); X.set(Y);
      }
      for (i = 0; i < words; i++) { B[off + i * 4] = X[i] & 255; B[off + i * 4 + 1] = (X[i] >>> 8) & 255; B[off + i * 4 + 2] = (X[i] >>> 16) & 255; B[off + i * 4 + 3] = X[i] >>> 24; }
    }
    return pbkdf2(pw, B, 1, dkLen);
  }
  U.randomBytes = function (n) { var b = new Uint8Array(n); crypto.getRandomValues(b); return b; };
  U.hashPassword = function (pw) {
    var salt = U.randomBytes(16);
    return "scrypt$" + U.hex(salt) + "$" + U.hex(scrypt(U.utf8(pw), salt, 16384, 8, 1, 32));
  };
  U.verifyPassword = function (pw, stored) {
    try {
      var p = String(stored).split("$"); if (p.length !== 3) return false;
      return U.hex(scrypt(U.utf8(pw), U.unhex(p[1]), 16384, 8, 1, 32)) === p[2];
    } catch (e) { return false; }
  };

  /* ---------- acak ---------- */
  var URLSAFE = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
  U.randbelow = function (n) { var b = new Uint32Array(1), lim = Math.floor(4294967296 / n) * n; do { crypto.getRandomValues(b); } while (b[0] >= lim); return b[0] % n; };
  U.choice = function (s) { return s[U.randbelow(s.length)]; };
  U.tokenHex = function (n) { return U.hex(U.randomBytes(n)); };
  U.tokenUrlsafe = function (n) { var len = Math.ceil(n * 4 / 3), s = ""; for (var i = 0; i < len; i++) s += U.choice(URLSAFE); return s; };
  /* Slug portfolio: hanya huruf dan angka, supaya bisa dipakai sebagai #p-slug di tautan artifact. */
  U.slug = function () { var s = ""; for (var i = 0; i < 16; i++) s += U.choice(URLSAFE.slice(0, 62)); return s; };

  /* Acak yang bisa diulang dari sebuah benih (urutan soal/pilihan harus sama tiap kali dibaca). */
  U.rng = function (seed) {
    var h = sha256("metta-rng:" + seed), a = (h[0] | h[1] << 8 | h[2] << 16 | h[3] << 24) >>> 0, b = (h[4] | h[5] << 8 | h[6] << 16 | h[7] << 24) >>> 0,
        c = (h[8] | h[9] << 8 | h[10] << 16 | h[11] << 24) >>> 0, d = (h[12] | h[13] << 8 | h[14] << 16 | h[15] << 24) >>> 0;
    function next() { a >>>= 0; b >>>= 0; c >>>= 0; d >>>= 0; var t = (a + b) | 0; a = b ^ (b >>> 9); b = (c + (c << 3)) | 0; c = (c << 21) | (c >>> 11); d = (d + 1) | 0; t = (t + d) | 0; c = (c + t) | 0; return (t >>> 0) / 4294967296; }
    for (var i = 0; i < 12; i++) next();
    var R = { random: next };
    R.below = function (n) { return Math.floor(next() * n); };
    R.shuffle = function (arr) { for (var i = arr.length - 1; i > 0; i--) { var j = R.below(i + 1), t = arr[i]; arr[i] = arr[j]; arr[j] = t; } return arr; };
    R.sample = function (pop, k) { var a = pop.slice(); R.shuffle(a); return a.slice(0, k); };
    return R;
  };

  /* ---------- gaya Python ---------- */
  U.pyRound = function (x, nd) {
    if (x === null || x === undefined) return x;
    if (nd) { var f = Math.pow(10, nd); return Number((Math.round(x * f + (x >= 0 ? 1e-9 : -1e-9)) / f).toFixed(nd)); }
    var r = Math.round(x), diff = Math.abs(x - Math.trunc(x));
    if (diff === 0.5) r = 2 * Math.round(x / 2);
    return r === 0 ? 0 : r;
  };
  U.quotePlus = function (s) { return encodeURIComponent(s).replace(/%20/g, "+").replace(/[!'()*~]/g, function (c) { return "%" + c.charCodeAt(0).toString(16).toUpperCase(); }); };
  U.split = function (s) { return String(s).split(/\s+/).filter(Boolean); };          // str.split() tanpa argumen
  U.collapse = function (s) { return U.split(s).join(" "); };                         // " ".join(s.split())
  U.strip = function (s) { return String(s == null ? "" : s).trim(); };
  /* urlparse sederhana: cukup untuk scheme, hostname, username, path */
  U.urlparse = function (s) {
    var m = /^([A-Za-z][A-Za-z0-9+.\-]*):\/\/([^\/?#]*)([^?#]*)/.exec(s), out = { scheme: "", hostname: "", username: "", password: "", path: "" };
    if (!m) { var m2 = /^([A-Za-z][A-Za-z0-9+.\-]*):(.*)$/.exec(s); if (m2) out.scheme = m2[1].toLowerCase(); out.path = m2 ? m2[2] : s; return out; }
    out.scheme = m[1].toLowerCase(); var net = m[2], at = net.lastIndexOf("@");
    if (at >= 0) { var cred = net.slice(0, at); net = net.slice(at + 1); var ci = cred.indexOf(":"); out.username = ci >= 0 ? cred.slice(0, ci) : cred; out.password = ci >= 0 ? cred.slice(ci + 1) : ""; }
    var host = net; if (host[0] === "[") host = host.slice(1, host.indexOf("]")); else host = host.replace(/:\d*$/, "");
    out.hostname = host.toLowerCase(); out.path = m[3]; return out;
  };
  /* sort stabil dengan kunci tuple ala Python: key(x) -> array */
  U.sortBy = function (arr, key) {
    function cmp(a, b) { for (var i = 0; i < a.length; i++) { if (a[i] < b[i]) return -1; if (a[i] > b[i]) return 1; } return 0; }
    return arr.map(function (x, i) { return [key(x), i, x]; }).sort(function (p, q) { return cmp(p[0], q[0]) || (p[1] - q[1]); }).map(function (p) { return p[2]; });
  };
  U.sum = function (a) { var s = 0; for (var i = 0; i < a.length; i++) s += a[i]; return s; };
  U.fmt = function (s, kw) { return String(s).replace(/\{(\w+)\}/g, function (m, k) { return Object.prototype.hasOwnProperty.call(kw, k) ? String(kw[k]) : m; }); };

  root.MU = U;
  if (typeof module !== "undefined") module.exports = U;
})(typeof window !== "undefined" ? window : globalThis);
