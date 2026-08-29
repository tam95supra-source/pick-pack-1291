#!/usr/bin/env bash
set -Eeuo pipefail
R=ops/beta-release-request.json
E=/tmp/beta-publish
rm -rf "$E";mkdir -p "$E"
for n in GH_TOKEN GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN GAS_SCRIPT_ID GAS_DEPLOYMENT_ID GITHUB_REPOSITORY GITHUB_API_URL; do test -n "${!n:-}"; done

VERSION=$(jq -r '.version_name' "$R");CODE=$(jq -r '.version_code' "$R");PREV=$(jq -r '.base_version' "$R");BASE_CODE=$(jq -r '.base_version_code' "$R")
SOURCE=$(jq -r '.source_sha' "$R");SHA=$(jq -r '.apk_sha256' "$R");SIZE=$(jq -r '.apk_size' "$R");SIGNER=$(jq -r '.signer_sha256' "$R")
BASE_SOURCE=$(jq -r '.base_source_sha' "$R");BASE_SHA=$(jq -r '.base_apk_sha256' "$R");BASE_SIZE=$(jq -r '.base_apk_size' "$R")
RELEASE_NOTES=$(jq -r '.release_notes | if type=="array" then map("• "+.)|join("\n") else "" end' "$R")
test -n "$RELEASE_NOTES"
APK=/tmp/beta-candidate/pick-pack-1291-public-beta-$VERSION.apk
META=/tmp/beta-candidate/release-meta.json
VERIFY=/tmp/beta-verify/receipt.json
if [[ ! -f "$VERIFY" && -f /tmp/beta-verify/beta-verify/receipt.json ]]; then
  VERIFY=/tmp/beta-verify/beta-verify/receipt.json
fi
test -f "$APK" -a -f "$META" -a -f "$VERIFY"
jq -e --arg v "$VERSION" --argjson c "$CODE" --arg s "$SOURCE" --arg h "$SHA" --argjson z "$SIZE" --arg signer "$SIGNER" '
  .version_name==$v and .version_code==$c and .source_sha==$s and .apk_sha256==$h and .apk_size==$z and
  .signer_sha256==$signer and .candidate_locked==true and .stable_publish=="FORBIDDEN" and .authority_change=="NONE"
' "$META" >/dev/null
jq -e --arg v "$VERSION" --arg h "$SHA" --argjson z "$SIZE" '
  .status=="PASS" and .version_name==$v and .apk_sha256==$h and .apk_size==$z and
  .functional_pass==true and .current_day_only==true and .incomplete_and_complete_paths==true and
  .qr_session_cards==true and .null_sanitized==true and .settings_simplified==true and .old_warning_preserved==true and
  .reconciliation_above_scan==true and .work_info_order==true and .before_after_visible==true and
  .timeline_changed_fields_only==true and .employee_timeline_realtime==true and .employee_timeline_realtime_functional==true and
  .authoritative_resource_options==true and .authoritative_editor_offline_guard==true and .employee_ui_no_background_reset==true and .dual_changelog==true and .timeline_newest_first==true and .hhmm_edit_confirmation==true and .functional_size=="320x568" and
  .screenshot_count==26 and .meal_attendance_module==true and .meal_current_day_scan==true and .meal_duplicate_local==true and .meal_invalid_employee_guard==true and .qr_local_fast_path==true and .root_back_stays==true and .header_back_removed==true and .staff_contact_layout==true and .staff_search_fixed==true and .qr_employee_contact==true and .attendance_card==true and .detail_reconciliation_visible==true and .pda_return_projection_sanitized==true and .pick_phone_account==true and .scalar_snapshot_fallback==true and .reconciliation_emphasis==true and (.visual_sizes|sort)==(["320x568","360x640","480x800"]|sort)
' "$VERIFY" >/dev/null
jq -e '.human_visual_pass==true and .rebuild==false and .resign==false and .stable_publish=="FORBIDDEN" and .authority_change=="NONE"' "$R" >/dev/null
test "$(sha256sum "$APK"|awk '{print $1}')" = "$SHA"
test "$(stat -c '%s' "$APK")" = "$SIZE"
git diff --quiet "$SOURCE" HEAD -- app service google-apps-script

RAW=$(printf '%s' "$GAS_DEPLOYMENT_ID"|tr -d '\r\n\t ')
DEP="$RAW";if [[ "$RAW" == *"/s/"* ]]; then DEP="${RAW#*/s/}";DEP="${DEP%%/*}";fi
test -n "$DEP";GAS_URL="https://script.google.com/macros/s/$DEP/exec";echo "::add-mask::$GAS_URL"

gas(){
  local body="$1" out="$2" a
  for a in 0 1 2; do
    if curl -fsSL --connect-timeout 15 --max-time 35 -H 'content-type: application/json' "$GAS_URL" --data-binary "$body" > "$out"       && jq -e '.ok==true' "$out" >/dev/null 2>&1; then return 0; fi
    [[ "$a" -lt 2 ]] || break
    sleep $((2+a*4))
  done
  return 1
}
update(){
  local ch="$1" current="$2" out="$3" body
  body=$(jq -nc --arg ch "$ch" --arg current "$current" '{action:"update_check",channel:$ch,current_version:$current}')
  gas "$body" "$out"
}

MAIN_BEFORE=$(curl -fsSL --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/branches/main"|jq -r '.commit.sha')
test -n "$MAIN_BEFORE" -a "$MAIN_BEFORE" != null
update STABLE 0.1.0-stable "$E/stable-before.json"
jq -e '.channel=="STABLE" and .available==false' "$E/stable-before.json" >/dev/null

TOKEN_JSON=$(curl -fsS --connect-timeout 15 --max-time 30 https://oauth2.googleapis.com/token -H 'Content-Type: application/x-www-form-urlencoded' --data-urlencode "client_id=$GOOGLE_OAUTH_CLIENT_ID" --data-urlencode "client_secret=$GOOGLE_OAUTH_CLIENT_SECRET" --data-urlencode "refresh_token=$GOOGLE_OAUTH_REFRESH_TOKEN" --data-urlencode grant_type=refresh_token)
ACCESS_TOKEN=$(jq -r '.access_token//empty' <<<"$TOKEN_JSON");test -n "$ACCESS_TOKEN";export ACCESS_TOKEN;echo "::add-mask::$ACCESS_TOKEN"
FQ="name='BẢN THỬ NGHIỆM' and mimeType='application/vnd.google-apps.folder' and trashed=false"
curl -fsS --get --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" --data-urlencode "q=$FQ" --data-urlencode 'fields=files(id,name,parents)' https://www.googleapis.com/drive/v3/files > "$E/folders.json"
test "$(jq '.files|length' "$E/folders.json")" = 1
FOLDER=$(jq -r '.files[0].id' "$E/folders.json");test -n "$FOLDER";echo "::add-mask::$FOLDER"

BASE_APK_NAME="pick-pack-1291-public-beta-$PREV.apk"
BQ="'$FOLDER' in parents and name='$BASE_APK_NAME' and trashed=false"
curl -fsS --get --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" --data-urlencode "q=$BQ" --data-urlencode 'fields=files(id,name,size)' https://www.googleapis.com/drive/v3/files > "$E/base-files.json"
test "$(jq '.files|length' "$E/base-files.json")" = 1
BASE_FILE_ID=$(jq -r '.files[0].id' "$E/base-files.json");test -n "$BASE_FILE_ID";echo "::add-mask::$BASE_FILE_ID"
test "$(jq -r '.files[0].size' "$E/base-files.json")" = "$BASE_SIZE"
curl -fsS --connect-timeout 15 --max-time 120 -H "Authorization: Bearer $ACCESS_TOKEN" "https://www.googleapis.com/drive/v3/files/$BASE_FILE_ID?alt=media&acknowledgeAbuse=true" -o "$E/base-auth.apk"
test "$(sha256sum "$E/base-auth.apk"|awk '{print $1}')" = "$BASE_SHA";test "$(stat -c '%s' "$E/base-auth.apk")" = "$BASE_SIZE"
printf '%s\n' "Exact baseline $PREV retained for rollback." > "$E/base-release-notes.txt"
bash tools/ensure_beta_github_release.sh "$PREV" "$BASE_SOURCE" "$E/base-auth.apk" "$BASE_SHA" "$BASE_SIZE" "$E/base-release-notes.txt" "$BASE_APK_NAME" "$E/base-github-release.json"
BASE_URL=$(jq -r '.apk_url' "$E/base-github-release.json");test -n "$BASE_URL";echo "::add-mask::$BASE_URL"

BASE_PROBE=$(jq -r '.base_probe_version // empty' "$R")
if [[ -z "$BASE_PROBE" || "$BASE_PROBE" == null ]]; then
  BASE_PROBE=$(python3 - "$PREV" <<'PY'
import re,sys
v=sys.argv[1];m=re.search(r'^(.*beta\.)(\d+)

APK_NAME=$(basename "$APK")
Q="'$FOLDER' in parents and name='$APK_NAME' and trashed=false"
curl -fsS --get --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode "q=$Q" --data-urlencode 'fields=files(id,name,size,modifiedTime)' https://www.googleapis.com/drive/v3/files > "$E/preexisting.json"
COUNT=$(jq '.files|length' "$E/preexisting.json");test "$COUNT" -le 1
UPLOADED_NEW=false
if [[ "$COUNT" = 0 ]]; then
  META_JSON=$(jq -nc --arg n "$APK_NAME" --arg p "$FOLDER" '{name:$n,parents:[$p]}')
  curl -fsS --connect-timeout 15 --max-time 120 -X POST -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "metadata=$META_JSON;type=application/json;charset=UTF-8" -F "file=@$APK;type=application/vnd.android.package-archive" \
    'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,size' > "$E/upload.json"
  FILE_ID=$(jq -r '.id//empty' "$E/upload.json");test -n "$FILE_ID"
  UPLOADED_NEW=true
else
  FILE_ID=$(jq -r '.files[0].id//empty' "$E/preexisting.json");test -n "$FILE_ID"
  test "$(jq -r '.files[0].size//empty' "$E/preexisting.json")" = "$SIZE"
  jq -nc --arg id "$FILE_ID" --arg name "$APK_NAME" --argjson size "$SIZE" '{id:$id,name:$name,size:$size,reused_exact:true}' > "$E/upload.json"
fi
echo "::add-mask::$FILE_ID"
jq -nc --arg d "$RELEASE_NOTES" '{description:$d}' > "$E/meta.json"
curl -fsS --connect-timeout 15 --max-time 30 -X PATCH -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' \
  --data-binary @"$E/meta.json" "https://www.googleapis.com/drive/v3/files/$FILE_ID?fields=id,name,size,description" > "$E/meta-out.json"
curl -fsS --connect-timeout 15 --max-time 30 -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' \
  -d '{"type":"anyone","role":"reader"}' "https://www.googleapis.com/drive/v3/files/$FILE_ID/permissions?fields=id,type,role" > "$E/permission.json" || true

curl -fsS --connect-timeout 15 --max-time 120 -H "Authorization: Bearer $ACCESS_TOKEN" "https://www.googleapis.com/drive/v3/files/$FILE_ID?alt=media&acknowledgeAbuse=true" -o "$E/staged-drive.apk"
test "$(sha256sum "$E/staged-drive.apk"|awk '{print $1}')" = "$SHA";test "$(stat -c '%s' "$E/staged-drive.apk")" = "$SIZE";cmp -s "$APK" "$E/staged-drive.apk"
printf '%s\n' "$RELEASE_NOTES" > "$E/release-notes.txt"
bash tools/ensure_beta_github_release.sh "$VERSION" "$SOURCE" "$APK" "$SHA" "$SIZE" "$E/release-notes.txt" "$APK_NAME" "$E/github-release.json"
APK_URL=$(jq -r '.apk_url' "$E/github-release.json");test -n "$APK_URL";echo "::add-mask::$APK_URL"

PUBLISHED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
if ! python3 tools/gas_ota_static_contract.py --version "$VERSION" --version-code "$CODE" --sha256 "$SHA" --size "$SIZE" --apk-url "$APK_URL" --published-at "$PUBLISHED_AT" --notes-file "$E/release-notes.txt" --receipt "$E/gas-contract.json" --description "Pick Pack 1291 exact Beta97 OTA contract"; then
  printf '%s\n' "Khôi phục hợp đồng OTA exact $PREV" > "$E/base-notes.txt"
  python3 tools/gas_ota_static_contract.py --version "$PREV" --version-code "$BASE_CODE" --sha256 "$BASE_SHA" --size "$BASE_SIZE" --apk-url "$BASE_URL" --published-at "$PUBLISHED_AT" --notes-file "$E/base-notes.txt" --receipt "$E/gas-contract-recovery.json" --description "Pick Pack 1291 restore exact baseline OTA contract" || true
  exit 1
fi
PASS=0
for a in 0 1 2 3; do
  update BETA "$PREV" "$E/beta-after.json" || true
  if jq -e --arg v "$VERSION" --arg h "$SHA" --argjson z "$SIZE" '.channel=="BETA" and .available==true and .version_name==$v and .sha256==$h and .size==$z and ((.apk_url//"")|length)>0' "$E/beta-after.json" >/dev/null 2>&1; then PASS=1;break;fi
  [[ "$a" -lt 3 ]] && sleep $((3+a*4))
done
if [[ "$PASS" != 1 ]]; then
  printf '%s\n' "Khôi phục hợp đồng OTA exact $PREV" > "$E/base-notes.txt"
  python3 tools/gas_ota_static_contract.py --version "$PREV" --version-code "$BASE_CODE" --sha256 "$BASE_SHA" --size "$BASE_SIZE" --apk-url "$BASE_URL" --published-at "$PUBLISHED_AT" --notes-file "$E/base-notes.txt" --receipt "$E/gas-contract-recovery.json" --description "Pick Pack 1291 restore exact baseline OTA contract"
  RESTORED=0
  for a in 0 1 2 3; do
    update BETA "$BASE_PROBE" "$E/beta-restored.json" || true
    if jq -e --arg v "$PREV" --arg h "$BASE_SHA" --argjson z "$BASE_SIZE" '.channel=="BETA" and .available==true and .version_name==$v and .sha256==$h and .size==$z' "$E/beta-restored.json" >/dev/null 2>&1; then RESTORED=1;break;fi
    sleep $((3+a*4))
  done
  test "$RESTORED" = 1
  exit 1
fi
RETURNED_URL=$(jq -r '.apk_url' "$E/beta-after.json");echo "::add-mask::$RETURNED_URL"
curl -fsSL --retry 2 --retry-delay 2 --connect-timeout 15 --max-time 120 "$RETURNED_URL" -o "$E/contract.apk"
test "$(sha256sum "$E/contract.apk"|awk '{print $1}')" = "$SHA";test "$(stat -c '%s' "$E/contract.apk")" = "$SIZE";cmp -s "$APK" "$E/contract.apk"
update BETA "$VERSION" "$E/beta-current.json"
jq -e --arg v "$VERSION" '.channel=="BETA" and .available==false and .version_name==$v' "$E/beta-current.json" >/dev/null
update STABLE 0.1.0-stable "$E/stable-after.json";jq -S . "$E/stable-before.json" > "$E/sb";jq -S . "$E/stable-after.json" > "$E/sa";cmp -s "$E/sb" "$E/sa"
MAIN_AFTER=$(curl -fsSL --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/branches/main"|jq -r '.commit.sha');test "$MAIN_AFTER" = "$MAIN_BEFORE"
curl -fsSL --connect-timeout 15 --max-time 30 "$SERVICE_URL/v1/authority" > "$E/authority-after.json"
jq -S '.authority' "$E/authority-before.json" > "$E/ab";jq -S '.authority' "$E/authority-after.json" > "$E/aa";cmp -s "$E/ab" "$E/aa"

jq -n --arg v "$VERSION" --argjson c "$CODE" --arg source "$SOURCE" --arg h "$SHA" --argjson z "$SIZE" --arg signer "$SIGNER" \
  --arg file "$FILE_ID" --arg url "$RETURNED_URL" --arg main "$MAIN_AFTER" --argjson uploaded "$UPLOADED_NEW" \
  --slurpfile beta "$E/beta-after.json" --slurpfile current "$E/beta-current.json" --slurpfile stable "$E/stable-after.json" --slurpfile auth "$E/authority-after.json" --slurpfile baseline "$E/baseline-evidence.json" --slurpfile contract "$E/gas-contract.json" --slurpfile gh "$E/github-release.json" --slurpfile basegh "$E/base-github-release.json" \
  '{status:"PASS",channel:"BETA",version_name:$v,version_code:$c,source_sha:$source,apk_sha256:$h,apk_size:$z,signer_sha256:$signer,
    drive_file_id:$file,apk_url:$url,uploaded_new:$uploaded,ota_exact_bytes:true,ota_transport:"GITHUB_RELEASE_CANONICAL",drive_staging_exact:true,ota_contract_mode:"GAS_STATIC_EXACT",
    baseline_evidence:$baseline[0],baseline_github_release:$basegh[0],github_release:$gh[0],gas_contract:$contract[0],
    beta_readback:$beta[0],target_current_readback:$current[0],stable_readback:$stable[0],stable_unchanged:true,main_sha:$main,main_unchanged:true,authority:$auth[0].authority,authority_change:"NONE"}' > "$E/receipt.json"
cat "$E/receipt.json"
,v);assert m and int(m.group(2))>0
print(m.group(1)+str(int(m.group(2))-1))
PY
)
fi
BASELINE_READBACK="LIVE_GAS"
if ! update BETA "$BASE_PROBE" "$E/beta-before.json"; then
  jq -e '(.error//"")|contains("DriveApp")' "$E/beta-before.json" >/dev/null
  BASELINE_READBACK="DRIVE_API_EXACT_RECOVERY"
else
  jq -e --arg v "$PREV" --arg h "$BASE_SHA" --argjson z "$BASE_SIZE" '.channel=="BETA" and .available==true and .version_name==$v and .sha256==$h and .size==$z and ((.apk_url//"")|length)>0' "$E/beta-before.json" >/dev/null
fi
jq -n --arg mode "$BASELINE_READBACK" --arg v "$PREV" --arg h "$BASE_SHA" --argjson z "$BASE_SIZE" --arg url "$BASE_URL" '{status:"PASS",mode:$mode,version_name:$v,sha256:$h,size:$z,apk_url:$url}' > "$E/baseline-evidence.json"

DISCOVERY_BODY=$(jq -nc '{action:"service_discovery",_app_channel:"BETA"}')
gas "$DISCOVERY_BODY" "$E/discovery-before.json"
SERVICE_URL=$(jq -r '.service_url' "$E/discovery-before.json")
jq -e '.authority_mode=="SERVICE_PRIMARY" and .authority.mode=="SERVICE_PRIMARY" and .authority.scope=="PRODUCTION"' "$E/discovery-before.json" >/dev/null
[[ "$SERVICE_URL" == https://* ]];echo "::add-mask::$SERVICE_URL"
curl -fsSL --connect-timeout 15 --max-time 30 "$SERVICE_URL/v1/authority" > "$E/authority-before.json"
jq -e '.ok==true and .authority.mode=="SERVICE_PRIMARY" and .authority.scope=="PRODUCTION"' "$E/authority-before.json" >/dev/null

APK_NAME=$(basename "$APK")
Q="'$FOLDER' in parents and name='$APK_NAME' and trashed=false"
curl -fsS --get --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode "q=$Q" --data-urlencode 'fields=files(id,name,size,modifiedTime)' https://www.googleapis.com/drive/v3/files > "$E/preexisting.json"
COUNT=$(jq '.files|length' "$E/preexisting.json");test "$COUNT" -le 1
UPLOADED_NEW=false
if [[ "$COUNT" = 0 ]]; then
  META_JSON=$(jq -nc --arg n "$APK_NAME" --arg p "$FOLDER" '{name:$n,parents:[$p]}')
  curl -fsS --connect-timeout 15 --max-time 120 -X POST -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "metadata=$META_JSON;type=application/json;charset=UTF-8" -F "file=@$APK;type=application/vnd.android.package-archive" \
    'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,size' > "$E/upload.json"
  FILE_ID=$(jq -r '.id//empty' "$E/upload.json");test -n "$FILE_ID"
  UPLOADED_NEW=true
else
  FILE_ID=$(jq -r '.files[0].id//empty' "$E/preexisting.json");test -n "$FILE_ID"
  test "$(jq -r '.files[0].size//empty' "$E/preexisting.json")" = "$SIZE"
  jq -nc --arg id "$FILE_ID" --arg name "$APK_NAME" --argjson size "$SIZE" '{id:$id,name:$name,size:$size,reused_exact:true}' > "$E/upload.json"
fi
echo "::add-mask::$FILE_ID"
jq -nc --arg d "$RELEASE_NOTES" '{description:$d}' > "$E/meta.json"
curl -fsS --connect-timeout 15 --max-time 30 -X PATCH -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' \
  --data-binary @"$E/meta.json" "https://www.googleapis.com/drive/v3/files/$FILE_ID?fields=id,name,size,description" > "$E/meta-out.json"
curl -fsS --connect-timeout 15 --max-time 30 -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' \
  -d '{"type":"anyone","role":"reader"}' "https://www.googleapis.com/drive/v3/files/$FILE_ID/permissions?fields=id,type,role" > "$E/permission.json" || true

APK_URL=""
for u in "https://drive.usercontent.google.com/download?id=$FILE_ID&export=download&confirm=t" "https://drive.google.com/uc?export=download&id=$FILE_ID"; do
  if curl -fsSL --retry 2 --retry-delay 2 --connect-timeout 15 --max-time 120 "$u" -o "$E/public.apk" \
    && [[ "$(sha256sum "$E/public.apk"|awk '{print $1}')" == "$SHA" ]] && [[ "$(stat -c '%s' "$E/public.apk")" == "$SIZE" ]]; then APK_URL="$u";break;fi
done
test -n "$APK_URL";echo "::add-mask::$APK_URL";cmp -s "$APK" "$E/public.apk"

PASS=0
for a in 0 1 2; do
  update BETA "$PREV" "$E/beta-after.json" || true
  if jq -e --arg v "$VERSION" --arg h "$SHA" --argjson z "$SIZE" '
    .channel=="BETA" and .available==true and .version_name==$v and .sha256==$h and .size==$z and ((.apk_url//"")|length)>0
  ' "$E/beta-after.json" >/dev/null 2>&1; then PASS=1;break;fi
  [[ "$a" -lt 2 ]] && sleep $((3+a*5))
done
test "$PASS" = 1
RETURNED_URL=$(jq -r '.apk_url' "$E/beta-after.json");echo "::add-mask::$RETURNED_URL"
curl -fsSL --retry 2 --retry-delay 2 --connect-timeout 15 --max-time 120 "$RETURNED_URL" -o "$E/contract.apk"
test "$(sha256sum "$E/contract.apk"|awk '{print $1}')" = "$SHA";test "$(stat -c '%s' "$E/contract.apk")" = "$SIZE";cmp -s "$APK" "$E/contract.apk"
update BETA "$VERSION" "$E/beta-current.json"
jq -e --arg v "$VERSION" '.channel=="BETA" and .available==false and .version_name==$v' "$E/beta-current.json" >/dev/null
update STABLE 0.1.0-stable "$E/stable-after.json";jq -S . "$E/stable-before.json" > "$E/sb";jq -S . "$E/stable-after.json" > "$E/sa";cmp -s "$E/sb" "$E/sa"
MAIN_AFTER=$(curl -fsSL --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/branches/main"|jq -r '.commit.sha');test "$MAIN_AFTER" = "$MAIN_BEFORE"
curl -fsSL --connect-timeout 15 --max-time 30 "$SERVICE_URL/v1/authority" > "$E/authority-after.json"
jq -S '.authority' "$E/authority-before.json" > "$E/ab";jq -S '.authority' "$E/authority-after.json" > "$E/aa";cmp -s "$E/ab" "$E/aa"

jq -n --arg v "$VERSION" --argjson c "$CODE" --arg source "$SOURCE" --arg h "$SHA" --argjson z "$SIZE" --arg signer "$SIGNER" \
  --arg file "$FILE_ID" --arg url "$RETURNED_URL" --arg main "$MAIN_AFTER" --argjson uploaded "$UPLOADED_NEW" \
  --slurpfile beta "$E/beta-after.json" --slurpfile current "$E/beta-current.json" --slurpfile stable "$E/stable-after.json" --slurpfile auth "$E/authority-after.json" \
  '{status:"PASS",channel:"BETA",version_name:$v,version_code:$c,source_sha:$source,apk_sha256:$h,apk_size:$z,signer_sha256:$signer,
    drive_file_id:$file,apk_url:$url,uploaded_new:$uploaded,ota_exact_bytes:true,beta_readback:$beta[0],target_current_readback:$current[0],
    stable_readback:$stable[0],stable_unchanged:true,main_sha:$main,main_unchanged:true,authority:$auth[0].authority,authority_change:"NONE"}' > "$E/receipt.json"
cat "$E/receipt.json"
