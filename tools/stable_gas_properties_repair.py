#!/usr/bin/env python3
import hashlib,json,os,pathlib,secrets,subprocess,sys,urllib.parse,urllib.request,urllib.error
ROOT=pathlib.Path(__file__).resolve().parents[1];SERVICE=ROOT/"service";CF="https://api.cloudflare.com/client/v4"
OWNER_EMAIL="tam95.supra@gmail.com"
def need(n):
    v=os.environ.get(n,"").strip()
    if not v:raise RuntimeError("MISSING_REQUIRED_SECRET:"+n)
    return v
def req(url,method="GET",token=None,body=None,timeout=60):
    data=None if body is None else json.dumps(body,separators=(",",":")).encode();h={"Accept":"application/json"}
    if token:h["Authorization"]="Bearer "+token
    if data is not None:h["Content-Type"]="application/json"
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
def sheet_values(tok,sid,rng):
    code,j=req("https://sheets.googleapis.com/v4/spreadsheets/"+urllib.parse.quote(sid,safe="")+"/values/"+urllib.parse.quote(rng,safe=""),token=tok)
    if code//100!=2:raise RuntimeError("SHEET_READ_FAILED:"+str(code))
    return j.get("values") or []
def contract(tok,sid):
    rows=sheet_values(tok,sid,"'__ENVIRONMENT_CONTRACT'!A:B")
    return {str(r[0]):str(r[1]) for r in rows if len(r)>=2 and str(r[0]).strip()}
def curl_json(url,body=None):
    cmd=["curl","-fsS","-L","--connect-timeout","15","--max-time","60","-H","Content-Type: application/json"]
    inp=None
    if body is not None:cmd+=["--data-binary","@-"];inp=json.dumps(body,separators=(",",":"))
    cmd.append(url)
    p=subprocess.run(cmd,input=inp,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=75)
    if p.returncode:raise RuntimeError("WEBAPP_HTTP_FAILED:"+p.stderr[-600:])
    try:return json.loads(p.stdout)
    except:raise RuntimeError("WEBAPP_BAD_JSON:"+p.stdout[:500])
def d1_rows(db,sql):
    r=cf("/d1/database/"+urllib.parse.quote(db,safe="")+"/query","POST",{"sql":sql})
    if not isinstance(r,list) or not r:raise RuntimeError("D1_QUERY_EMPTY")
    return r[0].get("results") or []
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def bindings(raw):
    out=[]
    for b in raw.get("bindings",[]) or []:
        t=str(b.get("type") or "");n=str(b.get("name") or "");x={"name":n,"type":t}
        if t=="plain_text":x["text"]=str(b.get("text") or "")
        if t=="d1":x["id"]=str(b.get("id") or "")
        if t=="durable_object_namespace":x["class_name"]=str(b.get("class_name") or "")
        out.append(x)
    return sorted(out,key=lambda x:(x["name"],x["type"]))
def d1_state(db):
    return {"accounts":d1_rows(db,"SELECT login_id,role,status,source_row,source_checksum FROM accounts ORDER BY login_id"),
      "authority":d1_rows(db,"SELECT singleton_id,authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state ORDER BY singleton_id"),
      "counts":d1_rows(db,"SELECT (SELECT COUNT(*) FROM events) events,(SELECT COUNT(*) FROM auth_sessions) auth_sessions,(SELECT COUNT(*) FROM auth_web_sessions) auth_web_sessions,(SELECT COUNT(*) FROM sheet_replication_outbox) sheet_outbox,(SELECT COUNT(*) FROM outbound_replication_outbox) outbound_outbox")}
def canary(url,tok,kind,cid):
    base={"action":"stable_runtime_canary","_environment_id":"STABLE","_service_audience":"PICK_PACK_1291_STABLE","google_access_token":tok,"canary_id":cid}
    a=curl_json(url,{**base,"operation":"UPSERT"})
    b=curl_json(url,{**base,"operation":"UPSERT"})
    c=curl_json(url,{**base,"operation":"CLEANUP"})
    d=curl_json(url,{**base,"operation":"CLEANUP"})
    if a.get("ok") is not True or a.get("idempotent") is not False or a.get("kind")!=kind:raise RuntimeError("CANARY_FIRST_FAILED:"+kind+":"+str(a.get("error")))
    if b.get("ok") is not True or b.get("idempotent") is not True:raise RuntimeError("CANARY_REPLAY_FAILED:"+kind)
    if c.get("ok") is not True or c.get("cleanup") is not True:raise RuntimeError("CANARY_CLEANUP_FAILED:"+kind)
    if d.get("ok") is not True or d.get("idempotent") is not True:raise RuntimeError("CANARY_CLEANUP_REPLAY_FAILED:"+kind)
def main():
    cfg=json.loads((ROOT/"ops/stable-private-provision-request.json").read_text())
    if cfg.get("environment")!="STABLE" or cfg.get("stable_public_activation") is not False or cfg.get("mode")!="GAS_PROPERTIES_REPAIR":
        raise RuntimeError("GAS_PROPERTIES_REPAIR_REQUEST_FAIL_CLOSED")
    tok=oauth();print("::add-mask::"+tok)
    name=str(cfg["target_worker_name"]);raw=cf("/workers/scripts/"+urllib.parse.quote(name,safe="")+"/settings") or {};before_bind=bindings(raw)
    by={x["name"]:x for x in before_bind}
    if (by.get("ENVIRONMENT_ID") or {}).get("text")!="STABLE" or (by.get("SERVICE_AUDIENCE") or {}).get("text")!="PICK_PACK_1291_STABLE":raise RuntimeError("STABLE_WORKER_ENV_DRIFT")
    db=str((by.get("DB") or {}).get("id") or "");gen=str((by.get("SERVICE_GENERATION") or {}).get("text") or "")
    if not db or not gen:raise RuntimeError("STABLE_WORKER_BINDING_INCOMPLETE")
    secret_names={x["name"] for x in before_bind if x["type"]=="secret_text"}
    if not {"SERVICE_TOKEN_SECRET","M1_ADMIN_TOKEN","GAS_BRIDGE_SHARED_SECRET"}.issubset(secret_names):raise RuntimeError("STABLE_SECRET_BINDING_MISSING")
    before_d1=d1_state(db);before_hash=digest(before_d1)
    primary=contract(tok,cfg["stable_primary_sheet_id"]);outbound=contract(tok,cfg["stable_outbound_sheet_id"]);dr=contract(tok,cfg["stable_dr_sheet_id"])
    urls={"PRIMARY":primary.get("gas_web_url",""),"OUTBOUND":outbound.get("gas_web_url",""),"DR":dr.get("gas_web_url","")}
    if any(not u.startswith("https://script.google.com/") for u in urls.values()):raise RuntimeError("STABLE_GAS_URL_MISSING")
    og=curl_json(urls["OUTBOUND"]);dg=curl_json(urls["DR"])
    if og.get("provisioned") is True or dg.get("provisioned") is True:raise RuntimeError("GAS_ALREADY_PROVISIONED_UNEXPECTED")
    bridge=secrets.token_urlsafe(48);print("::add-mask::"+bridge)
    # Rotate only the Stable bridge secret; do not touch code, D1, vars, or other secrets.
    wc={"name":name,"main":"src/entry_product.ts","compatibility_date":str(raw.get("compatibility_date") or "2026-08-08"),
      "vars":{k:(by.get(k) or {}).get("text","") for k in ["SERVICE_GENERATION","ENVIRONMENT_ID","SERVICE_AUDIENCE","GAS_API_URL","OUTBOUND_GAS_API_URL","DR_GAS_API_URL","DR_TARGET_ID","GOOGLE_SOURCE_SHEET_ID","GOOGLE_OUTBOUND_SHEET_ID"]},
      "d1_databases":[{"binding":"DB","database_name":cfg["target_d1_name"],"database_id":db,"migrations_dir":"migrations"}]}
    p=SERVICE/"wrangler.stable.secretrepair.generated.jsonc";p.write_text(json.dumps(wc,indent=2)+"\n")
    try:
        proc=subprocess.run(["npx","wrangler","secret","put","GAS_BRIDGE_SHARED_SECRET","--config",str(p.name)],cwd=SERVICE,input=bridge+"\n",text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
        if proc.returncode:raise RuntimeError("WRANGLER_SECRET_PUT_FAILED:"+"\n".join(proc.stdout.splitlines()[-30:])[:2000])
    finally:p.unlink(missing_ok=True)
    common={"google_access_token":tok,"bridge_secret":bridge,"_environment_id":"STABLE","_service_audience":"PICK_PACK_1291_STABLE"}
    o=curl_json(urls["OUTBOUND"],{"action":"stable_bound_provision",**common})
    d=curl_json(urls["DR"],{"action":"stable_bound_provision",**common})
    sub=str((cf("/workers/subdomain") or {}).get("subdomain") or "");service_url=f"https://{name}.{sub}.workers.dev"
    pr=curl_json(urls["PRIMARY"],{"action":"stable_environment_provision",**common,"service_url":service_url,"service_generation":gen,"outbound_gas_url":urls["OUTBOUND"]})
    for label,j in [("OUTBOUND",o),("DR",d),("PRIMARY",pr)]:
        if j.get("ok") is not True:raise RuntimeError("GAS_PROPERTIES_PROVISION_FAILED:"+label+":"+str(j.get("error")))
    cid="__CI_STABLE_CANARY_"+str(os.environ.get("GITHUB_RUN_ID","repair"))
    canary(urls["PRIMARY"],tok,"PRIMARY",cid);canary(urls["OUTBOUND"],tok,"OUTBOUND",cid);canary(urls["DR"],tok,"DR",cid)
    after_raw=cf("/workers/scripts/"+urllib.parse.quote(name,safe="")+"/settings") or {};after_bind=bindings(after_raw)
    after_secret_names={x["name"] for x in after_bind if x["type"]=="secret_text"}
    if before_bind!=after_bind:raise RuntimeError("NONSECRET_BINDINGS_CHANGED_DURING_GAS_REPAIR")
    if secret_names!=after_secret_names:raise RuntimeError("SECRET_BINDING_NAMES_CHANGED_DURING_GAS_REPAIR")
    after_d1=d1_state(db);after_hash=digest(after_d1)
    if before_hash!=after_hash:raise RuntimeError("D1_CHANGED_DURING_GAS_REPAIR")
    rec={"status":"PASS","mode":"GAS_PROPERTIES_REPAIR","environment":"STABLE","stable_public_activation":False,
      "bridge_secret_rotated":True,"bridge_secret_persisted_in_receipt":False,"d1_changed":False,"auth_changed":False,
      "nonsecret_bindings_changed":False,"secret_binding_names_changed":False,"gas_properties":{"primary":"PASS","outbound":"PASS","dr":"PASS"},
      "canary_replay_cleanup":{"primary":"PASS","outbound":"PASS","dr":"PASS"}}
    pathlib.Path("/tmp/stable-private-provision-receipt.json").write_text(json.dumps(rec,indent=2)+"\n")
    print(json.dumps(rec))
if __name__=="__main__":
    try:main()
    except Exception as e:
        pathlib.Path("/tmp/stable-private-provision-receipt.json").write_text(json.dumps({"status":"FAIL","mode":"GAS_PROPERTIES_REPAIR","error":str(e)[:1400],"stable_public_activation":False},indent=2)+"\n")
        print("STABLE_GAS_PROPERTIES_REPAIR_ERROR:"+str(e)[:1800],file=sys.stderr);sys.exit(1)
