#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "service/src/session_hotfix.ts"

old = '''async function validateResource(env:Env,type:string,id:string,sessionId:string):Promise<void>{if(!id)return;const [r,l]=await env.DB.batch([env.DB.prepare("SELECT available FROM resources WHERE resource_type=?1 AND resource_id=?2").bind(type,id),env.DB.prepare("SELECT session_id FROM resource_leases WHERE resource_type=?1 AND resource_id=?2").bind(type,id)]);const available=Number((r?.results?.[0] as {available?:number}|undefined)?.available??0)===1;const holder=String((l?.results?.[0] as {session_id?:string}|undefined)?.session_id??"");if(!available)throw new Error(`${type}_UNAVAILABLE`);if(holder&&holder!==sessionId)throw new Error(`${type}_IN_USE`);}'''
new = '''// S63_RESOURCE_OWNER_LEASE_VALIDATION: a resource already leased by this exact active session remains valid even when the projected free-list marks it unavailable.\nasync function validateResource(env:Env,type:string,id:string,sessionId:string):Promise<void>{if(!id)return;const [r,l]=await env.DB.batch([env.DB.prepare("SELECT available FROM resources WHERE resource_type=?1 AND resource_id=?2").bind(type,id),env.DB.prepare("SELECT session_id FROM resource_leases WHERE resource_type=?1 AND resource_id=?2").bind(type,id)]);const available=Number((r?.results?.[0] as {available?:number}|undefined)?.available??0)===1;const holder=String((l?.results?.[0] as {session_id?:string}|undefined)?.session_id??"");if(holder===sessionId)return;if(holder)throw new Error(`${type}_IN_USE`);if(!available)throw new Error(`${type}_UNAVAILABLE`);}'''

text = TARGET.read_text()
if "S63_RESOURCE_OWNER_LEASE_VALIDATION" in text:
    print("S63 resource owner lease fix already materialized")
else:
    if old not in text:
        raise SystemExit("validateResource anchor not found; refusing unsafe patch")
    text = text.replace(old, new, 1)
    TARGET.write_text(text)

check = TARGET.read_text()
assert check.count("S63_RESOURCE_OWNER_LEASE_VALIDATION") == 1
frag = check[check.index("S63_RESOURCE_OWNER_LEASE_VALIDATION"):check.index("S63_RESOURCE_OWNER_LEASE_VALIDATION") + 1800]
assert "if(holder===sessionId)return" in frag
assert "if(holder)throw new Error(`${type}_IN_USE`)" in frag
assert "if(!available)throw new Error(`${type}_UNAVAILABLE`)" in frag
assert frag.index("if(holder===sessionId)return") < frag.index("if(holder)throw new Error(`${type}_IN_USE`)") < frag.index("if(!available)throw new Error(`${type}_UNAVAILABLE`)")
print("S63_RESOURCE_OWNER_LEASE_VALIDATION PASS")
