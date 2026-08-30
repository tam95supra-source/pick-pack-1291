#!/usr/bin/env python3
import json,os,re,sys,time,urllib.request,urllib.error
from pathlib import Path

API="https://script.googleapis.com/v1/projects"
ACTIONS=["emergency_ledger_capture","emergency_ledger_finalize","emergency_ledger_query","lan_presence","lan_lease"]
FUNCS=["ppEmergencyLedgerCapture_","ppEmergencyLedgerFinalize_","ppEmergencyLedgerQuery_","ppLanPresence_","ppLanLease_"]
TAIL_MARK="// === RESILIENCE_V1 GOOGLE EMERGENCY LEDGER ==="
ROUTES="""    // RESILIENCE_V1: Google captures immutable emergency events only; it does not become the business-rule writer.
    if (action === 'emergency_ledger_capture') return ppJson_(ppEmergencyLedgerCapture_(auth, body));
    if (action === 'emergency_ledger_finalize') return ppJson_(ppEmergencyLedgerFinalize_(auth, body));
    if (action === 'emergency_ledger_query') return ppJson_(ppEmergencyLedgerQuery_(auth, body));
    if (action === 'lan_presence') return ppJson_(ppLanPresence_(auth, body));
    if (action === 'lan_lease') return ppJson_(ppLanLease_(auth, body));
"""

def req(url,token,method="GET",body=None):
    data=None if body is None else json.dumps(body).encode()
    headers={"Authorization":f"Bearer {token}","Accept":"application/json"}
    if data is not None: headers["Content-Type"]="application/json; charset=utf-8"
    request=urllib.request.Request(url,data=data,headers=headers,method=method)
    try:
        with urllib.request.urlopen(request,timeout=45) as response:
            raw=response.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{method} HTTP {exc.code}: "+exc.read().decode("utf-8","replace")[:1000]) from exc

def normalize_deployment(value):
    value=(value or "").strip()
    return value.split("/s/",1)[1].split("/",1)[0] if "/s/" in value else value

def server_source(project):
    return "\n".join(str(f.get("source") or "") for f in project.get("files") or [] if f.get("type")=="SERVER_JS")

def flags(source):
    return {"actions":{a:(f"action === '{a}'" in source or f'action === "{a}"' in source) for a in ACTIONS},
            "functions":{f:(f"function {f}(" in source) for f in FUNCS}}

def full(value):
    return all(value["actions"].values()) and all(value["functions"].values())

def extract_update_check(source):
    marker=re.search(r"function ppUpdateCheck_\(body\)\s*\{",source)
    if not marker:return ""
    start=source.find("{",marker.start());depth=0;state="code";i=start
    while i<len(source):
        ch=source[i];nxt=source[i+1] if i+1<len(source) else ""
        if state=="code":
            if ch=="'":state="sq"
            elif ch=='"':state="dq"
            elif ch=="`":state="tpl"
            elif ch=="/" and nxt=="/":state="line";i+=1
            elif ch=="/" and nxt=="*":state="block";i+=1
            elif ch=="{":depth+=1
            elif ch=="}":
                depth-=1
                if depth==0:return source[marker.start():i+1]
        elif state in ("sq","dq","tpl"):
            end={"sq":"'","dq":'"',"tpl":"`"}[state]
            if ch=="\\":i+=1
            elif ch==end:state="code"
        elif state=="line":
            if ch=="\n":state="code"
        elif state=="block" and ch=="*" and nxt=="/":state="code";i+=1
        i+=1
    raise RuntimeError("ppUpdateCheck parse failed")

def patch_one(live,repo):
    live_flags=flags(live);repo_flags=flags(repo)
    if full(live_flags): return live,False
    if any(live_flags["actions"].values()) or any(live_flags["functions"].values()):
        raise RuntimeError("partial live resilience contract; refusing automatic patch")
    if not full(repo_flags): raise RuntimeError("repo resilience contract incomplete")
    tail_at=repo.find(TAIL_MARK)
    if tail_at<0: raise RuntimeError("repo resilience tail missing")
    tail=repo[tail_at:].strip()+"\n"
    anchor=re.compile(r"(\n\s*const auth = ppAuthenticate_\(body\);\s*\n\s*if \(!auth\) return ppJson_\(\{ok:false,error:['\"]UNAUTHORIZED['\"]\}, 401\);\s*\n)")
    match=anchor.search(live)
    if not match: raise RuntimeError("auth insertion anchor missing")
    patched=live[:match.end()]+"\n"+ROUTES+live[match.end():]
    if TAIL_MARK in patched: raise RuntimeError("tail marker unexpectedly already present")
    patched=patched.rstrip()+"\n\n"+tail
    if not full(flags(patched)): raise RuntimeError("patched contract incomplete")
    if extract_update_check(live)!=extract_update_check(patched): raise RuntimeError("ppUpdateCheck changed")
    return patched,True

def main():
    out=Path(sys.argv[1]);sid=os.environ.get("GAS_SCRIPT_ID","").strip();token=os.environ.get("ACCESS_TOKEN","").strip();dep=normalize_deployment(os.environ.get("GAS_DEPLOYMENT_ID",""))
    if not sid or not token or not dep: raise RuntimeError("GAS patch env missing")
    deployment=req(f"{API}/{sid}/deployments/{dep}",token);old_version=(deployment.get("deploymentConfig") or {}).get("versionNumber")
    if not isinstance(old_version,int): raise RuntimeError("old deployment version missing")
    head=req(f"{API}/{sid}/content",token)
    repo=Path("google-apps-script/PICK_PACK_API.gs").read_text(encoding="utf-8")
    before=flags(server_source(head))
    old_files=[{k:f[k] for k in ("name","type","source") if k in f} for f in head.get("files") or []]
    files=[];changed=[];before_ota="";after_ota=""
    for file in old_files:
        item=dict(file)
        if item.get("type")=="SERVER_JS" and "function doPost(" in item.get("source",""):
            before_ota=extract_update_check(item["source"])
            item["source"],did=patch_one(item["source"],repo)
            after_ota=extract_update_check(item["source"])
            if did:changed.append(item.get("name",""))
        files.append(item)
    if len(changed)!=1: raise RuntimeError(f"expected one changed server file, got {changed}")
    if not before_ota or before_ota!=after_ota: raise RuntimeError("OTA function not preserved")
    req(f"{API}/{sid}/content",token,"PUT",{"files":files})
    version=req(f"{API}/{sid}/versions",token,"POST",{"description":"Pick Pack 1291 add missing RESILIENCE_V1 GAS contract without changing OTA/authority"})
    new_version=int(version["versionNumber"])
    payload={"deploymentConfig":{"scriptId":sid,"versionNumber":new_version,"manifestFileName":"appsscript","description":"Pick Pack 1291 RESILIENCE_V1 contract sync"}}
    deployed=False
    try:
        req(f"{API}/{sid}/deployments/{dep}",token,"PUT",payload);deployed=True
        for attempt in range(12):
            current=req(f"{API}/{sid}/deployments/{dep}",token)
            if (current.get("deploymentConfig") or {}).get("versionNumber")==new_version:break
            if attempt==11: raise RuntimeError("deployment readback version mismatch")
            time.sleep(min(2+attempt*2,10))
        deployed_content=req(f"{API}/{sid}/content?versionNumber={new_version}",token)
        after=flags(server_source(deployed_content))
        if not full(after): raise RuntimeError("deployed contract incomplete after patch")
        if extract_update_check(server_source(deployed_content))!=before_ota: raise RuntimeError("deployed OTA function changed")
        data={"status":"PASS","production_write":True,"change_scope":"RESILIENCE_V1_GAS_ROUTES_AND_FUNCTIONS_ONLY",
              "previous_deployment_version":old_version,"deployment_version":new_version,"changed_file":changed[0],
              "before_contract":before,"after_contract":after,"ota_function_unchanged":True,"authority_change":"NONE"}
        out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8");print(json.dumps(data))
    except Exception:
        if deployed:
            try:req(f"{API}/{sid}/deployments/{dep}",token,"PUT",{"deploymentConfig":{"scriptId":sid,"versionNumber":old_version,"manifestFileName":"appsscript","description":"Rollback after failed RESILIENCE_V1 patch"}})
            except Exception:pass
        try:req(f"{API}/{sid}/content",token,"PUT",{"files":old_files})
        except Exception:pass
        raise

if __name__=="__main__":
    try:main()
    except Exception as exc:
        print(f"GAS_RESILIENCE_PATCH_ERROR: {exc}",file=sys.stderr);sys.exit(1)
