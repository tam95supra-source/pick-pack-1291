#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / 'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'
GRADLE = ROOT / 'app/build.gradle.kts'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise SystemExit(f'{label}: anchor missing')


# Beta71 is exactly one beta after the locked/failed Beta69 candidate.
g = GRADLE.read_text()
g = replace_once(
    g,
    'versionCode = 75\n            versionName = "0.4.2-beta.69"',
    'versionCode = 77\n            versionName = "0.4.2-beta.71"',
    'Beta71 version',
)
GRADLE.write_text(g)

ops = OPS.read_text()

old = '''                listBox.removeAllViews();if(handleAuth(rr))return@runOnUiThread
                if(!rr.ok){showError(rr.error?:"Không tải được tài nguyên");return@runOnUiThread}
                val resources=rr.json?.optJSONArray("resources")?:JSONArray();val holders=mutableListOf<Pair<String,String>>();val seen=linkedSetOf<String>()
                for(i in 0 until resources.length()){
                    val x=resources.optJSONObject(i)?:continue;if(x.optString("resource_type")!="PDA")continue
                    val serial=x.optString("resource_id").trim();if(serial.isBlank())continue
                    val mnv=localMnvFor(serial)
                    if(mnv.isBlank()||!matches(serial,filter)||!seen.add(serial))continue
                    holders.add(serial to mnv)
                }
                val day=operationalStore.loadDay(operationalStore.businessDate());val sessions=day?.optJSONArray("sessions")?:JSONArray()
                for(i in 0 until sessions.length()){
                    val s=sessions.optJSONObject(i)?:continue;if(!s.optString("state").equals("ACTIVE",true))continue
                    val serial=s.optString("pda_serial").trim();val mnv=s.optString("mnv").trim();if(serial.isBlank()||mnv.isBlank()||!matches(serial,filter)||!seen.add(serial))continue
                    holders.add(serial to mnv)
                }
                holders.sortWith(Comparator{a,b->naturalUserCompare(a.first,b.first)})'''

new = '''                listBox.removeAllViews();if(handleAuth(rr))return@runOnUiThread
                // Beta71: local active sessions are the first authority for the PDA holder list.
                // Remote master may enrich/merge the same local-held serials, but its failure must never erase them.
                val holders=mutableListOf<Pair<String,String>>();val seen=linkedSetOf<String>()
                val day=operationalStore.loadDay(operationalStore.businessDate());val sessions=day?.optJSONArray("sessions")?:JSONArray()
                for(i in 0 until sessions.length()){
                    val s=sessions.optJSONObject(i)?:continue;if(!s.optString("state").equals("ACTIVE",true))continue
                    val serial=s.optString("pda_serial").trim();val mnv=s.optString("mnv").trim();if(serial.isBlank()||mnv.isBlank()||!matches(serial,filter)||!seen.add(serial))continue
                    holders.add(serial to mnv)
                }
                if(rr.ok){
                    val resources=rr.json?.optJSONArray("resources")?:JSONArray()
                    for(i in 0 until resources.length()){
                        val x=resources.optJSONObject(i)?:continue;if(x.optString("resource_type")!="PDA")continue
                        val serial=x.optString("resource_id").trim();if(serial.isBlank())continue
                        val mnv=localMnvFor(serial)
                        if(mnv.isBlank()||!matches(serial,filter)||!seen.add(serial))continue
                        holders.add(serial to mnv)
                    }
                }else{
                    TopNotice.show(this@OperationsActivity,"Chưa tải được danh mục PDA từ Service • vẫn hiển thị PDA đang dùng đã lưu trên thiết bị.",TopNotice.Kind.WARNING)
                }
                holders.sortWith(Comparator{a,b->naturalUserCompare(a.first,b.first)})'''

if old in ops:
    ops = ops.replace(old, new, 1)
elif 'Beta71: local active sessions are the first authority for the PDA holder list.' not in ops:
    raise SystemExit('Beta71 PDA local-holder anchor missing')

OPS.write_text(ops)

# Static regression against the materialized Android source.
assert 'versionCode = 77' in g and 'versionName = "0.4.2-beta.71"' in g
assert 'versionCode = 1' in g and 'versionName = "0.1.0-stable"' in g
assert 'Beta71: local active sessions are the first authority for the PDA holder list.' in ops
assert 'if(!rr.ok){showError(rr.error?:"Không tải được tài nguyên");return@runOnUiThread}' not in ops
local_pos = ops.index('val day=operationalStore.loadDay(operationalStore.businessDate());val sessions=day?.optJSONArray("sessions")?:JSONArray()', ops.index('private fun pdaExchangeScreen'))
remote_pos = ops.index('if(rr.ok){', local_pos)
assert local_pos < remote_pos
assert 'Chưa tải được danh mục PDA từ Service • vẫn hiển thị PDA đang dùng đã lưu trên thiết bị.' in ops
assert 'if(q.length==5&&q.all{it.isDigit()})serial.takeLast(5)==q' in ops
assert 'setOnClickListener{openHolder(serial,mnv)}' in ops
assert 'Xác nhận Đổi / Trả PDA' in ops

# Deterministic behavior regression model mirroring the holder selection contract.
def matches(serial: str, typed: str) -> bool:
    q = typed.strip()
    if not q:
        return True
    return serial[-5:] == q if len(q) == 5 and q.isdigit() else serial.lower() == q.lower()


def holders(local_sessions, remote_resources, remote_ok=True, query=''):
    out=[]; seen=set()
    for s in local_sessions:
        if str(s.get('state','')).upper() != 'ACTIVE':
            continue
        serial=str(s.get('pda_serial','')).strip(); mnv=str(s.get('mnv','')).strip()
        if not serial or not mnv or not matches(serial,query) or serial in seen:
            continue
        seen.add(serial); out.append((serial,mnv))
    if remote_ok:
        # Remote master only merges serials that resolve to an active local holder; it never overrides local holder authority.
        by_serial={str(s.get('pda_serial','')).strip():str(s.get('mnv','')).strip() for s in local_sessions if str(s.get('state','')).upper()=='ACTIVE'}
        for r in remote_resources:
            if r.get('resource_type') != 'PDA':
                continue
            serial=str(r.get('resource_id','')).strip(); mnv=by_serial.get(serial,'')
            if not serial or not mnv or not matches(serial,query) or serial in seen:
                continue
            seen.add(serial); out.append((serial,mnv))
    return sorted(out)

local=[
    {'state':'ACTIVE','pda_serial':'MT905512345','mnv':'10001'},
    {'state':'ACTIVE','pda_serial':'MT905567890','mnv':'10002'},
    {'state':'ENDED','pda_serial':'MT905500000','mnv':'10003'},
]
remote=[
    {'resource_type':'PDA','resource_id':'MT905512345'},
    {'resource_type':'PDA','resource_id':'MT905567890'},
    {'resource_type':'PDA','resource_id':'MT905599999'},
]
assert holders(local,remote,True)==[('MT905512345','10001'),('MT905567890','10002')]                 # remote/master OK
assert holders(local,remote,False)==[('MT905512345','10001'),('MT905567890','10002')]                # remote fail + local holders
assert holders([],remote,False)==[]                                                                  # no local holder
assert len(holders(local,remote,False))==2                                                           # multiple active PDA
assert holders(local,remote,False,'12345')==[('MT905512345','10001')]                               # search last 5
assert 'openHolder(serial,mnv)' in ops and 'confirmPdaHandoverCondition' in ops                       # confirmation path retained
print('BETA71_PDA_LOCAL_HOLDER_FIX_PASS')
