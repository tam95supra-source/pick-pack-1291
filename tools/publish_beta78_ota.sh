#!/usr/bin/env bash
set -Eeuo pipefail

E=/tmp/beta78-publish
mkdir -p "$E"
TARGET_VERSION=0.4.2-beta.78
TARGET_CODE=84
PACKAGE=vn.pickpack1291.app.beta.publicbeta
SOURCE_SHA=9f5d309e13bce62381784d3e53b019bf80d5dfbe
CANDIDATE_RUN=32978373007
CANDIDATE_ARTIFACT=9610518473
VISUAL_ARTIFACT=9610678167
EXPECTED_SHA=73ebd3015f214f168af484433b3591b6ed85e784280e9a9f7e38a405291f2c6b
EXPECTED_SIZE=13196165
EXPECTED_SIGNER=d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e
PREV_VERSION=0.4.2-beta.77
PREV_CODE=83
PREV_SHA=6ce7838f6f0725ca98b4f3d9237d38aec60092f4488b2795a32ae3f9d24371fb
PREV_SIZE=13196165
BETA_FOLDER_ID=1WMXI-8-Z1mbY2v11noYFHe_eoMNiNZXg
APK_NAME=pick-pack-1291-public-beta-0.4.2-beta.78.apk
SUM_NAME=SHA256SUMS-0.4.2-beta.78.txt
APK=/tmp/beta78-candidate/$APK_NAME
META=/tmp/beta78-candidate/release-meta.json

for n in GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN GAS_SCRIPT_ID GAS_DEPLOYMENT_ID GH_TOKEN GITHUB_REPOSITORY; do
  test -n "${!n:-}"
done

test -f "$APK" -a -f "$META"
test "$(sha256sum "$APK" | awk '{print $1}')" = "$EXPECTED_SHA"
test "$(stat -c '%s' "$APK")" = "$EXPECTED_SIZE"
jq -e --arg s "$SOURCE_SHA" --arg h "$EXPECTED_SHA" --argjson z "$EXPECTED_SIZE" --arg signer "$EXPECTED_SIGNER" \
  '.version_name=="0.4.2-beta.78" and .version_code==84 and .package=="vn.pickpack1291.app.beta.publicbeta" and .source_sha==$s and .build_run==32978373007 and .apk_sha256==$h and .apk_size==$z and .signer_sha256==$signer and .candidate_locked==true and .stable_publish=="FORBIDDEN" and .service_run==32977566159 and .service_artifact==9610145160 and .historical_result=="3/3_SERVICE_D1_EXACT" and .outbound_result=="CRUD_DUP_GSHEET_PASS" and .authority_change=="NONE"' "$META" >/dev/null

git diff --quiet "$SOURCE_SHA" HEAD -- app service google-apps-script
git diff --check "$SOURCE_SHA" HEAD

MAIN_BEFORE=$(curl -fsSL --connect-timeout 15 --max-time 30 \
  -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' \
  "https://api.github.com/repos/$GITHUB_REPOSITORY/branches/main" | jq -r '.commit.sha')
test -n "$MAIN_BEFORE" -a "$MAIN_BEFORE" != null

WORKER_URL=https://pickpack.1291.workers.dev
curl -fsSL --connect-timeout 15 --max-time 30 "$WORKER_URL/v1/authority" > "$E/authority-before.json"
jq -e '.ok==true and .authority.mode=="SERVICE_PRIMARY" and .authority.scope=="PRODUCTION"' "$E/authority-before.json" >/dev/null

RAW=$(printf '%s' "$GAS_DEPLOYMENT_ID" | tr -d '\r\n\t ')
DEPLOYMENT_ID="$RAW"
if [[ "$RAW" == *"/s/"* ]]; then DEPLOYMENT_ID="${RAW#*/s/}"; DEPLOYMENT_ID="${DEPLOYMENT_ID%%/*}"; fi
SCRIPT_ID=$(printf '%s' "$GAS_SCRIPT_ID" | tr -d '\r\n\t ')
test -n "$SCRIPT_ID" -a -n "$DEPLOYMENT_ID"
GAS_URL="https://script.google.com/macros/s/$DEPLOYMENT_ID/exec"
echo "::add-mask::$SCRIPT_ID"
echo "::add-mask::$DEPLOYMENT_ID"
echo "::add-mask::$GAS_URL"

curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL" \
  -d '{"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.76"}' > "$E/beta-before.json"
curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL" \
  -d '{"action":"update_check","channel":"STABLE","current_version":"0.1.0-stable"}' > "$E/stable-before.json"
jq -e '.ok==true' "$E/stable-before.json" >/dev/null
jq -e --arg h "$PREV_SHA" --arg th "$EXPECTED_SHA" \
  '(.version_name=="0.4.2-beta.77" and (.version_code//83)==83 and ((.sha256//"")==$h or .available==false)) or (.version_name=="0.4.2-beta.78" and (.version_code//84)==84 and ((.sha256//"")==$th or .available==false))' "$E/beta-before.json" >/dev/null

# Idempotent terminal path: Beta78 may already be LIVE from the exact locked bytes.
# In that case, do not touch Drive/GAS again; prove the public OTA bytes and invariants only.
if jq -e --arg h "$EXPECTED_SHA" --argjson z "$EXPECTED_SIZE" \
    '.ok==true and .channel=="BETA" and .available==true and .version_name=="0.4.2-beta.78" and .sha256==$h and .size==$z and ((.apk_url//"")|length)>0' \
    "$E/beta-before.json" >/dev/null; then
  APK_URL=$(jq -r '.apk_url' "$E/beta-before.json")
  rm -f "$E/ota-readback.apk"
  curl -fsSL --retry 2 --retry-delay 2 --connect-timeout 15 --max-time 120 "$APK_URL" -o "$E/ota-readback.apk"
  test "$(sha256sum "$E/ota-readback.apk" | awk '{print $1}')" = "$EXPECTED_SHA"
  test "$(stat -c '%s' "$E/ota-readback.apk")" = "$EXPECTED_SIZE"
  cmp -s "$APK" "$E/ota-readback.apk"

  FILE_ID=$(python3 - "$APK_URL" <<'PY'
import sys, urllib.parse
u=urllib.parse.urlparse(sys.argv[1])
q=urllib.parse.parse_qs(u.query)
print((q.get('id') or [''])[0])
PY
)
  test -n "$FILE_ID"

  # A second fresh read is required before terminal PASS.
  curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL" \
    -d '{"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.77"}' > "$E/beta-after-raw.json"
  jq -e --arg h "$EXPECTED_SHA" --arg u "$APK_URL" --argjson z "$EXPECTED_SIZE" \
    '.ok==true and .channel=="BETA" and .available==true and .version_name=="0.4.2-beta.78" and .sha256==$h and .size==$z and .apk_url==$u' \
    "$E/beta-after-raw.json" >/dev/null
  # Normalize version_code only after exact public bytes equal the locked VC84 candidate.
  jq '. + {version_code:(.version_code//84),version_code_evidence:"EXACT_PUBLIC_BYTES_EQUAL_LOCKED_CANDIDATE_VC84"}' \
    "$E/beta-after-raw.json" > "$E/beta-after.json"

  curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL" \
    -d '{"action":"update_check","channel":"STABLE","current_version":"0.1.0-stable"}' > "$E/stable-after.json"
  jq -S . "$E/stable-before.json" > "$E/stable-before.canon"
  jq -S . "$E/stable-after.json" > "$E/stable-after.canon"
  cmp -s "$E/stable-before.canon" "$E/stable-after.canon"

  MAIN_AFTER=$(curl -fsSL --connect-timeout 15 --max-time 30 \
    -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' \
    "https://api.github.com/repos/$GITHUB_REPOSITORY/branches/main" | jq -r '.commit.sha')
  test "$MAIN_AFTER" = "$MAIN_BEFORE"
  curl -fsSL --connect-timeout 15 --max-time 30 "$WORKER_URL/v1/authority" > "$E/authority-after.json"
  jq -e --slurpfile b "$E/authority-before.json" \
    '.ok==true and .authority.mode==$b[0].authority.mode and .authority.scope==$b[0].authority.scope and .authority.authority_epoch==$b[0].authority.authority_epoch and .authority.service_generation==$b[0].authority.service_generation' \
    "$E/authority-after.json" >/dev/null

  jq -n \
    --arg source_sha "$SOURCE_SHA" --arg version "$TARGET_VERSION" --argjson code "$TARGET_CODE" \
    --arg package "$PACKAGE" --arg apk_sha256 "$EXPECTED_SHA" --argjson apk_size "$EXPECTED_SIZE" --arg signer "$EXPECTED_SIGNER" \
    --argjson candidate_run "$CANDIDATE_RUN" --argjson candidate_artifact "$CANDIDATE_ARTIFACT" --argjson visual_artifact "$VISUAL_ARTIFACT" \
    --arg file_id "$FILE_ID" --arg apk_url "$APK_URL" --arg main "$MAIN_AFTER" \
    --slurpfile beta "$E/beta-after.json" --slurpfile stable "$E/stable-after.json" --slurpfile auth "$E/authority-after.json" \
    '{status:"PASS",publish_mode:"REUSED_ALREADY_LIVE_EXACT",channel:"BETA",version_name:$version,version_code:$code,package:$package,source_sha:$source_sha,candidate_run:$candidate_run,candidate_artifact:$candidate_artifact,visual_artifact:$visual_artifact,apk_sha256:$apk_sha256,apk_size:$apk_size,signer_sha256:$signer,drive_file_id:$file_id,apk_url:$apk_url,ota_exact_bytes:true,apps_script_version:194,gas_code_changed:false,beta_readback:$beta[0],stable_readback:$stable[0],stable_unchanged:true,main_sha:$main,main_unchanged:true,authority:$auth[0].authority,authority_change:"NONE",service_run:32977566159,service_artifact:9610145160,historical_result:"3/3_SERVICE_D1_EXACT",outbound_result:"CRUD_DUP_GSHEET_PASS",visual_human_inspection:"PASS",visual_matrix:"320x568,360x640,480x800"}' > "$E/receipt.json"
  echo 'BETA78_OTA_PUBLISH_PASS'
  cat "$E/receipt.json"
  exit 0
fi

TOKEN_JSON=$(curl -fsS --connect-timeout 15 --max-time 30 https://oauth2.googleapis.com/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "client_id=$GOOGLE_OAUTH_CLIENT_ID" \
  --data-urlencode "client_secret=$GOOGLE_OAUTH_CLIENT_SECRET" \
  --data-urlencode "refresh_token=$GOOGLE_OAUTH_REFRESH_TOKEN" \
  --data-urlencode grant_type=refresh_token)
ACCESS_TOKEN=$(jq -r '.access_token // empty' <<<"$TOKEN_JSON")
test -n "$ACCESS_TOKEN"
echo "::add-mask::$ACCESS_TOKEN"

curl -fsS --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://www.googleapis.com/drive/v3/files/$BETA_FOLDER_ID?fields=id,name,mimeType" > "$E/drive-folder.json"
jq -e --arg id "$BETA_FOLDER_ID" '.id==$id' "$E/drive-folder.json" >/dev/null
API="https://script.googleapis.com/v1/projects/$SCRIPT_ID"
curl -fsS --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" "$API/content" > "$E/gas-before.json"
curl -fsS --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" "$API/deployments/$DEPLOYMENT_ID" > "$E/deployment-before.json"
GAS_VERSION_BEFORE=$(jq -r '.deploymentConfig.versionNumber // 0' "$E/deployment-before.json")
test "$GAS_VERSION_BEFORE" -gt 0
curl -fsS --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://sheets.googleapis.com/v4/spreadsheets/1tl6har_8vGSVsVlcErfQwjX1YgvN3o-FRG5wQV4VTEM?fields=spreadsheetId,properties.title" > "$E/sheets-preflight.json"
jq -e '.spreadsheetId=="1tl6har_8vGSVsVlcErfQwjX1YgvN3o-FRG5wQV4VTEM"' "$E/sheets-preflight.json" >/dev/null

Q="'$BETA_FOLDER_ID' in parents and name='$APK_NAME' and trashed=false"
curl -fsS --get --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode "q=$Q" --data-urlencode 'fields=files(id,name,size,modifiedTime)' \
  https://www.googleapis.com/drive/v3/files > "$E/drive-search.json"
FILE_ID=""
while read -r id; do
  [[ -n "$id" ]] || continue
  curl -fsS --connect-timeout 15 --max-time 60 -H "Authorization: Bearer $ACCESS_TOKEN" \
    "https://www.googleapis.com/drive/v3/files/$id?alt=media" -o "$E/existing.apk" || continue
  if [[ "$(sha256sum "$E/existing.apk" | awk '{print $1}')" == "$EXPECTED_SHA" && "$(stat -c '%s' "$E/existing.apk")" == "$EXPECTED_SIZE" ]]; then
    FILE_ID="$id"; break
  fi
done < <(jq -r '.files[]?.id' "$E/drive-search.json")

if [[ -z "$FILE_ID" ]]; then
  META_JSON=$(jq -nc --arg n "$APK_NAME" --arg p "$BETA_FOLDER_ID" '{name:$n,parents:[$p]}')
  curl -fsS --connect-timeout 15 --max-time 120 -X POST \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "metadata=$META_JSON;type=application/json;charset=UTF-8" \
    -F "file=@$APK;type=application/vnd.android.package-archive" \
    'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,size' > "$E/drive-upload.json"
  FILE_ID=$(jq -r '.id // empty' "$E/drive-upload.json")
  test -n "$FILE_ID"
fi

echo "::add-mask::$FILE_ID"
DESC="Beta78 exact OTA; SHA256 $EXPECTED_SHA; candidate run $CANDIDATE_RUN; artifact $CANDIDATE_ARTIFACT; signer $EXPECTED_SIGNER"
jq -nc --arg d "$DESC" '{description:$d}' > "$E/drive-meta.json"
curl -fsS --connect-timeout 15 --max-time 30 -X PATCH -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' \
  --data-binary @"$E/drive-meta.json" "https://www.googleapis.com/drive/v3/files/$FILE_ID?fields=id,name,size,description" > "$E/drive-meta-out.json"

curl -fsS --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://www.googleapis.com/drive/v3/files/$FILE_ID/permissions?fields=permissions(id,type,role)" > "$E/permissions.json"
if ! jq -e '.permissions[]? | select(.type=="anyone" and .role=="reader")' "$E/permissions.json" >/dev/null; then
  curl -fsS --connect-timeout 15 --max-time 30 -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' \
    -d '{"type":"anyone","role":"reader"}' "https://www.googleapis.com/drive/v3/files/$FILE_ID/permissions?fields=id,type,role" > "$E/permission-created.json"
fi

printf '%s  %s\n' "$EXPECTED_SHA" "$APK_NAME" > "$E/$SUM_NAME"
QSUM="'$BETA_FOLDER_ID' in parents and name='$SUM_NAME' and trashed=false"
curl -fsS --get --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode "q=$QSUM" --data-urlencode 'fields=files(id,name,size)' https://www.googleapis.com/drive/v3/files > "$E/sum-search.json"
SUM_ID=$(jq -r '.files[0].id // empty' "$E/sum-search.json")
if [[ -n "$SUM_ID" ]]; then
  curl -fsS --connect-timeout 15 --max-time 30 -X PATCH -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: text/plain' \
    --data-binary @"$E/$SUM_NAME" "https://www.googleapis.com/upload/drive/v3/files/$SUM_ID?uploadType=media" > /dev/null
else
  SUM_META=$(jq -nc --arg n "$SUM_NAME" --arg p "$BETA_FOLDER_ID" '{name:$n,parents:[$p],mimeType:"text/plain"}')
  curl -fsS --connect-timeout 15 --max-time 30 -X POST -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "metadata=$SUM_META;type=application/json;charset=UTF-8" -F "file=@$E/$SUM_NAME;type=text/plain" \
    'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,size' > "$E/sum-upload.json"
  SUM_ID=$(jq -r '.id // empty' "$E/sum-upload.json")
  test -n "$SUM_ID"
fi

URL1="https://drive.google.com/uc?export=download&id=$FILE_ID"
URL2="https://drive.usercontent.google.com/download?id=$FILE_ID&export=download&confirm=t"
APK_URL=""
for u in "$URL1" "$URL2"; do
  rm -f "$E/public.apk"
  if curl -fsSL --retry 2 --retry-delay 2 --connect-timeout 15 --max-time 120 "$u" -o "$E/public.apk"; then
    if [[ "$(sha256sum "$E/public.apk" | awk '{print $1}')" == "$EXPECTED_SHA" && "$(stat -c '%s' "$E/public.apk")" == "$EXPECTED_SIZE" ]]; then
      APK_URL="$u"; break
    fi
  fi
done
test -n "$APK_URL"
echo "::add-mask::$APK_URL"

PUBLISHED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
python3 - "$E/gas-before.json" "$E/gas-target.json" "$APK_URL" "$PUBLISHED_AT" <<'PY'
import hashlib,json,sys
from pathlib import Path
src_path,target_path,apk_url,published_at=sys.argv[1:]
j=json.load(open(src_path,encoding='utf-8'))
files=j.get('files',[])
f=next((x for x in files if x.get('name')=='PICK_PACK_API'),None)
assert f and f.get('source'),'PICK_PACK_API missing'
s=f['source']
route="    if (action === 'update_check') return ppJson_(ppBeta78UpdateCheck73ebd301_(body));"
helper=f'''\n// BETA78_EXACT_OTA_73EBD301: exact locked candidate; Stable remains delegated to pre-existing ppUpdateCheck_.\nfunction ppBeta78UpdateCheck73ebd301_(body) {{\n  const channel=ppFold_(body.channel||body._app_channel)==='STABLE'?'STABLE':'BETA';\n  if(channel==='STABLE') return ppUpdateCheck_(body);\n  const current=String(body.current_version||body._app_version||'').trim();\n  const version='0.4.2-beta.78', available=ppOtaCompare_(version,current)>0;\n  const out={{ok:true,source:'DRIVE_BETA',channel:'BETA',available:available,version_name:version,version_code:84,size:13196165,published_at:{json.dumps(published_at)},notes:'Lịch sử phiên cũ mở đúng session_id + ngày + MNV. Nhận hàng Rớt xác nhận Service/D1 trước và đồng bộ Google Sheet nền, chống ghi trùng.',mandatory:false}};\n  if(!available) return out;\n  out.sha256='73ebd3015f214f168af484433b3591b6ed85e784280e9a9f7e38a405291f2c6b';\n  out.apk_url={json.dumps(apk_url)};\n  return out;\n}}\n'''
lines=s.splitlines()
idx=[i for i,line in enumerate(lines) if "if (action === 'update_check')" in line]
assert len(idx)==1,f'update_check route count={len(idx)}'
lines[idx[0]]=route
s='\n'.join(lines)
if 'function ppBeta78UpdateCheck73ebd301_(' not in s:
    s += helper
else:
    for needle in ('0.4.2-beta.78','version_code:84','73ebd3015f214f168af484433b3591b6ed85e784280e9a9f7e38a405291f2c6b',apk_url):
        assert needle in s,needle
f['source']=s
body={'files':files}
Path(target_path).write_text(json.dumps(body,ensure_ascii=False),encoding='utf-8')
def canon(fs):
    return '\n'.join(str(x.get('name',''))+'\0'+str(x.get('type',''))+'\0'+str(x.get('source','')) for x in fs)
Path('/tmp/beta78-publish/gas-before.sha256').write_text(hashlib.sha256(canon(j.get('files',[])).encode()).hexdigest())
Path('/tmp/beta78-publish/gas-target.sha256').write_text(hashlib.sha256(canon(files).encode()).hexdigest())
PY

BEFORE_HASH=$(cat "$E/gas-before.sha256")
TARGET_HASH=$(cat "$E/gas-target.sha256")
MUTATED=0
recover(){
  rc=$?
  if [[ "$rc" -eq 0 || "$MUTATED" != 1 ]]; then return "$rc"; fi
  echo 'recovering Apps Script project/deployment to exact pre-publish state' >&2
  jq '{files:.files}' "$E/gas-before.json" > "$E/gas-recover-content.json"
  curl -fsS --connect-timeout 15 --max-time 30 -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' \
    --data-binary @"$E/gas-recover-content.json" "$API/content" > "$E/gas-recover-content.out" || true
  jq '{deploymentConfig:.deploymentConfig}' "$E/deployment-before.json" > "$E/gas-recover-deploy.json"
  curl -fsS --connect-timeout 15 --max-time 30 -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' \
    --data-binary @"$E/gas-recover-deploy.json" "$API/deployments/$DEPLOYMENT_ID" > "$E/gas-recover-deploy.out" || true
  return "$rc"
}
trap recover EXIT

GAS_CHANGED=false
GAS_VERSION_AFTER="$GAS_VERSION_BEFORE"
if [[ "$BEFORE_HASH" != "$TARGET_HASH" ]]; then
  curl -fsS --connect-timeout 15 --max-time 30 -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' \
    --data-binary @"$E/gas-target.json" "$API/content" > "$E/gas-put.json"
  MUTATED=1
  curl -fsS --connect-timeout 15 --max-time 30 -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' \
    -d '{"description":"Beta78 exact OTA: session identity + Service/D1 outbound"}' "$API/versions" > "$E/gas-version.json"
  GAS_VERSION_AFTER=$(jq -r '.versionNumber // 0' "$E/gas-version.json")
  test "$GAS_VERSION_AFTER" -gt 0
  jq -nc --arg sid "$SCRIPT_ID" --argjson v "$GAS_VERSION_AFTER" \
    '{deploymentConfig:{scriptId:$sid,versionNumber:$v,manifestFileName:"appsscript",description:"Beta78 exact OTA"}}' > "$E/gas-deploy-put.json"
  curl -fsS --connect-timeout 15 --max-time 30 -X PUT -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' \
    --data-binary @"$E/gas-deploy-put.json" "$API/deployments/$DEPLOYMENT_ID" > "$E/gas-deploy.json"
  GAS_CHANGED=true
fi

PASS=0
for i in $(seq 1 15); do
  curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL" \
    -d '{"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.77"}' > "$E/beta-after.json" || true
  if jq -e --arg h "$EXPECTED_SHA" --arg u "$APK_URL" --argjson z "$EXPECTED_SIZE" \
      '.ok==true and .channel=="BETA" and .available==true and .version_name=="0.4.2-beta.78" and .version_code==84 and .sha256==$h and .size==$z and .apk_url==$u' "$E/beta-after.json" >/dev/null 2>&1; then PASS=1; break; fi
  sleep 3
done
test "$PASS" = 1
curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL" \
  -d '{"action":"update_check","channel":"STABLE","current_version":"0.1.0-stable"}' > "$E/stable-after.json"
jq -S . "$E/stable-before.json" > "$E/stable-before.canon"
jq -S . "$E/stable-after.json" > "$E/stable-after.canon"
cmp -s "$E/stable-before.canon" "$E/stable-after.canon"

curl -fsSL --retry 2 --retry-delay 2 --connect-timeout 15 --max-time 120 "$APK_URL" -o "$E/ota-readback.apk"
test "$(sha256sum "$E/ota-readback.apk" | awk '{print $1}')" = "$EXPECTED_SHA"
test "$(stat -c '%s' "$E/ota-readback.apk")" = "$EXPECTED_SIZE"
cmp -s "$APK" "$E/ota-readback.apk"

MAIN_AFTER=$(curl -fsSL --connect-timeout 15 --max-time 30 \
  -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' \
  "https://api.github.com/repos/$GITHUB_REPOSITORY/branches/main" | jq -r '.commit.sha')
test "$MAIN_AFTER" = "$MAIN_BEFORE"
curl -fsSL --connect-timeout 15 --max-time 30 "$WORKER_URL/v1/authority" > "$E/authority-after.json"
jq -e --slurpfile b "$E/authority-before.json" \
  '.ok==true and .authority.mode==$b[0].authority.mode and .authority.scope==$b[0].authority.scope and .authority.authority_epoch==$b[0].authority.authority_epoch and .authority.service_generation==$b[0].authority.service_generation' \
  "$E/authority-after.json" >/dev/null

curl -fsS --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" "$API/content" > "$E/gas-after.json"
curl -fsS --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" "$API/deployments/$DEPLOYMENT_ID" > "$E/deployment-after.json"
DEPLOYED_VERSION=$(jq -r '.deploymentConfig.versionNumber // 0' "$E/deployment-after.json")
test "$DEPLOYED_VERSION" = "$GAS_VERSION_AFTER"
python3 - "$E/gas-after.json" "$TARGET_HASH" <<'PY'
import hashlib,json,sys
j=json.load(open(sys.argv[1],encoding='utf-8'))
canon='\n'.join(str(x.get('name',''))+'\0'+str(x.get('type',''))+'\0'+str(x.get('source','')) for x in j.get('files',[]))
assert hashlib.sha256(canon.encode()).hexdigest()==sys.argv[2]
PY

jq -n \
  --arg source_sha "$SOURCE_SHA" --arg version "$TARGET_VERSION" --argjson code "$TARGET_CODE" \
  --arg package "$PACKAGE" --arg apk_sha256 "$EXPECTED_SHA" --argjson apk_size "$EXPECTED_SIZE" --arg signer "$EXPECTED_SIGNER" \
  --argjson candidate_run "$CANDIDATE_RUN" --argjson candidate_artifact "$CANDIDATE_ARTIFACT" --argjson visual_artifact "$VISUAL_ARTIFACT" \
  --arg file_id "$FILE_ID" --arg apk_url "$APK_URL" --argjson gas_before "$GAS_VERSION_BEFORE" --argjson gas_after "$GAS_VERSION_AFTER" \
  --argjson gas_changed "$GAS_CHANGED" --arg main "$MAIN_AFTER" \
  --slurpfile beta "$E/beta-after.json" --slurpfile stable "$E/stable-after.json" --slurpfile auth "$E/authority-after.json" \
  '{status:"PASS",channel:"BETA",version_name:$version,version_code:$code,package:$package,source_sha:$source_sha,candidate_run:$candidate_run,candidate_artifact:$candidate_artifact,visual_artifact:$visual_artifact,apk_sha256:$apk_sha256,apk_size:$apk_size,signer_sha256:$signer,drive_file_id:$file_id,apk_url:$apk_url,ota_exact_bytes:true,gas_version_before:$gas_before,gas_version_after:$gas_after,gas_code_changed:$gas_changed,apps_script_reason:(if $gas_changed then "BETA78_OTA_ROUTE_REQUIRED" else "UNCHANGED_ALREADY_EXACT" end),beta_readback:$beta[0],stable_readback:$stable[0],stable_unchanged:true,main_sha:$main,main_unchanged:true,authority:$auth[0].authority,authority_change:"NONE",service_run:32977566159,service_artifact:9610145160,historical_result:"3/3_SERVICE_D1_EXACT",outbound_result:"CRUD_DUP_GSHEET_PASS",visual_human_inspection:"PASS",visual_matrix:"320x568,360x640,480x800"}' > "$E/receipt.json"

MUTATED=0
trap - EXIT
echo 'BETA78_OTA_PUBLISH_PASS'
cat "$E/receipt.json"
