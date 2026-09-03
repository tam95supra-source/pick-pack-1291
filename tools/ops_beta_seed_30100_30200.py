#!/usr/bin/env python3
import base64, hashlib, hmac, json, os, pathlib, re, subprocess, sys, urllib.error, urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=pathlib.Path("/tmp/beta115-owner-seed-30100-30200.json")
SEED="OWNER_BETA115_30100_30200_20260903"
MNVS=[str(i) for i in range(30100,30201)]
SHIFTS=["Ca 1","Ca HC","Ca 2"]
LOGIN="";D1_NAME=""

def need(n):
    v=os.environ.get(n,"").strip()
    if not v:raise RuntimeError("MISSING_REQUIRED_SECRET:"+n)
    return v
def q(s):return "'" + str(s).replace("'","''") + "'"
def b64u(b):return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def det(m):return SHIFTS[int.from_bytes(hashlib.sha256(f"{SEED}|shift|{m}".encode()).digest()[:8],"big")%3]

def d1(sql):
    p=subprocess.run(["npx","wrangler","d1","execute",D1_NAME,"--remote","--command",sql,"--json"],
      cwd=str(ROOT/"service"),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=os.environ.copy(),timeout=120)
    if p.returncode:raise RuntimeError("D1_QUERY_FAILED:"+p.stderr[-400:].replace("\n"," "))
    j=json.loads(p.stdout)
    if not isinstance(j,list) or not j or j[0].get("success") is not True:raise RuntimeError("D1_QUERY_NOT_SUCCESS")
    return j[0].get("results") or []

def http(url,method="GET",token=None,body=None,timeout=45):
    h={"Accept":"application/json","X-Pick-Pack-Environment":"BETA","X-Pick-Pack-Audience":"PICK_PACK_1291_BETA"}
    if token:h["Authorization"]="Bearer "+token
    data=None
    if body is not None:
        h["Content-Type"]="application/json";data=json.dumps(body,ensure_ascii=False,separators=(",",":")).encode()
    r=urllib.request.Request(url,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(r,timeout=timeout) as x:
            raw=x.read().decode();return x.status,json.loads(raw or "{}")
    except urllib.error.HTTPError as e:
        raw=e.read().decode(errors="replace")
        try:j=json.loads(raw)
        except Exception:j={"raw":raw[:300]}
        return e.code,j

def must(url,method="GET",token=None,body=None,timeout=60):
    code,j=http(url,method,token,body,timeout)
    if code//100!=2 or j.get("ok") is not True:raise RuntimeError("SERVICE_CALL_FAILED:"+str(code)+":"+json.dumps(j.get("error") or j,ensure_ascii=False)[:500])
    return j

def cleanup():
    if LOGIN:
        try:d1("DELETE FROM auth_sessions WHERE login_id="+q(LOGIN)+"; DELETE FROM auth_web_sessions WHERE login_id="+q(LOGIN)+"; DELETE FROM auth_challenges WHERE login_id="+q(LOGIN)+"; DELETE FROM accounts WHERE login_id="+q(LOGIN)+";")
        except Exception:pass

def receipt(status,**extra):
    r={"schema_version":1,"project":"APK PICK PACK 1291","channel":"BETA","operation":"OWNER_TEST_ATTENDANCE_SEED_30100_30200",
       "status":status,"requested_count":101,"enter_only":True,"employee_master_mutations":0,"stable_write_attempts":0,
       "recorded_at_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z")}
    r.update(extra);OUT.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

try:
    account=need("CLOUDFLARE_ACCOUNT_ID");google_secret=need("GOOGLE_OAUTH_CLIENT_SECRET");need("CLOUDFLARE_API_TOKEN")
    cfg=json.loads((ROOT/"config/environment_contracts.json").read_text(encoding="utf-8"));beta=cfg["environments"]["BETA"];stable=cfg["environments"]["STABLE"]
    if beta.get("lifecycle")!="LIVE" or stable.get("lifecycle")=="LIVE":raise RuntimeError("ENVIRONMENT_LIFECYCLE_GUARD_FAILED")
    D1_NAME=str((beta.get("current_service") or {}).get("d1_database") or "")
    auth=d1("SELECT authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state WHERE singleton_id=1;")
    if len(auth)!=1 or auth[0].get("mode")!="SERVICE_PRIMARY" or auth[0].get("scope")!="PRODUCTION":raise RuntimeError("BETA_AUTHORITY_NOT_SERVICE_PRIMARY")
    generation=str(auth[0].get("service_generation") or "");epoch=int(auth[0].get("authority_epoch") or 0)

    def healthy(code,j):
        a=j.get("authority") or {}
        return code//100==2 and j.get("ok") is True and j.get("environment")=="production" and str(j.get("generation") or "")==generation and a.get("mode")=="SERVICE_PRIMARY" and a.get("scope")=="PRODUCTION" and int(a.get("authority_epoch") or 0)==epoch
    candidates=[]
    for u in [str((beta.get("current_service") or {}).get("url") or ""),str(beta.get("target_web_origin") or "")]:
        u=u.rstrip("/")
        if u and u not in candidates:candidates.append(u)
    diag=[];service_url=""
    for u in candidates:
        code,j=http(u+"/health",timeout=20);diag.append({"url":u,"http":code,"ok":j.get("ok") is True})
        if healthy(code,j):service_url=u;break
    if not service_url:raise RuntimeError("BETA_LIVE_DIRECT_UNAVAILABLE:"+json.dumps(diag,separators=(",",":")))

    emp=d1("SELECT mnv,main_position FROM employees WHERE length(mnv)=5 AND CAST(mnv AS INTEGER) BETWEEN 30100 AND 30200 ORDER BY CAST(mnv AS INTEGER);")
    if {str(x.get("mnv") or "") for x in emp}!=set(MNVS):raise RuntimeError("TARGET_EMPLOYEE_SET_MISMATCH")
    pos={}
    for x in emp:
        p=str(x.get("main_position") or "-");pos[p]=pos.get(p,0)+1
    business_date=datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%Y-%m-%d")
    before=d1("SELECT mnv,state,exit_at FROM attendance_sessions WHERE business_date="+q(business_date)+" AND length(mnv)=5 AND CAST(mnv AS INTEGER) BETWEEN 30100 AND 30200;")
    bad=[x for x in before if str(x.get("state"))!="ACTIVE" or x.get("exit_at") not in (None,"")]
    if bad:raise RuntimeError("TARGET_HAS_EXIT_OR_NONACTIVE")
    pre={str(x.get("mnv") or "") for x in before};pending=[m for m in MNVS if m not in pre]

    suffix=hashlib.sha256((os.environ.get("GITHUB_RUN_ID","run")+"-"+os.environ.get("GITHUB_RUN_ATTEMPT","1")).encode()).hexdigest()[:12]
    LOGIN="__OWNER_SEED_"+suffix;device="__OWNER_SEED_DEVICE_"+suffix;sess="__OWNER_SEED_AUTH_"+suffix;vh="owner_seed_"+suffix+"_vh";now=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    d1("DELETE FROM auth_sessions WHERE login_id="+q(LOGIN)+"; DELETE FROM accounts WHERE login_id="+q(LOGIN)+";"
       " INSERT INTO accounts(login_id,verifier,verifier_hash,role,display_name,position,email,status,source_row,source_checksum,is_shadow_test)"
       " VALUES("+q(LOGIN)+",'seed-fixture',"+q(vh)+",'SUPERADMIN','OWNER Beta test seed','TEST','','ACTIVE',-30100,'owner-beta-seed',1);"
       " INSERT INTO auth_sessions(login_id,session_id,device_id,issued_at) VALUES("+q(LOGIN)+","+q(sess)+","+q(device)+","+q(now)+");")
    secret=hashlib.sha256((account+"|"+google_secret+"|pick-pack-1291-m2-service-token-v1").encode()).hexdigest()
    payload={"l":LOGIN,"r":"SUPERADMIN","v":vh,"s":sess,"d":device,"c":"PDA"}
    enc=b64u(json.dumps(payload,separators=(",",":")).encode());token=enc+"."+b64u(hmac.new(secret.encode(),enc.encode(),hashlib.sha256).digest())

    events=[{"action":"enter","event_id":"OWNER_BETA_TEST_ENTER_"+business_date.replace("-","")+"_"+m,"device_id":"OWNER_BETA_TEST_SEED","business_date":business_date,
             "payload":{"mnv":m,"shift":det(m),"work_choice":"KHONG","note":"OWNER TEST ONLY"}} for m in pending]
    confirmed=duplicates=0
    for i in range(0,len(events),100):
        j=must(service_url+"/v1/legacy-mutations/batch","POST",token,{"events":events[i:i+100]},timeout=120)
        rs=j.get("results") or []
        if len(rs)!=len(events[i:i+100]):raise RuntimeError("BATCH_RESULT_COUNT_MISMATCH")
        bad=[x for x in rs if x.get("status") not in ("CONFIRMED","DUPLICATE")]
        if bad:raise RuntimeError("BATCH_REJECTED:"+json.dumps(bad[:5],ensure_ascii=False)[:600])
        confirmed+=sum(1 for x in rs if x.get("status")=="CONFIRMED");duplicates+=sum(1 for x in rs if x.get("status")=="DUPLICATE")

    final=d1("SELECT mnv,state,shift,work_choice,exit_at FROM attendance_sessions WHERE business_date="+q(business_date)+" AND length(mnv)=5 AND CAST(mnv AS INTEGER) BETWEEN 30100 AND 30200 ORDER BY CAST(mnv AS INTEGER);")
    if len(final)!=101 or any(str(x.get("state"))!="ACTIVE" or x.get("exit_at") not in (None,"") for x in final):raise RuntimeError("FINAL_D1_ENTER_ONLY_FAILED")
    shifts={s:0 for s in SHIFTS}
    for x in final:shifts[str(x.get("shift") or "")]=shifts.get(str(x.get("shift") or ""),0)+1
    if any(shifts.get(s,0)==0 for s in SHIFTS):raise RuntimeError("SHIFT_DISTRIBUTION_INCOMPLETE")
    receipt("PASS",business_date=business_date,transport="DIRECT_SERVICE_CUSTOM_OR_CANONICAL",service_url=service_url,
            preexisting_active_count=len(pre),new_enter_count=confirmed,duplicate_count=duplicates,active_count=101,exit_count=0,
            distribution={"shift":shifts,"employee_main_position":pos},d1_readback="PASS",authority_mode="SERVICE_PRIMARY",
            stable_unchanged_by_scope=True,idempotent_seed=True)
    cleanup();LOGIN=""
    print(json.dumps({"status":"PASS","business_date":business_date,"active":101,"exit":0,"new_enter":confirmed,"shift":shifts,"positions":pos,"service_url":service_url},ensure_ascii=False))
except Exception as e:
    cleanup();receipt("FAIL",error=str(e)[:1000],stable_unchanged_by_scope=True)
    print("BETA_OWNER_TEST_SEED_ERROR:"+str(e)[:1200],file=sys.stderr);sys.exit(1)
