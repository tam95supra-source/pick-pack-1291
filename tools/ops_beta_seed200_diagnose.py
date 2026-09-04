#!/usr/bin/env python3
import json, os, pathlib, re, subprocess, sys, unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=pathlib.Path('/tmp/beta-seed200-receipt.json')
TODAY=datetime.now(ZoneInfo('Asia/Bangkok')).strftime('%Y-%m-%d')
D1=''
TARGET={'Ca 1':80,'Ca 2':80,'Ca HC':40}
def q(s): return "'"+str(s).replace("'","''")+"'"
def d1(sql):
 p=subprocess.run(['npx','wrangler','d1','execute',D1,'--remote','--command',sql,'--json'],cwd=str(ROOT/'service'),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=os.environ.copy(),timeout=120)
 if p.returncode: raise RuntimeError('D1:'+p.stderr[-500:].replace('\n',' '))
 j=json.loads(p.stdout)
 if not j or j[0].get('success') is not True: raise RuntimeError('D1_NOT_SUCCESS')
 return j[0].get('results') or []
def norm(v): return ' '.join(unicodedata.normalize('NFD',str(v or '')).encode('ascii','ignore').decode().lower().replace('-',' ').split())
def cat(v):
 n=norm(v)
 if 'chuyen vien' in n:return 'SPECIALIST'
 if 'to truong' in n:return 'LEADER'
 if 'keo hang' in n:return 'PULL'
 if 'pack' in n:return 'PACK'
 if 'pick' in n:return 'PICK'
 return 'OTHER'
try:
 if TODAY!='2026-09-04': raise RuntimeError('DATE_FENCE')
 cfg=json.loads((ROOT/'config/environment_contracts.json').read_text()); b=cfg['environments']['BETA']; s=cfg['environments']['STABLE']
 if b.get('lifecycle')!='LIVE' or s.get('lifecycle')=='LIVE': raise RuntimeError('ENV_GUARD')
 D1=b['current_service']['d1_database']; a=d1('SELECT authority_epoch,mode,scope,service_generation FROM authority_state WHERE singleton_id=1;')[0]
 if a['mode']!='SERVICE_PRIMARY' or a['scope']!='PRODUCTION': raise RuntimeError('AUTHORITY_GUARD')
 attendance=d1('SELECT a.session_id,a.mnv,a.shift,a.work_choice,a.state,a.pda_serial,a.user_pick,a.pack_table,a.user_pack,a.exit_at,e.full_name,e.main_position FROM attendance_sessions a JOIN employees e ON e.mnv=a.mnv WHERE a.business_date='+q(TODAY)+' ORDER BY a.shift,a.mnv')
 labor_n=int(d1('SELECT COUNT(*) n FROM labor_sessions WHERE business_date='+q(TODAY))[0]['n'])
 meal_n=int(d1('SELECT COUNT(*) n FROM post_meal_attendance WHERE business_date='+q(TODAY))[0]['n'])
 events=d1("SELECT event_id,entity_id,authority_seq FROM events WHERE business_date="+q(TODAY)+" AND event_id LIKE 'OWNER_SEED200_20260904_%' ORDER BY authority_seq")
 seen=[]
 for x in events:
  m=re.match(r'^OWNER_SEED200_20260904_(\d{3})_',str(x.get('event_id') or ''))
  if m: seen.append(int(m.group(1)))
 missing=[i for i in range(1,201) if i not in set(seen)]
 shifts={k:sum(1 for x in attendance if x.get('shift')==k) for k in TARGET}
 works={k:sum(1 for x in attendance if x.get('work_choice')==k) for k in ('PICK','PACK','KHONG')}
 core={}; core_people={}
 for sh in TARGET:
  rows=[x for x in attendance if x.get('shift')==sh]
  cats=[cat(x.get('main_position')) for x in rows]
  core[sh]={'SPECIALIST':cats.count('SPECIALIST'),'LEADER':cats.count('LEADER'),'PULL':cats.count('PULL'),'PICK_ROLE':cats.count('PICK'),'PACK_ROLE':cats.count('PACK')}
  core_people[sh]={k:[{'mnv':x.get('mnv'),'name':x.get('full_name'),'position':x.get('main_position')} for x in rows if cat(x.get('main_position'))==k] for k in ('SPECIALIST','LEADER','PULL')}
 active=sum(1 for x in attendance if x.get('state')=='ACTIVE' and x.get('exit_at') in (None,''))
 res={'PDA':sorted({str(x.get('pda_serial')) for x in attendance if x.get('pda_serial')}),'USER_PICK':sorted({str(x.get('user_pick')) for x in attendance if x.get('user_pick')}),'PACK_TABLE':sorted({str(x.get('pack_table')) for x in attendance if x.get('pack_table')}),'USER_PACK':sorted({str(x.get('user_pack')) for x in attendance if x.get('user_pack')})}
 outbox=d1("SELECT status,COUNT(*) n,MIN(outbox_id) min_id,MAX(outbox_id) max_id FROM sheet_replication_outbox GROUP BY status ORDER BY status")
 seed_outbox=d1("SELECT o.status,COUNT(*) n FROM sheet_replication_outbox o JOIN events e ON e.event_id=o.event_id WHERE e.business_date="+q(TODAY)+" AND e.event_id LIKE 'OWNER_SEED200_20260904_%' GROUP BY o.status ORDER BY o.status")
 pending_seed=int(d1("SELECT COUNT(*) n FROM sheet_replication_outbox o JOIN events e ON e.event_id=o.event_id WHERE e.business_date="+q(TODAY)+" AND e.event_id LIKE 'OWNER_SEED200_20260904_%' AND o.status IN ('PENDING','RETRY','INFLIGHT')")[0]['n'])
 due_seed=int(d1("SELECT COUNT(*) n FROM sheet_replication_outbox o JOIN events e ON e.event_id=o.event_id WHERE e.business_date="+q(TODAY)+" AND e.event_id LIKE 'OWNER_SEED200_20260904_%' AND o.status IN ('PENDING','RETRY') AND o.next_attempt_at<=strftime('%Y-%m-%dT%H:%M:%fZ','now')")[0]['n'])
 errors=d1("SELECT status,last_error_class,last_error,attempt_count,COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT') GROUP BY status,last_error_class,last_error,attempt_count ORDER BY n DESC LIMIT 10")
 rs=d1("SELECT target_kind,state,checkpoint,pending_count,retry_count,last_attempt_at,last_success_at,last_error_class,last_error,updated_at FROM replication_status WHERE singleton_id=1")
 ok=(len(attendance)==200 and active==200 and labor_n==0 and len(events)==200 and not missing and shifts==TARGET and works=={'PICK':3,'PACK':3,'KHONG':194} and all(core[sh]['SPECIALIST']==1 and core[sh]['LEADER']==1 and core[sh]['PULL']==3 and core[sh]['PICK_ROLE']>=1 and core[sh]['PACK_ROLE']>=1 for sh in TARGET) and all(len(res[k])==3 for k in res))
 result={'project':'APK PICK PACK 1291','channel':'BETA','operation':'OWNER_SEED_200_FULL_DIAGNOSE','business_date':TODAY,'status':'PASS' if ok else 'FAIL','authority':a,'attendance_count':len(attendance),'active_count':active,'labor_count':labor_n,'post_meal_count':meal_n,'owner_seed_event_count':len(events),'missing_seed_indices':missing,'shift_distribution':shifts,'work_choice_distribution':works,'core_composition':core,'core_people':core_people,'unique_resources':res,'outbox_by_status':outbox,'seed_outbox_by_status':seed_outbox,'seed_pending':pending_seed,'seed_due':due_seed,'pending_error_groups':errors,'replication_status':rs[0] if rs else {},'stable_write_attempts':0}
 OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'status':result['status'],'attendance':len(attendance),'active':active,'labor':labor_n,'meal':meal_n,'seed_events':len(events),'missing':missing,'shift':shifts,'work':works,'core':core,'resources':{k:len(v) for k,v in res.items()},'seed_outbox':seed_outbox,'seed_pending':pending_seed,'seed_due':due_seed,'replication_status':result['replication_status'],'errors':errors},ensure_ascii=False))
 if not ok: sys.exit(1)
except Exception as e:
 OUT.write_text(json.dumps({'project':'APK PICK PACK 1291','channel':'BETA','operation':'OWNER_SEED_200_FULL_DIAGNOSE','business_date':TODAY,'status':'FAIL','error':str(e)[:1200],'stable_write_attempts':0},ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print('DIAG_ERROR:'+str(e),file=sys.stderr); sys.exit(1)
