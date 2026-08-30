#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import time
from pathlib import Path

API = "https://script.googleapis.com/v1/projects"


def req(url, token, method="GET", body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:1200]
        raise RuntimeError(f"Apps Script API {method} failed HTTP {exc.code}: {detail}") from exc


def normalize_deployment(raw):
    value = (raw or "").strip()
    if "/s/" in value:
        value = value.split("/s/", 1)[1].split("/", 1)[0]
    if not value:
        raise RuntimeError("GAS_DEPLOYMENT_ID missing")
    return value


def replace_function(source, marker, replacement):
    start = source.find(marker)
    if start < 0:
        return None
    brace = source.find("{", start + len(marker))
    if brace < 0:
        raise RuntimeError("ppUpdateCheck_ opening brace missing")

    depth = 0
    state = "code"
    i = brace
    while i < len(source):
        ch = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""
        if state == "code":
            if ch == "'":
                state = "sq"
            elif ch == '"':
                state = "dq"
            elif ch == "`":
                state = "tpl"
            elif ch == "/" and nxt == "/":
                state = "line"
                i += 1
            elif ch == "/" and nxt == "*":
                state = "block"
                i += 1
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return source[:start] + replacement + source[i + 1 :]
        elif state == "sq":
            if ch == "\\":
                i += 1
            elif ch == "'":
                state = "code"
        elif state == "dq":
            if ch == "\\":
                i += 1
            elif ch == '"':
                state = "code"
        elif state == "tpl":
            if ch == "\\":
                i += 1
            elif ch == "`":
                state = "code"
        elif state == "line":
            if ch == "\n":
                state = "code"
        elif state == "block":
            if ch == "*" and nxt == "/":
                state = "code"
                i += 1
        i += 1
    raise RuntimeError("ppUpdateCheck_ closing brace missing")


def js(value):
    return json.dumps(value, ensure_ascii=False)


def contract_function(args):
    mandatory = "true" if args.mandatory else "false"
    return f"""function ppUpdateCheck_(body) {{
  const raw=String((body&&((body.channel||body._app_channel)))||'BETA').trim().toUpperCase();
  const channel=raw==='STABLE'?'STABLE':'BETA';
  const current=String((body&&((body.current_version||body._app_version)))||'').trim();
  if(channel==='STABLE') return {{ok:true,source:'GOOGLE_DRIVE',channel:'STABLE',available:false,reason:'NO_APK'}};
  const parts=function(v){{return (String(v||'').match(/\\d+/g)||[]).slice(0,6).map(function(x){{return Number(x)||0;}});}};
  const newer=function(a,b){{const aa=parts(a),bb=parts(b),n=Math.max(aa.length,bb.length);for(let i=0;i<n;i++){{const av=aa[i]||0,bv=bb[i]||0;if(av!==bv)return av>bv;}}return false;}};
  const version={js(args.version)}, available=newer(version,current);
  const out={{ok:true,source:'GITHUB_RELEASE',channel:'BETA',available:available,version_name:version,version_code:{args.version_code},package:{js(args.package)},size:{args.size},published_at:{js(args.published_at)},notes:{js(args.notes)},mandatory:{mandatory}}};
  if(!available)return out;
  out.sha256={js(args.sha256.lower())};
  out.apk_url={js(args.apk_url)};
  return out;
}}"""



def paged_versions(script_id, token):
    out = []
    page = ""
    while True:
        url = f"{API}/{script_id}/versions?pageSize=50"
        if page:
            url += "&pageToken=" + urllib.parse.quote(page, safe="")
        data = req(url, token)
        out.extend(data.get("versions") or [])
        page = str(data.get("nextPageToken") or "")
        if not page:
            return out


def content_matches_function(files, marker, replacement):
    found = []
    for file in files or []:
        if file.get("type") != "SERVER_JS":
            continue
        source = file.get("source", "")
        if marker not in source:
            continue
        updated = replace_function(source, marker, replacement)
        if updated == source:
            found.append(file.get("name", ""))
    return len(found) == 1


def find_matching_version(script_id, token, versions, marker, replacement, limit=20, fetch_content=None):
    nums = sorted(
        (v.get("versionNumber") for v in versions if isinstance(v.get("versionNumber"), int)),
        reverse=True,
    )
    if fetch_content is None:
        fetch_content = lambda n: req(f"{API}/{script_id}/content?versionNumber={n}", token)
    for number in nums[:limit]:
        project = fetch_content(number)
        if content_matches_function(project.get("files") or [], marker, replacement):
            return number
    return None


def wait_deployment_version(
    script_id,
    deployment_id,
    token,
    expected,
    attempts=12,
    sleep_fn=time.sleep,
    fetch_fn=req,
):
    last = None
    for attempt in range(attempts):
        deployment = fetch_fn(f"{API}/{script_id}/deployments/{deployment_id}", token)
        value = ((deployment.get("deploymentConfig") or {}).get("versionNumber"))
        last = value
        if isinstance(value, int) and value == expected:
            return deployment
        if attempt + 1 < attempts:
            sleep_fn(min(2 + attempt * 2, 10))
    raise RuntimeError(
        f"deployment version readback mismatch after retry: expected {expected}, got {last}"
    )


def self_test():
    marker = "function ppUpdateCheck_(body)"
    target = "function ppUpdateCheck_(body) {\n  return {ok:true,target:'beta98'};\n}"
    base = "function ppUpdateCheck_(body) {\n  return {ok:true,target:'beta97'};\n}"
    versions = [{"versionNumber": 200}, {"versionNumber": 201}, {"versionNumber": 202}]
    contents = {
        200: {"files": [{"name": "api", "type": "SERVER_JS", "source": "x\n" + base + "\ny"}]},
        201: {"files": [{"name": "api", "type": "SERVER_JS", "source": "x\n" + target + "\ny"}]},
        202: {"files": [{"name": "api", "type": "SERVER_JS", "source": "x\n" + base + "\ny"}]},
    }
    matched = find_matching_version(
        "script",
        "token",
        versions,
        marker,
        target,
        fetch_content=lambda n: contents[n],
    )
    if matched != 201:
        raise RuntimeError(f"self-test exact version reuse failed: {matched}")

    reads = iter([200, 200, 201])
    calls = []

    def fake_fetch(url, token):
        value = next(reads)
        calls.append(value)
        return {"deploymentConfig": {"versionNumber": value}}

    deployment = wait_deployment_version(
        "script",
        "deployment",
        "token",
        201,
        attempts=3,
        sleep_fn=lambda _: None,
        fetch_fn=fake_fetch,
    )
    if deployment["deploymentConfig"]["versionNumber"] != 201 or calls != [200, 200, 201]:
        raise RuntimeError("self-test deployment eventual-consistency retry failed")

    print(json.dumps({
        "status": "PASS",
        "self_test": "GAS_DEPLOYMENT_EVENTUAL_CONSISTENCY_AND_VERSION_REUSE",
        "matched_version": matched,
        "readback_sequence": calls,
    }))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--version-code", required=True, type=int)
    parser.add_argument("--package", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--size", required=True, type=int)
    parser.add_argument("--apk-url", required=True)
    parser.add_argument("--published-at", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--notes-file")
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--description", default="Pick Pack 1291 exact OTA contract")
    parser.add_argument("--mandatory", action="store_true")
    args = parser.parse_args()

    if args.notes_file:
        args.notes = Path(args.notes_file).read_text(encoding="utf-8").strip()
    if not args.version.startswith("0.4.2-beta."):
        raise RuntimeError("unexpected beta version")
    if not args.package.startswith("vn.pickpack1291.app.beta."):
        raise RuntimeError("unexpected beta package")
    if len(args.sha256) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in args.sha256):
        raise RuntimeError("invalid sha256")
    if args.size <= 0 or not args.apk_url.startswith("https://github.com/"):
        raise RuntimeError("invalid GitHub Release OTA metadata")
    if "/releases/download/" not in args.apk_url:
        raise RuntimeError("apk_url is not a GitHub Release asset")

    script_id = os.environ.get("GAS_SCRIPT_ID", "").strip()
    token = os.environ.get("ACCESS_TOKEN", "").strip()
    deployment_id = normalize_deployment(os.environ.get("GAS_DEPLOYMENT_ID", ""))
    if not script_id or not token:
        raise RuntimeError("GAS_SCRIPT_ID/ACCESS_TOKEN missing")

    project = req(f"{API}/{script_id}/content", token)
    files = project.get("files") or []
    marker = "function ppUpdateCheck_(body)"
    replacement = contract_function(args)
    changed = []
    previous_function_sha256 = ""
    replacement_sha256 = hashlib.sha256(replacement.encode("utf-8")).hexdigest()
    put_files = []

    for file in files:
        item = {key: file[key] for key in ("name", "type", "source") if key in file}
        source = item.get("source", "")
        if item.get("type") == "SERVER_JS" and marker in source:
            updated = replace_function(source, marker, replacement)
            if updated is None:
                raise RuntimeError("OTA function replacement failed")
            old_function = replace_function(source, marker, "")
            if old_function is None:
                raise RuntimeError("OTA function extraction failed")
            previous_function_sha256 = hashlib.sha256(
                source[source.find(marker) :].encode("utf-8")
            ).hexdigest()
            item["source"] = updated
            changed.append(item.get("name", ""))
        put_files.append(item)

    if len(changed) != 1:
        raise RuntimeError(f"expected exactly one ppUpdateCheck_, found {len(changed)} in {changed}")

    versions = paged_versions(script_id, token)
    version_numbers = sorted(
        v.get("versionNumber") for v in versions if isinstance(v.get("versionNumber"), int)
    )
    matching_version = find_matching_version(
        script_id, token, versions, marker, replacement
    )
    reused_existing_version = matching_version is not None

    if matching_version is None and len(version_numbers) >= 200:
        raise RuntimeError(
            "GAS version limit reached and no exact matching target version is reusable"
        )

    req(f"{API}/{script_id}/content", token, "PUT", {"files": put_files})

    if matching_version is not None:
        version_number = int(matching_version)
    else:
        version = req(
            f"{API}/{script_id}/versions",
            token,
            "POST",
            {"description": args.description},
        )
        version_number = int(version["versionNumber"])

    payload = {
        "deploymentConfig": {
            "scriptId": script_id,
            "versionNumber": version_number,
            "manifestFileName": "appsscript",
            "description": args.description,
        }
    }
    current_deployment = req(f"{API}/{script_id}/deployments/{deployment_id}", token)
    current_version = int(current_deployment["deploymentConfig"]["versionNumber"])
    if current_version != version_number:
        req(f"{API}/{script_id}/deployments/{deployment_id}", token, "PUT", payload)
        deployment = wait_deployment_version(
            script_id, deployment_id, token, version_number
        )
    else:
        deployment = current_deployment
    deployed_version = int(deployment["deploymentConfig"]["versionNumber"])

    output = {
        "status": "PASS",
        "change_scope": "ppUpdateCheck_only",
        "changed_file": changed[0],
        "deployment_version": version_number,
        "deployment_readback_version": deployed_version,
        "reused_existing_version": reused_existing_version,
        "version_name": args.version,
        "version_code": args.version_code,
        "package": args.package,
        "sha256": args.sha256.lower(),
        "size": args.size,
        "apk_url": args.apk_url,
        "ota_transport": "GITHUB_RELEASE",
        "google_drive_apk": "FORBIDDEN",
        "replacement_sha256": replacement_sha256,
        "previous_tail_sha256": previous_function_sha256,
    }
    Path(args.receipt).parent.mkdir(parents=True, exist_ok=True)
    Path(args.receipt).write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                key: output[key]
                for key in (
                    "status",
                    "change_scope",
                    "deployment_version",
                    "version_name",
                    "version_code",
                    "package",
                    "sha256",
                    "size",
                    "ota_transport",
                )
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--self-test"]:
            self_test()
        else:
            main()
    except Exception as exc:
        print(f"GAS_OTA_CONTRACT_ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
