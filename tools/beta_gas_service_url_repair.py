#!/usr/bin/env python3
import json,os,pathlib,re,sys,time,urllib.error,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
API="https://script.googleapis.com/v1/projects"
OUT=pathlib.Path("/tmp/beta-gas-service-url-repair.json")
MARK="// __BETA_SERVICE_URL_REPAIR_ONCE_V1__"

def need(n):
    v=os.environ.get(n,"").strip()
    if not v: raise RuntimeError("MISSING_REQUIRED_SECRET:"+n)
    return v

def api(url,token,method="GET",body=None):
    data=None if body is None else json.dumps(body,separators=(",",":")).encode()
    h={"Authorization":"Bearer "+token,"Accept":"application/json"}
    if data is not None: h["Content-Type"]="application/json; charset=utf-8"
    q=urllib.request.Request(url,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(q,timeout=45) as r:
            raw=r.read().decode("utf-8","replace")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        raw=e.read().decode("utf-8","replace")
        raise RuntimeError("APPS_SCRIPT_API_"+method+"_HTTP_"+str(e.code)+":"+raw[:700]) from e

def dep_id(v):
    v=(v or "").strip()
    return v.split("/s/",1)[1].split("/",1)[0] if "/s/" in v else v

def post(url,body):
    q=urllib.request.Request(url,data=json.dumps(body,separators=(",",":")).encode(),headers={"Content-Type":"application/json"},method="POST")
    try:
        with urllib.request.urlopen(q,timeout=60) as r:
            raw=r.read().decode("utf-8","replace")
            return r.status,json.loads(raw or "{}")
    except urllib.error.HTTPError as e:
        raw=e.read().decode("utf-8","replace")
        try:j=json.loads(raw or "{}")
        except:j={"raw":raw[:700]}
        return e.code,j

def wait_dep(sid,dep,token,want):
    last=None
    for i in range(12):
        d=api(f"{API}/{sid}/deployments/{dep}",token)
        last=(d.get("deploymentConfig") or {}).get("versionNumber")
        if last==want:return
        time.sleep(min(2+i*2,10))
    raise RuntimeError("DEPLOYMENT_VERSION_READBACK_MISMATCH:"+str(last))

def files_of(project):
    return [{k:f[k] for k in ("name","type","source") if k in f} for f in project.get("files") or []]

def patched_files(files):
    out=[];changed=0
    route='    if (action === "__repair_beta_service_url_once") return ppJson_(ppRepairBetaServiceUrlOnce_(body));\n'
    helper=r'''
// __BETA_SERVICE_URL_REPAIR_ONCE_V1__
function ppRepairBetaServiceUrlOnce_(body){
  if(ppEnvironmentId_()!=='BETA')return {ok:false,error:'BETA_ONLY'};
  const token=String((body||{}).google_access_token||''),expected=String((body||{}).expected_current||'').replace(/\/+$/,''),
    target=String((body||{}).target_service_url||'').replace(/\/+$/,'');
  if(!token||!expected||!target||!ppM2ValidServiceUrl_(target))return {ok:false,error:'BETA_SERVICE_URL_REPAIR_FIELDS_INVALID'};
  const ss=ppSs_();
  if(!ppStableOwnerFile_(token,ss.getId(),'application/vnd.google-apps.spreadsheet'))return {ok:false,error:'BETA_SERVICE_URL_REPAIR_OWNER_PROOF_FAILED'};
  const p=PropertiesService.getScriptProperties(),current=String(p.getProperty('PP_M2_SERVICE_URL')||'').replace(/\/+$/,'');
  if(current===target)return {ok:true,idempotent:true,environment_id:'BETA',service_url:target};
  if(current!==expected)return {ok:false,error:'BETA_SERVICE_URL_REPAIR_UNEXPECTED_CURRENT',current_service_url:current};
  p.setProperty('PP_M2_SERVICE_URL',target);
  const readback=String(p.getProperty('PP_M2_SERVICE_URL')||'').replace(/\/+$/,'');
  if(readback!==target)return {ok:false,error:'BETA_SERVICE_URL_REPAIR_READBACK_FAILED'};
  return {ok:true,idempotent:false,environment_id:'BETA',service_url:readback};
}
'''
    for f in files:
        item=dict(f);src=str(item.get("source") or "")
        if item.get("type")=="SERVER_JS" and "function doPost(" in src:
            if MARK in src: raise RuntimeError("TEMP_REPAIR_MARK_ALREADY_PRESENT")
            a=re.search(r"(\n\s*const environmentFence=ppEnvironmentFence_\(body\);\s*\n\s*if\(environmentFence\)return ppJson_\(environmentFence\);\s*\n)",src)
            if not a: raise RuntimeError("TEMP_REPAIR_ROUTE_ANCHOR_MISSING")
            if "function ppStableOwnerFile_(" not in src: raise RuntimeError("OWNER_PROOF_HELPER_MISSING")
            src=src[:a.end()]+route+src[a.end():]
            item["source"]=src.rstrip()+"\n\n"+helper.strip()+"\n";changed+=1
        out.append(item)
    if changed!=1: raise RuntimeError("TEMP_REPAIR_EXPECTED_ONE_SERVER_FILE:"+str(changed))
    return out

def discovery(web):
    return post(web,{"action":"service_discovery","_app_channel":"BETA","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA"})

def main():
    token=need("ACCESS_TOKEN");sid=need("GAS_SCRIPT_ID");dep=dep_id(need("GAS_DEPLOYMENT_ID"))
    reqj=json.loads((ROOT/"ops/beta-gas-service-url-repair-request.json").read_text())
    rel=json.loads((ROOT/"ops/beta-release-request.json").read_text())
    cfg=json.loads((ROOT/"config/environment_contracts.json").read_text())
    if reqj.get("stage")!="BETA_GAS_SERVICE_URL_REPAIR" or reqj.get("stable_publish")!="FORBIDDEN" or reqj.get("authority_change")!="NONE":
        raise RuntimeError("REPAIR_REQUEST_FAIL_CLOSED")
    if rel.get("candidate_locked") is not True or rel.get("rebuild") is not False or rel.get("resign") is not False:
        raise RuntimeError("BETA_RELEASE_LOCK_NOT_INTACT")
    beta=cfg["environments"]["BETA"];stable=cfg["environments"]["STABLE"]
    target=str((beta.get("current_service") or {}).get("url") or "").rstrip("/")
    expected=str(stable.get("target_web_origin") or "").rstrip("/")
    if not target.startswith("https://") or ".workers.dev" not in target or not expected.startswith("https://") or target==expected:
        raise RuntimeError("SERVICE_URL_CONTRACT_INVALID")
    web=f"https://script.google.com/macros/s/{dep}/exec"
    code,before=discovery(web)
    if code!=200 or before.get("ok") is not True or before.get("environment_id")!="BETA" or before.get("service_audience")!="PICK_PACK_1291_BETA":
        raise RuntimeError("BETA_DISCOVERY_PRECHECK_FAILED:"+str(code))
    current=str(before.get("service_url") or "").rstrip("/")
    authority_before=before.get("authority");generation_before=before.get("service_generation")
    if current==target:
        rec={"status":"PASS","mode":"BETA_GAS_SERVICE_URL_REPAIR","idempotent":True,"before_service_url":current,"after_service_url":target,
             "authority_unchanged":True,"stable_touched":False,"source_restored":True,"deployment_restored":True,"candidate_rebuilt":False,"candidate_resigned":False}
        OUT.write_text(json.dumps(rec,indent=2)+"\n");print(json.dumps(rec));return
    if current!=expected:
        raise RuntimeError("BETA_DISCOVERY_UNEXPECTED_CURRENT:"+json.dumps({"expected_legacy":expected,"got":current},separators=(",",":")))

    depj=api(f"{API}/{sid}/deployments/{dep}",token);old_cfg=dict(depj.get("deploymentConfig") or {});old_version=old_cfg.get("versionNumber")
    if not isinstance(old_version,int): raise RuntimeError("CURRENT_DEPLOYMENT_VERSION_MISSING")
    old_files=files_of(api(f"{API}/{sid}/content",token));patched=patched_files(old_files)
    temp=None;temp_deployed=False;restore=[]
    try:
        api(f"{API}/{sid}/content",token,"PUT",{"files":patched})
        temp=int(api(f"{API}/{sid}/versions",token,"POST",{"description":"TEMP BETA service URL property repair; source restored immediately"})["versionNumber"])
        cfg2={"scriptId":sid,"versionNumber":temp,"manifestFileName":str(old_cfg.get("manifestFileName") or "appsscript"),"description":"TEMP BETA service URL property repair"}
        api(f"{API}/{sid}/deployments/{dep}",token,"PUT",{"deploymentConfig":cfg2});temp_deployed=True;wait_dep(sid,dep,token,temp)
        c,res=post(web,{"action":"__repair_beta_service_url_once","_app_channel":"BETA","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA",
                        "google_access_token":token,"expected_current":current,"target_service_url":target})
        if c!=200 or res.get("ok") is not True or str(res.get("service_url") or "").rstrip("/")!=target:
            raise RuntimeError("BETA_SERVICE_URL_REPAIR_CALL_FAILED:"+str(c)+":"+str(res.get("error") or "ASSERT"))
        c2,mid=discovery(web)
        if c2!=200 or str(mid.get("service_url") or "").rstrip("/")!=target: raise RuntimeError("TEMP_READBACK_FAILED")
    finally:
        if temp_deployed:
            try:
                back={"scriptId":sid,"versionNumber":old_version,"manifestFileName":str(old_cfg.get("manifestFileName") or "appsscript"),
                      "description":str(old_cfg.get("description") or "Restore canonical deployment")}
                api(f"{API}/{sid}/deployments/{dep}",token,"PUT",{"deploymentConfig":back});wait_dep(sid,dep,token,old_version)
            except Exception as e: restore.append("deployment:"+str(e))
        try: api(f"{API}/{sid}/content",token,"PUT",{"files":old_files})
        except Exception as e: restore.append("head:"+str(e))
    if restore: raise RuntimeError("REPAIR_RECOVERY_FAILED:"+"|".join(restore))
    c3,after=discovery(web)
    got=str(after.get("service_url") or "").rstrip("/")
    if c3!=200 or after.get("ok") is not True or after.get("environment_id")!="BETA" or after.get("service_audience")!="PICK_PACK_1291_BETA" or got!=target:
        raise RuntimeError("BETA_DISCOVERY_POST_RESTORE_FAILED:"+str(c3)+":"+got)
    if after.get("authority")!=authority_before or after.get("service_generation")!=generation_before:
        raise RuntimeError("BETA_AUTHORITY_CHANGED_DURING_SERVICE_URL_REPAIR")
    if MARK in "\n".join(str(f.get("source") or "") for f in files_of(api(f"{API}/{sid}/content",token))):
        raise RuntimeError("TEMP_REPAIR_SOURCE_NOT_REMOVED")
    final=api(f"{API}/{sid}/deployments/{dep}",token)
    if (final.get("deploymentConfig") or {}).get("versionNumber")!=old_version: raise RuntimeError("CANONICAL_DEPLOYMENT_NOT_RESTORED")
    rec={"status":"PASS","mode":"BETA_GAS_SERVICE_URL_REPAIR","idempotent":False,"before_service_url":current,"after_service_url":got,
         "authority_unchanged":True,"service_generation_unchanged":True,"stable_touched":False,"source_restored":True,"deployment_restored":True,
         "canonical_deployment_version":old_version,"temporary_version_created":temp,"temporary_version_unreferenced":True,
         "candidate_rebuilt":False,"candidate_resigned":False}
    OUT.write_text(json.dumps(rec,indent=2)+"\n");print(json.dumps(rec))

if __name__=="__main__":
    try: main()
    except Exception as e:
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps({"status":"FAIL","mode":"BETA_GAS_SERVICE_URL_REPAIR","error":str(e)[:1800],"stable_touched":False},indent=2)+"\n")
        print("BETA_GAS_SERVICE_URL_REPAIR_ERROR:"+str(e)[:1800],file=sys.stderr);sys.exit(1)
