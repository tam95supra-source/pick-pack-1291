#!/usr/bin/env python3
import json,os,pathlib,sqlite3,subprocess,sys,hashlib
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=pathlib.Path('/tmp/beta-today-backup.json');RECEIPT=pathlib.Path('/tmp/beta-today-backup-receipt.json');TODAY=datetime.now(ZoneInfo('Asia/Bangkok')).strftime('%Y-%m-%d');D1=''
def q(s):return "'"+str(s).replace("'","''")+"'"
def need(n):
 v=os.environ.get(n,'').strip()
 if not v:raise RuntimeError('MISSING:'+n)
 return v
def d1(sql):
 p=subprocess.run(['npx','wrangler','d1','execute',D1,'--remote','--command',sql,'--json'],cwd=str(ROOT/'service'),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=os.environ.copy(),timeout=120)
 if p.returncode:raise RuntimeError('D1:'+p.stderr[-500:].replace('\n',' '))
 j=json.loads(p.stdout)
 if not j or j[0].get('success') is not True:raise RuntimeError('D1_NOT_SUCCESS')
 return j[0].get('results') or []
def checksum(rows):return hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def rec(status,**x):
 r={'project':'APK PICK PACK 1291','channel':'BETA','operation':'BACKUP_TODAY_BEFORE_OWNER_RESET','business_date':TODAY,'status':status,'recorded_at_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z')};r.update(x);RECEIPT.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
try:
 if TODAY!='2026-09-04':raise RuntimeError('DATE_FENCE')
 need('CLOUDFLARE_API_TOKEN');cfg=json.loads((ROOT/'config/environment_contracts.json').read_text());b=cfg['environments']['BETA'];s=cfg['environments']['STABLE']
 if b.get('lifecycle')!='LIVE' or s.get('lifecycle')=='LIVE':raise RuntimeError('ENV_GUARD')
 D1=b['current_service']['d1_database'];auth=d1('SELECT authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state WHERE singleton_id=1;')[0]
 if auth['mode']!='SERVICE_PRIMARY' or auth['scope']!='PRODUCTION':raise RuntimeError('AUTHORITY_GUARD')
 queries={
 'events':f'SELECT * FROM events WHERE business_date={q(TODAY)} ORDER BY authority_epoch,authority_seq',
 'attendance_sessions':f'SELECT * FROM attendance_sessions WHERE business_date={q(TODAY)} ORDER BY mnv',
 'labor_sessions':f'SELECT * FROM labor_sessions WHERE business_date={q(TODAY)} ORDER BY mnv,labor_id',
 'resource_leases':f'SELECT * FROM resource_leases WHERE business_date={q(TODAY)} ORDER BY resource_type,resource_id',
 'resource_daily_consumption':f'SELECT * FROM resource_daily_consumption WHERE business_date={q(TODAY)} ORDER BY resource_type,resource_id',
 'historical_session_snapshots':f'SELECT * FROM historical_session_snapshots WHERE business_date={q(TODAY)} ORDER BY mnv,session_id',
 'post_meal_attendance':f'SELECT * FROM post_meal_attendance WHERE business_date={q(TODAY)} ORDER BY mnv',
 'post_meal_attendance_audit':f'SELECT * FROM post_meal_attendance_audit WHERE business_date={q(TODAY)} ORDER BY mnv,created_at',
 'sheet_replication_outbox':f'SELECT o.* FROM sheet_replication_outbox o JOIN events e ON e.event_id=o.event_id WHERE e.business_date={q(TODAY)} ORDER BY o.outbox_id',
 'outbound_replication_outbox':f'SELECT o.* FROM outbound_replication_outbox o JOIN events e ON e.event_id=o.event_id WHERE e.business_date={q(TODAY)} ORDER BY o.outbox_id',
 'mutation_assertions':f'SELECT m.* FROM mutation_assertions m JOIN events e ON e.event_id=m.event_id WHERE e.business_date={q(TODAY)} ORDER BY m.event_id'}
 tables={k:d1(v) for k,v in queries.items()};checks={k:checksum(v) for k,v in tables.items()};counts={k:len(v) for k,v in tables.items()};doc={'schema_version':1,'project':'APK PICK PACK 1291','channel':'BETA','business_date':TODAY,'authority':auth,'tables':tables,'checksums':checks};OUT.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
 # Restore rehearsal into isolated local sqlite tables and compare canonicalized row sets.
 db=sqlite3.connect('/tmp/beta-today-restore-test.sqlite')
 try:
  for table,rows in tables.items():
   if not rows:continue
   cols=list(rows[0].keys());db.execute('CREATE TABLE "'+table+'" ('+','.join('"'+c+'"' for c in cols)+')');marks=','.join('?' for _ in cols);names=','.join('"'+c+'"' for c in cols)
   for row in rows:db.execute(f'INSERT INTO "{table}" ({names}) VALUES ({marks})',[row.get(c) for c in cols])
   got=[dict(zip(cols,x)) for x in db.execute('SELECT '+names+' FROM "'+table+'"').fetchall()]
   src=sorted(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')) for x in rows);dst=sorted(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')) for x in got)
   if src!=dst:raise RuntimeError('RESTORE_COMPARE_FAIL:'+table)
  db.commit()
 finally:db.close()
 rec('PASS',authority=auth,counts=counts,checksums=checks,restore_test='PASS',stable_write_attempts=0);print(json.dumps({'status':'PASS','counts':counts,'restore_test':'PASS'},ensure_ascii=False))
except Exception as e:
 rec('FAIL',error=str(e)[:1200],stable_write_attempts=0);print('BACKUP_ERROR:'+str(e),file=sys.stderr);sys.exit(1)
