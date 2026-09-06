export type SheetsQuotaKind="READ"|"WRITE";
export type GasSheetOperationCost={read?:number;write?:number};

function utcKeys(d=new Date()):{day:string;minute:string}{
  const iso=d.toISOString();return{day:iso.slice(0,10),minute:iso.slice(0,16)};
}
function usageStmt(db:D1Database,windowKey:string,metric:string,count:number):D1PreparedStatement{
  return db.prepare(`INSERT INTO quota_usage(window_key,metric,used,hard_limit,updated_at)
    SELECT ?1,p.metric,?3,p.hard_limit,strftime('%Y-%m-%dT%H:%M:%fZ','now') FROM quota_policy p WHERE p.metric=?2
    ON CONFLICT(window_key,metric) DO UPDATE SET
      used=quota_usage.used+excluded.used,hard_limit=excluded.hard_limit,updated_at=excluded.updated_at`)
    .bind(windowKey,metric,count);
}
function units(value:unknown,max=100):number{
  const n=Math.floor(Number(value||0));return Number.isFinite(n)?Math.max(0,Math.min(max,n)):0;
}

/** Reserve quota before an actual Google Sheets API request. */
export async function reserveSheetsCall(db:D1Database,kind:SheetsQuotaKind,count=1):Promise<boolean>{
  const n=Math.max(1,units(count)||1),k=utcKeys(),metric=kind==="READ"?"GOOGLE_SHEETS_READ_MINUTE":"GOOGLE_SHEETS_WRITE_MINUTE";
  try{
    await db.batch([
      usageStmt(db,`D:${k.day}`,"GOOGLE_SHEETS_DAILY",n),
      usageStmt(db,`M:${k.minute}`,"GOOGLE_SHEETS_PROJECT_MINUTE",n),
      usageStmt(db,`M:${k.minute}`,metric,n),
    ]);
    return true;
  }catch(e){
    if(String(e).includes("quota_hard_limit")||String(e).includes("CHECK constraint failed"))return false;
    throw e;
  }
}
export async function requireSheetsCall(db:D1Database,kind:SheetsQuotaKind,count=1):Promise<void>{
  if(!await reserveSheetsCall(db,kind,count))throw new Error(`QUOTA_DEFERRED:GOOGLE_SHEETS:${kind}`);
}

/**
 * Application-side guard for SpreadsheetApp work performed behind GAS bridges.
 * These units are deliberately distinct from Sheets API requests. One HTTP bridge
 * call can reserve multiple logical read/write operation units.
 */
export async function reserveGasSheetOperations(db:D1Database,cost:GasSheetOperationCost):Promise<boolean>{
  const read=units(cost.read,100),write=units(cost.write,100),total=read+write;if(total<=0)return true;
  const k=utcKeys(),stmts:D1PreparedStatement[]=[usageStmt(db,`D:${k.day}`,"GOOGLE_GAS_SHEET_OP_DAILY",total)];
  if(read>0)stmts.push(usageStmt(db,`M:${k.minute}`,"GOOGLE_GAS_SHEET_READ_MINUTE",read));
  if(write>0)stmts.push(usageStmt(db,`M:${k.minute}`,"GOOGLE_GAS_SHEET_WRITE_MINUTE",write));
  try{await db.batch(stmts);return true;}
  catch(e){
    if(String(e).includes("quota_hard_limit")||String(e).includes("CHECK constraint failed"))return false;
    throw e;
  }
}
export async function requireGasSheetOperations(db:D1Database,cost:GasSheetOperationCost):Promise<void>{
  if(!await reserveGasSheetOperations(db,cost))throw new Error("QUOTA_DEFERRED:GOOGLE_GAS_SHEET_OP");
}

export async function quotaUsageSnapshot(db:D1Database):Promise<Record<string,unknown>>{
  const k=utcKeys(),results=await db.batch([
    db.prepare("SELECT metric,hard_limit,unit,source_requirement FROM quota_policy ORDER BY metric"),
    db.prepare("SELECT metric,used FROM quota_usage WHERE window_key=?1 ORDER BY metric").bind(`D:${k.day}`),
    db.prepare("SELECT metric,used FROM quota_usage WHERE window_key=?1 ORDER BY metric").bind(`M:${k.minute}`),
  ]),policy=results[0]?.results??[],day=results[1]?.results??[],minute=results[2]?.results??[];
  return{day_utc:k.day,minute_utc:k.minute,policy,day,minute};
}
