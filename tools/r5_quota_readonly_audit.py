#!/usr/bin/env python3
"""Bounded read-only audit. No deploy, migration, business mutation or load test."""
import os,json,re,hashlib
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from urllib.parse import quote,urlencode
OUT=Path('/tmp/r5-quota-readonly-audit');OUT.mkdir(parents=True,exist_ok=True)
now=datetime.now(timezone.utc); today=now.date().isoformat()
account=os.environ['CLOUDFLARE_ACCOUNT_ID'];token=os.environ['CLOUDFLARE_API_TOKEN']
base='https://api.cloudflare.com/client/v4/accounts/'+account
calls=0;d1reads=0;d1writes=0
result={'captured_at':now.isoformat(),'source_sha':os.environ.get('GITHUB_SHA'),'kind':'BOUNDED_READ_ONLY_AUDIT','live_deployments':0,'load_test_mutations':0,'limitations':[]}
def http(url,auth=None,body=None,form=None):
 global calls
 if calls>=45: return {'ok':False,'error':'AUDIT_HTTP_BUDGET_STOP'}
 calls+=1
 headers={'Accept':'application/json'}
 if auth: headers['Authorization']='Bearer '+auth
 data=None
 if body is not None:data=json.dumps(body).encode();headers['Content-Type']='application/json'
 if form is not None:data=urlencode(form).encode();headers['Content-Type']='application/x-www-form-urlencoded'
 try:
  with urlopen(Request(url,headers=headers,data=data,method='POST' if data else 'GET'),timeout=15) as resp:
   b=resp.read(2000000);j=json.loads(b)
  if isinstance(j,dict) and (j.get('success') is False or j.get('errors')):return {'ok':False,'errors':[str(x.get('message',''))[:180] for x in j.get('errors',[]) if isinstance(x,dict)]}
  return {'ok':True,'data':j}
 except HTTPError as e:return {'ok':False,'http_status':e.code}
 except (URLError,TimeoutError,ValueError):return {'ok':False,'error':'TRANSPORT_OR_NON_JSON'}
def cf(path):return http(base+path,token)
def payload(r):return r.get('data',{}).get('result')
def safe_error(r):return {k:v for k,v in r.items() if k!='data'}
def gql(query,variables):
 r=http('https://api.cloudflare.com/client/v4/graphql',token,{'query':query,'variables':variables})
 if not r.get('ok'):return safe_error(r)
 accounts=r['data'].get('data',{}).get('viewer',{}).get('accounts',[])
 return {'ok':bool(accounts),'data':accounts[0] if accounts else {}}
subs=cf('/subscriptions'); settings=cf('/workers/account-settings')
result['plan']={'subscriptions_read':safe_error(subs),'settings_read':safe_error(settings),'default_usage_model':(payload(settings) or {}).get('default_usage_model'),'subscriptions':[]}
for s in payload(subs) or []:
 p=s.get('rate_plan') or {}
 result['plan']['subscriptions'].append({'plan_id':p.get('id'),'public_name':p.get('public_name'),'scope':p.get('scope'),'state':s.get('state'),'price':s.get('price')})
dbs=cf('/d1/database?per_page=100')
dbrows=payload(dbs) or []
dbmap={x.get('uuid',x.get('id')):x.get('name') for x in dbrows}
result['d1_inventory']={'read':safe_error(dbs),'count':len(dbrows),'databases':[]}
for d in dbrows[:12]:
 ident=d.get('uuid',d.get('id'));info=cf('/d1/database/'+quote(ident,safe=''));x=payload(info) or {}
 result['d1_inventory']['databases'].append({'name':d.get('name'),'id':ident,'file_size':x.get('file_size'),'version':x.get('version'),'read':safe_error(info)})
q='query($accountTag:string!,$start:Date,$end:Date){viewer{accounts(filter:{accountTag:$accountTag}){d1AnalyticsAdaptiveGroups(limit:1000,filter:{date_geq:$start,date_leq:$end}){sum{rowsRead rowsWritten readQueries writeQueries} dimensions{date databaseId}}}}}'
result['d1_daily_analytics']=gql(q,{'accountTag':account,'start':(now-timedelta(days=1)).date().isoformat(),'end':today})
r=result['d1_daily_analytics']
if r.get('ok'):
 for row in r['data'].get('d1AnalyticsAdaptiveGroups',[]):row['database_name']=dbmap.get(row.get('dimensions',{}).get('databaseId'),'UNRESOLVED')
q='query($accountTag:string,$start:string,$end:string){viewer{accounts(filter:{accountTag:$accountTag}){workersInvocationsAdaptive(limit:1000,filter:{datetime_geq:$start,datetime_leq:$end}){sum{requests subrequests errors} quantiles{cpuTimeP50 cpuTimeP99} dimensions{scriptName}}}}}'
result['workers_utc_today']=gql(q,{'accountTag':account,'start':today+'T00:00:00Z','end':now.isoformat().replace('+00:00','Z')})
result['workers']=[]
for name in ['pickpack','pickpack1291-stable-private']:
 sr=cf('/workers/scripts/'+name+'/settings');s=payload(sr) or {};bindings=s.get('bindings',[])
 vars={b.get('name'):b.get('text',b.get('value')) for b in bindings if b.get('type')=='plain_text'}
 did=next((b.get('id',b.get('database_id')) for b in bindings if b.get('name')=='DB' and 'd1' in b.get('type','').lower()),None)
 record={'name':name,'settings_read':safe_error(sr),'environment_id':vars.get('ENVIRONMENT_ID'),'audience':vars.get('SERVICE_AUDIENCE'),'generation':vars.get('SERVICE_GENERATION'),'d1_id':did,'d1_name':dbmap.get(did),'usage_model':s.get('usage_model'),'limits':s.get('limits'),'observability':s.get('observability'),'has_realtime_hub':any(b.get('name')=='REALTIME_HUB' for b in bindings),'sheet_ids':{k:vars.get(k) for k in ['GOOGLE_SOURCE_SHEET_ID','GOOGLE_OUTBOUND_SHEET_ID'] if vars.get(k)}}
 schedules=cf('/workers/scripts/'+name+'/schedules');record['schedules']=payload(schedules) if schedules.get('ok') else safe_error(schedules)
 deploy=cf('/workers/scripts/'+name+'/deployments');dv=payload(deploy) or {}
 ds=dv if isinstance(dv,list) else dv.get('deployments',[])
 record['deployments']=[{k:d.get(k) for k in ['id','created_on','source','strategy','versions']} for d in ds[:3]] if deploy.get('ok') else safe_error(deploy)
 result['workers'].append(record)
 if did and d1reads<300 and name=='pickpack':
  def readsql(label,sql,params=None):
   global d1reads,d1writes
   assert sql.lstrip().upper().startswith('SELECT') and ';' not in sql
   if d1reads>=300:return {'ok':False,'reason':'READ_BUDGET_STOP'}
   rr=http(base+'/d1/database/'+did+'/query',token,{'sql':sql,'params':params or []})
   if not rr.get('ok'):return safe_error(rr)
   groups=payload(rr) or [];out=[]
   for g in groups:
    m=g.get('meta',{}); d1reads+=int(m.get('rows_read',0)); d1writes+=int(m.get('rows_written',0))
    out.append({'results':g.get('results',[]),'meta':{k:m.get(k) for k in ['rows_read','rows_written','duration','size_after']}})
   if d1writes:raise RuntimeError('UNEXPECTED_D1_WRITE')
   return {'ok':True,'data':out}
  record['authority']=readsql('authority','SELECT authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state WHERE singleton_id=1')
  record['r5_tables']=readsql('schema',"SELECT name FROM sqlite_master WHERE type='table' AND name IN ('day_revision_state','quota_policy','quota_usage','push_wake_outbox','session_special_projection_outbox')")
  table_names={x['name'] for g in record['r5_tables'].get('data',[]) for x in g['results']}
  if 'quota_policy' in table_names:record['quota_policy']=readsql('policy','SELECT metric,hard_limit,unit FROM quota_policy ORDER BY metric LIMIT 16')
  if 'quota_usage' in table_names:record['quota_today']=readsql('usage','SELECT metric,used,hard_limit,updated_at FROM quota_usage WHERE window_key=? ORDER BY metric LIMIT 16',['D:'+today])
  filter={'AND':[{'datetimeHour_geq':today+'T00:00:00Z','datetimeHour_leq':now.isoformat().replace('+00:00','Z'),'databaseId':did}]}
  for sort in ['rowsRead','rowsWritten']:
   query='query($accountTag:string,$filter:ZoneWorkersRequestsFilter_InputObject){viewer{accounts(filter:{accountTag:$accountTag}){d1QueriesAdaptiveGroups(limit:8,filter:$filter,orderBy:[sum_'+sort+'_DESC]){sum{queryDurationMs rowsRead rowsWritten rowsReturned} count dimensions{query}}}}}'
   qr=gql(query,{'accountTag':account,'filter':filter})
   if qr.get('ok'):
    for row in qr['data'].get('d1QueriesAdaptiveGroups',[]):
     raw=row.get('dimensions',{}).get('query','');row['query_sha256']=hashlib.sha256(raw.encode()).hexdigest()
     row['dimensions']['query']=re.sub(r"'(?:''|[^'])*'","'?'",raw)[:1200]
   record['top_'+sort]=qr
health=http('https://pickpack.1291.workers.dev/health')
result['beta_health']=safe_error(health)
if health.get('ok'):
 h=health['data'];result['beta_health']['data']={k:h.get(k) for k in ['ok','environment','environment_id','service_audience','generation','version','source_sha']}
 result['beta_health']['data']['authority']={k:(h.get('authority') or {}).get(k) for k in ['authority_epoch','authority_seq','mode','scope','service_generation']}
# API metadata only for Google; no spreadsheet values fetched.
form={k:os.environ.get(v,'') for k,v in [('client_id','GOOGLE_OAUTH_CLIENT_ID'),('client_secret','GOOGLE_OAUTH_CLIENT_SECRET'),('refresh_token','GOOGLE_OAUTH_REFRESH_TOKEN')]}
result['google']={'usage_metrics':'NOT_AVAILABLE_FROM_SHEETS_METADATA','billing_state':'NOT_VERIFIED','sheets':[]}
if all(form.values()):
 form['grant_type']='refresh_token';oauth=http('https://oauth2.googleapis.com/token',form=form)
 if oauth.get('ok') and oauth['data'].get('access_token'):
  access=oauth['data']['access_token']
  contracts=json.loads(Path('config/environment_contracts.json').read_text())
  ids={e['gsheet']['spreadsheet_id'] for e in contracts['environments'].values()}
  ids.update(v for w in result['workers'] for v in w['sheet_ids'].values())
  for sid in sorted(ids)[:4]:
   meta=http('https://sheets.googleapis.com/v4/spreadsheets/'+quote(sid,safe='')+'?fields=spreadsheetId,properties(title),sheets(properties(title,gridProperties(rowCount,columnCount)))',access)
   sheet={'spreadsheet_id':sid,'read':safe_error(meta)}
   if meta.get('ok'):
    v=meta['data'];sheet['title']=v.get('properties',{}).get('title');sheet['tab_count']=len(v.get('sheets',[]))
    sheet['allocated_cells']=sum(x.get('properties',{}).get('gridProperties',{}).get('rowCount',0)*x.get('properties',{}).get('gridProperties',{}).get('columnCount',0) for x in v.get('sheets',[]))
   result['google']['sheets'].append(sheet)
  drive=http('https://www.googleapis.com/drive/v3/about?fields=storageQuota',access)
  result['google']['drive_storage']=drive.get('data',{}).get('storageQuota') if drive.get('ok') else safe_error(drive)
 else:result['google']['oauth']=safe_error(oauth)
# Passive DR inventory through provider control APIs; never wake hosted DR apps.
result['dr']={}
for provider,url,key in [('render','https://api.render.com/v1/services?limit=100&includePreviews=false','RENDER_API_KEY'),('deno','https://api.deno.com/v2/apps?limit=100','DENO_DEPLOY_TOKEN')]:
 t=os.environ.get(key)
 if not t:result['dr'][provider]={'ok':False,'reason':'CREDENTIAL_NOT_EXPOSED'};continue
 rr=http(url,t);v=rr.get('data',[])
 if not rr.get('ok'):result['dr'][provider]=safe_error(rr);continue
 rows=v if isinstance(v,list) else v.get('items',v.get('apps',[]))
 safe=[]
 for x in rows:
  x=x.get('service',x);name=str(x.get('name',x.get('slug','')))
  if '1291' not in name or ('pick' not in name and 'pp1291' not in name):continue
  details=x.get('serviceDetails',{})
  safe.append({'name':name,'plan':details.get('plan',x.get('plan')),'region':details.get('region'),'suspended':x.get('suspended'),'autoDeploy':x.get('autoDeploy')})
 result['dr'][provider]={'ok':True,'items':safe,'usage':'NOT_VERIFIED'}
t=os.environ.get('TURSO_API_TOKEN')
if t:
 rr=http('https://api.turso.tech/v1/organizations',t);v=rr.get('data',[])
 rows=v if isinstance(v,list) else v.get('organizations',[])
 result['dr']['turso']={'read':safe_error(rr),'organization_count':len(rows),'usage':'NOT_VERIFIED'}
 if rr.get('ok') and len(rows)==1:
  org=rows[0].get('slug',rows[0].get('name',''))
  dd=http('https://api.turso.tech/v1/organizations/'+quote(org,safe='')+'/databases?limit=100',t)
  v=dd.get('data',{});rows=v if isinstance(v,list) else v.get('databases',[])
  result['dr']['turso']['databases']=[{k:d.get(k) for k in ['Name','name','group','primaryRegion','primary_region']} for d in rows if '1291' in str(d.get('Name',d.get('name','')))]
result['audit_cost']={'http_calls':calls,'http_budget':45,'direct_d1_rows_read':d1reads,'direct_d1_rows_written':d1writes,'note':'Control API/Analytics reads are not D1 business queries; one health request may perform additional bounded reads not counted in direct query meta.'}
result['limitations']+=['Analytics can lag and may use adaptive sampling; no attribution of all daily usage to AI without a separate run ledger.','No runtime load, UI/frame, full-day, failure injection or Stable deployment performed.','Google/DR metadata does not establish daily usage or billing status.']
OUT.joinpath('receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('R5_READONLY_AUDIT_JSON='+json.dumps(result,ensure_ascii=False,separators=(',',':')))
