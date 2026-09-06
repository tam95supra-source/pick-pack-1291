#!/usr/bin/env python3
from pathlib import Path
p=Path('service/src/replication.ts')
t=p.read_text(encoding='utf-8')

# One Sheets values:batchUpdate call can update many labor finish rows.
anchor='function assertHeaderValues(sheet:string,values:unknown[][],headers:readonly string[]):void{'
pos=t.index(anchor)
helper=r'''async function batchPutValues(env:Env,sheetId:string,token:string,data:Array<{sheet:string;range:string;values:unknown[][]}>):Promise<void>{
  if(!data.length)return;
  if(isStableEnvironment(env)){for(const d of data)await stableSheetBridge(env,"primary","put_values",{sheet:d.sheet,range:d.range,values:d.values});return;}
  const url=`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(sheetId)}/values:batchUpdate`,body={valueInputOption:"RAW",data:data.map(d=>({range:a1(d.sheet,d.range),majorDimension:"ROWS",values:d.values}))};
  const r=await fetch(url,{method:"POST",headers:authHeaders(token,{"content-type":"application/json"}),body:JSON.stringify(body)});if(!r.ok){const x=await r.text();throw new Error(`GOOGLE_BATCH_PUT:${r.status}:${x.slice(0,240)}`);}
}
'''
t=t[:pos]+helper+t[pos:]

start=t.index('async function replicateOperational(')
end=t.index('function retryDelaySeconds',start)
new=r'''function historyRow(e:EventRow,sessionId:string,mnv:string,name:string,shift:string,label:string,detail:string):unknown[]{return[visibleDate(e.business_date),sessionId,mnv,name,shift,e.event_type,label,visibleDateTime(e.occurred_at),e.actor_id,detail,e.event_id,"SERVICE_M2",e.authority_seq];}
type AssignmentRow={first_event_id:string;resource_type:string;resource_id:string};
async function replicateOperational(db:D1Database,env:Env,token:string,events:EventRow[]):Promise<{count:number;index:OperationalIndex|null}>{
  const a=await db.prepare("SELECT scope FROM authority_state WHERE singleton_id=1").first<{scope:string}>();if(a?.scope!=="PRODUCTION")return{count:0,index:null};
  const master=await replicateMasterProjection(db,env,token,events),index=await loadOperationalIndex(env,token),sheetId=env.GOOGLE_SOURCE_SHEET_ID;
  const attendanceEvents=events.filter(e=>["ATTENDANCE_ENTER","RESOURCE_CHANGE","ATTENDANCE_EXIT"].includes(e.event_type)),attendanceIds=[...new Set(attendanceEvents.map(e=>e.entity_id))],laborEvents=events.filter(e=>e.event_type==="LABOR_START"||e.event_type==="LABOR_FINISH"),laborIds=[...new Set(laborEvents.map(e=>e.entity_id))];
  const attendanceRows:AttendanceOperationalRow[]=attendanceIds.length?((await db.prepare(`SELECT s.session_id,s.mnv,s.business_date,s.shift,s.work_choice,s.pda_serial,s.user_pick,s.pack_table,s.user_pack,e.full_name,e.phone,e.main_position,e.supplier,e.department,e.site,e.warehouse FROM attendance_sessions s JOIN employees e ON e.mnv=s.mnv WHERE s.session_id IN (${attendanceIds.map(()=>"?").join(",")})`).bind(...attendanceIds).all<AttendanceOperationalRow>()).results??[]):[];
  const laborRows:LaborOperationalRow[]=laborIds.length?((await db.prepare(`SELECT l.labor_id,l.mnv,l.business_date,l.shift,l.labor_type,l.time_marker,l.start_at,l.end_at,l.note,l.deduct_staff,l.start_event_id,l.finish_event_id,e.full_name,e.phone,e.main_position,e.supplier,e.department,e.site,e.warehouse,a.session_id AS attendance_session_id,a.work_choice AS attendance_work_choice FROM labor_sessions l JOIN employees e ON e.mnv=l.mnv LEFT JOIN attendance_sessions a ON a.mnv=l.mnv AND a.business_date=l.business_date WHERE l.labor_id IN (${laborIds.map(()=>"?").join(",")})`).bind(...laborIds).all<LaborOperationalRow>()).results??[]):[];
  const eventIds=events.map(e=>e.event_id),assignments:AssignmentRow[]=eventIds.length?((await db.prepare(`SELECT first_event_id,resource_type,resource_id FROM resource_daily_consumption WHERE first_event_id IN (${eventIds.map(()=>"?").join(",")}) AND resource_type IN ('USER_PICK','USER_PACK') ORDER BY first_event_id,resource_type,resource_id`).bind(...eventIds).all<AssignmentRow>()).results??[]):[];
  const attMap=new Map(attendanceRows.map(x=>[x.session_id,x])),laborMap=new Map(laborRows.map(x=>[x.labor_id,x])),assignmentMap=new Map<string,AssignmentRow[]>();for(const x of assignments){const q=assignmentMap.get(x.first_event_id)??[];q.push(x);assignmentMap.set(x.first_event_id,q);}
  const ra:Array<{eventId:string;row:unknown[]}>=[],users:Array<{key:string;row:unknown[]}>=[],starts:Array<{eventId:string;row:unknown[]}>=[],finishes:Array<{event:EventRow;labor:LaborOperationalRow}>=[],hist:Array<{eventId:string;row:unknown[]}>=[];let n=0;
  const addHistory=(e:EventRow,sessionId:string,mnv:string,name:string,shift:string,label:string,detail:string)=>{if(!index.historyEvents.has(e.event_id)&&!hist.some(x=>x.eventId===e.event_id))hist.push({eventId:e.event_id,row:historyRow(e,sessionId,mnv,name,shift,label,detail)});};
  for(const e of events){
    if(["ATTENDANCE_ENTER","RESOURCE_CHANGE","ATTENDANCE_EXIT"].includes(e.event_type)){
      const s=attMap.get(e.entity_id);if(!s)throw new Error(`REPLICA_ATTENDANCE_MISSING:${e.entity_id}`);
      for(const x of assignmentMap.get(e.event_id)??[]){const pos=x.resource_type==="USER_PICK"?"PICK":"PACK",key=`${e.event_id}:${pos}`;if(!index.userEvents.has(key)&&!users.some(y=>y.key===key))users.push({key,row:[visibleDate(e.business_date),s.shift,s.mnv,s.full_name,s.supplier,s.department,s.site,pos,x.resource_id,e.actor_id,key]});}
      if(e.event_type==="RESOURCE_CHANGE")addHistory(e,s.session_id,s.mnv,s.full_name,s.shift,"Cập nhật công việc / tài nguyên",resourceChangeDetail(e));
      else{const enter=e.event_type==="ATTENDANCE_ENTER";if(!index.raEvents.has(e.event_id))ra.push({eventId:e.event_id,row:[visibleDate(e.business_date),s.shift,s.mnv,s.full_name,s.phone,s.supplier,s.department,s.site,s.warehouse,s.main_position,"","","","","",enter?"VÀO":"RA","",e.actor_id,visibleDateTime(e.occurred_at),e.event_id,enter?"ENTER":"EXIT",e.authority_seq]});addHistory(e,s.session_id,s.mnv,s.full_name,s.shift,enter?"Vào ca":"Ra ca",`${enter?"Bắt đầu":"Kết thúc"} phiên • Vị trí chính: ${s.main_position||"—"}`);}n++;continue;
    }
    if(e.event_type==="LABOR_START"){
      const l=laborMap.get(e.entity_id);if(!l)throw new Error(`REPLICA_LABOR_MISSING:${e.entity_id}`);if(!l.attendance_session_id)throw new Error(`REPLICA_ATTENDANCE_FOR_LABOR_MISSING:${l.mnv}`);if(!index.laborStartRows.has(e.event_id))starts.push({eventId:e.event_id,row:[visibleDate(e.business_date),l.shift,l.mnv,l.full_name,l.phone,l.supplier,l.department,l.site,l.warehouse,l.main_position,workLabel(l.attendance_work_choice??""),l.labor_type,visibleDateTime(l.start_at),"",l.time_marker,"Đang làm",l.note||"",e.actor_id,visibleDateTime(e.occurred_at),e.event_id,"",e.authority_seq,l.deduct_staff?"Có":"Không"]});addHistory(e,l.attendance_session_id,l.mnv,l.full_name,l.shift,"Bắt đầu công nhật",`${l.labor_type} • Bắt đầu ${visibleDateTime(l.start_at)} • Khấu trừ ${l.deduct_staff?"Có":"Không"}`);n++;continue;
    }
    if(e.event_type==="LABOR_FINISH"){
      const l=laborMap.get(e.entity_id);if(!l)throw new Error(`REPLICA_LABOR_MISSING:${e.entity_id}`);if(!index.laborFinishEvents.has(e.event_id))finishes.push({event:e,labor:l});const corrected=payload(e).correction===true;addHistory(e,l.attendance_session_id||`${visibleDate(e.business_date)}|${l.mnv}`,l.mnv,l.full_name,l.shift,corrected?"Sửa công nhật":"Hoàn thành công nhật",`${l.labor_type} • ${visibleDateTime(l.start_at)} → ${visibleDateTime(l.end_at||e.occurred_at)} • Khấu trừ ${l.deduct_staff?"Có":"Không"}`);n++;continue;
    }
    if(e.origin==="ADMIN_AUDIT"){
      const p=payload(e),targetType=ptext(p,"target_type")||e.entity_type,targetId=ptext(p,"target_id")||e.entity_id,targetLabel=ptext(p,"target_label"),detail=ptext(p,"detail"),mnv=targetType==="STAFF"?targetId:"";addHistory(e,`ADMIN|${targetType}|${targetId}`,mnv,targetLabel,"",adminAuditLabel(e.event_type),detail);n++;
    }
  }
  if(ra.length){await appendValues(env,sheetId,token,"RA - VÀO TRONG CA","A:V",ra.map(x=>x.row));for(const x of ra)index.raEvents.add(x.eventId);}
  if(users.length){await appendValues(env,sheetId,token,"THÔNG TIN USER CỦA NLĐ","A:K",users.map(x=>x.row));for(const x of users)index.userEvents.add(x.key);}
  if(starts.length){const updated=await appendValues(env,sheetId,token,"CÔNG NHẬT","A:W",starts.map(x=>x.row)),first=appendRowNumber(updated);if(first===null)throw new Error("REPLICA_LABOR_BATCH_ROW_UNKNOWN");starts.forEach((x,i)=>index.laborStartRows.set(x.eventId,first+i));}
  if(finishes.length){const plans=finishes.map(x=>{const row=index.laborStartRows.get(x.labor.start_event_id);if(!row)throw new Error(`REPLICA_LABOR_START_ROW_MISSING:${x.labor.start_event_id}`);return{...x,row};}),needNotes=plans.filter(x=>!x.labor.note),noteValues=needNotes.length?await batchGetValues(env,sheetId,token,needNotes.map(x=>["CÔNG NHẬT",`Q${x.row}:Q${x.row}`] as [string,string])):[],noteByEvent=new Map(needNotes.map((x,i)=>[x.event.event_id,String(noteValues[i]?.[0]?.[0]??"")]));await batchPutValues(env,sheetId,token,plans.map(x=>({sheet:"CÔNG NHẬT",range:`M${x.row}:V${x.row}`,values:[[visibleDateTime(x.labor.start_at),visibleDateTime(x.labor.end_at||x.event.occurred_at),x.labor.time_marker,"Hoàn thành",x.labor.note||noteByEvent.get(x.event.event_id)||"",x.event.actor_id,visibleDateTime(x.event.occurred_at),x.labor.start_event_id,x.event.event_id,x.event.authority_seq]]})));for(const x of plans)index.laborFinishEvents.add(x.event.event_id);}
  if(hist.length){await appendValues(env,sheetId,token,"LỊCH SỬ NGHIỆP VỤ","A:M",hist.map(x=>x.row));for(const x of hist)index.historyEvents.add(x.eventId);}
  return{count:n+master,index};
}

'''
t=t[:start]+new+t[end:]

start=t.index('export async function replicatePending(')
end=t.index('export async function replicationHealth',start)
new_pending=r'''export async function replicatePending(db:D1Database,env:Env,limit=100):Promise<{ok:boolean;processed:number;appended:number;operational:number;pending:number;checkpoint?:string;error?:string}>{
  const staleClaimCutoff=new Date(Date.now()-15*60*1000).toISOString(),requeueAt=nowIso();
  await db.prepare("UPDATE sheet_replication_outbox SET status='RETRY',claim_token=NULL,claimed_at=NULL,next_attempt_at=?1,last_error_class=COALESCE(last_error_class,'STALE_INFLIGHT_RECOVERED'),last_error=COALESCE(last_error,'Recovered stale INFLIGHT claim for canonical retry') WHERE status='INFLIGHT' AND (claimed_at IS NULL OR claimed_at<=?2)").bind(requeueAt,staleClaimCutoff).run();
  const rows=await db.prepare("SELECT outbox_id,event_id,attempt_count FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY') AND next_attempt_at<=?1 ORDER BY outbox_id LIMIT ?2").bind(nowIso(),Math.max(1,Math.min(limit,100))).all<OutboxRow>(),due=rows.results??[];
  if(!due.length){const p=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();return{ok:true,processed:0,appended:0,operational:0,pending:p?.n??0};}
  const claim=crypto.randomUUID(),claimAt=nowIso(),dueIds=due.map(x=>x.outbox_id),dueMarks=dueIds.map(()=>"?").join(",");let claimed:OutboxRow[]=[];
  try{
    await db.prepare(`UPDATE sheet_replication_outbox SET status='INFLIGHT',claim_token=?,claimed_at=?,attempt_count=attempt_count+1,last_error_class=NULL,last_error=NULL WHERE outbox_id IN (${dueMarks}) AND status IN ('PENDING','RETRY')`).bind(claim,claimAt,...dueIds).run();
    claimed=(await db.prepare("SELECT outbox_id,event_id,attempt_count FROM sheet_replication_outbox WHERE status='INFLIGHT' AND claim_token=?1 ORDER BY outbox_id").bind(claim).all<OutboxRow>()).results??[];
    if(!claimed.length){const pending=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();return{ok:true,processed:0,appended:0,operational:0,pending:pending?.n??0};}
    const assertOwnership=async()=>{const ownership=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status='INFLIGHT' AND claim_token=?1").bind(claim).first<{n:number}>();if((ownership?.n??0)!==claimed.length)throw new Error(`REPLICATION_CLAIM_LOST:${claim}`);await db.prepare("UPDATE sheet_replication_outbox SET claimed_at=?1 WHERE status='INFLIGHT' AND claim_token=?2").bind(nowIso(),claim).run();};
    await assertOwnership();const ids=claimed.map(x=>x.event_id),marks=ids.map(()=>"?").join(","),token=await googleAccessToken(env),present=await ensureReplicaSheet(env,token);await assertOwnership();
    const allEvents=(await db.prepare(`SELECT * FROM events WHERE event_id IN (${marks}) ORDER BY authority_epoch,authority_seq`).bind(...ids).all<EventRow>()).results??[];if(allEvents.length!==claimed.length||new Set(allEvents.map(e=>e.event_id)).size!==claimed.length)throw new Error("REPLICATION_EVENT_SET_MISMATCH");
    const technical=allEvents.filter(e=>!present.has(e.event_id));await assertOwnership();const checkpoint=await appendTechnicalRows(env,token,technical);await assertOwnership();const op=await replicateOperational(db,env,token,allEvents),operational=op.count;await assertOwnership();
    if(op.index)for(const e of allEvents){if(e.event_type==="ATTENDANCE_ENTER"||e.event_type==="ATTENDANCE_EXIT"){const raOk=op.index.raEvents.has(e.event_id),historyOk=op.index.historyEvents.has(e.event_id);if(!raOk||!historyOk)throw new Error(`REPLICATION_OPERATIONAL_INCOMPLETE:${e.event_id}:RA=${raOk?1:0}:HISTORY=${historyOk?1:0}`);}}
    await assertOwnership();const doneAt=nowIso();await db.prepare("UPDATE sheet_replication_outbox SET status='SYNCED',claim_token=NULL,claimed_at=NULL,replicated_at=?1,google_checkpoint=?2,last_error_class=NULL,last_error=NULL WHERE status='INFLIGHT' AND claim_token=?3").bind(doneAt,checkpoint,claim).run();const ackMarks=claimed.map(()=>"?").join(","),acked=await db.prepare(`SELECT COUNT(*) n FROM sheet_replication_outbox WHERE outbox_id IN (${ackMarks}) AND status='SYNCED'`).bind(...claimed.map(x=>x.outbox_id)).first<{n:number}>();if((acked?.n??0)!==claimed.length)throw new Error(`REPLICATION_ACK_FENCE_FAILED:${claim}`);
    const pending=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();await db.prepare("UPDATE replication_status SET target_identity=?1,state='HEALTHY',checkpoint=?2,pending_count=?3,last_attempt_at=?4,last_success_at=?4,last_error_class=NULL,last_error=NULL,updated_at=?4 WHERE singleton_id=1").bind(isStableEnvironment(env)?"STABLE_PRIMARY_GAS:__M1_SERVICE_REPLICA":env.GOOGLE_STAGING_SHEET_ID,checkpoint,pending?.n??0,doneAt).run();return{ok:true,processed:claimed.length,appended:technical.length,operational,pending:pending?.n??0,checkpoint};
  }catch(e){const msg=String(e).slice(0,700),failedAt=nowIso(),maxAttempt=Math.max(1,...claimed.map(x=>x.attempt_count)),next=new Date(Date.now()+retryDelaySeconds(maxAttempt)*1000).toISOString();if(claimed.length)await db.prepare("UPDATE sheet_replication_outbox SET status='RETRY',claim_token=NULL,claimed_at=NULL,next_attempt_at=?1,last_error_class='TRANSIENT',last_error=?2 WHERE status='INFLIGHT' AND claim_token=?3").bind(next,msg,claim).run();const pending=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();await db.prepare("UPDATE replication_status SET state='DEGRADED',pending_count=?1,retry_count=retry_count+1,last_attempt_at=?2,last_error_class='TRANSIENT',last_error=?3,updated_at=?2 WHERE singleton_id=1").bind(pending?.n??0,failedAt,msg).run();return{ok:false,processed:claimed.length,appended:0,operational:0,pending:pending?.n??0,error:msg};}
}

'''
t=t[:start]+new_pending+t[end:]
p.write_text(t,encoding='utf-8')
print('R5_REPLICATION_BATCH_APPLY_PASS')
