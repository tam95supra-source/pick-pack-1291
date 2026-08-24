#!/usr/bin/env python3
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'service/src/session_hotfix.ts'
s=p.read_text()
old_sig='async function sessionEvent(env:Env,auth:AuthLike,s:SessionRow,type:string,payload:Record<string,unknown>,idem:string,newVersion:number):Promise<EventRow>{\n  const a=await currentAuthority(env.DB);'
new_sig='async function sessionEvent(env:Env,auth:AuthLike,s:SessionRow,type:string,payload:Record<string,unknown>,idem:string,newVersion:number,aOverride?:Awaited<ReturnType<typeof currentAuthority>>):Promise<EventRow>{\n  const a=aOverride??await currentAuthority(env.DB);'
if old_sig in s:
    s=s.replace(old_sig,new_sig,1)
elif new_sig not in s:
    raise SystemExit('sessionEvent signature drift')

# Every caller that already captured authority for CAS must build the event from that exact snapshot.
needle=',idem,newVersion);const stmts=eventStmts(env.DB,e,a.authority_seq'
replacement=',idem,newVersion,a);const stmts=eventStmts(env.DB,e,a.authority_seq'
if needle in s:
    count=s.count(needle)
    s=s.replace(needle,replacement)
    if count < 5:
        raise SystemExit(f'unexpectedly few authority-fenced callers: {count}')
elif s.count(replacement) < 5:
    raise SystemExit('sessionEvent caller shape drift')

p.write_text(s)

out=p.read_text()
assert 'aOverride?:Awaited<ReturnType<typeof currentAuthority>>' in out
assert 'const a=aOverride??await currentAuthority(env.DB);' in out
# Validate the actual sessionEvent invocation, not an earlier projection/reference to the same event type.
for marker in ['RESOURCE_CHANGE','ATTENDANCE_EXIT','ATTENDANCE_TIME_CORRECTED','ATTENDANCE_EXIT_DELETED','ATTENDANCE_ENTER_DELETED']:
    pattern=re.compile(
        r'sessionEvent\(env,auth,s,"'+re.escape(marker)+r'".*?,idem,newVersion,a\);const stmts=eventStmts\(env\.DB,e,a\.authority_seq',
        re.S,
    )
    if not pattern.search(out):
        raise SystemExit(f'{marker} is not authority-snapshot fenced')
print('Service S62 authority snapshot materialization PASS')
