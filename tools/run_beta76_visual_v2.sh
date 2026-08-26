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
D8="$SDK_ROOT/build-tools/36.0.0/d8"
test -x "$D8"
mkdir -p "$HARNESS_BUILD/dex"
"$D8" \
  --min-api 29 \
  --lib "$ANDROID_JAR" \
  --classpath "$HARNESS_BUILD/classes" \
  --output "$HARNESS_BUILD/dex" \
  "$HARNESS_BUILD/classes/com/android/commands/uiautomator/VisualHierarchyDumper.class"
jar cf "$HARNESS_BUILD/beta77-visual-dumper.jar" -C "$HARNESS_BUILD/dex" classes.dex
test -s "$HARNESS_BUILD/beta77-visual-dumper.jar"
unzip -Z1 "$HARNESS_BUILD/beta77-visual-dumper.jar" | grep -Fxq 'classes.dex'

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
