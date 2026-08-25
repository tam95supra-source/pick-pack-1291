#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'tools/apply_beta71_owner_requests_base.py'
src=base.read_text()

# Replace obsolete reconciliation patch with exact live per-shift button behavior.
s3=src.find('# 3) Mismatched attendance reconciliation gets a prominent blinking warning; matching state stays calm.')
e3=src.find('# 4) Professional PDA exchange presentation; active/session authority from Beta68 is untouched.',s3)
if s3<0 or e3<0: raise SystemExit('Beta71 attendance section missing')
section3=r'''# 3) Live reconciliation is one button per shift. Blink only the shift whose Vào != Ra.
recon_button='val button=reconciliationButton("$shift – ${entered.size}/${exited.size}",entered.size==exited.size)'
recon_blink=recon_button+'\n            if(entered.size!=exited.size){button.contentDescription="Cảnh báo đối soát $shift chưa khớp: vào ${entered.size}, ra ${exited.size}";button.startAnimation(android.view.animation.AlphaAnimation(1f,0.28f).apply{duration=650L;repeatMode=android.view.animation.Animation.REVERSE;repeatCount=android.view.animation.Animation.INFINITE})}'
ops=replace_once(ops,recon_button,recon_blink,'Shift reconciliation blinking warning')

'''
src=src[:s3]+section3+src[e3:]

# Replace obsolete legacy work_choice timeline patch with the exact Beta65 operations[] model.
s6=src.find('# 6) Shift timeline reports the actual before -> after work/resource delta, not only work_choice.')
e6=src.find('OPS.write_text(ops)',s6)
if s6<0 or e6<0: raise SystemExit('Beta71 timeline section missing')
section6=r'''# 6) Timeline correctness for the active Beta65 session model.
# session_resource_mutate writes operations[]; canonical events may also include before/after snapshots.
session_helpers=r'''    private fun sessionWorkChangeDetail(payload:JSONObject):String{
        val before=payload.optJSONObject("before")?:JSONObject();val after=payload.optJSONObject("after")?:JSONObject()
        fun assignments(s:JSONObject):JSONArray=s.optJSONArray("resource_assignments_v64")?:s.optJSONArray("resource_assignments")?:s.optJSONArray("assignments")?:JSONArray()
        fun positions(s:JSONObject):JSONArray=s.optJSONArray("positions_v64")?:s.optJSONArray("positions")?:JSONArray()
        fun resName(t:String):String=when(t.uppercase()){ "PDA"->"PDA";"USER_PICK"->"User Pick";"PACK_TABLE"->"Bàn Pack";"USER_PACK"->"User Pack";else->t.ifBlank{"Tài nguyên"} }
        fun assignmentById(s:JSONObject,id:String):JSONObject?{val a=assignments(s);for(i in 0 until a.length()){val x=a.optJSONObject(i)?:continue;if(x.optString("assignment_id")==id)return x};return null}
        fun positionLabel(s:JSONObject,key:String):String{val a=positions(s);for(i in 0 until a.length()){val x=a.optJSONObject(i)?:continue;if(x.optString("position_key").equals(key,true))return x.optString("position_label").ifBlank{x.optString("position_key")}};return key}
        val changes=mutableListOf<String>();val ops=payload.optJSONArray("operations")
        if(ops!=null){for(i in 0 until ops.length()){
            val x=ops.optJSONObject(i)?:continue;val op=x.optString("op").uppercase()
            when(op){
                "ADD_RESOURCE"->{val t=x.optString("resource_type");val id=x.optString("resource_id");if(id.isNotBlank())changes.add("Thêm ${resName(t)}: $id")}
                "REMOVE_RESOURCE"->{val old=assignmentById(before,x.optString("assignment_id"));val t=old?.optString("resource_type").orEmpty().ifBlank{x.optString("resource_type")};val id=old?.optString("resource_id").orEmpty().ifBlank{x.optString("resource_id")};changes.add("Xóa ${resName(t)}: ${id.ifBlank{"—"}}${x.optString("reason").takeIf{it.isNotBlank()}?.let{" • Lý do: $it"}.orEmpty()}")}
                "REPLACE_RESOURCE"->{val old=assignmentById(before,x.optString("assignment_id"));val t=old?.optString("resource_type").orEmpty().ifBlank{x.optString("resource_type")};val oldId=old?.optString("resource_id").orEmpty().ifBlank{"—"};val newId=x.optString("new_resource_id").ifBlank{"—"};changes.add("Đổi ${resName(t)}: $oldId → $newId${x.optString("reason").takeIf{it.isNotBlank()}?.let{" • Lý do: $it"}.orEmpty()}")}
                "ADD_POSITION"->{val v=x.optString("position_label").ifBlank{x.optString("position_key")};changes.add("Thêm vị trí trong ca: ${v.ifBlank{"—"}}")}
                "REMOVE_POSITION"->{val key=x.optString("position_key");changes.add("Xóa vị trí trong ca: ${positionLabel(before,key).ifBlank{"—"}}${x.optString("reason").takeIf{it.isNotBlank()}?.let{" • Lý do: $it"}.orEmpty()}")}
                "UPDATE_SHIFT"->{val old=before.optString("shift").ifBlank{"—"};val next=x.optString("shift").ifBlank{after.optString("shift")}.ifBlank{"—"};changes.add("Đổi ca: $old → $next")}
            }
        }}
        if(changes.isNotEmpty())return changes.joinToString(" • ")
        // Canonical fallback: calculate exact set differences from before/after snapshots.
        fun resources(s:JSONObject):Map<String,String>{val out=linkedMapOf<String,String>();val a=assignments(s);for(i in 0 until a.length()){val x=a.optJSONObject(i)?:continue;if(x.optString("state").uppercase() !in setOf("","ACTIVE"))continue;val t=x.optString("resource_type");val id=x.optString("resource_id");if(id.isNotBlank())out["${t.uppercase()}|$id"]="${resName(t)}: $id"};return out}
        fun pos(s:JSONObject):Map<String,String>{val out=linkedMapOf<String,String>();val a=positions(s);for(i in 0 until a.length()){val x=a.optJSONObject(i)?:continue;if(x.optString("state").uppercase() !in setOf("","ACTIVE"))continue;val key=x.optString("position_key");val label=x.optString("position_label").ifBlank{key};if(key.isNotBlank()||label.isNotBlank())out[key.ifBlank{label.uppercase()}]=label};return out}
        val br=resources(before);val ar=resources(after);for(k in br.keys-ar.keys)changes.add("Xóa ${br[k]}");for(k in ar.keys-br.keys)changes.add("Thêm ${ar[k]}")
        val bp=pos(before);val ap=pos(after);for(k in bp.keys-ap.keys)changes.add("Xóa vị trí trong ca: ${bp[k]}");for(k in ap.keys-bp.keys)changes.add("Thêm vị trí trong ca: ${ap[k]}")
        val bs=before.optString("shift");val asv=after.optString("shift");if(bs.isNotBlank()&&asv.isNotBlank()&&bs!=asv)changes.add("Đổi ca: $bs → $asv")
        return changes.joinToString(" • ")
    }
    private fun sessionWorkSnapshotDetail(s:JSONObject):String{
        val parts=mutableListOf<String>();val pa=s.optJSONArray("positions_v64")?:s.optJSONArray("positions")?:JSONArray();for(i in 0 until pa.length()){val x=pa.optJSONObject(i)?:continue;if(x.optString("state").uppercase() !in setOf("","ACTIVE"))continue;val v=x.optString("position_label").ifBlank{x.optString("position_key")};if(v.isNotBlank())parts.add("Vị trí $v")}
        val ra=s.optJSONArray("resource_assignments_v64")?:s.optJSONArray("resource_assignments")?:s.optJSONArray("assignments")?:JSONArray();for(i in 0 until ra.length()){val x=ra.optJSONObject(i)?:continue;if(x.optString("state").uppercase() !in setOf("","ACTIVE"))continue;val t=when(x.optString("resource_type").uppercase()){ "PDA"->"PDA";"USER_PICK"->"User Pick";"PACK_TABLE"->"Bàn Pack";"USER_PACK"->"User Pack";else->x.optString("resource_type")};val id=x.optString("resource_id");if(id.isNotBlank())parts.add("$t $id")};return parts.distinct().joinToString(" • ")
    }
'''
marker='    private fun sessionTimelineItems(mnv:String,ses:JSONObject)'
if 'private fun sessionWorkChangeDetail(payload:JSONObject)' not in ops:
    if marker not in ops: raise SystemExit('Exact Beta65 sessionTimelineItems marker missing')
    ops=ops.replace(marker,session_helpers+marker,1)
old_resource='''if(type=="RESOURCE_CHANGE"){val before=p.optJSONObject("before")?:JSONObject();val after=p.optJSONObject("after")?:JSONObject();val kind=p.optString("mutation_kind").uppercase();val verb=when(kind){"ADD"->"Thêm";"DELETE"->"Xóa";else->"Sửa"};return "$verb • Trước: ${sessionWorkDetail(before).ifBlank{"—"}} • Sau: ${sessionWorkDetail(after).ifBlank{"—"}}"}'''
new_resource='''if(type=="RESOURCE_CHANGE"){val delta=sessionWorkChangeDetail(p);if(delta.isNotBlank())return delta;val before=p.optJSONObject("before")?:JSONObject();val after=p.optJSONObject("after")?:JSONObject();return "Trước: ${sessionWorkSnapshotDetail(before).ifBlank{sessionWorkDetail(before).ifBlank{"—"}}} • Sau: ${sessionWorkSnapshotDetail(after).ifBlank{sessionWorkDetail(after).ifBlank{"—"}}}"}'''
ops=replace_once(ops,old_resource,new_resource,'Exact RESOURCE_CHANGE timeline detail')

'''
src=src[:s6]+section6+src[e6:]

# Replace stale regression anchors from v1 with exact live assertions.
src=src.replace("assert 'CẢNH BÁO: Đối soát vào / ra ca chưa khớp' in ops and 'Animation.INFINITE' in ops", "assert 'Cảnh báo đối soát $shift chưa khớp' in ops and 'Animation.INFINITE' in ops")
src=src.replace("assert 'sessionWorkChangeDetail' in ops and 'WORK_SESSION_UPDATE' in ops and 'val delta=sessionWorkChangeDetail(before,after)' in ops", "assert 'sessionWorkChangeDetail(payload:JSONObject)' in ops and 'REPLACE_RESOURCE' in ops and 'val delta=sessionWorkChangeDetail(p)' in ops")

ns={'__file__':str(base),'__name__':'__main__'}
exec(compile(src,str(base),'exec'),ns)
print('BETA71_OWNER_SIX_FIXES_V4_PASS')
