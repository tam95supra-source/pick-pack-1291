#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=pathlib.Path('/tmp/beta-seed200-receipt.json')
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
 cfg=json.loads((ROOT/'config/environment_contracts.json').read_text())
 b=cfg['environments']['BETA']; s=cfg['environments']['STABLE']
 if b.get('lifecycle')!='LIVE' or s.get('lifecycle')=='LIVE': raise RuntimeError('ENV_GUARD')
 D1=b['current_service']['d1_database']
 a=d1('SELECT authority_epoch,mode,scope,service_generation FROM authority_state WHERE singleton_id=1;')[0]
 if a['mode']!='SERVICE_PRIMARY' or a['scope']!='PRODUCTION': raise RuntimeError('AUTHORITY_GUARD')
 counts={}
 for t in ('attendance_sessions','labor_sessions','post_meal_attendance'):
  counts[t]=int(d1('SELECT COUNT(*) n FROM '+t+' WHERE business_date='+q(TODAY))[0]['n'])
 events=d1("SELECT event_id,event_type,entity_id,authority_seq,payload_json FROM events WHERE business_date="+q(TODAY)+" AND event_id LIKE 'OWNER_SEED200_20260904_%' ORDER BY authority_seq")
 attendance=d1('SELECT session_id,mnv,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,enter_at,exit_at FROM attendance_sessions WHERE business_date='+q(TODAY)+' ORDER BY mnv')
 event_entities={str(x.get('entity_id') or '') for x in events}
 attendance_ids={str(x.get('session_id') or '') for x in attendance}
 owner_only=(len(attendance_ids-event_entities)==0)
 statuses={}
 for x in events: statuses[x.get('event_type','UNKNOWN')]=statuses.get(x.get('event_type','UNKNOWN'),0)+1
 result={
  'project':'APK PICK PACK 1291','channel':'BETA','operation':'OWNER_SEED_200_PARTIAL_DIAGNOSE','business_date':TODAY,'status':'PASS',
  'authority':a,'counts':counts,'owner_seed_event_count':len(events),'owner_seed_event_types':statuses,
  'attendance_count':len(attendance),'attendance_all_backed_by_owner_seed_event_entity':owner_only,
  'attendance_without_owner_event':sorted(attendance_ids-event_entities)[:20],
  'owner_events_without_attendance_entity':sorted(event_entities-attendance_ids)[:20],
  'attendance_sample':attendance[:30],
  'owner_event_sample':[{k:v for k,v in x.items() if k!='payload_json'} for x in events[:30]],
  'stable_write_attempts':0
 }
 OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:result[k] for k in ('status','counts','owner_seed_event_count','attendance_count','attendance_all_backed_by_owner_seed_event_entity')},ensure_ascii=False))
except Exception as e:
 OUT.write_text(json.dumps({'project':'APK PICK PACK 1291','channel':'BETA','operation':'OWNER_SEED_200_PARTIAL_DIAGNOSE','business_date':TODAY,'status':'FAIL','error':str(e)[:1200],'stable_write_attempts':0},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('DIAG_ERROR:'+str(e),file=sys.stderr); sys.exit(1)
