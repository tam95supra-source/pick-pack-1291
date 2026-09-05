#!/usr/bin/env python3
from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]
read=lambda p:(root/p).read_text(encoding="utf-8")

ops=read("app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt")
transport=read("app/src/main/java/vn/pickpack1291/app/beta/M2ServiceTransport.kt")
store=read("app/src/main/java/vn/pickpack1291/app/beta/OperationalDataStore.kt")
meal_store=read("app/src/main/java/vn/pickpack1291/app/beta/MealAttendanceLocalStore.kt")
postmeal=read("app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt")
meal_service=read("service/src/meal_attendance.ts")
bridge=read("app/src/main/java/vn/pickpack1291/app/beta/M2RuntimeBridge.kt")
calendar=read("app/src/main/java/vn/pickpack1291/app/beta/DataDatePickerUi.kt")
notes=read("app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt")
gradle=read("app/build.gradle.kts")
service=read("service/src/index.ts")
core=read("service/src/core.ts")
mobile=read("service/src/mobile_hotfix.ts")
compat=read("service/src/compat.ts")
outbound=read("service/src/outbound_beta78.ts")
session_hotfix=read("service/src/session_hotfix.ts")
publish=read("tools/beta83_publish_ota.sh")

# 1) Changelog is version-fenced; Beta115 is the minimum accepted baseline and later Betas inherit this contract.
beta_block=gradle[gradle.index('create("beta")'):gradle.index('create("stable")')]
code_match=re.search(r'versionCode = (\d+)',beta_block)
name_match=re.search(r'versionName = "(0\.4\.2-beta\.(\d+))"',beta_block)
assert code_match and int(code_match.group(1))>=121
assert name_match and int(name_match.group(2))>=115
assert f'const val VERSION_NAME = "{name_match.group(1)}"' in notes
assert 'verifyBetaReleaseNotes' in gradle and 'dependsOn("verifyBetaReleaseNotes")' in gradle

# 2) Admin audit durable routing keeps transport action and business audit action separate.
assert '.put("action","admin_audit")' in transport
assert '.put("audit_action",action)' in transport
assert 'audit_action?:string' in service
assert 'action:String(raw.audit_action||"").trim()' in service

# 3) SUPERADMIN can remove local terminal history without inventing Service deletes.
assert 'fun deleteLocalHistory(eventIds:Collection<String>)' in store
assert '"mutation_outbox","event_id=? AND status IN' in store
delete_fn=ops[ops.index("private fun deleteHistoryBulk"):ops.index("private fun historyActionVi")]
assert 'if(!isSuper())' in delete_fn
assert 'operationalStore.deleteLocalHistory(clean)' in delete_fn
assert 'deferred_ids' in delete_fn and 'addAll(canonical)' in delete_fn
assert 'addAll(clean)' not in delete_fn[delete_fn.index('val deferred='):]

# 4,7,10) Scan/select/common UI hierarchy is centralized; locked review warning stays separate.
mnv=ops[ops.index("private fun mnvInput"):ops.index("private fun scanSearchInput")]
assert 'scanField(h,true,50)' in mnv and 'setStroke(dp(2),teal)' in mnv
labelled=ops[ops.index("private fun labelled"):ops.index("private fun primary")]
assert 'l.uppercase()' in labelled and 'Typeface.DEFAULT_BOLD' in labelled
assert 'private fun spinner(items:Array<String>)=Spinner(this).apply{' in labelled
assert 'minimumHeight=dp(36)' in labelled and 'v.minHeight=dp(38)' in labelled
assert 'private fun outline()=GradientDrawable().apply{setColor(surface);cornerRadius=dp(12)' in ops

# 5,6) Labor scan precedes list; multi-interval is explicit, non-overlap, max one OPEN.
labor_home=ops[ops.index("private fun laborHome"):ops.index("private fun laborWheelPick")]
assert labor_home.index('section("Ghi nhận công nhật")') < labor_home.index('section("Chi tiết công nhật theo ngày")')
assert 'DataDatePickerUi.show(this,laborDates,selectedLaborDate)' in labor_home
labor_ctx=ops[ops.index("private fun showLaborContext"):ops.index("private fun resourceHome")]
assert 'ctx.optJSONArray("labor_intervals")' in labor_ctx and '"Các khoảng công nhật trong phiên"' in labor_ctx
for token in ['LABOR_OTHER_INTERVAL_OPEN','LABOR_INTERVAL_OVERLAP','LABOR_START_IN_FUTURE','LABOR_END_AFTER_SHIFT_OR_EXIT','FUTURE_LABOR_BLOCKS_EXIT','deductStaffEnabled']:
    assert token in core, token
for token in ['OPEN_LABOR_BLOCKS_EXIT','FUTURE_LABOR_BLOCKS_EXIT','MAX(end_at) max_end']:
    assert token in session_hotfix, token
assert 'LABOR_END_IN_FUTURE' not in core
for token in ['"CA 1":14*60','"CA HC":17*60','"CA 2":22*60']:
    assert token in core, token
assert 'arrayOf("00","15","30","45")' in ops and 'wrapSelectorWheel=true' in ops
assert 'allowFuture:Boolean=false' in ops and '!allowFuture&&picked.isAfter' in ops
assert '"Mã nhân viên KHÁC"' not in labor_ctx
assert 'private fun showLaborBatchCreate' in ops and 'private fun showLaborBatchFinish' in ops
assert 'verifyActionPassword("tạo công nhật nhanh cho ${chosen.size} nhân sự")' in ops
assert 'verifyActionPassword("kết thúc công nhật nhanh cho ${chosen.size} nhân sự")' in ops
assert 'labor_intervals:laborRows' in mobile
assert 'if(action==="labor_dates")return laborDates(env);' in mobile
assert '"labor_dates"' in bridge
for token in ['staffShiftKey','label:"Hỗ trợ bộ phận khác"','matrix(main,columns)','deducted.has(staffShiftKey(s.mnv,s.shift))']:
    assert token in compat, token
assert 'rowsByType' not in compat, "Support report must count each MNV+shift once across multiple labor types"

# Release provenance: APK bytes bind candidate source; mutable service source is guarded separately.
assert 'CANDIDATE_SOURCE=$(jq -r \'.candidate_source_sha // .source_sha\' "$R")' in publish
assert 'SERVICE_SOURCE=$(jq -r \'.source_sha\' "$R")' in publish
assert 'git diff --quiet "$SERVICE_SOURCE" HEAD -- service google-apps-script' in publish
assert 'git diff --quiet "$CANDIDATE_SOURCE" HEAD -- app' in publish
assert 'ensure_beta_github_release.sh "$VERSION" "$CANDIDATE_SOURCE"' in publish

# 8) Display-only calendar visibly disables empty dates; edit calendar remains unrestricted.
for token in ['isEnabled=enabled','alpha=if(enabled)1f else .30f','if(enabled)setOnClickListener','availableDates:Collection<String>','val today=LocalDate.now()','val enabled=hasData||date==today']:
    assert token in calendar, token
assert ops.count("DatePickerDialog") == 1, "Only staff start-date editor may keep unrestricted DatePickerDialog"
assert ops.count("DataDatePickerUi.show(") >= 3, "Report, History and Labor must use data-only calendar"
assert "DatePickerDialog" not in postmeal, "Point Attendance display history must not use unrestricted DatePickerDialog"
assert "DataDatePickerUi.show(activity,availableDates,selected.toString())" in postmeal
assert 'selectSpinner(values:List<String>)' in postmeal
assert 'labelledSelect("Lý do không vào ca",reasonSpinner)' in postmeal
assert 'setItems(reasons)' not in postmeal
assert 'api.call("meal_attendance_dates")' in postmeal
assert "availableDatesWithData" in meal_store
assert "export async function mealAttendanceDates" in meal_service
assert '"meal_attendance_dates"' in bridge and 'action==="meal_attendance_dates"' in mobile

# 8b) Outbound location replication must preserve physical Sheet row indexes across blank rows.
location_replication=outbound[outbound.index('if(e.event_type.startsWith("OUTBOUND_LOCATION_"))'):outbound.index('export async function replicateOutboundPending')]
assert 'values=rows.map(r=>norm(r[0])),keys=values.map(key)' in location_replication
assert '.filter(Boolean)' not in location_replication
assert 'A${idx+2}:A${idx+2}' in location_replication

# 9) OWNER Beta123 supersedes the older inline-roster-after-scan behavior.
# Shift review remains compact, but once a scan has a result neither the scan screen nor
# rendered employee context may append the full current-shift roster. The standalone
# roster component remains available for explicit/no-result list surfaces.
recon=ops[ops.index("private fun addBusinessShiftReconciliation"):ops.index("private fun addInlineCurrentShiftStaff")]
assert 'HIỂN THỊ CHI TIẾT NHÂN SỰ' not in recon
assert 'shiftStaffOrdered(pending)' in recon and '"RA CA"' in recon
scan=ops[ops.index("private fun employeeScan()"):ops.index("private fun employeeRenderSignature")]
assert 'addInlineCurrentShiftStaff(body)' not in scan
render=ops[ops.index("private fun renderEmployee(ctx"):ops.index("private fun sameEmployeeContext")]
assert 'addInlineCurrentShiftStaff(body)' not in render
inline=ops[ops.index("private fun addInlineCurrentShiftStaff"):ops.index("private fun addScannedOldSessionWarning")]
assert ('showCurrentDayShiftStaff(currentDate,shift,group)' in inline or 'showCurrentDayShiftStaff(currentDate,shiftName,group)' in inline)
for token in ['setOnClickListener{if(id.mnv.isNotBlank())loadEmployee(id.mnv)}','contentDescription="Mở quét QR vào ra']:
    assert token in inline, token

print("beta123_owner_scope_contract=PASS changelog=PASS audit=PASS history_delete=PASS labor_revised=PASS bulk=PASS select_ui=PASS today_calendar=PASS outbound_sheet_row_index=PASS scan_roster_suppression=PASS")
