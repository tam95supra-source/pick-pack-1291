#!/usr/bin/env python3
from pathlib import Path

# Durable coalesced wake + terminal special-projection outboxes.
m=Path('service/migrations/0016_r5_background_terminal.sql')
if not m.exists():
    m.write_text(r'''PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS push_wake_outbox (
  scope_key TEXT PRIMARY KEY,
  namespace TEXT NOT NULL,
  revision INTEGER,
  business_date TEXT,
  authority_epoch INTEGER NOT NULL,
  authority_seq INTEGER NOT NULL,
  payload_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','RETRY','SENT','FAILED')),
  attempt_count INTEGER NOT NULL DEFAULT 0,
  next_attempt_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  last_error_class TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_push_wake_due ON push_wake_outbox(status,next_attempt_at,updated_at);

CREATE TABLE IF NOT EXISTS session_special_projection_outbox (
  event_id TEXT PRIMARY KEY REFERENCES events(event_id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','INFLIGHT','RETRY','SYNCED','FAILED')),
  attempt_count INTEGER NOT NULL DEFAULT 0,
  next_attempt_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  claim_token TEXT,
  claimed_at TEXT,
  last_error TEXT,
  projected_at TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_session_special_due ON session_special_projection_outbox(status,next_attempt_at,created_at);

INSERT OR IGNORE INTO schema_migrations(version,checksum)
VALUES('0016_r5_background_terminal','R5_BACKGROUND_TERMINAL_V1');
''',encoding='utf-8')

# Replace push staging/flush tail. Latest revision supersedes older wakes because FCM is wake-only.
p=Path('service/src/push.ts')
t=p.read_text(encoding='utf-8')
start=t.index('export async function enqueueInvalidation')
new=r'''function wakeScope(namespace:string,businessDate?:string):string{return businessDate?`DAY:${businessDate}`:`MASTER:${namespace}`;}
async function upsertWake(db:D1Database,namespace:string,revision:number|undefined,businessDate:string|undefined,authorityEpoch:number,authoritySeq:number,at:string):Promise<void>{
  const scope=wakeScope(namespace,businessDate),payload={type:businessDate?"DAY_CHANGED":"MASTER_CHANGED",namespace,revision:revision??null,business_date:businessDate??null,authority_epoch:authorityEpoch,authority_seq:authoritySeq};
  await db.prepare(`INSERT INTO push_wake_outbox(scope_key,namespace,revision,business_date,authority_epoch,authority_seq,payload_json,status,attempt_count,next_attempt_at,created_at,updated_at)
    VALUES(?1,?2,?3,?4,?5,?6,?7,'PENDING',0,?8,?8,?8)
    ON CONFLICT(scope_key) DO UPDATE SET namespace=excluded.namespace,revision=excluded.revision,business_date=excluded.business_date,
      authority_epoch=excluded.authority_epoch,authority_seq=excluded.authority_seq,payload_json=excluded.payload_json,status='PENDING',attempt_count=0,
      next_attempt_at=excluded.next_attempt_at,last_error_class=NULL,updated_at=excluded.updated_at
    WHERE excluded.authority_epoch>push_wake_outbox.authority_epoch OR (excluded.authority_epoch=push_wake_outbox.authority_epoch AND excluded.authority_seq>=push_wake_outbox.authority_seq)`).bind(scope,namespace,revision??null,businessDate??null,authorityEpoch,authoritySeq,JSON.stringify(payload),at).run();
}
export async function enqueueInvalidation(db:D1Database,namespace:string,revision:number|undefined,businessDate?:string):Promise<void>{const a=await currentAuthority(db);await upsertWake(db,namespace,revision,businessDate,a.authority_epoch,a.authority_seq,nowIso());}

/** Stage at most one current wake per changed business day. This reads the O(days) revision projection, never scans event rows. */
async function stageRecentDayInvalidations(db:D1Database):Promise<void>{
  const cutoff=new Date(Date.now()-10*60_000).toISOString(),a=await currentAuthority(db),rows=(await db.prepare(`SELECT business_date,revision,updated_at FROM day_revision_state WHERE authority_epoch=?1 AND service_generation=?2 AND updated_at>=?3 ORDER BY updated_at DESC LIMIT 7`).bind(a.authority_epoch,a.service_generation,cutoff).all<{business_date:string;revision:number;updated_at:string}>()).results??[];
  for(const r of rows)await upsertWake(db,"business_day",r.revision,r.business_date,a.authority_epoch,Math.max(a.authority_seq,r.revision),r.updated_at||nowIso());
}

type PushWake={scope_key:string;payload_json:string;attempt_count:number};
type PushDevice={device_id:string;login_id:string;fcm_token:string};
export async function flushPushOutbox(db:D1Database,rawEnv:Env,limit=12):Promise<{configured:boolean;sent:number;invalid:number;retry:number;pending:number}>{
  await stageRecentDayInvalidations(db);
  const env=rawEnv as PushEnv,access=await fcmAccessToken(env);if(!access)return{configured:false,sent:0,invalid:0,retry:0,pending:(await db.prepare("SELECT COUNT(*) n FROM push_wake_outbox WHERE status IN ('PENDING','RETRY')").first<{n:number}>())?.n??0};
  const now=nowIso(),pushes=(await db.prepare("SELECT scope_key,payload_json,attempt_count FROM push_wake_outbox WHERE status IN ('PENDING','RETRY') AND next_attempt_at<=?1 ORDER BY updated_at LIMIT ?2").bind(now,Math.max(1,Math.min(24,limit))).all<PushWake>()).results??[],devices=(await db.prepare("SELECT device_id,login_id,fcm_token FROM push_devices WHERE status='ACTIVE'").all<PushDevice>()).results??[];let sent=0,invalid=0,retry=0;
  const deviceState=new Map<string,{token:string;ok:boolean;invalid:boolean;error:string|null}>();
  for(const d of devices)deviceState.set(d.fcm_token,{token:d.fcm_token,ok:false,invalid:false,error:null});
  for(const p of pushes){let transient=false;for(const d of devices){const state=deviceState.get(d.fcm_token)!;if(state.invalid)continue;const data=JSON.parse(p.payload_json) as Record<string,unknown>,stringData=Object.fromEntries(Object.entries(data).map(([k,v])=>[k,v==null?"":String(v)]));const r=await fetch(`https://fcm.googleapis.com/v1/projects/${encodeURIComponent(access.projectId)}/messages:send`,{method:"POST",headers:{authorization:`Bearer ${access.token}`,"content-type":"application/json"},body:JSON.stringify({message:{token:d.fcm_token,data:stringData,android:{priority:"high"}}})});if(r.ok){sent++;state.ok=true;continue;}const text=(await r.text()).slice(0,800);if(r.status===404||/UNREGISTERED|registration-token-not-registered/i.test(text)){invalid++;state.invalid=true;state.error='UNREGISTERED';}else if(r.status===429||r.status>=500){transient=true;retry++;state.error=`FCM_HTTP_${r.status}`;}else state.error=`FCM_HTTP_${r.status}`;}
    const attempts=p.attempt_count+1,next=new Date(Date.now()+Math.min(3600_000,Math.pow(2,Math.min(attempts,8))*5000)).toISOString();await db.prepare("UPDATE push_wake_outbox SET status=?1,attempt_count=?2,next_attempt_at=?3,last_error_class=?4,updated_at=?5 WHERE scope_key=?6").bind(transient&&attempts<8?"RETRY":transient?"FAILED":"SENT",attempts,next,transient?"FCM_TRANSIENT":null,nowIso(),p.scope_key).run();
  }
  const updates:D1PreparedStatement[]=[];for(const s of deviceState.values()){if(s.invalid)updates.push(db.prepare("UPDATE push_devices SET status='INVALID',last_error_class='UNREGISTERED',updated_at=?1 WHERE fcm_token=?2").bind(nowIso(),s.token));else if(s.ok)updates.push(db.prepare("UPDATE push_devices SET last_success_at=?1,last_error_class=?2,updated_at=?1 WHERE fcm_token=?3").bind(nowIso(),s.error,s.token));else if(s.error)updates.push(db.prepare("UPDATE push_devices SET last_error_class=?1,updated_at=?2 WHERE fcm_token=?3").bind(s.error,nowIso(),s.token));}if(updates.length)await db.batch(updates);
  const pending=(await db.prepare("SELECT COUNT(*) n FROM push_wake_outbox WHERE status IN ('PENDING','RETRY')").first<{n:number}>())?.n??0;return{configured:true,sent,invalid,retry,pending};
}
'''
p.write_text(t[:start]+new,encoding='utf-8')

# Convert correction/delete projection to a durable terminal outbox with fencing.
p=Path('service/src/session_hotfix.ts')
s=p.read_text(encoding='utf-8')
anchor='async function projectSpecial(env:Env,e:EventRow):Promise<void>{'
pos=s.index(anchor)
# Insert helpers immediately before projectSpecial, keeping projectSpecial itself.
helpers=r'''function specialOutboxStmt(db:D1Database,e:EventRow):D1PreparedStatement{return db.prepare("INSERT OR IGNORE INTO session_special_projection_outbox(event_id,status,next_attempt_at,created_at,updated_at) VALUES(?1,'PENDING',?2,?2,?2)").bind(e.event_id,e.committed_at);}
async function projectSpecialTerminal(env:Env,e:EventRow):Promise<boolean>{
  await env.DB.prepare("INSERT OR IGNORE INTO session_special_projection_outbox(event_id,status,next_attempt_at,created_at,updated_at) VALUES(?1,'PENDING',?2,?2,?2)").bind(e.event_id,e.committed_at).run();
  const token=crypto.randomUUID(),at=nowIso(),claim=await env.DB.prepare("UPDATE session_special_projection_outbox SET status='INFLIGHT',claim_token=?1,claimed_at=?2,attempt_count=attempt_count+1,updated_at=?2 WHERE event_id=?3 AND status IN ('PENDING','RETRY') AND next_attempt_at<=?2").bind(token,at,e.event_id).run();if(Number(claim.meta.changes||0)!==1)return false;
  try{await projectSpecial(env,e);await env.DB.prepare("UPDATE session_special_projection_outbox SET status='SYNCED',claim_token=NULL,claimed_at=NULL,last_error=NULL,projected_at=?1,updated_at=?1 WHERE event_id=?2 AND claim_token=?3").bind(nowIso(),e.event_id,token).run();return true;}catch(err){const row=await env.DB.prepare("SELECT attempt_count FROM session_special_projection_outbox WHERE event_id=?1").bind(e.event_id).first<{attempt_count:number}>(),attempt=Math.max(1,Number(row?.attempt_count||1)),terminal=attempt>=8,next=new Date(Date.now()+Math.min(3600_000,Math.pow(2,Math.min(attempt,8))*5000)).toISOString();await env.DB.prepare("UPDATE session_special_projection_outbox SET status=?1,claim_token=NULL,claimed_at=NULL,next_attempt_at=?2,last_error=?3,updated_at=?4 WHERE event_id=?5 AND claim_token=?6").bind(terminal?'FAILED':'RETRY',next,String(err).slice(0,500),nowIso(),e.event_id,token).run();return false;}
}
'''
s=s[:pos]+helpers+s[pos:]

# Add outbox in same D1 batch as each special event.
needle="const stmts=eventStmts(env.DB,e,a.authority_seq,false);stmts.push(env.DB.prepare(`UPDATE attendance_sessions SET ${field}=?1,version=?2,updated_at=?3 WHERE session_id=?4 AND version=?5`).bind(next,newVersion,e.committed_at,s.session_id,s.version));"
repl="const stmts=eventStmts(env.DB,e,a.authority_seq,false);stmts.push(specialOutboxStmt(env.DB,e));stmts.push(env.DB.prepare(`UPDATE attendance_sessions SET ${field}=?1,version=?2,updated_at=?3 WHERE session_id=?4 AND version=?5`).bind(next,newVersion,e.committed_at,s.session_id,s.version));"
if needle not in s: raise SystemExit('SPECIAL_CORRECT_TX_ANCHOR_MISSING')
s=s.replace(needle,repl,1)
needle="const stmts=eventStmts(env.DB,e,a.authority_seq,false);stmts.push(env.DB.prepare(\"UPDATE attendance_sessions SET state='ACTIVE',exit_at=NULL,exited_by=NULL,pda_exit_status=NULL,pda_serial=?1,user_pick=?2,pack_table=?3,user_pack=?4,pda_enter_status=CASE WHEN ?1 IS NULL THEN NULL ELSE pda_enter_status END,version=?5,updated_at=?6 WHERE session_id=?7 AND version=?8 AND state='ENDED'\")"
repl="const stmts=eventStmts(env.DB,e,a.authority_seq,false);stmts.push(specialOutboxStmt(env.DB,e));stmts.push(env.DB.prepare(\"UPDATE attendance_sessions SET state='ACTIVE',exit_at=NULL,exited_by=NULL,pda_exit_status=NULL,pda_serial=?1,user_pick=?2,pack_table=?3,user_pack=?4,pda_enter_status=CASE WHEN ?1 IS NULL THEN NULL ELSE pda_enter_status END,version=?5,updated_at=?6 WHERE session_id=?7 AND version=?8 AND state='ENDED'\")"
if needle not in s: raise SystemExit('SPECIAL_DELETE_TX_ANCHOR_MISSING')
s=s.replace(needle,repl,1)
# Never re-project an already terminal duplicate; helper claims only due nonterminal rows.
s=s.replace('try{await projectSpecial(env,prior);}catch{}return json({ok:true,duplicate:true,event:prior,session:await byId(env.DB,id)});','await projectSpecialTerminal(env,prior);return json({ok:true,duplicate:true,event:prior,session:await byId(env.DB,id)});')
s=s.replace('let pending=false;try{await projectSpecial(env,e!);}catch{pending=true;}return json({ok:true,event:e!,session:await byId(env.DB,id),projection_pending:pending},201);','const projected=await projectSpecialTerminal(env,e!);return json({ok:true,event:e!,session:await byId(env.DB,id),projection_pending:!projected},201);',1)
s=s.replace('let pending=false;try{await projectSpecial(env,e!);}catch{pending=true;}return json({ok:true,event:e!,session:await byId(env.DB,id),resource_reacquire_conflicts:conflicts,projection_pending:pending},201);','const projected=await projectSpecialTerminal(env,e!);return json({ok:true,event:e!,session:await byId(env.DB,id),resource_reacquire_conflicts:conflicts,projection_pending:!projected},201);',1)
old='export async function flushSessionSpecialProjections(env:Env):Promise<number>{const rows=(await env.DB.prepare("SELECT * FROM events WHERE event_type IN (\'ATTENDANCE_TIME_CORRECTED\',\'ATTENDANCE_EXIT_DELETED\') ORDER BY authority_seq DESC LIMIT 120").all<EventRow>()).results??[];let n=0;for(const e of rows.reverse()){try{await projectSpecial(env,e);n++;}catch{}}return n;}'
new='export async function flushSessionSpecialProjections(env:Env,limit=25):Promise<number>{const stale=new Date(Date.now()-15*60_000).toISOString(),at=nowIso();await env.DB.prepare("UPDATE session_special_projection_outbox SET status=\'RETRY\',claim_token=NULL,claimed_at=NULL,next_attempt_at=?1,updated_at=?1,last_error=COALESCE(last_error,\'STALE_INFLIGHT_RECOVERED\') WHERE status=\'INFLIGHT\' AND (claimed_at IS NULL OR claimed_at<=?2)").bind(at,stale).run();const rows=(await env.DB.prepare("SELECT e.* FROM session_special_projection_outbox o JOIN events e ON e.event_id=o.event_id WHERE o.status IN (\'PENDING\',\'RETRY\') AND o.next_attempt_at<=?1 ORDER BY o.created_at LIMIT ?2").bind(at,Math.max(1,Math.min(50,limit))).all<EventRow>()).results??[];let n=0;for(const e of rows)if(await projectSpecialTerminal(env,e))n++;return n;}'
if old not in s: raise SystemExit('SPECIAL_FLUSH_ANCHOR_MISSING')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('R5_BACKGROUND_TERMINAL_APPLY_PASS')
