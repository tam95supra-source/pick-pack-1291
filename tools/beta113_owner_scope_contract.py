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

# 1) Changelog is version-fenced and current Beta metadata is exact.
assert 'versionCode = 119' in gradle
assert 'versionName = "0.4.2-beta.113"' in gradle
assert 'const val VERSION_NAME = "0.4.2-beta.113"' in notes
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
assert 'l.uppercase()' in labelled and 'Typeface.DEFAULT_BOLD' in labelled and 'minimumHeight=dp(46)' in labelled
assert 'private fun outline()=GradientDrawable().apply{setColor(surface);cornerRadius=dp(12)' in ops

# 5,6) Labor scan precedes list; multi-interval is explicit, non-overlap, max one OPEN.
labor_home=ops[ops.index("private fun laborHome"):ops.index("private fun laborWheelPick")]
assert labor_home.index('section("Ghi nhận công nhật")') < labor_home.index('section("Chi tiết công nhật theo ngày")')
assert 'DataDatePickerUi.show(this,laborDates,selectedLaborDate)' in labor_home
labor_ctx=ops[ops.index("private fun showLaborContext"):ops.index("private fun resourceHome")]
assert 'ctx.optJSONArray("labor_intervals")' in labor_ctx and '"Các khoảng công nhật trong phiên"' in labor_ctx
for token in ['LABOR_OTHER_INTERVAL_OPEN','LABOR_INTERVAL_OVERLAP','LABOR_START_IN_FUTURE','LABOR_END_IN_FUTURE']:
    assert token in core, token
assert 'labor_intervals:laborRows' in mobile
assert 'if(action==="labor_dates")return laborDates(env);' in mobile
assert '"labor_dates"' in bridge

# 8) Display-only calendar visibly disables empty dates; edit calendar remains unrestricted.
for token in ['isEnabled=enabled','alpha=if(enabled)1f else .30f','if(enabled)setOnClickListener','availableDates:Collection<String>']:
    assert token in calendar, token
assert ops.count("DatePickerDialog") == 1, "Only staff start-date editor may keep unrestricted DatePickerDialog"
assert ops.count("DataDatePickerUi.show(") >= 3, "Report, History and Labor must use data-only calendar"
assert "DatePickerDialog" not in postmeal, "Point Attendance display history must not use unrestricted DatePickerDialog"
assert "DataDatePickerUi.show(activity,availableDates,selected.toString())" in postmeal
assert 'api.call("meal_attendance_dates")' in postmeal
assert "availableDatesWithData" in meal_store
assert "export async function mealAttendanceDates" in meal_service
assert '"meal_attendance_dates"' in bridge and 'action==="meal_attendance_dates"' in mobile

# 9) Shift review tile no longer navigates to full roster; roster is inline below scan/session.
recon=ops[ops.index("private fun addBusinessShiftReconciliation"):ops.index("private fun addInlineCurrentShiftStaff")]
assert 'HIỂN THỊ CHI TIẾT NHÂN SỰ' not in recon
assert 'shiftStaffOrdered(pending)' in recon and '"RA CA"' in recon
scan=ops[ops.index("private fun employeeScan()"):ops.index("private fun employeeRenderSignature")]
assert scan.index('body.addView(mnv') < scan.index('addInlineCurrentShiftStaff(body)')
render=ops[ops.index("private fun renderEmployee(ctx"):ops.index("private fun sameEmployeeContext")]
assert render.index('when(state)') < render.index('addInlineCurrentShiftStaff(body)')

print("beta113_owner_scope_contract=PASS changelog=PASS audit=PASS history_delete=PASS scan_select_ui=PASS labor_multi_interval=PASS all_view_data_dates=PASS inline_roster=PASS")
