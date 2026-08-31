#!/usr/bin/env python3
import base64,hashlib,hmac,json,os,pathlib,secrets,sys,urllib.error,urllib.parse,urllib.request
CF="https://api.cloudflare.com/client/v4"
OUT=pathlib.Path("/tmp/beta-stable-auth-isolation.json")
def need(n):
    v=os.environ.get(n,"").strip()
    if not v: raise RuntimeError("MISSING_REQUIRED:"+n)
    return v
def req(url,method="GET",token=None,body=None,headers=None,timeout=40):
    data=None if body is None else json.dumps(body,separators=(",",":")).encode()
    h={"Accept":"application/json"}
    if token:h["Authorization"]="Bearer "+token
    if data is not None:h["Content-Type"]="application/json"
    if headers:h.update(headers)
    r=urllib.request.Request(url,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(r,timeout=timeout) as x:
            raw=x.read().decode("utf-8","replace"); return x.status,(json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw=e.read().decode("utf-8","replace")
        try:j=json.loads(raw)
        except:j={"raw":raw[:300]}
        return e.code,j
def cf(path,method="GET",body=None):
    code,j=req(f"{CF}/accounts/{need('CLOUDFLARE_ACCOUNT_ID')}{path}",method,need("CLOUDFLARE_API_TOKEN"),body)
    if code//100!=2 or j.get("success") is not True: raise RuntimeError("CF_API_FAILED:"+str(code))
    return j.get("result")
def bindmap(worker):
    s=cf("/workers/scripts/"+urllib.parse.quote(worker,safe="")+"/settings") or {}
    return {str(b.get("name")):b for b in (s.get("bindings") or [])}
def bid(m,k):return str((m.get(k) or {}).get("id") or "")
def btext(m,k):return str((m.get(k) or {}).get("text") or "")
def dq(db,sql):
    r=cf("/d1/database/"+urllib.parse.quote(db,safe="")+"/query","POST",{"sql":sql})
    if not isinstance(r,list) or not r or r[0].get("success") is False: raise RuntimeError("D1_QUERY_FAILED")
    return r[0].get("results") or []
def q(v):return "'"+str(v).replace("'","''")+"'"
def b64u(b):return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def b64ud(s):return base64.urlsafe_b64decode(str(s)+"="*((4-len(str(s))%4)%4))
def make_verifier(password):
    salt=secrets.token_bytes(16); it=120000
    key=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,it,32)
    v="pbkdf2_sha256$"+str(it)+"$"+b64u(salt)+"$"+b64u(key)
    return v,hashlib.sha256(v.encode()).hexdigest()
def proof(password,ch):
    salt=b64ud(ch["salt"]); it=int(ch["iterations"])
    key=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,it,32)
    return b64u(hmac.new(key,str(ch["challenge"]).encode(),hashlib.sha256).digest())
def api(base,env,aud,path,method="GET",body=None,token=None):
    h={"X-Pick-Pack-Environment":env,"X-Pick-Pack-Audience":aud}
    if token:h["Authorization"]="Bearer "+token
    return req(base+path,method,body=body,headers=h)
def login(base,env,aud,user,password,device):
    c,j=api(base,env,aud,"/v1/auth/challenge","POST",{"login_id":user})
    if c!=200 or not j.get("ok"): raise RuntimeError("CHALLENGE_FAILED:"+env+":"+str(c))
    p=proof(password,j)
    c2,j2=api(base,env,aud,"/v1/auth/login","POST",{"login_id":user,"challenge_id":j["challenge_id"],"proof":p,"device_id":device})
    return c2,j2
def main():
    for n in ["CLOUDFLARE_API_TOKEN","CLOUDFLARE_ACCOUNT_ID"]: print("::add-mask::"+need(n))
    beta_worker="pickpack"; stable_worker="pickpack1291-stable-private"
    bb,sb=bindmap(beta_worker),bindmap(stable_worker)
    beta_db,stable_db=bid(bb,"DB"),bid(sb,"DB")
    if not beta_db or not stable_db or beta_db==stable_db: raise RuntimeError("DB_ISOLATION_MISSING")
    if btext(bb,"ENVIRONMENT_ID") not in ("","BETA") or btext(sb,"ENVIRONMENT_ID")!="STABLE": raise RuntimeError("ENV_BINDING_DRIFT")
    if btext(sb,"SERVICE_AUDIENCE")!="PICK_PACK_1291_STABLE": raise RuntimeError("STABLE_AUDIENCE_DRIFT")
    sub=str((cf("/workers/subdomain") or {}).get("subdomain") or "")
    if not sub: raise RuntimeError("WORKERS_SUBDOMAIN_MISSING")
    beta="https://"+beta_worker+"."+sub+".workers.dev"; stable="https://"+stable_worker+"."+sub+".workers.dev"
    srows=dq(stable_db,"SELECT login_id,verifier,verifier_hash,role,status FROM accounts WHERE login_id='admin'")
    if len(srows)!=1 or srows[0].get("role")!="SUPERADMIN" or srows[0].get("status")!="ACTIVE": raise RuntimeError("STABLE_ADMIN_BASELINE_INVALID")
    if dq(stable_db,"SELECT COUNT(*) n FROM auth_sessions")[0].get("n",0)!=0 or dq(stable_db,"SELECT COUNT(*) n FROM auth_web_sessions")[0].get("n",0)!=0: raise RuntimeError("STABLE_SESSION_NOT_CLEAN_PREFLIGHT")
    oldv,oldh=str(srows[0]["verifier"]),str(srows[0]["verifier_hash"])
    canary="__audit_auth_"+str(os.environ.get("GITHUB_RUN_ID","local"))
    spass=b64u(secrets.token_bytes(24)); bpass=b64u(secrets.token_bytes(24))
    sv,sh=make_verifier(spass); bv,bh=make_verifier(bpass)
    for x in [spass,bpass,sv,sh,bv,bh]: print("::add-mask::"+x)
    inserted=False; stable_changed=False
    receipt={"status":"FAIL","environment":"BETA_STABLE","run_id":os.environ.get("GITHUB_RUN_ID"),"plaintext_secret":False}
    try:
        dq(stable_db,"UPDATE accounts SET verifier="+q(sv)+",verifier_hash="+q(sh)+" WHERE login_id='admin' AND role='SUPERADMIN' AND status='ACTIVE'")
        stable_changed=True
        chk=dq(stable_db,"SELECT verifier_hash FROM accounts WHERE login_id='admin'")
        if len(chk)!=1 or chk[0].get("verifier_hash")!=sh: raise RuntimeError("STABLE_TEMP_VERIFIER_READBACK_FAIL")
        c,sl=login(stable,"STABLE","PICK_PACK_1291_STABLE","admin",spass,"audit-stable")
        if c!=200 or not sl.get("ok") or not sl.get("token"): raise RuntimeError("STABLE_ADMIN_LOGIN_FAIL:"+str(c))
        stok=str(sl["token"]); print("::add-mask::"+stok)
        cb,bad=login(beta,"BETA","PICK_PACK_1291_BETA","admin",spass,"audit-cross")
        if cb!=401 or bad.get("ok") is not False: raise RuntimeError("STABLE_ADMIN_CROSS_LOGIN_NOT_REJECTED:"+str(cb))
        dq(beta_db,"INSERT INTO accounts(login_id,verifier,verifier_hash,role,display_name,position,email,status,source_row,source_checksum,is_shadow_test) VALUES("+q(canary)+","+q(bv)+","+q(bh)+",'USER','audit','audit','','ACTIVE',0,'AUDIT_AUTH_ISOLATION',1)")
        inserted=True
        cb2,bl=login(beta,"BETA","PICK_PACK_1291_BETA",canary,bpass,"audit-beta")
        if cb2!=200 or not bl.get("ok") or not bl.get("token"): raise RuntimeError("BETA_CANARY_LOGIN_FAIL:"+str(cb2))
        btok=str(bl["token"]); print("::add-mask::"+btok)
        x1,_=api(beta,"BETA","PICK_PACK_1291_BETA","/v1/auth/logout","POST",{},stok)
        x2,_=api(stable,"STABLE","PICK_PACK_1291_STABLE","/v1/auth/logout","POST",{},btok)
        if x1!=401 or x2!=401: raise RuntimeError("CROSS_TOKEN_REJECT_FAIL:"+str(x1)+":"+str(x2))
        lb,_=api(beta,"BETA","PICK_PACK_1291_BETA","/v1/auth/logout","POST",{},btok)
        if lb!=200: raise RuntimeError("BETA_LOGOUT_FAIL:"+str(lb))
        ls,_=api(stable,"STABLE","PICK_PACK_1291_STABLE","/v1/auth/logout","POST",{},stok)
        if ls!=200: raise RuntimeError("STABLE_SESSION_AFFECTED_BY_BETA_LOGOUT:"+str(ls))
        dq(beta_db,"UPDATE accounts SET role='ADMIN' WHERE login_id="+q(canary))
        sr=dq(stable_db,"SELECT role,verifier_hash FROM accounts WHERE login_id='admin'")[0]
        if sr.get("role")!="SUPERADMIN" or sr.get("verifier_hash")!=sh: raise RuntimeError("BETA_ROLE_CHANGE_AFFECTED_STABLE")
        c3,sl2=login(stable,"STABLE","PICK_PACK_1291_STABLE","admin",spass,"audit-stable-2")
        if c3!=200 or not sl2.get("token"): raise RuntimeError("STABLE_SECOND_LOGIN_FAIL")
        stok2=str(sl2["token"]); print("::add-mask::"+stok2)
        dq(stable_db,"UPDATE accounts SET verifier="+q(oldv)+",verifier_hash="+q(oldh)+" WHERE login_id='admin'")
        stable_changed=False
        rv,_=api(stable,"STABLE","PICK_PACK_1291_STABLE","/v1/auth/logout","POST",{},stok2)
        if rv!=401: raise RuntimeError("STABLE_PASSWORD_RESET_DID_NOT_REVOKE:"+str(rv))
        receipt.update({"status":"PASS","stable_admin_login":"PASS","stable_admin_beta_login_rejected":"PASS","cross_token_both_ways":"PASS","logout_isolation":"PASS","password_revoke":"PASS","role_isolation":"PASS"})
    except Exception as e:
        receipt["error"]=str(e)[:1000]
    finally:
        if stable_changed:
            try:dq(stable_db,"UPDATE accounts SET verifier="+q(oldv)+",verifier_hash="+q(oldh)+" WHERE login_id='admin'")
            except Exception:pass
        try:dq(stable_db,"DELETE FROM auth_challenges WHERE login_id='admin'; DELETE FROM auth_sessions WHERE login_id='admin'; DELETE FROM auth_web_sessions WHERE login_id='admin'")
        except Exception:pass
        if inserted:
            try:dq(beta_db,"DELETE FROM auth_challenges WHERE login_id="+q(canary)+"; DELETE FROM auth_sessions WHERE login_id="+q(canary)+"; DELETE FROM auth_web_sessions WHERE login_id="+q(canary)+"; DELETE FROM accounts WHERE login_id="+q(canary))
            except Exception:pass
        beta_active=sorted((str(r.get("login_id")),str(r.get("role"))) for r in dq(beta_db,"SELECT login_id,role FROM accounts WHERE status='ACTIVE' AND is_shadow_test=0 ORDER BY login_id"))
        stable_active=sorted((str(r.get("login_id")),str(r.get("role"))) for r in dq(stable_db,"SELECT login_id,role FROM accounts WHERE status='ACTIVE' ORDER BY login_id"))
        receipt["cleanup_beta_exact_five"]=len(beta_active)==5 and [x[0] for x in beta_active]==["adminbeta","admintest","user1","user2","user3"]
        receipt["cleanup_stable_exact_one"]=stable_active==[("admin","SUPERADMIN")]
        receipt["stable_sessions_clean"]=dq(stable_db,"SELECT COUNT(*) n FROM auth_sessions")[0].get("n",0)==0 and dq(stable_db,"SELECT COUNT(*) n FROM auth_web_sessions")[0].get("n",0)==0
        if receipt.get("status")=="PASS" and not all(receipt[k] for k in ["cleanup_beta_exact_five","cleanup_stable_exact_one","stable_sessions_clean"]):
            receipt["status"]="FAIL"; receipt["error"]="CLEANUP_READBACK_FAIL"
        OUT.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")
    if receipt.get("status")!="PASS": raise RuntimeError(str(receipt.get("error") or "AUTH_ISOLATION_FAILED"))
    print(json.dumps(receipt,separators=(",",":")))
if __name__=="__main__":
    try:main()
    except Exception as e:
        if not OUT.exists(): OUT.write_text(json.dumps({"status":"FAIL","error":str(e)[:1000],"plaintext_secret":False},indent=2)+"\n")
        print("BETA_STABLE_AUTH_ISOLATION_ERROR:"+str(e)[:1200],file=sys.stderr);sys.exit(1)
