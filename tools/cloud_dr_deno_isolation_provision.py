#!/usr/bin/env python3
import base64, datetime as dt, hashlib, json, os, pathlib, secrets, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=pathlib.Path("/tmp/cloud-dr-deno-isolation.json")
CF="https://api.cloudflare.com/client/v4"
TURSO="https://api.turso.tech/v1"
DENO="https://api.deno.com/v2"
REDACT=[]

def mask(v):
    v=str(v or "")
    if v:
        REDACT.append(v)
        print("::add-mask::"+v)
    return v

def safe(s):
    x=str(s)
    for v in REDACT:
        x=x.replace(v,"***")
    return x

def need(n):
    v=os.environ.get(n,"").strip()
    if not v: raise RuntimeError("MISSING_REQUIRED:"+n)
    return v

def req(url,method="GET",token=None,body=None,timeout=60):
    data=None if body is None else json.dumps(body,separators=(",",":")).encode()
    h={"Accept":"application/json","User-Agent":"PickPack1291-DR-Deno/1"}
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
        except:j={"raw":safe(raw[:500])}
        return e.code,j

def cf(path):
    c,j=req(f"{CF}/accounts/{need('CLOUDFLARE_ACCOUNT_ID')}{path}",token=need("CLOUDFLARE_API_TOKEN"))
    if c!=200 or j.get("success") is not True: raise RuntimeError("CF_READ_FAILED:"+str(c))
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
    if eid!=env: raise RuntimeError(env+"_PRIMARY_ENVIRONMENT_DRIFT")
    expected="PICK_PACK_1291_BETA" if env=="BETA" else "PICK_PACK_1291_STABLE"
    if aud!=expected: raise RuntimeError(env+"_PRIMARY_AUDIENCE_DRIFT")
    gen=btext(b,"SERVICE_GENERATION")
    if not gen: raise RuntimeError(env+"_SERVICE_GENERATION_MISSING")
    gas={k:btext(b,k) for k in ("GAS_API_URL","OUTBOUND_GAS_API_URL","DR_GAS_API_URL")}
    if not gas["GAS_API_URL"].startswith("https://script.google.com/"): raise RuntimeError(env+"_PRIMARY_GAS_BINDING_MISSING")
    target=btext(b,"DR_TARGET_ID")
    if env=="STABLE":
        if any(not gas[k].startswith("https://script.google.com/") for k in ("OUTBOUND_GAS_API_URL","DR_GAS_API_URL")): raise RuntimeError("STABLE_GAS_BINDING_MISSING")
        if not target: raise RuntimeError("STABLE_DR_TARGET_ID_MISSING")
    else:
        for k in ("OUTBOUND_GAS_API_URL","DR_GAS_API_URL"):
            if gas[k] and not gas[k].startswith("https://script.google.com/"): raise RuntimeError("BETA_OPTIONAL_GAS_BINDING_INVALID:"+k)
    sub=cf("/workers/subdomain") or {}
    sd=str(sub.get("subdomain") or "")
    if not sd: raise RuntimeError("WORKERS_SUBDOMAIN_MISSING")
    return {"environment":env,"audience":aud,"generation":gen,"gas":gas,"dr_target_id":target,
            "discovery_url":f"https://{worker}.{sd}.workers.dev"}

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
    cand=[]
    explicit=os.environ.get("TURSO_ORGANIZATION","").strip()
    if explicit:cand.append(explicit)
    cand+=jwt_candidates(token)
    gh=os.environ.get("GITHUB_REPOSITORY","")
    if gh:cand += [gh.split("/",1)[0],gh.split("/",1)[-1]]
    actor=os.environ.get("GITHUB_ACTOR","").strip()
    if actor:cand.append(actor)
    c,j=req(TURSO+"/organizations",token=token)
    if c==200:
        rows=j if isinstance(j,list) else j.get("organizations",[])
        cand += [str(x.get("slug") or "").strip() for x in rows if isinstance(x,dict)]
    seen=set()
    for o in cand:
        if not o or o in seen:continue
        seen.add(o)
        c,j=req(TURSO+"/organizations/"+urllib.parse.quote(o,safe="")+"/databases?limit=100",token=token)
        if c==200 and isinstance(j.get("databases"),list):return o,j["databases"]
    raise RuntimeError("TURSO_ORG_UNRESOLVED")

def turso_token(org,db,expiration=None):
    q="?authorization=full-access"
    if expiration:q="?expiration="+urllib.parse.quote(expiration,safe="")+"&authorization=full-access"
    c,j=req(TURSO+"/organizations/"+urllib.parse.quote(org,safe="")+"/databases/"+urllib.parse.quote(db,safe="")+"/auth/tokens"+q,
            method="POST",token=need("TURSO_API_TOKEN"),body={})
    tok=str(j.get("jwt") or "") if isinstance(j,dict) else ""
    if c!=200 or not tok:raise RuntimeError("TURSO_DB_TOKEN_CREATE_FAILED:"+db+":"+str(c))
    return mask(tok)

def node_query_denied(url,token):
    code="""import {createClient} from '@libsql/client';const c=createClient({url:process.env.DB_URL,authToken:process.env.DB_TOKEN});try{await c.execute('SELECT 1');console.log('ALLOWED')}catch{console.log('DENIED')}finally{c.close()}"""
    env=os.environ.copy();env["DB_URL"]=url;env["DB_TOKEN"]=token
    p=subprocess.run(["node","--input-type=module","-e",code],cwd=ROOT/"services/cloud-dr",env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
    return p.returncode==0 and p.stdout.strip().endswith("DENIED")

def deno(method,path,body=None):
    c,j=req(DENO+path,method=method,token=need("DENO_DEPLOY_TOKEN"),body=body,timeout=90)
    if c//100!=2:raise RuntimeError("DENO_API_FAILED:"+method+":"+path+":"+str(c)+":"+safe(json.dumps(j))[:300])
    return j

def env_input(k,v,secret=False):
    return {"key":k,"value":v,"secret":secret,"contexts":"all"}

def source_bundle():
    p=ROOT/"services/cloud-dr/dist/deno.mjs"
    if not p.exists():raise RuntimeError("DENO_BUNDLE_MISSING")
    data=p.read_bytes()
    if not data:raise RuntimeError("DENO_BUNDLE_EMPTY")
    return data,hashlib.sha256(data).hexdigest()

def required_plain(contract,url,limits):
    out={
      "TURSO_DATABASE_URL":url,
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
        out.update({"OUTBOUND_GAS_API_URL":contract["gas"]["OUTBOUND_GAS_API_URL"],"DR_GAS_API_URL":contract["gas"]["DR_GAS_API_URL"],"DR_TARGET_ID":contract["dr_target_id"]})
    else:
        for k in ("OUTBOUND_GAS_API_URL","DR_GAS_API_URL"):
            if contract["gas"][k]: out[k]=contract["gas"][k]
        if contract["dr_target_id"]: out["DR_TARGET_ID"]=contract["dr_target_id"]
    return out

def config_ok(app):
    cfg=app.get("config") or {};rt=cfg.get("runtime") or {}
    return rt.get("type")=="dynamic" and rt.get("entrypoint")=="main.mjs" and cfg.get("crons") is False

def verify_app_env(app,plain):
    ev={str(x.get("key")):x for x in (app.get("env_vars") or [])}
    missing_plain=[k for k in plain if k not in ev]
    drift=[k for k,v in plain.items() if k in ev and (ev[k].get("secret") is True or str(ev[k].get("value") or "")!=v)]
    missing_secret=[k for k in ("TURSO_AUTH_TOKEN","SERVICE_TOKEN_SECRET") if k not in ev or ev[k].get("secret") is not True]
    if missing_plain or drift or missing_secret:
        raise RuntimeError("DENO_APP_ENV_DRIFT:"+str(app.get("slug"))+":"+",".join(missing_plain+drift+missing_secret))
    return {"plain_keys":sorted(plain),"secret_keys":["SERVICE_TOKEN_SECRET","TURSO_AUTH_TOKEN"],"all_present":True}

def revisions(app):
    x=deno("GET","/apps/"+urllib.parse.quote(app,safe="")+"/revisions?limit=100")
    return x if isinstance(x,list) else []

def poll_revision(rid):
    for _ in range(120):
        x=deno("GET","/revisions/"+urllib.parse.quote(rid,safe=""))
        st=str(x.get("status") or "")
        if st=="succeeded":return x
        if st in ("failed","skipped"):raise RuntimeError("DENO_REVISION_"+st.upper()+":"+rid+":"+safe(json.dumps(x.get("failure_detail") or {}))[:300])
        time.sleep(2)
    raise RuntimeError("DENO_REVISION_TIMEOUT:"+rid)

def ensure_app(slug,env,plain,runtime_token,bundle,bundle_sha,source_sha,apps_before):
    matches=[x for x in apps_before if str(x.get("slug") or "")==slug]
    if len(matches)>1:raise RuntimeError("DENO_APP_NOT_UNIQUE:"+slug)
    created=False
    cfg={"runtime":{"type":"dynamic","entrypoint":"main.mjs"},"crons":False}
    if not matches:
        service_secret=mask(base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode())
        ev=[env_input(k,v,False) for k,v in plain.items()]
        ev += [env_input("TURSO_AUTH_TOKEN",runtime_token,True),env_input("SERVICE_TOKEN_SECRET",service_secret,True)]
        app=deno("POST","/apps",{"slug":slug,"labels":{"pp1291.project":"pick-pack-1291","pp1291.environment":env,"pp1291.role":"cloud-dr"},
                                  "env_vars":ev,"config":cfg})
        created=True
    else:
        app=deno("GET","/apps/"+urllib.parse.quote(slug,safe=""))
        if not config_ok(app):raise RuntimeError("DENO_APP_CONFIG_DRIFT:"+slug)
    env_proof=verify_app_env(app,plain)
    revs=revisions(slug)
    exact=[r for r in revs if str((r.get("labels") or {}).get("pp1291.source_sha") or "")==source_sha and
                                 str((r.get("labels") or {}).get("pp1291.bundle_sha") or "")==bundle_sha]
    if exact:
        exact.sort(key=lambda x:str(x.get("created_at") or ""),reverse=True)
        r=exact[0];st=str(r.get("status") or "")
        if st in ("queued","building"):r=poll_revision(str(r.get("id")))
        elif st=="succeeded":r=deno("GET","/revisions/"+urllib.parse.quote(str(r.get("id")),safe=""))
        else:raise RuntimeError("DENO_EXACT_REVISION_NOT_REUSABLE:"+slug+":"+st)
        deployed=False
    else:
        payload={"assets":{"main.mjs":{"kind":"file","encoding":"base64","content":base64.b64encode(bundle).decode()}},
                 "config":cfg,
                 "labels":{"pp1291.source_sha":source_sha,"pp1291.bundle_sha":bundle_sha,"pp1291.environment":env},
                 "production":{"domains":[]},"preview":False,"retention":"auto"}
        r=deno("POST","/apps/"+urllib.parse.quote(slug,safe="")+"/deploy",payload)
        rid=str(r.get("id") or "")
        if not rid:raise RuntimeError("DENO_REVISION_ID_MISSING:"+slug)
        r=poll_revision(rid);deployed=True
    hostnames=[]
    for t in (r.get("timelines") or []):
        hostnames += [str(x) for x in (t.get("hostnames") or []) if str(x)]
    if hostnames:raise RuntimeError("DENO_PUBLIC_DOMAIN_ATTACHED:"+slug)
    if str(r.get("status"))!="succeeded":raise RuntimeError("DENO_REVISION_NOT_SUCCEEDED:"+slug)
    return {"slug":slug,"app_id":app.get("id"),"created":created,"env":env_proof,
            "revision_id":r.get("id"),"revision_status":"succeeded","deployed":deployed,
            "public_hostnames":[],"writer_mode":"PASSIVE","kill_switch":"1"}

def main():
    for n in ("DENO_DEPLOY_TOKEN","TURSO_API_TOKEN","CLOUDFLARE_API_TOKEN","CLOUDFLARE_ACCOUNT_ID"):mask(need(n))
    limits=json.loads((ROOT/"config/provider_free_limits.json").read_text())
    dl=limits.get("deno") or {}
    max_apps=int(dl.get("max_active_apps") or 0);max_builds=int(dl.get("builds_per_hour") or 0)
    if max_apps<2 or max_builds<2:raise RuntimeError("DENO_FREE_LIMIT_AUTHORITY_MISSING")
    c,j=req(DENO+"/apps?limit=100",token=need("DENO_DEPLOY_TOKEN"))
    if c!=200 or not isinstance(j,list):raise RuntimeError("DENO_APPS_READ_FAILED:"+str(c))
    apps_before=j
    targets={"BETA":"pp1291-dr-beta","STABLE":"pp1291-dr-stable"}
    present={str(x.get("slug") or "") for x in apps_before}
    missing=sum(1 for x in targets.values() if x not in present)
    if len(apps_before)+missing>max_apps:raise RuntimeError("DENO_FREE_APP_CAPACITY_BLOCKED")

    recent=0;cut=dt.datetime.now(dt.timezone.utc)-dt.timedelta(hours=1)
    for a in apps_before:
        slug=str(a.get("slug") or "")
        if not slug:continue
        try:rs=revisions(slug)
        except Exception:continue
        for r in rs:
            try:
                t=dt.datetime.fromisoformat(str(r.get("created_at") or "").replace("Z","+00:00"))
                if t>=cut:recent+=1
            except Exception:pass
    if recent+missing>max_builds:raise RuntimeError("DENO_FREE_BUILD_RATE_HEADROOM_BLOCKED")

    beta=worker_contract("BETA","pickpack")
    stable=worker_contract("STABLE","pickpack1291-stable-private")
    bp={x for x in beta["gas"].values() if x};sp={x for x in stable["gas"].values() if x}
    if bp & sp:raise RuntimeError("DENO_GAS_CROSS_ENV_BINDING")

    org,dbs=resolve_turso(need("TURSO_API_TOKEN"))
    byname={str(x.get("Name") or x.get("name") or ""):x for x in dbs}
    dbnames={"BETA":"pick-pack-1291-dr-beta","STABLE":"pick-pack-1291-dr-stable"}
    for n in dbnames.values():
        if n not in byname:raise RuntimeError("TURSO_TARGET_MISSING:"+n)
    urls={}
    for env,n in dbnames.items():
        host=str(byname[n].get("Hostname") or byname[n].get("hostname") or "")
        if not host:raise RuntimeError("TURSO_HOST_MISSING:"+n)
        urls[env]="libsql://"+host

    tb=turso_token(org,dbnames["BETA"],"30m");ts=turso_token(org,dbnames["STABLE"],"30m")
    if not node_query_denied(urls["STABLE"],tb):raise RuntimeError("DENO_PREFLIGHT_BETA_TOKEN_CAN_ACCESS_STABLE")
    if not node_query_denied(urls["BETA"],ts):raise RuntimeError("DENO_PREFLIGHT_STABLE_TOKEN_CAN_ACCESS_BETA")

    bundle,bsha=source_bundle();source_sha=str(os.environ.get("GITHUB_SHA") or "")
    if len(source_sha)<12:raise RuntimeError("GITHUB_SHA_MISSING")

    out={}
    for env,contract in (("BETA",beta),("STABLE",stable)):
        slug=targets[env]
        existing=slug in present
        app_detail=deno("GET","/apps/"+urllib.parse.quote(slug,safe="")) if existing else None
        ev={str(x.get("key")):x for x in ((app_detail or {}).get("env_vars") or [])}
        need_runtime=(not existing) or ("TURSO_AUTH_TOKEN" not in ev)
        runtime=turso_token(org,dbnames[env]) if need_runtime else ""
        if existing:
            # Existing targets are only accepted when all immutable safety/secret bindings already exist.
            # This avoids silently rotating hidden credentials or mutating a previously verified app.
            if "SERVICE_TOKEN_SECRET" not in ev or ev.get("SERVICE_TOKEN_SECRET",{}).get("secret") is not True:
                raise RuntimeError("DENO_EXISTING_SERVICE_SECRET_MISSING:"+slug)
            plain=required_plain(contract,urls[env],dl)
            if need_runtime:
                patch={"env_vars":[env_input("TURSO_AUTH_TOKEN",runtime,True)]}
                deno("PATCH","/apps/"+urllib.parse.quote(slug,safe=""),patch)
        plain=required_plain(contract,urls[env],dl)
        out[env.lower()]=ensure_app(slug,env,plain,runtime,bundle,bsha,source_sha,apps_before)

    c,after=req(DENO+"/apps?limit=100",token=need("DENO_DEPLOY_TOKEN"))
    if c!=200 or not isinstance(after,list):raise RuntimeError("DENO_APPS_POST_READ_FAILED")
    names={str(x.get("slug") or "") for x in after}
    if not set(targets.values()).issubset(names):raise RuntimeError("DENO_TARGET_PRESENCE_READBACK_FAILED")
    if len(after)>max_apps:raise RuntimeError("DENO_FREE_APP_LIMIT_EXCEEDED")
    receipt={"status":"PASS","provider":"DENO","environment":"BETA_STABLE","zero_cost_guard":"PASS",
      "app_count_before":len(apps_before),"app_count_after":len(after),"max_active_apps":max_apps,
      "builds_last_hour_before":recent,"max_builds_per_hour":max_builds,
      "bundle_sha256":bsha,"source_sha":source_sha,
      "cross_credentials":"DENIED_BOTH_WAYS","temporary_cross_check_tokens":"AUTO_EXPIRE_30M",
      "resource_separation":"SEPARATE_APPS","credential_separation":"SEPARATE_DATABASE_AND_SERVICE_SECRETS",
      "runtime_mode":"PASSIVE","kill_switch":"ACTIVE","public_domains_attached":0,
      "beta":out["beta"],"stable":out["stable"],
      "gas_cross_environment":False,"secrets_exposed":False,"paid_action":False,
      "stable_public_activation":False,"cleanup":"PASS_NO_TEMP_APP_OR_REVISION"}
    OUT.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"status":"PASS","provider":"DENO","beta_revision":out["beta"]["revision_status"],
      "stable_revision":out["stable"]["revision_status"],"cross_credentials":"DENIED_BOTH_WAYS",
      "public_domains_attached":0,"app_count_before":len(apps_before),"app_count_after":len(after),"secrets_exposed":False}))

if __name__=="__main__":
    try:main()
    except Exception as e:
        OUT.write_text(json.dumps({"status":"FAIL","provider":"DENO","error":safe(str(e))[:1000],
                                   "secrets_exposed":False,"stable_public_activation":False},indent=2)+"\n")
        print("CLOUD_DR_DENO_ISOLATION_ERROR:"+safe(str(e))[:1400],file=sys.stderr);sys.exit(1)
