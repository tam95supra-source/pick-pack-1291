#!/usr/bin/env bash
set -Eeuo pipefail
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
