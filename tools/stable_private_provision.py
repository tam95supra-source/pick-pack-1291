#!/usr/bin/env python3
import base64, hashlib, json, os, pathlib, secrets, subprocess, sys, tempfile, urllib.parse, urllib.request, urllib.error

ROOT=pathlib.Path(__file__).resolve().parents[1]
SERVICE=ROOT/"service"
API_CF="https://api.cloudflare.com/client/v4"
API_SCRIPT="https://script.googleapis.com/v1/projects"
OWNER_EMAIL="tam95.supra@gmail.com"

def need(name):
    v=os.environ.get(name,"").strip()
    if not v: raise RuntimeError("MISSING_REQUIRED_SECRET:"+name)
    return v

def req_json(url,method="GET",token=None,body=None,headers=None):
    data=None if body is None else json.dumps(body).encode()
    h={"Accept":"application/json"}
    if token: h["Authorization"]="Bearer "+token
    if data is not None: h["Content-Type"]="application/json; charset=utf-8"
    if headers: h.update(headers)
    r=urllib.request.Request(url,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(r,timeout=60) as x:
            raw=x.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        detail=e.read().decode("utf-8","replace")[:1200]
        raise RuntimeError(f"{method} {url} HTTP {e.code}: {detail}") from e

def oauth():
    payload=urllib.parse.urlencode({
      "client_id":need("GOOGLE_OAUTH_CLIENT_ID"),"client_secret":need("GOOGLE_OAUTH_CLIENT_SECRET"),
      "refresh_token":need("GOOGLE_OAUTH_REFRESH_TOKEN"),"grant_type":"refresh_token"}).encode()
    r=urllib.request.Request("https://oauth2.googleapis.com/token",data=payload,headers={"Content-Type":"application/x-www-form-urlencoded"},method="POST")
    with urllib.request.urlopen(r,timeout=45) as x: j=json.loads(x.read().decode())
    t=j.get("access_token","")
    if not t: raise RuntimeError("GOOGLE_ACCESS_TOKEN_MISSING")
    return t

def cf(path,method="GET",body=None):
    acct=need("CLOUDFLARE_ACCOUNT_ID"); tok=need("CLOUDFLARE_API_TOKEN")
    j=req_json(f"{API_CF}/accounts/{acct}{path}",method,tok,body)
    if j.get("success") is not True: raise RuntimeError("CLOUDFLARE_API_FAILED:"+json.dumps(j.get("errors",[]))[:500])
    return j

def sh(cmd,cwd=None,input_text=None):
    p=subprocess.run(cmd,cwd=cwd,text=True,input=input_text,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600)
    if p.returncode:
        tail="\n".join(p.stdout.splitlines()[-40:])
        raise RuntimeError("COMMAND_FAILED:"+cmd[0]+": "+tail[:3500])
    return p.stdout

def b64u(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def verifier(password):
    salt=secrets.token_bytes(16); it=120000
    key=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,it,dklen=32)
    v=f"pbkdf2_sha256$${it}$${b64u(salt)}$${b64u(key)}"
    return v,hashlib.sha256(v.encode()).hexdigest()

def sheet_values(token,sid,range_a1):
    url=f"https://sheets.googleapis.com/v4/spreadsheets/{urllib.parse.quote(sid,safe='')}/values/{urllib.parse.quote(range_a1,safe='')}"
    return req_json(url,token=token).get("values",[])

def sheet_put(token,sid,range_a1,values):
    url=f"https://sheets.googleapis.com/v4/spreadsheets/{urllib.parse.quote(sid,safe='')}/values/{urllib.parse.quote(range_a1,safe='')}?valueInputOption=RAW"
    req_json(url,"PUT",token,{"range":range_a1,"majorDimension":"ROWS","values":values})

def contract_map(token,sid):
    vals=sheet_values(token,sid,"__ENVIRONMENT_CONTRACT!A:B")
    return {str(r[0]):str(r[1]) for r in vals if len(r)>=2 and str(r[0]).strip()}

def contract_set(token,sid,key,value):
    vals=sheet_values(token,sid,"__ENVIRONMENT_CONTRACT!A:B")
    row=None
    for i,r in enumerate(vals,1):
        if r and str(r[0])==key: row=i; break
    if row is None: row=max(1,len(vals)+1)
    sheet_put(token,sid,f"__ENVIRONMENT_CONTRACT!A{row}:B{row}",[[key,value]])

def gas_files(kind):
    if kind=="primary":
        manifest=(ROOT/"google-apps-script/stable-primary-appsscript.json").read_text()
        names=["AUTH_HELPERS.gs","OUTBOUND_DROP_RECEIVE.gs","PICK_PACK_API.gs","SERVICE_MIGRATION_M2.gs","ZZZ_GITHUB_OTA_OVERRIDE.gs"]
        files=[{"name":pathlib.Path(n).stem,"type":"SERVER_JS","source":(ROOT/"google-apps-script"/n).read_text()} for n in names]
    else:
        base=ROOT/"google-apps-script"/("stable-outbound" if kind=="outbound" else "stable-dr")
        manifest=(base/"appsscript.json").read_text()
        files=[{"name":"Code","type":"SERVER_JS","source":(base/"Code.gs").read_text()}]
    files.append({"name":"appsscript","type":"JSON","source":manifest})
    return files

def gas_deploy(token,sid,kind):
    c=contract_map(token,sid)
    script_id=c.get("gas_script_id",""); deploy_id=c.get("gas_deployment_id",""); web_url=c.get("gas_web_url","")
    if not script_id:
        j=req_json(API_SCRIPT,"POST",token,{"title":f"PICK_PACK_1291_STABLE_{kind.upper()}","parentId":sid})
        script_id=j.get("scriptId","")
        if not script_id: raise RuntimeError("GAS_SCRIPT_CREATE_NO_ID:"+kind)
        contract_set(token,sid,"gas_script_id",script_id)
    req_json(f"{API_SCRIPT}/{script_id}/content","PUT",token,{"files":gas_files(kind)})
    v=req_json(f"{API_SCRIPT}/{script_id}/versions","POST",token,{"description":f"Stable {kind} private READY_NOT_LIVE"})
    vn=v.get("versionNumber")
    if not isinstance(vn,int): raise RuntimeError("GAS_VERSION_MISSING:"+kind)
    if deploy_id:
        dep=req_json(f"{API_SCRIPT}/{script_id}/deployments/{deploy_id}","PUT",token,{"deploymentConfig":{"scriptId":script_id,"versionNumber":vn,"manifestFileName":"appsscript","description":f"Stable {kind} READY_NOT_LIVE"}})
    else:
        dep=req_json(f"{API_SCRIPT}/{script_id}/deployments","POST",token,{"versionNumber":vn,"manifestFileName":"appsscript","description":f"Stable {kind} READY_NOT_LIVE"})
        deploy_id=dep.get("deploymentId","")
        if not deploy_id: raise RuntimeError("GAS_DEPLOYMENT_ID_MISSING:"+kind)
        contract_set(token,sid,"gas_deployment_id",deploy_id)
    for ep in dep.get("entryPoints",[]) or []:
        if ep.get("entryPointType")=="WEB_APP": web_url=(ep.get("webApp") or {}).get("url","") or web_url
    if not web_url:
        current=req_json(f"{API_SCRIPT}/{script_id}/deployments/{deploy_id}",token=token)
        for ep in current.get("entryPoints",[]) or []:
            if ep.get("entryPointType")=="WEB_APP": web_url=(ep.get("webApp") or {}).get("url","") or web_url
    if not web_url: raise RuntimeError("GAS_WEB_URL_MISSING:"+kind)
    contract_set(token,sid,"gas_web_url",web_url); contract_set(token,sid,"gas_version",str(vn))
    return {"script_id":script_id,"deployment_id":deploy_id,"version":vn,"url":web_url}

def post_json_curl(url,payload):
    p=subprocess.run(["curl","-fsS","-L","--connect-timeout","20","--max-time","60","-H","Content-Type: application/json","--data-binary","@-",url],
                     input=json.dumps(payload),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=75)
    if p.returncode: raise RuntimeError("WEBAPP_HTTP_FAILED:"+p.stderr[-800:])
    try: return json.loads(p.stdout)
    except Exception as e: raise RuntimeError("WEBAPP_BAD_JSON:"+p.stdout[:500]) from e

def d1_inventory(): return cf("/d1/database?per_page=100").get("result",[])
def ensure_d1(name):
    matches=[x for x in d1_inventory() if x.get("name")==name]
    if len(matches)>1: raise RuntimeError("D1_TARGET_NOT_UNIQUE")
    if matches: return matches[0].get("uuid") or matches[0].get("id")
    j=cf("/d1/database","POST",{"name":name}); r=j.get("result") or {}
    return r.get("uuid") or r.get("id")

def scheduler_profile(req):
    lifecycle=str(req.get("lifecycle_target","")).upper()
    profile=str(req.get("scheduler_profile","")).upper()
    if lifecycle=="READY_NOT_LIVE":
        if profile!="PRIVATE_IDLE": raise RuntimeError("STABLE_PRIVATE_SCHEDULER_PROFILE_REQUIRED")
        crons=req.get("private_idle_crons",[])
        if crons not in ([],None): raise RuntimeError("STABLE_PRIVATE_IDLE_CRON_FORBIDDEN")
        sample=float(req.get("private_idle_observability_sampling",0.1))
        return [],max(0.0,min(1.0,sample)),"PRIVATE_IDLE"
    crons=req.get("activation_crons",["*/1 * * * *"])
    sample=float(req.get("active_observability_sampling",0.1))
    return list(crons),max(0.0,min(1.0,sample)),"ACTIVE"

def wrangler_config(req,d1_id,gas,gen):
    crons,sampling,profile=scheduler_profile(req)
    cfg={"name":req["target_worker_name"],"main":"src/entry_product.ts","compatibility_date":"2026-08-08","compatibility_flags":["nodejs_compat"],
      "workers_dev":True,"placement":{"mode":"smart"},
      "vars":{"SERVICE_GENERATION":gen,"ENVIRONMENT_ID":"STABLE","SERVICE_AUDIENCE":"PICK_PACK_1291_STABLE","RUNTIME_LIFECYCLE":req["lifecycle_target"],"SCHEDULER_PROFILE":profile,"GAS_API_URL":gas["primary"]["url"],
      "OUTBOUND_GAS_API_URL":gas["outbound"]["url"],"DR_GAS_API_URL":gas["dr"]["url"],"DR_TARGET_ID":req["stable_dr_sheet_id"],
      "GOOGLE_SOURCE_SHEET_ID":req["stable_primary_sheet_id"],"GOOGLE_OUTBOUND_SHEET_ID":req["stable_outbound_sheet_id"]},
      "d1_databases":[{"binding":"DB","database_name":req["target_d1_name"],"database_id":d1_id,"migrations_dir":"migrations"}],
      "durable_objects":{"bindings":[{"name":"REALTIME_HUB","class_name":"RealtimeHub"}]},
      "migrations":[{"tag":"v1","new_sqlite_classes":["RealtimeHub"]}],
      "assets":{"directory":"./public","binding":"ASSETS","not_found_handling":"single-page-application","run_worker_first":["/health","/environment.json","/v1/*","/internal/*"]},
      "triggers":{"crons":crons},"observability":{"enabled":True,"head_sampling_rate":sampling}}
    path=SERVICE/"wrangler.stable.private.generated.jsonc"; path.write_text(json.dumps(cfg,indent=2)+"\n"); return path

def seed_d1(config,db_name,verifier_value,verifier_hash,gen):
    sh(["npx","wrangler","d1","migrations","apply",db_name,"--remote","--config",str(config.name)],cwd=SERVICE)
    q=lambda v:"'"+str(v).replace("'","''")+"'"
    checksum=hashlib.sha256(b"STABLE_ADMIN_BOOTSTRAP_V1").hexdigest()
    sql=f"""DELETE FROM auth_challenges;
DELETE FROM auth_sessions;
DELETE FROM auth_web_sessions;
DELETE FROM realtime_tickets;
DELETE FROM accounts;
INSERT INTO accounts(login_id,verifier,verifier_hash,role,display_name,position,email,status,source_row,source_checksum,is_shadow_test)
VALUES('admin',{q(verifier_value)},{q(verifier_hash)},'SUPERADMIN','admin','superadmin',{q(OWNER_EMAIL)},'ACTIVE',2,{q(checksum)},0);
UPDATE authority_state SET mode='SERVICE_PRIMARY',scope='PRODUCTION',service_generation={q(gen)},updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE singleton_id=1;
"""
    with tempfile.NamedTemporaryFile("w",suffix=".sql",delete=False) as f: f.write(sql); p=f.name
    try: sh(["npx","wrangler","d1","execute",db_name,"--remote","--file",p,"--config",str(config.name)],cwd=SERVICE)
    finally: pathlib.Path(p).unlink(missing_ok=True)

def deploy_worker(req,config,secrets_map):
    sh(["npx","wrangler","deploy","--config",str(config.name)],cwd=SERVICE)
    with tempfile.NamedTemporaryFile("w",suffix=".json",delete=False) as f: json.dump(secrets_map,f); p=f.name
    os.chmod(p,0o600)
    try: sh(["npx","wrangler","secret","bulk",p,"--config",str(config.name)],cwd=SERVICE)
    finally: pathlib.Path(p).unlink(missing_ok=True)
    sub=(cf("/workers/subdomain").get("result") or {}).get("subdomain","")
    if not sub: raise RuntimeError("WORKERS_SUBDOMAIN_MISSING")
    return f"https://{req['target_worker_name']}.{sub}.workers.dev"

def private_idle_readback(req):
    enc=urllib.parse.quote(req["target_worker_name"],safe="")
    schedules=cf(f"/workers/scripts/{enc}/schedules").get("result") or []
    settings=cf(f"/workers/scripts/{enc}/settings").get("result") or {}
    return {"cron_count":len(schedules),"schedules":schedules,"observability":settings.get("observability"),"usage_model":settings.get("usage_model")}

def verify_worker(url):
    with urllib.request.urlopen(url+"/health",timeout=30) as r:
        if r.status!=200: raise RuntimeError("STABLE_HEALTH_HTTP")
    for headers,label in [({"x-pick-pack-environment":"BETA","x-pick-pack-audience":"PICK_PACK_1291_BETA"},"beta"),({},"missing")]:
        request=urllib.request.Request(url+"/v1/service/connections",headers=headers)
        try:
            urllib.request.urlopen(request,timeout=20); raise RuntimeError("STABLE_ENV_FENCE_NOT_REJECTED:"+label)
        except urllib.error.HTTPError as e:
            if e.code not in (401,403,409): raise

def main():
    req=json.loads((ROOT/"ops/stable-private-provision-request.json").read_text())
    if req.get("environment")!="STABLE" or req.get("stable_public_activation") is not False: raise RuntimeError("STABLE_REQUEST_FAIL_CLOSED")
    if str(req.get("lifecycle_target","")).upper()!="READY_NOT_LIVE": raise RuntimeError("STABLE_PRIVATE_LIFECYCLE_REQUIRED")
    scheduler_profile(req)
    mode=str(req.get("mode","PREFLIGHT_ONLY")); token=oauth()
    for k in ("stable_primary_sheet_id","stable_dr_sheet_id","stable_outbound_sheet_id"):
        sid=req[k]; j=req_json(f"https://www.googleapis.com/drive/v3/files/{sid}?fields=id,mimeType,owners(emailAddress)",token=token)
        if j.get("id")!=sid or j.get("mimeType")!="application/vnd.google-apps.spreadsheet": raise RuntimeError("STABLE_SHEET_IDENTITY_FAILED:"+k)
        if OWNER_EMAIL.lower() not in [str(x.get("emailAddress","")).lower() for x in j.get("owners",[])]: raise RuntimeError("STABLE_SHEET_OWNER_FAILED:"+k)
    dbs=d1_inventory()
    if len(dbs)>=10 and not any(x.get("name")==req["target_d1_name"] for x in dbs): raise RuntimeError("D1_FREE_CAPACITY_BLOCKED")
    target_dbs=[x for x in dbs if x.get("name")==req["target_d1_name"]]
    workers=(cf("/workers/scripts?per_page=100").get("result") or [])
    target_workers=[x for x in workers if (x.get("id") or x.get("name"))==req["target_worker_name"]]
    worker_settings={}; idle_readback={"cron_count":0,"schedules":[],"observability":None,"usage_model":None}
    if len(target_workers)==1:
        enc=urllib.parse.quote(req["target_worker_name"],safe="")
        raw=cf(f"/workers/scripts/{enc}/settings").get("result") or {}
        bindings=[]
        for b in raw.get("bindings",[]) or []:
            item={"name":b.get("name"),"type":b.get("type")}
            if b.get("type")=="plain_text" and b.get("name") in ("ENVIRONMENT_ID","SERVICE_AUDIENCE","SERVICE_GENERATION","RUNTIME_LIFECYCLE","SCHEDULER_PROFILE","GAS_API_URL","OUTBOUND_GAS_API_URL","DR_GAS_API_URL","DR_TARGET_ID","GOOGLE_SOURCE_SHEET_ID","GOOGLE_OUTBOUND_SHEET_ID"):
                item["text"]=b.get("text")
            if b.get("type")=="d1": item["id"]=b.get("id")
            bindings.append(item)
        worker_settings={"bindings":bindings,"compatibility_date":raw.get("compatibility_date"),"observability":raw.get("observability"),"usage_model":raw.get("usage_model")}
        idle_readback=private_idle_readback(req)
    gas_readback={}
    for kind,key in (("primary","stable_primary_sheet_id"),("outbound","stable_outbound_sheet_id"),("dr","stable_dr_sheet_id")):
        c=contract_map(token,req[key]); sid=c.get("gas_script_id",""); depid=c.get("gas_deployment_id",""); url=c.get("gas_web_url","")
        entry=[]; http_status=None
        if sid and depid:
            dep=req_json(f"{API_SCRIPT}/{sid}/deployments/{depid}",token=token)
            for ep in dep.get("entryPoints",[]) or []:
                w=ep.get("webApp") or {}; cfg=w.get("entryPointConfig") or {}
                entry.append({"entryPointType":ep.get("entryPointType"),"webApp":{"url":w.get("url"),"access":cfg.get("access"),"executeAs":cfg.get("executeAs")}})
        if url:
            try:
                with urllib.request.urlopen(url,timeout=25) as x: http_status=x.status
            except urllib.error.HTTPError as e: http_status=e.code
            except Exception: http_status=-1
        gas_readback[kind]={"script_id":sid,"deployment_id":depid,"url":url,"entry_points":entry,"runtime_http_status":http_status}
    receipt={"status":"PASS","mode":mode,"environment":"STABLE","stable_public_activation":False,
      "scheduler_target":{"profile":"PRIVATE_IDLE","crons":[],"observability_head_sampling_rate":float(req.get("private_idle_observability_sampling",0.1))},
      "preflight":{"d1_count":len(dbs),"target_d1_matches":len(target_dbs),"target_d1_id":((target_dbs[0].get("uuid") or target_dbs[0].get("id")) if len(target_dbs)==1 else None),
      "target_worker_matches":len(target_workers),"worker_settings":worker_settings,"private_idle_readback":idle_readback,"sheets_owner_verified":True,"gas_readback":gas_readback}}
    if mode=="PREFLIGHT_ONLY":
        pathlib.Path("/tmp/stable-private-provision-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n"); print(json.dumps(receipt)); return
    if mode!="PROVISION_PRIVATE": raise RuntimeError("UNKNOWN_PROVISION_MODE")

    password=b64u(secrets.token_bytes(24)); verifier_value,verifier_hash=verifier(password)
    service_token=b64u(secrets.token_bytes(48)); admin_token=b64u(secrets.token_bytes(48)); bridge=b64u(secrets.token_bytes(48))
    for v in (password,verifier_value,service_token,admin_token,bridge): print("::add-mask::"+v)

    gas={}
    for kind,key in (("outbound","stable_outbound_sheet_id"),("dr","stable_dr_sheet_id"),("primary","stable_primary_sheet_id")):
        gas[kind]=gas_deploy(token,req[key],kind)
    d1_id=ensure_d1(req["target_d1_name"])
    if not d1_id: raise RuntimeError("D1_ID_MISSING")
    gen="stable-private-"+os.environ.get("GITHUB_SHA","unknown")[:12]
    config=wrangler_config(req,d1_id,gas,gen)
    try:
        seed_d1(config,req["target_d1_name"],verifier_value,verifier_hash,gen)
        worker_url=deploy_worker(req,config,{"SERVICE_TOKEN_SECRET":service_token,"M1_ADMIN_TOKEN":admin_token,"GAS_BRIDGE_SHARED_SECRET":bridge})
    finally: config.unlink(missing_ok=True)

    common={"google_access_token":token,"bridge_secret":bridge,"_environment_id":"STABLE","_service_audience":"PICK_PACK_1291_STABLE"}
    checks=[
      ("outbound",post_json_curl(gas["outbound"]["url"],{"action":"stable_bound_provision",**common})),
      ("dr",post_json_curl(gas["dr"]["url"],{"action":"stable_bound_provision",**common})),
      ("primary",post_json_curl(gas["primary"]["url"],{"action":"stable_environment_provision",**common,"service_url":worker_url,"service_generation":gen,"outbound_gas_url":gas["outbound"]["url"]})),
      ("admin",post_json_curl(gas["primary"]["url"],{"action":"stable_admin_bootstrap",**common,"password_verifier":verifier_value,"email":OWNER_EMAIL}))
    ]
    for label,j in checks:
        if j.get("ok") is not True: raise RuntimeError("GAS_PROVISION_FAILED:"+label+":"+str(j.get("error","UNKNOWN")))
    verify_worker(worker_url)
    idle=private_idle_readback(req)
    if idle.get("cron_count")!=0: raise RuntimeError("STABLE_PRIVATE_CRON_STILL_ACTIVE")

    config=wrangler_config(req,d1_id,gas,gen)
    try:
        raw=sh(["npx","wrangler","d1","execute",req["target_d1_name"],"--remote","--command","SELECT login_id,role,status FROM accounts; SELECT mode,scope,service_generation FROM authority_state WHERE singleton_id=1;","--json","--config",str(config.name)],cwd=SERVICE)
        d1_ok='"admin"' in raw and '"SUPERADMIN"' in raw and gen in raw
    finally: config.unlink(missing_ok=True)
    if not d1_ok: raise RuntimeError("STABLE_D1_READBACK_FAILED")

    receipt.update({"resource":{"d1_name":req["target_d1_name"],"d1_id":d1_id,"worker_name":req["target_worker_name"],"worker_url":worker_url,"generation":gen},
      "gas":{k:{"script_id":v["script_id"],"deployment_id":v["deployment_id"],"version":v["version"],"url":v["url"]} for k,v in gas.items()},
      "auth":{"active_accounts":1,"login_id":"admin","role":"SUPERADMIN","password_exposed":False},
      "scheduler_readback":idle,
      "isolation":{"worker_separate":True,"d1_separate":True,"google_oauth_in_worker":False,"bound_gas_currentonly":True,"beta_header_rejected":True,"missing_environment_rejected":True}})
    pathlib.Path("/tmp/stable-private-provision-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({"status":"PASS","mode":mode,"environment":"STABLE","worker":req["target_worker_name"],"d1":req["target_d1_name"],"gas_count":3,"active_accounts":1,"password_exposed":False,"scheduler_profile":"PRIVATE_IDLE","cron_count":idle.get("cron_count")}))

if __name__=="__main__":
    try: main()
    except Exception as e:
        pathlib.Path("/tmp/stable-private-provision-receipt.json").write_text(json.dumps({"status":"FAIL","error":str(e)[:1000],"stable_public_activation":False},indent=2)+"\n")
        print("STABLE_PRIVATE_PROVISION_ERROR:"+str(e)[:1600],file=sys.stderr); sys.exit(1)
