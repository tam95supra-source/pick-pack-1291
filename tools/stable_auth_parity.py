#!/usr/bin/env python3
import base64,hashlib,json,os,pathlib,secrets,sys,urllib.error,urllib.parse,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
CF="https://api.cloudflare.com/client/v4"
OWNER_EMAIL="tam95.supra@gmail.com"
def need(n):
    v=os.environ.get(n,"").strip()
    if not v:raise RuntimeError("MISSING_REQUIRED_SECRET:"+n)
    return v
def req(url,method="GET",token=None,body=None,timeout=45):
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
    if code//100!=2 or j.get("success") is not True:raise RuntimeError("CF_API_FAILED:"+str(code))
    return j.get("result")
def oauth():
    data=urllib.parse.urlencode({"client_id":need("GOOGLE_OAUTH_CLIENT_ID"),"client_secret":need("GOOGLE_OAUTH_CLIENT_SECRET"),"refresh_token":need("GOOGLE_OAUTH_REFRESH_TOKEN"),"grant_type":"refresh_token"}).encode()
    r=urllib.request.Request("https://oauth2.googleapis.com/token",data=data,headers={"Content-Type":"application/x-www-form-urlencoded"},method="POST")
    with urllib.request.urlopen(r,timeout=45) as x:j=json.loads(x.read().decode())
    t=str(j.get("access_token",""))
    if not t:raise RuntimeError("GOOGLE_TOKEN_MISSING")
    return t
def d1_query(db,sql):
    r=cf("/d1/database/"+urllib.parse.quote(db,safe="")+"/query","POST",{"sql":sql})
    if not isinstance(r,list) or not r:raise RuntimeError("D1_QUERY_EMPTY")
    return r[0].get("results") or []
def sheet_values(tok,sid,rng):
    code,j=req("https://sheets.googleapis.com/v4/spreadsheets/"+urllib.parse.quote(sid,safe="")+"/values/"+urllib.parse.quote(rng,safe=""),token=tok)
    if code//100!=2:raise RuntimeError("SHEET_READ_FAILED:"+str(code))
    return j.get("values") or []
def sheet_put(tok,sid,rng,vals):
    code,j=req("https://sheets.googleapis.com/v4/spreadsheets/"+urllib.parse.quote(sid,safe="")+"/values/"+urllib.parse.quote(rng,safe="")+"?valueInputOption=RAW","PUT",tok,{"range":rng,"majorDimension":"ROWS","values":vals})
    if code//100!=2:raise RuntimeError("SHEET_WRITE_FAILED:"+str(code))
def b64u(b):return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def valid_verifier(v):
    try:
        p=str(v).split("$")
        if len(p)!=4 or p[0]!="pbkdf2_sha256" or int(p[1])<100000:return False
        for x,want in ((p[2],16),(p[3],32)):
            raw=x+"="*((4-len(x)%4)%4)
            if len(base64.urlsafe_b64decode(raw))!=want:return False
        return str(v).count("$")==3
    except Exception:return False
def make_verifier():
    password=b64u(secrets.token_bytes(24));salt=secrets.token_bytes(16);it=120000
    key=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,it,32)
    v="pbkdf2_sha256$"+str(it)+"$"+b64u(salt)+"$"+b64u(key)
    return password,v,hashlib.sha256(v.encode()).hexdigest()
def q(v):return "'"+str(v).replace("'","''")+"'"
def main():
    tok=oauth();print("::add-mask::"+tok)
    cfg=json.loads((ROOT/"ops/stable-private-provision-request.json").read_text())
    if cfg.get("mode")!="AUTH_PARITY_REPAIR" or cfg.get("environment")!="STABLE" or cfg.get("stable_public_activation") is not False:raise RuntimeError("AUTH_PARITY_REQUEST_FAIL_CLOSED")
    dbs=cf("/d1/database?per_page=100") or [];m=[x for x in dbs if x.get("name")==cfg["target_d1_name"]]
    if len(m)!=1:raise RuntimeError("STABLE_D1_NOT_UNIQUE")
    db=str(m[0].get("uuid") or m[0].get("id") or "")
    rows=d1_query(db,"SELECT login_id,verifier,verifier_hash,role,email,status FROM accounts ORDER BY login_id")
    active=[r for r in rows if str(r.get("status") or "").upper()=="ACTIVE"]
    if len(active)!=1 or active[0].get("login_id")!="admin" or active[0].get("role")!="SUPERADMIN":raise RuntimeError("STABLE_D1_AUTH_NOT_EXACT_ONE_ADMIN")
    a=active[0];ver=str(a.get("verifier") or "");vh=str(a.get("verifier_hash") or "");d1_changed=False
    if not valid_verifier(ver) or not vh or hashlib.sha256(ver.encode()).hexdigest()!=vh:
        password,ver,vh=make_verifier()
        for secret in (password,ver,vh):print("::add-mask::"+secret)
        checksum=hashlib.sha256(("admin|SUPERADMIN|ACTIVE|"+vh).encode()).hexdigest()
        d1_query(db,"UPDATE accounts SET verifier="+q(ver)+",verifier_hash="+q(vh)+",source_checksum="+q(checksum)+" WHERE login_id='admin' AND role='SUPERADMIN' AND status='ACTIVE'")
        check=d1_query(db,"SELECT verifier,verifier_hash FROM accounts WHERE login_id='admin'")
        if len(check)!=1 or check[0].get("verifier")!=ver or check[0].get("verifier_hash")!=vh:raise RuntimeError("STABLE_D1_VERIFIER_REPAIR_READBACK_FAILED")
        d1_changed=True
    print("::add-mask::"+ver);print("::add-mask::"+vh)
    sid=str(cfg["stable_primary_sheet_id"])
    if not sid or sid=="1E7ZWz-4eMcBliQxDYBVoogIoeSYyiaXGwj0I6mbMm78":raise RuntimeError("STABLE_SHEET_BINDING_INVALID")
    vals=sheet_values(tok,sid,"'Danh sách Admin'!A1:K200")
    data=[]
    for idx,r in enumerate(vals[1:],2):
        login=str(r[0]).strip() if r else ""
        if login:data.append((idx,r))
    others=[r for _,r in data if str(r[0]).strip()!="admin" and (str(r[8]).upper().strip() if len(r)>8 and str(r[8]).strip() else "ACTIVE")=="ACTIVE"]
    if others:raise RuntimeError("STABLE_SHEET_HAS_OTHER_ACTIVE_ACCOUNTS")
    admins=[(idx,r) for idx,r in data if str(r[0]).strip()=="admin"]
    now="AUTH_PARITY_REPAIR"
    rowvals=["admin",ver,"superadmin","admin","superadmin",str(a.get("email") or OWNER_EMAIL),"","","ACTIVE",now,""]
    if not admins:
        row=max(2,len(vals)+1);sheet_put(tok,sid,f"'Danh sách Admin'!A{row}:K{row}",[rowvals]);changed=True
    elif len(admins)==1:
        row,cur=admins[0]
        curver=str(cur[1]) if len(cur)>1 else "";currole=str(cur[2]).upper() if len(cur)>2 else "";curstatus=(str(cur[8]).upper() if len(cur)>8 and str(cur[8]).strip() else "ACTIVE")
        if currole!="SUPERADMIN" or curstatus!="ACTIVE":raise RuntimeError("STABLE_SHEET_ADMIN_ROLE_STATUS_MISMATCH")
        if curver!=ver:
            sheet_put(tok,sid,f"'Danh sách Admin'!A{row}:K{row}",[rowvals]);changed=True
        else:changed=False
    else:raise RuntimeError("STABLE_SHEET_ADMIN_DUPLICATE")
    after=sheet_values(tok,sid,"'Danh sách Admin'!A1:K200")
    active_after=[]
    for r in after[1:]:
        if not r or not str(r[0]).strip():continue
        status=(str(r[8]).upper().strip() if len(r)>8 and str(r[8]).strip() else "ACTIVE")
        if status=="ACTIVE":active_after.append((str(r[0]),str(r[2]).upper() if len(r)>2 else ""))
    if active_after!=[("admin","SUPERADMIN")]:raise RuntimeError("STABLE_SHEET_AUTH_READBACK_FAILED:"+json.dumps(active_after))
    rec={"status":"PASS","mode":"AUTH_PARITY_REPAIR","environment":"STABLE","d1_changed":d1_changed,"beta_touched":False,"sheet_changed":changed,
      "active_accounts":1,"login_id":"admin","role":"SUPERADMIN","verifier_hash_match":True,"verifier_format_valid":valid_verifier(ver),"password_plaintext":False}
    pathlib.Path("/tmp/stable-private-provision-receipt.json").write_text(json.dumps(rec,indent=2)+"\n")
    print(json.dumps(rec))
if __name__=="__main__":
    try:main()
    except Exception as e:
        pathlib.Path("/tmp/stable-private-provision-receipt.json").write_text(json.dumps({"status":"FAIL","mode":"AUTH_PARITY_REPAIR","error":str(e)[:1200],"password_plaintext":False},indent=2)+"\n")
        print("STABLE_AUTH_PARITY_ERROR:"+str(e)[:1600],file=sys.stderr);sys.exit(1)
