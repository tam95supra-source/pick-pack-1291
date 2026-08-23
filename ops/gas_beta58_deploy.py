#!/usr/bin/env python3
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

GAS_URL = "https://script.google.com/macros/s/AKfycbzbEoGfbNg6s2HnP-gUpcBJ7mMIkVBtYuQKMndb9seDV2c55lQwSUO1GZ-LtQ2CxMCauA/exec"
OLD_SHA = "d7a27bc6ba3fcf7daecc04ec54ade1937c2c498f9f186c07c811831eee7739b8"
TARGET_VERSION = "0.4.2-beta.58"
TARGET_CODE = 64
TARGET_SHA = "1fb36447ea15a4f6a536814335acc4e693d85dc9b4de0b13e8fee5bdcffd475d"
TARGET_SIZE = 13027947
APK_NAME = "pick-pack-1291-public-beta-0.4.2-beta.58.apk"
TAG = "v0.4.2-beta.58-publicbeta"
EXPECTED_OLD_DEPLOYED_VERSION = 133


def need(name):
    v = os.environ.get(name, "").strip()
    if not v:
        raise RuntimeError(f"missing environment {name}")
    return v


def http_json(url, method="GET", token=None, payload=None, form=None, timeout=90):
    headers = {}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode()
    elif form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urllib.parse.urlencode(form).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def post_gas(body):
    req = urllib.request.Request(
        GAS_URL,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())


def find_function(src, marker="function ppUpdateCheck_(body) {"):
    start = src.find(marker)
    if start < 0:
        raise RuntimeError("ppUpdateCheck_ not found")
    i, depth, quote, esc = start, 0, None, False
    while i < len(src):
        c = src[i]
        if quote:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == quote:
                quote = None
        else:
            if c in "'\"`":
                quote = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0 and i > start:
                    return start, i + 1, src[start:i + 1]
        i += 1
    raise RuntimeError("ppUpdateCheck_ end not found")


def desired_function(published_at):
    return f'''function ppUpdateCheck_(body) {{
  const channel = ppFold_((body && (body.channel || body._app_channel)) || '') === 'STABLE'
    ? 'STABLE'
    : 'BETA';
  const current = String((body && (body.current_version || body._app_version)) || '').trim();

  // Stable remains intentionally locked/unpublished.
  if (channel === 'STABLE') {{
    return {{
      ok: true,
      source: 'GITHUB_RELEASE',
      channel: 'STABLE',
      available: false,
      reason: 'NO_RELEASE'
    }};
  }}

  const version = '0.4.2-beta.58';
  const available = ppOtaCompare_(version, current) > 0;

  const out = {{
    ok: true,
    source: 'GITHUB_RELEASE',
    channel: 'BETA',
    available: available,
    version_name: version,
    version_code: 64,
    size: 13027947,
    published_at: '{published_at}',
    notes: 'Beta58: sửa thống kê Nhật ký không còn về 0 sau khi upload; hiển thị đúng Google Drive khi thử tắt Cloudflare; đưa Đối soát vào/ra ca lên đầu Nghiệp vụ và chỉ hiện ca có nhân sự. OTA tiếp tục manual-only; Stable không thay đổi.',
    mandatory: false
  }};

  if (!available) return out;

  out.sha256 = '1fb36447ea15a4f6a536814335acc4e693d85dc9b4de0b13e8fee5bdcffd475d';
  out.apk_url = 'https://github.com/tam95supra-source/pick-pack-1291/releases/download/v0.4.2-beta.58-publicbeta/pick-pack-1291-public-beta-0.4.2-beta.58.apk';
  return out;
}}'''


def main():
    client_id = need("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = need("GOOGLE_OAUTH_CLIENT_SECRET")
    refresh = need("GOOGLE_OAUTH_REFRESH_TOKEN")
    script_id = need("GAS_SCRIPT_ID").replace("\r", "").replace("\n", "").replace("\t", "").replace(" ", "")
    raw_dep = need("GAS_DEPLOYMENT_ID").replace("\r", "").replace("\n", "").replace("\t", "").replace(" ", "")
    m = re.search(r"/s/([^/]+)", raw_dep)
    deployment_id = m.group(1) if m else raw_dep
    published_at = need("PUBLISHED_AT")

    tok = http_json(
        "https://oauth2.googleapis.com/token",
        method="POST",
        form={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh,
            "grant_type": "refresh_token",
        },
    ).get("access_token", "")
    if not tok:
        raise RuntimeError("OAuth access token missing")
    print("OAuth=PASS")

    dep_url = f"https://script.googleapis.com/v1/projects/{script_id}/deployments/{deployment_id}"
    dep = http_json(dep_url, token=tok)
    deployed_version = int(dep["deploymentConfig"]["versionNumber"])
    content_url = f"https://script.googleapis.com/v1/projects/{script_id}/content?versionNumber={deployed_version}"
    content = http_json(content_url, token=tok)
    files = content.get("files", [])
    idx = next((i for i, x in enumerate(files) if x.get("type") == "SERVER_JS" and x.get("name") == "PICK_PACK_API"), None)
    if idx is None:
        raise RuntimeError("PICK_PACK_API missing")
    src = str(files[idx].get("source", ""))
    old_sha = hashlib.sha256(src.encode()).hexdigest()
    start, end, old_fn = find_function(src)
    wanted = desired_function(published_at)

    already_target = (
        "const version = '0.4.2-beta.58';" in old_fn
        and "version_code: 64" in old_fn
        and TARGET_SHA in old_fn
        and TAG in old_fn
    )

    new_version = deployed_version
    new_sha = old_sha
    deploy_action = "ALREADY_TARGET"

    if already_target:
        print(f"GAS already at Beta58 OTA, deployed_version={deployed_version}")
    else:
        if deployed_version != EXPECTED_OLD_DEPLOYED_VERSION:
            raise RuntimeError(f"unexpected deployed version {deployed_version}, expected {EXPECTED_OLD_DEPLOYED_VERSION}")
        if old_sha != OLD_SHA:
            raise RuntimeError(f"unexpected PICK_PACK_API sha {old_sha}")
        for needle in ["const version = '0.4.2-beta.57';", "version_code: 63", "ae060aaf96d47388d699577e6b1cd003229b6d7f35feb6da12f5b339cb1d2fcc", "v0.4.2-beta.57-publicbeta"]:
            if needle not in old_fn:
                raise RuntimeError(f"old OTA contract mismatch: {needle}")
        patched = src[:start] + wanted + src[end:]
        if patched[:start] != src[:start] or patched[start + len(wanted):] != src[end:]:
            raise RuntimeError("patch scope escaped ppUpdateCheck_")
        if patched.count("function ppUpdateCheck_(body) {") != 1:
            raise RuntimeError("unexpected ppUpdateCheck_ count")
        files[idx]["source"] = patched
        new_sha = hashlib.sha256(patched.encode()).hexdigest()
        tmp = pathlib.Path("/tmp/PICK_PACK_API_beta58.js")
        tmp.write_text(patched, encoding="utf-8")
        subprocess.run(["node", "--check", str(tmp)], check=True)

        http_json(
            f"https://script.googleapis.com/v1/projects/{script_id}/content",
            method="PUT",
            token=tok,
            payload={"files": files},
        )
        ver = http_json(
            f"https://script.googleapis.com/v1/projects/{script_id}/versions",
            method="POST",
            token=tok,
            payload={"description": "Pick Pack 1291 Beta58 manual OTA metadata"},
        )
        new_version = int(ver["versionNumber"])
        if new_version <= deployed_version:
            raise RuntimeError("new GAS version did not advance")
        http_json(
            dep_url,
            method="PUT",
            token=tok,
            payload={
                "deploymentConfig": {
                    "scriptId": script_id,
                    "versionNumber": new_version,
                    "manifestFileName": "appsscript",
                    "description": "Pick Pack 1291 Beta58 manual OTA metadata",
                }
            },
        )
        deploy_action = "PATCHED_AND_DEPLOYED"
        print(f"GAS deploy={deployed_version}->{new_version}")

    # Exact deployed-source readback.
    dep2 = http_json(dep_url, token=tok)
    live_version = int(dep2["deploymentConfig"]["versionNumber"])
    if live_version != new_version:
        raise RuntimeError((live_version, new_version))
    after = http_json(
        f"https://script.googleapis.com/v1/projects/{script_id}/content?versionNumber={live_version}",
        token=tok,
    )
    live_src = next(str(x.get("source", "")) for x in after["files"] if x.get("type") == "SERVER_JS" and x.get("name") == "PICK_PACK_API")
    live_sha = hashlib.sha256(live_src.encode()).hexdigest()
    _, _, live_fn = find_function(live_src)
    for needle in ["const version = '0.4.2-beta.58';", "version_code: 64", TARGET_SHA, TAG]:
        if needle not in live_fn:
            raise RuntimeError(f"deployed OTA missing {needle}")

    # Live E2E with propagation retry.
    update = None
    for _ in range(30):
        try:
            j = post_gas({"action": "update_check", "channel": "BETA", "current_version": "0.4.2-beta.57"})
            if (
                j.get("ok") is True
                and j.get("available") is True
                and j.get("source") == "GITHUB_RELEASE"
                and j.get("version_name") == TARGET_VERSION
                and int(j.get("version_code", -1)) == TARGET_CODE
                and str(j.get("sha256", "")).lower() == TARGET_SHA
                and int(j.get("size", -1)) == TARGET_SIZE
                and str(j.get("apk_url", "")).endswith("/" + APK_NAME)
            ):
                update = j
                break
        except Exception as e:
            print("propagation retry:", type(e).__name__)
        time.sleep(4)
    if update is None:
        raise RuntimeError("Beta57->Beta58 live OTA gate failed")

    self_j = post_gas({"action": "update_check", "channel": "BETA", "current_version": TARGET_VERSION})
    stable_j = post_gas({"action": "update_check", "channel": "STABLE", "current_version": "0.1.0-stable"})
    if not (self_j.get("ok") is True and self_j.get("available") is False and self_j.get("version_name") == TARGET_VERSION):
        raise RuntimeError(("self", self_j))
    if not (stable_j.get("ok") is True and stable_j.get("available") is False and stable_j.get("channel") == "STABLE" and stable_j.get("reason") == "NO_RELEASE"):
        raise RuntimeError(("stable", stable_j))

    apk_url = update["apk_url"]
    with urllib.request.urlopen(apk_url, timeout=180) as r:
        apk = r.read()
    if len(apk) != TARGET_SIZE or hashlib.sha256(apk).hexdigest() != TARGET_SHA:
        raise RuntimeError("public OTA APK bytes mismatch")

    out = pathlib.Path("out")
    out.mkdir(exist_ok=True)
    receipt = {
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "old_deployed_version": deployed_version,
        "new_deployed_version": live_version,
        "deploy_action": deploy_action,
        "old_pick_pack_api_sha256": old_sha,
        "deployed_pick_pack_api_sha256": live_sha,
        "patch_scope": "ppUpdateCheck_ONLY",
        "target_version": TARGET_VERSION,
        "target_code": TARGET_CODE,
        "apk_sha256": TARGET_SHA,
        "apk_size": TARGET_SIZE,
        "ota_beta57_to_beta58": "PASS",
        "ota_beta58_self_no_update": "PASS",
        "stable_no_update": "PASS",
        "ota_mode": "MANUAL_ONLY",
        "stable": "UNTOUCHED",
        "verdict": "PASS",
    }
    (out / "GAS_BETA58_DEPLOY_OTA_RECEIPT.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        raise
