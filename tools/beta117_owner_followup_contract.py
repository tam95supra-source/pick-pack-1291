#!/usr/bin/env python3
from pathlib import Path

root=Path(__file__).resolve().parents[1]
read=lambda p:(root/p).read_text(encoding="utf-8")

doc=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentManagementFeature.kt")
ops=read("app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt")
attendance=read("app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt")
drop=read("app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt")
lan=read("app/src/main/java/vn/pickpack1291/app/beta/LanCoordinator.kt")
transport=read("app/src/main/java/vn/pickpack1291/app/beta/M2ServiceTransport.kt")
bridge=read("app/src/main/java/vn/pickpack1291/app/beta/M2RuntimeBridge.kt")
doc_service=read("service/src/document_management.ts")
entry=read("service/src/entry_product.ts")
mobile=read("service/src/mobile_hotfix.ts")
outbound=read("service/src/outbound_beta78.ts")
migration=read("service/migrations/0014_beta117_manual_lan.sql")
visual_harness=read("tools/Beta83UiChecksInstrumentation.java")
gradle=read("app/build.gradle.kts")
notes=read("app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt")
assert not (root/"service/migrations/0014_beta117_owner_followup.sql").exists()
assert 'versionCode = 123' in gradle and 'versionName = "0.4.2-beta.117"' in gradle
assert 'const val VERSION_NAME = "0.4.2-beta.117"' in notes
assert 'versionCode = 1' in gradle and 'versionName = "0.1.0-stable"' in gradle
assert 'DOCUMENT_PENDING_BOX_VISIBLE_WHEN_EMPTY' in visual_harness
assert 'DOCUMENT_MODE_VISIBLE_WITH_ZERO_DRAFTS' in visual_harness
assert 'waitText("Ảnh chờ tải",true,false,10000L)' not in visual_harness
assert 'waitText("Không có ảnh chờ tải.",true,false,10000L)' not in visual_harness
assert visual_harness.count("PENDING_BOX_VISIBLE_WHEN_EMPTY") >= 2
# Release request metadata is checked independently by resilience_static_gate.mjs.

for token in [
    "modeRowHost.visibility=if(enabled)View.VISIBLE else View.GONE",
    "pendingBoxView.visibility=if(items.isEmpty())View.GONE else View.VISIBLE",
    "draftActionRow.visibility=if(has)View.VISIBLE else View.GONE",
    "currentDocumentItems",
    "Biên bản • vuốt mọi ảnh / pinch / kéo ảnh",
    "TOÀN MÀN HÌNH",
    "translationX=(translationX+e.x-lastX)",
    "translationY=(translationY+e.y-lastY)",
    "updateDocumentRecord(",
    'client.post("/v1/documents/update"',
    "selectedInViewer",
]:
    assert token in doc, token
assert doc.index("selectAllDraftButton=") < doc.index("deleteDraftButton=") < doc.index("uploadButton=")
assert 'iconButton(android.R.drawable.ic_menu_agenda,navy,"Chọn tất cả' in doc
assert 'iconButton(R.drawable.ic_pp_delete,red,"Xóa' in doc
for token in ["export async function documentUpdate", "DOCUMENT_UPDATE", "before:{category_id:", "after:{category_id:"]:
    assert token in doc_service, token
assert 'u.pathname==="/v1/documents/update"' in entry

for token in [
    'DateTimeFormatter.ofPattern("HH:mm dd/MM/yyyy")',
    "sortedByDescending",
    '"DO: ${x.optString("do_number")',
    '"Số kiện: ${x.optInt("package_count")',
    'val canDelete=normalizedRole=="ADMIN"||actualSuper',
]:
    assert token in drop, token
assert 'auth.role!=="ADMIN"&&auth.role!=="SUPERADMIN"' in outbound

spinner=ops[ops.index("private fun spinner(items:Array<String>)"):ops.index("private fun primary")]
assert "minimumHeight=dp(36)" in spinner and "v.minHeight=dp(38)" in spinner
assert "postDelayed(it,140L)" in attendance
assert "renderGeneration" in attendance and "startIndex+24" in attendance
assert "qrRenderGeneration" in ops and "from+24" in ops
assert "laborRenderGeneration" in ops and "from+16" in ops
assert "from+18" in ops and "renderGroup(groupIndex+1)" in ops
assert "listRenderGeneration" in ops and "from+20" in ops
assert "historySearchGeneration" in ops and "postDelayed({if(generation==historySearchGeneration" in ops and "},160L)" in ops
assert "documentRenderGeneration" in doc and "from+10" in doc and "addDocumentChunk" in doc
assert "dropRenderGeneration" in drop and "from+20" in drop and "addDropChunk" in drop
viewer=doc[doc.index("private fun viewDocumentGroup"):doc.index("private fun formatTime")]
assert viewer.count("category.adapter=")==1, "viewer must reuse category adapter while swiping"
assert "val bitmap=bytes?.let{BitmapFactory.decodeByteArray(it,0,it.size)}" in viewer
draft_viewer=doc[doc.index("private fun showSelectedViewer"):doc.index("private fun applyCategoryEntries")]
assert 'button("TOÀN MÀN HÌNH",navy)' in draft_viewer

for token in [
    '"CHỌN TẤT CẢ"',
    '"TẠO CÔNG NHẬT ĐÃ CHỌN"',
    "selected=linkedSetOf<String>()",
    "remaining.removeAll{it.optString(\"session_id\")==sid}",
    "showLaborBatchCreateForm(chosen.map{laborBatchCandidateFromSession(it)})",
]:
    assert token in ops, token

for token in [
    "manualModeEnabled",
    "applyGlobalManualMode",
    "globalManualModeEnabled",
    "if(manualModeEnabled||testModeEnabled)",
]:
    assert token in lan, token
for token in [
    "lan.globalManualModeEnabled()",
    '"LAN_MANUAL_PENDING"',
    '"LAN_MANUAL_NOT_READY"',
]:
    assert token in transport, token
assert '"lan_manual_mode_get","lan_manual_mode_set"' in bridge
assert "lan_manual_mode_set" in mobile and "SUPERADMIN_REQUIRED" in mobile
assert "CREATE TABLE IF NOT EXISTS lan_manual_mode" in migration
assert "LAN thực tế thủ công" in ops and "Chỉ SUPERADMIN" in ops
assert "LAN cô lập phục vụ test" in ops

feedback=ops[ops.index("private fun tapFeedback"):ops.index("private fun iconActionButton")]
for token in ["scaleX(.95f)","scaleY(.95f)","scaleX(1.01f)","scaleY(1.01f)"]:
    assert token in feedback, token
assert "layoutParams" not in feedback and "requestLayout" not in feedback

print("beta117_owner_followup_contract=PASS document=PASS drop=PASS performance=PASS labor=PASS lan=PASS tap=PASS")
