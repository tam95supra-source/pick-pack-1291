#!/usr/bin/env python3
import json, os, pathlib, re, sys, time, urllib.error, urllib.request, subprocess

ROOT=pathlib.Path(__file__).resolve().parents[1]
API="https://script.googleapis.com/v1/projects"
OUT=pathlib.Path("/tmp/beta-gas-service-url-repair.json")
TEMP_MARK="__BETA_ENVIRONMENT_REPAIR_ONCE_V2__"
TARGET_FUNCS_PICK=["ppBoundEnvironmentBootstrap_","ppEnvironmentId_","ppServiceAudience_","ppSheetId_","ppEnvironmentFence_"]
TARGET_FUNCS_M2=["ppM2ServiceUrl_","ppM2ValidServiceUrl_","ppM2StateSnapshot_","ppM2Discovery_","ppM2ServiceFetch_","ppM2CompleteFailback_"]

def need(name):
    v=os.environ.get(name,"").strip()
    if not v: raise RuntimeError("MISSING_REQUIRED_SECRET:"+name)
    return v

def req(url,token,method="GET",body=None):
    data=None if body is None else json.dumps(body,separators=(",",":")).encode()
    headers={"Authorization":"Bearer "+token,"Accept":"application/json"}
    if data is not None: headers["Content-Type"]="application/json; charset=utf-8"
    r=urllib.request.Request(url,data=data,headers=headers,method=method)
    try:
        with urllib.request.urlopen(r,timeout=45) as x:
            raw=x.read().decode("utf-8","replace")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        raw=e.read().decode("utf-8","replace")
        raise RuntimeError("APPS_SCRIPT_API_"+method+"_HTTP_"+str(e.code)+":"+raw[:900]) from e

def curl_json(method,url,body=None,timeout=60):
    method=str(method).upper()
    cmd=["curl","-sS","-L","--connect-timeout","12","--max-time",str(timeout)]
    data=None
    if body is not None:
        cmd += ["-H","Content-Type: application/json","--data-binary","@-"]
        data=json.dumps(body,separators=(",",":"))
        if method!="POST":cmd += ["-X",method]
    elif method!="GET":
        cmd += ["-X",method]
    cmd += ["-w","\\n__STATUS__:%{http_code}",url]
    p=subprocess.run(cmd,input=data,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout+10)
    if p.returncode:return -1,{"transport_error":p.stderr[-300:]}
    marker="\n__STATUS__:"
    if marker not in p.stdout:return -1,{"transport_error":"STATUS_MISSING"}
    raw,code=p.stdout.rsplit(marker,1)
    try:j=json.loads(raw) if raw.strip() else {}
    except:j={"raw":raw[:500]}
    return int(code.strip()),j

def post(url,body):
    last=(-1,{"transport_error":"NOT_ATTEMPTED"})
    for i in range(3):
        last=curl_json("POST",url,body,60)
        if last[0]!=-1:return last
        time.sleep(2+i*3)
    return last

def get_json(url):
    last=(-1,{"transport_error":"NOT_ATTEMPTED"})
    for i in range(3):
        last=curl_json("GET",url,None,45)
        if last[0]!=-1:return last
        time.sleep(2+i*3)
    return last

def normalize_dep(v):
    v=(v or "").strip()
    return v.split("/s/",1)[1].split("/",1)[0] if "/s/" in v else v

def files(project):
    return [{k:f[k] for k in ("name","type","source") if k in f} for f in project.get("files") or []]

def server_source(project):
    return "\n".join(str(f.get("source") or "") for f in project.get("files") or [] if f.get("type")=="SERVER_JS")

def extract_function(src,name):
    m=re.search(r"function\s+"+re.escape(name)+r"\s*\(",src)
    if not m: raise RuntimeError("FUNCTION_NOT_FOUND:"+name)
    start=m.start();brace=src.find("{",m.end())
    if brace<0: raise RuntimeError("FUNCTION_BRACE_NOT_FOUND:"+name)
    depth=0;state="code";i=brace
    while i<len(src):
        c=src[i];n=src[i+1] if i+1<len(src) else ""
        if state=="code":
            if c=="'":state="sq"
            elif c=='"':state="dq"
            elif c=="\x60":state="tpl"
            elif c=="/" and n=="/":state="line";i+=1
            elif c=="/" and n=="*":state="block";i+=1
            elif c=="{":depth+=1
            elif c=="}":
                depth-=1
                if depth==0:return src[start:i+1]
        elif state in ("sq","dq","tpl"):
            end={"sq":"'","dq":'"',"tpl":"\x60"}[state]
            if c=="\\":i+=1
            elif c==end:state="code"
        elif state=="line":
            if c=="\n":state="code"
        elif state=="block" and c=="*" and n=="/":
            state="code";i+=1
        i+=1
    raise RuntimeError("FUNCTION_PARSE_FAILED:"+name)

def replace_function(dst,src,name):
    want=extract_function(src,name)
    try:old=extract_function(dst,name)
    except RuntimeError:return dst,None,want
    return dst.replace(old,want,1),old,want

def insert_before(src,anchor,block):
    i=src.find(anchor)
    if i<0: raise RuntimeError("INSERT_ANCHOR_NOT_FOUND:"+anchor)
    return src[:i]+block.rstrip()+"\n\n"+src[i:]

def ensure_do_post_fence(src):
    do_post=extract_function(src,"doPost")
    if "const environmentFence=ppEnvironmentFence_(body);" in do_post:return src
    pat=re.compile(r"(const\s+action\s*=\s*String\(body\.action\s*\|\|\s*['\"]['\"]\)\.trim\(\);)")
    m=pat.search(do_post)
    if not m: raise RuntimeError("DO_POST_ACTION_ANCHOR_MISSING")
    block="\n    const environmentFence=ppEnvironmentFence_(body);\n    if(environmentFence)return ppJson_(environmentFence);"
    patched=do_post[:m.end()]+block+do_post[m.end():]
    return src.replace(do_post,patched,1)

def add_temp_route(src):
    if TEMP_MARK in src: raise RuntimeError("TEMP_MARK_ALREADY_PRESENT")
    anchor="    if (action === 'service_discovery') return ppJson_(ppM2Discovery_(body));"
    if anchor not in src: raise RuntimeError("SERVICE_DISCOVERY_ROUTE_ANCHOR_MISSING")
    route="    if (action === '__beta_environment_repair_once') return ppJson_(ppBetaEnvironmentRepairOnce_(body)); // "+TEMP_MARK+"\n"
    src=src.replace(anchor,route+anchor,1)
    helper=r'''
// __BETA_ENVIRONMENT_REPAIR_ONCE_V2__
function ppBetaEnvironmentRepairOnce_(body){
  if(ppEnvironmentId_()!=='BETA'||ppServiceAudience_()!=='PICK_PACK_1291_BETA')return {ok:false,error:'BETA_ENVIRONMENT_REPAIR_WRONG_ENV'};
  const token=String((body||{}).google_access_token||''), expected=String((body||{}).expected_current||'').replace(/\/+$/,''),
    target=String((body||{}).target_service_url||'').replace(/\/+$/,'');
  if(!token||!expected||!/^https:\/\/[A-Za-z0-9._-]+$/.test(target))return {ok:false,error:'BETA_ENVIRONMENT_REPAIR_FIELDS_INVALID'};
  const id=ppSheetId_(),url='https://www.googleapis.com/drive/v3/files/'+encodeURIComponent(id)+'?fields=id,mimeType,owners(emailAddress)&supportsAllDrives=true';
  const rr=UrlFetchApp.fetch(url,{method:'get',muteHttpExceptions:true,headers:{Authorization:'Bearer '+token}});
  let jj={};try{jj=JSON.parse(rr.getContentText()||'{}');}catch(_){return {ok:false,error:'BETA_ENVIRONMENT_REPAIR_OWNER_JSON'};}
  const owner=(jj.owners||[]).some(function(x){return String(x.emailAddress||'').toLowerCase()==='tam95.supra@gmail.com';});
  if(rr.getResponseCode()<200||rr.getResponseCode()>=300||String(jj.id||'')!==id||!owner)return {ok:false,error:'BETA_ENVIRONMENT_REPAIR_OWNER_PROOF_FAILED'};
  const p=PropertiesService.getScriptProperties(),current=String(p.getProperty('PP_M2_SERVICE_URL')||'').replace(/\/+$/,'');
  if(current===target)return {ok:true,idempotent:true,environment_id:'BETA',service_audience:'PICK_PACK_1291_BETA',service_url:target};
  if(current!==expected)return {ok:false,error:'BETA_ENVIRONMENT_REPAIR_UNEXPECTED_CURRENT',current_service_url:current};
  p.setProperty('PP_M2_SERVICE_URL',target);
  const readback=String(p.getProperty('PP_M2_SERVICE_URL')||'').replace(/\/+$/,'');
  if(readback!==target)return {ok:false,error:'BETA_ENVIRONMENT_REPAIR_PROPERTY_READBACK_FAILED'};
  return {ok:true,idempotent:false,environment_id:'BETA',service_audience:'PICK_PACK_1291_BETA',service_url:readback};
}
'''
    return src.rstrip()+"\n\n"+helper.strip()+"\n"

def build_final(old_files,repo_pick,repo_m2):
    out=[];pick_done=False;m2_done=False
    helpers="\n\n".join(extract_function(repo_pick,n) for n in TARGET_FUNCS_PICK)
    for f in old_files:
        item=dict(f);src=str(item.get("source") or "")
        if item.get("type")=="SERVER_JS" and item.get("name")=="PICK_PACK_API":
            for n in TARGET_FUNCS_PICK:
                try: src,_,_=replace_function(src,repo_pick,n)
                except RuntimeError as e:
                    if str(e)!="FUNCTION_NOT_FOUND:"+n: raise
            missing=[n for n in TARGET_FUNCS_PICK if ("function "+n+"(") not in src]
            if missing:
                src=insert_before(src,"function doGet()",helpers)
            for n in TARGET_FUNCS_PICK:
                if ("function "+n+"(") not in src: raise RuntimeError("PICK_HELPER_PATCH_MISSING:"+n)
            src,_,_=replace_function(src,repo_pick,"doGet")
            src=ensure_do_post_fence(src);item["source"]=src;pick_done=True
        elif item.get("type")=="SERVER_JS" and item.get("name")=="SERVICE_MIGRATION_M2":
            for n in TARGET_FUNCS_M2:
                src,_,_=replace_function(src,repo_m2,n)
            item["source"]=src;m2_done=True
        out.append(item)
    if not pick_done or not m2_done: raise RuntimeError("LIVE_CANONICAL_FILE_MAPPING_MISSING")
    return out

def make_temp(final_files):
    out=[]
    for f in final_files:
        item=dict(f)
        if item.get("type")=="SERVER_JS" and item.get("name")=="PICK_PACK_API":
            item["source"]=add_temp_route(str(item.get("source") or ""))
        out.append(item)
    return out

def wait_dep(sid,dep,token,want):
    last=None
    for i in range(12):
        d=req(f"{API}/{sid}/deployments/{dep}",token)
        last=(d.get("deploymentConfig") or {}).get("versionNumber")
        if last==want:return d
        time.sleep(min(2+i*2,10))
    raise RuntimeError("DEPLOYMENT_VERSION_READBACK_MISMATCH:"+str(last))

def deploy_version(sid,dep,token,version,manifest,description):
    payload={"deploymentConfig":{"scriptId":sid,"versionNumber":version,"manifestFileName":manifest,"description":description}}
    req(f"{API}/{sid}/deployments/{dep}",token,"PUT",payload)
    return wait_dep(sid,dep,token,version)

def discovery(web):
    return post(web,{"action":"service_discovery","_app_channel":"BETA","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA"})

def mismatch(web):
    return post(web,{"action":"service_discovery","_app_channel":"STABLE","_environment_id":"STABLE","_service_audience":"PICK_PACK_1291_STABLE"})

def update_check(web):
    return post(web,{"action":"update_check","channel":"BETA","current_version":"0.0.0","_app_channel":"BETA","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA"})

def temp_action(web,token,expected,target):
    return post(web,{"action":"__beta_environment_repair_once","_app_channel":"BETA","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA",
                     "google_access_token":token,"expected_current":expected,"target_service_url":target})

def wait_temp_runtime(web,token,current,target,attempts=18):
    last=None
    for i in range(attempts):
        c,j=temp_action(web,token,current,current);last=(c,j)
        got=str(j.get("service_url") or j.get("current_service_url") or "").rstrip("/")
        if c==200 and j.get("environment_id")=="BETA" and j.get("service_audience")=="PICK_PACK_1291_BETA":
            if j.get("ok") is True and got==current:return current
            if j.get("error")=="BETA_ENVIRONMENT_REPAIR_UNEXPECTED_CURRENT" and got==target:return target
        time.sleep(min(2+i,8))
    c,j=last or (-1,{})
    got=str(j.get("service_url") or j.get("current_service_url") or "").rstrip("/")
    raise RuntimeError("TEMP_RUNTIME_NOT_READY:"+str(c)+":"+str(j.get("error") or j.get("transport_error") or "ASSERT")+":current="+got)

def wait_final_runtime(web,target,base_version,attempts=24):
    last={};consecutive=0
    for i in range(attempts):
        c2,after=discovery(web);cm,bad=mismatch(web);cu,ota=update_check(web);cg,getj=get_json(web)
        ok=(c2==200 and after.get("ok") is True and after.get("environment_id")=="BETA" and after.get("service_audience")=="PICK_PACK_1291_BETA"
            and str(after.get("service_url") or "").rstrip("/")==target
            and cm==200 and bad.get("ok") is False and bad.get("error") in ("ENVIRONMENT_MISMATCH","SERVICE_AUDIENCE_MISMATCH","CHANNEL_ENVIRONMENT_MISMATCH")
            and cu==200 and ota.get("ok") is True and ota.get("version_name")==base_version and ota.get("source")=="GITHUB_RELEASE"
            and cg==200 and getj.get("ok") is True and getj.get("environment_id")=="BETA" and getj.get("service_audience")=="PICK_PACK_1291_BETA")
        last={"discovery_http":c2,"discovery":after,"mismatch_http":cm,"mismatch":bad,"update_http":cu,"update":ota,"get_http":cg,"get":getj}
        if ok:
            consecutive+=1
            if consecutive>=2:return after,bad,ota,getj
            time.sleep(3);continue
        consecutive=0
        time.sleep(min(2+i,8))
    raise RuntimeError("FINAL_RUNTIME_NOT_READY:"+json.dumps({
        "discovery_http":last.get("discovery_http"),"discovery_error":(last.get("discovery") or {}).get("error"),
        "discovery_environment":(last.get("discovery") or {}).get("environment_id"),"discovery_audience":(last.get("discovery") or {}).get("service_audience"),
        "discovery_url":(last.get("discovery") or {}).get("service_url"),"mismatch_error":(last.get("mismatch") or {}).get("error"),
        "update_version":(last.get("update") or {}).get("version_name"),"get_environment":(last.get("get") or {}).get("environment_id")
    },separators=(",",":")))

def wait_legacy_runtime(web,current,attempts=18):
    last=None
    for i in range(attempts):
        c,j=discovery(web);last=(c,j)
        if c==200 and j.get("ok") is True and j.get("authority_mode")=="SERVICE_PRIMARY" and str(j.get("service_url") or "").rstrip("/")==current:
            return j
        time.sleep(min(2+i,8))
    c,j=last or (-1,{})
    raise RuntimeError("LEGACY_RUNTIME_NOT_RESTORED:"+str(c)+":"+str(j.get("error") or j.get("transport_error") or "ASSERT"))

def source_only_canonical_repair(sid,dep,token,request):
    release=json.loads((ROOT/"ops/beta-release-request.json").read_text())
    contracts=json.loads((ROOT/"config/environment_contracts.json").read_text())
    if request.get("stage")!="BETA_GAS_SERVICE_URL_REPAIR" or request.get("stable_publish")!="FORBIDDEN" or request.get("authority_change")!="NONE":
        raise RuntimeError("SOURCE_ONLY_REQUEST_FAIL_CLOSED")
    if release.get("candidate_locked") is not True or release.get("rebuild") is not False or release.get("resign") is not False or release.get("live") is not False:
        raise RuntimeError("SOURCE_ONLY_RELEASE_LOCK_NOT_INTACT")
    beta=contracts["environments"]["BETA"];stable=contracts["environments"]["STABLE"]
    target=str((beta.get("current_service") or {}).get("url") or "").rstrip("/")
    if beta.get("environment_id")!="BETA" or beta.get("service_audience")!="PICK_PACK_1291_BETA" or not target.endswith(".workers.dev"):
        raise RuntimeError("SOURCE_ONLY_BETA_CONTRACT_INVALID")
    if stable.get("stable_publish_allowed") is not False:
        raise RuntimeError("SOURCE_ONLY_STABLE_PUBLIC_GUARD_INVALID")

    depj=req(f"{API}/{sid}/deployments/{dep}",token);old_cfg=dict(depj.get("deploymentConfig") or {})
    old_version=old_cfg.get("versionNumber")
    expected=int(request.get("expected_deployment_version") or 0)
    if not isinstance(old_version,int) or old_version!=expected:
        raise RuntimeError("SOURCE_ONLY_DEPLOYMENT_VERSION_DRIFT:"+str(old_version))
    head=req(f"{API}/{sid}/content",token);deployed=req(f"{API}/{sid}/content?versionNumber={old_version}",token)
    old_files=files(head)
    if old_files!=files(deployed):
        raise RuntimeError("SOURCE_ONLY_HEAD_DEPLOYMENT_DRIFT")

    old_all=server_source(head)
    old_ota=extract_function(old_all,"ppUpdateCheck_")
    web=f"https://script.google.com/macros/s/{dep}/exec"
    c0,before=discovery(web)
    if c0!=200 or before.get("ok") is not True or before.get("authority_mode")!="SERVICE_PRIMARY":
        raise RuntimeError("SOURCE_ONLY_PRECHECK_FAILED:"+str(c0))
    legacy_url=str(before.get("service_url") or "").rstrip("/")
    if legacy_url==target and before.get("environment_id")=="BETA" and before.get("service_audience")=="PICK_PACK_1291_BETA":
        raise RuntimeError("SOURCE_ONLY_ALREADY_CANONICAL_USE_READBACK")
    if legacy_url not in (str(stable.get("target_web_origin") or "").rstrip("/"),target):
        raise RuntimeError("SOURCE_ONLY_UNEXPECTED_LEGACY_URL:"+legacy_url)

    repo_pick=(ROOT/"google-apps-script/PICK_PACK_API.gs").read_text(encoding="utf-8")
    repo_m2=(ROOT/"google-apps-script/SERVICE_MIGRATION_M2.gs").read_text(encoding="utf-8")
    final_files=build_final(old_files,repo_pick,repo_m2)
    final_all=server_source({"files":final_files})
    if extract_function(final_all,"ppUpdateCheck_")!=old_ota:
        raise RuntimeError("SOURCE_ONLY_OTA_FUNCTION_CHANGED")
    if "ppM2CanonicalServiceUrl_(" in extract_function(final_all,"ppM2ServiceUrl_"):
        raise RuntimeError("SOURCE_ONLY_LEGACY_CANONICALIZER_STILL_IN_RESOLVER")
    if "ppM2CanonicalServiceUrl_(" in extract_function(final_all,"ppM2StateSnapshot_"):
        raise RuntimeError("SOURCE_ONLY_LEGACY_CANONICALIZER_STILL_IN_SNAPSHOT")
    if final_all.count("ppM2CanonicalServiceUrl_(")>1:
        raise RuntimeError("SOURCE_ONLY_LEGACY_CANONICALIZER_ACTIVE_REFERENCE_REMAINS")
    if "environment_id:s.environmentId" not in extract_function(final_all,"ppM2Discovery_") or "service_audience:s.serviceAudience" not in extract_function(final_all,"ppM2Discovery_"):
        raise RuntimeError("SOURCE_ONLY_DISCOVERY_ENVIRONMENT_FIELDS_MISSING")
    if "x-pick-pack-environment" not in extract_function(final_all,"ppM2ServiceFetch_").lower() or "x-pick-pack-audience" not in extract_function(final_all,"ppM2ServiceFetch_").lower():
        raise RuntimeError("SOURCE_ONLY_SERVICE_HEADERS_MISSING")
    if "environment_id:ppEnvironmentId_()" not in extract_function(final_all,"doGet") or "service_audience:ppServiceAudience_()" not in extract_function(final_all,"doGet"):
        raise RuntimeError("SOURCE_ONLY_DOGET_ENVIRONMENT_FIELDS_MISSING")
    do_post=extract_function(final_all,"doPost")
    if "const environmentFence=ppEnvironmentFence_(body);" not in do_post:
        raise RuntimeError("SOURCE_ONLY_DOPOST_FENCE_MISSING")

    new_version=None
    try:
        req(f"{API}/{sid}/content",token,"PUT",{"files":final_files})
        new_version=int(req(f"{API}/{sid}/versions",token,"POST",{"description":"Beta GAS canonical resolver/environment source-only repair"})["versionNumber"])
        deploy_version(sid,dep,token,new_version,str(old_cfg.get("manifestFileName") or "appsscript"),"Beta GAS canonical resolver/environment source-only repair")
        after,bad,ota,getj=wait_final_runtime(web,target,release.get("base_version"))

        deployed_final=req(f"{API}/{sid}/content?versionNumber={new_version}",token)
        head_final=req(f"{API}/{sid}/content",token)
        if files(deployed_final)!=files(head_final):
            raise RuntimeError("SOURCE_ONLY_FINAL_HEAD_DEPLOYMENT_DRIFT")
        live_src=server_source(deployed_final)
        if TEMP_MARK in live_src:
            raise RuntimeError("SOURCE_ONLY_TEMP_MARK_LEAK")
        if extract_function(live_src,"ppUpdateCheck_")!=old_ota:
            raise RuntimeError("SOURCE_ONLY_DEPLOYED_OTA_CHANGED")
        if "ppM2CanonicalServiceUrl_(" in extract_function(live_src,"ppM2ServiceUrl_") or "ppM2CanonicalServiceUrl_(" in extract_function(live_src,"ppM2StateSnapshot_"):
            raise RuntimeError("SOURCE_ONLY_DEPLOYED_LEGACY_CANONICALIZER_ACTIVE")

        result={
            "status":"PASS","mode":"BETA_GAS_SOURCE_ONLY_CANONICAL_RESOLVER_REPAIR",
            "previous_deployment_version":old_version,"deployment_version":new_version,
            "service_url":target,"environment_id":"BETA","service_audience":"PICK_PACK_1291_BETA",
            "legacy_canonicalizer_active":False,"environment_negative_fence":"PASS","service_fetch_headers":"PASS",
            "ota_function_unchanged":True,"ota_manifest_version":ota.get("version_name"),
            "property_touched":False,"stable_touched":False,"stable_publish":"FORBIDDEN","authority_change":"NONE",
            "candidate_rebuilt":False,"candidate_resigned":False,"rollback_version":old_version,"rollback_ready":True
        }
        OUT.write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result))
    except Exception as original:
        errors=[]
        try:req(f"{API}/{sid}/content",token,"PUT",{"files":old_files})
        except Exception as e:errors.append("head:"+str(e))
        try:
            deploy_version(sid,dep,token,old_version,str(old_cfg.get("manifestFileName") or "appsscript"),str(old_cfg.get("description") or "Restore exact v206 Beta GAS baseline"))
            wait_legacy_runtime(web,legacy_url)
        except Exception as e:errors.append("deployment:"+str(e))
        if errors:
            raise RuntimeError("SOURCE_ONLY_ROLLBACK_FAILED:original="+str(original)[:700]+"|"+"|".join(errors))
        raise

def recover_temp_deployment_only(sid,dep,token,request):
    target=int(request.get("rollback_target_version") or 0)
    expected=int(request.get("expected_current_deployment_version") or 0)
    if target<=0 or expected<=0: raise RuntimeError("RECOVERY_VERSION_FIELDS_REQUIRED")
    d=req(f"{API}/{sid}/deployments/{dep}",token);cfg=dict(d.get("deploymentConfig") or {});current=cfg.get("versionNumber")
    if current==target:
        result={"status":"PASS","mode":"RECOVER_TEMP_DEPLOYMENT_ONLY","idempotent":True,"deployment_version":target,"stable_touched":False,"property_touched":False}
        OUT.write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result));return
    if current!=expected: raise RuntimeError("RECOVERY_CURRENT_VERSION_DRIFT:"+str(current))
    cur=req(f"{API}/{sid}/content?versionNumber={current}",token)
    old=req(f"{API}/{sid}/content?versionNumber={target}",token)
    head=req(f"{API}/{sid}/content",token)
    if TEMP_MARK not in server_source(cur): raise RuntimeError("RECOVERY_EXPECTED_TEMP_MARK_MISSING")
    if TEMP_MARK in server_source(old): raise RuntimeError("RECOVERY_TARGET_CONTAINS_TEMP_MARK")
    if files(head)!=files(old): raise RuntimeError("RECOVERY_HEAD_NOT_EQUAL_TARGET_VERSION")
    deploy_version(sid,dep,token,target,str(cfg.get("manifestFileName") or "appsscript"),"Recover exact pre-repair Beta GAS deployment")
    for i in range(4):
        time.sleep(3+i*2)
        check=req(f"{API}/{sid}/deployments/{dep}",token)
        if (check.get("deploymentConfig") or {}).get("versionNumber")!=target:
            if i==3: raise RuntimeError("RECOVERY_DEPLOYMENT_NOT_STABLE_AT_TARGET")
            continue
    result={"status":"PASS","mode":"RECOVER_TEMP_DEPLOYMENT_ONLY","idempotent":False,"previous_deployment_version":current,
            "deployment_version":target,"head_equal_target":True,"temp_marker_removed_from_deployment":True,"stable_touched":False,
            "property_touched":False,"candidate_rebuilt":False,"candidate_resigned":False}
    OUT.write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result))

def main():
    token=need("ACCESS_TOKEN");sid=need("GAS_SCRIPT_ID");dep=normalize_dep(need("GAS_DEPLOYMENT_ID"))
    request=json.loads((ROOT/"ops/beta-gas-service-url-repair-request.json").read_text())
    if request.get("mode")=="RECOVER_TEMP_DEPLOYMENT_ONLY":
        recover_temp_deployment_only(sid,dep,token,request)
        return
    if request.get("mode")=="BETA_GAS_SOURCE_ONLY_CANONICAL_RESOLVER_REPAIR":
        source_only_canonical_repair(sid,dep,token,request)
        return
    release=json.loads((ROOT/"ops/beta-release-request.json").read_text())
    contracts=json.loads((ROOT/"config/environment_contracts.json").read_text())
    if request.get("stage")!="BETA_GAS_SERVICE_URL_REPAIR" or request.get("stable_publish")!="FORBIDDEN" or request.get("authority_change")!="NONE":
        raise RuntimeError("REPAIR_REQUEST_FAIL_CLOSED")
    if release.get("candidate_locked") is not True or release.get("rebuild") is not False or release.get("resign") is not False or release.get("live") is not False:
        raise RuntimeError("BETA_RELEASE_LOCK_NOT_INTACT")
    beta=contracts["environments"]["BETA"];stable=contracts["environments"]["STABLE"]
    target=str((beta.get("current_service") or {}).get("url") or "").rstrip("/")
    old_expected=str(stable.get("target_web_origin") or "").rstrip("/")
    if beta.get("environment_id")!="BETA" or beta.get("service_audience")!="PICK_PACK_1291_BETA" or not target.endswith(".workers.dev"):
        raise RuntimeError("BETA_CONTRACT_INVALID")
    if stable.get("stable_publish_allowed") is not False: raise RuntimeError("STABLE_PUBLIC_GUARD_INVALID")

    depj=req(f"{API}/{sid}/deployments/{dep}",token);old_cfg=dict(depj.get("deploymentConfig") or {})
    old_version=old_cfg.get("versionNumber")
    if not isinstance(old_version,int): raise RuntimeError("CURRENT_DEPLOYMENT_VERSION_MISSING")
    expected_version=request.get("expected_deployment_version")
    if expected_version is not None and int(expected_version)!=old_version: raise RuntimeError("DEPLOYMENT_VERSION_DRIFT:"+str(old_version))
    head=req(f"{API}/{sid}/content",token);deployed=req(f"{API}/{sid}/content?versionNumber={old_version}",token)
    old_files=files(head);old_deployed=files(deployed)
    if [(f.get("name"),f.get("type"),f.get("source")) for f in old_files] != [(f.get("name"),f.get("type"),f.get("source")) for f in old_deployed]:
        raise RuntimeError("HEAD_DEPLOYMENT_SOURCE_DRIFT_BEFORE_REPAIR")

    old_all=server_source(head)
    old_ota=extract_function(old_all,"ppUpdateCheck_")
    web=f"https://script.google.com/macros/s/{dep}/exec"
    c0,before=discovery(web)
    if c0!=200 or before.get("ok") is not True or before.get("authority_mode")!="SERVICE_PRIMARY":
        raise RuntimeError("BETA_DISCOVERY_PRECHECK_FAILED:"+str(c0)+":"+str(before.get("transport_error") or before.get("error") or "ASSERT")[:500])
    current=str(before.get("service_url") or "").rstrip("/")
    if current not in (old_expected,target):
        raise RuntimeError("BETA_DISCOVERY_UNEXPECTED_CURRENT:"+json.dumps({"expected_legacy":old_expected,"target":target,"got":current},separators=(",",":")))

    repo_pick=(ROOT/"google-apps-script/PICK_PACK_API.gs").read_text(encoding="utf-8")
    repo_m2=(ROOT/"google-apps-script/SERVICE_MIGRATION_M2.gs").read_text(encoding="utf-8")
    final_files=build_final(old_files,repo_pick,repo_m2)
    final_all="\n".join(str(f.get("source") or "") for f in final_files if f.get("type")=="SERVER_JS")
    if extract_function(final_all,"ppUpdateCheck_")!=old_ota: raise RuntimeError("OTA_FUNCTION_CHANGED_BY_PATCH")
    for n in TARGET_FUNCS_PICK+TARGET_FUNCS_M2:
        if ("function "+n+"(") not in final_all: raise RuntimeError("FINAL_CONTRACT_FUNCTION_MISSING:"+n)
    if "x-pick-pack-environment" not in final_all.lower() or "x-pick-pack-audience" not in final_all.lower():
        raise RuntimeError("FINAL_SERVICE_FETCH_HEADERS_MISSING")
    final_do_post=extract_function(final_all,"doPost")
    if "const environmentFence=ppEnvironmentFence_(body);" not in final_do_post or "if(environmentFence)return ppJson_(environmentFence);" not in final_do_post:
        raise RuntimeError("DO_POST_ENVIRONMENT_FENCE_NOT_PATCHED")
    temp_files=make_temp(final_files)

    temp_version=None;final_version=None;property_changed=False
    try:
        req(f"{API}/{sid}/content",token,"PUT",{"files":temp_files})
        temp_version=int(req(f"{API}/{sid}/versions",token,"POST",{"description":"TEMP Beta GAS environment repair with rollback"})["versionNumber"])
        deploy_version(sid,dep,token,temp_version,str(old_cfg.get("manifestFileName") or "appsscript"),"TEMP Beta GAS environment repair")
        observed_property=wait_temp_runtime(web,token,current,target)
        if observed_property==target:
            r1={"ok":True,"idempotent":True,"service_url":target}
            property_changed=False
        else:
            c1,r1=temp_action(web,token,observed_property,target)
            if c1!=200 or r1.get("ok") is not True or str(r1.get("service_url") or "").rstrip("/")!=target:
                raise RuntimeError("BETA_SERVICE_URL_PROPERTY_REPAIR_FAILED:"+str(c1)+":"+str(r1.get("error") or r1.get("transport_error") or "ASSERT"))
            property_changed=True

        req(f"{API}/{sid}/content",token,"PUT",{"files":final_files})
        final_version=int(req(f"{API}/{sid}/versions",token,"POST",{"description":"Beta GAS environment/audience/service discovery canonical contract"})["versionNumber"])
        deploy_version(sid,dep,token,final_version,str(old_cfg.get("manifestFileName") or "appsscript"),"Beta GAS environment/audience/service discovery canonical contract")
        after,bad,ota,getj=wait_final_runtime(web,target,release.get("base_version"))

        deployed_final=req(f"{API}/{sid}/content?versionNumber={final_version}",token)
        head_final=req(f"{API}/{sid}/content",token)
        if files(deployed_final)!=files(head_final): raise RuntimeError("FINAL_HEAD_DEPLOYMENT_SOURCE_DRIFT")
        final_live=server_source(deployed_final)
        if TEMP_MARK in final_live: raise RuntimeError("TEMP_REPAIR_ROUTE_LEAK")
        if extract_function(final_live,"ppUpdateCheck_")!=old_ota: raise RuntimeError("DEPLOYED_OTA_FUNCTION_CHANGED")
        result={"status":"PASS","mode":"BETA_GAS_ENVIRONMENT_DISCOVERY_CANONICAL_REPAIR","previous_deployment_version":old_version,
                "temporary_version":temp_version,"deployment_version":final_version,"environment_id":"BETA","service_audience":"PICK_PACK_1291_BETA",
                "service_url":target,"legacy_service_url_removed":current!=target,"environment_negative_fence":"PASS","service_fetch_headers":"PASS",
                "ota_function_unchanged":True,"ota_manifest_version":ota.get("version_name"),"stable_touched":False,"stable_publish":"FORBIDDEN",
                "authority_change":"NONE","candidate_rebuilt":False,"candidate_resigned":False,"rollback_ready":True}
        OUT.write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result))
    except Exception as original:
        rollback_errors=[]
        if property_changed and temp_version is not None:
            try:
                deploy_version(sid,dep,token,temp_version,str(old_cfg.get("manifestFileName") or "appsscript"),"TEMP rollback Beta GAS service URL")
                rollback_observed=wait_temp_runtime(web,token,target,current)
                cr,rr=temp_action(web,token,rollback_observed,current)
                if cr!=200 or rr.get("ok") is not True or str(rr.get("service_url") or "").rstrip("/")!=current:
                    raise RuntimeError("PROPERTY_ROLLBACK_ASSERT:"+str(cr)+":"+str(rr.get("error") or rr.get("transport_error") or "ASSERT"))
            except Exception as e: rollback_errors.append("property:"+str(e))
        try:
            req(f"{API}/{sid}/content",token,"PUT",{"files":old_files})
        except Exception as e: rollback_errors.append("head:"+str(e))
        try:
            deploy_version(sid,dep,token,old_version,str(old_cfg.get("manifestFileName") or "appsscript"),str(old_cfg.get("description") or "Restore pre-repair deployment"))
            wait_legacy_runtime(web,current)
        except Exception as e: rollback_errors.append("deployment:"+str(e))
        if rollback_errors:
            raise RuntimeError("BETA_GAS_REPAIR_ROLLBACK_FAILED:original="+str(original)[:700]+"|"+"|".join(rollback_errors))
        raise

if __name__=="__main__":
    try:main()
    except Exception as e:
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps({"status":"FAIL","mode":"BETA_GAS_ENVIRONMENT_DISCOVERY_CANONICAL_REPAIR","error":str(e)[:1800],"stable_touched":False},indent=2)+"\n")
        print("BETA_GAS_ENVIRONMENT_REPAIR_ERROR:"+str(e)[:1800],file=sys.stderr);sys.exit(1)
