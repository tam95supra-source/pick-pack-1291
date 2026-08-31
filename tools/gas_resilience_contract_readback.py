#!/usr/bin/env python3
import json, os, sys, urllib.request, urllib.error, hashlib
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

def environment_flags(source):
    return {
        "environment_helper": "function ppEnvironmentId_(" in source,
        "audience_helper": "function ppServiceAudience_(" in source,
        "environment_fence": "function ppEnvironmentFence_(" in source,
        "discovery_environment_id": "environment_id:s.environmentId" in source,
        "discovery_service_audience": "service_audience:s.serviceAudience" in source,
        "service_fetch_environment_header": "x-pick-pack-environment" in source.lower(),
        "service_fetch_audience_header": "x-pick-pack-audience" in source.lower(),
    }

def environment_ok(value):
    return all(value.values())

def file_features(project):
    out=[]
    for f in project.get("files") or []:
        if f.get("type")!="SERVER_JS": continue
        src=str(f.get("source") or "")
        out.append({
            "name":str(f.get("name") or ""),
            "sha256":hashlib.sha256(src.encode()).hexdigest(),
            "doPost":"function doPost(" in src,
            "update_check":"function ppUpdateCheck_(" in src,
            "environment_helper":"function ppEnvironmentId_(" in src,
            "environment_fence":"function ppEnvironmentFence_(" in src,
            "m2_snapshot":"function ppM2StateSnapshot_(" in src,
            "m2_discovery":"function ppM2Discovery_(" in src,
            "m2_service_fetch":"function ppM2ServiceFetch_(" in src,
            "resilience_marker":"RESILIENCE_V1 GOOGLE EMERGENCY LEDGER" in src,
        })
    return out

def repo_project():
    files=[]
    for path in sorted((Path("google-apps-script")).glob("*.gs")):
        files.append({"name":path.stem,"type":"SERVER_JS","source":path.read_text(encoding="utf-8")})
    return {"files":files}

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
    repo_obj=repo_project()
    repo=server_source(repo_obj)
    deployed_flags=flags(server_source(deployed))
    head_flags=flags(server_source(head))
    repo_flags=flags(repo)
    deployed_environment=environment_flags(server_source(deployed))
    head_environment=environment_flags(server_source(head))
    repo_environment=environment_flags(repo)
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
        "deployment_environment_contract":deployed_environment,
        "head_environment_contract":head_environment,
        "repo_environment_contract":repo_environment,
        "deployment_has_full_environment_contract":environment_ok(deployed_environment),
        "head_has_full_environment_contract":environment_ok(head_environment),
        "repo_has_full_environment_contract":environment_ok(repo_environment),
        "deployment_server_files":file_features(deployed),
        "head_server_files":file_features(head),
        "repo_server_files":file_features(repo_obj),
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
