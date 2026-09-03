#!/usr/bin/env python3
import base64, hashlib, hmac, json, os, pathlib, subprocess, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=pathlib.Path("/tmp/beta115-owner-seed-30100-30200.json")
MARKER="BETA_TEST_QR_30100_30200"
SEED="OWNER_BETA115_30100_30200_20260903"
MNVS=[str(i) for i in range(30100,30201)]
SHIFTS=["Ca 1","Ca HC","Ca 2"]
WORK_CHOICES=["PICK","KHÔNG"]

def need(n):
    v=os.environ.get(n,"").strip()
    if not v: raise RuntimeError("MISSING_REQUIRED_SECRET:"+n)
    return v

def b64ud(s):
    v=s+"="*((4-len(s)%4)%4)
    return base64.urlsafe_b64decode(v.encode())

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
      "grant_type":"refresh_token"
    })
    if code//100!=2 or not j.get("access_token"):raise RuntimeError("GOOGLE_OAUTH_FAILED:"+str(code))
    return str(j["access_token"])

def sheet_values(tok,sid,rng):
    u="https://sheets.googleapis.com/v4/spreadsheets/"+urllib.parse.quote(sid,safe="")+"/values/"+urllib.parse.quote(rng,safe="")+"?valueRenderOption=FORMATTED_VALUE"
    code,j=req_json(u,headers={"Authorization":"Bearer "+tok})
    if code//100!=2:raise RuntimeError("SHEETS_READ_FAILED:"+str(code)+":"+rng)
    return j.get("values") or []

def gas_post(gas_url,body):
    p=subprocess.run(
      ["curl","-fsS","-L","--connect-timeout","15","--max-time","60","-H","Content-Type: application/json","--data-binary","@-",gas_url],
      input=json.dumps(body,ensure_ascii=False,separators=(",",":")),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=70)
    if p.returncode:raise RuntimeError("GAS_TRANSPORT_FAILED:"+p.stderr[-300:].replace("\n"," "))
    try:return json.loads(p.stdout)
    except Exception as e:raise RuntimeError("GAS_BAD_JSON:"+p.stdout[:200]) from e

def env_body(action,extra=None):
    x={"action":action,"_app_channel":"BETA","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA"}
    if extra:x.update(extra)
    return x

def auth_body(token,device,action,extra=None):
    x=env_body(action,extra);x["_token"]=token;x["_device_id"]=device;x["_device_label"]="OWNER BETA TEST SEED"
    return x

def write_receipt(status,**extra):
    r={"schema_version":1,"project":"APK PICK PACK 1291","channel":"BETA","operation":"OWNER_TEST_DATA_SEED_30100_30200","transport":"GAS_GOOGLE_FALLBACK","status":status,
       "requested_count":101,"mnv_start":"30100","mnv_end":"30200","enter_only":True,"stable_write_attempts":0,
       "marker":MARKER,"recorded_at_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z")}
    r.update(extra);OUT.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

try:
    cfg=json.loads((ROOT/"config/environment_contracts.json").read_text(encoding="utf-8"))
    beta=cfg["environments"]["BETA"];stable=cfg["environments"]["STABLE"]
    if beta.get("lifecycle")!="LIVE" or stable.get("lifecycle")=="LIVE":raise RuntimeError("ENVIRONMENT_LIFECYCLE_GUARD_FAILED")
    sid=str((beta.get("gsheet") or {}).get("spreadsheet_id") or "")
    if not sid:raise RuntimeError("BETA_SHEET_ID_MISSING")
    gas_id=need("GAS_DEPLOYMENT_ID")
    gas_url="https://script.google.com/macros/s/"+gas_id+"/exec"
    tok=google_token()

    discovery=gas_post(gas_url,env_body("service_discovery"))
    if discovery.get("ok") is not True or discovery.get("environment_id")!="BETA" or discovery.get("service_audience")!="PICK_PACK_1291_BETA":
        raise RuntimeError("BETA_GAS_DISCOVERY_INVALID")
    mode_before=str(discovery.get("authority_mode") or (discovery.get("authority") or {}).get("mode") or "")
    business_date=str(discovery.get("business_date") or datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%Y-%m-%d"))
    if mode_before not in ("SERVICE_PRIMARY","GOOGLE_FALLBACK"):raise RuntimeError("BETA_AUTHORITY_MODE_UNEXPECTED:"+mode_before)

    admins=sheet_values(tok,sid,"'Danh sách Admin'!A2:K")
    admin=None
    for row in admins:
        login=str(row[0] if len(row)>0 else "").strip()
        role=str(row[2] if len(row)>2 else "").strip().upper()
        status=str(row[8] if len(row)>8 else "ACTIVE").strip().upper() or "ACTIVE"
        if login=="admintest" and role=="ADMIN" and status=="ACTIVE":
            admin=row;break
    if not admin:raise RuntimeError("BETA_ADMINTEST_ACTIVE_ACCOUNT_NOT_FOUND")
    verifier=str(admin[1] if len(admin)>1 else "").strip()
    vp=verifier.split("$")
    if len(vp)!=4 or vp[0] not in ("pbkdf2_sha256","reset_sha256"):raise RuntimeError("BETA_ADMINTEST_VERIFIER_INVALID")
    key=b64ud(vp[3])

    device="owner-seed-"+hashlib.sha256((os.environ.get("GITHUB_RUN_ID","run")+"-gas").encode()).hexdigest()[:12]
    ch=gas_post(gas_url,env_body("login_challenge",{"login_id":"admintest","_device_id":device}))
    if ch.get("ok") is not True:raise RuntimeError("GAS_LOGIN_CHALLENGE_FAILED")
    proof=b64u(hmac.new(key,str(ch["challenge"]).encode(),hashlib.sha256).digest())
    login=gas_post(gas_url,env_body("login",{"login_id":"admintest","challenge_id":ch["challenge_id"],"proof":proof,"_device_id":device,"_device_label":"OWNER BETA TEST SEED"}))
    if login.get("ok") is not True or (login.get("account") or {}).get("role")!="ADMIN":raise RuntimeError("GAS_ADMINTEST_LOGIN_FAILED")
    gas_token=str(login.get("token") or "")
    if not gas_token:raise RuntimeError("GAS_TOKEN_MISSING")

    staff=sheet_values(tok,sid,"'DANH SÁCH NHÂN SỰ'!A2:L")
    existing={}
    positions=[]
    for row in staff:
        mnv=str(row[0] if len(row)>0 else "").strip()
        pos=str(row[3] if len(row)>3 else "").strip()
        note=str(row[9] if len(row)>9 else "").strip()
        if pos and mnv not in MNVS and pos not in positions:positions.append(pos)
        if mnv in MNVS:existing[mnv]={"note":note,"position":pos}
    if not positions:raise RuntimeError("BETA_POSITION_SOURCE_EMPTY")
    foreign=[m for m,x in existing.items() if MARKER not in x["note"]]
    if foreign:raise RuntimeError("MNV_RANGE_COLLIDES_WITH_NON_TEST_EMPLOYEES:"+",".join(sorted(foreign)[:30]))

    display_date=datetime.strptime(business_date,"%Y-%m-%d").strftime("%d/%m/%Y")
    ra_before=sheet_values(tok,sid,"'RA - VÀO TRONG CA'!A2:V")
    prior_exit=[]
    for row in ra_before:
        date=str(row[0] if len(row)>0 else "").strip()
        mnv=str(row[2] if len(row)>2 else "").strip()
        app=str(row[20] if len(row)>20 else "").strip().upper()
        if date==display_date and mnv in MNVS and app in ("EXIT","RA"):prior_exit.append(mnv)
    if prior_exit:raise RuntimeError("TEST_RANGE_ALREADY_HAS_EXIT:"+",".join(sorted(set(prior_exit))[:30]))

    mode_after=mode_before
    fallback_epoch=(discovery.get("authority") or {}).get("authority_epoch")
    probe_responses=[]
    if mode_before=="SERVICE_PRIMARY":
        probe={"mnv":"__OWNER_FALLBACK_PROBE__","event_id":"OWNER_BETA_FALLBACK_PROBE_"+business_date.replace("-",""),"work_choice":"KHÔNG","_device_id":device}
        for _ in range(3):
            pr=gas_post(gas_url,auth_body(gas_token,device,"resource_change",probe))
            probe_responses.append(str(pr.get("error") or "OK"))
            d=gas_post(gas_url,env_body("service_discovery"))
            mode_after=str(d.get("authority_mode") or (d.get("authority") or {}).get("mode") or "")
            fallback_epoch=(d.get("authority") or {}).get("authority_epoch")
            if mode_after=="GOOGLE_FALLBACK":break
        if mode_after!="GOOGLE_FALLBACK":
            raise RuntimeError("GOOGLE_FALLBACK_CLAIM_FAILED:"+json.dumps(probe_responses)[:300])
    elif mode_before=="GOOGLE_FALLBACK":
        mode_after="GOOGLE_FALLBACK"

    expected={}
    staff_ok=0
    for mnv in MNVS:
        pos=positions[det("position",mnv,len(positions))]
        shift=SHIFTS[det("shift",mnv,len(SHIFTS))]
        work=WORK_CHOICES[det("work",mnv,len(WORK_CHOICES))]
        expected[mnv]={"position":pos,"shift":shift,"work":work}
        body={
          "event_id":"OWNER_BETA_TEST_STAFF_"+mnv,
          "mnv":mnv,"full_name":"TEST QR "+mnv,"phone":"","main_position":pos,
          "supplier":"","department":"","site":"","warehouse":"","start_date":business_date,
          "note":MARKER+" | OWNER TEST"
        }
        rr=gas_post(gas_url,auth_body(gas_token,device,"staff_upsert",body))
        if rr.get("ok") is not True:raise RuntimeError("STAFF_UPSERT_FAILED:"+mnv+":"+str(rr.get("error")))
        staff_ok+=1

    enter_ok=0
    for mnv in MNVS:
        ex=expected[mnv]
        body={"event_id":"OWNER_BETA_TEST_ENTER_"+business_date.replace("-","")+"_"+mnv,
              "business_date":business_date,"mnv":mnv,"shift":ex["shift"],"work_choice":ex["work"]}
        rr=gas_post(gas_url,auth_body(gas_token,device,"enter",body))
        if rr.get("ok") is not True:raise RuntimeError("ENTER_FAILED:"+mnv+":"+str(rr.get("error")))
        enter_ok+=1

    final_discovery=gas_post(gas_url,env_body("service_discovery"))
    final_mode=str(final_discovery.get("authority_mode") or (final_discovery.get("authority") or {}).get("mode") or "")
    if final_mode!="GOOGLE_FALLBACK":raise RuntimeError("FALLBACK_AUTHORITY_DRIFT_AFTER_SEED:"+final_mode)

    staff_final=sheet_values(tok,sid,"'DANH SÁCH NHÂN SỰ'!A2:L")
    sm={str(r[0] if len(r)>0 else "").strip():r for r in staff_final if str(r[0] if len(r)>0 else "").strip() in MNVS}
    if len(sm)!=101:raise RuntimeError("STAFF_READBACK_COUNT:"+str(len(sm)))
    bad_staff=[]
    for m in MNVS:
        r=sm[m];pos=str(r[3] if len(r)>3 else "").strip();note=str(r[9] if len(r)>9 else "").strip()
        if pos!=expected[m]["position"] or MARKER not in note:bad_staff.append(m)
    if bad_staff:raise RuntimeError("STAFF_READBACK_MISMATCH:"+",".join(bad_staff[:30]))

    ra=sheet_values(tok,sid,"'RA - VÀO TRONG CA'!A2:V")
    target_rows=[]
    for r in ra:
        date=str(r[0] if len(r)>0 else "").strip();mnv=str(r[2] if len(r)>2 else "").strip()
        if date==display_date and mnv in MNVS:target_rows.append(r)
    by_m={m:[] for m in MNVS}
    for r in target_rows:by_m[str(r[2]).strip()].append(r)
    missing=[];with_exit=[];bad_shift=[]
    for m in MNVS:
        rows=by_m[m]
        if not rows:missing.append(m);continue
        acts=[str(r[20] if len(r)>20 else "").strip().upper() for r in rows]
        if any(a in ("EXIT","RA") for a in acts):with_exit.append(m)
        enter_rows=[r for r in rows if str(r[20] if len(r)>20 else "").strip().upper() in ("ENTER","VAO")]
        if not enter_rows:missing.append(m);continue
        last=enter_rows[-1]
        if str(last[1] if len(last)>1 else "").strip()!=expected[m]["shift"]:bad_shift.append(m)
    if missing:raise RuntimeError("ENTER_READBACK_MISSING:"+",".join(missing[:30]))
    if with_exit:raise RuntimeError("ENTER_ONLY_READBACK_HAS_EXIT:"+",".join(with_exit[:30]))
    if bad_shift:raise RuntimeError("SHIFT_READBACK_MISMATCH:"+",".join(bad_shift[:30]))

    shifts={x:0 for x in SHIFTS};works={x:0 for x in WORK_CHOICES};pos_counts={}
    for m,e in expected.items():
        shifts[e["shift"]]+=1;works[e["work"]]+=1;pos_counts[e["position"]]=pos_counts.get(e["position"],0)+1

    try:gas_post(gas_url,auth_body(gas_token,device,"logout",{}))
    except Exception:pass
    write_receipt("PASS",business_date=business_date,authority_mode_before=mode_before,authority_mode_after=final_mode,
                  authority_epoch=fallback_epoch,staff_upsert_count=staff_ok,active_enter_count=enter_ok,exit_count=0,
                  distribution={"shift":shifts,"work_choice":works,"main_position":pos_counts},
                  fallback_probe=probe_responses,beta_sheet_readback="PASS",stable_unchanged_by_scope=True,idempotent_seed=True)
    print(json.dumps({"status":"PASS","transport":"GOOGLE_FALLBACK","business_date":business_date,"employees":101,"active":101,"exit":0,"shift":shifts,"work":works,"positions":len(pos_counts),"authority_mode":final_mode,"stable_write_attempts":0},ensure_ascii=False))
except Exception as e:
    write_receipt("FAIL",error=str(e)[:1000],stable_unchanged_by_scope=True)
    print("BETA_GAS_FALLBACK_SEED_ERROR:"+str(e)[:1200],file=sys.stderr)
    sys.exit(1)
