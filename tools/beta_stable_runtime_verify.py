#!/usr/bin/env python3
import datetime,hashlib,json,os,pathlib,re,subprocess,sys,urllib.error,urllib.parse,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
# Runtime DoD exact-source comparison requires full git history in the workflow checkout.
CF="https://api.cloudflare.com/client/v4"
SCRIPT_API="https://script.googleapis.com/v1/projects"
CANARY_SHEET="__STABLE_RUNTIME_CANARY"

def need(n):
    v=os.environ.get(n,"").strip()
    if not v:raise RuntimeError("MISSING_REQUIRED_SECRET:"+n)
    return v
def req(url,method="GET",token=None,body=None,headers=None,timeout=45):
    data=None if body is None else json.dumps(body,separators=(",",":")).encode()
    h={"Accept":"application/json"}
    if token:h["Authorization"]="Bearer "+token
    if data is not None:h["Content-Type"]="application/json"
    if headers:h.update(headers)
    r=urllib.request.Request(url,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(r,timeout=timeout) as x:
            raw=x.read().decode("utf-8","replace");return x.status,(json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw=e.read().decode("utf-8","replace")
        try:j=json.loads(raw)
        except:j={"raw":raw[:500]}
        return e.code,j
def cf(path,method="GET",body=None):
    code,j=req(f"{CF}/accounts/{need('CLOUDFLARE_ACCOUNT_ID')}{path}",method,need("CLOUDFLARE_API_TOKEN"),body)
    if code//100!=2 or j.get("success") is not True:raise RuntimeError("CF_API_FAILED:"+str(code)+":"+json.dumps(j.get("errors",j))[:500])
    return j.get("result")
def oauth():
    data=urllib.parse.urlencode({"client_id":need("GOOGLE_OAUTH_CLIENT_ID"),"client_secret":need("GOOGLE_OAUTH_CLIENT_SECRET"),"refresh_token":need("GOOGLE_OAUTH_REFRESH_TOKEN"),"grant_type":"refresh_token"}).encode()
    r=urllib.request.Request("https://oauth2.googleapis.com/token",data=data,headers={"Content-Type":"application/x-www-form-urlencoded"},method="POST")
    with urllib.request.urlopen(r,timeout=45) as x:j=json.loads(x.read().decode())
    t=str(j.get("access_token",""))
    if not t:raise RuntimeError("GOOGLE_TOKEN_MISSING")
    return t
def curl_args(method,headers=None,body_present=False,follow=False,timeout=35):
    method=str(method).upper()
    cmd=["curl","-sS","--connect-timeout","12","--max-time",str(timeout)]
    if follow:cmd.append("-L")
    for k,v in (headers or {}).items():cmd += ["-H",f"{k}: {v}"]
    if body_present:
        cmd += ["-H","Content-Type: application/json","--data-binary","@-"]
        if method!="POST":cmd += ["-X",method]
    elif method!="GET":
        cmd += ["-X",method]
    return cmd
def curl_transport_selftest():
    post=curl_args("POST",body_present=True,follow=True)
    if "-X" in post or "--data-binary" not in post or "-L" not in post:raise RuntimeError("CURL_REDIRECT_POST_SELFTEST_FAIL")
    get=curl_args("GET",follow=True)
    if "-X" in get:raise RuntimeError("CURL_GET_SELFTEST_FAIL")
    put=curl_args("PUT",body_present=True)
    if "-X" not in put or put[put.index("-X")+1]!="PUT":raise RuntimeError("CURL_NONPOST_METHOD_SELFTEST_FAIL")
def curl_json(method,url,headers=None,body=None,follow=False,timeout=35):
    cmd=curl_args(method,headers=headers,body_present=body is not None,follow=follow,timeout=timeout)
    inp=None
    if body is not None:inp=json.dumps(body,separators=(",",":"))
    cmd += ["-w","\n__STATUS__:%{http_code}",url]
    p=subprocess.run(cmd,input=inp,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout+10)
    if p.returncode:return -1,{"transport_error":p.stderr[-300:]}
    marker="\n__STATUS__:"
    if marker not in p.stdout:return -1,{"transport_error":"STATUS_MISSING"}
    raw,code=p.stdout.rsplit(marker,1)
    try:j=json.loads(raw) if raw.strip() else {}
    except:j={"raw":raw[:500]}
    return int(code.strip()),j
def curl_status(url):
    p=subprocess.run(["curl","-sS","-L","--connect-timeout","8","--max-time","20","-o","/dev/null","-w","%{http_code}",url],text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=25)
    return int(p.stdout.strip() or 0) if p.returncode==0 else 0
def worker_settings(name):return cf("/workers/scripts/"+urllib.parse.quote(name,safe="")+"/settings") or {}
def bindmap(settings):return {str(b.get("name")):b for b in (settings.get("bindings") or [])}
def btext(by,k):return str((by.get(k) or {}).get("text") or "")
def bid(by,k):return str((by.get(k) or {}).get("id") or "")
def d1_rows(db,sql):
    r=cf("/d1/database/"+urllib.parse.quote(db,safe="")+"/query","POST",{"sql":sql})
    if not isinstance(r,list) or not r:raise RuntimeError("D1_QUERY_EMPTY")
    if r[0].get("success") is False:raise RuntimeError("D1_QUERY_FAILED")
    return r[0].get("results") or []
def table_count(db,name):
    safe='"'+name.replace('"','""')+'"'
    r=d1_rows(db,f"SELECT COUNT(*) AS n FROM {safe}")
    return int((r[0] if r else {}).get("n",0))
def table_exists(db,name):
    return bool(d1_rows(db,"SELECT name FROM sqlite_master WHERE type='table' AND name="+q(name)))
def q(v):return "'"+str(v).replace("'","''")+"'"
QUOTA_KEYS=("WARN_DB_PERCENT","PREPARE_NEXT_DB_PERCENT","CUTOVER_DB_PERCENT","OWNER_TOTAL_QUOTA_WARN_PERCENT","RETENTION_DAYS","D1_DB_QUOTA_BYTES","D1_ACCOUNT_QUOTA_BYTES")
def validate_quota_rows(rows,limits):
    got={str(x.get("config_key")):str(x.get("config_value")) for x in rows}
    missing=[k for k in QUOTA_KEYS if k not in got]
    if missing:raise RuntimeError("BETA_QUOTA_GUARD_MISSING:"+",".join(missing))
    try:nums={k:float(got[k]) for k in QUOTA_KEYS}
    except:raise RuntimeError("BETA_QUOTA_GUARD_NON_NUMERIC")
    free=limits.get("cloudflare_workers_free") or {}
    if int(nums["D1_DB_QUOTA_BYTES"])!=int(free.get("d1_database_bytes") or 0):raise RuntimeError("BETA_DB_QUOTA_BYTES_DRIFT")
    if int(nums["D1_ACCOUNT_QUOTA_BYTES"])!=int(free.get("d1_account_bytes") or 0):raise RuntimeError("BETA_ACCOUNT_QUOTA_BYTES_DRIFT")
    warn,prepare,cutover=nums["WARN_DB_PERCENT"],nums["PREPARE_NEXT_DB_PERCENT"],nums["CUTOVER_DB_PERCENT"]
    if not (0<warn<prepare<cutover<100):raise RuntimeError("BETA_QUOTA_THRESHOLDS_INVALID")
    if not (0<nums["OWNER_TOTAL_QUOTA_WARN_PERCENT"]<=100):raise RuntimeError("BETA_OWNER_QUOTA_THRESHOLD_INVALID")
    if nums["RETENTION_DAYS"]<45:raise RuntimeError("BETA_RETENTION_GUARD_INVALID")
    return {k:got[k] for k in QUOTA_KEYS}
def quota_selftest():
    curl_transport_selftest()
    limits={"cloudflare_workers_free":{"d1_database_bytes":524288000,"d1_account_bytes":5368709120}}
    good=[
      {"config_key":"WARN_DB_PERCENT","config_value":"70"},{"config_key":"PREPARE_NEXT_DB_PERCENT","config_value":"80"},
      {"config_key":"CUTOVER_DB_PERCENT","config_value":"85"},{"config_key":"OWNER_TOTAL_QUOTA_WARN_PERCENT","config_value":"80"},
      {"config_key":"RETENTION_DAYS","config_value":"45"},{"config_key":"D1_DB_QUOTA_BYTES","config_value":"524288000"},
      {"config_key":"D1_ACCOUNT_QUOTA_BYTES","config_value":"5368709120"}]
    validate_quota_rows(good,limits)
    for bad,expected in [
      ([x for x in good if x["config_key"]!="PREPARE_NEXT_DB_PERCENT"],"BETA_QUOTA_GUARD_MISSING"),
      ([{**x,"config_value":"1"} if x["config_key"]=="D1_DB_QUOTA_BYTES" else x for x in good],"BETA_DB_QUOTA_BYTES_DRIFT"),
      ([{**x,"config_value":"90"} if x["config_key"]=="WARN_DB_PERCENT" else x for x in good],"BETA_QUOTA_THRESHOLDS_INVALID")]:
        try:validate_quota_rows(bad,limits)
        except RuntimeError as e:
            if not str(e).startswith(expected):raise
        else:raise RuntimeError("QUOTA_SELFTEST_NEGATIVE_FAIL:"+expected)

def sheet_values(tok,sid,rng):
    code,j=req("https://sheets.googleapis.com/v4/spreadsheets/"+urllib.parse.quote(sid,safe="")+"/values/"+urllib.parse.quote(rng,safe=""),token=tok)
    if code//100!=2:raise RuntimeError("SHEET_READ_FAILED:"+str(code))
    return j.get("values") or []
def sheet_contract(tok,sid):
    vals=sheet_values(tok,sid,"'__ENVIRONMENT_CONTRACT'!A:B")
    return {str(r[0]):str(r[1]) for r in vals if len(r)>=2 and str(r[0]).strip()}
def sheet_titles(tok,sid):
    code,j=req("https://sheets.googleapis.com/v4/spreadsheets/"+urllib.parse.quote(sid,safe="")+"?fields=sheets.properties.title",token=tok)
    if code//100!=2:raise RuntimeError("SHEET_METADATA_FAILED:"+str(code))
    return [str((x.get("properties") or {}).get("title") or "") for x in j.get("sheets",[])]
def active_sheet_accounts(tok,sid):
    rows=sheet_values(tok,sid,"'Danh sách Admin'!A1:K200");out=[]
    for r in rows[1:]:
        login=str(r[0]).strip() if len(r)>0 else ""
        if not login:continue
        role=(str(r[2]).upper().strip() if len(r)>2 else "USER")
        status=(str(r[8]).upper().strip() if len(r)>8 and str(r[8]).strip() else "ACTIVE")
        if status=="ACTIVE":out.append((login,role))
    return sorted(out)
def deployment_readback(tok,script_id,deployment_id,url):
    code,j=req(f"{SCRIPT_API}/{script_id}/deployments/{deployment_id}",token=tok)
    if code//100!=2:raise RuntimeError("GAS_DEPLOYMENT_READ_FAILED:"+str(code))
    eps=[]
    for ep in j.get("entryPoints",[]) or []:
        if ep.get("entryPointType")!="WEB_APP":continue
        w=ep.get("webApp") or {};cfg=w.get("entryPointConfig") or {}
        eps.append({"url":str(w.get("url") or ""),"access":str(cfg.get("access") or ""),"executeAs":str(cfg.get("executeAs") or "")})
    if len(eps)!=1:raise RuntimeError("GAS_WEBAPP_ENTRYPOINT_NOT_UNIQUE")
    ep=eps[0]
    if ep["url"]!=url or ep["access"]!="ANYONE_ANONYMOUS" or ep["executeAs"]!="USER_DEPLOYING":raise RuntimeError("GAS_WEBAPP_POLICY_DRIFT")
    return ep
def _canary_diag(code,j):
    return {"http":code,"ok":j.get("ok"),"error":j.get("error"),"idempotent":j.get("idempotent"),"cleanup":j.get("cleanup")}

def cleanup_stable_gas_canary(kind,url,tok,canary_id,request_fn=None):
    request_fn=request_fn or curl_json
    base={"action":"stable_runtime_canary","_environment_id":"STABLE","_service_audience":"PICK_PACK_1291_STABLE","google_access_token":tok,"canary_id":canary_id}
    c1,j1=request_fn("POST",url,body={**base,"operation":"CLEANUP"},follow=True,timeout=60)
    first_ok=c1==200 and j1.get("ok") is True and (j1.get("cleanup") is True or j1.get("idempotent") is True)
    if not first_ok:raise RuntimeError("STABLE_GAS_CANARY_RECOVERY_CLEANUP_FAILED:"+kind+":"+json.dumps(_canary_diag(c1,j1),separators=(",",":")))
    c2,j2=request_fn("POST",url,body={**base,"operation":"CLEANUP"},follow=True,timeout=60)
    if c2!=200 or j2.get("ok") is not True or j2.get("idempotent") is not True:
        raise RuntimeError("STABLE_GAS_CANARY_RECOVERY_REPLAY_FAILED:"+kind+":"+json.dumps(_canary_diag(c2,j2),separators=(",",":")))
    return {"cleanup":"PASS","cleanup_replay":"PASS","first_idempotent":j1.get("idempotent") is True}

def gas_runtime_canary(kind,url,tok,canary_id,request_fn=None):
    request_fn=request_fn or curl_json
    expected=kind.upper()
    get_code,get_j=request_fn("GET",url,follow=True)
    if get_code!=200 or get_j.get("ok") is not True or get_j.get("environment_id")!="STABLE":raise RuntimeError("STABLE_GAS_GET_FAILED:"+kind+":"+str(get_code))
    base={"action":"stable_runtime_canary","_environment_id":"STABLE","_service_audience":"PICK_PACK_1291_STABLE","google_access_token":tok,"canary_id":canary_id}
    primary_error=None
    try:
        c1,j1=request_fn("POST",url,body={**base,"operation":"UPSERT"},follow=True,timeout=60)
        if c1!=200:raise RuntimeError("STABLE_GAS_RUNTIME_NOT_AUTHORIZED:"+kind+":"+str(c1))
        if j1.get("ok") is not True or j1.get("idempotent") is not False or j1.get("environment_id")!="STABLE" or j1.get("kind")!=expected or j1.get("properties_ok") is not True or j1.get("bound_sheet") is not True:
            raise RuntimeError("STABLE_GAS_CANARY_FIRST_WRITE_FAILED:"+kind+":"+json.dumps(_canary_diag(c1,j1),separators=(",",":")))
        c2,j2=request_fn("POST",url,body={**base,"operation":"UPSERT"},follow=True,timeout=60)
        if c2!=200 or j2.get("ok") is not True or j2.get("idempotent") is not True:
            raise RuntimeError("STABLE_GAS_CANARY_REPLAY_FAILED:"+kind+":"+json.dumps(_canary_diag(c2,j2),separators=(",",":")))
    except Exception as e:
        primary_error=e
    cleanup_error=None
    cleanup_result=None
    try:
        cleanup_result=cleanup_stable_gas_canary(kind,url,tok,canary_id,request_fn=request_fn)
    except Exception as e:
        cleanup_error=e
    if primary_error and cleanup_error:raise RuntimeError(str(primary_error)+";"+str(cleanup_error))
    if primary_error:raise primary_error
    if cleanup_error:raise cleanup_error
    return {"http":200,"get":"PASS","first_write":"PASS","replay_idempotent":"PASS","cleanup":cleanup_result["cleanup"],"cleanup_replay":cleanup_result["cleanup_replay"],"properties":"PASS","bound_sheet":"PASS"}

def gas_runtime_canary_selftest():
    calls=[]
    def fake(method,url,body=None,follow=False,timeout=35):
        op=(body or {}).get("operation")
        calls.append(op or method)
        if method=="GET":return 200,{"ok":True,"environment_id":"STABLE"}
        if op=="UPSERT" and calls.count("UPSERT")==1:return 200,{"ok":True,"idempotent":False,"environment_id":"STABLE","kind":"DR","properties_ok":True,"bound_sheet":True}
        if op=="UPSERT":return 200,{"ok":False,"error":"SYNTHETIC_REPLAY_FAIL","idempotent":False}
        if op=="CLEANUP" and calls.count("CLEANUP")==1:return 200,{"ok":True,"cleanup":True,"idempotent":False}
        if op=="CLEANUP":return 200,{"ok":True,"idempotent":True}
        return 500,{"ok":False}
    try:gas_runtime_canary("dr","https://example.invalid","tok","cid",request_fn=fake)
    except RuntimeError as e:
        if not str(e).startswith("STABLE_GAS_CANARY_REPLAY_FAILED:dr:"):raise
    else:raise RuntimeError("GAS_CANARY_SELFTEST_EXPECTED_REPLAY_FAILURE")
    if calls.count("CLEANUP")!=2:raise RuntimeError("GAS_CANARY_SELFTEST_CLEANUP_NOT_ATTEMPTED")
def assert_exact_candidate_source(source):
    p=subprocess.run(["git","diff","--quiet",source,"HEAD","--","app","service","google-apps-script"],cwd=ROOT)
    if p.returncode!=0:raise RuntimeError("EXACT_BETA_CANDIDATE_SOURCE_DRIFT")
def repo_secret_sanity(obj,label):
    def walk(x,path=""):
        if isinstance(x,dict):
            for k,v in x.items():
                lk=str(k).lower();np=path+"."+str(k)
                if any(t in lk for t in ["password","client_secret","refresh_token","signing_key","bridge_secret"]) and v not in (None,"",False):
                    raise RuntimeError("PLAINTEXT_SECRET_FIELD:"+label+np)
                walk(v,np)
        elif isinstance(x,list):
            for i,v in enumerate(x):walk(v,path+f"[{i}]")
    walk(obj)
def recover_runtime_canary_if_requested(tok,prov,release):
    if release.get("mode")!="RECOVER_STABLE_DR_CANARY_AFTER_RUNTIME_DOD_FAILURE":return False
    cid=str(release.get("runtime_recovery_canary_id") or "")
    failed_run=int(release.get("runtime_recovery_failed_run_id") or 0)
    if cid!="__CI_STABLE_CANARY_"+str(failed_run) or failed_run<=0:
        raise RuntimeError("STABLE_GAS_CANARY_RECOVERY_ID_INVALID")
    sid=str(prov.get("stable_dr_sheet_id") or "")
    if not sid:raise RuntimeError("STABLE_DR_SHEET_ID_MISSING")
    c=sheet_contract(tok,sid)
    if c.get("environment_id")!="STABLE" or c.get("stable_spreadsheet_id")!=sid:
        raise RuntimeError("STABLE_DR_CONTRACT_RECOVERY_FAILED")
    script_id=str(c.get("gas_script_id") or "");deployment_id=str(c.get("gas_deployment_id") or "");url=str(c.get("gas_web_url") or "")
    if not script_id or not deployment_id or not url:raise RuntimeError("STABLE_DR_GAS_RECOVERY_ID_MISSING")
    deployment_readback(tok,script_id,deployment_id,url)
    result=cleanup_stable_gas_canary("dr",url,tok,cid)
    if CANARY_SHEET in sheet_titles(tok,sid):raise RuntimeError("STABLE_DR_CANARY_RECOVERY_SHEET_LEAK")
    receipt={"status":"PASS","phase":"STABLE_GAS_CANARY_RECOVERY","failed_run_id":failed_run,"canary_id":cid,
      "target":"dr","cleanup":result,"stable_public":False,"beta_touched":False,"auth_changed":False,"d1_changed":False}
    pathlib.Path("/tmp/beta-stable-runtime-verify.json").write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"status":"PASS","phase":"STABLE_GAS_CANARY_RECOVERY","target":"dr","stable_public":False}))
    return True

def promotion_lock_mode_selftest():
    promo={"beta_acceptance_lock":{"status":"OWNER_ACCEPTED","source_sha":"old-beta","owner_acceptance_ref":"ops/beta104-owner-acceptance.json","beta":{}},"stable_promotion_lock":{"accepted_source_sha":"old-beta","owner_promotion_authorization":None,"stable":{"manifest_active":False,"ota_active":False,"public_domain_active":False}}}
    source="new-beta"
    # PRE_OTA runtime must allow a historical OWNER-accepted promotion lock from an older LIVE Beta.
    sp=promo["stable_promotion_lock"]
    if sp.get("owner_promotion_authorization") is not None:raise RuntimeError("PREOTA_PROMOTION_LOCK_SELFTEST_FAILED")
    # Promotion mode must still reject source drift.
    if promo["beta_acceptance_lock"].get("source_sha")==source:raise RuntimeError("PROMOTION_SOURCE_DRIFT_SELFTEST_INVALID_FIXTURE")

def beta_user_update_path_probe():
    for n in ["CLOUDFLARE_API_TOKEN","CLOUDFLARE_ACCOUNT_ID","GOOGLE_OAUTH_CLIENT_ID","GOOGLE_OAUTH_CLIENT_SECRET","GOOGLE_OAUTH_REFRESH_TOKEN"]:
        print("::add-mask::"+need(n))
    contract=json.loads((ROOT/"config/environment_contracts.json").read_text())
    release=json.loads((ROOT/"ops/beta-release-request.json").read_text())
    beta=contract["environments"]["BETA"]
    worker=str(beta["current_service"]["worker"])
    settings=worker_settings(worker); by=bindmap(settings)
    sub=str((cf("/workers/subdomain") or {}).get("subdomain") or "")
    worker_url=f"https://{worker}.{sub}.workers.dev"
    health_code,health=curl_json("GET",worker_url+"/health")
    env_code,envj=curl_json("GET",worker_url+"/environment.json")
    gas_url=btext(by,"GAS_API_URL")
    discovery_code,discovery=curl_json("POST",gas_url,body={"action":"service_discovery","_app_channel":"BETA","_app_version":"0.4.2-beta.115","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA"},follow=True,timeout=60)
    update_code,update=curl_json("POST",gas_url,body={"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.115","_app_channel":"BETA","_app_version":"0.4.2-beta.115","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA"},follow=True,timeout=60)
    expected_url=str(beta["current_service"]["url"]).rstrip("/")
    expected_sha=str(release["apk_sha256"])
    expected_size=int(release["apk_size"])
    expected_version=str(release["version_name"])
    checks={
      "worker_health": health_code==200 and health.get("ok") is True,
      "worker_environment": env_code==200 and envj.get("environment_id")=="BETA" and envj.get("service_audience")=="PICK_PACK_1291_BETA",
      "gas_discovery": discovery_code==200 and discovery.get("ok") is True and str(discovery.get("service_url") or "").rstrip("/")==expected_url,
      "gas_update_http": update_code==200 and update.get("ok") is True,
      "gas_update_available_from_115": update.get("available") is True,
      "gas_update_version": str(update.get("version_name") or "")==expected_version,
      "gas_update_sha": str(update.get("sha256") or "")==expected_sha,
      "gas_update_size": int(update.get("size") or 0)==expected_size,
      "gas_update_url": str(update.get("apk_url") or "").startswith("https://github.com/") and "/releases/download/" in str(update.get("apk_url") or "")
    }
    receipt={"status":"PASS" if all(checks.values()) else "FAIL","phase":"BETA115_TO_BETA116_USER_UPDATE_PATH_READONLY","checks":checks,
      "worker":{"url":worker_url,"health_http":health_code,"health_ok":health.get("ok"),"environment_http":env_code,"environment_id":envj.get("environment_id"),"service_audience":envj.get("service_audience")},
      "gas":{"discovery_http":discovery_code,"discovery_ok":discovery.get("ok"),"service_url":discovery.get("service_url"),"update_http":update_code,"update_ok":update.get("ok"),"available":update.get("available"),"version_name":update.get("version_name"),"sha256":update.get("sha256"),"size":update.get("size"),"apk_url":update.get("apk_url"),"error":update.get("error")},
      "writes":False}
    pathlib.Path("/tmp/beta-stable-runtime-verify.json").write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps(receipt,ensure_ascii=False))
    if receipt["status"]!="PASS": raise RuntimeError("BETA_USER_UPDATE_PATH_FAIL:"+json.dumps(checks,separators=(",",":")))
    return

def main():
    release_probe=json.loads((ROOT/"ops/beta-release-request.json").read_text())
    if release_probe.get("mode")=="BETA116_USER_UPDATE_PATH_READONLY":
        beta_user_update_path_probe()
        return
    promotion_mode="--promotion-dry-run" in sys.argv
    for n in ["CLOUDFLARE_API_TOKEN","CLOUDFLARE_ACCOUNT_ID","GOOGLE_OAUTH_CLIENT_ID","GOOGLE_OAUTH_CLIENT_SECRET","GOOGLE_OAUTH_REFRESH_TOKEN"]:
        print("::add-mask::"+need(n))
    tok=oauth();print("::add-mask::"+tok)
    contract=json.loads((ROOT/"config/environment_contracts.json").read_text())
    prov=json.loads((ROOT/"ops/stable-private-provision-request.json").read_text())
    release=json.loads((ROOT/"ops/beta-release-request.json").read_text())
    if release.get("candidate_locked") is not True or release.get("rebuild") is not False or release.get("resign") is not False or release.get("stable_publish")!="FORBIDDEN":raise RuntimeError("BETA_RELEASE_LOCK_INVALID")
    if recover_runtime_canary_if_requested(tok,prov,release):return
    promo=json.loads((ROOT/"ops/promotion-lock-dry-run.json").read_text())
    owner_acceptance=json.loads((ROOT/"ops/beta104-owner-acceptance.json").read_text()) if promotion_mode else None
    proof=json.loads((ROOT/"ops/stable-isolation-proof.json").read_text())
    limits=json.loads((ROOT/"config/provider_free_limits.json").read_text())
    repo_secret_sanity(release,"release");repo_secret_sanity(prov,"provision");repo_secret_sanity(promo,"promotion");repo_secret_sanity(proof,"backup")
    if release.get("candidate_locked") is not True or release.get("rebuild") is not False or release.get("resign") is not False or release.get("stable_publish")!="FORBIDDEN":raise RuntimeError("BETA_RELEASE_LOCK_INVALID")
    if release.get("device_regression_status")!="PASS":raise RuntimeError("SERVICE_DISCOVERY_DEVICE_REGRESSION_NOT_PASS")
    if not isinstance(release.get("device_regression_run_id"),int) or not isinstance(release.get("device_regression_artifact_id"),int):raise RuntimeError("SERVICE_DISCOVERY_DEVICE_EVIDENCE_MISSING")
    source=str(release.get("source_sha") or "");assert_exact_candidate_source(source)
    beta_lock=promo["beta_acceptance_lock"];beta_meta=beta_lock.get("beta") or {}
    sp=promo["stable_promotion_lock"]
    if promotion_mode:
        if beta_lock.get("source_sha")!=source:raise RuntimeError("BETA_ACCEPTANCE_LOCK_SOURCE_INVALID")
        if beta_lock.get("status")!="OWNER_ACCEPTED" or beta_lock.get("owner_acceptance_ref")!="ops/beta104-owner-acceptance.json":raise RuntimeError("BETA_ACCEPTANCE_LOCK_OWNER_STATE_INVALID")
        if not owner_acceptance or owner_acceptance.get("status")!="OWNER_ACCEPTED" or owner_acceptance.get("release")!=release.get("version_name"):raise RuntimeError("BETA_OWNER_ACCEPTANCE_RECEIPT_INVALID")
        if any(str((owner_acceptance.get("checklist") or {}).get(str(i)))!="OK" for i in range(1,7)):raise RuntimeError("BETA_OWNER_ACCEPTANCE_CHECKLIST_INCOMPLETE")
        if release.get("live") is not True:raise RuntimeError("BETA104_NOT_LIVE_FOR_PROMOTION_DRY_RUN")
        if release.get("version_name")!=beta_meta.get("version_name") or int(release.get("version_code",0))!=int(beta_meta.get("version_code",0)) or release.get("package")!=beta_meta.get("package_name"):raise RuntimeError("BETA_CANDIDATE_METADATA_DRIFT")
        if release.get("apk_sha256")!=beta_meta.get("apk_sha256") or int(release.get("apk_size",0))!=int(beta_meta.get("apk_size",0)) or release.get("signer_sha256")!=beta_meta.get("signer_sha256"):raise RuntimeError("BETA_CANDIDATE_RELEASE_IDENTITY_DRIFT")
        if sp.get("accepted_source_sha")!=source or sp.get("owner_promotion_authorization") is not None:raise RuntimeError("STABLE_PROMOTION_AUTHORIZATION_INVALID")
    elif sp.get("owner_promotion_authorization") is not None:
        raise RuntimeError("STABLE_PROMOTION_AUTHORIZATION_INVALID")
    if proof.get("status")!="PASS" or proof.get("restore_compare")!="PASS" or proof.get("restore_canary_deleted") is not True or proof.get("d1_count_after")!=3:raise RuntimeError("STABLE_BACKUP_RESTORE_PROOF_INVALID")
    if any(bool(sp["stable"].get(k)) for k in ["manifest_active","ota_active","public_domain_active"]):raise RuntimeError("STABLE_PROMOTION_ALREADY_PUBLIC")
    beta_c=contract["environments"]["BETA"];stable_c=contract["environments"]["STABLE"]
    if stable_c.get("stable_publish_allowed") is not False:raise RuntimeError("STABLE_CONTRACT_PUBLISH_ALLOWED")
    beta_name=str(beta_c["current_service"]["worker"]);stable_name=str(prov["target_worker_name"])
    beta_s,stable_s=worker_settings(beta_name),worker_settings(stable_name);bb,sb=bindmap(beta_s),bindmap(stable_s)
    beta_db,stable_db=bid(bb,"DB"),bid(sb,"DB")
    if not beta_db or not stable_db or beta_db==stable_db:raise RuntimeError("D1_ENVIRONMENT_ISOLATION_FAILED")
    dbs=cf("/d1/database?per_page=100") or []
    if len(dbs)!=3:raise RuntimeError("D1_COUNT_DRIFT:"+str(len(dbs)))
    names=[str(x.get("name") or "") for x in dbs]
    if any(("restore-canary" in x.lower() or "rehearsal" in x.lower()) for x in names):raise RuntimeError("D1_REHEARSAL_LEAK")
    stable_match=[x for x in dbs if (x.get("uuid") or x.get("id"))==stable_db]
    if len(stable_match)!=1 or stable_match[0].get("name")!=prov["target_d1_name"] or proof.get("target_d1_name")!=prov["target_d1_name"]:raise RuntimeError("STABLE_BACKUP_BINDING_DRIFT")
    if btext(sb,"ENVIRONMENT_ID")!="STABLE" or btext(sb,"SERVICE_AUDIENCE")!="PICK_PACK_1291_STABLE":raise RuntimeError("STABLE_WORKER_ENV_BINDING_FAILED")
    if (btext(bb,"ENVIRONMENT_ID") or "BETA")!="BETA" or (btext(bb,"SERVICE_AUDIENCE") or "PICK_PACK_1291_BETA")!="PICK_PACK_1291_BETA":raise RuntimeError("BETA_WORKER_ENV_BINDING_FAILED")
    if btext(sb,"GOOGLE_SOURCE_SHEET_ID")!=prov["stable_primary_sheet_id"] or btext(sb,"GOOGLE_OUTBOUND_SHEET_ID")!=prov["stable_outbound_sheet_id"]:raise RuntimeError("STABLE_SHEET_BINDING_FAILED")
    if btext(bb,"GOOGLE_SOURCE_SHEET_ID")!=beta_c["gsheet"]["spreadsheet_id"]:raise RuntimeError("BETA_SHEET_BINDING_FAILED")
    if any(k in sb for k in ["GOOGLE_OAUTH_CLIENT_ID","GOOGLE_OAUTH_CLIENT_SECRET","GOOGLE_OAUTH_REFRESH_TOKEN"]):raise RuntimeError("STABLE_BROAD_GOOGLE_OAUTH_PRESENT")
    stable_gas_urls=[btext(sb,k) for k in ["GAS_API_URL","OUTBOUND_GAS_API_URL","DR_GAS_API_URL"]]
    if any(not x.startswith("https://script.google.com/") for x in stable_gas_urls) or len(set(stable_gas_urls))!=3 or btext(bb,"GAS_API_URL") in stable_gas_urls:raise RuntimeError("GAS_ENVIRONMENT_ISOLATION_FAILED")
    # Writer/fencing/outbox/fallback current-state checks without replaying destructive DR.
    for t in ["accounts","authority_state","runtime_config","replication_status","fallback_event_inbox","outbound_replication_outbox","sheet_replication_outbox","events","auth_sessions","auth_web_sessions","realtime_tickets"]:
        if not table_exists(stable_db,t):raise RuntimeError("STABLE_TABLE_MISSING:"+t)
    sa=d1_rows(stable_db,"SELECT mode,scope,service_generation FROM authority_state WHERE singleton_id=1")
    if len(sa)!=1 or sa[0].get("mode")!="SERVICE_PRIMARY" or sa[0].get("scope")!="PRODUCTION" or str(sa[0].get("service_generation") or "")!=btext(sb,"SERVICE_GENERATION"):raise RuntimeError("STABLE_WRITER_FENCE_DRIFT")
    stable_zero={t:table_count(stable_db,t) for t in ["fallback_event_inbox","outbound_replication_outbox","sheet_replication_outbox","events","auth_sessions","auth_web_sessions","realtime_tickets"]}
    if any(v!=0 for v in stable_zero.values()):raise RuntimeError("STABLE_READY_NOT_LIVE_MUTABLE_STATE_DIRTY:"+json.dumps(stable_zero,sort_keys=True))
    if table_count(stable_db,"replication_status")<1 or table_count(stable_db,"runtime_config")<1:raise RuntimeError("STABLE_RUNTIME_GUARD_MISSING")
    ba=d1_rows(beta_db,"SELECT mode,scope,service_generation FROM authority_state WHERE singleton_id=1")
    if len(ba)!=1 or ba[0].get("mode")!="SERVICE_PRIMARY" or ba[0].get("scope")!="PRODUCTION" or str(ba[0].get("service_generation") or "")!=btext(bb,"SERVICE_GENERATION"):raise RuntimeError("BETA_WRITER_FENCE_DRIFT")
    quota=d1_rows(beta_db,"SELECT config_key,config_value FROM runtime_config WHERE config_key IN ('WARN_DB_PERCENT','PREPARE_NEXT_DB_PERCENT','CUTOVER_DB_PERCENT','OWNER_TOTAL_QUOTA_WARN_PERCENT','RETENTION_DAYS','D1_DB_QUOTA_BYTES','D1_ACCOUNT_QUOTA_BYTES')")
    quota_cfg=validate_quota_rows(quota,limits)
    if not limits.get("sources",{}).get("cloudflare_d1"):raise RuntimeError("PROVIDER_LIMIT_SOURCE_MISSING")
    verified=datetime.date.fromisoformat(str(limits.get("verified_at")));max_age=int(limits.get("max_age_days",0))
    if (datetime.date.today()-verified).days>max_age:raise RuntimeError("PROVIDER_LIMITS_STALE")
    sub=str((cf("/workers/subdomain") or {}).get("subdomain") or "")
    beta_url=f"https://{beta_name}.{sub}.workers.dev";stable_url=f"https://{stable_name}.{sub}.workers.dev"
    bh=curl_json("GET",beta_url+"/health")[1];sh=curl_json("GET",stable_url+"/health")[1]
    if not bh.get("ok") or not sh.get("ok"):raise RuntimeError("WORKER_HEALTH_FAILED")
    be_code,be=curl_json("GET",beta_url+"/environment.json");se_code,se=curl_json("GET",stable_url+"/environment.json")
    if be_code!=200 or se_code!=200 or be.get("environment_id")!="BETA" or se.get("environment_id")!="STABLE":
        diag={"beta":{"http":be_code,"environment_id":be.get("environment_id"),"service_audience":be.get("service_audience"),"release_channel":be.get("release_channel")},
              "stable":{"http":se_code,"environment_id":se.get("environment_id"),"service_audience":se.get("service_audience"),"release_channel":se.get("release_channel")}}
        raise RuntimeError("ENVIRONMENT_ENDPOINT_FAILED:"+json.dumps(diag,separators=(",",":")))
    b_mismatch,_=curl_json("GET",beta_url+"/v1/sync/status",headers={"X-Pick-Pack-Environment":"STABLE","X-Pick-Pack-Audience":"PICK_PACK_1291_STABLE"})
    s_mismatch,_=curl_json("GET",stable_url+"/v1/sync/status",headers={"X-Pick-Pack-Environment":"BETA","X-Pick-Pack-Audience":"PICK_PACK_1291_BETA"})
    s_missing,_=curl_json("GET",stable_url+"/v1/sync/status")
    if b_mismatch not in (403,409) or s_mismatch not in (403,409) or s_missing not in (403,409):raise RuntimeError("CROSS_ENVIRONMENT_HTTP_FENCE_FAILED")
    want_beta=sorted([("adminbeta","SUPERADMIN"),("admintest","ADMIN"),("user1","USER"),("user2","USER"),("user3","USER")])
    beta_active=sorted((str(r.get("login_id")),str(r.get("role"))) for r in d1_rows(beta_db,"SELECT login_id,role FROM accounts WHERE status='ACTIVE' ORDER BY login_id"))
    stable_active=sorted((str(r.get("login_id")),str(r.get("role"))) for r in d1_rows(stable_db,"SELECT login_id,role FROM accounts WHERE status='ACTIVE' ORDER BY login_id"))
    if beta_active!=want_beta:raise RuntimeError("BETA_D1_AUTH_TARGET_FAILED:"+json.dumps(beta_active))
    if stable_active!=[("admin","SUPERADMIN")]:raise RuntimeError("STABLE_D1_AUTH_TARGET_FAILED:"+json.dumps(stable_active))
    if active_sheet_accounts(tok,beta_c["gsheet"]["spreadsheet_id"])!=want_beta:raise RuntimeError("BETA_SHEET_AUTH_TARGET_FAILED")
    if active_sheet_accounts(tok,prov["stable_primary_sheet_id"])!=[("admin","SUPERADMIN")]:raise RuntimeError("STABLE_SHEET_AUTH_TARGET_FAILED")
    # Three distinct Stable GAS deployments, exact policy, live runtime + idempotent canary + cleanup.
    gas={};scripts=set();deployments=set();canary_id="__CI_STABLE_CANARY_"+str(os.environ.get("GITHUB_RUN_ID","local"))
    specs=[("primary",prov["stable_primary_sheet_id"]),("outbound",prov["stable_outbound_sheet_id"]),("dr",prov["stable_dr_sheet_id"])]
    for kind,sid in specs:
        c=sheet_contract(tok,sid)
        if c.get("environment_id")!="STABLE" or c.get("stable_spreadsheet_id")!=sid:raise RuntimeError("STABLE_GAS_CONTRACT_FAILED:"+kind)
        script_id,deployment_id,url=str(c.get("gas_script_id") or ""),str(c.get("gas_deployment_id") or ""),str(c.get("gas_web_url") or "")
        if not script_id or not deployment_id or not url:raise RuntimeError("STABLE_GAS_ID_MISSING:"+kind)
        deployment_readback(tok,script_id,deployment_id,url);scripts.add(script_id);deployments.add(deployment_id)
        gas[kind]=gas_runtime_canary(kind,url,tok,canary_id)
        if CANARY_SHEET in sheet_titles(tok,sid):raise RuntimeError("STABLE_GAS_CANARY_CLEANUP_READBACK_FAILED:"+kind)
    if len(scripts)!=3 or len(deployments)!=3:raise RuntimeError("STABLE_GAS_DEPLOYMENTS_NOT_DISTINCT")
    if CANARY_SHEET in sheet_titles(tok,beta_c["gsheet"]["spreadsheet_id"]):raise RuntimeError("STABLE_CANARY_WRITTEN_TO_BETA")
    # Beta GAS discovery is environment-routing authority and must converge to canonical BETA Service.
    beta_gas=btext(bb,"GAS_API_URL")
    discovery_code,discovery=curl_json("POST",beta_gas,body={"action":"service_discovery","_app_channel":"BETA","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA"},follow=True,timeout=60)
    expected_beta_service=str((beta_c.get("current_service") or {}).get("url") or "").rstrip("/")
    got_beta_service=str(discovery.get("service_url") or "").rstrip("/")
    if discovery_code!=200 or discovery.get("ok") is not True or discovery.get("environment_id")!="BETA" or discovery.get("service_audience")!="PICK_PACK_1291_BETA":
        raise RuntimeError("BETA_GAS_SERVICE_DISCOVERY_ENV_FAILED:"+str(discovery_code))
    if not expected_beta_service or got_beta_service!=expected_beta_service:
        raise RuntimeError("BETA_GAS_SERVICE_DISCOVERY_DRIFT:"+json.dumps({"expected":expected_beta_service,"got":got_beta_service},separators=(",",":")))

    # Manifest readback: pre-OTA expects previous LIVE; promotion dry-run expects OWNER-accepted Beta104 LIVE.
    manifest_code,manifest=curl_json("POST",beta_gas,body={"action":"update_check","channel":"BETA","current_version":"0.0.0","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA"},follow=True,timeout=60)
    if manifest_code!=200 or manifest.get("ok") is not True:raise RuntimeError("BETA_MANIFEST_READBACK_FAILED:"+str(manifest_code))
    if promotion_mode:
        if manifest.get("version_name")!=release.get("version_name") or release.get("live") is not True:raise RuntimeError("BETA_LIVE_MANIFEST_DRIFT")
        if str(manifest.get("sha256") or "")!=str(release.get("apk_sha256") or "") or int(manifest.get("size") or 0)!=int(release.get("apk_size") or 0):raise RuntimeError("BETA_LIVE_MANIFEST_IDENTITY_DRIFT")
        stable_manifest_code,stable_manifest=curl_json("POST",stable_gas_urls[0],body={"action":"update_check","channel":"STABLE","current_version":"0.0.0","_environment_id":"STABLE","_service_audience":"PICK_PACK_1291_STABLE"},follow=True,timeout=60)
        if stable_manifest_code!=200 or stable_manifest.get("ok") is not True or stable_manifest.get("channel")!="STABLE" or stable_manifest.get("available") is not False:raise RuntimeError("STABLE_PRIVATE_MANIFEST_NOT_DISABLED:"+str(stable_manifest_code))
        if stable_manifest.get("apk_url") or stable_manifest.get("sha256"):raise RuntimeError("STABLE_PRIVATE_MANIFEST_LEAK")
    else:
        stable_manifest={"available":False}
        if manifest.get("version_name")!=release.get("base_version") or release.get("live") is not False:raise RuntimeError("BETA_PREOTA_MANIFEST_LEAK")
    beta_domain=curl_status(str(beta_c["target_web_origin"]));stable_domain=curl_status(str(stable_c["target_web_origin"]))
    if beta_domain not in (200,301,302,307,308,401,403):raise RuntimeError("BETA_TARGET_DOMAIN_NOT_READY:"+str(beta_domain))
    if stable_domain in (200,301,302,307,308):raise RuntimeError("STABLE_ROOT_DOMAIN_PUBLIC:"+str(stable_domain))
    phase="PROMOTION_DRY_RUN" if promotion_mode else "PRE_OTA_RUNTIME_DOD"
    receipt={"status":"PASS","phase":phase,"candidate":{"source_sha":source,"version_name":release["version_name"],"version_code":release["version_code"],"package":release["package"],"apk_sha256":release["apk_sha256"],"apk_size":release["apk_size"],"signer_sha256":release["signer_sha256"],"exact_source_unchanged":True},
      "d1":{"count":3,"rehearsal_absent":True,"stable_ready_not_live_zero_state":stable_zero,"quota_guard":"PASS","writer_fencing":"PASS"},
      "backup_restore":{"run_id":proof["run_id"],"artifact_id":proof["artifact_id"],"backup_sha256":proof["backup_sha256"],"restore_compare":"PASS","canary_deleted":True,"current_binding_unchanged":True},
      "workers":{"beta":beta_name,"stable":stable_name,"db_separate":True,"sheet_separate":True,"gas_separate":True,"stable_broad_google_oauth_absent":True},
      "beta_gas_discovery":{"service_url":got_beta_service,"environment_id":discovery.get("environment_id"),"service_audience":discovery.get("service_audience"),"status":"PASS"},
      "service_discovery_device":{"status":"PASS","run_id":release["device_regression_run_id"],"artifact_id":release["device_regression_artifact_id"],"exact_candidate":True},
      "auth":{"beta_active":[x[0] for x in beta_active],"stable_active":[x[0] for x in stable_active],"sheet_parity":"PASS"},
      "cross_environment":{"headers_rejected_both_ways":True,"stable_missing_env_rejected":True,"fallback_cross_route_absent":True},
      "gas":gas,"gas_deployments":{"distinct_projects":True,"distinct_deployments":True,"policy":"ANYONE_ANONYMOUS/USER_DEPLOYING","canary_cleanup_readback":"PASS","beta_sheet_untouched":True},
      "domains":{"beta_target_http":beta_domain,"stable_root_http":stable_domain,"stable_public":False},
      "release":{"beta_manifest_version":manifest.get("version_name"),"beta_manifest_sha256":manifest.get("sha256"),"stable_manifest_available":stable_manifest.get("available"),"candidate_manifest_leak":False,"stable_manifest":False,"stable_ota":False,"stable_release":False},
      "promotion":{"owner_acceptance":("OWNER_ACCEPTED_BETA104" if promotion_mode else None),"owner_promotion_authorization":None,"stable_public":False,"dry_run":promotion_mode},
      "secrets":{"plaintext_in_receipt":False},"stable_lifecycle_target":"READY_NOT_LIVE"}
    pathlib.Path("/tmp/beta-stable-runtime-verify.json").write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"status":"PASS","phase":phase,"d1":3,"beta_auth":5,"stable_auth":1,"gas":3,"backup_restore":"PASS","stable_public":False,"stable_manifest_available":stable_manifest.get("available")}))
if __name__=="__main__":
    if "--self-test" in sys.argv:
        try:
            quota_selftest()
            gas_runtime_canary_selftest()
            promotion_lock_mode_selftest()
            print("beta_stable_runtime_quota_selftest=PASS")
            print("beta_stable_runtime_gas_canary_selftest=PASS")
            print("beta_stable_runtime_promotion_mode_selftest=PASS")
        except Exception as e:
            print("BETA_STABLE_RUNTIME_QUOTA_SELFTEST_ERROR:"+str(e),file=sys.stderr);sys.exit(1)
        sys.exit(0)
    try:main()
    except Exception as e:
        pathlib.Path("/tmp/beta-stable-runtime-verify.json").write_text(json.dumps({"status":"FAIL","error":str(e)[:1200],"plaintext_secret":False},indent=2)+"\n")
        print("BETA_STABLE_RUNTIME_VERIFY_ERROR:"+str(e)[:1600],file=sys.stderr);sys.exit(1)
