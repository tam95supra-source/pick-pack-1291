#!/usr/bin/env python3
import base64,hashlib,hmac,json,os,pathlib,random,subprocess,sys,unicodedata,urllib.error,urllib.request
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=pathlib.Path('/tmp/beta-seed200-receipt.json');TODAY=datetime.now(ZoneInfo('Asia/Bangkok')).strftime('%Y-%m-%d');D1='';LOGIN=''
TARGET={'Ca 1':80,'Ca 2':80,'Ca HC':40}
def q(s):return "'"+str(s).replace("'","''")+"'"
def need(n):
 v=os.environ.get(n,'').strip()
 if not v:raise RuntimeError('MISSING:'+n)
 return v
def d1(sql):
 p=subprocess.run(['npx','wrangler','d1','execute',D1,'--remote','--command',sql,'--json'],cwd=str(ROOT/'service'),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=os.environ.copy(),timeout=120)
 if p.returncode:raise RuntimeError('D1:'+p.stderr[-400:].replace('\n',' '))
 j=json.loads(p.stdout)
 if not j or j[0].get('success') is not True:raise RuntimeError('D1_NOT_SUCCESS')
 return j[0].get('results') or []
def norm(v):return ' '.join(unicodedata.normalize('NFD',str(v or '')).encode('ascii','ignore').decode().lower().replace('-',' ').split())
def cat(p):
 n=norm(p)
 if 'chuyen vien' in n:return 'SPECIALIST'
 if 'to truong' in n:return 'LEADER'
 if 'keo hang' in n:return 'PULL'
 if 'pack' in n:return 'PACK'
 if 'pick' in n:return 'PICK'
 return 'OTHER'
def b64u(b):return base64.urlsafe_b64encode(b).rstrip(b'=').decode()
def http(url,method='GET',token=None,body=None,timeout=45):
 h={'Accept':'application/json','X-Pick-Pack-Environment':'BETA','X-Pick-Pack-Audience':'PICK_PACK_1291_BETA'}
 if token:h['Authorization']='Bearer '+token
 data=None
 if body is not None:h['Content-Type']='application/json';data=json.dumps(body,ensure_ascii=False,separators=(',',':')).encode()
 req=urllib.request.Request(url,data=data,headers=h,method=method)
 try:
  with urllib.request.urlopen(req,timeout=timeout) as r:return r.status,json.loads(r.read().decode() or '{}')
 except urllib.error.HTTPError as e:
  try:j=json.loads(e.read().decode())
  except Exception:j={}
  return e.code,j
def must(url,method='GET',token=None,body=None,timeout=60):
 c,j=http(url,method,token,body,timeout)
 if c//100!=2 or j.get('ok') is not True:raise RuntimeError('SERVICE:'+str(c)+':'+str(j.get('error') or j)[:500])
 return j
def rec(status,**x):
 r={'project':'APK PICK PACK 1291','channel':'BETA','operation':'OWNER_SEED_200_AFTER_CLEAN','business_date':TODAY,'status':status,'requested_count':200,'stable_write_attempts':0};r.update(x);OUT.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def cleanup():
 global LOGIN
 if LOGIN:
  try:d1("DELETE FROM auth_sessions WHERE login_id="+q(LOGIN)+"; DELETE FROM auth_web_sessions WHERE login_id="+q(LOGIN)+"; DELETE FROM auth_challenges WHERE login_id="+q(LOGIN)+"; DELETE FROM accounts WHERE login_id="+q(LOGIN)+";")
  except Exception:pass
  LOGIN=''
try:
 if TODAY!='2026-09-04':raise RuntimeError('DATE_FENCE')
 account=need('CLOUDFLARE_ACCOUNT_ID');secret2=need('GOOGLE_OAUTH_CLIENT_SECRET');need('CLOUDFLARE_API_TOKEN')
 cfg=json.loads((ROOT/'config/environment_contracts.json').read_text());b=cfg['environments']['BETA'];s=cfg['environments']['STABLE']
 if b.get('lifecycle')!='LIVE' or s.get('lifecycle')=='LIVE':raise RuntimeError('ENV_GUARD')
 D1=b['current_service']['d1_database'];url=b['current_service']['url'].rstrip('/')
 a=d1('SELECT authority_epoch,mode,scope,service_generation FROM authority_state WHERE singleton_id=1;')[0]
 if a['mode']!='SERVICE_PRIMARY' or a['scope']!='PRODUCTION':raise RuntimeError('AUTHORITY_GUARD')
 # Hard precondition: owner-requested cleanup must already be complete before any seed write.
 for t in ('attendance_sessions','labor_sessions','post_meal_attendance'):
  if int(d1('SELECT COUNT(*) n FROM '+t+' WHERE business_date='+q(TODAY))[0]['n'])!=0:raise RuntimeError('CLEANUP_REQUIRED:'+t)
 rows=d1('SELECT mnv,full_name,main_position,supplier FROM employees ORDER BY mnv');rows=[dict(x,cat=cat(x.get('main_position'))) for x in rows if str(x.get('mnv') or '').strip() and not str(x.get('mnv')).startswith('__')]
 if len(rows)<200:raise RuntimeError('EMPLOYEE_LT_200')
 rng=random.Random('OWNER_200|'+TODAY);rng.shuffle(rows);used=set();plan=[]
 pools={k:[x for x in rows if x['cat']==k] for k in ('SPECIALIST','LEADER','PULL','PICK','PACK')}
 for v in pools.values():rng.shuffle(v)
 def take(k,n):
  out=[]
  while pools[k] and len(out)<n:
   x=pools[k].pop()
   if x['mnv'] not in used:used.add(x['mnv']);out.append(x)
  if len(out)!=n:raise RuntimeError('POSITION_SHORT:'+k)
  return out
 for shift,n in TARGET.items():
  specialist=take('SPECIALIST',1);leader=take('LEADER',1);pull=take('PULL',3);pick=take('PICK',1);pack=take('PACK',1)
  crew=specialist+leader+pull+pick+pack
  fill=[x for x in rows if x['mnv'] not in used and x['cat'] not in ('SPECIALIST','LEADER','PULL')];rng.shuffle(fill);fill=fill[:n-7]
  if len(fill)!=n-7:raise RuntimeError('FILL_SHORT')
  for x in fill:used.add(x['mnv'])
  for x in crew+fill:
   work='PICK' if x['mnv']==pick[0]['mnv'] else ('PACK' if x['mnv']==pack[0]['mnv'] else 'KHONG')
   plan.append(dict(x,shift=shift,work_choice=work))
 if len(plan)!=200 or len({x['mnv'] for x in plan})!=200:raise RuntimeError('PLAN_NOT_200')
 # Give the designated PICK/PACK employees real unique resources for each shift.
 pdas=[x['resource_id'] for x in d1("SELECT resource_id FROM resources WHERE resource_type='PDA' AND available=1 ORDER BY resource_id")]
 picks=[x['resource_id'] for x in d1("SELECT resource_id FROM resources WHERE resource_type='USER_PICK' AND available=1 ORDER BY resource_id")]
 packs=d1("SELECT rpm.shift,rpm.pack_table,rpm.user_pack FROM resource_pack_map rpm JOIN resources t ON t.resource_type='PACK_TABLE' AND t.resource_id=rpm.pack_table AND t.available=1 JOIN resources p ON p.resource_type='USER_PACK' AND p.resource_id=rpm.user_pack AND p.available=1 WHERE rpm.available=1 ORDER BY rpm.shift,rpm.pack_table")
 by={k:[x for x in packs if str(x.get('shift'))==k] for k in TARGET}
 if len(pdas)<3 or len(picks)<3 or any(not by[k] for k in TARGET):raise RuntimeError('RESOURCE_CAPACITY')
 resource_used={'PDA':[],'USER_PICK':[],'PACK_PAIR':[]}
 for shift in TARGET:
  pick_emp=next(x for x in plan if x['shift']==shift and x['work_choice']=='PICK');pack_emp=next(x for x in plan if x['shift']==shift and x['work_choice']=='PACK')
  pick_emp['pda_serial']=pdas.pop(0);pick_emp['user_pick']=picks.pop(0);pair=by[shift][0];pack_emp['pack_table']=pair['pack_table'];pack_emp['user_pack']=pair['user_pack']
  resource_used['PDA'].append(pick_emp['pda_serial']);resource_used['USER_PICK'].append(pick_emp['user_pick']);resource_used['PACK_PAIR'].append({'shift':shift,'pack_table':pack_emp['pack_table'],'user_pack':pack_emp['user_pack']})
 suffix=hashlib.sha256((os.environ.get('GITHUB_RUN_ID','run')+os.environ.get('GITHUB_RUN_ATTEMPT','1')).encode()).hexdigest()[:12];LOGIN='__OWNER_SEED200_'+suffix;dev='__OWNER_SEED200_DEV_'+suffix;sess='__OWNER_SEED200_AUTH_'+suffix;vh='owner_seed200_'+suffix;now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
 d1("INSERT INTO accounts(login_id,verifier,verifier_hash,role,display_name,position,email,status,source_row,source_checksum,is_shadow_test) VALUES("+q(LOGIN)+",'fixture',"+q(vh)+",'SUPERADMIN','OWNER seed200','TEST','','ACTIVE',-32001,'seed200',1); INSERT INTO auth_sessions(login_id,session_id,device_id,issued_at) VALUES("+q(LOGIN)+","+q(sess)+","+q(dev)+","+q(now)+");")
 sec=hashlib.sha256((account+'|'+secret2+'|pick-pack-1291-m2-service-token-v1').encode()).hexdigest();payload={'l':LOGIN,'r':'SUPERADMIN','v':vh,'s':sess,'d':dev,'c':'PDA'};enc=b64u(json.dumps(payload,separators=(',',':')).encode());token=enc+'.'+b64u(hmac.new(sec.encode(),enc.encode(),hashlib.sha256).digest())
 ev=[]
 for i,x in enumerate(plan,1):
  p={'mnv':x['mnv'],'shift':x['shift'],'work_choice':x['work_choice'],'note':'OWNER TEST 200'}
  for k in ('pda_serial','user_pick','pack_table','user_pack'):
   if x.get(k):p[k]=x[k]
  ev.append({'action':'enter','event_id':f'OWNER_SEED200_{TODAY.replace("-","")}_{i:03d}_{x["mnv"]}','device_id':'OWNER_SEED200','business_date':TODAY,'payload':p})
 confirmed=0
 for i in range(0,200,25):
  j=must(url+'/v1/legacy-mutations/batch','POST',token,{'events':ev[i:i+25]},120);rs=j.get('results') or []
  if len(rs)!=len(ev[i:i+25]) or any(x.get('status') not in ('CONFIRMED','DUPLICATE') for x in rs):raise RuntimeError('BATCH_REJECT')
  confirmed+=sum(1 for x in rs if x.get('status')=='CONFIRMED')
 final=d1('SELECT a.mnv,a.shift,a.work_choice,a.state,a.exit_at,e.main_position FROM attendance_sessions a JOIN employees e ON e.mnv=a.mnv WHERE a.business_date='+q(TODAY))
 if len(final)!=200 or any(x['state']!='ACTIVE' or x.get('exit_at') not in (None,'') for x in final):raise RuntimeError('READBACK_200_FAIL')
 shifts={k:sum(1 for x in final if x['shift']==k) for k in TARGET};works={k:sum(1 for x in final if x['work_choice']==k) for k in ('PICK','PACK','KHONG')}
 if shifts!=TARGET or works!={'PICK':3,'PACK':3,'KHONG':194}:raise RuntimeError('DISTRIBUTION_FAIL')
 core={}
 for sh in TARGET:
  cats=[cat(x['main_position']) for x in final if x['shift']==sh];core[sh]={'SPECIALIST':cats.count('SPECIALIST'),'LEADER':cats.count('LEADER'),'PULL':cats.count('PULL'),'PICK_ROLE':cats.count('PICK'),'PACK_ROLE':cats.count('PACK')}
  if core[sh]['SPECIALIST']!=1 or core[sh]['LEADER']!=1 or core[sh]['PULL']!=3 or core[sh]['PICK_ROLE']<1 or core[sh]['PACK_ROLE']<1:raise RuntimeError('CORE_FAIL:'+sh)
 cleanup();rec('PASS',confirmed=confirmed,active=200,shift_distribution=shifts,work_choice_distribution=works,core_composition=core,resource_used=resource_used,d1_readback='PASS',stable_unchanged=True);print(json.dumps({'status':'PASS','active':200,'shift':shifts,'work':works,'core':core},ensure_ascii=False))
except Exception as e:
 cleanup();rec('FAIL',error=str(e)[:1200],stable_unchanged=True);print('SEED200_ERROR:'+str(e),file=sys.stderr);sys.exit(1)
