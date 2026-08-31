#!/usr/bin/env python3
import base64, hashlib, json, os, pathlib, secrets, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=pathlib.Path("/tmp/cloud-dr-render-isolation.json")
CF="https://api.cloudflare.com/client/v4"
TURSO="https://api.turso.tech/v1"
RENDER="https://api.render.com/v1"
BRANCH="release/audit-beta104-stable-private-20260831"
REPO="https://github.com/tam95supra-source/pick-pack-1291"
REDACT=[]

def mask(v):
    v=str(v or "")
    if v:
        REDACT.append(v)
        print("::add-mask::"+v)
    return v

def safe(v):
    s=str(v)
    for x in REDACT:s=s.replace(x,"***")
    return s

def need(n):
    v=os.environ.get(n,"").strip()
    if not v:raise RuntimeError("MISSING_REQUIRED:"+n)
    return v

def request(url,method="GET",token=None,body=None,timeout=60):
    data=None if body is None else json.dumps(body,separators=(",",":")).encode()
    h={"Accept":"application/json","User-Agent":"PickPack1291-DR-Render/1"}
    if token:h["Authorization"]="Bearer "+token
    if data is not None:h["Content-Type"]="application/json"
    req=urllib.request.Request(url,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            raw=r.read().decode("utf-8","replace")
            return r.status,(json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw=e.read().decode("utf-8","replace")
        try:j=json.loads(raw)
        except:j={"raw":safe(raw[:500])}
        return e.code,j

def render(path,method="GET",body=None):
    c,j=request(RENDER+path,method,need("RENDER_API_KEY"),body,90)
    if c//100!=2:raise RuntimeError("RENDER_API_FAILED:"+method+":"+path+":"+str(c)+":"+safe(json.dumps(j))[:400])
    return j

def cf(path):
    c,j=request(f"{CF}/accounts/{need('CLOUDFLARE_ACCOUNT_ID')}{path}",token=need("CLOUDFLARE_API_TOKEN"))
    if c!=200 or j.get("success") is not True:raise RuntimeError("CF_READ_FAILED:"+str(c))
    return j.get("result")

def bindings(worker):
    s=cf("/workers/scripts/"+urllib.parse.quote(worker,safe="")+"/settings") or {}
    return {str(x.get("name")):x for x in (s.get("bindings") or [])}

def btext(b,k):
    x=b.get(k) or {}
    return str(x.get("text") or "") if x.get("type")=="plain_text" else ""

def worker_contract(env,worker):
    b=bindings(worker)
    eid=(btext(b,"ENVIRONMENT_ID") or env).upper()
    aud=btext(b,"SERVICE_AUDIENCE") or ("PICK_PACK_1291_BETA" if env=="BETA" else "PICK_PACK_1291_STABLE")
    if eid!=env:raise RuntimeError(env+"_PRIMARY_ENVIRONMENT_DRIFT")
    expected="PICK_PACK_1291_BETA" if env=="BETA" else "PICK_PACK_1291_STABLE"
    if aud!=expected:raise RuntimeError(env+"_PRIMARY_AUDIENCE_DRIFT")
    gen=btext(b,"SERVICE_GENERATION")
    if not gen:raise RuntimeError(env+"_SERVICE_GENERATION_MISSING")
    gas={k:btext(b,k) for k in ("GAS_API_URL","OUTBOUND_GAS_API_URL","DR_GAS_API_URL")}
    if not gas["GAS_API_URL"].startswith("https://script.google.com/"):raise RuntimeError(env+"_PRIMARY_GAS_BINDING_MISSING")
    target=btext(b,"DR_TARGET_ID")
    if env=="STABLE":
        if any(not gas[k].startswith("https://script.google.com/") for k in ("OUTBOUND_GAS_API_URL","DR_GAS_API_URL")):raise RuntimeError("STABLE_GAS_BINDING_MISSING")
        if not target:raise RuntimeError("STABLE_DR_TARGET_ID_MISSING")
    sub=cf("/workers/subdomain") or {};sd=str(sub.get("subdomain") or "")
    if not sd:raise RuntimeError("WORKERS_SUBDOMAIN_MISSING")
    return {"environment":env,"audience":aud,"generation":gen,"gas":gas,"dr_target_id":target,"discovery_url":f"https://{worker}.{sd}.workers.dev"}

def jwt_candidates(token):
    out=[]
    try:
        p=token.split(".")[1];p+="="*((4-len(p)%4)%4)
        j=json.loads(base64.urlsafe_b64decode(p.encode()).decode())
        for k in ("organization_slug","organizationSlug","organization","org","org_slug","o"):
            v=str(j.get(k) or "").strip()
            if v:out.append(v)
    except Exception:pass
    return out

def resolve_turso(token):
    cand=[];explicit=os.environ.get("TURSO_ORGANIZATION","").strip()
    if explicit:cand.append(explicit)
    cand+=jwt_candidates(token)
    gh=os.environ.get("GITHUB_REPOSITORY","")
    if gh:cand += [gh.split("/",1)[0],gh.split("/",1)[-1]]
    actor=os.environ.get("GITHUB_ACTOR","").strip()
    if actor:cand.append(actor)
    c,j=request(TURSO+"/organizations",token=token)
    if c==200:
        rows=j if isinstance(j,list) else j.get("organizations",[])
        cand += [str(x.get("slug") or "").strip() for x in rows if isinstance(x,dict)]
    seen=set()
    for org in cand:
        if not org or org in seen:continue
        seen.add(org)
        c,j=request(TURSO+"/organizations/"+urllib.parse.quote(org,safe="")+"/databases?limit=100",token=token)
        if c==200 and isinstance(j.get("databases"),list):return org,j["databases"]
    raise RuntimeError("TURSO_ORG_UNRESOLVED")

def turso_token(org,db,expiration=None):
    q="?authorization=full-access"
    if expiration:q="?expiration="+urllib.parse.quote(expiration,safe="")+"&authorization=full-access"
    c,j=request(TURSO+"/organizations/"+urllib.parse.quote(org,safe="")+"/databases/"+urllib.parse.quote(db,safe="")+"/auth/tokens"+q,
                method="POST",token=need("TURSO_API_TOKEN"),body={})
    tok=str(j.get("jwt") or "")
    if c!=200 or not tok:raise RuntimeError("TURSO_DB_TOKEN_CREATE_FAILED:"+db+":"+str(c))
    return mask(tok)

def token_denied(url,token):
    code="""import {createClient} from '@libsql/client';const c=createClient({url:process.env.DB_URL,authToken:process.env.DB_TOKEN});try{await c.execute('SELECT 1');console.log('ALLOWED')}catch{console.log('DENIED')}finally{c.close()}"""
    e=os.environ.copy();e["DB_URL"]=url;e["DB_TOKEN"]=token
    p=subprocess.run(["node","--input-type=module","-e",code],cwd=ROOT/"services/cloud-dr",env=e,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
    return p.returncode==0 and p.stdout.strip().endswith("DENIED")

def env_vars(contract,url,runtime_token,limits):
    vals={
      "NODE_VERSION":"22",
      "TURSO_DATABASE_URL":url,
      "TURSO_AUTH_TOKEN":runtime_token,
      "SERVICE_TOKEN_SECRET":mask(base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()),
      "SERVICE_GENERATION":contract["generation"],
      "DISCOVERY_URL":contract["discovery_url"],
      "DR_WRITER_MODE":"PASSIVE",
      "ENVIRONMENT_ID":contract["environment"],
      "SERVICE_AUDIENCE":contract["audience"],
      "GAS_API_URL":contract["gas"]["GAS_API_URL"],
      "DR_MAX_REQUESTS_PER_MINUTE":str(int(limits["max_dr_requests_per_minute"])),
      "DR_MAX_MUTATIONS_PER_BATCH":str(int(limits["max_dr_mutations_per_batch"])),
      "DR_KILL_SWITCH":"1",
    }
    if contract["environment"]=="STABLE":
        vals.update({"OUTBOUND_GAS_API_URL":contract["gas"]["OUTBOUND_GAS_API_URL"],"DR_GAS_API_URL":contract["gas"]["DR_GAS_API_URL"],"DR_TARGET_ID":contract["dr_target_id"]})
    else:
        for k in ("OUTBOUND_GAS_API_URL","DR_GAS_API_URL"):
            if contract["gas"][k]:vals[k]=contract["gas"][k]
        if contract["dr_target_id"]:vals["DR_TARGET_ID"]=contract["dr_target_id"]
    return vals

def unwrap_services(j):
    rows=j if isinstance(j,list) else []
    return [x.get("service",x) if isinstance(x,dict) else {} for x in rows]

def unwrap_owners(j):
    rows=j if isinstance(j,list) else []
    return [x.get("owner",x) if isinstance(x,dict) else {} for x in rows]

def unwrap_deploys(j):
    rows=j if isinstance(j,list) else []
    return [x.get("deploy",x) if isinstance(x,dict) else {} for x in rows]

def service_details(s):
    return s.get("serviceDetails") or s.get("service_details") or {}

def service_safe(s):
    d=service_details(s)
    return {"id":s.get("id"),"name":s.get("name"),"type":s.get("type"),"plan":d.get("plan") or s.get("plan"),
            "region":d.get("region") or s.get("region"),"url":d.get("url") or s.get("url"),"suspended":s.get("suspended"),
            "repo":s.get("repo"),"branch":s.get("branch"),"autoDeploy":s.get("autoDeploy")}

def expected_commands():
    build="cd services/cloud-dr && npm install --ignore-scripts --no-audit --no-fund --package-lock=false --no-save @libsql/client@0.15.15 esbuild@0.25.9 typescript@5.9.2 @types/node@24.3.0 && npm run check && npm test && npm run build"
    start="node services/cloud-dr/dist/render.mjs"
    return build,start

def create_service(owner,name,env,contract,url,runtime_token,limits):
    build,start=expected_commands()
    payload={"type":"web_service","name":name,"ownerId":owner,"repo":REPO,"branch":BRANCH,"autoDeploy":"no",
      "envVars":[{"key":k,"value":v} for k,v in env_vars(contract,url,runtime_token,limits).items()],
      "serviceDetails":{"runtime":"node","plan":"free","region":"singapore","numInstances":1,"healthCheckPath":"/health",
                        "envSpecificDetails":{"buildCommand":build,"startCommand":start}}}
    c,j=request(RENDER+"/services","POST",need("RENDER_API_KEY"),payload,90)
    if c==402:raise RuntimeError("RENDER_PAID_ACTION_BLOCKED_402")
    if c!=201:raise RuntimeError("RENDER_CREATE_FAILED:"+name+":"+str(c)+":"+safe(json.dumps(j))[:500])
    s=j.get("service",j) if isinstance(j,dict) else {}
    if not s.get("id"):raise RuntimeError("RENDER_CREATE_NO_SERVICE_ID:"+name)
    return s

def validate_existing(s,name):
    d=service_details(s);plan=str(d.get("plan") or s.get("plan") or "");region=str(d.get("region") or s.get("region") or "")
    if s.get("name")!=name or s.get("type")!="web_service":raise RuntimeError("RENDER_EXISTING_TARGET_TYPE_DRIFT:"+name)
    if plan!="free":raise RuntimeError("RENDER_EXISTING_TARGET_NOT_FREE:"+name+":"+plan)
    if region!="singapore":raise RuntimeError("RENDER_EXISTING_TARGET_REGION_DRIFT:"+name+":"+region)
    if str(s.get("branch") or "")!=BRANCH:raise RuntimeError("RENDER_EXISTING_TARGET_BRANCH_DRIFT:"+name)
    if str(s.get("repo") or "").rstrip("/")!=REPO:raise RuntimeError("RENDER_EXISTING_TARGET_REPO_DRIFT:"+name)
    return True

def update_env(sid,vals):
    body=[{"key":k,"value":v} for k,v in vals.items()]
    c,j=request(RENDER+"/services/"+urllib.parse.quote(sid,safe="")+"/env-vars","PUT",need("RENDER_API_KEY"),body,90)
    if c!=200:raise RuntimeError("RENDER_ENV_UPDATE_FAILED:"+sid+":"+str(c)+":"+safe(json.dumps(j))[:300])

def deploy_exact(sid,source_sha):
    rows=unwrap_deploys(render("/services/"+urllib.parse.quote(sid,safe="")+"/deploys?limit=100"))
    exact=[x for x in rows if str((x.get("commit") or {}).get("id") or "")==source_sha]
    if exact:
        exact.sort(key=lambda x:str(x.get("createdAt") or x.get("created_at") or ""),reverse=True)
        d=exact[0]
    else:
        d=render("/services/"+urllib.parse.quote(sid,safe="")+"/deploys","POST",{"commitId":source_sha,"clearCache":"do_not_clear"})
    did=str(d.get("id") or "")
    if not did:raise RuntimeError("RENDER_DEPLOY_ID_MISSING:"+sid)
    terminal={"live","deactivated","build_failed","update_failed","canceled","pre_deploy_failed"}
    for _ in range(240):
        x=render("/services/"+urllib.parse.quote(sid,safe="")+"/deploys/"+urllib.parse.quote(did,safe=""))
        st=str(x.get("status") or "")
        if st=="live":
            cid=str((x.get("commit") or {}).get("id") or "")
            if cid!=source_sha:raise RuntimeError("RENDER_DEPLOY_SHA_MISMATCH:"+sid+":"+cid)
            return x
        if st in terminal:raise RuntimeError("RENDER_DEPLOY_FAILED:"+sid+":"+st)
        time.sleep(3)
    raise RuntimeError("RENDER_DEPLOY_TIMEOUT:"+sid)

def http_json(url,path,headers=None,method="GET"):
    q=urllib.request.Request(url.rstrip("/")+path,headers=headers or {},method=method)
    try:
        with urllib.request.urlopen(q,timeout=90) as r:
            raw=r.read().decode("utf-8","replace")
            try:j=json.loads(raw)
            except:j={}
            return r.status,j
    except urllib.error.HTTPError as e:
        raw=e.read().decode("utf-8","replace")
        try:j=json.loads(raw)
        except:j={}
        return e.code,j

def verify_runtime(s,env,aud):
    d=service_details(s);url=str(d.get("url") or s.get("url") or "")
    if not url.startswith("https://") or not url.endswith(".onrender.com"):raise RuntimeError("RENDER_DEFAULT_URL_INVALID:"+env)
    last=""
    for _ in range(80):
        c,j=http_json(url,"/health")
        if c==200 and j.get("ok") is True:break
        last=str(c);time.sleep(3)
    else:raise RuntimeError("RENDER_HEALTH_TIMEOUT:"+env+":"+last)
    if j.get("provider")!="TURSO" or j.get("writer_mode")!="PASSIVE" or str(j.get("environment_id") or "").upper()!=env:
        raise RuntimeError("RENDER_PASSIVE_HEALTH_DRIFT:"+env)
    c,e=http_json(url,"/environment.json")
    if c!=200 or str(e.get("environment_id") or "").upper()!=env:raise RuntimeError("RENDER_ENVIRONMENT_READBACK_FAILED:"+env)
    c,k=http_json(url,"/v1/mobile/read",{"x-pick-pack-environment":env,"x-pick-pack-audience":aud},"POST")
    code=str(((k.get("error") or {}).get("code")) or "")
    if c!=503 or code!="DR_KILL_SWITCH_ACTIVE":raise RuntimeError("RENDER_KILL_SWITCH_READBACK_FAILED:"+env+":"+str(c)+":"+code)
    c,m=http_json(url,"/v1/mobile/read",{}, "POST")
    mcode=str(((m.get("error") or {}).get("code")) or "")
    if c!=403 or mcode!="ENVIRONMENT_ID_REQUIRED":raise RuntimeError("RENDER_ENV_FENCE_READBACK_FAILED:"+env+":"+str(c)+":"+mcode)
    return {"url":url,"health":"PASS","environment":"PASS","kill_switch":"PASS","environment_fence":"PASS","writer_mode":"PASSIVE"}

def suspend_and_readback(sid):
    c,j=request(RENDER+"/services/"+urllib.parse.quote(sid,safe="")+"/suspend","POST",need("RENDER_API_KEY"),{},60)
    if c not in (200,202):raise RuntimeError("RENDER_SUSPEND_FAILED:"+sid+":"+str(c))
    for _ in range(60):
        s=render("/services/"+urllib.parse.quote(sid,safe=""))
        if str(s.get("suspended") or "")=="suspended":return s
        time.sleep(2)
    raise RuntimeError("RENDER_SUSPEND_READBACK_TIMEOUT:"+sid)

def main():
    for n in ("RENDER_API_KEY","TURSO_API_TOKEN","CLOUDFLARE_API_TOKEN","CLOUDFLARE_ACCOUNT_ID"):mask(need(n))
    limits=json.loads((ROOT/"config/provider_free_limits.json").read_text());rl=limits.get("render") or {};dl=limits.get("deno") or {}
    if rl.get("required_service_plan")!="free" or rl.get("required_region")!="singapore":raise RuntimeError("RENDER_FREE_LIMIT_AUTHORITY_MISSING")
    if int(rl.get("workspace_free_instance_hours_monthly") or 0)<=0:raise RuntimeError("RENDER_FREE_HOURS_AUTHORITY_MISSING")
    if int(dl.get("max_dr_requests_per_minute") or 0)<=0 or int(dl.get("max_dr_mutations_per_batch") or 0)<=0:raise RuntimeError("DR_RUNTIME_LIMIT_AUTHORITY_MISSING")
    owners=unwrap_owners(render("/owners?limit=100"))
    if len(owners)!=1:raise RuntimeError("RENDER_OWNER_NOT_UNIQUE:"+str(len(owners)))
    owner=str(owners[0].get("id") or "")
    if not owner:raise RuntimeError("RENDER_OWNER_ID_MISSING")
    services=unwrap_services(render("/services?limit=100&includePreviews=false"))
    targets={"BETA":"pick-pack-1291-dr-beta","STABLE":"pick-pack-1291-dr-stable"}
    byname={}
    for s in services:byname.setdefault(str(s.get("name") or ""),[]).append(s)
    for name in targets.values():
        if len(byname.get(name,[]))>1:raise RuntimeError("RENDER_TARGET_NOT_UNIQUE:"+name)
        if byname.get(name):validate_existing(byname[name][0],name)

    beta=worker_contract("BETA","pickpack");stable=worker_contract("STABLE","pickpack1291-stable-private")
    if {x for x in beta["gas"].values() if x}&{x for x in stable["gas"].values() if x}:raise RuntimeError("RENDER_GAS_CROSS_ENV_BINDING")
    org,dbs=resolve_turso(need("TURSO_API_TOKEN"));dbmap={str(x.get("Name") or x.get("name") or ""):x for x in dbs}
    dbnames={"BETA":"pick-pack-1291-dr-beta","STABLE":"pick-pack-1291-dr-stable"};urls={}
    for env,n in dbnames.items():
        if n not in dbmap:raise RuntimeError("TURSO_TARGET_MISSING:"+n)
        host=str(dbmap[n].get("Hostname") or dbmap[n].get("hostname") or "")
        if not host:raise RuntimeError("TURSO_HOST_MISSING:"+n)
        urls[env]="libsql://"+host
    tb=turso_token(org,dbnames["BETA"],"30m");ts=turso_token(org,dbnames["STABLE"],"30m")
    if not token_denied(urls["STABLE"],tb):raise RuntimeError("RENDER_PREFLIGHT_BETA_TOKEN_CAN_ACCESS_STABLE")
    if not token_denied(urls["BETA"],ts):raise RuntimeError("RENDER_PREFLIGHT_STABLE_TOKEN_CAN_ACCESS_BETA")

    source_sha=str(os.environ.get("GITHUB_SHA") or "")
    if len(source_sha)!=40:raise RuntimeError("GITHUB_SHA_INVALID")
    result={}
    for env,contract in (("BETA",beta),("STABLE",stable)):
        name=targets[env];existing=(byname.get(name) or [None])[0]
        runtime=turso_token(org,dbnames[env])
        vals=env_vars(contract,urls[env],runtime,dl)
        if existing:
            sid=str(existing.get("id") or "");update_env(sid,vals);service=render("/services/"+urllib.parse.quote(sid,safe=""))
        else:
            service=create_service(owner,name,env,contract,urls[env],runtime,dl);sid=str(service.get("id") or "")
        d=service_details(service)
        plan=str(d.get("plan") or service.get("plan") or "");region=str(d.get("region") or service.get("region") or "")
        if plan!="free" or region!="singapore":raise RuntimeError("RENDER_POST_CREATE_FREE_GUARD_FAILED:"+name+":"+plan+":"+region)
        dep=deploy_exact(sid,source_sha)
        service=render("/services/"+urllib.parse.quote(sid,safe=""))
        runtime_proof=verify_runtime(service,env,contract["audience"])
        suspended=suspend_and_readback(sid)
        result[env.lower()]={"service":service_safe(suspended),"deploy_id":dep.get("id"),
          "deploy_status":"live_before_suspend","deploy_commit":(dep.get("commit") or {}).get("id"),
          "runtime":runtime_proof,"suspend_readback":"PASS","writer_mode":"PASSIVE","kill_switch":"1","custom_domain_created":False}
    services_after=unwrap_services(render("/services?limit=100&includePreviews=false"))
    after_names=[str(x.get("name") or "") for x in services_after]
    if not set(targets.values()).issubset(set(after_names)):raise RuntimeError("RENDER_TARGET_PRESENCE_READBACK_FAILED")
    for env in ("beta","stable"):
        s=result[env]["service"]
        if s["plan"]!="free" or s["region"]!="singapore" or s["suspended"]!="suspended":raise RuntimeError("RENDER_FINAL_FREE_SUSPEND_DRIFT:"+env)
    receipt={"status":"PASS","provider":"RENDER","environment":"BETA_STABLE","zero_cost_guard":"PLAN_FREE_SUSPENDED",
      "workspace_owner_id":owner,"service_count_before":len(services),"service_count_after":len(services_after),
      "required_plan":"free","required_region":"singapore","free_instance_hours_monthly":rl["workspace_free_instance_hours_monthly"],
      "auto_deploy":"OFF","resource_separation":"SEPARATE_WEB_SERVICES","credential_separation":"SEPARATE_DATABASE_AND_SERVICE_SECRETS",
      "cross_credentials":"DENIED_BOTH_WAYS","temporary_cross_check_tokens":"AUTO_EXPIRE_30M",
      "runtime_mode":"PASSIVE","kill_switch":"ACTIVE","suspended_after_verify":True,"discovery_activation":False,
      "custom_domains_created":0,"paid_service_plan_created":False,"secrets_exposed":False,"stable_public_activation":False,
      "billing_usage_api_available":False,"billing_risk_control":"FREE_PLAN_PLUS_IMMEDIATE_SUSPEND_NO_AUTODEPLOY",
      "beta":result["beta"],"stable":result["stable"],"cleanup":"PASS_NO_TEMP_RENDER_RESOURCES"}
    OUT.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"status":"PASS","provider":"RENDER","beta":"SUSPENDED_PASSIVE","stable":"SUSPENDED_PASSIVE",
      "cross_credentials":"DENIED_BOTH_WAYS","plan":"free","region":"singapore","auto_deploy":"OFF","secrets_exposed":False}))

if __name__=="__main__":
    try:main()
    except Exception as e:
        OUT.write_text(json.dumps({"status":"FAIL","provider":"RENDER","error":safe(str(e))[:1200],
          "secrets_exposed":False,"stable_public_activation":False},indent=2)+"\n")
        print("CLOUD_DR_RENDER_ISOLATION_ERROR:"+safe(str(e))[:1600],file=sys.stderr);sys.exit(1)
