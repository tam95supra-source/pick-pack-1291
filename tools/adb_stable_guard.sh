#!/usr/bin/env bash
# Source-only helper for emulator/PDA CI harnesses.
adb_wait_stable(){
  local timeout_s="${1:-120}" needed="${2:-5}"
  local deadline
  deadline=$((SECONDS+timeout_s))
  local good=0 serial="" state="" boot="" probe=""
  while (( SECONDS < deadline )); do
    adb start-server >/dev/null 2>&1 || true
    serial="$(adb devices | awk 'NR>1 && $2=="device"{print $1;exit}')"
    if [[ -n "$serial" ]]; then
      export ANDROID_SERIAL="$serial"
      state="$(adb get-state 2>/dev/null || true)"
      boot="$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
      probe="$(adb shell 'printf ADB_STABLE' 2>/dev/null | tr -d '\r' || true)"
      if [[ "$state" == device && "$boot" == 1 && "$probe" == ADB_STABLE ]]; then
        good=$((good+1))
        if (( good >= needed )); then return 0; fi
      else
        good=0
      fi
    else
      good=0
    fi
    adb reconnect offline >/dev/null 2>&1 || true
    sleep 2
  done
  adb devices -l >&2 || true
  echo "ADB_STABILITY_TIMEOUT" >&2
  return 1
}
adb_root_stable(){
  adb_wait_stable "${1:-120}" 3
  adb root >/tmp/adb-root-stable.txt 2>&1 || true
  sleep 2
  adb_wait_stable "${1:-120}" 5
  [[ "$(adb shell id -u 2>/dev/null | tr -d '\r')" == 0 ]] || { cat /tmp/adb-root-stable.txt >&2 || true; echo "ADB_ROOT_NOT_READY" >&2; return 1; }
}
