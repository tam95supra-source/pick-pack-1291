#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API="https://script.googleapis.com/v1/projects"

def req(url, token, method="GET", body=None):
    data=None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers={"Authorization":f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"]="application/json; charset=utf-8"
    r=urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=45) as resp:
            raw=resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        detail=e.read().decode("utf-8", "replace")[:1200]
        raise RuntimeError(f"Apps Script API {method} failed HTTP {e.code}: {detail}") from e

def normalize_deployment(raw):
    value=(raw or "").strip()
    if "/s/" in value:
        value=value.split("/s/",1)[1].split("/",1)[0]
    if not value:
        raise RuntimeError("GAS_DEPLOYMENT_ID missing")
    return value

def replace_function(source, marker, replacement):
    start=source.find(marker)
    if start < 0:
        return None
    brace=source.find("{", start+len(marker))
    if brace < 0:
        raise RuntimeError("ppUpdateCheck_ opening brace missing")
    depth=0
    state="code"
    i=brace
    while i < len(source):
        ch=source[i]
        nxt=source[i+1] if i+1 < len(source) else ""
        if state=="code":
            if ch=="'" : state="sq"
            elif ch=='"' : state="dq"
            elif ch=="\x60" : state="tpl"
            elif ch=="/" and nxt=="/": state="line"; i+=1
            elif ch=="/" and nxt=="*": state="block"; i+=1
            elif ch=="{": depth+=1
            elif ch=="}":
                depth-=1
                if depth==0:
                    return source[:start]+replacement+source[i+1:]
        elif state=="sq":
            if ch=="\\": i+=1
            elif ch=="'": state="code"
        elif state=="dq":
            if ch=="\\": i+=1
            elif ch=='"': state="code"
        elif state=="tpl":
            if ch=="\\": i+=1
            elif ch=="\x60": state="code"
        elif state=="line":
            if ch=="\n": state="code"
        elif state=="block":
            if ch=="*" and nxt=="/": state="code"; i+=1
        i+=1
    raise RuntimeError("ppUpdateCheck_ closing brace missing")

def js(v):
    return json.dumps(v, ensure_ascii=False)

def contract_function(args):
    mandatory="true" if args.mandatory else "false"
    return f'''function ppUpdateCheck_(body) {{
  const raw=String((body&&((body.channel||body._app_channel)))||'BETA').trim().toUpperCase();
  const channel=raw==='STABLE'?'STABLE':'BETA';
  const current=String((body&&((body.current_version||body._app_version)))||'').trim();
  if(channel==='STABLE') return {{ok:true,source:'GOOGLE_DRIVE',channel:'STABLE',available:false,reason:'NO_APK'}};
  const parts=function(v){{return (String(v||'').match(/\\d+/g)||[]).slice(0,6).map(function(x){{return Number(x)||0;}});}};
  const newer=function(a,b){{const aa=parts(a),bb=parts(b),n=Math.max(aa.length,bb.length);for(let i=0;i<n;i++){{const av=aa[i]||0,bv=bb[i]||0;if(av!==bv)return av>bv;}}return false;}};
  const version={js(args.version)}, available=newer(version,current);
  const out={{ok:true,source:'GOOGLE_DRIVE',channel:'BETA',available:available,version_name:version,version_code:{args.version_code},size:{args.size},published_at:{js(args.published_at)},notes:{js(args.notes)},mandatory:{mandatory}}};
  if(!available)return out;
  out.sha256={js(args.sha256.lower())};
  out.apk_url={js(args.apk_url)};
  return out;
}}'''

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--version", required=True)
    p.add_argument("--version-code", required=True, type=int)
    p.add_argument("--sha256", required=True)
    p.add_argument("--size", required=True, type=int)
    p.add_argument("--apk-url", required=True)
    p.add_argument("--published-at", default="")
    p.add_argument("--notes", default="")
    p.add_argument("--notes-file")
    p.add_argument("--receipt", required=True)
    p.add_argument("--description", default="Pick Pack 1291 exact OTA contract")
    p.add_argument("--mandatory", action="store_true")
    args=p.parse_args()
    if args.notes_file:
        args.notes=Path(args.notes_file).read_text(encoding="utf-8").strip()
    if not args.version.startswith("0.4.2-beta."):
        raise RuntimeError("unexpected beta version")
    if len(args.sha256)!=64 or any(c not in "0123456789abcdefABCDEF" for c in args.sha256):
        raise RuntimeError("invalid sha256")
    if args.size<=0 or not args.apk_url.startswith("https://"):
        raise RuntimeError("invalid OTA bytes metadata")
    script_id=os.environ.get("GAS_SCRIPT_ID","").strip()
    token=os.environ.get("ACCESS_TOKEN","").strip()
    dep=normalize_deployment(os.environ.get("GAS_DEPLOYMENT_ID",""))
    if not script_id or not token:
        raise RuntimeError("GAS_SCRIPT_ID/ACCESS_TOKEN missing")
    project=req(f"{API}/{script_id}/content", token)
    files=project.get("files") or []
    marker="function ppUpdateCheck_(body)"
    replacement=contract_function(args)
    changed=[]
    before_hash=""
    after_hash=hashlib.sha256(replacement.encode("utf-8")).hexdigest()
    put_files=[]
    for f in files:
        item={k:f[k] for k in ("name","type","source") if k in f}
        source=item.get("source","")
        if item.get("type")=="SERVER_JS" and marker in source:
            updated=replace_function(source,marker,replacement)
            if updated is None:
                raise RuntimeError("OTA function replacement failed")
            before_hash=hashlib.sha256(source[source.find(marker):].encode("utf-8")).hexdigest()
            item["source"]=updated
            changed.append(item.get("name",""))
        put_files.append(item)
    if len(changed)!=1:
        raise RuntimeError(f"expected exactly one ppUpdateCheck_, found {len(changed)} in {changed}")
    req(f"{API}/{script_id}/content", token, "PUT", {"files":put_files})
    version=req(f"{API}/{script_id}/versions", token, "POST", {"description":args.description})
    version_number=int(version["versionNumber"])
    payload={"deploymentConfig":{"scriptId":script_id,"versionNumber":version_number,"manifestFileName":"appsscript","description":args.description}}
    req(f"{API}/{script_id}/deployments/{dep}", token, "PUT", payload)
    out={
      "status":"PASS","change_scope":"ppUpdateCheck_only","changed_file":changed[0],
      "deployment_version":version_number,"version_name":args.version,"version_code":args.version_code,
      "sha256":args.sha256.lower(),"size":args.size,"apk_url":args.apk_url,
      "replacement_sha256":after_hash,"previous_tail_sha256":before_hash
    }
    Path(args.receipt).parent.mkdir(parents=True,exist_ok=True)
    Path(args.receipt).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:out[k] for k in ("status","change_scope","deployment_version","version_name","sha256","size")},ensure_ascii=False))

if __name__=="__main__":
    try:
        main()
    except Exception as e:
        print(f"GAS_OTA_CONTRACT_ERROR: {e}", file=sys.stderr)
        sys.exit(1)
