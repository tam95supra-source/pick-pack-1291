#!/usr/bin/env python3
import base64, hashlib, hmac, json, os, pathlib, re, subprocess, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=pathlib.Path("/tmp/beta115-owner-seed-30100-30200.json")
MARKER="BETA_TEST_QR_30100_30200"
SEED="OWNER_BETA115_30100_30200_20260903"
MNV_LIST=[str(i) for i in range(30100,30201)]
SHIFTS=["Ca 1","Ca HC","Ca 2"]
WORK_CHOICES=["PICK","KHONG"]
LOGIN=""
D1_NAME=""

def need(name):
    v=os.environ.get(name,"").strip()
    if not v: raise RuntimeError("MISSING_REQUIRED_SECRET:"+name)
    return v

def q(s):
    return "'" + str(s).replace("'","''") + "'"

def wrangler_sql(sql):
    p=subprocess.run(
        ["npx","wrangler","d1","execute",D1_NAME,"--remote","--command",sql,"--json"],
        cwd=str(ROOT/"service"), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=os.environ.copy(), timeout=120)
    if p.returncode:
        raise RuntimeError("D1_QUERY_FAILED:"+p.stderr[-500:].replace("\n"," "))
    try: j=json.loads(p.stdout)
    except Exception as e: raise RuntimeError("D1_JSON_INVALID") from e
    if not isinstance(j,list) or not j or j[0].get("success") is not True:
        raise RuntimeError("D1_QUERY_NOT_SUCCESS")
    return j[0].get("results") or []

def service_json(url, method="GET", token=None, body=None, timeout=60):
    headers={"Accept":"application/json","X-Pick-Pack-Environment":"BETA","X-Pick-Pack-Audience":"PICK_PACK_1291_BETA"}
    data=None
    if token: headers["Authorization"]="Bearer "+token
    if body is not None:
        headers["Content-Type"]="application/json"
        data=json.dumps(body,ensure_ascii=False,separators=(",",":")).encode()
    req=urllib.request.Request(url,data=data,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            raw=r.read().decode()
            return r.status, json.loads(raw or "{}")
    except urllib.error.HTTPError as e:
        raw=e.read().decode(errors="replace")
        try: payload=json.loads(raw)
        except Exception: payload={"raw":raw[:500]}
        return e.code,payload

def must(url, method="GET", token=None, body=None, timeout=60):
    code,j=service_json(url,method,token,body,timeout)
    if code//100!=2 or j.get("ok") is not True:
        err=j.get("error") if isinstance(j,dict) else None
        raise RuntimeError("SERVICE_CALL_FAILED:"+str(code)+":"+json.dumps(err or j,ensure_ascii=False)[:500])
    return j

def b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

def det_index(kind,mnv,n):
    h=hashlib.sha256(f"{SEED}|{kind}|{mnv}".encode()).digest()
    return int.from_bytes(h[:8],"big")%n

def cleanup_auth():
    global LOGIN
    if LOGIN and D1_NAME:
        try:
            wrangler_sql("DELETE FROM auth_sessions WHERE login_id="+q(LOGIN)+"; DELETE FROM auth_web_sessions WHERE login_id="+q(LOGIN)+"; DELETE FROM auth_challenges WHERE login_id="+q(LOGIN)+"; DELETE FROM accounts WHERE login_id="+q(LOGIN)+";")
        except Exception:
            pass

def receipt(status, **extra):
    base={
      "schema_version":1,
      "project":"APK PICK PACK 1291",
      "channel":"BETA",
      "operation":"OWNER_TEST_DATA_SEED_30100_30200",
      "status":status,
      "mnv_start":"30100","mnv_end":"30200","requested_count":101,
      "enter_only":True,"stable_write_attempts":0,
      "marker":MARKER,
      "recorded_at_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    }
    base.update(extra)
    OUT.write_text(json.dumps(base,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

try:
    need("CLOUDFLARE_API_TOKEN"); account_id=need("CLOUDFLARE_ACCOUNT_ID"); google_secret=need("GOOGLE_OAUTH_CLIENT_SECRET")
    cfg=json.loads((ROOT/"config/environment_contracts.json").read_text(encoding="utf-8"))
    beta=cfg["environments"]["BETA"] if "environments" in cfg else cfg["channels"]["BETA"]
    stable=cfg["environments"]["STABLE"] if "environments" in cfg else cfg["channels"]["STABLE"]
    if str(beta.get("lifecycle"))!="LIVE": raise RuntimeError("BETA_NOT_LIVE")
    if str(stable.get("lifecycle"))=="LIVE": raise RuntimeError("STABLE_UNEXPECTEDLY_LIVE")
    service_url=str((beta.get("current_service") or {}).get("url") or "").rstrip("/")
    if not service_url.startswith("https://"): raise RuntimeError("BETA_SERVICE_URL_MISSING")

    workflow=(ROOT/".github/workflows/beta-release.yml").read_text(encoding="utf-8")
    m=re.search(r"(?m)^\s+D1_NAME:\s*([A-Za-z0-9_.-]+)\s*$",workflow)
    if not m: raise RuntimeError("BETA_D1_NAME_NOT_FOUND_IN_CANONICAL_WORKFLOW")
    D1_NAME=m.group(1)

    auth=wrangler_sql("SELECT authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state WHERE singleton_id=1;")
    if len(auth)!=1 or auth[0].get("mode")!="SERVICE_PRIMARY" or auth[0].get("scope")!="PRODUCTION":
        raise RuntimeError("BETA_AUTHORITY_NOT_SERVICE_PRIMARY_PRODUCTION")
    generation=str(auth[0].get("service_generation") or "")
    epoch=int(auth[0].get("authority_epoch") or 0)
    code,health=service_json(service_url+"/health",timeout=30)
    if code//100!=2 or health.get("ok") is not True or health.get("environment")!="production":
        raise RuntimeError("BETA_HEALTH_FAILED")
    ha=health.get("authority") or {}
    if str(health.get("generation") or "")!=generation or ha.get("mode")!="SERVICE_PRIMARY" or ha.get("scope")!="PRODUCTION" or int(ha.get("authority_epoch") or 0)!=epoch:
        raise RuntimeError("BETA_LIVE_READBACK_AUTHORITY_MISMATCH")

    suffix=hashlib.sha256((os.environ.get("GITHUB_RUN_ID","local")+"-"+os.environ.get("GITHUB_RUN_ATTEMPT","1")).encode()).hexdigest()[:12]
    LOGIN="__OWNER_SEED_"+suffix
    device="__OWNER_SEED_DEVICE_"+suffix
    auth_session="__OWNER_SEED_AUTH_"+suffix
    vhash="owner_seed_"+suffix+"_vh"
    now=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    wrangler_sql(
      "DELETE FROM auth_sessions WHERE login_id="+q(LOGIN)+"; DELETE FROM accounts WHERE login_id="+q(LOGIN)+";"
      " INSERT INTO accounts(login_id,verifier,verifier_hash,role,display_name,position,email,status,source_row,source_checksum,is_shadow_test)"
      " VALUES("+q(LOGIN)+",'seed-fixture',"+q(vhash)+",'SUPERADMIN','OWNER Beta test seed','TEST','','ACTIVE',-30100,'owner-beta-seed',1);"
      " INSERT INTO auth_sessions(login_id,session_id,device_id,issued_at) VALUES("+q(LOGIN)+","+q(auth_session)+","+q(device)+","+q(now)+");"
    )
    service_secret=hashlib.sha256((account_id+"|"+google_secret+"|pick-pack-1291-m2-service-token-v1").encode()).hexdigest()
    payload={"l":LOGIN,"r":"SUPERADMIN","v":vhash,"s":auth_session,"d":device,"c":"PDA"}
    enc=b64u(json.dumps(payload,separators=(",",":")).encode())
    token=enc+"."+b64u(hmac.new(service_secret.encode(),enc.encode(),hashlib.sha256).digest())

    schema=must(service_url+"/v1/import/schema?dataset=employees",token=token)
    positions=[str(x).strip() for x in ((schema.get("select_values") or {}).get("main_position") or []) if str(x).strip()]
    if not positions: raise RuntimeError("BETA_MAIN_POSITION_CATALOG_EMPTY")

    business_date=datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%Y-%m-%d")
    before=must(service_url+"/v1/bootstrap?business_date="+urllib.parse.quote(business_date)+"&client_source=WEB",token=token)
    existing_emps={str(x.get("mnv")):x for x in before.get("employees",[]) if str(x.get("mnv")) in MNV_LIST}
    foreign=[m for m,e in existing_emps.items() if MARKER not in str(e.get("note") or "")]
    if foreign:
        raise RuntimeError("MNV_RANGE_COLLIDES_WITH_NON_TEST_EMPLOYEES:"+",".join(sorted(foreign)[:30]))

    expected={}
    rows=[]
    for mnv in MNV_LIST:
        pos=positions[det_index("position",mnv,len(positions))]
        shift=SHIFTS[det_index("shift",mnv,len(SHIFTS))]
        work=WORK_CHOICES[det_index("work",mnv,len(WORK_CHOICES))]
        expected[mnv]={"main_position":pos,"shift":shift,"work_choice":work}
        rows.append({
          "mnv":mnv,
          "full_name":"TEST QR "+mnv,
          "phone":"",
          "main_position":pos,
          "supplier":"",
          "department":"",
          "site":"",
          "warehouse":"",
          "start_date":business_date,
          "note":MARKER+" | OWNER TEST"
        })

    existing_att={str(x.get("mnv")):x for x in before.get("attendance",[]) if str(x.get("mnv")) in MNV_LIST}
    ended=[m for m,s in existing_att.items() if str(s.get("state"))!="ACTIVE" or s.get("exit_at")]
    if ended: raise RuntimeError("TEST_RANGE_HAS_ENDED_SESSION:"+",".join(sorted(ended)[:30]))
    drift=[m for m,s in existing_att.items() if str(s.get("shift"))!=expected[m]["shift"] or str(s.get("work_choice"))!=expected[m]["work_choice"]]
    if drift: raise RuntimeError("EXISTING_TEST_SESSION_ASSIGNMENT_DRIFT:"+",".join(sorted(drift)[:30]))

    normalized=json.dumps(rows,ensure_ascii=False,separators=(",",":"))
    file_sha=hashlib.sha256(normalized.encode()).hexdigest()
    start=must(service_url+"/v1/import/batches","POST",token,{
      "dataset":"employees","template_version":schema["template_version"],
      "schema_checksum":schema["schema_checksum"],"file_sha256":file_sha
    })
    batch_id=str(start["import_batch_id"])
    chunk_sha=hashlib.sha256(normalized.encode()).hexdigest()
    must(service_url+"/v1/import/batches/"+urllib.parse.quote(batch_id)+"/chunks","POST",token,{
      "chunk_no":0,"chunk_checksum":chunk_sha,"rows":rows
    })
    preview=must(service_url+"/v1/import/batches/"+urllib.parse.quote(batch_id)+"/preview","POST",token)
    summary=preview.get("summary") or {}
    if int(summary.get("rejected") or 0)!=0 or int(summary.get("row_count") or 0)!=101:
        raise RuntimeError("EMPLOYEE_IMPORT_PREVIEW_INVALID:"+json.dumps(summary,ensure_ascii=False)[:500])
    committed=must(service_url+"/v1/import/batches/"+urllib.parse.quote(batch_id)+"/commit","POST",token,{})

    after_import=must(service_url+"/v1/bootstrap?business_date="+urllib.parse.quote(business_date)+"&client_source=WEB",token=token)
    emp_map={str(x.get("mnv")):x for x in after_import.get("employees",[]) if str(x.get("mnv")) in MNV_LIST}
    if len(emp_map)!=101: raise RuntimeError("EMPLOYEE_IMPORT_READBACK_COUNT:"+str(len(emp_map)))
    bad_emp=[m for m in MNV_LIST if str(emp_map[m].get("main_position") or "")!=expected[m]["main_position"] or MARKER not in str(emp_map[m].get("note") or "")]
    if bad_emp: raise RuntimeError("EMPLOYEE_IMPORT_READBACK_MISMATCH:"+",".join(bad_emp[:30]))

    att_now={str(x.get("mnv")):x for x in after_import.get("attendance",[]) if str(x.get("mnv")) in MNV_LIST}
    pending=[m for m in MNV_LIST if m not in att_now]
    events=[]
    for mnv in pending:
        ex=expected[mnv]
        events.append({
          "action":"enter",
          "event_id":"OWNER_BETA_TEST_ENTER_"+business_date.replace("-","")+"_"+mnv,
          "device_id":"OWNER_BETA_TEST_SEED",
          "business_date":business_date,
          "payload":{"mnv":mnv,"shift":ex["shift"],"work_choice":ex["work_choice"],"note":MARKER}
        })
    confirmed=duplicates=0
    for i in range(0,len(events),100):
        j=must(service_url+"/v1/legacy-mutations/batch","POST",token,{"events":events[i:i+100]},timeout=120)
        results=j.get("results") or []
        if len(results)!=len(events[i:i+100]): raise RuntimeError("ATTENDANCE_BATCH_RESULT_COUNT_MISMATCH")
        bad=[x for x in results if x.get("status") not in ("CONFIRMED","DUPLICATE")]
        if bad: raise RuntimeError("ATTENDANCE_BATCH_REJECTED:"+json.dumps(bad[:5],ensure_ascii=False)[:800])
        confirmed+=sum(1 for x in results if x.get("status")=="CONFIRMED")
        duplicates+=sum(1 for x in results if x.get("status")=="DUPLICATE")

    final=must(service_url+"/v1/bootstrap?business_date="+urllib.parse.quote(business_date)+"&client_source=WEB",token=token)
    final_att={str(x.get("mnv")):x for x in final.get("attendance",[]) if str(x.get("mnv")) in MNV_LIST}
    if len(final_att)!=101: raise RuntimeError("FINAL_ATTENDANCE_COUNT:"+str(len(final_att)))
    bad_active=[m for m,s in final_att.items() if s.get("state")!="ACTIVE" or s.get("exit_at") not in (None,"")]
    if bad_active: raise RuntimeError("FINAL_ENTER_ONLY_FAILED:"+",".join(sorted(bad_active)[:30]))
    bad_assignment=[m for m,s in final_att.items() if str(s.get("shift"))!=expected[m]["shift"] or str(s.get("work_choice"))!=expected[m]["work_choice"]]
    if bad_assignment: raise RuntimeError("FINAL_ASSIGNMENT_MISMATCH:"+",".join(sorted(bad_assignment)[:30]))

    dbcheck=wrangler_sql(
      "SELECT COUNT(*) total,"
      " SUM(CASE WHEN state='ACTIVE' THEN 1 ELSE 0 END) active,"
      " SUM(CASE WHEN exit_at IS NOT NULL THEN 1 ELSE 0 END) with_exit"
      " FROM attendance_sessions WHERE business_date="+q(business_date)+" AND CAST(mnv AS INTEGER) BETWEEN 30100 AND 30200;"
    )
    if len(dbcheck)!=1 or int(dbcheck[0].get("total") or 0)!=101 or int(dbcheck[0].get("active") or 0)!=101 or int(dbcheck[0].get("with_exit") or 0)!=0:
        raise RuntimeError("D1_ENTER_ONLY_READBACK_FAILED:"+json.dumps(dbcheck))

    shift_counts={s:0 for s in SHIFTS}
    work_counts={w:0 for w in WORK_CHOICES}
    position_counts={}
    for m in MNV_LIST:
        e=expected[m]
        shift_counts[e["shift"]]+=1
        work_counts[e["work_choice"]]+=1
        position_counts[e["main_position"]]=position_counts.get(e["main_position"],0)+1

    receipt("PASS",
      beta_service=service_url,
      business_date=business_date,
      authority={"epoch":epoch,"mode":"SERVICE_PRIMARY","scope":"PRODUCTION","service_generation":generation},
      employee_import={"batch_id":batch_id,"preview":summary,"changed":int(committed.get("changed") or 0),"readback_count":101},
      attendance={"new_confirmed":confirmed,"duplicates":duplicates,"active_count":101,"exit_count":0},
      distribution={"shift":shift_counts,"work_choice":work_counts,"main_position":position_counts},
      beta_readback="PASS",
      stable_unchanged_by_scope=True,
      idempotent_seed=True
    )
    cleanup_auth()
    LOGIN=""
    print(json.dumps({"status":"PASS","business_date":business_date,"employees":101,"active":101,"exit":0,"shift":shift_counts,"positions":len(position_counts),"stable_write_attempts":0},ensure_ascii=False))
except Exception as e:
    cleanup_auth()
    receipt("FAIL",error=str(e)[:1000],stable_unchanged_by_scope=True)
    print("BETA_OWNER_TEST_SEED_ERROR:"+str(e)[:1200],file=sys.stderr)
    sys.exit(1)
