#!/usr/bin/env bash
set -Eeuo pipefail

: "${GH_TOKEN:?}"
: "${GOOGLE_OAUTH_CLIENT_ID:?}"
: "${GOOGLE_OAUTH_CLIENT_SECRET:?}"
: "${GOOGLE_OAUTH_REFRESH_TOKEN:?}"
: "${GAS_SCRIPT_ID:?}"
: "${GAS_DEPLOYMENT_ID:?}"

SOURCE_RUN_ID=32754196617
ARTIFACT_ID=9530301628
SOURCE_SHA=63917d672aeced142cacda925300978deef65277
TARGET_VERSION=0.4.2-beta.68
TARGET_CODE=74
TARGET_PACKAGE=vn.pickpack1291.app.beta.publicbeta
APK_NAME=pick-pack-1291-public-beta-0.4.2-beta.68.apk
EXPECTED_SHA=34554a19621be73ebc1e3bd64bef547959f5843f8d0fc902b5bcc8d573cf4641
EXPECTED_SIZE=13097861
EXPECTED_SIGNER_SHA256=d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e
EXPECTED_MAIN=a8c0c0d92522c7173230d4175b4f0d3a4906c8bb
BETA_FOLDER_ID=1WMXI-8-Z1mbY2v11noYFHe_eoMNiNZXg
DRIVE_APK_ID=19UqMJSUccpws03hXamgzBLER19lt_eay
TAG=v0.4.2-beta.68-publicbeta
GAS_URL='https://script.google.com/macros/s/AKfycbzbEoGfbNg6s2HnP-gUpcBJ7mMIkVBtYuQKMndb9seDV2c55lQwSUO1GZ-LtQ2CxMCauA/exec'
NOTES=$(cat <<'EOF'
Thiết kế lại màn đăng nhập đơn giản, chuyên nghiệp và đồng bộ toàn ứng dụng; giữ logo công ty và copyright.
Đổi / Trả PDA chỉ hiển thị PDA đang được sử dụng.
Hiển thị đúng Dữ liệu người dùng và Bộ nhớ đệm của ứng dụng.
Bật lại tự động kiểm tra OTA khi mở hoặc quay lại ứng dụng; không polling nền.
Bổ sung trạng thái chi tiết, chính xác cho Mạng, Đồng bộ và Dịch vụ.
EOF
)
export NOTES
mkdir -p /tmp/candidate /tmp/github-live

# Locked visual/candidate evidence.
grep -qx 'verdict=PASS' ops/beta68-v4-visual-inspection.txt
grep -qx "source_sha=$SOURCE_SHA" ops/beta68-v4-visual-inspection.txt
grep -qx "candidate_run_id=$SOURCE_RUN_ID" ops/beta68-v4-visual-inspection.txt
grep -qx "candidate_artifact_id=$ARTIFACT_ID" ops/beta68-v4-visual-inspection.txt
grep -qx "apk_sha256=$EXPECTED_SHA" ops/beta68-v4-visual-inspection.txt
grep -qx "apk_size=$EXPECTED_SIZE" ops/beta68-v4-visual-inspection.txt
grep -qx 'matrix=320x568,360x640,480x800' ops/beta68-v4-visual-inspection.txt
grep -qx 'login_model=SIMPLE_APP_THEME_V1' ops/beta68-v4-visual-inspection.txt
grep -qx 'human_inspection=PASS' ops/beta68-v4-visual-inspection.txt

MAIN_BEFORE=$(curl -fsSL -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$GITHUB_REPOSITORY/branches/main"|jq -r '.commit.sha')
[[ "$MAIN_BEFORE" == "$EXPECTED_MAIN" ]]
curl -fsSL -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"STABLE","current_version":"0.1.0-stable"}' > /tmp/stable-before.json
jq -e '.ok==true' /tmp/stable-before.json >/dev/null

curl -fsSL -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$GITHUB_REPOSITORY/actions/artifacts/$ARTIFACT_ID/zip" -o /tmp/candidate.zip
unzip -q /tmp/candidate.zip -d /tmp/candidate
APK=$(find /tmp/candidate -type f -name "$APK_NAME" -print -quit)
[[ -n "$APK" && -s "$APK" ]]
[[ "$(sha256sum "$APK"|awk '{print $1}')" == "$EXPECTED_SHA" ]]
[[ "$(stat -c '%s' "$APK")" == "$EXPECTED_SIZE" ]]
META=$(find /tmp/candidate -type f -name release-meta.json -print -quit)
jq -e --arg v "$TARGET_VERSION" --argjson c "$TARGET_CODE" --arg p "$TARGET_PACKAGE" --arg s "$SOURCE_SHA" --arg h "$EXPECTED_SHA" --argjson z "$EXPECTED_SIZE" --arg signer "$EXPECTED_SIGNER_SHA256" '.version_name==$v and .version_code==$c and .package==$p and .source_sha==$s and .apk_sha256==$h and .apk_size==$z and .signer_sha256==$signer and .stable_publish=="FORBIDDEN" and .visual_model=="SIMPLE_APP_THEME_V1"' "$META" >/dev/null

# Snapshot current GAS, install one-purpose metadata helper, then restore byte-for-byte source.
RESP=$(curl -fsS https://oauth2.googleapis.com/token -H 'Content-Type: application/x-www-form-urlencoded' --data-urlencode "client_id=$GOOGLE_OAUTH_CLIENT_ID" --data-urlencode "client_secret=$GOOGLE_OAUTH_CLIENT_SECRET" --data-urlencode "refresh_token=$GOOGLE_OAUTH_REFRESH_TOKEN" --data-urlencode 'grant_type=refresh_token')
ACCESS_TOKEN=$(jq -r '.access_token // empty' <<<"$RESP"); [[ -n "$ACCESS_TOKEN" ]]
SCRIPT_ID=$(printf '%s' "$GAS_SCRIPT_ID"|tr -d '\r\n\t ')
RAW=$(printf '%s' "$GAS_DEPLOYMENT_ID"|tr -d '\r\n\t '); DEPLOYMENT_ID="$RAW"; if [[ "$RAW" =~ /s/([^/]+)/ ]]; then DEPLOYMENT_ID="${BASH_REMATCH[1]}"; fi
echo "::add-mask::$ACCESS_TOKEN"; echo "::add-mask::$SCRIPT_ID"; echo "::add-mask::$DEPLOYMENT_ID"
curl -fsS -H "Authorization: Bearer $ACCESS_TOKEN" "https://script.googleapis.com/v1/projects/$SCRIPT_ID/content" > /tmp/gas-original.json
curl -fsS -H "Authorization: Bearer $ACCESS_TOKEN" "https://script.googleapis.com/v1/projects/$SCRIPT_ID/deployments/$DEPLOYMENT_ID" > /tmp/deploy-before.json
python3 - <<'PY'
import json,hashlib
j=json.load(open('/tmp/gas-original.json'))
assert any(f.get('name')=='PICK_PACK_API' and f.get('source') for f in j.get('files',[]))
canon='\n'.join(f.get('name','')+'\0'+f.get('type','')+'\0'+f.get('source','') for f in j.get('files',[]))
open('/tmp/gas-original.sha','w').write(hashlib.sha256(canon.encode()).hexdigest())
PY

GAS_MUTATED=0
restore_gas(){
  if [[ "$GAS_MUTATED" != 1 ]]; then return 0; fi
  jq '{files:.files}' /tmp/gas-original.json > /tmp/gas-restore.json
  H=$(curl -sS -o /tmp/restore-put.out -w '%{http_code}' -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/gas-restore.json "https://script.googleapis.com/v1/projects/$SCRIPT_ID/content")
  [[ "$H" == 200 ]] || return 1
  H=$(curl -sS -o /tmp/restore-ver.json -w '%{http_code}' -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' -d '{"description":"Restore exact source after Beta68 notes helper"}' "https://script.googleapis.com/v1/projects/$SCRIPT_ID/versions")
  [[ "$H" == 200 ]] || return 1
  V=$(jq -r '.versionNumber' /tmp/restore-ver.json); [[ "$V" =~ ^[0-9]+$ ]]
  jq -nc --arg sid "$SCRIPT_ID" --argjson v "$V" '{deploymentConfig:{scriptId:$sid,versionNumber:$v,manifestFileName:"appsscript",description:"Restore exact source after Beta68 notes helper"}}' > /tmp/restore-deploy.json
  H=$(curl -sS -o /tmp/restore-deploy.out -w '%{http_code}' -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/restore-deploy.json "https://script.googleapis.com/v1/projects/$SCRIPT_ID/deployments/$DEPLOYMENT_ID")
  [[ "$H" == 200 ]] || return 1
  curl -fsS -H "Authorization: Bearer $ACCESS_TOKEN" "https://script.googleapis.com/v1/projects/$SCRIPT_ID/content" > /tmp/gas-after.json
  python3 - <<'PY'
import json,hashlib
j=json.load(open('/tmp/gas-after.json')); canon='\n'.join(f.get('name','')+'\0'+f.get('type','')+'\0'+f.get('source','') for f in j.get('files',[]))
assert hashlib.sha256(canon.encode()).hexdigest()==open('/tmp/gas-original.sha').read().strip()
PY
  GAS_MUTATED=0
}
trap 'rc=$?; restore_gas || rc=99; exit $rc' EXIT

NONCE=$(openssl rand -hex 32); echo "::add-mask::$NONCE"
python3 - "$NONCE" <<'PY'
import json,sys,os
nonce=sys.argv[1]; notes=os.environ['NOTES']
j=json.load(open('/tmp/gas-original.json')); f=next(x for x in j['files'] if x.get('name')=='PICK_PACK_API'); s=f['source']
anchor="    if (action === 'health') return ppJson_(ppHealth_());"
assert anchor in s
route="    if (action === '__b68_notes_fix') return ppJson_(ppB68NotesFixTmp_(body));"
helper='''\nfunction ppB68NotesFixTmp_(body){\n  if(String(body.token||'')!=='__NONCE__')return {ok:false,error:'FORBIDDEN'};\n  if(String(body.file_id||'')!=='19UqMJSUccpws03hXamgzBLER19lt_eay'||String(body.folder_id||'')!=='1WMXI-8-Z1mbY2v11noYFHe_eoMNiNZXg')return {ok:false,error:'TARGET_MISMATCH'};\n  const f=DriveApp.getFileById(String(body.file_id)); if(f.getName()!=='pick-pack-1291-public-beta-0.4.2-beta.68.apk'||f.getSize()!==13097861)return {ok:false,error:'IDENTITY_MISMATCH'};\n  const sha=ppOtaSha256_(f); if(sha!=='34554a19621be73ebc1e3bd64bef547959f5843f8d0fc902b5bcc8d573cf4641')return {ok:false,error:'SHA_MISMATCH',sha256:sha};\n  const ps=f.getParents(); if(!ps.hasNext()||ps.next().getId()!=='1WMXI-8-Z1mbY2v11noYFHe_eoMNiNZXg')return {ok:false,error:'PARENT_MISMATCH'};\n  f.setDescription(__NOTES__);\n  return {ok:true,file_id:f.getId(),name:f.getName(),size:f.getSize(),sha256:sha,description:f.getDescription()};\n}\n'''.replace('__NONCE__',nonce).replace('__NOTES__',json.dumps(notes,ensure_ascii=False))
f['source']=s.replace(anchor,anchor+'\n'+route,1)+helper
open('/tmp/gas-helper.json','w').write(json.dumps({'files':j['files']},ensure_ascii=False))
PY
H=$(curl -sS -o /tmp/helper-put.out -w '%{http_code}' -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/gas-helper.json "https://script.googleapis.com/v1/projects/$SCRIPT_ID/content"); [[ "$H" == 200 ]]
GAS_MUTATED=1
H=$(curl -sS -o /tmp/helper-ver.json -w '%{http_code}' -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' -d '{"description":"TEMP Beta68 OTA notes helper"}' "https://script.googleapis.com/v1/projects/$SCRIPT_ID/versions"); [[ "$H" == 200 ]]
V=$(jq -r '.versionNumber' /tmp/helper-ver.json); [[ "$V" =~ ^[0-9]+$ ]]
jq -nc --arg sid "$SCRIPT_ID" --argjson v "$V" '{deploymentConfig:{scriptId:$sid,versionNumber:$v,manifestFileName:"appsscript",description:"TEMP Beta68 OTA notes helper"}}' > /tmp/helper-deploy.json
H=$(curl -sS -o /tmp/helper-deploy.out -w '%{http_code}' -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/helper-deploy.json "https://script.googleapis.com/v1/projects/$SCRIPT_ID/deployments/$DEPLOYMENT_ID"); [[ "$H" == 200 ]]

jq -nc --arg token "$NONCE" --arg file "$DRIVE_APK_ID" --arg folder "$BETA_FOLDER_ID" '{action:"__b68_notes_fix",token:$token,file_id:$file,folder_id:$folder}' > /tmp/notes-req.json
OK=false
for n in $(seq 1 20); do
  curl -fsSL -H 'content-type: application/json' "$GAS_URL" --data-binary @/tmp/notes-req.json > /tmp/notes-res.json || true
  if jq -e --arg h "$EXPECTED_SHA" --argjson z "$EXPECTED_SIZE" --arg notes "$NOTES" '.ok==true and .sha256==$h and .size==$z and .description==$notes' /tmp/notes-res.json >/dev/null 2>&1; then OK=true; break; fi
  sleep 3
done
[[ "$OK" == true ]] || { cat /tmp/notes-res.json; exit 1; }
restore_gas

# GitHub prerelease exact bytes and detailed changelog.
cat > /tmp/release-notes.md <<'EOF'
## Beta68
- Thiết kế lại màn đăng nhập đơn giản, chuyên nghiệp và đồng bộ toàn ứng dụng; giữ logo công ty và copyright.
- Đổi / Trả PDA chỉ hiển thị PDA đang được sử dụng.
- Hiển thị đúng Dữ liệu người dùng và Bộ nhớ đệm của ứng dụng.
- Bật lại tự động kiểm tra OTA khi mở hoặc quay lại ứng dụng; không polling nền.
- Bổ sung trạng thái chi tiết, chính xác cho Mạng, Đồng bộ và Dịch vụ.
EOF
TAG_SHA=$(git rev-list -n1 "$TAG" 2>/dev/null || true); [[ "$TAG_SHA" == "$SOURCE_SHA" ]]
gh release edit "$TAG" --prerelease --title "Pick Pack 1291 $TARGET_VERSION" --notes-file /tmp/release-notes.md
printf '%s  %s\n' "$EXPECTED_SHA" "$APK_NAME" > /tmp/SHA256SUMS-0.4.2-beta.68.txt
gh release upload "$TAG" "$APK" /tmp/SHA256SUMS-0.4.2-beta.68.txt --clobber
gh release download "$TAG" -p "$APK_NAME" -D /tmp/github-live
[[ "$(sha256sum /tmp/github-live/$APK_NAME|awk '{print $1}')" == "$EXPECTED_SHA" ]]
[[ "$(stat -c '%s' /tmp/github-live/$APK_NAME)" == "$EXPECTED_SIZE" ]]

# Live OTA readback. version_code is optional in the current GOOGLE_DRIVE response schema;
# when present it must equal 74. Exact downloaded bytes + candidate metadata prove code 74.
PASS=false
for n in $(seq 1 20); do
  curl -fsSL -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.66"}' > /tmp/ota-old.json
  if jq -e --arg v "$TARGET_VERSION" --argjson c "$TARGET_CODE" --arg h "$EXPECTED_SHA" --argjson z "$EXPECTED_SIZE" '.ok==true and .available==true and .version_name==$v and (.version_code==null or .version_code==$c) and .sha256==$h and .size==$z' /tmp/ota-old.json >/dev/null 2>&1; then
    python3 - <<'PY'
import json,os
j=json.load(open('/tmp/ota-old.json')); notes=j.get('notes','')
need=[
'Thiết kế lại màn đăng nhập đơn giản, chuyên nghiệp và đồng bộ toàn ứng dụng; giữ logo công ty và copyright.',
'Đổi / Trả PDA chỉ hiển thị PDA đang được sử dụng.',
'Hiển thị đúng Dữ liệu người dùng và Bộ nhớ đệm của ứng dụng.',
'Bật lại tự động kiểm tra OTA khi mở hoặc quay lại ứng dụng; không polling nền.',
'Bổ sung trạng thái chi tiết, chính xác cho Mạng, Đồng bộ và Dịch vụ.'
]
assert all(x in notes for x in need),notes
PY
    PASS=true; break
  fi
  sleep 3
done
[[ "$PASS" == true ]] || { cat /tmp/ota-old.json; exit 1; }
LIVE_URL=$(jq -r '.apk_url // empty' /tmp/ota-old.json); [[ "$LIVE_URL" == https://* ]]
curl -fsSL -L --connect-timeout 15 --max-time 120 "$LIVE_URL" -o /tmp/ota-live.apk
[[ "$(sha256sum /tmp/ota-live.apk|awk '{print $1}')" == "$EXPECTED_SHA" ]]
[[ "$(stat -c '%s' /tmp/ota-live.apk)" == "$EXPECTED_SIZE" ]]

curl -fsSL -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.68"}' > /tmp/ota-current.json
jq -e --arg v "$TARGET_VERSION" --argjson c "$TARGET_CODE" '.ok==true and .available==false and .version_name==$v and (.version_code==null or .version_code==$c)' /tmp/ota-current.json >/dev/null

curl -fsSL -H 'content-type: application/json' "$GAS_URL" -d '{"action":"update_check","channel":"STABLE","current_version":"0.1.0-stable"}' > /tmp/stable-after.json
python3 - <<'PY'
import json
a=json.load(open('/tmp/stable-before.json')); b=json.load(open('/tmp/stable-after.json'))
keys=('source','channel','version_name','version_code','sha256','size','apk_url','available','reason')
assert {k:a.get(k) for k in keys}=={k:b.get(k) for k in keys},(a,b)
PY
MAIN_AFTER=$(curl -fsSL -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$GITHUB_REPOSITORY/branches/main"|jq -r '.commit.sha')
[[ "$MAIN_AFTER" == "$EXPECTED_MAIN" ]]

# Persist immutable PASS receipt without touching main/stable.
git fetch origin release/beta68-exact-20260824
git checkout -B release/beta68-exact-20260824 origin/release/beta68-exact-20260824
cat > ops/beta68-v4-final-pass.txt <<EOF
verdict=PASS
released_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
version=0.4.2-beta.68
version_code=74
package=$TARGET_PACKAGE
source_sha=$SOURCE_SHA
candidate_run_id=$SOURCE_RUN_ID
candidate_artifact_id=$ARTIFACT_ID
apk_sha256=$EXPECTED_SHA
apk_size=$EXPECTED_SIZE
signer_sha256=$EXPECTED_SIGNER_SHA256
visual=PASS
visual_matrix=320x568,360x640,480x800
login_model=SIMPLE_APP_THEME_V1
ota_live=PASS
ota_source=$(jq -r '.source // empty' /tmp/ota-old.json)
ota_url=$LIVE_URL
ota_notes=PASS_5_ITEMS
github_prerelease=PASS
drive_file_id=$DRIVE_APK_ID
drive_exact_bytes=PASS
gas_source_restored=PASS
stable_unchanged=PASS
main_sha=$EXPECTED_MAIN
main_unchanged=PASS
EOF
git config user.name github-actions[bot]
git config user.email 41898282+github-actions[bot]@users.noreply.github.com
git add ops/beta68-v4-final-pass.txt
git commit -m 'ops: record Beta68 v4 OTA final PASS'
git push origin release/beta68-exact-20260824
trap - EXIT
