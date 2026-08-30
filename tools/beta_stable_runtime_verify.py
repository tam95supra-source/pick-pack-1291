#!/usr/bin/env python3
import json,os,pathlib,subprocess,sys,urllib.parse,urllib.request,urllib.error,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
CF="https://api.cloudflare.com/client/v4"

def need(n):
    v=os.environ.get(n,"").strip()
    if not v: raise RuntimeError("MISSING_REQUIRED_SECRET:"+n)
    return v
def req(url,method="GET",token=None,body=None,headers=None,timeout=45):
    data=None if body is None else json.dumps(body,separators=(",",":")).encode()
    h={"Accept":"application/json"}
    if token:h["Authorization"]="Bearer "+token
    if body is not None:h["Content-Type"]="application/json"
    if headers:h.update(headers)
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
    if code//100!=2 or j.get("success") is not True:raise RuntimeError("CF_API_FAILED:"+str(code)+":"+json.dumps(j.get("errors",j))[:500])
    return j.get("result")
def oauth():
    data=urllib.parse.urlencode({"client_id":need("GOOGLE_OAUTH_CLIENT_ID"),"client_secret":need("GOOGLE_OAUTH_CLIENT_SECRET"),"refresh_token":need("GOOGLE_OAUTH_REFRESH_TOKEN"),"grant_type":"refresh_token"}).encode()
    r=urllib.request.Request("https://oauth2.googleapis.com/token",data=data,headers={"Content-Type":"application/x-www-form-urlencoded"},method="POST")
    with urllib.request.urlopen(r,timeout=45) as x:j=json.loads(x.read().decode())
    t=str(j.get("access_token",""))
    if not t:raise RuntimeError("GOOGLE_TOKEN_MISSING")
    return t
def curl_json(method,url,headers=None,body=None):
    cmd=["curl","-sS","--connect-timeout","12","--max-time","35","-X",method]
    for k,v in (headers or {}).items():cmd += ["-H",f"{k}: {v}"]
    inp=None
    if body is not None:
        cmd += ["-H","Content-Type: application/json","--data-binary","@-"]
        inp=json.dumps(body,separators=(",",":"))
    cmd += ["-w","\n__STATUS__:%{http_code}",url]
    p=subprocess.run(cmd,input=inp,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
    if p.returncode:return -1,{"transport_error":p.stderr[-300:]}
    if "\n__STATUS__:" not in p.stdout:return -1,{"transport_error":"STATUS_MISSING"}
    raw,code=p.stdout.rsplit("\n__STATUS__:",1)
    try:j=json.loads(raw) if raw.strip() else {}
    except:j={"raw":raw[:500]}
    return int(code.strip()),j
def curl_status(url):
    p=subprocess.run(["curl","-sS","-L","--connect-timeout","8","--max-time","20","-o","/dev/null","-w","%{http_code}",url],text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=25)
    return int(p.stdout.strip() or 0) if p.returncode==0 else 0
def worker_settings(name):
    return cf("/workers/scripts/"+urllib.parse.quote(name,safe="")+"/settings") or {}
def bindmap(settings):return {str(b.get("name")):b for b in (settings.get("bindings") or [])}
def btext(by,k):return str((by.get(k) or {}).get("text") or "")
def bid(by,k):return str((by.get(k) or {}).get("id") or "")
def d1_rows(db,sql):
    r=cf("/d1/database/"+urllib.parse.quote(db,safe="")+"/query","POST",{"sql":sql})
    if not isinstance(r,list) or not r:raise RuntimeError("D1_QUERY_EMPTY")
    return r[0].get("results") or []
def sheet_values(tok,sid,rng):
    code,j=req("https://sheets.googleapis.com/v4/spreadsheets/"+urllib.parse.quote(sid,safe="")+"/values/"+urllib.parse.quote(rng,safe=""),token=tok)
    if code//100!=2:raise RuntimeError("SHEET_READ_FAILED:"+str(code))
    return j.get("values") or []
def sheet_contract(tok,sid):
    vals=sheet_values(tok,sid,"'__ENVIRONMENT_CONTRACT'!A:B")
    return {str(r[0]):str(r[1]) for r in vals if len(r)>=2 and str(r[0]).strip()}
def active_sheet_accounts(tok,sid):
    a=sheet_values(tok,sid,"'Danh sách Admin'!A1:A200")
    c=sheet_values(tok,sid,"'Danh sách Admin'!C1:C200")
    i=sheet_values(tok,sid,"'Danh sách Admin'!I1:I200")
    out=[]
    for idx in range(1,max(len(a),len(c),len(i))):
        login=str(a[idx][0]).strip() if idx<len(a) and a[idx] else ""
        if not login:continue
        role=str(c[idx][0]).upper().strip() if idx<len(c) and c[idx] else "USER"
        status=str(i[idx][0]).upper().strip() if idx<len(i) and i[idx] else "ACTIVE"
        if status=="ACTIVE":out.append((login,role))
    return sorted(out)
def gas_probe(url):
    code,j=curl_json("POST",url,body={"action":"__RUNTIME_AUTHORIZATION_PROBE__","_environment_id":"STABLE","_service_audience":"PICK_PACK_1291_STABLE"})
    return {"http":code,"json":bool(j),"error":((j.get("error") or {}).get("code") if isinstance(j.get("error"),dict) else j.get("error"))}
def main():
    for n in ["CLOUDFLARE_API_TOKEN","CLOUDFLARE_ACCOUNT_ID","GOOGLE_OAUTH_CLIENT_ID","GOOGLE_OAUTH_CLIENT_SECRET","GOOGLE_OAUTH_REFRESH_TOKEN"]:
        print("::add-mask::"+need(n))
    tok=oauth();print("::add-mask::"+tok)
    contract=json.loads((ROOT/"config/environment_contracts.json").read_text())
    prov=json.loads((ROOT/"ops/stable-private-provision-request.json").read_text())
    beta_c=contract["environments"]["BETA"]; stable_c=contract["environments"]["STABLE"]
    beta_name=str(beta_c["current_service"]["worker"]); stable_name=str(prov["target_worker_name"])
    beta_s,stable_s=worker_settings(beta_name),worker_settings(stable_name)
    bb,sb=bindmap(beta_s),bindmap(stable_s)
    beta_db=bid(bb,"DB");stable_db=bid(sb,"DB")
    if not beta_db or not stable_db or beta_db==stable_db:raise RuntimeError("D1_ENVIRONMENT_ISOLATION_FAILED")
    if btext(sb,"ENVIRONMENT_ID")!="STABLE" or btext(sb,"SERVICE_AUDIENCE")!="PICK_PACK_1291_STABLE":raise RuntimeError("STABLE_WORKER_ENV_BINDING_FAILED")
    beta_env=btext(bb,"ENVIRONMENT_ID") or "BETA"; beta_aud=btext(bb,"SERVICE_AUDIENCE") or "PICK_PACK_1291_BETA"
    if beta_env!="BETA" or beta_aud!="PICK_PACK_1291_BETA":raise RuntimeError("BETA_WORKER_ENV_BINDING_FAILED")
    if btext(sb,"GOOGLE_SOURCE_SHEET_ID")!=prov["stable_primary_sheet_id"] or btext(sb,"GOOGLE_OUTBOUND_SHEET_ID")!=prov["stable_outbound_sheet_id"]:raise RuntimeError("STABLE_SHEET_BINDING_FAILED")
    if btext(bb,"GOOGLE_SOURCE_SHEET_ID")!=beta_c["gsheet"]["spreadsheet_id"]:raise RuntimeError("BETA_SHEET_BINDING_FAILED")
    if any(k in sb for k in ["GOOGLE_OAUTH_CLIENT_ID","GOOGLE_OAUTH_CLIENT_SECRET","GOOGLE_OAUTH_REFRESH_TOKEN"]):raise RuntimeError("STABLE_BROAD_GOOGLE_OAUTH_PRESENT")
    dbs=cf("/d1/database?per_page=100") or []
    if len(dbs)!=3:raise RuntimeError("D1_COUNT_DRIFT:"+str(len(dbs)))
    sub=str((cf("/workers/subdomain") or {}).get("subdomain") or "")
    beta_url=f"https://{beta_name}.{sub}.workers.dev"; stable_url=f"https://{stable_name}.{sub}.workers.dev"
    bh=curl_json("GET",beta_url+"/health")[1]; sh=curl_json("GET",stable_url+"/health")[1]
    if not bh.get("ok") or not sh.get("ok"):raise RuntimeError("WORKER_HEALTH_FAILED")
    be=curl_json("GET",beta_url+"/environment.json")[1]; se=curl_json("GET",stable_url+"/environment.json")[1]
    if be.get("environment_id")!="BETA" or se.get("environment_id")!="STABLE":raise RuntimeError("ENVIRONMENT_ENDPOINT_FAILED")
    b_mismatch,_=curl_json("GET",beta_url+"/v1/sync/status",headers={"X-Pick-Pack-Environment":"STABLE","X-Pick-Pack-Audience":"PICK_PACK_1291_STABLE"})
    s_mismatch,_=curl_json("GET",stable_url+"/v1/sync/status",headers={"X-Pick-Pack-Environment":"BETA","X-Pick-Pack-Audience":"PICK_PACK_1291_BETA"})
    s_missing,_=curl_json("GET",stable_url+"/v1/sync/status")
    if b_mismatch not in (403,409) or s_mismatch not in (403,409) or s_missing not in (403,409):raise RuntimeError("CROSS_ENVIRONMENT_HTTP_FENCE_FAILED")
    beta_active=sorted((str(r.get("login_id")),str(r.get("role"))) for r in d1_rows(beta_db,"SELECT login_id,role FROM accounts WHERE status='ACTIVE' ORDER BY login_id"))
    stable_active=sorted((str(r.get("login_id")),str(r.get("role"))) for r in d1_rows(stable_db,"SELECT login_id,role FROM accounts WHERE status='ACTIVE' ORDER BY login_id"))
    want_beta=sorted([("adminbeta","SUPERADMIN"),("admintest","ADMIN"),("user1","USER"),("user2","USER"),("user3","USER")])
    if beta_active!=want_beta:raise RuntimeError("BETA_D1_AUTH_TARGET_FAILED:"+json.dumps(beta_active))
    if stable_active!=[("admin","SUPERADMIN")]:raise RuntimeError("STABLE_D1_AUTH_TARGET_FAILED:"+json.dumps(stable_active))
    beta_sheet=active_sheet_accounts(tok,beta_c["gsheet"]["spreadsheet_id"])
    stable_sheet=active_sheet_accounts(tok,prov["stable_primary_sheet_id"])
    if beta_sheet!=want_beta:raise RuntimeError("BETA_SHEET_AUTH_TARGET_FAILED:"+json.dumps(beta_sheet))
    if stable_sheet!=[("admin","SUPERADMIN")]:raise RuntimeError("STABLE_SHEET_AUTH_TARGET_FAILED:"+json.dumps(stable_sheet))
    gas={}
    for kind,sid in [("primary",prov["stable_primary_sheet_id"]),("outbound",prov["stable_outbound_sheet_id"]),("dr",prov["stable_dr_sheet_id"])]:
        c=sheet_contract(tok,sid)
        if c.get("environment_id")!="STABLE" or not c.get("gas_web_url"):raise RuntimeError("STABLE_GAS_CONTRACT_FAILED:"+kind)
        gas[kind]={"lifecycle":c.get("lifecycle"),**gas_probe(c["gas_web_url"])}
        if gas[kind]["http"]!=200:raise RuntimeError("STABLE_GAS_RUNTIME_NOT_AUTHORIZED:"+kind+":"+str(gas[kind]["http"]))
    beta_domain=curl_status(str(beta_c["target_web_origin"]))
    stable_domain=curl_status(str(stable_c["target_web_origin"]))
    if beta_domain not in (200,301,302,307,308,401,403):raise RuntimeError("BETA_TARGET_DOMAIN_NOT_READY:"+str(beta_domain))
    if stable_domain in (200,301,302,307,308):raise RuntimeError("STABLE_ROOT_DOMAIN_PUBLIC:"+str(stable_domain))
    receipt={"status":"PASS","d1_count":len(dbs),"workers":{"beta":beta_name,"stable":stable_name,"db_separate":True,"sheet_separate":True,"stable_broad_google_oauth_absent":True},
      "auth":{"beta_active":[x[0] for x in beta_active],"stable_active":[x[0] for x in stable_active],"sheet_parity":True},
      "cross_environment":{"beta_rejects_stable_headers":True,"stable_rejects_beta_headers":True,"stable_missing_env_rejected":True},
      "gas":gas,"domains":{"beta_target_http":beta_domain,"stable_root_http":stable_domain,"stable_public":False},
      "stable_public_activation":False,"d1_quota_guard":"PASS_COUNT_3"}
    pathlib.Path("/tmp/beta-stable-runtime-verify.json").write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"status":"PASS","d1_count":3,"beta_auth":5,"stable_auth":1,"gas":3,"stable_public":False}))
if __name__=="__main__":
    try:main()
    except Exception as e:
        pathlib.Path("/tmp/beta-stable-runtime-verify.json").write_text(json.dumps({"status":"FAIL","error":str(e)[:1200]},indent=2)+"\n")
        print("BETA_STABLE_RUNTIME_VERIFY_ERROR:"+str(e)[:1600],file=sys.stderr);sys.exit(1)
