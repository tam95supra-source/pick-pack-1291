#!/usr/bin/env python3
from pathlib import Path

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
    if count < 4:
        raise SystemExit(f'unexpectedly few authority-fenced callers: {count}')
elif replacement not in s:
    raise SystemExit('sessionEvent caller shape drift')

p.write_text(s)

out=p.read_text()
assert 'aOverride?:Awaited<ReturnType<typeof currentAuthority>>' in out
assert 'const a=aOverride??await currentAuthority(env.DB);' in out
# The hot paths must no longer capture one authority seq for CAS and a second one for event construction.
for marker in ['RESOURCE_CHANGE','ATTENDANCE_EXIT','ATTENDANCE_TIME_CORRECTED','ATTENDANCE_EXIT_DELETED','ATTENDANCE_ENTER_DELETED']:
    idx=out.find(f'"{marker}"')
    if idx < 0:
        raise SystemExit(f'missing marker {marker}')
    tail=out[idx:idx+1800]
    if ',idem,newVersion,a);const stmts=eventStmts(env.DB,e,a.authority_seq' not in tail:
        raise SystemExit(f'{marker} is not authority-snapshot fenced')
print('Service S62 authority snapshot materialization PASS')
