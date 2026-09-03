#!/usr/bin/env python3
import base64, hashlib, hmac, json, os, pathlib, secrets, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
CF="https://api.cloudflare.com/client/v4"
OWNER_EMAIL="tam95.supra@gmail.com"
TARGETS=[
 ("adminbeta","SUPERADMIN"),
 ("admintest","ADMIN"),
 ("user1","USER"),
 ("user2","USER"),
 ("user3","USER"),
]

def need(n):
    v=os.environ.get(n,"").strip()
    if not v: raise RuntimeError("MISSING_REQUIRED_SECRET:"+n)
    return v

def req_json(url,method="GET",token=None,body=None,headers=None,timeout=60):
    data=None if body is None else json.dumps(body,separators=(",",":")).encode()
    h={"Accept":"application/json"}
    if token: h["Authorization"]="Bearer "+token
    if data is not None: h["Content-Type"]="application/json"
    if headers: h.update(headers)
    r=urllib.request.Request(url,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(r,timeout=timeout) as x:
            raw=x.read().decode("utf-8")
            return x.status,(json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw=e.read().decode("utf-8","replace")
        try:j=json.loads(raw)
        except:j={"raw":raw[:800]}
        return e.code,j

def cf(path,method="GET",body=None):
    code,j=req_json(f"{CF}/accounts/{need('CLOUDFLARE_ACCOUNT_ID')}{path}",method,need("CLOUDFLARE_API_TOKEN"),body)
    if code//100!=2 or j.get("success") is not True:
        raise RuntimeError("CLOUDFLARE_API_FAILED:"+str(code)+":"+json.dumps(j.get("errors",j))[:700])
    return j.get("result")

def google_token():
    body=urllib.parse.urlencode({
      "client_id":need("GOOGLE_OAUTH_CLIENT_ID"),
      "client_secret":need("GOOGLE_OAUTH_CLIENT_SECRET"),
      "refresh_token":need("GOOGLE_OAUTH_REFRESH_TOKEN"),
      "grant_type":"refresh_token"}).encode()
    r=urllib.request.Request("https://oauth2.googleapis.com/token",data=body,headers={"Content-Type":"application/x-www-form-urlencoded"},method="POST")
    with urllib.request.urlopen(r,timeout=45) as x:j=json.loads(x.read().decode())
    t=str(j.get("access_token",""))
    if not t:raise RuntimeError("GOOGLE_ACCESS_TOKEN_MISSING")
    return t

def health(url):
    try:
        p=subprocess.run(["curl","-fsS","--connect-timeout","10","--max-time","20",url+"/health"],text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=25)
        if p.returncode:return None
        return json.loads(p.stdout)
    except:return None

def bindings(name):
    s=cf("/workers/scripts/"+urllib.parse.quote(name,safe="")+"/settings") or {}
    return s,{str(b.get("name")):b for b in (s.get("bindings") or [])}

def text_binding(by,name,default=""):
    b=by.get(name) or {}
    return str(b.get("text") or default)

def d1_binding(by):
    b=by.get("DB") or {}
    return str(b.get("id") or "")

def discover():
    sub=str((cf("/workers/subdomain") or {}).get("subdomain") or "")
    if not sub:raise RuntimeError("WORKERS_SUBDOMAIN_MISSING")
    scripts=cf("/workers/scripts?per_page=100") or []
    beta=[];stable=[]
    for x in scripts:
        name=str(x.get("id") or x.get("name") or "")
        if not name:continue
        try:s,by=bindings(name)
        except:continue
        db=d1_binding(by)
        if not db:continue
        env=text_binding(by,"ENVIRONMENT_ID","BETA").upper()
        url=f"https://{name}.{sub}.workers.dev"
        h=health(url)
        item={"name":name,"url":url,"env":env,"db":db,"gas":text_binding(by,"GAS_API_URL"),"sheet":text_binding(by,"GOOGLE_SOURCE_SHEET_ID"),"aud":text_binding(by,"SERVICE_AUDIENCE", "PICK_PACK_1291_STABLE" if env=="STABLE" else "PICK_PACK_1291_BETA"),"health":h}
        if env=="STABLE":stable.append(item)
        elif item["gas"] and item["sheet"] and h and (h.get("authority") or {}).get("mode")=="SERVICE_PRIMARY" and (h.get("authority") or {}).get("scope")=="PRODUCTION":
            beta.append(item)
    if len(beta)!=1:
        diag=[]
        for x in scripts:
            name=str(x.get("id") or x.get("name") or "")
            if not name:continue
            try:
                _,by=bindings(name);env=text_binding(by,"ENVIRONMENT_ID","BETA").upper();h=health(f"https://{name}.{sub}.workers.dev")
                diag.append({"worker":name,"env":env,"db":bool(d1_binding(by)),"gas":bool(text_binding(by,"GAS_API_URL")),"sheet":bool(text_binding(by,"GOOGLE_SOURCE_SHEET_ID")),"health":bool(h and h.get("ok") is True),"authority_mode":str(((h or {}).get("authority") or {}).get("mode") or "")})
            except:pass
        print("BETA_AUTH_DISCOVERY_DIAG:"+json.dumps(diag,separators=(",",":")),file=sys.stderr)
        raise RuntimeError("BETA_LIVE_WORKER_NOT_UNIQUE:"+str(len(beta)))
    if len(stable)!=1:raise RuntimeError("STABLE_WORKER_NOT_UNIQUE:"+str(len(stable)))
    if beta[0]["db"]==stable[0]["db"] or beta[0]["sheet"]==stable[0]["sheet"]:raise RuntimeError("BETA_STABLE_AUTH_BINDING_COLLISION")
    return beta[0],stable[0]

def d1_query(db,sql):
    r=cf(f"/d1/database/{urllib.parse.quote(db,safe='')}/query","POST",{"sql":sql})
    if not isinstance(r,list) or not r:raise RuntimeError("D1_QUERY_EMPTY")
    if r[0].get("success") is False:raise RuntimeError("D1_QUERY_FAILED:"+json.dumps(r[0])[:700])
    return r[0].get("results") or []

def q(v): return "'"+str(v).replace("'","''")+"'"

def sheet_get(tok,sid,rng):
    code,j=req_json(f"https://sheets.googleapis.com/v4/spreadsheets/{urllib.parse.quote(sid,safe='')}/values/{urllib.parse.quote(rng,safe='')}",token=tok)
    if code//100!=2:raise RuntimeError("SHEET_READ_FAILED:"+str(code))
    return j.get("values") or []

def sheet_put(tok,sid,rng,values):
    code,j=req_json(f"https://sheets.googleapis.com/v4/spreadsheets/{urllib.parse.quote(sid,safe='')}/values/{urllib.parse.quote(rng,safe='')}?valueInputOption=RAW","PUT",tok,{"range":rng,"majorDimension":"ROWS","values":values})
    if code//100!=2:raise RuntimeError("SHEET_WRITE_FAILED:"+str(code)+":"+json.dumps(j)[:500])

def b64u(b):return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

def make_credential():
    password=b64u(secrets.token_bytes(24));salt=secrets.token_bytes(16);it=120000
    key=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,it,32)
    verifier=f"pbkdf2_sha256${it}${b64u(salt)}${b64u(key)}"
    return password,verifier,hashlib.sha256(verifier.encode()).hexdigest()

def split_worker_curl_output(out):
    marker="\n__HTTP_STATUS__:"
    if marker not in out: raise RuntimeError("WORKER_CURL_STATUS_MISSING")
    raw,code=out.rsplit(marker,1)
    try:j=json.loads(raw) if raw.strip() else {}
    except:j={"raw":raw[:500]}
    return int(code.strip()),j

def worker_transport_selftest():
    code,j=split_worker_curl_output('{"ok":true}\n__HTTP_STATUS__:200')
    if code!=200 or j.get("ok") is not True: raise RuntimeError("WORKER_CURL_PARSER_POSITIVE_FAIL")
    try:split_worker_curl_output('{"ok":false}')
    except RuntimeError as e:
        if str(e)!="WORKER_CURL_STATUS_MISSING": raise
    else: raise RuntimeError("WORKER_CURL_PARSER_NEGATIVE_FAIL")

def worker_json(method,url,body=None,headers=None):
    cmd=["curl","-sS","--connect-timeout","15","--max-time","45","-X",method]
    for k,v in (headers or {}).items(): cmd += ["-H",f"{k}: {v}"]
    if body is not None:
        cmd += ["-H","Content-Type: application/json","--data-binary","@-"]
    cmd += ["-w","\\n__HTTP_STATUS__:%{http_code}",url]
    p=subprocess.run(cmd,input=(json.dumps(body,separators=(",",":")) if body is not None else None),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=55)
    if p.returncode: raise RuntimeError("WORKER_CURL_FAILED:"+p.stderr[-500:])
    return split_worker_curl_output(p.stdout)

def gas_post(url,payload):
    p=subprocess.run(["curl","-fsS","-L","--connect-timeout","15","--max-time","45","-H","Content-Type: application/json","--data-binary","@-",url],
      input=json.dumps(payload,separators=(",",":")),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=55)
    if p.returncode:raise RuntimeError("GAS_HTTP_FAILED:"+p.stderr[-500:])
    try:return json.loads(p.stdout)
    except:raise RuntimeError("GAS_JSON_FAILED:"+p.stdout[:500])

def proof(password,salt,it,challenge):
    raw=salt+"="*((4-len(salt)%4)%4)
    key=hashlib.pbkdf2_hmac("sha256",password.encode(),base64.urlsafe_b64decode(raw),it,32)
    return b64u(hmac.new(key,challenge.encode(),hashlib.sha256).digest())

def sanitized_d1(db):
    rows=d1_query(db,"SELECT login_id,role,status,verifier_hash FROM accounts ORDER BY login_id")
    clean=[{"login_id":str(r.get("login_id","")),"role":str(r.get("role","")),"status":str(r.get("status","")),"verifier_hash":str(r.get("verifier_hash",""))} for r in rows]
    return clean,hashlib.sha256(json.dumps(clean,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def sanitized_sheet(tok,sid):
    rows=sheet_get(tok,sid,"'Danh sách Admin'!A1:K200")
    clean=[]
    for i,r in enumerate(rows[1:],2):
        login=str(r[0]).strip() if len(r)>0 else ""
        if not login:continue
        verifier=str(r[1]) if len(r)>1 else ""
        clean.append({"row":i,"login_id":login,"role":(str(r[2]).upper() if len(r)>2 else "USER"),"status":(str(r[8]).upper() if len(r)>8 and str(r[8]).strip() else "ACTIVE"),"verifier_hash":hashlib.sha256(verifier.encode()).hexdigest() if verifier else ""})
    return clean,hashlib.sha256(json.dumps(clean,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def repair_sheet_parity_from_d1(tok,beta,stable):
    target_roles=dict(TARGETS);target_ids=set(target_roles)
    beta_d1_before,beta_d1_hash_before=sanitized_d1(beta["db"])
    beta_sheet_before,beta_sheet_hash_before=sanitized_sheet(tok,beta["sheet"])
    stable_d1_before,stable_d1_hash_before=sanitized_d1(stable["db"])
    stable_sheet_before,stable_sheet_hash_before=sanitized_sheet(tok,stable["sheet"])
    raw=d1_query(beta["db"],"SELECT login_id,role,status,verifier,display_name,position,email,source_row FROM accounts ORDER BY login_id")
    by_login={str(x.get("login_id") or ""):x for x in raw}
    active=sorted((str(x.get("login_id") or ""),str(x.get("role") or "")) for x in raw if str(x.get("status") or "").upper()=="ACTIVE")
    want=sorted(TARGETS)
    if active!=want:raise RuntimeError("BETA_D1_AUTH_TARGET_FAILED:"+json.dumps(active))
    current_rows={x["login_id"]:x["row"] for x in beta_sheet_before}
    occupied={x["row"]:x["login_id"] for x in beta_sheet_before}
    next_row=max([x["row"] for x in beta_sheet_before] or [1])+1
    repaired=[]
    now=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
    for login,role in TARGETS:
        src=by_login.get(login) or {}
        verifier=str(src.get("verifier") or "")
        if not verifier:raise RuntimeError("BETA_D1_VERIFIER_MISSING:"+login)
        row=current_rows.get(login)
        if not row:
            preferred=int(src.get("source_row") or 0)
            if preferred>=2 and (preferred not in occupied or occupied.get(preferred)==login):
                row=preferred
            else:
                while next_row in occupied:next_row+=1
                row=next_row;next_row+=1
            repaired.append(login)
        occupied[row]=login
        display=str(src.get("display_name") or login)
        position=str(src.get("position") or role.lower())
        email=str(src.get("email") or OWNER_EMAIL)
        sheet_put(tok,beta["sheet"],f"'Danh sách Admin'!A{row}:K{row}",[[login,verifier,role.lower(),display,position,email,"","","ACTIVE","AUTH_PARITY_REPAIR",now]])
    beta_sheet_after,beta_sheet_hash_after=sanitized_sheet(tok,beta["sheet"])
    active_sheet=sorted((x["login_id"],x["role"]) for x in beta_sheet_after if x["status"]=="ACTIVE")
    if active_sheet!=want:raise RuntimeError("BETA_SHEET_AUTH_TARGET_FAILED:"+json.dumps(active_sheet))
    d1_verifier_hash={login:hashlib.sha256(str((by_login.get(login) or {}).get("verifier") or "").encode()).hexdigest() for login in target_ids}
    sheet_verifier_hash={x["login_id"]:x["verifier_hash"] for x in beta_sheet_after if x["login_id"] in target_ids}
    if d1_verifier_hash!=sheet_verifier_hash:raise RuntimeError("BETA_SHEET_VERIFIER_PARITY_FAILED")
    beta_d1_after,beta_d1_hash_after=sanitized_d1(beta["db"])
    stable_d1_after,stable_d1_hash_after=sanitized_d1(stable["db"])
    stable_sheet_after,stable_sheet_hash_after=sanitized_sheet(tok,stable["sheet"])
    if beta_d1_hash_after!=beta_d1_hash_before:raise RuntimeError("BETA_D1_CHANGED_DURING_SHEET_PARITY_REPAIR")
    if stable_d1_hash_after!=stable_d1_hash_before or stable_sheet_hash_after!=stable_sheet_hash_before:raise RuntimeError("STABLE_AUTH_CHANGED_DURING_BETA_SHEET_PARITY_REPAIR")
    receipt={
      "status":"PASS","environment":"BETA","mode":"REPAIR_BETA_AUTH_SHEET_PARITY",
      "target_active_accounts":[x[0] for x in want],"repaired_sheet_accounts":sorted(repaired),
      "passwords_rotated":False,"d1_mutated":False,"sessions_revoked":False,
      "verifier_parity":"PASS","beta_d1_unchanged":True,"stable_unchanged":True,
      "before":{"beta_d1_hash":beta_d1_hash_before,"beta_sheet_hash":beta_sheet_hash_before,"stable_d1_hash":stable_d1_hash_before,"stable_sheet_hash":stable_sheet_hash_before},
      "after":{"beta_d1_hash":beta_d1_hash_after,"beta_sheet_hash":beta_sheet_hash_after,"stable_d1_hash":stable_d1_hash_after,"stable_sheet_hash":stable_sheet_hash_after},
      "password_plaintext_in_receipt":False,"credentials_logged":False
    }
    pathlib.Path("/tmp/beta-auth-converge-receipt.json").write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"status":"PASS","mode":"REPAIR_BETA_AUTH_SHEET_PARITY","repaired":sorted(repaired),"passwords_rotated":False,"d1_mutated":False,"stable_unchanged":True}))


def stable_reject(stable,service_token):
    headers={"X-Pick-Pack-Environment":"STABLE","X-Pick-Pack-Audience":"PICK_PACK_1291_STABLE","Authorization":"Bearer "+service_token}
    code,_=worker_json("GET",stable["url"]+"/v1/sync/status",headers=headers)
    if code not in (401,403):raise RuntimeError("BETA_TOKEN_ACCEPTED_BY_STABLE:"+str(code))
    bad={"X-Pick-Pack-Environment":"BETA","X-Pick-Pack-Audience":"PICK_PACK_1291_BETA","Authorization":"Bearer "+service_token}
    code2,_=worker_json("GET",stable["url"]+"/v1/sync/status",headers=bad)
    if code2 not in (401,403,409):raise RuntimeError("BETA_ENV_ACCEPTED_BY_STABLE:"+str(code2))
    return code,code2

def main():
    for n in ["CLOUDFLARE_API_TOKEN","CLOUDFLARE_ACCOUNT_ID","GOOGLE_OAUTH_CLIENT_ID","GOOGLE_OAUTH_CLIENT_SECRET","GOOGLE_OAUTH_REFRESH_TOKEN"]:
        print("::add-mask::"+need(n))
    tok=google_token();print("::add-mask::"+tok)
    beta,stable=discover()
    release=json.loads((ROOT/"ops/beta-release-request.json").read_text())
    if release.get("mode")=="REPAIR_BETA_AUTH_SHEET_PARITY":
        repair_sheet_parity_from_d1(tok,beta,stable)
        return
    beta_before,beta_d1_hash_before=sanitized_d1(beta["db"]); beta_sheet_before,beta_sheet_hash_before=sanitized_sheet(tok,beta["sheet"])
    stable_before,stable_d1_hash_before=sanitized_d1(stable["db"]); stable_sheet_before,stable_sheet_hash_before=sanitized_sheet(tok,stable["sheet"])
    if len([x for x in beta_before if x["status"]=="ACTIVE"])<1:raise RuntimeError("BETA_NO_ACTIVE_ACCOUNT_PRECHECK")
    if not beta["gas"].startswith("https://script.google.com/"):raise RuntimeError("BETA_GAS_BINDING_INVALID")

    # Replacement first: old accounts remain untouched until adminbeta proves GAS + Service auth.
    current_rows={x["login_id"]:x["row"] for x in beta_sheet_before}
    next_row=max([x["row"] for x in beta_sheet_before] or [1])+1
    creds={}
    row_map={}
    now=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
    for login,role in TARGETS:
        password,verifier,vhash=make_credential()
        for secret in (password,verifier):print("::add-mask::"+secret)
        creds[login]=(password,verifier,vhash)
        row=current_rows.get(login)
        if not row:row=next_row;next_row+=1
        row_map[login]=row
        sheet_put(tok,beta["sheet"],f"'Danh sách Admin'!A{row}:K{row}",[[login,verifier,role.lower(),login,role.lower(),OWNER_EMAIL,"","","ACTIVE","AUTH_TARGET_MIGRATION",now]])
        checksum=hashlib.sha256(f"{login}|{role}|ACTIVE|{row}".encode()).hexdigest()
        sql=f"""INSERT INTO accounts(login_id,verifier,verifier_hash,role,display_name,position,email,status,source_row,source_checksum,is_shadow_test)
VALUES({q(login)},{q(verifier)},{q(vhash)},{q(role)},{q(login)},{q(role.lower())},{q(OWNER_EMAIL)},'ACTIVE',{row},{q(checksum)},0)
ON CONFLICT(login_id) DO UPDATE SET verifier=excluded.verifier,verifier_hash=excluded.verifier_hash,role=excluded.role,display_name=excluded.display_name,position=excluded.position,email=excluded.email,status='ACTIVE',source_row=excluded.source_row,source_checksum=excluded.source_checksum,is_shadow_test=0;"""
        d1_query(beta["db"],sql)

    # GAS auth cache is max 300 seconds and direct Sheets API does not execute onEdit.
    time.sleep(305)
    login="adminbeta";password=creds[login][0];device="auth-migrate-"+b64u(secrets.token_bytes(8))
    c=gas_post(beta["gas"],{"action":"login_challenge","login_id":login,"_device_id":device,"_app_channel":"BETA","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA"})
    if c.get("ok") is not True:raise RuntimeError("ADMINBETA_GAS_CHALLENGE_FAILED:"+str(c.get("error")))
    pr=proof(password,str(c["salt"]),int(c.get("iterations",120000)),str(c["challenge"]))
    print("::add-mask::"+pr)
    g=gas_post(beta["gas"],{"action":"login","login_id":login,"challenge_id":c["challenge_id"],"proof":pr,"_device_id":device,"_device_label":"CI AUTH MIGRATION","_app_channel":"BETA","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA"})
    if g.get("ok") is not True or (g.get("account") or {}).get("role")!="SUPERADMIN":raise RuntimeError("ADMINBETA_GAS_LOGIN_FAILED")
    gas_token=str(g.get("token",""));print("::add-mask::"+gas_token)
    # Prove the freshly issued GAS bearer directly before asking Service to exchange it.
    # Service's validator uses the same m2_authority_status call but has a short network timeout,
    # so bounded same-token retries distinguish a transient GAS fetch from bad credentials.
    gas_check=gas_post(beta["gas"],{"action":"m2_authority_status","_token":gas_token,"_device_id":device,"_app_channel":"BETA","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA","_app_version":"auth-converge-direct-proof"})
    if gas_check.get("ok") is not True or str(gas_check.get("authority_mode",""))!="SERVICE_PRIMARY":
        raise RuntimeError("ADMINBETA_GAS_SESSION_PROOF_FAILED:"+str(gas_check.get("error") or gas_check.get("authority_mode") or "UNKNOWN")[:120])
    sess={};code=0
    for attempt,delay in enumerate((0,3,8,15),1):
        if delay:time.sleep(delay)
        code,sess=worker_json("POST",beta["url"]+"/v1/auth/gas-session",body={"gas_token":gas_token,"device_id":device,"device_label":"CI AUTH MIGRATION","environment_id":"BETA","service_audience":"PICK_PACK_1291_BETA"},headers={"X-Pick-Pack-Environment":"BETA","X-Pick-Pack-Audience":"PICK_PACK_1291_BETA"})
        if code//100==2 and sess.get("ok") is True and (sess.get("account") or {}).get("role")=="SUPERADMIN":break
        err=(sess.get("error") or {})
        errcode=(err.get("code") if isinstance(err,dict) else str(err)) or sess.get("error_code") or "UNKNOWN"
        if str(errcode)!="GAS_SESSION_INVALID":break
    if code//100!=2 or sess.get("ok") is not True or (sess.get("account") or {}).get("role")!="SUPERADMIN":
        err=(sess.get("error") or {})
        errcode=(err.get("code") if isinstance(err,dict) else str(err)) or sess.get("error_code") or "UNKNOWN"
        raise RuntimeError("ADMINBETA_SERVICE_EXCHANGE_FAILED:"+str(code)+":"+str(errcode)[:120])
    service_token=str(sess.get("token",""));print("::add-mask::"+service_token)
    stable_code,stable_env_code=stable_reject(stable,service_token)

    # Only after replacement auth is proven: disable legacy accounts and revoke their D1 sessions/tokens.
    target_ids={x[0] for x in TARGETS}
    legacy=[x["login_id"] for x in beta_sheet_before if x["login_id"] not in target_ids]
    for x in beta_sheet_before:
        if x["login_id"] in legacy:
            sheet_put(tok,beta["sheet"],f"'Danh sách Admin'!I{x['row']}:K{x['row']}",[["DISABLED","AUTH_TARGET_MIGRATION",now]])
    if legacy:
        ids=",".join(q(x) for x in legacy)
        d1_query(beta["db"],f"UPDATE accounts SET status='DISABLED' WHERE login_id IN ({ids}); DELETE FROM auth_sessions WHERE login_id IN ({ids}); DELETE FROM auth_web_sessions WHERE login_id IN ({ids}); DELETE FROM auth_challenges WHERE login_id IN ({ids});")
    # Force the newly used adminbeta session to be disposable; owner will use Forgot Password when needed.
    d1_query(beta["db"],"DELETE FROM auth_sessions WHERE login_id='adminbeta'; DELETE FROM auth_web_sessions WHERE login_id='adminbeta';")

    # Wait out GAS account cache so legacy status is no longer usable by GAS token validation.
    time.sleep(305)
    beta_after,beta_d1_hash_after=sanitized_d1(beta["db"]); beta_sheet_after,beta_sheet_hash_after=sanitized_sheet(tok,beta["sheet"])
    stable_after,stable_d1_hash_after=sanitized_d1(stable["db"]); stable_sheet_after,stable_sheet_hash_after=sanitized_sheet(tok,stable["sheet"])
    active_d1=sorted(x["login_id"] for x in beta_after if x["status"]=="ACTIVE")
    active_sheet=sorted(x["login_id"] for x in beta_sheet_after if x["status"]=="ACTIVE")
    want=sorted(target_ids)
    if active_d1!=want or active_sheet!=want:raise RuntimeError("BETA_ACTIVE_TARGET_MISMATCH:"+json.dumps({"d1":active_d1,"sheet":active_sheet}))
    if any(x["login_id"]=="admin" and x["status"]=="ACTIVE" for x in beta_after+beta_sheet_after):raise RuntimeError("STABLE_ADMIN_ID_STILL_ACTIVE_IN_BETA")
    if stable_d1_hash_after!=stable_d1_hash_before or stable_sheet_hash_after!=stable_sheet_hash_before:raise RuntimeError("STABLE_AUTH_CHANGED_DURING_BETA_MIGRATION")
    if beta["db"]==stable["db"] or beta["sheet"]==stable["sheet"]:raise RuntimeError("AUTH_ISOLATION_COLLISION_POST")

    receipt={
      "status":"PASS","environment":"BETA","target_active_accounts":want,
      "replacement_first":{"adminbeta_gas_login":"PASS","adminbeta_service_exchange":"PASS","legacy_disabled_after_adminbeta_verified":True},
      "cross_environment":{"beta_token_to_stable_http":stable_code,"beta_environment_to_stable_http":stable_env_code,"stable_admin_absent_from_beta_active":True},
      "bindings":{"beta_worker":beta["name"],"stable_worker":stable["name"],"beta_db_separate":beta["db"]!=stable["db"],"beta_sheet_separate":beta["sheet"]!=stable["sheet"],"gas_health_authority_match":True},
      "before":{"beta_active_count":len([x for x in beta_before if x["status"]=="ACTIVE"]),"beta_d1_hash":beta_d1_hash_before,"beta_sheet_hash":beta_sheet_hash_before,"stable_d1_hash":stable_d1_hash_before,"stable_sheet_hash":stable_sheet_hash_before},
      "after":{"beta_active_count":len(active_d1),"beta_d1_hash":beta_d1_hash_after,"beta_sheet_hash":beta_sheet_hash_after,"stable_d1_hash":stable_d1_hash_after,"stable_sheet_hash":stable_sheet_hash_after},
      "legacy_accounts_disabled":sorted(legacy),
      "password_plaintext_in_receipt":False,"credentials_logged":False,
      "owner_recovery":"Use Forgot Password for adminbeta; generated CI bootstrap passwords are intentionally not persisted."
    }
    pathlib.Path("/tmp/beta-auth-converge-receipt.json").write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"status":"PASS","active_accounts":want,"adminbeta_login":"PASS","stable_unchanged":True,"legacy_disabled":len(legacy)}))

if __name__=="__main__":
    if "--self-test" in sys.argv:
        try:
            worker_transport_selftest()
            print("beta_auth_worker_transport_selftest=PASS")
        except Exception as e:
            print("BETA_AUTH_WORKER_TRANSPORT_SELFTEST_ERROR:"+str(e),file=sys.stderr);sys.exit(1)
        sys.exit(0)
    try:main()
    except Exception as e:
        pathlib.Path("/tmp/beta-auth-converge-receipt.json").write_text(json.dumps({"status":"FAIL","error":str(e)[:1200],"password_plaintext_in_receipt":False},indent=2)+"\n")
        print("BETA_AUTH_CONVERGE_ERROR:"+str(e)[:1600],file=sys.stderr);sys.exit(1)
