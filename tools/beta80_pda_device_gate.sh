#!/usr/bin/env bash
set -euo pipefail
PKG=vn.pickpack1291.app.beta.publicbeta
VERIFY_COMPONENT=vn.pickpack1291.verify/.Beta80VerifyInstrumentation
OUT=/tmp/beta80-pda-verify
mkdir -p "$OUT"

adb root >"$OUT/adb-root.txt" 2>&1 || true
adb wait-for-device
test "$(adb shell id -u 2>/dev/null | tr -d '\\r')" = "0"

# Exact old Beta79 -> exact OTA positive path. No file picker and no host-side APK install for Beta80.
adb uninstall "$PKG" >/dev/null 2>&1 || true
adb install "$OLD_APK" >"$OUT/install-beta79.txt"
adb shell dumpsys package "$PKG" >"$OUT/package-beta79.txt"
grep -Fq 'versionName=0.4.2-beta.79' "$OUT/package-beta79.txt"
grep -Eq 'versionCode=85([[:space:]]|$)' "$OUT/package-beta79.txt"
adb shell appops set "$PKG" REQUEST_INSTALL_PACKAGES allow >/dev/null 2>&1 || true
adb install -r "$VERIFY_HARNESS_APK" >"$OUT/install-verify-harness.txt"

OTA_URL_B64=$(printf '%s' "$OTA_URL" | base64 -w0)
adb shell am instrument -w -r   -e mode ota   -e version '0.4.2-beta.80'   -e url_b64 "$OTA_URL_B64"   -e sha "$EXPECTED_SHA"   "$VERIFY_COMPONENT" >"$OUT/ota-instrument.txt" 2>&1 &
OTA_PID=$!

INSTALLER_SEEN=0
FILEPROVIDER_GRANT_SEEN=0
for _ in $(seq 1 240); do
  adb shell dumpsys activity activities >"$OUT/installer-activity-current.txt" 2>/dev/null || true
  adb shell dumpsys activity uri-permissions >"$OUT/installer-uri-permissions-current.txt" 2>/dev/null || true
  if grep -Eqi 'packageinstaller|installer' "$OUT/installer-activity-current.txt"; then
    cp "$OUT/installer-activity-current.txt" "$OUT/installer-activity.txt"
    INSTALLER_SEEN=1
  fi
  if grep -Fqi "$PKG.fileprovider" "$OUT/installer-uri-permissions-current.txt"; then
    cp "$OUT/installer-uri-permissions-current.txt" "$OUT/installer-uri-permissions.txt"
    FILEPROVIDER_GRANT_SEEN=1
  fi
  if [[ "$INSTALLER_SEEN" == 1 && "$FILEPROVIDER_GRANT_SEEN" == 1 ]]; then break; fi
  sleep 0.25
done
test "$INSTALLER_SEEN" = 1
test "$FILEPROVIDER_GRANT_SEEN" = 1

UPDATED=0
for _ in $(seq 1 120); do
  adb shell dumpsys package "$PKG" >"$OUT/package-current.txt" 2>/dev/null || true
  if grep -Fq 'versionName=0.4.2-beta.80' "$OUT/package-current.txt" && grep -Eq 'versionCode=86([[:space:]]|$)' "$OUT/package-current.txt"; then
    cp "$OUT/package-current.txt" "$OUT/package-beta80.txt"
    UPDATED=1
    break
  fi
  sleep 0.5
done
test "$UPDATED" = 1
wait "$OTA_PID" || true

DOWNLOADED="/sdcard/Android/data/$PKG/files/Download/pick-pack-1291-beta-0.4.2-beta.80.apk"
adb pull "$DOWNLOADED" "$OUT/ota-downloaded.apk" >/dev/null
test "$(sha256sum "$OUT/ota-downloaded.apk" | awk '{print $1}')" = "$EXPECTED_SHA"
test "$(stat -c '%s' "$OUT/ota-downloaded.apk")" = "$EXPECTED_SIZE"
grep -Fqi "$PKG.fileprovider" "$OUT/installer-uri-permissions.txt"

adb shell cat "/data/user/0/$PKG/shared_prefs/pp_beta80_verify.xml" >"$OUT/ota-flags.xml"
grep -Fq 'name="ota_prompt_entry_clicked" value="true"' "$OUT/ota-flags.xml"
grep -Fq 'name="ota_download_clicked" value="true"' "$OUT/ota-flags.xml"
grep -Fq 'name="ota_installer_seen" value="true"' "$OUT/ota-flags.xml"
adb shell am start -W -n "$PKG/vn.pickpack1291.app.beta.FullBetaActivity" >"$OUT/open-beta80.txt"
adb shell dumpsys activity activities >"$OUT/activity-beta80-open.txt"
grep -Fq "$PKG" "$OUT/activity-beta80-open.txt"

sql(){ (cd service && npx wrangler d1 execute "$D1_NAME" --remote --config wrangler.live.jsonc --command "$1" --json); }

# Installed Beta80 performs Vào ca from the actual QR employee UI.
adb shell am instrument -w -r   -e mode enter   -e login "$TEST_LOGIN"   -e mnv "$TEST_MNV"   -e service_token "$SERVICE_TOKEN"   -e service_url "$SERVICE_URL"   "$VERIFY_COMPONENT" >"$OUT/enter-instrument.txt" 2>&1
grep -Fq 'INSTRUMENTATION_CODE: 0' "$OUT/enter-instrument.txt"

ROW=''
for _ in $(seq 1 20); do
  ROW=$(sql "SELECT session_id,mnv,business_date,shift,work_choice,state,version FROM attendance_sessions WHERE mnv='$TEST_MNV' ORDER BY updated_at DESC LIMIT 1;")
  if [[ "$(jq -r '.[0].results[0].state // empty' <<<"$ROW")" == "ACTIVE" ]]; then break; fi
  sleep 0.5
done
printf '%s' "$ROW" >"$OUT/session-after-ui-enter.json"
TEST_SID=$(jq -r '.[0].results[0].session_id // empty' <<<"$ROW")
ENTER_DATE=$(jq -r '.[0].results[0].business_date // empty' <<<"$ROW")
ENTER_STATE=$(jq -r '.[0].results[0].state // empty' <<<"$ROW")
test -n "$TEST_SID" -a "$ENTER_DATE" = "$TEST_TODAY" -a "$ENTER_STATE" = "ACTIVE"
echo "::add-mask::$TEST_SID"

# Isolated fixture becomes an old active session; exact session_id is preserved.
sql "UPDATE attendance_sessions SET business_date='$TEST_OLD_DATE',shift='Ca 1',work_choice='PICK' WHERE session_id='$TEST_SID' AND mnv='$TEST_MNV' AND state='ACTIVE';" >/dev/null
MOVED=$(sql "SELECT session_id,mnv,business_date,shift,work_choice,state,version FROM attendance_sessions WHERE session_id='$TEST_SID';")
printf '%s' "$MOVED" >"$OUT/session-moved-to-old-date.json"
jq -e --arg sid "$TEST_SID" --arg m "$TEST_MNV" --arg d "$TEST_OLD_DATE" '.[0].results[0] | .session_id==$sid and .mnv==$m and .business_date==$d and .shift=="Ca 1" and .work_choice=="PICK" and .state=="ACTIVE"' <<<"$MOVED" >/dev/null

# Open the exact old-session card in the same QR UI, edit shift, then Bắn/Ra ca.
adb shell am instrument -w -r   -e mode historical   -e login "$TEST_LOGIN"   -e mnv "$TEST_MNV"   -e service_token "$SERVICE_TOKEN"   -e service_url "$SERVICE_URL"   "$VERIFY_COMPONENT" >"$OUT/historical-instrument.txt" 2>&1
grep -Fq 'INSTRUMENTATION_CODE: 0' "$OUT/historical-instrument.txt"

FINAL=''
for _ in $(seq 1 20); do
  FINAL=$(sql "SELECT session_id,mnv,business_date,shift,work_choice,state,version,pda_serial,user_pick,pack_table,user_pack,exit_at FROM attendance_sessions WHERE session_id='$TEST_SID';")
  if [[ "$(jq -r '.[0].results[0].state // empty' <<<"$FINAL")" == "ENDED" ]]; then break; fi
  sleep 0.5
done
printf '%s' "$FINAL" >"$OUT/d1-final-session.json"
jq -e --arg sid "$TEST_SID" --arg m "$TEST_MNV" --arg d "$TEST_OLD_DATE" '.[0].results[0] | .session_id==$sid and .mnv==$m and .business_date==$d and .shift=="Ca 2" and .state=="ENDED" and .version>=3 and (.exit_at|length)>0' <<<"$FINAL" >/dev/null

EVENTS=$(sql "SELECT event_type,entity_id,business_date,payload_json FROM events WHERE actor_id='$TEST_LOGIN' ORDER BY authority_epoch,authority_seq;")
printf '%s' "$EVENTS" >"$OUT/d1-fixture-events.json"
jq -e --arg sid "$TEST_SID" '[.[0].results[] | select(.entity_id==$sid and .event_type=="ATTENDANCE_ENTER")] | length==1' <<<"$EVENTS" >/dev/null
jq -e --arg sid "$TEST_SID" '[.[0].results[] | select(.entity_id==$sid and .event_type=="RESOURCE_CHANGE")] | length>=1' <<<"$EVENTS" >/dev/null
jq -e --arg sid "$TEST_SID" '[.[0].results[] | select(.entity_id==$sid and .event_type=="ATTENDANCE_EXIT")] | length==1' <<<"$EVENTS" >/dev/null
COUNT=$(sql "SELECT COUNT(*) n FROM attendance_sessions WHERE mnv='$TEST_MNV';")
test "$(jq -r '.[0].results[0].n' <<<"$COUNT")" = "1"

adb shell cat "/data/user/0/$PKG/shared_prefs/pp_beta80_verify.xml" >"$OUT/ui-flags.xml"
for flag in enter_ui_clicked historical_shared_ui historical_edit_clicked historical_exit_clicked; do
  grep -Fq "name=\"$flag\" value=\"true\"" "$OUT/ui-flags.xml"
done

curl -fsS "$SERVICE_URL/v1/authority" >"$OUT/authority-after.json"
jq -e --slurpfile b "$OUT/authority-before.json" '.ok==true and .authority.mode==$b[0].authority.mode and .authority.scope==$b[0].authority.scope and .authority.authority_epoch==$b[0].authority.authority_epoch and .authority.service_generation==$b[0].authority.service_generation' "$OUT/authority-after.json" >/dev/null
MAIN_AFTER=$(curl -fsS -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$GITHUB_REPOSITORY/branches/main" | jq -r '.commit.sha')
test "$MAIN_AFTER" = "$MAIN_BEFORE"
printf '%s\n' "$MAIN_AFTER" >"$OUT/main-after.txt"

PUBLIC_OK=0
for attempt in 0 1 2; do
  if curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' 'https://script.google.com/macros/s/AKfycbzbEoGfbNg6s2HnP-gUpcBJ7mMIkVBtYuQKMndb9seDV2c55lQwSUO1GZ-LtQ2CxMCauA/exec' -d '{"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.79"}' >"$OUT/beta-final.json" && jq -e --arg h "$EXPECTED_SHA" --argjson z "$EXPECTED_SIZE" '.ok==true and .channel=="BETA" and .available==true and .version_name=="0.4.2-beta.80" and ((.version_code//86)==86) and .sha256==$h and .size==$z and ((.apk_url//"")|length)>0' "$OUT/beta-final.json" >/dev/null 2>&1; then PUBLIC_OK=1; break; fi
  [[ "$attempt" -lt 2 ]] && sleep $((2+attempt*4))
done
test "$PUBLIC_OK" = 1

STABLE_OK=0
for attempt in 0 1 2; do
  if curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' 'https://script.google.com/macros/s/AKfycbzbEoGfbNg6s2HnP-gUpcBJ7mMIkVBtYuQKMndb9seDV2c55lQwSUO1GZ-LtQ2CxMCauA/exec' -d '{"action":"update_check","channel":"STABLE","current_version":"0.1.0-stable"}' >"$OUT/stable-final.json" && jq -e '.ok==true and .channel=="STABLE" and .available==false and .reason=="NO_APK"' "$OUT/stable-final.json" >/dev/null 2>&1; then STABLE_OK=1; break; fi
  [[ "$attempt" -lt 2 ]] && sleep $((2+attempt*4))
done
test "$STABLE_OK" = 1

jq -n   --arg sha "$EXPECTED_SHA" --argjson size "$EXPECTED_SIZE" --arg signer "$EXPECTED_SIGNER"   --arg sid "$TEST_SID" --arg mnv "$TEST_MNV" --arg old_date "$TEST_OLD_DATE" --arg main "$MAIN_AFTER"   --slurpfile beta "$OUT/beta-final.json" --slurpfile stable "$OUT/stable-final.json" --slurpfile auth "$OUT/authority-after.json"   '{status:"PASS",version_name:"0.4.2-beta.80",version_code:86,candidate_artifact:9629377960,apk_sha256:$sha,apk_size:$size,signer_sha256:$signer,ota_from_beta79_positive_update_click:true,ota_downloadmanager_exact_sha:true,fileprovider_installer_intent_seen:true,android_installer_clicked:true,file_picker_required:false,installed_and_opened_beta80:true,session:{mnv:$mnv,session_id:$sid,business_date:$old_date,flow:"Vào ca UI -> mở đúng session_id -> Sửa Ca 2 -> Bắn ra",shared_qr_ui:true,not_found:false,wrong_session:false,d1_final:"ENDED"},beta_readback:$beta[0],stable_readback:$stable[0],stable_unchanged:true,main_sha:$main,main_unchanged:true,authority:$auth[0].authority,authority_change:"NONE"}' >"$OUT/receipt.json"
cat "$OUT/receipt.json"
