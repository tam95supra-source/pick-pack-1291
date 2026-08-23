var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// src/util.ts
function json(data, status = 200, extra = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...extra }
  });
}
__name(json, "json");
function apiError(code, errorClass, status, retryable = false, messageOrConflict, conflictOrMessage) {
  const body = { ok: false, error: { code, error_class: errorClass, retryable } };
  let message;
  let conflict;
  if (typeof messageOrConflict === "string") message = messageOrConflict;
  else if (messageOrConflict && typeof messageOrConflict === "object") conflict = messageOrConflict;
  if (typeof conflictOrMessage === "string") {
    if (!message) message = conflictOrMessage;
  } else if (conflictOrMessage && typeof conflictOrMessage === "object") conflict = conflictOrMessage;
  else if (conflictOrMessage === null) conflict = null;
  if (message) body.error.message = message;
  if (conflict !== void 0) body.error.conflict = conflict;
  return json(body, status);
}
__name(apiError, "apiError");
function nowIso() {
  return (/* @__PURE__ */ new Date()).toISOString();
}
__name(nowIso, "nowIso");
function b64u(bytes) {
  const arr2 = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  let s = "";
  for (const b of arr2) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}
__name(b64u, "b64u");
function b64uDecode(value) {
  let s = value.replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4) s += "=";
  const raw = atob(s);
  const out = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i2 = 0; i2 < raw.length; i2++) out[i2] = raw.charCodeAt(i2);
  return out;
}
__name(b64uDecode, "b64uDecode");
async function sha256Hex(value) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
__name(sha256Hex, "sha256Hex");
async function hmacB64u(keyBytes, value) {
  const stable = new Uint8Array(new ArrayBuffer(keyBytes.byteLength));
  stable.set(keyBytes);
  const key = await crypto.subtle.importKey("raw", stable.buffer, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return b64u(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(value)));
}
__name(hmacB64u, "hmacB64u");
function constantTimeEqual(a, b) {
  const aa = new TextEncoder().encode(a), bb = new TextEncoder().encode(b), n = Math.max(aa.length, bb.length);
  let diff = aa.length ^ bb.length;
  for (let i2 = 0; i2 < n; i2++) diff |= (aa[i2] ?? 0) ^ (bb[i2] ?? 0);
  return diff === 0;
}
__name(constantTimeEqual, "constantTimeEqual");
function randomB64u(bytes = 32) {
  const out = new Uint8Array(bytes);
  crypto.getRandomValues(out);
  return b64u(out);
}
__name(randomB64u, "randomB64u");
function validIsoDate(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value);
}
__name(validIsoDate, "validIsoDate");
function fold(value) {
  return String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase().trim();
}
__name(fold, "fold");
function workChoice(value) {
  const f = fold(value);
  return f === "PICK" ? "PICK" : f === "PACK" ? "PACK" : "KHONG";
}
__name(workChoice, "workChoice");
function isAvailableLabel(value) {
  return ["KHA DUNG", "NGUYEN VEN", "ACTIVE", "ONLINE", "HOAT DONG"].includes(fold(value));
}
__name(isAvailableLabel, "isAvailableLabel");
function parseVisibleDate(value) {
  const m = String(value).match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  return m && m[1] && m[2] && m[3] ? `${m[3]}-${m[2]}-${m[1]}` : "";
}
__name(parseVisibleDate, "parseVisibleDate");
function visibleToIsoTimestamp(value) {
  const m = String(value).match(/^(\d{2})\/(\d{2})\/(\d{4})(?:\s+(\d{2}):(\d{2})(?::(\d{2}))?)?$/);
  if (!m || !m[1] || !m[2] || !m[3]) return nowIso();
  const iso2 = `${m[3]}-${m[2]}-${m[1]}T${m[4] ?? "00"}:${m[5] ?? "00"}:${m[6] ?? "00"}+07:00`, d = new Date(iso2);
  return Number.isNaN(d.getTime()) ? nowIso() : d.toISOString();
}
__name(visibleToIsoTimestamp, "visibleToIsoTimestamp");
async function readJsonBody(request, maxBytes = 15e5) {
  const len = Number(request.headers.get("content-length") || "0");
  if (len > maxBytes) throw new Error("BODY_TOO_LARGE");
  const text7 = await request.text();
  if (text7.length > maxBytes) throw new Error("BODY_TOO_LARGE");
  return JSON.parse(text7);
}
__name(readJsonBody, "readJsonBody");

// src/auth.ts
function verifierParts(value) {
  const p = String(value || "").split("$");
  if (p.length !== 4) return null;
  const prefix = p[0], iterRaw = p[1], salt = p[2], key = p[3];
  if (prefix !== "pbkdf2_sha256" || !iterRaw || !salt || !key) return null;
  const n = Number(iterRaw);
  if (!Number.isInteger(n) || n < 1e5 || n > 1e6) return null;
  return { iterations: n, salt, key };
}
__name(verifierParts, "verifierParts");
async function createChallenge(db, loginId) {
  const account = await db.prepare("SELECT login_id,verifier,status FROM accounts WHERE login_id=?1").bind(loginId).first();
  const parts = account && account.status === "ACTIVE" ? verifierParts(account.verifier) : null;
  const challengeId = crypto.randomUUID(), challenge = randomB64u(32), fakeSalt = randomB64u(16), expires = Date.now() + 12e4, createdAt = nowIso();
  await db.batch([
    db.prepare("DELETE FROM auth_challenges WHERE expires_at<?1").bind(Date.now()),
    db.prepare("INSERT INTO auth_challenges(challenge_id,login_id,purpose,challenge,expires_at,created_at) VALUES(?1,?2,'LOGIN',?3,?4,?5)").bind(challengeId, loginId, challenge, expires, createdAt)
  ]);
  return { ok: true, challenge_id: challengeId, challenge, algorithm: "pbkdf2_sha256", iterations: parts?.iterations ?? 12e4, salt: parts?.salt ?? fakeSalt };
}
__name(createChallenge, "createChallenge");
async function createSession(db, env, input) {
  const results = await db.batch([
    db.prepare("SELECT challenge_id,login_id,challenge,expires_at FROM auth_challenges WHERE challenge_id=?1 AND login_id=?2 AND purpose='LOGIN'").bind(input.challenge_id, input.login_id),
    db.prepare("SELECT login_id,verifier,verifier_hash,role,display_name,position,email,status FROM accounts WHERE login_id=?1").bind(input.login_id),
    db.prepare("DELETE FROM auth_challenges WHERE challenge_id=?1").bind(input.challenge_id)
  ]);
  const challenge = results[0]?.results?.[0] ?? null, account = results[1]?.results?.[0] ?? null;
  const parts = account ? verifierParts(account.verifier) : null;
  if (!challenge || challenge.expires_at < Date.now() || !account || account.status !== "ACTIVE" || !parts) return { ok: false, error: { code: "INVALID_CREDENTIALS", error_class: "AUTH", retryable: false } };
  const expected = await hmacB64u(b64uDecode(parts.key), challenge.challenge);
  if (!constantTimeEqual(expected, input.proof)) return { ok: false, error: { code: "INVALID_CREDENTIALS", error_class: "AUTH", retryable: false } };
  const deviceId = String(input.device_id || "").trim().slice(0, 180);
  if (!deviceId) return { ok: false, error: { code: "DEVICE_ID_REQUIRED", error_class: "VALIDATION", retryable: false } };
  const kind = String(input.client_source || "").toUpperCase() === "WEB" ? "WEB" : "PDA";
  const currentPda = kind === "PDA" ? await db.prepare("SELECT session_id,device_id FROM auth_sessions WHERE login_id=?1").bind(account.login_id).first() : null;
  const sessionId = kind === "PDA" && currentPda?.device_id === deviceId && currentPda.session_id ? currentPda.session_id : crypto.randomUUID(), issuedAt = nowIso();
  if (kind === "WEB") {
    await db.prepare(`INSERT INTO auth_web_sessions(login_id,session_id,device_id,issued_at) VALUES(?1,?2,?3,?4)
      ON CONFLICT(login_id) DO UPDATE SET session_id=excluded.session_id,device_id=excluded.device_id,issued_at=excluded.issued_at`).bind(account.login_id, sessionId, deviceId, issuedAt).run();
  } else {
    await db.prepare(`INSERT INTO auth_sessions(login_id,session_id,device_id,issued_at) VALUES(?1,?2,?3,?4)
      ON CONFLICT(login_id) DO UPDATE SET session_id=excluded.session_id,device_id=excluded.device_id,issued_at=excluded.issued_at`).bind(account.login_id, sessionId, deviceId, issuedAt).run();
  }
  const payload3 = { l: account.login_id, r: account.role, v: account.verifier_hash, s: sessionId, d: deviceId, c: kind };
  const encoded = b64u(new TextEncoder().encode(JSON.stringify(payload3))), sig = await hmacB64u(new TextEncoder().encode(env.SERVICE_TOKEN_SECRET), encoded);
  return { ok: true, token: `${encoded}.${sig}`, account: { login_id: account.login_id, role: account.role, display_name: account.display_name, position: account.position, email: account.email }, session: { issued_at: issuedAt, device_label: String(input.device_label || "").slice(0, 120), kind } };
}
__name(createSession, "createSession");
async function authenticate(db, env, request) {
  const auth4 = request.headers.get("authorization") || "";
  if (!auth4.startsWith("Bearer ")) return null;
  const token3 = auth4.slice(7), parts = token3.split(".");
  if (parts.length !== 2) return null;
  const encoded = parts[0], signature = parts[1];
  if (!encoded || !signature) return null;
  const expected = await hmacB64u(new TextEncoder().encode(env.SERVICE_TOKEN_SECRET), encoded);
  if (!constantTimeEqual(expected, signature)) return null;
  let payload3;
  try {
    payload3 = JSON.parse(new TextDecoder().decode(b64uDecode(encoded)));
  } catch {
    return null;
  }
  const kind = payload3.c === "WEB" ? "WEB" : "PDA";
  const sessionQuery = kind === "WEB" ? db.prepare("SELECT session_id,device_id FROM auth_web_sessions WHERE login_id=?1").bind(payload3.l) : db.prepare("SELECT session_id,device_id FROM auth_sessions WHERE login_id=?1").bind(payload3.l);
  const results = await db.batch([
    db.prepare("SELECT login_id,role,display_name,verifier_hash,status FROM accounts WHERE login_id=?1").bind(payload3.l),
    sessionQuery
  ]);
  const account = results[0]?.results?.[0] ?? null;
  const session = results[1]?.results?.[0] ?? null;
  if (!account || account.status !== "ACTIVE" || account.role !== payload3.r || account.verifier_hash !== payload3.v || !session || session.session_id !== payload3.s || session.device_id !== payload3.d) return null;
  return { login_id: account.login_id, role: account.role, display_name: account.display_name, device_id: session.device_id, session_id: session.session_id, verifier_hash: account.verifier_hash, session_kind: kind };
}
__name(authenticate, "authenticate");
async function logout(db, auth4) {
  if (auth4.session_kind === "WEB") await db.prepare("DELETE FROM auth_web_sessions WHERE login_id=?1 AND session_id=?2 AND device_id=?3").bind(auth4.login_id, auth4.session_id, auth4.device_id).run();
  else await db.prepare("DELETE FROM auth_sessions WHERE login_id=?1 AND session_id=?2 AND device_id=?3").bind(auth4.login_id, auth4.session_id, auth4.device_id).run();
}
__name(logout, "logout");
async function internalAuthorized(request, env) {
  const token3 = request.headers.get("x-m1-admin-token") || "";
  const a = await sha256Hex(token3), b = await sha256Hex(env.M1_ADMIN_TOKEN);
  return constantTimeEqual(a, b);
}
__name(internalAuthorized, "internalAuthorized");

// src/bootstrap.ts
var EXPECTED = [
  { name: "Danh m\u1EE5c", headers: ["DANH S\xC1CH NH\xC2N S\u1EF0_V\u1ECB tr\xED ch\xEDnh", "DANH S\xC1CH NH\xC2N S\u1EF0_Nh\xE0 cung c\u1EA5p", "DANH S\xC1CH NH\xC2N S\u1EF0_B\u1ED9 ph\u1EADn", "DANH S\xC1CH NH\xC2N S\u1EF0_Site", "DANH S\xC1CH NH\xC2N S\u1EF0_Kho", "DANH S\xC1CH PDA_T\xECnh tr\u1EA1ng", "DANH S\xC1CH USER PICK_T\xECnh tr\u1EA1ng", "DANH S\xC1CH B\xC0N PACK_T\xECnh tr\u1EA1ng", "DANH S\xC1CH USER PACK_T\xECnh tr\u1EA1ng", "RA - V\xC0O TRONG CA_Lo\u1EA1i thao t\xE1c", "V\xC0O - RA TRONG CA_Ca", "C\xD4NG NH\u1EACT_Th\xF4ng tin c\xF4ng nh\u1EADt", "C\xD4NG NH\u1EACT_M\u1ED1c th\u1EDDi gian", "C\xD4NG NH\u1EACT_Tr\u1EA1ng th\xE1i"] },
  { name: "L\u1ECACH S\u1EEC NGHI\u1EC6P V\u1EE4", headers: ["Ng\xE0y", "Session ID", "M\xE3 nh\xE2n vi\xEAn", "H\u1ECD t\xEAn", "Ca", "Lo\u1EA1i s\u1EF1 ki\u1EC7n", "Nh\xE3n s\u1EF1 ki\u1EC7n", "Th\u1EDDi gian", "Ng\u01B0\u1EDDi x\u1EED l\xFD", "Chi ti\u1EBFt", "Event ID", "Ph\u1EA1m vi", "App Revision"] },
  { name: "DANH S\xC1CH PDA", headers: ["Seri PDA", "5 s\u1ED1 cu\u1ED1i Seri", "T\xECnh tr\u1EA1ng", "Ghi ch\xFA"] },
  { name: "DANH S\xC1CH USER PICK", headers: ["S\u1ED1 User", "User Pick", "T\xECnh tr\u1EA1ng", "Ghi ch\xFA"] },
  { name: "DANH S\xC1CH B\xC0N PACK", headers: ["T\xEAn b\xE0n pack", "T\xECnh tr\u1EA1ng"] },
  { name: "DANH S\xC1CH USER PACK", headers: ["T\xEAn b\xE0n pack", "User pack", "User Pack", "T\xECnh tr\u1EA1ng"] },
  { name: "DANH S\xC1CH NH\xC2N S\u1EF0", headers: ["M\xE3 nh\xE2n vi\xEAn", "H\u1ECD v\xE0 t\xEAn", "S\u1ED1 \u0111i\u1EC7n tho\u1EA1i", "V\u1ECB tr\xED ch\xEDnh", "Nh\xE0 cung c\u1EA5p", "B\u1ED9 ph\u1EADn", "Site", "Kho", "Ng\xE0y b\u1EAFt \u0111\u1EA7u l\xE0m vi\u1EC7c", "Ghi ch\xFA", "Ng\u01B0\u1EDDi c\u1EADp nh\u1EADt", "Th\u1EDDi gian c\u1EADp nh\u1EADt"] },
  { name: "RA - V\xC0O TRONG CA", headers: ["Ng\xE0y", "Ca", "M\xE3 nh\xE2n vi\xEAn", "H\u1ECD v\xE0 t\xEAn", "S\u1ED1 \u0111i\u1EC7n tho\u1EA1i", "Nh\xE0 cung c\u1EA5p", "B\u1ED9 ph\u1EADn", "Site", "Kho", "V\u1ECB tr\xED ch\xEDnh", "V\u1ECB tr\xED trong ca", "Seri PDA", "User Pick", "B\xE0n Pack", "User Pack", "Lo\u1EA1i thao t\xE1c", "Ghi ch\xFA", "Ng\u01B0\u1EDDi c\u1EADp nh\u1EADt", "Th\u1EDDi gian c\u1EADp nh\u1EADt", "Event ID", "App action", "App revision"] },
  { name: "C\xD4NG NH\u1EACT", headers: ["Ng\xE0y", "Ca", "M\xE3 nh\xE2n vi\xEAn", "H\u1ECD v\xE0 t\xEAn", "S\u1ED1 \u0111i\u1EC7n tho\u1EA1i", "Nh\xE0 cung c\u1EA5p", "B\u1ED9 ph\u1EADn", "Site", "Kho", "V\u1ECB tr\xED ch\xEDnh", "V\u1ECB tr\xED trong ca", "Th\xF4ng tin c\xF4ng nh\u1EADt", "Th\u1EDDi gian b\u1EAFt \u0111\u1EA7u", "Th\u1EDDi gian k\u1EBFt th\xFAc", "M\u1ED1c th\u1EDDi gian", "Tr\u1EA1ng th\xE1i", "Ghi ch\xFA", "Ng\u01B0\u1EDDi c\u1EADp nh\u1EADt", "Th\u1EDDi gian c\u1EADp nh\u1EADt", "Event ID", "Finish Event ID", "App revision", "Kh\u1EA5u tr\u1EEB nh\xE2n s\u1EF1"] },
  { name: "Danh s\xE1ch Admin", headers: ["S\u1ED1 User", "Password verifier", "T\xECnh tr\u1EA1ng", "Ghi ch\xFA", "V\u1ECB tr\xED", "Mail", "Logic quy\u1EC1n c\u01A1 b\u1EA3n", "", "Tr\u1EA1ng th\xE1i t\xE0i kho\u1EA3n", "Ng\u01B0\u1EDDi c\u1EADp nh\u1EADt", "Th\u1EDDi gian c\u1EADp nh\u1EADt"] }
];
async function token(env) {
  const body = new URLSearchParams({ client_id: env.GOOGLE_OAUTH_CLIENT_ID, client_secret: env.GOOGLE_OAUTH_CLIENT_SECRET, refresh_token: env.GOOGLE_OAUTH_REFRESH_TOKEN, grant_type: "refresh_token" });
  const r = await fetch("https://oauth2.googleapis.com/token", { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" }, body });
  const j = await r.json();
  if (!r.ok || !j.access_token) throw new Error(`GOOGLE_OAUTH:${j.error ?? r.status}`);
  return j.access_token;
}
__name(token, "token");
function auth(t) {
  return { authorization: `Bearer ${t}` };
}
__name(auth, "auth");
function q(name) {
  return `'${name.replace(/'/g, "''")}'`;
}
__name(q, "q");
function obj(headers, row) {
  const o = {};
  headers.forEach((h, i2) => {
    if (h) o[h] = String(row[i2] ?? "").trim();
  });
  return o;
}
__name(obj, "obj");
function normRow(row, n) {
  return Array.from({ length: n }, (_, i2) => String(row[i2] ?? "").trim());
}
__name(normRow, "normRow");
function activeStatus(v) {
  return isAvailableLabel(v) || ["ACTIVE", "HOAT DONG", "DANG HOAT DONG"].includes(fold(v)) ? "ACTIVE" : "DISABLED";
}
__name(activeStatus, "activeStatus");
function role(v) {
  const f = fold(v);
  return f === "SUPERADMIN" ? "SUPERADMIN" : f === "ADMIN" ? "ADMIN" : "USER";
}
__name(role, "role");
async function runChunks(db, stmts, size = 50) {
  for (let i2 = 0; i2 < stmts.length; i2 += size) await db.batch(stmts.slice(i2, i2 + size));
}
__name(runChunks, "runChunks");
async function fetchWorkbook(env) {
  const t = await token(env), id = env.GOOGLE_SOURCE_SHEET_ID;
  const metaR = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}?fields=properties.title,sheets.properties.title`, { headers: auth(t) });
  if (!metaR.ok) throw new Error(`GOOGLE_SOURCE_META:${metaR.status}`);
  const meta3 = await metaR.json();
  const title = String(meta3.properties?.title ?? "");
  if (title !== "D\u1EEE LI\u1EC6U THEO NG\xC0Y") throw new Error(`SOURCE_TITLE_MISMATCH:${title}`);
  const actual = (meta3.sheets ?? []).map((x2) => x2.properties?.title ?? "").filter(Boolean);
  const expected = EXPECTED.map((x2) => x2.name);
  if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error(`SOURCE_TABS_MISMATCH:${JSON.stringify(actual)}`);
  const params = EXPECTED.map((x2) => `ranges=${encodeURIComponent(`${q(x2.name)}!A:AZ`)}`).join("&");
  const valuesR = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}/values:batchGet?majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE&${params}`, { headers: auth(t) });
  if (!valuesR.ok) throw new Error(`GOOGLE_SOURCE_VALUES:${valuesR.status}`);
  const values = await valuesR.json();
  const tables = /* @__PURE__ */ new Map(), sheetReport = [];
  for (let i2 = 0; i2 < EXPECTED.length; i2++) {
    const spec = EXPECTED[i2];
    const raw = values.valueRanges?.[i2]?.values ?? [];
    const header = normRow(raw[0] ?? [], spec.headers.length);
    if (JSON.stringify(header) !== JSON.stringify(spec.headers)) throw new Error(`SOURCE_HEADERS_MISMATCH:${spec.name}:${JSON.stringify(header)}`);
    const rows2 = raw.slice(1).map((r) => normRow(r, spec.headers.length)).filter((r) => r.some(Boolean));
    const checks = [];
    for (const r of rows2) checks.push(await sha256Hex(JSON.stringify(r)));
    const checksum2 = await sha256Hex(checks.join("\n"));
    tables.set(spec.name, { headers: header, rows: rows2, objects: rows2.map((r) => obj(header, r)), rowChecksums: checks });
    sheetReport.push({ name: spec.name, row_count: rows2.length, checksum: checksum2 });
  }
  return { title, tables, sheetReport };
}
__name(fetchWorkbook, "fetchWorkbook");
async function bootstrapFromGoogle(db, env) {
  const a = await db.prepare("SELECT scope,mode FROM authority_state WHERE singleton_id=1").first();
  if (a?.scope !== "STAGING_SHADOW") throw new Error("BOOTSTRAP_ONLY_ALLOWED_IN_STAGING_SHADOW");
  const started = nowIso(), runId = crypto.randomUUID();
  await db.prepare("INSERT INTO bootstrap_runs(run_id,source_title,source_sheet_identity,started_at,status,manifest_json) VALUES(?1,'D\u1EEE LI\u1EC6U THEO NG\xC0Y',?2,?3,'RUNNING',?4)").bind(runId, env.GOOGLE_SOURCE_SHEET_ID, started, JSON.stringify({ schema_version: 1, tabs: EXPECTED.map((x2) => x2.name) })).run();
  try {
    const wb = await fetchWorkbook(env), tables = wb.tables;
    const sourceStmts = [db.prepare("DELETE FROM source_rows")];
    for (const spec of EXPECTED) {
      const table = tables.get(spec.name);
      table.rows.forEach((r, i2) => sourceStmts.push(db.prepare("INSERT INTO source_rows(sheet_name,row_index,row_checksum,row_json,import_run_id) VALUES(?1,?2,?3,?4,?5)").bind(spec.name, i2 + 2, table.rowChecksums[i2], JSON.stringify(r), runId)));
    }
    await runChunks(db, sourceStmts);
    const catalog = tables.get("Danh m\u1EE5c");
    const catStmts = [db.prepare("DELETE FROM catalog_values")];
    catalog.headers.forEach((h, c) => {
      const seen = /* @__PURE__ */ new Set();
      for (let r = 0; r < catalog.rows.length; r++) {
        const v = catalog.rows[r]?.[c] ?? "";
        if (!v || seen.has(v)) continue;
        seen.add(v);
        catStmts.push(db.prepare("INSERT INTO catalog_values(namespace,ordinal,value,source_checksum) VALUES(?1,?2,?3,?4)").bind(h, seen.size, v, catalog.rowChecksums[r]));
      }
    });
    await runChunks(db, catStmts);
    const staff = tables.get("DANH S\xC1CH NH\xC2N S\u1EF0");
    const staffStmts = [db.prepare("DELETE FROM employees")];
    staff.objects.forEach((r, i2) => {
      const mnv = r["M\xE3 nh\xE2n vi\xEAn"] || "";
      if (!mnv) return;
      staffStmts.push(db.prepare("INSERT INTO employees(mnv,full_name,phone,main_position,supplier,department,site,warehouse,start_date,note,source_row,source_checksum) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12)").bind(mnv, r["H\u1ECD v\xE0 t\xEAn"] || "", r["S\u1ED1 \u0111i\u1EC7n tho\u1EA1i"] || "", r["V\u1ECB tr\xED ch\xEDnh"] || "", r["Nh\xE0 cung c\u1EA5p"] || "", r["B\u1ED9 ph\u1EADn"] || "", r["Site"] || "", r["Kho"] || "", r["Ng\xE0y b\u1EAFt \u0111\u1EA7u l\xE0m vi\u1EC7c"] || "", r["Ghi ch\xFA"] || "", i2 + 2, staff.rowChecksums[i2]));
    });
    await runChunks(db, staffStmts);
    const resStmts = [db.prepare("DELETE FROM resources"), db.prepare("DELETE FROM resource_pack_map")];
    const addResource = /* @__PURE__ */ __name((sheet, type, idField) => {
      const t = tables.get(sheet);
      t.objects.forEach((r, i2) => {
        const id = r[idField] || "";
        if (!id) return;
        resStmts.push(db.prepare("INSERT INTO resources(resource_type,resource_id,status_label,available,metadata_json,source_row,source_checksum) VALUES(?1,?2,?3,?4,?5,?6,?7)").bind(type, id, r["T\xECnh tr\u1EA1ng"] || "", isAvailableLabel(r["T\xECnh tr\u1EA1ng"]) ? 1 : 0, JSON.stringify(r), i2 + 2, t.rowChecksums[i2]));
      });
    }, "addResource");
    addResource("DANH S\xC1CH PDA", "PDA", "Seri PDA");
    addResource("DANH S\xC1CH USER PICK", "USER_PICK", "User Pick");
    addResource("DANH S\xC1CH B\xC0N PACK", "PACK_TABLE", "T\xEAn b\xE0n pack");
    addResource("DANH S\xC1CH USER PACK", "USER_PACK", "User Pack");
    const packs = tables.get("DANH S\xC1CH USER PACK");
    packs.objects.forEach((r, i2) => {
      const table = r["T\xEAn b\xE0n pack"] || "", user = r["User Pack"] || "", label2 = r["User pack"] || "";
      if (!table || !user) return;
      const f = fold(label2), shift = f.startsWith("CA 1-") ? "Ca 1" : f.startsWith("CA 2-") ? "Ca 2" : f.startsWith("HP-") || fold(table) === "HP" ? "Ca HC" : "";
      if (!shift) return;
      resStmts.push(db.prepare("INSERT OR REPLACE INTO resource_pack_map(pack_table,shift,user_pack,label,available,source_row,source_checksum) VALUES(?1,?2,?3,?4,?5,?6,?7)").bind(table, shift, user, label2, isAvailableLabel(r["T\xECnh tr\u1EA1ng"]) ? 1 : 0, i2 + 2, packs.rowChecksums[i2]));
    });
    await runChunks(db, resStmts);
    const admins = tables.get("Danh s\xE1ch Admin");
    const accountStmts = [db.prepare("DELETE FROM auth_sessions"), db.prepare("DELETE FROM auth_challenges"), db.prepare("DELETE FROM accounts WHERE is_shadow_test=0")];
    for (let i2 = 0; i2 < admins.objects.length; i2++) {
      const r = admins.objects[i2], login = r["S\u1ED1 User"] || "", verifier = r["Password verifier"] || "";
      if (!login || !verifier) continue;
      const rr = role(r["V\u1ECB tr\xED"] || "");
      accountStmts.push(db.prepare("INSERT INTO accounts(login_id,verifier,verifier_hash,role,display_name,position,email,status,source_row,source_checksum,is_shadow_test) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,0)").bind(login, verifier, await sha256Hex(verifier), rr, login, rr.toLowerCase(), r["Mail"] || "", activeStatus(r["Tr\u1EA1ng th\xE1i t\xE0i kho\u1EA3n"] || r["T\xECnh tr\u1EA1ng"] || ""), i2 + 2, admins.rowChecksums[i2]));
    }
    await runChunks(db, accountStmts);
    const ra = tables.get("RA - V\xC0O TRONG CA"), labor = tables.get("C\xD4NG NH\u1EACT");
    const dates = /* @__PURE__ */ new Set();
    for (const r of [...ra.objects, ...labor.objects]) {
      const d = parseVisibleDate(r["Ng\xE0y"] || "");
      if (d) dates.add(d);
    }
    const sorted = [...dates].sort();
    const dateStmts = [db.prepare("DELETE FROM business_dates")];
    sorted.forEach((d, i2) => dateStmts.push(db.prepare("INSERT INTO business_dates(business_date,sequence_no,source) VALUES(?1,?2,'GOOGLE_BOOTSTRAP')").bind(d, i2 + 1)));
    await runChunks(db, dateStmts);
    const attendanceMap = /* @__PURE__ */ new Map();
    ra.objects.forEach((o, i2) => {
      const d = parseVisibleDate(o["Ng\xE0y"] || ""), m = o["M\xE3 nh\xE2n vi\xEAn"] || "";
      if (!d || !m) return;
      const k = `${d}|${m}`, x2 = attendanceMap.get(k) ?? { date: d, mnv: m, rows: [] };
      x2.rows.push({ o, idx: i2 });
      attendanceMap.set(k, x2);
    });
    const attStmts = [db.prepare("DELETE FROM resource_leases"), db.prepare("DELETE FROM resource_daily_consumption"), db.prepare("DELETE FROM attendance_sessions")];
    for (const x2 of attendanceMap.values()) {
      const last = x2.rows[x2.rows.length - 1], first = x2.rows[0], action = fold(last.o["Lo\u1EA1i thao t\xE1c"] || last.o["App action"] || ""), ended = action.includes("RA") && !action.includes("VAO"), sid = `BOOTSTRAP:${x2.date}:${x2.mnv}`;
      const pda = last.o["Seri PDA"] || "", pick = last.o["User Pick"] || "", table = last.o["B\xE0n Pack"] || "", pack = last.o["User Pack"] || "";
      attStmts.push(db.prepare("INSERT INTO attendance_sessions(session_id,mnv,business_date,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,enter_at,exit_at,entered_by,exited_by,version,source_last_row,updated_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,'GOOGLE_BOOTSTRAP',?13,?14,?15,?16)").bind(sid, x2.mnv, x2.date, last.o["Ca"] || "", workChoice(last.o["V\u1ECB tr\xED trong ca"]), ended ? "ENDED" : "ACTIVE", pda || null, pick || null, table || null, pack || null, visibleToIsoTimestamp(first.o["Th\u1EDDi gian c\u1EADp nh\u1EADt"] || ""), ended ? visibleToIsoTimestamp(last.o["Th\u1EDDi gian c\u1EADp nh\u1EADt"] || "") : null, ended ? "GOOGLE_BOOTSTRAP" : null, x2.rows.length, last.idx + 2, visibleToIsoTimestamp(last.o["Th\u1EDDi gian c\u1EADp nh\u1EADt"] || "")));
      if (!ended) {
        for (const [type, id] of [["PDA", pda], ["USER_PICK", pick], ["PACK_TABLE", table], ["USER_PACK", pack]]) if (id) attStmts.push(db.prepare("INSERT OR IGNORE INTO resource_leases(resource_type,resource_id,session_id,mnv,business_date,acquired_event_id,acquired_at) VALUES(?1,?2,?3,?4,?5,?6,?7)").bind(type, id, sid, x2.mnv, x2.date, `BOOTSTRAP:${x2.date}:${x2.mnv}:${type}`, nowIso()));
      }
    }
    await runChunks(db, attStmts);
    const laborStmts = [db.prepare("DELETE FROM labor_sessions")];
    for (let i2 = 0; i2 < labor.objects.length; i2++) {
      const r = labor.objects[i2], d = parseVisibleDate(r["Ng\xE0y"] || ""), m = r["M\xE3 nh\xE2n vi\xEAn"] || "";
      if (!d || !m) continue;
      const startId = r["Event ID"] || `BOOTSTRAP-LABOR:${d}:${m}:${i2 + 2}`, finishId = r["Finish Event ID"] || null, status = fold(r["Tr\u1EA1ng th\xE1i"] || ""), state = status.includes("HOAN") || status.includes("COMPLET") || Boolean(finishId) ? "COMPLETED" : "OPEN";
      laborStmts.push(db.prepare("INSERT OR REPLACE INTO labor_sessions(labor_id,mnv,business_date,shift,labor_type,time_marker,state,start_at,end_at,note,deduct_staff,start_event_id,finish_event_id,version,source_row,updated_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16)").bind(startId, m, d, r["Ca"] || "", r["Th\xF4ng tin c\xF4ng nh\u1EADt"] || "", r["M\u1ED1c th\u1EDDi gian"] || "", state, visibleToIsoTimestamp(r["Th\u1EDDi gian b\u1EAFt \u0111\u1EA7u"] || r["Th\u1EDDi gian c\u1EADp nh\u1EADt"] || ""), state === "COMPLETED" ? visibleToIsoTimestamp(r["Th\u1EDDi gian k\u1EBFt th\xFAc"] || r["Th\u1EDDi gian c\u1EADp nh\u1EADt"] || "") : null, r["Ghi ch\xFA"] || "", fold(r["Kh\u1EA5u tr\u1EEB nh\xE2n s\u1EF1"] || "") === "CO" ? 1 : 0, startId, finishId, state === "COMPLETED" ? 2 : 1, i2 + 2, visibleToIsoTimestamp(r["Th\u1EDDi gian c\u1EADp nh\u1EADt"] || "")));
    }
    await runChunks(db, laborStmts);
    const counts = {};
    for (const table of ["employees", "catalog_values", "resources", "resource_pack_map", "accounts", "business_dates", "attendance_sessions", "labor_sessions"]) {
      const c = await db.prepare(`SELECT COUNT(*) n FROM ${table}`).first();
      counts[table] = c?.n ?? 0;
    }
    const report = { run_id: runId, source_title: wb.title, source_sheet_id: env.GOOGLE_SOURCE_SHEET_ID, sheets: wb.sheetReport, projection_counts: counts, business_date_min: sorted[0] ?? null, business_date_max: sorted[sorted.length - 1] ?? null, business_date_count: sorted.length, completed_at: nowIso() };
    await db.prepare("UPDATE bootstrap_runs SET completed_at=?1,status='COMPLETE',report_json=?2 WHERE run_id=?3").bind(report.completed_at, JSON.stringify(report), runId).run();
    return { ok: true, ...report };
  } catch (e) {
    const at = nowIso();
    await db.prepare("UPDATE bootstrap_runs SET completed_at=?1,status='FAILED',report_json=?2 WHERE run_id=?3").bind(at, JSON.stringify({ error: String(e) }), runId).run();
    throw e;
  }
}
__name(bootstrapFromGoogle, "bootstrapFromGoogle");

// src/core.ts
var CoreError = class extends Error {
  constructor(code, errorClass, status = 400, retryable = false, conflict) {
    super(code);
    this.code = code;
    this.errorClass = errorClass;
    this.status = status;
    this.retryable = retryable;
    this.conflict = conflict;
  }
  code;
  errorClass;
  status;
  retryable;
  conflict;
  static {
    __name(this, "CoreError");
  }
};
function text(payload3, key, max2 = 240) {
  return String(payload3[key] ?? "").trim().slice(0, max2);
}
__name(text, "text");
var SENSITIVE_KEY = /(^|_)(token|password|verifier|secret|authorization|cookie|oauth)(_|$)/i;
function sanitizeSensitive(value) {
  if (Array.isArray(value)) return value.map(sanitizeSensitive);
  if (value && typeof value === "object") {
    const out = {};
    for (const [k, v] of Object.entries(value)) {
      if (SENSITIVE_KEY.test(k)) continue;
      out[k] = sanitizeSensitive(v);
    }
    return out;
  }
  return value;
}
__name(sanitizeSensitive, "sanitizeSensitive");
async function authority(db) {
  const row = await db.prepare("SELECT authority_epoch,authority_seq,mode,scope,service_generation,updated_at FROM authority_state WHERE singleton_id=1").first();
  if (!row) throw new CoreError("AUTHORITY_STATE_MISSING", "INTEGRITY", 503, false);
  return row;
}
__name(authority, "authority");
async function existingByIdentity(db, request) {
  return db.prepare("SELECT * FROM events WHERE event_id=?1 OR idempotency_key=?2 ORDER BY committed_at LIMIT 1").bind(request.event_id, request.idempotency_key).first();
}
__name(existingByIdentity, "existingByIdentity");
function normalizeMutation(req) {
  const eventId = String(req.event_id ?? "").trim();
  const idem = String(req.idempotency_key ?? "").trim();
  const entityId = String(req.entity_id ?? "").trim();
  const deviceId = String(req.device_id ?? "").trim();
  if (!eventId || eventId.length > 180) throw new CoreError("EVENT_ID_REQUIRED", "VALIDATION", 400);
  if (!idem || idem.length > 220) throw new CoreError("IDEMPOTENCY_KEY_REQUIRED", "VALIDATION", 400);
  if (!entityId || entityId.length > 220) throw new CoreError("ENTITY_ID_REQUIRED", "VALIDATION", 400);
  if (!deviceId || deviceId.length > 180) throw new CoreError("DEVICE_ID_REQUIRED", "VALIDATION", 400);
  if (!validIsoDate(String(req.business_date ?? ""))) throw new CoreError("BUSINESS_DATE_INVALID", "VALIDATION", 400);
  if (!Number.isInteger(req.base_version) || req.base_version < 0) throw new CoreError("BASE_VERSION_INVALID", "VALIDATION", 400);
  if (!["ATTENDANCE_ENTER", "ATTENDANCE_EXIT", "RESOURCE_CHANGE", "LABOR_START", "LABOR_FINISH", "M1_SHADOW_PROBE"].includes(String(req.event_type))) throw new CoreError("EVENT_TYPE_UNSUPPORTED", "VALIDATION", 400);
  if (req.schema_version !== 1) throw new CoreError("SCHEMA_VERSION_UNSUPPORTED", "SCHEMA", 409);
  return {
    ...req,
    event_id: eventId,
    idempotency_key: idem,
    entity_id: entityId,
    device_id: deviceId,
    business_date: String(req.business_date),
    timestamp: String(req.timestamp || nowIso()),
    payload: sanitizeSensitive(req.payload && typeof req.payload === "object" ? req.payload : {}),
    client_source: req.client_source === "WEB" || req.client_source === "FILE_IMPORT" ? req.client_source : "PDA"
  };
}
__name(normalizeMutation, "normalizeMutation");
function eventStatements(db, event, expectedSeq) {
  return [
    db.prepare("UPDATE authority_state SET authority_seq=?1,updated_at=?2 WHERE singleton_id=1 AND authority_seq=?3 AND authority_epoch=?4").bind(event.authority_seq, event.committed_at, expectedSeq, event.authority_epoch),
    db.prepare(`INSERT INTO events(event_id,event_type,entity_type,entity_id,business_date,authority_epoch,authority_seq,service_generation,base_version,new_version,actor_id,actor_role,device_id,occurred_at,committed_at,payload_json,idempotency_key,origin,schema_version,checksum)
      VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,?20)`).bind(event.event_id, event.event_type, event.entity_type, event.entity_id, event.business_date, event.authority_epoch, event.authority_seq, event.service_generation, event.base_version, event.new_version, event.actor_id, event.actor_role, event.device_id, event.occurred_at, event.committed_at, event.payload_json, event.idempotency_key, event.origin, event.schema_version, event.checksum),
    db.prepare("INSERT INTO sheet_replication_outbox(event_id,status,next_attempt_at) VALUES(?1,'PENDING',?2)").bind(event.event_id, event.committed_at),
    db.prepare("INSERT INTO mutation_assertions(event_id,ok) VALUES(?1,1)").bind(event.event_id)
  ];
}
__name(eventStatements, "eventStatements");
async function buildEvent(req, auth4, a, newVersion) {
  const committed = nowIso();
  const base = {
    event_id: req.event_id,
    event_type: req.event_type,
    entity_type: req.entity_type,
    entity_id: req.entity_id,
    business_date: req.business_date,
    authority_epoch: a.authority_epoch,
    authority_seq: a.authority_seq + 1,
    service_generation: a.service_generation,
    base_version: req.base_version,
    new_version: newVersion,
    actor_id: auth4.login_id,
    actor_role: auth4.role,
    device_id: req.device_id,
    occurred_at: req.timestamp,
    committed_at: committed,
    payload_json: JSON.stringify(req.payload),
    idempotency_key: req.idempotency_key,
    origin: "SERVICE",
    schema_version: 1
  };
  return { ...base, checksum: await sha256Hex(JSON.stringify(base)) };
}
__name(buildEvent, "buildEvent");
function leaseStatements(db, sessionId, mnv, date, eventId, at, resources, allowDailyReplay = false) {
  const out = [];
  for (const [type, id] of resources) {
    if (!id) continue;
    out.push(db.prepare("INSERT INTO resource_leases(resource_type,resource_id,session_id,mnv,business_date,acquired_event_id,acquired_at) VALUES(?1,?2,?3,?4,?5,?6,?7)").bind(type, id, sessionId, mnv, date, eventId, at));
    if (type === "USER_PICK" || type === "USER_PACK") {
      const sql = allowDailyReplay ? "INSERT OR IGNORE INTO resource_daily_consumption(business_date,resource_type,resource_id,mnv,first_event_id) VALUES(?1,?2,?3,?4,?5)" : "INSERT INTO resource_daily_consumption(business_date,resource_type,resource_id,mnv,first_event_id) VALUES(?1,?2,?3,?4,?5)";
      out.push(db.prepare(sql).bind(date, type, id, mnv, eventId));
    }
  }
  return out;
}
__name(leaseStatements, "leaseStatements");
async function ensureDailyUserReuseAllowed(db, date, pick, pack, duplicateUser, currentPick = "", currentPack = "") {
  for (const [type, id, current] of [["USER_PICK", pick, currentPick], ["USER_PACK", pack, currentPack]]) {
    if (!id || id === current) continue;
    const prior = await db.prepare("SELECT 1 x FROM resource_daily_consumption WHERE business_date=?1 AND resource_type=?2 AND resource_id=?3").bind(date, type, id).first();
    if (prior && !duplicateUser) throw new CoreError(type === "USER_PICK" ? "USER_PICK_ALREADY_USED_TODAY" : "USER_PACK_ALREADY_USED_TODAY", "RESOURCE", 409, false);
  }
}
__name(ensureDailyUserReuseAllowed, "ensureDailyUserReuseAllowed");
async function ensurePackPairAllowed(db, table, pack) {
  if (!table && !pack) return;
  if (!table || !pack) throw new CoreError("PACK_RESOURCES_REQUIRED", "VALIDATION", 400);
  const row = await db.prepare("SELECT 1 x FROM resource_pack_map WHERE pack_table=?1 AND user_pack=?2 AND available=1 LIMIT 1").bind(table, pack).first();
  if (!row) throw new CoreError("PACK_MAPPING_INVALID", "RESOURCE", 409, false);
}
__name(ensurePackPairAllowed, "ensurePackPairAllowed");
async function commitAttendanceEnter(db, auth4, req, a) {
  const p = req.payload, mnv = text(p, "mnv", 80), shift = text(p, "shift", 80), choice = workChoice(p.work_choice);
  if (!mnv || !shift) throw new CoreError("ATTENDANCE_FIELDS_REQUIRED", "VALIDATION", 400);
  const pda = text(p, "pda_serial"), pick = text(p, "user_pick"), table = text(p, "pack_table"), pack = text(p, "user_pack"), pdaEnterStatus = text(p, "pda_enter_status", 180), resourceNote = text(p, "resource_note", 500);
  const checks = await db.batch([
    db.prepare("SELECT 1 AS x FROM employees WHERE mnv=?1").bind(mnv),
    db.prepare("SELECT session_id,mnv,business_date,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,pda_enter_status,pda_exit_status,resource_note,version FROM attendance_sessions WHERE mnv=?1 AND business_date=?2").bind(mnv, req.business_date),
    db.prepare("SELECT available FROM resources WHERE resource_type='PDA' AND resource_id=?1").bind(pda),
    db.prepare("SELECT available FROM resources WHERE resource_type='USER_PICK' AND resource_id=?1").bind(pick),
    db.prepare("SELECT available FROM resources WHERE resource_type='PACK_TABLE' AND resource_id=?1").bind(table),
    db.prepare("SELECT available FROM resources WHERE resource_type='USER_PACK' AND resource_id=?1").bind(pack)
  ]);
  if (!checks[0]?.results?.length) throw new CoreError("EMPLOYEE_NOT_FOUND", "VALIDATION", 404);
  const current = checks[1]?.results?.[0] ?? null, currentVersion = current?.version ?? 0;
  if (currentVersion !== req.base_version) throw new CoreError("STALE_BASE_VERSION", "CONFLICT", 409, false, { current_version: currentVersion });
  if (current?.state === "ACTIVE") throw new CoreError("ATTENDANCE_ALREADY_ACTIVE", "CONFLICT", 409, false, { session_id: current.session_id });
  if (current?.state === "ENDED") throw new CoreError("ATTENDANCE_ALREADY_ENDED", "CONFLICT", 409, false, { session_id: current.session_id });
  if (pda && !Boolean(checks[2]?.results?.[0]?.available)) throw new CoreError("PDA_UNAVAILABLE", "RESOURCE", 409);
  if (pick && !Boolean(checks[3]?.results?.[0]?.available)) throw new CoreError("USER_PICK_UNAVAILABLE", "RESOURCE", 409);
  if (table && !Boolean(checks[4]?.results?.[0]?.available)) throw new CoreError("PACK_TABLE_UNAVAILABLE", "RESOURCE", 409);
  if (pack && !Boolean(checks[5]?.results?.[0]?.available)) throw new CoreError("USER_PACK_UNAVAILABLE", "RESOURCE", 409);
  if (choice === "PICK" && !pda) throw new CoreError("PDA_REQUIRED_FOR_PICK", "VALIDATION", 400);
  if (choice === "PACK" && (!table || !pack)) throw new CoreError("PACK_RESOURCES_REQUIRED", "VALIDATION", 400);
  const duplicateUser = Boolean(p.duplicate_user);
  await ensurePackPairAllowed(db, table, pack);
  await ensureDailyUserReuseAllowed(db, req.business_date, pick, pack, duplicateUser);
  const event = await buildEvent(req, auth4, a, currentVersion + 1);
  const sessionId = req.entity_id;
  const stmts = eventStatements(db, event, a.authority_seq);
  stmts.push(db.prepare(`INSERT INTO attendance_sessions(session_id,mnv,business_date,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,enter_at,entered_by,version,updated_at)
    VALUES(?1,?2,?3,?4,?5,'ACTIVE',?6,?7,?8,?9,?10,?11,?12,?13)
    ON CONFLICT(mnv,business_date) DO UPDATE SET session_id=excluded.session_id,shift=excluded.shift,work_choice=excluded.work_choice,state='ACTIVE',pda_serial=excluded.pda_serial,user_pick=excluded.user_pick,pack_table=excluded.pack_table,user_pack=excluded.user_pack,enter_at=excluded.enter_at,entered_by=excluded.entered_by,version=excluded.version,updated_at=excluded.updated_at`).bind(sessionId, mnv, req.business_date, shift, choice, pda || null, pick || null, table || null, pack || null, event.committed_at, auth4.login_id, event.new_version, event.committed_at));
  stmts.push(db.prepare("UPDATE attendance_sessions SET pda_enter_status=?1,resource_note=?2 WHERE session_id=?3").bind(pdaEnterStatus || null, resourceNote, sessionId));
  stmts.push(...leaseStatements(db, sessionId, mnv, req.business_date, event.event_id, event.committed_at, [["PDA", pda], ["USER_PICK", pick], ["PACK_TABLE", table], ["USER_PACK", pack]], duplicateUser));
  try {
    await db.batch(stmts);
  } catch (e) {
    const msg = String(e);
    if (msg.includes("resource_leases") || msg.includes("resource_daily_consumption") || msg.includes("UNIQUE constraint")) throw new CoreError("EXCLUSIVE_RESOURCE_CONFLICT", "RESOURCE", 409, false);
    throw e;
  }
  return event;
}
__name(commitAttendanceEnter, "commitAttendanceEnter");
async function commitAttendanceExit(db, auth4, req, a) {
  const p = req.payload, mnv = text(p, "mnv", 80);
  const checks = await db.batch([
    db.prepare("SELECT session_id,mnv,business_date,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,pda_enter_status,pda_exit_status,resource_note,version FROM attendance_sessions WHERE mnv=?1 AND business_date=?2").bind(mnv, req.business_date),
    db.prepare("SELECT COUNT(*) AS n FROM labor_sessions WHERE mnv=?1 AND business_date=?2 AND state='OPEN'").bind(mnv, req.business_date)
  ]);
  const current = checks[0]?.results?.[0] ?? null;
  if (!current || current.state !== "ACTIVE") throw new CoreError("ATTENDANCE_NOT_ACTIVE", "CONFLICT", 409);
  if (current.version !== req.base_version) throw new CoreError("STALE_BASE_VERSION", "CONFLICT", 409, false, { current_version: current.version });
  const open = checks[1]?.results?.[0] ?? null;
  if ((open?.n ?? 0) > 0) throw new CoreError("OPEN_LABOR_BLOCKS_EXIT", "CONFLICT", 409);
  const pdaExitStatus = text(p, "pda_exit_status", 180);
  if (current.pda_serial) {
    let expected = text({ v: current.pda_enter_status ?? "" }, "v", 180);
    if (!expected) {
      const row = await db.prepare("SELECT status_label FROM resources WHERE resource_type='PDA' AND resource_id=?1").bind(current.pda_serial).first();
      expected = String(row?.status_label ?? "").trim().slice(0, 180);
    }
    if (!pdaExitStatus) throw new CoreError("PDA_EXIT_STATUS_REQUIRED", "VALIDATION", 400);
    if (expected && pdaExitStatus !== expected) throw new CoreError("PDA_STATUS_MISMATCH_NOTIFY_SPECIALIST", "CONFLICT", 409, false, { expected_status: expected, current_status: pdaExitStatus, pda_serial: current.pda_serial });
  }
  const event = await buildEvent(req, auth4, a, current.version + 1), stmts = eventStatements(db, event, a.authority_seq);
  stmts.push(db.prepare("UPDATE attendance_sessions SET state='ENDED',exit_at=?1,exited_by=?2,version=?3,updated_at=?1 WHERE session_id=?4 AND version=?5 AND state='ACTIVE'").bind(event.committed_at, auth4.login_id, event.new_version, current.session_id, current.version));
  stmts.push(db.prepare("UPDATE attendance_sessions SET pda_exit_status=?1 WHERE session_id=?2").bind(pdaExitStatus || null, current.session_id));
  stmts.push(db.prepare("DELETE FROM resource_leases WHERE session_id=?1").bind(current.session_id));
  await db.batch(stmts);
  return event;
}
__name(commitAttendanceExit, "commitAttendanceExit");
async function commitResourceChange(db, auth4, req, a) {
  const p = req.payload, mnv = text(p, "mnv", 80);
  const current = await db.prepare("SELECT session_id,mnv,business_date,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,pda_enter_status,pda_exit_status,resource_note,version FROM attendance_sessions WHERE mnv=?1 AND business_date=?2").bind(mnv, req.business_date).first();
  if (!current || current.state !== "ACTIVE") throw new CoreError("ATTENDANCE_NOT_ACTIVE", "CONFLICT", 409);
  if (current.version !== req.base_version) throw new CoreError("STALE_BASE_VERSION", "CONFLICT", 409, false, { current_version: current.version });
  const pda = text(p, "pda_serial") || current.pda_serial || "", pick = text(p, "user_pick") || "", table = text(p, "pack_table") || "", pack = text(p, "user_pack") || "";
  const duplicateUser = Boolean(p.duplicate_user);
  await ensurePackPairAllowed(db, table, pack);
  await ensureDailyUserReuseAllowed(db, req.business_date, pick, pack, duplicateUser, current.user_pick || "", current.user_pack || "");
  const event = await buildEvent(req, auth4, a, current.version + 1), stmts = eventStatements(db, event, a.authority_seq);
  stmts.push(db.prepare("DELETE FROM resource_leases WHERE session_id=?1").bind(current.session_id));
  stmts.push(db.prepare("UPDATE attendance_sessions SET pda_serial=?1,user_pick=?2,pack_table=?3,user_pack=?4,version=?5,updated_at=?6 WHERE session_id=?7 AND version=?8").bind(pda || null, pick || null, table || null, pack || null, event.new_version, event.committed_at, current.session_id, current.version));
  const resourceNote = text(p, "resource_note", 500);
  if (resourceNote) stmts.push(db.prepare("UPDATE attendance_sessions SET resource_note=?1 WHERE session_id=?2").bind(resourceNote, current.session_id));
  stmts.push(...leaseStatements(db, current.session_id, current.mnv, req.business_date, event.event_id, event.committed_at, [["PDA", pda], ["USER_PICK", pick], ["PACK_TABLE", table], ["USER_PACK", pack]], duplicateUser));
  try {
    await db.batch(stmts);
  } catch (e) {
    if (String(e).includes("UNIQUE constraint")) throw new CoreError("EXCLUSIVE_RESOURCE_CONFLICT", "RESOURCE", 409);
    throw e;
  }
  return event;
}
__name(commitResourceChange, "commitResourceChange");
async function commitLaborStart(db, auth4, req, a) {
  if (auth4.role === "USER") throw new CoreError("LABOR_ADMIN_REQUIRED", "PERMISSION", 403);
  const p = req.payload, mnv = text(p, "mnv", 80), shift = text(p, "shift", 80), laborType = text(p, "labor_type", 180), marker = text(p, "time_marker", 120);
  if (!mnv || !shift || !laborType || !marker) throw new CoreError("LABOR_FIELDS_REQUIRED", "VALIDATION", 400);
  const checks = await db.batch([
    db.prepare("SELECT labor_id,mnv,business_date,state,version FROM labor_sessions WHERE labor_id=?1").bind(req.entity_id),
    db.prepare("SELECT state FROM attendance_sessions WHERE mnv=?1 AND business_date=?2").bind(mnv, req.business_date)
  ]);
  const current = checks[0]?.results?.[0] ?? null, v = current?.version ?? 0;
  if (v !== req.base_version) throw new CoreError("STALE_BASE_VERSION", "CONFLICT", 409, false, { current_version: v });
  if (current?.state === "OPEN") throw new CoreError("LABOR_ALREADY_OPEN", "CONFLICT", 409);
  const attendance2 = checks[1]?.results?.[0] ?? null;
  if (attendance2?.state !== "ACTIVE") throw new CoreError("ATTENDANCE_NOT_ACTIVE", "CONFLICT", 409);
  const event = await buildEvent(req, auth4, a, v + 1), stmts = eventStatements(db, event, a.authority_seq);
  stmts.push(db.prepare(`INSERT INTO labor_sessions(labor_id,mnv,business_date,shift,labor_type,time_marker,state,start_at,note,deduct_staff,start_event_id,version,updated_at)
    VALUES(?1,?2,?3,?4,?5,?6,'OPEN',?7,?8,?9,?10,?11,?12)`).bind(req.entity_id, mnv, req.business_date, shift, laborType, marker, event.committed_at, text(p, "note", 500), fold(p.deduct_staff) === "CO" ? 1 : 0, event.event_id, event.new_version, event.committed_at));
  await db.batch(stmts);
  return event;
}
__name(commitLaborStart, "commitLaborStart");
async function commitLaborFinish(db, auth4, req, a) {
  if (auth4.role === "USER") throw new CoreError("LABOR_ADMIN_REQUIRED", "PERMISSION", 403);
  const current = await db.prepare("SELECT labor_id,mnv,business_date,state,version FROM labor_sessions WHERE labor_id=?1").bind(req.entity_id).first();
  if (!current || current.state !== "OPEN") throw new CoreError("LABOR_NOT_OPEN", "CONFLICT", 409);
  if (current.version !== req.base_version) throw new CoreError("STALE_BASE_VERSION", "CONFLICT", 409, false, { current_version: current.version });
  const event = await buildEvent(req, auth4, a, current.version + 1), stmts = eventStatements(db, event, a.authority_seq);
  stmts.push(db.prepare("UPDATE labor_sessions SET state='COMPLETED',end_at=?1,finish_event_id=?2,version=?3,updated_at=?1 WHERE labor_id=?4 AND version=?5 AND state='OPEN'").bind(event.committed_at, event.event_id, event.new_version, current.labor_id, current.version));
  await db.batch(stmts);
  return event;
}
__name(commitLaborFinish, "commitLaborFinish");
async function commitProbe(db, auth4, req, a) {
  const event = await buildEvent(req, auth4, a, req.base_version + 1);
  await db.batch(eventStatements(db, event, a.authority_seq));
  return event;
}
__name(commitProbe, "commitProbe");
async function commitMutation(db, env, auth4, input) {
  const req = normalizeMutation(input);
  if (req.event_type === "M1_SHADOW_PROBE" && auth4.role !== "SUPERADMIN") throw new CoreError("SHADOW_PROBE_SUPERADMIN_REQUIRED", "PERMISSION", 403);
  const preflightStatements = [
    db.prepare("SELECT * FROM events WHERE event_id=?1 OR idempotency_key=?2 ORDER BY committed_at LIMIT 1").bind(req.event_id, req.idempotency_key),
    db.prepare("SELECT authority_epoch,authority_seq,mode,scope,service_generation,updated_at FROM authority_state WHERE singleton_id=1")
  ];
  const writeWindow = auth4.role === "SUPERADMIN" ? 7 : 2;
  if (writeWindow) preflightStatements.push(db.prepare("SELECT business_date FROM business_dates ORDER BY sequence_no DESC LIMIT ?1").bind(writeWindow));
  const preflight = await db.batch(preflightStatements), prior = preflight[0]?.results?.[0] ?? null;
  if (prior) return { event: prior, duplicate: true };
  const a = preflight[1]?.results?.[0] ?? null;
  if (!a) throw new CoreError("AUTHORITY_STATE_MISSING", "INTEGRITY", 503, false);
  if (a.mode !== "SERVICE_PRIMARY") throw new CoreError("SERVICE_NOT_WRITE_AUTHORITY", "CONFLICT", 409, true, { mode: a.mode, authority_epoch: a.authority_epoch });
  if (req.authority_epoch !== void 0 && req.authority_epoch !== a.authority_epoch) throw new CoreError("AUTHORITY_EPOCH_STALE", "CONFLICT", 409, false, { current_epoch: a.authority_epoch });
  if (req.service_generation && req.service_generation !== a.service_generation) throw new CoreError("SERVICE_GENERATION_STALE", "CONFLICT", 409, true, { service_generation: a.service_generation });
  if (writeWindow) {
    const allowed2 = new Set((preflight[2]?.results ?? []).map((r) => String(r.business_date ?? "")));
    if (!allowed2.has(req.business_date)) throw new CoreError(auth4.role === "SUPERADMIN" ? "BUSINESS_DATE_OUTSIDE_PDA_7_DAY_WINDOW" : "BUSINESS_DATE_NOT_N_N_MINUS_1", "PERMISSION", 403, false, { allowed: [...allowed2] });
  }
  try {
    const event = req.event_type === "ATTENDANCE_ENTER" ? await commitAttendanceEnter(db, auth4, req, a) : req.event_type === "ATTENDANCE_EXIT" ? await commitAttendanceExit(db, auth4, req, a) : req.event_type === "RESOURCE_CHANGE" ? await commitResourceChange(db, auth4, req, a) : req.event_type === "LABOR_START" ? await commitLaborStart(db, auth4, req, a) : req.event_type === "LABOR_FINISH" ? await commitLaborFinish(db, auth4, req, a) : await commitProbe(db, auth4, req, a);
    return { event, duplicate: false };
  } catch (e) {
    if (e instanceof CoreError) throw e;
    const msg = String(e);
    if (msg.includes("UNIQUE constraint failed: events.authority_epoch, events.authority_seq")) throw new CoreError("AUTHORITY_RACE_RETRY", "TRANSIENT", 409, true);
    if (msg.includes("events.event_id") || msg.includes("events.idempotency_key")) {
      const again = await existingByIdentity(db, req);
      if (again) return { event: again, duplicate: true };
    }
    throw e;
  }
}
__name(commitMutation, "commitMutation");
async function delta(db, epoch, afterSeq, limit = 500) {
  const cap = Math.max(1, Math.min(500, limit)), results = await db.batch([
    db.prepare("SELECT authority_epoch,authority_seq,mode,scope,service_generation,updated_at FROM authority_state WHERE singleton_id=1"),
    db.prepare("SELECT * FROM events WHERE authority_epoch=?1 AND authority_seq>?2 ORDER BY authority_seq LIMIT ?3").bind(epoch, afterSeq, cap + 1)
  ]), a = results[0]?.results?.[0] ?? null;
  if (!a) throw new CoreError("AUTHORITY_STATE_MISSING", "INTEGRITY", 503, false);
  if (epoch !== a.authority_epoch) return { authority: a, events: [], has_more: false };
  const all = results[1]?.results ?? [];
  return { authority: a, events: all.slice(0, cap), has_more: all.length > cap };
}
__name(delta, "delta");
async function currentAuthority(db) {
  return authority(db);
}
__name(currentAuthority, "currentAuthority");
async function transitionAuthority(db, input) {
  const a = await authority(db);
  if (a.authority_epoch !== input.expected_epoch) throw new CoreError("AUTHORITY_EPOCH_STALE", "CONFLICT", 409, false, { current_epoch: a.authority_epoch });
  const nextEpoch = input.increment_epoch ? a.authority_epoch + 1 : a.authority_epoch, nextSeq = input.increment_epoch ? 0 : a.authority_seq, at = nowIso();
  await db.prepare("UPDATE authority_state SET authority_epoch=?1,authority_seq=?2,mode=?3,scope=?4,service_generation=?5,updated_at=?6 WHERE singleton_id=1 AND authority_epoch=?7").bind(nextEpoch, nextSeq, input.mode, input.scope ?? a.scope, input.service_generation ?? a.service_generation, at, a.authority_epoch).run();
  return authority(db);
}
__name(transitionAuthority, "transitionAuthority");

// src/business_date.ts
function bangkokToday() {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Ho_Chi_Minh", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(/* @__PURE__ */ new Date());
  const get = /* @__PURE__ */ __name((type) => parts.find((p) => p.type === type)?.value || "", "get");
  return `${get("year")}-${get("month")}-${get("day")}`;
}
__name(bangkokToday, "bangkokToday");
async function ensureCurrentBangkokBusinessDate(db, requestedDate) {
  const date = String(requestedDate || "").trim();
  if (!date || date !== bangkokToday()) return false;
  const exists = await db.prepare("SELECT sequence_no FROM business_dates WHERE business_date=?1").bind(date).first();
  if (exists) return false;
  const latest = await db.prepare("SELECT business_date,sequence_no FROM business_dates ORDER BY sequence_no DESC LIMIT 1").first();
  if (latest?.business_date && latest.business_date > date) return false;
  try {
    await db.prepare(`INSERT INTO business_dates(business_date,sequence_no,source)
      SELECT ?1,COALESCE(MAX(sequence_no),0)+1,'SERVICE_DAILY_ROLLOVER' FROM business_dates
      WHERE NOT EXISTS(SELECT 1 FROM business_dates WHERE business_date=?1)`).bind(date).run();
  } catch (e) {
    const won = await db.prepare("SELECT sequence_no FROM business_dates WHERE business_date=?1").bind(date).first();
    if (!won) throw e;
  }
  const inserted = await db.prepare("SELECT sequence_no FROM business_dates WHERE business_date=?1").bind(date).first();
  if (inserted) {
    await db.prepare("INSERT INTO system_meta(key,value,updated_at) VALUES('business_date_rollover',?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at").bind(JSON.stringify({ business_date: date, sequence_no: inserted.sequence_no, source: "SERVICE_DAILY_ROLLOVER" }), nowIso()).run();
  }
  return Boolean(inserted);
}
__name(ensureCurrentBangkokBusinessDate, "ensureCurrentBangkokBusinessDate");

// src/legacy.ts
function text2(v, max2 = 240) {
  return String(v ?? "").trim().slice(0, max2);
}
__name(text2, "text");
async function currentBusinessDate(db) {
  const date = bangkokToday();
  try {
    await ensureCurrentBangkokBusinessDate(db, date);
    return date;
  } catch {
    throw new CoreError("BUSINESS_DATE_NOT_BOOTSTRAPPED", "INTEGRITY", 503, true);
  }
}
__name(currentBusinessDate, "currentBusinessDate");
async function attendance(db, mnv, date) {
  return db.prepare("SELECT session_id,state,version FROM attendance_sessions WHERE mnv=?1 AND business_date=?2").bind(mnv, date).first();
}
__name(attendance, "attendance");
async function activeLabor(db, mnv, date) {
  return db.prepare("SELECT labor_id,state,version FROM labor_sessions WHERE mnv=?1 AND business_date=?2 AND state='OPEN' ORDER BY start_at DESC LIMIT 1").bind(mnv, date).first();
}
__name(activeLabor, "activeLabor");
async function legacyCanonical(db, input, auth4) {
  const payload3 = input.payload && typeof input.payload === "object" ? input.payload : {}, mnv = text2(payload3.mnv, 80);
  if (!mnv) throw new CoreError("MNV_REQUIRED", "VALIDATION", 400);
  const today = await currentBusinessDate(db);
  const explicit = text2(input.business_date || payload3.business_date, 10);
  const businessDate2 = explicit || today;
  const a = await currentAuthority(db), device = text2(input.device_id || payload3._device_id || auth4.device_id, 180) || auth4.device_id;
  const eventId = text2(input.event_id || payload3.event_id, 180) || crypto.randomUUID();
  let eventType, entityType, entityId, baseVersion = 0, canonicalPayload = { ...payload3, mnv };
  if (input.action === "enter") {
    const old = await attendance(db, mnv, businessDate2);
    const pack = text2(payload3.user_pack || payload3.userPack, 180);
    eventType = "ATTENDANCE_ENTER";
    entityType = "ATTENDANCE_SESSION";
    entityId = old?.session_id || crypto.randomUUID();
    baseVersion = old?.version ?? 0;
    canonicalPayload = { mnv, shift: text2(payload3.shift, 80), work_choice: text2(payload3.work_choice, 40), pda_serial: text2(payload3.pda_serial || payload3.pda, 180), user_pick: text2(payload3.user_pick || payload3.userPick, 180), pack_table: text2(payload3.pack_table || payload3.packTable, 180), user_pack: pack, pda_enter_status: text2(payload3.pda_enter_status || payload3.pda_status_at_enter, 180), resource_note: text2(payload3.resource_note, 500), duplicate_user: Boolean(payload3.duplicate_user), note: text2(payload3.note, 500) };
  } else if (input.action === "exit" || input.action === "resource_change") {
    const old = await attendance(db, mnv, businessDate2);
    if (!old) throw new CoreError("ATTENDANCE_NOT_ENTERED", "CONFLICT", 409);
    eventType = input.action === "exit" ? "ATTENDANCE_EXIT" : "RESOURCE_CHANGE";
    entityType = "ATTENDANCE_SESSION";
    entityId = old.session_id;
    baseVersion = old.version;
    canonicalPayload = input.action === "exit" ? { mnv, pda_exit_status: text2(payload3.pda_exit_status, 180), note: text2(payload3.note, 500) } : { mnv, work_choice: text2(payload3.work_choice, 40), pda_serial: text2(payload3.pda_serial || payload3.pda, 180), user_pick: text2(payload3.user_pick || payload3.userPick, 180), pack_table: text2(payload3.pack_table || payload3.packTable, 180), user_pack: text2(payload3.user_pack || payload3.userPack, 180), resource_note: text2(payload3.resource_note, 500), duplicate_user: Boolean(payload3.duplicate_user), note: text2(payload3.note, 500) };
  } else if (input.action === "labor_start") {
    eventType = "LABOR_START";
    entityType = "LABOR_SESSION";
    entityId = text2(payload3.labor_id, 180) || eventId;
    const existing2 = await db.prepare("SELECT version FROM labor_sessions WHERE labor_id=?1").bind(entityId).first();
    baseVersion = existing2?.version ?? 0;
    canonicalPayload = { mnv, shift: text2(payload3.shift, 80), labor_type: text2(payload3.labor_type, 180), time_marker: text2(payload3.time_marker, 120) || "Trong ng\xE0y", note: text2(payload3.note, 500), deduct_staff: payload3.deduct_staff ?? false };
  } else {
    const open = await activeLabor(db, mnv, businessDate2);
    if (!open) throw new CoreError("LABOR_NOT_OPEN", "CONFLICT", 409);
    eventType = "LABOR_FINISH";
    entityType = "LABOR_SESSION";
    entityId = open.labor_id;
    baseVersion = open.version;
    canonicalPayload = { mnv, note: text2(payload3.note, 500) };
  }
  return { event_id: eventId, event_type: eventType, entity_type: entityType, entity_id: entityId, business_date: businessDate2, authority_epoch: a.authority_epoch, service_generation: a.service_generation, base_version: baseVersion, timestamp: text2(payload3.timestamp, 80) || nowIso(), payload: canonicalPayload, idempotency_key: `legacy:${device}:${eventId}`, device_id: device, schema_version: 1 };
}
__name(legacyCanonical, "legacyCanonical");
async function commitLegacyMutation(db, env, auth4, input) {
  const canonical = await legacyCanonical(db, input, auth4), r = await commitMutation(db, env, auth4, canonical), e = r.event;
  return { ok: true, idempotent: r.duplicate, duplicate: r.duplicate, result: { event_id: e.event_id, revision: e.authority_seq, authority_epoch: e.authority_epoch, new_version: e.new_version }, event: e, projection: "SERVICE_D1" };
}
__name(commitLegacyMutation, "commitLegacyMutation");

// src/admin_audit.ts
var ALLOWED = /* @__PURE__ */ new Set(["staff_upsert", "staff_delete", "account_upsert", "account_status", "account_delete", "change_email", "change_password", "staff_import", "account_login", "account_logout", "settings_change"]);
var TYPE = {
  staff_upsert: "MASTER_STAFF_UPSERT",
  staff_delete: "MASTER_STAFF_DELETE",
  account_upsert: "ACCOUNT_UPSERT",
  account_status: "ACCOUNT_STATUS",
  account_delete: "ACCOUNT_DELETE",
  change_email: "ACCOUNT_EMAIL",
  change_password: "ACCOUNT_PASSWORD",
  staff_import: "MASTER_STAFF_IMPORT",
  account_login: "ACCOUNT_LOGIN",
  account_logout: "ACCOUNT_LOGOUT",
  settings_change: "SETTINGS_CHANGE"
};
function text3(v, max2 = 240) {
  return String(v ?? "").trim().slice(0, max2);
}
__name(text3, "text");
async function commitAdminAudit(db, auth4, input) {
  const action = text3(input.action, 80);
  if (!ALLOWED.has(action)) throw new CoreError("ADMIN_AUDIT_ACTION_INVALID", "VALIDATION", 400);
  const eventId = text3(input.event_id, 180) || crypto.randomUUID();
  const existing2 = await db.prepare("SELECT * FROM events WHERE event_id=?1").bind(eventId).first();
  if (existing2) return { ok: true, duplicate: true, event: existing2 };
  const a = await currentAuthority(db);
  if (a.mode !== "SERVICE_PRIMARY" || a.scope !== "PRODUCTION") throw new CoreError("ADMIN_AUDIT_REQUIRES_SERVICE_PRIMARY", "CONFLICT", 409, true);
  const latest = await db.prepare("SELECT business_date FROM business_dates ORDER BY sequence_no DESC LIMIT 1").first();
  if (!latest?.business_date) throw new CoreError("BUSINESS_DATE_NOT_BOOTSTRAPPED", "INTEGRITY", 503, true);
  const businessDate2 = latest.business_date, seq = a.authority_seq + 1, at = nowIso(), targetId = text3(input.target_id, 180) || auth4.login_id, targetType = text3(input.target_type, 80) || "ADMIN_ACTION";
  const payload3 = sanitizeSensitive({ action, target_type: targetType, target_id: targetId, target_label: text3(input.target_label, 240), mnv: targetType === "STAFF" ? targetId : "", result: text3(input.result, 80) || "OK", detail: text3(input.detail, 500) });
  const base = { event_id: eventId, event_type: TYPE[action] || "ADMIN_AUDIT", entity_type: targetType, entity_id: targetId, business_date: businessDate2, authority_epoch: a.authority_epoch, authority_seq: seq, service_generation: a.service_generation, base_version: 0, new_version: 0, actor_id: auth4.login_id, actor_role: auth4.role, device_id: text3(input.device_id, 180) || auth4.device_id, occurred_at: text3(input.occurred_at, 80) || at, committed_at: at, payload_json: JSON.stringify(payload3), idempotency_key: `admin-audit:${eventId}`, origin: "ADMIN_AUDIT", schema_version: 1 };
  const checksum2 = await sha256Hex(JSON.stringify(base));
  const e = { ...base, checksum: checksum2 };
  await db.batch([
    db.prepare("UPDATE authority_state SET authority_seq=?1,updated_at=?2 WHERE singleton_id=1 AND authority_epoch=?3 AND authority_seq=?4 AND mode='SERVICE_PRIMARY' AND scope='PRODUCTION'").bind(seq, at, a.authority_epoch, a.authority_seq),
    db.prepare(`INSERT INTO events(event_id,event_type,entity_type,entity_id,business_date,authority_epoch,authority_seq,service_generation,base_version,new_version,actor_id,actor_role,device_id,occurred_at,committed_at,payload_json,idempotency_key,origin,schema_version,checksum) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,?20)`).bind(e.event_id, e.event_type, e.entity_type, e.entity_id, e.business_date, e.authority_epoch, e.authority_seq, e.service_generation, e.base_version, e.new_version, e.actor_id, e.actor_role, e.device_id, e.occurred_at, e.committed_at, e.payload_json, e.idempotency_key, e.origin, e.schema_version, e.checksum),
    db.prepare("INSERT INTO sheet_replication_outbox(event_id,status,attempt_count,next_attempt_at,created_at) VALUES(?1,'PENDING',0,?2,?2)").bind(e.event_id, at),
    db.prepare("INSERT INTO mutation_assertions(event_id,ok) VALUES(?1,1)").bind(e.event_id)
  ]);
  return { ok: true, duplicate: false, event: e };
}
__name(commitAdminAudit, "commitAdminAudit");

// src/domain.ts
var REPLICA_HEADERS = [
  "event_id",
  "event_type",
  "entity_type",
  "entity_id",
  "business_date",
  "authority_epoch",
  "authority_seq",
  "service_generation",
  "base_version",
  "new_version",
  "actor_id",
  "actor_role",
  "device_id",
  "occurred_at",
  "committed_at",
  "idempotency_key",
  "origin",
  "schema_version",
  "checksum",
  "payload_json"
];

// src/master_replication.ts
var MASTER_TYPES = { MASTER_EMPLOYEES: "employees", MASTER_PDA: "pda", MASTER_USER_PICK: "user_pick", MASTER_PACK_TABLE: "pack_table", MASTER_USER_PACK: "user_pack" };
var CATALOG_HEADERS = ["DANH S\xC1CH NH\xC2N S\u1EF0_V\u1ECB tr\xED ch\xEDnh", "DANH S\xC1CH NH\xC2N S\u1EF0_Nh\xE0 cung c\u1EA5p", "DANH S\xC1CH NH\xC2N S\u1EF0_B\u1ED9 ph\u1EADn", "DANH S\xC1CH NH\xC2N S\u1EF0_Site", "DANH S\xC1CH NH\xC2N S\u1EF0_Kho", "DANH S\xC1CH PDA_T\xECnh tr\u1EA1ng", "DANH S\xC1CH USER PICK_T\xECnh tr\u1EA1ng", "DANH S\xC1CH B\xC0N PACK_T\xECnh tr\u1EA1ng", "DANH S\xC1CH USER PACK_T\xECnh tr\u1EA1ng", "RA - V\xC0O TRONG CA_Lo\u1EA1i thao t\xE1c", "V\xC0O - RA TRONG CA_Ca", "C\xD4NG NH\u1EACT_Th\xF4ng tin c\xF4ng nh\u1EADt", "C\xD4NG NH\u1EACT_M\u1ED1c th\u1EDDi gian", "C\xD4NG NH\u1EACT_Tr\u1EA1ng th\xE1i"];
function q2(name) {
  return `'${name.replace(/'/g, "''")}'`;
}
__name(q2, "q");
function payload(e) {
  try {
    return JSON.parse(e.payload_json);
  } catch {
    return {};
  }
}
__name(payload, "payload");
function after(e) {
  const p = payload(e), v = p.after;
  return v && typeof v === "object" && !Array.isArray(v) ? v : null;
}
__name(after, "after");
function text4(v) {
  return String(v ?? "").trim();
}
__name(text4, "text");
function meta(v) {
  try {
    const x2 = typeof v === "string" ? JSON.parse(v) : v;
    return x2 && typeof x2 === "object" && !Array.isArray(x2) ? x2 : {};
  } catch {
    return {};
  }
}
__name(meta, "meta");
function rowIndex(grid, keyCol, key) {
  for (let i2 = 1; i2 < grid.length; i2++) if (text4(grid[i2]?.[keyCol]) === key) return i2 + 1;
  return null;
}
__name(rowIndex, "rowIndex");
function nextRow(grid) {
  let last = 1;
  for (let i2 = 1; i2 < grid.length; i2++) if ((grid[i2] ?? []).some((x2) => text4(x2))) last = i2 + 1;
  return last + 1;
}
__name(nextRow, "nextRow");
async function batchGet(sheetId, token3, ranges) {
  const qs = ranges.map((r2) => `ranges=${encodeURIComponent(r2)}`).join("&"), r = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(sheetId)}/values:batchGet?majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE&${qs}`, { headers: { authorization: `Bearer ${token3}` } });
  if (!r.ok) throw new Error(`GOOGLE_MASTER_BATCH_READ:${r.status}`);
  const j = await r.json();
  return ranges.map((_, i2) => j.valueRanges?.[i2]?.values ?? []);
}
__name(batchGet, "batchGet");
async function batchPut(sheetId, token3, data) {
  if (!data.length) return;
  const r = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(sheetId)}/values:batchUpdate`, { method: "POST", headers: { authorization: `Bearer ${token3}`, "content-type": "application/json" }, body: JSON.stringify({ valueInputOption: "RAW", data: data.map((x2) => ({ range: x2.range, majorDimension: "ROWS", values: x2.values })) }) });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`GOOGLE_MASTER_BATCH_WRITE:${r.status}:${t.slice(0, 180)}`);
  }
}
__name(batchPut, "batchPut");
function assertHeader(grid, expected, name) {
  const got = (grid[0] ?? []).slice(0, expected.length).map(String);
  if (JSON.stringify(got) !== JSON.stringify([...expected])) throw new Error(`GOOGLE_MASTER_SCHEMA_DRIFT:${name}`);
}
__name(assertHeader, "assertHeader");
async function statusLabel(db, namespace, available) {
  const rows2 = (await db.prepare("SELECT value FROM catalog_values WHERE namespace=?1 ORDER BY ordinal").bind(namespace).all()).results ?? [];
  const match = rows2.map((x2) => x2.value).find((v) => isAvailableLabel(v) === available);
  if (!match) throw new Error(`MASTER_STATUS_LABEL_MISSING:${namespace}:${available}`);
  return match;
}
__name(statusLabel, "statusLabel");
async function replicateMasterProjection(db, env, token3, events) {
  const master = events.filter((e) => Boolean(MASTER_TYPES[e.entity_type]) && (e.event_type === "MASTER_IMPORT_UPSERT" || e.event_type === "MASTER_IMPORT_ROLLBACK"));
  if (!master.length) return 0;
  const id = env.GOOGLE_SOURCE_SHEET_ID, ranges = [`${q2("Danh m\u1EE5c")}!A:N`, `${q2("DANH S\xC1CH NH\xC2N S\u1EF0")}!A:L`, `${q2("DANH S\xC1CH PDA")}!A:D`, `${q2("DANH S\xC1CH USER PICK")}!A:D`, `${q2("DANH S\xC1CH B\xC0N PACK")}!A:B`, `${q2("DANH S\xC1CH USER PACK")}!A:D`], g = await batchGet(id, token3, ranges), catalog = g[0] ?? [], staff = g[1] ?? [], pda = g[2] ?? [], pick = g[3] ?? [], tables = g[4] ?? [], pack = g[5] ?? [];
  assertHeader(catalog, CATALOG_HEADERS, "Danh m\u1EE5c");
  assertHeader(staff, ["M\xE3 nh\xE2n vi\xEAn", "H\u1ECD v\xE0 t\xEAn", "S\u1ED1 \u0111i\u1EC7n tho\u1EA1i", "V\u1ECB tr\xED ch\xEDnh", "Nh\xE0 cung c\u1EA5p", "B\u1ED9 ph\u1EADn", "Site", "Kho", "Ng\xE0y b\u1EAFt \u0111\u1EA7u l\xE0m vi\u1EC7c", "Ghi ch\xFA", "Ng\u01B0\u1EDDi c\u1EADp nh\u1EADt", "Th\u1EDDi gian c\u1EADp nh\u1EADt"], "DANH S\xC1CH NH\xC2N S\u1EF0");
  assertHeader(pda, ["Seri PDA", "5 s\u1ED1 cu\u1ED1i Seri", "T\xECnh tr\u1EA1ng", "Ghi ch\xFA"], "DANH S\xC1CH PDA");
  assertHeader(pick, ["S\u1ED1 User", "User Pick", "T\xECnh tr\u1EA1ng", "Ghi ch\xFA"], "DANH S\xC1CH USER PICK");
  assertHeader(tables, ["T\xEAn b\xE0n pack", "T\xECnh tr\u1EA1ng"], "DANH S\xC1CH B\xC0N PACK");
  assertHeader(pack, ["T\xEAn b\xE0n pack", "User pack", "User Pack", "T\xECnh tr\u1EA1ng"], "DANH S\xC1CH USER PACK");
  const updates = [];
  let projected = 0;
  for (const e of master) {
    const dataset = MASTER_TYPES[e.entity_type], r = after(e);
    if (!r) continue;
    if (dataset === "employees") {
      const key = text4(r.mnv), row = rowIndex(staff, 0, key) ?? nextRow(staff);
      if (row > staff.length) staff.push([]);
      updates.push({ range: `${q2("DANH S\xC1CH NH\xC2N S\u1EF0")}!A${row}:L${row}`, values: [[key, text4(r.full_name), text4(r.phone), text4(r.main_position), text4(r.supplier), text4(r.department), text4(r.site), text4(r.warehouse), text4(r.start_date), text4(r.note), e.actor_id, e.committed_at]] });
      projected++;
      continue;
    }
    if (dataset === "pda") {
      const key = text4(r.resource_id), m = meta(r.metadata_json), row = rowIndex(pda, 0, key) ?? nextRow(pda);
      if (row > pda.length) pda.push([]);
      const old = pda[row - 1] ?? [];
      updates.push({ range: `${q2("DANH S\xC1CH PDA")}!A${row}:D${row}`, values: [[key, text4(m["5 s\u1ED1 cu\u1ED1i Seri"] ?? m.last5) || key.slice(-5), text4(r.status_label), text4(m["Ghi ch\xFA"] ?? m.note ?? old[3])]] });
      projected++;
      continue;
    }
    if (dataset === "user_pick") {
      const key = text4(r.resource_id), m = meta(r.metadata_json), row = rowIndex(pick, 1, key) ?? nextRow(pick);
      if (row > pick.length) pick.push([]);
      const old = pick[row - 1] ?? [];
      updates.push({ range: `${q2("DANH S\xC1CH USER PICK")}!A${row}:D${row}`, values: [[text4(m["S\u1ED1 User"] ?? m.number ?? old[0]), key, text4(r.status_label), text4(m["Ghi ch\xFA"] ?? m.note ?? old[3])]] });
      projected++;
      continue;
    }
    if (dataset === "user_pack") {
      const key = text4(r.resource_id), m = meta(r.metadata_json), row = rowIndex(pack, 2, key) ?? nextRow(pack);
      if (row > pack.length) pack.push([]);
      const old = pack[row - 1] ?? [];
      updates.push({ range: `${q2("DANH S\xC1CH USER PACK")}!A${row}:D${row}`, values: [[text4(m["T\xEAn b\xE0n pack"] ?? m.pack_table ?? old[0]), text4(m["User pack"] ?? m.label ?? old[1]), key, text4(r.status_label)]] });
      projected++;
      continue;
    }
    if (dataset === "pack_table") {
      const key = text4(r.pack_table), available = Boolean(Number(r.available)), status = text4(r.status_label) || await statusLabel(db, "DANH S\xC1CH B\xC0N PACK_T\xECnh tr\u1EA1ng", available), tableRow = rowIndex(tables, 0, key) ?? nextRow(tables);
      if (tableRow > tables.length) tables.push([]);
      updates.push({ range: `${q2("DANH S\xC1CH B\xC0N PACK")}!A${tableRow}:B${tableRow}`, values: [[key, status]] });
      const user = text4(r.user_pack);
      if (user) {
        const packRow = rowIndex(pack, 2, user) ?? nextRow(pack);
        if (packRow > pack.length) pack.push([]);
        const old = pack[packRow - 1] ?? [];
        updates.push({ range: `${q2("DANH S\xC1CH USER PACK")}!A${packRow}:D${packRow}`, values: [[key, text4(r.label) || text4(old[1]), user, text4(old[3]) || await statusLabel(db, "DANH S\xC1CH USER PACK_T\xECnh tr\u1EA1ng", true)]] });
      }
      projected++;
    }
  }
  await batchPut(id, token3, updates);
  return projected;
}
__name(replicateMasterProjection, "replicateMasterProjection");

// src/replication.ts
var RA_HEADERS = ["Ng\xE0y", "Ca", "M\xE3 nh\xE2n vi\xEAn", "H\u1ECD v\xE0 t\xEAn", "S\u1ED1 \u0111i\u1EC7n tho\u1EA1i", "Nh\xE0 cung c\u1EA5p", "B\u1ED9 ph\u1EADn", "Site", "Kho", "V\u1ECB tr\xED ch\xEDnh", "V\u1ECB tr\xED trong ca", "Seri PDA", "User Pick", "B\xE0n Pack", "User Pack", "Lo\u1EA1i thao t\xE1c", "Ghi ch\xFA", "Ng\u01B0\u1EDDi c\u1EADp nh\u1EADt", "Th\u1EDDi gian c\u1EADp nh\u1EADt", "Event ID", "App action", "App revision"];
var USER_HEADERS = ["Ng\xE0y", "Ca", "M\xE3 nh\xE2n vi\xEAn", "H\u1ECD v\xE0 t\xEAn", "Nh\xE0 cung c\u1EA5p", "B\u1ED9 ph\u1EADn", "Site", "V\u1ECB tr\xED trong ca", "User", "Ng\u01B0\u1EDDi c\u1EADp nh\u1EADt", "Event ID"];
var LABOR_HEADERS = ["Ng\xE0y", "Ca", "M\xE3 nh\xE2n vi\xEAn", "H\u1ECD v\xE0 t\xEAn", "S\u1ED1 \u0111i\u1EC7n tho\u1EA1i", "Nh\xE0 cung c\u1EA5p", "B\u1ED9 ph\u1EADn", "Site", "Kho", "V\u1ECB tr\xED ch\xEDnh", "V\u1ECB tr\xED trong ca", "Th\xF4ng tin c\xF4ng nh\u1EADt", "Th\u1EDDi gian b\u1EAFt \u0111\u1EA7u", "Th\u1EDDi gian k\u1EBFt th\xFAc", "M\u1ED1c th\u1EDDi gian", "Tr\u1EA1ng th\xE1i", "Ghi ch\xFA", "Ng\u01B0\u1EDDi c\u1EADp nh\u1EADt", "Th\u1EDDi gian c\u1EADp nh\u1EADt", "Event ID", "Finish Event ID", "App revision", "Kh\u1EA5u tr\u1EEB nh\xE2n s\u1EF1"];
var HISTORY_HEADERS = ["Ng\xE0y", "Session ID", "M\xE3 nh\xE2n vi\xEAn", "H\u1ECD t\xEAn", "Ca", "Lo\u1EA1i s\u1EF1 ki\u1EC7n", "Nh\xE3n s\u1EF1 ki\u1EC7n", "Th\u1EDDi gian", "Ng\u01B0\u1EDDi x\u1EED l\xFD", "Chi ti\u1EBFt", "Event ID", "Ph\u1EA1m vi", "App Revision"];
async function googleAccessToken(env) {
  const body = new URLSearchParams({ client_id: env.GOOGLE_OAUTH_CLIENT_ID, client_secret: env.GOOGLE_OAUTH_CLIENT_SECRET, refresh_token: env.GOOGLE_OAUTH_REFRESH_TOKEN, grant_type: "refresh_token" });
  const r = await fetch("https://oauth2.googleapis.com/token", { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" }, body });
  const j = await r.json();
  if (!r.ok || !j.access_token) throw new Error(`GOOGLE_OAUTH:${j.error ?? r.status}`);
  return j.access_token;
}
__name(googleAccessToken, "googleAccessToken");
function authHeaders(token3, extra = {}) {
  return { authorization: `Bearer ${token3}`, ...extra };
}
__name(authHeaders, "authHeaders");
function a1(name, range) {
  return `'${name.replace(/'/g, "''")}'!${range}`;
}
__name(a1, "a1");
function visibleDate(iso2) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso2);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : iso2;
}
__name(visibleDate, "visibleDate");
function visibleDateTime(iso2) {
  const d = new Date(iso2);
  if (Number.isNaN(d.getTime())) return iso2;
  return new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Ho_Chi_Minh", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }).format(d).replace(",", "");
}
__name(visibleDateTime, "visibleDateTime");
function workLabel(v) {
  return v === "PICK" ? "Pick" : v === "PACK" ? "Pack" : "Kh\xF4ng";
}
__name(workLabel, "workLabel");
function payload2(e) {
  try {
    return JSON.parse(e.payload_json);
  } catch {
    return {};
  }
}
__name(payload2, "payload");
function ptext(p, key) {
  return String(p[key] ?? "").trim();
}
__name(ptext, "ptext");
function pobj(p, key) {
  const v = p[key];
  return v && typeof v === "object" && !Array.isArray(v) ? v : {};
}
__name(pobj, "pobj");
function appendRowNumber(updatedRange) {
  const m = /!A(\d+):/i.exec(updatedRange);
  return m?.[1] ? Number(m[1]) : null;
}
__name(appendRowNumber, "appendRowNumber");
async function getValues(sheetId, token3, sheet, range) {
  const url = `https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(sheetId)}/values/${encodeURIComponent(a1(sheet, range))}?valueRenderOption=FORMATTED_VALUE`;
  const r = await fetch(url, { headers: authHeaders(token3) });
  if (!r.ok) throw new Error(`GOOGLE_READ:${sheet}:${r.status}`);
  const j = await r.json();
  return j.values ?? [];
}
__name(getValues, "getValues");
async function batchGetValues(sheetId, token3, ranges) {
  const qs = ranges.map(([sheet, range]) => `ranges=${encodeURIComponent(a1(sheet, range))}`).join("&"), url = `https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(sheetId)}/values:batchGet?valueRenderOption=FORMATTED_VALUE&${qs}`;
  const r = await fetch(url, { headers: authHeaders(token3) });
  if (!r.ok) throw new Error(`GOOGLE_BATCH_READ:${r.status}`);
  const j = await r.json();
  return ranges.map((_, i2) => j.valueRanges?.[i2]?.values ?? []);
}
__name(batchGetValues, "batchGetValues");
async function putValues(sheetId, token3, sheet, range, values) {
  const full = a1(sheet, range), url = `https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(sheetId)}/values/${encodeURIComponent(full)}?valueInputOption=RAW`;
  const r = await fetch(url, { method: "PUT", headers: authHeaders(token3, { "content-type": "application/json" }), body: JSON.stringify({ range: full, majorDimension: "ROWS", values }) });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`GOOGLE_PUT:${sheet}:${r.status}:${t.slice(0, 200)}`);
  }
}
__name(putValues, "putValues");
async function appendValues(sheetId, token3, sheet, range, values) {
  if (!values.length) return "NOOP";
  const full = a1(sheet, range), url = `https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(sheetId)}/values/${encodeURIComponent(full)}:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS`;
  const r = await fetch(url, { method: "POST", headers: authHeaders(token3, { "content-type": "application/json" }), body: JSON.stringify({ range: full, majorDimension: "ROWS", values }) });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`GOOGLE_APPEND:${sheet}:${r.status}:${t.slice(0, 240)}`);
  }
  const j = await r.json();
  return j.updates?.updatedRange ?? "APPENDED";
}
__name(appendValues, "appendValues");
function assertHeaderValues(sheet, values, headers) {
  const got = (values[0] ?? []).map(String);
  if (JSON.stringify(got) !== JSON.stringify([...headers])) throw new Error(`GOOGLE_OPERATIONAL_SCHEMA_DRIFT:${sheet}`);
}
__name(assertHeaderValues, "assertHeaderValues");
async function ensureReplicaSheet(env, token3) {
  const id = env.GOOGLE_STAGING_SHEET_ID;
  const meta3 = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}?fields=sheets.properties(sheetId,title,hidden)`, { headers: authHeaders(token3) });
  if (!meta3.ok) throw new Error(`GOOGLE_META:${meta3.status}`);
  const m = await meta3.json();
  const p = m.sheets?.map((x2) => x2.properties).find((x2) => x2?.title === "__M1_SERVICE_REPLICA");
  if (!p) {
    const create = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}:batchUpdate`, { method: "POST", headers: authHeaders(token3, { "content-type": "application/json" }), body: JSON.stringify({ requests: [{ addSheet: { properties: { title: "__M1_SERVICE_REPLICA", hidden: true } } }] }) });
    if (!create.ok) throw new Error(`GOOGLE_CREATE_REPLICA:${create.status}`);
  } else if (!p.hidden && p.sheetId !== void 0) {
    const hide = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}:batchUpdate`, { method: "POST", headers: authHeaders(token3, { "content-type": "application/json" }), body: JSON.stringify({ requests: [{ updateSheetProperties: { properties: { sheetId: p.sheetId, hidden: true }, fields: "hidden" } }] }) });
    if (!hide.ok) throw new Error(`GOOGLE_HIDE_REPLICA:${hide.status}`);
  }
  const [header = [], ids = []] = await batchGetValues(id, token3, [["__M1_SERVICE_REPLICA", "A1:T1"], ["__M1_SERVICE_REPLICA", "A2:A"]]);
  if (JSON.stringify((header[0] ?? []).map(String)) !== JSON.stringify([...REPLICA_HEADERS])) await putValues(id, token3, "__M1_SERVICE_REPLICA", "A1:T1", [[...REPLICA_HEADERS]]);
  return new Set(ids.map((r) => String(r[0] ?? "")).filter(Boolean));
}
__name(ensureReplicaSheet, "ensureReplicaSheet");
function eventValues(e) {
  return [e.event_id, e.event_type, e.entity_type, e.entity_id, e.business_date, e.authority_epoch, e.authority_seq, e.service_generation, e.base_version, e.new_version, e.actor_id, e.actor_role, e.device_id, e.occurred_at, e.committed_at, e.idempotency_key, e.origin, e.schema_version, e.checksum, e.payload_json];
}
__name(eventValues, "eventValues");
async function appendTechnicalRows(env, token3, events) {
  return appendValues(env.GOOGLE_STAGING_SHEET_ID, token3, "__M1_SERVICE_REPLICA", "A:T", events.map(eventValues));
}
__name(appendTechnicalRows, "appendTechnicalRows");
async function loadOperationalIndex(env, token3) {
  const id = env.GOOGLE_SOURCE_SHEET_ID, ranges = [
    ["RA - V\xC0O TRONG CA", "A1:V1"],
    ["C\xD4NG NH\u1EACT", "A1:W1"],
    ["L\u1ECACH S\u1EEC NGHI\u1EC6P V\u1EE4", "A1:M1"],
    ["TH\xD4NG TIN USER C\u1EE6A NL\u0110", "A1:K1"],
    ["RA - V\xC0O TRONG CA", "T2:T"],
    ["C\xD4NG NH\u1EACT", "T2:U"],
    ["L\u1ECACH S\u1EEC NGHI\u1EC6P V\u1EE4", "K2:K"],
    ["TH\xD4NG TIN USER C\u1EE6A NL\u0110", "K2:K"]
  ], v = await batchGetValues(id, token3, ranges);
  assertHeaderValues("RA - V\xC0O TRONG CA", v[0] ?? [], RA_HEADERS);
  assertHeaderValues("C\xD4NG NH\u1EACT", v[1] ?? [], LABOR_HEADERS);
  assertHeaderValues("L\u1ECACH S\u1EEC NGHI\u1EC6P V\u1EE4", v[2] ?? [], HISTORY_HEADERS);
  assertHeaderValues("TH\xD4NG TIN USER C\u1EE6A NL\u0110", v[3] ?? [], USER_HEADERS);
  const raEvents = new Set((v[4] ?? []).map((r) => String(r[0] ?? "")).filter(Boolean)), laborStartRows = /* @__PURE__ */ new Map(), laborFinishEvents = /* @__PURE__ */ new Set();
  for (let i2 = 0; i2 < (v[5] ?? []).length; i2++) {
    const r = (v[5] ?? [])[i2] ?? [], start = String(r[0] ?? ""), finish = String(r[1] ?? "");
    if (start) laborStartRows.set(start, i2 + 2);
    if (finish) laborFinishEvents.add(finish);
  }
  const historyEvents = new Set((v[6] ?? []).map((r) => String(r[0] ?? "")).filter(Boolean)), userEvents = new Set((v[7] ?? []).map((r) => String(r[0] ?? "")).filter(Boolean));
  return { raEvents, userEvents, laborStartRows, laborFinishEvents, historyEvents };
}
__name(loadOperationalIndex, "loadOperationalIndex");
async function appendHistory(sheetId, token3, index, e, sessionId, mnv, name, shift, label2, detail) {
  if (index.historyEvents.has(e.event_id)) return;
  await appendValues(sheetId, token3, "L\u1ECACH S\u1EEC NGHI\u1EC6P V\u1EE4", "A:M", [[visibleDate(e.business_date), sessionId, mnv, name, shift, e.event_type, label2, visibleDateTime(e.occurred_at), e.actor_id, detail, e.event_id, "SERVICE_M2", e.authority_seq]]);
  index.historyEvents.add(e.event_id);
}
__name(appendHistory, "appendHistory");
async function attendanceOperational(db, entityId) {
  const r = await db.prepare(`SELECT s.session_id,s.mnv,s.business_date,s.shift,s.work_choice,s.pda_serial,s.user_pick,s.pack_table,s.user_pack,e.full_name,e.phone,e.main_position,e.supplier,e.department,e.site,e.warehouse
    FROM attendance_sessions s JOIN employees e ON e.mnv=s.mnv WHERE s.session_id=?1`).bind(entityId).first();
  if (!r) throw new Error(`REPLICA_ATTENDANCE_MISSING:${entityId}`);
  return r;
}
__name(attendanceOperational, "attendanceOperational");
async function laborOperational(db, entityId) {
  const r = await db.prepare(`SELECT l.labor_id,l.mnv,l.business_date,l.shift,l.labor_type,l.time_marker,l.start_at,l.end_at,l.note,l.deduct_staff,l.start_event_id,l.finish_event_id,e.full_name,e.phone,e.main_position,e.supplier,e.department,e.site,e.warehouse,a.session_id AS attendance_session_id,a.work_choice AS attendance_work_choice
    FROM labor_sessions l JOIN employees e ON e.mnv=l.mnv LEFT JOIN attendance_sessions a ON a.mnv=l.mnv AND a.business_date=l.business_date WHERE l.labor_id=?1`).bind(entityId).first();
  if (!r) throw new Error(`REPLICA_LABOR_MISSING:${entityId}`);
  return r;
}
__name(laborOperational, "laborOperational");
async function replicateUserAssignments(db, sheetId, token3, index, e, s) {
  const r = await db.prepare("SELECT resource_type,resource_id FROM resource_daily_consumption WHERE first_event_id=?1 AND resource_type IN ('USER_PICK','USER_PACK') ORDER BY resource_type,resource_id").bind(e.event_id).all();
  let n = 0;
  for (const x2 of r.results ?? []) {
    const pos = x2.resource_type === "USER_PICK" ? "PICK" : "PACK", key = `${e.event_id}:${pos}`;
    if (index.userEvents.has(key)) continue;
    await appendValues(sheetId, token3, "TH\xD4NG TIN USER C\u1EE6A NL\u0110", "A:K", [[visibleDate(e.business_date), s.shift, s.mnv, s.full_name, s.supplier, s.department, s.site, pos, x2.resource_id, e.actor_id, key]]);
    index.userEvents.add(key);
    n++;
  }
  return n;
}
__name(replicateUserAssignments, "replicateUserAssignments");
function resourceChangeDetail(e) {
  const p = payload2(e), before = pobj(p, "before"), after2 = pobj(p, "after"), labels = { work_choice: "V\u1ECB tr\xED", pda_serial: "PDA", user_pick: "User Pick", pack_table: "B\xE0n Pack", user_pack: "User Pack" }, parts = [];
  if (Object.keys(after2).length) {
    for (const k of Object.keys(labels)) {
      const a = ptext(before, k) || "\u2014", b = ptext(after2, k) || "\u2014";
      if (a !== b) parts.push(`${labels[k]}: ${a} \u2192 ${b}`);
    }
  }
  if (!parts.length) {
    for (const k of Object.keys(labels)) {
      const v = ptext(p, k);
      if (v) parts.push(`${labels[k]}: ${v}`);
    }
  }
  return parts.join(" \u2022 ") || "C\u1EADp nh\u1EADt c\xF4ng vi\u1EC7c / t\xE0i nguy\xEAn trong ca";
}
__name(resourceChangeDetail, "resourceChangeDetail");
function attendanceResourceSnapshot(e, s) {
  const p = payload2(e), after2 = pobj(p, "after");
  const value = /* @__PURE__ */ __name((key, fallback) => ptext(after2, key) || ptext(p, key) || fallback || "", "value");
  return {
    workChoice: value("work_choice", s.work_choice),
    pdaSerial: value("pda_serial", s.pda_serial),
    userPick: value("user_pick", s.user_pick),
    packTable: value("pack_table", s.pack_table),
    userPack: value("user_pack", s.user_pack)
  };
}
__name(attendanceResourceSnapshot, "attendanceResourceSnapshot");
async function replicateAttendanceEvent(db, sheetId, token3, index, e) {
  const s = await attendanceOperational(db, e.entity_id);
  await replicateUserAssignments(db, sheetId, token3, index, e, s);
  if (e.event_type === "RESOURCE_CHANGE") {
    await appendHistory(sheetId, token3, index, e, s.session_id, s.mnv, s.full_name, s.shift, "C\u1EADp nh\u1EADt c\xF4ng vi\u1EC7c / t\xE0i nguy\xEAn", resourceChangeDetail(e));
    return;
  }
  if (index.raEvents.has(e.event_id)) return;
  const r = attendanceResourceSnapshot(e, s);
  const enter = e.event_type === "ATTENDANCE_ENTER", action = enter ? "V\xC0O" : "RA", appAction = enter ? "ENTER" : "EXIT";
  await appendValues(sheetId, token3, "RA - V\xC0O TRONG CA", "A:V", [[visibleDate(e.business_date), s.shift, s.mnv, s.full_name, s.phone, s.supplier, s.department, s.site, s.warehouse, s.main_position, workLabel(r.workChoice), r.pdaSerial, r.userPick, r.packTable, r.userPack, action, "", e.actor_id, visibleDateTime(e.occurred_at), e.event_id, appAction, e.authority_seq]]);
  index.raEvents.add(e.event_id);
  await appendHistory(sheetId, token3, index, e, s.session_id, s.mnv, s.full_name, s.shift, enter ? "V\xE0o ca" : "Ra ca", `${enter ? "B\u1EAFt \u0111\u1EA7u" : "K\u1EBFt th\xFAc"} phi\xEAn \u2022 V\u1ECB tr\xED ch\xEDnh: ${s.main_position || "\u2014"}`);
}
__name(replicateAttendanceEvent, "replicateAttendanceEvent");
async function replicateLaborStartOperational(db, sheetId, token3, index, e) {
  if (index.laborStartRows.has(e.event_id)) return;
  const l = await laborOperational(db, e.entity_id);
  if (!l.attendance_session_id) throw new Error(`REPLICA_ATTENDANCE_FOR_LABOR_MISSING:${l.mnv}`);
  const updated = await appendValues(sheetId, token3, "C\xD4NG NH\u1EACT", "A:W", [[visibleDate(e.business_date), l.shift, l.mnv, l.full_name, l.phone, l.supplier, l.department, l.site, l.warehouse, l.main_position, workLabel(l.attendance_work_choice ?? ""), l.labor_type, visibleDateTime(l.start_at), "", l.time_marker, "\u0110ang l\xE0m", l.note || "", e.actor_id, visibleDateTime(e.occurred_at), e.event_id, "", e.authority_seq, l.deduct_staff ? "C\xF3" : "Kh\xF4ng"]]);
  const row = appendRowNumber(updated);
  if (row !== null) index.laborStartRows.set(e.event_id, row);
  await appendHistory(sheetId, token3, index, e, l.attendance_session_id, l.mnv, l.full_name, l.shift, "B\u1EAFt \u0111\u1EA7u c\xF4ng nh\u1EADt", `${l.labor_type} \u2022 M\u1ED1c ${l.time_marker} \u2022 Kh\u1EA5u tr\u1EEB ${l.deduct_staff ? "C\xF3" : "Kh\xF4ng"}`);
}
__name(replicateLaborStartOperational, "replicateLaborStartOperational");
async function replicateLaborFinishOperational(db, sheetId, token3, index, e) {
  if (index.laborFinishEvents.has(e.event_id)) return;
  const l = await laborOperational(db, e.entity_id), row = index.laborStartRows.get(l.start_event_id);
  if (!row) throw new Error(`REPLICA_LABOR_START_ROW_MISSING:${l.start_event_id}`);
  const oldNote = l.note || String((await getValues(sheetId, token3, "C\xD4NG NH\u1EACT", `Q${row}:Q${row}`))[0]?.[0] ?? "");
  await putValues(sheetId, token3, "C\xD4NG NH\u1EACT", `N${row}:V${row}`, [[visibleDateTime(l.end_at || e.occurred_at), l.time_marker, "Ho\xE0n th\xE0nh", oldNote, e.actor_id, visibleDateTime(e.occurred_at), l.start_event_id, e.event_id, e.authority_seq]]);
  index.laborFinishEvents.add(e.event_id);
  await appendHistory(sheetId, token3, index, e, l.attendance_session_id || `${visibleDate(e.business_date)}|${l.mnv}`, l.mnv, l.full_name, l.shift, "Ho\xE0n th\xE0nh c\xF4ng nh\u1EADt", `${l.labor_type} \u2022 M\u1ED1c ${l.time_marker} \u2022 Kh\u1EA5u tr\u1EEB ${l.deduct_staff ? "C\xF3" : "Kh\xF4ng"}`);
}
__name(replicateLaborFinishOperational, "replicateLaborFinishOperational");
function adminAuditLabel(type) {
  const m = { MASTER_STAFF_UPSERT: "C\u1EADp nh\u1EADt nh\xE2n s\u1EF1", MASTER_STAFF_DELETE: "X\xF3a nh\xE2n s\u1EF1", ACCOUNT_UPSERT: "T\u1EA1o / s\u1EEDa t\xE0i kho\u1EA3n", ACCOUNT_STATUS: "\u0110\u1ED5i tr\u1EA1ng th\xE1i t\xE0i kho\u1EA3n", ACCOUNT_EMAIL: "\u0110\u1ED5i email t\xE0i kho\u1EA3n", ACCOUNT_PASSWORD: "\u0110\u1ED5i m\u1EADt kh\u1EA9u", MASTER_STAFF_IMPORT: "Import nh\xE2n s\u1EF1", ACCOUNT_LOGIN: "\u0110\u0103ng nh\u1EADp", ACCOUNT_LOGOUT: "\u0110\u0103ng xu\u1EA5t", SETTINGS_CHANGE: "\u0110\u1ED5i c\xE0i \u0111\u1EB7t" };
  return m[type] || type;
}
__name(adminAuditLabel, "adminAuditLabel");
async function replicateAdminAudit(sheetId, token3, index, e) {
  const p = payload2(e), targetType = ptext(p, "target_type") || e.entity_type, targetId = ptext(p, "target_id") || e.entity_id, targetLabel = ptext(p, "target_label"), detail = ptext(p, "detail");
  const mnv = targetType === "STAFF" ? targetId : "";
  await appendHistory(sheetId, token3, index, e, `ADMIN|${targetType}|${targetId}`, mnv, targetLabel, "", adminAuditLabel(e.event_type), detail);
}
__name(replicateAdminAudit, "replicateAdminAudit");
async function replicateOperational(db, env, token3, events) {
  const a = await db.prepare("SELECT scope FROM authority_state WHERE singleton_id=1").first();
  if (a?.scope !== "PRODUCTION") return 0;
  const master = await replicateMasterProjection(db, env, token3, events), index = await loadOperationalIndex(env, token3);
  let n = 0;
  for (const e of events) {
    if (["ATTENDANCE_ENTER", "RESOURCE_CHANGE", "ATTENDANCE_EXIT"].includes(e.event_type)) await replicateAttendanceEvent(db, env.GOOGLE_SOURCE_SHEET_ID, token3, index, e);
    else if (e.event_type === "LABOR_START") await replicateLaborStartOperational(db, env.GOOGLE_SOURCE_SHEET_ID, token3, index, e);
    else if (e.event_type === "LABOR_FINISH") await replicateLaborFinishOperational(db, env.GOOGLE_SOURCE_SHEET_ID, token3, index, e);
    else if (e.origin === "ADMIN_AUDIT") await replicateAdminAudit(env.GOOGLE_SOURCE_SHEET_ID, token3, index, e);
    else continue;
    n++;
  }
  return n + master;
}
__name(replicateOperational, "replicateOperational");
function retryDelaySeconds(attempt) {
  return Math.min(900, Math.max(5, Math.pow(2, Math.min(8, attempt)) * 5));
}
__name(retryDelaySeconds, "retryDelaySeconds");
async function replicatePending(db, env, limit = 50) {
  const staleClaimCutoff = new Date(Date.now() - 15 * 60 * 1e3).toISOString(), requeueAt = nowIso();
  await db.prepare("UPDATE sheet_replication_outbox SET status='RETRY',claim_token=NULL,claimed_at=NULL,next_attempt_at=?1,last_error_class=COALESCE(last_error_class,'STALE_INFLIGHT_RECOVERED'),last_error=COALESCE(last_error,'Recovered stale INFLIGHT claim for canonical retry') WHERE status='INFLIGHT' AND (claimed_at IS NULL OR claimed_at<=?2)").bind(requeueAt, staleClaimCutoff).run();
  const rows2 = await db.prepare("SELECT outbox_id,event_id,attempt_count FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY') AND next_attempt_at<=?1 ORDER BY outbox_id LIMIT ?2").bind(nowIso(), Math.max(1, Math.min(limit, 100))).all();
  const due = rows2.results ?? [];
  if (!due.length) {
    const p = await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first();
    return { ok: true, processed: 0, appended: 0, operational: 0, pending: p?.n ?? 0 };
  }
  const ids = due.map((x2) => x2.event_id), marks = ids.map(() => "?").join(",");
  try {
    const claim = crypto.randomUUID(), at = nowIso();
    await db.batch(due.map((x2) => db.prepare("UPDATE sheet_replication_outbox SET status='INFLIGHT',claim_token=?1,claimed_at=?2,attempt_count=attempt_count+1,last_error_class=NULL,last_error=NULL WHERE outbox_id=?3 AND status IN ('PENDING','RETRY')").bind(claim, at, x2.outbox_id)));
    const token3 = await googleAccessToken(env), present = await ensureReplicaSheet(env, token3);
    const eventsResult = await db.prepare(`SELECT * FROM events WHERE event_id IN (${marks}) ORDER BY authority_epoch,authority_seq`).bind(...ids).all();
    const allEvents = eventsResult.results ?? [], technical = allEvents.filter((e) => !present.has(e.event_id));
    const checkpoint = await appendTechnicalRows(env, token3, technical);
    const operational = await replicateOperational(db, env, token3, allEvents);
    const doneAt = nowIso();
    await db.batch(due.map((x2) => db.prepare("UPDATE sheet_replication_outbox SET status='SYNCED',claim_token=NULL,claimed_at=NULL,replicated_at=?1,google_checkpoint=?2,last_error_class=NULL,last_error=NULL WHERE outbox_id=?3").bind(doneAt, checkpoint, x2.outbox_id)));
    const pending = await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first();
    await db.prepare("UPDATE replication_status SET target_identity=?1,state='HEALTHY',checkpoint=?2,pending_count=?3,last_attempt_at=?4,last_success_at=?4,last_error_class=NULL,last_error=NULL,updated_at=?4 WHERE singleton_id=1").bind(env.GOOGLE_STAGING_SHEET_ID, checkpoint, pending?.n ?? 0, doneAt).run();
    return { ok: true, processed: due.length, appended: technical.length, operational, pending: pending?.n ?? 0, checkpoint };
  } catch (e) {
    const msg = String(e).slice(0, 700), at = nowIso();
    await db.batch(due.map((x2) => {
      const sec = retryDelaySeconds(x2.attempt_count + 1), next = new Date(Date.now() + sec * 1e3).toISOString();
      return db.prepare("UPDATE sheet_replication_outbox SET status='RETRY',claim_token=NULL,claimed_at=NULL,next_attempt_at=?1,last_error_class='TRANSIENT',last_error=?2 WHERE outbox_id=?3").bind(next, msg, x2.outbox_id);
    }));
    const pending = await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first();
    await db.prepare("UPDATE replication_status SET state='DEGRADED',pending_count=?1,retry_count=retry_count+1,last_attempt_at=?2,last_error_class='TRANSIENT',last_error=?3,updated_at=?2 WHERE singleton_id=1").bind(pending?.n ?? 0, at, msg).run();
    return { ok: false, processed: due.length, appended: 0, operational: 0, pending: pending?.n ?? 0, error: msg };
  }
}
__name(replicatePending, "replicatePending");

// src/sync_contract.ts
var NS = /* @__PURE__ */ new Set(["employees", "catalogs", "accounts", "pda", "user_pick", "pack_table", "user_pack"]);
async function syncStatusV2(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  const now = nowIso(), cutoff = new Date(Date.now() - 6e4).toISOString();
  const results = await env.DB.batch([
    env.DB.prepare(`WITH recent AS (SELECT business_date,sequence_no FROM business_dates ORDER BY sequence_no DESC LIMIT 7)
      SELECT r.business_date,r.sequence_no,COALESCE(MAX(e.authority_seq),0) revision FROM recent r LEFT JOIN events e ON e.business_date=r.business_date GROUP BY r.business_date,r.sequence_no ORDER BY r.sequence_no DESC`),
    env.DB.prepare("SELECT authority_epoch,authority_seq,mode,scope,service_generation,updated_at FROM authority_state WHERE singleton_id=1"),
    env.DB.prepare("SELECT namespace,revision,updated_at FROM revision_state ORDER BY namespace"),
    env.DB.prepare("SELECT target_kind,target_identity,schema_version,state,checkpoint,pending_count,retry_count,last_attempt_at,last_success_at,last_error_class,updated_at FROM replication_status WHERE singleton_id=1"),
    env.DB.prepare(`INSERT INTO client_devices(device_id,login_id,platform,app_version,channel,authority_epoch,authority_seq,service_generation,last_seen_at,last_online_at,metadata_json)
      SELECT ?1,?2,'ANDROID','UNKNOWN','UNKNOWN',a.authority_epoch,a.authority_seq,a.service_generation,?3,?3,'{}' FROM authority_state a WHERE a.singleton_id=1
      ON CONFLICT(device_id) DO UPDATE SET login_id=excluded.login_id,authority_epoch=excluded.authority_epoch,authority_seq=excluded.authority_seq,service_generation=excluded.service_generation,last_seen_at=excluded.last_seen_at,last_online_at=excluded.last_online_at
      WHERE client_devices.last_seen_at<?4`).bind(auth4.device_id, auth4.login_id, now, cutoff)
  ]);
  const authority2 = results[1]?.results?.[0];
  if (!authority2) return apiError("AUTHORITY_STATE_MISSING", "INTEGRITY", 503);
  const window = (results[0]?.results ?? []).map((r) => ({ business_date: String(r.business_date || ""), sequence_no: Number(r.sequence_no || 0), revision: Number(r.revision || 0) }));
  const master = {};
  for (const r of results[2]?.results ?? []) master[String(r.namespace)] = Number(r.revision || 0);
  const rep = results[3]?.results?.[0] ?? {}, metas = results.map((x2) => x2?.meta).filter(Boolean), telemetry = { d1_duration_ms: metas.reduce((n, m) => n + Number(m?.duration || 0), 0), d1_rows_read: metas.reduce((n, m) => n + Number(m?.rows_read || 0), 0), d1_rows_written: metas.reduce((n, m) => n + Number(m?.rows_written || 0), 0), served_by_region: String(metas[0]?.served_by_region || ""), served_by_primary: Boolean(metas[0]?.served_by_primary) };
  return json({ ok: true, contract: "LOCAL_FIRST_REVISION_V1", authority: authority2, service_generation: authority2.service_generation, server_seq: authority2.authority_seq, business_window: window, business_dates: window, master_revisions: master, replication: rep, realtime: { protocol: "INVALIDATION_V1", ticket_endpoint: "/v1/realtime/ticket", ws_endpoint: "/v1/realtime" }, delta: { day_endpoint: "/v1/delta/day", master_endpoint: "/v1/delta/master", authority_endpoint: "/v1/delta" }, service_telemetry: telemetry });
}
__name(syncStatusV2, "syncStatusV2");
async function allowedDate(db, date, superadmin) {
  if (superadmin) return true;
  const r = await db.prepare("SELECT 1 x FROM (SELECT business_date FROM business_dates ORDER BY sequence_no DESC LIMIT 7) WHERE business_date=?1").bind(date).first();
  return !!r;
}
__name(allowedDate, "allowedDate");
async function dayDeltaV2(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  const u = new URL(request.url), date = String(u.searchParams.get("business_date") || ""), after2 = Number(u.searchParams.get("after_revision") || 0);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return apiError("BUSINESS_DATE_INVALID", "VALIDATION", 400);
  if (!await allowedDate(env.DB, date, auth4.role === "SUPERADMIN" && u.searchParams.get("client_source") === "WEB")) return apiError("BUSINESS_DATE_OUTSIDE_VIEW_WINDOW", "PERMISSION", 403);
  const r = await env.DB.prepare("SELECT * FROM events WHERE business_date=?1 AND authority_seq>?2 ORDER BY authority_seq LIMIT 501").bind(date, Math.max(0, after2)).all(), all = r.results ?? [], events = all.slice(0, 500), revision = events.length ? Number(events[events.length - 1].authority_seq || after2) : after2;
  return json({ ok: true, business_date: date, from_revision: after2, to_revision: revision, events, has_more: all.length > 500, service_telemetry: { d1_duration_ms: r.meta.duration, d1_rows_read: r.meta.rows_read, served_by_region: r.meta.served_by_region ?? "", served_by_primary: r.meta.served_by_primary ?? false } });
}
__name(dayDeltaV2, "dayDeltaV2");
async function masterDeltaV2(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  const u = new URL(request.url), ns = String(u.searchParams.get("namespace") || ""), after2 = Number(u.searchParams.get("after_revision") || 0);
  if (!NS.has(ns)) return apiError("MASTER_NAMESPACE_INVALID", "VALIDATION", 400);
  const rev2 = (await env.DB.prepare("SELECT revision FROM revision_state WHERE namespace=?1").bind(ns).first())?.revision ?? 0;
  if (after2 === rev2) return json({ ok: true, namespace: ns, from_revision: after2, to_revision: rev2, changed: false, rows: [] });
  let rows2 = [];
  if (ns === "employees") rows2 = (await env.DB.prepare("SELECT mnv,full_name,phone,main_position,supplier,department,site,warehouse,start_date,note FROM employees ORDER BY mnv").all()).results ?? [];
  else if (ns === "catalogs") rows2 = (await env.DB.prepare("SELECT namespace,ordinal,value FROM catalog_values ORDER BY namespace,ordinal").all()).results ?? [];
  else if (ns === "pack_table") rows2 = (await env.DB.prepare("SELECT pack_table,shift,user_pack,label,available FROM resource_pack_map ORDER BY pack_table,shift").all()).results ?? [];
  else if (ns === "accounts") rows2 = (await env.DB.prepare("SELECT login_id,role,display_name,position,status FROM accounts WHERE login_id=?1").bind(auth4.login_id).all()).results ?? [];
  else {
    const type = ns === "pda" ? "PDA" : ns === "user_pick" ? "USER_PICK" : "USER_PACK";
    rows2 = (await env.DB.prepare("SELECT resource_id,status_label,available,metadata_json FROM resources WHERE resource_type=?1 ORDER BY resource_id").bind(type).all()).results ?? [];
  }
  return json({ ok: true, namespace: ns, from_revision: after2, to_revision: rev2, changed: true, mode: "NAMESPACE_SNAPSHOT_ON_REVISION_CHANGE", rows: rows2 });
}
__name(masterDeltaV2, "masterDeltaV2");

// src/push.ts
var tokenCache = null;
function b64u2(input) {
  const bytes = typeof input === "string" ? new TextEncoder().encode(input) : new Uint8Array(input);
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}
__name(b64u2, "b64u");
function pemBytes(pem) {
  const raw = pem.replace(/\\n/g, "\n").replace(/-----[^-]+-----/g, "").replace(/\s/g, "");
  const bin = atob(raw), out = new Uint8Array(bin.length);
  for (let i2 = 0; i2 < bin.length; i2++) out[i2] = bin.charCodeAt(i2);
  return out.buffer;
}
__name(pemBytes, "pemBytes");
function fcmCredentials(env) {
  if (env.FCM_SERVICE_ACCOUNT_JSON) {
    try {
      const j = JSON.parse(env.FCM_SERVICE_ACCOUNT_JSON), projectId = String(j.project_id || "").trim(), clientEmail = String(j.client_email || "").trim(), privateKey = String(j.private_key || "");
      if (projectId && clientEmail && privateKey.includes("PRIVATE KEY")) return { projectId, clientEmail, privateKey };
    } catch {
    }
  }
  if (env.FCM_PROJECT_ID && env.FCM_CLIENT_EMAIL && env.FCM_PRIVATE_KEY) return { projectId: env.FCM_PROJECT_ID, clientEmail: env.FCM_CLIENT_EMAIL, privateKey: env.FCM_PRIVATE_KEY };
  return null;
}
__name(fcmCredentials, "fcmCredentials");
async function fcmAccessToken(env) {
  const creds = fcmCredentials(env);
  if (!creds) return null;
  if (tokenCache && tokenCache.projectId === creds.projectId && tokenCache.expires > Date.now() + 6e4) return { token: tokenCache.token, projectId: tokenCache.projectId };
  const now = Math.floor(Date.now() / 1e3), header = b64u2(JSON.stringify({ alg: "RS256", typ: "JWT" })), claims = b64u2(JSON.stringify({ iss: creds.clientEmail, scope: "https://www.googleapis.com/auth/firebase.messaging", aud: "https://oauth2.googleapis.com/token", iat: now, exp: now + 3600 })), unsigned = `${header}.${claims}`;
  const key = await crypto.subtle.importKey("pkcs8", pemBytes(creds.privateKey), { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]), sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key, new TextEncoder().encode(unsigned)), assertion = `${unsigned}.${b64u2(sig)}`;
  const r = await fetch("https://oauth2.googleapis.com/token", { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" }, body: new URLSearchParams({ grant_type: "urn:ietf:params:grant-type:jwt-bearer", assertion }) });
  if (!r.ok) throw new Error(`FCM_OAUTH_${r.status}`);
  const j = await r.json();
  if (!j.access_token) throw new Error("FCM_OAUTH_TOKEN_MISSING");
  tokenCache = { token: j.access_token, expires: Date.now() + Math.max(300, Number(j.expires_in || 3600)) * 1e3, projectId: creds.projectId };
  return { token: j.access_token, projectId: creds.projectId };
}
__name(fcmAccessToken, "fcmAccessToken");
async function registerPushDevice(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  const b = await readJsonBody(request), token3 = String(b.fcm_token || "").trim();
  if (token3.length < 32 || token3.length > 4096) return apiError("FCM_TOKEN_INVALID", "VALIDATION", 400);
  const at = nowIso();
  await env.DB.prepare(`INSERT INTO push_devices(device_id,login_id,fcm_token,platform,app_version,channel,status,registered_at,updated_at)
    VALUES(?1,?2,?3,'ANDROID',?4,?5,'ACTIVE',?6,?6) ON CONFLICT(device_id,login_id) DO UPDATE SET fcm_token=excluded.fcm_token,app_version=excluded.app_version,channel=excluded.channel,status='ACTIVE',updated_at=excluded.updated_at,last_error_class=NULL`).bind(auth4.device_id, auth4.login_id, token3, String(b.app_version || "").slice(0, 80), String(b.channel || "").slice(0, 40), at).run();
  return json({ ok: true, device_id: auth4.device_id, push: "FCM_WAKE_ONLY" });
}
__name(registerPushDevice, "registerPushDevice");
async function revokePushDevice(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  await env.DB.prepare("UPDATE push_devices SET status='REVOKED',updated_at=?1 WHERE device_id=?2 AND login_id=?3").bind(nowIso(), auth4.device_id, auth4.login_id).run();
  return json({ ok: true });
}
__name(revokePushDevice, "revokePushDevice");
async function enqueueInvalidation(db, namespace, revision, businessDate2) {
  const a = await currentAuthority(db), at = nowIso(), payload3 = { type: businessDate2 ? "DAY_CHANGED" : "MASTER_CHANGED", namespace, revision: revision ?? null, business_date: businessDate2 ?? null, authority_epoch: a.authority_epoch, authority_seq: a.authority_seq };
  await db.prepare("INSERT INTO push_outbox(push_id,namespace,revision,business_date,authority_epoch,authority_seq,payload_json,status,next_attempt_at,created_at) VALUES(?1,?2,?3,?4,?5,?6,?7,'PENDING',?8,?8)").bind(crypto.randomUUID(), namespace, revision ?? null, businessDate2 ?? null, a.authority_epoch, a.authority_seq, JSON.stringify(payload3), at).run();
}
__name(enqueueInvalidation, "enqueueInvalidation");
async function stageRecentDayInvalidations(db) {
  const cutoff = new Date(Date.now() - 10 * 6e4).toISOString();
  await db.prepare(`INSERT OR IGNORE INTO push_outbox(push_id,namespace,revision,business_date,authority_epoch,authority_seq,payload_json,status,next_attempt_at,created_at)
    SELECT 'day:'||event_id,'business_day',authority_seq,business_date,authority_epoch,authority_seq,
      json_object('type','DAY_CHANGED','namespace','business_day','revision',authority_seq,'business_date',business_date,'authority_epoch',authority_epoch,'authority_seq',authority_seq),
      'PENDING',committed_at,committed_at
    FROM events
    WHERE business_date<>'MASTER' AND committed_at>=?1`).bind(cutoff).run();
}
__name(stageRecentDayInvalidations, "stageRecentDayInvalidations");
async function flushPushOutbox(db, rawEnv, limit = 50) {
  await stageRecentDayInvalidations(db);
  const env = rawEnv, access = await fcmAccessToken(env);
  if (!access) return { configured: false, sent: 0, invalid: 0, retry: 0, pending: (await db.prepare("SELECT COUNT(*) n FROM push_outbox WHERE status IN ('PENDING','RETRY')").first())?.n ?? 0 };
  const pushes = (await db.prepare("SELECT push_id,payload_json,attempt_count FROM push_outbox WHERE status IN ('PENDING','RETRY') AND next_attempt_at<=?1 ORDER BY created_at LIMIT ?2").bind(nowIso(), Math.max(1, Math.min(100, limit))).all()).results ?? [], devices = (await db.prepare("SELECT device_id,login_id,fcm_token FROM push_devices WHERE status='ACTIVE'").all()).results ?? [];
  let sent = 0, invalid = 0, retry = 0;
  for (const p of pushes) {
    let transient = false;
    for (const d of devices) {
      const data = JSON.parse(p.payload_json), stringData = Object.fromEntries(Object.entries(data).map(([k, v]) => [k, v == null ? "" : String(v)]));
      const r = await fetch(`https://fcm.googleapis.com/v1/projects/${encodeURIComponent(access.projectId)}/messages:send`, { method: "POST", headers: { authorization: `Bearer ${access.token}`, "content-type": "application/json" }, body: JSON.stringify({ message: { token: d.fcm_token, data: stringData, android: { priority: "high" } } }) });
      if (r.ok) {
        sent++;
        await db.prepare("UPDATE push_devices SET last_success_at=?1,last_error_class=NULL WHERE fcm_token=?2").bind(nowIso(), d.fcm_token).run();
        continue;
      }
      const text7 = (await r.text()).slice(0, 800);
      if (r.status === 404 || /UNREGISTERED|registration-token-not-registered/i.test(text7)) {
        invalid++;
        await db.prepare("UPDATE push_devices SET status='INVALID',last_error_class='UNREGISTERED',updated_at=?1 WHERE fcm_token=?2").bind(nowIso(), d.fcm_token).run();
      } else if (r.status === 429 || r.status >= 500) {
        transient = true;
        retry++;
      } else await db.prepare("UPDATE push_devices SET last_error_class=?1,updated_at=?2 WHERE fcm_token=?3").bind(`FCM_HTTP_${r.status}`, nowIso(), d.fcm_token).run();
    }
    const attempts = p.attempt_count + 1, next = new Date(Date.now() + Math.min(36e5, Math.pow(2, Math.min(attempts, 8)) * 5e3)).toISOString();
    await db.prepare("UPDATE push_outbox SET status=?1,attempt_count=?2,next_attempt_at=?3,last_error_class=?4 WHERE push_id=?5").bind(transient && attempts < 8 ? "RETRY" : transient ? "FAILED" : "SENT", attempts, next, transient ? "FCM_TRANSIENT" : null, p.push_id).run();
  }
  const pending = (await db.prepare("SELECT COUNT(*) n FROM push_outbox WHERE status IN ('PENDING','RETRY')").first())?.n ?? 0;
  return { configured: true, sent, invalid, retry, pending };
}
__name(flushPushOutbox, "flushPushOutbox");

// src/correction.ts
var ATTENDANCE_FIELDS = /* @__PURE__ */ new Set(["shift", "work_choice", "pda_serial", "user_pick", "pack_table", "user_pack", "state"]);
var LABOR_FIELDS = /* @__PURE__ */ new Set(["shift", "labor_type", "time_marker", "state", "note", "deduct_staff", "start_at", "end_at"]);
function safePatch(entity, patch) {
  const allowed2 = entity === "ATTENDANCE_SESSION" ? ATTENDANCE_FIELDS : LABOR_FIELDS, out = {};
  for (const [k, v] of Object.entries(patch)) if (allowed2.has(k)) out[k] = v;
  return out;
}
__name(safePatch, "safePatch");
async function historicalCorrection(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  if (auth4.role !== "SUPERADMIN") return apiError("SUPERADMIN_REQUIRED", "PERMISSION", 403);
  const b = await readJsonBody(request), entity = b.entity_type, id = String(b.entity_id || "").trim(), reason = String(b.reason || "").trim(), idem = String(b.idempotency_key || "").trim();
  if (!["ATTENDANCE_SESSION", "LABOR_SESSION"].includes(entity) || !id || reason.length < 3 || !idem) return apiError("CORRECTION_FIELDS_REQUIRED", "VALIDATION", 400);
  const prior = await env.DB.prepare("SELECT * FROM events WHERE idempotency_key=?1").bind(idem).first();
  if (prior) return json({ ok: true, duplicate: true, event: prior });
  const table = entity === "ATTENDANCE_SESSION" ? "attendance_sessions" : "labor_sessions", pk = entity === "ATTENDANCE_SESSION" ? "session_id" : "labor_id", before = await env.DB.prepare(`SELECT * FROM ${table} WHERE ${pk}=?1`).bind(id).first();
  if (!before) return apiError("CORRECTION_TARGET_NOT_FOUND", "VALIDATION", 404);
  const patch = safePatch(entity, b.patch || {});
  if (!Object.keys(patch).length) return apiError("CORRECTION_PATCH_EMPTY", "VALIDATION", 400);
  const after2 = { ...before, ...patch }, a = await currentAuthority(env.DB);
  if (a.mode !== "SERVICE_PRIMARY") return apiError("SERVICE_NOT_WRITE_AUTHORITY", "CONFLICT", 409, true);
  const committed = nowIso(), newVersion = Number(before.version || 0) + 1, base = { event_id: crypto.randomUUID(), event_type: "HISTORICAL_CORRECTION", entity_type: entity, entity_id: id, business_date: String(before.business_date || ""), authority_epoch: a.authority_epoch, authority_seq: a.authority_seq + 1, service_generation: a.service_generation, base_version: Number(before.version || 0), new_version: newVersion, actor_id: auth4.login_id, actor_role: auth4.role, device_id: auth4.device_id, occurred_at: committed, committed_at: committed, payload_json: JSON.stringify({ source: "WEB", reason, target_event_id: String(b.target_event_id || ""), before, after: after2 }), idempotency_key: idem, origin: "WEB_CORRECTION", schema_version: 1 }, event = { ...base, checksum: await sha256Hex(JSON.stringify(base)) };
  const sets = Object.keys(patch).map((k, i2) => `${k}=?${i2 + 1}`);
  sets.push(`version=?${Object.keys(patch).length + 1}`, `updated_at=?${Object.keys(patch).length + 2}`);
  const values = [...Object.values(patch), newVersion, committed, id], targetIndex = values.length;
  try {
    await env.DB.batch([
      env.DB.prepare(`UPDATE ${table} SET ${sets.join(",")} WHERE ${pk}=?${targetIndex} AND version=?${targetIndex + 1}`).bind(...values, Number(before.version || 0)),
      env.DB.prepare("UPDATE authority_state SET authority_seq=?1,updated_at=?2 WHERE singleton_id=1 AND authority_epoch=?3 AND authority_seq=?4").bind(event.authority_seq, committed, a.authority_epoch, a.authority_seq),
      env.DB.prepare(`INSERT INTO events(event_id,event_type,entity_type,entity_id,business_date,authority_epoch,authority_seq,service_generation,base_version,new_version,actor_id,actor_role,device_id,occurred_at,committed_at,payload_json,idempotency_key,origin,schema_version,checksum) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,?20)`).bind(event.event_id, event.event_type, event.entity_type, event.entity_id, event.business_date, event.authority_epoch, event.authority_seq, event.service_generation, event.base_version, event.new_version, event.actor_id, event.actor_role, event.device_id, event.occurred_at, event.committed_at, event.payload_json, event.idempotency_key, event.origin, event.schema_version, event.checksum),
      env.DB.prepare("INSERT INTO sheet_replication_outbox(event_id,status,next_attempt_at) VALUES(?1,'PENDING',?2)").bind(event.event_id, committed)
    ]);
  } catch (e) {
    return apiError("CORRECTION_CONFLICT", "TRANSIENT", 409, true, String(e).slice(0, 160));
  }
  await enqueueInvalidation(env.DB, "day", event.authority_seq, event.business_date);
  try {
    const hub = env.REALTIME_HUB.getByName(`business:${event.business_date}`);
    await hub.invalidate({ type: "DAY_CHANGED", business_date: event.business_date, day_revision: event.authority_seq, authority_epoch: event.authority_epoch, authority_seq: event.authority_seq });
  } catch {
  }
  return json({ ok: true, duplicate: false, event, before, after: after2 }, 201);
}
__name(historicalCorrection, "historicalCorrection");

// src/import_rules.ts
var STATUS_NS = {
  pda: "DANH S\xC1CH PDA_T\xECnh tr\u1EA1ng",
  user_pick: "DANH S\xC1CH USER PICK_T\xECnh tr\u1EA1ng",
  pack_table: "DANH S\xC1CH B\xC0N PACK_T\xECnh tr\u1EA1ng",
  user_pack: "DANH S\xC1CH USER PACK_T\xECnh tr\u1EA1ng"
};
var EMPLOYEE_FIELDS = {
  main_position: "DANH S\xC1CH NH\xC2N S\u1EF0_V\u1ECB tr\xED ch\xEDnh",
  supplier: "DANH S\xC1CH NH\xC2N S\u1EF0_Nh\xE0 cung c\u1EA5p",
  department: "DANH S\xC1CH NH\xC2N S\u1EF0_B\u1ED9 ph\u1EADn",
  site: "DANH S\xC1CH NH\xC2N S\u1EF0_Site",
  warehouse: "DANH S\xC1CH NH\xC2N S\u1EF0_Kho"
};
var CATALOG_NAMESPACES = [
  "DANH S\xC1CH NH\xC2N S\u1EF0_V\u1ECB tr\xED ch\xEDnh",
  "DANH S\xC1CH NH\xC2N S\u1EF0_Nh\xE0 cung c\u1EA5p",
  "DANH S\xC1CH NH\xC2N S\u1EF0_B\u1ED9 ph\u1EADn",
  "DANH S\xC1CH NH\xC2N S\u1EF0_Site",
  "DANH S\xC1CH NH\xC2N S\u1EF0_Kho",
  "DANH S\xC1CH PDA_T\xECnh tr\u1EA1ng",
  "DANH S\xC1CH USER PICK_T\xECnh tr\u1EA1ng",
  "DANH S\xC1CH B\xC0N PACK_T\xECnh tr\u1EA1ng",
  "DANH S\xC1CH USER PACK_T\xECnh tr\u1EA1ng",
  "RA - V\xC0O TRONG CA_Lo\u1EA1i thao t\xE1c",
  "V\xC0O - RA TRONG CA_Ca",
  "C\xD4NG NH\u1EACT_Th\xF4ng tin c\xF4ng nh\u1EADt",
  "C\xD4NG NH\u1EACT_M\u1ED1c th\u1EDDi gian",
  "C\xD4NG NH\u1EACT_Tr\u1EA1ng th\xE1i"
];
async function loadImportRules(db) {
  const rows2 = (await db.prepare("SELECT namespace,value FROM catalog_values ORDER BY namespace,ordinal").all()).results ?? [], rules = /* @__PURE__ */ new Map();
  for (const r of rows2) {
    const set = rules.get(r.namespace) ?? /* @__PURE__ */ new Set();
    set.add(String(r.value));
    rules.set(r.namespace, set);
  }
  return rules;
}
__name(loadImportRules, "loadImportRules");
function allowed(rules, ns, value) {
  const v = String(value ?? "").trim();
  return !v || Boolean(rules.get(ns)?.has(v));
}
__name(allowed, "allowed");
function importRuleError(rules, dataset, row) {
  if (dataset === "catalogs") {
    const ns2 = String(row.namespace ?? "").trim();
    if (!CATALOG_NAMESPACES.includes(ns2)) return "CATALOG_NAMESPACE_INVALID";
    return null;
  }
  if (dataset === "employees") {
    for (const [field, ns2] of Object.entries(EMPLOYEE_FIELDS)) if (!allowed(rules, ns2, row[field])) return `SELECT_${field.toUpperCase()}_INVALID`;
    return null;
  }
  const ns = STATUS_NS[dataset];
  if (ns && !allowed(rules, ns, row.status_label)) return "STATUS_LABEL_INVALID";
  if (dataset === "pack_table" && !allowed(rules, "V\xC0O - RA TRONG CA_Ca", row.shift)) return "SHIFT_INVALID";
  return null;
}
__name(importRuleError, "importRuleError");
function selectValuesForDataset(rules, dataset) {
  const out = {};
  if (dataset === "catalogs") out.namespace = [...CATALOG_NAMESPACES];
  if (dataset === "employees") for (const [field, ns2] of Object.entries(EMPLOYEE_FIELDS)) out[field] = [...rules.get(ns2) ?? []];
  const ns = STATUS_NS[dataset];
  if (ns) out.status_label = [...rules.get(ns) ?? []];
  if (dataset === "pack_table") out.shift = [...rules.get("V\xC0O - RA TRONG CA_Ca") ?? []];
  return out;
}
__name(selectValuesForDataset, "selectValuesForDataset");

// src/import_engine.ts
var VERSION = "2026-08-19-v1";
var SCHEMAS = {
  employees: { headers: ["mnv", "full_name", "phone", "main_position", "supplier", "department", "site", "warehouse", "start_date", "note"], key: /* @__PURE__ */ __name((r) => String(r.mnv || "").trim(), "key"), required: ["mnv", "full_name"] },
  catalogs: { headers: ["namespace", "ordinal", "value"], key: /* @__PURE__ */ __name((r) => `${String(r.namespace || "").trim()}|${String(r.value || "").trim()}`, "key"), required: ["namespace", "value"] },
  pda: { headers: ["resource_id", "status_label", "available", "metadata_json"], key: /* @__PURE__ */ __name((r) => String(r.resource_id || "").trim(), "key"), required: ["resource_id"] },
  user_pick: { headers: ["resource_id", "status_label", "available", "metadata_json"], key: /* @__PURE__ */ __name((r) => String(r.resource_id || "").trim(), "key"), required: ["resource_id"] },
  pack_table: { headers: ["pack_table", "shift", "user_pack", "label", "status_label", "available"], key: /* @__PURE__ */ __name((r) => `${String(r.pack_table || "").trim()}|${String(r.shift || "").trim()}`, "key"), required: ["pack_table", "shift", "status_label"] },
  user_pack: { headers: ["resource_id", "status_label", "available", "metadata_json"], key: /* @__PURE__ */ __name((r) => String(r.resource_id || "").trim(), "key"), required: ["resource_id"] }
};
var RESOURCE_TYPE = { pda: "PDA", user_pick: "USER_PICK", user_pack: "USER_PACK" };
function isDataset(x2) {
  return Object.hasOwn(SCHEMAS, x2);
}
__name(isDataset, "isDataset");
async function requireSuper(request, env) {
  const a = await authenticate(env.DB, env, request);
  if (!a) return apiError("UNAUTHORIZED", "AUTH", 401);
  if (a.role !== "SUPERADMIN") return apiError("SUPERADMIN_REQUIRED", "PERMISSION", 403);
  return a;
}
__name(requireSuper, "requireSuper");
async function schemaChecksum(dataset) {
  return sha256Hex(JSON.stringify({ version: VERSION, dataset, headers: SCHEMAS[dataset].headers, required: SCHEMAS[dataset].required }));
}
__name(schemaChecksum, "schemaChecksum");
function cleanRow(dataset, row) {
  const out = {};
  for (const h of SCHEMAS[dataset].headers) {
    let v = row[h];
    if (h === "available") v = [true, 1, "1", "true", "TRUE", "C\xF3", "CO", "ACTIVE", "Ho\u1EA1t \u0111\u1ED9ng"].includes(v) ? 1 : 0;
    if (h === "ordinal") v = Math.max(0, Number(v || 0));
    if (h === "metadata_json") {
      if (v && typeof v === "object") v = JSON.stringify(v);
      else {
        const s = String(v || "{}");
        try {
          JSON.parse(s);
          v = s;
        } catch {
          v = "{}";
        }
      }
    } else if (typeof v !== "number") v = String(v ?? "").trim();
    out[h] = v;
  }
  return out;
}
__name(cleanRow, "cleanRow");
function rowError(dataset, row) {
  for (const h of SCHEMAS[dataset].required) if (!String(row[h] ?? "").trim()) return `REQUIRED_${h.toUpperCase()}`;
  if (dataset === "catalogs" && !Number.isFinite(Number(row.ordinal))) return "ORDINAL_INVALID";
  if (dataset === "pack_table" && String(row.user_pack || "").length > 240) return "USER_PACK_TOO_LONG";
  return null;
}
__name(rowError, "rowError");
async function loadRows(db, batchId) {
  const chunks3 = (await db.prepare("SELECT rows_json FROM import_chunks WHERE import_batch_id=?1 ORDER BY chunk_no").bind(batchId).all()).results ?? [], rows2 = [];
  for (const c of chunks3) {
    const a = JSON.parse(c.rows_json);
    if (!Array.isArray(a)) throw new Error("IMPORT_CHUNK_SHAPE_INVALID");
    for (const r of a) if (r && typeof r === "object" && !Array.isArray(r)) rows2.push(r);
  }
  return rows2;
}
__name(loadRows, "loadRows");
async function existingMap(db, dataset) {
  let sql = "";
  if (dataset === "employees") sql = "SELECT mnv,full_name,phone,main_position,supplier,department,site,warehouse,start_date,note FROM employees";
  else if (dataset === "catalogs") sql = "SELECT namespace,ordinal,value FROM catalog_values";
  else if (dataset === "pack_table") sql = "SELECT pack_table,shift,user_pack,label,available FROM resource_pack_map";
  else sql = `SELECT resource_id,status_label,available,metadata_json FROM resources WHERE resource_type='${RESOURCE_TYPE[dataset]}'`;
  const rows2 = (await db.prepare(sql).all()).results ?? [], m = /* @__PURE__ */ new Map();
  for (const r of rows2) m.set(SCHEMAS[dataset].key(r), cleanRow(dataset, r));
  return m;
}
__name(existingMap, "existingMap");
function equalRow(a, b) {
  return !!a && JSON.stringify(a) === JSON.stringify(b);
}
__name(equalRow, "equalRow");
async function batchMeta(db, id) {
  const r = await db.prepare("SELECT dataset,state,actor_id FROM import_batches WHERE import_batch_id=?1").bind(id).first();
  return r && isDataset(r.dataset) ? { ...r, dataset: r.dataset } : null;
}
__name(batchMeta, "batchMeta");
async function importSchema(request, env) {
  const a = await requireSuper(request, env);
  if (a instanceof Response) return a;
  const u = new URL(request.url), dataset = String(u.searchParams.get("dataset") || "");
  if (!isDataset(dataset)) return apiError("IMPORT_DATASET_UNSUPPORTED", "VALIDATION", 400);
  const def = SCHEMAS[dataset], rules = await loadImportRules(env.DB);
  return json({ ok: true, dataset, template_version: VERSION, schema_checksum: await schemaChecksum(dataset), headers: def.headers, required: def.required, select_values: selectValuesForDataset(rules, dataset), upsert_policy: "MATCH_KEY_UPDATE_MISSING_INSERT_OMITTED_NO_ACTION", credential_columns_forbidden: true });
}
__name(importSchema, "importSchema");
async function importStart(request, env) {
  const a = await requireSuper(request, env);
  if (a instanceof Response) return a;
  const b = await readJsonBody(request);
  if (!isDataset(String(b.dataset || ""))) return apiError("IMPORT_DATASET_UNSUPPORTED", "VALIDATION", 400);
  const dataset = b.dataset, expected = await schemaChecksum(dataset);
  if (b.template_version !== VERSION || b.schema_checksum !== expected) return apiError("IMPORT_TEMPLATE_STALE", "SCHEMA", 409);
  if (!/^[a-f0-9]{64}$/i.test(String(b.file_sha256 || ""))) return apiError("IMPORT_FILE_SHA256_INVALID", "VALIDATION", 400);
  const id = crypto.randomUUID(), at = nowIso();
  await env.DB.prepare("INSERT INTO import_batches(import_batch_id,dataset,template_version,schema_checksum,file_sha256,actor_id,state,started_at) VALUES(?1,?2,?3,?4,?5,?6,'UPLOADING',?7)").bind(id, dataset, VERSION, expected, String(b.file_sha256).toLowerCase(), a.login_id, at).run();
  return json({ ok: true, import_batch_id: id, state: "UPLOADING" }, 201);
}
__name(importStart, "importStart");
async function importChunk(request, env, id) {
  const a = await requireSuper(request, env);
  if (a instanceof Response) return a;
  const meta3 = await batchMeta(env.DB, id);
  if (!meta3) return apiError("IMPORT_BATCH_NOT_FOUND", "VALIDATION", 404);
  if (meta3.actor_id !== a.login_id) return apiError("IMPORT_BATCH_OWNER_MISMATCH", "PERMISSION", 403);
  if (meta3.state !== "UPLOADING") return apiError("IMPORT_BATCH_NOT_UPLOADING", "CONFLICT", 409);
  const b = await readJsonBody(request);
  if (!Number.isInteger(b.chunk_no) || b.chunk_no < 0 || !Array.isArray(b.rows) || b.rows.length > 500) return apiError("IMPORT_CHUNK_INVALID", "VALIDATION", 400);
  const normalized = b.rows.map((r) => cleanRow(meta3.dataset, r)), raw = JSON.stringify(normalized), digest = await sha256Hex(raw);
  if (digest !== String(b.chunk_checksum || "").toLowerCase()) return apiError("IMPORT_CHUNK_CHECKSUM_MISMATCH", "INTEGRITY", 409);
  const prior = await env.DB.prepare("SELECT chunk_checksum FROM import_chunks WHERE import_batch_id=?1 AND chunk_no=?2").bind(id, b.chunk_no).first();
  if (prior && prior.chunk_checksum !== digest) return apiError("IMPORT_CHUNK_COLLISION", "INTEGRITY", 409);
  await env.DB.prepare("INSERT INTO import_chunks(import_batch_id,chunk_no,chunk_checksum,rows_json,uploaded_at) VALUES(?1,?2,?3,?4,?5) ON CONFLICT(import_batch_id,chunk_no) DO NOTHING").bind(id, b.chunk_no, digest, raw, nowIso()).run();
  return json({ ok: true, import_batch_id: id, chunk_no: b.chunk_no, duplicate: !!prior, row_count: normalized.length });
}
__name(importChunk, "importChunk");
async function importPreview(request, env, id) {
  const a = await requireSuper(request, env);
  if (a instanceof Response) return a;
  const meta3 = await batchMeta(env.DB, id);
  if (!meta3) return apiError("IMPORT_BATCH_NOT_FOUND", "VALIDATION", 404);
  if (meta3.actor_id !== a.login_id) return apiError("IMPORT_BATCH_OWNER_MISMATCH", "PERMISSION", 403);
  if (!["UPLOADING", "VALIDATED"].includes(meta3.state)) return apiError("IMPORT_BATCH_STATE_INVALID", "CONFLICT", 409);
  const rows2 = await loadRows(env.DB, id);
  if (!rows2.length) return apiError("IMPORT_EMPTY", "VALIDATION", 400);
  if (rows2.length > 1e4) return apiError("IMPORT_TOO_LARGE", "VALIDATION", 413);
  const existing2 = await existingMap(env.DB, meta3.dataset), rules = await loadImportRules(env.DB), seen = /* @__PURE__ */ new Set(), audit = [];
  let inserts = 0, updates = 0, noops = 0, rejected = 0;
  const errors = [];
  for (let i2 = 0; i2 < rows2.length; i2++) {
    const row = cleanRow(meta3.dataset, rows2[i2]), key = SCHEMAS[meta3.dataset].key(row);
    let error = rowError(meta3.dataset, row) || importRuleError(rules, meta3.dataset, row);
    if (!key) error = error || "BUSINESS_KEY_REQUIRED";
    if (seen.has(key)) error = error || "DUPLICATE_BUSINESS_KEY_IN_FILE";
    seen.add(key);
    const before = existing2.get(key), action = error ? "REJECTED" : !before ? "INSERT" : equalRow(before, row) ? "NOOP" : "UPDATE";
    if (action === "INSERT") inserts++;
    else if (action === "UPDATE") updates++;
    else if (action === "NOOP") noops++;
    else {
      rejected++;
      errors.push({ row_no: i2 + 1, business_key: key, error_code: error });
    }
    audit.push(env.DB.prepare("INSERT INTO import_row_audit(import_batch_id,row_no,business_key,action,before_json,after_json,error_code) VALUES(?1,?2,?3,?4,?5,?6,?7) ON CONFLICT(import_batch_id,row_no) DO UPDATE SET business_key=excluded.business_key,action=excluded.action,before_json=excluded.before_json,after_json=excluded.after_json,error_code=excluded.error_code,canonical_event_id=NULL").bind(id, i2 + 1, key, action, before ? JSON.stringify(before) : null, JSON.stringify(row), error));
  }
  if (audit.length) for (let i2 = 0; i2 < audit.length; i2 += 100) await env.DB.batch(audit.slice(i2, i2 + 100));
  const summary = { row_count: rows2.length, inserts, updates, noops, rejected, errors: errors.slice(0, 200) };
  await env.DB.prepare("UPDATE import_batches SET state=?1,validated_at=?2,summary_json=?3 WHERE import_batch_id=?4").bind(rejected ? "FAILED" : "VALIDATED", nowIso(), JSON.stringify(summary), id).run();
  return json({ ok: rejected === 0, import_batch_id: id, state: rejected ? "FAILED" : "VALIDATED", summary });
}
__name(importPreview, "importPreview");
async function importHistory(request, env) {
  const a = await requireSuper(request, env);
  if (a instanceof Response) return a;
  const rows2 = (await env.DB.prepare("SELECT import_batch_id,dataset,template_version,file_sha256,actor_id,state,started_at,validated_at,committed_at,rolled_back_at,summary_json FROM import_batches ORDER BY started_at DESC LIMIT 100").all()).results ?? [];
  return json({ ok: true, batches: rows2 });
}
__name(importHistory, "importHistory");

// src/import_atomic.ts
var RESOURCE_TYPE2 = { pda: "PDA", user_pick: "USER_PICK", user_pack: "USER_PACK" };
var MAX_CHANGED_ROWS = 4e3;
var CHUNK_ROWS = 500;
function isDataset2(x2) {
  return ["employees", "catalogs", "pda", "user_pick", "pack_table", "user_pack"].includes(x2);
}
__name(isDataset2, "isDataset");
async function requireSuper2(request, env) {
  const a = await authenticate(env.DB, env, request);
  if (!a) return apiError("UNAUTHORIZED", "AUTH", 401);
  if (a.role !== "SUPERADMIN") return apiError("SUPERADMIN_REQUIRED", "PERMISSION", 403);
  return a;
}
__name(requireSuper2, "requireSuper");
async function meta2(db, id) {
  const r = await db.prepare("SELECT dataset,state,actor_id FROM import_batches WHERE import_batch_id=?1").bind(id).first();
  return r && isDataset2(r.dataset) ? { dataset: r.dataset, state: r.state, actor_id: r.actor_id } : null;
}
__name(meta2, "meta");
function chunks(rows2) {
  const out = [];
  for (let i2 = 0; i2 < rows2.length; i2 += CHUNK_ROWS) out.push(rows2.slice(i2, i2 + CHUNK_ROWS));
  return out;
}
__name(chunks, "chunks");
function projectionStatements(db, dataset, rows2) {
  const raw = JSON.stringify(rows2);
  if (dataset === "employees") return [db.prepare(`INSERT INTO employees(mnv,full_name,phone,main_position,supplier,department,site,warehouse,start_date,note,source_row,source_checksum)
    SELECT json_extract(value,'$.mnv'),json_extract(value,'$.full_name'),json_extract(value,'$.phone'),json_extract(value,'$.main_position'),json_extract(value,'$.supplier'),json_extract(value,'$.department'),json_extract(value,'$.site'),json_extract(value,'$.warehouse'),json_extract(value,'$.start_date'),json_extract(value,'$.note'),0,json_extract(value,'$._checksum') FROM json_each(?1) WHERE 1
    ON CONFLICT(mnv) DO UPDATE SET full_name=excluded.full_name,phone=excluded.phone,main_position=excluded.main_position,supplier=excluded.supplier,department=excluded.department,site=excluded.site,warehouse=excluded.warehouse,start_date=excluded.start_date,note=excluded.note,source_checksum=excluded.source_checksum`).bind(raw)];
  if (dataset === "catalogs") return [db.prepare(`INSERT INTO catalog_values(namespace,ordinal,value,source_checksum)
    SELECT json_extract(value,'$.namespace'),CAST(json_extract(value,'$.ordinal') AS INTEGER),json_extract(value,'$.value'),json_extract(value,'$._checksum') FROM json_each(?1) WHERE 1
    ON CONFLICT(namespace,value) DO UPDATE SET ordinal=excluded.ordinal,source_checksum=excluded.source_checksum`).bind(raw)];
  if (dataset === "pack_table") return [
    db.prepare(`INSERT INTO resource_pack_map(pack_table,shift,user_pack,label,available,source_row,source_checksum)
      SELECT json_extract(value,'$.pack_table'),json_extract(value,'$.shift'),json_extract(value,'$.user_pack'),json_extract(value,'$.label'),CAST(json_extract(value,'$.available') AS INTEGER),0,json_extract(value,'$._checksum') FROM json_each(?1) WHERE 1
      ON CONFLICT(pack_table,shift) DO UPDATE SET user_pack=excluded.user_pack,label=excluded.label,available=excluded.available,source_checksum=excluded.source_checksum`).bind(raw),
    db.prepare(`INSERT INTO resources(resource_type,resource_id,status_label,available,metadata_json,source_row,source_checksum)
      SELECT 'PACK_TABLE',json_extract(value,'$.pack_table'),json_extract(value,'$.status_label'),CAST(json_extract(value,'$.available') AS INTEGER),'{}',0,json_extract(value,'$._checksum') FROM json_each(?1) WHERE 1
      ON CONFLICT(resource_type,resource_id) DO UPDATE SET status_label=excluded.status_label,available=excluded.available,source_checksum=excluded.source_checksum`).bind(raw)
  ];
  const rt = RESOURCE_TYPE2[dataset];
  return [db.prepare(`INSERT INTO resources(resource_type,resource_id,status_label,available,metadata_json,source_row,source_checksum)
    SELECT ?2,json_extract(value,'$.resource_id'),json_extract(value,'$.status_label'),CAST(json_extract(value,'$.available') AS INTEGER),COALESCE(json_extract(value,'$.metadata_json'),'{}'),0,json_extract(value,'$._checksum') FROM json_each(?1) WHERE 1
    ON CONFLICT(resource_type,resource_id) DO UPDATE SET status_label=excluded.status_label,available=excluded.available,metadata_json=excluded.metadata_json,source_checksum=excluded.source_checksum`).bind(raw, rt)];
}
__name(projectionStatements, "projectionStatements");
async function buildEvent2(a, auth4, dataset, key, batchId, rowNo, before, after2, revision, seq, type) {
  const committed = nowIso(), base = { event_id: crypto.randomUUID(), event_type: type, entity_type: `MASTER_${dataset.toUpperCase()}`, entity_id: key, business_date: "MASTER", authority_epoch: a.authority_epoch, authority_seq: seq, service_generation: a.service_generation, base_version: revision - 1, new_version: revision, actor_id: auth4.login_id, actor_role: auth4.role, device_id: auth4.device_id, occurred_at: committed, committed_at: committed, payload_json: JSON.stringify({ source: "FILE_IMPORT", import_batch_id: batchId, row_no: rowNo, before, after: after2, reason: type === "MASTER_IMPORT_ROLLBACK" ? "IMPORT_BATCH_ROLLBACK" : "IMPORT_BATCH_COMMIT" }), idempotency_key: `import:${batchId}:${type}:${rowNo}`, origin: "FILE_IMPORT", schema_version: 1 };
  return { ...base, checksum: await sha256Hex(JSON.stringify(base)) };
}
__name(buildEvent2, "buildEvent");
function eventInsert(db, events) {
  const raw = JSON.stringify(events);
  return db.prepare(`INSERT INTO events(event_id,event_type,entity_type,entity_id,business_date,authority_epoch,authority_seq,service_generation,base_version,new_version,actor_id,actor_role,device_id,occurred_at,committed_at,payload_json,idempotency_key,origin,schema_version,checksum)
  SELECT json_extract(value,'$.event_id'),json_extract(value,'$.event_type'),json_extract(value,'$.entity_type'),json_extract(value,'$.entity_id'),json_extract(value,'$.business_date'),CAST(json_extract(value,'$.authority_epoch') AS INTEGER),CAST(json_extract(value,'$.authority_seq') AS INTEGER),json_extract(value,'$.service_generation'),CAST(json_extract(value,'$.base_version') AS INTEGER),CAST(json_extract(value,'$.new_version') AS INTEGER),json_extract(value,'$.actor_id'),json_extract(value,'$.actor_role'),json_extract(value,'$.device_id'),json_extract(value,'$.occurred_at'),json_extract(value,'$.committed_at'),json_extract(value,'$.payload_json'),json_extract(value,'$.idempotency_key'),json_extract(value,'$.origin'),CAST(json_extract(value,'$.schema_version') AS INTEGER),json_extract(value,'$.checksum') FROM json_each(?1)`).bind(raw);
}
__name(eventInsert, "eventInsert");
function outboxInsert(db, events) {
  const raw = JSON.stringify(events);
  return db.prepare(`INSERT INTO sheet_replication_outbox(event_id,status,next_attempt_at)
  SELECT json_extract(value,'$.event_id'),'PENDING',json_extract(value,'$.committed_at') FROM json_each(?1)`).bind(raw);
}
__name(outboxInsert, "outboxInsert");
function auditLink(db, batchId, links) {
  const raw = JSON.stringify(links);
  return db.prepare(`WITH m AS (SELECT CAST(json_extract(value,'$.row_no') AS INTEGER) row_no,json_extract(value,'$.event_id') event_id FROM json_each(?2))
  UPDATE import_row_audit SET canonical_event_id=(SELECT event_id FROM m WHERE m.row_no=import_row_audit.row_no) WHERE import_batch_id=?1 AND row_no IN (SELECT row_no FROM m)`).bind(batchId, raw);
}
__name(auditLink, "auditLink");
async function notify(env, dataset, revision, a) {
  try {
    await enqueueInvalidation(env.DB, dataset, revision);
  } catch (e) {
    console.log(JSON.stringify({ level: "warn", kind: "fcm_invalidation_enqueue_failed", namespace: dataset, error_class: "TRANSIENT", error: String(e).slice(0, 160) }));
  }
  try {
    const hub = env.REALTIME_HUB.getByName("master:global");
    await hub.invalidate({ type: "MASTER_CHANGED", namespace: dataset, revision, authority_epoch: a.authority_epoch, authority_seq: a.authority_seq, service_generation: a.service_generation });
  } catch (e) {
    console.log(JSON.stringify({ level: "warn", kind: "ws_master_invalidation_failed", namespace: dataset, error_class: "TRANSIENT", error: String(e).slice(0, 160) }));
  }
}
__name(notify, "notify");
async function importCommitAtomic(request, env, id) {
  const auth4 = await requireSuper2(request, env);
  if (auth4 instanceof Response) return auth4;
  const m = await meta2(env.DB, id);
  if (!m) return apiError("IMPORT_BATCH_NOT_FOUND", "VALIDATION", 404);
  if (m.actor_id !== auth4.login_id) return apiError("IMPORT_BATCH_OWNER_MISMATCH", "PERMISSION", 403);
  if (m.state === "COMMITTED") return json({ ok: true, import_batch_id: id, duplicate: true, state: "COMMITTED" });
  if (m.state !== "VALIDATED") return apiError("IMPORT_NOT_VALIDATED", "CONFLICT", 409);
  const [a, revRow, audits] = await Promise.all([currentAuthority(env.DB), env.DB.prepare("SELECT revision FROM revision_state WHERE namespace=?1").bind(m.dataset).first(), env.DB.prepare("SELECT row_no,business_key,action,before_json,after_json FROM import_row_audit WHERE import_batch_id=?1 ORDER BY row_no").bind(id).all()]);
  if (a.mode !== "SERVICE_PRIMARY") return apiError("SERVICE_NOT_WRITE_AUTHORITY", "CONFLICT", 409, true);
  const changed = (audits.results ?? []).filter((x2) => x2.action === "INSERT" || x2.action === "UPDATE");
  if ((audits.results ?? []).some((x2) => x2.action === "REJECTED")) return apiError("IMPORT_HAS_REJECTED_ROWS", "VALIDATION", 409);
  if (changed.length > MAX_CHANGED_ROWS) return apiError("IMPORT_ATOMIC_LIMIT_EXCEEDED", "VALIDATION", 413, false, void 0, { max_changed_rows: MAX_CHANGED_ROWS });
  if (!changed.length) {
    await env.DB.prepare("UPDATE import_batches SET state='COMMITTED',committed_at=?1 WHERE import_batch_id=?2 AND state='VALIDATED'").bind(nowIso(), id).run();
    return json({ ok: true, import_batch_id: id, state: "COMMITTED", dataset: m.dataset, revision: revRow?.revision ?? 0, changed: 0, event_ids: {} });
  }
  const revision = (revRow?.revision ?? 0) + 1, events = [], rows2 = [], links = [];
  let seq = a.authority_seq;
  for (const x2 of changed) {
    const after2 = JSON.parse(x2.after_json), before = x2.before_json ? JSON.parse(x2.before_json) : null, projection = { ...after2, _checksum: await sha256Hex(JSON.stringify(after2)) };
    const e = await buildEvent2(a, auth4, m.dataset, x2.business_key, id, x2.row_no, before, after2, revision, ++seq, "MASTER_IMPORT_UPSERT");
    events.push(e);
    rows2.push(projection);
    links.push({ row_no: x2.row_no, event_id: e.event_id });
  }
  const stmts = [];
  const rowChunks = chunks(rows2), eventChunks = chunks(events), linkChunks = chunks(links);
  for (let i2 = 0; i2 < rowChunks.length; i2++) {
    stmts.push(...projectionStatements(env.DB, m.dataset, rowChunks[i2]));
    stmts.push(eventInsert(env.DB, eventChunks[i2]));
    stmts.push(outboxInsert(env.DB, eventChunks[i2]));
    stmts.push(auditLink(env.DB, id, linkChunks[i2]));
  }
  const at = nowIso();
  stmts.push(env.DB.prepare("UPDATE authority_state SET authority_seq=?1,updated_at=?2 WHERE singleton_id=1 AND authority_epoch=?3 AND authority_seq=?4").bind(seq, at, a.authority_epoch, a.authority_seq));
  stmts.push(env.DB.prepare("INSERT INTO revision_state(namespace,revision,updated_at) VALUES(?1,?2,?3) ON CONFLICT(namespace) DO UPDATE SET revision=excluded.revision,updated_at=excluded.updated_at").bind(m.dataset, revision, at));
  stmts.push(env.DB.prepare("UPDATE import_batches SET state='COMMITTED',committed_at=?1 WHERE import_batch_id=?2 AND state='VALIDATED'").bind(at, id));
  try {
    await env.DB.batch(stmts);
  } catch (e) {
    return apiError("IMPORT_COMMIT_CONFLICT", "TRANSIENT", 409, true, String(e).slice(0, 180));
  }
  await notify(env, m.dataset, revision, { authority_epoch: a.authority_epoch, authority_seq: seq, service_generation: a.service_generation });
  return json({ ok: true, import_batch_id: id, state: "COMMITTED", dataset: m.dataset, revision, changed: changed.length, event_ids: Object.fromEntries(links.map((x2) => [x2.row_no, x2.event_id])) });
}
__name(importCommitAtomic, "importCommitAtomic");
async function importRollbackAtomic(request, env, id) {
  const auth4 = await requireSuper2(request, env);
  if (auth4 instanceof Response) return auth4;
  const m = await meta2(env.DB, id);
  if (!m) return apiError("IMPORT_BATCH_NOT_FOUND", "VALIDATION", 404);
  if (m.state === "ROLLED_BACK") return json({ ok: true, import_batch_id: id, duplicate: true, state: "ROLLED_BACK" });
  if (m.state !== "COMMITTED") return apiError("IMPORT_NOT_COMMITTED", "CONFLICT", 409);
  const audits = (await env.DB.prepare("SELECT row_no,business_key,action,before_json,after_json FROM import_row_audit WHERE import_batch_id=?1 AND action IN ('INSERT','UPDATE') ORDER BY row_no").bind(id).all()).results ?? [];
  if (audits.some((x2) => x2.action === "INSERT" && !x2.before_json)) return apiError("IMPORT_ROLLBACK_INSERT_REQUIRES_EXPLICIT_CORRECTION", "CONFLICT", 409, false, void 0, { policy: "NO_IMPLICIT_DELETE" });
  if (audits.length > MAX_CHANGED_ROWS) return apiError("IMPORT_ATOMIC_LIMIT_EXCEEDED", "VALIDATION", 413, false, void 0, { max_changed_rows: MAX_CHANGED_ROWS });
  const [a, revRow] = await Promise.all([currentAuthority(env.DB), env.DB.prepare("SELECT revision FROM revision_state WHERE namespace=?1").bind(m.dataset).first()]);
  if (a.mode !== "SERVICE_PRIMARY") return apiError("SERVICE_NOT_WRITE_AUTHORITY", "CONFLICT", 409, true);
  if (!audits.length) {
    await env.DB.prepare("UPDATE import_batches SET state='ROLLED_BACK',rolled_back_at=?1 WHERE import_batch_id=?2 AND state='COMMITTED'").bind(nowIso(), id).run();
    return json({ ok: true, import_batch_id: id, state: "ROLLED_BACK", dataset: m.dataset, revision: revRow?.revision ?? 0, corrected: 0 });
  }
  const revision = (revRow?.revision ?? 0) + 1, events = [], rows2 = [];
  let seq = a.authority_seq;
  for (const x2 of audits) {
    const before = JSON.parse(x2.before_json), after2 = JSON.parse(x2.after_json), projection = { ...before, _checksum: await sha256Hex(JSON.stringify(before)) };
    events.push(await buildEvent2(a, auth4, m.dataset, x2.business_key, id, x2.row_no, after2, before, revision, ++seq, "MASTER_IMPORT_ROLLBACK"));
    rows2.push(projection);
  }
  const stmts = [];
  const rowChunks = chunks(rows2), eventChunks = chunks(events);
  for (let i2 = 0; i2 < rowChunks.length; i2++) {
    stmts.push(...projectionStatements(env.DB, m.dataset, rowChunks[i2]));
    stmts.push(eventInsert(env.DB, eventChunks[i2]));
    stmts.push(outboxInsert(env.DB, eventChunks[i2]));
  }
  const at = nowIso();
  stmts.push(env.DB.prepare("UPDATE authority_state SET authority_seq=?1,updated_at=?2 WHERE singleton_id=1 AND authority_epoch=?3 AND authority_seq=?4").bind(seq, at, a.authority_epoch, a.authority_seq));
  stmts.push(env.DB.prepare("UPDATE revision_state SET revision=?1,updated_at=?2 WHERE namespace=?3").bind(revision, at, m.dataset));
  stmts.push(env.DB.prepare("UPDATE import_batches SET state='ROLLED_BACK',rolled_back_at=?1 WHERE import_batch_id=?2 AND state='COMMITTED'").bind(at, id));
  try {
    await env.DB.batch(stmts);
  } catch (e) {
    return apiError("IMPORT_ROLLBACK_CONFLICT", "TRANSIENT", 409, true, String(e).slice(0, 180));
  }
  await notify(env, m.dataset, revision, { authority_epoch: a.authority_epoch, authority_seq: seq, service_generation: a.service_generation });
  return json({ ok: true, import_batch_id: id, state: "ROLLED_BACK", dataset: m.dataset, revision, corrected: audits.length });
}
__name(importRollbackAtomic, "importRollbackAtomic");

// src/realtime.ts
import { DurableObject } from "cloudflare:workers";
var RealtimeHub = class extends DurableObject {
  static {
    __name(this, "RealtimeHub");
  }
  async fetch(request) {
    if (request.headers.get("Upgrade") !== "websocket") return json({ ok: false, error: "WEBSOCKET_REQUIRED" }, 426);
    const url = new URL(request.url);
    const pair = new WebSocketPair();
    const sockets = Object.values(pair);
    const client = sockets[0], server = sockets[1];
    if (!client || !server) return json({ ok: false, error: "WEBSOCKET_PAIR_FAILED" }, 500);
    const device = url.searchParams.get("device_id") || "unknown";
    this.ctx.acceptWebSocket(server, [`device:${device.slice(0, 180)}`]);
    server.serializeAttachment({ device_id: device.slice(0, 180), connected_at: nowIso() });
    server.send(JSON.stringify({ type: "REALTIME_READY", at: nowIso(), protocol: "INVALIDATION_V1" }));
    return new Response(null, { status: 101, webSocket: client });
  }
  async broadcast(event) {
    return this.invalidate({ type: "DAY_CHANGED", business_date: event.business_date, day_revision: event.authority_seq, authority_epoch: event.authority_epoch, authority_seq: event.authority_seq, service_generation: event.service_generation, event_id: event.event_id, entity_type: event.entity_type, entity_id: event.entity_id, new_version: event.new_version });
  }
  async invalidate(message) {
    const payload3 = JSON.stringify(message);
    if (payload3.length > 4096) throw new Error("REALTIME_INVALIDATION_TOO_LARGE");
    let delivered = 0;
    for (const ws of this.ctx.getWebSockets()) {
      try {
        ws.send(payload3);
        delivered++;
      } catch {
      }
    }
    return delivered;
  }
  async connectionCount() {
    return this.ctx.getWebSockets().length;
  }
  webSocketMessage(ws, message) {
    if (typeof message === "string" && message === "ping") ws.send("pong");
  }
  webSocketClose(_ws, _code, _reason, _wasClean) {
  }
};

// src/index.ts
function statusParts(row) {
  const authority2 = { authority_epoch: row.authority_epoch, authority_seq: row.authority_seq, mode: row.authority_mode, scope: row.authority_scope, service_generation: row.authority_generation, updated_at: row.authority_updated_at };
  const replication = { target_kind: row.target_kind, target_identity: row.target_identity, schema_version: row.replication_schema_version, state: row.replication_state, checkpoint: row.checkpoint, pending_count: Number(row.actual_pending_count ?? 0), retry_count: Number(row.retry_count ?? 0), last_attempt_at: row.last_attempt_at, last_success_at: row.last_success_at, last_error_class: row.last_error_class, last_error: row.last_error, updated_at: row.replication_updated_at };
  return { authority: authority2, replication };
}
__name(statusParts, "statusParts");
async function ensureConfiguredGeneration(env) {
  const a = await env.DB.prepare("SELECT service_generation FROM authority_state WHERE singleton_id=1").first();
  if (a?.service_generation === "UNCONFIGURED") await env.DB.prepare("UPDATE authority_state SET service_generation=?1,updated_at=?2 WHERE singleton_id=1 AND service_generation='UNCONFIGURED'").bind(env.SERVICE_GENERATION, nowIso()).run();
}
__name(ensureConfiguredGeneration, "ensureConfiguredGeneration");
async function requireAuth(request, env) {
  const a = await authenticate(env.DB, env, request);
  if (!a) throw new CoreError("UNAUTHORIZED", "AUTH", 401);
  return a;
}
__name(requireAuth, "requireAuth");
async function gasBridgeAuthorized(request, env) {
  const supplied = request.headers.get("x-gas-bridge-secret") || "";
  if (!supplied) return false;
  return constantTimeEqual(await sha256Hex(supplied), await sha256Hex(env.GAS_BRIDGE_SHARED_SECRET));
}
__name(gasBridgeAuthorized, "gasBridgeAuthorized");
function eventPublic(e) {
  return e;
}
__name(eventPublic, "eventPublic");
async function broadcastEvent(env, e) {
  const hub = env.REALTIME_HUB.getByName(`business:${e.business_date}`);
  try {
    return await hub.broadcast(e);
  } catch (err2) {
    console.log(JSON.stringify({ level: "warn", kind: "realtime_broadcast_failed", event_id: e.event_id, error: String(err2) }));
    return 0;
  }
}
__name(broadcastEvent, "broadcastEvent");
async function healthSnapshot(env) {
  const q4 = `SELECT a.authority_epoch,a.authority_seq,a.mode AS authority_mode,a.scope AS authority_scope,a.service_generation AS authority_generation,a.updated_at AS authority_updated_at,
    r.target_kind,r.target_identity,r.schema_version AS replication_schema_version,r.state AS replication_state,r.checkpoint,r.pending_count AS replication_pending_count,r.retry_count,r.last_attempt_at,r.last_success_at,r.last_error_class,r.last_error,r.updated_at AS replication_updated_at,
    (SELECT COUNT(*) FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')) AS actual_pending_count,
    NULL AS business_date,NULL AS sequence_no
    FROM authority_state a LEFT JOIN replication_status r ON r.singleton_id=1 WHERE a.singleton_id=1`;
  const result = await env.DB.prepare(q4).first();
  if (!result) throw new CoreError("AUTHORITY_STATE_MISSING", "INTEGRITY", 503, false);
  if (result.authority_generation === "UNCONFIGURED") {
    const at = nowIso();
    await env.DB.prepare("UPDATE authority_state SET service_generation=?1,updated_at=?2 WHERE singleton_id=1 AND service_generation='UNCONFIGURED'").bind(env.SERVICE_GENERATION, at).run();
    result.authority_generation = env.SERVICE_GENERATION;
    result.authority_updated_at = at;
  }
  const { authority: authority2, replication } = statusParts(result);
  return json({ ok: true, service: "pick-pack-1291-service", environment: result.authority_scope === "STAGING_SHADOW" ? "staging-shadow" : "production", generation: env.SERVICE_GENERATION, authority: authority2, replication });
}
__name(healthSnapshot, "healthSnapshot");
async function realtimeTicket(request, env) {
  const auth4 = await requireAuth(request, env), u = new URL(request.url), scope = u.searchParams.get("scope") === "master" ? "master" : "day", requested = u.searchParams.get("business_date") || "", date = scope === "master" ? "__MASTER__" : requested;
  if (scope === "day" && !/^\d{4}-\d{2}-\d{2}$/.test(date)) return apiError("BUSINESS_DATE_INVALID", "VALIDATION", 400);
  const ticket = crypto.randomUUID(), expires = Date.now() + 12e4, createdAt = nowIso();
  await env.DB.batch([
    env.DB.prepare("DELETE FROM realtime_tickets WHERE expires_at<?1").bind(Date.now()),
    env.DB.prepare("INSERT INTO realtime_tickets(ticket_id,login_id,device_id,business_date,expires_at,created_at) VALUES(?1,?2,?3,?4,?5,?6)").bind(ticket, auth4.login_id, auth4.device_id, date, expires, createdAt)
  ]);
  return json({ ok: true, ticket, expires_at: expires, scope, business_date: scope === "day" ? date : null });
}
__name(realtimeTicket, "realtimeTicket");
async function realtimeConnect(request, env) {
  if (request.headers.get("Upgrade") !== "websocket") return apiError("WEBSOCKET_REQUIRED", "VALIDATION", 426);
  const u = new URL(request.url), ticket = u.searchParams.get("ticket") || "";
  const row = await env.DB.prepare("SELECT ticket_id,login_id,device_id,business_date,expires_at FROM realtime_tickets WHERE ticket_id=?1").bind(ticket).first();
  if (!row || row.expires_at < Date.now()) return apiError("REALTIME_TICKET_INVALID", "AUTH", 401);
  await env.DB.prepare("DELETE FROM realtime_tickets WHERE ticket_id=?1").bind(ticket).run();
  const hub = env.REALTIME_HUB.getByName(row.business_date === "__MASTER__" ? "master:global" : `business:${row.business_date}`), target = new URL(request.url);
  target.searchParams.set("device_id", row.device_id);
  target.searchParams.set("login_id", row.login_id);
  return hub.fetch(new Request(target, request));
}
__name(realtimeConnect, "realtimeConnect");
async function bootstrapSnapshot(request, env) {
  const auth4 = await requireAuth(request, env), u = new URL(request.url), date = u.searchParams.get("business_date") || "";
  if (date && !(auth4.role === "SUPERADMIN" && u.searchParams.get("client_source") === "WEB")) {
    const allowed2 = await env.DB.prepare("SELECT 1 x FROM (SELECT business_date FROM business_dates ORDER BY sequence_no DESC LIMIT 7) WHERE business_date=?1").bind(date).first();
    if (!allowed2) return apiError("BUSINESS_DATE_OUTSIDE_VIEW_WINDOW", "PERMISSION", 403);
  }
  const results = await env.DB.batch([
    env.DB.prepare("SELECT mnv,full_name,phone,main_position,supplier,department,site,warehouse,start_date,note FROM employees ORDER BY mnv"),
    env.DB.prepare("SELECT resource_type,resource_id,status_label,available,metadata_json FROM resources ORDER BY resource_type,resource_id"),
    env.DB.prepare("SELECT namespace,ordinal,value FROM catalog_values ORDER BY namespace,ordinal"),
    date ? env.DB.prepare("SELECT * FROM attendance_sessions WHERE business_date=?1 ORDER BY mnv").bind(date) : env.DB.prepare("SELECT * FROM attendance_sessions WHERE 0"),
    date ? env.DB.prepare("SELECT * FROM labor_sessions WHERE business_date=?1 ORDER BY mnv,start_at").bind(date) : env.DB.prepare("SELECT * FROM labor_sessions WHERE 0"),
    env.DB.prepare("SELECT authority_epoch,authority_seq,mode,scope,service_generation,updated_at FROM authority_state WHERE singleton_id=1")
  ]);
  const authority2 = results[5]?.results?.[0];
  if (!authority2) throw new CoreError("AUTHORITY_STATE_MISSING", "INTEGRITY", 503, false);
  return json({ ok: true, authority: authority2, employees: results[0]?.results ?? [], resources: results[1]?.results ?? [], catalogs: results[2]?.results ?? [], attendance: results[3]?.results ?? [], labor: results[4]?.results ?? [] });
}
__name(bootstrapSnapshot, "bootstrapSnapshot");
async function mutate(request, env) {
  const auth4 = await requireAuth(request, env), body = await readJsonBody(request), result = await commitMutation(env.DB, env, auth4, body), e = result.event;
  const delivered = await broadcastEvent(env, { event_id: e.event_id, event_type: e.event_type, entity_type: e.entity_type, entity_id: e.entity_id, business_date: e.business_date, authority_epoch: e.authority_epoch, authority_seq: e.authority_seq, service_generation: e.service_generation, new_version: e.new_version });
  return json({ ok: true, duplicate: result.duplicate, event: eventPublic(e), realtime_delivered: delivered }, result.duplicate ? 200 : 201);
}
__name(mutate, "mutate");
async function mutateBatch(request, env) {
  const auth4 = await requireAuth(request, env), body = await readJsonBody(request), events = Array.isArray(body.events) ? body.events : [];
  if (!events.length || events.length > 100) return apiError("MUTATION_BATCH_INVALID", "VALIDATION", 400);
  const results = [];
  for (const input of events) {
    const localEventId = String(input?.event_id || "");
    try {
      const result = await commitMutation(env.DB, env, auth4, input), e = result.event, delivered = await broadcastEvent(env, e);
      results.push({ local_event_id: localEventId, status: result.duplicate ? "DUPLICATE" : "CONFIRMED", canonical_event_id: e.event_id, authority_epoch: e.authority_epoch, authority_seq: e.authority_seq, new_version: e.new_version, error_code: null, conflict: null, realtime_delivered: delivered });
    } catch (err2) {
      if (err2 instanceof CoreError) {
        const review = err2.errorClass === "CONFLICT" || err2.errorClass === "RESOURCE";
        results.push({ local_event_id: localEventId, status: review ? "REVIEW_REQUIRED" : "REJECTED", canonical_event_id: null, authority_epoch: null, authority_seq: null, new_version: null, error_code: err2.code, conflict: err2.conflict ?? null, retryable: err2.retryable });
        continue;
      }
      throw err2;
    }
  }
  return json({ ok: true, results });
}
__name(mutateBatch, "mutateBatch");
async function legacyMutation(request, env) {
  const auth4 = await requireAuth(request, env), input = await readJsonBody(request), result = await commitLegacyMutation(env.DB, env, auth4, input), e = result.event;
  const delivered = await broadcastEvent(env, e);
  return json({ ...result, realtime_delivered: delivered }, result.duplicate ? 200 : 201);
}
__name(legacyMutation, "legacyMutation");
async function adminAuditDirect(request, env) {
  const auth4 = await requireAuth(request, env), input = await readJsonBody(request), result = await commitAdminAudit(env.DB, auth4, input), e = result.event;
  const delivered = await broadcastEvent(env, e);
  return json({ ok: true, duplicate: result.duplicate, event: eventPublic(e), realtime_delivered: delivered }, result.duplicate ? 200 : 201);
}
__name(adminAuditDirect, "adminAuditDirect");
async function legacyMutationBatch(request, env) {
  const auth4 = await requireAuth(request, env), body = await readJsonBody(request), events = Array.isArray(body.events) ? body.events : [];
  if (!events.length || events.length > 100) return apiError("LEGACY_MUTATION_BATCH_INVALID", "VALIDATION", 400);
  const results = [];
  for (const input of events) {
    const localEventId = String(input?.event_id || "");
    try {
      if (String(input.action || "") === "admin_audit") {
        const ai = input, ar = await commitAdminAudit(env.DB, auth4, ai), ae = ar.event, delivered2 = await broadcastEvent(env, ae);
        results.push({ local_event_id: localEventId, status: ar.duplicate ? "DUPLICATE" : "CONFIRMED", canonical_event_id: ae.event_id, authority_epoch: ae.authority_epoch, authority_seq: ae.authority_seq, new_version: 0, error_code: null, conflict: null, realtime_delivered: delivered2 });
        continue;
      }
      const result = await commitLegacyMutation(env.DB, env, auth4, input), e = result.event, delivered = await broadcastEvent(env, e);
      results.push({ local_event_id: localEventId, status: result.duplicate ? "DUPLICATE" : "CONFIRMED", canonical_event_id: e.event_id, authority_epoch: e.authority_epoch, authority_seq: e.authority_seq, new_version: e.new_version, error_code: null, conflict: null, realtime_delivered: delivered });
    } catch (err2) {
      if (err2 instanceof CoreError) {
        const review = err2.errorClass === "CONFLICT" || err2.errorClass === "RESOURCE";
        results.push({ local_event_id: localEventId, status: review ? "REVIEW_REQUIRED" : "REJECTED", canonical_event_id: null, authority_epoch: null, authority_seq: null, new_version: null, error_code: err2.code, conflict: err2.conflict ?? null, retryable: err2.retryable });
        continue;
      }
      throw err2;
    }
  }
  return json({ ok: true, results });
}
__name(legacyMutationBatch, "legacyMutationBatch");
async function gasLegacyBridge(request, env) {
  if (!await gasBridgeAuthorized(request, env)) return apiError("GAS_BRIDGE_UNAUTHORIZED", "AUTH", 401);
  const body = await readJsonBody(request), actor = body.actor;
  if (!actor?.login_id || !["SUPERADMIN", "ADMIN", "USER"].includes(actor.role)) return apiError("GAS_BRIDGE_ACTOR_INVALID", "VALIDATION", 400);
  const auth4 = { login_id: actor.login_id, role: actor.role, display_name: actor.display_name || actor.login_id, device_id: actor.device_id || body.mutation.device_id || "gas-legacy", session_id: "GAS_BRIDGE", verifier_hash: "GAS_BRIDGE" };
  const result = await commitLegacyMutation(env.DB, env, auth4, body.mutation), e = result.event;
  const delivered = await broadcastEvent(env, e);
  return json({ ...result, realtime_delivered: delivered }, result.duplicate ? 200 : 201);
}
__name(gasLegacyBridge, "gasLegacyBridge");
async function transitionWithAudit(env, input) {
  const before = await currentAuthority(env.DB), productionPromotion = (input.scope === "PRODUCTION" || before.scope === "PRODUCTION") && input.mode === "SERVICE_PRIMARY" && Boolean(input.increment_epoch);
  if (productionPromotion && input.confirmation !== "OWNER_LOCKED_M2_CUTOVER") throw new CoreError("PRODUCTION_PROMOTION_CONFIRMATION_REQUIRED", "PERMISSION", 403);
  const after2 = await transitionAuthority(env.DB, input), at = nowIso();
  await env.DB.prepare(`INSERT INTO authority_transitions(from_epoch,to_epoch,from_mode,to_mode,from_generation,to_generation,reason,initiated_by,checkpoint_epoch,checkpoint_seq,validation_json,created_at)
    VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,'{}',?11)`).bind(before.authority_epoch, after2.authority_epoch, before.mode, after2.mode, before.service_generation, after2.service_generation, String(input.reason || "UNSPECIFIED").slice(0, 500), String(input.initiated_by || "M2_INTERNAL").slice(0, 180), before.authority_epoch, before.authority_seq, at).run();
  return { ok: true, before, authority: after2 };
}
__name(transitionWithAudit, "transitionWithAudit");
async function fallbackIngest(request, env) {
  if (!await gasBridgeAuthorized(request, env)) return apiError("GAS_BRIDGE_UNAUTHORIZED", "AUTH", 401);
  const b = await readJsonBody(request), a = await currentAuthority(env.DB);
  if (!["GOOGLE_FALLBACK", "RECONCILING"].includes(a.mode)) return apiError("FALLBACK_INGEST_NOT_ALLOWED", "CONFLICT", 409, false, void 0, { mode: a.mode });
  await env.DB.prepare(`INSERT INTO fallback_event_inbox(event_id,authority_epoch,authority_seq,service_generation,event_json,checksum,source,ingest_status,received_at)
    VALUES(?1,?2,?3,?4,?5,?6,'GOOGLE_FALLBACK','PENDING',?7) ON CONFLICT(event_id) DO NOTHING`).bind(b.event_id, b.authority_epoch, b.authority_seq, b.service_generation, JSON.stringify(b.event), b.checksum, nowIso()).run();
  return json({ ok: true, event_id: b.event_id });
}
__name(fallbackIngest, "fallbackIngest");
async function drManifest(env) {
  const a = await currentAuthority(env.DB), tables = ["events", "employees", "attendance_sessions", "labor_sessions"], counts = {};
  for (const t of tables) {
    const c = await env.DB.prepare(`SELECT COUNT(*) n FROM ${t}`).first();
    counts[t] = c?.n ?? 0;
  }
  const raw = { authority_epoch: a.authority_epoch, authority_seq: a.authority_seq, service_generation: a.service_generation, event_count: counts.events ?? 0, employee_count: counts.employees ?? 0, attendance_count: counts.attendance_sessions ?? 0, labor_count: counts.labor_sessions ?? 0 }, checksum2 = await sha256Hex(JSON.stringify(raw)), manifestId = crypto.randomUUID(), at = nowIso();
  await env.DB.prepare("INSERT INTO dr_manifests(manifest_id,authority_epoch,authority_seq,service_generation,event_count,employee_count,attendance_count,labor_count,checksum,manifest_json,created_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11)").bind(manifestId, a.authority_epoch, a.authority_seq, a.service_generation, raw.event_count, raw.employee_count, raw.attendance_count, raw.labor_count, checksum2, JSON.stringify(raw), at).run();
  return { ok: true, manifest_id: manifestId, checksum: checksum2, ...raw, created_at: at };
}
__name(drManifest, "drManifest");
async function internalTestAccount(request, env) {
  if (!await internalAuthorized(request, env)) return apiError("INTERNAL_UNAUTHORIZED", "AUTH", 401);
  const b = await readJsonBody(request), login = String(b.login_id || "").trim(), verifier = String(b.verifier || "").trim();
  if (!login || !verifier) return apiError("TEST_ACCOUNT_FIELDS_REQUIRED", "VALIDATION", 400);
  const role3 = b.role ?? "SUPERADMIN";
  await env.DB.prepare(`INSERT INTO accounts(login_id,verifier,verifier_hash,role,display_name,position,email,status,source_row,source_checksum,is_shadow_test) VALUES(?1,?2,?3,?4,?1,?5,'','ACTIVE',0,'M1_SHADOW_TEST',1)
    ON CONFLICT(login_id) DO UPDATE SET verifier=excluded.verifier,verifier_hash=excluded.verifier_hash,role=excluded.role,display_name=excluded.display_name,position=excluded.position,status='ACTIVE',is_shadow_test=1`).bind(login, verifier, await sha256Hex(verifier), role3, role3.toLowerCase()).run();
  return json({ ok: true, login_id: login, role: role3 });
}
__name(internalTestAccount, "internalTestAccount");
async function route(request, env) {
  const u = new URL(request.url), p = u.pathname, method = request.method.toUpperCase();
  if (p === "/health" && method === "GET") return healthSnapshot(env);
  if (p === "/v1/capabilities" && method === "GET") return json({ ok: true, api_version: "v1", canonical_event_schema: 1, auth: "PBKDF2_HMAC_SHA256_CHALLENGE", session_model: "SINGLE_ACTIVE_DEVICE_V1", realtime: "DURABLE_OBJECT_WEBSOCKET_HIBERNATION", realtime_protocol: "INVALIDATION_V1", delta: true, revision_namespaces: true, business_window: 7, mutation_batch: true, offline_outbox: true, fcm_wake: true, import_engine: true, historical_corrections: true, legacy_adapter: true, authority_modes: ["SERVICE_PRIMARY", "GOOGLE_FALLBACK", "OFFLINE_LOCAL", "RECONCILING"], production_cutover: (await currentAuthority(env.DB)).scope === "PRODUCTION" });
  if (p === "/v1/authority" && method === "GET") return json({ ok: true, authority: await currentAuthority(env.DB) });
  if (p === "/v1/auth/challenge" && method === "POST") {
    const b = await readJsonBody(request);
    return json(await createChallenge(env.DB, String(b.login_id || "").trim()));
  }
  if (p === "/v1/auth/login" && method === "POST") {
    const b = await readJsonBody(request), out = await createSession(env.DB, env, b);
    return json(out, out.ok === false ? 401 : 200);
  }
  if (p === "/v1/auth/logout" && method === "POST") {
    const a = await requireAuth(request, env);
    await logout(env.DB, a);
    return json({ ok: true });
  }
  if (p === "/v1/mutations" && method === "POST") return mutate(request, env);
  if (p === "/v1/mutations/batch" && method === "POST") return mutateBatch(request, env);
  if (p === "/v1/corrections" && method === "POST") return historicalCorrection(request, env);
  if (p === "/v1/legacy-mutations" && method === "POST") return legacyMutation(request, env);
  if (p === "/v1/legacy-mutations/batch" && method === "POST") return legacyMutationBatch(request, env);
  if (p === "/v1/admin/audit" && method === "POST") return adminAuditDirect(request, env);
  if (p === "/v1/delta" && method === "GET") {
    await requireAuth(request, env);
    const epoch = Number(u.searchParams.get("authority_epoch") || "0"), after2 = Number(u.searchParams.get("after_seq") || "0"), limit = Number(u.searchParams.get("limit") || "500");
    return json({ ok: true, ...await delta(env.DB, epoch, after2, limit) });
  }
  if (p === "/v1/sync/status" && method === "GET") return syncStatusV2(request, env);
  if (p === "/v1/delta/day" && method === "GET") return dayDeltaV2(request, env);
  if (p === "/v1/delta/master" && method === "GET") return masterDeltaV2(request, env);
  if (p === "/v1/bootstrap" && method === "GET") return bootstrapSnapshot(request, env);
  if (p === "/v1/realtime/ticket" && method === "POST") return realtimeTicket(request, env);
  if (p === "/v1/realtime" && method === "GET") return realtimeConnect(request, env);
  if (p === "/v1/push/register" && method === "POST") return registerPushDevice(request, env);
  if (p === "/v1/push/revoke" && method === "POST") return revokePushDevice(request, env);
  if (p === "/v1/import/schema" && method === "GET") return importSchema(request, env);
  if (p === "/v1/import/batches" && method === "POST") return importStart(request, env);
  if (p === "/v1/import/history" && method === "GET") return importHistory(request, env);
  const im = p.match(/^\/v1\/import\/batches\/([^/]+)\/(chunks|preview|commit|rollback)$/);
  if (im) {
    const id = decodeURIComponent(im[1]), op = im[2];
    if (op === "chunks" && (method === "POST" || method === "PUT")) return importChunk(request, env, id);
    if (op === "preview" && method === "POST") return importPreview(request, env, id);
    if (op === "commit" && method === "POST") return importCommitAtomic(request, env, id);
    if (op === "rollback" && method === "POST") return importRollbackAtomic(request, env, id);
  }
  if (p === "/internal/legacy-bridge" && method === "POST") return gasLegacyBridge(request, env);
  if (p === "/internal/fallback/ingest" && method === "POST") return fallbackIngest(request, env);
  if (p === "/internal/bootstrap-google" && method === "POST") {
    if (!await internalAuthorized(request, env)) return apiError("INTERNAL_UNAUTHORIZED", "AUTH", 401);
    await ensureConfiguredGeneration(env);
    return json(await bootstrapFromGoogle(env.DB, env));
  }
  if (p === "/internal/replicate" && method === "POST") {
    if (!await internalAuthorized(request, env)) return apiError("INTERNAL_UNAUTHORIZED", "AUTH", 401);
    return json(await replicatePending(env.DB, env));
  }
  if (p === "/internal/push/flush" && method === "POST") {
    if (!await internalAuthorized(request, env)) return apiError("INTERNAL_UNAUTHORIZED", "AUTH", 401);
    return json({ ok: true, ...await flushPushOutbox(env.DB, env) });
  }
  if (p === "/internal/test-account" && method === "POST") return internalTestAccount(request, env);
  if (p === "/internal/dr/manifest" && method === "POST") {
    if (!await internalAuthorized(request, env)) return apiError("INTERNAL_UNAUTHORIZED", "AUTH", 401);
    return json(await drManifest(env));
  }
  if (p === "/internal/authority/transition" && method === "POST") {
    if (!await internalAuthorized(request, env)) return apiError("INTERNAL_UNAUTHORIZED", "AUTH", 401);
    const b = await readJsonBody(request);
    return json(await transitionWithAudit(env, b));
  }
  return apiError("NOT_FOUND", "VALIDATION", 404);
}
__name(route, "route");
var index_default = {
  async fetch(request, env) {
    const started = Date.now(), requestId = request.headers.get("x-request-id")?.slice(0, 100) || crypto.randomUUID(), path = new URL(request.url).pathname;
    try {
      const response = await route(request, env);
      if (response.status !== 101) response.headers.set("x-request-id", requestId);
      console.log(JSON.stringify({ level: "info", kind: "request_complete", request_id: requestId, route: path, method: request.method, status: response.status, wall_ms: Date.now() - started }));
      return response;
    } catch (e) {
      if (e instanceof CoreError) return apiError(e.code, e.errorClass, e.status, e.retryable, void 0, e.conflict);
      console.log(JSON.stringify({ level: "error", kind: "request_failed", request_id: requestId, route: path, method: request.method, wall_ms: Date.now() - started, error_class: "INTERNAL", error: String(e).slice(0, 240) }));
      return apiError("INTERNAL_ERROR", "INTERNAL", 500, true);
    }
  },
  async scheduled(_controller, env, ctx) {
    ctx.waitUntil(Promise.all([replicatePending(env.DB, env), flushPushOutbox(env.DB, env)]).then(() => void 0).catch((e) => console.log(JSON.stringify({ level: "error", kind: "scheduled_background_failed", error: String(e).slice(0, 240) }))));
  }
};

// src/bootstrap_resumable.ts
var EXPECTED2 = [
  { name: "Danh m\u1EE5c", headers: ["DANH S\xC1CH NH\xC2N S\u1EF0_V\u1ECB tr\xED ch\xEDnh", "DANH S\xC1CH NH\xC2N S\u1EF0_Nh\xE0 cung c\u1EA5p", "DANH S\xC1CH NH\xC2N S\u1EF0_B\u1ED9 ph\u1EADn", "DANH S\xC1CH NH\xC2N S\u1EF0_Site", "DANH S\xC1CH NH\xC2N S\u1EF0_Kho", "DANH S\xC1CH PDA_T\xECnh tr\u1EA1ng", "DANH S\xC1CH USER PICK_T\xECnh tr\u1EA1ng", "DANH S\xC1CH B\xC0N PACK_T\xECnh tr\u1EA1ng", "DANH S\xC1CH USER PACK_T\xECnh tr\u1EA1ng", "RA - V\xC0O TRONG CA_Lo\u1EA1i thao t\xE1c", "V\xC0O - RA TRONG CA_Ca", "C\xD4NG NH\u1EACT_Th\xF4ng tin c\xF4ng nh\u1EADt", "C\xD4NG NH\u1EACT_M\u1ED1c th\u1EDDi gian", "C\xD4NG NH\u1EACT_Tr\u1EA1ng th\xE1i"] },
  { name: "L\u1ECACH S\u1EEC NGHI\u1EC6P V\u1EE4", headers: ["Ng\xE0y", "Session ID", "M\xE3 nh\xE2n vi\xEAn", "H\u1ECD t\xEAn", "Ca", "Lo\u1EA1i s\u1EF1 ki\u1EC7n", "Nh\xE3n s\u1EF1 ki\u1EC7n", "Th\u1EDDi gian", "Ng\u01B0\u1EDDi x\u1EED l\xFD", "Chi ti\u1EBFt", "Event ID", "Ph\u1EA1m vi", "App Revision"] },
  { name: "DANH S\xC1CH PDA", headers: ["Seri PDA", "5 s\u1ED1 cu\u1ED1i Seri", "T\xECnh tr\u1EA1ng", "Ghi ch\xFA"] },
  { name: "DANH S\xC1CH USER PICK", headers: ["S\u1ED1 User", "User Pick", "T\xECnh tr\u1EA1ng", "Ghi ch\xFA"] },
  { name: "DANH S\xC1CH B\xC0N PACK", headers: ["T\xEAn b\xE0n pack", "T\xECnh tr\u1EA1ng"] },
  { name: "DANH S\xC1CH USER PACK", headers: ["T\xEAn b\xE0n pack", "User pack", "User Pack", "T\xECnh tr\u1EA1ng"] },
  { name: "DANH S\xC1CH NH\xC2N S\u1EF0", headers: ["M\xE3 nh\xE2n vi\xEAn", "H\u1ECD v\xE0 t\xEAn", "S\u1ED1 \u0111i\u1EC7n tho\u1EA1i", "V\u1ECB tr\xED ch\xEDnh", "Nh\xE0 cung c\u1EA5p", "B\u1ED9 ph\u1EADn", "Site", "Kho", "Ng\xE0y b\u1EAFt \u0111\u1EA7u l\xE0m vi\u1EC7c", "Ghi ch\xFA", "Ng\u01B0\u1EDDi c\u1EADp nh\u1EADt", "Th\u1EDDi gian c\u1EADp nh\u1EADt"] },
  { name: "RA - V\xC0O TRONG CA", headers: ["Ng\xE0y", "Ca", "M\xE3 nh\xE2n vi\xEAn", "H\u1ECD v\xE0 t\xEAn", "S\u1ED1 \u0111i\u1EC7n tho\u1EA1i", "Nh\xE0 cung c\u1EA5p", "B\u1ED9 ph\u1EADn", "Site", "Kho", "V\u1ECB tr\xED ch\xEDnh", "V\u1ECB tr\xED trong ca", "Seri PDA", "User Pick", "B\xE0n Pack", "User Pack", "Lo\u1EA1i thao t\xE1c", "Ghi ch\xFA", "Ng\u01B0\u1EDDi c\u1EADp nh\u1EADt", "Th\u1EDDi gian c\u1EADp nh\u1EADt", "Event ID", "App action", "App revision"] },
  { name: "C\xD4NG NH\u1EACT", headers: ["Ng\xE0y", "Ca", "M\xE3 nh\xE2n vi\xEAn", "H\u1ECD v\xE0 t\xEAn", "S\u1ED1 \u0111i\u1EC7n tho\u1EA1i", "Nh\xE0 cung c\u1EA5p", "B\u1ED9 ph\u1EADn", "Site", "Kho", "V\u1ECB tr\xED ch\xEDnh", "V\u1ECB tr\xED trong ca", "Th\xF4ng tin c\xF4ng nh\u1EADt", "Th\u1EDDi gian b\u1EAFt \u0111\u1EA7u", "Th\u1EDDi gian k\u1EBFt th\xFAc", "M\u1ED1c th\u1EDDi gian", "Tr\u1EA1ng th\xE1i", "Ghi ch\xFA", "Ng\u01B0\u1EDDi c\u1EADp nh\u1EADt", "Th\u1EDDi gian c\u1EADp nh\u1EADt", "Event ID", "Finish Event ID", "App revision", "Kh\u1EA5u tr\u1EEB nh\xE2n s\u1EF1"] },
  { name: "Danh s\xE1ch Admin", headers: ["S\u1ED1 User", "Password verifier", "T\xECnh tr\u1EA1ng", "Ghi ch\xFA", "V\u1ECB tr\xED", "Mail", "Logic quy\u1EC1n c\u01A1 b\u1EA3n", "", "Tr\u1EA1ng th\xE1i t\xE0i kho\u1EA3n", "Ng\u01B0\u1EDDi c\u1EADp nh\u1EADt", "Th\u1EDDi gian c\u1EADp nh\u1EADt"] }
];
var FETCH_ROWS = 200;
var ATTENDANCE_ROWS = 120;
var LABOR_ROWS = 160;
var LEASE_ROWS = 160;
async function googleToken(env) {
  const body = new URLSearchParams({ client_id: env.GOOGLE_OAUTH_CLIENT_ID, client_secret: env.GOOGLE_OAUTH_CLIENT_SECRET, refresh_token: env.GOOGLE_OAUTH_REFRESH_TOKEN, grant_type: "refresh_token" });
  const r = await fetch("https://oauth2.googleapis.com/token", { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" }, body });
  const j = await r.json();
  if (!r.ok || !j.access_token) throw new Error(`GOOGLE_OAUTH:${j.error ?? r.status}`);
  return j.access_token;
}
__name(googleToken, "googleToken");
function auth2(t) {
  return { authorization: `Bearer ${t}` };
}
__name(auth2, "auth");
function q3(name) {
  return `'${name.replace(/'/g, "''")}'`;
}
__name(q3, "q");
function obj2(headers, row) {
  const out = {};
  headers.forEach((h, i2) => {
    if (h) out[h] = String(row[i2] ?? "").trim();
  });
  return out;
}
__name(obj2, "obj");
function normRow2(row, n) {
  return Array.from({ length: n }, (_, i2) => String(row[i2] ?? "").trim());
}
__name(normRow2, "normRow");
function activeStatus2(v) {
  return isAvailableLabel(v) || ["ACTIVE", "HOAT DONG", "DANG HOAT DONG"].includes(fold(v)) ? "ACTIVE" : "DISABLED";
}
__name(activeStatus2, "activeStatus");
function role2(v) {
  const f = fold(v);
  return f === "SUPERADMIN" ? "SUPERADMIN" : f === "ADMIN" ? "ADMIN" : "USER";
}
__name(role2, "role");
async function runChunks2(db, stmts, size = 50) {
  for (let i2 = 0; i2 < stmts.length; i2 += size) await db.batch(stmts.slice(i2, i2 + size));
}
__name(runChunks2, "runChunks");
function initialState() {
  return { schema_version: 2, mode: "RESUMABLE", phase: "FETCH", sheet_index: 0, next_row: 1, current_sheet_rows: 0, current_sheet_checksum: "", sheet_report: [], business_dates: [], cursor: 0 };
}
__name(initialState, "initialState");
function parseState(raw) {
  const s = JSON.parse(raw);
  if (s?.schema_version !== 2 || s.mode !== "RESUMABLE") throw new Error("BOOTSTRAP_STATE_VERSION_INVALID");
  return s;
}
__name(parseState, "parseState");
async function saveState(db, runId, state) {
  await db.prepare("UPDATE bootstrap_runs SET manifest_json=?1 WHERE run_id=?2 AND status='RUNNING'").bind(JSON.stringify(state), runId).run();
}
__name(saveState, "saveState");
async function ensureShadow(db) {
  const a = await db.prepare("SELECT scope FROM authority_state WHERE singleton_id=1").first();
  if (a?.scope !== "STAGING_SHADOW") throw new Error("BOOTSTRAP_ONLY_ALLOWED_IN_STAGING_SHADOW");
}
__name(ensureShadow, "ensureShadow");
async function validateWorkbook(env) {
  const t = await googleToken(env), id = env.GOOGLE_SOURCE_SHEET_ID;
  const r = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}?fields=properties.title,sheets.properties.title`, { headers: auth2(t) });
  if (!r.ok) throw new Error(`GOOGLE_SOURCE_META:${r.status}`);
  const meta3 = await r.json();
  const title = String(meta3.properties?.title ?? "");
  if (title !== "D\u1EEE LI\u1EC6U THEO NG\xC0Y") throw new Error(`SOURCE_TITLE_MISMATCH:${title}`);
  const actual = (meta3.sheets ?? []).map((x2) => x2.properties?.title ?? "").filter(Boolean), expected = EXPECTED2.map((x2) => x2.name);
  if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error(`SOURCE_TABS_MISMATCH:${JSON.stringify(actual)}`);
}
__name(validateWorkbook, "validateWorkbook");
async function fetchSheetChunk(db, env, runId, state) {
  const spec = EXPECTED2[state.sheet_index];
  if (!spec) {
    state.phase = "CATALOG";
    state.cursor = 0;
    return state;
  }
  const start = state.next_row, end = start + FETCH_ROWS - 1, t = await googleToken(env), id = env.GOOGLE_SOURCE_SHEET_ID;
  const range = encodeURIComponent(`${q3(spec.name)}!A${start}:AZ${end}`);
  const r = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}/values/${range}?majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE`, { headers: auth2(t) });
  if (!r.ok) throw new Error(`GOOGLE_SOURCE_VALUES:${spec.name}:${r.status}`);
  const payload3 = await r.json(), raw = payload3.values ?? [];
  let dataStart = 0;
  if (start === 1) {
    const header = normRow2(raw[0] ?? [], spec.headers.length);
    if (JSON.stringify(header) !== JSON.stringify(spec.headers)) throw new Error(`SOURCE_HEADERS_MISMATCH:${spec.name}:${JSON.stringify(header)}`);
    dataStart = 1;
  }
  const stmts = [], checks = [];
  let added = 0;
  const dates = new Set(state.business_dates);
  for (let i2 = dataStart; i2 < raw.length; i2++) {
    const row = normRow2(raw[i2] ?? [], spec.headers.length);
    if (!row.some(Boolean)) continue;
    const rowIndex2 = start + i2, checksum2 = await sha256Hex(JSON.stringify(row));
    checks.push(checksum2);
    added++;
    stmts.push(db.prepare("INSERT OR REPLACE INTO source_rows(sheet_name,row_index,row_checksum,row_json,import_run_id) VALUES(?1,?2,?3,?4,?5)").bind(spec.name, rowIndex2, checksum2, JSON.stringify(row), runId));
    if (spec.name === "RA - V\xC0O TRONG CA" || spec.name === "C\xD4NG NH\u1EACT") {
      const d = parseVisibleDate(row[0] ?? "");
      if (d) dates.add(d);
    }
  }
  await runChunks2(db, stmts);
  state.current_sheet_rows += added;
  if (checks.length) state.current_sheet_checksum = await sha256Hex([state.current_sheet_checksum, ...checks].filter(Boolean).join("\n"));
  state.business_dates = [...dates].sort();
  const done = raw.length < FETCH_ROWS;
  if (done) {
    state.sheet_report.push({ name: spec.name, row_count: state.current_sheet_rows, checksum: state.current_sheet_checksum || await sha256Hex("") });
    state.sheet_index++;
    state.next_row = 1;
    state.current_sheet_rows = 0;
    state.current_sheet_checksum = "";
    if (state.sheet_index >= EXPECTED2.length) {
      state.phase = "CATALOG";
      state.cursor = 0;
    }
  } else state.next_row = start + FETCH_ROWS;
  return state;
}
__name(fetchSheetChunk, "fetchSheetChunk");
async function loadTable(db, name) {
  const spec = EXPECTED2.find((x2) => x2.name === name);
  if (!spec) throw new Error(`BOOTSTRAP_SHEET_UNKNOWN:${name}`);
  const got = await db.prepare("SELECT row_index,row_checksum,row_json FROM source_rows WHERE sheet_name=?1 ORDER BY row_index").bind(name).all();
  const stored = got.results ?? [], rows2 = stored.map((x2) => normRow2(JSON.parse(x2.row_json), spec.headers.length));
  return { headers: spec.headers, rows: rows2, objects: rows2.map((r) => obj2(spec.headers, r)), rowChecksums: stored.map((x2) => x2.row_checksum), rowIndexes: stored.map((x2) => x2.row_index) };
}
__name(loadTable, "loadTable");
async function projectCatalog(db) {
  const t = await loadTable(db, "Danh m\u1EE5c"), stmts = [db.prepare("DELETE FROM catalog_values")];
  t.headers.forEach((h, c) => {
    const seen = /* @__PURE__ */ new Set();
    for (let r = 0; r < t.rows.length; r++) {
      const v = t.rows[r]?.[c] ?? "";
      if (!v || seen.has(v)) continue;
      seen.add(v);
      stmts.push(db.prepare("INSERT INTO catalog_values(namespace,ordinal,value,source_checksum) VALUES(?1,?2,?3,?4)").bind(h, seen.size, v, t.rowChecksums[r]));
    }
  });
  await runChunks2(db, stmts);
}
__name(projectCatalog, "projectCatalog");
async function projectStaff(db) {
  const t = await loadTable(db, "DANH S\xC1CH NH\xC2N S\u1EF0"), stmts = [db.prepare("DELETE FROM employees")];
  t.objects.forEach((r, i2) => {
    const mnv = r["M\xE3 nh\xE2n vi\xEAn"] || "";
    if (!mnv) return;
    stmts.push(db.prepare("INSERT INTO employees(mnv,full_name,phone,main_position,supplier,department,site,warehouse,start_date,note,source_row,source_checksum) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12)").bind(mnv, r["H\u1ECD v\xE0 t\xEAn"] || "", r["S\u1ED1 \u0111i\u1EC7n tho\u1EA1i"] || "", r["V\u1ECB tr\xED ch\xEDnh"] || "", r["Nh\xE0 cung c\u1EA5p"] || "", r["B\u1ED9 ph\u1EADn"] || "", r["Site"] || "", r["Kho"] || "", r["Ng\xE0y b\u1EAFt \u0111\u1EA7u l\xE0m vi\u1EC7c"] || "", r["Ghi ch\xFA"] || "", t.rowIndexes[i2], t.rowChecksums[i2]));
  });
  await runChunks2(db, stmts);
}
__name(projectStaff, "projectStaff");
async function projectResources(db) {
  const stmts = [db.prepare("DELETE FROM resources"), db.prepare("DELETE FROM resource_pack_map")];
  const add = /* @__PURE__ */ __name(async (sheet, type, idField) => {
    const t = await loadTable(db, sheet);
    t.objects.forEach((r, i2) => {
      const id = r[idField] || "";
      if (!id) return;
      stmts.push(db.prepare("INSERT INTO resources(resource_type,resource_id,status_label,available,metadata_json,source_row,source_checksum) VALUES(?1,?2,?3,?4,?5,?6,?7)").bind(type, id, r["T\xECnh tr\u1EA1ng"] || "", isAvailableLabel(r["T\xECnh tr\u1EA1ng"]) ? 1 : 0, JSON.stringify(r), t.rowIndexes[i2], t.rowChecksums[i2]));
    });
    return t;
  }, "add");
  await add("DANH S\xC1CH PDA", "PDA", "Seri PDA");
  await add("DANH S\xC1CH USER PICK", "USER_PICK", "User Pick");
  await add("DANH S\xC1CH B\xC0N PACK", "PACK_TABLE", "T\xEAn b\xE0n pack");
  const packs = await add("DANH S\xC1CH USER PACK", "USER_PACK", "User Pack");
  packs.objects.forEach((r, i2) => {
    const table = r["T\xEAn b\xE0n pack"] || "", user = r["User Pack"] || "", label2 = r["User pack"] || "";
    if (!table || !user) return;
    const f = fold(label2), shift = f.startsWith("CA 1-") ? "Ca 1" : f.startsWith("CA 2-") ? "Ca 2" : f.startsWith("HP-") || fold(table) === "HP" ? "Ca HC" : "";
    if (!shift) return;
    stmts.push(db.prepare("INSERT OR REPLACE INTO resource_pack_map(pack_table,shift,user_pack,label,available,source_row,source_checksum) VALUES(?1,?2,?3,?4,?5,?6,?7)").bind(table, shift, user, label2, isAvailableLabel(r["T\xECnh tr\u1EA1ng"]) ? 1 : 0, packs.rowIndexes[i2], packs.rowChecksums[i2]));
  });
  await runChunks2(db, stmts);
}
__name(projectResources, "projectResources");
async function projectAccounts(db) {
  const t = await loadTable(db, "Danh s\xE1ch Admin"), stmts = [db.prepare("DELETE FROM auth_sessions"), db.prepare("DELETE FROM auth_challenges"), db.prepare("DELETE FROM accounts WHERE is_shadow_test=0")];
  for (let i2 = 0; i2 < t.objects.length; i2++) {
    const r = t.objects[i2], login = r["S\u1ED1 User"] || "", verifier = r["Password verifier"] || "";
    if (!login || !verifier) continue;
    const rr = role2(r["V\u1ECB tr\xED"] || "");
    stmts.push(db.prepare("INSERT INTO accounts(login_id,verifier,verifier_hash,role,display_name,position,email,status,source_row,source_checksum,is_shadow_test) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,0)").bind(login, verifier, await sha256Hex(verifier), rr, login, rr.toLowerCase(), r["Mail"] || "", activeStatus2(r["Tr\u1EA1ng th\xE1i t\xE0i kho\u1EA3n"] || r["T\xECnh tr\u1EA1ng"] || ""), t.rowIndexes[i2], t.rowChecksums[i2]));
  }
  await runChunks2(db, stmts);
}
__name(projectAccounts, "projectAccounts");
async function projectDates(db, state) {
  const sorted = [...new Set(state.business_dates)].sort(), stmts = [db.prepare("DELETE FROM business_dates")];
  sorted.forEach((d, i2) => stmts.push(db.prepare("INSERT INTO business_dates(business_date,sequence_no,source) VALUES(?1,?2,'GOOGLE_BOOTSTRAP')").bind(d, i2 + 1)));
  await runChunks2(db, stmts);
}
__name(projectDates, "projectDates");
async function projectAttendanceStep(db, state) {
  if (state.cursor === 0) await db.batch([db.prepare("DELETE FROM resource_leases"), db.prepare("DELETE FROM resource_daily_consumption"), db.prepare("DELETE FROM attendance_sessions")]);
  const got = await db.prepare("SELECT row_index,row_json FROM source_rows WHERE sheet_name='RA - V\xC0O TRONG CA' AND row_index>?1 ORDER BY row_index LIMIT ?2").bind(state.cursor, ATTENDANCE_ROWS).all(), rows2 = got.results ?? [];
  const spec = EXPECTED2.find((x2) => x2.name === "RA - V\xC0O TRONG CA"), groups = /* @__PURE__ */ new Map();
  for (const x2 of rows2) {
    const r = normRow2(JSON.parse(x2.row_json), spec.headers.length), o = obj2(spec.headers, r), d = parseVisibleDate(o["Ng\xE0y"] || ""), m = o["M\xE3 nh\xE2n vi\xEAn"] || "";
    if (!d || !m) continue;
    const sid = `BOOTSTRAP:${d}:${m}`, g = groups.get(sid) ?? [];
    g.push({ row_index: x2.row_index, o });
    groups.set(sid, g);
  }
  const stmts = [];
  for (const [sid, g] of groups) {
    const first = g[0], last = g[g.length - 1], o = last.o, d = parseVisibleDate(o["Ng\xE0y"] || ""), m = o["M\xE3 nh\xE2n vi\xEAn"] || "", action = fold(o["Lo\u1EA1i thao t\xE1c"] || o["App action"] || ""), ended = action.includes("RA") && !action.includes("VAO"), pda = o["Seri PDA"] || "", pick = o["User Pick"] || "", table = o["B\xE0n Pack"] || "", pack = o["User Pack"] || "", updated = visibleToIsoTimestamp(o["Th\u1EDDi gian c\u1EADp nh\u1EADt"] || "");
    stmts.push(db.prepare(`INSERT INTO attendance_sessions(session_id,mnv,business_date,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,enter_at,exit_at,entered_by,exited_by,version,source_last_row,updated_at)
      VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,'GOOGLE_BOOTSTRAP',?13,?14,?15,?16)
      ON CONFLICT(session_id) DO UPDATE SET shift=excluded.shift,work_choice=excluded.work_choice,state=excluded.state,pda_serial=excluded.pda_serial,user_pick=excluded.user_pick,pack_table=excluded.pack_table,user_pack=excluded.user_pack,enter_at=COALESCE(attendance_sessions.enter_at,excluded.enter_at),exit_at=excluded.exit_at,exited_by=excluded.exited_by,version=attendance_sessions.version+excluded.version,source_last_row=excluded.source_last_row,updated_at=excluded.updated_at
      WHERE excluded.source_last_row>attendance_sessions.source_last_row`).bind(sid, m, d, o["Ca"] || "", workChoice(o["V\u1ECB tr\xED trong ca"]), ended ? "ENDED" : "ACTIVE", pda || null, pick || null, table || null, pack || null, visibleToIsoTimestamp(first.o["Th\u1EDDi gian c\u1EADp nh\u1EADt"] || ""), ended ? updated : null, ended ? "GOOGLE_BOOTSTRAP" : null, g.length, last.row_index, updated));
  }
  await runChunks2(db, stmts);
  if (rows2.length) state.cursor = rows2[rows2.length - 1].row_index;
  return { state, done: rows2.length < ATTENDANCE_ROWS };
}
__name(projectAttendanceStep, "projectAttendanceStep");
async function projectLeasesStep(db, state) {
  const got = await db.prepare("SELECT session_id,mnv,business_date,pda_serial,user_pick,pack_table,user_pack FROM attendance_sessions WHERE state='ACTIVE' ORDER BY session_id LIMIT ?1 OFFSET ?2").bind(LEASE_ROWS, state.cursor).all(), rows2 = got.results ?? [], stmts = [];
  for (const x2 of rows2) {
    for (const [type, id] of [["PDA", x2.pda_serial], ["USER_PICK", x2.user_pick], ["PACK_TABLE", x2.pack_table], ["USER_PACK", x2.user_pack]]) {
      if (!id) continue;
      stmts.push(db.prepare("INSERT OR IGNORE INTO resource_leases(resource_type,resource_id,session_id,mnv,business_date,acquired_event_id,acquired_at) VALUES(?1,?2,?3,?4,?5,?6,?7)").bind(type, id, x2.session_id, x2.mnv, x2.business_date, `BOOTSTRAP:${x2.business_date}:${x2.mnv}:${type}`, nowIso()));
    }
  }
  await runChunks2(db, stmts);
  state.cursor += rows2.length;
  return { state, done: rows2.length < LEASE_ROWS };
}
__name(projectLeasesStep, "projectLeasesStep");
async function projectLaborStep(db, state) {
  if (state.cursor === 0) await db.prepare("DELETE FROM labor_sessions").run();
  const got = await db.prepare("SELECT row_index,row_json FROM source_rows WHERE sheet_name='C\xD4NG NH\u1EACT' AND row_index>?1 ORDER BY row_index LIMIT ?2").bind(state.cursor, LABOR_ROWS).all(), rows2 = got.results ?? [], spec = EXPECTED2.find((x2) => x2.name === "C\xD4NG NH\u1EACT"), stmts = [];
  for (const x2 of rows2) {
    const r = obj2(spec.headers, normRow2(JSON.parse(x2.row_json), spec.headers.length)), d = parseVisibleDate(r["Ng\xE0y"] || ""), m = r["M\xE3 nh\xE2n vi\xEAn"] || "";
    if (!d || !m) continue;
    const startId = r["Event ID"] || `BOOTSTRAP-LABOR:${d}:${m}:${x2.row_index}`, finishId = r["Finish Event ID"] || null, status = fold(r["Tr\u1EA1ng th\xE1i"] || ""), stateLabel = status.includes("HOAN") || status.includes("COMPLET") || Boolean(finishId) ? "COMPLETED" : "OPEN";
    stmts.push(db.prepare("INSERT OR REPLACE INTO labor_sessions(labor_id,mnv,business_date,shift,labor_type,time_marker,state,start_at,end_at,note,deduct_staff,start_event_id,finish_event_id,version,source_row,updated_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16)").bind(startId, m, d, r["Ca"] || "", r["Th\xF4ng tin c\xF4ng nh\u1EADt"] || "", r["M\u1ED1c th\u1EDDi gian"] || "", stateLabel, visibleToIsoTimestamp(r["Th\u1EDDi gian b\u1EAFt \u0111\u1EA7u"] || r["Th\u1EDDi gian c\u1EADp nh\u1EADt"] || ""), stateLabel === "COMPLETED" ? visibleToIsoTimestamp(r["Th\u1EDDi gian k\u1EBFt th\xFAc"] || r["Th\u1EDDi gian c\u1EADp nh\u1EADt"] || "") : null, r["Ghi ch\xFA"] || "", fold(r["Kh\u1EA5u tr\u1EEB nh\xE2n s\u1EF1"] || "") === "CO" ? 1 : 0, startId, finishId, stateLabel === "COMPLETED" ? 2 : 1, x2.row_index, visibleToIsoTimestamp(r["Th\u1EDDi gian c\u1EADp nh\u1EADt"] || "")));
  }
  await runChunks2(db, stmts);
  if (rows2.length) state.cursor = rows2[rows2.length - 1].row_index;
  return { state, done: rows2.length < LABOR_ROWS };
}
__name(projectLaborStep, "projectLaborStep");
async function finalize(db, env, runId, state) {
  const counts = {};
  for (const table of ["employees", "catalog_values", "resources", "resource_pack_map", "accounts", "business_dates", "attendance_sessions", "labor_sessions"]) {
    const c = await db.prepare(`SELECT COUNT(*) n FROM ${table}`).first();
    counts[table] = c?.n ?? 0;
  }
  const dates = [...new Set(state.business_dates)].sort(), completed = nowIso(), report = { run_id: runId, source_title: "D\u1EEE LI\u1EC6U THEO NG\xC0Y", source_sheet_id: env.GOOGLE_SOURCE_SHEET_ID, sheets: state.sheet_report, projection_counts: counts, business_date_min: dates[0] ?? null, business_date_max: dates[dates.length - 1] ?? null, business_date_count: dates.length, completed_at: completed, resumable: true };
  state.phase = "COMPLETE";
  await db.prepare("UPDATE bootstrap_runs SET completed_at=?1,status='COMPLETE',manifest_json=?2,report_json=?3 WHERE run_id=?4").bind(completed, JSON.stringify(state), JSON.stringify(report), runId).run();
  return { ok: true, done: true, ...report };
}
__name(finalize, "finalize");
async function bootstrapGoogleStart(db, env) {
  await ensureShadow(db);
  await validateWorkbook(env);
  const at = nowIso(), runId = crypto.randomUUID(), state = initialState();
  await db.batch([
    db.prepare("UPDATE bootstrap_runs SET completed_at=?1,status='FAILED',report_json=?2 WHERE status='RUNNING'").bind(at, JSON.stringify({ error: "SUPERSEDED_BY_RESUMABLE_BOOTSTRAP", at })),
    db.prepare("DELETE FROM source_rows"),
    db.prepare("INSERT INTO bootstrap_runs(run_id,source_title,source_sheet_identity,started_at,status,manifest_json) VALUES(?1,'D\u1EEE LI\u1EC6U THEO NG\xC0Y',?2,?3,'RUNNING',?4)").bind(runId, env.GOOGLE_SOURCE_SHEET_ID, at, JSON.stringify(state))
  ]);
  return { ok: true, done: false, run_id: runId, phase: state.phase, state };
}
__name(bootstrapGoogleStart, "bootstrapGoogleStart");
async function bootstrapGoogleStatus(db, runId) {
  const row = runId ? await db.prepare("SELECT run_id,status,manifest_json,report_json,started_at,completed_at FROM bootstrap_runs WHERE run_id=?1").bind(runId).first() : await db.prepare("SELECT run_id,status,manifest_json,report_json,started_at,completed_at FROM bootstrap_runs ORDER BY started_at DESC LIMIT 1").first();
  if (!row) throw new Error("BOOTSTRAP_RUN_NOT_FOUND");
  const state = parseState(row.manifest_json);
  return { ok: true, done: row.status === "COMPLETE", run_id: row.run_id, status: row.status, phase: state.phase, state, report: row.report_json ? JSON.parse(row.report_json) : null, started_at: row.started_at, completed_at: row.completed_at };
}
__name(bootstrapGoogleStatus, "bootstrapGoogleStatus");
async function bootstrapGoogleStep(db, env, runId) {
  await ensureShadow(db);
  const row = await db.prepare("SELECT status,manifest_json,report_json FROM bootstrap_runs WHERE run_id=?1").bind(runId).first();
  if (!row) throw new Error("BOOTSTRAP_RUN_NOT_FOUND");
  if (row.status === "COMPLETE") return { ok: true, done: true, run_id: runId, report: row.report_json ? JSON.parse(row.report_json) : null };
  if (row.status !== "RUNNING") throw new Error(`BOOTSTRAP_RUN_NOT_RUNNING:${row.status}`);
  let state = parseState(row.manifest_json);
  try {
    if (state.phase === "FETCH") state = await fetchSheetChunk(db, env, runId, state);
    else if (state.phase === "CATALOG") {
      await projectCatalog(db);
      state.phase = "STAFF";
      state.cursor = 0;
    } else if (state.phase === "STAFF") {
      await projectStaff(db);
      state.phase = "RESOURCES";
      state.cursor = 0;
    } else if (state.phase === "RESOURCES") {
      await projectResources(db);
      state.phase = "ACCOUNTS";
      state.cursor = 0;
    } else if (state.phase === "ACCOUNTS") {
      await projectAccounts(db);
      state.phase = "DATES";
      state.cursor = 0;
    } else if (state.phase === "DATES") {
      await projectDates(db, state);
      state.phase = "ATTENDANCE";
      state.cursor = 0;
    } else if (state.phase === "ATTENDANCE") {
      const x2 = await projectAttendanceStep(db, state);
      state = x2.state;
      if (x2.done) {
        state.phase = "LEASES";
        state.cursor = 0;
      }
    } else if (state.phase === "LEASES") {
      const x2 = await projectLeasesStep(db, state);
      state = x2.state;
      if (x2.done) {
        state.phase = "LABOR";
        state.cursor = 0;
      }
    } else if (state.phase === "LABOR") {
      const x2 = await projectLaborStep(db, state);
      state = x2.state;
      if (x2.done) {
        state.phase = "FINALIZE";
        state.cursor = 0;
      }
    } else if (state.phase === "FINALIZE") return await finalize(db, env, runId, state);
    else if (state.phase === "COMPLETE") return bootstrapGoogleStatus(db, runId);
    await saveState(db, runId, state);
    return { ok: true, done: false, run_id: runId, phase: state.phase, state };
  } catch (e) {
    await db.prepare("UPDATE bootstrap_runs SET report_json=?1 WHERE run_id=?2 AND status='RUNNING'").bind(JSON.stringify({ last_error: String(e), at: nowIso(), phase: state.phase }), runId).run().catch(() => void 0);
    throw e;
  }
}
__name(bootstrapGoogleStep, "bootstrapGoogleStep");

// src/bootstrap_resources.ts
async function rows(db, sheet) {
  const got = await db.prepare("SELECT row_index,row_checksum,row_json FROM source_rows WHERE sheet_name=?1 ORDER BY row_index").bind(sheet).all();
  return got.results ?? [];
}
__name(rows, "rows");
function arr(x2) {
  const raw = JSON.parse(x2.row_json);
  return raw.map((v) => String(v ?? "").trim());
}
__name(arr, "arr");
function shiftFrom(label2, table) {
  const f = fold(label2), t = fold(table);
  if (f.startsWith("CA 1-")) return "Ca 1";
  if (f.startsWith("CA 2-")) return "Ca 2";
  if (f.startsWith("HP-") || t === "HP") return "Ca HC";
  return "";
}
__name(shiftFrom, "shiftFrom");
async function chunks2(db, stmts, size = 50) {
  for (let i2 = 0; i2 < stmts.length; i2 += size) await db.batch(stmts.slice(i2, i2 + size));
}
__name(chunks2, "chunks");
function resourceStmt(db, c) {
  return db.prepare("INSERT INTO resources(resource_type,resource_id,status_label,available,metadata_json,source_row,source_checksum) VALUES(?1,?2,?3,?4,?5,?6,?7)").bind(c.resource_type, c.resource_id, c.status_label, c.available, c.metadata_json, c.source_row, c.source_checksum);
}
__name(resourceStmt, "resourceStmt");
async function bootstrapResourceProjectionStep(db, runId) {
  const run = await db.prepare("SELECT status,manifest_json FROM bootstrap_runs WHERE run_id=?1").bind(runId).first();
  if (!run) throw new Error("BOOTSTRAP_RUN_NOT_FOUND");
  if (run.status !== "RUNNING") throw new Error(`BOOTSTRAP_RUN_NOT_RUNNING:${run.status}`);
  const state = JSON.parse(run.manifest_json);
  if (state.phase !== "RESOURCES") throw new Error(`BOOTSTRAP_RESOURCE_PHASE_INVALID:${String(state.phase)}`);
  const warnings = Array.isArray(state.warnings) ? state.warnings : [];
  const pdaRows = await rows(db, "DANH S\xC1CH PDA");
  const pickRows = await rows(db, "DANH S\xC1CH USER PICK");
  const tableRows = await rows(db, "DANH S\xC1CH B\xC0N PACK");
  const packRows = await rows(db, "DANH S\xC1CH USER PACK");
  const validTables = /* @__PURE__ */ new Set();
  for (const x2 of tableRows) {
    const r = arr(x2), id = r[0] || "";
    if (id) validTables.add(id);
  }
  const selected = /* @__PURE__ */ new Map();
  const put = /* @__PURE__ */ __name((c) => {
    if (!c.resource_id) return;
    const key = `${c.resource_type}\0${c.resource_id}`, old = selected.get(key);
    if (!old) {
      selected.set(key, c);
      return;
    }
    warnings.push({ code: "DUPLICATE_RESOURCE_ID", resource_type: c.resource_type, resource_id: c.resource_id, kept_source_row: old.source_row, candidate_source_row: c.source_row });
    if (!old.valid_reference && c.valid_reference) {
      selected.set(key, c);
      return;
    }
    if (old.valid_reference === c.valid_reference && c.source_row < old.source_row) selected.set(key, c);
  }, "put");
  for (const x2 of pdaRows) {
    const r = arr(x2);
    put({ resource_type: "PDA", resource_id: r[0] || "", status_label: r[2] || "", available: isAvailableLabel(r[2] || "") ? 1 : 0, metadata_json: JSON.stringify({ "Seri PDA": r[0] || "", "5 s\u1ED1 cu\u1ED1i Seri": r[1] || "", "T\xECnh tr\u1EA1ng": r[2] || "", "Ghi ch\xFA": r[3] || "" }), source_row: x2.row_index, source_checksum: x2.row_checksum, valid_reference: true });
  }
  for (const x2 of pickRows) {
    const r = arr(x2);
    put({ resource_type: "USER_PICK", resource_id: r[1] || "", status_label: r[2] || "", available: isAvailableLabel(r[2] || "") ? 1 : 0, metadata_json: JSON.stringify({ "S\u1ED1 User": r[0] || "", "User Pick": r[1] || "", "T\xECnh tr\u1EA1ng": r[2] || "", "Ghi ch\xFA": r[3] || "" }), source_row: x2.row_index, source_checksum: x2.row_checksum, valid_reference: true });
  }
  for (const x2 of tableRows) {
    const r = arr(x2);
    put({ resource_type: "PACK_TABLE", resource_id: r[0] || "", status_label: r[1] || "", available: isAvailableLabel(r[1] || "") ? 1 : 0, metadata_json: JSON.stringify({ "T\xEAn b\xE0n pack": r[0] || "", "T\xECnh tr\u1EA1ng": r[1] || "" }), source_row: x2.row_index, source_checksum: x2.row_checksum, valid_reference: true });
  }
  const mappings = [];
  const mapByShiftUser = /* @__PURE__ */ new Map();
  for (const x2 of packRows) {
    const r = arr(x2), table = r[0] || "", label2 = r[1] || "", user = r[2] || "", status = r[3] || "", validTable = validTables.has(table), shift = shiftFrom(label2, table);
    if (!user) continue;
    put({ resource_type: "USER_PACK", resource_id: user, status_label: status, available: isAvailableLabel(status) ? 1 : 0, metadata_json: JSON.stringify({ "T\xEAn b\xE0n pack": table, "User pack": label2, "User Pack": user, "T\xECnh tr\u1EA1ng": status }), source_row: x2.row_index, source_checksum: x2.row_checksum, valid_reference: validTable });
    if (!validTable) {
      warnings.push({ code: "PACK_TABLE_REFERENCE_MISSING", pack_table: table, user_pack: user, label: label2, source_row: x2.row_index });
      continue;
    }
    if (!shift) {
      warnings.push({ code: "PACK_SHIFT_UNRECOGNIZED", pack_table: table, user_pack: user, label: label2, source_row: x2.row_index });
      continue;
    }
    const m = { pack_table: table, shift, user_pack: user, label: label2, available: isAvailableLabel(status) ? 1 : 0, source_row: x2.row_index, source_checksum: x2.row_checksum };
    const uniqueKey = `${shift}\0${user}`, old = mapByShiftUser.get(uniqueKey);
    if (old) {
      warnings.push({ code: "DUPLICATE_PACK_USER_SHIFT", shift, user_pack: user, kept_pack_table: old.pack_table, kept_source_row: old.source_row, candidate_pack_table: table, candidate_source_row: x2.row_index });
      continue;
    }
    mapByShiftUser.set(uniqueKey, m);
    mappings.push(m);
  }
  const stmts = [db.prepare("DELETE FROM resource_pack_map"), db.prepare("DELETE FROM resources")];
  for (const c of selected.values()) stmts.push(resourceStmt(db, c));
  for (const m of mappings) stmts.push(db.prepare("INSERT INTO resource_pack_map(pack_table,shift,user_pack,label,available,source_row,source_checksum) VALUES(?1,?2,?3,?4,?5,?6,?7)").bind(m.pack_table, m.shift, m.user_pack, m.label, m.available, m.source_row, m.source_checksum));
  await chunks2(db, stmts);
  state.phase = "ACCOUNTS";
  state.warnings = warnings;
  await db.prepare("UPDATE bootstrap_runs SET manifest_json=?1 WHERE run_id=?2 AND status='RUNNING'").bind(JSON.stringify(state), runId).run();
  return { ok: true, done: false, run_id: runId, phase: "ACCOUNTS", state, resource_count: selected.size, pack_mapping_count: mappings.length, warnings };
}
__name(bootstrapResourceProjectionStep, "bootstrapResourceProjectionStep");

// src/compat.ts
var REPORT_ROWS = ["Tr\u01B0\u1EDFng nh\xF3m", "Chuy\xEAn vi\xEAn", "T\u1ED5 tr\u01B0\u1EDFng", "\u0110i\u1EC1u ph\u1ED1i khu pack", "\u0110i\u1EC1u ph\u1ED1i khu ch\u1EDD xu\u1EA5t", "K\xE9o h\xE0ng", "5S", "Picker", "Packer", "Ph\xFAc Long"];
var SUPPLIER_ORDER = ["IH", "NLV", "VW", "MP", "MGL", "HGP", "HAD"];
function supplierCode(v) {
  const f = fold(v).replace(/[^A-Z0-9]+/g, " ");
  for (const c of SUPPLIER_ORDER) if (new RegExp(`(^| )${c}( |$)`).test(f)) return c;
  return SUPPLIER_ORDER.includes(f) ? f : "";
}
__name(supplierCode, "supplierCode");
function reportPosition(s) {
  const e = s.employee_snapshot, p = fold(e.main_position), d = fold(e.department), work = String(s.work_choice || "");
  if (p === "TRUONG NHOM") return "Tr\u01B0\u1EDFng nh\xF3m";
  if (p === "CHUYEN VIEN") return "Chuy\xEAn vi\xEAn";
  if (p === "TO TRUONG") return "T\u1ED5 tr\u01B0\u1EDFng";
  if (p.includes("DIEU PHOI")) {
    if (p.includes("PACK") || d.includes("PICK PACK")) return "\u0110i\u1EC1u ph\u1ED1i khu pack";
    if (p.includes("CHO XUAT") || d.includes("GIAO VAN") || d.includes("OUTBOUND")) return "\u0110i\u1EC1u ph\u1ED1i khu ch\u1EDD xu\u1EA5t";
    return "";
  }
  if (p === "KEO HANG") return "K\xE9o h\xE0ng";
  if (p === "5S") return "5S";
  if (p.includes("PHUC LONG")) return "Ph\xFAc Long";
  if (work === "PICK" || p === "PICK" || p === "PICKER") return "Picker";
  if (work === "PACK" || p === "PACK" || p === "PACKER") return "Packer";
  return "";
}
__name(reportPosition, "reportPosition");
function deductAllowed(mainPosition, laborType) {
  const a = fold(mainPosition), b = fold(laborType), fixed = /* @__PURE__ */ __name((v) => v.includes("KEO HANG") || v.includes("TO TRUONG"), "fixed");
  return !fixed(a) && !fixed(b);
}
__name(deductAllowed, "deductAllowed");
function tenureDays(startDate, businessDate2) {
  if (!startDate) return 99999;
  let iso2 = startDate;
  const m = startDate.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (m && m[1] && m[2] && m[3]) iso2 = `${m[3]}-${m[2]}-${m[1]}`;
  const a = Date.parse(`${iso2}T00:00:00+07:00`), b = Date.parse(`${businessDate2}T00:00:00+07:00`);
  return Number.isFinite(a) && Number.isFinite(b) ? Math.max(0, Math.floor((b - a) / 864e5)) : 99999;
}
__name(tenureDays, "tenureDays");
function matrix(sessions, columns) {
  const data = {};
  for (const r of REPORT_ROWS) {
    data[r] = {};
    for (const c of columns) data[r][c] = 0;
  }
  for (const s of sessions) {
    const pos = reportPosition(s), sup = supplierCode(s.employee_snapshot.supplier);
    if (pos && sup && data[pos] && columns.includes(sup)) data[pos][sup] = (data[pos][sup] ?? 0) + 1;
  }
  const rows2 = REPORT_ROWS.map((position) => {
    const counts = {};
    for (const c of columns) counts[c] = data[position]?.[c] ?? 0;
    return { position, counts, total: columns.reduce((n, c) => n + (counts[c] ?? 0), 0) };
  });
  const totals = {};
  for (const c of columns) totals[c] = rows2.reduce((n, r) => n + (r.counts[c] ?? 0), 0);
  return { columns, rows: rows2, totals, total: columns.reduce((n, c) => n + (totals[c] ?? 0), 0) };
}
__name(matrix, "matrix");
function tenure(sessions, columns, work, deducted, date) {
  const data = { "Nh\xE2n s\u1EF1 m\u1EDBi": {}, "Nh\xE2n s\u1EF1 c\u0169": {} };
  for (const label2 of Object.keys(data)) for (const c of columns) data[label2][c] = 0;
  for (const s of sessions) {
    if (s.work_choice !== work || deducted.has(s.mnv)) continue;
    const sup = supplierCode(s.employee_snapshot.supplier);
    if (!sup || !columns.includes(sup)) continue;
    const label2 = tenureDays(s.employee_snapshot.start_date, date) <= 30 ? "Nh\xE2n s\u1EF1 m\u1EDBi" : "Nh\xE2n s\u1EF1 c\u0169";
    data[label2][sup] = (data[label2][sup] ?? 0) + 1;
  }
  const rows2 = ["Nh\xE2n s\u1EF1 m\u1EDBi", "Nh\xE2n s\u1EF1 c\u0169"].map((label2) => {
    const counts = {};
    for (const c of columns) counts[c] = data[label2]?.[c] ?? 0;
    return { label: label2, counts, total: columns.reduce((n, c) => n + (counts[c] ?? 0), 0) };
  });
  const totals = {};
  for (const c of columns) totals[c] = rows2.reduce((n, r) => n + (r.counts[c] ?? 0), 0);
  return { columns, rows: rows2, totals, total: rows2.reduce((n, r) => n + r.total, 0) };
}
__name(tenure, "tenure");
function support(sessions, labor, allowed2, columns) {
  const byMnv = new Map(sessions.map((s) => [s.mnv, s])), deducted = /* @__PURE__ */ new Set(), rowsByType = {}, seen = /* @__PURE__ */ new Set();
  for (const r of labor) {
    if (!allowed2.includes(r.shift) || !r.deduct_staff) continue;
    const s = byMnv.get(r.mnv);
    if (!s) continue;
    const type = r.labor_type || "Kh\xE1c";
    if (!deductAllowed(s.employee_snapshot.main_position, type)) continue;
    const k = `${type}|${r.mnv}`;
    if (seen.has(k)) continue;
    seen.add(k);
    deducted.add(r.mnv);
    const sup = supplierCode(s.employee_snapshot.supplier);
    if (!sup || !columns.includes(sup)) continue;
    if (!rowsByType[type]) {
      const counts = {};
      for (const c of columns) counts[c] = 0;
      rowsByType[type] = { label: type, counts, total: 0 };
    }
    rowsByType[type].counts[sup] = (rowsByType[type].counts[sup] ?? 0) + 1;
    rowsByType[type].total++;
  }
  const rows2 = Object.keys(rowsByType).sort().map((k) => rowsByType[k]);
  const totals = {};
  for (const c of columns) totals[c] = rows2.reduce((n, r) => n + (r.counts[c] ?? 0), 0);
  return { deducted, matrix: { columns, rows: rows2, totals, total: rows2.reduce((n, r) => n + r.total, 0), unique_staff: deducted.size } };
}
__name(support, "support");
function period(sessions, labor, allowed2, label2, date) {
  const items = sessions.filter((s) => allowed2.includes(s.shift)), seen = /* @__PURE__ */ new Set();
  for (const s of items) {
    const c = supplierCode(s.employee_snapshot.supplier);
    if (c) seen.add(c);
  }
  const columns = SUPPLIER_ORDER.filter((c) => seen.has(c));
  const sp = support(items, labor, allowed2, columns), picker = tenure(items, columns, "PICK", sp.deducted, date), packer = tenure(items, columns, "PACK", sp.deducted, date);
  const one = /* @__PURE__ */ __name((x2) => {
    const n = x2.rows[0]?.total ?? 0, o = x2.rows[1]?.total ?? 0;
    return { new: n, old: o, total: n + o };
  }, "one");
  return { label: label2, manpower: matrix(items, columns), picker_tenure: picker, packer_tenure: packer, support: sp.matrix, remaining: { picker: one(picker), packer: one(packer) }, session_total: items.length };
}
__name(period, "period");
function history(events) {
  const groups = {};
  for (const e of events) {
    let g = groups[e.mnv];
    if (!g) g = groups[e.mnv] = { mnv: e.mnv, full_name: e.full_name || "", shift: e.shift || "", state: "ACTIVE", event_count: 0, last_time: "", last_at_iso: "", last_actor: "", last_label: "" };
    if (e.full_name) g.full_name = e.full_name;
    if (e.shift) g.shift = e.shift;
    g.event_count++;
    if (e.event_type === "EXIT" || e.event_type === "ATTENDANCE_EXIT") g.state = "ENDED";
    g.last_time = e.at || g.last_time;
    g.last_at_iso = e.at_iso || g.last_at_iso;
    g.last_actor = e.actor || g.last_actor;
    g.last_label = e.label || g.last_label;
  }
  const items = Object.values(groups).sort((a, b) => (Date.parse(b.last_at_iso) || 0) - (Date.parse(a.last_at_iso) || 0));
  return { total: items.length, active_count: items.filter((x2) => x2.state === "ACTIVE").length, ended_count: items.filter((x2) => x2.state === "ENDED").length, items };
}
__name(history, "history");
function labelFor(type) {
  return type === "ATTENDANCE_ENTER" ? "V\xE0o ca" : type === "ATTENDANCE_EXIT" ? "Ra ca" : type === "RESOURCE_CHANGE" ? "\u0110\u1ED5i t\xE0i nguy\xEAn" : type === "LABOR_START" ? "B\u1EAFt \u0111\u1EA7u c\xF4ng nh\u1EADt" : type === "LABOR_FINISH" ? "K\u1EBFt th\xFAc c\xF4ng nh\u1EADt" : type === "MASTER_STAFF_UPSERT" ? "C\u1EADp nh\u1EADt nh\xE2n s\u1EF1" : type === "MASTER_STAFF_DELETE" ? "X\xF3a nh\xE2n s\u1EF1" : type === "ACCOUNT_UPSERT" ? "T\u1EA1o / s\u1EEDa t\xE0i kho\u1EA3n" : type === "ACCOUNT_STATUS" ? "\u0110\u1ED5i tr\u1EA1ng th\xE1i t\xE0i kho\u1EA3n" : type === "ACCOUNT_EMAIL" ? "\u0110\u1ED5i email t\xE0i kho\u1EA3n" : type === "ACCOUNT_PASSWORD" ? "\u0110\u1ED5i m\u1EADt kh\u1EA9u" : type === "MASTER_STAFF_IMPORT" ? "Import nh\xE2n s\u1EF1" : type === "ACCOUNT_LOGIN" ? "\u0110\u0103ng nh\u1EADp" : type === "ACCOUNT_LOGOUT" ? "\u0110\u0103ng xu\u1EA5t" : type === "SETTINGS_CHANGE" ? "\u0110\u1ED5i c\xE0i \u0111\u1EB7t" : type === "FALLBACK_RECONCILED_DUPLICATE" ? "\u0110\u1ED1i so\xE1t d\u1EEF li\u1EC7u d\u1EF1 ph\xF2ng" : type;
}
__name(labelFor, "labelFor");
function employeeFromJoined(s) {
  return { mnv: s.mnv, full_name: s.emp_full_name ?? "", phone: s.emp_phone ?? "", main_position: s.emp_main_position ?? "", supplier: s.emp_supplier ?? "", department: s.emp_department ?? "", site: s.emp_site ?? "", warehouse: s.emp_warehouse ?? "", start_date: s.emp_start_date ?? "", note: s.emp_note ?? "" };
}
__name(employeeFromJoined, "employeeFromJoined");
function inParams(count) {
  return Array.from({ length: count }, (_, i2) => `?${i2 + 1}`).join(",");
}
__name(inParams, "inParams");
async function revisions(db, limit = 45) {
  const cap = Math.max(1, Math.min(45, limit));
  const q4 = `WITH recent AS (SELECT business_date,sequence_no FROM business_dates ORDER BY sequence_no DESC LIMIT ?1)
    SELECT recent.business_date,recent.sequence_no,MAX(COALESCE(events.authority_seq,0)) AS max_seq
    FROM recent LEFT JOIN events ON events.business_date=recent.business_date
    GROUP BY recent.business_date,recent.sequence_no ORDER BY recent.sequence_no DESC`;
  const res = await db.prepare(q4).bind(cap).all();
  const rows2 = (res.results ?? []).map((r) => ({ business_date: r.business_date, sequence_no: r.sequence_no }));
  const out = {};
  for (const r of res.results ?? []) out[r.business_date] = Math.max(1, Number(r.max_seq ?? 0));
  return { rows: rows2, out, floor: rows2.length ? rows2[rows2.length - 1].business_date : "" };
}
__name(revisions, "revisions");
async function revisionForDate(db, date) {
  const row = await db.prepare(`SELECT b.business_date,MAX(COALESCE(e.authority_seq,0)) AS max_seq FROM business_dates b LEFT JOIN events e ON e.business_date=b.business_date WHERE b.business_date=?1 GROUP BY b.business_date`).bind(date).first();
  return row ? Math.max(1, Number(row.max_seq ?? 0)) : null;
}
__name(revisionForDate, "revisionForDate");
async function loadDaysBulk(db, wanted, rev2) {
  if (!wanted.length) return [];
  const marks = inParams(wanted.length);
  const sessionSql = `SELECT s.session_id,s.mnv,s.business_date,s.shift,s.work_choice,s.state,s.pda_serial,s.user_pick,s.pack_table,s.user_pack,s.enter_at,s.exit_at,s.entered_by,s.exited_by,s.version,
    e.full_name AS emp_full_name,e.phone AS emp_phone,e.main_position AS emp_main_position,e.supplier AS emp_supplier,e.department AS emp_department,e.site AS emp_site,e.warehouse AS emp_warehouse,e.start_date AS emp_start_date,e.note AS emp_note
    FROM attendance_sessions s LEFT JOIN employees e ON e.mnv=s.mnv WHERE s.business_date IN (${marks}) ORDER BY s.business_date,s.mnv`;
  const laborSql = `SELECT labor_id,mnv,business_date,shift,labor_type,time_marker,state,start_at,end_at,note,deduct_staff,start_event_id,finish_event_id,version FROM labor_sessions WHERE business_date IN (${marks}) ORDER BY business_date,start_at`;
  const eventSql = `SELECT event_id,business_date,event_type,actor_id,committed_at,authority_seq,payload_json FROM events WHERE business_date IN (${marks}) ORDER BY business_date,authority_seq`;
  const [sessionsRaw, laborRaw, eventRaw] = await Promise.all([
    db.prepare(sessionSql).bind(...wanted).all(),
    db.prepare(laborSql).bind(...wanted).all(),
    db.prepare(eventSql).bind(...wanted).all()
  ]);
  const sessionsByDate = /* @__PURE__ */ new Map(), sessionByKey = /* @__PURE__ */ new Map(), laborByDate = /* @__PURE__ */ new Map(), eventsByDate = /* @__PURE__ */ new Map(), staff = /* @__PURE__ */ new Map();
  for (const s of sessionsRaw.results ?? []) {
    const emp = employeeFromJoined(s), key = `${s.business_date}|${s.mnv}`;
    staff.set(key, emp);
    const row = { id: s.session_id, business_date: s.business_date, mnv: s.mnv, employee_snapshot: emp, shift: s.shift, work_choice: s.work_choice, pda_serial: s.pda_serial, user_pick: s.user_pick, pack_table: s.pack_table, user_pack: s.user_pack, state: s.state, enter_at: s.enter_at, exit_at: s.exit_at, entered_by: s.entered_by, exited_by: s.exited_by, version: s.version };
    sessionByKey.set(key, row);
    const list = sessionsByDate.get(s.business_date) ?? [];
    list.push(row);
    sessionsByDate.set(s.business_date, list);
  }
  for (const l of laborRaw.results ?? []) {
    const list = laborByDate.get(l.business_date) ?? [];
    list.push(l);
    laborByDate.set(l.business_date, list);
  }
  for (const e of eventRaw.results ?? []) {
    let p = {};
    try {
      p = JSON.parse(e.payload_json);
    } catch {
    }
    const mnv = String(p.mnv ?? ""), key = `${e.business_date}|${mnv}`, session = sessionByKey.get(key), emp = staff.get(key);
    const item = { event_id: e.event_id, mnv, full_name: emp?.full_name ?? String(p.target_label ?? ""), shift: String(session?.shift ?? p.shift ?? ""), event_type: e.event_type, label: labelFor(e.event_type), at: e.committed_at, at_iso: e.committed_at, actor: e.actor_id, detail: String(p.note ?? p.labor_type ?? p.detail ?? ""), authority_seq: e.authority_seq };
    const list = eventsByDate.get(e.business_date) ?? [];
    list.push(item);
    eventsByDate.set(e.business_date, list);
  }
  return wanted.map((date) => {
    const sessions = sessionsByDate.get(date) ?? [], labor = laborByDate.get(date) ?? [], events = eventsByDate.get(date) ?? [];
    const report = { ok: true, business_date: date, reports: { ca1_hc: period(sessions, labor, ["Ca 1", "Ca HC"], "Ca 1 + Ca HC", date), ca2: period(sessions, labor, ["Ca 2"], "Ca 2", date), all: period(sessions, labor, ["Ca 1", "Ca HC", "Ca 2"], "C\u1EA3 ng\xE0y", date) } };
    return { business_date: date, day_revision: rev2[date] ?? 1, snapshot_engine: "S15_LOCAL_FIRST_45D_SERVICE", sessions, labor, events, history: history(events), report };
  });
}
__name(loadDaysBulk, "loadDaysBulk");
async function compatDay(db, date) {
  const revision = date ? await revisionForDate(db, date) : null;
  if (revision === null) throw new CoreError("DATE_OUTSIDE_RETENTION", "VALIDATION", 400);
  const days = await loadDaysBulk(db, [date], { [date]: revision });
  return days[0] ?? { business_date: date, day_revision: revision, snapshot_engine: "S15_LOCAL_FIRST_45D_SERVICE", sessions: [], labor: [], events: [], history: history([]), report: { ok: true, business_date: date, reports: {} } };
}
__name(compatDay, "compatDay");
async function compatBootstrap(db, dates) {
  const rev2 = await revisions(db), wanted = Array.isArray(dates) ? dates.map(String).filter((d) => d in rev2.out).slice(0, 45) : rev2.rows.map((x2) => x2.business_date), days = await loadDaysBulk(db, wanted, rev2.out), a = await currentAuthority(db);
  return { ok: true, sync_engine: "S15_LOCAL_FIRST_45D_SERVICE", retention_floor: rev2.floor, retention_epoch: a.authority_epoch, days };
}
__name(compatBootstrap, "compatBootstrap");

// src/dr.ts
var HEADERS = {
  "Danh m\u1EE5c": ["DANH S\xC1CH NH\xC2N S\u1EF0_V\u1ECB tr\xED ch\xEDnh", "DANH S\xC1CH NH\xC2N S\u1EF0_Nh\xE0 cung c\u1EA5p", "DANH S\xC1CH NH\xC2N S\u1EF0_B\u1ED9 ph\u1EADn", "DANH S\xC1CH NH\xC2N S\u1EF0_Site", "DANH S\xC1CH NH\xC2N S\u1EF0_Kho", "DANH S\xC1CH PDA_T\xECnh tr\u1EA1ng", "DANH S\xC1CH USER PICK_T\xECnh tr\u1EA1ng", "DANH S\xC1CH B\xC0N PACK_T\xECnh tr\u1EA1ng", "DANH S\xC1CH USER PACK_T\xECnh tr\u1EA1ng", "RA - V\xC0O TRONG CA_Lo\u1EA1i thao t\xE1c", "V\xC0O - RA TRONG CA_Ca", "C\xD4NG NH\u1EACT_Th\xF4ng tin c\xF4ng nh\u1EADt", "C\xD4NG NH\u1EACT_M\u1ED1c th\u1EDDi gian", "C\xD4NG NH\u1EACT_Tr\u1EA1ng th\xE1i"],
  "L\u1ECACH S\u1EEC NGHI\u1EC6P V\u1EE4": ["Ng\xE0y", "Session ID", "M\xE3 nh\xE2n vi\xEAn", "H\u1ECD t\xEAn", "Ca", "Lo\u1EA1i s\u1EF1 ki\u1EC7n", "Nh\xE3n s\u1EF1 ki\u1EC7n", "Th\u1EDDi gian", "Ng\u01B0\u1EDDi x\u1EED l\xFD", "Chi ti\u1EBFt", "Event ID", "Ph\u1EA1m vi", "App Revision"],
  "DANH S\xC1CH PDA": ["Seri PDA", "5 s\u1ED1 cu\u1ED1i Seri", "T\xECnh tr\u1EA1ng", "Ghi ch\xFA"],
  "DANH S\xC1CH USER PICK": ["S\u1ED1 User", "User Pick", "T\xECnh tr\u1EA1ng", "Ghi ch\xFA"],
  "DANH S\xC1CH B\xC0N PACK": ["T\xEAn b\xE0n pack", "T\xECnh tr\u1EA1ng"],
  "DANH S\xC1CH USER PACK": ["T\xEAn b\xE0n pack", "User pack", "User Pack", "T\xECnh tr\u1EA1ng"],
  "DANH S\xC1CH NH\xC2N S\u1EF0": ["M\xE3 nh\xE2n vi\xEAn", "H\u1ECD v\xE0 t\xEAn", "S\u1ED1 \u0111i\u1EC7n tho\u1EA1i", "V\u1ECB tr\xED ch\xEDnh", "Nh\xE0 cung c\u1EA5p", "B\u1ED9 ph\u1EADn", "Site", "Kho", "Ng\xE0y b\u1EAFt \u0111\u1EA7u l\xE0m vi\u1EC7c", "Ghi ch\xFA", "Ng\u01B0\u1EDDi c\u1EADp nh\u1EADt", "Th\u1EDDi gian c\u1EADp nh\u1EADt"],
  "RA - V\xC0O TRONG CA": ["Ng\xE0y", "Ca", "M\xE3 nh\xE2n vi\xEAn", "H\u1ECD v\xE0 t\xEAn", "S\u1ED1 \u0111i\u1EC7n tho\u1EA1i", "Nh\xE0 cung c\u1EA5p", "B\u1ED9 ph\u1EADn", "Site", "Kho", "V\u1ECB tr\xED ch\xEDnh", "V\u1ECB tr\xED trong ca", "Seri PDA", "User Pick", "B\xE0n Pack", "User Pack", "Lo\u1EA1i thao t\xE1c", "Ghi ch\xFA", "Ng\u01B0\u1EDDi c\u1EADp nh\u1EADt", "Th\u1EDDi gian c\u1EADp nh\u1EADt", "Event ID", "App action", "App revision"],
  "C\xD4NG NH\u1EACT": ["Ng\xE0y", "Ca", "M\xE3 nh\xE2n vi\xEAn", "H\u1ECD v\xE0 t\xEAn", "S\u1ED1 \u0111i\u1EC7n tho\u1EA1i", "Nh\xE0 cung c\u1EA5p", "B\u1ED9 ph\u1EADn", "Site", "Kho", "V\u1ECB tr\xED ch\xEDnh", "V\u1ECB tr\xED trong ca", "Th\xF4ng tin c\xF4ng nh\u1EADt", "Th\u1EDDi gian b\u1EAFt \u0111\u1EA7u", "Th\u1EDDi gian k\u1EBFt th\xFAc", "M\u1ED1c th\u1EDDi gian", "Tr\u1EA1ng th\xE1i", "Ghi ch\xFA", "Ng\u01B0\u1EDDi c\u1EADp nh\u1EADt", "Th\u1EDDi gian c\u1EADp nh\u1EADt", "Event ID", "Finish Event ID", "App revision", "Kh\u1EA5u tr\u1EEB nh\xE2n s\u1EF1"],
  "Danh s\xE1ch Admin": ["S\u1ED1 User", "Password verifier", "T\xECnh tr\u1EA1ng", "Ghi ch\xFA", "V\u1ECB tr\xED", "Mail", "Logic quy\u1EC1n c\u01A1 b\u1EA3n", "", "Tr\u1EA1ng th\xE1i t\xE0i kho\u1EA3n", "Ng\u01B0\u1EDDi c\u1EADp nh\u1EADt", "Th\u1EDDi gian c\u1EADp nh\u1EADt"]
};
function visibleDate2(iso2) {
  const m = iso2.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return m && m[1] && m[2] && m[3] ? `${m[3]}/${m[2]}/${m[1]}` : iso2;
}
__name(visibleDate2, "visibleDate");
function visibleTime(iso2) {
  if (!iso2) return "";
  const d = new Date(iso2);
  if (Number.isNaN(d.getTime())) return iso2;
  return new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Bangkok", day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(d).replace(",", "");
}
__name(visibleTime, "visibleTime");
function a12(name, range) {
  return `'${name.replace(/'/g, "''")}'!${range}`;
}
__name(a12, "a1");
async function token2(env) {
  const body = new URLSearchParams({ client_id: env.GOOGLE_OAUTH_CLIENT_ID, client_secret: env.GOOGLE_OAUTH_CLIENT_SECRET, refresh_token: env.GOOGLE_OAUTH_REFRESH_TOKEN, grant_type: "refresh_token" });
  const r = await fetch("https://oauth2.googleapis.com/token", { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" }, body });
  const j = await r.json();
  if (!r.ok || !j.access_token) throw new Error(`GOOGLE_OAUTH:${j.error ?? r.status}`);
  return j.access_token;
}
__name(token2, "token");
function auth3(t, extra = {}) {
  return { authorization: `Bearer ${t}`, ...extra };
}
__name(auth3, "auth");
async function writeTable(env, t, name, rows2) {
  const id = env.GOOGLE_STAGING_SHEET_ID;
  const clear = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}/values/${encodeURIComponent(a12(name, "A:AZ"))}:clear`, { method: "POST", headers: auth3(t, { "content-type": "application/json" }), body: "{}" });
  if (!clear.ok) throw new Error(`DR_CLEAR:${name}:${clear.status}`);
  const all = [HEADERS[name], ...rows2];
  for (let i2 = 0; i2 < all.length; i2 += 500) {
    const chunk = all.slice(i2, i2 + 500), start = i2 + 1, range = a12(name, `A${start}`);
    const r = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}/values/${encodeURIComponent(range)}?valueInputOption=RAW`, { method: "PUT", headers: auth3(t, { "content-type": "application/json" }), body: JSON.stringify({ range, majorDimension: "ROWS", values: chunk }) });
    if (!r.ok) throw new Error(`DR_WRITE:${name}:${start}:${r.status}`);
  }
}
__name(writeTable, "writeTable");
function resourceMeta(raw) {
  try {
    return JSON.parse(raw);
  } catch {
    return {};
  }
}
__name(resourceMeta, "resourceMeta");
function label(type) {
  return type === "ATTENDANCE_ENTER" ? "V\xE0o ca" : type === "ATTENDANCE_EXIT" ? "Ra ca" : type === "RESOURCE_CHANGE" ? "\u0110\u1ED5i t\xE0i nguy\xEAn" : type === "LABOR_START" ? "B\u1EAFt \u0111\u1EA7u c\xF4ng nh\u1EADt" : type === "LABOR_FINISH" ? "K\u1EBFt th\xFAc c\xF4ng nh\u1EADt" : type;
}
__name(label, "label");
async function rebuildGoogleStagingFromD1(db, env) {
  if (env.GOOGLE_STAGING_SHEET_ID === env.GOOGLE_SOURCE_SHEET_ID) throw new Error("DR_TARGET_MUST_NOT_BE_PRODUCTION_SOURCE");
  const started = nowIso(), recoveryId = crypto.randomUUID(), authority2 = await currentAuthority(db);
  await db.prepare("INSERT INTO recovery_runs(recovery_id,recovery_type,from_generation,to_generation,source_authority_epoch,source_authority_seq,target_authority_epoch,status,started_at,validation_json) VALUES(?1,'GOOGLE_REBUILD_FROM_D1',?2,?2,?3,?4,?3,'RUNNING',?5,'{}')").bind(recoveryId, authority2.service_generation, authority2.authority_epoch, authority2.authority_seq, started).run();
  try {
    const employees = (await db.prepare("SELECT mnv,full_name,phone,main_position,supplier,department,site,warehouse,start_date,note FROM employees ORDER BY mnv").all()).results ?? [], staff = new Map(employees.map((e) => [e.mnv, e]));
    const catalog = (await db.prepare("SELECT namespace,ordinal,value FROM catalog_values ORDER BY namespace,ordinal").all()).results ?? [];
    const cats = /* @__PURE__ */ new Map();
    for (const c of catalog) {
      const a = cats.get(c.namespace) ?? [];
      a[c.ordinal - 1] = c.value;
      cats.set(c.namespace, a);
    }
    const catHeaders = HEADERS["Danh m\u1EE5c"], catMax = Math.max(0, ...catHeaders.map((h) => (cats.get(h) ?? []).length)), catRows = Array.from({ length: catMax }, (_, i2) => catHeaders.map((h) => cats.get(h)?.[i2] ?? ""));
    const resources = (await db.prepare("SELECT resource_type,resource_id,status_label,metadata_json FROM resources ORDER BY resource_type,resource_id").all()).results ?? [];
    const pdaRows = resources.filter((r) => r.resource_type === "PDA").map((r) => {
      const m = resourceMeta(r.metadata_json);
      return [r.resource_id, m["5 s\u1ED1 cu\u1ED1i Seri"] ?? r.resource_id.slice(-5), r.status_label, m["Ghi ch\xFA"] ?? ""];
    });
    const pickRows = resources.filter((r) => r.resource_type === "USER_PICK").map((r) => {
      const m = resourceMeta(r.metadata_json);
      return [m["S\u1ED1 User"] ?? "", r.resource_id, r.status_label, m["Ghi ch\xFA"] ?? ""];
    });
    const tableRows = resources.filter((r) => r.resource_type === "PACK_TABLE").map((r) => [r.resource_id, r.status_label]);
    const packMap = (await db.prepare("SELECT pack_table,shift,user_pack,label,available FROM resource_pack_map ORDER BY pack_table,shift,user_pack").all()).results ?? [];
    const packRows = packMap.map((r) => [r.pack_table, r.label, r.user_pack, r.available ? "Kh\u1EA3 d\u1EE5ng" : "Kh\xF4ng kh\u1EA3 d\u1EE5ng"]);
    const employeeRows = employees.map((e) => [e.mnv, e.full_name, e.phone, e.main_position, e.supplier, e.department, e.site, e.warehouse, e.start_date, e.note, "SERVICE_DR", visibleTime(started)]);
    const events = (await db.prepare("SELECT event_id,event_type,entity_id,business_date,authority_seq,service_generation,actor_id,committed_at,payload_json FROM events ORDER BY authority_epoch,authority_seq").all()).results ?? [];
    const attendanceRows = [], historyRows = [];
    for (const e of events) {
      let p = {};
      try {
        p = JSON.parse(e.payload_json);
      } catch {
      }
      const mnv = String(p.mnv ?? ""), emp = staff.get(mnv), shift = String(p.shift ?? "");
      historyRows.push([visibleDate2(e.business_date), e.entity_id, mnv, emp?.full_name ?? "", shift, e.event_type, label(e.event_type), visibleTime(e.committed_at), e.actor_id, String(p.note ?? p.labor_type ?? ""), e.event_id, "SERVICE_D1", e.service_generation]);
      if (["ATTENDANCE_ENTER", "ATTENDANCE_EXIT", "RESOURCE_CHANGE"].includes(e.event_type)) attendanceRows.push([visibleDate2(e.business_date), shift, mnv, emp?.full_name ?? "", emp?.phone ?? "", emp?.supplier ?? "", emp?.department ?? "", emp?.site ?? "", emp?.warehouse ?? "", emp?.main_position ?? "", String(p.work_choice ?? ""), String(p.pda_serial ?? ""), String(p.user_pick ?? ""), String(p.pack_table ?? ""), String(p.user_pack ?? ""), label(e.event_type), String(p.note ?? ""), e.actor_id, visibleTime(e.committed_at), e.event_id, e.event_type, e.service_generation]);
    }
    const labor = (await db.prepare("SELECT labor_id,mnv,business_date,shift,labor_type,time_marker,state,start_at,end_at,note,deduct_staff,start_event_id,finish_event_id,version,updated_at FROM labor_sessions ORDER BY business_date,start_at").all()).results ?? [];
    const laborRows = labor.map((r) => {
      const e = staff.get(r.mnv);
      return [visibleDate2(r.business_date), r.shift, r.mnv, e?.full_name ?? "", e?.phone ?? "", e?.supplier ?? "", e?.department ?? "", e?.site ?? "", e?.warehouse ?? "", e?.main_position ?? "", "", r.labor_type, visibleTime(r.start_at), visibleTime(r.end_at), r.time_marker, r.state, r.note, "SERVICE_DR", visibleTime(r.updated_at), r.start_event_id, r.finish_event_id ?? "", `v${r.version}`, r.deduct_staff ? "C\xF3" : "Kh\xF4ng"];
    });
    const accounts = (await db.prepare("SELECT login_id,verifier,role,display_name,position,email,status FROM accounts WHERE is_shadow_test=0 ORDER BY login_id").all()).results ?? [];
    const adminRows = accounts.map((a) => [a.login_id, a.verifier, a.status, a.display_name, a.role, a.email, a.role, "", a.status, "SERVICE_DR", visibleTime(started)]);
    const t = await token2(env);
    const tables = [["Danh m\u1EE5c", catRows], ["L\u1ECACH S\u1EEC NGHI\u1EC6P V\u1EE4", historyRows], ["DANH S\xC1CH PDA", pdaRows], ["DANH S\xC1CH USER PICK", pickRows], ["DANH S\xC1CH B\xC0N PACK", tableRows], ["DANH S\xC1CH USER PACK", packRows], ["DANH S\xC1CH NH\xC2N S\u1EF0", employeeRows], ["RA - V\xC0O TRONG CA", attendanceRows], ["C\xD4NG NH\u1EACT", laborRows], ["Danh s\xE1ch Admin", adminRows]];
    for (const [name, rows2] of tables) await writeTable(env, t, name, rows2);
    const counts = Object.fromEntries(tables.map(([n, r]) => [n, r.length])), checksum2 = await sha256Hex(JSON.stringify({ authority_epoch: authority2.authority_epoch, authority_seq: authority2.authority_seq, counts })), done = nowIso(), validation = { target_sheet_id: env.GOOGLE_STAGING_SHEET_ID, production_source_untouched: env.GOOGLE_SOURCE_SHEET_ID !== env.GOOGLE_STAGING_SHEET_ID, counts, checksum: checksum2 };
    await db.prepare("UPDATE recovery_runs SET status='COMPLETE',completed_at=?1,validation_json=?2 WHERE recovery_id=?3").bind(done, JSON.stringify(validation), recoveryId).run();
    return { ok: true, recovery_id: recoveryId, authority: authority2, validation };
  } catch (e) {
    await db.prepare("UPDATE recovery_runs SET status='FAILED',completed_at=?1,error=?2 WHERE recovery_id=?3").bind(nowIso(), String(e).slice(0, 1e3), recoveryId).run().catch(() => void 0);
    throw e;
  }
}
__name(rebuildGoogleStagingFromD1, "rebuildGoogleStagingFromD1");

// node_modules/fflate/esm/browser.js
var u8 = Uint8Array;
var u16 = Uint16Array;
var i32 = Int32Array;
var fleb = new u8([
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  1,
  1,
  1,
  1,
  2,
  2,
  2,
  2,
  3,
  3,
  3,
  3,
  4,
  4,
  4,
  4,
  5,
  5,
  5,
  5,
  0,
  /* unused */
  0,
  0,
  /* impossible */
  0
]);
var fdeb = new u8([
  0,
  0,
  0,
  0,
  1,
  1,
  2,
  2,
  3,
  3,
  4,
  4,
  5,
  5,
  6,
  6,
  7,
  7,
  8,
  8,
  9,
  9,
  10,
  10,
  11,
  11,
  12,
  12,
  13,
  13,
  /* unused */
  0,
  0
]);
var clim = new u8([16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]);
var freb = /* @__PURE__ */ __name(function(eb, start) {
  var b = new u16(31);
  for (var i2 = 0; i2 < 31; ++i2) {
    b[i2] = start += 1 << eb[i2 - 1];
  }
  var r = new i32(b[30]);
  for (var i2 = 1; i2 < 30; ++i2) {
    for (var j = b[i2]; j < b[i2 + 1]; ++j) {
      r[j] = j - b[i2] << 5 | i2;
    }
  }
  return { b, r };
}, "freb");
var _a = freb(fleb, 2);
var fl = _a.b;
var revfl = _a.r;
fl[28] = 258, revfl[258] = 28;
var _b = freb(fdeb, 0);
var fd = _b.b;
var revfd = _b.r;
var rev = new u16(32768);
for (i = 0; i < 32768; ++i) {
  x = (i & 43690) >> 1 | (i & 21845) << 1;
  x = (x & 52428) >> 2 | (x & 13107) << 2;
  x = (x & 61680) >> 4 | (x & 3855) << 4;
  rev[i] = ((x & 65280) >> 8 | (x & 255) << 8) >> 1;
}
var x;
var i;
var hMap = /* @__PURE__ */ __name((function(cd, mb, r) {
  var s = cd.length;
  var i2 = 0;
  var l = new u16(mb);
  for (; i2 < s; ++i2) {
    if (cd[i2])
      ++l[cd[i2] - 1];
  }
  var le = new u16(mb);
  for (i2 = 1; i2 < mb; ++i2) {
    le[i2] = le[i2 - 1] + l[i2 - 1] << 1;
  }
  var co;
  if (r) {
    co = new u16(1 << mb);
    var rvb = 15 - mb;
    for (i2 = 0; i2 < s; ++i2) {
      if (cd[i2]) {
        var sv = i2 << 4 | cd[i2];
        var r_1 = mb - cd[i2];
        var v = le[cd[i2] - 1]++ << r_1;
        for (var m = v | (1 << r_1) - 1; v <= m; ++v) {
          co[rev[v] >> rvb] = sv;
        }
      }
    }
  } else {
    co = new u16(s);
    for (i2 = 0; i2 < s; ++i2) {
      if (cd[i2]) {
        co[i2] = rev[le[cd[i2] - 1]++] >> 15 - cd[i2];
      }
    }
  }
  return co;
}), "hMap");
var flt = new u8(288);
for (i = 0; i < 144; ++i)
  flt[i] = 8;
var i;
for (i = 144; i < 256; ++i)
  flt[i] = 9;
var i;
for (i = 256; i < 280; ++i)
  flt[i] = 7;
var i;
for (i = 280; i < 288; ++i)
  flt[i] = 8;
var i;
var fdt = new u8(32);
for (i = 0; i < 32; ++i)
  fdt[i] = 5;
var i;
var flm = /* @__PURE__ */ hMap(flt, 9, 0);
var flrm = /* @__PURE__ */ hMap(flt, 9, 1);
var fdm = /* @__PURE__ */ hMap(fdt, 5, 0);
var fdrm = /* @__PURE__ */ hMap(fdt, 5, 1);
var max = /* @__PURE__ */ __name(function(a) {
  var m = a[0];
  for (var i2 = 1; i2 < a.length; ++i2) {
    if (a[i2] > m)
      m = a[i2];
  }
  return m;
}, "max");
var bits = /* @__PURE__ */ __name(function(d, p, m) {
  var o = p / 8 | 0;
  return (d[o] | d[o + 1] << 8) >> (p & 7) & m;
}, "bits");
var bits16 = /* @__PURE__ */ __name(function(d, p) {
  var o = p / 8 | 0;
  return (d[o] | d[o + 1] << 8 | d[o + 2] << 16) >> (p & 7);
}, "bits16");
var shft = /* @__PURE__ */ __name(function(p) {
  return (p + 7) / 8 | 0;
}, "shft");
var slc = /* @__PURE__ */ __name(function(v, s, e) {
  if (s == null || s < 0)
    s = 0;
  if (e == null || e > v.length)
    e = v.length;
  return new u8(v.subarray(s, e));
}, "slc");
var ec = [
  "unexpected EOF",
  "invalid block type",
  "invalid length/literal",
  "invalid distance",
  "stream finished",
  "no stream handler",
  ,
  // determined by compression function
  "no callback",
  "invalid UTF-8 data",
  "extra field too long",
  "date not in range 1980-2099",
  "filename too long",
  "stream finishing",
  "invalid zip data"
  // determined by unknown compression method
];
var err = /* @__PURE__ */ __name(function(ind, msg, nt) {
  var e = new Error(msg || ec[ind]);
  e.code = ind;
  if (Error.captureStackTrace)
    Error.captureStackTrace(e, err);
  if (!nt)
    throw e;
  return e;
}, "err");
var inflt = /* @__PURE__ */ __name(function(dat, st, buf, dict) {
  var sl = dat.length, dl = dict ? dict.length : 0;
  if (!sl || st.f && !st.l)
    return buf || new u8(0);
  var noBuf = !buf;
  var resize = noBuf || st.i != 2;
  var noSt = st.i;
  if (noBuf)
    buf = new u8(sl * 3);
  var cbuf = /* @__PURE__ */ __name(function(l2) {
    var bl = buf.length;
    if (l2 > bl) {
      var nbuf = new u8(Math.max(bl * 2, l2));
      nbuf.set(buf);
      buf = nbuf;
    }
  }, "cbuf");
  var final = st.f || 0, pos = st.p || 0, bt = st.b || 0, lm = st.l, dm = st.d, lbt = st.m, dbt = st.n;
  var tbts = sl * 8;
  do {
    if (!lm) {
      final = bits(dat, pos, 1);
      var type = bits(dat, pos + 1, 3);
      pos += 3;
      if (!type) {
        var s = shft(pos) + 4, l = dat[s - 4] | dat[s - 3] << 8, t = s + l;
        if (t > sl) {
          if (noSt)
            err(0);
          break;
        }
        if (resize)
          cbuf(bt + l);
        buf.set(dat.subarray(s, t), bt);
        st.b = bt += l, st.p = pos = t * 8, st.f = final;
        continue;
      } else if (type == 1)
        lm = flrm, dm = fdrm, lbt = 9, dbt = 5;
      else if (type == 2) {
        var hLit = bits(dat, pos, 31) + 257, hcLen = bits(dat, pos + 10, 15) + 4;
        var tl = hLit + bits(dat, pos + 5, 31) + 1;
        pos += 14;
        var ldt = new u8(tl);
        var clt = new u8(19);
        for (var i2 = 0; i2 < hcLen; ++i2) {
          clt[clim[i2]] = bits(dat, pos + i2 * 3, 7);
        }
        pos += hcLen * 3;
        var clb = max(clt), clbmsk = (1 << clb) - 1;
        var clm = hMap(clt, clb, 1);
        for (var i2 = 0; i2 < tl; ) {
          var r = clm[bits(dat, pos, clbmsk)];
          pos += r & 15;
          var s = r >> 4;
          if (s < 16) {
            ldt[i2++] = s;
          } else {
            var c = 0, n = 0;
            if (s == 16)
              n = 3 + bits(dat, pos, 3), pos += 2, c = ldt[i2 - 1];
            else if (s == 17)
              n = 3 + bits(dat, pos, 7), pos += 3;
            else if (s == 18)
              n = 11 + bits(dat, pos, 127), pos += 7;
            while (n--)
              ldt[i2++] = c;
          }
        }
        var lt = ldt.subarray(0, hLit), dt = ldt.subarray(hLit);
        lbt = max(lt);
        dbt = max(dt);
        lm = hMap(lt, lbt, 1);
        dm = hMap(dt, dbt, 1);
      } else
        err(1);
      if (pos > tbts) {
        if (noSt)
          err(0);
        break;
      }
    }
    if (resize)
      cbuf(bt + 131072);
    var lms = (1 << lbt) - 1, dms = (1 << dbt) - 1;
    var lpos = pos;
    for (; ; lpos = pos) {
      var c = lm[bits16(dat, pos) & lms], sym = c >> 4;
      pos += c & 15;
      if (pos > tbts) {
        if (noSt)
          err(0);
        break;
      }
      if (!c)
        err(2);
      if (sym < 256)
        buf[bt++] = sym;
      else if (sym == 256) {
        lpos = pos, lm = null;
        break;
      } else {
        var add = sym - 254;
        if (sym > 264) {
          var i2 = sym - 257, b = fleb[i2];
          add = bits(dat, pos, (1 << b) - 1) + fl[i2];
          pos += b;
        }
        var d = dm[bits16(dat, pos) & dms], dsym = d >> 4;
        if (!d)
          err(3);
        pos += d & 15;
        var dt = fd[dsym];
        if (dsym > 3) {
          var b = fdeb[dsym];
          dt += bits16(dat, pos) & (1 << b) - 1, pos += b;
        }
        if (pos > tbts) {
          if (noSt)
            err(0);
          break;
        }
        if (resize)
          cbuf(bt + 131072);
        var end = bt + add;
        if (bt < dt) {
          var shift = dl - dt, dend = Math.min(dt, end);
          if (shift + bt < 0)
            err(3);
          for (; bt < dend; ++bt)
            buf[bt] = dict[shift + bt];
        }
        for (; bt < end; ++bt)
          buf[bt] = buf[bt - dt];
      }
    }
    st.l = lm, st.p = lpos, st.b = bt, st.f = final;
    if (lm)
      final = 1, st.m = lbt, st.d = dm, st.n = dbt;
  } while (!final);
  return bt != buf.length && noBuf ? slc(buf, 0, bt) : buf.subarray(0, bt);
}, "inflt");
var wbits = /* @__PURE__ */ __name(function(d, p, v) {
  v <<= p & 7;
  var o = p / 8 | 0;
  d[o] |= v;
  d[o + 1] |= v >> 8;
}, "wbits");
var wbits16 = /* @__PURE__ */ __name(function(d, p, v) {
  v <<= p & 7;
  var o = p / 8 | 0;
  d[o] |= v;
  d[o + 1] |= v >> 8;
  d[o + 2] |= v >> 16;
}, "wbits16");
var hTree = /* @__PURE__ */ __name(function(d, mb) {
  var t = [];
  for (var i2 = 0; i2 < d.length; ++i2) {
    if (d[i2])
      t.push({ s: i2, f: d[i2] });
  }
  var s = t.length;
  var t2 = t.slice();
  if (!s)
    return { t: et, l: 0 };
  if (s == 1) {
    var v = new u8(t[0].s + 1);
    v[t[0].s] = 1;
    return { t: v, l: 1 };
  }
  t.sort(function(a, b) {
    return a.f - b.f;
  });
  t.push({ s: -1, f: 25001 });
  var l = t[0], r = t[1], i0 = 0, i1 = 1, i22 = 2;
  t[0] = { s: -1, f: l.f + r.f, l, r };
  while (i1 != s - 1) {
    l = t[t[i0].f < t[i22].f ? i0++ : i22++];
    r = t[i0 != i1 && t[i0].f < t[i22].f ? i0++ : i22++];
    t[i1++] = { s: -1, f: l.f + r.f, l, r };
  }
  var maxSym = t2[0].s;
  for (var i2 = 1; i2 < s; ++i2) {
    if (t2[i2].s > maxSym)
      maxSym = t2[i2].s;
  }
  var tr = new u16(maxSym + 1);
  var mbt = ln(t[i1 - 1], tr, 0);
  if (mbt > mb) {
    var i2 = 0, dt = 0;
    var lft = mbt - mb, cst = 1 << lft;
    t2.sort(function(a, b) {
      return tr[b.s] - tr[a.s] || a.f - b.f;
    });
    for (; i2 < s; ++i2) {
      var i2_1 = t2[i2].s;
      if (tr[i2_1] > mb) {
        dt += cst - (1 << mbt - tr[i2_1]);
        tr[i2_1] = mb;
      } else
        break;
    }
    dt >>= lft;
    while (dt > 0) {
      var i2_2 = t2[i2].s;
      if (tr[i2_2] < mb)
        dt -= 1 << mb - tr[i2_2]++ - 1;
      else
        ++i2;
    }
    for (; i2 >= 0 && dt; --i2) {
      var i2_3 = t2[i2].s;
      if (tr[i2_3] == mb) {
        --tr[i2_3];
        ++dt;
      }
    }
    mbt = mb;
  }
  return { t: new u8(tr), l: mbt };
}, "hTree");
var ln = /* @__PURE__ */ __name(function(n, l, d) {
  return n.s == -1 ? Math.max(ln(n.l, l, d + 1), ln(n.r, l, d + 1)) : l[n.s] = d;
}, "ln");
var lc = /* @__PURE__ */ __name(function(c) {
  var s = c.length;
  while (s && !c[--s])
    ;
  var cl = new u16(++s);
  var cli = 0, cln = c[0], cls = 1;
  var w = /* @__PURE__ */ __name(function(v) {
    cl[cli++] = v;
  }, "w");
  for (var i2 = 1; i2 <= s; ++i2) {
    if (c[i2] == cln && i2 != s)
      ++cls;
    else {
      if (!cln && cls > 2) {
        for (; cls > 138; cls -= 138)
          w(32754);
        if (cls > 2) {
          w(cls > 10 ? cls - 11 << 5 | 28690 : cls - 3 << 5 | 12305);
          cls = 0;
        }
      } else if (cls > 3) {
        w(cln), --cls;
        for (; cls > 6; cls -= 6)
          w(8304);
        if (cls > 2)
          w(cls - 3 << 5 | 8208), cls = 0;
      }
      while (cls--)
        w(cln);
      cls = 1;
      cln = c[i2];
    }
  }
  return { c: cl.subarray(0, cli), n: s };
}, "lc");
var clen = /* @__PURE__ */ __name(function(cf, cl) {
  var l = 0;
  for (var i2 = 0; i2 < cl.length; ++i2)
    l += cf[i2] * cl[i2];
  return l;
}, "clen");
var wfblk = /* @__PURE__ */ __name(function(out, pos, dat) {
  var s = dat.length;
  var o = shft(pos + 2);
  out[o] = s & 255;
  out[o + 1] = s >> 8;
  out[o + 2] = out[o] ^ 255;
  out[o + 3] = out[o + 1] ^ 255;
  for (var i2 = 0; i2 < s; ++i2)
    out[o + i2 + 4] = dat[i2];
  return (o + 4 + s) * 8;
}, "wfblk");
var wblk = /* @__PURE__ */ __name(function(dat, out, final, syms, lf, df, eb, li, bs, bl, p) {
  wbits(out, p++, final);
  ++lf[256];
  var _a2 = hTree(lf, 15), dlt = _a2.t, mlb = _a2.l;
  var _b2 = hTree(df, 15), ddt = _b2.t, mdb = _b2.l;
  var _c = lc(dlt), lclt = _c.c, nlc = _c.n;
  var _d = lc(ddt), lcdt = _d.c, ndc = _d.n;
  var lcfreq = new u16(19);
  for (var i2 = 0; i2 < lclt.length; ++i2)
    ++lcfreq[lclt[i2] & 31];
  for (var i2 = 0; i2 < lcdt.length; ++i2)
    ++lcfreq[lcdt[i2] & 31];
  var _e = hTree(lcfreq, 7), lct = _e.t, mlcb = _e.l;
  var nlcc = 19;
  for (; nlcc > 4 && !lct[clim[nlcc - 1]]; --nlcc)
    ;
  var flen = bl + 5 << 3;
  var ftlen = clen(lf, flt) + clen(df, fdt) + eb;
  var dtlen = clen(lf, dlt) + clen(df, ddt) + eb + 14 + 3 * nlcc + clen(lcfreq, lct) + 2 * lcfreq[16] + 3 * lcfreq[17] + 7 * lcfreq[18];
  if (bs >= 0 && flen <= ftlen && flen <= dtlen)
    return wfblk(out, p, dat.subarray(bs, bs + bl));
  var lm, ll, dm, dl;
  wbits(out, p, 1 + (dtlen < ftlen)), p += 2;
  if (dtlen < ftlen) {
    lm = hMap(dlt, mlb, 0), ll = dlt, dm = hMap(ddt, mdb, 0), dl = ddt;
    var llm = hMap(lct, mlcb, 0);
    wbits(out, p, nlc - 257);
    wbits(out, p + 5, ndc - 1);
    wbits(out, p + 10, nlcc - 4);
    p += 14;
    for (var i2 = 0; i2 < nlcc; ++i2)
      wbits(out, p + 3 * i2, lct[clim[i2]]);
    p += 3 * nlcc;
    var lcts = [lclt, lcdt];
    for (var it = 0; it < 2; ++it) {
      var clct = lcts[it];
      for (var i2 = 0; i2 < clct.length; ++i2) {
        var len = clct[i2] & 31;
        wbits(out, p, llm[len]), p += lct[len];
        if (len > 15)
          wbits(out, p, clct[i2] >> 5 & 127), p += clct[i2] >> 12;
      }
    }
  } else {
    lm = flm, ll = flt, dm = fdm, dl = fdt;
  }
  for (var i2 = 0; i2 < li; ++i2) {
    var sym = syms[i2];
    if (sym > 255) {
      var len = sym >> 18 & 31;
      wbits16(out, p, lm[len + 257]), p += ll[len + 257];
      if (len > 7)
        wbits(out, p, sym >> 23 & 31), p += fleb[len];
      var dst = sym & 31;
      wbits16(out, p, dm[dst]), p += dl[dst];
      if (dst > 3)
        wbits16(out, p, sym >> 5 & 8191), p += fdeb[dst];
    } else {
      wbits16(out, p, lm[sym]), p += ll[sym];
    }
  }
  wbits16(out, p, lm[256]);
  return p + ll[256];
}, "wblk");
var deo = /* @__PURE__ */ new i32([65540, 131080, 131088, 131104, 262176, 1048704, 1048832, 2114560, 2117632]);
var et = /* @__PURE__ */ new u8(0);
var dflt = /* @__PURE__ */ __name(function(dat, lvl, plvl, pre, post, st) {
  var s = st.z || dat.length;
  var o = new u8(pre + s + 5 * (1 + Math.ceil(s / 7e3)) + post);
  var w = o.subarray(pre, o.length - post);
  var lst = st.l;
  var pos = (st.r || 0) & 7;
  if (lvl) {
    if (pos)
      w[0] = st.r >> 3;
    var opt = deo[lvl - 1];
    var n = opt >> 13, c = opt & 8191;
    var msk_1 = (1 << plvl) - 1;
    var prev = st.p || new u16(32768), head = st.h || new u16(msk_1 + 1);
    var bs1_1 = Math.ceil(plvl / 3), bs2_1 = 2 * bs1_1;
    var hsh = /* @__PURE__ */ __name(function(i3) {
      return (dat[i3] ^ dat[i3 + 1] << bs1_1 ^ dat[i3 + 2] << bs2_1) & msk_1;
    }, "hsh");
    var syms = new i32(25e3);
    var lf = new u16(288), df = new u16(32);
    var lc_1 = 0, eb = 0, i2 = st.i || 0, li = 0, wi = st.w || 0, bs = 0;
    for (; i2 + 2 < s; ++i2) {
      var hv = hsh(i2);
      var imod = i2 & 32767, pimod = head[hv];
      prev[imod] = pimod;
      head[hv] = imod;
      if (wi <= i2) {
        var rem = s - i2;
        if ((lc_1 > 7e3 || li > 24576) && (rem > 423 || !lst)) {
          pos = wblk(dat, w, 0, syms, lf, df, eb, li, bs, i2 - bs, pos);
          li = lc_1 = eb = 0, bs = i2;
          for (var j = 0; j < 286; ++j)
            lf[j] = 0;
          for (var j = 0; j < 30; ++j)
            df[j] = 0;
        }
        var l = 2, d = 0, ch_1 = c, dif = imod - pimod & 32767;
        if (rem > 2 && hv == hsh(i2 - dif)) {
          var maxn = Math.min(n, rem) - 1;
          var maxd = Math.min(32767, i2);
          var ml = Math.min(258, rem);
          while (dif <= maxd && --ch_1 && imod != pimod) {
            if (dat[i2 + l] == dat[i2 + l - dif]) {
              var nl = 0;
              for (; nl < ml && dat[i2 + nl] == dat[i2 + nl - dif]; ++nl)
                ;
              if (nl > l) {
                l = nl, d = dif;
                if (nl > maxn)
                  break;
                var mmd = Math.min(dif, nl - 2);
                var md = 0;
                for (var j = 0; j < mmd; ++j) {
                  var ti = i2 - dif + j & 32767;
                  var pti = prev[ti];
                  var cd = ti - pti & 32767;
                  if (cd > md)
                    md = cd, pimod = ti;
                }
              }
            }
            imod = pimod, pimod = prev[imod];
            dif += imod - pimod & 32767;
          }
        }
        if (d) {
          syms[li++] = 268435456 | revfl[l] << 18 | revfd[d];
          var lin = revfl[l] & 31, din = revfd[d] & 31;
          eb += fleb[lin] + fdeb[din];
          ++lf[257 + lin];
          ++df[din];
          wi = i2 + l;
          ++lc_1;
        } else {
          syms[li++] = dat[i2];
          ++lf[dat[i2]];
        }
      }
    }
    for (i2 = Math.max(i2, wi); i2 < s; ++i2) {
      syms[li++] = dat[i2];
      ++lf[dat[i2]];
    }
    pos = wblk(dat, w, lst, syms, lf, df, eb, li, bs, i2 - bs, pos);
    if (!lst) {
      st.r = pos & 7 | w[pos / 8 | 0] << 3;
      pos -= 7;
      st.h = head, st.p = prev, st.i = i2, st.w = wi;
    }
  } else {
    for (var i2 = st.w || 0; i2 < s + lst; i2 += 65535) {
      var e = i2 + 65535;
      if (e >= s) {
        w[pos / 8 | 0] = lst;
        e = s;
      }
      pos = wfblk(w, pos + 1, dat.subarray(i2, e));
    }
    st.i = s;
  }
  return slc(o, 0, pre + shft(pos) + post);
}, "dflt");
var crct = /* @__PURE__ */ (function() {
  var t = new Int32Array(256);
  for (var i2 = 0; i2 < 256; ++i2) {
    var c = i2, k = 9;
    while (--k)
      c = (c & 1 && -306674912) ^ c >>> 1;
    t[i2] = c;
  }
  return t;
})();
var crc = /* @__PURE__ */ __name(function() {
  var c = -1;
  return {
    p: /* @__PURE__ */ __name(function(d) {
      var cr = c;
      for (var i2 = 0; i2 < d.length; ++i2)
        cr = crct[cr & 255 ^ d[i2]] ^ cr >>> 8;
      c = cr;
    }, "p"),
    d: /* @__PURE__ */ __name(function() {
      return ~c;
    }, "d")
  };
}, "crc");
var dopt = /* @__PURE__ */ __name(function(dat, opt, pre, post, st) {
  if (!st) {
    st = { l: 1 };
    if (opt.dictionary) {
      var dict = opt.dictionary.subarray(-32768);
      var newDat = new u8(dict.length + dat.length);
      newDat.set(dict);
      newDat.set(dat, dict.length);
      dat = newDat;
      st.w = dict.length;
    }
  }
  return dflt(dat, opt.level == null ? 6 : opt.level, opt.mem == null ? st.l ? Math.ceil(Math.max(8, Math.min(13, Math.log(dat.length))) * 1.5) : 20 : 12 + opt.mem, pre, post, st);
}, "dopt");
var mrg = /* @__PURE__ */ __name(function(a, b) {
  var o = {};
  for (var k in a)
    o[k] = a[k];
  for (var k in b)
    o[k] = b[k];
  return o;
}, "mrg");
var b2 = /* @__PURE__ */ __name(function(d, b) {
  return d[b] | d[b + 1] << 8;
}, "b2");
var b4 = /* @__PURE__ */ __name(function(d, b) {
  return (d[b] | d[b + 1] << 8 | d[b + 2] << 16 | d[b + 3] << 24) >>> 0;
}, "b4");
var b8 = /* @__PURE__ */ __name(function(d, b) {
  return b4(d, b) + b4(d, b + 4) * 4294967296;
}, "b8");
var wbytes = /* @__PURE__ */ __name(function(d, b, v) {
  for (; v; ++b)
    d[b] = v, v >>>= 8;
}, "wbytes");
function deflateSync(data, opts) {
  return dopt(data, opts || {}, 0, 0);
}
__name(deflateSync, "deflateSync");
function inflateSync(data, opts) {
  return inflt(data, { i: 2 }, opts && opts.out, opts && opts.dictionary);
}
__name(inflateSync, "inflateSync");
var fltn = /* @__PURE__ */ __name(function(d, p, t, o) {
  for (var k in d) {
    var val = d[k], n = p + k, op = o;
    if (Array.isArray(val))
      op = mrg(o, val[1]), val = val[0];
    if (ArrayBuffer.isView(val))
      t[n] = [val, op];
    else {
      t[n += "/"] = [new u8(0), op];
      fltn(val, n, t, o);
    }
  }
}, "fltn");
var te = typeof TextEncoder != "undefined" && /* @__PURE__ */ new TextEncoder();
var td = typeof TextDecoder != "undefined" && /* @__PURE__ */ new TextDecoder();
var tds = 0;
try {
  td.decode(et, { stream: true });
  tds = 1;
} catch (e) {
}
var dutf8 = /* @__PURE__ */ __name(function(d) {
  for (var r = "", i2 = 0; ; ) {
    var c = d[i2++];
    var eb = (c > 127) + (c > 223) + (c > 239);
    if (i2 + eb > d.length)
      return { s: r, r: slc(d, i2 - 1) };
    if (!eb)
      r += String.fromCharCode(c);
    else if (eb == 3) {
      c = ((c & 15) << 18 | (d[i2++] & 63) << 12 | (d[i2++] & 63) << 6 | d[i2++] & 63) - 65536, r += String.fromCharCode(55296 | c >> 10, 56320 | c & 1023);
    } else if (eb & 1)
      r += String.fromCharCode((c & 31) << 6 | d[i2++] & 63);
    else
      r += String.fromCharCode((c & 15) << 12 | (d[i2++] & 63) << 6 | d[i2++] & 63);
  }
}, "dutf8");
function strToU8(str, latin1) {
  if (latin1) {
    var ar_1 = new u8(str.length);
    for (var i2 = 0; i2 < str.length; ++i2)
      ar_1[i2] = str.charCodeAt(i2);
    return ar_1;
  }
  if (te)
    return te.encode(str);
  var l = str.length;
  var ar = new u8(str.length + (str.length >> 1));
  var ai = 0;
  var w = /* @__PURE__ */ __name(function(v) {
    ar[ai++] = v;
  }, "w");
  for (var i2 = 0; i2 < l; ++i2) {
    if (ai + 5 > ar.length) {
      var n = new u8(ai + 8 + (l - i2 << 1));
      n.set(ar);
      ar = n;
    }
    var c = str.charCodeAt(i2);
    if (c < 128 || latin1)
      w(c);
    else if (c < 2048)
      w(192 | c >> 6), w(128 | c & 63);
    else if (c > 55295 && c < 57344)
      c = 65536 + (c & 1023 << 10) | str.charCodeAt(++i2) & 1023, w(240 | c >> 18), w(128 | c >> 12 & 63), w(128 | c >> 6 & 63), w(128 | c & 63);
    else
      w(224 | c >> 12), w(128 | c >> 6 & 63), w(128 | c & 63);
  }
  return slc(ar, 0, ai);
}
__name(strToU8, "strToU8");
function strFromU8(dat, latin1) {
  if (latin1) {
    var r = "";
    for (var i2 = 0; i2 < dat.length; i2 += 16384)
      r += String.fromCharCode.apply(null, dat.subarray(i2, i2 + 16384));
    return r;
  } else if (td) {
    return td.decode(dat);
  } else {
    var _a2 = dutf8(dat), s = _a2.s, r = _a2.r;
    if (r.length)
      err(8);
    return s;
  }
}
__name(strFromU8, "strFromU8");
var slzh = /* @__PURE__ */ __name(function(d, b) {
  return b + 30 + b2(d, b + 26) + b2(d, b + 28);
}, "slzh");
var zh = /* @__PURE__ */ __name(function(d, b, z) {
  var fnl = b2(d, b + 28), efl = b2(d, b + 30), fn = strFromU8(d.subarray(b + 46, b + 46 + fnl), !(b2(d, b + 8) & 2048)), es = b + 46 + fnl;
  var _a2 = z64hs(d, es, efl, z, b4(d, b + 20), b4(d, b + 24), b4(d, b + 42)), sc = _a2[0], su = _a2[1], off = _a2[2];
  return [b2(d, b + 10), sc, su, fn, es + efl + b2(d, b + 32), off];
}, "zh");
var z64hs = /* @__PURE__ */ __name(function(d, b, l, z, sc, su, off) {
  var nsc = sc == 4294967295, nsu = su == 4294967295, noff = off == 4294967295, e = b + l;
  var nf = nsc + nsu + noff;
  if (z && nf) {
    for (; b + 4 < e; b += 4 + b2(d, b + 2)) {
      if (b2(d, b) == 1) {
        return [
          nsc ? b8(d, b + 4 + 8 * nsu) : sc,
          nsu ? b8(d, b + 4) : su,
          noff ? b8(d, b + 4 + 8 * (nsu + nsc)) : off,
          1
        ];
      }
    }
    if (z < 2)
      err(13);
  }
  return [sc, su, off, 0];
}, "z64hs");
var exfl = /* @__PURE__ */ __name(function(ex) {
  var le = 0;
  if (ex) {
    for (var k in ex) {
      var l = ex[k].length;
      if (l > 65535)
        err(9);
      le += l + 4;
    }
  }
  return le;
}, "exfl");
var wzh = /* @__PURE__ */ __name(function(d, b, f, fn, u, c, ce, co) {
  var fl2 = fn.length, ex = f.extra, col = co && co.length;
  var exl = exfl(ex);
  wbytes(d, b, ce != null ? 33639248 : 67324752), b += 4;
  if (ce != null)
    d[b++] = 20, d[b++] = f.os;
  d[b] = 20, b += 2;
  d[b++] = f.flag << 1 | (c < 0 && 8), d[b++] = u && 8;
  d[b++] = f.compression & 255, d[b++] = f.compression >> 8;
  var dt = new Date(f.mtime == null ? Date.now() : f.mtime), y = dt.getFullYear() - 1980;
  if (y < 0 || y > 119)
    err(10);
  wbytes(d, b, y << 25 | dt.getMonth() + 1 << 21 | dt.getDate() << 16 | dt.getHours() << 11 | dt.getMinutes() << 5 | dt.getSeconds() >> 1), b += 4;
  if (c != -1) {
    wbytes(d, b, f.crc);
    wbytes(d, b + 4, c < 0 ? -c - 2 : c);
    wbytes(d, b + 8, f.size);
  }
  wbytes(d, b + 12, fl2);
  wbytes(d, b + 14, exl), b += 16;
  if (ce != null) {
    wbytes(d, b, col);
    wbytes(d, b + 6, f.attrs);
    wbytes(d, b + 10, ce), b += 14;
  }
  d.set(fn, b);
  b += fl2;
  if (exl) {
    for (var k in ex) {
      var exf = ex[k], l = exf.length;
      wbytes(d, b, +k);
      wbytes(d, b + 2, l);
      d.set(exf, b + 4), b += 4 + l;
    }
  }
  if (col)
    d.set(co, b), b += col;
  return b;
}, "wzh");
var wzf = /* @__PURE__ */ __name(function(o, b, c, d, e) {
  wbytes(o, b, 101010256);
  wbytes(o, b + 8, c);
  wbytes(o, b + 10, c);
  wbytes(o, b + 12, d);
  wbytes(o, b + 16, e);
}, "wzf");
function zipSync(data, opts) {
  if (!opts)
    opts = {};
  var r = {};
  var files = [];
  fltn(data, "", r, opts);
  var o = 0;
  var tot = 0;
  for (var fn in r) {
    var _a2 = r[fn], file = _a2[0], p = _a2[1];
    var compression = p.level == 0 ? 0 : 8;
    var f = strToU8(fn), s = f.length;
    var com = p.comment, m = com && strToU8(com), ms = m && m.length;
    var exl = exfl(p.extra);
    if (s > 65535)
      err(11);
    var d = compression ? deflateSync(file, p) : file, l = d.length;
    var c = crc();
    c.p(file);
    files.push(mrg(p, {
      size: file.length,
      crc: c.d(),
      c: d,
      f,
      m,
      u: s != fn.length || m && com.length != ms,
      o,
      compression
    }));
    o += 30 + s + exl + l;
    tot += 76 + 2 * (s + exl) + (ms || 0) + l;
  }
  var out = new u8(tot + 22), oe = o, cdl = tot - o;
  for (var i2 = 0; i2 < files.length; ++i2) {
    var f = files[i2];
    wzh(out, f.o, f, f.f, f.u, f.c.length);
    var badd = 30 + f.f.length + exfl(f.extra);
    out.set(f.c, f.o + badd);
    wzh(out, o, f, f.f, f.u, f.c.length, f.o, f.m), o += 16 + badd + (f.m ? f.m.length : 0);
  }
  wzf(out, o, files.length, cdl, oe);
  return out;
}
__name(zipSync, "zipSync");
function unzipSync(data, opts) {
  var files = {};
  var e = data.length - 22;
  for (; b4(data, e) != 101010256; --e) {
    if (!e || data.length - e > 65558)
      err(13);
  }
  ;
  var c = b2(data, e + 8);
  if (!c)
    return {};
  var o = b4(data, e + 16);
  var z = b4(data, e - 20) == 117853008;
  if (z) {
    var ze = b4(data, e - 12);
    z = b4(data, ze) == 101075792;
    if (z) {
      c = b4(data, ze + 32);
      o = b4(data, ze + 48);
    }
  }
  var fltr = opts && opts.filter;
  for (var i2 = 0; i2 < c; ++i2) {
    var _a2 = zh(data, o, z), c_2 = _a2[0], sc = _a2[1], su = _a2[2], fn = _a2[3], no = _a2[4], off = _a2[5], b = slzh(data, off);
    o = no;
    if (!fltr || fltr({
      name: fn,
      size: sc,
      originalSize: su,
      compression: c_2
    })) {
      if (!c_2)
        files[fn] = slc(data, b, b + sc);
      else if (c_2 == 8)
        files[fn] = inflateSync(data.subarray(b, b + sc), { out: new u8(su) });
      else
        err(14, "unknown compression type " + c_2);
    }
  }
  return files;
}
__name(unzipSync, "unzipSync");

// src/import_xlsx.ts
var VERSION2 = "2026-08-19-v1";
var SPECS = {
  employees: { headers: ["mnv", "full_name", "phone", "main_position", "supplier", "department", "site", "warehouse", "start_date", "note"], required: ["mnv", "full_name"] },
  catalogs: { headers: ["namespace", "ordinal", "value"], required: ["namespace", "value"] },
  pda: { headers: ["resource_id", "status_label", "available", "metadata_json"], required: ["resource_id"] },
  user_pick: { headers: ["resource_id", "status_label", "available", "metadata_json"], required: ["resource_id"] },
  pack_table: { headers: ["pack_table", "shift", "user_pack", "label", "status_label", "available"], required: ["pack_table", "shift", "status_label"] },
  user_pack: { headers: ["resource_id", "status_label", "available", "metadata_json"], required: ["resource_id"] }
};
function isDataset3(v) {
  return Object.hasOwn(SPECS, v);
}
__name(isDataset3, "isDataset");
async function requireSuper3(request, env) {
  const a = await authenticate(env.DB, env, request);
  if (!a) return apiError("UNAUTHORIZED", "AUTH", 401);
  if (a.role !== "SUPERADMIN") return apiError("SUPERADMIN_REQUIRED", "PERMISSION", 403);
  return true;
}
__name(requireSuper3, "requireSuper");
async function checksum(dataset) {
  const s = SPECS[dataset];
  return sha256Hex(JSON.stringify({ version: VERSION2, dataset, headers: s.headers, required: s.required }));
}
__name(checksum, "checksum");
function esc(v) {
  return v.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&apos;");
}
__name(esc, "esc");
function unesc(v) {
  return v.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&amp;/g, "&");
}
__name(unesc, "unesc");
function colName(n) {
  let out = "";
  for (let x2 = n + 1; x2 > 0; x2 = Math.floor((x2 - 1) / 26)) out = String.fromCharCode(65 + (x2 - 1) % 26) + out;
  return out;
}
__name(colName, "colName");
function colIndex(ref) {
  let n = 0;
  for (const ch of ref.replace(/[^A-Za-z].*$/, "")) n = n * 26 + (ch.toUpperCase().charCodeAt(0) - 64);
  return n - 1;
}
__name(colIndex, "colIndex");
function sheetXml(rows2) {
  const body = rows2.map((row, ri) => `<row r="${ri + 1}">${row.map((v, ci) => `<c r="${colName(ci)}${ri + 1}" t="inlineStr"><is><t xml:space="preserve">${esc(v)}</t></is></c>`).join("")}</row>`).join("");
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>${body}</sheetData></worksheet>`;
}
__name(sheetXml, "sheetXml");
async function importTemplateXlsx(request, env) {
  const ok = await requireSuper3(request, env);
  if (ok instanceof Response) return ok;
  const u = new URL(request.url), dataset = String(u.searchParams.get("dataset") || "");
  if (!isDataset3(dataset)) return apiError("IMPORT_DATASET_UNSUPPORTED", "VALIDATION", 400);
  const spec = SPECS[dataset], digest = await checksum(dataset);
  const files = {
    "[Content_Types].xml": strToU8(`<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>`),
    "_rels/.rels": strToU8(`<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`),
    "xl/workbook.xml": strToU8(`<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="DATA" sheetId="1" r:id="rId1"/><sheet name="__IMPORT_META" sheetId="2" state="hidden" r:id="rId2"/></sheets></workbook>`),
    "xl/_rels/workbook.xml.rels": strToU8(`<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`),
    "xl/styles.xml": strToU8(`<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts><fills count="1"><fill><patternFill patternType="none"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs></styleSheet>`),
    "xl/worksheets/sheet1.xml": strToU8(sheetXml([spec.headers])),
    "xl/worksheets/sheet2.xml": strToU8(sheetXml([["key", "value"], ["template_version", VERSION2], ["dataset", dataset], ["schema_checksum", digest]]))
  };
  const bytes = zipSync(files, { level: 6 });
  return new Response(bytes, { status: 200, headers: { "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "content-disposition": `attachment; filename="pick-pack-1291-${dataset}-${VERSION2}.xlsx"`, "cache-control": "no-store" } });
}
__name(importTemplateXlsx, "importTemplateXlsx");
function decodeShared(xml) {
  const out = [];
  for (const m of xml.matchAll(/<si\b[^>]*>([\s\S]*?)<\/si>/g)) {
    let s = "";
    for (const t of m[1].matchAll(/<t\b[^>]*>([\s\S]*?)<\/t>/g)) s += unesc(t[1] ?? "");
    out.push(s);
  }
  return out;
}
__name(decodeShared, "decodeShared");
function parseSheet(xml, shared) {
  const rows2 = [];
  for (const rm of xml.matchAll(/<row\b[^>]*>([\s\S]*?)<\/row>/g)) {
    const cells = [];
    for (const cm of rm[1].matchAll(/<c\b([^>]*)>([\s\S]*?)<\/c>/g)) {
      const attrs = cm[1] ?? "", inner = cm[2] ?? "", ref = /\br="([A-Z]+\d+)"/.exec(attrs)?.[1] ?? "A1", idx = colIndex(ref), type = /\bt="([^"]+)"/.exec(attrs)?.[1] ?? "";
      let value = "";
      if (type === "inlineStr") {
        for (const t of inner.matchAll(/<t\b[^>]*>([\s\S]*?)<\/t>/g)) value += unesc(t[1] ?? "");
      } else {
        const raw = /<v\b[^>]*>([\s\S]*?)<\/v>/.exec(inner)?.[1] ?? "";
        value = type === "s" ? shared[Number(raw)] ?? "" : unesc(raw);
      }
      while (cells.length <= idx) cells.push("");
      cells[idx] = value;
    }
    rows2.push(cells);
  }
  return rows2;
}
__name(parseSheet, "parseSheet");
function b64Bytes(v) {
  const clean = v.replace(/^data:[^,]+,/, "").replace(/\s/g, "");
  const raw = atob(clean), out = new Uint8Array(raw.length);
  for (let i2 = 0; i2 < raw.length; i2++) out[i2] = raw.charCodeAt(i2);
  return out;
}
__name(b64Bytes, "b64Bytes");
function metaMap(table) {
  const out = {};
  for (const row of table.slice(1)) {
    const k = String(row[0] || "").trim(), v = String(row[1] || "").trim();
    if (k) out[k] = v;
  }
  return out;
}
__name(metaMap, "metaMap");
async function importParseXlsx(request, env) {
  const ok = await requireSuper3(request, env);
  if (ok instanceof Response) return ok;
  const b = await readJsonBody(request), dataset = String(b.dataset || "");
  if (!isDataset3(dataset)) return apiError("IMPORT_DATASET_UNSUPPORTED", "VALIDATION", 400);
  if (!String(b.file_name || "").toLowerCase().endsWith(".xlsx")) return apiError("IMPORT_XLSX_EXTENSION_REQUIRED", "VALIDATION", 400);
  let bytes;
  try {
    bytes = b64Bytes(String(b.file_base64 || ""));
  } catch {
    return apiError("IMPORT_XLSX_BASE64_INVALID", "VALIDATION", 400);
  }
  if (bytes.length < 4 || bytes[0] !== 80 || bytes[1] !== 75) return apiError("IMPORT_XLSX_ZIP_INVALID", "VALIDATION", 400);
  if (bytes.length > 8 * 1024 * 1024) return apiError("IMPORT_XLSX_TOO_LARGE", "VALIDATION", 413, false, void 0, { max_bytes: 8 * 1024 * 1024 });
  let zip;
  try {
    zip = unzipSync(bytes, { filter: /* @__PURE__ */ __name((file) => file.name === "xl/sharedStrings.xml" || file.name === "xl/worksheets/sheet1.xml" || file.name === "xl/worksheets/sheet2.xml", "filter") });
  } catch {
    return apiError("IMPORT_XLSX_ZIP_INVALID", "VALIDATION", 400);
  }
  const sheet = zip["xl/worksheets/sheet1.xml"], metaSheet = zip["xl/worksheets/sheet2.xml"];
  if (!sheet) return apiError("IMPORT_XLSX_DATA_SHEET_MISSING", "SCHEMA", 400);
  if (!metaSheet) return apiError("IMPORT_TEMPLATE_METADATA_MISSING", "SCHEMA", 409);
  const decoder = new TextDecoder(), shared = zip["xl/sharedStrings.xml"] ? decodeShared(decoder.decode(zip["xl/sharedStrings.xml"])) : [], table = parseSheet(decoder.decode(sheet), shared), meta3 = metaMap(parseSheet(decoder.decode(metaSheet), shared)), expectedChecksum = await checksum(dataset);
  if (meta3.template_version !== VERSION2) return apiError("IMPORT_TEMPLATE_VERSION_STALE", "SCHEMA", 409, false, void 0, { expected: VERSION2, actual: meta3.template_version || null });
  if (meta3.dataset !== dataset) return apiError("IMPORT_TEMPLATE_DATASET_MISMATCH", "SCHEMA", 409, false, void 0, { expected: dataset, actual: meta3.dataset || null });
  if (meta3.schema_checksum !== expectedChecksum) return apiError("IMPORT_TEMPLATE_SCHEMA_STALE", "SCHEMA", 409, false, void 0, { expected: expectedChecksum, actual: meta3.schema_checksum || null });
  if (!table.length) return apiError("IMPORT_EMPTY", "VALIDATION", 400);
  if (table.length > 10001) return apiError("IMPORT_TOO_LARGE", "VALIDATION", 413);
  const spec = SPECS[dataset], headers = (table[0] ?? []).map((x2) => x2.trim());
  if (headers.length !== spec.headers.length || headers.some((h, i2) => h !== spec.headers[i2])) return apiError("IMPORT_HEADERS_MISMATCH", "SCHEMA", 409, false, void 0, { expected: spec.headers, actual: headers });
  const rows2 = [];
  for (const values of table.slice(1)) {
    const row = {};
    let any = false;
    for (let i2 = 0; i2 < spec.headers.length; i2++) {
      const v = (values[i2] ?? "").trim();
      row[spec.headers[i2]] = v;
      if (v) any = true;
    }
    if (any) rows2.push(row);
  }
  return json({ ok: true, dataset, template_version: VERSION2, schema_checksum: expectedChecksum, headers: spec.headers, row_count: rows2.length, rows: rows2 });
}
__name(importParseXlsx, "importParseXlsx");

// src/recovery.ts
async function reconciliationLocked(db) {
  const r = await db.prepare("SELECT value FROM system_meta WHERE key='m2_reconciling'").first();
  return r?.value === "1";
}
__name(reconciliationLocked, "reconciliationLocked");
function parseEnvelope(raw) {
  const x2 = JSON.parse(raw);
  if (!x2.action || !x2.business_date || !x2.actor || !x2.role || !x2.payload_json) throw new Error("FALLBACK_EVENT_SHAPE_INVALID");
  if (!["enter", "exit", "resource_change", "labor_start", "labor_finish"].includes(x2.action)) throw new Error("FALLBACK_ACTION_INVALID");
  if (!["SUPERADMIN", "ADMIN", "USER"].includes(x2.role)) throw new Error("FALLBACK_ROLE_INVALID");
  return x2;
}
__name(parseEnvelope, "parseEnvelope");
async function verifyRow(row, e) {
  if (row.source_checksum_verified === 1) {
    const digest2 = await sha256Hex(row.event_json);
    if (!row.sanitized_checksum || digest2 !== row.sanitized_checksum) throw new Error(`FALLBACK_SANITIZED_CHECKSUM_MISMATCH:${row.event_id}`);
    return;
  }
  const raw = [row.event_id, row.authority_epoch, row.authority_seq, row.service_generation, e.action, e.business_date, e.actor, e.role, e.device_id || "", e.occurred_at || "", e.payload_json].join("|");
  const digest = await sha256Hex(raw);
  if (digest !== row.checksum) throw new Error(`FALLBACK_CHECKSUM_MISMATCH:${row.event_id}`);
}
__name(verifyRow, "verifyRow");
async function setLock(db, value) {
  await db.prepare("INSERT INTO system_meta(key,value,updated_at) VALUES('m2_reconciling',?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at").bind(value ? "1" : "0", nowIso()).run();
}
__name(setLock, "setLock");
async function loadInbox(db, epoch) {
  const rows2 = (await db.prepare("SELECT event_id,authority_epoch,authority_seq,service_generation,event_json,checksum,ingest_status,source_checksum_verified,sanitized_checksum FROM fallback_event_inbox WHERE authority_epoch=?1 ORDER BY authority_seq").bind(epoch).all()).results ?? [];
  if (!rows2.length) throw new Error("FAILBACK_INBOX_EMPTY");
  for (let i2 = 0; i2 < rows2.length; i2++) {
    if (rows2[i2].authority_seq !== i2 + 1) throw new Error(`FAILBACK_SEQUENCE_GAP:${i2 + 1}`);
  }
  const generation = rows2[0].service_generation;
  if (rows2.some((r) => r.service_generation !== generation)) throw new Error("FAILBACK_GENERATION_MIXED");
  return rows2;
}
__name(loadInbox, "loadInbox");
async function replayRow(db, env, row) {
  const e = parseEnvelope(row.event_json);
  await verifyRow(row, e);
  await ensureCurrentBangkokBusinessDate(db, e.business_date);
  const payload3 = JSON.parse(e.payload_json);
  payload3.timestamp = e.occurred_at;
  payload3._device_id = e.device_id;
  const auth4 = { login_id: e.actor, role: e.role, display_name: e.actor, device_id: e.device_id || "gas-fallback", session_id: "M2_FALLBACK_REPLAY", verifier_hash: "M2_FALLBACK_REPLAY" };
  const mutation = { action: e.action, payload: payload3, event_id: row.event_id, business_date: e.business_date, device_id: e.device_id || "gas-fallback" };
  const result = await commitLegacyMutation(db, env, auth4, mutation), event = result.event;
  if (event.authority_epoch !== row.authority_epoch || event.authority_seq !== row.authority_seq) throw new Error(`FAILBACK_SEQUENCE_DIVERGENCE:${row.event_id}:${event.authority_epoch}/${event.authority_seq}`);
  await db.prepare("UPDATE fallback_event_inbox SET ingest_status='APPLIED',applied_at=?1,last_error=NULL WHERE event_id=?2").bind(nowIso(), row.event_id).run();
}
__name(replayRow, "replayRow");
async function recordAlreadyReflectedEnter(db, row) {
  const e = parseEnvelope(row.event_json);
  if (e.action !== "enter") return false;
  const cur = await db.prepare(`WITH f AS (
    SELECT json_extract(event_json,'$.business_date') d,
      json_extract(json_extract(event_json,'$.payload_json'),'$.mnv') mnv,
      COALESCE(json_extract(json_extract(event_json,'$.payload_json'),'$.shift'),'') shift,
      CASE WHEN UPPER(TRIM(COALESCE(json_extract(json_extract(event_json,'$.payload_json'),'$.work_choice'),'')))='PICK' THEN 'PICK'
           WHEN UPPER(TRIM(COALESCE(json_extract(json_extract(event_json,'$.payload_json'),'$.work_choice'),'')))='PACK' THEN 'PACK' ELSE 'KHONG' END work_choice,
      COALESCE(json_extract(json_extract(event_json,'$.payload_json'),'$.pda_serial'),json_extract(json_extract(event_json,'$.payload_json'),'$.pda'),'') pda_serial,
      COALESCE(json_extract(json_extract(event_json,'$.payload_json'),'$.user_pick'),json_extract(json_extract(event_json,'$.payload_json'),'$.userPick'),'') user_pick,
      COALESCE(json_extract(json_extract(event_json,'$.payload_json'),'$.pack_table'),json_extract(json_extract(event_json,'$.payload_json'),'$.packTable'),'') pack_table,
      COALESCE(json_extract(json_extract(event_json,'$.payload_json'),'$.user_pack'),json_extract(json_extract(event_json,'$.payload_json'),'$.userPack'),'') user_pack
    FROM fallback_event_inbox WHERE event_id=?1 AND authority_epoch=?2 AND authority_seq=?3
  ) SELECT f.mnv,s.session_id,s.state,s.version,
      CASE WHEN s.shift=f.shift AND s.work_choice=f.work_choice AND COALESCE(s.pda_serial,'')=f.pda_serial AND COALESCE(s.user_pick,'')=f.user_pick AND COALESCE(s.pack_table,'')=f.pack_table AND COALESCE(s.user_pack,'')=f.user_pack THEN 1 ELSE 0 END semantic_match
    FROM f LEFT JOIN attendance_sessions s ON s.business_date=f.d AND s.mnv=f.mnv`).bind(row.event_id, row.authority_epoch, row.authority_seq).first();
  if (!cur || !cur.session_id || cur.state !== "ACTIVE" || Number(cur.semantic_match) !== 1) return false;
  const a = await currentAuthority(db);
  if (a.authority_epoch !== row.authority_epoch || a.authority_seq !== row.authority_seq - 1) throw new Error(`FALLBACK_REFLECTED_SEQ_STATE_INVALID:${a.authority_epoch}/${a.authority_seq}:${row.authority_seq}`);
  const committed = nowIso(), payload3 = sanitizeSensitive({ original_action: e.action, mnv: cur.mnv, resolution: "ALREADY_REFLECTED_NOOP", source: "GOOGLE_FALLBACK" }), v = Number(cur.version ?? 0);
  const base = { event_id: row.event_id, event_type: "FALLBACK_RECONCILED_DUPLICATE", entity_type: "ATTENDANCE_SESSION", entity_id: cur.session_id, business_date: e.business_date, authority_epoch: row.authority_epoch, authority_seq: row.authority_seq, service_generation: row.service_generation, base_version: v, new_version: v, actor_id: e.actor, actor_role: e.role, device_id: e.device_id || "gas-fallback", occurred_at: e.occurred_at || committed, committed_at: committed, payload_json: JSON.stringify(payload3), idempotency_key: `fallback-reconciled:${row.event_id}`, origin: "GOOGLE_FALLBACK_RECONCILED", schema_version: 1 };
  const checksum2 = await sha256Hex(JSON.stringify(base));
  await db.batch([
    db.prepare("UPDATE authority_state SET authority_seq=?1,updated_at=?2 WHERE singleton_id=1 AND authority_epoch=?3 AND authority_seq=?4").bind(row.authority_seq, committed, row.authority_epoch, row.authority_seq - 1),
    db.prepare(`INSERT INTO events(event_id,event_type,entity_type,entity_id,business_date,authority_epoch,authority_seq,service_generation,base_version,new_version,actor_id,actor_role,device_id,occurred_at,committed_at,payload_json,idempotency_key,origin,schema_version,checksum) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,?20)`).bind(base.event_id, base.event_type, base.entity_type, base.entity_id, base.business_date, base.authority_epoch, base.authority_seq, base.service_generation, base.base_version, base.new_version, base.actor_id, base.actor_role, base.device_id, base.occurred_at, base.committed_at, base.payload_json, base.idempotency_key, base.origin, base.schema_version, checksum2),
    db.prepare("INSERT INTO mutation_assertions(event_id,ok) VALUES(?1,1)").bind(row.event_id),
    db.prepare("UPDATE fallback_event_inbox SET ingest_status='APPLIED',applied_at=?1,last_error=NULL WHERE event_id=?2").bind(committed, row.event_id)
  ]);
  return true;
}
__name(recordAlreadyReflectedEnter, "recordAlreadyReflectedEnter");
async function failbackFromFallbackInbox(db, env, input) {
  if (input.confirmation !== "OWNER_LOCKED_M2_FAILBACK") throw new Error("FAILBACK_CONFIRMATION_REQUIRED");
  const before = await currentAuthority(db);
  if (before.authority_epoch !== input.expected_service_epoch) throw new Error(`FAILBACK_SERVICE_EPOCH_STALE:${before.authority_epoch}`);
  if (input.fallback_epoch !== before.authority_epoch + 1) throw new Error(`FAILBACK_EPOCH_GAP:${input.fallback_epoch}`);
  const rows2 = await loadInbox(db, input.fallback_epoch), generation = rows2[0].service_generation;
  const recoveryId = crypto.randomUUID(), started = nowIso();
  await db.prepare("INSERT INTO recovery_runs(recovery_id,recovery_type,from_generation,to_generation,source_authority_epoch,source_authority_seq,target_authority_epoch,status,started_at,validation_json) VALUES(?1,'FAILBACK',?2,?3,?4,?5,?6,'RUNNING',?7,'{}')").bind(recoveryId, generation, env.SERVICE_GENERATION, input.fallback_epoch, rows2.length, input.fallback_epoch + 1, started).run();
  await setLock(db, true);
  try {
    for (const row of rows2) {
      const e = parseEnvelope(row.event_json);
      await verifyRow(row, e);
      await ensureCurrentBangkokBusinessDate(db, e.business_date);
    }
    await db.prepare("UPDATE authority_state SET authority_epoch=?1,authority_seq=0,mode='SERVICE_PRIMARY',service_generation=?2,updated_at=?3 WHERE singleton_id=1 AND authority_epoch=?4").bind(input.fallback_epoch, generation, nowIso(), before.authority_epoch).run();
    await db.prepare("INSERT INTO authority_transitions(from_epoch,to_epoch,from_mode,to_mode,from_generation,to_generation,reason,initiated_by,checkpoint_epoch,checkpoint_seq,validation_json,created_at) VALUES(?1,?2,?3,'RECONCILING',?4,?5,'FAILBACK_REPLAY',?6,?1,?7,?8,?9)").bind(before.authority_epoch, input.fallback_epoch, before.mode, before.service_generation, generation, String(input.initiated_by || "M2_RECOVERY").slice(0, 180), before.authority_seq, JSON.stringify({ public_write_lock: true, inbox_count: rows2.length }), nowIso()).run();
    let applied = 0;
    for (const row of rows2) {
      if (row.ingest_status === "APPLIED") {
        applied++;
        continue;
      }
      await replayRow(db, env, row);
      applied++;
    }
    const authority2 = await currentAuthority(db);
    if (authority2.authority_epoch !== input.fallback_epoch || authority2.authority_seq !== rows2.length) throw new Error(`FAILBACK_CHECKPOINT_DIVERGENCE:${authority2.authority_epoch}/${authority2.authority_seq}`);
    const eventCount = await db.prepare("SELECT COUNT(*) n FROM events WHERE authority_epoch=?1").bind(input.fallback_epoch).first();
    if ((eventCount?.n ?? 0) < rows2.length) throw new Error("FAILBACK_EVENT_COUNT_MISMATCH");
    const at = nowIso();
    await db.prepare("UPDATE authority_state SET authority_epoch=?1,authority_seq=0,mode='SERVICE_PRIMARY',service_generation=?2,updated_at=?3 WHERE singleton_id=1 AND authority_epoch=?4 AND authority_seq=?5").bind(input.fallback_epoch + 1, env.SERVICE_GENERATION, at, input.fallback_epoch, rows2.length).run();
    await db.prepare("INSERT INTO authority_transitions(from_epoch,to_epoch,from_mode,to_mode,from_generation,to_generation,reason,initiated_by,checkpoint_epoch,checkpoint_seq,validation_json,created_at) VALUES(?1,?2,'RECONCILING','SERVICE_PRIMARY',?3,?4,'FAILBACK_COMPLETE',?5,?1,?6,?7,?8)").bind(input.fallback_epoch, input.fallback_epoch + 1, generation, env.SERVICE_GENERATION, String(input.initiated_by || "M2_RECOVERY").slice(0, 180), rows2.length, JSON.stringify({ applied, event_count: eventCount?.n ?? 0, checksum_verified: true }), at).run();
    await setLock(db, false);
    const after2 = await currentAuthority(db), validation = { inbox_count: rows2.length, applied, event_count: eventCount?.n ?? 0, checksum_verified: true, contiguous_sequence: true, final_epoch: after2.authority_epoch };
    await db.prepare("UPDATE recovery_runs SET status='COMPLETE',completed_at=?1,validation_json=?2 WHERE recovery_id=?3").bind(at, JSON.stringify(validation), recoveryId).run();
    return { ok: true, recovery_id: recoveryId, validation, authority: after2 };
  } catch (e) {
    await db.prepare("UPDATE authority_state SET mode='RECONCILING',updated_at=?1 WHERE singleton_id=1").bind(nowIso()).run().catch(() => void 0);
    await db.prepare("UPDATE recovery_runs SET status='FAILED',completed_at=?1,error=?2 WHERE recovery_id=?3").bind(nowIso(), String(e).slice(0, 1e3), recoveryId).run().catch(() => void 0);
    throw e;
  }
}
__name(failbackFromFallbackInbox, "failbackFromFallbackInbox");

// src/recovery_resume_compat.ts
function parseEnvelope2(raw) {
  const x2 = JSON.parse(raw);
  if (!x2.action || !x2.business_date || !x2.actor || !x2.role || !x2.payload_json) throw new Error("FALLBACK_EVENT_SHAPE_INVALID");
  if (!["enter", "exit", "resource_change", "labor_start", "labor_finish"].includes(x2.action)) throw new Error("FALLBACK_ACTION_INVALID");
  if (!["SUPERADMIN", "ADMIN", "USER"].includes(x2.role)) throw new Error("FALLBACK_ROLE_INVALID");
  return x2;
}
__name(parseEnvelope2, "parseEnvelope");
async function verifyRow2(row, e) {
  if (row.source_checksum_verified === 1) {
    const digest2 = await sha256Hex(row.event_json);
    if (!row.sanitized_checksum || digest2 !== row.sanitized_checksum) throw new Error(`FALLBACK_SANITIZED_CHECKSUM_MISMATCH:${row.event_id}`);
    return;
  }
  const raw = [row.event_id, row.authority_epoch, row.authority_seq, row.service_generation, e.action, e.business_date, e.actor, e.role, e.device_id || "", e.occurred_at || "", e.payload_json].join("|");
  const digest = await sha256Hex(raw);
  if (digest !== row.checksum) throw new Error(`FALLBACK_CHECKSUM_MISMATCH:${row.event_id}`);
}
__name(verifyRow2, "verifyRow");
async function loadInbox2(db, epoch) {
  const rows2 = (await db.prepare("SELECT event_id,authority_epoch,authority_seq,service_generation,event_json,checksum,ingest_status,source_checksum_verified,sanitized_checksum FROM fallback_event_inbox WHERE authority_epoch=?1 ORDER BY authority_seq").bind(epoch).all()).results ?? [];
  if (!rows2.length) throw new Error("FAILBACK_INBOX_EMPTY");
  for (let i2 = 0; i2 < rows2.length; i2++) if (rows2[i2].authority_seq !== i2 + 1) throw new Error(`FAILBACK_SEQUENCE_GAP:${i2 + 1}`);
  const generation = rows2[0].service_generation;
  if (rows2.some((r) => r.service_generation !== generation)) throw new Error("FAILBACK_GENERATION_MIXED");
  return rows2;
}
__name(loadInbox2, "loadInbox");
async function locked(db) {
  const r = await db.prepare("SELECT value FROM system_meta WHERE key='m2_reconciling'").first();
  return r?.value === "1";
}
__name(locked, "locked");
async function setLock2(db, value) {
  await db.prepare("INSERT INTO system_meta(key,value,updated_at) VALUES('m2_reconciling',?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at").bind(value ? "1" : "0", nowIso()).run();
}
__name(setLock2, "setLock");
async function activeAttendanceShift(db, businessDate2, mnv) {
  if (!mnv) return "";
  const row = await db.prepare("SELECT shift FROM attendance_sessions WHERE business_date=?1 AND mnv=?2 AND state='ACTIVE'").bind(businessDate2, mnv).first();
  return String(row?.shift || "").trim();
}
__name(activeAttendanceShift, "activeAttendanceShift");
async function hydrateLegacyPackUser(db, e, payload3) {
  if (e.action !== "enter" && e.action !== "resource_change") return;
  const table = String(payload3.pack_table || "").trim(), existing2 = String(payload3.user_pack || "").trim();
  if (!table || existing2) return;
  const work = String(payload3.work_choice || "").trim();
  if (work && work !== "PACK") return;
  let shift = String(payload3.shift || "").trim();
  if (!shift) shift = await activeAttendanceShift(db, e.business_date, String(payload3.mnv || "").trim());
  if (!shift) throw new Error(`FAILBACK_PACK_SHIFT_MISSING:${table}`);
  const rows2 = (await db.prepare("SELECT user_pack FROM resource_pack_map WHERE pack_table=?1 AND shift=?2 AND available=1 ORDER BY user_pack LIMIT 2").bind(table, shift).all()).results ?? [];
  if (rows2.length === 0) throw new Error(`FAILBACK_PACK_USER_MISSING:${table}:${shift}`);
  if (rows2.length !== 1) throw new Error(`FAILBACK_PACK_USER_AMBIGUOUS:${table}:${shift}:${rows2.length}`);
  const user = String(rows2[0].user_pack || "").trim();
  if (!user) throw new Error(`FAILBACK_PACK_USER_EMPTY:${table}:${shift}`);
  payload3.user_pack = user;
}
__name(hydrateLegacyPackUser, "hydrateLegacyPackUser");
async function hydrateLegacyLaborShift(db, e, payload3) {
  if (e.action !== "labor_start" || String(payload3.shift || "").trim()) return;
  const shift = await activeAttendanceShift(db, e.business_date, String(payload3.mnv || "").trim());
  if (!shift) throw new Error(`FAILBACK_LABOR_SHIFT_MISSING:${e.business_date}`);
  payload3.shift = shift;
}
__name(hydrateLegacyLaborShift, "hydrateLegacyLaborShift");
async function replayRow2(db, env, row) {
  const e = parseEnvelope2(row.event_json);
  await verifyRow2(row, e);
  await ensureCurrentBangkokBusinessDate(db, e.business_date);
  const payload3 = JSON.parse(e.payload_json);
  await hydrateLegacyPackUser(db, e, payload3);
  await hydrateLegacyLaborShift(db, e, payload3);
  payload3.timestamp = e.occurred_at;
  payload3._device_id = e.device_id;
  const auth4 = { login_id: e.actor, role: e.role, display_name: e.actor, device_id: e.device_id || "gas-fallback", session_id: "M2_FALLBACK_REPLAY", verifier_hash: "M2_FALLBACK_REPLAY" };
  const mutation = { action: e.action, payload: payload3, event_id: row.event_id, business_date: e.business_date, device_id: e.device_id || "gas-fallback" };
  const result = await commitLegacyMutation(db, env, auth4, mutation), event = result.event;
  if (event.authority_epoch !== row.authority_epoch || event.authority_seq !== row.authority_seq) throw new Error(`FAILBACK_SEQUENCE_DIVERGENCE:${row.event_id}:${event.authority_epoch}/${event.authority_seq}`);
  await db.prepare("UPDATE fallback_event_inbox SET ingest_status='APPLIED',applied_at=?1,last_error=NULL WHERE event_id=?2").bind(nowIso(), row.event_id).run();
}
__name(replayRow2, "replayRow");
async function resumeFailbackWithLegacyCompat(db, env, input) {
  if (input.confirmation !== "OWNER_LOCKED_M2_FAILBACK_RESUME") throw new Error("FAILBACK_RESUME_CONFIRMATION_REQUIRED");
  const before = await currentAuthority(db);
  if (before.mode !== "RECONCILING" || before.authority_epoch !== input.fallback_epoch) throw new Error(`FAILBACK_RESUME_STATE_INVALID:${before.mode}:${before.authority_epoch}`);
  if (!await locked(db)) throw new Error("FAILBACK_RESUME_LOCK_MISSING");
  const rows2 = await loadInbox2(db, input.fallback_epoch), generation = rows2[0].service_generation;
  if (before.authority_seq < 0 || before.authority_seq > rows2.length) throw new Error(`FAILBACK_RESUME_SEQ_INVALID:${before.authority_seq}`);
  for (const row of rows2) {
    const e = parseEnvelope2(row.event_json);
    await verifyRow2(row, e);
    await ensureCurrentBangkokBusinessDate(db, e.business_date);
  }
  for (let seq = 1; seq <= before.authority_seq; seq++) {
    const row = rows2[seq - 1];
    const ev = await db.prepare("SELECT event_id FROM events WHERE authority_epoch=?1 AND authority_seq=?2").bind(input.fallback_epoch, seq).first();
    if (!ev || ev.event_id !== row.event_id) throw new Error(`FAILBACK_RESUME_EVENT_PREFIX_MISMATCH:${seq}`);
    if (row.ingest_status !== "APPLIED") await db.prepare("UPDATE fallback_event_inbox SET ingest_status='APPLIED',applied_at=COALESCE(applied_at,?1),last_error=NULL WHERE event_id=?2").bind(nowIso(), row.event_id).run();
  }
  const recoveryId = crypto.randomUUID(), started = nowIso();
  await db.prepare("INSERT INTO recovery_runs(recovery_id,recovery_type,from_generation,to_generation,source_authority_epoch,source_authority_seq,target_authority_epoch,status,started_at,validation_json) VALUES(?1,'FAILBACK',?2,?3,?4,?5,?6,'RUNNING',?7,?8)").bind(recoveryId, generation, env.SERVICE_GENERATION, input.fallback_epoch, rows2.length, input.fallback_epoch + 1, started, JSON.stringify({ resume: true, legacy_pack_compat: true, legacy_labor_shift_compat: true, resume_from_seq: before.authority_seq })).run();
  try {
    await db.prepare("UPDATE authority_state SET mode='SERVICE_PRIMARY',service_generation=?1,updated_at=?2 WHERE singleton_id=1 AND authority_epoch=?3 AND authority_seq=?4 AND mode='RECONCILING'").bind(generation, nowIso(), input.fallback_epoch, before.authority_seq).run();
    let applied = before.authority_seq;
    for (let i2 = before.authority_seq; i2 < rows2.length; i2++) {
      const row = rows2[i2];
      if (await recordAlreadyReflectedEnter(db, row)) {
        applied++;
        continue;
      }
      await replayRow2(db, env, row);
      applied++;
    }
    const checkpoint = await currentAuthority(db);
    if (checkpoint.authority_epoch !== input.fallback_epoch || checkpoint.authority_seq !== rows2.length) throw new Error(`FAILBACK_RESUME_CHECKPOINT_DIVERGENCE:${checkpoint.authority_epoch}/${checkpoint.authority_seq}`);
    const eventCount = await db.prepare("SELECT COUNT(*) n FROM events WHERE authority_epoch=?1").bind(input.fallback_epoch).first();
    if ((eventCount?.n ?? 0) < rows2.length) throw new Error("FAILBACK_RESUME_EVENT_COUNT_MISMATCH");
    const at = nowIso();
    await db.prepare("UPDATE authority_state SET authority_epoch=?1,authority_seq=0,mode='SERVICE_PRIMARY',service_generation=?2,updated_at=?3 WHERE singleton_id=1 AND authority_epoch=?4 AND authority_seq=?5").bind(input.fallback_epoch + 1, env.SERVICE_GENERATION, at, input.fallback_epoch, rows2.length).run();
    await db.prepare("INSERT INTO authority_transitions(from_epoch,to_epoch,from_mode,to_mode,from_generation,to_generation,reason,initiated_by,checkpoint_epoch,checkpoint_seq,validation_json,created_at) VALUES(?1,?2,'RECONCILING','SERVICE_PRIMARY',?3,?4,'FAILBACK_RESUME_COMPLETE',?5,?1,?6,?7,?8)").bind(input.fallback_epoch, input.fallback_epoch + 1, generation, env.SERVICE_GENERATION, String(input.initiated_by || "M2_RECOVERY_RESUME").slice(0, 180), rows2.length, JSON.stringify({ resume: true, legacy_pack_compat: true, legacy_labor_shift_compat: true, applied, event_count: eventCount?.n ?? 0, checksum_verified: true }), at).run();
    await setLock2(db, false);
    const after2 = await currentAuthority(db), validation = { resume: true, legacy_pack_compat: true, legacy_labor_shift_compat: true, inbox_count: rows2.length, applied, event_count: eventCount?.n ?? 0, checksum_verified: true, contiguous_sequence: true, final_epoch: after2.authority_epoch };
    await db.prepare("UPDATE recovery_runs SET status='COMPLETE',completed_at=?1,validation_json=?2 WHERE recovery_id=?3").bind(at, JSON.stringify(validation), recoveryId).run();
    return { ok: true, recovery_id: recoveryId, validation, authority: after2 };
  } catch (e) {
    await db.prepare("UPDATE authority_state SET mode='RECONCILING',updated_at=?1 WHERE singleton_id=1").bind(nowIso()).run().catch(() => void 0);
    await db.prepare("UPDATE recovery_runs SET status='FAILED',completed_at=?1,error=?2 WHERE recovery_id=?3").bind(nowIso(), String(e).slice(0, 1e3), recoveryId).run().catch(() => void 0);
    throw e;
  }
}
__name(resumeFailbackWithLegacyCompat, "resumeFailbackWithLegacyCompat");

// src/entry.ts
async function m2ClientSyncStatus(db) {
  const q4 = `WITH recent AS (
      SELECT business_date,sequence_no FROM business_dates ORDER BY sequence_no DESC LIMIT 7
    ), rev AS (
      SELECT recent.business_date,recent.sequence_no,MAX(COALESCE(events.authority_seq,0)) AS max_seq
      FROM recent LEFT JOIN events ON events.business_date=recent.business_date
      GROUP BY recent.business_date,recent.sequence_no
    ), meta AS (
      SELECT
        (SELECT business_date FROM business_dates ORDER BY sequence_no ASC LIMIT 1) AS server_retention_floor,
        COALESCE((SELECT pending_count FROM replication_status WHERE singleton_id=1),0) AS projection_pending,
        COALESCE((SELECT MAX(source_row) FROM employees),0) AS master_revision
    )
    SELECT rev.business_date,rev.sequence_no,rev.max_seq,
      a.authority_epoch,a.authority_seq,a.mode,a.scope,a.service_generation,a.updated_at,
      meta.server_retention_floor,meta.projection_pending,meta.master_revision
    FROM rev CROSS JOIN authority_state a CROSS JOIN meta
    WHERE a.singleton_id=1 ORDER BY rev.sequence_no DESC`;
  const result = await db.prepare(q4).all(), rows2 = result.results ?? [], first = rows2[0];
  if (!first) throw new Error("SYNC_STATUS_EMPTY");
  const dayRevisions = {};
  for (const r of rows2) dayRevisions[r.business_date] = Math.max(1, Number(r.max_seq ?? 0));
  const authority2 = { authority_epoch: first.authority_epoch, authority_seq: first.authority_seq, mode: first.mode, scope: first.scope, service_generation: first.service_generation, updated_at: first.updated_at };
  return {
    ok: true,
    business_date: first.business_date,
    server_seq: first.authority_seq,
    master_revision: Number(first.master_revision ?? 0),
    last_event_at: first.updated_at,
    projection_pending: Number(first.projection_pending ?? 0),
    mode: "APP_SERVICE_D1",
    sync_engine: "M2_SERVICE_BUSINESS_WINDOW_7",
    retention_floor: rows2[rows2.length - 1]?.business_date ?? first.business_date,
    server_retention_floor: first.server_retention_floor ?? rows2[rows2.length - 1]?.business_date ?? first.business_date,
    retention_epoch: first.authority_epoch,
    day_revisions: dayRevisions,
    authority: authority2,
    service_generation: first.service_generation,
    service_telemetry: { db_duration_ms: result.meta.duration, db_rows_read: result.meta.rows_read, served_by_region: result.meta.served_by_region ?? "", served_by_primary: result.meta.served_by_primary ?? false }
  };
}
__name(m2ClientSyncStatus, "m2ClientSyncStatus");
async function legacySync(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  const body = await readJsonBody(request), action = String(body.action || "");
  if (action === "sync_status") return json(await m2ClientSyncStatus(env.DB));
  if (action === "sync_day") return json({ ok: true, sync_engine: "M2_SERVICE_BUSINESS_WINDOW_7", day: await compatDay(env.DB, String(body.business_date || "")) });
  if (action === "sync_bootstrap") return json(await compatBootstrap(env.DB, body.dates));
  return apiError("LEGACY_SYNC_ACTION_UNSUPPORTED", "VALIDATION", 400);
}
__name(legacySync, "legacySync");
async function recoveryFailback(request, env) {
  if (!await internalAuthorized(request, env)) return apiError("INTERNAL_UNAUTHORIZED", "AUTH", 401);
  const input = await readJsonBody(request);
  try {
    return json(await failbackFromFallbackInbox(env.DB, env, input));
  } catch (e) {
    console.log(JSON.stringify({ level: "error", kind: "failback_failed", error: String(e) }));
    return apiError("FAILBACK_FAILED", "INTEGRITY", 409, false, String(e).slice(0, 500));
  }
}
__name(recoveryFailback, "recoveryFailback");
async function recoveryResume(request, env) {
  if (!await internalAuthorized(request, env)) return apiError("INTERNAL_UNAUTHORIZED", "AUTH", 401);
  const input = await readJsonBody(request);
  try {
    return json(await resumeFailbackWithLegacyCompat(env.DB, env, input));
  } catch (e) {
    console.log(JSON.stringify({ level: "error", kind: "failback_resume_failed", error: String(e) }));
    return apiError("FAILBACK_RESUME_FAILED", "INTEGRITY", 409, false, String(e).slice(0, 500));
  }
}
__name(recoveryResume, "recoveryResume");
async function adminAudit(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  const input = await readJsonBody(request);
  try {
    const result = await commitAdminAudit(env.DB, auth4, input);
    return json({ ok: true, duplicate: result.duplicate, event: result.event }, result.duplicate ? 200 : 201);
  } catch (e) {
    if (e instanceof Error) console.log(JSON.stringify({ level: "warn", kind: "admin_audit_failed", error: String(e).slice(0, 240) }));
    throw e;
  }
}
__name(adminAudit, "adminAudit");
async function drRebuildGoogle(request, env) {
  if (!await internalAuthorized(request, env)) return apiError("INTERNAL_UNAUTHORIZED", "AUTH", 401);
  try {
    return json(await rebuildGoogleStagingFromD1(env.DB, env));
  } catch (e) {
    console.log(JSON.stringify({ level: "error", kind: "dr_google_rebuild_failed", error: String(e) }));
    return apiError("DR_GOOGLE_REBUILD_FAILED", "INTEGRITY", 409, false, String(e).slice(0, 500));
  }
}
__name(drRebuildGoogle, "drRebuildGoogle");
async function resumableBootstrap(request, env, action) {
  if (!await internalAuthorized(request, env)) return apiError("INTERNAL_UNAUTHORIZED", "AUTH", 401);
  try {
    if (action === "start") return json(await bootstrapGoogleStart(env.DB, env));
    const body = await readJsonBody(request), runId = String(body.run_id || "").trim();
    if (action === "step") {
      if (!runId) return apiError("BOOTSTRAP_RUN_ID_REQUIRED", "VALIDATION", 400);
      const status = await bootstrapGoogleStatus(env.DB, runId);
      if (status.state?.phase === "RESOURCES") return json(await bootstrapResourceProjectionStep(env.DB, runId));
      return json(await bootstrapGoogleStep(env.DB, env, runId));
    }
    return json(await bootstrapGoogleStatus(env.DB, runId || void 0));
  } catch (e) {
    console.log(JSON.stringify({ level: "error", kind: "resumable_bootstrap_failed", action, error: String(e) }));
    return apiError("BOOTSTRAP_RESUMABLE_FAILED", "INTERNAL", 500, true, String(e).slice(0, 500));
  }
}
__name(resumableBootstrap, "resumableBootstrap");
async function gasBridgeAuthorized2(request, env) {
  const supplied = request.headers.get("x-gas-bridge-secret") || "";
  if (!supplied) return false;
  return constantTimeEqual(await sha256Hex(supplied), await sha256Hex(env.GAS_BRIDGE_SHARED_SECRET));
}
__name(gasBridgeAuthorized2, "gasBridgeAuthorized");
async function fallbackIngestFenced(request, env) {
  if (!await gasBridgeAuthorized2(request, env)) return apiError("GAS_BRIDGE_UNAUTHORIZED", "AUTH", 401);
  const body = await readJsonBody(request);
  const eventId = String(body.event_id || "").trim(), generation = String(body.service_generation || "").trim(), checksum2 = String(body.checksum || "").trim();
  if (!eventId || !generation || !checksum2 || !Number.isInteger(body.authority_epoch) || !Number.isInteger(body.authority_seq) || body.authority_seq < 1 || !body.event || typeof body.event !== "object") return apiError("FALLBACK_INGEST_INVALID", "VALIDATION", 400);
  const e = body.event, sourceRaw = [eventId, body.authority_epoch, body.authority_seq, generation, String(e.action || ""), String(e.business_date || ""), String(e.actor || ""), String(e.role || ""), String(e.device_id || ""), String(e.occurred_at || ""), String(e.payload_json || "")].join("|");
  if (await sha256Hex(sourceRaw) !== checksum2) return apiError("FALLBACK_SOURCE_CHECKSUM_MISMATCH", "INTEGRITY", 409);
  let cleanPayload = {};
  try {
    cleanPayload = sanitizeSensitive(JSON.parse(String(e.payload_json || "{}")));
  } catch {
    cleanPayload = {};
  }
  const cleanEvent = { ...e, payload_json: JSON.stringify(cleanPayload) }, cleanJson = JSON.stringify(cleanEvent), sanitizedChecksum = await sha256Hex(cleanJson);
  const a = await currentAuthority(env.DB), futureFallback = a.mode === "SERVICE_PRIMARY" && body.authority_epoch === a.authority_epoch + 1, currentFallback = ["GOOGLE_FALLBACK", "RECONCILING"].includes(a.mode) && body.authority_epoch === a.authority_epoch;
  if (!futureFallback && !currentFallback) return apiError("FALLBACK_EPOCH_NOT_ACCEPTABLE", "CONFLICT", 409, false, void 0, { current_epoch: a.authority_epoch, current_mode: a.mode, incoming_epoch: body.authority_epoch });
  const existing2 = await env.DB.prepare("SELECT authority_epoch,authority_seq,checksum FROM fallback_event_inbox WHERE event_id=?1").bind(eventId).first();
  if (existing2) {
    if (existing2.authority_epoch !== body.authority_epoch || existing2.authority_seq !== body.authority_seq || existing2.checksum !== checksum2) return apiError("FALLBACK_EVENT_ID_COLLISION", "INTEGRITY", 409);
    return json({ ok: true, event_id: eventId, duplicate: true, authority_epoch: body.authority_epoch, authority_seq: body.authority_seq });
  }
  const seqCollision = await env.DB.prepare("SELECT event_id,checksum FROM fallback_event_inbox WHERE authority_epoch=?1 AND authority_seq=?2").bind(body.authority_epoch, body.authority_seq).first();
  if (seqCollision) return apiError("FALLBACK_SEQUENCE_COLLISION", "INTEGRITY", 409, false, void 0, { existing_event_id: seqCollision.event_id, incoming_event_id: eventId, authority_epoch: body.authority_epoch, authority_seq: body.authority_seq });
  await env.DB.prepare(`INSERT INTO fallback_event_inbox(event_id,authority_epoch,authority_seq,service_generation,event_json,checksum,source,ingest_status,received_at,source_checksum_verified,sanitized_checksum)
    VALUES(?1,?2,?3,?4,?5,?6,'GOOGLE_FALLBACK','PENDING',?7,1,?8)`).bind(eventId, body.authority_epoch, body.authority_seq, generation, cleanJson, checksum2, nowIso(), sanitizedChecksum).run();
  return json({ ok: true, event_id: eventId, duplicate: false, staged_for_failback: true, authority_epoch: body.authority_epoch, authority_seq: body.authority_seq });
}
__name(fallbackIngestFenced, "fallbackIngestFenced");
var entry_default = {
  async fetch(request, env, _ctx) {
    const u = new URL(request.url), path = u.pathname;
    if (path === "/internal/bootstrap-google/start" && request.method === "POST") return resumableBootstrap(request, env, "start");
    if (path === "/internal/bootstrap-google/step" && request.method === "POST") return resumableBootstrap(request, env, "step");
    if (path === "/internal/bootstrap-google/status" && request.method === "POST") return resumableBootstrap(request, env, "status");
    if (path === "/internal/fallback/ingest" && request.method === "POST") return fallbackIngestFenced(request, env);
    if (path === "/internal/recovery/failback" && request.method === "POST") return recoveryFailback(request, env);
    if (path === "/internal/recovery/failback-resume" && request.method === "POST") return recoveryResume(request, env);
    if (path === "/internal/dr/rebuild-google-staging" && request.method === "POST") return drRebuildGoogle(request, env);
    if (path === "/v1/import/template" && request.method === "GET") return importTemplateXlsx(request, env);
    if (path === "/v1/import/xlsx/parse" && request.method === "POST") return importParseXlsx(request, env);
    if (path === "/v1/legacy-sync" && request.method === "POST") {
      try {
        return await legacySync(request, env);
      } catch (e) {
        console.log(JSON.stringify({ level: "error", kind: "legacy_sync_failed", error: String(e) }));
        return apiError("LEGACY_SYNC_FAILED", "INTERNAL", 500, true);
      }
    }
    if (await reconciliationLocked(env.DB)) {
      if (path === "/v1/mutations" || path === "/v1/mutations/batch" || path === "/v1/legacy-mutations" || path === "/v1/legacy-mutations/batch" || path === "/v1/admin-audit" || path === "/internal/legacy-bridge") return apiError("RECONCILING_RETRY", "CONFLICT", 409, true);
    }
    if (path === "/v1/admin-audit" && request.method === "POST") return adminAudit(request, env);
    return index_default.fetch(request, env);
  },
  async scheduled(controller, env, ctx) {
    return index_default.scheduled(controller, env, ctx);
  }
};

// src/mobile_hotfix.ts
var GAS_API_URL = "https://script.google.com/macros/s/AKfycbzbEoGfbNg6s2HnP-gUpcBJ7mMIkVBtYuQKMndb9seDV2c55lQwSUO1GZ-LtQ2CxMCauA/exec";
function parseGasToken(token3) {
  try {
    const first = token3.split(".")[0];
    if (!first) return null;
    return JSON.parse(new TextDecoder().decode(b64uDecode(first)));
  } catch {
    return null;
  }
}
__name(parseGasToken, "parseGasToken");
async function validateGasSession(gasToken, payload3) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 4500);
  try {
    const response = await fetch(GAS_API_URL, {
      method: "POST",
      headers: { "content-type": "application/json; charset=utf-8", "accept": "application/json" },
      body: JSON.stringify({ action: "m2_authority_status", _token: gasToken, _device_id: String(payload3.d || ""), _app_channel: "BETA", _app_version: "m2-session-exchange-v1" }),
      signal: controller.signal
    });
    const body = await response.json();
    return response.ok && body.ok === true ? body : null;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}
__name(validateGasSession, "validateGasSession");
async function exchangeGasSession(request, env) {
  const input = await readJsonBody(request, 64e3);
  const gasToken = String(input.gas_token || "").trim(), deviceId = String(input.device_id || "").trim().slice(0, 180);
  if (!gasToken || !deviceId) return apiError("SESSION_EXCHANGE_FIELDS_REQUIRED", "VALIDATION", 400);
  const payload3 = parseGasToken(gasToken);
  if (!payload3?.l || !payload3.r || !payload3.v || !payload3.s || !payload3.d) return apiError("GAS_SESSION_INVALID", "AUTH", 401);
  const discovery = await validateGasSession(gasToken, payload3);
  if (!discovery) return apiError("GAS_SESSION_INVALID", "AUTH", 401);
  if (String(discovery.authority_mode || "") !== "SERVICE_PRIMARY") return apiError("SERVICE_NOT_PRIMARY", "CONFLICT", 409, true);
  const account = await env.DB.prepare("SELECT login_id,role,display_name,position,email,verifier_hash,status FROM accounts WHERE login_id=?1").bind(String(payload3.l)).first();
  if (!account || account.status !== "ACTIVE" || account.role !== String(payload3.r)) return apiError("SESSION_EXCHANGE_ACCOUNT_MISMATCH", "AUTH", 401);
  const current = await env.DB.prepare("SELECT session_id,device_id FROM auth_sessions WHERE login_id=?1").bind(account.login_id).first();
  const reused = Boolean(current?.session_id && current.device_id === deviceId);
  const sessionId = reused ? String(current?.session_id) : crypto.randomUUID(), issuedAt = nowIso();
  await env.DB.prepare(`INSERT INTO auth_sessions(login_id,session_id,device_id,issued_at) VALUES(?1,?2,?3,?4)
    ON CONFLICT(login_id) DO UPDATE SET session_id=excluded.session_id,device_id=excluded.device_id,issued_at=excluded.issued_at`).bind(account.login_id, sessionId, deviceId, issuedAt).run();
  const servicePayload = { l: account.login_id, r: account.role, v: account.verifier_hash, s: sessionId, d: deviceId };
  const encoded = b64u(new TextEncoder().encode(JSON.stringify(servicePayload)));
  const sig = await hmacB64u(new TextEncoder().encode(env.SERVICE_TOKEN_SECRET), encoded);
  return json({ ok: true, token: `${encoded}.${sig}`, account: { login_id: account.login_id, role: account.role, display_name: account.display_name, position: account.position, email: account.email }, session: { issued_at: issuedAt, device_label: String(input.device_label || "").slice(0, 120), session_id: sessionId, reused }, authority: discovery.authority, authority_mode: discovery.authority_mode, service_generation: discovery.service_generation });
}
__name(exchangeGasSession, "exchangeGasSession");
async function businessDate(db) {
  const date = bangkokToday();
  await ensureCurrentBangkokBusinessDate(db, date);
  return date;
}
__name(businessDate, "businessDate");
function employeeJson(e) {
  return e ? { mnv: e.mnv, full_name: e.full_name, phone: e.phone, main_position: e.main_position, supplier: e.supplier, department: e.department, site: e.site, warehouse: e.warehouse, start_date: e.start_date, note: e.note } : null;
}
__name(employeeJson, "employeeJson");
function visibleWork(v) {
  return v === "KHONG" ? "KH\xD4NG" : v;
}
__name(visibleWork, "visibleWork");
async function resourceOptions(db, date, mnv) {
  const leaseRows = (await db.prepare("SELECT resource_type,resource_id,mnv FROM resource_leases WHERE business_date=?1").bind(date).all()).results ?? [];
  const busy = new Set(leaseRows.map((x2) => `${x2.resource_type}|${x2.resource_id}`));
  const usedRows = (await db.prepare("SELECT resource_type,resource_id,mnv FROM resource_daily_consumption WHERE business_date=?1").bind(date).all()).results ?? [];
  const used = new Set(usedRows.map((x2) => `${x2.resource_type}|${x2.resource_id}`));
  const current = await db.prepare("SELECT pda_serial,user_pick,pack_table,user_pack FROM attendance_sessions WHERE business_date=?1 AND mnv=?2 AND state='ACTIVE'").bind(date, mnv).first();
  const pdasRaw = (await db.prepare("SELECT resource_id,status_label,metadata_json FROM resources WHERE resource_type='PDA' AND available=1 ORDER BY resource_id").all()).results ?? [];
  const pdas = pdasRaw.filter((x2) => !busy.has(`PDA|${x2.resource_id}`) || x2.resource_id === current?.pda_serial).map((x2) => {
    let m = {};
    try {
      m = JSON.parse(x2.metadata_json);
    } catch {
    }
    return { serial: x2.resource_id, last5: String(m["5 s\u1ED1 cu\u1ED1i Seri"] || x2.resource_id.slice(-5)), status: x2.status_label };
  });
  const picksRaw = (await db.prepare("SELECT resource_id FROM resources WHERE resource_type='USER_PICK' AND available=1 ORDER BY resource_id").all()).results ?? [];
  const user_picks = [], user_picks_reissue = [];
  for (const x2 of picksRaw) {
    const id = x2.resource_id, isCurrent = id === current?.user_pick, isBusy = busy.has(`USER_PICK|${id}`), isUsed = used.has(`USER_PICK|${id}`);
    if (isCurrent || !isBusy && !isUsed) user_picks.push(id);
    else if (!isBusy && isUsed) user_picks_reissue.push({ id, busy: false, used_today: true, duplicate_user: true, note: "PH\xC1T L\u1EA0I USER" });
  }
  const packsRaw = (await db.prepare("SELECT pack_table,shift,user_pack FROM resource_pack_map WHERE available=1 ORDER BY pack_table,shift,user_pack").all()).results ?? [];
  const pack_tables = [], pack_tables_reissue = [];
  for (const x2 of packsRaw) {
    const exactCurrent = x2.pack_table === current?.pack_table && x2.user_pack === current?.user_pack;
    const tableBusy = busy.has(`PACK_TABLE|${x2.pack_table}`), userBusy = busy.has(`USER_PACK|${x2.user_pack}`), userUsed = used.has(`USER_PACK|${x2.user_pack}`);
    if (exactCurrent || !tableBusy && !userBusy && !userUsed) pack_tables.push({ table: x2.pack_table, shift: x2.shift, user_pack: x2.user_pack, duplicate_user: false });
    else if (!tableBusy && !userBusy && userUsed) pack_tables_reissue.push({ table: x2.pack_table, shift: x2.shift, user_pack: x2.user_pack, duplicate_user: true, used_today: true, note: "PH\xC1T L\u1EA0I USER" });
  }
  return { ok: true, business_date: date, pdas, user_picks, user_picks_reissue, pack_tables, pack_tables_reissue, current };
}
__name(resourceOptions, "resourceOptions");
async function employeeContext(env, body) {
  const mnv = String(body.mnv || "").trim();
  if (!mnv) return apiError("MNV_REQUIRED", "VALIDATION", 400);
  const date = await businessDate(env.DB);
  const employee = await env.DB.prepare("SELECT mnv,full_name,phone,main_position,supplier,department,site,warehouse,start_date,note FROM employees WHERE mnv=?1").bind(mnv).first();
  if (!employee) return apiError("EMPLOYEE_NOT_FOUND", "VALIDATION", 404);
  const session = await env.DB.prepare("SELECT session_id,mnv,business_date,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,pda_enter_status,pda_exit_status,resource_note,enter_at,exit_at,entered_by,exited_by,version FROM attendance_sessions WHERE business_date=?1 AND mnv=?2").bind(date, mnv).first();
  const state = !session ? "NOT_ENTERED" : String(session.state) === "ACTIVE" ? "ACTIVE" : "ENDED";
  const sessionOut = session ? { ...session, work_choice: visibleWork(String(session.work_choice || "")) } : null;
  const activeLabor2 = body.include_labor === true ? await env.DB.prepare("SELECT labor_id,mnv,business_date,shift,labor_type,time_marker,state,start_at,end_at,note,deduct_staff,start_event_id,finish_event_id,version FROM labor_sessions WHERE business_date=?1 AND mnv=?2 AND state='OPEN' ORDER BY start_at DESC LIMIT 1").bind(date, mnv).first() : null;
  const options = body.include_options === true && state === "NOT_ENTERED" ? await resourceOptions(env.DB, date, mnv) : null;
  return json({ ok: true, source: "SERVICE_D1", business_date: date, employee: employeeJson(employee), state, session: sessionOut, active_labor: activeLabor2, options });
}
__name(employeeContext, "employeeContext");
function eventLabel(type) {
  return type === "ATTENDANCE_ENTER" ? "V\xE0o ca" : type === "ATTENDANCE_EXIT" ? "Ra ca" : type === "RESOURCE_CHANGE" ? "\u0110\u1ED5i t\xE0i nguy\xEAn" : type === "LABOR_START" ? "B\u1EAFt \u0111\u1EA7u c\xF4ng nh\u1EADt" : type === "LABOR_FINISH" ? "Ho\xE0n th\xE0nh c\xF4ng nh\u1EADt" : type;
}
__name(eventLabel, "eventLabel");
async function sharedHistory(env, body) {
  const requested = String(body.business_date || "").trim();
  const date = requested || await businessDate(env.DB), target = String(body.mnv || "").trim();
  const raw = (await env.DB.prepare("SELECT event_id,event_type,actor_id,committed_at,payload_json FROM events WHERE business_date=?1 ORDER BY authority_seq").bind(date).all()).results ?? [];
  const employeeRows = (await env.DB.prepare("SELECT mnv,full_name FROM employees").all()).results ?? [];
  const names = new Map(employeeRows.map((x2) => [x2.mnv, x2.full_name]));
  const timeline = raw.map((e) => {
    let p = {};
    try {
      p = JSON.parse(e.payload_json);
    } catch {
    }
    const mnv = String(p.mnv || "");
    return { scope: "SESSION", session_id: `${date}|${mnv}`, mnv, full_name: names.get(mnv) || "", shift: String(p.shift || ""), event_type: e.event_type, label: eventLabel(e.event_type), at: e.committed_at, at_iso: e.committed_at, actor: e.actor_id, detail: String(p.labor_type || p.note || ""), event_id: e.event_id };
  }).filter((x2) => x2.mnv && (!target || x2.mnv === target));
  if (target) return json({ ok: true, source: "SERVICE_D1", history_engine: "M2_CANONICAL_D1", business_date: date, mnv: target, timeline });
  const groups = {};
  for (const e of timeline) {
    let g = groups[e.mnv];
    if (!g) g = groups[e.mnv] = { mnv: e.mnv, full_name: e.full_name, shift: e.shift, state: "ACTIVE", event_count: 0, last_time: "", last_at_iso: "", last_actor: "", last_label: "" };
    if (e.full_name) g.full_name = e.full_name;
    if (e.shift) g.shift = e.shift;
    g.event_count++;
    if (e.event_type === "ATTENDANCE_EXIT") g.state = "ENDED";
    g.last_time = e.at;
    g.last_at_iso = e.at_iso;
    g.last_actor = e.actor;
    g.last_label = e.label;
  }
  const items = Object.values(groups).sort((a, b) => (Date.parse(b.last_at_iso) || 0) - (Date.parse(a.last_at_iso) || 0));
  return json({ ok: true, source: "SERVICE_D1", history_engine: "M2_CANONICAL_D1", business_date: date, total: items.length, active_count: items.filter((x2) => x2.state === "ACTIVE").length, ended_count: items.filter((x2) => x2.state === "ENDED").length, items });
}
__name(sharedHistory, "sharedHistory");
async function mobileRead(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  const body = await readJsonBody(request, 256e3), action = String(body.action || "");
  if (action === "employee_context") return employeeContext(env, body);
  if (action === "master_options") return json(await resourceOptions(env.DB, await businessDate(env.DB), String(body.mnv || "")));
  if (action === "history_shared") return sharedHistory(env, body);
  if (action === "runtime_status") return json({ ok: true, source: "SERVICE_D1", authority: await currentAuthority(env.DB), service_generation: env.SERVICE_GENERATION });
  return apiError("MOBILE_READ_ACTION_UNSUPPORTED", "VALIDATION", 400);
}
__name(mobileRead, "mobileRead");

// src/resource_admin.ts
var NS2 = { PDA: "pda", USER_PICK: "user_pick", PACK_TABLE: "pack_table", USER_PACK: "user_pack" };
var ENTITY = { PDA: "MASTER_PDA", USER_PICK: "MASTER_USER_PICK", PACK_TABLE: "MASTER_PACK_TABLE", USER_PACK: "MASTER_USER_PACK" };
function text5(v, max2 = 180) {
  return String(v ?? "").trim().slice(0, max2);
}
__name(text5, "text");
function shiftFrom2(label2, table) {
  const f = label2.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase().trim(), t = table.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase().trim();
  if (f.startsWith("CA 1-")) return "Ca 1";
  if (f.startsWith("CA 2-")) return "Ca 2";
  if (f.startsWith("HP-") || t === "HP") return "Ca HC";
  return "";
}
__name(shiftFrom2, "shiftFrom");
function cleanMeta(raw) {
  const out = {};
  for (const [k, v] of Object.entries(raw || {})) {
    const key = text5(k, 80);
    if (!key || /pass|password|token|secret|cookie|authorization|verifier|private.?key/i.test(key)) continue;
    out[key] = typeof v === "boolean" || typeof v === "number" ? v : text5(v, 300);
  }
  return out;
}
__name(cleanMeta, "cleanMeta");
async function resourceAdminList(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  const [resources, maps, catalogs] = await env.DB.batch([
    env.DB.prepare("SELECT resource_type,resource_id,status_label,available,metadata_json FROM resources ORDER BY resource_type,resource_id"),
    env.DB.prepare("SELECT pack_table,shift,user_pack,label,available FROM resource_pack_map ORDER BY pack_table,shift,user_pack"),
    env.DB.prepare("SELECT namespace,ordinal,value FROM catalog_values WHERE namespace IN ('DANH S\xC1CH PDA_T\xECnh tr\u1EA1ng','DANH S\xC1CH USER PICK_T\xECnh tr\u1EA1ng','DANH S\xC1CH B\xC0N PACK_T\xECnh tr\u1EA1ng','DANH S\xC1CH USER PACK_T\xECnh tr\u1EA1ng') ORDER BY namespace,ordinal")
  ]);
  return json({ ok: true, resources: resources?.results ?? [], pack_map: maps?.results ?? [], catalogs: catalogs?.results ?? [], can_edit: auth4.role === "ADMIN" || auth4.role === "SUPERADMIN" });
}
__name(resourceAdminList, "resourceAdminList");
async function resourceAdminMutate(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  if (auth4.role !== "ADMIN" && auth4.role !== "SUPERADMIN") return apiError("ADMIN_REQUIRED", "PERMISSION", 403);
  const b = await readJsonBody(request), operation = String(b.operation || "").toUpperCase(), type = String(b.resource_type || "").toUpperCase(), id = text5(b.resource_id), idem = text5(b.idempotency_key, 220);
  if (!["UPSERT", "DELETE"].includes(operation) || !["PDA", "USER_PICK", "PACK_TABLE", "USER_PACK"].includes(type) || !id || !idem) return apiError("RESOURCE_ADMIN_FIELDS_REQUIRED", "VALIDATION", 400);
  const prior = await env.DB.prepare("SELECT * FROM events WHERE idempotency_key=?1").bind(idem).first();
  if (prior) return json({ ok: true, duplicate: true, event: prior });
  const authority2 = await currentAuthority(env.DB);
  if (authority2.mode !== "SERVICE_PRIMARY" || authority2.scope !== "PRODUCTION") return apiError("SERVICE_NOT_WRITE_AUTHORITY", "CONFLICT", 409, true);
  const leased = await env.DB.prepare("SELECT 1 x FROM resource_leases WHERE resource_type=?1 AND resource_id=?2 LIMIT 1").bind(type, id).first();
  if (operation === "DELETE" && leased) return apiError("RESOURCE_IN_USE", "RESOURCE", 409, false);
  if (operation === "DELETE" && type === "PACK_TABLE") {
    const mapped = await env.DB.prepare("SELECT 1 x FROM resource_pack_map WHERE pack_table=?1 LIMIT 1").bind(id).first();
    if (mapped) return apiError("RESOURCE_HAS_PACK_MAPPING", "RESOURCE", 409, false);
  }
  const before = await env.DB.prepare("SELECT resource_type,resource_id,status_label,available,metadata_json FROM resources WHERE resource_type=?1 AND resource_id=?2").bind(type, id).first();
  if (operation === "DELETE" && !before) return apiError("RESOURCE_NOT_FOUND", "VALIDATION", 404);
  const latest = await env.DB.prepare("SELECT business_date FROM business_dates ORDER BY sequence_no DESC LIMIT 1").first();
  if (!latest?.business_date) return apiError("BUSINESS_DATE_NOT_BOOTSTRAPPED", "INTEGRITY", 503, true);
  const at = nowIso(), meta3 = cleanMeta(b.metadata);
  const statusLabel2 = text5(b.status_label) || text5(before?.status_label) || "Ho\u1EA1t \u0111\u1ED9ng", available = isAvailableLabel(statusLabel2) ? 1 : 0, after2 = operation === "DELETE" ? null : { resource_type: type, resource_id: id, status_label: statusLabel2, available, metadata_json: JSON.stringify(meta3) };
  const seq = authority2.authority_seq + 1, namespace = NS2[type], rev2 = (await env.DB.prepare("SELECT revision FROM revision_state WHERE namespace=?1").bind(namespace).first())?.revision ?? 0, newRev = rev2 + 1;
  const base = { event_id: crypto.randomUUID(), event_type: operation === "DELETE" ? "MASTER_RESOURCE_DELETE" : "MASTER_RESOURCE_UPSERT", entity_type: ENTITY[type], entity_id: id, business_date: latest.business_date, authority_epoch: authority2.authority_epoch, authority_seq: seq, service_generation: authority2.service_generation, base_version: rev2, new_version: newRev, actor_id: auth4.login_id, actor_role: auth4.role, device_id: auth4.device_id, occurred_at: at, committed_at: at, payload_json: JSON.stringify({ source: "SERVICE_RESOURCE_ADMIN", client_source: auth4.session_kind ?? "PDA", operation, before, after: after2, resource_type: type, namespace }), idempotency_key: idem, origin: auth4.session_kind === "WEB" ? "WEB_RESOURCE_ADMIN" : "PDA_RESOURCE_ADMIN", schema_version: 1 }, event = { ...base, checksum: await sha256Hex(JSON.stringify(base)) };
  const stmts = [];
  if (operation === "UPSERT") {
    stmts.push(env.DB.prepare("INSERT INTO resources(resource_type,resource_id,status_label,available,metadata_json,source_row,source_checksum) VALUES(?1,?2,?3,?4,?5,0,?6) ON CONFLICT(resource_type,resource_id) DO UPDATE SET status_label=excluded.status_label,available=excluded.available,metadata_json=excluded.metadata_json,source_checksum=excluded.source_checksum").bind(type, id, statusLabel2, available, JSON.stringify(meta3), event.event_id));
    if (type === "USER_PACK") {
      const table = text5(meta3["T\xEAn b\xE0n pack"] ?? meta3.pack_table), label2 = text5(meta3["User pack"] ?? meta3.label), shift = shiftFrom2(label2, table);
      if (table && shift) stmts.push(env.DB.prepare("INSERT INTO resource_pack_map(pack_table,shift,user_pack,label,available,source_row,source_checksum) VALUES(?1,?2,?3,?4,?5,0,?6) ON CONFLICT(pack_table,shift) DO UPDATE SET user_pack=excluded.user_pack,label=excluded.label,available=excluded.available,source_checksum=excluded.source_checksum").bind(table, shift, id, label2, available, event.event_id));
    }
  } else {
    stmts.push(env.DB.prepare("DELETE FROM resources WHERE resource_type=?1 AND resource_id=?2").bind(type, id));
    if (type === "USER_PACK") stmts.push(env.DB.prepare("DELETE FROM resource_pack_map WHERE user_pack=?1").bind(id));
  }
  stmts.push(env.DB.prepare("UPDATE revision_state SET revision=?1,updated_at=?2 WHERE namespace=?3 AND revision=?4").bind(newRev, at, namespace, rev2));
  stmts.push(env.DB.prepare("UPDATE authority_state SET authority_seq=?1,updated_at=?2 WHERE singleton_id=1 AND authority_epoch=?3 AND authority_seq=?4").bind(seq, at, authority2.authority_epoch, authority2.authority_seq));
  stmts.push(env.DB.prepare("INSERT INTO events(event_id,event_type,entity_type,entity_id,business_date,authority_epoch,authority_seq,service_generation,base_version,new_version,actor_id,actor_role,device_id,occurred_at,committed_at,payload_json,idempotency_key,origin,schema_version,checksum) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,?20)").bind(event.event_id, event.event_type, event.entity_type, event.entity_id, event.business_date, event.authority_epoch, event.authority_seq, event.service_generation, event.base_version, event.new_version, event.actor_id, event.actor_role, event.device_id, event.occurred_at, event.committed_at, event.payload_json, event.idempotency_key, event.origin, event.schema_version, event.checksum));
  stmts.push(env.DB.prepare("INSERT INTO sheet_replication_outbox(event_id,status,next_attempt_at) VALUES(?1,'PENDING',?2)").bind(event.event_id, at));
  try {
    await env.DB.batch(stmts);
  } catch (e) {
    return apiError("RESOURCE_ADMIN_CONFLICT", "TRANSIENT", 409, true, String(e).slice(0, 160));
  }
  await enqueueInvalidation(env.DB, namespace, newRev);
  try {
    const hub = env.REALTIME_HUB.getByName("master:global");
    await hub.invalidate({ type: "MASTER_CHANGED", namespace, revision: newRev, authority_epoch: event.authority_epoch, authority_seq: event.authority_seq });
  } catch {
  }
  return json({ ok: true, duplicate: false, event, resource: after2, deleted: operation === "DELETE", namespace, revision: newRev }, 201);
}
__name(resourceAdminMutate, "resourceAdminMutate");

// src/session_hotfix.ts
function text6(v, max2 = 300) {
  return String(v ?? "").trim().slice(0, max2);
}
__name(text6, "text");
function own(o, k) {
  return Object.prototype.hasOwnProperty.call(o, k);
}
__name(own, "own");
function iso(v) {
  const d = new Date(v);
  return !!v && !Number.isNaN(d.getTime()) && /^\d{4}-\d{2}-\d{2}T/.test(v);
}
__name(iso, "iso");
function visibleDate3(v) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(v);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : v;
}
__name(visibleDate3, "visibleDate");
function visibleDateTime2(v) {
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return v;
  return new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Ho_Chi_Minh", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }).format(d).replace(",", "");
}
__name(visibleDateTime2, "visibleDateTime");
async function byId(db, id) {
  return db.prepare("SELECT session_id,mnv,business_date,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,pda_enter_status,pda_exit_status,resource_note,enter_at,exit_at,entered_by,exited_by,version FROM attendance_sessions WHERE session_id=?1").bind(id).first();
}
__name(byId, "byId");
async function resolveActiveSession(db, id, mnv) {
  const requested = id ? await byId(db, id) : null;
  if (requested && mnv && requested.mnv !== mnv) return { session: null, error: "SESSION_EMPLOYEE_MISMATCH" };
  if (requested?.state === "ACTIVE") return { session: requested };
  if (!mnv) return { session: null };
  const rows2 = await db.prepare("SELECT session_id,mnv,business_date,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,pda_enter_status,pda_exit_status,resource_note,enter_at,exit_at,entered_by,exited_by,version FROM attendance_sessions WHERE mnv=?1 AND state='ACTIVE' ORDER BY business_date DESC,updated_at DESC LIMIT 2").bind(mnv).all();
  const active = rows2.results ?? [];
  if (active.length > 1) return { session: null, error: "SESSION_ACTIVE_AMBIGUOUS" };
  return { session: active[0] ?? null };
}
__name(resolveActiveSession, "resolveActiveSession");
async function sessionEvent(env, auth4, s, type, payload3, idem, newVersion) {
  const a = await currentAuthority(env.DB);
  if (a.mode !== "SERVICE_PRIMARY" || a.scope !== "PRODUCTION") throw new Error("SERVICE_NOT_WRITE_AUTHORITY");
  const at = nowIso();
  const base = { event_id: crypto.randomUUID(), event_type: type, entity_type: "ATTENDANCE_SESSION", entity_id: s.session_id, business_date: s.business_date, authority_epoch: a.authority_epoch, authority_seq: a.authority_seq + 1, service_generation: a.service_generation, base_version: s.version, new_version: newVersion, actor_id: auth4.login_id, actor_role: auth4.role, device_id: auth4.device_id, occurred_at: at, committed_at: at, payload_json: JSON.stringify(payload3), idempotency_key: idem, origin: "SESSION_HOTFIX", schema_version: 1 };
  return { ...base, checksum: await sha256Hex(JSON.stringify(base)) };
}
__name(sessionEvent, "sessionEvent");
function eventStmts(db, e, expectedSeq, replicate) {
  const x2 = [
    db.prepare("UPDATE authority_state SET authority_seq=?1,updated_at=?2 WHERE singleton_id=1 AND authority_epoch=?3 AND authority_seq=?4").bind(e.authority_seq, e.committed_at, e.authority_epoch, expectedSeq),
    db.prepare("INSERT INTO events(event_id,event_type,entity_type,entity_id,business_date,authority_epoch,authority_seq,service_generation,base_version,new_version,actor_id,actor_role,device_id,occurred_at,committed_at,payload_json,idempotency_key,origin,schema_version,checksum) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,?20)").bind(e.event_id, e.event_type, e.entity_type, e.entity_id, e.business_date, e.authority_epoch, e.authority_seq, e.service_generation, e.base_version, e.new_version, e.actor_id, e.actor_role, e.device_id, e.occurred_at, e.committed_at, e.payload_json, e.idempotency_key, e.origin, e.schema_version, e.checksum)
  ];
  if (replicate) x2.push(db.prepare("INSERT INTO sheet_replication_outbox(event_id,status,next_attempt_at) VALUES(?1,'PENDING',?2)").bind(e.event_id, e.committed_at));
  return x2;
}
__name(eventStmts, "eventStmts");
async function invalidate(env, e) {
  await enqueueInvalidation(env.DB, "day", e.authority_seq, e.business_date);
  try {
    const hub = env.REALTIME_HUB.getByName(`business:${e.business_date}`);
    await hub.invalidate({ type: "DAY_CHANGED", business_date: e.business_date, day_revision: e.authority_seq, authority_epoch: e.authority_epoch, authority_seq: e.authority_seq });
  } catch {
  }
}
__name(invalidate, "invalidate");
async function existing(env, idem) {
  return env.DB.prepare("SELECT * FROM events WHERE idempotency_key=?1").bind(idem).first();
}
__name(existing, "existing");
async function validateResource(env, type, id, sessionId) {
  if (!id) return;
  const [r, l] = await env.DB.batch([env.DB.prepare("SELECT available FROM resources WHERE resource_type=?1 AND resource_id=?2").bind(type, id), env.DB.prepare("SELECT session_id FROM resource_leases WHERE resource_type=?1 AND resource_id=?2").bind(type, id)]);
  const available = Number(r?.results?.[0]?.available ?? 0) === 1;
  const holder = String(l?.results?.[0]?.session_id ?? "");
  if (!available) throw new Error(`${type}_UNAVAILABLE`);
  if (holder && holder !== sessionId) throw new Error(`${type}_IN_USE`);
}
__name(validateResource, "validateResource");
async function sessionWorkUpdate(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  const b = await readJsonBody(request, 128e3), id = text6(b.session_id, 220), mnv = text6(b.mnv, 80), idem = text6(b.idempotency_key, 220);
  if (!id && !mnv || !idem) return apiError("SESSION_WORK_FIELDS_REQUIRED", "VALIDATION", 400);
  const prior = await existing(env, idem);
  if (prior) return json({ ok: true, duplicate: true, event: prior, session: await byId(env.DB, String(prior.entity_id ?? id)) });
  const resolved = await resolveActiveSession(env.DB, id, mnv);
  if (resolved.error) return apiError(resolved.error, "CONFLICT", 409);
  const s = resolved.session;
  if (!s) return apiError("SESSION_NOT_ACTIVE", "CONFLICT", 409);
  const pda = own(b, "pda_serial") ? text6(b.pda_serial) : text6(s.pda_serial), pick = own(b, "user_pick") ? text6(b.user_pick) : text6(s.user_pick), table = own(b, "pack_table") ? text6(b.pack_table) : text6(s.pack_table), pack = own(b, "user_pack") ? text6(b.user_pack) : text6(s.user_pack);
  if (Boolean(table) !== Boolean(pack)) return apiError("PACK_TABLE_USER_REQUIRED_TOGETHER", "VALIDATION", 400);
  const duplicateUser = Boolean(b.duplicate_user);
  try {
    await validateResource(env, "PDA", pda, s.session_id);
    await validateResource(env, "USER_PICK", pick, s.session_id);
    await validateResource(env, "PACK_TABLE", table, s.session_id);
    await validateResource(env, "USER_PACK", pack, s.session_id);
  } catch (e2) {
    return apiError(String(e2).replace(/^Error: /, ""), "RESOURCE", 409);
  }
  for (const [t, r, current] of [["USER_PICK", pick, text6(s.user_pick)], ["USER_PACK", pack, text6(s.user_pack)]]) {
    if (!r || r === current) continue;
    const used = await env.DB.prepare("SELECT 1 x FROM resource_daily_consumption WHERE business_date=?1 AND resource_type=?2 AND resource_id=?3").bind(s.business_date, t, r).first();
    if (used && !duplicateUser) return apiError(t === "USER_PICK" ? "USER_PICK_ALREADY_USED_TODAY" : "USER_PACK_ALREADY_USED_TODAY", "RESOURCE", 409);
  }
  if (table && pack) {
    const m = await env.DB.prepare("SELECT 1 x FROM resource_pack_map WHERE pack_table=?1 AND user_pack=?2 AND available=1 LIMIT 1").bind(table, pack).first();
    if (!m) return apiError("PACK_MAPPING_INVALID", "RESOURCE", 409);
  }
  const hasPick = Boolean(pda || pick), hasPack = Boolean(table && pack);
  let choice = text6(b.work_choice, 20).toUpperCase();
  if (!["PICK", "PACK", "KHONG"].includes(choice)) choice = s.work_choice;
  if (hasPick && hasPack) {
    if (choice !== "PICK" && choice !== "PACK") choice = s.work_choice === "PACK" ? "PACK" : "PICK";
  } else if (hasPick) choice = "PICK";
  else if (hasPack) choice = "PACK";
  else choice = "KHONG";
  let pdaStatus = null;
  if (pda) {
    if (pda === text6(s.pda_serial) && text6(s.pda_enter_status)) pdaStatus = s.pda_enter_status;
    else pdaStatus = (await env.DB.prepare("SELECT status_label FROM resources WHERE resource_type='PDA' AND resource_id=?1").bind(pda).first())?.status_label ?? null;
  }
  const note = text6(b.resource_note, 500), newVersion = s.version + 1;
  let e;
  try {
    const a = await currentAuthority(env.DB);
    e = await sessionEvent(env, auth4, s, "RESOURCE_CHANGE", { mnv: s.mnv, shift: s.shift, work_choice: choice, pda_serial: pda, user_pick: pick, pack_table: table, user_pack: pack, pda_enter_status: pdaStatus || "", resource_note: note, duplicate_user: duplicateUser, before: { work_choice: s.work_choice, pda_serial: s.pda_serial, user_pick: s.user_pick, pack_table: s.pack_table, user_pack: s.user_pack, pda_enter_status: s.pda_enter_status }, after: { work_choice: choice, pda_serial: pda || null, user_pick: pick || null, pack_table: table || null, user_pack: pack || null, pda_enter_status: pdaStatus } }, idem, newVersion);
    const stmts = eventStmts(env.DB, e, a.authority_seq, true);
    stmts.push(env.DB.prepare("DELETE FROM resource_leases WHERE session_id=?1").bind(s.session_id));
    stmts.push(env.DB.prepare("UPDATE attendance_sessions SET work_choice=?1,pda_serial=?2,user_pick=?3,pack_table=?4,user_pack=?5,pda_enter_status=?6,pda_exit_status=NULL,resource_note=?7,version=?8,updated_at=?9 WHERE session_id=?10 AND version=?11 AND state='ACTIVE'").bind(choice, pda || null, pick || null, table || null, pack || null, pdaStatus, note, newVersion, e.committed_at, s.session_id, s.version));
    for (const [t, r] of [["PDA", pda], ["USER_PICK", pick], ["PACK_TABLE", table], ["USER_PACK", pack]]) {
      if (!r) continue;
      stmts.push(env.DB.prepare("INSERT INTO resource_leases(resource_type,resource_id,session_id,mnv,business_date,acquired_event_id,acquired_at) VALUES(?1,?2,?3,?4,?5,?6,?7)").bind(t, r, s.session_id, s.mnv, s.business_date, e.event_id, e.committed_at));
      if (t === "USER_PICK" || t === "USER_PACK") stmts.push(env.DB.prepare("INSERT OR IGNORE INTO resource_daily_consumption(business_date,resource_type,resource_id,mnv,first_event_id) VALUES(?1,?2,?3,?4,?5)").bind(s.business_date, t, r, s.mnv, e.event_id));
    }
    await env.DB.batch(stmts);
  } catch (x2) {
    return apiError("SESSION_WORK_CONFLICT", "CONFLICT", 409, true, void 0, String(x2).slice(0, 180));
  }
  await invalidate(env, e);
  return json({ ok: true, event: e, session: await byId(env.DB, s.session_id) }, 201);
}
__name(sessionWorkUpdate, "sessionWorkUpdate");
async function sessionExitGuarded(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  const b = await readJsonBody(request, 64e3), id = text6(b.session_id, 220), mnv = text6(b.mnv, 80), idem = text6(b.idempotency_key, 220);
  if (!id && !mnv || !idem) return apiError("SESSION_EXIT_FIELDS_REQUIRED", "VALIDATION", 400);
  const prior = await existing(env, idem);
  if (prior) return json({ ok: true, duplicate: true, event: prior, session: await byId(env.DB, String(prior.entity_id ?? id)) });
  const resolved = await resolveActiveSession(env.DB, id, mnv);
  if (resolved.error) return apiError(resolved.error, "CONFLICT", 409);
  const s = resolved.session;
  if (!s) return apiError("SESSION_NOT_ACTIVE", "CONFLICT", 409);
  const open = (await env.DB.prepare("SELECT COUNT(*) n FROM labor_sessions WHERE mnv=?1 AND business_date=?2 AND state='OPEN'").bind(s.mnv, s.business_date).first())?.n ?? 0;
  if (open > 0) return apiError("OPEN_LABOR_BLOCKS_EXIT", "CONFLICT", 409);
  const nowStatus = text6(b.pda_exit_status, 180);
  if (text6(s.pda_serial)) {
    let expected = text6(s.pda_enter_status, 180);
    if (!expected) expected = text6((await env.DB.prepare("SELECT status_label FROM resources WHERE resource_type='PDA' AND resource_id=?1").bind(s.pda_serial).first())?.status_label, 180);
    if (!nowStatus) return apiError("PDA_EXIT_STATUS_REQUIRED", "VALIDATION", 400);
    if (expected && nowStatus !== expected) return apiError("PDA_STATUS_MISMATCH_NOTIFY_SPECIALIST", "CONFLICT", 409, false, { expected_status: expected, current_status: nowStatus, pda_serial: s.pda_serial });
  }
  const newVersion = s.version + 1;
  let e;
  try {
    const a = await currentAuthority(env.DB);
    e = await sessionEvent(env, auth4, s, "ATTENDANCE_EXIT", { mnv: s.mnv, shift: s.shift, work_choice: s.work_choice, pda_serial: s.pda_serial || "", user_pick: s.user_pick || "", pack_table: s.pack_table || "", user_pack: s.user_pack || "", pda_exit_status: nowStatus }, idem, newVersion);
    const stmts = eventStmts(env.DB, e, a.authority_seq, true);
    stmts.push(env.DB.prepare("UPDATE attendance_sessions SET state='ENDED',exit_at=?1,exited_by=?2,pda_exit_status=?3,version=?4,updated_at=?1 WHERE session_id=?5 AND version=?6 AND state='ACTIVE'").bind(e.committed_at, auth4.login_id, nowStatus || null, newVersion, s.session_id, s.version));
    stmts.push(env.DB.prepare("DELETE FROM resource_leases WHERE session_id=?1").bind(s.session_id));
    await env.DB.batch(stmts);
  } catch (x2) {
    return apiError("SESSION_EXIT_CONFLICT", "CONFLICT", 409, true, void 0, String(x2).slice(0, 180));
  }
  await invalidate(env, e);
  return json({ ok: true, event: e, session: await byId(env.DB, s.session_id) }, 201);
}
__name(sessionExitGuarded, "sessionExitGuarded");
async function googleToken2(env) {
  const body = new URLSearchParams({ client_id: env.GOOGLE_OAUTH_CLIENT_ID, client_secret: env.GOOGLE_OAUTH_CLIENT_SECRET, refresh_token: env.GOOGLE_OAUTH_REFRESH_TOKEN, grant_type: "refresh_token" });
  const r = await fetch("https://oauth2.googleapis.com/token", { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" }, body });
  const j = await r.json();
  if (!r.ok || !j.access_token) throw new Error(`GOOGLE_OAUTH:${j.error ?? r.status}`);
  return j.access_token;
}
__name(googleToken2, "googleToken");
function gh(t) {
  return { authorization: `Bearer ${t}`, "content-type": "application/json" };
}
__name(gh, "gh");
async function raRows(env, t) {
  const range = encodeURIComponent("'RA - V\xC0O TRONG CA'!A2:V");
  const r = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(env.GOOGLE_SOURCE_SHEET_ID)}/values/${range}?valueRenderOption=FORMATTED_VALUE`, { headers: { authorization: `Bearer ${t}` } });
  if (!r.ok) throw new Error(`GOOGLE_RA_READ:${r.status}`);
  return (await r.json()).values ?? [];
}
__name(raRows, "raRows");
async function updateRaTime(env, t, row, value) {
  const range = encodeURIComponent(`'RA - V\xC0O TRONG CA'!S${row}`);
  const r = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(env.GOOGLE_SOURCE_SHEET_ID)}/values/${range}?valueInputOption=RAW`, { method: "PUT", headers: gh(t), body: JSON.stringify({ range: `'RA - V\xC0O TRONG CA'!S${row}`, majorDimension: "ROWS", values: [[visibleDateTime2(value)]] }) });
  if (!r.ok) throw new Error(`GOOGLE_RA_TIME:${r.status}`);
}
__name(updateRaTime, "updateRaTime");
async function raSheetId(env, t) {
  const r = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(env.GOOGLE_SOURCE_SHEET_ID)}?fields=sheets.properties(sheetId,title)`, { headers: { authorization: `Bearer ${t}` } });
  if (!r.ok) throw new Error(`GOOGLE_META:${r.status}`);
  const j = await r.json();
  const id = j.sheets?.find((x2) => x2.properties?.title === "RA - V\xC0O TRONG CA")?.properties?.sheetId;
  if (id === void 0) throw new Error("GOOGLE_RA_SHEET_MISSING");
  return id;
}
__name(raSheetId, "raSheetId");
async function deleteRaRow(env, t, row) {
  const sheetId = await raSheetId(env, t);
  const r = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(env.GOOGLE_SOURCE_SHEET_ID)}:batchUpdate`, { method: "POST", headers: gh(t), body: JSON.stringify({ requests: [{ deleteDimension: { range: { sheetId, dimension: "ROWS", startIndex: row - 1, endIndex: row } } }] }) });
  if (!r.ok) throw new Error(`GOOGLE_RA_DELETE:${r.status}`);
}
__name(deleteRaRow, "deleteRaRow");
async function historyHas(env, t, eventId) {
  const range = encodeURIComponent("'L\u1ECACH S\u1EEC NGHI\u1EC6P V\u1EE4'!K2:K");
  const r = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(env.GOOGLE_SOURCE_SHEET_ID)}/values/${range}`, { headers: { authorization: `Bearer ${t}` } });
  if (!r.ok) throw new Error(`GOOGLE_HISTORY_READ:${r.status}`);
  const v = (await r.json()).values ?? [];
  return v.some((x2) => String(x2[0] ?? "") === eventId);
}
__name(historyHas, "historyHas");
async function appendHistory2(env, t, e, s, label2, detail) {
  if (await historyHas(env, t, e.event_id)) return;
  const emp = await env.DB.prepare("SELECT full_name FROM employees WHERE mnv=?1").bind(s.mnv).first();
  const range = encodeURIComponent("'L\u1ECACH S\u1EEC NGHI\u1EC6P V\u1EE4'!A:M");
  const values = [[visibleDate3(e.business_date), s.session_id, s.mnv, emp?.full_name ?? "", s.shift, e.event_type, label2, visibleDateTime2(e.occurred_at), e.actor_id, detail, e.event_id, "SERVICE_M2", e.authority_seq]];
  const r = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(env.GOOGLE_SOURCE_SHEET_ID)}/values/${range}:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS`, { method: "POST", headers: gh(t), body: JSON.stringify({ range: "'L\u1ECACH S\u1EEC NGHI\u1EC6P V\u1EE4'!A:M", majorDimension: "ROWS", values }) });
  if (!r.ok) throw new Error(`GOOGLE_HISTORY_APPEND:${r.status}`);
}
__name(appendHistory2, "appendHistory");
async function projectSpecial(env, e) {
  const p = JSON.parse(e.payload_json), s = await byId(env.DB, e.entity_id);
  if (!s) return;
  const t = await googleToken2(env), rows2 = await raRows(env, t), date = visibleDate3(e.business_date), wanted = e.event_type === "ATTENDANCE_EXIT_DELETED" ? "EXIT" : String(p.field) === "enter_at" ? "ENTER" : "EXIT";
  let row = -1;
  for (let i2 = rows2.length - 1; i2 >= 0; i2--) {
    const r = rows2[i2] ?? [];
    if (String(r[0] ?? "") === date && String(r[2] ?? "") === s.mnv && String(r[20] ?? "").toUpperCase() === wanted) {
      row = i2 + 2;
      break;
    }
  }
  if (e.event_type === "ATTENDANCE_TIME_CORRECTED") {
    if (row > 0) await updateRaTime(env, t, row, String(p.after_value || ""));
    await appendHistory2(env, t, e, s, "S\u1EEDa gi\u1EDD " + (String(p.field) === "enter_at" ? "v\xE0o ca" : "ra ca"), `${visibleDateTime2(String(p.before_value || ""))} \u2192 ${visibleDateTime2(String(p.after_value || ""))} \u2022 L\xFD do: ${String(p.reason || "")}`);
  } else if (e.event_type === "ATTENDANCE_EXIT_DELETED") {
    if (row > 0) await deleteRaRow(env, t, row);
    await appendHistory2(env, t, e, s, "X\xF3a ghi nh\u1EADn ra ca", `\u0110\xE3 x\xF3a m\u1ED1c ra ca ${visibleDateTime2(String(p.before_exit_at || ""))} kh\u1ECFi d\u1EEF li\u1EC7u RA/V\xC0O. L\xFD do: ${String(p.reason || "")}`);
  }
}
__name(projectSpecial, "projectSpecial");
async function attendanceTimeCorrect(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  if (auth4.role !== "ADMIN" && auth4.role !== "SUPERADMIN") return apiError("ADMIN_REQUIRED", "PERMISSION", 403);
  const b = await readJsonBody(request, 64e3), id = text6(b.session_id, 220), field = text6(b.field, 20), next = text6(b.corrected_at, 60), reason = text6(b.reason, 500), idem = text6(b.idempotency_key, 220);
  if (!id || !["enter_at", "exit_at"].includes(field) || !iso(next) || reason.length < 3 || !idem) return apiError("ATTENDANCE_CORRECTION_FIELDS_REQUIRED", "VALIDATION", 400);
  const prior = await existing(env, idem);
  if (prior) {
    try {
      await projectSpecial(env, prior);
    } catch {
    }
    return json({ ok: true, duplicate: true, event: prior, session: await byId(env.DB, id) });
  }
  const s = await byId(env.DB, id);
  if (!s) return apiError("SESSION_NOT_FOUND", "VALIDATION", 404);
  const old = field === "enter_at" ? text6(s.enter_at, 60) : text6(s.exit_at, 60);
  if (!old) return apiError("ATTENDANCE_TIME_NOT_RECORDED", "VALIDATION", 409);
  if (field === "exit_at" && s.state !== "ENDED") return apiError("EXIT_TIME_REQUIRES_ENDED_SESSION", "CONFLICT", 409);
  const newVersion = s.version + 1;
  let e;
  try {
    const a = await currentAuthority(env.DB);
    e = await sessionEvent(env, auth4, s, "ATTENDANCE_TIME_CORRECTED", { mnv: s.mnv, field, before_value: old, after_value: next, reason, before: { enter_at: s.enter_at, exit_at: s.exit_at }, after: { enter_at: field === "enter_at" ? next : s.enter_at, exit_at: field === "exit_at" ? next : s.exit_at } }, idem, newVersion);
    const stmts = eventStmts(env.DB, e, a.authority_seq, false);
    stmts.push(env.DB.prepare(`UPDATE attendance_sessions SET ${field}=?1,version=?2,updated_at=?3 WHERE session_id=?4 AND version=?5`).bind(next, newVersion, e.committed_at, s.session_id, s.version));
    await env.DB.batch(stmts);
  } catch (x2) {
    return apiError("ATTENDANCE_CORRECTION_CONFLICT", "CONFLICT", 409, true, void 0, String(x2).slice(0, 180));
  }
  await invalidate(env, e);
  let pending = false;
  try {
    await projectSpecial(env, e);
  } catch {
    pending = true;
  }
  return json({ ok: true, event: e, session: await byId(env.DB, id), projection_pending: pending }, 201);
}
__name(attendanceTimeCorrect, "attendanceTimeCorrect");
async function attendanceExitDelete(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  if (auth4.role !== "ADMIN" && auth4.role !== "SUPERADMIN") return apiError("ADMIN_REQUIRED", "PERMISSION", 403);
  const b = await readJsonBody(request, 64e3), id = text6(b.session_id, 220), reason = text6(b.reason, 500), idem = text6(b.idempotency_key, 220);
  if (!id || reason.length < 3 || !idem) return apiError("EXIT_DELETE_FIELDS_REQUIRED", "VALIDATION", 400);
  const prior = await existing(env, idem);
  if (prior) {
    try {
      await projectSpecial(env, prior);
    } catch {
    }
    return json({ ok: true, duplicate: true, event: prior, session: await byId(env.DB, id) });
  }
  const s = await byId(env.DB, id);
  if (!s || s.state !== "ENDED" || !s.exit_at) return apiError("ENDED_SESSION_REQUIRED", "CONFLICT", 409);
  const conflicts = [];
  let pda = text6(s.pda_serial), pick = text6(s.user_pick), table = text6(s.pack_table), pack = text6(s.user_pack);
  for (const [t, r] of [["PDA", pda], ["USER_PICK", pick], ["PACK_TABLE", table], ["USER_PACK", pack]]) {
    if (!r) continue;
    const l = await env.DB.prepare("SELECT session_id FROM resource_leases WHERE resource_type=?1 AND resource_id=?2").bind(t, r).first();
    const master = await env.DB.prepare("SELECT available FROM resources WHERE resource_type=?1 AND resource_id=?2").bind(t, r).first();
    if (l && l.session_id !== s.session_id || !master?.available) {
      conflicts.push(`${t}:${r}`);
      if (t === "PDA") pda = "";
      if (t === "USER_PICK") pick = "";
      if (t === "PACK_TABLE") {
        table = "";
        pack = "";
      }
      if (t === "USER_PACK") {
        pack = "";
        table = "";
      }
    }
  }
  const newVersion = s.version + 1;
  let e;
  try {
    const a = await currentAuthority(env.DB);
    e = await sessionEvent(env, auth4, s, "ATTENDANCE_EXIT_DELETED", { mnv: s.mnv, before_exit_at: s.exit_at, before_exited_by: s.exited_by, reason, resource_reacquire_conflicts: conflicts, before: { state: s.state, pda_serial: s.pda_serial, user_pick: s.user_pick, pack_table: s.pack_table, user_pack: s.user_pack }, after: { state: "ACTIVE", pda_serial: pda || null, user_pick: pick || null, pack_table: table || null, user_pack: pack || null } }, idem, newVersion);
    const stmts = eventStmts(env.DB, e, a.authority_seq, false);
    stmts.push(env.DB.prepare("UPDATE attendance_sessions SET state='ACTIVE',exit_at=NULL,exited_by=NULL,pda_exit_status=NULL,pda_serial=?1,user_pick=?2,pack_table=?3,user_pack=?4,pda_enter_status=CASE WHEN ?1 IS NULL THEN NULL ELSE pda_enter_status END,version=?5,updated_at=?6 WHERE session_id=?7 AND version=?8 AND state='ENDED'").bind(pda || null, pick || null, table || null, pack || null, newVersion, e.committed_at, s.session_id, s.version));
    for (const [t, r] of [["PDA", pda], ["USER_PICK", pick], ["PACK_TABLE", table], ["USER_PACK", pack]]) {
      if (r) stmts.push(env.DB.prepare("INSERT OR IGNORE INTO resource_leases(resource_type,resource_id,session_id,mnv,business_date,acquired_event_id,acquired_at) VALUES(?1,?2,?3,?4,?5,?6,?7)").bind(t, r, s.session_id, s.mnv, s.business_date, e.event_id, e.committed_at));
    }
    await env.DB.batch(stmts);
  } catch (x2) {
    return apiError("EXIT_DELETE_CONFLICT", "CONFLICT", 409, true, void 0, String(x2).slice(0, 180));
  }
  await invalidate(env, e);
  let pending = false;
  try {
    await projectSpecial(env, e);
  } catch {
    pending = true;
  }
  return json({ ok: true, event: e, session: await byId(env.DB, id), resource_reacquire_conflicts: conflicts, projection_pending: pending }, 201);
}
__name(attendanceExitDelete, "attendanceExitDelete");

// src/beta44_owner.ts
async function googleAccessToken2(env) {
  const body = new URLSearchParams({ client_id: env.GOOGLE_OAUTH_CLIENT_ID, client_secret: env.GOOGLE_OAUTH_CLIENT_SECRET, refresh_token: env.GOOGLE_OAUTH_REFRESH_TOKEN, grant_type: "refresh_token" });
  const r = await fetch("https://oauth2.googleapis.com/token", { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" }, body });
  const j = await r.json();
  if (!r.ok || !j.access_token) throw new Error(`GOOGLE_OAUTH:${j.error ?? r.status}`);
  return j.access_token;
}
__name(googleAccessToken2, "googleAccessToken");
async function clearAdminRow(env, row) {
  const token3 = await googleAccessToken2(env), range = `'Danh s\xE1ch Admin'!A${row}:K${row}`, url = `https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(env.GOOGLE_SOURCE_SHEET_ID)}/values/${encodeURIComponent(range)}:clear`;
  const r = await fetch(url, { method: "POST", headers: { authorization: `Bearer ${token3}`, "content-type": "application/json" }, body: "{}" });
  if (!r.ok) throw new Error(`GOOGLE_ACCOUNT_CLEAR:${r.status}`);
}
__name(clearAdminRow, "clearAdminRow");
async function superadminDeleteAccounts(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  if (auth4.role !== "SUPERADMIN") return apiError("SUPERADMIN_REQUIRED", "PERMISSION", 403);
  let body;
  try {
    body = await request.json();
  } catch {
    return apiError("ACCOUNT_DELETE_BODY_INVALID", "VALIDATION", 400);
  }
  const ids = Array.isArray(body.login_ids) ? [...new Set(body.login_ids.map((x2) => String(x2 || "").trim()).filter(Boolean))].slice(0, 100) : [];
  if (!ids.length) return apiError("ACCOUNT_DELETE_IDS_REQUIRED", "VALIDATION", 400);
  const deleted = [], blocked = [];
  for (const id of ids) {
    if (id === auth4.login_id) {
      blocked.push({ login_id: id, reason: "Kh\xF4ng th\u1EC3 x\xF3a t\xE0i kho\u1EA3n \u0111ang \u0111\u0103ng nh\u1EADp" });
      continue;
    }
    const row = await env.DB.prepare("SELECT login_id,role,display_name,source_row,status FROM accounts WHERE login_id=?1").bind(id).first();
    if (!row) {
      blocked.push({ login_id: id, reason: "Kh\xF4ng t\xECm th\u1EA5y t\xE0i kho\u1EA3n" });
      continue;
    }
    if (row.role === "SUPERADMIN") {
      blocked.push({ login_id: id, reason: "T\xE0i kho\u1EA3n Qu\u1EA3n tr\u1ECB cao nh\u1EA5t \u0111\u01B0\u1EE3c b\u1EA3o v\u1EC7" });
      continue;
    }
    await env.DB.prepare("UPDATE accounts SET status='DISABLED' WHERE login_id=?1").bind(id).run();
    try {
      if (Number(row.source_row) > 1) await clearAdminRow(env, Number(row.source_row));
      else throw new Error("ACCOUNT_SOURCE_ROW_INVALID");
    } catch (e) {
      blocked.push({ login_id: id, reason: "Kh\xF4ng c\u1EADp nh\u1EADt \u0111\u01B0\u1EE3c Google Sheet" });
      continue;
    }
    await env.DB.prepare("DELETE FROM accounts WHERE login_id=?1 AND role<>'SUPERADMIN'").bind(id).run();
    await commitAdminAudit(env.DB, auth4, { action: "account_delete", target_type: "ACCOUNT", target_id: id, target_label: row.display_name, result: "OK", detail: "X\xF3a t\xE0i kho\u1EA3n theo y\xEAu c\u1EA7u Superadmin", device_id: auth4.device_id });
    deleted.push(id);
  }
  return json({ ok: true, deleted, blocked });
}
__name(superadminDeleteAccounts, "superadminDeleteAccounts");

// src/beta47_connections.ts
function roleVi(role3) {
  return role3 === "SUPERADMIN" ? "Qu\u1EA3n tr\u1ECB cao nh\u1EA5t" : role3 === "ADMIN" ? "Qu\u1EA3n tr\u1ECB" : "Ng\u01B0\u1EDDi d\xF9ng";
}
__name(roleVi, "roleVi");
function platformVi(kind) {
  return kind === "WEB" ? "Web" : "\u1EE8ng d\u1EE5ng";
}
__name(platformVi, "platformVi");
async function serviceConnectionsV47(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  const r = await env.DB.prepare(`
    SELECT x.login_id,a.display_name,a.role,x.session_id,x.device_id,x.issued_at,x.client_kind,d.last_seen_at
    FROM (
      SELECT login_id,session_id,device_id,issued_at,'APP' client_kind FROM auth_sessions
      UNION ALL
      SELECT login_id,session_id,device_id,issued_at,'WEB' client_kind FROM auth_web_sessions
    ) x
    JOIN accounts a ON a.login_id=x.login_id AND a.status='ACTIVE'
    LEFT JOIN client_devices d ON d.device_id=x.device_id
    ORDER BY x.client_kind,x.login_id
  `).all();
  const items = (r.results ?? []).map((x2) => ({
    tai_khoan: x2.login_id,
    ten_hien_thi: x2.display_name || x2.login_id,
    quyen: roleVi(x2.role || "USER"),
    nen_tang: platformVi(x2.client_kind),
    loai_ket_noi: x2.client_kind,
    thiet_bi: x2.device_id,
    phien: x2.session_id,
    dang_ket_noi: true,
    dang_nhap_luc: x2.issued_at,
    lan_hoat_dong_gan_nhat: x2.last_seen_at || x2.issued_at
  }));
  return json({ ok: true, cap_nhat_luc: nowIso(), nguoi_dung: items, dang_ket_noi: items.length, app: items.filter((x2) => x2.loai_ket_noi === "APP").length, web: items.filter((x2) => x2.loai_ket_noi === "WEB").length });
}
__name(serviceConnectionsV47, "serviceConnectionsV47");

// src/history_delete.ts
var INSERT_EVENT = `INSERT INTO events(event_id,event_type,entity_type,entity_id,business_date,authority_epoch,authority_seq,service_generation,base_version,new_version,actor_id,actor_role,device_id,occurred_at,committed_at,payload_json,idempotency_key,origin,schema_version,checksum) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,?20)`;
async function historyDelete(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  if (auth4.role !== "SUPERADMIN") return apiError("SUPERADMIN_REQUIRED", "PERMISSION", 403);
  const body = await readJsonBody(request);
  const ids = [...new Set((body.event_ids ?? []).map((v) => String(v || "").trim()).filter(Boolean))];
  const idem = String(body.idempotency_key || "").trim();
  const reason = String(body.reason || "").trim().slice(0, 500);
  if (ids.length < 1 || ids.length > 100 || !idem) return apiError("HISTORY_DELETE_FIELDS_REQUIRED", "VALIDATION", 400);
  const authority2 = await currentAuthority(env.DB);
  if (authority2.mode !== "SERVICE_PRIMARY") return apiError("SERVICE_NOT_WRITE_AUTHORITY", "CONFLICT", 409, true);
  const targets = [];
  for (const id of ids) {
    const row = await env.DB.prepare("SELECT event_id,event_type,business_date,entity_type,entity_id FROM events WHERE event_id=?1").bind(id).first();
    if (!row) return apiError("HISTORY_DELETE_TARGET_NOT_FOUND", "VALIDATION", 404, false, id);
    if (row.event_type === "HISTORY_DELETE") return apiError("HISTORY_DELETE_AUDIT_PROTECTED", "PERMISSION", 403, false, id);
    targets.push(row);
  }
  const byDate = /* @__PURE__ */ new Map();
  for (const row of targets) {
    const date = String(row.business_date || "").trim();
    if (!date) return apiError("HISTORY_DELETE_DATE_MISSING", "INTEGRITY", 409, false, row.event_id);
    const list = byDate.get(date) ?? [];
    list.push(row);
    byDate.set(date, list);
  }
  const dates = [...byDate.keys()].sort();
  const prior = [];
  for (const date of dates) {
    const key = `history-delete:${idem}:${date}`;
    const e = await env.DB.prepare("SELECT * FROM events WHERE idempotency_key=?1").bind(key).first();
    if (e) prior.push(e);
  }
  if (prior.length) {
    if (prior.length === dates.length) return json({ ok: true, duplicate: true, deleted_count: ids.length, target_event_ids: ids, tombstones: prior });
    return apiError("HISTORY_DELETE_PARTIAL_IDEMPOTENCY", "INTEGRITY", 409);
  }
  const committed = nowIso(), clientSource = auth4.session_kind === "WEB" ? "WEB" : "PDA";
  const tombstones = [];
  let seq = authority2.authority_seq;
  for (const date of dates) {
    const rows2 = byDate.get(date) ?? [];
    seq += 1;
    const summaries = rows2.map((x2) => ({ event_id: x2.event_id, event_type: x2.event_type, entity_type: x2.entity_type, entity_id: x2.entity_id }));
    const detail = `\u0110\xE3 x\xF3a ${rows2.length} m\u1EE5c: ${rows2.map((x2) => `${x2.event_type} \u2022 ${x2.entity_type}:${x2.entity_id}`).join(", ")}`.slice(0, 900);
    const payload3 = { logical_delete: true, target_event_ids: rows2.map((x2) => x2.event_id), target_summaries: summaries, deleted_count: rows2.length, detail, reason, source: clientSource, actor_login_id: auth4.login_id, actor_role: auth4.role, original_events_immutable: true };
    const base = { event_id: crypto.randomUUID(), event_type: "HISTORY_DELETE", entity_type: "HISTORY", entity_id: `history-delete:${date}:${crypto.randomUUID()}`, business_date: date, authority_epoch: authority2.authority_epoch, authority_seq: seq, service_generation: authority2.service_generation, base_version: 0, new_version: 1, actor_id: auth4.login_id, actor_role: auth4.role, device_id: auth4.device_id, occurred_at: committed, committed_at: committed, payload_json: JSON.stringify(payload3), idempotency_key: `history-delete:${idem}:${date}`, origin: clientSource === "WEB" ? "WEB_HISTORY_DELETE" : "PDA_HISTORY_DELETE", schema_version: 1 };
    tombstones.push({ ...base, checksum: await sha256Hex(JSON.stringify(base)) });
  }
  const statements = [env.DB.prepare("UPDATE authority_state SET authority_seq=?1,updated_at=?2 WHERE singleton_id=1 AND authority_epoch=?3 AND authority_seq=?4").bind(seq, committed, authority2.authority_epoch, authority2.authority_seq)];
  for (const event of tombstones) {
    statements.push(env.DB.prepare(INSERT_EVENT).bind(event.event_id, event.event_type, event.entity_type, event.entity_id, event.business_date, event.authority_epoch, event.authority_seq, event.service_generation, event.base_version, event.new_version, event.actor_id, event.actor_role, event.device_id, event.occurred_at, event.committed_at, event.payload_json, event.idempotency_key, event.origin, event.schema_version, event.checksum));
    statements.push(env.DB.prepare("INSERT INTO sheet_replication_outbox(event_id,status,next_attempt_at) VALUES(?1,'PENDING',?2)").bind(event.event_id, committed));
  }
  try {
    await env.DB.batch(statements);
  } catch (e) {
    return apiError("HISTORY_DELETE_CONFLICT", "TRANSIENT", 409, true, String(e).slice(0, 160));
  }
  for (const event of tombstones) {
    await enqueueInvalidation(env.DB, "day", event.authority_seq, event.business_date);
    try {
      const hub = env.REALTIME_HUB.getByName(`business:${event.business_date}`);
      await hub.invalidate({ type: "DAY_CHANGED", business_date: event.business_date, day_revision: event.authority_seq, authority_epoch: event.authority_epoch, authority_seq: event.authority_seq });
    } catch {
    }
  }
  return json({ ok: true, duplicate: false, deleted_count: ids.length, target_event_ids: ids, tombstones }, 201);
}
__name(historyDelete, "historyDelete");

// src/health_product.ts
async function productHealth(env) {
  const [a, r, p, c] = await Promise.all([
    env.DB.prepare("SELECT authority_epoch,authority_seq,mode,scope,service_generation,updated_at FROM authority_state WHERE singleton_id=1").first(),
    env.DB.prepare("SELECT target_kind,target_identity,schema_version,state,checkpoint,pending_count,retry_count,last_attempt_at,last_success_at,last_error_class,last_error,updated_at FROM replication_status WHERE singleton_id=1").first(),
    env.DB.prepare("SELECT COUNT(*) n,MIN(created_at) oldest FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first(),
    env.DB.prepare("SELECT COUNT(*) n FROM conflicts WHERE status='OPEN'").first()
  ]);
  if (!a) return json({ ok: false, service: "pickpack", environment: "production", error: "AUTHORITY_STATE_MISSING" }, 503);
  const pending = Number(p?.n ?? 0), oldest = p?.oldest ?? null;
  const oldestMs = oldest ? Date.parse(oldest) : NaN;
  const lagSeconds = pending > 0 && Number.isFinite(oldestMs) ? Math.max(0, Math.floor((Date.now() - oldestMs) / 1e3)) : 0;
  const drift = Number(c?.n ?? 0);
  let state = String(r?.state ?? "UNKNOWN"), healthReason = "CLEAN";
  if (drift > 0) {
    state = "DRIFT";
    healthReason = "OPEN_CONFLICTS";
  } else if (pending > 0 && lagSeconds >= 900) {
    state = "LAGGING";
    healthReason = "REPLICATION_LAG";
  } else if (pending > 0 && state === "HEALTHY") {
    state = "PENDING";
    healthReason = "REPLICATION_PENDING";
  } else if (state !== "HEALTHY") {
    healthReason = state;
  }
  return json({
    ok: true,
    service: "pickpack",
    environment: a.scope === "STAGING_SHADOW" ? "staging-shadow" : "production",
    generation: a.service_generation,
    authority: { authority_epoch: a.authority_epoch, authority_seq: a.authority_seq, mode: a.mode, scope: a.scope, service_generation: a.service_generation, updated_at: a.updated_at },
    replication: {
      target_kind: r?.target_kind ?? null,
      target_identity: r?.target_identity ?? null,
      schema_version: r?.schema_version ?? null,
      state,
      checkpoint: r?.checkpoint ?? null,
      pending_count: pending,
      retry_count: Number(r?.retry_count ?? 0),
      failed_unresolved_count: 0,
      drift_candidate_count: drift,
      oldest_pending_at: oldest,
      lag_seconds: lagSeconds,
      last_attempt_at: r?.last_attempt_at ?? null,
      last_success_at: r?.last_success_at ?? null,
      last_error_class: r?.last_error_class ?? null,
      last_error: r?.last_error ?? null,
      updated_at: r?.updated_at ?? null
    },
    health_reason: healthReason
  });
}
__name(productHealth, "productHealth");

// src/reset_fence.ts
function fenceValues(event) {
  const payload3 = event.payload && typeof event.payload === "object" ? event.payload : {};
  const epoch = Number(event.authority_epoch ?? payload3.authority_epoch ?? payload3._authority_epoch ?? 0);
  const generation = String(event.service_generation ?? payload3.service_generation ?? payload3._service_generation ?? "").trim();
  return { epoch, generation };
}
__name(fenceValues, "fenceValues");
async function resetFenceGate(request, env) {
  const u = new URL(request.url);
  if (request.method !== "POST" || !["/v1/legacy-mutations", "/v1/legacy-mutations/batch"].includes(u.pathname)) return null;
  const reset = await env.DB.prepare("SELECT value FROM system_meta WHERE key='m2_operational_reset_epoch'").first();
  const resetEpoch = Number(reset?.value ?? 0);
  if (!Number.isInteger(resetEpoch) || resetEpoch <= 0) return null;
  if (!await authenticate(env.DB, env, request)) return null;
  const authority2 = await currentAuthority(env.DB);
  if (authority2.authority_epoch < resetEpoch) return null;
  let parsed;
  try {
    parsed = await request.clone().json();
  } catch {
    return null;
  }
  const body = parsed && typeof parsed === "object" ? parsed : {};
  const events = u.pathname.endsWith("/batch") ? Array.isArray(body.events) ? body.events : [] : [body];
  for (const raw of events) {
    const event = raw && typeof raw === "object" ? raw : {};
    const { epoch, generation } = fenceValues(event);
    if (!Number.isInteger(epoch) || epoch !== authority2.authority_epoch || generation !== authority2.service_generation) {
      return apiError("RESET_FENCE_REQUIRED", "CONFLICT", 409, false);
    }
  }
  return null;
}
__name(resetFenceGate, "resetFenceGate");

// src/entry_product.ts
var REPLICATION_LEASE_MS = 9e4;
async function historicalBusinessDates(request, env) {
  const auth4 = await authenticate(env.DB, env, request);
  if (!auth4) return apiError("UNAUTHORIZED", "AUTH", 401);
  if (auth4.role !== "SUPERADMIN") return apiError("SUPERADMIN_REQUIRED", "PERMISSION", 403);
  const u = new URL(request.url), limit = Math.min(200, Math.max(1, Number(u.searchParams.get("limit") || 50))), beforeRaw = Number(u.searchParams.get("before_sequence") || 0), before = Number.isFinite(beforeRaw) && beforeRaw > 0 ? beforeRaw : null;
  const q4 = before === null ? env.DB.prepare("SELECT business_date,sequence_no FROM business_dates ORDER BY sequence_no DESC LIMIT ?1").bind(limit + 1) : env.DB.prepare("SELECT business_date,sequence_no FROM business_dates WHERE sequence_no<?1 ORDER BY sequence_no DESC LIMIT ?2").bind(before, limit + 1);
  const r = await q4.all(), all = r.results ?? [], rows2 = all.slice(0, limit), next = all.length > limit ? rows2[rows2.length - 1]?.sequence_no ?? null : null;
  return json({ ok: true, items: rows2, next_before_sequence: next, has_more: all.length > limit });
}
__name(historicalBusinessDates, "historicalBusinessDates");
async function recoverAbandonedReplicationClaims(env) {
  const now = nowIso(), cutoff = new Date(Date.now() - REPLICATION_LEASE_MS).toISOString();
  const r = await env.DB.prepare("UPDATE sheet_replication_outbox SET status='RETRY',claim_token=NULL,claimed_at=NULL,next_attempt_at=?1,last_error_class='STALE_INFLIGHT_RECOVERED',last_error='Recovered abandoned replication claim for canonical retry' WHERE status='INFLIGHT' AND (claimed_at IS NULL OR claimed_at<=?2)").bind(now, cutoff).run();
  return Number(r.meta?.changes ?? 0);
}
__name(recoverAbandonedReplicationClaims, "recoverAbandonedReplicationClaims");
async function runReplicationSerialized(env, source) {
  const now = nowIso(), leaseCutoff = new Date(Date.now() - REPLICATION_LEASE_MS).toISOString();
  const lock = await env.DB.prepare("UPDATE replication_status SET state='RUNNING',last_attempt_at=?1,updated_at=?1 WHERE singleton_id=1 AND (state<>'RUNNING' OR last_attempt_at IS NULL OR last_attempt_at<=?2)").bind(now, leaseCutoff).run();
  if (Number(lock.meta?.changes ?? 0) === 0) {
    console.log(JSON.stringify({ level: "info", kind: "replication_kick_skipped", source, reason: "ACTIVE_LEASE" }));
    return;
  }
  try {
    const recovered = await recoverAbandonedReplicationClaims(env);
    const replication = await replicatePending(env.DB, env);
    if (replication.processed === 0) {
      const state = replication.pending === 0 ? "HEALTHY" : "DEGRADED";
      await env.DB.prepare("UPDATE replication_status SET state=?1,pending_count=?2,last_attempt_at=?3,last_success_at=CASE WHEN ?2=0 THEN ?3 ELSE last_success_at END,last_error_class=CASE WHEN ?2=0 THEN NULL ELSE last_error_class END,last_error=CASE WHEN ?2=0 THEN NULL ELSE last_error END,updated_at=?3 WHERE singleton_id=1").bind(state, replication.pending, nowIso()).run();
    }
    console.log(JSON.stringify({ level: replication.ok ? "info" : "error", kind: "replication_kick_complete", source, recovered, ...replication }));
  } catch (e) {
    const at = nowIso(), error = String(e).slice(0, 700);
    await env.DB.prepare("UPDATE replication_status SET state='DEGRADED',last_attempt_at=?1,last_error_class='TRANSIENT',last_error=?2,updated_at=?1 WHERE singleton_id=1").bind(at, error).run();
    console.log(JSON.stringify({ level: "error", kind: "replication_kick_failed", source, error }));
  }
}
__name(runReplicationSerialized, "runReplicationSerialized");
function kickReplication(ctx, env, source) {
  ctx.waitUntil(runReplicationSerialized(env, source));
}
__name(kickReplication, "kickReplication");
async function runProductionScheduled(env) {
  await runReplicationSerialized(env, "CRON");
  try {
    const push = await flushPushOutbox(env.DB, env);
    console.log(JSON.stringify({ level: "info", kind: "scheduled_push_complete", ...push }));
  } catch (e) {
    console.log(JSON.stringify({ level: "error", kind: "scheduled_push_failed", error: String(e).slice(0, 500) }));
  }
}
__name(runProductionScheduled, "runProductionScheduled");
function shouldKickAfterResponse(method, response) {
  return method === "POST" && response.status >= 200 && response.status < 300;
}
__name(shouldKickAfterResponse, "shouldKickAfterResponse");
var entry_product_default = {
  async fetch(request, env, ctx) {
    const u = new URL(request.url), method = request.method.toUpperCase();
    if (u.pathname === "/health" && method === "GET") return productHealth(env);
    const fence = await resetFenceGate(request, env);
    if (fence) return fence;
    if (u.pathname === "/v1/auth/gas-session" && method === "POST") return exchangeGasSession(request, env);
    if (u.pathname === "/v1/mobile/read" && method === "POST") return mobileRead(request, env);
    if (u.pathname === "/v1/admin/business-dates" && method === "GET") return historicalBusinessDates(request, env);
    if (u.pathname === "/v1/service/connections" && method === "GET") return serviceConnectionsV47(request, env);
    if (u.pathname === "/v1/admin/accounts/delete" && method === "POST") {
      const response2 = await superadminDeleteAccounts(request, env);
      if (shouldKickAfterResponse(method, response2)) kickReplication(ctx, env, u.pathname);
      return response2;
    }
    if (u.pathname === "/v1/admin/resources" && method === "GET") return resourceAdminList(request, env);
    if (u.pathname === "/v1/admin/resources" && method === "POST") {
      const response2 = await resourceAdminMutate(request, env);
      if (shouldKickAfterResponse(method, response2)) kickReplication(ctx, env, u.pathname);
      return response2;
    }
    if (u.pathname === "/v1/history/delete" && method === "POST") {
      const response2 = await historyDelete(request, env);
      if (shouldKickAfterResponse(method, response2)) kickReplication(ctx, env, u.pathname);
      return response2;
    }
    if (u.pathname === "/v1/session/work" && method === "POST") {
      const response2 = await sessionWorkUpdate(request, env);
      if (shouldKickAfterResponse(method, response2)) kickReplication(ctx, env, u.pathname);
      return response2;
    }
    if (u.pathname === "/v1/session/exit" && method === "POST") {
      const response2 = await sessionExitGuarded(request, env);
      if (shouldKickAfterResponse(method, response2)) kickReplication(ctx, env, u.pathname);
      return response2;
    }
    if (u.pathname === "/v1/session/time-correction" && method === "POST") {
      const response2 = await attendanceTimeCorrect(request, env);
      if (shouldKickAfterResponse(method, response2)) kickReplication(ctx, env, u.pathname);
      return response2;
    }
    if (u.pathname === "/v1/session/delete-exit" && method === "POST") {
      const response2 = await attendanceExitDelete(request, env);
      if (shouldKickAfterResponse(method, response2)) kickReplication(ctx, env, u.pathname);
      return response2;
    }
    const response = await entry_default.fetch(request, env, ctx);
    if (shouldKickAfterResponse(method, response) && !u.pathname.startsWith("/v1/auth/")) kickReplication(ctx, env, u.pathname);
    return response;
  },
  // Cron is now retry-only. Normal successful POST mutations kick projection immediately.
  async scheduled(_controller, env, ctx) {
    ctx.waitUntil(runProductionScheduled(env));
  }
};
export {
  RealtimeHub,
  entry_product_default as default
};
//# sourceMappingURL=entry_product.js.map
