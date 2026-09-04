#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=pathlib.Path('/tmp/beta-seed200-recovery.json')
TODAY=datetime.now(ZoneInfo('Asia/Bangkok')).strftime('%Y-%m-%d')
D1=''
def q(s): return "'"+str(s).replace("'","''")+"'"
def d1(sql):
 p=subprocess.run(['npx','wrangler','d1','execute',D1,'--remote','--command',sql,'--json'],cwd=str(ROOT/'service'),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=os.environ.copy(),timeout=120)
 if p.returncode: raise RuntimeError('D1:'+p.stderr[-500:].replace('\n',' '))
 j=json.loads(p.stdout)
 if not j or j[0].get('success') is not True: raise RuntimeError('D1_NOT_SUCCESS')
 return j[0].get('results') or []
try:
 if TODAY!='2026-09-04': raise RuntimeError('DATE_FENCE')
 cfg=json.loads((ROOT/'config/environment_contracts.json').read_text()); b=cfg['environments']['BETA']; s=cfg['environments']['STABLE']
 if b.get('lifecycle')!='LIVE' or s.get('lifecycle')=='LIVE': raise RuntimeError('ENV_GUARD')
 D1=b['current_service']['d1_database']
 a=d1('SELECT authority_epoch,mode,scope,service_generation FROM authority_state WHERE singleton_id=1;')[0]
 if a['mode']!='SERVICE_PRIMARY' or a['scope']!='PRODUCTION': raise RuntimeError('AUTHORITY_GUARD')
 attendance=int(d1('SELECT COUNT(*) n FROM attendance_sessions WHERE business_date='+q(TODAY)+" AND state='ACTIVE' AND exit_at IS NULL")[0]['n'])
 events=int(d1("SELECT COUNT(*) n FROM events WHERE business_date="+q(TODAY)+" AND event_id LIKE 'OWNER_SEED200_20260904_%'")[0]['n'])
 labor=int(d1('SELECT COUNT(*) n FROM labor_sessions WHERE business_date='+q(TODAY))[0]['n'])
 if attendance!=200 or events!=200 or labor!=0: raise RuntimeError(f'BUSINESS_PRECONDITION:{attendance}:{events}:{labor}')
 rows=d1("SELECT o.status,o.claimed_at,COUNT(*) n FROM sheet_replication_outbox o JOIN events e ON e.event_id=o.event_id WHERE e.business_date="+q(TODAY)+" AND e.event_id LIKE 'OWNER_SEED200_20260904_%' GROUP BY o.status,o.claimed_at ORDER BY o.status,o.claimed_at")
 inflight=int(d1("SELECT COUNT(*) n FROM sheet_replication_outbox o JOIN events e ON e.event_id=o.event_id WHERE e.business_date="+q(TODAY)+" AND e.event_id LIKE 'OWNER_SEED200_20260904_%' AND o.status='INFLIGHT'")[0]['n'])
 if inflight!=200: raise RuntimeError(f'EXPECTED_200_INFLIGHT_GOT_{inflight}')
 cutoff=(datetime.now(timezone.utc)-timedelta(minutes=15)).isoformat(timespec='milliseconds').replace('+00:00','Z')
 fresh=int(d1("SELECT COUNT(*) n FROM sheet_replication_outbox o JOIN events e ON e.event_id=o.event_id WHERE e.business_date="+q(TODAY)+" AND e.event_id LIKE 'OWNER_SEED200_20260904_%' AND o.status='INFLIGHT' AND o.claimed_at IS NOT NULL AND o.claimed_at>"+q(cutoff))[0]['n'])
 if fresh: raise RuntimeError(f'FRESH_INFLIGHT_PRESENT:{fresh}')
 now=datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
 sql="UPDATE sheet_replication_outbox SET status='RETRY',claim_token=NULL,claimed_at=NULL,next_attempt_at="+q(now)+",last_error_class='STALE_INFLIGHT_RECOVERED',last_error='Owner seed200 stale claim recovery; exact event preserved' WHERE status='INFLIGHT' AND event_id IN (SELECT event_id FROM events WHERE business_date="+q(TODAY)+" AND event_id LIKE 'OWNER_SEED200_20260904_%');"
 d1(sql)
 after=d1("SELECT o.status,COUNT(*) n FROM sheet_replication_outbox o JOIN events e ON e.event_id=o.event_id WHERE e.business_date="+q(TODAY)+" AND e.event_id LIKE 'OWNER_SEED200_20260904_%' GROUP BY o.status ORDER BY o.status")
 retry=sum(int(x['n']) for x in after if x['status']=='RETRY')
 if retry!=200: raise RuntimeError(f'RECOVERY_POSTCONDITION:{after}')
 result={'status':'PASS','operation':'OWNER_SEED200_STALE_OUTBOX_RECOVERY','business_date':TODAY,'authority':a,'before':rows,'after':after,'recovered':200,'stable_write_attempts':0}
 OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'status':'PASS','recovered':200,'after':after},ensure_ascii=False))
except Exception as e:
 OUT.write_text(json.dumps({'status':'FAIL','operation':'OWNER_SEED200_STALE_OUTBOX_RECOVERY','error':str(e)[:1200],'stable_write_attempts':0},ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print('RECOVERY_ERROR:'+str(e),file=sys.stderr); sys.exit(1)
