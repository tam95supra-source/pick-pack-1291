#!/usr/bin/env python3
import json, os, sys, urllib.request, urllib.error, hashlib, subprocess
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

def function_body(source,name):
    import re
    m=re.search(r"function\s+"+re.escape(name)+r"\s*\(",source)
    if not m:return ""
    brace=source.find("{",m.end())
    if brace<0:return ""
    depth=0;state="code";i=brace
    while i<len(source):
        c=source[i];n=source[i+1] if i+1<len(source) else ""
        if state=="code":
            if c=="'":state="sq"
            elif c=='"':state="dq"
            elif c=="\x60":state="tpl"
            elif c=="/" and n=="/":state="line";i+=1
            elif c=="/" and n=="*":state="block";i+=1
            elif c=="{":depth+=1
            elif c=="}":
                depth-=1
                if depth==0:return source[m.start():i+1]
        elif state in ("sq","dq","tpl"):
            end={"sq":"'","dq":'"',"tpl":"\x60"}[state]
            if c=="\\":i+=1
            elif c==end:state="code"
        elif state=="line":
            if c=="\n":state="code"
        elif state=="block" and c=="*" and n=="/":
            state="code";i+=1
        i+=1
    return ""

def function_body_selftest():
    fixture="""function ppM2ServiceUrl_(){\n  // comment with { brace }\n  const v='x';\n  return v;\n}\nfunction other(){return 1;}"""
    body=function_body(fixture,"ppM2ServiceUrl_")
    if not body.startswith("function ppM2ServiceUrl_(") or "return v;" not in body or "function other" in body:
        raise RuntimeError("FUNCTION_BODY_SELFTEST_FAILED")
    missing=function_body(fixture,"missing")
    if missing!="":
        raise RuntimeError("FUNCTION_BODY_NEGATIVE_SELFTEST_FAILED")

def m2_resolution_semantics(project):
    src=server_source(project)
    names=["ppM2ServiceUrl_","ppM2StateSnapshot_","ppM2Discovery_"]
    bodies={n:function_body(src,n) for n in names}
    joined="\n".join(bodies.values())
    return {
        "service_url_reads_property":"PP_M2_SERVICE_URL" in bodies["ppM2ServiceUrl_"],
        "snapshot_reads_all_properties":"getProperties()" in bodies["ppM2StateSnapshot_"],
        "snapshot_reads_service_url_property":"PP_M2_SERVICE_URL" in bodies["ppM2StateSnapshot_"],
        "snapshot_calls_service_url_helper":"ppM2ServiceUrl_(" in bodies["ppM2StateSnapshot_"],
        "discovery_calls_snapshot":"ppM2StateSnapshot_(" in bodies["ppM2Discovery_"],
        "discovery_calls_service_url_helper":"ppM2ServiceUrl_(" in bodies["ppM2Discovery_"],
        "uses_cache_service":"CacheService" in joined,
        "uses_properties_service":"PropertiesService" in joined,
        "contains_stable_root":"pickpack1291.cc.cd" in joined,
        "contains_workers_dev":"pickpack.1291.workers.dev" in joined,
        "service_url_body":" ".join(bodies["ppM2ServiceUrl_"].split()),
        "snapshot_body":" ".join(bodies["ppM2StateSnapshot_"].split()),
        "discovery_body":" ".join(bodies["ppM2Discovery_"].split()),
    }

def m2_service_url_diag(project):
    src=server_source(project)
    body=function_body(src,"ppM2ServiceUrl_")
    valid=function_body(src,"ppM2ValidServiceUrl_")
    return {
        "service_url_function_present":bool(body),
        "service_url_reads_property":"PP_M2_SERVICE_URL" in body,
        "service_url_contains_stable_root":"pickpack1291.cc.cd" in body,
        "service_url_contains_workers_dev":".workers.dev" in body,
        "service_url_function_sha256":hashlib.sha256(body.encode()).hexdigest() if body else "",
        "valid_url_accepts_workers_dev":"workers.dev" in valid or "workers\\.dev" in valid,
        "valid_url_function_sha256":hashlib.sha256(valid.encode()).hexdigest() if valid else "",
    }

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

def live_post(url,body):
    cmd=["curl","-sS","-L","--connect-timeout","12","--max-time","60","-H","Content-Type: application/json","--data-binary","@-","-w","\\n__STATUS__:%{http_code}",url]
    p=subprocess.run(cmd,input=json.dumps(body,separators=(",",":")),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=70)
    if p.returncode:return -1,{"transport_error":p.stderr[-300:]}
    marker="\n__STATUS__:"
    if marker not in p.stdout:return -1,{"transport_error":"STATUS_MISSING"}
    raw,code=p.stdout.rsplit(marker,1)
    try:j=json.loads(raw) if raw.strip() else {}
    except:j={"raw":raw[:500]}
    return int(code.strip()),j

def main():
    function_body_selftest()
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
    web=f"https://script.google.com/macros/s/{dep}/exec"
    live_code,live_discovery=live_post(web,{"action":"service_discovery","_app_channel":"BETA","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA"})
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
        "live_discovery":{"http":live_code,"ok":live_discovery.get("ok"),"error":live_discovery.get("error"),"environment_id":live_discovery.get("environment_id"),"service_audience":live_discovery.get("service_audience"),"service_url":live_discovery.get("service_url"),"authority_mode":live_discovery.get("authority_mode")},
        "deployment_m2_service_url_diag":m2_service_url_diag(deployed),
        "head_m2_service_url_diag":m2_service_url_diag(head),
        "repo_m2_service_url_diag":m2_service_url_diag(repo_obj),
        "deployment_m2_resolution_semantics":m2_resolution_semantics(deployed),
        "head_m2_resolution_semantics":m2_resolution_semantics(head),
        "repo_m2_resolution_semantics":m2_resolution_semantics(repo_obj),
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
