#!/usr/bin/env python3
import hashlib,json,os,pathlib,subprocess,sys,urllib.parse,urllib.request,urllib.error
ROOT=pathlib.Path(__file__).resolve().parents[1]
SERVICE=ROOT/"service"
CF="https://api.cloudflare.com/client/v4"

def need(n):
    v=os.environ.get(n,"").strip()
    if not v: raise RuntimeError("MISSING_REQUIRED_SECRET:"+n)
    return v

def req_json(url,method="GET",token=None,body=None,timeout=60):
    data=None if body is None else json.dumps(body,separators=(",",":")).encode()
    h={"Accept":"application/json"}
    if token:h["Authorization"]="Bearer "+token
    if data is not None:h["Content-Type"]="application/json"
    r=urllib.request.Request(url,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(r,timeout=timeout) as x:
            raw=x.read().decode("utf-8","replace")
            return x.status,(json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw=e.read().decode("utf-8","replace")
        try:j=json.loads(raw)
        except:j={"raw":raw[:500]}
        return e.code,j

def cf(path,method="GET",body=None):
    code,j=req_json(f"{CF}/accounts/{need('CLOUDFLARE_ACCOUNT_ID')}{path}",method,need("CLOUDFLARE_API_TOKEN"),body)
    if code//100!=2 or j.get("success") is not True:raise RuntimeError("CF_API_FAILED:"+str(code)+":"+json.dumps(j.get("errors",j))[:600])
    return j.get("result")

def sh(cmd,cwd=None):
    p=subprocess.run(cmd,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=900)
    if p.returncode:raise RuntimeError("COMMAND_FAILED:"+cmd[0]+":"+"\n".join(p.stdout.splitlines()[-50:])[:4000])
    return p.stdout

def d1_rows(db,sql):
    r=cf("/d1/database/"+urllib.parse.quote(db,safe="")+"/query","POST",{"sql":sql})
    if not isinstance(r,list) or not r:raise RuntimeError("D1_QUERY_EMPTY")
    if r[0].get("success") is False:raise RuntimeError("D1_QUERY_FAILED")
    return r[0].get("results") or []

def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def binding_snapshot(raw):
    out=[]
    for b in raw.get("bindings",[]) or []:
        t=str(b.get("type") or "");n=str(b.get("name") or "")
        x={"name":n,"type":t}
        if t=="plain_text":x["text"]=str(b.get("text") or "")
        if t=="d1":x["id"]=str(b.get("id") or "")
        if t=="durable_object_namespace":x["class_name"]=str(b.get("class_name") or "")
        out.append(x)
    return sorted(out,key=lambda x:(x["name"],x["type"]))

def d1_snapshot(db):
    return {
      "accounts":d1_rows(db,"SELECT login_id,role,status,source_row,source_checksum FROM accounts ORDER BY login_id"),
      "authority":d1_rows(db,"SELECT singleton_id,authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state ORDER BY singleton_id"),
      "counts":d1_rows(db,"SELECT (SELECT COUNT(*) FROM events) events,(SELECT COUNT(*) FROM auth_sessions) auth_sessions,(SELECT COUNT(*) FROM auth_web_sessions) auth_web_sessions,(SELECT COUNT(*) FROM sheet_replication_outbox) sheet_outbox,(SELECT COUNT(*) FROM outbound_replication_outbox) outbound_outbox")
    }

def curl_json(url,headers=None):
    cmd=["curl","-fsS","--connect-timeout","12","--max-time","35"]
    for k,v in (headers or {}).items():cmd += ["-H",f"{k}: {v}"]
    cmd.append(url)
    p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
    if p.returncode:raise RuntimeError("CURL_FAILED:"+p.stderr[-500:])
    try:return json.loads(p.stdout)
    except:raise RuntimeError("CURL_BAD_JSON:"+p.stdout[:300])

def main():
    req=json.loads((ROOT/"ops/stable-private-provision-request.json").read_text())
    if req.get("environment")!="STABLE" or req.get("stable_public_activation") is not False or req.get("mode")!="WORKER_CODE_SYNC":
        raise RuntimeError("WORKER_CODE_SYNC_REQUEST_FAIL_CLOSED")
    accepted=str(req.get("accepted_service_source_sha") or "")
    if len(accepted)!=40:raise RuntimeError("ACCEPTED_SERVICE_SOURCE_SHA_REQUIRED")
    diff=subprocess.run(["git","diff","--quiet",accepted,"HEAD","--","service"],cwd=ROOT)
    if diff.returncode!=0:raise RuntimeError("STABLE_SERVICE_SOURCE_NOT_EXACT_ACCEPTED")
    name=str(req["target_worker_name"]);enc=urllib.parse.quote(name,safe="")
    raw=cf(f"/workers/scripts/{enc}/settings") or {}
    before_bindings=binding_snapshot(raw)
    by={x["name"]:x for x in before_bindings}
    if (by.get("ENVIRONMENT_ID") or {}).get("text")!="STABLE":raise RuntimeError("STABLE_ENV_BINDING_DRIFT")
    if (by.get("SERVICE_AUDIENCE") or {}).get("text")!="PICK_PACK_1291_STABLE":raise RuntimeError("STABLE_AUDIENCE_BINDING_DRIFT")
    db=str((by.get("DB") or {}).get("id") or "")
    if not db:raise RuntimeError("STABLE_D1_BINDING_MISSING")
    required_secrets={"SERVICE_TOKEN_SECRET","M1_ADMIN_TOKEN","GAS_BRIDGE_SHARED_SECRET"}
    secret_names={x["name"] for x in before_bindings if x["type"]=="secret_text"}
    if not required_secrets.issubset(secret_names):raise RuntimeError("STABLE_REQUIRED_SECRETS_MISSING")
    if any(x in secret_names for x in {"GOOGLE_OAUTH_CLIENT_ID","GOOGLE_OAUTH_CLIENT_SECRET","GOOGLE_OAUTH_REFRESH_TOKEN"}):raise RuntimeError("STABLE_BROAD_GOOGLE_OAUTH_PRESENT")
    before_d1=d1_snapshot(db);before_d1_hash=digest(before_d1)

    vars_names=["SERVICE_GENERATION","ENVIRONMENT_ID","SERVICE_AUDIENCE","GAS_API_URL","OUTBOUND_GAS_API_URL","DR_GAS_API_URL","DR_TARGET_ID","GOOGLE_SOURCE_SHEET_ID","GOOGLE_OUTBOUND_SHEET_ID"]
    vars_map={k:(by.get(k) or {}).get("text","") for k in vars_names}
    if vars_map["GOOGLE_SOURCE_SHEET_ID"]!=req["stable_primary_sheet_id"] or vars_map["GOOGLE_OUTBOUND_SHEET_ID"]!=req["stable_outbound_sheet_id"]:
        raise RuntimeError("STABLE_SHEET_BINDING_DRIFT")
    cfg={
      "name":name,"main":"src/entry_product.ts","compatibility_date":str(raw.get("compatibility_date") or "2026-08-08"),
      "compatibility_flags":["nodejs_compat"],"workers_dev":True,"placement":{"mode":"smart"},"vars":vars_map,
      "d1_databases":[{"binding":"DB","database_name":req["target_d1_name"],"database_id":db,"migrations_dir":"migrations"}],
      "durable_objects":{"bindings":[{"name":"REALTIME_HUB","class_name":"RealtimeHub"}]},
      "migrations":[{"tag":"v1","new_sqlite_classes":["RealtimeHub"]}],
      "assets":{"directory":"./public","binding":"ASSETS","not_found_handling":"single-page-application","run_worker_first":["/health","/environment.json","/v1/*","/internal/*"]},
      "triggers":{"crons":["*/1 * * * *"]},"observability":{"enabled":True,"head_sampling_rate":1}
    }
    path=SERVICE/"wrangler.stable.codesync.generated.jsonc";path.write_text(json.dumps(cfg,indent=2)+"\n")
    try:
        sh(["npx","wrangler","deploy","--keep-vars","--config",str(path.name)],cwd=SERVICE)
    finally:path.unlink(missing_ok=True)

    after_raw=cf(f"/workers/scripts/{enc}/settings") or {}
    after_bindings=binding_snapshot(after_raw);after_by={x["name"]:x for x in after_bindings}
    after_secret_names={x["name"] for x in after_bindings if x["type"]=="secret_text"}
    if before_bindings!=after_bindings:raise RuntimeError("STABLE_BINDINGS_CHANGED_DURING_CODE_SYNC")
    if secret_names!=after_secret_names:raise RuntimeError("STABLE_SECRET_BINDINGS_CHANGED_DURING_CODE_SYNC")
    after_d1=d1_snapshot(db);after_d1_hash=digest(after_d1)
    if before_d1_hash!=after_d1_hash:raise RuntimeError("STABLE_D1_CHANGED_DURING_CODE_SYNC")

    sub=str((cf("/workers/subdomain") or {}).get("subdomain") or "")
    if not sub:raise RuntimeError("WORKERS_SUBDOMAIN_MISSING")
    url=f"https://{name}.{sub}.workers.dev"
    env=curl_json(url+"/environment.json")
    if env.get("environment_id")!="STABLE" or env.get("service_audience")!="PICK_PACK_1291_STABLE" or env.get("release_channel")!="STABLE":
        raise RuntimeError("STABLE_ENVIRONMENT_ENDPOINT_STILL_DRIFTED:"+json.dumps({k:env.get(k) for k in ("environment_id","service_audience","release_channel")}))
    health=curl_json(url+"/health")
    if health.get("ok") is not True:raise RuntimeError("STABLE_HEALTH_FAILED_AFTER_CODE_SYNC")
    p=subprocess.run(["curl","-sS","-o","/dev/null","-w","%{http_code}","--connect-timeout","10","--max-time","20",
      "-H","X-Pick-Pack-Environment: BETA","-H","X-Pick-Pack-Audience: PICK_PACK_1291_BETA",url+"/v1/sync/status"],text=True,stdout=subprocess.PIPE,timeout=30)
    if int(p.stdout.strip() or 0) not in (403,409):raise RuntimeError("STABLE_CROSS_ENV_REJECT_FAILED_AFTER_CODE_SYNC")
    rec={"status":"PASS","mode":"WORKER_CODE_SYNC","environment":"STABLE","accepted_service_source_sha":accepted,
      "worker_name":name,"stable_public_activation":False,"d1_changed":False,"auth_changed":False,"bindings_changed":False,
      "secret_bindings_changed":False,"before_binding_hash":digest(before_bindings),"after_binding_hash":digest(after_bindings),
      "before_d1_hash":before_d1_hash,"after_d1_hash":after_d1_hash,
      "environment_endpoint":{"environment_id":"STABLE","service_audience":"PICK_PACK_1291_STABLE","release_channel":"STABLE"},
      "health":"PASS","cross_environment_reject":"PASS"}
    pathlib.Path("/tmp/stable-private-provision-receipt.json").write_text(json.dumps(rec,indent=2)+"\n")
    print(json.dumps({"status":"PASS","mode":"WORKER_CODE_SYNC","d1_changed":False,"auth_changed":False,"bindings_changed":False,"environment_endpoint":"PASS"}))
if __name__=="__main__":
    try:main()
    except Exception as e:
        pathlib.Path("/tmp/stable-private-provision-receipt.json").write_text(json.dumps({"status":"FAIL","mode":"WORKER_CODE_SYNC","error":str(e)[:1400],"stable_public_activation":False},indent=2)+"\n")
        print("STABLE_WORKER_CODE_SYNC_ERROR:"+str(e)[:1800],file=sys.stderr);sys.exit(1)
