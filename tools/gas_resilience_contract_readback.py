#!/usr/bin/env python3
import json, os, sys, urllib.request, urllib.error
from pathlib import Path

API="https://script.googleapis.com/v1/projects"
REQ_ACTIONS=["emergency_ledger_capture","emergency_ledger_finalize","emergency_ledger_query","lan_presence","lan_lease"]
REQ_FUNCS=["ppEmergencyLedgerCapture_","ppEmergencyLedgerFinalize_","ppEmergencyLedgerQuery_","ppLanPresence_","ppLanLease_"]

def req(url,token):
    request=urllib.request.Request(url,headers={"Authorization":f"Bearer {token}","Accept":"application/json"})
    try:
        with urllib.request.urlopen(request,timeout=45) as response:
            raw=response.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        detail=exc.read().decode("utf-8","replace")[:1000]
        raise RuntimeError(f"GET HTTP {exc.code}: {detail}") from exc

def normalize_deployment(value):
    value=(value or "").strip()
    if "/s/" in value:
        value=value.split("/s/",1)[1].split("/",1)[0]
    return value

def server_source(project):
    return "\n".join(str(f.get("source") or "") for f in project.get("files") or [] if f.get("type")=="SERVER_JS")

def flags(source):
    return {
        "actions":{x:(f"action === '{x}'" in source or f'action === "{x}"' in source) for x in REQ_ACTIONS},
        "functions":{x:(f"function {x}(" in source) for x in REQ_FUNCS},
    }

def all_ok(value):
    return all(value["actions"].values()) and all(value["functions"].values())

def main():
    out=Path(sys.argv[1])
    sid=os.environ.get("GAS_SCRIPT_ID","").strip()
    token=os.environ.get("ACCESS_TOKEN","").strip()
    dep=normalize_deployment(os.environ.get("GAS_DEPLOYMENT_ID",""))
    if not sid or not token or not dep:
        raise RuntimeError("GAS readback env missing")
    deployment=req(f"{API}/{sid}/deployments/{dep}",token)
    version=(deployment.get("deploymentConfig") or {}).get("versionNumber")
    if not isinstance(version,int):
        raise RuntimeError("deployment version missing")
    deployed=req(f"{API}/{sid}/content?versionNumber={version}",token)
    head=req(f"{API}/{sid}/content",token)
    repo=Path("google-apps-script/PICK_PACK_API.gs").read_text(encoding="utf-8")
    deployed_flags=flags(server_source(deployed))
    head_flags=flags(server_source(head))
    repo_flags=flags(repo)
    data={
        "status":"PASS" if all_ok(deployed_flags) else "FAIL",
        "read_only":True,
        "deployment_version":version,
        "deployment_contract":deployed_flags,
        "head_contract":head_flags,
        "repo_contract":repo_flags,
        "deployment_has_full_resilience_contract":all_ok(deployed_flags),
        "head_has_full_resilience_contract":all_ok(head_flags),
        "repo_has_full_resilience_contract":all_ok(repo_flags),
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(data))
    if not all_ok(deployed_flags):
        raise RuntimeError("DEPLOYED_RESILIENCE_CONTRACT_MISSING")

if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        print(f"GAS_RESILIENCE_READBACK_ERROR: {exc}",file=sys.stderr)
        sys.exit(1)
