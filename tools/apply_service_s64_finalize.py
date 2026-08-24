#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ENTRY=ROOT/'service/src/entry_product.ts'
HOT=ROOT/'service/src/session_hotfix.ts'

def once(text,old,new,label):
    if new in text:return text
    if old not in text:raise SystemExit(f'missing anchor: {label}')
    return text.replace(old,new,1)

e=ENTRY.read_text()
anchor='''    if(u.pathname==="/v1/session/enter-v2"&&method==="POST"){\n'''
marker='''    if(u.pathname==="/v1/session/model-version"&&method==="GET")return new Response(JSON.stringify({ok:true,model:"S64_SESSION_MULTI_POSITION_MULTI_RESOURCE",session_version_cas:true,multi_user:true,pack_user_table_independent:true}),{status:200,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store"}});\n'''
e=once(e,anchor,marker+anchor,'model marker route')
ENTRY.write_text(e)

h=HOT.read_text()
h=once(h,
'''  const s=await byId(env.DB,id);if(!s||s.state!=="ACTIVE"||!s.enter_at)return apiError("ACTIVE_SESSION_REQUIRED","CONFLICT",409);\n''',
'''  const s=await byId(env.DB,id);if(!s||!s.enter_at)return apiError("ATTENDANCE_SESSION_REQUIRED","CONFLICT",409);\n''',
'delete active-only guard')
old='''const stmts=eventStmts(env.DB,e,a.authority_seq,false);stmts.push(env.DB.prepare("DELETE FROM resource_leases WHERE session_id=?1").bind(s.session_id));stmts.push(env.DB.prepare("DELETE FROM attendance_sessions WHERE session_id=?1 AND version=?2 AND state='ACTIVE'").bind(s.session_id,s.version));await env.DB.batch(stmts);'''
new='''const stmts=eventStmts(env.DB,e,a.authority_seq,false);stmts.push(env.DB.prepare(`DELETE FROM resource_daily_consumption
    WHERE business_date=?1 AND mnv=?2
      AND EXISTS(SELECT 1 FROM session_resource_assignments a WHERE a.session_id=?3 AND a.resource_type=resource_daily_consumption.resource_type AND a.resource_id=resource_daily_consumption.resource_id)
      AND NOT EXISTS(SELECT 1 FROM session_resource_assignments other WHERE other.session_id<>?3 AND other.business_date=?1 AND other.resource_type=resource_daily_consumption.resource_type AND other.resource_id=resource_daily_consumption.resource_id AND other.state='USED')`).bind(s.business_date,s.mnv,s.session_id));stmts.push(env.DB.prepare("DELETE FROM resource_leases WHERE session_id=?1").bind(s.session_id));stmts.push(env.DB.prepare("DELETE FROM attendance_sessions WHERE session_id=?1 AND version=?2").bind(s.session_id,s.version));await env.DB.batch(stmts);'''
h=once(h,old,new,'full session operational delete')
HOT.write_text(h)

assert 'S64_SESSION_MULTI_POSITION_MULTI_RESOURCE' in ENTRY.read_text()
assert 'ATTENDANCE_SESSION_REQUIRED' in HOT.read_text()
assert "state='ACTIVE'\").bind(s.session_id,s.version)" not in HOT.read_text()
print('S64_FINALIZE_PASS')
