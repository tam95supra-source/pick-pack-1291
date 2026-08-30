#!/usr/bin/env python3
import json, os, sys, urllib.parse, urllib.request, urllib.error
from pathlib import Path

API="https://script.googleapis.com/v1/projects"
def req(url, token):
    r=urllib.request.Request(url,headers={"Authorization":f"Bearer {token}","Accept":"application/json"})
    try:
        with urllib.request.urlopen(r,timeout=45) as x:
            raw=x.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        detail=exc.read().decode("utf-8","replace")[:1200]
        raise RuntimeError(f"Apps Script inventory GET failed HTTP {exc.code}: {detail}") from exc

def paged(url, token, key):
    out=[]; page=""
    while True:
        u=url + (("&" if "?" in url else "?")+"pageSize=50")
        if page:u+="&pageToken="+urllib.parse.quote(page,safe="")
        j=req(u,token);out.extend(j.get(key) or [])
        page=str(j.get("nextPageToken") or "")
        if not page:return out

def main():
    out=Path(sys.argv[1])
    sid=os.environ.get("GAS_SCRIPT_ID","").strip()
    tok=os.environ.get("ACCESS_TOKEN","").strip()
    dep_raw=os.environ.get("GAS_DEPLOYMENT_ID","").strip()
    dep=dep_raw.split("/s/",1)[1].split("/",1)[0] if "/s/" in dep_raw else dep_raw
    if not sid or not tok or not dep: raise RuntimeError("inventory env missing")
    versions=paged(f"{API}/{sid}/versions",tok,"versions")
    deployments=paged(f"{API}/{sid}/deployments",tok,"deployments")
    refs={}
    for d in deployments:
        cfg=d.get("deploymentConfig") or {}
        n=cfg.get("versionNumber")
        if isinstance(n,int):
            refs.setdefault(n,[]).append(str(d.get("deploymentId") or ""))
    nums=sorted(v.get("versionNumber") for v in versions if isinstance(v.get("versionNumber"),int))
    unref=[n for n in nums if n not in refs]
    current=next((d for d in deployments if str(d.get("deploymentId") or "")==dep),None)
    current_v=((current or {}).get("deploymentConfig") or {}).get("versionNumber")
    safe=[n for n in unref if n!=current_v]
    data={
      "status":"PASS","read_only":True,
      "version_count":len(nums),"min_version":nums[0] if nums else None,"max_version":nums[-1] if nums else None,
      "deployment_count":len(deployments),"referenced_versions":sorted(refs),
      "current_deployment_version":current_v,
      "safe_unreferenced_oldest":safe[:10],
      "recommended_delete_version":safe[0] if safe else None
    }
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(data))
    if not safe: raise RuntimeError("NO_SAFE_UNREFERENCED_GAS_VERSION")

if __name__=="__main__":
    try: main()
    except Exception as e:
        print(f"GAS_VERSION_INVENTORY_ERROR: {e}",file=sys.stderr);sys.exit(1)
