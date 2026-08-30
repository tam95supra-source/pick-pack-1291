#!/usr/bin/env python3
import hashlib,json,os,pathlib,subprocess,sys,tempfile,urllib.parse,urllib.request,urllib.error
ROOT=pathlib.Path(__file__).resolve().parents[1]; SERVICE=ROOT/"service"; API="https://api.cloudflare.com/client/v4"
def need(n):
 v=os.environ.get(n,"").strip()
 if not v: raise RuntimeError("MISSING:"+n)
 return v
def call(path,method="GET",body=None):
 url=f"{API}/accounts/{need('CLOUDFLARE_ACCOUNT_ID')}{path}"; data=None if body is None else json.dumps(body).encode()
 r=urllib.request.Request(url,data=data,method=method,headers={"Authorization":"Bearer "+need("CLOUDFLARE_API_TOKEN"),"Content-Type":"application/json"})
 try:
  with urllib.request.urlopen(r,timeout=60) as x: j=json.loads(x.read().decode())
 except urllib.error.HTTPError as e: raise RuntimeError(f"CF_HTTP_{e.code}:{e.read().decode()[:800]}")
 if j.get("success") is not True: raise RuntimeError("CF_API:"+json.dumps(j.get("errors",[]))[:800])
 return j.get("result")
def sh(args,cwd=None):
 p=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600)
 if p.returncode: raise RuntimeError("CMD_FAIL:"+" ".join(args[:4])+":"+p.stdout[-2500:])
 return p.stdout
def dbs(): return call("/d1/database?per_page=100") or []
def workers(): return call("/workers/scripts?per_page=100") or []
def db_id(name):
 x=[d for d in dbs() if d.get("name")==name]
 if len(x)!=1: raise RuntimeError("DB_NOT_UNIQUE:"+name+":"+str(len(x)))
 return x[0].get("uuid") or x[0].get("id")
def query(db,sql):
 r=call(f"/d1/database/{db}/query","POST",{"sql":sql})
 if not isinstance(r,list) or not r: raise RuntimeError("D1_QUERY_EMPTY")
 return r[0].get("results") or []
def table_signature(db):
 tables=[r["name"] for r in query(db,"SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name") if r.get("name") and not str(r["name"]).startswith("_cf_")]
 out={}
 for t in tables:
  safe='"'+str(t).replace('"','""')+'"'
  rows=query(db,f"SELECT * FROM {safe} ORDER BY rowid")
  raw=json.dumps(rows,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
  out[t]={"count":len(rows),"sha256":hashlib.sha256(raw).hexdigest()}
 return out
def minimal_config(name,id):
 p=SERVICE/"wrangler.stable.verify.generated.jsonc"
 p.write_text(json.dumps({"name":"pp1291-stable-verify-local","compatibility_date":"2026-08-08","d1_databases":[{"binding":"DB","database_name":name,"database_id":id}]},indent=2))
 return p
def worker_settings(name):
 enc=urllib.parse.quote(name,safe=""); return call(f"/workers/scripts/{enc}/settings") or {}
def endpoint(name):
 sub=(call("/workers/subdomain") or {}).get("subdomain","")
 return f"https://{name}.{sub}.workers.dev" if sub else ""
def http_status(url,headers=None):
 r=urllib.request.Request(url,headers=headers or {})
 try:
  with urllib.request.urlopen(r,timeout=25) as x:return x.status
 except urllib.error.HTTPError as e:return e.code
def main():
 req=json.loads((ROOT/"ops/stable-private-provision-request.json").read_text()); target=req["target_d1_name"]; worker=req["target_worker_name"]
 before=dbs(); before_count=len(before); tid=db_id(target)
 if not any(d.get("name")=="pick-pack-1291-service-prod" for d in before):raise RuntimeError("BETA_SERVICE_D1_MISSING")
 if not any(d.get("name")=="pick-pack-1291-primary" for d in before):raise RuntimeError("BETA_PRIMARY_D1_MISSING")
 ws=worker_settings(worker); bindings=ws.get("bindings") or []
 by={b.get("name"):b for b in bindings}
 if (by.get("DB") or {}).get("id")!=tid:raise RuntimeError("STABLE_WORKER_D1_BINDING_MISMATCH")
 if (by.get("ENVIRONMENT_ID") or {}).get("text")!="STABLE":raise RuntimeError("STABLE_ENV_BINDING_MISMATCH")
 if (by.get("SERVICE_AUDIENCE") or {}).get("text")!="PICK_PACK_1291_STABLE":raise RuntimeError("STABLE_AUDIENCE_BINDING_MISMATCH")
 forbidden=["GOOGLE_OAUTH_CLIENT_ID","GOOGLE_OAUTH_CLIENT_SECRET","GOOGLE_OAUTH_REFRESH_TOKEN"]
 if any(x in by for x in forbidden):raise RuntimeError("STABLE_WORKER_HAS_BROAD_GOOGLE_OAUTH")
 if (by.get("GOOGLE_SOURCE_SHEET_ID") or {}).get("text")!=req["stable_primary_sheet_id"]:raise RuntimeError("STABLE_PRIMARY_SHEET_BINDING_MISMATCH")
 if (by.get("GOOGLE_OUTBOUND_SHEET_ID") or {}).get("text")!=req["stable_outbound_sheet_id"]:raise RuntimeError("STABLE_OUTBOUND_SHEET_BINDING_MISMATCH")
 original=table_signature(tid)
 backup="/tmp/stable-d1-backup.sql"; cfg=minimal_config(target,tid)
 canary=f"pp1291-stable-restore-canary-{os.environ.get('GITHUB_RUN_ID','local')}"
 cid=None
 try:
  pathlib.Path(backup).unlink(missing_ok=True)
  sh(["npx","wrangler","d1","export",target,"--remote","--output",backup,"--config",str(cfg.name)],cwd=SERVICE)
  if not pathlib.Path(backup).exists() or pathlib.Path(backup).stat().st_size<100:raise RuntimeError("D1_BACKUP_EXPORT_EMPTY")
  backup_sha=hashlib.sha256(pathlib.Path(backup).read_bytes()).hexdigest()
  exists=[d for d in dbs() if d.get("name")==canary]
  if exists: raise RuntimeError("RESTORE_CANARY_PREEXISTS")
  cr=call("/d1/database","POST",{"name":canary}) or {}; cid=cr.get("uuid") or cr.get("id")
  if not cid:raise RuntimeError("RESTORE_CANARY_CREATE_NO_ID")
  rcfg=minimal_config(canary,cid)
  sh(["npx","wrangler","d1","execute",canary,"--remote","--file",backup,"--config",str(rcfg.name)],cwd=SERVICE)
  restored=table_signature(cid)
  if restored!=original:raise RuntimeError("RESTORE_COMPARE_MISMATCH")
  # No Worker may bind the canary before destructive cleanup.
  for w in workers():
   name=w.get("id") or w.get("name")
   if not name:continue
   st=worker_settings(name)
   raw=json.dumps(st,separators=(",",":"))
   if cid in raw or canary in raw:raise RuntimeError("RESTORE_CANARY_BOUND_ABORT_DELETE:"+name)
  call(f"/d1/database/{cid}","DELETE");cid=None
  after=dbs()
  if len(after)!=before_count:raise RuntimeError(f"D1_QUOTA_NOT_RESTORED:{before_count}->{len(after)}")
  if any(d.get("name")==canary for d in after):raise RuntimeError("RESTORE_CANARY_DELETE_READBACK_FAILED")
  url=endpoint(worker)
  stable_beta_status=http_status(url+"/v1/sync/status",{"x-pick-pack-environment":"BETA","x-pick-pack-audience":"PICK_PACK_1291_BETA"}) if url else -1
  stable_missing_status=http_status(url+"/v1/sync/status") if url else -1
  if stable_beta_status not in (401,403,409) or stable_missing_status not in (401,403,409):raise RuntimeError(f"STABLE_FENCE_FAIL:{stable_beta_status}:{stable_missing_status}")
  rec={"status":"PASS","environment":"STABLE","d1_count_before":before_count,"d1_count_after":len(after),"stable_d1_id":tid,
   "backup":{"sha256":backup_sha,"tables":original,"restore_compare":"PASS","canary_deleted":True},
   "worker":{"name":worker,"separate_d1":True,"broad_google_oauth_absent":True,"stable_env_binding":True,"stable_audience_binding":True},
   "cross_env":{"beta_headers_to_stable_rejected":True,"missing_headers_to_stable_rejected":True},
   "beta_resources_preserved":True}
  pathlib.Path("/tmp/stable-isolation-verify-receipt.json").write_text(json.dumps(rec,indent=2,ensure_ascii=False)+"\n")
  print(json.dumps({"status":"PASS","restore_compare":"PASS","d1_count_after":len(after),"canary_deleted":True}))
 finally:
  cfg.unlink(missing_ok=True)
  pathlib.Path(SERVICE/"wrangler.stable.verify.generated.jsonc").unlink(missing_ok=True)
  if cid:
   try:
    # Recovery cleanup only when still provably unbound.
    raw="".join(json.dumps(worker_settings((w.get("id") or w.get("name")))) for w in workers() if (w.get("id") or w.get("name")))
    if cid not in raw and canary not in raw: call(f"/d1/database/{cid}","DELETE")
   except Exception as e: print("CANARY_RECOVERY_CLEANUP_FAILED:"+str(e)[:500],file=sys.stderr)
if __name__=="__main__":
 try:main()
 except Exception as e:
  pathlib.Path("/tmp/stable-isolation-verify-receipt.json").write_text(json.dumps({"status":"FAIL","error":str(e)[:1000]},indent=2)+"\n")
  print("STABLE_ISOLATION_VERIFY_ERROR:"+str(e)[:1600],file=sys.stderr);sys.exit(1)
