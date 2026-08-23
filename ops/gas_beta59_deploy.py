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
OLD_SHA = "5d54b0f43e35a2e67e3485f565b249d353c62d2f07c2add1fb63ad2875cc97bc"
TARGET_VERSION = "0.4.2-beta.59"
TARGET_CODE = 65
TARGET_SHA = "55f6e3db521ee39dc5e58130a3444fee6ac1e936b38556f0ac281ea9e4212567"
TARGET_SIZE = 13044331
APK_NAME = "pick-pack-1291-public-beta-0.4.2-beta.59.apk"
TAG = "v0.4.2-beta.59-publicbeta"
EXPECTED_OLD_DEPLOYED_VERSION = 134


def need(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"missing environment {name}")
    return value


def http_json(url, method="GET", token=None, payload=None, form=None, timeout=90):
    headers = {}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    elif form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def post_gas(body):
    req = urllib.request.Request(
        GAS_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


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

  const version = '0.4.2-beta.59';
  const available = ppOtaCompare_(version, current) > 0;

  const out = {{
    ok: true,
    source: 'GITHUB_RELEASE',
    channel: 'BETA',
    available: available,
    version_name: version,
    version_code: 65,
    size: 13044331,
    published_at: '{published_at}',
    notes: 'Beta59: hoàn thiện Quét QR nhân sự; tách Thêm/Sửa/Xóa/Ra ca; hiển thị PDA và User đã sử dụng trong ca; đối soát Vào/Ra theo timestamp thực; lịch sử/audit chi tiết. OTA tiếp tục manual-only; Stable không thay đổi.',
    mandatory: false
  }};

  if (!available) return out;

  out.sha256 = '55f6e3db521ee39dc5e58130a3444fee6ac1e936b38556f0ac281ea9e4212567';
  out.apk_url = 'https://github.com/tam95supra-source/pick-pack-1291/releases/download/v0.4.2-beta.59-publicbeta/pick-pack-1291-public-beta-0.4.2-beta.59.apk';
  return out;
}}'''


def main():
    client_id = need("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = need("GOOGLE_OAUTH_CLIENT_SECRET")
    refresh = need("GOOGLE_OAUTH_REFRESH_TOKEN")
    script_id = need("GAS_SCRIPT_ID").replace("\r", "").replace("\n", "").replace("\t", "").replace(" ", "")
    raw_dep = need("GAS_DEPLOYMENT_ID").replace("\r", "").replace("\n", "").replace("\t", "").replace(" ", "")
    match = re.search(r"/s/([^/]+)", raw_dep)
    deployment_id = match.group(1) if match else raw_dep
    published_at = need("PUBLISHED_AT")

    token = http_json(
        "https://oauth2.googleapis.com/token",
        method="POST",
        form={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh,
            "grant_type": "refresh_token",
        },
    ).get("access_token", "")
    if not token:
        raise RuntimeError("OAuth access token missing")
    print("OAuth=PASS")

    dep_url = f"https://script.googleapis.com/v1/projects/{script_id}/deployments/{deployment_id}"
    dep = http_json(dep_url, token=token)
    deployed_version = int(dep["deploymentConfig"]["versionNumber"])
    content = http_json(
        f"https://script.googleapis.com/v1/projects/{script_id}/content?versionNumber={deployed_version}",
        token=token,
    )
    files = content.get("files", [])
    idx = next((i for i, item in enumerate(files) if item.get("type") == "SERVER_JS" and item.get("name") == "PICK_PACK_API"), None)
    if idx is None:
        raise RuntimeError("PICK_PACK_API missing")

    src = str(files[idx].get("source", ""))
    old_sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
    start, end, old_fn = find_function(src)
    wanted = desired_function(published_at)

    already_target = (
        "const version = '0.4.2-beta.59';" in old_fn
        and "version_code: 65" in old_fn
        and TARGET_SHA in old_fn
        and TAG in old_fn
    )

    new_version = deployed_version
    new_sha = old_sha
    deploy_action = "ALREADY_TARGET"

    if already_target:
        print(f"GAS already at Beta59 OTA, deployed_version={deployed_version}")
    else:
        if deployed_version != EXPECTED_OLD_DEPLOYED_VERSION:
            raise RuntimeError(f"unexpected deployed version {deployed_version}, expected {EXPECTED_OLD_DEPLOYED_VERSION}")
        if old_sha != OLD_SHA:
            raise RuntimeError(f"unexpected PICK_PACK_API sha {old_sha}")
        for needle in [
            "const version = '0.4.2-beta.58';",
            "version_code: 64",
            "1fb36447ea15a4f6a536814335acc4e693d85dc9b4de0b13e8fee5bdcffd475d",
            "v0.4.2-beta.58-publicbeta",
        ]:
            if needle not in old_fn:
                raise RuntimeError(f"old OTA contract mismatch: {needle}")

        patched = src[:start] + wanted + src[end:]
        if patched[:start] != src[:start] or patched[start + len(wanted):] != src[end:]:
            raise RuntimeError("patch scope escaped ppUpdateCheck_")
        if patched.count("function ppUpdateCheck_(body) {") != 1:
            raise RuntimeError("unexpected ppUpdateCheck_ count")

        files[idx]["source"] = patched
        new_sha = hashlib.sha256(patched.encode("utf-8")).hexdigest()
        tmp = pathlib.Path("/tmp/PICK_PACK_API_beta59.js")
        tmp.write_text(patched, encoding="utf-8")
        subprocess.run(["node", "--check", str(tmp)], check=True)

        http_json(
            f"https://script.googleapis.com/v1/projects/{script_id}/content",
            method="PUT",
            token=token,
            payload={"files": files},
        )
        version = http_json(
            f"https://script.googleapis.com/v1/projects/{script_id}/versions",
            method="POST",
            token=token,
            payload={"description": "Pick Pack 1291 Beta59 manual OTA metadata"},
        )
        new_version = int(version["versionNumber"])
        if new_version <= deployed_version:
            raise RuntimeError("new GAS version did not advance")
        http_json(
            dep_url,
            method="PUT",
            token=token,
            payload={
                "deploymentConfig": {
                    "scriptId": script_id,
                    "versionNumber": new_version,
                    "manifestFileName": "appsscript",
                    "description": "Pick Pack 1291 Beta59 manual OTA metadata",
                }
            },
        )
        deploy_action = "PATCHED_AND_DEPLOYED"
        print(f"GAS deploy={deployed_version}->{new_version}")

    dep2 = http_json(dep_url, token=token)
    live_version = int(dep2["deploymentConfig"]["versionNumber"])
    if live_version != new_version:
        raise RuntimeError((live_version, new_version))
    after = http_json(
        f"https://script.googleapis.com/v1/projects/{script_id}/content?versionNumber={live_version}",
        token=token,
    )
    live_src = next(str(item.get("source", "")) for item in after["files"] if item.get("type") == "SERVER_JS" and item.get("name") == "PICK_PACK_API")
    live_sha = hashlib.sha256(live_src.encode("utf-8")).hexdigest()
    _, _, live_fn = find_function(live_src)
    for needle in ["const version = '0.4.2-beta.59';", "version_code: 65", TARGET_SHA, TAG]:
        if needle not in live_fn:
            raise RuntimeError(f"deployed OTA missing {needle}")

    update = None
    for attempt in range(30):
        try:
            result = post_gas({"action": "update_check", "channel": "BETA", "current_version": "0.4.2-beta.58"})
            if (
                result.get("ok") is True
                and result.get("available") is True
                and result.get("source") == "GITHUB_RELEASE"
                and result.get("version_name") == TARGET_VERSION
                and int(result.get("version_code", -1)) == TARGET_CODE
                and str(result.get("sha256", "")).lower() == TARGET_SHA
                and int(result.get("size", -1)) == TARGET_SIZE
                and str(result.get("apk_url", "")).endswith("/" + APK_NAME)
            ):
                update = result
                break
        except Exception as exc:
            print("propagation retry:", type(exc).__name__)
        time.sleep(4)
    if update is None:
        raise RuntimeError("Beta58->Beta59 live OTA gate failed")

    self_result = post_gas({"action": "update_check", "channel": "BETA", "current_version": TARGET_VERSION})
    stable_result = post_gas({"action": "update_check", "channel": "STABLE", "current_version": "0.1.0-stable"})
    if not (self_result.get("ok") is True and self_result.get("available") is False and self_result.get("version_name") == TARGET_VERSION):
        raise RuntimeError(("self", self_result))
    if not (
        stable_result.get("ok") is True
        and stable_result.get("available") is False
        and stable_result.get("channel") == "STABLE"
        and stable_result.get("reason") == "NO_RELEASE"
    ):
        raise RuntimeError(("stable", stable_result))

    with urllib.request.urlopen(update["apk_url"], timeout=180) as response:
        apk = response.read()
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
        "ota_beta58_to_beta59": "PASS",
        "ota_beta59_self_no_update": "PASS",
        "stable_no_update": "PASS",
        "ota_mode": "MANUAL_ONLY",
        "stable": "UNTOUCHED",
        "verdict": "PASS",
    }
    (out / "GAS_BETA59_DEPLOY_OTA_RECEIPT.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
