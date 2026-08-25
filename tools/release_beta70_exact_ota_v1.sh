#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_RUN_ID=32792583861
ARTIFACT_ID=9543716011
SOURCE_SHA=23b3c1a786277bb3801ff2f481109a7b8e8f59a1
TARGET_VERSION=0.4.2-beta.70
TARGET_CODE=76
TARGET_PACKAGE=vn.pickpack1291.app.beta.publicbeta
APK_NAME=pick-pack-1291-public-beta-0.4.2-beta.70.apk
EXPECTED_SHA=f4113bf8ffb330cd5ebf51f06a5fd211be04323546d28e4e04dec498d1d83899
EXPECTED_SIZE=13114245
EXPECTED_SIGNER_SHA256=d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e
BETA_FOLDER_ID=1WMXI-8-Z1mbY2v11noYFHe_eoMNiNZXg
TAG=v0.4.2-beta.70-publicbeta
GAS_URL='https://script.google.com/macros/s/AKfycbzbEoGfbNg6s2HnP-gUpcBJ7mMIkVBtYuQKMndb9seDV2c55lQwSUO1GZ-LtQ2CxMCauA/exec'
BRANCH=release/beta70-pda-local-holder-fix-20260825

for n in GH_TOKEN GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN GAS_SCRIPT_ID GAS_DEPLOYMENT_ID; do
  [[ -n "${!n:-}" ]] || { echo "MISSING_REQUIRED_ENV:$n"; exit 10; }
done

mkdir -p /tmp/b70/evidence /tmp/b70/candidate /tmp/b70/github-live
RESULT=/tmp/b70/release-result
: > "$RESULT"
HELPER_INSTALLED=0
ACCESS_TOKEN=''
SCRIPT_ID=''
DEPLOYMENT_ID=''

restore_gas() {
  [[ "$HELPER_INSTALLED" == 1 ]] || return 0
  set +e
  echo 'RESTORE_GAS_BEGIN'
  jq '{files:.files}' /tmp/b70/live-original.json > /tmp/b70/original-put.json
  H=$(curl -sS -o /tmp/b70/restore-put.out -w '%{http_code}' -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/b70/original-put.json "https://script.googleapis.com/v1/projects/$SCRIPT_ID/content")
  if [[ "$H" != 200 ]]; then echo "RESTORE_SOURCE_HTTP_$H"; return 1; fi
  H=$(curl -sS -o /tmp/b70/restore-ver.json -w '%{http_code}' -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' -d '{"description":"Restore exact pre-Beta70 source after temporary Drive transport"}' "https://script.googleapis.com/v1/projects/$SCRIPT_ID/versions")
  if [[ "$H" != 200 ]]; then echo "RESTORE_VERSION_HTTP_$H"; return 1; fi
  V=$(jq -r '.versionNumber // empty' /tmp/b70/restore-ver.json)
  [[ "$V" =~ ^[0-9]+$ ]] || return 1
  jq -nc --arg sid "$SCRIPT_ID" --argjson v "$V" '{deploymentConfig:{scriptId:$sid,versionNumber:$v,manifestFileName:"appsscript",description:"Restore exact pre-Beta70 source"}}' > /tmp/b70/restore-deploy.json
  H=$(curl -sS -o /tmp/b70/restore-deploy.out -w '%{http_code}' -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/b70/restore-deploy.json "https://script.googleapis.com/v1/projects/$SCRIPT_ID/deployments/$DEPLOYMENT_ID")
  if [[ "$H" != 200 ]]; then echo "RESTORE_DEPLOY_HTTP_$H"; return 1; fi
  curl -fsS -H "Authorization: Bearer $ACCESS_TOKEN" "https://script.googleapis.com/v1/projects/$SCRIPT_ID/content" > /tmp/b70/live-after-restore.json || return 1
  python3 - <<'PY'
import json,hashlib
j=json.load(open('/tmp/b70/live-after-restore.json'))
canon='\n'.join(f.get('name','')+'\0'+f.get('type','')+'\0'+f.get('source','') for f in j.get('files',[]))
after=hashlib.sha256(canon.encode()).hexdigest()
before=open('/tmp/b70/original-canon.sha').read().strip()
assert after==before,(before,after)
open('/tmp/b70/evidence/gas-source-after.sha256','w').write(after+'\n')
PY
  RC=$?
  if [[ $RC == 0 ]]; then HELPER_INSTALLED=0; echo 'gas_source_restored=PASS' >> "$RESULT"; echo 'RESTORE_GAS_PASS'; fi
  return $RC
}
trap 'rc=$?; if [[ "$HELPER_INSTALLED" == 1 ]]; then restore_gas || rc=90; fi; exit $rc' EXIT

# A: lock visual PASS + fresh live authority.
V=ops/beta70-visual-inspection.txt
grep -qx 'verdict=PASS' "$V"
grep -qx "source_sha=$SOURCE_SHA" "$V"
grep -qx "candidate_run_id=$SOURCE_RUN_ID" "$V"
grep -qx "candidate_artifact_id=$ARTIFACT_ID" "$V"
grep -qx "apk_sha256=$EXPECTED_SHA" "$V"
grep -qx "apk_size=$EXPECTED_SIZE" "$V"
grep -qx "signer_sha256=$EXPECTED_SIGNER_SHA256" "$V"
grep -qx 'matrix=320x568,360x640,480x800' "$V"
grep -qx 'pda_local_holder_offline=PASS' "$V"
grep -qx 'service_error_preserves_local_holder=PASS' "$V"
grep -qx 'human_inspection=PASS' "$V"
MAIN_BEFORE=$(curl -fsSL -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$GITHUB_REPOSITORY/branches/main" | jq -r '.commit.sha')
[[ "$MAIN_BEFORE" =~ ^[0-9a-f]{40}$ ]]
curl -fsSL -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"STABLE","current_version":"0.1.0-stable"}' > /tmp/b70/stable-before.json
curl -fsSL -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.67"}' > /tmp/b70/beta-before.json
jq -e '.ok==true' /tmp/b70/stable-before.json >/dev/null
jq -e '.ok==true and .version_name=="0.4.2-beta.68" and .version_code==74' /tmp/b70/beta-before.json >/dev/null
OTA_SOURCE_BEFORE=$(jq -r '.source // empty' /tmp/b70/beta-before.json); [[ -n "$OTA_SOURCE_BEFORE" ]]
printf 'main_before=%s\nota_source_before=%s\nvisual_lock=PASS\n' "$MAIN_BEFORE" "$OTA_SOURCE_BEFORE" >> "$RESULT"
cp /tmp/b70/stable-before.json /tmp/b70/evidence/stable-before.json
cp /tmp/b70/beta-before.json /tmp/b70/evidence/beta-before.json

# B: exact locked candidate.
curl -fsSL -L -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$GITHUB_REPOSITORY/actions/artifacts/$ARTIFACT_ID/zip" -o /tmp/b70/candidate.zip
unzip -q /tmp/b70/candidate.zip -d /tmp/b70/candidate
APK=$(find /tmp/b70/candidate -type f -name "$APK_NAME" -print -quit)
META=$(find /tmp/b70/candidate -type f -name release-meta.json -print -quit)
SUM=$(find /tmp/b70/candidate -type f -name 'SHA256SUMS-*.txt' -print -quit)
[[ -n "$APK" && -s "$APK" && -n "$META" && -n "$SUM" ]]
[[ "$(sha256sum "$APK"|awk '{print $1}')" == "$EXPECTED_SHA" ]]
[[ "$(stat -c '%s' "$APK")" == "$EXPECTED_SIZE" ]]
grep -qx "$EXPECTED_SHA  $APK_NAME" "$SUM"
jq -e --arg v "$TARGET_VERSION" --argjson c "$TARGET_CODE" --arg p "$TARGET_PACKAGE" --arg s "$SOURCE_SHA" --arg h "$EXPECTED_SHA" --argjson z "$EXPECTED_SIZE" --arg signer "$EXPECTED_SIGNER_SHA256" '.version_name==$v and .version_code==$c and .package==$p and .source_sha==$s and .apk_sha256==$h and .apk_size==$z and .signer_sha256==$signer and .stable_publish=="FORBIDDEN"' "$META" >/dev/null
echo 'artifact_exact_bytes=PASS' >> "$RESULT"
cp "$META" /tmp/b70/evidence/release-meta.json

# C: OAuth + exact current GAS source/deployment + signed artifact URL.
RESP=$(curl -fsS https://oauth2.googleapis.com/token -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "client_id=$GOOGLE_OAUTH_CLIENT_ID" \
  --data-urlencode "client_secret=$GOOGLE_OAUTH_CLIENT_SECRET" \
  --data-urlencode "refresh_token=$GOOGLE_OAUTH_REFRESH_TOKEN" \
  --data-urlencode 'grant_type=refresh_token')
ACCESS_TOKEN=$(jq -r '.access_token // empty' <<<"$RESP"); [[ -n "$ACCESS_TOKEN" ]]
SCRIPT_ID=$(printf '%s' "$GAS_SCRIPT_ID"|tr -d '\r\n\t ')
RAW=$(printf '%s' "$GAS_DEPLOYMENT_ID"|tr -d '\r\n\t '); DEPLOYMENT_ID="$RAW"; if [[ "$RAW" =~ /s/([^/]+)/ ]]; then DEPLOYMENT_ID="${BASH_REMATCH[1]}"; fi
echo "::add-mask::$ACCESS_TOKEN"; echo "::add-mask::$SCRIPT_ID"; echo "::add-mask::$DEPLOYMENT_ID"
curl -fsS -H "Authorization: Bearer $ACCESS_TOKEN" "https://script.googleapis.com/v1/projects/$SCRIPT_ID/content" > /tmp/b70/live-original.json
curl -fsS -H "Authorization: Bearer $ACCESS_TOKEN" "https://script.googleapis.com/v1/projects/$SCRIPT_ID/deployments/$DEPLOYMENT_ID" > /tmp/b70/deployment-before.json
python3 - <<'PY'
import json,hashlib
j=json.load(open('/tmp/b70/live-original.json'))
assert any(f.get('name')=='PICK_PACK_API' and f.get('source') for f in j.get('files',[]))
canon='\n'.join(f.get('name','')+'\0'+f.get('type','')+'\0'+f.get('source','') for f in j.get('files',[]))
open('/tmp/b70/original-canon.sha','w').write(hashlib.sha256(canon.encode()).hexdigest())
PY
cp /tmp/b70/original-canon.sha /tmp/b70/evidence/gas-source-before.sha256
cp /tmp/b70/deployment-before.json /tmp/b70/evidence/gas-deployment-before.json
HDR=$(mktemp)
curl -sS -D "$HDR" -o /dev/null -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$GITHUB_REPOSITORY/actions/artifacts/$ARTIFACT_ID/zip"
ART_URL=$(awk 'BEGIN{IGNORECASE=1}/^location:/{sub(/\r$/,"");sub(/^location:[[:space:]]*/,"");print;exit}' "$HDR")
[[ "$ART_URL" == https://* ]]; echo "::add-mask::$ART_URL"

# D: temporary nonce-gated exact Drive transport helper.
NONCE=$(openssl rand -hex 32); echo "::add-mask::$NONCE"
python3 - "$NONCE" <<'PY'
import json,sys
nonce=sys.argv[1]
j=json.load(open('/tmp/b70/live-original.json'))
f=next(x for x in j['files'] if x.get('name')=='PICK_PACK_API')
s=f['source']
anchor="    if (action === 'health') return ppJson_(ppHealth_());"
if anchor not in s: raise SystemExit('HEALTH_ACTION_ANCHOR_MISSING')
route="    if (action === '__b70_exact_drive_backup') return ppJson_(ppB70ExactDriveBackupTmp_(body));"
s=s.replace(anchor,anchor+'\n'+route,1)
helper=r'''
function ppB70ExactDriveBackupTmp_(body){
  if(String(body.token||'')!=='__NONCE__')return {ok:false,error:'FORBIDDEN'};
  if(String(body.folder_id||'')!=='1WMXI-8-Z1mbY2v11noYFHe_eoMNiNZXg')return {ok:false,error:'TARGET_MISMATCH'};
  const expected=String(body.sha||'').toLowerCase(), expectedSize=Number(body.size||0), apkName='pick-pack-1291-public-beta-0.4.2-beta.70.apk', sumName='SHA256SUMS-0.4.2-beta.70.txt';
  const r=UrlFetchApp.fetch(String(body.artifact_url||''),{muteHttpExceptions:true,followRedirects:true}); if(r.getResponseCode()!==200)return {ok:false,error:'FETCH_'+r.getResponseCode()};
  const blobs=Utilities.unzip(r.getBlob()); let apk=null; blobs.forEach(function(b){if(String(b.getName()||'')===apkName)apk=b;}); if(!apk)return {ok:false,error:'APK_MISSING'};
  const bytes=apk.getBytes(); if(bytes.length!==expectedSize)return {ok:false,error:'SIZE_MISMATCH',size:bytes.length};
  const dig=Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,bytes), sha=dig.map(function(b){return ('0'+((b+256)%256).toString(16)).slice(-2);}).join(''); if(sha!==expected)return {ok:false,error:'SHA_MISMATCH',sha256:sha};
  const folder=DriveApp.getFolderById(String(body.folder_id)); let af=null,it=folder.getFilesByName(apkName);
  while(it.hasNext()){let x=it.next();if(x.getSize()===expectedSize){const xb=x.getBlob().getBytes(),xd=Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,xb),xh=xd.map(function(b){return ('0'+((b+256)%256).toString(16)).slice(-2);}).join('');if(xh===expected){af=x;break;}}}
  if(!af)af=folder.createFile(apk.copyBlob().setName(apkName));
  af.setDescription('Beta70 PDA local holder fix | SHA256 '+expected+' | exact candidate run 32792583861');
  let sf=null,si=folder.getFilesByName(sumName); while(si.hasNext()){let x=si.next();if(String(x.getBlob().getDataAsString()).indexOf(expected)>=0){sf=x;break;}} if(!sf)sf=folder.createFile(sumName,expected+'  '+apkName+'\n','text/plain');
  try{af.setSharing(DriveApp.Access.ANYONE_WITH_LINK,DriveApp.Permission.VIEW);}catch(_){} try{sf.setSharing(DriveApp.Access.ANYONE_WITH_LINK,DriveApp.Permission.VIEW);}catch(_){}
  return {ok:true,apk_file_id:af.getId(),sum_file_id:sf.getId(),sha256:sha,size:af.getSize(),apk_name:af.getName(),sum_name:sf.getName()};
}
'''.replace('__NONCE__',nonce)
f['source']=s+helper
open('/tmp/b70/helper-content.json','w').write(json.dumps({'files':j['files']},ensure_ascii=False))
PY
H=$(curl -sS -o /tmp/b70/helper-put.out -w '%{http_code}' -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/b70/helper-content.json "https://script.googleapis.com/v1/projects/$SCRIPT_ID/content"); [[ "$H" == 200 ]] || { cat /tmp/b70/helper-put.out; exit 1; }
HELPER_INSTALLED=1
H=$(curl -sS -o /tmp/b70/helper-ver.json -w '%{http_code}' -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' -d '{"description":"TEMP Beta70 exact Drive transport helper"}' "https://script.googleapis.com/v1/projects/$SCRIPT_ID/versions"); [[ "$H" == 200 ]] || { cat /tmp/b70/helper-ver.json; exit 1; }
HV=$(jq -r '.versionNumber // empty' /tmp/b70/helper-ver.json); [[ "$HV" =~ ^[0-9]+$ ]]
jq -nc --arg sid "$SCRIPT_ID" --argjson v "$HV" '{deploymentConfig:{scriptId:$sid,versionNumber:$v,manifestFileName:"appsscript",description:"TEMP Beta70 exact Drive transport helper"}}' > /tmp/b70/helper-deploy.json
H=$(curl -sS -o /tmp/b70/helper-deploy.out -w '%{http_code}' -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/b70/helper-deploy.json "https://script.googleapis.com/v1/projects/$SCRIPT_ID/deployments/$DEPLOYMENT_ID"); [[ "$H" == 200 ]] || { cat /tmp/b70/helper-deploy.out; exit 1; }

# E: exact locked bytes to canonical Beta Drive.
jq -nc --arg token "$NONCE" --arg folder "$BETA_FOLDER_ID" --arg url "$ART_URL" --arg sha "$EXPECTED_SHA" --argjson size "$EXPECTED_SIZE" '{action:"__b70_exact_drive_backup",token:$token,folder_id:$folder,artifact_url:$url,sha:$sha,size:$size}' > /tmp/b70/transport-request.json
OK=false
for i in $(seq 1 25); do
  curl -fsSL --retry 2 -H 'content-type: application/json' "$GAS_URL" --data-binary @/tmp/b70/transport-request.json > /tmp/b70/transport.json || true
  if jq -e --arg h "$EXPECTED_SHA" --argjson z "$EXPECTED_SIZE" --arg n "$APK_NAME" '.ok==true and .sha256==$h and .size==$z and .apk_name==$n' /tmp/b70/transport.json >/dev/null 2>&1; then OK=true; break; fi
  sleep 4
done
[[ "$OK" == true ]] || { cat /tmp/b70/transport.json; exit 1; }
DRIVE_APK_ID=$(jq -r '.apk_file_id' /tmp/b70/transport.json); DRIVE_SUM_ID=$(jq -r '.sum_file_id' /tmp/b70/transport.json); [[ -n "$DRIVE_APK_ID" && -n "$DRIVE_SUM_ID" ]]
cp /tmp/b70/transport.json /tmp/b70/evidence/drive-transport.json
printf 'drive_file_id=%s\ndrive_exact_bytes=PASS\n' "$DRIVE_APK_ID" >> "$RESULT"

# F: restore exact original GAS source before publishing authority.
restore_gas

# G: GitHub prerelease exact same bytes.
cat > /tmp/b70/release-notes.md <<'EOF'
## Beta70
- Sửa Đổi / Trả PDA: khi dịch vụ/master tạm lỗi, PDA đang active từ local state vẫn hiển thị và thao tác được.
- Không thay đổi Stable.

Exact signed candidate from run 32792583861 / artifact 9543716011.
EOF
printf '%s  %s\n' "$EXPECTED_SHA" "$APK_NAME" > /tmp/b70/SHA256SUMS-0.4.2-beta.70.txt
git fetch --tags origin
if gh release view "$TAG" >/dev/null 2>&1; then
  TAG_SHA=$(git rev-list -n1 "$TAG" 2>/dev/null || true); [[ "$TAG_SHA" == "$SOURCE_SHA" ]]
  gh release edit "$TAG" --prerelease --title "Pick Pack 1291 $TARGET_VERSION" --notes-file /tmp/b70/release-notes.md
else
  gh release create "$TAG" --target "$SOURCE_SHA" --prerelease --title "Pick Pack 1291 $TARGET_VERSION" --notes-file /tmp/b70/release-notes.md
fi
gh release upload "$TAG" "$APK" /tmp/b70/SHA256SUMS-0.4.2-beta.70.txt --clobber
gh release download "$TAG" -p "$APK_NAME" -D /tmp/b70/github-live
[[ "$(sha256sum /tmp/b70/github-live/$APK_NAME|awk '{print $1}')" == "$EXPECTED_SHA" ]]
[[ "$(stat -c '%s' /tmp/b70/github-live/$APK_NAME)" == "$EXPECTED_SIZE" ]]
printf 'github_prerelease=PASS\ngithub_tag=%s\ngithub_public_bytes=PASS\n' "$TAG" >> "$RESULT"

# H: fresh public OTA update_check + actual PDA URL download + Drive + Stable/main isolation.
PASS=false
for n in $(seq 1 25); do
  curl -fsSL -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.68"}' > /tmp/b70/ota-public.json
  if jq -e --arg v "$TARGET_VERSION" --argjson c "$TARGET_CODE" --arg h "$EXPECTED_SHA" --argjson z "$EXPECTED_SIZE" '.ok==true and .available==true and .version_name==$v and .version_code==$c and .sha256==$h and .size==$z' /tmp/b70/ota-public.json >/dev/null 2>&1; then PASS=true; break; fi
  sleep 4
done
[[ "$PASS" == true ]] || { cat /tmp/b70/ota-public.json; exit 1; }
OTA_SOURCE_AFTER=$(jq -r '.source // empty' /tmp/b70/ota-public.json); [[ "$OTA_SOURCE_AFTER" == "$OTA_SOURCE_BEFORE" ]]
curl -fsSL -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.70"}' > /tmp/b70/ota-current.json
jq -e --arg v "$TARGET_VERSION" --argjson c "$TARGET_CODE" '.ok==true and .available==false and .version_name==$v and .version_code==$c' /tmp/b70/ota-current.json >/dev/null
LIVE_URL=$(jq -r '.apk_url // .download_url // .url // empty' /tmp/b70/ota-public.json); [[ "$LIVE_URL" == https://* ]]
curl -fsSL -L --connect-timeout 15 --max-time 150 "$LIVE_URL" -o /tmp/b70/ota-public.apk
[[ "$(sha256sum /tmp/b70/ota-public.apk|awk '{print $1}')" == "$EXPECTED_SHA" ]]
[[ "$(stat -c '%s' /tmp/b70/ota-public.apk)" == "$EXPECTED_SIZE" ]]
SDKROOT=${ANDROID_HOME:-/usr/local/lib/android/sdk}
AAPT=$(find "$SDKROOT/build-tools" -type f -name aapt 2>/dev/null | sort -V | tail -1); [[ -n "$AAPT" ]]
BADGING=$($AAPT dump badging /tmp/b70/ota-public.apk | head -1)
grep -F "versionCode='76'" <<<"$BADGING"; grep -F "versionName='0.4.2-beta.70'" <<<"$BADGING"
APKSIGNER=$(find "$SDKROOT/build-tools" -type f -name apksigner 2>/dev/null | sort -V | tail -1); [[ -n "$APKSIGNER" ]]
$APKSIGNER verify --print-certs /tmp/b70/ota-public.apk > /tmp/b70/public-apksigner.txt
PUB_SIGNER=$(grep -im1 'certificate SHA-256 digest' /tmp/b70/public-apksigner.txt | sed -E 's/.*:[[:space:]]*//' | tr -d '\r' | tr '[:upper:]' '[:lower:]')
[[ "$PUB_SIGNER" == "$EXPECTED_SIGNER_SHA256" ]]
curl -fsSL -L --connect-timeout 15 --max-time 150 "https://drive.usercontent.google.com/download?id=$DRIVE_APK_ID&export=download&confirm=t" -o /tmp/b70/drive-public.apk
[[ "$(sha256sum /tmp/b70/drive-public.apk|awk '{print $1}')" == "$EXPECTED_SHA" ]]
[[ "$(stat -c '%s' /tmp/b70/drive-public.apk)" == "$EXPECTED_SIZE" ]]
curl -fsSL -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"STABLE","current_version":"0.1.0-stable"}' > /tmp/b70/stable-after.json
python3 - <<'PY'
import json
a=json.load(open('/tmp/b70/stable-before.json')); b=json.load(open('/tmp/b70/stable-after.json'))
keys=('source','channel','version_name','version_code','sha256','size','apk_url','available','reason')
assert {k:a.get(k) for k in keys}=={k:b.get(k) for k in keys},(a,b)
PY
MAIN_AFTER=$(curl -fsSL -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$GITHUB_REPOSITORY/branches/main"|jq -r '.commit.sha'); [[ "$MAIN_AFTER" == "$MAIN_BEFORE" ]]
cp /tmp/b70/ota-public.json /tmp/b70/evidence/update-check-beta70.json
cp /tmp/b70/ota-current.json /tmp/b70/evidence/update-check-beta70-current.json
cp /tmp/b70/stable-after.json /tmp/b70/evidence/stable-after.json
cp /tmp/b70/public-apksigner.txt /tmp/b70/evidence/public-apksigner.txt
printf '%s\n' "$BADGING" > /tmp/b70/evidence/public-apk-badging.txt
printf '%s\n' "$PUB_SIGNER" > /tmp/b70/evidence/public-apk-signer-sha256.txt
printf 'ota_live=PASS\nota_source=%s\nota_version=%s\nota_code=%s\nota_sha256=%s\nota_size=%s\nota_url=%s\npublic_apk_version=PASS\npublic_apk_code=PASS\npublic_apk_sha256=PASS\npublic_apk_size=PASS\npublic_apk_signer=%s\ndrive_public_bytes=PASS\nstable_unchanged=PASS\nmain_unchanged=PASS\n' "$OTA_SOURCE_AFTER" "$TARGET_VERSION" "$TARGET_CODE" "$EXPECTED_SHA" "$EXPECTED_SIZE" "$LIVE_URL" "$PUB_SIGNER" >> "$RESULT"

# I: immutable release receipt through contents API.
{
  echo 'verdict=PASS'
  echo "release_run_id=$GITHUB_RUN_ID"
  echo "released_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "source_sha=$SOURCE_SHA"
  echo "candidate_run_id=$SOURCE_RUN_ID"
  echo "candidate_artifact_id=$ARTIFACT_ID"
  echo "beta_name=$TARGET_VERSION"
  echo "beta_code=$TARGET_CODE"
  echo "package=$TARGET_PACKAGE"
  echo "apk_file=$APK_NAME"
  echo "apk_sha256=$EXPECTED_SHA"
  echo "apk_size=$EXPECTED_SIZE"
  echo "signer_sha256=$EXPECTED_SIGNER_SHA256"
  echo "beta_folder_id=$BETA_FOLDER_ID"
  cat "$RESULT"
  echo 'stable_name=0.1.0-stable'
  echo 'stable_code=1'
  echo 'stable_publish=FORBIDDEN'
} > /tmp/b70/final-receipt.txt
CONTENT=$(base64 -w0 /tmp/b70/final-receipt.txt)
PATHQ=ops/beta70-v1-release-result.txt
CURRENT=$(gh api "repos/${GITHUB_REPOSITORY}/contents/$PATHQ?ref=$BRANCH" --jq .sha 2>/dev/null || true)
args=(--method PUT "repos/${GITHUB_REPOSITORY}/contents/$PATHQ" -f message='ops: record Beta70 v1 exact OTA PASS' -f content="$CONTENT" -f branch="$BRANCH")
[[ -n "$CURRENT" ]] && args+=(-f sha="$CURRENT")
gh api "${args[@]}" >/dev/null
cat /tmp/b70/final-receipt.txt
