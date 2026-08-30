#!/usr/bin/env python3
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://script.googleapis.com/v1/projects"
CONFIRM_TEXT = "DELETE_UNREFERENCED_GAS_VERSIONS"


def request(method, url, token, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:2000]
        raise RuntimeError(f"Apps Script {method} failed HTTP {exc.code}: {detail}") from exc


def paged(url, token, key):
    out = []
    page = ""
    while True:
        u = url + (("&" if "?" in url else "?") + "pageSize=50")
        if page:
            u += "&pageToken=" + urllib.parse.quote(page, safe="")
        payload = request("GET", u, token)
        out.extend(payload.get(key) or [])
        page = str(payload.get("nextPageToken") or "")
        if not page:
            return out


def deployment_id(raw):
    raw = raw.strip()
    return raw.split("/s/", 1)[1].split("/", 1)[0] if "/s/" in raw else raw


def inventory(script_id, token, current_deployment_id):
    versions = paged(f"{API}/{script_id}/versions", token, "versions")
    deployments = paged(f"{API}/{script_id}/deployments", token, "deployments")
    refs = {}
    for dep in deployments:
        cfg = dep.get("deploymentConfig") or {}
        number = cfg.get("versionNumber")
        if isinstance(number, int):
            refs.setdefault(number, []).append(str(dep.get("deploymentId") or ""))
    nums = sorted(
        v.get("versionNumber")
        for v in versions
        if isinstance(v.get("versionNumber"), int)
    )
    current = next(
        (d for d in deployments if str(d.get("deploymentId") or "") == current_deployment_id),
        None,
    )
    current_v = ((current or {}).get("deploymentConfig") or {}).get("versionNumber")
    if not isinstance(current_v, int):
        raise RuntimeError("CURRENT_DEPLOYMENT_VERSION_NOT_RESOLVED")
    if current_v not in refs:
        raise RuntimeError("CURRENT_DEPLOYMENT_NOT_IN_REFERENCED_SET")
    return nums, refs, current_v, deployments


def main():
    out_path = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/gas-version-cleanup/receipt.json")
    sid = os.environ.get("GAS_SCRIPT_ID", "").strip()
    token = os.environ.get("ACCESS_TOKEN", "").strip()
    dep = deployment_id(os.environ.get("GAS_DEPLOYMENT_ID", ""))
    action = os.environ.get("CLEANUP_ACTION", "DRY_RUN").strip().upper()
    confirm = os.environ.get("CLEANUP_CONFIRM", "").strip()
    try:
        keep_latest = int(os.environ.get("KEEP_LATEST", "40"))
    except ValueError as exc:
        raise RuntimeError("KEEP_LATEST_MUST_BE_INTEGER") from exc

    if not sid or not token or not dep:
        raise RuntimeError("CLEANUP_ENV_MISSING")
    if action not in {"DRY_RUN", "DELETE"}:
        raise RuntimeError("CLEANUP_ACTION_MUST_BE_DRY_RUN_OR_DELETE")
    if keep_latest < 20 or keep_latest > 180:
        raise RuntimeError("KEEP_LATEST_OUT_OF_SAFE_RANGE_20_180")

    nums, refs, current_v, deployments = inventory(sid, token, dep)
    keep_recent = set(nums[-keep_latest:])
    referenced = set(refs)
    protected = keep_recent | referenced | {current_v}
    candidates = [n for n in nums if n not in protected]

    # Safety invariants before any destructive request.
    if current_v in candidates:
        raise RuntimeError("SAFETY_CURRENT_DEPLOYMENT_SELECTED_FOR_DELETE")
    if referenced.intersection(candidates):
        raise RuntimeError("SAFETY_REFERENCED_VERSION_SELECTED_FOR_DELETE")
    if len(nums) - len(candidates) < keep_latest:
        raise RuntimeError("SAFETY_RETENTION_FLOOR_BREACHED")

    before = {
        "version_count": len(nums),
        "min_version": nums[0] if nums else None,
        "max_version": nums[-1] if nums else None,
        "deployment_count": len(deployments),
        "referenced_versions": sorted(referenced),
        "current_deployment_version": current_v,
    }

    deleted = []
    if action == "DELETE":
        raise RuntimeError("APPS_SCRIPT_API_VERSION_DELETE_UNSUPPORTED_USE_PROJECT_HISTORY_BULK_DELETE_UI")
        for number in candidates:
            # Fresh deployment readback immediately before each destructive deletion.
            _, live_refs, live_current, _ = inventory(sid, token, dep)
            if live_current != current_v:
                raise RuntimeError(
                    f"DEPLOYMENT_CHANGED_DURING_CLEANUP:{current_v}->{live_current}"
                )
            if number in live_refs:
                raise RuntimeError(f"VERSION_BECAME_REFERENCED:{number}")
            request("DELETE", f"{API}/{sid}/versions/{number}", token)
            deleted.append(number)
            time.sleep(0.12)

    after_nums, after_refs, after_current, after_deployments = inventory(sid, token, dep)
    if after_current != current_v:
        raise RuntimeError("CURRENT_DEPLOYMENT_CHANGED_AFTER_CLEANUP")
    if set(after_refs) != referenced:
        raise RuntimeError("REFERENCED_VERSION_SET_CHANGED_AFTER_CLEANUP")
    if len(after_deployments) != len(deployments):
        raise RuntimeError("DEPLOYMENT_COUNT_CHANGED_AFTER_CLEANUP")

    expected_after = len(nums) if action == "DRY_RUN" else len(nums) - len(candidates)
    if len(after_nums) != expected_after:
        raise RuntimeError(
            f"VERSION_COUNT_READBACK_MISMATCH:expected={expected_after},actual={len(after_nums)}"
        )

    receipt = {
        "status": "PASS",
        "action": action,
        "keep_latest": keep_latest,
        "before": before,
        "planned_delete_count": len(candidates),
        "planned_delete_versions": candidates,
        "deleted_count": len(deleted),
        "deleted_versions": deleted,
        "after": {
            "version_count": len(after_nums),
            "min_version": after_nums[0] if after_nums else None,
            "max_version": after_nums[-1] if after_nums else None,
            "deployment_count": len(after_deployments),
            "referenced_versions": sorted(after_refs),
            "current_deployment_version": after_current,
            "free_version_slots_estimate": max(0, 200 - len(after_nums)),
        },
        "safety": {
            "all_referenced_preserved": True,
            "current_deployment_preserved": True,
            "deployment_count_preserved": True,
            "minimum_recent_versions_preserved": keep_latest,
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"GAS_VERSION_CLEANUP_ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
