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
REQ_SOURCE=$(jq -r '.source_sha' "$REQ");REQ_SIGNER=$(jq -r '.signer_sha256' "$REQ")
jq -e --arg v "$VERSION" --argjson code "$CODE" --arg pkg "$PKG" --arg src "$REQ_SOURCE" --arg signer "$REQ_SIGNER" '
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
grep -Fq 'cleanPdaSerial' "$OPS"
grep -Fq 'if(kind=="Trả")' "$OPS"
grep -Fq 'tag=h.serial' "$OPS"
grep -Fq 'Tài khoản $phone / $employeeName' "$OPS"
grep -Fq 'addBusinessShiftReconciliation(body);body.addView(gap(5))' "$OPS"
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
adb root >"$OUT/adb-root.txt" 2>&1 || true;timeout 30s adb wait-for-device
test "$(adb shell id -u 2>/dev/null|tr -d '\r')" = 0
adb install -r "$APK" >"$OUT/install-candidate.txt";adb install -r "$VERIFY_HARNESS_APK" >"$OUT/install-harness.txt"
for spec in '320 568 160' '360 640 180' '480 800 240'; do
  read -r W H D <<<"$spec";TAG="${W}x${H}"
  MODE=visual
  if [[ "$VISUAL_ONLY" != "true" && "$TAG" == "320x568" ]]; then MODE=checks; fi
  adb shell wm size "${W}x${H}" >/dev/null;adb shell wm density "$D" >/dev/null
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  adb shell pm clear "$PKG" >/dev/null
  adb shell svc wifi disable >/dev/null 2>&1 || true;adb shell svc data disable >/dev/null 2>&1 || true
  set +e
  timeout 150s adb shell am instrument -w -r -e mode "$MODE" -e tag "$TAG" -e mnv 981820081 -e mnv2 981820082 -e mnv3 981820083 vn.pickpack1291.verify/.Beta83UiChecksInstrumentation >"$OUT/$TAG-instrument.txt" 2>&1
  RC=$?
  set -e
  test "$RC" = 0;grep -Fq 'INSTRUMENTATION_CODE: 0' "$OUT/$TAG-instrument.txt"
  mkdir -p "$OUT/$TAG"
  adb pull "/sdcard/Android/data/$PKG/files/beta83-visual/." "$OUT/$TAG/" >/dev/null
  if [[ "$MODE" == checks ]]; then
    adb shell cat "/data/user/0/$PKG/shared_prefs/pp_beta83_verify.xml" >"$OUT/$TAG-flags.xml"
    for flag in current_day_filter header_removed header_sync_chip attendance_card root_back_stays old_warning_preserved qr_reconciliation null_sanitized incomplete_detail_button detail_reconciliation_visible staff_list_to_qr complete_direct_list staff_contact_layout staff_search_fixed settings_simplified dual_changelog log_metadata_persisted reconciliation_above_scan work_info_order qr_employee_contact pick_phone_account owner_actions_above_shift before_after_visible timeline_changed_fields_only employee_timeline_realtime_functional assignment_snapshot_authoritative scalar_snapshot_fallback timeline_newest_first hhmm_edit_confirmation delete_reason_editable report_compact_grid report_available_dates_only; do
      grep -Fq "name=\"$flag\" value=\"true\"" "$OUT/$TAG-flags.xml"
    done
  fi
done
python3 - <<'PY'
from pathlib import Path
import os
visual_only=os.environ.get("VISUAL_ONLY","false")=="true"
expected={"320x568":((320,568),5),"360x640":((360,640),5),"480x800":((480,800),5)} if visual_only else {"320x568":((320,568),13),"360x640":((360,640),5),"480x800":((480,800),5)}
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
  jq -nc --arg version "$VERSION" --argjson code "$CODE" --arg sha "$SHA" --argjson size "$SIZE" --argjson run "$GITHUB_RUN_ID" '{status:"PASS",version_name:$version,version_code:$code,apk_sha256:$sha,apk_size:$size,run:$run,visual_evidence_only:true,functional_pass:false,functional_inherited_run:33146411629,visual_sizes:["320x568","360x640","480x800"],screenshot_count:15,human_inspection_required:true}' > "$OUT/receipt.json"
else
  jq -nc --arg version "$VERSION" --argjson code "$CODE" --arg sha "$SHA" --argjson size "$SIZE" --argjson run "$GITHUB_RUN_ID" '{status:"PASS",version_name:$version,version_code:$code,apk_sha256:$sha,apk_size:$size,run:$run,functional_pass:true,current_day_only:true,incomplete_and_complete_paths:true,qr_session_cards:true,null_sanitized:true,settings_simplified:true,log_metadata_after_cleanup:true,old_warning_preserved:true,reconciliation_above_scan:true,work_info_order:true,owner_actions_above_shift:true,header_sync_chip:true,delete_reason_editable:true,pack_pair_validated:true,authoritative_resource_options:true,employee_ui_no_background_reset:true,dual_changelog:true,before_after_visible:true,timeline_changed_fields_only:true,employee_timeline_realtime:true,employee_timeline_realtime_functional:true,assignment_snapshot_authoritative:true,timeline_newest_first:true,hhmm_edit_confirmation:true,event_driven_status:true,partial_realtime_refresh:true,no_750ms_ui_ticker:true,report_available_dates_only:true,report_grid_borders:true,root_back_stays:true,header_back_removed:true,staff_contact_layout:true,staff_search_fixed:true,qr_employee_contact:true,attendance_card:true,detail_reconciliation_visible:true,pda_return_projection_sanitized:true,pick_phone_account:true,scalar_snapshot_fallback:true,reconciliation_emphasis:true,visual_sizes:["320x568","360x640","480x800"],screenshot_count:23,functional_size:"320x568",human_inspection_required:true}' > "$OUT/receipt.json"
fi
cat "$OUT/receipt.json"
