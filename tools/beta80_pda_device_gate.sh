#!/usr/bin/env bash
set -euo pipefail
adb root >/tmp/beta80-pda-verify/adb-root.txt 2>&1 || true
adb wait-for-device
test "$(adb shell id -u 2>/dev/null | tr -d '\\r')" = "0"

python3 /tmp/beta80_pda_verify.py ota-old
python3 /tmp/beta80_pda_verify.py fileprovider
python3 /tmp/beta80_pda_verify.py enter

sql(){ (cd service && npx wrangler d1 execute "$D1_NAME" --remote --config wrangler.live.jsonc --command "$1" --json); }
ROW=$(sql "SELECT session_id,mnv,business_date,shift,work_choice,state,version FROM attendance_sessions WHERE mnv='$TEST_MNV' ORDER BY updated_at DESC LIMIT 1;")
printf '%s' "$ROW" > /tmp/beta80-pda-verify/session-after-ui-enter.json
TEST_SID=$(jq -r '.[0].results[0].session_id // empty' <<<"$ROW")
ENTER_DATE=$(jq -r '.[0].results[0].business_date // empty' <<<"$ROW")
ENTER_STATE=$(jq -r '.[0].results[0].state // empty' <<<"$ROW")
test -n "$TEST_SID" -a "$ENTER_DATE" = "$TEST_TODAY" -a "$ENTER_STATE" = "ACTIVE"
echo "::add-mask::$TEST_SID"
sql "UPDATE attendance_sessions SET business_date='$TEST_OLD_DATE',work_choice='PICK' WHERE session_id='$TEST_SID' AND mnv='$TEST_MNV' AND state='ACTIVE';" >/dev/null
MOVED=$(sql "SELECT session_id,mnv,business_date,work_choice,state,version FROM attendance_sessions WHERE session_id='$TEST_SID';")
printf '%s' "$MOVED" > /tmp/beta80-pda-verify/session-moved-to-old-date.json
jq -e --arg sid "$TEST_SID" --arg m "$TEST_MNV" --arg d "$TEST_OLD_DATE" '.[0].results[0] | .session_id==$sid and .mnv==$m and .business_date==$d and .work_choice=="PICK" and .state=="ACTIVE"' <<<"$MOVED" >/dev/null
export TEST_SID
python3 /tmp/beta80_pda_verify.py historical

FINAL=$(sql "SELECT session_id,mnv,business_date,shift,work_choice,state,version,pda_serial,user_pick,pack_table,user_pack,exit_at FROM attendance_sessions WHERE session_id='$TEST_SID';")
printf '%s' "$FINAL" > /tmp/beta80-pda-verify/d1-final-session.json
jq -e --arg sid "$TEST_SID" --arg m "$TEST_MNV" --arg d "$TEST_OLD_DATE" '.[0].results[0] | .session_id==$sid and .mnv==$m and .business_date==$d and .shift=="Ca 2" and .state=="ENDED" and .version>=4 and (.exit_at|length)>0' <<<"$FINAL" >/dev/null
EVENTS=$(sql "SELECT event_type,entity_id,business_date,payload_json FROM events WHERE actor_id='$TEST_LOGIN' ORDER BY authority_epoch,authority_seq;")
printf '%s' "$EVENTS" > /tmp/beta80-pda-verify/d1-fixture-events.json
jq -e --arg sid "$TEST_SID" '[.[0].results[] | select(.entity_id==$sid and .event_type=="ATTENDANCE_ENTER")] | length==1' <<<"$EVENTS" >/dev/null
jq -e --arg sid "$TEST_SID" '[.[0].results[] | select(.entity_id==$sid and .event_type=="RESOURCE_CHANGE")] | length>=2' <<<"$EVENTS" >/dev/null
jq -e --arg sid "$TEST_SID" '[.[0].results[] | select(.entity_id==$sid and .event_type=="ATTENDANCE_EXIT")] | length==1' <<<"$EVENTS" >/dev/null
COUNT=$(sql "SELECT COUNT(*) n FROM attendance_sessions WHERE mnv='$TEST_MNV';")
test "$(jq -r '.[0].results[0].n' <<<"$COUNT")" = "1"

curl -fsS "$SERVICE_URL/v1/authority" > /tmp/beta80-pda-verify/authority-after.json
jq -e --slurpfile b /tmp/beta80-pda-verify/authority-before.json '.ok==true and .authority.mode==$b[0].authority.mode and .authority.scope==$b[0].authority.scope and .authority.authority_epoch==$b[0].authority.authority_epoch and .authority.service_generation==$b[0].authority.service_generation' /tmp/beta80-pda-verify/authority-after.json >/dev/null
MAIN_AFTER=$(curl -fsS -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$GITHUB_REPOSITORY/branches/main" | jq -r '.commit.sha')
test "$MAIN_AFTER" = "$MAIN_BEFORE"
printf '%s\\n' "$MAIN_AFTER" > /tmp/beta80-pda-verify/main-after.txt

PUBLIC_OK=0
for attempt in 0 1 2; do
  if curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' 'https://script.google.com/macros/s/AKfycbzbEoGfbNg6s2HnP-gUpcBJ7mMIkVBtYuQKMndb9seDV2c55lQwSUO1GZ-LtQ2CxMCauA/exec' -d '{"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.79"}' > /tmp/beta80-pda-verify/beta-final.json && jq -e --arg h "$EXPECTED_SHA" --argjson z "$EXPECTED_SIZE" '.ok==true and .channel=="BETA" and .available==true and .version_name=="0.4.2-beta.80" and ((.version_code//86)==86) and .sha256==$h and .size==$z and ((.apk_url//"")|length)>0' /tmp/beta80-pda-verify/beta-final.json >/dev/null 2>&1; then PUBLIC_OK=1; break; fi
  [[ "$attempt" -lt 2 ]] && sleep $((2+attempt*4))
done
test "$PUBLIC_OK" = 1
STABLE_OK=0
for attempt in 0 1 2; do
  if curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' 'https://script.google.com/macros/s/AKfycbzbEoGfbNg6s2HnP-gUpcBJ7mMIkVBtYuQKMndb9seDV2c55lQwSUO1GZ-LtQ2CxMCauA/exec' -d '{"action":"update_check","channel":"STABLE","current_version":"0.1.0-stable"}' > /tmp/beta80-pda-verify/stable-final.json && jq -e '.ok==true and .channel=="STABLE" and .available==false and .reason=="NO_APK"' /tmp/beta80-pda-verify/stable-final.json >/dev/null 2>&1; then STABLE_OK=1; break; fi
  [[ "$attempt" -lt 2 ]] && sleep $((2+attempt*4))
done
test "$STABLE_OK" = 1

jq -n --arg sha "$EXPECTED_SHA" --argjson size "$EXPECTED_SIZE" --arg signer "$EXPECTED_SIGNER" --arg sid "$TEST_SID" --arg mnv "$TEST_MNV" --arg old_date "$TEST_OLD_DATE" --arg main "$MAIN_AFTER"               --slurpfile beta /tmp/beta80-pda-verify/beta-final.json --slurpfile stable /tmp/beta80-pda-verify/stable-final.json --slurpfile auth /tmp/beta80-pda-verify/authority-after.json               '{status:"PASS",version_name:"0.4.2-beta.80",version_code:86,candidate_artifact:9629377960,apk_sha256:$sha,apk_size:$size,signer_sha256:$signer,ota_from_beta79_direct_installer:true,beta80_fileprovider_actual_self_reinstall:true,file_picker_required:false,installed_and_opened_beta80:true,session:{mnv:$mnv,session_id:$sid,business_date:$old_date,flow:"Vào ca UI -> mở đúng session_id -> Xóa -> Sửa Ca 2 -> Bắn ra",not_found:false,wrong_session:false,d1_final:"ENDED"},beta_readback:$beta[0],stable_readback:$stable[0],stable_unchanged:true,main_sha:$main,main_unchanged:true,authority:$auth[0].authority,authority_change:"NONE"}' > /tmp/beta80-pda-verify/receipt.json
cat /tmp/beta80-pda-verify/receipt.json
