from pathlib import Path

p = Path("service/src/session_hotfix.ts")
s = p.read_text()
if "mutation_kind:mutationKind" not in s:
    anchor = "  const duplicateUser=Boolean(b.duplicate_user);"
    repl = '  const duplicateUser=Boolean(b.duplicate_user),requestedKind=text(b.mutation_kind,20).toUpperCase(),mutationKind=(["ADD","EDIT","DELETE"].includes(requestedKind)?requestedKind:"EDIT"),auditNote=text(b.audit_note,300);'
    if anchor not in s:
        raise SystemExit("session duplicateUser anchor missing")
    s = s.replace(anchor, repl, 1)
    old = '{mnv:s.mnv,shift:s.shift,work_choice:choice,pda_serial:pda,user_pick:pick,pack_table:table,user_pack:pack,pda_enter_status:pdaStatus||"",resource_note:note,duplicate_user:duplicateUser,before:{work_choice:s.work_choice,pda_serial:s.pda_serial,user_pick:s.user_pick,pack_table:s.pack_table,user_pack:s.user_pack,pda_enter_status:s.pda_enter_status},after:{work_choice:choice,pda_serial:pda||null,user_pick:pick||null,pack_table:table||null,user_pack:pack||null,pda_enter_status:pdaStatus}}'
    new = '{mnv:s.mnv,shift:s.shift,work_choice:choice,pda_serial:pda,user_pick:pick,pack_table:table,user_pack:pack,pda_enter_status:pdaStatus||"",resource_note:note,duplicate_user:duplicateUser,mutation_kind:mutationKind,audit_note:auditNote,before:{work_choice:s.work_choice,pda_serial:s.pda_serial,user_pick:s.user_pick,pack_table:s.pack_table,user_pack:s.user_pack,pda_enter_status:s.pda_enter_status},after:{work_choice:choice,pda_serial:pda||null,user_pick:pick||null,pack_table:table||null,user_pack:pack||null,pda_enter_status:pdaStatus}}'
    if old not in s:
        raise SystemExit("session event payload anchor missing")
    s = s.replace(old, new, 1)
    p.write_text(s)

p = Path("service/src/replication.ts")
s = p.read_text()
if "S60_RA_ENTER_AGGREGATE" in s:
    raise SystemExit("S60 service patch already applied")

s = s.replace(
    "interface OperationalIndex { raEvents:Set<string>;userEvents:Set<string>;laborStartRows:Map<string,number>;laborFinishEvents:Set<string>;historyEvents:Set<string>; }",
    "interface OperationalIndex { raEvents:Set<string>;raEventRows:Map<string,number>;userEvents:Set<string>;laborStartRows:Map<string,number>;laborFinishEvents:Set<string>;historyEvents:Set<string>; }",
    1,
)
old = '''  const raEvents=new Set((v[4]??[]).map(r=>String(r[0]??"")).filter(Boolean)),laborStartRows=new Map<string,number>(),laborFinishEvents=new Set<string>();
  for(let i=0;i<(v[5]??[]).length;i++){const r=(v[5]??[])[i]??[],start=String(r[0]??""),finish=String(r[1]??"");if(start)laborStartRows.set(start,i+2);if(finish)laborFinishEvents.add(finish);}
  const historyEvents=new Set((v[6]??[]).map(r=>String(r[0]??"")).filter(Boolean)),userEvents=new Set((v[7]??[]).map(r=>String(r[0]??"")).filter(Boolean));return{raEvents,userEvents,laborStartRows,laborFinishEvents,historyEvents};'''
new = '''  const raEvents=new Set<string>(),raEventRows=new Map<string,number>(),laborStartRows=new Map<string,number>(),laborFinishEvents=new Set<string>();
  for(let i=0;i<(v[4]??[]).length;i++){const id=String((v[4]??[])[i]?.[0]??"");if(id){raEvents.add(id);raEventRows.set(id,i+2);}}
  for(let i=0;i<(v[5]??[]).length;i++){const r=(v[5]??[])[i]??[],start=String(r[0]??""),finish=String(r[1]??"");if(start)laborStartRows.set(start,i+2);if(finish)laborFinishEvents.add(finish);}
  const historyEvents=new Set((v[6]??[]).map(r=>String(r[0]??"")).filter(Boolean)),userEvents=new Set((v[7]??[]).map(r=>String(r[0]??"")).filter(Boolean));return{raEvents,raEventRows,userEvents,laborStartRows,laborFinishEvents,historyEvents};'''
if old not in s:
    raise SystemExit("replication operational-index anchor missing")
s = s.replace(old, new, 1)

start = s.index("function resourceChangeDetail(e:EventRow):string{")
end = s.index("async function replicateLaborStartOperational", start)
replacement = r'''function resourceChangeDetail(e:EventRow):string{
  const p=payload(e),before=pobj(p,"before"),after=pobj(p,"after"),labels:Record<string,string>={work_choice:"Vị trí",pda_serial:"PDA",user_pick:"User Pick",pack_table:"Bàn Pack",user_pack:"User Pack"},parts:string[]=[];
  if(Object.keys(after).length){for(const k of Object.keys(labels)){const a=ptext(before,k)||"—",b=ptext(after,k)||"—";if(a!==b)parts.push(`${labels[k]}: ${a} → ${b}`);}}
  if(!parts.length){for(const k of Object.keys(labels)){const v=ptext(p,k);if(v)parts.push(`${labels[k]}: ${v}`);}}
  const kind=ptext(p,"mutation_kind").toUpperCase(),verb=kind==="ADD"?"Thêm":kind==="DELETE"?"Xóa":"Sửa",note=ptext(p,"audit_note");
  return [verb,note,...parts].filter(Boolean).join(" • ")||"Cập nhật công việc / tài nguyên trong ca";
}

// S60_RA_ENTER_AGGREGATE: keep one VÀO row and accumulate all resource usage for that shift session.
type AttendanceUsage={workChoices:string[];pdaSerials:string[];userPicks:string[];packTables:string[];userPacks:string[]};
async function attendanceUsageThrough(db:D1Database,sessionId:string,throughSeq:number):Promise<AttendanceUsage>{
  const r=await db.prepare("SELECT payload_json FROM events WHERE entity_id=?1 AND event_type IN ('ATTENDANCE_ENTER','RESOURCE_CHANGE') AND authority_seq<=?2 ORDER BY authority_seq,event_id").bind(sessionId,throughSeq).all<{payload_json:string}>();
  const work:string[]=[],pdas:string[]=[],picks:string[]=[],tables:string[]=[],packs:string[]=[];const add=(a:string[],v:string)=>{const x=v.trim();if(x&&!a.includes(x))a.push(x);};
  const snap=(x:Record<string,unknown>)=>{const w=ptext(x,"work_choice").toUpperCase();if(w==="PICK"||w==="PACK")add(work,w);add(pdas,ptext(x,"pda_serial"));add(picks,ptext(x,"user_pick"));add(tables,ptext(x,"pack_table"));add(packs,ptext(x,"user_pack"));};
  for(const row of r.results??[]){let p:Record<string,unknown>={};try{p=JSON.parse(row.payload_json) as Record<string,unknown>;}catch{}snap(p);const before=pobj(p,"before"),after=pobj(p,"after");if(Object.keys(before).length)snap(before);if(Object.keys(after).length)snap(after);}
  return{workChoices:work,pdaSerials:pdas,userPicks:picks,packTables:tables,userPacks:packs};
}
async function updateAttendanceEnterAggregate(db:D1Database,sheetId:string,token:string,index:OperationalIndex,e:EventRow):Promise<void>{
  const enter=await db.prepare("SELECT event_id FROM events WHERE entity_id=?1 AND event_type='ATTENDANCE_ENTER' ORDER BY authority_seq,event_id LIMIT 1").bind(e.entity_id).first<{event_id:string}>();
  if(!enter?.event_id)throw new Error(`RA_ENTER_EVENT_MISSING:${e.entity_id}`);const row=index.raEventRows.get(enter.event_id);if(!row)throw new Error(`RA_ENTER_ROW_MISSING:${enter.event_id}`);
  const u=await attendanceUsageThrough(db,e.entity_id,e.authority_seq),positions=u.workChoices.map(workLabel).join(", ")||"Không";
  await putValues(sheetId,token,"RA - VÀO TRONG CA",`K${row}:O${row}`,[[positions,u.pdaSerials.join(", "),u.userPicks.join(", "),u.packTables.join(", "),u.userPacks.join(", ")]]);
}

function attendanceResourceSnapshot(e:EventRow,s:AttendanceOperationalRow):{workChoice:string;pdaSerial:string;userPick:string;packTable:string;userPack:string}{
  const p=payload(e),after=pobj(p,"after");const value=(key:string,fallback:string|null):string=>ptext(after,key)||ptext(p,key)||fallback||"";
  return{workChoice:value("work_choice",s.work_choice),pdaSerial:value("pda_serial",s.pda_serial),userPick:value("user_pick",s.user_pick),packTable:value("pack_table",s.pack_table),userPack:value("user_pack",s.user_pack)};
}

async function replicateAttendanceEvent(db:D1Database,sheetId:string,token:string,index:OperationalIndex,e:EventRow):Promise<void>{
  const s=await attendanceOperational(db,e.entity_id);await replicateUserAssignments(db,sheetId,token,index,e,s);
  if(e.event_type==="RESOURCE_CHANGE"){
    const p=payload(e),kind=ptext(p,"mutation_kind").toUpperCase(),label=kind==="ADD"?"Thêm công việc / User":kind==="DELETE"?"Xóa công việc / tài nguyên":"Sửa công việc / tài nguyên";
    await appendHistory(sheetId,token,index,e,s.session_id,s.mnv,s.full_name,s.shift,label,resourceChangeDetail(e));await updateAttendanceEnterAggregate(db,sheetId,token,index,e);return;
  }
  if(index.raEvents.has(e.event_id))return;
  const r=attendanceResourceSnapshot(e,s),enter=e.event_type==="ATTENDANCE_ENTER",action=enter?"VÀO":"RA",appAction=enter?"ENTER":"EXIT";
  const resourceCells=enter?[r.pdaSerial,r.userPick,r.packTable,r.userPack]:["","","",""];
  const updated=await appendValues(sheetId,token,"RA - VÀO TRONG CA","A:V",[[visibleDate(e.business_date),s.shift,s.mnv,s.full_name,s.phone,s.supplier,s.department,s.site,s.warehouse,s.main_position,workLabel(r.workChoice),...resourceCells,action,"",e.actor_id,visibleDateTime(e.occurred_at),e.event_id,appAction,e.authority_seq]]);index.raEvents.add(e.event_id);const row=appendRowNumber(updated);if(row!==null)index.raEventRows.set(e.event_id,row);
  if(enter)await updateAttendanceEnterAggregate(db,sheetId,token,index,e);
  await appendHistory(sheetId,token,index,e,s.session_id,s.mnv,s.full_name,s.shift,enter?"Vào ca":"Ra ca",`${enter?"Bắt đầu":"Kết thúc"} phiên • Vị trí chính: ${s.main_position||"—"}`);
}

'''
s = s[:start] + replacement + s[end:]
p.write_text(s)
