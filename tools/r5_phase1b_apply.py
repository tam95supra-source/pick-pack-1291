#!/usr/bin/env python3
from pathlib import Path

# --- Service day delta: indexed, authority-fenced, canonical entity patch.
p=Path("service/src/sync_contract.ts")
t=p.read_text(encoding="utf-8")
start=t.index("export async function dayDeltaV2")
end=t.index("export async function masterDeltaV2", start)
new=r'''type DeltaRow=Record<string,unknown>;
function compatLabel(type:string):string{return type==="ATTENDANCE_ENTER"?"Vào ca":type==="ATTENDANCE_EXIT"?"Ra ca":type==="RESOURCE_CHANGE"?"Đổi tài nguyên":type==="LABOR_START"?"Bắt đầu công nhật":type==="LABOR_FINISH"?"Kết thúc công nhật":type==="ATTENDANCE_TIME_CORRECTED"?"Sửa thời gian vào/ra":type==="ATTENDANCE_EXIT_DELETED"?"Xóa thời gian ra":type;}
function employeePatch(r:DeltaRow,prefix:"a_"|"l_"):Record<string,unknown>{return{mnv:String(r[prefix+"mnv"]||""),full_name:String(r[prefix+"full_name"]||""),phone:String(r[prefix+"phone"]||""),main_position:String(r[prefix+"main_position"]||""),supplier:String(r[prefix+"supplier"]||""),department:String(r[prefix+"department"]||""),site:String(r[prefix+"site"]||""),warehouse:String(r[prefix+"warehouse"]||""),start_date:String(r[prefix+"start_date"]||""),note:String(r[prefix+"note"]||"")};}
function canonicalPatch(r:DeltaRow):Record<string,unknown>|null{
  if(r.a_session_id){return{entity_type:"ATTENDANCE_SESSION",entity_id:String(r.a_session_id),deleted:false,entity:{id:String(r.a_session_id),session_id:String(r.a_session_id),business_date:String(r.business_date||""),mnv:String(r.a_mnv||""),employee_snapshot:employeePatch(r,"a_"),shift:String(r.a_shift||""),work_choice:String(r.a_work_choice||""),state:String(r.a_state||""),pda_serial:r.a_pda_serial??null,user_pick:r.a_user_pick??null,pack_table:r.a_pack_table??null,user_pack:r.a_user_pack??null,enter_at:r.a_enter_at??null,exit_at:r.a_exit_at??null,entered_by:r.a_entered_by??null,exited_by:r.a_exited_by??null,version:Number(r.a_version||0)}};}
  if(r.l_labor_id){return{entity_type:"LABOR_SESSION",entity_id:String(r.l_labor_id),deleted:false,entity:{labor_id:String(r.l_labor_id),mnv:String(r.l_mnv||""),business_date:String(r.business_date||""),shift:String(r.l_shift||""),labor_type:String(r.l_labor_type||""),time_marker:String(r.l_time_marker||""),state:String(r.l_state||""),start_at:r.l_start_at??null,end_at:r.l_end_at??null,note:String(r.l_note||""),deduct_staff:Number(r.l_deduct_staff||0),start_event_id:String(r.l_start_event_id||""),finish_event_id:r.l_finish_event_id??null,version:Number(r.l_version||0)}};}
  if(String(r.entity_type||"")==="ATTENDANCE_SESSION")return{entity_type:"ATTENDANCE_SESSION",entity_id:String(r.entity_id||""),deleted:true,entity:null};
  if(String(r.entity_type||"")==="LABOR_SESSION")return{entity_type:"LABOR_SESSION",entity_id:String(r.entity_id||""),deleted:true,entity:null};
  return null;
}
function deltaItem(r:DeltaRow):Record<string,unknown>{
  let payload:Record<string,unknown>={};try{payload=JSON.parse(String(r.payload_json||"{}")) as Record<string,unknown>;}catch{}
  const mnv=String(r.a_mnv||r.l_mnv||payload.mnv||""),fullName=String(r.a_full_name||r.l_full_name||payload.full_name||payload.target_label||""),shift=String(r.a_shift||r.l_shift||payload.shift||"");
  const event={event_id:String(r.event_id||""),event_type:String(r.event_type||""),entity_type:String(r.entity_type||""),entity_id:String(r.entity_id||""),business_date:String(r.business_date||""),authority_epoch:Number(r.authority_epoch||0),authority_seq:Number(r.authority_seq||0),service_generation:String(r.service_generation||""),base_version:Number(r.base_version||0),new_version:Number(r.new_version||0),actor_id:String(r.actor_id||""),actor_role:String(r.actor_role||""),device_id:String(r.device_id||""),occurred_at:String(r.occurred_at||""),committed_at:String(r.committed_at||""),payload_json:String(r.payload_json||"{}"),idempotency_key:String(r.idempotency_key||""),origin:String(r.origin||""),schema_version:Number(r.schema_version||0),checksum:String(r.checksum||"")};
  const compat_event={event_id:event.event_id,mnv,full_name:fullName,shift,event_type:event.event_type,label:compatLabel(event.event_type),at:event.committed_at,at_iso:event.committed_at,actor:event.actor_id,actor_role:event.actor_role,device_id:event.device_id,origin:event.origin||"SERVICE",detail:String(payload.note||payload.labor_type||payload.detail||""),authority_seq:event.authority_seq,payload_json:event.payload_json};
  return{event,canonical_patch:canonicalPatch(r),compat_event};
}
export async function dayDeltaData(db:D1Database,date:string,after:number,limit=250):Promise<Record<string,unknown>>{
  const cap=Math.max(1,Math.min(250,limit)),authority=await db.prepare("SELECT authority_epoch,service_generation FROM authority_state WHERE singleton_id=1").first<{authority_epoch:number;service_generation:string}>();
  if(!authority)throw new Error("AUTHORITY_STATE_MISSING");
  const rev=(await db.prepare("SELECT revision FROM day_revision_state WHERE business_date=?1 AND authority_epoch=?2 AND service_generation=?3").bind(date,authority.authority_epoch,authority.service_generation).first<{revision:number}>())?.revision??0;
  if(after<0||after>rev)return{ok:true,business_date:date,from_revision:after,to_revision:after,current_revision:rev,items:[],has_more:false,reset_required:true,reset_reason:"CURSOR_OUTSIDE_CURRENT_REVISION"};
  const q=`SELECT e.event_id,e.event_type,e.entity_type,e.entity_id,e.business_date,e.authority_epoch,e.authority_seq,e.service_generation,e.base_version,e.new_version,e.actor_id,e.actor_role,e.device_id,e.occurred_at,e.committed_at,e.payload_json,e.idempotency_key,e.origin,e.schema_version,e.checksum,
    s.session_id AS a_session_id,s.mnv AS a_mnv,s.shift AS a_shift,s.work_choice AS a_work_choice,s.state AS a_state,s.pda_serial AS a_pda_serial,s.user_pick AS a_user_pick,s.pack_table AS a_pack_table,s.user_pack AS a_user_pack,s.enter_at AS a_enter_at,s.exit_at AS a_exit_at,s.entered_by AS a_entered_by,s.exited_by AS a_exited_by,s.version AS a_version,
    se.full_name AS a_full_name,se.phone AS a_phone,se.main_position AS a_main_position,se.supplier AS a_supplier,se.department AS a_department,se.site AS a_site,se.warehouse AS a_warehouse,se.start_date AS a_start_date,se.note AS a_note,
    l.labor_id AS l_labor_id,l.mnv AS l_mnv,l.shift AS l_shift,l.labor_type AS l_labor_type,l.time_marker AS l_time_marker,l.state AS l_state,l.start_at AS l_start_at,l.end_at AS l_end_at,l.note AS l_note,l.deduct_staff AS l_deduct_staff,l.start_event_id AS l_start_event_id,l.finish_event_id AS l_finish_event_id,l.version AS l_version,
    le.full_name AS l_full_name,le.phone AS l_phone,le.main_position AS l_main_position,le.supplier AS l_supplier,le.department AS l_department,le.site AS l_site,le.warehouse AS l_warehouse,le.start_date AS l_start_date,le.note AS l_note_emp
    FROM events e
    LEFT JOIN attendance_sessions s ON e.entity_type='ATTENDANCE_SESSION' AND s.session_id=e.entity_id
    LEFT JOIN employees se ON se.mnv=s.mnv
    LEFT JOIN labor_sessions l ON e.entity_type='LABOR_SESSION' AND l.labor_id=e.entity_id
    LEFT JOIN employees le ON le.mnv=l.mnv
    WHERE e.business_date=?1 AND e.authority_epoch=?2 AND e.service_generation=?3 AND e.authority_seq>?4
    ORDER BY e.authority_seq LIMIT ?5`;
  const result=await db.prepare(q).bind(date,authority.authority_epoch,authority.service_generation,Math.max(0,after),cap+1).all<DeltaRow>(),all=result.results??[],page=all.slice(0,cap),items=page.map(deltaItem),to=page.length?Number(page[page.length-1]!.authority_seq||after):after,hasMore=all.length>cap;
  const gap=items.length===0&&after<rev;
  return{ok:true,business_date:date,from_revision:after,to_revision:to,current_revision:rev,items,has_more:hasMore,reset_required:gap,reset_reason:gap?"CURSOR_GAP_OR_RETENTION":null,service_telemetry:{d1_duration_ms:result.meta.duration,d1_rows_read:result.meta.rows_read,served_by_region:result.meta.served_by_region??"",served_by_primary:result.meta.served_by_primary??false}};
}
export async function dayDeltaV2(request:Request,env:Env):Promise<Response>{const auth=await authenticate(env.DB,env,request);if(!auth)return apiError("UNAUTHORIZED","AUTH",401);const u=new URL(request.url),date=String(u.searchParams.get("business_date")||""),after=Number(u.searchParams.get("after_revision")||0),limit=Number(u.searchParams.get("limit")||250);if(!/^\d{4}-\d{2}-\d{2}$/.test(date))return apiError("BUSINESS_DATE_INVALID","VALIDATION",400);if(!await allowedDate(env.DB,date,auth.role==="SUPERADMIN"&&u.searchParams.get("client_source")==="WEB"))return apiError("BUSINESS_DATE_OUTSIDE_VIEW_WINDOW","PERMISSION",403);return json(await dayDeltaData(env.DB,date,after,limit));}
'''
p.write_text(t[:start]+new+t[end:], encoding="utf-8")

# Legacy portable gets delta without a second HTTP/auth layer.
p=Path("service/src/legacy_sync_portable.ts")
t=p.read_text(encoding="utf-8")
t=t.replace('import { apiError, json, readJsonBody } from "./util";', 'import { apiError, json, readJsonBody } from "./util";\nimport { dayDeltaData } from "./sync_contract";',1)
t=t.replace('const body=await readJsonBody<{action:string;business_date?:string;dates?:unknown[]}>(request),action=String(body.action||"");',
'''const body=await readJsonBody<{action:string;business_date?:string;dates?:unknown[];after_revision?:number}>(request),action=String(body.action||"");''',1)
old='''  if(action==="sync_day")return json({ok:true,sync_engine:"M2_SERVICE_BUSINESS_WINDOW_7",day:await compatDay(env.DB,String(body.business_date||""))});
  if(action==="sync_bootstrap")return json(await compatBootstrap(env.DB,body.dates));'''
new='''  if(action==="sync_delta")return json(await dayDeltaData(env.DB,String(body.business_date||""),Math.max(0,Number(body.after_revision||0)),250));
  if(action==="sync_day")return json({ok:true,sync_engine:"M2_SERVICE_BUSINESS_WINDOW_7",day:await compatDay(env.DB,String(body.business_date||""))});
  if(action==="sync_bootstrap")return json(await compatBootstrap(env.DB,body.dates));'''
if old not in t: raise SystemExit("LEGACY_DELTA_ANCHOR_MISSING")
p.write_text(t.replace(old,new,1),encoding="utf-8")

# Canonical mutation ACK includes entity patch + day revision/cursor; reuses indexed delta helper.
p=Path("service/src/index.ts")
t=p.read_text(encoding="utf-8")
t=t.replace('import { dayDeltaV2, masterDeltaV2, syncStatusV2 } from "./sync_contract";','import { dayDeltaData, dayDeltaV2, masterDeltaV2, syncStatusV2 } from "./sync_contract";',1)
anchor='''async function broadcastEvent(env:Env,e:{event_id:string;event_type:string;entity_type:string;entity_id:string;business_date:string;authority_epoch:number;authority_seq:number;service_generation:string;new_version:number}):Promise<number>{
  const hub=env.REALTIME_HUB.getByName(`business:${e.business_date}`) as unknown as {broadcast(event:typeof e):Promise<number>};try{return await hub.broadcast(e);}catch(err){console.log(JSON.stringify({level:"warn",kind:"realtime_broadcast_failed",event_id:e.event_id,error:String(err)}));return 0;}
}
'''
helper='''async function broadcastEvent(env:Env,e:{event_id:string;event_type:string;entity_type:string;entity_id:string;business_date:string;authority_epoch:number;authority_seq:number;service_generation:string;new_version:number}):Promise<number>{
  const hub=env.REALTIME_HUB.getByName(`business:${e.business_date}`) as unknown as {broadcast(event:typeof e):Promise<number>};try{return await hub.broadcast(e);}catch(err){console.log(JSON.stringify({level:"warn",kind:"realtime_broadcast_failed",event_id:e.event_id,error:String(err)}));return 0;}
}
async function canonicalAck(env:Env,e:{event_id:string;business_date:string;authority_epoch:number;authority_seq:number;service_generation:string}):Promise<Record<string,unknown>>{
  const d=await dayDeltaData(env.DB,e.business_date,Math.max(0,e.authority_seq-1),1),items=Array.isArray(d.items)?d.items as Record<string,unknown>:[],item=items.find(x=>String((x.event as Record<string,unknown>|undefined)?.event_id||"")===e.event_id)??items[0]??{};
  const rev=Math.max(e.authority_seq,Number(d.current_revision||e.authority_seq));
  return{canonical_patch:item.canonical_patch??null,compat_event:item.compat_event??null,business_date:e.business_date,business_date_revision:rev,cursor:{authority_epoch:e.authority_epoch,authority_seq:rev,service_generation:e.service_generation}};
}
'''
if anchor not in t: raise SystemExit("INDEX_ACK_HELPER_ANCHOR_MISSING")
t=t.replace(anchor,helper,1)

old='''  const delivered=await broadcastEvent(env,{event_id:e.event_id,event_type:e.event_type,entity_type:e.entity_type,entity_id:e.entity_id,business_date:e.business_date,authority_epoch:e.authority_epoch,authority_seq:e.authority_seq,service_generation:e.service_generation,new_version:e.new_version});
  return json({ok:true,duplicate:result.duplicate,event:eventPublic(e as unknown as Record<string,unknown>),realtime_delivered:delivered},result.duplicate?200:201);'''
new='''  const delivered=await broadcastEvent(env,{event_id:e.event_id,event_type:e.event_type,entity_type:e.entity_type,entity_id:e.entity_id,business_date:e.business_date,authority_epoch:e.authority_epoch,authority_seq:e.authority_seq,service_generation:e.service_generation,new_version:e.new_version}),ack=await canonicalAck(env,e);
  return json({ok:true,duplicate:result.duplicate,event:eventPublic(e as unknown as Record<string,unknown>),...ack,realtime_delivered:delivered},result.duplicate?200:201);'''
if old not in t: raise SystemExit("INDEX_MUTATE_ACK_ANCHOR_MISSING")
t=t.replace(old,new,1)

old='''for(const input of events){const localEventId=String(input?.event_id||"");try{const result=await commitMutation(env.DB,env,auth,input),e=result.event,delivered=await broadcastEvent(env,e);results.push({local_event_id:localEventId,status:result.duplicate?"DUPLICATE":"CONFIRMED",canonical_event_id:e.event_id,authority_epoch:e.authority_epoch,authority_seq:e.authority_seq,new_version:e.new_version,error_code:null,conflict:null,realtime_delivered:delivered});'''
new='''for(const input of events){const localEventId=String(input?.event_id||"");try{const result=await commitMutation(env.DB,env,auth,input),e=result.event,delivered=await broadcastEvent(env,e),ack=await canonicalAck(env,e);results.push({local_event_id:localEventId,status:result.duplicate?"DUPLICATE":"CONFIRMED",canonical_event_id:e.event_id,authority_epoch:e.authority_epoch,authority_seq:e.authority_seq,new_version:e.new_version,error_code:null,conflict:null,...ack,realtime_delivered:delivered});'''
if old not in t: raise SystemExit("INDEX_BATCH_ACK_ANCHOR_MISSING")
t=t.replace(old,new,1)

old='''  const delivered=await broadcastEvent(env,e);return json({...result,realtime_delivered:delivered},result.duplicate?200:201);'''
new='''  const delivered=await broadcastEvent(env,e),ack=await canonicalAck(env,e);return json({...result,...ack,realtime_delivered:delivered},result.duplicate?200:201);'''
if old not in t: raise SystemExit("INDEX_LEGACY_ACK_ANCHOR_MISSING")
t=t.replace(old,new,1)

old='''const result=await commitLegacyMutation(env.DB,env,auth,input),e=result.event as {event_id:string;event_type:string;entity_type:string;entity_id:string;business_date:string;authority_epoch:number;authority_seq:number;service_generation:string;new_version:number},delivered=await broadcastEvent(env,e);
    results.push({local_event_id:localEventId,status:result.duplicate?"DUPLICATE":"CONFIRMED",canonical_event_id:e.event_id,authority_epoch:e.authority_epoch,authority_seq:e.authority_seq,new_version:e.new_version,error_code:null,conflict:null,realtime_delivered:delivered});'''
new='''const result=await commitLegacyMutation(env.DB,env,auth,input),e=result.event as {event_id:string;event_type:string;entity_type:string;entity_id:string;business_date:string;authority_epoch:number;authority_seq:number;service_generation:string;new_version:number},delivered=await broadcastEvent(env,e),ack=await canonicalAck(env,e);
    results.push({local_event_id:localEventId,status:result.duplicate?"DUPLICATE":"CONFIRMED",canonical_event_id:e.event_id,authority_epoch:e.authority_epoch,authority_seq:e.authority_seq,new_version:e.new_version,error_code:null,conflict:null,...ack,realtime_delivered:delivered});'''
if old not in t: raise SystemExit("INDEX_LEGACY_BATCH_ACK_ANCHOR_MISSING")
t=t.replace(old,new,1)
p.write_text(t,encoding="utf-8")

# Android local snapshot applies only canonical entity/event patches; no business rule duplication.
p=Path("app/src/main/java/vn/pickpack1291/app/beta/OperationalDataStore.kt")
t=p.read_text(encoding="utf-8")
anchor='''    fun loadDay(date: String): JSONObject? {
'''
method=r'''    fun applyDayDelta(date: String, toRevision: Long, items: JSONArray): Boolean = withDbLock {
        if (date.isBlank() || toRevision <= 0L) return@withDbLock false
        val db = writableDb()
        val raw = db.query("day_snapshot", arrayOf("snapshot_json"), "business_date=?", arrayOf(date), null, null, null, "1").use { c ->
            if (c.moveToFirst()) c.getString(0) else null
        } ?: return@withDbLock false
        val day = runCatching { JSONObject(raw) }.getOrNull() ?: return@withDbLock false
        val sessions = day.optJSONArray("sessions") ?: JSONArray()
        val labor = day.optJSONArray("labor") ?: JSONArray()
        val events = day.optJSONArray("events") ?: JSONArray()

        fun upsert(array: JSONArray, key: String, id: String, entity: JSONObject?, deleted: Boolean) {
            if (id.isBlank()) return
            var found = -1
            for (i in 0 until array.length()) if (array.optJSONObject(i)?.optString(key) == id) { found = i; break }
            if (deleted) { if (found >= 0) array.remove(found); return }
            if (entity == null) return
            if (found >= 0) array.put(found, JSONObject(entity.toString())) else array.put(JSONObject(entity.toString()))
        }
        fun upsertEvent(event: JSONObject?) {
            if (event == null) return
            val id = event.optString("event_id")
            if (id.isBlank()) return
            var found = -1
            for (i in 0 until events.length()) if (events.optJSONObject(i)?.optString("event_id") == id) { found = i; break }
            if (found >= 0) events.put(found, JSONObject(event.toString())) else events.put(JSONObject(event.toString()))
        }

        for (i in 0 until items.length()) {
            val item = items.optJSONObject(i) ?: continue
            val patch = item.optJSONObject("canonical_patch")
            if (patch != null) {
                val entityType = patch.optString("entity_type")
                val entityId = patch.optString("entity_id")
                val deleted = patch.optBoolean("deleted", false)
                val entity = patch.optJSONObject("entity")
                when (entityType) {
                    "ATTENDANCE_SESSION" -> upsert(sessions, "id", entityId, entity, deleted)
                    "LABOR_SESSION" -> upsert(labor, "labor_id", entityId, entity, deleted)
                }
            }
            upsertEvent(item.optJSONObject("compat_event"))
        }
        day.put("sessions", sessions).put("labor", labor).put("events", events).put("day_revision", toRevision)
        val values = ContentValues().apply {
            put("business_date", date); put("day_revision", toRevision); put("snapshot_json", day.toString()); put("saved_at", System.currentTimeMillis())
        }
        db.beginTransaction()
        try {
            db.insertWithOnConflict("day_snapshot", null, values, SQLiteDatabase.CONFLICT_REPLACE)
            db.setTransactionSuccessful()
        } finally { db.endTransaction() }
        MEMORY[date] = JSONObject(day.toString())
        true
    }

'''
if anchor not in t: raise SystemExit("STORE_DELTA_ANCHOR_MISSING")
p.write_text(t.replace(anchor,method+anchor,1),encoding="utf-8")

# Android transport can request delta and consume canonical ACK without an extra status/full snapshot.
p=Path("app/src/main/java/vn/pickpack1291/app/beta/M2ServiceTransport.kt")
t=p.read_text(encoding="utf-8")
if 'val SYNC_ACTIONS = setOf("sync_status", "sync_day", "sync_bootstrap", "service_connections")' not in t: raise SystemExit("SYNC_ACTIONS_ANCHOR_MISSING")
t=t.replace('val SYNC_ACTIONS = setOf("sync_status", "sync_day", "sync_bootstrap", "service_connections")','val SYNC_ACTIONS = setOf("sync_status", "sync_delta", "sync_day", "sync_bootstrap", "service_connections")',1)
old='''                    "CONFIRMED","DUPLICATE"->{store.markMutationSynced(eventId);finalized.put(JSONObject().put("event_id",eventId).put("status",result.optString("status")).put("canonical_event_id",result.optString("event_id").ifBlank{eventId}))}'''
new='''                    "CONFIRMED","DUPLICATE"->{
                        val date=result.optString("business_date");val revision=result.optLong("business_date_revision",0L)
                        if(date.isNotBlank()&&revision>0L){
                            val ackItem=JSONObject().put("canonical_patch",result.optJSONObject("canonical_patch")).put("compat_event",result.optJSONObject("compat_event"))
                            runCatching{store.applyDayDelta(date,revision,JSONArray().put(ackItem))}
                        }
                        store.markMutationSynced(eventId);finalized.put(JSONObject().put("event_id",eventId).put("status",result.optString("status")).put("canonical_event_id",result.optString("canonical_event_id").ifBlank{eventId}))
                    }'''
if old not in t: raise SystemExit("TRANSPORT_ACK_ANCHOR_MISSING")
p.write_text(t.replace(old,new,1),encoding="utf-8")

# Foreground must never enqueue catch-up after every successful status; only outbox on network recovery.
p=Path("app/src/main/java/vn/pickpack1291/app/beta/ForegroundSyncCoordinator.kt")
t=p.read_text(encoding="utf-8")
old1="                    M2WorkScheduler.schedule(app)\n                    M2PushRegistration.flush(app)\n                    LanCoordinator.get(app).onNetworkChanged()"
new1="                    M2WorkScheduler.scheduleOutbox(app)\n                    M2PushRegistration.flush(app)\n                    LanCoordinator.get(app).onNetworkChanged()"
if old1 not in t: raise SystemExit("FG_NETWORK_ANCHOR_MISSING")
t=t.replace(old1,new1,1)
old2="                    M2WorkScheduler.schedule(app)\n                    M2PushRegistration.flush(app)\n\n                    if (state == State.ACTIVE"
new2="                    // R5: successful foreground status is already the orchestrator wake; do not enqueue a second catch-up.\n\n                    if (state == State.ACTIVE"
if old2 not in t: raise SystemExit("FG_SUCCESS_ANCHOR_MISSING")
t=t.replace(old2,new2,1)
p.write_text(t,encoding="utf-8")

# FCM is a coalesced background catch-up wake, not a generic outbox+catchup fan-out.
p=Path("app/src/main/java/vn/pickpack1291/app/beta/M2Firebase.kt")
t=p.read_text(encoding="utf-8")
if "M2WorkScheduler.schedule(applicationContext)" not in t: raise SystemExit("FCM_SCHEDULE_ANCHOR_MISSING")
p.write_text(t.replace("M2WorkScheduler.schedule(applicationContext)","M2WorkScheduler.scheduleCatchUp(applicationContext)"),encoding="utf-8")

print("R5_PHASE1B_APPLY_PASS")
