#!/usr/bin/env bash
set -Eeuo pipefail

R=ops/beta-release-request.json
E=/tmp/beta-publish
rm -rf "$E"; mkdir -p "$E"

for n in GH_TOKEN GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN GAS_SCRIPT_ID GAS_DEPLOYMENT_ID GITHUB_REPOSITORY GITHUB_API_URL; do
  test -n "${!n:-}"
done

VERSION=$(jq -r '.version_name' "$R")
CODE=$(jq -r '.version_code' "$R")
PKG=$(jq -r '.package' "$R")
PREV=$(jq -r '.base_version' "$R")
BASE_CODE=$(jq -r '.base_version_code' "$R")
SERVICE_SOURCE=$(jq -r '.source_sha' "$R")
CANDIDATE_SOURCE=$(jq -r '.candidate_source_sha // .source_sha' "$R")
BASE_SOURCE=$(jq -r '.base_source_sha' "$R")
SHA=$(jq -r '.apk_sha256' "$R")
SIZE=$(jq -r '.apk_size' "$R")
SIGNER=$(jq -r '.signer_sha256' "$R")
BASE_SHA=$(jq -r '.base_apk_sha256' "$R")
BASE_SIZE=$(jq -r '.base_apk_size' "$R")
RELEASE_NOTES=$(jq -r '.release_notes | if type=="array" then map("• "+.)|join("\n") else "" end' "$R")
test -n "$RELEASE_NOTES"

APK="/tmp/beta-candidate/pick-pack-1291-public-beta-$VERSION.apk"
BASE_APK="/tmp/beta-base/pick-pack-1291-public-beta-$PREV.apk"
META=/tmp/beta-candidate/release-meta.json
VERIFY=/tmp/beta-verify/receipt.json
BASE_FINAL=/tmp/beta-base-final/receipt.json
if [[ ! -f "$VERIFY" && -f /tmp/beta-verify/beta-verify/receipt.json ]]; then VERIFY=/tmp/beta-verify/beta-verify/receipt.json; fi
test -f "$APK" -a -f "$BASE_APK" -a -f "$META" -a -f "$VERIFY" -a -f "$BASE_FINAL"

jq -e --arg v "$VERSION" --argjson c "$CODE" --arg p "$PKG" --arg s "$CANDIDATE_SOURCE" --arg h "$SHA" --argjson z "$SIZE" --arg signer "$SIGNER" '
  .version_name==$v and .version_code==$c and .package==$p and .source_sha==$s and .apk_sha256==$h and .apk_size==$z and
  .signer_sha256==$signer and .candidate_locked==true and .stable_publish=="FORBIDDEN" and .authority_change=="NONE"
' "$META" >/dev/null

jq -e --arg v "$VERSION" --arg h "$SHA" --argjson z "$SIZE" '
  .status=="PASS" and .version_name==$v and .apk_sha256==$h and .apk_size==$z and
  .functional_pass==true and .current_day_only==true and .incomplete_and_complete_paths==true and
  .meal_attendance_module==true and .meal_current_day_scan==true and .meal_old_session_blocked==true and
  .history_hidden_user==true and .history_deeplink_blocked_user==true and .status_header_meal==true and
  .qr_local_fast_path==true and .root_back_stays==true and .employee_ui_no_background_reset==true and
  .authoritative_resource_options==true and .timeline_newest_first==true and .hhmm_edit_confirmation==true and
  .functional_size=="320x568" and .human_inspection_required==true
' "$VERIFY" >/dev/null

python3 tools/verify_beta_visual_receipt.py \
  --receipt "$VERIFY" \
  --evidence-dir "$(dirname "$VERIFY")" \
  --request "$R" > "$E/visual-receipt-verify.json"

jq -e --arg v "$PREV" --arg source "$BASE_SOURCE" --arg h "$BASE_SHA" --argjson z "$BASE_SIZE" --arg signer "$SIGNER" '
  .status=="PASS" and .version_name==$v and .source_sha==$source and .apk_sha256==$h and .apk_size==$z and
  .signer_sha256==$signer and .stable_unchanged==true and .authority_change=="NONE" and .readback==true
' "$BASE_FINAL" >/dev/null

jq -e '.human_visual_pass==true and .visual_matrix=="PASS" and .pda_functional_pre_ota=="PASS" and .back_api36=="PASS" and
       .rebuild==false and .resign==false and .stable_publish=="FORBIDDEN" and .authority_change=="NONE" and
       .apk_transport=="GITHUB_RELEASE_ONLY" and .google_drive_apk=="FORBIDDEN"' "$R" >/dev/null

test "$(sha256sum "$APK"|awk '{print $1}')" = "$SHA"
test "$(stat -c '%s' "$APK")" = "$SIZE"
test "$(sha256sum "$BASE_APK"|awk '{print $1}')" = "$BASE_SHA"
test "$(stat -c '%s' "$BASE_APK")" = "$BASE_SIZE"
git diff --quiet "$SERVICE_SOURCE" HEAD -- service google-apps-script
git diff --quiet "$CANDIDATE_SOURCE" HEAD -- app

RAW=$(printf '%s' "$GAS_DEPLOYMENT_ID"|tr -d '\r\n\t ')
DEP="$RAW"
if [[ "$RAW" == *"/s/"* ]]; then DEP="${RAW#*/s/}"; DEP="${DEP%%/*}"; fi
test -n "$DEP"
GAS_URL="https://script.google.com/macros/s/$DEP/exec"
echo "::add-mask::$GAS_URL"

gas(){
  local body="$1" out="$2" a
  for a in 0 1 2; do
    if curl -fsSL --connect-timeout 15 --max-time 35 -H 'content-type: application/json' "$GAS_URL" --data-binary "$body" > "$out" \
       && jq -e '.ok==true' "$out" >/dev/null 2>&1; then return 0; fi
    [[ "$a" -lt 2 ]] || break
    sleep $((2+a*4))
  done
  return 1
}
update(){
  local ch="$1" current="$2" out="$3"
  gas "$(jq -nc --arg ch "$ch" --arg current "$current" '{action:"update_check",channel:$ch,current_version:$current}')" "$out"
}

MAIN_BEFORE=$(curl -fsSL --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/branches/main"|jq -r '.commit.sha')
test -n "$MAIN_BEFORE" -a "$MAIN_BEFORE" != null
update STABLE 0.1.0-stable "$E/stable-before.json"
jq -e '.ok==true and .channel=="STABLE" and .available==false' "$E/stable-before.json" >/dev/null

TOKEN_JSON=$(curl -fsS --connect-timeout 15 --max-time 30 https://oauth2.googleapis.com/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "client_id=$GOOGLE_OAUTH_CLIENT_ID" \
  --data-urlencode "client_secret=$GOOGLE_OAUTH_CLIENT_SECRET" \
  --data-urlencode "refresh_token=$GOOGLE_OAUTH_REFRESH_TOKEN" \
  --data-urlencode grant_type=refresh_token)
ACCESS_TOKEN=$(jq -r '.access_token//empty' <<<"$TOKEN_JSON")
test -n "$ACCESS_TOKEN"
export ACCESS_TOKEN
echo "::add-mask::$ACCESS_TOKEN"
python3 tools/gas_version_inventory.py "$E/gas-version-inventory.json"
python3 tools/gas_resilience_contract_readback.py "$E/gas-resilience-readback.json"

BASE_APK_NAME=$(basename "$BASE_APK")
printf '%s\n' "Exact LIVE rollback baseline $PREV." > "$E/base-release-notes.txt"
bash tools/ensure_beta_github_release.sh "$PREV" "$BASE_SOURCE" "$BASE_APK" "$BASE_SHA" "$BASE_SIZE" \
  "$E/base-release-notes.txt" "$BASE_APK_NAME" "$E/base-github-release.json"
BASE_URL=$(jq -r '.apk_url' "$E/base-github-release.json")
test -n "$BASE_URL"
echo "::add-mask::$BASE_URL"

BASE_PROBE=$(jq -r '.base_probe_version // empty' "$R")
if [[ -z "$BASE_PROBE" || "$BASE_PROBE" == null ]]; then
  BASE_PROBE=$(python3 - "$PREV" <<'PY'
import re,sys
m=re.search(r'^(.*beta\.)(\d+)$',sys.argv[1]); assert m and int(m.group(2))>0
print(m.group(1)+str(int(m.group(2))-1))
PY
)
fi

BASELINE_READBACK=LIVE_GAS_BASELINE
if update BETA "$BASE_PROBE" "$E/beta-before.json"; then
  if jq -e --arg v "$PREV" --arg h "$BASE_SHA" --argjson z "$BASE_SIZE" '
    .channel=="BETA" and .available==true and .version_name==$v and .sha256==$h and .size==$z
  ' "$E/beta-before.json" >/dev/null 2>&1; then
    BASELINE_READBACK=LIVE_GAS_BASELINE
  elif jq -e --arg v "$VERSION" --arg p "$PKG" --arg h "$SHA" --argjson z "$SIZE" '
    .source=="GITHUB_RELEASE" and .channel=="BETA" and .available==true and
    .version_name==$v and .package==$p and .sha256==$h and .size==$z
  ' "$E/beta-before.json" >/dev/null 2>&1; then
    BASELINE_READBACK=PARTIAL_TARGET_ACTIVE_FROM_PRIOR_PUBLISH
  else
    echo "Unexpected Beta manifest state before publish" >&2
    cat "$E/beta-before.json" >&2
    exit 1
  fi
else
  jq -e '(.error//"")|contains("DriveApp")' "$E/beta-before.json" >/dev/null
  BASELINE_READBACK=LEGACY_GAS_DRIVEAPP_BROKEN_BUT_FINAL_RECEIPT_PASS
fi
jq -n --arg mode "$BASELINE_READBACK" --arg v "$PREV" --arg h "$BASE_SHA" --argjson z "$BASE_SIZE" --arg url "$BASE_URL" \
  --slurpfile final "$BASE_FINAL" --slurpfile gh "$E/base-github-release.json" \
  '{status:"PASS",mode:$mode,version_name:$v,sha256:$h,size:$z,apk_url:$url,final_receipt:$final[0],github_release:$gh[0]}' > "$E/baseline-evidence.json"

EXPECTED_BETA_SERVICE_URL=$(jq -r '.environments.BETA.current_service.url // empty' config/environment_contracts.json)
test -n "$EXPECTED_BETA_SERVICE_URL"
DISCOVERY_BODY=$(jq -nc '{action:"service_discovery",_app_channel:"BETA",_environment_id:"BETA",_service_audience:"PICK_PACK_1291_BETA"}')
gas "$DISCOVERY_BODY" "$E/discovery-before.json"
SERVICE_URL=$(jq -r '.service_url // empty' "$E/discovery-before.json")
if ! jq -e --arg u "$EXPECTED_BETA_SERVICE_URL" '
  .ok==true and .environment_id=="BETA" and .service_audience=="PICK_PACK_1291_BETA" and
  .authority_mode=="SERVICE_PRIMARY" and .authority.mode=="SERVICE_PRIMARY" and .authority.scope=="PRODUCTION" and
  (.service_url|rtrimstr("/"))==($u|rtrimstr("/"))
' "$E/discovery-before.json" >/dev/null; then
  echo "BETA_SERVICE_DISCOVERY_DRIFT" >&2
  jq '{ok,environment_id,service_audience,authority_mode,service_url}' "$E/discovery-before.json" >&2 || true
  exit 71
fi
[[ "$SERVICE_URL" == https://* ]]
echo "::add-mask::$SERVICE_URL"
curl -fsSL --connect-timeout 15 --max-time 30 "$SERVICE_URL/v1/authority" > "$E/authority-before.json"
jq -e '.ok==true and .authority.mode=="SERVICE_PRIMARY" and .authority.scope=="PRODUCTION"' "$E/authority-before.json" >/dev/null

APK_NAME=$(basename "$APK")
printf '%s\n' "$RELEASE_NOTES" > "$E/release-notes.txt"
bash tools/ensure_beta_github_release.sh "$VERSION" "$CANDIDATE_SOURCE" "$APK" "$SHA" "$SIZE" \
  "$E/release-notes.txt" "$APK_NAME" "$E/github-release.json"
APK_URL=$(jq -r '.apk_url' "$E/github-release.json")
test -n "$APK_URL"
echo "::add-mask::$APK_URL"

PUBLISHED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
restore_baseline(){
  printf '%s\n' "Khôi phục exact LIVE $PREV qua GitHub Release." > "$E/base-notes.txt"
  python3 tools/gas_ota_static_contract.py --version "$PREV" --version-code "$BASE_CODE" --package "$PKG" \
    --sha256 "$BASE_SHA" --size "$BASE_SIZE" --apk-url "$BASE_URL" --published-at "$PUBLISHED_AT" \
    --notes-file "$E/base-notes.txt" --receipt "$E/gas-contract-recovery.json" \
    --description "Pick Pack 1291 restore exact $PREV GitHub Release OTA contract"
  local restored=0 a
  for a in 0 1 2 3 4 5 6 7; do
    update BETA "$BASE_PROBE" "$E/beta-restored.json" || true
    if jq -e --arg v "$PREV" --arg p "$PKG" --arg h "$BASE_SHA" --argjson z "$BASE_SIZE" '
      .ok==true and .channel=="BETA" and .source=="GITHUB_RELEASE" and .available==true and
      .version_name==$v and .package==$p and .sha256==$h and .size==$z
    ' "$E/beta-restored.json" >/dev/null 2>&1; then restored=1; break; fi
    sleep $((2+a*3))
  done
  test "$restored" = 1
}

ACTIVATED=0
rollback_on_error(){
  local rc=$?
  if [[ "$ACTIVATED" == 1 ]]; then
    trap - ERR
    restore_baseline || true
  fi
  exit "$rc"
}
trap rollback_on_error ERR

if ! python3 tools/gas_ota_static_contract.py --version "$VERSION" --version-code "$CODE" --package "$PKG" \
  --sha256 "$SHA" --size "$SIZE" --apk-url "$APK_URL" --published-at "$PUBLISHED_AT" \
  --notes-file "$E/release-notes.txt" --receipt "$E/gas-contract.json" \
  --description "Pick Pack 1291 exact $VERSION GitHub Release OTA contract"; then
  restore_baseline || true
  exit 1
fi
ACTIVATED=1

PASS=0
for a in 0 1 2 3 4 5 6 7; do
  update BETA "$PREV" "$E/beta-after.json" || true
  if jq -e --arg v "$VERSION" --arg p "$PKG" --arg h "$SHA" --argjson z "$SIZE" '
    .ok==true and .channel=="BETA" and .source=="GITHUB_RELEASE" and .available==true and
    .version_name==$v and .package==$p and .sha256==$h and .size==$z and ((.apk_url//"")|length)>0
  ' "$E/beta-after.json" >/dev/null 2>&1; then PASS=1; break; fi
  [[ "$a" -lt 4 ]] && sleep $((3+a*4))
done
test "$PASS" = 1

RETURNED_URL=$(jq -r '.apk_url' "$E/beta-after.json")
test "$RETURNED_URL" = "$APK_URL"
echo "::add-mask::$RETURNED_URL"
curl -fsSL --retry 2 --retry-delay 2 --connect-timeout 15 --max-time 180 "$RETURNED_URL" -o "$E/contract.apk"
test "$(sha256sum "$E/contract.apk"|awk '{print $1}')" = "$SHA"
test "$(stat -c '%s' "$E/contract.apk")" = "$SIZE"
cmp -s "$APK" "$E/contract.apk"

CURRENT_PASS=0
for a in 0 1 2 3 4 5 6 7; do
  update BETA "$VERSION" "$E/beta-current.json" || true
  if jq -e --arg v "$VERSION" --arg p "$PKG" '
    .ok==true and .channel=="BETA" and .source=="GITHUB_RELEASE" and .available==false and .version_name==$v and .package==$p
  ' "$E/beta-current.json" >/dev/null 2>&1; then CURRENT_PASS=1; break; fi
  sleep $((2+a*3))
done
test "$CURRENT_PASS" = 1

update STABLE 0.1.0-stable "$E/stable-after.json"
jq -S . "$E/stable-before.json" > "$E/sb"
jq -S . "$E/stable-after.json" > "$E/sa"
cmp -s "$E/sb" "$E/sa"

MAIN_AFTER=$(curl -fsSL --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/branches/main"|jq -r '.commit.sha')
test "$MAIN_AFTER" = "$MAIN_BEFORE"

curl -fsSL --connect-timeout 15 --max-time 30 "$SERVICE_URL/v1/authority" > "$E/authority-after.json"
jq -S '.authority' "$E/authority-before.json" > "$E/ab"
jq -S '.authority' "$E/authority-after.json" > "$E/aa"
cmp -s "$E/ab" "$E/aa"

jq -n \
  --arg v "$VERSION" --argjson c "$CODE" --arg p "$PKG" --arg source "$CANDIDATE_SOURCE" --arg service_source "$SERVICE_SOURCE" --arg h "$SHA" --argjson z "$SIZE" --arg signer "$SIGNER" \
  --arg url "$RETURNED_URL" --arg main "$MAIN_AFTER" \
  --slurpfile beta "$E/beta-after.json" --slurpfile current "$E/beta-current.json" --slurpfile stable "$E/stable-after.json" \
  --slurpfile auth "$E/authority-after.json" --slurpfile baseline "$E/baseline-evidence.json" \
  --slurpfile contract "$E/gas-contract.json" --slurpfile gh "$E/github-release.json" --slurpfile basegh "$E/base-github-release.json" \
  '{
    status:"PASS",channel:"BETA",version_name:$v,version_code:$c,package:$p,source_sha:$source,service_source_sha:$service_source,apk_sha256:$h,apk_size:$z,signer_sha256:$signer,
    apk_url:$url,ota_exact_bytes:true,ota_transport:"GITHUB_RELEASE",google_drive_apk:"FORBIDDEN",
    baseline_evidence:$baseline[0],baseline_github_release:$basegh[0],github_release:$gh[0],gas_contract:$contract[0],
    beta_readback:$beta[0],target_current_readback:$current[0],stable_readback:$stable[0],
    stable_unchanged:true,main_sha:$main,main_unchanged:true,authority:$auth[0].authority,authority_change:"NONE"
  }' > "$E/receipt.json"

ACTIVATED=0
trap - ERR
cat "$E/receipt.json"
