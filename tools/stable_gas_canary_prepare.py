#!/usr/bin/env python3
import json,os,pathlib,subprocess,sys,urllib.parse,urllib.request,urllib.error
ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRIPT_API="https://script.googleapis.com/v1/projects"

def need(n):
    v=os.environ.get(n,"").strip()
    if not v: raise RuntimeError("MISSING_REQUIRED_SECRET:"+n)
    return v

def req_json(url,method="GET",token=None,body=None,timeout=60):
    data=None if body is None else json.dumps(body,separators=(",",":")).encode()
    h={"Accept":"application/json"}
    if token:h["Authorization"]="Bearer "+token
    if data is not None:h["Content-Type"]="application/json; charset=utf-8"
    r=urllib.request.Request(url,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(r,timeout=timeout) as x:
            raw=x.read().decode("utf-8","replace")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        raw=e.read().decode("utf-8","replace")
        raise RuntimeError("HTTP_"+str(e.code)+":"+raw[:800])

def oauth():
    data=urllib.parse.urlencode({
      "client_id":need("GOOGLE_OAUTH_CLIENT_ID"),
      "client_secret":need("GOOGLE_OAUTH_CLIENT_SECRET"),
      "refresh_token":need("GOOGLE_OAUTH_REFRESH_TOKEN"),
      "grant_type":"refresh_token"}).encode()
    r=urllib.request.Request("https://oauth2.googleapis.com/token",data=data,headers={"Content-Type":"application/x-www-form-urlencoded"},method="POST")
    with urllib.request.urlopen(r,timeout=45) as x:j=json.loads(x.read().decode())
    t=str(j.get("access_token",""))
    if not t:raise RuntimeError("GOOGLE_ACCESS_TOKEN_MISSING")
    return t

def sheet_values(tok,sid,rng):
    url="https://sheets.googleapis.com/v4/spreadsheets/"+urllib.parse.quote(sid,safe="")+"/values/"+urllib.parse.quote(rng,safe="")
    j=req_json(url,token=tok);return j.get("values") or []

def sheet_put(tok,sid,rng,values):
    url="https://sheets.googleapis.com/v4/spreadsheets/"+urllib.parse.quote(sid,safe="")+"/values/"+urllib.parse.quote(rng,safe="")+"?valueInputOption=RAW"
    req_json(url,"PUT",tok,{"range":rng,"majorDimension":"ROWS","values":values})

def contract(tok,sid):
    rows=sheet_values(tok,sid,"'__ENVIRONMENT_CONTRACT'!A:B")
    return {str(r[0]):str(r[1]) for r in rows if len(r)>=2 and str(r[0]).strip()}

def contract_set(tok,sid,key,value):
    rows=sheet_values(tok,sid,"'__ENVIRONMENT_CONTRACT'!A:B")
    row=None
    for i,r in enumerate(rows,1):
        if r and str(r[0])==key:row=i;break
    if row is None:raise RuntimeError("CONTRACT_KEY_MISSING:"+key)
    sheet_put(tok,sid,f"'__ENVIRONMENT_CONTRACT'!A{row}:B{row}",[[key,value]])

def gas_files(kind):
    if kind=="primary":
        manifest=(ROOT/"google-apps-script/stable-primary-appsscript.json").read_text()
        names=["AUTH_HELPERS.gs","OUTBOUND_DROP_RECEIVE.gs","PICK_PACK_API.gs","SERVICE_MIGRATION_M2.gs","ZZZ_GITHUB_OTA_OVERRIDE.gs"]
        files=[{"name":pathlib.Path(n).stem,"type":"SERVER_JS","source":(ROOT/"google-apps-script"/n).read_text()} for n in names]
        if "stable_runtime_canary" not in files[2]["source"]:raise RuntimeError("PRIMARY_CANARY_SOURCE_MISSING")
    else:
        base=ROOT/"google-apps-script"/("stable-outbound" if kind=="outbound" else "stable-dr")
        manifest=(base/"appsscript.json").read_text()
        src=(base/"Code.gs").read_text()
        if "stable_runtime_canary" not in src:raise RuntimeError(kind.upper()+"_CANARY_SOURCE_MISSING")
        files=[{"name":"Code","type":"SERVER_JS","source":src}]
    files.append({"name":"appsscript","type":"JSON","source":manifest})
    return files

def web_entry(dep):
    found=[]
    for ep in dep.get("entryPoints",[]) or []:
        if ep.get("entryPointType")!="WEB_APP":continue
        w=ep.get("webApp") or {};cfg=w.get("entryPointConfig") or {}
        found.append({"url":str(w.get("url") or ""),"access":str(cfg.get("access") or ""),"executeAs":str(cfg.get("executeAs") or "")})
    if len(found)!=1:raise RuntimeError("WEBAPP_ENTRYPOINT_NOT_UNIQUE:"+str(len(found)))
    x=found[0]
    if x["access"]!="ANYONE_ANONYMOUS" or x["executeAs"]!="USER_DEPLOYING":raise RuntimeError("WEBAPP_ENTRYPOINT_POLICY_DRIFT")
    return x

def http_status(url):
    p=subprocess.run(["curl","-sS","-L","--connect-timeout","12","--max-time","30","-o","/dev/null","-w","%{http_code}",url],
      text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=35)
    return int(p.stdout.strip() or 0) if p.returncode==0 else 0

def main():
    tok=oauth();print("::add-mask::"+tok)
    req=json.loads((ROOT/"ops/stable-private-provision-request.json").read_text())
    if req.get("environment")!="STABLE" or req.get("stable_public_activation") is not False or req.get("mode")!="GAS_CANARY_UPDATE":
        raise RuntimeError("GAS_CANARY_UPDATE_REQUEST_FAIL_CLOSED")
    specs=[("primary","stable_primary_sheet_id"),("outbound","stable_outbound_sheet_id"),("dr","stable_dr_sheet_id")]
    before={};after={}
    # Full readback before any write: exact three existing projects/deployments only.
    for kind,key in specs:
        sid=str(req[key]);c=contract(tok,sid)
        if c.get("environment_id")!="STABLE" or c.get("stable_spreadsheet_id")!=sid:raise RuntimeError("STABLE_CONTRACT_IDENTITY_FAILED:"+kind)
        script_id=str(c.get("gas_script_id") or "");dep_id=str(c.get("gas_deployment_id") or "");url=str(c.get("gas_web_url") or "")
        if not script_id or not dep_id or not url:raise RuntimeError("EXISTING_GAS_ID_REQUIRED:"+kind)
        dep=req_json(f"{SCRIPT_API}/{script_id}/deployments/{dep_id}",token=tok)
        ep=web_entry(dep)
        if ep["url"]!=url:raise RuntimeError("GAS_URL_DRIFT:"+kind)
        before[kind]={"sheet_id":sid,"script_id":script_id,"deployment_id":dep_id,"url":url,"version":c.get("gas_version"),"entry":ep,"runtime_http":http_status(url)}
    if len({v["script_id"] for v in before.values()})!=3 or len({v["deployment_id"] for v in before.values()})!=3:
        raise RuntimeError("STABLE_GAS_NOT_DISTINCT")

    for kind,key in specs:
        x=before[kind]
        req_json(f"{SCRIPT_API}/{x['script_id']}/content","PUT",tok,{"files":gas_files(kind)})
        ver=req_json(f"{SCRIPT_API}/{x['script_id']}/versions","POST",tok,{"description":f"Stable {kind} runtime canary READY_NOT_LIVE"})
        vn=ver.get("versionNumber")
        if not isinstance(vn,int):raise RuntimeError("GAS_VERSION_MISSING:"+kind)
        dep=req_json(f"{SCRIPT_API}/{x['script_id']}/deployments/{x['deployment_id']}","PUT",tok,{
          "deploymentConfig":{"scriptId":x["script_id"],"versionNumber":vn,"manifestFileName":"appsscript","description":f"Stable {kind} runtime canary READY_NOT_LIVE"}})
        ep=web_entry(dep)
        if ep["url"]!=x["url"]:raise RuntimeError("GAS_DEPLOYMENT_URL_CHANGED:"+kind)
        contract_set(tok,x["sheet_id"],"gas_version",str(vn))
        after[kind]={"script_id":x["script_id"],"deployment_id":x["deployment_id"],"url":x["url"],"version":vn,"entry":ep,"runtime_http":http_status(x["url"])}
    for kind in before:
        if before[kind]["script_id"]!=after[kind]["script_id"] or before[kind]["deployment_id"]!=after[kind]["deployment_id"] or before[kind]["url"]!=after[kind]["url"]:
            raise RuntimeError("GAS_IDENTITY_CHANGED:"+kind)
    rec={"status":"PASS","mode":"GAS_CANARY_UPDATE","environment":"STABLE","stable_public_activation":False,
      "resource_changes":{"d1":False,"worker":False,"auth":False,"runtime_secrets":False,"gas_existing_deployments_only":True},
      "before":before,"after":after,"oauth_authorization_changed":False,
      "next_expected":"Existing webapps may remain HTTP403 until deployer grants Apps Script runtime OAuth consent."}
    pathlib.Path("/tmp/stable-private-provision-receipt.json").write_text(json.dumps(rec,indent=2)+"\n")
    print(json.dumps({"status":"PASS","mode":"GAS_CANARY_UPDATE","gas_count":3,"d1_changed":False,"worker_changed":False,"auth_changed":False}))
if __name__=="__main__":
    try:main()
    except Exception as e:
        pathlib.Path("/tmp/stable-private-provision-receipt.json").write_text(json.dumps({"status":"FAIL","mode":"GAS_CANARY_UPDATE","error":str(e)[:1200],"stable_public_activation":False},indent=2)+"\n")
        print("STABLE_GAS_CANARY_UPDATE_ERROR:"+str(e)[:1600],file=sys.stderr);sys.exit(1)
