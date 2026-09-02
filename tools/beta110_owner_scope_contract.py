#!/usr/bin/env python3
from pathlib import Path

root=Path(__file__).resolve().parents[1]
read=lambda p:(root/p).read_text(encoding="utf-8")

activity=read("app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt")
document=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentManagementFeature.kt")
draft=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentDraftStore.kt")
pending=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentPendingStore.kt")
meal=read("app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt")
core=read("service/src/core.ts")
session=read("service/src/session_hotfix.ts")
doc_service=read("service/src/document_management.ts")
admin_audit=read("service/src/admin_audit.ts")
entry=read("service/src/entry_product.ts")

# Document multi-image / multi-page / multi-document / bulk delete.
for token in ["Intent.EXTRA_ALLOW_MULTIPLE","onImagesSelected(uris","clipData"]:
    assert token in activity, token
for token in ["Một biên bản nhiều trang","Nhiều biên bản","MULTI_PAGE","MULTI_DOCUMENT","selectedDocumentIds","deleteSelectedRecords","filterSpinner"]:
    assert token in document, token
assert 'val pageIndex=if(mode=="MULTI_PAGE")index+1 else 1' in document
assert 'val pageCount=if(mode=="MULTI_PAGE")batch.size else 1' in document
assert "fun loadAll(ownerLogin:String):List<Draft>" in draft
assert "fun append(ownerLogin:String" in draft and '"manifest.json"' in draft
for token in ["groupId:String","groupMode:String","pageIndex:Int","pageCount:Int"]:
    assert token in pending, token
for token in ["documentDeleteMutate","processDocumentDeleteMutations","DOCUMENT_DELETE_SELECTED","group_id","page_index","page_count"]:
    assert token in doc_service, token
assert '"/v1/documents/delete"' in entry

# Document operations must reach canonical history.
for token in ["document_upload","document_delete","document_category_create","document_category_update","document_category_delete"]:
    assert token in admin_audit, token
for token in ["DOCUMENT_UPLOAD","DOCUMENT_DELETE","DOCUMENT_CATEGORY_CREATE","DOCUMENT_CATEGORY_UPDATE","DOCUMENT_CATEGORY_DELETE"]:
    assert token in activity, token

# Labor: explicit time picker/range, open record can exist, exit remains fail-closed while OPEN.
labor_start=activity[activity.index("private fun showLaborContext"):activity.index("private fun resourceHome")]
assert "laborWheelPick" in activity and activity.count("wrapSelectorWheel=false") >= 2
assert '.put("start_at",startIso)' in labor_start
assert '.put("end_at",end)' in labor_start or '.put("end_at",selectedEnd)' in labor_start
assert '.put("time_marker"' not in labor_start
assert "laborOpenWarning()" in activity and 'api.call("labor_list"' in activity
assert "Chi tiết công nhật theo ngày" in activity and "CẢNH BÁO:" in activity
for token in ["selectedStart","LABOR_START_TIME_INVALID","selectedEnd","LABOR_END_TIME_INVALID","LABOR_END_BEFORE_START"]:
    assert token in core, token
assert "state='OPEN'" in session and "OPEN_LABOR_BLOCKS_EXIT" in session, "OPEN labor must block exit"

# Attendance: compact UI, no literal null, active warning/date semantics preserved.
assert 'fun safe(v:String)=v.trim().takeUnless{it.isBlank()||it.equals("null",true)}?:"-"' in meal
assert 'header.addView(text("ĐIỂM DANH",15f,Color.WHITE,true))' in meal
assert "Ngày hiện tại có thể cập nhật" not in meal
assert "MEAL_EMPLOYEE_NOT_ACTIVE" in meal
assert "buildHomeWarning" in meal
assert 'ses.optString("business_date")==date' in meal

# Remove technical/AI-style helper prose from touched screens.
for forbidden in [
    "Ảnh được nén trên máy rồi tải thẳng lên Google Drive",
    "Service chỉ lưu thông tin biên bản",
    "Sửa: đổi tên toàn bộ biên bản và file Drive thuộc loại",
    "Ảnh chỉ giữ tạm trên máy khi chưa được Drive xác nhận",
    "Tìm trên toàn bộ lịch sử đang giữ trên PDA",
    "Cần OWNER",
]:
    assert forbidden not in document+activity, forbidden

print("beta110_owner_scope_contract=PASS document_batch=PASS labor_range=PASS labor_exit_guard=PASS attendance_null=PASS compact_copy=PASS history=PASS")
