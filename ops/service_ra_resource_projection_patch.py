from pathlib import Path

p=Path("service/src/replication.ts")
s=p.read_text(encoding="utf-8")
if "S59_RA_RESOURCE_PROJECTION" in s:
    print("service RA resource projection already patched")
    raise SystemExit(0)

old='''async function replicateAttendanceEvent(db:D1Database,sheetId:string,token:string,index:OperationalIndex,e:EventRow):Promise<void>{
  const s=await attendanceOperational(db,e.entity_id);await replicateUserAssignments(db,sheetId,token,index,e,s);
  if(e.event_type==="RESOURCE_CHANGE"){await appendHistory(sheetId,token,index,e,s.session_id,s.mnv,s.full_name,s.shift,"Cập nhật công việc / tài nguyên",resourceChangeDetail(e));return;}
  if(index.raEvents.has(e.event_id))return;
  const enter=e.event_type==="ATTENDANCE_ENTER",action=enter?"VÀO":"RA",appAction=enter?"ENTER":"EXIT";
  await appendValues(sheetId,token,"RA - VÀO TRONG CA","A:V",[[visibleDate(e.business_date),s.shift,s.mnv,s.full_name,s.phone,s.supplier,s.department,s.site,s.warehouse,s.main_position,"","","","","",action,"",e.actor_id,visibleDateTime(e.occurred_at),e.event_id,appAction,e.authority_seq]]);index.raEvents.add(e.event_id);
  await appendHistory(sheetId,token,index,e,s.session_id,s.mnv,s.full_name,s.shift,enter?"Vào ca":"Ra ca",`${enter?"Bắt đầu":"Kết thúc"} phiên • Vị trí chính: ${s.main_position||"—"}`);
}
'''

new='''// S59_RA_RESOURCE_PROJECTION: preserve the resource snapshot carried by the canonical event.
// If a legacy/exit event does not carry a resource field, fall back to the canonical D1 session.
function attendanceResourceSnapshot(e:EventRow,s:AttendanceOperationalRow):{workChoice:string;pdaSerial:string;userPick:string;packTable:string;userPack:string}{
  const p=payload(e),after=pobj(p,"after");
  const value=(key:string,fallback:string|null):string=>ptext(after,key)||ptext(p,key)||fallback||"";
  return{
    workChoice:value("work_choice",s.work_choice),
    pdaSerial:value("pda_serial",s.pda_serial),
    userPick:value("user_pick",s.user_pick),
    packTable:value("pack_table",s.pack_table),
    userPack:value("user_pack",s.user_pack),
  };
}

async function replicateAttendanceEvent(db:D1Database,sheetId:string,token:string,index:OperationalIndex,e:EventRow):Promise<void>{
  const s=await attendanceOperational(db,e.entity_id);await replicateUserAssignments(db,sheetId,token,index,e,s);
  if(e.event_type==="RESOURCE_CHANGE"){await appendHistory(sheetId,token,index,e,s.session_id,s.mnv,s.full_name,s.shift,"Cập nhật công việc / tài nguyên",resourceChangeDetail(e));return;}
  if(index.raEvents.has(e.event_id))return;
  const r=attendanceResourceSnapshot(e,s);
  const enter=e.event_type==="ATTENDANCE_ENTER",action=enter?"VÀO":"RA",appAction=enter?"ENTER":"EXIT";
  await appendValues(sheetId,token,"RA - VÀO TRONG CA","A:V",[[visibleDate(e.business_date),s.shift,s.mnv,s.full_name,s.phone,s.supplier,s.department,s.site,s.warehouse,s.main_position,workLabel(r.workChoice),r.pdaSerial,r.userPick,r.packTable,r.userPack,action,"",e.actor_id,visibleDateTime(e.occurred_at),e.event_id,appAction,e.authority_seq]]);index.raEvents.add(e.event_id);
  await appendHistory(sheetId,token,index,e,s.session_id,s.mnv,s.full_name,s.shift,enter?"Vào ca":"Ra ca",`${enter?"Bắt đầu":"Kết thúc"} phiên • Vị trí chính: ${s.main_position||"—"}`);
}
'''

if s.count(old)!=1:
    raise SystemExit(f"replicateAttendanceEvent block mismatch: {s.count(old)}")
s=s.replace(old,new,1)
p.write_text(s,encoding="utf-8")
print("service RA resource projection patch applied")
