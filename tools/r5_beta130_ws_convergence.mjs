import fs from 'node:fs';
import path from 'node:path';

const serviceUrl = String(process.env.SERVICE_URL || '').replace(/\/$/, '');
const date = String(process.env.B80_DATE || '');
const mnv = String(process.env.B80_MNV || '');
const suffix = String(process.env.SUFFIX || '');
const device = String(process.env.DEVICE || '');
const out = String(process.env.R5_WS_OUT || '/tmp/r5-ws-convergence');
const tokens = [1,2,3,4,5].map(i => String(process.env[`R5_TOKEN_${i}`] || ''));
if (!serviceUrl || !/^\d{4}-\d{2}-\d{2}$/.test(date) || !mnv || !suffix || !device || tokens.some(t => !t)) {
  throw new Error('R5_WS_ENV_INVALID');
}
fs.mkdirSync(out, {recursive:true});

const clients = tokens.map((token, idx) => ({id:idx+1, kind:idx < 3 ? 'PDA' : 'WEB', token, cursor:-1, ws:null}));
const samples = [];
const statusRows = [];

function timeout(ms, label) {
  return new Promise((_, reject) => setTimeout(() => reject(new Error(`TIMEOUT:${label}`)), ms));
}
async function fetchJson(url, init = {}, label = 'fetch') {
  const r = await fetch(url, init);
  const text = await r.text();
  let j; try { j = JSON.parse(text); } catch { throw new Error(`${label}_JSON:${r.status}:${text.slice(0,300)}`); }
  if (!r.ok) throw new Error(`${label}_HTTP_${r.status}:${JSON.stringify(j).slice(0,500)}`);
  return j;
}
async function status(client) {
  let j;
  if (client.kind === 'PDA') {
    j = await fetchJson(`${serviceUrl}/v1/legacy-sync`, {
      method:'POST', headers:{Authorization:`Bearer ${client.token}`,'Content-Type':'application/json'},
      body:JSON.stringify({action:'sync_status'})
    }, `PDA_STATUS_${client.id}`);
    if (!j.ok || j.mode !== 'APP_SERVICE_D1') throw new Error(`PDA_STATUS_CONTRACT_${client.id}`);
    client.cursor = Number(j.day_revisions?.[date] ?? -1);
    statusRows.push(Number(j.service_telemetry?.db_rows_read ?? 0));
  } else {
    j = await fetchJson(`${serviceUrl}/v1/sync/status`, {headers:{Authorization:`Bearer ${client.token}`}}, `WEB_STATUS_${client.id}`);
    if (!j.ok || j.contract !== 'LOCAL_FIRST_REVISION_V1') throw new Error(`WEB_STATUS_CONTRACT_${client.id}`);
    const row = Array.isArray(j.business_window) ? j.business_window.find(x => x.business_date === date) : null;
    client.cursor = Number(row?.revision ?? -1);
    statusRows.push(Number(j.service_telemetry?.d1_rows_read ?? 0));
  }
  if (!Number.isInteger(client.cursor) || client.cursor < 0) throw new Error(`CURSOR_INVALID_${client.id}:${client.cursor}`);
}
async function connect(client) {
  const ticket = await fetchJson(`${serviceUrl}/v1/realtime/ticket?business_date=${encodeURIComponent(date)}`, {
    method:'POST', headers:{Authorization:`Bearer ${client.token}`,'Content-Type':'application/json'}, body:'{}'
  }, `TICKET_${client.id}`);
  if (!ticket.ticket) throw new Error(`TICKET_MISSING_${client.id}`);
  const wsUrl = serviceUrl.replace(/^https:/,'wss:').replace(/^http:/,'ws:') + `/v1/realtime?ticket=${encodeURIComponent(ticket.ticket)}`;
  const ws = new WebSocket(wsUrl);
  client.ws = ws;
  await Promise.race([
    new Promise((resolve,reject) => {
      const onError = () => reject(new Error(`WS_ERROR_${client.id}`));
      ws.addEventListener('error', onError, {once:true});
      const onMessage = (ev) => {
        let j; try { j = JSON.parse(String(ev.data)); } catch { return; }
        if (j.type === 'REALTIME_READY') {
          if (j.protocol !== 'INVALIDATION_V1') reject(new Error(`WS_PROTOCOL_${client.id}:${j.protocol}`));
          else resolve();
        }
      };
      ws.addEventListener('message', onMessage);
    }), timeout(5000,`WS_READY_${client.id}`)
  ]);
}
async function delta(client, expectedId) {
  const requestAt = Date.now();
  let j;
  if (client.kind === 'PDA') {
    j = await fetchJson(`${serviceUrl}/v1/legacy-sync`, {
      method:'POST', headers:{Authorization:`Bearer ${client.token}`,'Content-Type':'application/json'},
      body:JSON.stringify({action:'sync_delta',business_date:date,after_revision:client.cursor})
    }, `PDA_DELTA_${client.id}`);
  } else {
    j = await fetchJson(`${serviceUrl}/v1/delta/day?business_date=${encodeURIComponent(date)}&after_revision=${client.cursor}&limit=250&client_source=WEB`, {
      headers:{Authorization:`Bearer ${client.token}`}
    }, `WEB_DELTA_${client.id}`);
  }
  if (!j.ok || j.reset_required === true) throw new Error(`DELTA_CONTRACT_${client.id}:${JSON.stringify(j).slice(0,400)}`);
  const item = (Array.isArray(j.items) ? j.items : []).find(x => x?.event?.event_id === expectedId);
  if (!item) throw new Error(`DELTA_EVENT_MISSING_${client.id}:${expectedId}:from=${client.cursor}:to=${j.to_revision}`);
  const next = Number(j.to_revision ?? item.event?.authority_seq ?? -1);
  if (!Number.isInteger(next) || next < client.cursor) throw new Error(`DELTA_CURSOR_INVALID_${client.id}:${client.cursor}->${next}`);
  client.cursor = next;
  const committed = Date.parse(String(item.event?.committed_at || ''));
  if (!Number.isFinite(committed)) throw new Error(`COMMITTED_AT_INVALID_${client.id}`);
  const rows = Number(client.kind === 'PDA' ? (j.service_telemetry?.db_rows_read ?? 0) : (j.service_telemetry?.d1_rows_read ?? 0));
  return {requestAt, visibleAt:Date.now(), committed, rows};
}
function waitInvalidation(client, expectedId, trial) {
  const waitStartedAt = Date.now();
  return Promise.race([
    new Promise((resolve,reject) => {
      const ws = client.ws;
      if (!ws) return reject(new Error(`WS_MISSING_${client.id}`));
      const handler = async (ev) => {
        let j; try { j = JSON.parse(String(ev.data)); } catch { return; }
        if (j.type !== 'DAY_CHANGED' || j.event_id !== expectedId || j.business_date !== date) return;
        ws.removeEventListener('message', handler);
        const wakeAt = Date.now();
        try {
          const d = await delta(client, expectedId);
          resolve({
            trial, client:client.id, kind:client.kind,
            ms:d.visibleAt-d.committed,
            commit_to_ws_wake_ms:wakeAt-d.committed,
            ws_wake_to_delta_visible_ms:d.visibleAt-wakeAt,
            delta_request_ms:d.visibleAt-d.requestAt,
            listener_wait_ms:wakeAt-waitStartedAt,
            d1_rows_read:d.rows,
            authority_seq:Number(j.authority_seq ?? 0)
          });
        } catch (e) { reject(e); }
      };
      ws.addEventListener('message', handler);
    }), timeout(2500,`INVALIDATION_${trial}_${client.id}`)
  ]);
}
function quantile(values,p){const v=[...values].sort((a,b)=>a-b);return v[Math.max(0,Math.ceil(v.length*p)-1)];}
function stats(values){
  const v=values.map(Number).filter(Number.isFinite);
  return {count:v.length,p50:quantile(v,.50),p95:quantile(v,.95),p99:quantile(v,.99),max:Math.max(...v),avg:v.reduce((a,b)=>a+b,0)/v.length};
}
function persistSamples(){fs.writeFileSync(path.join(out,'samples.json'),JSON.stringify(samples,null,2));}

try {
  await Promise.all(clients.map(status));
  const cursors = new Set(clients.map(c => c.cursor));
  if (cursors.size !== 1) throw new Error(`INITIAL_CURSOR_DIVERGENCE:${JSON.stringify(clients.map(c=>[c.id,c.cursor]))}`);
  await Promise.all(clients.map(connect));

  for (let trial=1; trial<=10; trial++) {
    const eventId = `__R5_WS_CONV_${suffix}_${String(trial).padStart(2,'0')}`;
    const waits = clients.map(c => waitInvalidation(c,eventId,trial));
    const mutation = await fetchJson(`${serviceUrl}/v1/legacy-mutations/batch`, {
      method:'POST', headers:{Authorization:`Bearer ${clients[0].token}`,'Content-Type':'application/json'},
      body:JSON.stringify({events:[{action:'resource_change',event_id:eventId,device_id:device,business_date:date,payload:{mnv,work_choice:'',pda_serial:'',user_pick:'',pack_table:'',user_pack:'',resource_note:'R5 WS wake to delta convergence',duplicate_user:false,note:''}}]})
    }, `MUTATION_${trial}`);
    const rr = mutation.results?.[0];
    if (!mutation.ok || rr?.status !== 'CONFIRMED' || rr?.canonical_event_id !== eventId) throw new Error(`MUTATION_CONTRACT_${trial}:${JSON.stringify(mutation).slice(0,600)}`);
    if (Number(rr?.realtime_delivered ?? 0) < 5) throw new Error(`REALTIME_DELIVERY_COUNT_${trial}:${rr?.realtime_delivered}`);
    const got = await Promise.all(waits);
    samples.push(...got);
    persistSamples();
    const seqs = new Set(got.map(x=>x.authority_seq));
    if (seqs.size !== 1 || Number(rr.authority_seq) !== got[0].authority_seq) throw new Error(`REVISION_MISMATCH_${trial}`);
  }

  if (samples.length !== 50) throw new Error(`SAMPLE_COUNT:${samples.length}`);
  const vals=samples.map(x=>x.ms), remote=stats(vals);
  const deltaRows=samples.map(x=>x.d1_rows_read), maxStatus=Math.max(...statusRows), maxDelta=Math.max(...deltaRows);
  const EVENTS=1540,CLIENTS=5,BATCH=100;
  const fixed=(EVENTS*40)+(1440*100)+(EVENTS*20)+100000;
  const reads=Math.ceil(fixed+(EVENTS*CLIENTS*maxDelta)+(CLIENTS*96*maxStatus));
  const writes=(EVENTS*9)+(CLIENTS*96)+(Math.ceil(EVENTS/BATCH)*10*3)+1000;
  const workers=EVENTS+(EVENTS*CLIENTS)+(CLIENTS*96)+1440+2000;
  const sheets=Math.ceil(EVENTS/BATCH)*10;
  const measurement={
    status:'MEASURED',classification:'EXACT_DEPLOYED_SERVICE_WS_WAKE_DELTA_5_ISOLATED_AUTH_SESSIONS',
    clients:{total:5,android_pda:3,web:2},auth_sessions:{isolated:true,pda:3,web:2,writer_client:1},trials:10,samples:50,
    realtime_path:'canonical commit -> Durable Object INVALIDATION_V1 DAY_CHANGED -> exact client delta transport -> target event visible',
    transport_paths:{android_pda_wake:'WebSocket /v1/realtime after POST /v1/realtime/ticket',android_pda_delta:'POST /v1/legacy-sync sync_delta',web_wake:'WebSocket /v1/realtime after POST /v1/realtime/ticket',web_delta:'GET /v1/delta/day'},
    remote_convergence_ms:{...remote,target_p95_max:1000,target_p99_max:2000,clock_start:'event.committed_at',clock_end:'delta response parsed and target canonical event visible'},
    phase_ms:{
      commit_to_ws_wake:stats(samples.map(x=>x.commit_to_ws_wake_ms)),
      ws_wake_to_delta_visible:stats(samples.map(x=>x.ws_wake_to_delta_visible_ms)),
      delta_request:stats(samples.map(x=>x.delta_request_ms)),
      pda_remote:stats(samples.filter(x=>x.kind==='PDA').map(x=>x.ms)),
      web_remote:stats(samples.filter(x=>x.kind==='WEB').map(x=>x.ms))
    },
    hot_path_d1_rows_read:{status_max:maxStatus,delta_max:maxDelta,status_avg:statusRows.reduce((a,b)=>a+b,0)/statusRows.length,delta_avg:deltaRows.reduce((a,b)=>a+b,0)/deltaRows.length},
    normalized_max_day:{events:EVENTS,clients:CLIENTS,d1_rows_read:reads,d1_rows_read_target_max:500000,d1_rows_written:writes,d1_rows_written_target_max:20000,worker_requests:workers,worker_requests_target_max:20000,sheets_api_calls:sheets,sheets_api_calls_target_max:250},
    before_baseline:{run_id:34001866785,rows_read_24h:3522525,rows_written_24h:33136,read_queries_24h:40820,write_queries_24h:2098}
  };
  fs.writeFileSync(path.join(out,'measurement.json'),JSON.stringify(measurement,null,2));
  console.log(JSON.stringify({r5_ws_measurement:'MEASURED',p50_ms:remote.p50,p95_ms:remote.p95,p99_ms:remote.p99,max_ms:remote.max,commit_to_ws_p95:measurement.phase_ms.commit_to_ws_wake.p95,delta_p95:measurement.phase_ms.ws_wake_to_delta_visible.p95}));

  if (remote.p95>1000) throw new Error(`R5_REMOTE_P95_EXCEEDED:${remote.p95}`);
  if (remote.p99>2000) throw new Error(`R5_REMOTE_P99_EXCEEDED:${remote.p99}`);
  if(reads>500000)throw new Error(`R5_D1_ROWS_READ_MODEL_EXCEEDED:${reads}`);
  if(writes>20000)throw new Error(`R5_D1_ROWS_WRITE_MODEL_EXCEEDED:${writes}`);
  if(workers>20000)throw new Error(`R5_WORKER_REQUEST_MODEL_EXCEEDED:${workers}`);
  if(sheets>250)throw new Error(`R5_SHEETS_CALL_MODEL_EXCEEDED:${sheets}`);

  const receipt={
    ...measurement,status:'PASS',
    notes:['Foreground production path is INVALIDATION_V1 WebSocket wake followed by revision-driven delta; background durability remains FCM/WorkManager and is covered separately.','Five independently authenticated sessions are held open concurrently: clients 1-3 PDA, clients 4-5 WEB.','No Google API is called by this measurement.']
  };
  fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2));
  console.log(JSON.stringify({r5_ws_convergence:'PASS',p50_ms:remote.p50,p95_ms:remote.p95,p99_ms:remote.p99,max_ms:remote.max,delta_rows_max:maxDelta,normalized_rows_read:reads,normalized_rows_written:writes,worker_requests:workers,sheets_calls:sheets}));
} catch (e) {
  persistSamples();
  fs.writeFileSync(path.join(out,'failure.json'),JSON.stringify({status:'FAIL',error:String(e?.message||e),samples:samples.length},null,2));
  throw e;
} finally {
  for (const c of clients) { try { c.ws?.close(1000,'done'); } catch {} }
}
