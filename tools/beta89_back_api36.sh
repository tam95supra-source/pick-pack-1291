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
# API36 emulator Quickstep can transiently ANR during cold boot and cover the target app with a
# system modal. That is a harness condition, not an APK Back regression. Suppress/close system
# error dialogs before instrumentation; product errors still surface through instrumentation.
adb shell settings put global hide_error_dialogs 1 >/dev/null 2>&1 || true
adb shell am broadcast -a android.intent.action.CLOSE_SYSTEM_DIALOGS >/dev/null 2>&1 || true
adb shell input keyevent 4 >/dev/null 2>&1 || true
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true

run_back36(){
  local attempt="$1"
  set +e
  timeout 150s adb shell am instrument -w -r -e mode back36 -e mnv 981820081 -e mnv2 981820082 -e mnv3 981820083 vn.pickpack1291.verify/.Beta83UiChecksInstrumentation > "$OUT/instrument-$attempt.txt" 2>&1
  local rc=$?
  set -e
  if [[ "$rc" = 0 ]] && grep -Fq 'INSTRUMENTATION_CODE: 0' "$OUT/instrument-$attempt.txt" && grep -Fq 'BETA89_BACK_API36_PASS' "$OUT/instrument-$attempt.txt"; then
    cp "$OUT/instrument-$attempt.txt" "$OUT/instrument.txt"
    return 0
  fi
  return 1
}

if ! run_back36 1; then
  adb shell uiautomator dump /sdcard/back36-first-failure.xml >/dev/null 2>&1 || true
  adb pull /sdcard/back36-first-failure.xml "$OUT/back36-first-failure.xml" >/dev/null 2>&1 || true
  # Retry only the known cold-boot launcher/system-modal startup failure.
  if grep -Fq 'ACTIVITY_START_TIMEOUT:BUSINESS:SUPERADMIN' "$OUT/instrument-1.txt" && grep -Eqi "Quickstep isn't responding|package=\"android\"" "$OUT/back36-first-failure.xml" 2>/dev/null; then
    adb shell am broadcast -a android.intent.action.CLOSE_SYSTEM_DIALOGS >/dev/null 2>&1 || true
    adb shell input keyevent 4 >/dev/null 2>&1 || true
    adb shell am force-stop com.android.launcher3 >/dev/null 2>&1 || true
    sleep 3
    adb shell pm clear "$PKG" >/dev/null 2>&1 || true
    if ! run_back36 2; then
      echo "BACK36_INSTRUMENT_FAILURE_AFTER_HARNESS_RECOVERY" >&2
      cat "$OUT/instrument-2.txt" >&2 || true
      exit 1
    fi
  else
    echo "BACK36_INSTRUMENT_FAILURE" >&2
    cat "$OUT/instrument-1.txt" >&2 || true
    exit 1
  fi
fi
jq -n --arg version "$VERSION" --arg package "$PKG" '{status:"PASS",api_level:36,android:"16",system_back:"PASS",child_one_level:"PASS",root_stays:"PASS",version_name:$version,package:$package}' > "$OUT/receipt.json"
test -f /tmp/beta-verify/receipt.json
tmp=$(mktemp);jq '. + {back_api36:"PASS",back_api36_target:36}' /tmp/beta-verify/receipt.json > "$tmp";mv "$tmp" /tmp/beta-verify/receipt.json
cat "$OUT/receipt.json"
