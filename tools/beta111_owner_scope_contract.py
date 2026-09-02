#!/usr/bin/env python3
from pathlib import Path

root=Path(__file__).resolve().parents[1]
read=lambda p:(root/p).read_text(encoding="utf-8")

activity=read("app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt")
document=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentManagementFeature.kt")
meal=read("app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt")
oldwarn=read("app/src/main/java/vn/pickpack1291/app/beta/OldSessionWarningFeature.kt")
reviewui=read("app/src/main/java/vn/pickpack1291/app/beta/ReviewAlertUi.kt")
transport=read("app/src/main/java/vn/pickpack1291/app/beta/M2ServiceTransport.kt")
runtime=read("app/src/main/java/vn/pickpack1291/app/beta/M2RuntimeBridge.kt")
mobile=read("service/src/mobile_hotfix.ts")
legacy=read("service/src/legacy.ts")
core=read("service/src/core.ts")
replication=read("service/src/replication.ts")

# Actual navigation stack, no fixed parent switch.
for token in ["ScreenSnapshot","screenBackStack","displayedScreenState","navigateBack()","screenBackStack.removeLast()"]:
    assert token in activity, token
back_block=activity[activity.index("private fun installSystemBackHandler"):activity.index("private fun simpleMessage")]
assert "when(screenState)" not in back_block
assert "handleBackNavigation()" in activity
assert "displayedScreenState!=screenState||displayedModule!=module" in activity

# Labor wheel must be vertical, finite and non-wrapping.
assert "NumberPicker(this)" in activity
assert activity.count("wrapSelectorWheel=false") >= 2
labor_block=activity[activity.index("private fun laborWheelPick"):activity.index("private fun resourceHome")]
assert "TimePickerDialog" not in labor_block

# Exact Service authority and stale-cache fencing.
for token in ['put("session_id",laborSessionId)','put("labor_id",active.optString("labor_id"))','put("business_date",laborBusinessDate)','api.call("labor_list"','openLaborExact','freshLabor?.optString("labor_id")']:
    assert token in activity, token
labor_home=activity[activity.index("private fun laborHome"):activity.index("private fun laborWheelPick")]
assert "PdaLocalProjection.employeeContext(this,v)" not in labor_home
assert '"labor_list"' in runtime and 'if(action==="labor_list")return laborList(env,body);' in mobile
for token in ["requestedSessionId","laborDate","session_id=?1 AND mnv=?2","attendance_session_id"]:
    assert token in mobile, token
for token in ['action=="labor_start"||action=="labor_finish"','payload.optString("business_date")']:
    assert token in transport, token
for token in ["session_id:text(payload.session_id","requestedLaborId","correction=payload.correction===true"]:
    assert token in legacy, token
for token in ["sessionId=text(p","LABOR_START_TIME_INVALID","LABOR_END_TIME_INVALID","LABOR_END_BEFORE_START","correction=req.payload.correction===true"]:
    assert token in core, token
assert "state IN (\'OPEN\',\'COMPLETED\')" in core
assert "M${row}:V${row}" in replication
assert 'corrected?"Sửa công nhật":"Hoàn thành công nhật"' in replication

# Start-only or start+end; completed edit and exit redirect.
for token in ['var startIso=Instant.now().toString();var endIso:String?=null','LƯU CÔNG NHẬT','selectedEnd==null','showCompletedLaborEditor','correction",true']:
    assert token in activity, token
assert activity.count("OPEN_LABOR_BLOCKS_EXIT") >= 1
assert 'openLaborExact(mnv,resolved.optString("session_id"))' in activity

# Daily labor list includes OPEN and COMPLETED.
for token in ["Chi tiết công nhật theo ngày",'state").equals("OPEN",true)','state").equals("COMPLETED",true)',"Hoàn thành: $done"]:
    assert token in activity, token

# Document batch mode is exclusive tick choice, not Spinner.
for token in ["multiPageCheck=CheckBox","multiDocumentCheck=CheckBox","multiDocumentCheck.isChecked","Một biên bản nhiều trang","Nhiều biên bản"]:
    assert token in document, token
assert "modeSpinner" not in document

# Warning/reconciliation shared geometry/treatment.
assert 'reconciliationButton("",false)' in activity
assert 'reconciliationButton(OldSessionWarningFeature.WARNING_TEXT,false)' in activity
assert "ReviewAlertUi.button" in activity
assert "ReviewAlertUi.button" in meal
assert "ReviewAlertUi.button" in oldwarn
for token in ["HEIGHT_DP=42","RADIUS_DP=10","STROKE_DP=2","TEXT_SP=10.5f","stateListAnimator=null"]:
    assert token in reviewui, token

# History delete only for canonical events and target-not-found is terminal cleanup.
assert 'history_source")=="SERVICE_CANONICAL"' in activity
assert "HISTORY_DELETE_TARGET_NOT_FOUND" in activity

print("beta111_owner_scope_contract=PASS nav_history=PASS labor_exact=PASS labor_wheel=PASS labor_day_list=PASS labor_correction=PASS exit_redirect=PASS document_tick=PASS warning_ui=PASS history_delete=PASS")
