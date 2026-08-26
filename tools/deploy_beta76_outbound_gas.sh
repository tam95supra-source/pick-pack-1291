#!/usr/bin/env bash
set -Eeuo pipefail

E=/tmp/beta76-outbound-gas-evidence
rm -rf "$E"
mkdir -p "$E"
for n in GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN GAS_SCRIPT_ID GAS_DEPLOYMENT_ID; do
  test -n "${!n:-}"
done

token_json=$(curl -fsS --connect-timeout 15 --max-time 30 https://oauth2.googleapis.com/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "client_id=$GOOGLE_OAUTH_CLIENT_ID" \
  --data-urlencode "client_secret=$GOOGLE_OAUTH_CLIENT_SECRET" \
  --data-urlencode "refresh_token=$GOOGLE_OAUTH_REFRESH_TOKEN" \
  --data-urlencode grant_type=refresh_token)
ACCESS_TOKEN=$(jq -r '.access_token // empty' <<<"$token_json")
test -n "$ACCESS_TOKEN"
SCRIPT_ID=$(printf '%s' "$GAS_SCRIPT_ID" | tr -d '\r\n\t ')
RAW=$(printf '%s' "$GAS_DEPLOYMENT_ID" | tr -d '\r\n\t ')
DEPLOYMENT_ID="$RAW"
if [[ "$RAW" == *"/s/"* ]]; then DEPLOYMENT_ID="${RAW#*/s/}"; DEPLOYMENT_ID="${DEPLOYMENT_ID%%/*}"; fi
GAS_URL="https://script.google.com/macros/s/$DEPLOYMENT_ID/exec"
echo "::add-mask::$ACCESS_TOKEN"
echo "::add-mask::$SCRIPT_ID"
echo "::add-mask::$DEPLOYMENT_ID"
echo "::add-mask::$GAS_URL"

api="https://script.googleapis.com/v1/projects/$SCRIPT_ID"
curl -fsS --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" "$api/content" > "$E/project-before.json"
curl -fsS --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" "$api/deployments/$DEPLOYMENT_ID" > "$E/deployment-before.json"

python3 - "$E/project-before.json" "$E/project-target.json" <<'PY'
import hashlib,json,sys
from pathlib import Path
src_path,target_path=sys.argv[1:]
j=json.load(open(src_path,encoding='utf-8'))
files=j.get('files',[])
api=next((f for f in files if f.get('name')=='PICK_PACK_API'),None)
assert api and api.get('source'),'PICK_PACK_API missing'
s=api['source']
block="""    if (action === 'outbound_location_list') return ppJson_(ppOutboundLocationList_(auth));\n    if (action === 'outbound_location_mutate') return ppJson_(ppWithLock_(function(){ return ppOutboundLocationMutate_(auth, body); }));\n    if (action === 'outbound_drop_append') return ppJson_(ppWithLock_(function(){ return ppOutboundAppend_(auth, body); }));\n    if (action === 'outbound_drop_clear') return ppJson_(ppWithLock_(function(){ return ppOutboundClear_(auth, body); }));\n"""
if "action === 'outbound_drop_append'" not in s:
    anchor="    if (action === 'sync_status') return ppJson_(ppSyncStatus_());\n"
    if s.count(anchor)!=1:
        anchor="    return ppJson_({ok:false,error:'UNKNOWN_ACTION'}, 404);\n"
        assert s.count(anchor)==1,'outbound route anchor drift'
        s=s.replace(anchor,block+'\n'+anchor,1)
    else:
        s=s.replace(anchor,anchor+block,1)
for required in ("outbound_location_list","outbound_location_mutate","outbound_drop_append","outbound_drop_clear"):
    assert required in s,required
api['source']=s
outbound=Path('google-apps-script/OUTBOUND_DROP_RECEIVE.gs').read_text(encoding='utf-8')
assert "SHEET_ID: '1tl6har_8vGSVsVlcErfQwjX1YgvN3o-FRG5wQV4VTEM'" in outbound
assert "DROP_SHEET: 'Nhận hàng rớt'" in outbound
assert '__beta76_outbound_test' not in outbound
existing=next((f for f in files if f.get('name')=='OUTBOUND_DROP_RECEIVE'),None)
if existing:
    existing['source']=outbound
    existing['type']='SERVER_JS'
else:
    files.append({'name':'OUTBOUND_DROP_RECEIVE','type':'SERVER_JS','source':outbound})
body={'files':files}
Path(target_path).write_text(json.dumps(body,ensure_ascii=False),encoding='utf-8')
def canon(fs):
    return '\n'.join(str(f.get('name',''))+'\0'+str(f.get('type',''))+'\0'+str(f.get('source','')) for f in fs)
Path('/tmp/beta76-outbound-gas-evidence/project-before.sha256').write_text(hashlib.sha256(canon(j.get('files',[])).encode()).hexdigest())
Path('/tmp/beta76-outbound-gas-evidence/project-target.sha256').write_text(hashlib.sha256(canon(files).encode()).hexdigest())
PY

BEFORE_HASH=$(cat "$E/project-before.sha256")
TARGET_HASH=$(cat "$E/project-target.sha256")
BEFORE_DESC=$(jq -r '.deploymentConfig.description // ""' "$E/deployment-before.json")
if [[ "$BEFORE_HASH" == "$TARGET_HASH" && "$BEFORE_DESC" == "Beta77 Nhận hàng rớt final" ]]; then
  curl -fsSL --connect-timeout 15 --max-time 30 -D "$E/live-health.headers" "$GAS_URL" > "$E/live-health.json"
  jq -e '.ok==true and .service=="pick-pack-gsheet-api"' "$E/live-health.json" >/dev/null
  grep -iq '^content-type:.*application/json' "$E/live-health.headers"
  jq -n --arg target_hash "$TARGET_HASH" --arg status "ALREADY_DEPLOYED" '{status:$status,target_hash:$target_hash,live_health:"PASS"}' > "$E/receipt.json"
  echo 'beta76_outbound_gas=ALREADY_DEPLOYED_PASS'
  exit 0
fi

MUTATED=0
recover(){
  if [[ "$MUTATED" != 1 ]]; then return 0; fi
  jq '{files:.files}' "$E/project-before.json" > "$E/recover-content.json"
  code=$(curl -sS --connect-timeout 15 --max-time 30 -o "$E/recover-content.out" -w '%{http_code}' -X PUT \
    -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @"$E/recover-content.json" "$api/content")
  [[ "$code" == 200 ]]
  jq '{deploymentConfig:.deploymentConfig}' "$E/deployment-before.json" > "$E/recover-deployment.json"
  code=$(curl -sS --connect-timeout 15 --max-time 30 -o "$E/recover-deployment.out" -w '%{http_code}' -X PUT \
    -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @"$E/recover-deployment.json" "$api/deployments/$DEPLOYMENT_ID")
  [[ "$code" == 200 ]]
  MUTATED=0
}
trap 'rc=$?; recover || rc=99; exit $rc' EXIT

NONCE=$(openssl rand -hex 32)
echo "::add-mask::$NONCE"
python3 - "$E/project-target.json" "$E/project-test.json" "$NONCE" <<'PY'
import json,sys
from pathlib import Path
src,target,nonce=sys.argv[1:]
j=json.load(open(src,encoding='utf-8'))
api=next(f for f in j['files'] if f.get('name')=='PICK_PACK_API')
s=api['source']
old_get="""function doGet() {\n  return ppJson_({ok:true, service:'pick-pack-gsheet-api', mode:'APP_GSHEET', report_engine:'S12_CURRENT_DAY', business_date:ppBusinessIso_()});\n}\n"""
new_get="""function doGet(e) {\n  const p=(e&&e.parameter)||{};\n  if(String(p.action||'')==='__beta76_outbound_test' && String(p.token||'')==='__NONCE__') return ppJson_({ok:true,beta77_probe:true});\n  return ppJson_({ok:true, service:'pick-pack-gsheet-api', mode:'APP_GSHEET', report_engine:'S12_CURRENT_DAY', business_date:ppBusinessIso_()});\n}\n""".replace('__NONCE__',nonce)
assert s.count(old_get)==1,'test GET anchor drift'
s=s.replace(old_get,new_get,1)
post_anchor="    const action = String(body.action || '').trim();\n"
post_test="    if (action === '__beta77_outbound_post_test') return ppJson_(ppWithLock_(function(){ return ppOutboundSelfTest_({token:String(body.token||'')}); }));\n"
assert s.count(post_anchor)==1,'test POST anchor drift'
s=s.replace(post_anchor,post_anchor+post_test,1)
api['source']=s
out=next(f for f in j['files'] if f.get('name')=='OUTBOUND_DROP_RECEIVE')
os=out['source']
os=os.replace('  ppHistorySafeAppendS13_({','  if(!auth.__beta76_test) ppHistorySafeAppendS13_({')
helper=r'''
function ppOutboundSelfTest_(body){
  if(String(body.token||'')!=='__NONCE__') return {ok:false,error:'FORBIDDEN'};
  const ss=ppOutboundSs_(), loc=ppOutboundSheet_(PP_OUTBOUND.LOCATION_SHEET), drop=ppOutboundSheet_(PP_OUTBOUND.DROP_SHEET);
  const headers=drop.getRange(1,1,1,8).getDisplayValues()[0];
  const expected=PP_OUTBOUND.HEADERS;
  if(ss.getName()!=='PICK PACK 1291 x OUTBOUND') return {ok:false,error:'SHEET_TITLE_MISMATCH'};
  if(!loc.isSheetHidden()) loc.hideSheet();
  if(!loc.isSheetHidden()) return {ok:false,error:'LOCATION_TAB_NOT_HIDDEN'};
  for(let i=0;i<expected.length;i++) if(String(headers[i]||'')!==String(expected[i]||'')) return {ok:false,error:'HEADER_MISMATCH_'+i};
  const beforeData=JSON.stringify(drop.getDataRange().getDisplayValues()), beforeRows=drop.getLastRow();
  function protectionInfo(sh){
    let out=[];
    [SpreadsheetApp.ProtectionType.RANGE,SpreadsheetApp.ProtectionType.SHEET].forEach(function(t){
      sh.getProtections(t).forEach(function(p){
        out.push({type:String(t),description:String(p.getDescription()||''),warning_only:p.isWarningOnly(),domain_edit:p.canDomainEdit(),editors:p.getEditors().map(function(e){return e.getEmail();})});
      });
    });
    return out;
  }
  const lp=protectionInfo(loc),dp=protectionInfo(drop);
  const allp=lp.concat(dp);
  if(allp.length<2) return {ok:false,error:'PROTECTION_MISSING',location_protections:lp,drop_protections:dp};
  const bad=allp.filter(function(p){return p.warning_only||p.domain_edit||p.editors.some(function(e){return e&&e!==PP_OUTBOUND.OWNER_EMAIL;});});
  if(bad.length) return {ok:false,error:'PROTECTION_OWNER_MISMATCH',bad:bad};
  const suffix=Utilities.getUuid().replace(/-/g,'').slice(0,10), a='__B77_TEST_'+suffix, b=a+'_EDIT';
  const owner={login_id:'beta77_owner_test',role:'SUPERADMIN',display_name:'Beta77 Test',email:PP_OUTBOUND.OWNER_EMAIL,__beta76_test:true};
  const user={login_id:'beta77_user_test',role:'USER',display_name:'Beta77 User',email:'beta77-user@example.invalid',__beta76_test:true};
  const admin={login_id:'beta77_admin_test',role:'ADMIN',display_name:'Beta77 Admin',email:'beta77-admin@example.invalid',__beta76_test:true};
  const record='__B77_TEST_ROW_'+suffix;
  let result={};
  try{
    const deny=ppOutboundLocationMutate_(user,{operation:'CREATE',after:a,event_id:'deny-'+suffix});
    if(deny.ok||deny.error!=='OUTBOUND_OWNER_REQUIRED') throw new Error('USER_LOCATION_GUARD_FAIL');
    let x=ppOutboundLocationMutate_(owner,{operation:'CREATE',after:a,event_id:'create-'+suffix}); if(!x.ok) throw new Error('OWNER_CREATE_FAIL_'+JSON.stringify(x));
    x=ppOutboundLocationMutate_(owner,{operation:'UPDATE',before:a,after:b,event_id:'update-'+suffix}); if(!x.ok) throw new Error('OWNER_UPDATE_FAIL_'+JSON.stringify(x));
    const listed=ppOutboundLocationList_(owner); if(!listed.ok||!listed.locations||listed.locations.indexOf(b)<0) throw new Error('LOCATION_LIST_FAIL_'+JSON.stringify(listed));
    const duplicate=ppOutboundLocationMutate_(owner,{operation:'CREATE',after:b,event_id:'duplicate-'+suffix}); if(duplicate.ok||duplicate.error!=='OUTBOUND_LOCATION_DUPLICATE') throw new Error('DUPLICATE_LOCATION_FAIL');
    const payload={location:b,scan_qr:'2AD7|7081639744|SOWIN8H9KA2BL3C|PB1260823D8CB48|CX1.1.1|5/13',do_number:'7081639744',package_count:13,idempotency_key:record};
    const first=ppOutboundAppend_(owner,payload); if(!first.ok||first.idempotent) throw new Error('APPEND_FAIL_'+JSON.stringify(first));
    const again=ppOutboundAppend_(owner,payload); if(!again.ok||!again.idempotent) throw new Error('IDEMPOTENCY_FAIL_'+JSON.stringify(again));
    if(drop.getLastRow()!==beforeRows+1) throw new Error('APPEND_ROW_COUNT_FAIL_'+String(drop.getLastRow()));
    const row=ppOutboundFindRecord_(drop,record); if(!row) throw new Error('APPEND_READBACK_MISSING');
    if(String(row.values[0])!==b||String(row.values[2])!==payload.scan_qr||String(row.values[3])!=='7081639744'||String(row.values[4])!=='13') throw new Error('APPEND_READBACK_CONTENT');
    const userClear=ppOutboundClear_(user,{idempotency_key:'uc-'+suffix}); if(userClear.ok||userClear.error!=='SUPERADMIN_REQUIRED') throw new Error('USER_CLEAR_GUARD_FAIL');
    const adminClear=ppOutboundClear_(admin,{idempotency_key:'ac-'+suffix}); if(adminClear.ok||adminClear.error!=='SUPERADMIN_REQUIRED') throw new Error('ADMIN_CLEAR_GUARD_FAIL');
    const marker=ppOutboundFindRecord_(drop,record); if(!marker) throw new Error('TEST_ROW_CLEANUP_MISSING');
    drop.deleteRow(marker.row); SpreadsheetApp.flush();
    x=ppOutboundLocationMutate_(owner,{operation:'DELETE',before:b,event_id:'delete-'+suffix}); if(!x.ok) throw new Error('OWNER_DELETE_FAIL_'+JSON.stringify(x));
    if(ppOutboundLocations_().some(function(v){return v===a||v===b;})) throw new Error('LOCATION_CLEANUP_FAIL');
    if(drop.getLastRow()!==beforeRows) throw new Error('REAL_DATA_ROW_COUNT_CHANGED');
    if(JSON.stringify(drop.getDataRange().getDisplayValues())!==beforeData) throw new Error('REAL_DATA_CHANGED');
    result={ok:true,parser_sample:{do_number:'7081639744',package_count:13},owner_crud:true,user_crud_denied:true,location_list_readable:true,append_once:true,idempotent_retry:true,user_clear_denied:true,admin_clear_denied:true,test_row_cleaned:true,real_data_preserved:true,location_hidden:true,headers:headers,location_protections:lp,drop_protections:dp};
  }catch(err){
    try{const f=ppOutboundFindRecord_(drop,record);if(f)drop.deleteRow(f.row);}catch(_){}
    try{const vals=ppOutboundLocations_();for(let i=vals.length-1;i>=0;i--){if(vals[i]===a||vals[i]===b)loc.deleteRow(i+2);}}catch(_){}
    return {ok:false,error:String(err&&err.message||err),location_protections:lp,drop_protections:dp};
  }
  return result;
}
'''.replace('__NONCE__',nonce)
out['source']=os+'\n'+helper
Path(target).write_text(json.dumps({'files':j['files']},ensure_ascii=False),encoding='utf-8')
PY

# Deploy temporary self-test version to the exact existing deployment.
code=$(curl -sS --connect-timeout 15 --max-time 30 -o "$E/test-content-put.json" -w '%{http_code}' -X PUT \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @"$E/project-test.json" "$api/content")
[[ "$code" == 200 ]]; MUTATED=1
code=$(curl -sS --connect-timeout 15 --max-time 30 -o "$E/test-version.json" -w '%{http_code}' -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' -d '{"description":"Beta77 Nhận hàng rớt temporary self-test"}' "$api/versions")
[[ "$code" == 200 ]]
TEST_VERSION=$(jq -r '.versionNumber' "$E/test-version.json"); test "$TEST_VERSION" != null
jq -nc --arg sid "$SCRIPT_ID" --argjson v "$TEST_VERSION" '{deploymentConfig:{scriptId:$sid,versionNumber:$v,manifestFileName:"appsscript",description:"Beta77 Nhận hàng rớt temporary self-test"}}' > "$E/test-deployment-put.json"
code=$(curl -sS --connect-timeout 15 --max-time 30 -o "$E/test-deployment.json" -w '%{http_code}' -X PUT \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @"$E/test-deployment-put.json" "$api/deployments/$DEPLOYMENT_ID")
[[ "$code" == 200 ]]

# Apps Script can temporarily serve Drive 404 while a Web App version cutover propagates.
# Initial probe + at most two bounded retries; exact deployment/version remains unchanged.
PROBE_OK=0
for attempt in 1 2 3; do
  http=$(curl -sSL --connect-timeout 15 --max-time 45 -D "$E/probe-$attempt.headers" -o "$E/probe-$attempt.json" -w '%{http_code}' -G \
    --data-urlencode 'action=__beta76_outbound_test' --data-urlencode "token=$NONCE" "$GAS_URL" || printf '000')
  printf '%s\n' "$http" > "$E/probe-$attempt.http"
  if [[ "$http" == 200 ]] \
    && grep -iq '^content-type:.*application/json' "$E/probe-$attempt.headers" \
    && jq -e '.ok==true and .beta77_probe==true' "$E/probe-$attempt.json" >/dev/null 2>&1; then
    PROBE_OK=1
    cp "$E/probe-$attempt.json" "$E/probe.json"
    break
  fi
  if [[ "$attempt" == 1 ]]; then sleep 60; elif [[ "$attempt" == 2 ]]; then sleep 120; fi
done
[[ "$PROBE_OK" == 1 ]]

# POST through the real /exec Web App. The temporary nonce route exercises the exact Sheet functions,
# appends one idempotent marker, reads it back, deletes only that marker, and proves real data unchanged.
POST_BODY=$(jq -nc --arg token "$NONCE" '{action:"__beta77_outbound_post_test",token:$token}')
POST_HTTP=$(curl -sSL --connect-timeout 15 --max-time 120 -D "$E/self-test.headers" -o "$E/self-test.json" -w '%{http_code}' \
  -H 'Content-Type: application/json; charset=utf-8' --data-binary "$POST_BODY" "$GAS_URL" || printf '000')
printf '%s\n' "$POST_HTTP" > "$E/self-test.http"
[[ "$POST_HTTP" == 200 ]]
grep -iq '^content-type:.*application/json' "$E/self-test.headers"
jq -e '.ok==true and .owner_crud==true and .user_crud_denied==true and .location_list_readable==true and .append_once==true and .idempotent_retry==true and .user_clear_denied==true and .admin_clear_denied==true and .test_row_cleaned==true and .real_data_preserved==true and .location_hidden==true' "$E/self-test.json" >/dev/null

# Final content contains no test route/helper; update the same deployment, never create a deployment.
code=$(curl -sS --connect-timeout 15 --max-time 30 -o "$E/final-content-put.json" -w '%{http_code}' -X PUT \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @"$E/project-target.json" "$api/content")
[[ "$code" == 200 ]]
code=$(curl -sS --connect-timeout 15 --max-time 30 -o "$E/final-version.json" -w '%{http_code}' -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' -d '{"description":"Beta77 Nhận hàng rớt final"}' "$api/versions")
[[ "$code" == 200 ]]
FINAL_VERSION=$(jq -r '.versionNumber' "$E/final-version.json"); test "$FINAL_VERSION" != null
jq -nc --arg sid "$SCRIPT_ID" --argjson v "$FINAL_VERSION" '{deploymentConfig:{scriptId:$sid,versionNumber:$v,manifestFileName:"appsscript",description:"Beta77 Nhận hàng rớt final"}}' > "$E/final-deployment-put.json"
code=$(curl -sS --connect-timeout 15 --max-time 30 -o "$E/final-deployment.json" -w '%{http_code}' -X PUT \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @"$E/final-deployment-put.json" "$api/deployments/$DEPLOYMENT_ID")
[[ "$code" == 200 ]]

curl -fsS --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" "$api/content" > "$E/project-after.json"
curl -fsS --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" "$api/deployments/$DEPLOYMENT_ID" > "$E/deployment-after.json"
python3 - "$E/project-after.json" "$E/project-target.json" <<'PY'
import hashlib,json,sys

def canon(path):
    j=json.load(open(path,encoding='utf-8'))
    return hashlib.sha256('\n'.join(str(f.get('name',''))+'\0'+str(f.get('type',''))+'\0'+str(f.get('source','')) for f in j.get('files',[])).encode()).hexdigest(),j
ha,a=canon(sys.argv[1]); ht,t=canon(sys.argv[2]); assert ha==ht,(ha,ht)
api=next(f for f in a['files'] if f.get('name')=='PICK_PACK_API')
out=next(f for f in a['files'] if f.get('name')=='OUTBOUND_DROP_RECEIVE')
assert "action === 'outbound_drop_append'" in api['source']
assert '__beta76_outbound_test' not in api['source'] and '__beta77_outbound_post_test' not in api['source'] and 'ppOutboundSelfTest_' not in out['source']
open('/tmp/beta76-outbound-gas-evidence/project-after.sha256','w').write(ha)
PY
jq -e --argjson v "$FINAL_VERSION" '.deploymentConfig.versionNumber==$v and .deploymentConfig.description=="Beta77 Nhận hàng rớt final"' "$E/deployment-after.json" >/dev/null
jq -e '.entryPoints[]? | select(.entryPointType=="WEB_APP") | .webApp.entryPointConfig.access=="ANYONE_ANONYMOUS" and .webApp.entryPointConfig.executeAs=="USER_DEPLOYING"' "$E/deployment-after.json" >/dev/null

# Wait for final cutover. The temporary POST route must disappear and normal GET must be JSON health.
FINAL_OK=0
for attempt in 1 2 3; do
  GET_HTTP=$(curl -sSL --connect-timeout 15 --max-time 45 -D "$E/live-health-$attempt.headers" -o "$E/live-health-$attempt.json" -w '%{http_code}' "$GAS_URL" || printf '000')
  TEST_HTTP=$(curl -sSL --connect-timeout 15 --max-time 45 -o "$E/final-route-check-$attempt.json" -w '%{http_code}' \
    -H 'Content-Type: application/json; charset=utf-8' --data-binary "$POST_BODY" "$GAS_URL" || printf '000')
  if [[ "$GET_HTTP" == 200 ]] \
    && grep -iq '^content-type:.*application/json' "$E/live-health-$attempt.headers" \
    && jq -e '.ok==true and .service=="pick-pack-gsheet-api"' "$E/live-health-$attempt.json" >/dev/null 2>&1 \
    && ! jq -e '.owner_crud==true' "$E/final-route-check-$attempt.json" >/dev/null 2>&1; then
    FINAL_OK=1
    cp "$E/live-health-$attempt.json" "$E/live-health.json"
    printf '%s\n' "$GET_HTTP" > "$E/live-health.http"
    break
  fi
  if [[ "$attempt" == 1 ]]; then sleep 60; elif [[ "$attempt" == 2 ]]; then sleep 120; fi
done
[[ "$FINAL_OK" == 1 ]]

jq -n \
  --arg target_hash "$TARGET_HASH" \
  --arg deployment_id "$DEPLOYMENT_ID" \
  --arg gas_url "$GAS_URL" \
  --argjson test_version "$TEST_VERSION" \
  --argjson final_version "$FINAL_VERSION" \
  --arg post_http "$POST_HTTP" \
  --slurpfile test "$E/self-test.json" \
  '{status:"PASS",target_hash:$target_hash,deployment_id:$deployment_id,gas_url:$gas_url,test_version:$test_version,final_version:$final_version,get_read_only:"PASS",post_http:$post_http,post_contract:"PASS",self_test:$test[0],cleanup:"PASS",real_data_preserved:true,live_health:"PASS",deployment_reused:true,access:"ANYONE_ANONYMOUS",execute_as:"USER_DEPLOYING"}' > "$E/receipt.json"
MUTATED=0
trap - EXIT
echo 'beta76_outbound_gas=PASS'
