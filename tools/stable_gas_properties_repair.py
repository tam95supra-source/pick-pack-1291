#!/usr/bin/env python3
import base64,hashlib,hmac,json,os,pathlib,subprocess,sys,urllib.error,urllib.parse,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
SERVICE=ROOT/"service"
CF="https://api.cloudflare.com/client/v4"

def need(n):
    v=os.environ.get(n,"").strip()
    if not v: raise RuntimeError("MISSING_REQUIRED_SECRET:"+n)
    return v

def req(url,method="GET",token=None,body=None,timeout=60):
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
    code,j=req(f"{CF}/accounts/{need('CLOUDFLARE_ACCOUNT_ID')}{path}",method,need("CLOUDFLARE_API_TOKEN"),body)
    if code//100!=2 or j.get("success") is not True:
        raise RuntimeError("CF_API_FAILED:"+str(code)+":"+json.dumps(j.get("errors",j))[:500])
    return j.get("result")

def oauth():
    data=urllib.parse.urlencode({
      "client_id":need("GOOGLE_OAUTH_CLIENT_ID"),
      "client_secret":need("GOOGLE_OAUTH_CLIENT_SECRET"),
      "refresh_token":need("GOOGLE_OAUTH_REFRESH_TOKEN"),
      "grant_type":"refresh_token"}).encode()
    r=urllib.request.Request("https://oauth2.googleapis.com/token",data=data,headers={"Content-Type":"application/x-www-form-urlencoded"},method="POST")
    with urllib.request.urlopen(r,timeout=45) as x:j=json.loads(x.read().decode())
    t=str(j.get("access_token",""))
    if not t:raise RuntimeError("GOOGLE_TOKEN_MISSING")
    return t

def sheet_values(tok,sid,rng):
    code,j=req("https://sheets.googleapis.com/v4/spreadsheets/"+urllib.parse.quote(sid,safe="")+"/values/"+urllib.parse.quote(rng,safe=""),token=tok)
    if code//100!=2:raise RuntimeError("SHEET_READ_FAILED:"+str(code))
    return j.get("values") or []

def sheet_titles(tok,sid):
    code,j=req("https://sheets.googleapis.com/v4/spreadsheets/"+urllib.parse.quote(sid,safe="")+"?fields=sheets.properties.title",token=tok)
    if code//100!=2:raise RuntimeError("SHEET_METADATA_FAILED:"+str(code))
    return [str((x.get("properties") or {}).get("title") or "") for x in j.get("sheets",[])]

def contract(tok,sid):
    rows=sheet_values(tok,sid,"'__ENVIRONMENT_CONTRACT'!A:B")
    return {str(r[0]):str(r[1]) for r in rows if len(r)>=2 and str(r[0]).strip()}

def curl_json(url,body=None):
    cmd=["curl","-fsS","-L","--connect-timeout","15","--max-time","60"]
    inp=None
    if body is not None:
        cmd+=["-H","Content-Type: application/json","--data-binary","@-"]
        inp=json.dumps(body,separators=(",",":"))
    cmd.append(url)
    p=subprocess.run(cmd,input=inp,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=75)
    if p.returncode:raise RuntimeError("WEBAPP_HTTP_FAILED:"+p.stderr[-600:])
    try:return json.loads(p.stdout)
    except:raise RuntimeError("WEBAPP_BAD_JSON:"+p.stdout[:500])

def d1_rows(db,sql):
    r=cf("/d1/database/"+urllib.parse.quote(db,safe="")+"/query","POST",{"sql":sql})
    if not isinstance(r,list) or not r:raise RuntimeError("D1_QUERY_EMPTY")
    if r[0].get("success") is False:raise RuntimeError("D1_QUERY_FAILED")
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
    return {
      "accounts":d1_rows(db,"SELECT login_id,role,status,source_row,source_checksum FROM accounts ORDER BY login_id"),
      "authority":d1_rows(db,"SELECT singleton_id,authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state ORDER BY singleton_id"),
      "counts":d1_rows(db,"SELECT (SELECT COUNT(*) FROM events) events,(SELECT COUNT(*) FROM auth_sessions) auth_sessions,(SELECT COUNT(*) FROM auth_web_sessions) auth_web_sessions,(SELECT COUNT(*) FROM sheet_replication_outbox) sheet_outbox,(SELECT COUNT(*) FROM outbound_replication_outbox) outbound_outbox")}

def active_accounts(db):
    return sorted((str(x.get("login_id")),str(x.get("role"))) for x in d1_rows(db,"SELECT login_id,role FROM accounts WHERE status='ACTIVE' ORDER BY login_id"))

def derived_bridge(transaction_id,worker_name):
    seed=hashlib.sha256((need("GOOGLE_OAUTH_REFRESH_TOKEN")+"\0"+need("CLOUDFLARE_API_TOKEN")).encode()).digest()
    raw=hmac.new(seed,("PICK_PACK_1291|STABLE|GAS_BRIDGE|"+transaction_id+"|"+worker_name).encode(),hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

def bridge_probe(url,kind,secret,environment="STABLE"):
    action="service_sheet_bridge" if kind=="PRIMARY" else "stable_bound_bridge"
    good=curl_json(url,{"action":action,"operation":"__probe__","_environment_id":environment,"_service_audience":"PICK_PACK_1291_STABLE","_bridge_secret":secret})
    expected="STABLE_BRIDGE_OPERATION_UNKNOWN" if kind=="PRIMARY" else "BRIDGE_OPERATION_UNKNOWN"
    if good.get("ok") is not False or good.get("error")!=expected:
        raise RuntimeError("BRIDGE_SECRET_PROBE_FAILED:"+kind+":"+str(good.get("error")))
    for label,bad_secret,bad_env in [("missing","",environment),("wrong","x"*48,environment),("wrong_env",secret,"BETA")]:
        bad=curl_json(url,{"action":action,"operation":"__probe__","_environment_id":bad_env,"_service_audience":"PICK_PACK_1291_STABLE","_bridge_secret":bad_secret})
        if bad.get("ok") is not False:
            raise RuntimeError("BRIDGE_NEGATIVE_ACCEPTED:"+kind+":"+label)

def canary(url,tok,kind,cid):
    base={"action":"stable_runtime_canary","_environment_id":"STABLE","_service_audience":"PICK_PACK_1291_STABLE","google_access_token":tok,"canary_id":cid}
    primary_error=None
    try:
        a=curl_json(url,{**base,"operation":"UPSERT"})
        if a.get("ok") is not True or a.get("idempotent") is not False or a.get("kind")!=kind or a.get("properties_ok") is not True or a.get("bound_sheet") is not True:
            raise RuntimeError("CANARY_FIRST_FAILED:"+kind+":"+str(a.get("error") or "ASSERT"))
        b=curl_json(url,{**base,"operation":"UPSERT"})
        if b.get("ok") is not True or b.get("idempotent") is not True:
            raise RuntimeError("CANARY_REPLAY_FAILED:"+kind)
    except Exception as e:
        primary_error=e
    cleanup_error=None
    try:
        c=curl_json(url,{**base,"operation":"CLEANUP"})
        d=curl_json(url,{**base,"operation":"CLEANUP"})
        if c.get("ok") is not True or c.get("cleanup") is not True or d.get("ok") is not True or d.get("idempotent") is not True:
            raise RuntimeError("CANARY_CLEANUP_FAILED:"+kind)
    except Exception as e:
        cleanup_error=e
    if primary_error and cleanup_error:raise RuntimeError(str(primary_error)+";"+str(cleanup_error))
    if primary_error:raise primary_error
    if cleanup_error:raise cleanup_error

def source_guard(cfg):
    expected=str(cfg.get("repair_script_sha256") or "")
    actual=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
    if expected!=actual:raise RuntimeError("REPAIR_SCRIPT_SHA256_MISMATCH")
    commit=str(cfg.get("repair_source_commit") or "")
    if len(commit)!=40:raise RuntimeError("REPAIR_SOURCE_COMMIT_REQUIRED")
    p=subprocess.run(["git","show",commit+":tools/stable_gas_properties_repair.py"],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    if p.returncode or hashlib.sha256(p.stdout).hexdigest()!=actual:raise RuntimeError("REPAIR_SOURCE_COMMIT_MISMATCH")
    accepted=str(cfg.get("accepted_service_source_sha") or "")
    if len(accepted)!=40:raise RuntimeError("ACCEPTED_SERVICE_SOURCE_SHA_REQUIRED")
    if subprocess.run(["git","diff","--quiet",accepted,"HEAD","--","service"],cwd=ROOT).returncode!=0:
        raise RuntimeError("STABLE_SERVICE_SOURCE_NOT_EXACT_ACCEPTED")

def selftest():
    os.environ["GOOGLE_OAUTH_REFRESH_TOKEN"]="test-refresh"
    os.environ["CLOUDFLARE_API_TOKEN"]="test-cf"
    a=derived_bridge("repair-v1","stable-worker")
    b=derived_bridge("repair-v1","stable-worker")
    c=derived_bridge("repair-v2","stable-worker")
    if a!=b or a==c or len(a)<40:raise RuntimeError("DERIVED_SECRET_SELFTEST_FAILED")
    if a in json.dumps({"fingerprint":hashlib.sha256(a.encode()).hexdigest()[:16]}):raise RuntimeError("SECRET_RECEIPT_SELFTEST_FAILED")
    print("stable_gas_properties_repair_selftest=PASS")

def main():
    cfg=json.loads((ROOT/"ops/stable-private-provision-request.json").read_text())
    if cfg.get("environment")!="STABLE" or cfg.get("lifecycle_target")!="READY_NOT_LIVE" or cfg.get("stable_public_activation") is not False or cfg.get("mode")!="GAS_PROPERTIES_REPAIR":
        raise RuntimeError("GAS_PROPERTIES_REPAIR_REQUEST_FAIL_CLOSED")
    tx=str(cfg.get("repair_transaction_id") or "")
    if not tx.startswith("stable-gas-properties-repair-"):raise RuntimeError("REPAIR_TRANSACTION_ID_INVALID")
    source_guard(cfg)
    tok=oauth();print("::add-mask::"+tok)

    env_contract=json.loads((ROOT/"config/environment_contracts.json").read_text())
    beta_cfg=(env_contract.get("environments") or {}).get("BETA") or {}
    beta_name=str(((beta_cfg.get("current_service") or {}).get("worker") or ""))
    if not beta_name:raise RuntimeError("BETA_WORKER_AUTHORITY_MISSING")
    stable_name=str(cfg["target_worker_name"])
    if stable_name==beta_name:raise RuntimeError("STABLE_TARGET_COLLIDES_BETA")

    stable_raw=cf("/workers/scripts/"+urllib.parse.quote(stable_name,safe="")+"/settings") or {}
    beta_raw=cf("/workers/scripts/"+urllib.parse.quote(beta_name,safe="")+"/settings") or {}
    before_stable_bind=bindings(stable_raw);before_beta_bind=bindings(beta_raw)
    sb={x["name"]:x for x in before_stable_bind};bb={x["name"]:x for x in before_beta_bind}
    if (sb.get("ENVIRONMENT_ID") or {}).get("text")!="STABLE" or (sb.get("SERVICE_AUDIENCE") or {}).get("text")!="PICK_PACK_1291_STABLE":
        raise RuntimeError("STABLE_WORKER_ENV_DRIFT")
    if (bb.get("ENVIRONMENT_ID") or {}).get("text")!="BETA" or (bb.get("SERVICE_AUDIENCE") or {}).get("text")!="PICK_PACK_1291_BETA":
        raise RuntimeError("BETA_WORKER_ENV_DRIFT")
    stable_db=str((sb.get("DB") or {}).get("id") or "");beta_db=str((bb.get("DB") or {}).get("id") or "")
    gen=str((sb.get("SERVICE_GENERATION") or {}).get("text") or "")
    if not stable_db or not beta_db or stable_db==beta_db or not gen:raise RuntimeError("D1_ENV_BINDING_INVALID")
    stable_secret_names={x["name"] for x in before_stable_bind if x["type"]=="secret_text"}
    if not {"SERVICE_TOKEN_SECRET","M1_ADMIN_TOKEN","GAS_BRIDGE_SHARED_SECRET"}.issubset(stable_secret_names):
        raise RuntimeError("STABLE_SECRET_BINDING_MISSING")
    if any(x in stable_secret_names for x in {"GOOGLE_OAUTH_CLIENT_ID","GOOGLE_OAUTH_CLIENT_SECRET","GOOGLE_OAUTH_REFRESH_TOKEN"}):
        raise RuntimeError("STABLE_BROAD_GOOGLE_OAUTH_PRESENT")

    before_stable_d1=d1_state(stable_db);before_stable_hash=digest(before_stable_d1)
    before_beta_active=active_accounts(beta_db)
    expected_beta=[("adminbeta","SUPERADMIN"),("admintest","ADMIN"),("user1","USER"),("user2","USER"),("user3","USER")]
    if before_beta_active!=expected_beta:raise RuntimeError("BETA_AUTH_PRECHECK_DRIFT")

    specs=[("PRIMARY","stable_primary_sheet_id"),("OUTBOUND","stable_outbound_sheet_id"),("DR","stable_dr_sheet_id")]
    urls={}
    identities=[]
    for kind,key in specs:
        sid=str(cfg[key]);c=contract(tok,sid)
        if c.get("environment_id")!="STABLE" or c.get("stable_spreadsheet_id")!=sid:
            raise RuntimeError("STABLE_GAS_CONTRACT_IDENTITY_FAILED:"+kind)
        script_id=str(c.get("gas_script_id") or "");dep_id=str(c.get("gas_deployment_id") or "");url=str(c.get("gas_web_url") or "")
        if not script_id or not dep_id or not url.startswith("https://script.google.com/"):
            raise RuntimeError("STABLE_GAS_IDENTITY_MISSING:"+kind)
        urls[kind]=url;identities.append((script_id,dep_id,url,sid))
    if len({x[0] for x in identities})!=3 or len({x[1] for x in identities})!=3 or len({x[2] for x in identities})!=3:
        raise RuntimeError("STABLE_GAS_NOT_DISTINCT")

    bridge=derived_bridge(tx,stable_name)
    fingerprint=hashlib.sha256(bridge.encode()).hexdigest()[:16]
    print("::add-mask::"+bridge)
    common={"google_access_token":tok,"bridge_secret":bridge,"_environment_id":"STABLE","_service_audience":"PICK_PACK_1291_STABLE"}
    sub=str((cf("/workers/subdomain") or {}).get("subdomain") or "")
    if not sub:raise RuntimeError("WORKERS_SUBDOMAIN_MISSING")
    service_url=f"https://{stable_name}.{sub}.workers.dev"

    # Provision GAS first. Partial failure leaves Worker secret untouched; retry derives the same bridge secret.
    results=[
      ("OUTBOUND",curl_json(urls["OUTBOUND"],{"action":"stable_bound_provision",**common})),
      ("DR",curl_json(urls["DR"],{"action":"stable_bound_provision",**common})),
      ("PRIMARY",curl_json(urls["PRIMARY"],{"action":"stable_environment_provision",**common,"service_url":service_url,"service_generation":gen,"outbound_gas_url":urls["OUTBOUND"]}))]
    for label,j in results:
        if j.get("ok") is not True:raise RuntimeError("GAS_PROPERTIES_PROVISION_FAILED:"+label+":"+str(j.get("error")))
    for kind in ("PRIMARY","OUTBOUND","DR"):bridge_probe(urls[kind],kind,bridge)

    # Stable GAS have converged. Rotate only the Stable Worker bridge secret to the exact same transaction-derived value.
    wc={"name":stable_name,"main":"src/entry_product.ts","compatibility_date":str(stable_raw.get("compatibility_date") or "2026-08-08"),
      "vars":{k:(sb.get(k) or {}).get("text","") for k in ["SERVICE_GENERATION","ENVIRONMENT_ID","SERVICE_AUDIENCE","GAS_API_URL","OUTBOUND_GAS_API_URL","DR_GAS_API_URL","DR_TARGET_ID","GOOGLE_SOURCE_SHEET_ID","GOOGLE_OUTBOUND_SHEET_ID"]},
      "d1_databases":[{"binding":"DB","database_name":cfg["target_d1_name"],"database_id":stable_db,"migrations_dir":"migrations"}]}
    p=SERVICE/"wrangler.stable.secretrepair.generated.jsonc";p.write_text(json.dumps(wc,indent=2)+"\n")
    try:
        proc=subprocess.run(["npx","wrangler","secret","put","GAS_BRIDGE_SHARED_SECRET","--config",str(p.name)],cwd=SERVICE,input=bridge+"\n",text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
        if proc.returncode:raise RuntimeError("WRANGLER_SECRET_PUT_FAILED:"+"\n".join(proc.stdout.splitlines()[-30:])[:2000])
    finally:p.unlink(missing_ok=True)

    # Positive, negative, replay/idempotency and cleanup checks.
    for kind in ("PRIMARY","OUTBOUND","DR"):bridge_probe(urls[kind],kind,bridge)
    cid="__CI_STABLE_CANARY_"+str(os.environ.get("GITHUB_RUN_ID","repair"))
    for kind in ("PRIMARY","OUTBOUND","DR"):canary(urls[kind],tok,kind,cid)

    for _,key in specs:
        if "__STABLE_RUNTIME_CANARY" in sheet_titles(tok,str(cfg[key])):
            raise RuntimeError("STABLE_CANARY_CLEANUP_DIRTY:"+key)
    beta_primary_sid=str((bb.get("GOOGLE_SOURCE_SHEET_ID") or {}).get("text") or "")
    beta_outbound_sid=str((bb.get("GOOGLE_OUTBOUND_SHEET_ID") or {}).get("text") or "")
    for sid in [x for x in (beta_primary_sid,beta_outbound_sid) if x]:
        if "__STABLE_RUNTIME_CANARY" in sheet_titles(tok,sid):raise RuntimeError("BETA_CANARY_CROSS_WRITE_DETECTED")
    beta_gas=str((bb.get("GAS_API_URL") or {}).get("text") or "")
    if beta_gas:
        x=curl_json(beta_gas,{"action":"service_sheet_bridge","operation":"__probe__","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA","_bridge_secret":bridge})
        if x.get("ok") is not False:raise RuntimeError("STABLE_BRIDGE_ACCEPTED_BY_BETA")

    after_stable_raw=cf("/workers/scripts/"+urllib.parse.quote(stable_name,safe="")+"/settings") or {}
    after_beta_raw=cf("/workers/scripts/"+urllib.parse.quote(beta_name,safe="")+"/settings") or {}
    after_stable_bind=bindings(after_stable_raw);after_beta_bind=bindings(after_beta_raw)
    after_secret_names={x["name"] for x in after_stable_bind if x["type"]=="secret_text"}
    if before_stable_bind!=after_stable_bind:raise RuntimeError("NONSECRET_BINDINGS_CHANGED_DURING_GAS_REPAIR")
    if stable_secret_names!=after_secret_names:raise RuntimeError("SECRET_BINDING_NAMES_CHANGED_DURING_GAS_REPAIR")
    if before_beta_bind!=after_beta_bind:raise RuntimeError("BETA_BINDINGS_CHANGED_DURING_GAS_REPAIR")
    after_stable_hash=digest(d1_state(stable_db))
    if before_stable_hash!=after_stable_hash:raise RuntimeError("STABLE_D1_CHANGED_DURING_GAS_REPAIR")
    if active_accounts(beta_db)!=before_beta_active:raise RuntimeError("BETA_AUTH_CHANGED_DURING_GAS_REPAIR")

    rec={"status":"PASS","mode":"GAS_PROPERTIES_REPAIR","environment":"STABLE","stable_public_activation":False,
      "repair_transaction_id":tx,"bridge_secret_fingerprint":fingerprint,"bridge_secret_plaintext":False,
      "bridge_secret_rotated":True,"d1_changed":False,"auth_changed":False,"beta_changed":False,
      "nonsecret_bindings_changed":False,"secret_binding_names_changed":False,
      "gas_properties":{"primary":"PASS","outbound":"PASS","dr":"PASS"},
      "bridge_auth_positive_negative":{"primary":"PASS","outbound":"PASS","dr":"PASS","stable_secret_rejected_by_beta":"PASS"},
      "canary_replay_cleanup":{"primary":"PASS","outbound":"PASS","dr":"PASS"},"cleanup_state":"PASS"}
    pathlib.Path("/tmp/stable-private-provision-receipt.json").write_text(json.dumps(rec,indent=2)+"\n")
    print(json.dumps(rec))

if __name__=="__main__":
    if "--self-test" in sys.argv:
        try:selftest()
        except Exception as e:
            print("STABLE_GAS_PROPERTIES_REPAIR_SELFTEST_ERROR:"+str(e),file=sys.stderr);sys.exit(1)
        sys.exit(0)
    try:main()
    except Exception as e:
        pathlib.Path("/tmp/stable-private-provision-receipt.json").write_text(json.dumps({"status":"FAIL","mode":"GAS_PROPERTIES_REPAIR","error":str(e)[:1400],"stable_public_activation":False,"bridge_secret_plaintext":False},indent=2)+"\n")
        print("STABLE_GAS_PROPERTIES_REPAIR_ERROR:"+str(e)[:1800],file=sys.stderr);sys.exit(1)
