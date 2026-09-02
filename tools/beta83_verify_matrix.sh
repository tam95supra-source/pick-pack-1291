#!/usr/bin/env bash
set -Eeuo pipefail
REQ=ops/beta-release-request.json
VERSION=$(jq -r '.version_name' "$REQ");CODE=$(jq -r '.version_code' "$REQ");PKG=$(jq -r '.package' "$REQ")
META=/tmp/beta-candidate/release-meta.json;APK=/tmp/beta-candidate/pick-pack-1291-public-beta-$VERSION.apk
test -f "$META" -a -f "$APK" -a -f "$VERIFY_HARNESS_APK"
SHA=$(jq -r '.apk_sha256' "$META");SIZE=$(jq -r '.apk_size' "$META")
STAGE=$(jq -r '.stage' "$REQ")
VISUAL_ONLY=$(jq -r '.visual_evidence_only // false' "$REQ")
export VISUAL_ONLY
REQ_SOURCE=$(jq -r '.source_sha' "$REQ");REQ_CANDIDATE_SOURCE=$(jq -r '.candidate_source_sha // .source_sha' "$REQ");REQ_SIGNER=$(jq -r '.signer_sha256' "$REQ")
jq -e --arg v "$VERSION" --argjson code "$CODE" --arg pkg "$PKG" --arg src "$REQ_CANDIDATE_SOURCE" --arg signer "$REQ_SIGNER" '
  .version_name==$v and .version_code==$code and .package==$pkg and .source_sha==$src and
  .signer_sha256==$signer and .candidate_locked==true and
  .stable_publish=="FORBIDDEN" and .authority_change=="NONE"
' "$META" >/dev/null
if [[ "$STAGE" == "VERIFY_ONLY" ]]; then
  REQ_SHA=$(jq -r '.apk_sha256' "$REQ");REQ_SIZE=$(jq -r '.apk_size' "$REQ")
  test "$SHA" = "$REQ_SHA";test "$SIZE" = "$REQ_SIZE"
fi
OPS=app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt
SYNC=app/src/main/java/vn/pickpack1291/app/beta/ForegroundSyncCoordinator.kt
API=app/src/main/java/vn/pickpack1291/app/beta/BetaApiClient.kt
grep -Fq 'QRCodeWriter().encode' "$OPS"
grep -Fq 'api.latestGithubRelease("BETA")' "$OPS"
grep -Fq 'api.latestGithubRelease("STABLE")' "$OPS"
grep -Fq 'if (channel.equals("STABLE", true))' "$API"
grep -Fq 'callback(githubUpdate("BETA", "0.0.0"))' "$API"
grep -Fq 'put("apk_url", asset.optString("browser_download_url"))' "$API"
grep -Fq 'STABLE_NOT_PUBLIC' "$API"
grep -q 'businessRealtimeRefresh' "$OPS"
grep -q 'reportRealtimeRefresh' "$OPS"
grep -q 'historyRealtimeRefresh' "$OPS"
! grep -q 'postDelayed(this,750L)' "$OPS"
grep -q 'override fun onLost(network: Network)' "$SYNC"
grep -q 'Bàn Pack / User Pack không còn khớp cấu hình hiện tại' "$OPS"
grep -q 'Chọn ngày có dữ liệu' "$OPS"
! grep -q 'Site 1291 • Ngày báo cáo' "$OPS"
grep -q 'showSoftInput(r,android.view.inputmethod.InputMethodManager.SHOW_IMPLICIT)' "$OPS"
! grep -Fq 'contentDescription="Quay lại"' "$OPS"
grep -Fq 'contentDescription="Tìm kiếm nhân sự cố định"' "$OPS"
grep -Fq 'Điểm danh nhân sự' "$OPS"
grep -Fq 'postMealAttendanceScreen()' "$OPS"
grep -Fq '"MEAL_ATTENDANCE" -> PostMealAttendanceFeature.onRealtime(changedDates)' "$OPS"
grep -Fq 'dynamic.addView(PostMealAttendanceFeature.buildHomeWarning(this,api){postMealAttendanceScreen()},matchWrap())' "$OPS"
grep -Fq 'root.addView(PostMealAttendanceFeature.build(this,api){businessHome()},LinearLayout.LayoutParams(-1,0,1f))' "$OPS"
grep -Fq 'root.addView(DropReceiveFeature.build(this,api,login,name,role){businessHome()},LinearLayout.LayoutParams(-1,0,1f))' "$OPS"
grep -Fq 'if(isAdmin())items.add(Triple(R.drawable.ic_pp_history,"Lịch sử","HISTORY"))' "$OPS"
grep -Fq 'if(target=="HISTORY"&&!isAdmin()){module="BUSINESS";businessHome();return}' "$OPS"
grep -Fq 'private fun historyScreen(){' "$OPS"
grep -Fq 'if(!isAdmin()){module="BUSINESS";businessHome();return}' "$OPS"
grep -Fq 'ses.optString("business_date")==date' app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt
grep -Fq 'CẢNH BÁO: CÒN $count NHÂN SỰ CHƯA ĐIỂM DANH' app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt
grep -Fq 'localInteractive=localNow!=null&&localNow.optBoolean("session_known",true)' "$OPS"
grep -Fq 'QrPerformanceDiagnostics.recordLocal' "$OPS"
grep -Fq 'minusDays(13)' app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt
grep -Fq 'minusDays(13)' app/src/main/java/vn/pickpack1291/app/beta/MealAttendanceLocalStore.kt
grep -Fq 'pp_meal_attendance_14d.db' app/src/main/java/vn/pickpack1291/app/beta/MealAttendanceLocalStore.kt
grep -Fq 'insertWithOnConflict("meal_day_cache",null,values,SQLiteDatabase.CONFLICT_REPLACE)' app/src/main/java/vn/pickpack1291/app/beta/MealAttendanceLocalStore.kt
! grep -Fq 'ON CONFLICT(business_date) DO UPDATE' app/src/main/java/vn/pickpack1291/app/beta/MealAttendanceLocalStore.kt
grep -Fq 'cleanPdaSerial' "$OPS"
grep -Fq 'if(kind=="Trả")' "$OPS"
grep -Fq 'tag=h.serial' "$OPS"
grep -Fq 'Tài khoản $phone / $employeeName' "$OPS"
grep -Fq 'addBusinessShiftReconciliation(body)' "$OPS"
test "$(grep -Fc 'if(projected.isNotBlank())return projected' "$OPS")" -ge 3
! grep -Fq 'super.onBackPressed()' "$OPS"
test "$(sha256sum "$APK"|awk '{print $1}')" = "$SHA";test "$(stat -c '%s' "$APK")" = "$SIZE"
OUT=/tmp/beta-verify;rm -rf "$OUT";mkdir -p "$OUT"
grep -Fq '"EMPLOYEE" -> employeeTimelineRealtimeRefresh?.invoke(changedDates)' app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt
grep -Fq 'private fun addRealtimeSessionTimeline' app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt
grep -Fq 'if(type=="RESOURCE_CHANGE"&&(p.optJSONObject("before")!=null||p.optJSONObject("after")!=null)&&sessionWorkChangeDetail(p).isBlank())continue' app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt
grep -Fq 'api.call("master_options",JSONObject().put("mnv",s.optString("mnv")))' "$OPS"
grep -Fq 'if(!forceRefresh&&localInteractive&&screenState=="EMPLOYEE"&&liveEmployeeMnv==resolved)return@runOnUiThread' "$OPS"
! grep -Fq 'val preferLocal=key=="pack_tables"||key=="pack_tables_reissue"' "$OPS"
grep -Fq 'THAY ĐỔI BẢN HIỆN TẠI' "$OPS"
grep -Fq 'THAY ĐỔI BẢN MỚI' "$OPS"
. tools/adb_stable_guard.sh
adb_root_stable 150
cp /tmp/adb-root-stable.txt "$OUT/adb-root.txt" 2>/dev/null || true
adb install -r "$APK" >"$OUT/install-candidate.txt";adb install -r "$VERIFY_HARNESS_APK" >"$OUT/install-harness.txt"
for spec in '320 568 160' '360 640 180' '480 800 240'; do
  read -r W H D <<<"$spec";TAG="${W}x${H}"
  MODE=visual
  if [[ "$VISUAL_ONLY" != "true" && "$TAG" == "320x568" ]]; then MODE=checks; fi
  adb shell wm size "${W}x${H}" >/dev/null;adb shell wm density "$D" >/dev/null
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  adb shell pm clear "$PKG" >/dev/null
  adb shell svc wifi disable >/dev/null 2>&1 || true;adb shell svc data disable >/dev/null 2>&1 || true
  adb logcat -c >/dev/null 2>&1 || true
  set +e
  timeout 150s adb shell am instrument -w -r -e mode "$MODE" -e tag "$TAG" -e mnv 981820081 -e mnv2 981820082 -e mnv3 981820083 vn.pickpack1291.verify/.Beta83UiChecksInstrumentation >"$OUT/$TAG-instrument.txt" 2>&1
  RC=$?
  adb logcat -d -v threadtime >"$OUT/$TAG-logcat.txt" 2>&1 || true
  set -e
  test "$RC" = 0;grep -Fq 'INSTRUMENTATION_CODE: 0' "$OUT/$TAG-instrument.txt"
  mkdir -p "$OUT/$TAG"
  adb pull "/sdcard/Android/data/$PKG/files/beta83-visual/." "$OUT/$TAG/" >/dev/null
  if [[ "$MODE" == checks ]]; then
    adb shell cat "/data/user/0/$PKG/shared_prefs/pp_beta83_verify.xml" >"$OUT/$TAG-flags.xml"
    for flag in current_day_filter header_removed header_sync_chip attendance_card root_back_stays old_warning_preserved qr_reconciliation null_sanitized incomplete_detail_button detail_reconciliation_visible shift_staff_grouped_ncc_beta105 shift_staff_filter_counts_beta105 staff_list_to_qr settings_download_qr_beta105 complete_direct_list staff_contact_layout staff_search_fixed settings_simplified dual_changelog authoritative_editor_offline_guard session_exit_identity_guard pda_exit_only_when_session_has_pda old_warning_unified report_columns_aligned log_metadata_persisted reconciliation_above_scan work_info_order qr_employee_contact pick_phone_account owner_actions_above_shift before_after_visible timeline_changed_fields_only employee_timeline_realtime_functional assignment_snapshot_authoritative scalar_snapshot_fallback timeline_newest_first hhmm_edit_confirmation delete_reason_editable report_compact_grid report_available_dates_only meal_attendance_module meal_current_day_scan meal_duplicate_local meal_invalid_employee_guard status_header_meal meal_old_session_blocked history_hidden_user history_deeplink_blocked_user qr_local_not_entered_no_service_wait status_chip_details_beta100 document_management_card_beta107 document_management_controls_beta107 document_pending_ui_beta108 document_pending_durable_beta108 document_selected_draft_durable_beta109 document_selected_multi_draft_beta110 document_batch_controls_beta110 document_category_cache_offline_beta109 document_media_cache_beta108 document_category_rename_delete_owner_rule_beta108 labor_open_list_beta110 navigation_history_beta111 meal_null_dash_beta110 resilience_scenario_selectable resilience_test_ledger_result resilience_business_outbox_isolated resilience_options_bordered_beta101 resilience_history_cards_beta101 resilience_stop_control_beta101; do
      grep -Fq "name=\"$flag\" value=\"true\"" "$OUT/$TAG-flags.xml"
    done
  fi
done
if [[ "$VISUAL_ONLY" != "true" ]]; then
  adb shell svc wifi enable >/dev/null 2>&1 || true
  adb shell svc data enable >/dev/null 2>&1 || true
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  sleep 4
  set +e
  timeout 45s adb shell am instrument -w -r -e mode service-discovery vn.pickpack1291.verify/.Beta83UiChecksInstrumentation >"$OUT/service-discovery-instrument.txt" 2>&1
  DRC=$?
  set -e
  test "$DRC" = 0
  grep -Fq 'INSTRUMENTATION_CODE: 0' "$OUT/service-discovery-instrument.txt"
  grep -Fq 'service_discovery_cache_regression=PASS' "$OUT/service-discovery-instrument.txt"
fi
python3 - <<'PY'
from pathlib import Path
import os
visual_only=os.environ.get("VISUAL_ONLY","false")=="true"
expected={"320x568":((320,568),11),"360x640":((360,640),11),"480x800":((480,800),11)} if visual_only else {"320x568":((320,568),19),"360x640":((360,640),11),"480x800":((480,800),11)}
root=Path("/tmp/beta-verify")
total=0
for tag,(size,count) in expected.items():
    files=sorted((root/tag).glob("*.png"))
    assert len(files)==count,(tag,len(files),count,[p.name for p in files])
    for p in files:
        b=p.read_bytes()
        assert b[:8]==b"\x89PNG\r\n\x1a\n",p
        wh=(int.from_bytes(b[16:20],"big"),int.from_bytes(b[20:24],"big"))
        assert wh==size,(p,wh,size)
        total+=1
(root/"visual-summary.txt").write_text(f"screenshots={total}\nsizes=320x568,360x640,480x800\nhuman_inspection_required=true\n",encoding="utf-8")
PY
if [[ "$VISUAL_ONLY" == "true" ]]; then
  jq -nc --arg version "$VERSION" --argjson code "$CODE" --arg sha "$SHA" --argjson size "$SIZE" --argjson run "$GITHUB_RUN_ID" '{status:"PASS",version_name:$version,version_code:$code,apk_sha256:$sha,apk_size:$size,run:$run,visual_evidence_only:true,functional_pass:false,functional_inherited_run:33146411629,visual_sizes:["320x568","360x640","480x800"],screenshot_count:33,human_inspection_required:true}' > "$OUT/receipt.json"
else
  jq -nc --arg version "$VERSION" --argjson code "$CODE" --arg sha "$SHA" --argjson size "$SIZE" --argjson run "$GITHUB_RUN_ID" '{status:"PASS",version_name:$version,version_code:$code,apk_sha256:$sha,apk_size:$size,run:$run,functional_pass:true,current_day_only:true,incomplete_and_complete_paths:true,qr_session_cards:true,null_sanitized:true,settings_simplified:true,log_metadata_after_cleanup:true,old_warning_preserved:true,reconciliation_above_scan:true,work_info_order:true,owner_actions_above_shift:true,header_sync_chip:true,delete_reason_editable:true,pack_pair_validated:true,authoritative_resource_options:true,authoritative_editor_offline_guard:true,session_exit_identity_guard:true,pda_exit_only_when_session_has_pda:true,old_warning_unified:true,report_columns_aligned:true,employee_ui_no_background_reset:true,dual_changelog:true,before_after_visible:true,timeline_changed_fields_only:true,employee_timeline_realtime:true,employee_timeline_realtime_functional:true,assignment_snapshot_authoritative:true,timeline_newest_first:true,hhmm_edit_confirmation:true,event_driven_status:true,partial_realtime_refresh:true,no_750ms_ui_ticker:true,report_available_dates_only:true,report_grid_borders:true,meal_attendance_module:true,meal_current_day_scan:true,meal_duplicate_local:true,meal_invalid_employee_guard:true,status_header_meal:true,meal_old_session_blocked:true,history_hidden_user:true,history_deeplink_blocked_user:true,qr_local_fast_path:true,root_back_stays:true,header_back_removed:true,status_chip_details_beta100:true,resilience_scenario_selectable:true,resilience_test_ledger_result:true,resilience_business_outbox_isolated:true,resilience_options_bordered_beta101:true,resilience_history_cards_beta101:true,resilience_stop_control_beta101:true,service_discovery_cache_regression:true,staff_contact_layout:true,staff_search_fixed:true,qr_employee_contact:true,attendance_card:true,detail_reconciliation_visible:true,shift_staff_grouped_ncc_beta105:true,shift_staff_filter_counts_beta105:true,settings_download_qr_beta105:true,pda_return_projection_sanitized:true,pick_phone_account:true,scalar_snapshot_fallback:true,reconciliation_emphasis:true,visual_sizes:["320x568","360x640","480x800"],screenshot_count:41,functional_size:"320x568",human_inspection_required:true}' > "$OUT/receipt.json"
fi
cat "$OUT/receipt.json"
