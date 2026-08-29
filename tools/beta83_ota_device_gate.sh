#!/usr/bin/env bash
set -Eeuo pipefail
R=ops/beta-release-request.json;OUT=/tmp/beta-pda;rm -rf "$OUT";mkdir -p "$OUT"
VERSION=$(jq -r '.version_name' "$R");CODE=$(jq -r '.version_code' "$R");PKG=$(jq -r '.package' "$R")
BASE=$(jq -r '.base_version' "$R");BASE_CODE=$(jq -r '.base_version_code' "$R")
SHA=$(jq -r '.apk_sha256' "$R");SIZE=$(jq -r '.apk_size' "$R");SIGNER=$(jq -r '.signer_sha256' "$R")
OLD=/tmp/beta-base/pick-pack-1291-public-beta-$BASE.apk
NEW=/tmp/beta-candidate/pick-pack-1291-public-beta-$VERSION.apk
PUB=/tmp/beta-publish/receipt.json;test -f "$OLD" -a -f "$NEW" -a -f "$PUB" -a -f "$VERIFY_HARNESS_APK"
test "$(sha256sum "$OLD"|awk '{print $1}')" = "$(jq -r '.base_apk_sha256' "$R")";test "$(stat -c '%s' "$OLD")" = "$(jq -r '.base_apk_size' "$R")"
test "$(sha256sum "$NEW"|awk '{print $1}')" = "$SHA";test "$(stat -c '%s' "$NEW")" = "$SIZE"
jq -e --arg p "$PKG" --arg h "$SHA" --argjson z "$SIZE" '
  .status=="PASS" and .package==$p and .ota_exact_bytes==true and .ota_transport=="GITHUB_RELEASE" and .google_drive_apk=="FORBIDDEN" and
  .apk_sha256==$h and .apk_size==$z and .stable_unchanged==true and .main_unchanged==true and .authority_change=="NONE"
' "$PUB" >/dev/null
OTA_URL=$(jq -r '.apk_url' "$PUB");MAIN_BEFORE=$(jq -r '.main_sha' "$PUB")
[[ "$OTA_URL" == https://github.com/*/releases/download/* ]];echo "::add-mask::$OTA_URL"

adb root > "$OUT/adb-root.txt" 2>&1 || true;timeout 30s adb wait-for-device
test "$(adb shell id -u 2>/dev/null|tr -d '\r')" = 0
adb uninstall "$PKG" >/dev/null 2>&1 || true
adb install "$OLD" > "$OUT/install-beta81.txt"
adb shell dumpsys package "$PKG" > "$OUT/pkg81.txt";grep -Fq "versionName=$BASE" "$OUT/pkg81.txt";grep -Eq "versionCode=$BASE_CODE([[:space:]]|$)" "$OUT/pkg81.txt"
adb shell appops set "$PKG" REQUEST_INSTALL_PACKAGES allow >/dev/null 2>&1 || true
adb install -r "$VERIFY_HARNESS_APK" > "$OUT/install-harness.txt"
URL_B64=$(printf '%s' "$OTA_URL"|base64 -w0)
adb shell am instrument -w -r -e mode ota -e version "$VERSION" -e url_b64 "$URL_B64" -e sha "$SHA" vn.pickpack1291.verify/.Beta80VerifyInstrumentation > "$OUT/ota-instrument.txt" 2>&1 &
PID=$!
UPDATED=0
for _ in $(seq 1 180); do
  adb shell dumpsys package "$PKG" > "$OUT/pkg-current.txt" 2>/dev/null || true
  if grep -Fq "versionName=$VERSION" "$OUT/pkg-current.txt" && grep -Eq "versionCode=$CODE([[:space:]]|$)" "$OUT/pkg-current.txt"; then cp "$OUT/pkg-current.txt" "$OUT/pkg-new.txt";UPDATED=1;break;fi
  sleep .5
done
test "$UPDATED" = 1;kill "$PID" >/dev/null 2>&1 || true;wait "$PID" || true
DOWN="/sdcard/Android/data/$PKG/files/Download/pick-pack-1291-beta-$VERSION.apk"
adb pull "$DOWN" "$OUT/ota-downloaded.apk" >/dev/null
test "$(sha256sum "$OUT/ota-downloaded.apk"|awk '{print $1}')" = "$SHA";test "$(stat -c '%s' "$OUT/ota-downloaded.apk")" = "$SIZE"
INSTALLED_APK_PATH=$(adb shell pm path "$PKG"|head -n1|sed 's/^package://'|tr -d '\r');test -n "$INSTALLED_APK_PATH";adb pull "$INSTALLED_APK_PATH" "$OUT/installed.apk" >/dev/null
test "$(sha256sum "$OUT/installed.apk"|awk '{print $1}')" = "$SHA";test "$(stat -c '%s' "$OUT/installed.apk")" = "$SIZE"
"$ANDROID_SDK_ROOT/build-tools/36.0.0/apksigner" verify --print-certs "$OUT/installed.apk" > "$OUT/cert.txt"
INST_SIGNER=$(grep -m1 'Signer #1 certificate SHA-256 digest:' "$OUT/cert.txt"|sed 's/.*digest: //'|tr 'A-F' 'a-f'|tr -d ':[:space:]');test "$INST_SIGNER" = "$SIGNER"
adb shell am start -W -n "$PKG/vn.pickpack1291.app.beta.FullBetaActivity" > "$OUT/launch.txt";! grep -Eq 'Error type|Permission Denial' "$OUT/launch.txt"

RAW=$(printf '%s' "$GAS_DEPLOYMENT_ID"|tr -d '\r\n\t ');DEP="$RAW";if [[ "$RAW" == *"/s/"* ]]; then DEP="${RAW#*/s/}";DEP="${DEP%%/*}";fi
GAS_URL="https://script.google.com/macros/s/$DEP/exec";echo "::add-mask::$GAS_URL"
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
  local ch="$1" current="$2" out="$3" body
  body=$(jq -nc --arg ch "$ch" --arg current "$current" '{action:"update_check",channel:$ch,current_version:$current}')
  gas "$body" "$out"
}
update BETA "$BASE" "$OUT/beta-old.json";jq -e --arg v "$VERSION" --arg p "$PKG" --arg h "$SHA" --argjson z "$SIZE" '
  .ok==true and .source=="GITHUB_RELEASE" and .channel=="BETA" and .available==true and .version_name==$v and .package==$p and .sha256==$h and .size==$z and
  (.apk_url|startswith("https://github.com/")) and (.apk_url|contains("/releases/download/"))
' "$OUT/beta-old.json" >/dev/null
update BETA "$VERSION" "$OUT/beta-current.json";jq -e --arg v "$VERSION" --arg p "$PKG" '
  .ok==true and .source=="GITHUB_RELEASE" and .channel=="BETA" and .available==false and .version_name==$v and .package==$p
' "$OUT/beta-current.json" >/dev/null
update STABLE 0.1.0-stable "$OUT/stable.json";jq -e '.ok==true and .channel=="STABLE" and .available==false' "$OUT/stable.json" >/dev/null
MAIN_AFTER=$(curl -fsSL --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/branches/main"|jq -r '.commit.sha');test "$MAIN_AFTER" = "$MAIN_BEFORE"
DISCOVERY_BODY=$(jq -nc '{action:"service_discovery",_app_channel:"BETA"}')
SERVICE_URL=$(curl -fsSL --connect-timeout 15 --max-time 35 -H 'content-type: application/json' "$GAS_URL" --data-binary "$DISCOVERY_BODY"|jq -r '.service_url');[[ "$SERVICE_URL" == https://* ]];echo "::add-mask::$SERVICE_URL"
curl -fsSL --connect-timeout 15 --max-time 30 "$SERVICE_URL/v1/authority" > "$OUT/authority.json"
jq -S '.authority' "$PUB" > "$OUT/pub-auth";jq -S '.authority' "$OUT/authority.json" > "$OUT/live-auth";cmp -s "$OUT/pub-auth" "$OUT/live-auth"
jq -n --arg v "$VERSION" --argjson c "$CODE" --arg p "$PKG" --arg base "$BASE" --arg h "$SHA" --argjson z "$SIZE" --arg signer "$INST_SIGNER" --arg main "$MAIN_AFTER" \
  --slurpfile beta "$OUT/beta-old.json" --slurpfile current "$OUT/beta-current.json" --slurpfile stable "$OUT/stable.json" --slurpfile auth "$OUT/authority.json" \
  '{status:"PASS",version_name:$v,version_code:$c,package:$p,base_version:$base,apk_sha256:$h,apk_size:$z,signer_sha256:$signer,
    ota_transport:"GITHUB_RELEASE",google_drive_apk:"FORBIDDEN",ota_from_base:true,ota_download_exact:true,
    installed_exact_bytes:true,installed_and_opened:true,beta_readback:$beta[0],target_current_readback:$current[0],stable_readback:$stable[0],
    stable_unchanged:true,main_sha:$main,main_unchanged:true,authority:$auth[0].authority,authority_change:"NONE"}' > "$OUT/receipt.json"
cat "$OUT/receipt.json"
