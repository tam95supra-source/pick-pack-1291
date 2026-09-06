export type SheetsQuotaKind="READ"|"WRITE";

function utcKeys(d=new Date()):{day:string;minute:string}{
  const iso=d.toISOString();return{day:iso.slice(0,10),minute:iso.slice(0,16)};
}
function usageStmt(db:D1Database,windowKey:string,metric:string,count:number):D1PreparedStatement{
  return db.prepare(`INSERT INTO quota_usage(window_key,metric,used,updated_at) VALUES(?1,?2,?3,strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    ON CONFLICT(window_key,metric) DO UPDATE SET used=used+excluded.used,updated_at=excluded.updated_at`).bind(windowKey,metric,count);
}

/**
 * Reserve quota atomically before an actual Google Sheets API request.
 * Policy limits live in quota_policy (migration/config), not business logic.
 * D1 batch rollback on trigger abort guarantees daily/project/kind windows advance together or not at all.
 */
export async function reserveSheetsCall(db:D1Database,kind:SheetsQuotaKind,count=1):Promise<boolean>{
  const n=Math.max(1,Math.min(100,Math.floor(count))),k=utcKeys(),metric=kind==="READ"?"GOOGLE_SHEETS_READ_MINUTE":"GOOGLE_SHEETS_WRITE_MINUTE";
  try{
    await db.batch([
      usageStmt(db,`D:${k.day}`,"GOOGLE_SHEETS_DAILY",n),
      usageStmt(db,`M:${k.minute}`,"GOOGLE_SHEETS_PROJECT_MINUTE",n),
      usageStmt(db,`M:${k.minute}`,metric,n),
    ]);
    return true;
  }catch(e){
    if(String(e).includes("QUOTA_HARD_LIMIT"))return false;
    throw e;
  }
}

export async function requireSheetsCall(db:D1Database,kind:SheetsQuotaKind,count=1):Promise<void>{
  if(!await reserveSheetsCall(db,kind,count))throw new Error(`QUOTA_DEFERRED:GOOGLE_SHEETS:${kind}`);
}

export async function quotaUsageSnapshot(db:D1Database):Promise<Record<string,unknown>>{
  const k=utcKeys(),[policy,day,minute]=await db.batch([
    db.prepare("SELECT metric,hard_limit,unit,source_requirement FROM quota_policy ORDER BY metric"),
    db.prepare("SELECT metric,used FROM quota_usage WHERE window_key=?1 ORDER BY metric").bind(`D:${k.day}`),
    db.prepare("SELECT metric,used FROM quota_usage WHERE window_key=?1 ORDER BY metric").bind(`M:${k.minute}`),
  ]);
  return{day_utc:k.day,minute_utc:k.minute,policy:policy.results??[],day:day.results??[],minute:minute.results??[]};
}
