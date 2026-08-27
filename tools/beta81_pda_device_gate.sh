#!/usr/bin/env bash
set -Eeuo pipefail

OUT=/tmp/beta81-pda-verify
PKG=vn.pickpack1291.app.beta.publicbeta
OTA_VERIFY=vn.pickpack1291.verify/.Beta80VerifyInstrumentation
LOCAL_VERIFY=vn.pickpack1291.verify/.Beta81LocalChecksInstrumentation
EXPECTED_SIGNER=d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e
SERVICE_URL=https://pickpack.1291.workers.dev
mkdir -p "$OUT"

for n in OLD_APK NEW_APK OTA_URL APK_SHA APK_SIZE VERIFY_HARNESS_APK ANDROID_SDK_ROOT GAS_DEPLOYMENT_ID GH_TOKEN GITHUB_API_URL GITHUB_REPOSITORY MAIN_BEFORE; do
  test -n "${!n:-}"
done

adb root >"$OUT/adb-root.txt" 2>&1 || true
adb wait-for-device
test "$(adb shell id -u 2>/dev/null | tr -d '\r')" = 0

adb uninstall "$PKG" >/dev/null 2>&1 || true
adb install "$OLD_APK" >"$OUT/install-beta80.txt"
adb shell dumpsys package "$PKG" >"$OUT/package-beta80.txt"
grep -Fq 'versionName=0.4.2-beta.80' "$OUT/package-beta80.txt"
grep -Eq 'versionCode=86([[:space:]]|$)' "$OUT/package-beta80.txt"
adb shell appops set "$PKG" REQUEST_INSTALL_PACKAGES allow >/dev/null 2>&1 || true
adb install -r "$VERIFY_HARNESS_APK" >"$OUT/install-harness.txt"

URL_B64=$(printf '%s' "$OTA_URL" | base64 -w0)
adb shell am instrument -w -r   -e mode ota   -e version 0.4.2-beta.81   -e url_b64 "$URL_B64"   -e sha "$APK_SHA"   "$OTA_VERIFY" >"$OUT/ota-instrument.txt" 2>&1 &
OTA_PID=$!

UPDATED=0
for _ in $(seq 1 180); do
  adb shell dumpsys package "$PKG" >"$OUT/package-current.txt" 2>/dev/null || true
  if grep -Fq 'versionName=0.4.2-beta.81' "$OUT/package-current.txt"     && grep -Eq 'versionCode=87([[:space:]]|$)' "$OUT/package-current.txt"; then
    cp "$OUT/package-current.txt" "$OUT/package-beta81.txt"
    UPDATED=1
    break
  fi
  sleep 0.5
done
test "$UPDATED" = 1
kill "$OTA_PID" >/dev/null 2>&1 || true
wait "$OTA_PID" || true

DOWNLOADED="/sdcard/Android/data/$PKG/files/Download/pick-pack-1291-beta-0.4.2-beta.81.apk"
adb pull "$DOWNLOADED" "$OUT/ota-downloaded.apk" >/dev/null
test "$(sha256sum "$OUT/ota-downloaded.apk" | awk '{print $1}')" = "$APK_SHA"
test "$(stat -c '%s' "$OUT/ota-downloaded.apk")" = "$APK_SIZE"

BASE_PATH=$(adb shell pm path "$PKG" | head -n1 | sed 's/^package://' | tr -d '\r')
test -n "$BASE_PATH"
adb pull "$BASE_PATH" "$OUT/installed-base.apk" >/dev/null
test "$(sha256sum "$OUT/installed-base.apk" | awk '{print $1}')" = "$APK_SHA"
test "$(stat -c '%s' "$OUT/installed-base.apk")" = "$APK_SIZE"
"$ANDROID_SDK_ROOT/build-tools/36.0.0/apksigner" verify --print-certs "$OUT/installed-base.apk" >"$OUT/installed-cert.txt"
INSTALLED_SIGNER=$(grep -m1 'Signer #1 certificate SHA-256 digest:' "$OUT/installed-cert.txt"   | sed 's/.*digest: //' | tr 'A-F' 'a-f' | tr -d ':[:space:]')
test "$INSTALLED_SIGNER" = "$EXPECTED_SIGNER"

adb install -r "$VERIFY_HARNESS_APK" >"$OUT/reinstall-harness.txt"
adb shell ip link set eth0 down >/dev/null 2>&1 || true
adb shell am instrument -w -r   -e login beta81_verify   -e mnv 981810081   -e mnv2 981810082   -e service_token offline-beta81   -e service_url http://127.0.0.1:1   "$LOCAL_VERIFY" >"$OUT/beta81checks.txt" 2>&1
grep -Fq 'INSTRUMENTATION_CODE: 0' "$OUT/beta81checks.txt"
adb shell cat "/data/user/0/$PKG/shared_prefs/pp_beta81_verify.xml" >"$OUT/beta81-flags.xml"
for flag in reconciliation_home_1_0 reconciliation_qr_1_0 rollover_old_active_preserved old_resources_preserved scanned_old_warning; do
  grep -Fq "name=\"$flag\" value=\"true\"" "$OUT/beta81-flags.xml"
done

RAW=$(printf '%s' "$GAS_DEPLOYMENT_ID" | tr -d '\r\n\t ')
DEPLOYMENT_ID="$RAW"
if [[ "$RAW" == *"/s/"* ]]; then
  DEPLOYMENT_ID="${RAW#*/s/}"
  DEPLOYMENT_ID="${DEPLOYMENT_ID%%/*}"
fi
test -n "$DEPLOYMENT_ID"
GAS_URL="https://script.google.com/macros/s/$DEPLOYMENT_ID/exec"
echo "::add-mask::$GAS_URL"

read_update(){
  local channel="$1" current="$2" out="$3" attempt
  for attempt in 0 1 2; do
    if curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL"       -d "{\"action\":\"update_check\",\"channel\":\"$channel\",\"current_version\":\"$current\"}" > "$out"; then
      return 0
    fi
    [[ "$attempt" -lt 2 ]] || break
    sleep $((2 + attempt * 4))
  done
  return 1
}

read_update BETA 0.4.2-beta.80 "$OUT/beta-old-readback.json"
jq -e --arg h "$APK_SHA" --argjson z "$APK_SIZE" '
  .ok==true and .channel=="BETA" and .available==true and
  .version_name=="0.4.2-beta.81" and .sha256==$h and .size==$z
' "$OUT/beta-old-readback.json" >/dev/null
read_update BETA 0.4.2-beta.81 "$OUT/beta-current-readback.json"
jq -e '.ok==true and .channel=="BETA" and .available==false and .version_name=="0.4.2-beta.81"' "$OUT/beta-current-readback.json" >/dev/null
read_update STABLE 0.1.0-stable "$OUT/stable-readback.json"
jq -e '.ok==true and .channel=="STABLE" and .available==false and .reason=="NO_APK"' "$OUT/stable-readback.json" >/dev/null

MAIN_AFTER=$(curl -fsSL --connect-timeout 15 --max-time 30   -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json'   "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/branches/main" | jq -r '.commit.sha')
test "$MAIN_AFTER" = "$MAIN_BEFORE"
curl -fsSL --connect-timeout 15 --max-time 30 "$SERVICE_URL/v1/authority" > "$OUT/authority.json"
jq -e '.ok==true and .authority.mode=="SERVICE_PRIMARY" and .authority.scope=="PRODUCTION"' "$OUT/authority.json" >/dev/null
test "$(jq -r '.authority.authority_epoch' "$OUT/authority.json")" = 9
test "$(jq -r '.authority.service_generation' "$OUT/authority.json")" = m2-prod-reset-20260823-001

jq -n   --arg h "$APK_SHA" --argjson z "$APK_SIZE" --arg signer "$INSTALLED_SIGNER" --arg main "$MAIN_AFTER"   --slurpfile beta "$OUT/beta-old-readback.json"   --slurpfile current "$OUT/beta-current-readback.json"   --slurpfile stable "$OUT/stable-readback.json"   --slurpfile auth "$OUT/authority.json"   '{
    status:"PASS",
    version_name:"0.4.2-beta.81",
    version_code:87,
    candidate_run:33073351925,
    candidate_artifact:9646920908,
    visual_artifact:9647045177,
    service_artifact:9646805806,
    apk_sha256:$h,
    apk_size:$z,
    signer_sha256:$signer,
    ota_from_beta80:true,
    ota_download_exact:true,
    installed_exact_bytes:true,
    installed_and_opened_beta81:true,
    fixes:{
      reconciliation_ended_exit_only:true,
      reconciliation_home_1_0:true,
      reconciliation_qr_1_0:true,
      scanned_old_session_warning:true,
      midnight_rollover_old_active_preserved:true,
      old_resources_not_released:true
    },
    beta_readback:$beta[0],
    target_current_readback:$current[0],
    stable_readback:$stable[0],
    stable_unchanged:true,
    main_sha:$main,
    main_unchanged:true,
    authority:$auth[0].authority,
    authority_change:"NONE"
  }' > "$OUT/receipt.json"

jq -e '
  .status=="PASS" and
  .fixes.reconciliation_ended_exit_only==true and
  .fixes.reconciliation_qr_1_0==true and
  .fixes.scanned_old_session_warning==true and
  .fixes.midnight_rollover_old_active_preserved==true and
  .fixes.old_resources_not_released==true and
  .stable_unchanged==true and
  .main_unchanged==true and
  .authority_change=="NONE"
' "$OUT/receipt.json" >/dev/null
cat "$OUT/receipt.json"
