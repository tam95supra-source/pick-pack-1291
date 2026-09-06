#!/usr/bin/env node
// Exact service functions, disposable SQLite, fixed clock; no network or LIVE writes.
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash, webcrypto } from 'node:crypto';
import { stripTypeScriptTypes } from 'node:module';
import { DatabaseSync } from 'node:sqlite';
import { createContext, SourceTextModule, SyntheticModule } from 'node:vm';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const businessDate = '2030-01-02'; // Isolated fixture, never a LIVE business date.
let clock = Date.parse(`${businessDate}T12:00:00+07:00`);
class ClockDate extends Date {
  constructor(...args) { super(...(args.length ? args : [clock])); }
  static now() { return clock; }
}
const actor = {login_id:'clock-test',role:'SUPERADMIN',device_id:'clock-test'};
const context = createContext({Date:ClockDate,crypto:webcrypto,Request,Response,Headers,TextEncoder,TextDecoder,URL,URLSearchParams,Intl,console});
const modules = new Map();
const hashes = {};
function stub(name, exports) {
  return new SyntheticModule(Object.keys(exports), function() {
    for (const [key, value] of Object.entries(exports)) this.setExport(key, value);
  }, {context,identifier:name});
}
modules.set('auth', stub('auth', {authenticate:async()=>actor}));
modules.set('push', stub('push', {enqueueInvalidation:async()=>{}}));
modules.set('quota_budget', stub('quota_budget', {requireSheetsCall:async()=>{throw Error('NETWORK_FORBIDDEN_IN_CLOCK_TEST');}}));
function load(name) {
  if (modules.has(name)) return modules.get(name);
  const path = `service/src/${name}.ts`;
  const source = readFileSync(resolve(root,path),'utf8');
  hashes[path] = createHash('sha256').update(source).digest('hex');
  const module = new SourceTextModule(stripTypeScriptTypes(source,{mode:'transform'}),{context,identifier:name});
  modules.set(name,module);
  return module;
}
const hotfix = load('session_hotfix');
await hotfix.link(specifier=>{
  assert.match(specifier,/^\.\/[a-z_]+$/);
  return load(specifier.slice(2));
});
await hotfix.evaluate();
const core = modules.get('core').namespace;

function fixture({shift='Ca 2',state='ACTIVE',exitAt=null,laborState='COMPLETED',endAt=null}={}) {
  const sqlite = new DatabaseSync(':memory:');
  sqlite.exec(`
    CREATE TABLE authority_state(singleton_id INTEGER PRIMARY KEY,authority_epoch,authority_seq,mode,scope,service_generation,updated_at);
    INSERT INTO authority_state VALUES(1,1,0,'SERVICE_PRIMARY','PRODUCTION','isolated-clock','');
    CREATE TABLE business_dates(business_date TEXT PRIMARY KEY,sequence_no INTEGER);
    CREATE TABLE attendance_sessions(session_id TEXT PRIMARY KEY,mnv,business_date,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,pda_enter_status,pda_exit_status,resource_note,enter_at,exit_at,entered_by,exited_by,version,updated_at);
    CREATE TABLE labor_sessions(labor_id TEXT PRIMARY KEY,mnv,business_date,state,start_at,end_at,version,finish_event_id,note,updated_at);
    CREATE TABLE events(event_id TEXT PRIMARY KEY,event_type,entity_type,entity_id,business_date,authority_epoch,authority_seq,service_generation,base_version,new_version,actor_id,actor_role,device_id,occurred_at,committed_at,payload_json,idempotency_key TEXT UNIQUE,origin,schema_version,checksum,UNIQUE(authority_epoch,authority_seq));
    CREATE TABLE day_revision_state(business_date,authority_epoch,service_generation,revision,updated_at,PRIMARY KEY(business_date,authority_epoch,service_generation));
    CREATE TABLE sheet_replication_outbox(event_id TEXT PRIMARY KEY,status,next_attempt_at);
    CREATE TABLE mutation_assertions(event_id TEXT PRIMARY KEY,ok);
    CREATE TABLE resource_leases(session_id);
  `);
  const startAt = new Date(Date.parse(`${businessDate}T06:00:00+07:00`)).toISOString();
  sqlite.prepare('INSERT INTO business_dates VALUES(?,1)').run(businessDate);
  sqlite.prepare('INSERT INTO attendance_sessions(session_id,mnv,business_date,shift,work_choice,state,resource_note,enter_at,exit_at,version) VALUES(?,?,?,?,?,?,?,?,?,1)').run('session-clock','employee-clock',businessDate,shift,'KHONG',state,'',startAt,exitAt);
  sqlite.prepare('INSERT INTO labor_sessions(labor_id,mnv,business_date,state,start_at,end_at,version) VALUES(?,?,?,?,?,?,1)').run('labor-clock','employee-clock',businessDate,laborState,startAt,endAt);
  class Statement {
    constructor(sql) { this.sql=sql; this.values={}; }
    bind(...args) { this.values=Object.fromEntries(args.map((v,i)=>[String(i+1),v])); return this; }
    execute() {
      const prepared=sqlite.prepare(this.sql);
      const args=Object.keys(this.values).length?[this.values]:[];
      if (/^\s*SELECT/i.test(this.sql)) return {success:true,results:prepared.all(...args),meta:{changes:0}};
      const result=prepared.run(...args);
      return {success:true,results:[],meta:{changes:Number(result.changes)}};
    }
    async first() { return this.execute().results[0]??null; }
    async all() { return this.execute(); }
    async run() { return this.execute(); }
  }
  const db={prepare:sql=>new Statement(sql),async batch(statements) {
    sqlite.exec('BEGIN');
    try { const result=statements.map(s=>s.execute()); sqlite.exec('COMMIT'); return result; }
    catch(error) { sqlite.exec('ROLLBACK'); throw error; }
  }};
  const env={DB:db,REALTIME_HUB:{getByName:()=>({invalidate:async()=>0})}};
  const request=(type,payload={})=>({event_id:`event-${type}`,idempotency_key:`idem-${type}`,entity_id:type==='LABOR_FINISH'?'labor-clock':'session-clock',entity_type:type==='LABOR_FINISH'?'LABOR_SESSION':'ATTENDANCE_SESSION',event_type:type,business_date:businessDate,device_id:actor.device_id,base_version:1,schema_version:1,authority_epoch:1,service_generation:'isolated-clock',timestamp:new Date(clock).toISOString(),payload:{mnv:'employee-clock',session_id:'session-clock',...payload}});
  return {db,env,sqlite,startAt,request};
}
const cases=[];
async function caseRun(name,fn) { await fn(); cases.push({name,status:'PASS'}); }
async function coreError(f,req,code) {
  await assert.rejects(()=>core.commitMutation(f.db,f.env,actor,req),error=>error.code===code);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) n FROM events').get().n,0,'rejected operation wrote an event');
}
async function exitCase(route,deltaMs,{shift='Ca 2',open=false,expected=null}={}) {
  const f=fixture({shift,laborState:open?'OPEN':'COMPLETED',endAt:new Date(clock+deltaMs).toISOString()});
  try {
    if(route==='core') {
      if(expected) await coreError(f,f.request('ATTENDANCE_EXIT'),expected);
      else await core.commitMutation(f.db,f.env,actor,f.request('ATTENDANCE_EXIT'));
    } else {
      const response=await hotfix.namespace.sessionExitGuarded(new Request('https://fixture.invalid/v1/session/exit-v2',{method:'POST',body:JSON.stringify({session_id:'session-clock',idempotency_key:'exit-clock'})}),f.env);
      const body=await response.json();
      if(expected) { assert.equal(response.status,409); assert.equal(body.error.code,expected); }
      else { assert.equal(response.status,201); assert.equal(body.session.state,'ENDED'); }
    }
    assert.equal(f.sqlite.prepare('SELECT state FROM attendance_sessions').get().state,expected?'ACTIVE':'ENDED');
    assert.equal(f.sqlite.prepare('SELECT COUNT(*) n FROM events').get().n,expected?0:1);
    assert.equal(f.sqlite.prepare('SELECT COUNT(*) n FROM sheet_replication_outbox').get().n,expected?0:1);
  } finally { f.sqlite.close(); }
}
for(const [shift,endHour] of [['Ca 1',14],['Ca HC',17],['Ca 2',22]]) {
  const scheduled=Date.parse(`${businessDate}T${endHour}:00:00+07:00`);
  for(const [period,now] of [['before_shift_end',scheduled-120_000],['late_day',scheduled+120_000]]) {
    clock=now;
    const cap=Math.max(scheduled,clock+60_000);
    await caseRun(`${shift}_${period}_finish_exact_cap`,async()=>{
      const f=fixture({shift,laborState:'OPEN'});
      try {
        const result=await core.commitMutation(f.db,f.env,actor,f.request('LABOR_FINISH',{start_at:f.startAt,end_at:new Date(cap).toISOString()}));
        assert.equal(result.event.event_type,'LABOR_FINISH');
        assert.equal(f.sqlite.prepare('SELECT state FROM labor_sessions').get().state,'COMPLETED');
      } finally { f.sqlite.close(); }
    });
    await caseRun(`${shift}_${period}_reject_after_cap`,async()=>{
      const f=fixture({shift,laborState:'OPEN'});
      try { await coreError(f,f.request('LABOR_FINISH',{end_at:new Date(cap+1).toISOString()}),'LABOR_END_AFTER_SHIFT_OR_EXIT'); }
      finally { f.sqlite.close(); }
    });
    for(const route of ['core','exit_v2']) {
      await caseRun(`${shift}_${period}_${route}_future_block`,()=>exitCase(route,60_001,{shift,expected:'FUTURE_LABOR_BLOCKS_EXIT'}));
      await caseRun(`${shift}_${period}_${route}_boundary_allowed`,()=>exitCase(route,60_000,{shift}));
      await caseRun(`${shift}_${period}_${route}_open_block`,()=>exitCase(route,0,{shift,open:true,expected:'OPEN_LABOR_BLOCKS_EXIT'}));
    }
  }
  clock=scheduled+300_000;
  for(const extra of [0,1]) await caseRun(`${shift}_actual_exit_cap_${extra?'reject':'allow'}`,async()=>{
    const exitAt=new Date(clock-60_000).toISOString();
    const f=fixture({shift,state:'ENDED',exitAt,laborState:'COMPLETED'});
    try {
      const req=f.request('LABOR_FINISH',{correction:true,end_at:new Date(Date.parse(exitAt)+extra).toISOString()});
      if(extra) await coreError(f,req,'LABOR_END_AFTER_SHIFT_OR_EXIT');
      else await core.commitMutation(f.db,f.env,actor,req);
    } finally { f.sqlite.close(); }
  });
}
const receipt={status:'PASS',classification:'EXACT_SERVICE_FUNCTIONS_ISOLATED_SQLITE_CONTROLLED_CLOCK',network:false,production_writes:0,source_sha256:hashes,case_count:cases.length,cases,limits:'Auth and invalidation transports are isolated stubs; this verifies labor/exit semantics, not deployment, auth, UI, or billing.'};
const output=process.argv[2];
if(output) { mkdirSync(dirname(resolve(output)),{recursive:true}); writeFileSync(output,JSON.stringify(receipt,null,2)+'\n'); }
console.log(JSON.stringify({status:receipt.status,classification:receipt.classification,case_count:receipt.case_count}));
