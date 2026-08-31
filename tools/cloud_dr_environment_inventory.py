#!/usr/bin/env python3
import base64,json,os,pathlib,sys,urllib.error,urllib.parse,urllib.request

OUT=pathlib.Path("/tmp/cloud-dr-environment-inventory.json")
CF="https://api.cloudflare.com/client/v4"

def need(n):
    v=os.environ.get(n,"").strip()
    if not v: raise RuntimeError("MISSING_REQUIRED:"+n)
    return v

def get_json(url,token,timeout=35):
    r=urllib.request.Request(url,headers={"Authorization":"Bearer "+token,"Accept":"application/json","User-Agent":"PickPack1291-DR-Audit/1"})
    try:
        with urllib.request.urlopen(r,timeout=timeout) as x:
            raw=x.read().decode("utf-8","replace")
            return x.status,json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        raw=e.read().decode("utf-8","replace")
        try:j=json.loads(raw)
        except:j={"raw":raw[:300]}
        return e.code,j

def cf(path):
    code,j=get_json(f"{CF}/accounts/{need('CLOUDFLARE_ACCOUNT_ID')}{path}",need("CLOUDFLARE_API_TOKEN"))
    if code!=200 or j.get("success") is not True: raise RuntimeError("CF_READ_FAILED:"+str(code))
    return j.get("result")

def worker_bindings(name):
    s=cf("/workers/scripts/"+urllib.parse.quote(name,safe="")+"/settings") or {}
    return {str(b.get("name")):b for b in (s.get("bindings") or [])}

def btext(m,k): return str((m.get(k) or {}).get("text") or "")
def bid(m,k): return str((m.get(k) or {}).get("id") or "")

def rows(x):
    if isinstance(x,list): return x
    if isinstance(x,dict):
        for k in ("items","apps","databases","owners","services"):
            if isinstance(x.get(k),list): return x[k]
    return []

def jwt_candidates(token):
    out=[]
    try:
        p=token.split(".")[1]
        p += "="*((4-len(p)%4)%4)
        j=json.loads(base64.urlsafe_b64decode(p.encode()).decode())
        for k in ("organization_slug","organizationSlug","organization","org","org_slug","o"):
            v=str(j.get(k) or "").strip()
            if v: out.append(v)
    except Exception: pass
    return out

def resolve_turso_org(token):
    explicit=os.environ.get("TURSO_ORGANIZATION","").strip()
    candidates=([explicit] if explicit else [])+jwt_candidates(token)
    gh=os.environ.get("GITHUB_REPOSITORY","")
    if gh:
        candidates += [gh.split("/",1)[0],gh.split("/",1)[-1]]
    actor=os.environ.get("GITHUB_ACTOR","").strip()
    if actor:candidates.append(actor)
    code,j=get_json("https://api.turso.tech/v1/organizations",token)
    if code==200:
        candidates += [str(x.get("slug") or "").strip() for x in rows(j)]
    seen=set()
    for cand in candidates:
        if not cand or cand in seen: continue
        seen.add(cand)
        code,j=get_json("https://api.turso.tech/v1/organizations/"+urllib.parse.quote(cand,safe="")+"/databases?limit=100",token)
        if code==200 and isinstance(j.get("databases"),list): return cand,j["databases"]
    raise RuntimeError("TURSO_ORG_UNRESOLVED")

def main():
    for n in ["RENDER_API_KEY","TURSO_API_TOKEN","DENO_DEPLOY_TOKEN","CLOUDFLARE_API_TOKEN","CLOUDFLARE_ACCOUNT_ID"]:
        print("::add-mask::"+need(n))
    render=need("RENDER_API_KEY");turso=need("TURSO_API_TOKEN");deno=need("DENO_DEPLOY_TOKEN")
    rc,ro=get_json("https://api.render.com/v1/owners?limit=100",render)
    if rc!=200: raise RuntimeError("RENDER_OWNERS_READ_FAILED:"+str(rc))
    owners=rows(ro)
    sc,sj=get_json("https://api.render.com/v1/services?limit=100&includePreviews=false",render)
    if sc!=200: raise RuntimeError("RENDER_SERVICES_READ_FAILED:"+str(sc))
    services=[x.get("service",x) if isinstance(x,dict) else {} for x in rows(sj)]
    dc,dj=get_json("https://api.deno.com/v2/apps?limit=100",deno)
    if dc!=200: raise RuntimeError("DENO_APPS_READ_FAILED:"+str(dc))
    apps=rows(dj)
    org,dbs=resolve_turso_org(turso)

    bb=worker_bindings("pickpack");sb=worker_bindings("pickpack1291-stable-private")
    beta_db,stable_db=bid(bb,"DB"),bid(sb,"DB")
    if not beta_db or not stable_db or beta_db==stable_db: raise RuntimeError("PRIMARY_D1_ISOLATION_DRIFT")
    if btext(sb,"ENVIRONMENT_ID")!="STABLE" or btext(sb,"SERVICE_AUDIENCE")!="PICK_PACK_1291_STABLE": raise RuntimeError("STABLE_BINDING_DRIFT")
    beta_gas=[btext(bb,k) for k in ("GAS_API_URL","OUTBOUND_GAS_API_URL","DR_GAS_API_URL")]
    stable_gas=[btext(sb,k) for k in ("GAS_API_URL","OUTBOUND_GAS_API_URL","DR_GAS_API_URL")]
    if any(not x.startswith("https://script.google.com/") for x in beta_gas+stable_gas): raise RuntimeError("GAS_BINDING_MISSING")
    if set(beta_gas)&set(stable_gas): raise RuntimeError("GAS_BINDING_CROSS_ENV")

    render_safe=[]
    for s in services:
        d=s.get("serviceDetails") or s.get("service_details") or {}
        render_safe.append({"id":s.get("id"),"name":s.get("name"),"type":s.get("type"),"plan":d.get("plan") or s.get("plan"),"region":d.get("region") or s.get("region"),"suspended":s.get("suspended")})
    deno_safe=[{"id":x.get("id"),"slug":x.get("slug"),"labels":x.get("labels")} for x in apps]
    db_safe=[{"name":x.get("Name") or x.get("name"),"id":x.get("DbId") or x.get("id"),"hostname":x.get("Hostname") or x.get("hostname"),"group":x.get("group"),"primary_region":x.get("primaryRegion") or x.get("primary_region")} for x in dbs]
    groups=sorted(set(str(x.get("group") or "") for x in dbs if x.get("group")))
    receipt={
      "status":"PASS","read_only":True,"no_paid_action":True,"stable_public_activation":False,
      "render":{"owner_count":len(owners),"owners":[{"id":x.get("owner",x).get("id"),"name":x.get("owner",x).get("name"),"type":x.get("owner",x).get("type")} for x in owners if isinstance(x,dict)],"service_count":len(services),"services":render_safe},
      "deno":{"app_count":len(apps),"apps":deno_safe},
      "turso":{"organization":org,"database_count":len(dbs),"groups":groups,"databases":db_safe},
      "primary":{"beta":{"worker":"pickpack","d1_id":beta_db,"environment_id":btext(bb,"ENVIRONMENT_ID") or "BETA","audience":btext(bb,"SERVICE_AUDIENCE") or "PICK_PACK_1291_BETA","gas_distinct":len(set(beta_gas))==3},
                 "stable":{"worker":"pickpack1291-stable-private","d1_id":stable_db,"environment_id":"STABLE","audience":"PICK_PACK_1291_STABLE","gas_distinct":len(set(stable_gas))==3}},
      "targets":{"turso":["pick-pack-1291-dr-beta","pick-pack-1291-dr-stable"],"deno":["pp1291-dr-beta","pp1291-dr-stable"],"render":["pick-pack-1291-dr-beta","pick-pack-1291-dr-stable"]}
    }
    OUT.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"status":"PASS","render_owner_count":len(owners),"render_service_count":len(services),"deno_app_count":len(apps),"turso_database_count":len(dbs),"turso_group_count":len(groups),"primary_d1_separate":True,"gas_cross_env":False}))

if __name__=="__main__":
    try:main()
    except Exception as e:
        OUT.write_text(json.dumps({"status":"FAIL","read_only":True,"error":str(e)[:1000]},indent=2)+"\n")
        print("CLOUD_DR_ENVIRONMENT_INVENTORY_ERROR:"+str(e)[:1200],file=sys.stderr);sys.exit(1)
