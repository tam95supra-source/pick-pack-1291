#!/usr/bin/env bash
set -Eeuo pipefail
REQ=ops/beta-release-request.json
META=/tmp/beta-candidate/release-meta.json
test -f "$META"
VERSION=$(jq -r '.version_name' "$META"); PKG=$(jq -r '.package' "$META")
APK=$(find /tmp/beta-candidate -maxdepth 1 -type f -name '*.apk' | head -1)
test -n "$APK" -a -f "$APK" -a -f /tmp/beta83-verify-harness.apk
OUT=/tmp/beta-back36;rm -rf "$OUT";mkdir -p "$OUT"
. tools/adb_stable_guard.sh
adb_wait_stable 150 5
test "$(adb shell getprop ro.build.version.sdk | tr -d '\r')" = 36
adb install -r "$APK" > "$OUT/install-candidate.txt"
adb install -r /tmp/beta83-verify-harness.apk > "$OUT/install-harness.txt"
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
set +e
timeout 150s adb shell am instrument -w -r -e mode back36 -e mnv 981820081 -e mnv2 981820082 -e mnv3 981820083 vn.pickpack1291.verify/.Beta83UiChecksInstrumentation > "$OUT/instrument.txt" 2>&1
RC=$?
set -e
test "$RC" = 0
grep -Fq 'INSTRUMENTATION_CODE: 0' "$OUT/instrument.txt"
grep -Fq 'BETA89_BACK_API36_PASS' "$OUT/instrument.txt"
jq -n --arg version "$VERSION" --arg package "$PKG" '{status:"PASS",api_level:36,android:"16",system_back:"PASS",child_one_level:"PASS",root_stays:"PASS",version_name:$version,package:$package}' > "$OUT/receipt.json"
test -f /tmp/beta-verify/receipt.json
tmp=$(mktemp);jq '. + {back_api36:"PASS",back_api36_target:36}' /tmp/beta-verify/receipt.json > "$tmp";mv "$tmp" /tmp/beta-verify/receipt.json
cat "$OUT/receipt.json"
