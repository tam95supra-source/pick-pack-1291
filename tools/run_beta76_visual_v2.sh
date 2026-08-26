#!/usr/bin/env bash
set -Eeuo pipefail

SDK_ROOT="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
PLATFORM="$SDK_ROOT/platforms/android-29"
test -f "$PLATFORM/android.jar"
test -f "$PLATFORM/uiautomator.jar"

HARNESS_BUILD="$(mktemp -d /tmp/beta77-visual-dumper.XXXXXX)"
trap 'rm -rf "$HARNESS_BUILD"' EXIT
mkdir -p "$HARNESS_BUILD/classes"
javac -source 8 -target 8 \
  -cp "$PLATFORM/android.jar:$PLATFORM/uiautomator.jar" \
  -d "$HARNESS_BUILD/classes" \
  tools/VisualHierarchyDumper.java
jar cf "$HARNESS_BUILD/beta77-visual-dumper.jar" -C "$HARNESS_BUILD/classes" .
test -s "$HARNESS_BUILD/beta77-visual-dumper.jar"

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
