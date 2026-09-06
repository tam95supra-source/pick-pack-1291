#!/usr/bin/env python3
from pathlib import Path

p = Path('service/src/auth.ts')
s = p.read_text(encoding='utf-8')
old = '''  const kind:SessionKind=payload.c==="WEB"?"WEB":"PDA";
  const sessionQuery=kind==="WEB"
    ?db.prepare("SELECT session_id,device_id FROM auth_web_sessions WHERE login_id=?1").bind(payload.l)
    :db.prepare("SELECT session_id,device_id FROM auth_sessions WHERE login_id=?1").bind(payload.l);
  const results=await db.batch([
    db.prepare("SELECT login_id,role,display_name,verifier_hash,status FROM accounts WHERE login_id=?1").bind(payload.l),
    sessionQuery,
  ]);
  const account=(results[0]?.results?.[0]??null) as {login_id:string;role:"SUPERADMIN"|"ADMIN"|"USER";display_name:string;verifier_hash:string;status:string}|null;
  const session=(results[1]?.results?.[0]??null) as SessionRow|null;
  if(!account||account.status!=="ACTIVE"||account.role!==payload.r||account.verifier_hash!==payload.v||!session||session.session_id!==payload.s||session.device_id!==payload.d) return null;
  return {login_id:account.login_id,role:account.role,display_name:account.display_name,device_id:session.device_id,session_id:session.session_id,verifier_hash:account.verifier_hash,session_kind:kind};
'''
new = '''  const kind:SessionKind=payload.c==="WEB"?"WEB":"PDA";
  // R5-15 / QUOTA-REALTIME-DELTA-001: authenticate is on every realtime status/delta request.
  // Preserve the exact revocation/role/verifier/session/device semantics while collapsing the
  // account + session lookup into one indexed D1 statement to remove concurrent read contention.
  const sessionTable=kind==="WEB"?"auth_web_sessions":"auth_sessions";
  const row=await db.prepare(`SELECT a.login_id,a.role,a.display_name,a.verifier_hash,a.status,s.session_id,s.device_id
    FROM accounts a JOIN ${sessionTable} s ON s.login_id=a.login_id
    WHERE a.login_id=?1 AND s.session_id=?2 AND s.device_id=?3 LIMIT 1`)
    .bind(payload.l,payload.s,payload.d)
    .first<{login_id:string;role:"SUPERADMIN"|"ADMIN"|"USER";display_name:string;verifier_hash:string;status:string;session_id:string;device_id:string}>();
  if(!row||row.status!=="ACTIVE"||row.role!==payload.r||row.verifier_hash!==payload.v||row.session_id!==payload.s||row.device_id!==payload.d) return null;
  return {login_id:row.login_id,role:row.role,display_name:row.display_name,device_id:row.device_id,session_id:row.session_id,verifier_hash:row.verifier_hash,session_kind:kind};
'''
if s.count(old) != 1:
    raise SystemExit(f'R5_AUTH_JOIN_ANCHOR_COUNT:{s.count(old)}')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('R5_AUTH_SINGLE_QUERY_PATCH_PASS')
