#!/usr/bin/env python3
from pathlib import Path

p = Path("service/src/auth.ts")
s = p.read_text(encoding="utf-8")
start = s.index("export async function authenticate(")
end = s.index("\nexport async function logout(", start)
a = s[start:end]

required = [
    'const expected=await hmacB64u(new TextEncoder().encode(env.SERVICE_TOKEN_SECRET),encoded); if(!constantTimeEqual(expected,signature)) return null;',
    'if(payload.e&&String(payload.e).toUpperCase()!==expectedEnvironment)return null;',
    'if(payload.a&&String(payload.a)!==expectedAudience)return null;',
    'if(expectedEnvironment==="STABLE"&&(!payload.e||!payload.a))return null;',
    'const kind:SessionKind=payload.c==="WEB"?"WEB":"PDA";',
    'const sessionTable=kind==="WEB"?"auth_web_sessions":"auth_sessions";',
    'FROM accounts a JOIN ${sessionTable} s ON s.login_id=a.login_id',
    'WHERE a.login_id=?1 AND s.session_id=?2 AND s.device_id=?3 LIMIT 1',
    '.bind(payload.l,payload.s,payload.d)',
    'row.status!=="ACTIVE"',
    'row.role!==payload.r',
    'row.verifier_hash!==payload.v',
    'row.session_id!==payload.s',
    'row.device_id!==payload.d',
    'return {login_id:row.login_id,role:row.role,display_name:row.display_name,device_id:row.device_id,session_id:row.session_id,verifier_hash:row.verifier_hash,session_kind:kind};',
]
missing = [x for x in required if x not in a]
if missing:
    raise SystemExit("R5_AUTH_JOIN_SEMANTIC_MISSING:" + " | ".join(missing))

# authenticate() is a realtime hot path: exactly one D1 statement is permitted here.
if a.count("db.prepare(") != 1:
    raise SystemExit(f"R5_AUTH_JOIN_D1_STATEMENT_COUNT:{a.count('db.prepare(')}")
if "db.batch(" in a:
    raise SystemExit("R5_AUTH_JOIN_BATCH_FORBIDDEN")
if a.count("${sessionTable}") != 1:
    raise SystemExit("R5_AUTH_JOIN_DYNAMIC_TABLE_NOT_SINGLE_WHITELISTED_USE")

# No compatibility path may bypass the canonical account+session validation.
for forbidden in (
    "const sessionQuery=",
    "Promise.all([",
    "SELECT login_id,role,display_name,verifier_hash,status FROM accounts WHERE login_id=?1",
):
    if forbidden in a:
        raise SystemExit("R5_AUTH_JOIN_LEGACY_LOOKUP_RETURNED:" + forbidden)

print("R5_AUTH_JOIN_CONTRACT_PASS")
