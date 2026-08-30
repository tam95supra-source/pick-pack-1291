#!/usr/bin/env bash
set -Eeuo pipefail
REQ=ops/beta-release-request.json
PROV=ops/stable-private-provision-request.json
OUT=/tmp/stable-private-apk
rm -rf "$OUT" && mkdir -p "$OUT"
for n in GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN; do
  test -n "${!n:-}" || { echo "MISSING_REQUIRED_SECRET:$n" >&2; exit 2; }
  echo "::add-mask::${!n}"
done
TOKEN=$(curl -fsS --connect-timeout 15 --max-time 40 -X POST https://oauth2.googleapis.com/token \
  -d client_id="$GOOGLE_OAUTH_CLIENT_ID" -d client_secret="$GOOGLE_OAUTH_CLIENT_SECRET" \
  -d refresh_token="$GOOGLE_OAUTH_REFRESH_TOKEN" -d grant_type=refresh_token | jq -er .access_token)
echo "::add-mask::$TOKEN"
SID=$(jq -er '.stable_primary_sheet_id' "$PROV")
ENC_RANGE=$(python3 - <<'PY'
import urllib.parse
print(urllib.parse.quote("'__ENVIRONMENT_CONTRACT'!A:B",safe=""))
PY
)
curl -fsS --connect-timeout 15 --max-time 40 -H "Authorization: Bearer $TOKEN" \
  "https://sheets.googleapis.com/v4/spreadsheets/$SID/values/$ENC_RANGE" > "$OUT/contract.json"
GAS_URL=$(jq -er '.values[] | select(.[0]=="gas_web_url") | .[1]' "$OUT/contract.json")
ENV_ID=$(jq -er '.values[] | select(.[0]=="environment_id") | .[1]' "$OUT/contract.json")
LIFE=$(jq -er '.values[] | select(.[0]=="lifecycle") | .[1]' "$OUT/contract.json")
test "$ENV_ID" = STABLE
[[ "$LIFE" == PROVISIONING* || "$LIFE" == READY_NOT_LIVE ]]
[[ "$GAS_URL" == https://script.google.com/macros/s/*/exec ]]
export STABLE_GSHEET_API_URL="$GAS_URL"

gradle --no-daemon --build-cache :app:assembleStableDebug
APK=app/build/outputs/apk/stable/debug/app-stable-debug.apk
test -f "$APK"
BT="$ANDROID_SDK_ROOT/build-tools/36.0.0"
"$BT/aapt" dump badging "$APK" > "$OUT/stable-badging.txt"
grep -q "package: name='vn.pickpack1291.app.stable'" "$OUT/stable-badging.txt"
grep -q "versionCode='1'" "$OUT/stable-badging.txt"
grep -q "versionName='0.1.0-stable'" "$OUT/stable-badging.txt"
grep -q "application-label:'Pick Pack 1291'" "$OUT/stable-badging.txt"
"$BT/apksigner" verify --print-certs "$APK" > "$OUT/stable-cert.txt"
STABLE_SIGNER=$(grep -m1 'Signer #1 certificate SHA-256 digest:' "$OUT/stable-cert.txt" | sed 's/.*digest: //' | tr 'A-F' 'a-f' | tr -d ':[:space:]')
STABLE_SHA=$(sha256sum "$APK"|awk '{print $1}')
STABLE_SIZE=$(stat -c '%s' "$APK")
cp "$APK" "$OUT/pick-pack-1291-stable-private-debug.apk"

BETA_APK=$(find /tmp/beta-candidate -maxdepth 1 -type f -name '*.apk' | head -1)
test -f "$BETA_APK"
BETA_SHA=$(sha256sum "$BETA_APK"|awk '{print $1}')
EXPECTED_BETA_SHA=$(jq -er '.apk_sha256' "$REQ")
test "$BETA_SHA" = "$EXPECTED_BETA_SHA"

adb install -r "$BETA_APK" > "$OUT/install-beta.txt"
adb install -r "$APK" > "$OUT/install-stable.txt"
adb shell pm list packages | tr -d '\r' > "$OUT/packages.txt"
grep -Fxq 'package:vn.pickpack1291.app.beta.publicbeta' "$OUT/packages.txt"
grep -Fxq 'package:vn.pickpack1291.app.stable' "$OUT/packages.txt"
adb shell am force-stop vn.pickpack1291.app.beta.publicbeta || true
adb shell am force-stop vn.pickpack1291.app.stable || true
adb shell monkey -p vn.pickpack1291.app.stable -c android.intent.category.LAUNCHER 1 > "$OUT/launch-stable.txt"
sleep 2
adb shell dumpsys activity activities | tail -n 160 > "$OUT/activity.txt"
grep -q 'vn.pickpack1291.app.stable' "$OUT/activity.txt"

jq -n \
 --arg stable_sha "$STABLE_SHA" --argjson stable_size "$STABLE_SIZE" --arg stable_signer "$STABLE_SIGNER" \
 --arg beta_sha "$BETA_SHA" --arg gas_url "$GAS_URL" \
 '{status:"PASS",environment:"STABLE",lifecycle:"PRIVATE_PREVIEW",package:"vn.pickpack1291.app.stable",version_name:"0.1.0-stable",version_code:1,
   stable_apk_sha256:$stable_sha,stable_apk_size:$stable_size,debug_signer_sha256:$stable_signer,debug_signer_non_release:true,
   beta_package:"vn.pickpack1291.app.beta.publicbeta",beta_exact_sha256:$beta_sha,side_by_side_install:"PASS",stable_launch:"PASS",
   gas_binding_source:"STABLE_SHEET_ENVIRONMENT_CONTRACT",gas_url_present:($gas_url|length>0),
   public_release:false,manifest_active:false,ota_active:false,root_domain_cutover:false}' > "$OUT/receipt.json"
cat "$OUT/receipt.json"
