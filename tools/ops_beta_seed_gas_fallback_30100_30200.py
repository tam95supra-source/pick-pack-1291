#!/usr/bin/env python3
import base64, hashlib, hmac, json, os, pathlib, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=pathlib.Path("/tmp/beta115-owner-seed-30100-30200.json")
SEED="OWNER_BETA115_30100_30200_20260903"
MNVS=[str(i) for i in range(30100,30201)]
SHIFTS=["Ca 1","Ca HC","Ca 2"]
gas_url=""; gas_token=""; device=""; D1_NAME=""

def need(n):
    v=os.environ.get(n,"").strip()
    if not v: raise RuntimeError("MISSING_REQUIRED_SECRET:"+n)
    return v

def q(s): return "'" + str(s).replace("'","''") + "'"
def b64ud(s): return base64.urlsafe_b64decode((s+"="*((4-len(s)%4)%4)).encode())
def b64u(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def det(kind,mnv,n): return int.from_bytes(hashlib.sha256(f"{SEED}|{kind}|{mnv}".encode()).digest()[:8],"big")%n

def req_json(url,method="GET",headers=None,body=None,form=None,timeout=60):
    h={"Accept":"application/json"}
    if headers:h.update(headers)
    data=None
    if body is not None:
        h["Content-Type"]="application/json";data=json.dumps(body,ensure_ascii=False,separators=(",",":")).encode()
    elif form is not None:
        h["Content-Type"]="application/x-www-form-urlencoded";data=urllib.parse.urlencode(form).encode()
    r=urllib.request.Request(url,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(r,timeout=timeout) as x:
            raw=x.read().decode(); return x.status,json.loads(raw or "{}")
    except urllib.error.HTTPError as e:
        raw=e.read().decode(errors="replace")
        try:j=json.loads(raw)
        except Exception:j={"raw":raw[:300]}
        return e.code,j

def google_token():
    code,j=req_json("https://oauth2.googleapis.com/token","POST",form={
      "client_id":need("GOOGLE_OAUTH_CLIENT_ID"),"client_secret":need("GOOGLE_OAUTH_CLIENT_SECRET"),
      "refresh_token":need("GOOGLE_OAUTH_REFRESH_TOKEN"),"grant_type":"refresh_token"})
    if code//100!=2 or not j.get("access_token"):raise RuntimeError("GOOGLE_OAUTH_FAILED:"+str(code))
    return str(j["access_token"])

def sheet_values(tok,sid,rng):
    u="https://sheets.googleapis.com/v4/spreadsheets/"+urllib.parse.quote(sid,safe="")+"/values/"+urllib.parse.quote(rng,safe="")+"?valueRenderOption=FORMATTED_VALUE"
    code,j=req_json(u,headers={"Authorization":"Bearer "+tok})
    if code//100!=2:raise RuntimeError("SHEETS_READ_FAILED:"+str(code)+":"+rng)
    return j.get("values") or []

def d1(sql):
    p=subprocess.run(["npx","wrangler","d1","execute",D1_NAME,"--remote","--command",sql,"--json"],
      cwd=str(ROOT/"service"),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=os.environ.copy(),timeout=120)
    if p.returncode:raise RuntimeError("D1_QUERY_FAILED:"+p.stderr[-400:].replace("\n"," "))
    j=json.loads(p.stdout)
    if not isinstance(j,list) or not j or j[0].get("success") is not True:raise RuntimeError("D1_QUERY_NOT_SUCCESS")
    return j[0].get("results") or []

def gas_post(body):
    action=str((body or {}).get("action") or "UNKNOWN")
    payload=json.dumps(body,ensure_ascii=False,separators=(",",":"))
    last=""
    for attempt in range(1,4):
        p=subprocess.run(["curl","-sS","-L","--connect-timeout","15","--max-time","45","-H","Content-Type: application/json","--data-binary","@-","-w","\\n__HTTP_STATUS__:%{http_code}",gas_url],
          input=payload,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=55)
        if p.returncode:
            last="TRANSPORT:"+p.stderr[-220:].replace("\n"," ")
        else:
            marker="\n__HTTP_STATUS__:"
            if marker not in p.stdout:last="STATUS_MISSING"
            else:
                raw,code_s=p.stdout.rsplit(marker,1)
                try:code=int(code_s.strip())
                except Exception:code=0
                if 200<=code<300:
                    try:return json.loads(raw or "{}")
                    except Exception as e:raise RuntimeError("GAS_BAD_JSON:"+action+":"+raw[:180]) from e
                last="HTTP_"+str(code)+":"+raw[:180].replace("\n"," ")
        if attempt<3:time.sleep(attempt)
    raise RuntimeError("GAS_CALL_FAILED:"+action+":"+last)

def env_body(action,extra=None):
    x={"action":action,"_app_channel":"BETA","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA"}
    if extra:x.update(extra)
    return x

def auth_body(action,extra=None):
    x=env_body(action,extra);x["_token"]=gas_token;x["_device_id"]=device;x["_device_label"]="OWNER BETA TEST SEED"
    return x

def operational(action,extra):
    last={}
    for attempt in range(1,4):
        last=gas_post(auth_body(action,extra))
        if last.get("ok") is True:return last
        err=str(last.get("error") or "")
        if err!="SERVICE_TEMP_UNAVAILABLE_RETRY":return last
        time.sleep(1)
    return last

def receipt(status,**extra):
    r={"schema_version":1,"project":"APK PICK PACK 1291","channel":"BETA",
       "operation":"OWNER_TEST_ATTENDANCE_SEED_30100_30200","transport":"GAS_SERVICE_BRIDGE",
       "status":status,"requested_count":101,"mnv_start":"30100","mnv_end":"30200",
       "enter_only":True,"employee_master_mutations":0,"stable_write_attempts":0,
       "recorded_at_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z")}
    r.update(extra);OUT.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

err=None; summary=None
try:
    cfg=json.loads((ROOT/"config/environment_contracts.json").read_text(encoding="utf-8"))
    beta=cfg["environments"]["BETA"];stable=cfg["environments"]["STABLE"]
    if beta.get("lifecycle")!="LIVE" or stable.get("lifecycle")=="LIVE":raise RuntimeError("ENVIRONMENT_LIFECYCLE_GUARD_FAILED")
    sid=str((beta.get("gsheet") or {}).get("spreadsheet_id") or "")
    D1_NAME=str(((beta.get("current_service") or {}).get("d1_database")) or "")
    if not sid or not D1_NAME:raise RuntimeError("BETA_BINDING_MISSING")
    gas_url="https://script.google.com/macros/s/"+need("GAS_DEPLOYMENT_ID")+"/exec"
    tok=google_token()

    discovery=gas_post(env_body("service_discovery"))
    mode=str(discovery.get("authority_mode") or (discovery.get("authority") or {}).get("mode") or "")
    business_date=str(discovery.get("business_date") or datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%Y-%m-%d"))
    if discovery.get("ok") is not True or discovery.get("environment_id")!="BETA" or discovery.get("service_audience")!="PICK_PACK_1291_BETA":
        raise RuntimeError("BETA_GAS_DISCOVERY_INVALID")
    if mode!="SERVICE_PRIMARY":raise RuntimeError("BETA_NOT_SERVICE_PRIMARY:"+mode)

    # Existing Beta master only; never mutate staff for this test-data request.
    emp=d1("SELECT mnv,main_position FROM employees WHERE length(mnv)=5 AND CAST(mnv AS INTEGER) BETWEEN 30100 AND 30200 ORDER BY CAST(mnv AS INTEGER);")
    got={str(x.get("mnv") or "") for x in emp}
    if got!=set(MNVS):raise RuntimeError("TARGET_EMPLOYEE_SET_MISMATCH:"+str(len(got)))
    pos_counts={}
    for x in emp:
        p=str(x.get("main_position") or "-");pos_counts[p]=pos_counts.get(p,0)+1

    # Authenticate with disposable Beta USER; verifier is read from Beta Sheet, no password required or changed.
    admins=sheet_values(tok,sid,"'Danh sách Admin'!A2:K")
    row=next((r for r in admins if str(r[0] if len(r)>0 else "").strip()=="user1"
              and str(r[2] if len(r)>2 else "").strip().upper()=="USER"
              and (str(r[8] if len(r)>8 else "ACTIVE").strip().upper() or "ACTIVE")=="ACTIVE"),None)
    if not row:raise RuntimeError("BETA_USER1_ACTIVE_ACCOUNT_NOT_FOUND")
    vp=str(row[1] if len(row)>1 else "").strip().split("$")
    if len(vp)!=4 or vp[0]!="pbkdf2_sha256":raise RuntimeError("BETA_USER1_VERIFIER_INVALID")
    key=b64ud(vp[3])
    device="owner-seed-"+hashlib.sha256((os.environ.get("GITHUB_RUN_ID","run")+"-gas").encode()).hexdigest()[:12]
    ch=gas_post(env_body("login_challenge",{"login_id":"user1","_device_id":device}))
    proof=b64u(hmac.new(key,str(ch.get("challenge") or "").encode(),hashlib.sha256).digest())
    lg=gas_post(env_body("login",{"login_id":"user1","challenge_id":ch.get("challenge_id"),"proof":proof,
                                   "_device_id":device,"_device_label":"OWNER BETA TEST SEED"}))
    if lg.get("ok") is not True or (lg.get("account") or {}).get("role")!="USER":raise RuntimeError("GAS_USER1_LOGIN_FAILED")
    gas_token=str(lg.get("token") or "")
    if not gas_token:raise RuntimeError("GAS_TOKEN_MISSING")

    before=d1("SELECT mnv,state,shift,work_choice,exit_at FROM attendance_sessions WHERE business_date="+q(business_date)+" AND length(mnv)=5 AND CAST(mnv AS INTEGER) BETWEEN 30100 AND 30200;")
    bad=[x for x in before if str(x.get("state"))!="ACTIVE" or x.get("exit_at") not in (None,"")]
    if bad:raise RuntimeError("TARGET_HAS_NON_ACTIVE_OR_EXIT_SESSION:"+str([x.get("mnv") for x in bad[:20]]))
    preactive={str(x.get("mnv") or "") for x in before}
    pending=[m for m in MNVS if m not in preactive]

    confirmed=0
    for mnv in pending:
        shift=SHIFTS[det("shift",mnv,len(SHIFTS))]
        body={"event_id":"OWNER_BETA_TEST_ENTER_"+business_date.replace("-","")+"_"+mnv,
              "business_date":business_date,"mnv":mnv,"shift":shift,"work_choice":"KHÔNG"}
        rr=operational("enter",body)
        if rr.get("ok") is not True:
            raise RuntimeError("ENTER_FAILED:"+mnv+":"+str(rr.get("error") or (rr.get("error") or {}).get("code") if isinstance(rr.get("error"),dict) else rr.get("error")))
        confirmed+=1

    final=d1("SELECT mnv,state,shift,work_choice,exit_at FROM attendance_sessions WHERE business_date="+q(business_date)+" AND length(mnv)=5 AND CAST(mnv AS INTEGER) BETWEEN 30100 AND 30200 ORDER BY CAST(mnv AS INTEGER);")
    if len(final)!=101:raise RuntimeError("FINAL_D1_COUNT:"+str(len(final)))
    bad=[x for x in final if str(x.get("state"))!="ACTIVE" or x.get("exit_at") not in (None,"")]
    if bad:raise RuntimeError("FINAL_D1_ENTER_ONLY_FAILED:"+str([x.get("mnv") for x in bad[:20]]))
    shifts={x:0 for x in SHIFTS}
    for x in final:shifts[str(x.get("shift") or "")]=shifts.get(str(x.get("shift") or ""),0)+1
    if any(shifts.get(s,0)==0 for s in SHIFTS):raise RuntimeError("SHIFT_DISTRIBUTION_INCOMPLETE:"+json.dumps(shifts))

    final_disc=gas_post(env_body("service_discovery"))
    final_mode=str(final_disc.get("authority_mode") or (final_disc.get("authority") or {}).get("mode") or "")
    if final_mode!="SERVICE_PRIMARY":raise RuntimeError("AUTHORITY_DRIFT_AFTER_SEED:"+final_mode)

    summary={"status":"PASS","business_date":business_date,"employees":101,"preexisting_active":len(preactive),
             "new_enter":confirmed,"active":101,"exit":0,"shift":shifts,"main_positions":pos_counts,
             "authority_mode":final_mode,"stable_write_attempts":0}
    receipt("PASS",business_date=business_date,authority_mode_before=mode,authority_mode_after=final_mode,
            employees_existing=101,preexisting_active_count=len(preactive),new_enter_count=confirmed,
            active_count=101,exit_count=0,distribution={"shift":shifts,"employee_main_position":pos_counts},
            d1_readback="PASS",stable_unchanged_by_scope=True,idempotent_seed=True)
except Exception as e:
    err=str(e)
finally:
    if gas_url and gas_token and device:
        try: gas_post(auth_body("logout",{}))
        except Exception: pass

if err:
    receipt("FAIL",error=err[:1000],stable_unchanged_by_scope=True)
    print("BETA_GAS_SERVICE_SEED_ERROR:"+err[:1200],file=sys.stderr)
    sys.exit(1)
print(json.dumps(summary,ensure_ascii=False))
