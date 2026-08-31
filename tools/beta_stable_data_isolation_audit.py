#!/usr/bin/env python3
import json,os,pathlib,sys,urllib.error,urllib.parse,urllib.request

CF="https://api.cloudflare.com/client/v4"
OUT=pathlib.Path("/tmp/beta-stable-data-isolation.json")

def need(n):
    v=os.environ.get(n,"").strip()
    if not v: raise RuntimeError("MISSING_REQUIRED:"+n)
    return v

def req(url,method="GET",token=None,body=None,timeout=40):
    data=None if body is None else json.dumps(body,separators=(",",":")).encode()
    h={"Accept":"application/json","User-Agent":"PickPack1291-Audit/1"}
    if token: h["Authorization"]="Bearer "+token
    if data is not None: h["Content-Type"]="application/json"
    r=urllib.request.Request(url,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(r,timeout=timeout) as x:
            raw=x.read().decode("utf-8","replace")
            return x.status,(json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw=e.read().decode("utf-8","replace")
        try:j=json.loads(raw)
        except:j={"raw":raw[:300]}
        return e.code,j

def cf(path,method="GET",body=None):
    code,j=req(f"{CF}/accounts/{need('CLOUDFLARE_ACCOUNT_ID')}{path}",method,need("CLOUDFLARE_API_TOKEN"),body)
    if code//100!=2 or j.get("success") is not True:
        raise RuntimeError("CF_API_FAILED:"+str(code))
    return j.get("result")

def bindmap(worker):
    s=cf("/workers/scripts/"+urllib.parse.quote(worker,safe="")+"/settings") or {}
    return {str(b.get("name")):b for b in (s.get("bindings") or [])}

def bid(m,k): return str((m.get(k) or {}).get("id") or "")
def btext(m,k): return str((m.get(k) or {}).get("text") or "")

def dq(db,sql):
    r=cf("/d1/database/"+urllib.parse.quote(db,safe="")+"/query","POST",{"sql":sql})
    if not isinstance(r,list) or not r or r[0].get("success") is False:
        raise RuntimeError("D1_QUERY_FAILED")
    return r[0].get("results") or []

def q(v): return "'"+str(v).replace("'","''")+"'"

def one(db,sql):
    rows=dq(db,sql)
    if len(rows)!=1: raise RuntimeError("EXPECTED_ONE_ROW")
    return rows[0]

def critical_counts(db):
    return {
      "accounts":int(one(db,"SELECT COUNT(*) n FROM accounts")["n"]),
      "attendance_sessions":int(one(db,"SELECT COUNT(*) n FROM attendance_sessions")["n"]),
      "outbox":int(one(db,"SELECT COUNT(*) n FROM sheet_replication_outbox")["n"])
    }

def read_canary(db,sheet,row):
    return dq(db,"SELECT row_checksum,row_json,import_run_id FROM source_rows WHERE sheet_name="+q(sheet)+" AND row_index="+str(row))

def expect_payload(db,sheet,row,checksum,payload,runid):
    rows=read_canary(db,sheet,row)
    return len(rows)==1 and rows[0].get("row_checksum")==checksum and rows[0].get("row_json")==payload and rows[0].get("import_run_id")==runid

def main():
    for n in ["CLOUDFLARE_API_TOKEN","CLOUDFLARE_ACCOUNT_ID"]:
        print("::add-mask::"+need(n))

    beta_worker="pickpack"
    stable_worker="pickpack1291-stable-private"
    bb,sb=bindmap(beta_worker),bindmap(stable_worker)
    beta_db,stable_db=bid(bb,"DB"),bid(sb,"DB")
    if not beta_db or not stable_db or beta_db==stable_db:
        raise RuntimeError("DB_ISOLATION_MISSING")
    if btext(sb,"ENVIRONMENT_ID")!="STABLE" or btext(sb,"SERVICE_AUDIENCE")!="PICK_PACK_1291_STABLE":
        raise RuntimeError("STABLE_BINDING_DRIFT")
    if btext(bb,"ENVIRONMENT_ID") not in ("","BETA"):
        raise RuntimeError("BETA_BINDING_DRIFT")

    runid=str(os.environ.get("GITHUB_RUN_ID","local"))
    numeric=sum(ord(c) for c in runid) if not runid.isdigit() else int(runid)
    row=800000000 + (numeric % 100000000)
    sheet="__AUDIT_BETA_STABLE_ISOLATION__"
    key=f"{sheet}:{row}"
    beta0=json.dumps({"environment":"BETA","phase":1,"key":key},separators=(",",":"))
    stable0=json.dumps({"environment":"STABLE","phase":1,"key":key},separators=(",",":"))
    beta1=json.dumps({"environment":"BETA","phase":2,"key":key},separators=(",",":"))
    stable1=json.dumps({"environment":"STABLE","phase":2,"key":key},separators=(",",":"))
    beta2=json.dumps({"environment":"BETA","phase":3,"key":key},separators=(",",":"))

    baseline_beta=critical_counts(beta_db)
    baseline_stable=critical_counts(stable_db)
    if read_canary(beta_db,sheet,row) or read_canary(stable_db,sheet,row):
        raise RuntimeError("CANARY_PREEXISTS")

    receipt={
      "status":"FAIL","environment":"BETA_STABLE","run_id":runid,
      "synthetic_only":True,"same_logical_id":True,"plaintext_secret":False,
      "beta_db_separate":True,"stable_db_separate":True
    }

    try:
        dq(beta_db,
          "INSERT INTO source_rows(sheet_name,row_index,row_checksum,row_json,import_run_id) VALUES("+
          q(sheet)+","+str(row)+","+q("BETA-1")+","+q(beta0)+","+q(runid)+")")
        if not expect_payload(beta_db,sheet,row,"BETA-1",beta0,runid): raise RuntimeError("BETA_CREATE_READBACK_FAIL")
        if read_canary(stable_db,sheet,row): raise RuntimeError("BETA_CREATE_LEAKED_TO_STABLE")

        dq(stable_db,
          "INSERT INTO source_rows(sheet_name,row_index,row_checksum,row_json,import_run_id) VALUES("+
          q(sheet)+","+str(row)+","+q("STABLE-1")+","+q(stable0)+","+q(runid)+")")
        if not expect_payload(stable_db,sheet,row,"STABLE-1",stable0,runid): raise RuntimeError("STABLE_CREATE_READBACK_FAIL")
        if not expect_payload(beta_db,sheet,row,"BETA-1",beta0,runid): raise RuntimeError("STABLE_CREATE_CHANGED_BETA")

        dq(beta_db,"UPDATE source_rows SET row_checksum="+q("BETA-2")+",row_json="+q(beta1)+" WHERE sheet_name="+q(sheet)+" AND row_index="+str(row))
        if not expect_payload(beta_db,sheet,row,"BETA-2",beta1,runid): raise RuntimeError("BETA_UPDATE_READBACK_FAIL")
        if not expect_payload(stable_db,sheet,row,"STABLE-1",stable0,runid): raise RuntimeError("BETA_UPDATE_CHANGED_STABLE")

        dq(stable_db,"UPDATE source_rows SET row_checksum="+q("STABLE-2")+",row_json="+q(stable1)+" WHERE sheet_name="+q(sheet)+" AND row_index="+str(row))
        if not expect_payload(stable_db,sheet,row,"STABLE-2",stable1,runid): raise RuntimeError("STABLE_UPDATE_READBACK_FAIL")
        if not expect_payload(beta_db,sheet,row,"BETA-2",beta1,runid): raise RuntimeError("STABLE_UPDATE_CHANGED_BETA")

        dq(beta_db,"DELETE FROM source_rows WHERE sheet_name="+q(sheet)+" AND row_index="+str(row))
        if read_canary(beta_db,sheet,row): raise RuntimeError("BETA_DELETE_READBACK_FAIL")
        if not expect_payload(stable_db,sheet,row,"STABLE-2",stable1,runid): raise RuntimeError("BETA_DELETE_CHANGED_STABLE")

        dq(beta_db,
          "INSERT INTO source_rows(sheet_name,row_index,row_checksum,row_json,import_run_id) VALUES("+
          q(sheet)+","+str(row)+","+q("BETA-3")+","+q(beta2)+","+q(runid)+")")
        dq(stable_db,"DELETE FROM source_rows WHERE sheet_name="+q(sheet)+" AND row_index="+str(row))
        if read_canary(stable_db,sheet,row): raise RuntimeError("STABLE_DELETE_READBACK_FAIL")
        if not expect_payload(beta_db,sheet,row,"BETA-3",beta2,runid): raise RuntimeError("STABLE_DELETE_CHANGED_BETA")

        receipt.update({
          "create_both_same_id":"PASS",
          "beta_update_stable_unchanged":"PASS",
          "stable_update_beta_unchanged":"PASS",
          "beta_delete_stable_survives":"PASS",
          "stable_delete_beta_survives":"PASS"
        })
    except Exception as e:
        receipt["error"]=str(e)[:1000]
    finally:
        for db in (beta_db,stable_db):
            try:dq(db,"DELETE FROM source_rows WHERE sheet_name="+q(sheet)+" AND row_index="+str(row))
            except Exception:pass

        beta_absent=not read_canary(beta_db,sheet,row)
        stable_absent=not read_canary(stable_db,sheet,row)
        counts_beta=critical_counts(beta_db)
        counts_stable=critical_counts(stable_db)
        receipt["cleanup_beta_absent"]=beta_absent
        receipt["cleanup_stable_absent"]=stable_absent
        receipt["critical_beta_counts_unchanged"]=counts_beta==baseline_beta
        receipt["critical_stable_counts_unchanged"]=counts_stable==baseline_stable
        if all([
          receipt.get("create_both_same_id")=="PASS",
          receipt.get("beta_update_stable_unchanged")=="PASS",
          receipt.get("stable_update_beta_unchanged")=="PASS",
          receipt.get("beta_delete_stable_survives")=="PASS",
          receipt.get("stable_delete_beta_survives")=="PASS",
          beta_absent,stable_absent,
          counts_beta==baseline_beta,counts_stable==baseline_stable
        ]):
            receipt["status"]="PASS"
        else:
            receipt["status"]="FAIL"
            receipt.setdefault("error","DATA_ISOLATION_OR_CLEANUP_READBACK_FAIL")
        OUT.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")

    if receipt["status"]!="PASS":
        raise RuntimeError(receipt.get("error","DATA_ISOLATION_FAILED"))
    print(json.dumps(receipt,separators=(",",":")))

if __name__=="__main__":
    try:main()
    except Exception as e:
        if not OUT.exists():
            OUT.write_text(json.dumps({"status":"FAIL","error":str(e)[:1000],"plaintext_secret":False},indent=2)+"\n")
        print("BETA_STABLE_DATA_ISOLATION_ERROR:"+str(e)[:1200],file=sys.stderr)
        sys.exit(1)
