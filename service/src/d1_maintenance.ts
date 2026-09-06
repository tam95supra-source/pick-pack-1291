import { nowIso } from "./util";

type MetaResult={changes?:number};
type Config={warnDbPercent:number;preparePercent:number;cutoverPercent:number;ownerTotalPercent:number;retentionDays:number;dbQuotaBytes:number;accountQuotaBytes:number};

export async function claimMaintenance(db:D1Database,taskKey:string,intervalMs:number):Promise<boolean>{
  const now=Date.now(),at=new Date(now).toISOString(),cutoff=new Date(now-Math.max(60_000,intervalMs)).toISOString();
  const r=await db.prepare(`INSERT INTO service_maintenance(task_key,last_run_at,checkpoint,updated_at)
    VALUES(?1,?2,'',?2)
    ON CONFLICT(task_key) DO UPDATE SET last_run_at=excluded.last_run_at,updated_at=excluded.updated_at
    WHERE service_maintenance.last_run_at IS NULL OR service_maintenance.last_run_at<=?3`).bind(taskKey,at,cutoff).run();
  return Number((r.meta as MetaResult|undefined)?.changes??0)>0;
}

async function configNumber(db:D1Database,key:string,fallback:number):Promise<number>{
  const r=await db.prepare("SELECT config_value FROM runtime_config WHERE config_key=?1").bind(key).first<{config_value:string}>();
  const n=Number(r?.config_value??fallback);return Number.isFinite(n)?n:fallback;
}
export async function readResilienceConfig(db:D1Database):Promise<Config>{
  const [warn,prepare,cutover,total,retention,dbQuota,accountQuota]=await Promise.all([
    configNumber(db,"WARN_DB_PERCENT",70),configNumber(db,"PREPARE_NEXT_DB_PERCENT",80),configNumber(db,"CUTOVER_DB_PERCENT",85),
    configNumber(db,"OWNER_TOTAL_QUOTA_WARN_PERCENT",80),configNumber(db,"RETENTION_DAYS",45),
    configNumber(db,"D1_DB_QUOTA_BYTES",0),configNumber(db,"D1_ACCOUNT_QUOTA_BYTES",0),
  ]);
  return {warnDbPercent:warn,preparePercent:prepare,cutoverPercent:cutover,ownerTotalPercent:total,retentionDays:Math.max(45,Math.min(365,Math.round(retention))),dbQuotaBytes:Math.max(0,dbQuota),accountQuotaBytes:Math.max(0,accountQuota)};
}

async function pragmaNumber(db:D1Database,name:"page_count"|"page_size"):Promise<number>{
  try{const r=await db.prepare(`PRAGMA ${name}`).first<Record<string,unknown>>();return Number(r?.[name]??0)||0;}catch{return 0;}
}
export async function d1CapacitySnapshot(db:D1Database):Promise<Record<string,unknown>>{
  const at=nowIso(),cfg=await readResilienceConfig(db);
  // Capacity is an operational guard, not a reporting endpoint. Keep its hot-path
  // reads bounded by retention metadata and indexed pending lookups; never COUNT
  // large business/event tables on every scheduled run.
  const [pageCount,pageSize,dates,pending,authority,gen,previous]=await Promise.all([
    pragmaNumber(db,"page_count"),pragmaNumber(db,"page_size"),
    db.prepare("SELECT MIN(business_date) oldest_business_date,MAX(business_date) newest_business_date,COUNT(*) business_dates FROM business_dates").first<Record<string,unknown>>(),
    db.prepare(`SELECT
      EXISTS(SELECT 1 FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT') LIMIT 1) sheet_pending,
      EXISTS(SELECT 1 FROM outbound_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT') LIMIT 1) outbound_pending,
      (SELECT created_at FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT') ORDER BY created_at LIMIT 1) oldest_sheet_pending_event,
      (SELECT created_at FROM outbound_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT') ORDER BY created_at LIMIT 1) oldest_outbound_pending_event`).first<Record<string,unknown>>(),
    db.prepare("SELECT authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state WHERE singleton_id=1").first<Record<string,unknown>>(),
    db.prepare("SELECT generation_id,db_binding,db_name,status,created_at,active_from_event,active_to_event,business_date_from,business_date_to,schema_version,checksum_checkpoint,authority_epoch FROM d1_generation_registry ORDER BY created_at").all<Record<string,unknown>>(),
    db.prepare("SELECT checkpoint,updated_at FROM service_maintenance WHERE task_key='capacity-snapshot'").first<{checkpoint:string;updated_at:string}>(),
  ]);
  const bytes=pageCount*pageSize,percent=cfg.dbQuotaBytes>0?(bytes/cfg.dbQuotaBytes)*100:null;
  let growthPerDay=0,estimatedDaysRemaining:number|null=null;
  try{
    const p=JSON.parse(previous?.checkpoint||"{}") as {bytes?:number;at?:string};
    const elapsed=(Date.parse(at)-Date.parse(String(p.at||"")))/86_400_000;
    if(elapsed>0&&Number(p.bytes)>=0)growthPerDay=Math.max(0,(bytes-Number(p.bytes))/elapsed);
  }catch{}
  if(cfg.dbQuotaBytes>0&&growthPerDay>0)estimatedDaysRemaining=Math.max(0,(cfg.dbQuotaBytes-bytes)/growthPerDay);
  const prepare=percent!==null&&percent>=cfg.preparePercent,cutover=percent!==null&&(percent>=cfg.cutoverPercent||(estimatedDaysRemaining!==null&&estimatedDaysRemaining<=3));
  const state=cutover?"CUTOVER_REQUIRED":prepare?"PREPARE_REQUIRED":percent!==null&&percent>=cfg.warnDbPercent?"WARN":"OK";
  const snapshot={at,bytes,page_count:pageCount,page_size:pageSize,db_quota_bytes:cfg.dbQuotaBytes,db_percent:percent,growth_bytes_per_day:growthPerDay,estimated_days_remaining:estimatedDaysRemaining,state,thresholds:{warn:cfg.warnDbPercent,prepare:cfg.preparePercent,cutover:cfg.cutoverPercent,owner_total:cfg.ownerTotalPercent},retention_days:cfg.retentionDays,dates:dates??{},pending:pending??{},authority:authority??{},generations:gen.results??[],rows_by_table:"OMITTED_FROM_HOT_PATH"};
  await db.prepare(`INSERT INTO service_maintenance(task_key,last_run_at,checkpoint,updated_at) VALUES('capacity-snapshot',?1,?2,?1)
    ON CONFLICT(task_key) DO UPDATE SET last_run_at=excluded.last_run_at,checkpoint=excluded.checkpoint,updated_at=excluded.updated_at`).bind(at,JSON.stringify({at,bytes,state,db_percent:percent,estimated_days_remaining:estimatedDaysRemaining})).run();
  return snapshot;
}

async function eligibleOldDates(db:D1Database,cutoff:string,limit=3):Promise<string[]>{
  const r=await db.prepare(`SELECT b.business_date
    FROM business_dates b
    WHERE b.business_date<?1
      AND EXISTS(SELECT 1 FROM backup_manifests m WHERE m.status='VERIFIED' AND m.first_business_date<=b.business_date AND m.last_business_date>=b.business_date)
      AND NOT EXISTS(SELECT 1 FROM attendance_sessions s WHERE s.business_date=b.business_date AND s.state='ACTIVE')
      AND NOT EXISTS(SELECT 1 FROM labor_sessions l WHERE l.business_date=b.business_date AND l.state='OPEN')
      AND NOT EXISTS(SELECT 1 FROM events e JOIN sheet_replication_outbox o ON o.event_id=e.event_id WHERE e.business_date=b.business_date AND o.status IN ('PENDING','RETRY','INFLIGHT'))
      AND NOT EXISTS(SELECT 1 FROM events e JOIN outbound_replication_outbox o ON o.event_id=e.event_id WHERE e.business_date=b.business_date AND o.status IN ('PENDING','RETRY','INFLIGHT'))
    ORDER BY b.business_date LIMIT ?2`).bind(cutoff,Math.max(1,Math.min(limit,3))).all<{business_date:string}>();
  return (r.results??[]).map(x=>x.business_date);
}
async function deleteBusinessDate(db:D1Database,date:string):Promise<void>{
  await db.batch([
    db.prepare("DELETE FROM resource_leases WHERE business_date=?1").bind(date),
    db.prepare("DELETE FROM resource_daily_consumption WHERE business_date=?1").bind(date),
    db.prepare("DELETE FROM labor_sessions WHERE business_date=?1").bind(date),
    db.prepare("DELETE FROM historical_session_snapshots WHERE business_date=?1").bind(date),
    db.prepare("DELETE FROM outbound_drop_records WHERE business_date=?1").bind(date),
    db.prepare("DELETE FROM attendance_sessions WHERE business_date=?1").bind(date),
    db.prepare("DELETE FROM conflicts WHERE event_id IN (SELECT event_id FROM events WHERE business_date=?1)").bind(date),
    db.prepare("DELETE FROM mutation_assertions WHERE event_id IN (SELECT event_id FROM events WHERE business_date=?1)").bind(date),
    db.prepare("DELETE FROM events WHERE business_date=?1").bind(date),
    db.prepare("DELETE FROM business_dates WHERE business_date=?1").bind(date),
  ]);
}
export async function recordVerifiedBackup(db:D1Database,input:{backup_id:string;created_at:string;source:string;first_event:string;last_event:string;first_business_date:string;last_business_date:string;row_counts_json:string;table_counts_json:string;checksum:string;schema_version:number;checkpoint:string}):Promise<void>{
  if(!input.backup_id||!input.checksum||!input.first_business_date||!input.last_business_date)throw new Error("BACKUP_MANIFEST_REQUIRED");
  await db.prepare(`INSERT INTO backup_manifests(backup_id,created_at,source,first_event,last_event,first_business_date,last_business_date,row_counts_json,table_counts_json,checksum,schema_version,checkpoint,status,verified_at)
    VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,'VERIFIED',?13)
    ON CONFLICT(backup_id) DO UPDATE SET status='VERIFIED',verified_at=excluded.verified_at,checksum=excluded.checksum,checkpoint=excluded.checkpoint`)
    .bind(input.backup_id,input.created_at,input.source,input.first_event,input.last_event,input.first_business_date,input.last_business_date,input.row_counts_json,input.table_counts_json,input.checksum,input.schema_version,input.checkpoint,nowIso()).run();
}
export async function runD1Retention(db:D1Database):Promise<{retention_days:number;operational_dates:number;meal_rows:number;meal_audit_rows:number;push_rows:number;import_batches:number;bootstrap_runs:number}>{
  const cfg=await readResilienceConfig(db),today=new Date(Date.now()+7*3600_000).toISOString().slice(0,10);
  const cutoff=new Date(Date.parse(today+"T00:00:00Z")-(cfg.retentionDays-1)*86_400_000).toISOString().slice(0,10);
  const dates=await eligibleOldDates(db,cutoff,3);
  for(const date of dates)await deleteBusinessDate(db,date);
  const mealAudit=await db.prepare(`DELETE FROM post_meal_attendance_audit WHERE business_date<?1 AND EXISTS(SELECT 1 FROM backup_manifests m WHERE m.status='VERIFIED' AND m.first_business_date<=post_meal_attendance_audit.business_date AND m.last_business_date>=post_meal_attendance_audit.business_date)`).bind(cutoff).run();
  const meal=await db.prepare(`DELETE FROM post_meal_attendance WHERE business_date<?1 AND EXISTS(SELECT 1 FROM backup_manifests m WHERE m.status='VERIFIED' AND m.first_business_date<=post_meal_attendance.business_date AND m.last_business_date>=post_meal_attendance.business_date)`).bind(cutoff).run();
  const technicalCutoff=new Date(Date.now()-45*86_400_000).toISOString();
  const push=await db.prepare("DELETE FROM push_outbox WHERE created_at<?1 AND status IN ('SENT','FAILED')").bind(technicalCutoff).run();
  const imports=await db.prepare("DELETE FROM import_batches WHERE started_at<?1").bind(technicalCutoff).run();
  const bootstrap=await db.prepare("DELETE FROM bootstrap_runs WHERE started_at<?1 AND status IN ('COMPLETE','FAILED') AND run_id NOT IN (SELECT run_id FROM bootstrap_runs WHERE status='COMPLETE' ORDER BY completed_at DESC LIMIT 3)").bind(technicalCutoff).run();
  const mealRows=Number((meal.meta as MetaResult|undefined)?.changes??0),mealAuditRows=Number((mealAudit.meta as MetaResult|undefined)?.changes??0),pushRows=Number((push.meta as MetaResult|undefined)?.changes??0),importBatches=Number((imports.meta as MetaResult|undefined)?.changes??0),bootstrapRuns=Number((bootstrap.meta as MetaResult|undefined)?.changes??0);
  await db.prepare("UPDATE service_maintenance SET checkpoint=?1,updated_at=?2 WHERE task_key='retention-daily'")
    .bind(JSON.stringify({at:nowIso(),retention_days:cfg.retentionDays,cutoff,dates,backup_required:true}),nowIso()).run();
  return{retention_days:cfg.retentionDays,operational_dates:dates.length,meal_rows:mealRows,meal_audit_rows:mealAuditRows,push_rows:pushRows,import_batches:importBatches,bootstrap_runs:bootstrapRuns};
}
