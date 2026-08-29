import { nowIso } from "./util";

type MetaResult={changes?:number};

export async function claimMaintenance(db:D1Database,taskKey:string,intervalMs:number):Promise<boolean>{
  const now=Date.now(),at=new Date(now).toISOString(),cutoff=new Date(now-Math.max(60_000,intervalMs)).toISOString();
  const r=await db.prepare(`INSERT INTO service_maintenance(task_key,last_run_at,checkpoint,updated_at)
    VALUES(?1,?2,'',?2)
    ON CONFLICT(task_key) DO UPDATE SET last_run_at=excluded.last_run_at,updated_at=excluded.updated_at
    WHERE service_maintenance.last_run_at IS NULL OR service_maintenance.last_run_at<=?3`).bind(taskKey,at,cutoff).run();
  return Number((r.meta as MetaResult|undefined)?.changes??0)>0;
}

async function eligibleOldDates(db:D1Database,cutoff:string,limit=3):Promise<string[]>{
  const r=await db.prepare(`SELECT b.business_date
    FROM business_dates b
    WHERE b.business_date<?1
      AND NOT EXISTS(SELECT 1 FROM attendance_sessions s WHERE s.business_date=b.business_date AND s.state='ACTIVE')
      AND NOT EXISTS(SELECT 1 FROM labor_sessions l WHERE l.business_date=b.business_date AND l.state='OPEN')
      AND NOT EXISTS(
        SELECT 1 FROM events e JOIN sheet_replication_outbox o ON o.event_id=e.event_id
        WHERE e.business_date=b.business_date AND o.status IN ('PENDING','RETRY','INFLIGHT')
      )
      AND NOT EXISTS(
        SELECT 1 FROM events e JOIN outbound_replication_outbox o ON o.event_id=e.event_id
        WHERE e.business_date=b.business_date AND o.status IN ('PENDING','RETRY','INFLIGHT')
      )
    ORDER BY b.business_date
    LIMIT ?2`).bind(cutoff,Math.max(1,Math.min(limit,3))).all<{business_date:string}>();
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
    db.prepare("DELETE FROM events WHERE business_date=?1").bind(date),
    db.prepare("DELETE FROM business_dates WHERE business_date=?1").bind(date),
  ]);
}

export async function runD1Retention(db:D1Database):Promise<{operational_dates:number;meal_rows:number;push_rows:number}>{
  const today=new Date(Date.now()+7*3600_000).toISOString().slice(0,10);
  const operationalCutoff=new Date(Date.parse(today+"T00:00:00Z")-44*86_400_000).toISOString().slice(0,10);
  const mealCutoff=new Date(Date.parse(today+"T00:00:00Z")-13*86_400_000).toISOString().slice(0,10);
  const dates=await eligibleOldDates(db,operationalCutoff,3);
  for(const date of dates)await deleteBusinessDate(db,date);
  const meal=await db.prepare("DELETE FROM post_meal_attendance WHERE business_date<?1").bind(mealCutoff).run();
  const push=await db.prepare("DELETE FROM push_outbox WHERE created_at<?1 AND status IN ('SENT','FAILED')").bind(new Date(Date.now()-45*86_400_000).toISOString()).run();
  const mealRows=Number((meal.meta as MetaResult|undefined)?.changes??0),pushRows=Number((push.meta as MetaResult|undefined)?.changes??0);
  await db.prepare("UPDATE service_maintenance SET checkpoint=?1,updated_at=?2 WHERE task_key='retention-daily'")
    .bind(JSON.stringify({at:nowIso(),operational_cutoff:operationalCutoff,meal_cutoff:mealCutoff,dates}),nowIso()).run();
  return{operational_dates:dates.length,meal_rows:mealRows,push_rows:pushRows};
}
