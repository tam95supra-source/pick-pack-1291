#!/usr/bin/env python3
import base64, hashlib, hmac, json, os, pathlib, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=pathlib.Path("/tmp/beta115-owner-seed-30100-30200.json")
SEED="OWNER_BETA115_30100_30200_20260903"
MNVS=[str(i) for i in range(30100,30201)]
SHIFTS=["Ca 1","Ca HC","Ca 2"]
WORK_PREFS=["PICK","PACK","KHÔNG"]
gas_url="";gas_token="";device=""

def need(n):
    v=os.environ.get(n,"").strip()
    if not v: raise RuntimeError("MISSING_REQUIRED_SECRET:"+n)
    return v

def b64ud(s):
    return base64.urlsafe_b64decode((s+"="*((4-len(s)%4)%4)).encode())

def b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

def det(kind,mnv,n):
    return int.from_bytes(hashlib.sha256(f"{SEED}|{kind}|{mnv}".encode()).digest()[:8],"big")%n

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
            raw=x.read().decode()
            return x.status,json.loads(raw or "{}")
    except urllib.error.HTTPError as e:
        raw=e.read().decode(errors="replace")
        try:j=json.loads(raw)
        except Exception:j={"raw":raw[:300]}
        return e.code,j

def google_token():
    code,j=req_json("https://oauth2.googleapis.com/token","POST",form={
      "client_id":need("GOOGLE_OAUTH_CLIENT_ID"),
      "client_secret":need("GOOGLE_OAUTH_CLIENT_SECRET"),
      "refresh_token":need("GOOGLE_OAUTH_REFRESH_TOKEN"),
      "grant_type":"refresh_token"})
    if code//100!=2 or not j.get("access_token"):raise RuntimeError("GOOGLE_OAUTH_FAILED:"+str(code))
    return str(j["access_token"])

def sheet_values(tok,sid,rng):
    u="https://sheets.googleapis.com/v4/spreadsheets/"+urllib.parse.quote(sid,safe="")+"/values/"+urllib.parse.quote(rng,safe="")+"?valueRenderOption=FORMATTED_VALUE"
    code,j=req_json(u,headers={"Authorization":"Bearer "+tok})
    if code//100!=2:raise RuntimeError("SHEETS_READ_FAILED:"+str(code)+":"+rng)
    return j.get("values") or []

def gas_post(body):
    action=str((body or {}).get("action") or "UNKNOWN")
    payload=json.dumps(body,ensure_ascii=False,separators=(",",":"))
    last=""
    for attempt in range(1,5):
        p=subprocess.run(["curl","-sS","-L","--connect-timeout","15","--max-time","60","-H","Content-Type: application/json","--data-binary","@-","-w","\\n__HTTP_STATUS__:%{http_code}",gas_url],
          input=payload,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=70)
        if p.returncode:
            last="TRANSPORT:"+p.stderr[-240:].replace("\n"," ")
        else:
            marker="\n__HTTP_STATUS__:"
            if marker not in p.stdout:
                last="STATUS_MISSING"
            else:
                raw,code_s=p.stdout.rsplit(marker,1)
                try:code=int(code_s.strip())
                except Exception:code=0
                if 200<=code<300:
                    try:return json.loads(raw or "{}")
                    except Exception as e:raise RuntimeError("GAS_BAD_JSON:"+action+":"+raw[:180]) from e
                last="HTTP_"+str(code)+":"+raw[:180].replace("\n"," ")
                if code not in (404,408,425,429) and not (500<=code<600):
                    break
        if attempt<4:time.sleep(attempt)
    raise RuntimeError("GAS_CALL_FAILED:"+action+":"+last)

def env_body(action,extra=None):
    x={"action":action,"_app_channel":"BETA","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA"}
    if extra:x.update(extra)
    return x

def auth_body(action,extra=None):
    x=env_body(action,extra);x["_token"]=gas_token;x["_device_id"]=device;x["_device_label"]="OWNER BETA TEST SEED"
    return x

def receipt(status,**extra):
    r={"schema_version":1,"project":"APK PICK PACK 1291","channel":"BETA",
       "operation":"OWNER_TEST_ATTENDANCE_SEED_30100_30200","transport":"GAS_GOOGLE_FALLBACK","status":status,
       "requested_count":101,"mnv_start":"30100","mnv_end":"30200","enter_only":True,
       "employee_master_mutations":0,"stable_write_attempts":0,
       "recorded_at_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z")}
    r.update(extra);OUT.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def active_state_from_ra(rows,date_visible):
    states={m:"NOT_ENTERED" for m in MNVS}
    for r in rows:
        date=str(r[0] if len(r)>0 else "").strip()
        mnv=str(r[2] if len(r)>2 else "").strip()
        if date!=date_visible or mnv not in states:continue
        act=str(r[20] if len(r)>20 else r[15] if len(r)>15 else "").strip().upper()
        if act in ("ENTER","VAO","VÀO"):states[mnv]="ACTIVE"
        elif act in ("EXIT","RA"):states[mnv]="ENDED"
    return states

def work_from_label(v):
    s=str(v or "").strip().upper()
    if s=="PICK":return "PICK"
    if s=="PACK":return "PACK"
    return "KHÔNG"

err=None
summary=None
try:
    cfg=json.loads((ROOT/"config/environment_contracts.json").read_text(encoding="utf-8"))
    beta=cfg["environments"]["BETA"];stable=cfg["environments"]["STABLE"]
    if beta.get("lifecycle")!="LIVE" or stable.get("lifecycle")=="LIVE":raise RuntimeError("ENVIRONMENT_LIFECYCLE_GUARD_FAILED")
    sid=str((beta.get("gsheet") or {}).get("spreadsheet_id") or "")
    if not sid:raise RuntimeError("BETA_SHEET_ID_MISSING")
    gas_url="https://script.google.com/macros/s/"+need("GAS_DEPLOYMENT_ID")+"/exec"
    tok=google_token()

    discovery=gas_post(env_body("service_discovery"))
    if discovery.get("ok") is not True or discovery.get("environment_id")!="BETA" or discovery.get("service_audience")!="PICK_PACK_1291_BETA":
        raise RuntimeError("BETA_GAS_DISCOVERY_INVALID")
    mode_before=str(discovery.get("authority_mode") or (discovery.get("authority") or {}).get("mode") or "")
    business_date=str(discovery.get("business_date") or datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%Y-%m-%d"))
    if mode_before not in ("SERVICE_PRIMARY","GOOGLE_FALLBACK"):raise RuntimeError("BETA_AUTHORITY_MODE_UNEXPECTED:"+mode_before)
    date_visible=datetime.strptime(business_date,"%Y-%m-%d").strftime("%d/%m/%Y")

    staff=sheet_values(tok,sid,"'DANH SÁCH NHÂN SỰ'!A2:L")
    staff_by={str(r[0] if len(r)>0 else "").strip():r for r in staff if str(r[0] if len(r)>0 else "").strip() in MNVS}
    missing_staff=[m for m in MNVS if m not in staff_by]
    if missing_staff:raise RuntimeError("TARGET_EMPLOYEE_MISSING:"+",".join(missing_staff[:30]))

    ra_before=sheet_values(tok,sid,"'RA - VÀO TRONG CA'!A2:V")
    states_before=active_state_from_ra(ra_before,date_visible)
    ended=[m for m,s in states_before.items() if s=="ENDED"]
    if ended:raise RuntimeError("TARGET_ALREADY_ENDED_TODAY:"+",".join(ended[:30]))
    preactive=[m for m,s in states_before.items() if s=="ACTIVE"]
    pending=[m for m,s in states_before.items() if s=="NOT_ENTERED"]

    admins=sheet_values(tok,sid,"'Danh sách Admin'!A2:K")
    admin=None
    for row in admins:
        login=str(row[0] if len(row)>0 else "").strip()
        role=str(row[2] if len(row)>2 else "").strip().upper()
        status=str(row[8] if len(row)>8 else "ACTIVE").strip().upper() or "ACTIVE"
        if login=="user1" and role=="USER" and status=="ACTIVE":admin=row;break
    if not admin:raise RuntimeError("BETA_USER1_ACTIVE_ACCOUNT_NOT_FOUND")
    verifier=str(admin[1] if len(admin)>1 else "").strip();vp=verifier.split("$")
    if len(vp)!=4 or vp[0]!="pbkdf2_sha256":raise RuntimeError("BETA_ADMINTEST_VERIFIER_INVALID")
    key=b64ud(vp[3])

    device="owner-seed-"+hashlib.sha256((os.environ.get("GITHUB_RUN_ID","run")+"-gas").encode()).hexdigest()[:12]
    ch=gas_post(env_body("login_challenge",{"login_id":"user1","_device_id":device}))
    if ch.get("ok") is not True:raise RuntimeError("GAS_LOGIN_CHALLENGE_FAILED")
    proof=b64u(hmac.new(key,str(ch["challenge"]).encode(),hashlib.sha256).digest())
    login=gas_post(env_body("login",{"login_id":"user1","challenge_id":ch["challenge_id"],"proof":proof,"_device_id":device,"_device_label":"OWNER BETA TEST SEED"}))
    if login.get("ok") is not True or (login.get("account") or {}).get("role")!="USER":
        raise RuntimeError("GAS_USER1_LOGIN_FAILED:"+str(login.get("error") or (login.get("account") or {}).get("role") or "UNKNOWN"))
    gas_token=str(login.get("token") or "")
    if not gas_token:raise RuntimeError("GAS_TOKEN_MISSING")

    mode_after=mode_before
    fallback_epoch=(discovery.get("authority") or {}).get("authority_epoch")
    probe_responses=[]
    if pending and mode_before=="SERVICE_PRIMARY":
        probe={"mnv":"__OWNER_FALLBACK_PROBE__","event_id":"OWNER_BETA_FALLBACK_PROBE_"+business_date.replace("-",""),"work_choice":"KHÔNG"}
        for _ in range(3):
            pr=gas_post(auth_body("resource_change",probe))
            probe_responses.append(str(pr.get("error") or "OK"))
            d=gas_post(env_body("service_discovery"))
            mode_after=str(d.get("authority_mode") or (d.get("authority") or {}).get("mode") or "")
            fallback_epoch=(d.get("authority") or {}).get("authority_epoch")
            if mode_after=="GOOGLE_FALLBACK":break
        if mode_after!="GOOGLE_FALLBACK":raise RuntimeError("GOOGLE_FALLBACK_CLAIM_FAILED:"+json.dumps(probe_responses)[:300])
    elif mode_before=="GOOGLE_FALLBACK":
        mode_after="GOOGLE_FALLBACK"

    expected={}
    new_count=0
    for mnv in pending:
        shift=SHIFTS[det("shift",mnv,len(SHIFTS))]
        pref=WORK_PREFS[det("work",mnv,len(WORK_PREFS))]
        ctx=gas_post(auth_body("employee_context",{"mnv":mnv,"include_options":True}))
        if ctx.get("ok") is not True or ctx.get("state")!="NOT_ENTERED":raise RuntimeError("EMPLOYEE_CONTEXT_DRIFT:"+mnv+":"+str(ctx.get("state") or ctx.get("error")))
        opts=ctx.get("options") or {}
        choice="KHÔNG";extra={}
        if pref=="PICK":
            pdas=opts.get("pdas") or []
            if pdas:
                p=pdas[det("pda",mnv,len(pdas))]
                serial=str((p or {}).get("serial") if isinstance(p,dict) else p).strip()
                if serial:choice="PICK";extra["pda_serial"]=serial
        elif pref=="PACK":
            packs=[x for x in (opts.get("pack_tables") or []) if str((x or {}).get("shift") or "")==shift]
            if packs:
                p=packs[det("pack",mnv,len(packs))]
                table=str((p or {}).get("table") or "").strip()
                if table:choice="PACK";extra["pack_table"]=table
        body={"event_id":"OWNER_BETA_TEST_ENTER_"+business_date.replace("-","")+"_"+mnv,
              "business_date":business_date,"mnv":mnv,"shift":shift,"work_choice":choice}
        body.update(extra)
        rr=gas_post(auth_body("enter",body))
        if rr.get("ok") is not True:raise RuntimeError("ENTER_FAILED:"+mnv+":"+str(rr.get("error")))
        expected[mnv]={"shift":shift,"work":choice}
        new_count+=1

    ra_final=sheet_values(tok,sid,"'RA - VÀO TRONG CA'!A2:V")
    states_final=active_state_from_ra(ra_final,date_visible)
    not_active=[m for m,s in states_final.items() if s!="ACTIVE"]
    if not_active:raise RuntimeError("FINAL_ACTIVE_READBACK_FAILED:"+",".join(not_active[:30]))

    latest_enter={}
    exit_ids=[]
    for r in ra_final:
        date=str(r[0] if len(r)>0 else "").strip();mnv=str(r[2] if len(r)>2 else "").strip()
        if date!=date_visible or mnv not in states_final:continue
        act=str(r[20] if len(r)>20 else r[15] if len(r)>15 else "").strip().upper()
        if act in ("EXIT","RA"):exit_ids.append(mnv)
        if act in ("ENTER","VAO","VÀO"):latest_enter[mnv]=r
    if exit_ids:raise RuntimeError("FINAL_ENTER_ONLY_HAS_EXIT:"+",".join(sorted(set(exit_ids))[:30]))
    if len(latest_enter)!=101:raise RuntimeError("FINAL_ENTER_ROW_COUNT:"+str(len(latest_enter)))

    for m,e in expected.items():
        r=latest_enter[m]
        got_shift=str(r[1] if len(r)>1 else "").strip()
        got_work=work_from_label(r[10] if len(r)>10 else "")
        if got_shift!=e["shift"] or got_work!=e["work"]:raise RuntimeError("FINAL_ASSIGNMENT_MISMATCH:"+m)

    shifts={x:0 for x in SHIFTS};works={x:0 for x in WORK_PREFS}
    for m,r in latest_enter.items():
        sh=str(r[1] if len(r)>1 else "").strip()
        wk=work_from_label(r[10] if len(r)>10 else "")
        shifts[sh]=shifts.get(sh,0)+1;works[wk]=works.get(wk,0)+1

    main_positions={}
    for m,r in staff_by.items():
        p=str(r[3] if len(r)>3 else "").strip() or "-"
        main_positions[p]=main_positions.get(p,0)+1

    final_discovery=gas_post(env_body("service_discovery"))
    final_mode=str(final_discovery.get("authority_mode") or (final_discovery.get("authority") or {}).get("mode") or "")
    if pending and final_mode!="GOOGLE_FALLBACK":raise RuntimeError("FALLBACK_AUTHORITY_DRIFT_AFTER_SEED:"+final_mode)
    summary={"status":"PASS","transport":"GOOGLE_FALLBACK" if pending else "NO_WRITE_NEEDED","business_date":business_date,
             "employees_existing":101,"new_enter":new_count,"preexisting_active":len(preactive),"active":101,"exit":0,
             "shift":shifts,"work":works,"main_positions":len(main_positions),"authority_mode":final_mode,"stable_write_attempts":0}
    receipt("PASS",business_date=business_date,authority_mode_before=mode_before,authority_mode_after=final_mode,
            authority_epoch=fallback_epoch,employees_existing=101,new_enter_count=new_count,preexisting_active_count=len(preactive),
            active_count=101,exit_count=0,distribution={"shift":shifts,"work_choice":works,"employee_main_position":main_positions},
            fallback_probe=probe_responses,beta_sheet_readback="PASS",stable_unchanged_by_scope=True,idempotent_seed=True)
except Exception as e:
    err=str(e)
finally:
    if gas_url and gas_token and device:
        try: gas_post(auth_body("logout",{}))
        except Exception: pass

if err:
    receipt("FAIL",error=err[:1000],stable_unchanged_by_scope=True)
    print("BETA_GAS_FALLBACK_SEED_ERROR:"+err[:1200],file=sys.stderr)
    sys.exit(1)
print(json.dumps(summary,ensure_ascii=False))
