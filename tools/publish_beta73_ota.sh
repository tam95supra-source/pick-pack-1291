#!/usr/bin/env bash
set -Eeuo pipefail

REQ=ops/beta-release-request.json
VIS=ops/beta73-visual-inspection.json
E=/tmp/beta73-release-evidence
C=/tmp/beta73-candidate
mkdir -p "$E" "$C"

for n in GH_TOKEN GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN GAS_SCRIPT_ID GAS_DEPLOYMENT_ID; do
  test -n "${!n:-}"
done

TARGET_VERSION=0.4.2-beta.73
TARGET_CODE=79
SOURCE_SHA=2d726828bdd83efe21e9cd41db8d5c06d16f5272
SOURCE_RUN_ID=32820317675
ARTIFACT_ID=9552942024
EXPECTED_SHA=ad037c1a17d245f90ead59539c5595cc5df6a568b8657ce636cc43d101175fd2
EXPECTED_SIZE=13130629
EXPECTED_SIGNER=d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e
PACKAGE=vn.pickpack1291.app.beta.publicbeta
APK_NAME=pick-pack-1291-public-beta-0.4.2-beta.73.apk
BETA_FOLDER_ID=1WMXI-8-Z1mbY2v11noYFHe_eoMNiNZXg
GAS_URL=https://script.google.com/macros/s/AKfycbzbEoGfbNg6s2HnP-gUpcBJ7mMIkVBtYuQKMndb9seDV2c55lQwSUO1GZ-LtQ2CxMCauA/exec
EXPECTED_MAIN=a8c0c0d92522c7173230d4175b4f0d3a4906c8bb
PREV_VERSION=0.4.2-beta.72
PREV_CODE=78
PREV_SHA=fdeb006122f065591e82fe912a4a615c9c42a149568c2fc32f7d5b35db353caf
PREV_SIZE=13114245
VISUAL_RUN=32834871019
VISUAL_ARTIFACT=9558250565

jq -e --arg v "$TARGET_VERSION" --argjson c "$TARGET_CODE" --argjson r "$SOURCE_RUN_ID" --argjson a "$ARTIFACT_ID" --arg h "$EXPECTED_SHA" --argjson z "$EXPECTED_SIZE" \
  '.stage=="publish" and .version_name==$v and .version_code==$c and .locked_run_id==$r and .locked_artifact_id==$a and .locked_sha256==$h and .locked_size==$z' "$REQ" >/dev/null
jq -e --arg v "$TARGET_VERSION" --argjson c "$TARGET_CODE" --argjson r "$SOURCE_RUN_ID" --argjson a "$ARTIFACT_ID" --arg h "$EXPECTED_SHA" --argjson z "$EXPECTED_SIZE" --arg s "$EXPECTED_SIGNER" --argjson vr "$VISUAL_RUN" --argjson va "$VISUAL_ARTIFACT" \
  '.status=="PASS" and .result=="HUMAN_VISUAL_PASS" and .candidate.version_name==$v and .candidate.version_code==$c and .candidate.build_run==$r and .candidate.artifact_id==$a and .candidate.sha256==$h and .candidate.size==$z and .candidate.signer_sha256==$s and .visual.run_id==$vr and .visual.artifact_id==$va and .human_inspection["320x568"].nhat_ky_visible==true and .human_inspection["360x640"].nhat_ky_visible==true and .human_inspection["480x800"].nhat_ky_visible==true' "$VIS" >/dev/null

MAIN_BEFORE=$(curl -fsSL --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$GITHUB_REPOSITORY/branches/main" | jq -r '.commit.sha')
test "$MAIN_BEFORE" = "$EXPECTED_MAIN"
curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.71"}' > "$E/beta-before.json"
curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"STABLE","current_version":"0.1.0-stable"}' > "$E/stable-before.json"
jq -e --arg v "$PREV_VERSION" --argjson c "$PREV_CODE" --arg h "$PREV_SHA" --argjson z "$PREV_SIZE" '.ok==true and .version_name==$v and .version_code==$c and .sha256==$h and .size==$z' "$E/beta-before.json" >/dev/null
jq -e '.ok==true' "$E/stable-before.json" >/dev/null

curl -fsSL --connect-timeout 15 --max-time 180 -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' \
  "https://api.github.com/repos/$GITHUB_REPOSITORY/actions/artifacts/$ARTIFACT_ID/zip" -o /tmp/beta73-candidate.zip
unzip -q /tmp/beta73-candidate.zip -d "$C"
APK=$(find "$C" -type f -name "$APK_NAME" -print -quit)
META=$(find "$C" -type f -name release-meta.json -print -quit)
SUM=$(find "$C" -type f -name 'SHA256SUMS-*.txt' -print -quit)
test -n "$APK" -a -n "$META" -a -n "$SUM"
test "$(sha256sum "$APK" | awk '{print $1}')" = "$EXPECTED_SHA"
test "$(stat -c '%s' "$APK")" = "$EXPECTED_SIZE"
grep -qx "$EXPECTED_SHA  $APK_NAME" "$SUM"
jq -e --arg v "$TARGET_VERSION" --argjson c "$TARGET_CODE" --arg p "$PACKAGE" --arg s "$SOURCE_SHA" --arg h "$EXPECTED_SHA" --argjson z "$EXPECTED_SIZE" --arg signer "$EXPECTED_SIGNER" \
  '.version_name==$v and .version_code==$c and .package==$p and .source_sha==$s and .apk_sha256==$h and .apk_size==$z and .signer_sha256==$signer and .stable_publish=="FORBIDDEN" and .service_change=="NONE" and .gas_change=="FORGOT_PASSWORD_PREVIEW"' "$META" >/dev/null
cp "$META" "$E/release-meta.json"

RESP=$(curl -fsS --connect-timeout 15 --max-time 30 https://oauth2.googleapis.com/token -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "client_id=$GOOGLE_OAUTH_CLIENT_ID" \
  --data-urlencode "client_secret=$GOOGLE_OAUTH_CLIENT_SECRET" \
  --data-urlencode "refresh_token=$GOOGLE_OAUTH_REFRESH_TOKEN" \
  --data-urlencode grant_type=refresh_token)
ACCESS_TOKEN=$(jq -r '.access_token // empty' <<<"$RESP")
test -n "$ACCESS_TOKEN"
SCRIPT_ID=$(printf '%s' "$GAS_SCRIPT_ID" | tr -d '\r\n\t ')
RAW=$(printf '%s' "$GAS_DEPLOYMENT_ID" | tr -d '\r\n\t ')
DEPLOYMENT_ID="$RAW"
if [[ "$RAW" == *"/s/"* ]]; then DEPLOYMENT_ID="${RAW#*/s/}"; DEPLOYMENT_ID="${DEPLOYMENT_ID%%/*}"; fi
echo "::add-mask::$ACCESS_TOKEN"
echo "::add-mask::$SCRIPT_ID"
echo "::add-mask::$DEPLOYMENT_ID"

curl -fsS --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" "https://script.googleapis.com/v1/projects/$SCRIPT_ID/content" > /tmp/gas-original.json
curl -fsS --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" "https://script.googleapis.com/v1/projects/$SCRIPT_ID/deployments/$DEPLOYMENT_ID" > /tmp/gas-deployment-before.json
python3 - <<'PY'
import hashlib,json
j=json.load(open('/tmp/gas-original.json'))
assert any(f.get('name')=='PICK_PACK_API' and f.get('source') for f in j.get('files',[]))
canon='\n'.join(f.get('name','')+'\0'+f.get('type','')+'\0'+f.get('source','') for f in j.get('files',[]))
open('/tmp/gas-original.sha256','w').write(hashlib.sha256(canon.encode()).hexdigest())
PY

python3 - <<'PY'
import hashlib,json
j=json.load(open('/tmp/gas-original.json'))
f=next(x for x in j['files'] if x.get('name')=='PICK_PACK_API')
s=f['source']
route="    if (action === 'forgot_password_preview') return ppJson_(ppForgotPasswordPreview_(body));"
forgot="    if (action === 'forgot_password') return ppJson_(ppForgotPassword_(body));"
if route not in s:
    assert s.count(forgot)==1, 'forgot_password route anchor drift'
    s=s.replace(forgot,route+'\n'+forgot,1)
helper_sig='function ppForgotPasswordPreview_(body)'
if helper_sig not in s:
    anchor='function ppForgotPassword_(body)'
    assert s.count(anchor)==1, 'forgot password function anchor drift'
    helper=r'''function ppForgotPasswordPreview_(body) {
  const login=String((body&&body.login_id)||(body&&body.login)||(body&&body.username)||'').trim();
  if(!login) return {ok:false,error:'LOGIN_REQUIRED'};
  const device=String((body&&body.device_id)||'APP').trim().slice(0,80);
  const cache=CacheService.getScriptCache();
  const key=('PP_FP_PREVIEW_'+login+'_'+device).replace(/[^A-Za-z0-9_.-]/g,'_').slice(0,220);
  if(cache.get(key)) return {ok:false,error:'RATE_LIMIT'};
  cache.put(key,'1',10);
  const a=ppAccount_(login);
  if(!a) return {ok:false,error:'ACCOUNT_NOT_FOUND'};
  return {ok:true,login_id:String(a.login_id||a.login||login),email:String(a.email||'')};
}

'''
    s=s.replace(anchor,helper+anchor,1)
assert route in s and helper_sig in s
f['source']=s
open('/tmp/gas-target.json','w').write(json.dumps({'files':j['files']},ensure_ascii=False))
canon='\n'.join(x.get('name','')+'\0'+x.get('type','')+'\0'+x.get('source','') for x in j['files'])
open('/tmp/gas-target.sha256','w').write(hashlib.sha256(canon.encode()).hexdigest())
PY

HDR=$(mktemp)
curl -sS --connect-timeout 15 --max-time 30 -D "$HDR" -o /dev/null -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' \
  "https://api.github.com/repos/$GITHUB_REPOSITORY/actions/artifacts/$ARTIFACT_ID/zip"
ARTIFACT_URL=$(awk 'BEGIN{IGNORECASE=1}/^location:/{sub(/\r$/,"&");sub(/&$/,"\r");sub(/\r$/,"");sub(/^location:[[:space:]]*/,"");print;exit}' "$HDR")
[[ "$ARTIFACT_URL" == https://* ]]
echo "::add-mask::$ARTIFACT_URL"

MUTATED=0
restore_original() {
  if test "$MUTATED" != 1; then return 0; fi
  jq '{files:.files}' /tmp/gas-original.json > /tmp/gas-restore.json
  test "$(curl -sS --connect-timeout 15 --max-time 30 -o /tmp/restore-put.out -w '%{http_code}' -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/gas-restore.json "https://script.googleapis.com/v1/projects/$SCRIPT_ID/content")" = 200
  test "$(curl -sS --connect-timeout 15 --max-time 30 -o /tmp/restore-ver.json -w '%{http_code}' -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' -d '{"description":"Restore exact pre-Beta73 GAS source"}' "https://script.googleapis.com/v1/projects/$SCRIPT_ID/versions")" = 200
  V=$(jq -r '.versionNumber' /tmp/restore-ver.json)
  jq -nc --arg sid "$SCRIPT_ID" --argjson v "$V" '{deploymentConfig:{scriptId:$sid,versionNumber:$v,manifestFileName:"appsscript",description:"Restore exact pre-Beta73 GAS source"}}' > /tmp/restore-deploy.json
  test "$(curl -sS --connect-timeout 15 --max-time 30 -o /tmp/restore-deploy.out -w '%{http_code}' -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/restore-deploy.json "https://script.googleapis.com/v1/projects/$SCRIPT_ID/deployments/$DEPLOYMENT_ID")" = 200
  MUTATED=0
}
trap 'rc=$?; restore_original || rc=99; exit $rc' EXIT

NONCE=$(openssl rand -hex 32)
echo "::add-mask::$NONCE"
python3 - "$NONCE" "$APK_NAME" "$EXPECTED_SHA" "$EXPECTED_SIZE" "$SOURCE_RUN_ID" <<'PY'
import json,sys
nonce,name,sha,size,run=sys.argv[1:]
j=json.load(open('/tmp/gas-target.json'))
f=next(x for x in j['files'] if x.get('name')=='PICK_PACK_API')
anchor="    if (action === 'health') return ppJson_(ppHealth_());"
assert f['source'].count(anchor)==1
route="    if (action === '__beta73_exact_drive_upload') return ppJson_(ppBeta73ExactDriveUploadTmp_(body));"
notes="• Cập nhật công việc giữ trạng thái màn và ghi rõ trước/sau.\n• User Pick bắt buộc PDA; User Pack ràng buộc theo Bàn Pack.\n• Cài đặt hiển thị dung lượng thực, OTA chờ cài và nhật ký chi tiết.\n• Đăng nhập thống nhất copyright; quên mật khẩu xác nhận user + email liên kết."
helper=f'''
function ppBeta73ExactDriveUploadTmp_(body){{
  if(String(body.token||'')!={json.dumps(nonce)})return {{ok:false,error:'FORBIDDEN'}};
  if(String(body.folder_id||'')!=='1WMXI-8-Z1mbY2v11noYFHe_eoMNiNZXg')return {{ok:false,error:'TARGET_MISMATCH'}};
  const expected={json.dumps(sha)},expectedSize={int(size)},apkName={json.dumps(name)},sumName='SHA256SUMS-0.4.2-beta.73.txt';
  const r=UrlFetchApp.fetch(String(body.artifact_url||''),{{muteHttpExceptions:true,followRedirects:true}});if(r.getResponseCode()!==200)return {{ok:false,error:'FETCH_'+r.getResponseCode()}};
  let apk=null;Utilities.unzip(r.getBlob()).forEach(function(b){{if(String(b.getName()||'')===apkName)apk=b;}});if(!apk)return {{ok:false,error:'APK_MISSING'}};
  const bytes=apk.getBytes();if(bytes.length!==expectedSize)return {{ok:false,error:'SIZE_MISMATCH',size:bytes.length}};
  const dig=Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,bytes),actual=dig.map(function(b){{return ('0'+((b+256)%256).toString(16)).slice(-2);}}).join('');if(actual!==expected)return {{ok:false,error:'SHA_MISMATCH',sha256:actual}};
  const folder=DriveApp.getFolderById(String(body.folder_id));let file=null,it=folder.getFilesByName(apkName);
  while(it.hasNext()){{let x=it.next();if(x.getSize()===expectedSize){{let xb=x.getBlob().getBytes(),xd=Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,xb),xh=xd.map(function(b){{return ('0'+((b+256)%256).toString(16)).slice(-2);}}).join('');if(xh===expected){{file=x;break;}}}}}}
  if(!file)file=folder.createFile(apk.copyBlob().setName(apkName));
  file.setDescription({json.dumps(notes)}+'\\nSHA256 '+expected+'\\nCandidate run '+{json.dumps(run)});
  let sum=null,si=folder.getFilesByName(sumName);while(si.hasNext()){{let x=si.next();if(String(x.getBlob().getDataAsString()).indexOf(expected)>=0){{sum=x;break;}}}}if(!sum)sum=folder.createFile(sumName,expected+'  '+apkName+'\\n','text/plain');
  try{{file.setSharing(DriveApp.Access.ANYONE_WITH_LINK,DriveApp.Permission.VIEW);}}catch(_){{}}try{{sum.setSharing(DriveApp.Access.ANYONE_WITH_LINK,DriveApp.Permission.VIEW);}}catch(_){{}}
  return {{ok:true,apk_file_id:file.getId(),sum_file_id:sum.getId(),sha256:actual,size:file.getSize(),apk_name:file.getName()}};
}}
'''
f['source']=f['source'].replace(anchor,anchor+'\n'+route,1)+helper
open('/tmp/gas-helper.json','w').write(json.dumps({'files':j['files']},ensure_ascii=False))
PY

test "$(curl -sS --connect-timeout 15 --max-time 30 -o /tmp/helper-put.out -w '%{http_code}' -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/gas-helper.json "https://script.googleapis.com/v1/projects/$SCRIPT_ID/content")" = 200
MUTATED=1
test "$(curl -sS --connect-timeout 15 --max-time 30 -o /tmp/helper-ver.json -w '%{http_code}' -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' -d '{"description":"TEMP Beta73 exact Drive upload + preview target"}' "https://script.googleapis.com/v1/projects/$SCRIPT_ID/versions")" = 200
V=$(jq -r '.versionNumber' /tmp/helper-ver.json)
jq -nc --arg sid "$SCRIPT_ID" --argjson v "$V" '{deploymentConfig:{scriptId:$sid,versionNumber:$v,manifestFileName:"appsscript",description:"TEMP Beta73 exact Drive upload + preview target"}}' > /tmp/helper-deploy.json
test "$(curl -sS --connect-timeout 15 --max-time 30 -o /tmp/helper-deploy.out -w '%{http_code}' -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/helper-deploy.json "https://script.googleapis.com/v1/projects/$SCRIPT_ID/deployments/$DEPLOYMENT_ID")" = 200

jq -nc --arg token "$NONCE" --arg folder "$BETA_FOLDER_ID" --arg url "$ARTIFACT_URL" '{action:"__beta73_exact_drive_upload",token:$token,folder_id:$folder,artifact_url:$url}' > /tmp/transport-request.json
OK=false
for i in 1 2 3 4 5 6; do
  curl -fsSL --connect-timeout 15 --max-time 180 --retry 1 -H 'content-type: application/json' "$GAS_URL" --data-binary @/tmp/transport-request.json > "$E/drive-transport.json" || true
  if jq -e --arg h "$EXPECTED_SHA" --argjson z "$EXPECTED_SIZE" --arg n "$APK_NAME" '.ok==true and .sha256==$h and .size==$z and .apk_name==$n' "$E/drive-transport.json" >/dev/null 2>&1; then OK=true; break; fi
  sleep $((i*3))
done
test "$OK" = true
DRIVE_ID=$(jq -r '.apk_file_id' "$E/drive-transport.json")
SUM_ID=$(jq -r '.sum_file_id' "$E/drive-transport.json")
test -n "$DRIVE_ID" -a -n "$SUM_ID"

# Remove the temporary upload route but keep the approved forgot-password preview patch.
test "$(curl -sS --connect-timeout 15 --max-time 30 -o /tmp/target-put.out -w '%{http_code}' -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/gas-target.json "https://script.googleapis.com/v1/projects/$SCRIPT_ID/content")" = 200
test "$(curl -sS --connect-timeout 15 --max-time 30 -o /tmp/target-ver.json -w '%{http_code}' -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' -d '{"description":"Beta73 forgot password preview"}' "https://script.googleapis.com/v1/projects/$SCRIPT_ID/versions")" = 200
V=$(jq -r '.versionNumber' /tmp/target-ver.json)
jq -nc --arg sid "$SCRIPT_ID" --argjson v "$V" '{deploymentConfig:{scriptId:$sid,versionNumber:$v,manifestFileName:"appsscript",description:"Beta73 forgot password preview"}}' > /tmp/target-deploy.json
test "$(curl -sS --connect-timeout 15 --max-time 30 -o /tmp/target-deploy.out -w '%{http_code}' -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/target-deploy.json "https://script.googleapis.com/v1/projects/$SCRIPT_ID/deployments/$DEPLOYMENT_ID")" = 200

curl -fsS --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" "https://script.googleapis.com/v1/projects/$SCRIPT_ID/content" > /tmp/gas-live-target.json
python3 - <<'PY'
import hashlib,json
j=json.load(open('/tmp/gas-live-target.json'))
canon='\n'.join(f.get('name','')+'\0'+f.get('type','')+'\0'+f.get('source','') for f in j.get('files',[]))
assert hashlib.sha256(canon.encode()).hexdigest()==open('/tmp/gas-target.sha256').read().strip()
s=next(f['source'] for f in j['files'] if f.get('name')=='PICK_PACK_API')
assert "action === 'forgot_password_preview'" in s and 'function ppForgotPasswordPreview_(body)' in s
assert '__beta73_exact_drive_upload' not in s
PY

PREVIEW_OK=false
for i in 1 2 3 4 5 6; do
  curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL" -d '{"action":"forgot_password_preview","login_id":"tamnv2","device_id":"BETA73_RELEASE_VERIFY"}' > /tmp/preview-raw.json || true
  if jq -e '.ok==true and (.login_id|type=="string") and (.email|type=="string")' /tmp/preview-raw.json >/dev/null 2>&1; then PREVIEW_OK=true; break; fi
  sleep $((i*3))
done
test "$PREVIEW_OK" = true
jq '{ok,login_id,email_field_present:has("email")}' /tmp/preview-raw.json > "$E/forgot-preview-readback.json"

PASS=false
for i in 1 2 3 4 5 6 7 8; do
  curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.72"}' > "$E/beta-after.json"
  if jq -e --arg h "$EXPECTED_SHA" --argjson z "$EXPECTED_SIZE" '.ok==true and .available==true and .version_name=="0.4.2-beta.73" and .version_code==79 and .sha256==$h and .size==$z and ((.apk_url // .download_url // .url // "")|startswith("https://"))' "$E/beta-after.json" >/dev/null 2>&1; then PASS=true; break; fi
  sleep $((i*3))
done
test "$PASS" = true
curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.73"}' > "$E/beta-current.json"
jq -e --argjson z "$EXPECTED_SIZE" '.ok==true and .channel=="BETA" and .available==false and .version_name=="0.4.2-beta.73" and .version_code==79 and .size==$z' "$E/beta-current.json" >/dev/null
LIVE_URL=$(jq -r '.apk_url // .download_url // .url // empty' "$E/beta-after.json")
[[ "$LIVE_URL" == https://* ]]
curl -fsSL -L --connect-timeout 15 --max-time 180 "$LIVE_URL" -o /tmp/beta73-live.apk
test "$(sha256sum /tmp/beta73-live.apk | awk '{print $1}')" = "$EXPECTED_SHA"
test "$(stat -c '%s' /tmp/beta73-live.apk)" = "$EXPECTED_SIZE"
curl -fsSL -L --connect-timeout 15 --max-time 180 "https://drive.usercontent.google.com/download?id=$DRIVE_ID&export=download&confirm=t" -o /tmp/beta73-drive.apk
test "$(sha256sum /tmp/beta73-drive.apk | awk '{print $1}')" = "$EXPECTED_SHA"
test "$(stat -c '%s' /tmp/beta73-drive.apk)" = "$EXPECTED_SIZE"

curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"STABLE","current_version":"0.1.0-stable"}' > "$E/stable-after.json"
python3 - <<'PY'
import json
a=json.load(open('/tmp/beta73-release-evidence/stable-before.json')); b=json.load(open('/tmp/beta73-release-evidence/stable-after.json'))
keys=('source','channel','version_name','version_code','sha256','size','apk_url','available','reason')
assert {k:a.get(k) for k in keys}=={k:b.get(k) for k in keys}
PY
MAIN_AFTER=$(curl -fsSL --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$GITHUB_REPOSITORY/branches/main" | jq -r '.commit.sha')
test "$MAIN_AFTER" = "$MAIN_BEFORE"

jq -nc --argjson run "$GITHUB_RUN_ID" --arg source "$SOURCE_SHA" --argjson candidate_run "$SOURCE_RUN_ID" --argjson artifact "$ARTIFACT_ID" --argjson visual_run "$VISUAL_RUN" --argjson visual_artifact "$VISUAL_ARTIFACT" \
  --arg sha "$EXPECTED_SHA" --argjson size "$EXPECTED_SIZE" --arg signer "$EXPECTED_SIGNER" --arg drive "$DRIVE_ID" --arg sum "$SUM_ID" --arg url "$LIVE_URL" --arg main "$MAIN_AFTER" \
  '{verdict:"PASS",release_run_id:$run,source_sha:$source,candidate_run_id:$candidate_run,candidate_artifact_id:$artifact,visual_run_id:$visual_run,visual_artifact_id:$visual_artifact,version_name:"0.4.2-beta.73",version_code:79,package:"vn.pickpack1291.app.beta.publicbeta",apk_sha256:$sha,apk_size:$size,signer_sha256:$signer,signer_proof:"EXACT_BYTES_MATCH_LOCKED_CANDIDATE",drive_file_id:$drive,drive_checksum_file_id:$sum,ota_url:$url,ota_live:"PASS",forgot_password_preview_live:"PASS",superseded_live_version:"0.4.2-beta.72",superseded_live_sha256:"fdeb006122f065591e82fe912a4a615c9c42a149568c2fc32f7d5b35db353caf",stable_unchanged:"PASS",main_unchanged:"PASS",main_sha:$main,service_change:"NONE",authority_change:"NONE"}' > ops/beta73-release-result.json
cp ops/beta73-release-result.json "$E/"

git config user.name github-actions[bot]
git config user.email 41898282+github-actions[bot]@users.noreply.github.com
git add ops/beta73-release-result.json
git commit -m 'ops: record Beta73 OTA PASS'
git push origin "HEAD:$GITHUB_REF_NAME"
MUTATED=0
trap - EXIT
