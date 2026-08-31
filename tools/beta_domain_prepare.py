#!/usr/bin/env python3
import json,os,pathlib,subprocess,sys,urllib.error,urllib.parse,urllib.request,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
CF="https://api.cloudflare.com/client/v4"

def need(n):
    v=os.environ.get(n,"").strip()
    if not v: raise RuntimeError("MISSING_REQUIRED_SECRET:"+n)
    return v

def req(url,method="GET",body=None,timeout=60):
    data=None if body is None else json.dumps(body,separators=(",",":")).encode()
    h={"Accept":"application/json","Authorization":"Bearer "+need("CLOUDFLARE_API_TOKEN")}
    if data is not None:h["Content-Type"]="application/json"
    r=urllib.request.Request(url,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(r,timeout=timeout) as x:
            raw=x.read().decode("utf-8","replace")
            return x.status,(json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw=e.read().decode("utf-8","replace")
        try:j=json.loads(raw)
        except:j={"raw":raw[:700]}
        return e.code,j

def cf_account(path,method="GET",body=None):
    code,j=req(f"{CF}/accounts/{need('CLOUDFLARE_ACCOUNT_ID')}{path}",method,body)
    if code//100!=2 or j.get("success") is not True:
        raise RuntimeError("CF_API_FAILED:"+str(code)+":"+json.dumps(j.get("errors",j))[:700])
    return j.get("result")

def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def worker_settings(name):
    return cf_account("/workers/scripts/"+urllib.parse.quote(name,safe="")+"/settings") or {}

def bindings(raw):
    out=[]
    for b in raw.get("bindings",[]) or []:
        t=str(b.get("type") or "");n=str(b.get("name") or "");x={"name":n,"type":t}
        if t=="plain_text":x["text"]=str(b.get("text") or "")
        if t=="d1":x["id"]=str(b.get("id") or "")
        if t=="durable_object_namespace":x["class_name"]=str(b.get("class_name") or "")
        out.append(x)
    return sorted(out,key=lambda x:(x["name"],x["type"]))

def d1_rows(db,sql):
    r=cf_account("/d1/database/"+urllib.parse.quote(db,safe="")+"/query","POST",{"sql":sql})
    if not isinstance(r,list) or not r or r[0].get("success") is False:raise RuntimeError("D1_QUERY_FAILED")
    return r[0].get("results") or []

def d1_state(db):
    return {
      "accounts":d1_rows(db,"SELECT login_id,role,status,source_row,source_checksum FROM accounts ORDER BY login_id"),
      "authority":d1_rows(db,"SELECT singleton_id,authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state ORDER BY singleton_id"),
      "counts":d1_rows(db,"SELECT (SELECT COUNT(*) FROM events) events,(SELECT COUNT(*) FROM auth_sessions) auth_sessions,(SELECT COUNT(*) FROM auth_web_sessions) auth_web_sessions,(SELECT COUNT(*) FROM sheet_replication_outbox) sheet_outbox,(SELECT COUNT(*) FROM outbound_replication_outbox) outbound_outbox")}

def list_domains():
    r=cf_account("/workers/domains")
    return r if isinstance(r,list) else []

def curl_status(url):
    p=subprocess.run(["curl","-sS","-L","--connect-timeout","10","--max-time","30","-o","/dev/null","-w","%{http_code}",url],
      text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=40)
    return int(p.stdout.strip() or 0) if p.returncode==0 else 0

def main():
    reqj=json.loads((ROOT/"ops/beta-release-request.json").read_text())
    cfg=json.loads((ROOT/"config/environment_contracts.json").read_text())
    if reqj.get("stage")!="BETA_DOMAIN_PREPARE" or reqj.get("candidate_locked") is not True or reqj.get("stable_publish")!="FORBIDDEN" or reqj.get("authority_change")!="NONE":
        raise RuntimeError("BETA_DOMAIN_PREPARE_REQUEST_FAIL_CLOSED")
    beta=cfg["environments"]["BETA"];stable=cfg["environments"]["STABLE"]
    host=urllib.parse.urlparse(str(beta["target_web_origin"])).hostname or ""
    stable_host=urllib.parse.urlparse(str(stable["target_web_origin"])).hostname or ""
    worker=str(beta["current_service"]["worker"])
    if not host or not stable_host or host==stable_host or not worker:raise RuntimeError("DOMAIN_CONTRACT_INVALID")
    if stable.get("stable_publish_allowed") is not False:raise RuntimeError("STABLE_PUBLIC_GUARD_INVALID")
    source=str(reqj.get("source_sha") or "")
    if len(source)!=40:raise RuntimeError("SOURCE_SHA_REQUIRED")
    if subprocess.run(["git","diff","--quiet",source,"HEAD","--","app","service","google-apps-script"],cwd=ROOT).returncode!=0:
        raise RuntimeError("EXACT_BETA102_SOURCE_DRIFT")

    before_raw=worker_settings(worker);before_bind=bindings(before_raw);by={x["name"]:x for x in before_bind}
    if (by.get("ENVIRONMENT_ID") or {}).get("text")!="BETA" or (by.get("SERVICE_AUDIENCE") or {}).get("text")!="PICK_PACK_1291_BETA":
        raise RuntimeError("BETA_WORKER_ENV_BINDING_DRIFT")
    db=str((by.get("DB") or {}).get("id") or "")
    if not db:raise RuntimeError("BETA_D1_BINDING_MISSING")
    before_d1=digest(d1_state(db))
    before_secret_names=sorted(x["name"] for x in before_bind if x["type"]=="secret_text")

    domains=list_domains()
    stable_matches=[d for d in domains if str(d.get("hostname") or "").lower()==stable_host.lower()]
    beta_matches=[d for d in domains if str(d.get("hostname") or "").lower()==host.lower()]
    root_migration_required=False
    root_domain_id=""
    if stable_matches:
        safe=[{"id":d.get("id"),"hostname":d.get("hostname"),"service":d.get("service"),"zone_name":d.get("zone_name")} for d in stable_matches]
        if len(stable_matches)!=1 or str(stable_matches[0].get("service") or "")!=worker or str(stable_matches[0].get("zone_name") or "").lower()!=stable_host.lower():
            raise RuntimeError("STABLE_ROOT_DOMAIN_ATTACHED_OUTSIDE_BETA_MIGRATION_SCOPE:"+json.dumps(safe,separators=(",",":")))
        root_domain_id=str(stable_matches[0].get("id") or "")
        if not root_domain_id:raise RuntimeError("STABLE_ROOT_DOMAIN_ID_MISSING")
        root_migration_required=True
    changed=False
    if beta_matches:
        if len(beta_matches)!=1 or str(beta_matches[0].get("service") or "")!=worker:
            raise RuntimeError("BETA_DOMAIN_ATTACHED_TO_WRONG_SERVICE")
        domain=beta_matches[0]
    else:
        code,j=req(f"{CF}/accounts/{need('CLOUDFLARE_ACCOUNT_ID')}/workers/domains","PUT",{"hostname":host,"service":worker})
        if code//100!=2 or j.get("success") is not True:
            err=json.dumps(j.get("errors",j))[:900]
            raise RuntimeError("BETA_DOMAIN_ATTACH_FAILED:"+str(code)+":"+err)
        domain=j.get("result") or {}
        changed=True

    # Verify the new Beta hostname before removing the legacy root route, preventing Beta downtime.
    status=0
    for _ in range(12):
        status=curl_status("https://"+host)
        if status in (200,301,302,307,308,401,403):break
        import time;time.sleep(10)
    if status not in (200,301,302,307,308,401,403):raise RuntimeError("BETA_DOMAIN_NOT_READY_AFTER_ATTACH:"+str(status))

    if root_migration_required:
        code,j=req(f"{CF}/accounts/{need('CLOUDFLARE_ACCOUNT_ID')}/workers/domains/"+urllib.parse.quote(root_domain_id,safe=""),"DELETE")
        if code//100!=2 or j.get("success") is not True:
            raise RuntimeError("STABLE_ROOT_BETA_ROUTE_DETACH_FAILED:"+str(code)+":"+json.dumps(j.get("errors",j))[:900])

    after_domains=list_domains()
    beta_after=[d for d in after_domains if str(d.get("hostname") or "").lower()==host.lower()]
    stable_after=[d for d in after_domains if str(d.get("hostname") or "").lower()==stable_host.lower()]
    if len(beta_after)!=1 or str(beta_after[0].get("service") or "")!=worker:raise RuntimeError("BETA_DOMAIN_ATTACH_READBACK_FAILED")
    if stable_after:raise RuntimeError("STABLE_ROOT_DOMAIN_STILL_ATTACHED")

    stable_status=curl_status("https://"+stable_host)
    if stable_status in (200,301,302,307,308):raise RuntimeError("STABLE_ROOT_DOMAIN_STILL_PUBLIC:"+str(stable_status))

    after_raw=worker_settings(worker);after_bind=bindings(after_raw)
    after_secret_names=sorted(x["name"] for x in after_bind if x["type"]=="secret_text")
    if before_bind!=after_bind:raise RuntimeError("BETA_WORKER_BINDINGS_CHANGED_DURING_DOMAIN_ATTACH")
    if before_secret_names!=after_secret_names:raise RuntimeError("BETA_SECRET_BINDINGS_CHANGED_DURING_DOMAIN_ATTACH")
    if before_d1!=digest(d1_state(db)):raise RuntimeError("BETA_D1_CHANGED_DURING_DOMAIN_ATTACH")

    d=beta_after[0]
    rec={"status":"PASS","mode":"BETA_DOMAIN_PREPARE","environment":"BETA","hostname":host,"service":worker,
      "changed":changed,"domain_id":d.get("id"),"zone_name":d.get("zone_name"),"http_status":status,
      "legacy_root_beta_route_migrated":root_migration_required,"stable_root_http_status":stable_status,
      "stable_root_attached":False,"worker_bindings_changed":False,"secret_binding_names_changed":False,"d1_changed":False,
      "beta102_source_unchanged":True,"stable_publish":"FORBIDDEN"}
    pathlib.Path("/tmp/beta-domain-prepare-receipt.json").write_text(json.dumps(rec,indent=2)+"\n")
    print(json.dumps({"status":"PASS","hostname":host,"service":worker,"changed":changed,"http_status":status,"legacy_root_beta_route_migrated":root_migration_required,"stable_root_attached":False}))

if __name__=="__main__":
    try:main()
    except Exception as e:
        pathlib.Path("/tmp/beta-domain-prepare-receipt.json").write_text(json.dumps({"status":"FAIL","mode":"BETA_DOMAIN_PREPARE","error":str(e)[:1400],"stable_publish":"FORBIDDEN"},indent=2)+"\n")
        print("BETA_DOMAIN_PREPARE_ERROR:"+str(e)[:1800],file=sys.stderr);sys.exit(1)
