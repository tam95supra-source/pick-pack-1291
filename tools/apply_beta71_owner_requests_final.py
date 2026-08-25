#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
v5=ROOT/'tools/apply_beta71_owner_requests_v5.py'
exec(compile(v5.read_text(),str(v5),'exec'),{'__file__':str(v5),'__name__':'__main__'})
ops_path=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'
ops=ops_path.read_text()
old='''        val display=api.networkStatus()\n        networkStatusText?.text=display'''
new='''        val net=runCatching{DeviceNetworkStatus.snapshot(this)}.getOrNull()\n        networkStatusText?.text=when{\n            net==null->"Đang kiểm tra"\n            !net.hasInternet->"Không Internet"\n            else->transportViHeader(net.transport)\n        }'''
if old in ops:
    ops=ops.replace(old,new,1)
elif new not in ops:
    raise SystemExit('Beta71 compact network helper anchor missing')
old_timeline=r'''        for(local in operationalStore.localHistoryAll()){
            val id=local.optString("event_id").trim();if(id.isBlank())continue;val body=local.optJSONObject("body")?:JSONObject();val p=body.optJSONObject("payload")?:body;if(p.optString("mnv").trim()!=mnv||!sameSession(body,p,local.optLong("queued_at",0L)))continue
            val action=body.optString("action").trim();val type=when(action){"enter"->"ATTENDANCE_ENTER";"resource_change"->"RESOURCE_CHANGE";"labor_start"->"LABOR_START";"labor_finish"->"LABOR_FINISH";"exit"->"ATTENDANCE_EXIT";else->""};if(type.isBlank())continue
            val existing=merged[id];if(existing!=null){existing.put("local_status",local.optString("status")).put("local_error",local.optString("error")).put("local_queued_at",local.optLong("queued_at",0L));continue}
            val label=when(type){"ATTENDANCE_ENTER"->"Vào ca";"RESOURCE_CHANGE"->"Cập nhật công việc";"LABOR_START"->"Bắt đầu công nhật";"LABOR_FINISH"->"Hoàn thành công nhật";"ATTENDANCE_EXIT"->"Ra ca";else->action}
            merged[id]=JSONObject().put("event_id",id).put("event_type",type).put("label",label).put("mnv",mnv).put("actor","Thiết bị này").put("detail",sessionWorkDetail(p)).put("timeline_source","LOCAL_PDA").put("local_status",local.optString("status")).put("local_error",local.optString("error")).put("local_queued_at",local.optLong("queued_at",0L))
        }'''
new_timeline=r'''        for(local in operationalStore.localHistoryAll()){
            val id=local.optString("event_id").trim();if(id.isBlank())continue;val body=local.optJSONObject("body")?:JSONObject();val p=body.optJSONObject("payload")?:body;val who=body.optString("mnv").ifBlank{p.optString("mnv")}.trim();if(who!=mnv||!sameSession(body,p,local.optLong("queued_at",0L)))continue
            val action=body.optString("action").trim().lowercase();val explicit=body.optString("event_type").trim().uppercase();val type=when(explicit){"ENTER"->"ATTENDANCE_ENTER";"RESOURCE"->"RESOURCE_CHANGE";"EXIT"->"ATTENDANCE_EXIT";in allowed->explicit;else->when(action){"enter"->"ATTENDANCE_ENTER";"resource_change"->"RESOURCE_CHANGE";"labor_start"->"LABOR_START";"labor_finish"->"LABOR_FINISH";"exit"->"ATTENDANCE_EXIT";else->""}};if(type.isBlank())continue
            val localError=local.optString("error").ifBlank{local.optString("last_error")};val existing=merged[id];if(existing!=null){existing.put("local_status",local.optString("status")).put("local_error",localError).put("local_queued_at",local.optLong("queued_at",0L));continue}
            val label=body.optString("label").ifBlank{when(type){"ATTENDANCE_ENTER"->"Vào ca";"RESOURCE_CHANGE"->"Cập nhật công việc";"LABOR_START"->"Bắt đầu công nhật";"LABOR_FINISH"->"Hoàn thành công nhật";"ATTENDANCE_EXIT"->"Ra ca";else->action}}
            val actor=body.optString("actor_name").ifBlank{body.optString("actor").ifBlank{body.optString("actor_id").ifBlank{"Thiết bị này"}}}
            merged[id]=JSONObject().put("event_id",id).put("event_type",type).put("label",label).put("mnv",mnv).put("actor",actor).put("detail",detail(type,body,p)).put("at_iso",body.optString("created_at").ifBlank{body.optString("updated_at")}).put("timeline_source","LOCAL_PDA").put("local_status",local.optString("status")).put("local_error",localError).put("local_queued_at",local.optLong("queued_at",0L))
        }'''
if old_timeline in ops:
    ops=ops.replace(old_timeline,new_timeline,1)
elif new_timeline not in ops:
    raise SystemExit('Beta71 local event timeline anchor missing')
old_resource_line=r'''"REPLACE_RESOURCE"->{val old=assignmentById(before,x.optString("assignment_id"));val t=old?.optString("resource_type").orEmpty().ifBlank{x.optString("resource_type")};val oldId=old?.optString("resource_id").orEmpty().ifBlank{"—"};val newId=x.optString("new_resource_id").ifBlank{"—"};changes.add("Đổi ${resName(t)}: $oldId → $newId${x.optString("reason").takeIf{it.isNotBlank()}?.let{" • Lý do: $it"}.orEmpty()}")}'''
new_resource_line=r'''"REPLACE_RESOURCE"->{val old=assignmentById(before,x.optString("assignment_id"));val t=old?.optString("resource_type").orEmpty().ifBlank{x.optString("resource_type")};val oldId=old?.optString("resource_id").orEmpty().ifBlank{when(t.uppercase()){"PDA"->before.optString("pda_serial");"USER_PICK"->before.optString("user_pick");"PACK_TABLE"->before.optString("pack_table");"USER_PACK"->before.optString("user_pack");else->""}}.ifBlank{"—"};val newId=x.optString("new_resource_id").ifBlank{"—"};changes.add("Đổi ${resName(t)}: $oldId → $newId${x.optString("reason").takeIf{it.isNotBlank()}?.let{" • Lý do: $it"}.orEmpty()}")}'''
if old_resource_line in ops:
    ops=ops.replace(old_resource_line,new_resource_line,1)
elif new_resource_line not in ops:
    raise SystemExit('Beta71 previous resource identity anchor missing')
ops_path.write_text(ops)
assert 'api.networkStatus()' not in ops
assert 'val explicit=body.optString("event_type").trim().uppercase()' in ops
assert '.put("detail",detail(type,body,p))' in ops
assert 'transportViHeader(net.transport)' in ops
print('BETA71_OWNER_SIX_FIXES_V6_PASS')
