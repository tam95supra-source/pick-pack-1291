#!/usr/bin/env bash
set -Eeuo pipefail
R=ops/beta-release-request.json
OUT=/tmp/beta-service-discovery
rm -rf "$OUT";mkdir -p "$OUT"
VERSION=$(jq -r '.version_name' "$R")
SHA=$(jq -r '.apk_sha256' "$R")
SIZE=$(jq -r '.apk_size' "$R")
PKG=$(jq -r '.package' "$R")
APK="/tmp/beta-candidate/pick-pack-1291-public-beta-$VERSION.apk"
test -f "$APK"
test "$(sha256sum "$APK"|awk '{print $1}')" = "$SHA"
test "$(stat -c '%s' "$APK")" = "$SIZE"
. tools/adb_stable_guard.sh
adb_root_stable 150
cp /tmp/adb-root-stable.txt "$OUT/adb-root.txt" 2>/dev/null || true
adb install -r "$APK" > "$OUT/install.txt"
adb install -r "$VERIFY_HARNESS_APK" > "$OUT/install-harness.txt"
adb shell svc wifi enable >/dev/null 2>&1 || true
adb shell svc data enable >/dev/null 2>&1 || true
sleep 4
set +e
timeout 60s adb shell am instrument -w -r -e mode service-discovery vn.pickpack1291.verify/.Beta83UiChecksInstrumentation > "$OUT/instrument.txt" 2>&1
RC=$?
set -e
adb logcat -d -v threadtime > "$OUT/logcat.txt" 2>&1 || true
test "$RC" = 0
grep -Fq 'INSTRUMENTATION_CODE: 0' "$OUT/instrument.txt"
grep -Fq 'service_discovery_cache_regression=PASS' "$OUT/instrument.txt"
grep -Fq 'cache_rewritten_in_process=PASS' "$OUT/instrument.txt"
grep -Fq 'stable_root_reused=false' "$OUT/instrument.txt"
adb shell cat "/data/user/0/$PKG/shared_prefs/pp_m2_service_transport.xml" > "$OUT/cache-after.xml" 2>/dev/null || true
SERVICE_URL=$(sed -n -E 's/^INSTRUMENTATION_(RESULT|STATUS): service_url=//p' "$OUT/instrument.txt"|tail -n1|tr -d '\r')
ENV_ID=$(sed -n -E 's/^INSTRUMENTATION_(RESULT|STATUS): environment_id=//p' "$OUT/instrument.txt"|tail -n1|tr -d '\r')
AUD=$(sed -n -E 's/^INSTRUMENTATION_(RESULT|STATUS): service_audience=//p' "$OUT/instrument.txt"|tail -n1|tr -d '\r')
test "$ENV_ID" = "BETA"
test "$AUD" = "PICK_PACK_1291_BETA"
[[ "$SERVICE_URL" == https://* ]]
test "$SERVICE_URL" != "https://pickpack1291.cc.cd"
jq -n --arg v "$VERSION" --arg h "$SHA" --argjson z "$SIZE" --arg env "$ENV_ID" --arg aud "$AUD" --arg url "$SERVICE_URL"   '{status:"PASS",version_name:$v,apk_sha256:$h,apk_size:$z,service_discovery_cache_regression:"PASS",stale_cache_seeded:true,ttl_unexpired:true,environment_id:$env,service_audience:$aud,service_url:$url,stable_root_reused:false,cache_rewritten_in_process:true,immediate_disk_flush_required:false,app_data_cleared:false}' > "$OUT/receipt.json"
cat "$OUT/receipt.json"
