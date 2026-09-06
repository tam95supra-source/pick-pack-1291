import { authenticate } from "./auth";
import { compatBootstrap, compatDay } from "./compat";
import { apiError, json, readJsonBody } from "./util";
import { dayDeltaData } from "./sync_contract";

interface ClientSyncRow{
  business_date:string;sequence_no:number;max_seq:number|null;
  authority_epoch:number;authority_seq:number;mode:string;scope:string;service_generation:string;updated_at:string;
  server_retention_floor:string|null;projection_pending:number|null;master_revision:number|null;
}

export async function m2ClientSyncStatus(db:D1Database):Promise<Record<string,unknown>>{
  const q=`WITH recent AS (
      SELECT business_date,sequence_no FROM business_dates ORDER BY sequence_no DESC LIMIT 7
    ), current_authority AS (
      SELECT authority_epoch,authority_seq,mode,scope,service_generation,updated_at FROM authority_state WHERE singleton_id=1
    ), rev AS (
      SELECT recent.business_date,recent.sequence_no,COALESCE(day_revision_state.revision,0) AS max_seq
      FROM recent CROSS JOIN current_authority a
      LEFT JOIN day_revision_state ON day_revision_state.business_date=recent.business_date
        AND day_revision_state.authority_epoch=a.authority_epoch
        AND day_revision_state.service_generation=a.service_generation
    ), meta AS (
      SELECT
        (SELECT business_date FROM business_dates ORDER BY sequence_no ASC LIMIT 1) AS server_retention_floor,
        COALESCE((SELECT pending_count FROM replication_status WHERE singleton_id=1),0) AS projection_pending,
        COALESCE((SELECT revision FROM revision_state WHERE namespace='employees'),0) AS master_revision
    )
    SELECT rev.business_date,rev.sequence_no,rev.max_seq,
      a.authority_epoch,a.authority_seq,a.mode,a.scope,a.service_generation,a.updated_at,
      meta.server_retention_floor,meta.projection_pending,meta.master_revision
    FROM rev CROSS JOIN current_authority a CROSS JOIN meta
    ORDER BY rev.sequence_no DESC`;
  const result=await db.prepare(q).all<ClientSyncRow>(),rows=result.results??[],first=rows[0];
  if(!first)throw new Error("SYNC_STATUS_EMPTY");
  const dayRevisions:Record<string,number>={};for(const r of rows)dayRevisions[r.business_date]=Math.max(1,Number(r.max_seq??0));
  const authority={authority_epoch:first.authority_epoch,authority_seq:first.authority_seq,mode:first.mode,scope:first.scope,service_generation:first.service_generation,updated_at:first.updated_at};
  const meta=(result.meta??{}) as Record<string,unknown>;
  return{
    ok:true,business_date:first.business_date,server_seq:first.authority_seq,master_revision:Number(first.master_revision??0),last_event_at:first.updated_at,
    projection_pending:Number(first.projection_pending??0),mode:"APP_SERVICE_D1",sync_engine:"M2_SERVICE_BUSINESS_WINDOW_7",
    retention_floor:rows[rows.length-1]?.business_date??first.business_date,server_retention_floor:first.server_retention_floor??rows[rows.length-1]?.business_date??first.business_date,
    retention_epoch:first.authority_epoch,day_revisions:dayRevisions,authority,service_generation:first.service_generation,
    service_telemetry:{db_duration_ms:Number(meta.duration||0),db_rows_read:Number(meta.rows_read||0),served_by_region:String(meta.served_by_region||""),served_by_primary:Boolean(meta.served_by_primary)}
  };
}

export async function legacySyncPortable(request:Request,env:Env):Promise<Response>{
  const auth=await authenticate(env.DB,env,request);if(!auth)return apiError("UNAUTHORIZED","AUTH",401);
  const body=await readJsonBody<{action:string;business_date?:string;dates?:unknown[];after_revision?:number}>(request),action=String(body.action||"");
  if(action==="sync_status")return json(await m2ClientSyncStatus(env.DB));
  if(action==="sync_delta")return json(await dayDeltaData(env.DB,String(body.business_date||""),Math.max(0,Number(body.after_revision||0)),250));
  if(action==="sync_day")return json({ok:true,sync_engine:"M2_SERVICE_BUSINESS_WINDOW_7",day:await compatDay(env.DB,String(body.business_date||""))});
  if(action==="sync_bootstrap")return json(await compatBootstrap(env.DB,body.dates));
  return apiError("LEGACY_SYNC_ACTION_UNSUPPORTED","VALIDATION",400);
}
