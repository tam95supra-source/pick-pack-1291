#!/usr/bin/env bash
set -Eeuo pipefail

REQ=ops/beta-release-request.json
VIS=ops/beta71-visual-inspection.json
E=/tmp/beta71-evidence
mkdir -p "$E" /tmp/beta71-candidate
for n in GH_TOKEN GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN GAS_SCRIPT_ID GAS_DEPLOYMENT_ID; do
  test -n "${!n:-}"
done

TARGET_VERSION=$(jq -r '.version_name' "$REQ")
TARGET_CODE=$(jq -r '.version_code' "$REQ")
SOURCE_SHA=$(jq -r '.source_sha' "$REQ")
SOURCE_RUN_ID=$(jq -r '.candidate_run_id' "$REQ")
ARTIFACT_ID=$(jq -r '.candidate_artifact_id' "$REQ")
EXPECTED_SHA=$(jq -r '.apk_sha256' "$REQ")
EXPECTED_SIZE=$(jq -r '.apk_size' "$REQ")
APK_NAME=$(jq -r '.apk_file' "$REQ")
EXPECTED_SIGNER=d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e
PACKAGE=vn.pickpack1291.app.beta.publicbeta
BETA_FOLDER_ID=1WMXI-8-Z1mbY2v11noYFHe_eoMNiNZXg
GAS_URL=https://script.google.com/macros/s/AKfycbzbEoGfbNg6s2HnP-gUpcBJ7mMIkVBtYuQKMndb9seDV2c55lQwSUO1GZ-LtQ2CxMCauA/exec

test "$(jq -r '.stage' "$REQ")" = publish
test "$TARGET_VERSION" = 0.4.2-beta.71
test "$TARGET_CODE" = 77
test "$(jq -r '.verdict' "$VIS")" = PASS
test "$(jq -r '.candidate_run_id' "$VIS")" = "$SOURCE_RUN_ID"
test "$(jq -r '.candidate_artifact_id' "$VIS")" = "$ARTIFACT_ID"
test "$(jq -r '.apk_sha256' "$VIS")" = "$EXPECTED_SHA"
test "$(jq -r '.apk_size' "$VIS")" = "$EXPECTED_SIZE"
test "$(jq -r '.human_inspection' "$VIS")" = PASS
test "$(jq -r '.matrix' "$VIS")" = "320x568,360x640,480x800"

MAIN_BEFORE=$(curl -fsSL -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$GITHUB_REPOSITORY/branches/main" | jq -r '.commit.sha')
curl -fsSL -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.67"}' > "$E/beta-before.json"
curl -fsSL -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"STABLE","current_version":"0.1.0-stable"}' > "$E/stable-before.json"
jq -e '.ok==true and ((.version_name=="0.4.2-beta.68" and .version_code==74) or (.version_name=="0.4.2-beta.70" and .sha256=="f4113bf8ffb330cd5ebf51f06a5fd211be04323546d28e4e04dec498d1d83899" and .size==13114245) or (.version_name=="0.4.2-beta.71" and .sha256=="5a8e29f5d50ac31010ebe2cd6e6096ffdd8bcd2b354007a7448878ae6eefec3b" and .size==13114245))' "$E/beta-before.json" >/dev/null
jq -e '.ok==true' "$E/stable-before.json" >/dev/null

curl -fsSL -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' \
  "https://api.github.com/repos/$GITHUB_REPOSITORY/actions/artifacts/$ARTIFACT_ID/zip" -o /tmp/beta71-candidate.zip
unzip -q /tmp/beta71-candidate.zip -d /tmp/beta71-candidate
APK=$(find /tmp/beta71-candidate -type f -name "$APK_NAME" -print -quit)
META=$(find /tmp/beta71-candidate -type f -name release-meta.json -print -quit)
SUM=$(find /tmp/beta71-candidate -type f -name 'SHA256SUMS-*.txt' -print -quit)
test -n "$APK" -a -n "$META" -a -n "$SUM"
test "$(sha256sum "$APK" | awk '{print $1}')" = "$EXPECTED_SHA"
test "$(stat -c '%s' "$APK")" = "$EXPECTED_SIZE"
grep -qx "$EXPECTED_SHA  $APK_NAME" "$SUM"
jq -e --arg v "$TARGET_VERSION" --argjson c "$TARGET_CODE" --arg p "$PACKAGE" --arg s "$SOURCE_SHA" --arg h "$EXPECTED_SHA" --argjson z "$EXPECTED_SIZE" --arg signer "$EXPECTED_SIGNER" \
  '.version_name==$v and .version_code==$c and .package==$p and .source_sha==$s and .apk_sha256==$h and .apk_size==$z and .signer_sha256==$signer and .stable_publish=="FORBIDDEN"' "$META" >/dev/null
cp "$META" "$E/release-meta.json"

RESP=$(curl -fsS https://oauth2.googleapis.com/token -H 'Content-Type: application/x-www-form-urlencoded' \
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

curl -fsS -H "Authorization: Bearer $ACCESS_TOKEN" "https://script.googleapis.com/v1/projects/$SCRIPT_ID/content" > /tmp/gas-original.json
curl -fsS -H "Authorization: Bearer $ACCESS_TOKEN" "https://script.googleapis.com/v1/projects/$SCRIPT_ID/deployments/$DEPLOYMENT_ID" > /tmp/gas-deployment-before.json
python3 - <<'PY'
import hashlib,json
j=json.load(open('/tmp/gas-original.json'))
assert any(f.get('name')=='PICK_PACK_API' and f.get('source') for f in j.get('files',[]))
canon='\n'.join(f.get('name','')+'\0'+f.get('type','')+'\0'+f.get('source','') for f in j.get('files',[]))
open('/tmp/gas-original.sha256','w').write(hashlib.sha256(canon.encode()).hexdigest())
PY

HDR=$(mktemp)
curl -sS -D "$HDR" -o /dev/null -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' \
  "https://api.github.com/repos/$GITHUB_REPOSITORY/actions/artifacts/$ARTIFACT_ID/zip"
ARTIFACT_URL=$(awk 'BEGIN{IGNORECASE=1}/^location:/{sub(/\r$/,"");sub(/^location:[[:space:]]*/,"");print;exit}' "$HDR")
[[ "$ARTIFACT_URL" == https://* ]]
echo "::add-mask::$ARTIFACT_URL"

MUTATED=0
restore_gas() {
  if test "$MUTATED" != 1; then return 0; fi
  jq '{files:.files}' /tmp/gas-original.json > /tmp/gas-restore.json
  test "$(curl -sS -o /tmp/restore-put.out -w '%{http_code}' -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/gas-restore.json "https://script.googleapis.com/v1/projects/$SCRIPT_ID/content")" = 200
  test "$(curl -sS -o /tmp/restore-ver.json -w '%{http_code}' -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' -d '{"description":"Restore exact pre-Beta71 source"}' "https://script.googleapis.com/v1/projects/$SCRIPT_ID/versions")" = 200
  V=$(jq -r '.versionNumber' /tmp/restore-ver.json)
  jq -nc --arg sid "$SCRIPT_ID" --argjson v "$V" '{deploymentConfig:{scriptId:$sid,versionNumber:$v,manifestFileName:"appsscript",description:"Restore exact pre-Beta71 source"}}' > /tmp/restore-deploy.json
  test "$(curl -sS -o /tmp/restore-deploy.out -w '%{http_code}' -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/restore-deploy.json "https://script.googleapis.com/v1/projects/$SCRIPT_ID/deployments/$DEPLOYMENT_ID")" = 200
  curl -fsS -H "Authorization: Bearer $ACCESS_TOKEN" "https://script.googleapis.com/v1/projects/$SCRIPT_ID/content" > /tmp/gas-restored.json
  python3 - <<'PY'
import hashlib,json
j=json.load(open('/tmp/gas-restored.json'))
canon='\n'.join(f.get('name','')+'\0'+f.get('type','')+'\0'+f.get('source','') for f in j.get('files',[]))
assert hashlib.sha256(canon.encode()).hexdigest()==open('/tmp/gas-original.sha256').read().strip()
PY
  MUTATED=0
}
trap 'rc=$?; restore_gas || rc=99; exit $rc' EXIT

NONCE=$(openssl rand -hex 32)
echo "::add-mask::$NONCE"
python3 - "$NONCE" "$APK_NAME" "$EXPECTED_SHA" "$EXPECTED_SIZE" "$SOURCE_RUN_ID" <<'PY'
import json,sys
nonce,name,sha,size,run=sys.argv[1:]
j=json.load(open('/tmp/gas-original.json'))
f=next(x for x in j['files'] if x.get('name')=='PICK_PACK_API')
anchor="    if (action === 'health') return ppJson_(ppHealth_());"
assert anchor in f['source']
route="    if (action === '__beta71_exact_drive_upload') return ppJson_(ppBeta71ExactDriveUploadTmp_(body));"
notes="• Lịch sử thuần Việt, rõ ai làm gì và thời gian.\n• Chi tiết Mạng, Đồng bộ, Dịch vụ chính xác hơn.\n• Cảnh báo đối soát vào / ra ca nhấp nháy khi lệch.\n• Đổi / Trả PDA chuyên nghiệp, chỉ hiện PDA đang dùng kể cả Service lỗi.\n• Vuốt cạnh quay lại màn trước trong ứng dụng.\n• Diễn biến trong ca hiển thị đúng thay đổi công việc."
helper=f'''
function ppBeta71ExactDriveUploadTmp_(body){{
  if(String(body.token||'')!={json.dumps(nonce)})return {{ok:false,error:'FORBIDDEN'}};
  if(String(body.folder_id||'')!=='1WMXI-8-Z1mbY2v11noYFHe_eoMNiNZXg')return {{ok:false,error:'TARGET_MISMATCH'}};
  const expected={json.dumps(sha)},expectedSize={int(size)},apkName={json.dumps(name)},sumName='SHA256SUMS-0.4.2-beta.71.txt';
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

test "$(curl -sS -o /tmp/helper-put.out -w '%{http_code}' -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/gas-helper.json "https://script.googleapis.com/v1/projects/$SCRIPT_ID/content")" = 200
MUTATED=1
test "$(curl -sS -o /tmp/helper-ver.json -w '%{http_code}' -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' -d '{"description":"TEMP Beta71 exact Drive upload"}' "https://script.googleapis.com/v1/projects/$SCRIPT_ID/versions")" = 200
V=$(jq -r '.versionNumber' /tmp/helper-ver.json)
jq -nc --arg sid "$SCRIPT_ID" --argjson v "$V" '{deploymentConfig:{scriptId:$sid,versionNumber:$v,manifestFileName:"appsscript",description:"TEMP Beta71 exact Drive upload"}}' > /tmp/helper-deploy.json
test "$(curl -sS -o /tmp/helper-deploy.out -w '%{http_code}' -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/helper-deploy.json "https://script.googleapis.com/v1/projects/$SCRIPT_ID/deployments/$DEPLOYMENT_ID")" = 200

jq -nc --arg token "$NONCE" --arg folder "$BETA_FOLDER_ID" --arg url "$ARTIFACT_URL" \
  '{action:"__beta71_exact_drive_upload",token:$token,folder_id:$folder,artifact_url:$url}' > /tmp/transport-request.json
OK=false
for i in 1 2 3 4 5 6; do
  curl -fsSL --retry 1 -H 'content-type: application/json' "$GAS_URL" --data-binary @/tmp/transport-request.json > "$E/drive-transport.json" || true
  if jq -e --arg h "$EXPECTED_SHA" --argjson z "$EXPECTED_SIZE" --arg n "$APK_NAME" '.ok==true and .sha256==$h and .size==$z and .apk_name==$n' "$E/drive-transport.json" >/dev/null 2>&1; then OK=true; break; fi
  sleep $((i*3))
done
test "$OK" = true
DRIVE_ID=$(jq -r '.apk_file_id' "$E/drive-transport.json")
test -n "$DRIVE_ID"
restore_gas

PASS=false
for i in 1 2 3 4 5 6 7 8; do
  curl -fsSL -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.68"}' > "$E/beta-after.json"
  if jq -e --arg h "$EXPECTED_SHA" '.ok==true and .available==true and .version_name=="0.4.2-beta.71" and .sha256==$h and .size==13114245' "$E/beta-after.json" >/dev/null 2>&1; then PASS=true; break; fi
  sleep $((i*3))
done
test "$PASS" = true
curl -fsSL -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.71"}' > "$E/beta-current.json"
jq -e '.ok==true and .source=="GOOGLE_DRIVE" and .channel=="BETA" and .available==false and .version_name=="0.4.2-beta.71" and .size==13114245' "$E/beta-current.json" >/dev/null
LIVE_URL=$(jq -r '.apk_url // .download_url // .url // empty' "$E/beta-after.json")
[[ "$LIVE_URL" == https://* ]]
curl -fsSL -L --connect-timeout 15 --max-time 180 "$LIVE_URL" -o /tmp/beta71-live.apk
test "$(sha256sum /tmp/beta71-live.apk | awk '{print $1}')" = "$EXPECTED_SHA"
test "$(stat -c '%s' /tmp/beta71-live.apk)" = "$EXPECTED_SIZE"
curl -fsSL -L --connect-timeout 15 --max-time 180 "https://drive.usercontent.google.com/download?id=$DRIVE_ID&export=download&confirm=t" -o /tmp/beta71-drive.apk
test "$(sha256sum /tmp/beta71-drive.apk | awk '{print $1}')" = "$EXPECTED_SHA"

curl -fsSL -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"STABLE","current_version":"0.1.0-stable"}' > "$E/stable-after.json"
python3 - <<'PY'
import json
a=json.load(open('/tmp/beta71-evidence/stable-before.json'));b=json.load(open('/tmp/beta71-evidence/stable-after.json'))
keys=('source','channel','version_name','version_code','sha256','size','apk_url','available','reason')
assert {k:a.get(k) for k in keys}=={k:b.get(k) for k in keys}
PY
MAIN_AFTER=$(curl -fsSL -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$GITHUB_REPOSITORY/branches/main" | jq -r '.commit.sha')
test "$MAIN_AFTER" = "$MAIN_BEFORE"

jq -nc --argjson run "$GITHUB_RUN_ID" --arg source "$SOURCE_SHA" --argjson candidate_run "$SOURCE_RUN_ID" --argjson artifact "$ARTIFACT_ID" \
  --arg sha "$EXPECTED_SHA" --argjson size "$EXPECTED_SIZE" --arg signer "$EXPECTED_SIGNER" --arg drive "$DRIVE_ID" --arg url "$LIVE_URL" \
  '{verdict:"PASS",release_run_id:$run,source_sha:$source,candidate_run_id:$candidate_run,candidate_artifact_id:$artifact,version_name:"0.4.2-beta.71",version_code:77,package:"vn.pickpack1291.app.beta.publicbeta",apk_sha256:$sha,apk_size:$size,signer_sha256:$signer,drive_file_id:$drive,ota_url:$url,ota_live:"PASS",superseded_live_version:"0.4.2-beta.70",superseded_live_sha256:"f4113bf8ffb330cd5ebf51f06a5fd211be04323546d28e4e04dec498d1d83899",base_version:"0.4.2-beta.68",stable_unchanged:"PASS",main_unchanged:"PASS"}' \
  > ops/beta71-release-result.json
cp ops/beta71-release-result.json "$E/"
git config user.name github-actions[bot]
git config user.email 41898282+github-actions[bot]@users.noreply.github.com
git add ops/beta71-release-result.json
git commit -m 'ops: record Beta71 OTA PASS'
git push origin "HEAD:$GITHUB_REF_NAME"
trap - EXIT
