#!/usr/bin/env python3
from pathlib import Path

root=Path(__file__).resolve().parents[1]
ops=(root/"app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt").read_text()
docs=(root/"app/src/main/java/vn/pickpack1291/app/beta/DocumentManagementFeature.kt").read_text()
draft=(root/"app/src/main/java/vn/pickpack1291/app/beta/DocumentDraftStore.kt").read_text()
pending=(root/"app/src/main/java/vn/pickpack1291/app/beta/DocumentPendingStore.kt").read_text()
upload=(root/"app/src/main/java/vn/pickpack1291/app/beta/DocumentUploadEngine.kt").read_text()
drop=(root/"app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt").read_text()
meal=(root/"app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt").read_text()
lan=(root/"app/src/main/java/vn/pickpack1291/app/beta/LanCoordinator.kt").read_text()
m2=(root/"app/src/main/java/vn/pickpack1291/app/beta/M2ServiceTransport.kt").read_text()
bridge=(root/"app/src/main/java/vn/pickpack1291/app/beta/M2RuntimeBridge.kt").read_text()
doc_service=(root/"service/src/document_management.ts").read_text()
outbound=(root/"service/src/outbound_beta78.ts").read_text()
mobile=(root/"service/src/mobile_hotfix.ts").read_text()
migration=(root/"service/migrations/0013_beta116_owner_scope.sql").read_text()
gradle=(root/"app/build.gradle.kts").read_text()
notes=(root/"app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt").read_text()

assert 'applicationId = "vn.pickpack1291.app.beta.publicbeta"' in gradle
assert 'const val VERSION_NAME = ' in notes

# Document UX: icon CRUD, pre-upload selection/delete, note durability, swipe/zoom group viewer.
for token in ['ic_pp_add','ic_pp_edit','ic_pp_delete','selectedDraftKeys','selectAllDraftButton','deleteDraftButton','ZoomSwipeImageView','showSelectedViewer','viewDocumentGroup']:
    assert token in docs, token
assert 'removeItems(ownerLogin:String,keys:Set<String>)' in draft
assert 'updateNote(ownerLogin:String,key:String,note:String)' in draft
assert 'val note:String' in pending and '.put("note",i.note)' in pending
assert '.put("note",item.note)' in upload
assert 'note:r.note||""' in doc_service
assert 'ADD COLUMN note TEXT NOT NULL DEFAULT' in migration

# Report + PDA resource rules. OWNER Beta126 supersedes the old redundant
# "Tổng nhân sự" / "Khấu trừ công nhật" summary rows; retain the actual
# Pick/Pack-after-support semantics instead of pinning removed labels.
for token in ['val main=selected','NHÂN SỰ PICK & PACK THỰC TẾ SAU KHI LOẠI TRỪ HỖ TRỢ','CHI TIẾT CÔNG NHẬT','Công nhật theo vị trí']:
    assert token in ops, token
assert '"Tổng nhân sự" to' not in ops
assert '"Khấu trừ công nhật" to' not in ops
assert 'if(type=="PDA"&&key.any{it.isWhitespace()})' in ops
assert 'val last=key.takeLast(5)' in ops

# Dropped receiving list + selected canonical delete.
for token in ['ic_pp_add','ic_pp_edit','ic_pp_delete','outbound_drop_list','outbound_drop_delete','selectedDropIds','Chọn tất cả','Số kiện']:
    assert token in drop, token
assert 'OUTBOUND_DROP_DELETE_SELECTED' in outbound
assert 'action==="outbound_drop_list"' in outbound and 'action==="outbound_drop_delete"' in outbound
assert '"outbound_drop_list"' in bridge and '"outbound_drop_delete"' in bridge

# Attendance and QR filters. OWNER Beta123 supersedes the abbreviated search placeholder.
for token in ['Tìm mã nhân viên / họ tên','Tất cả ca','Tất cả NCC','Tất cả vị trí','QUÉT ĐỂ ĐIỂM DANH']:
    assert token in meal, token
assert 'Tìm MNV / họ tên' not in meal
inline=ops[ops.index("private fun addInlineCurrentShiftStaff"):ops.index("private fun addScannedOldSessionWarning")]
for token in ['Tất cả ca','Tất cả NCC','Tất cả vị trí','Danh sách QR vào / ra']:
    assert token in inline, token
# Beta115 canonical click semantics must stay exact while allowing implementation-local variable naming.
assert any(token in inline for token in [
    'setOnClickListener{showCurrentDayShiftStaff(currentDate,shift,group)}',
    'setOnClickListener{showCurrentDayShiftStaff(currentDate,shiftName,group)}',
])
assert 'setOnClickListener{if(id.mnv.isNotBlank())loadEmployee(id.mnv)}' in inline

# Labor: local list shell, Service exact-session detail, fixed-position review and filters.
# Beta117+ owns compact/select geometry, so the old Beta116 .88f/1.12f button-weight pin is superseded.
labor=ops[ops.index("private fun laborHome()"):ops.index("private fun laborWheelPick(")]
for token in ['pp_labor_list_cache_v116','Tất cả ca','Tất cả NCC','Tất cả vị trí','KIỂM TRA CÔNG NHẬT CHO CÁC VỊ TRÍ CỐ ĐỊNH','api.call("employee_context"']:
    assert token in labor, token
assert 'PdaLocalProjection.employeeContext(this,v)' not in labor

# SUPERADMIN password: one account at a time, privileged re-auth, verifier generation remains inside BetaApiClient.
assert 'private fun changeOtherAccountPassword' in ops
assert 'verifyActionPassword("đổi mật khẩu tài khoản $id")' in ops
assert '.put("password",a)' in ops

# Global isolated LAN test: Service authority/epoch + app sync; production route remains separate.
for token in ['testModeEnabled','testModeEpoch','applyGlobalTestMode','canRouteForTest','submitTest']:
    assert token in lan, token
assert 'lan_test_mode_get' in bridge and 'lan_test_mode_set' in bridge
assert 'lan_test_mode_get' in mobile and 'lan_test_mode_set' in mobile
assert 'CREATE TABLE IF NOT EXISTS lan_test_mode' in migration and 'epoch INTEGER NOT NULL DEFAULT 0' in migration
assert 'lan.canRouteForTest()' in m2 and 'lan.submitTest(body)' in m2
assert 'if(lan.canRoute())' in m2, "production LAN routing must remain separate"
for token in ['refreshGlobalLanTestMode','setGlobalLanTestMode','resilienceLanModeAutoEnabled']:
    assert token in ops, token
assert ('BẬT LAN TEST TOÀN CỤC' in ops) or ('BẬT LAN TEST CÔ LẬP' in ops), "global isolated LAN test control must remain visible"

# Lightweight tap feedback must stay transform-only; OWNER Beta117 refined the strength.
assert 'private fun tapFeedback(v:View)' in ops
feedback=ops[ops.index("private fun tapFeedback(v:View)"):ops.index("private fun iconActionButton")]
assert (('scaleX(.96f)' in feedback and 'scaleY(.96f)' in feedback) or ('scaleX(.95f)' in feedback and 'scaleY(.95f)' in feedback))
assert 'layoutParams' not in feedback and 'requestLayout' not in feedback

print("beta116_owner_scope_contract=PASS document=PASS report=PASS resource=PASS dropped=PASS attendance=PASS labor=PASS qr=PASS admin_password=PASS lan_global=PASS tap_feedback=PASS")
