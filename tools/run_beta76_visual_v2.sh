#!/usr/bin/env bash
set -Eeuo pipefail

SDK_ROOT="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
ANDROID_JAR="$SDK_ROOT/platforms/android-36/android.jar"
test -f "$ANDROID_JAR"

HARNESS_BUILD="$(mktemp -d /tmp/beta77-visual-dumper.XXXXXX)"
trap 'rm -rf "$HARNESS_BUILD"' EXIT
mkdir -p "$HARNESS_BUILD/classes"
javac -source 8 -target 8 \
  -cp "$ANDROID_JAR" \
  -d "$HARNESS_BUILD/classes" \
  tools/UiAutomationShellWrapper.java \
  tools/VisualHierarchyDumper.java
jar cf "$HARNESS_BUILD/beta77-visual-dumper.jar" \
  -C "$HARNESS_BUILD/classes" \
  com/android/commands/uiautomator/VisualHierarchyDumper.class
test -s "$HARNESS_BUILD/beta77-visual-dumper.jar"
! jar tf "$HARNESS_BUILD/beta77-visual-dumper.jar" | grep -Fq 'UiAutomationShellWrapper.class'

adb push "$HARNESS_BUILD/beta77-visual-dumper.jar" /data/local/tmp/beta77-visual-dumper.jar
adb shell chmod 644 /data/local/tmp/beta77-visual-dumper.jar

adb root >/tmp/beta76-adb-root.txt 2>&1 || true
adb wait-for-device
for i in 1 2; do
  if [[ "$(adb shell id -u 2>/dev/null | tr -d '\r')" == "0" ]]; then
    exec python3 tools/run_beta76_visual.py
  fi
  sleep $((i*2))
  adb root >>/tmp/beta76-adb-root.txt 2>&1 || true
  adb wait-for-device
done
cat /tmp/beta76-adb-root.txt >&2 || true
echo 'VISUAL_HARNESS_ADB_ROOT_REQUIRED' >&2
exit 31
