#!/usr/bin/env bash
set -Eeuo pipefail

R=ops/beta-release-request.json
E=/tmp/beta-rollback
PUB=/tmp/beta-publish/receipt.json
rm -rf "$E"; mkdir -p "$E"
test -f "$PUB"

for n in GH_TOKEN GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN GAS_SCRIPT_ID GAS_DEPLOYMENT_ID GITHUB_REPOSITORY; do
  test -n "${!n:-}"
done

PREV=$(jq -r '.base_version' "$R")
BASE_CODE=$(jq -r '.base_version_code' "$R")
BASE_SOURCE=$(jq -r '.base_source_sha' "$R")
BASE_SHA=$(jq -r '.base_apk_sha256' "$R")
BASE_SIZE=$(jq -r '.base_apk_size' "$R")
PKG=$(jq -r '.package' "$R")
BASE_APK="/tmp/beta-base/pick-pack-1291-public-beta-$PREV.apk"
test -f "$BASE_APK"

jq -e '.status=="PASS" and .ota_transport=="GITHUB_RELEASE" and .google_drive_apk=="FORBIDDEN" and
       .ota_exact_bytes==true and .stable_unchanged==true and .main_unchanged==true and .authority_change=="NONE"' "$PUB" >/dev/null
test "$(sha256sum "$BASE_APK"|awk '{print $1}')" = "$BASE_SHA"
test "$(stat -c '%s' "$BASE_APK")" = "$BASE_SIZE"

printf '%s\n' "Khôi phục exact LIVE $PREV qua GitHub Release." > "$E/base-notes.txt"
BASE_APK_NAME=$(basename "$BASE_APK")
bash tools/ensure_beta_github_release.sh "$PREV" "$BASE_SOURCE" "$BASE_APK" "$BASE_SHA" "$BASE_SIZE" \
  "$E/base-notes.txt" "$BASE_APK_NAME" "$E/base-github-release.json"
BASE_URL=$(jq -r '.apk_url' "$E/base-github-release.json")
test -n "$BASE_URL"
echo "::add-mask::$BASE_URL"

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

python3 tools/gas_ota_static_contract.py --version "$PREV" --version-code "$BASE_CODE" --package "$PKG" \
  --sha256 "$BASE_SHA" --size "$BASE_SIZE" --apk-url "$BASE_URL" --published-at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --notes-file "$E/base-notes.txt" --receipt "$E/gas-contract.json" \
  --description "Pick Pack 1291 rollback exact $PREV GitHub Release OTA contract"

RAW=$(printf '%s' "$GAS_DEPLOYMENT_ID"|tr -d '\r\n\t ')
DEP="$RAW"
if [[ "$RAW" == *"/s/"* ]]; then DEP="${RAW#*/s/}"; DEP="${DEP%%/*}"; fi
test -n "$DEP"
URL="https://script.google.com/macros/s/$DEP/exec"
echo "::add-mask::$URL"

BASE_PROBE=$(jq -r '.base_probe_version // empty' "$R")
if [[ -z "$BASE_PROBE" || "$BASE_PROBE" == null ]]; then
  BASE_PROBE=$(python3 - "$PREV" <<'PY'
import re,sys
m=re.search(r'^(.*beta\.)(\d+)$',sys.argv[1]); assert m and int(m.group(2))>0
print(m.group(1)+str(int(m.group(2))-1))
PY
)
fi

PASS=0
for a in 0 1 2 3 4; do
  BODY=$(jq -nc --arg current "$BASE_PROBE" '{action:"update_check",channel:"BETA",current_version:$current}')
  curl -fsSL --connect-timeout 15 --max-time 35 -H 'content-type: application/json' "$URL" --data-binary "$BODY" > "$E/readback.json" || true
  if jq -e --arg v "$PREV" --arg p "$PKG" --arg h "$BASE_SHA" --argjson z "$BASE_SIZE" '
    .ok==true and .source=="GITHUB_RELEASE" and .channel=="BETA" and .available==true and
    .version_name==$v and .package==$p and .sha256==$h and .size==$z and ((.apk_url//"")|length)>0
  ' "$E/readback.json" >/dev/null 2>&1; then PASS=1; break; fi
  sleep $((3+a*4))
done
test "$PASS" = 1
test "$(jq -r '.apk_url' "$E/readback.json")" = "$BASE_URL"

curl -fsSL --retry 2 --retry-delay 2 --connect-timeout 15 --max-time 180 "$BASE_URL" -o "$E/base-public.apk"
test "$(sha256sum "$E/base-public.apk"|awk '{print $1}')" = "$BASE_SHA"
test "$(stat -c '%s' "$E/base-public.apk")" = "$BASE_SIZE"
cmp -s "$BASE_APK" "$E/base-public.apk"

jq -n --slurpfile r "$E/readback.json" --slurpfile c "$E/gas-contract.json" --slurpfile gh "$E/base-github-release.json" '
  {status:"PASS",rollback_base:true,manifest_restored:true,ota_transport:"GITHUB_RELEASE",google_drive_apk:"FORBIDDEN",
   beta_readback:$r[0],gas_contract:$c[0],baseline_github_release:$gh[0]}
' > "$E/receipt.json"
cat "$E/receipt.json"
