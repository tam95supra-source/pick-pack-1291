#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = "ops/owner-acceptance-current.json"


def fail(msg: str) -> None:
    raise SystemExit("OWNER_ACCEPTANCE_LEDGER_GUARD_FAIL:" + msg)


def load_text(text: str) -> dict:
    try:
        data = json.loads(text)
    except Exception as exc:
        fail(f"INVALID_JSON:{exc}")
    if not isinstance(data, dict):
        fail("ROOT_NOT_OBJECT")
    return data


def beta_no(version: str) -> int:
    m = re.fullmatch(r"0\.4\.2-beta\.(\d+)", str(version or ""))
    if not m:
        fail("INVALID_BETA_VERSION")
    return int(m.group(1))


def validate(data: dict) -> None:
    if data.get("schema_version") != 1:
        fail("SCHEMA_VERSION")
    epoch = data.get("state_epoch")
    if not isinstance(epoch, int) or epoch <= 0:
        fail("STATE_EPOCH")
    if data.get("channel") != "BETA":
        fail("CHANNEL")
    public = data.get("public_beta") or {}
    beta_no(public.get("version_name"))
    code = public.get("version_code")
    if not isinstance(code, int) or code <= 0:
        fail("VERSION_CODE")
    if not re.fullmatch(r"[0-9a-f]{40}", str(public.get("source_sha", ""))):
        fail("SOURCE_SHA")
    if not re.fullmatch(r"[0-9a-f]{64}", str(public.get("apk_sha256", ""))):
        fail("APK_SHA256")
    scope = data.get("owner_scope") or {}
    if not scope.get("scope_id"):
        fail("SCOPE_ID")
    checklist = data.get("checklist") or {}
    revision = checklist.get("revision")
    if not isinstance(revision, int) or revision < 0:
        fail("CHECKLIST_REVISION")
    responses = checklist.get("owner_responses")
    if not isinstance(responses, list):
        fail("OWNER_RESPONSES")
    fencing = data.get("fencing") or {}
    for key in ("reject_lower_state_epoch", "reject_older_beta_version", "reject_lower_checklist_revision"):
        if fencing.get(key) is not True:
            fail("FENCING_" + key.upper())
    if fencing.get("owner_silence_is_acceptance") is not False:
        fail("OWNER_SILENCE_POLICY")


def git_show(ref: str) -> str | None:
    p = subprocess.run(
        ["git", "show", f"{ref}:{LEDGER}"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return p.stdout if p.returncode == 0 else None


def compare(old: dict, new: dict) -> None:
    old_epoch = int(old["state_epoch"])
    new_epoch = int(new["state_epoch"])
    if new_epoch < old_epoch:
        fail("STATE_EPOCH_ROLLBACK")

    old_beta = beta_no(old["public_beta"]["version_name"])
    new_beta = beta_no(new["public_beta"]["version_name"])
    if new_beta < old_beta:
        fail("BETA_VERSION_ROLLBACK")

    old_check = old.get("checklist") or {}
    new_check = new.get("checklist") or {}
    old_id = old_check.get("checklist_id")
    new_id = new_check.get("checklist_id")
    old_rev = int(old_check.get("revision", 0))
    new_rev = int(new_check.get("revision", 0))

    if new_epoch == old_epoch:
        if (old.get("owner_scope") or {}).get("scope_id") != (new.get("owner_scope") or {}).get("scope_id"):
            fail("SCOPE_CHANGED_WITHOUT_EPOCH_ADVANCE")
        if new_beta != old_beta:
            fail("BETA_CHANGED_WITHOUT_EPOCH_ADVANCE")
        if old_id and new_id != old_id:
            fail("CHECKLIST_ID_CHANGED_WITHOUT_EPOCH_ADVANCE")
        if new_rev < old_rev:
            fail("CHECKLIST_REVISION_ROLLBACK")
        old_responses = old_check.get("owner_responses") or []
        new_responses = new_check.get("owner_responses") or []
        if len(new_responses) < len(old_responses):
            fail("OWNER_RESPONSE_HISTORY_TRUNCATED")

    if new_beta == old_beta and new_epoch > old_epoch and old_id and new_id == old_id and new_rev < old_rev:
        fail("CHECKLIST_REVISION_ROLLBACK_SAME_RELEASE")


def self_test() -> None:
    base = {
        "schema_version": 1,
        "state_epoch": 10,
        "channel": "BETA",
        "public_beta": {"version_name": "0.4.2-beta.118", "version_code": 124, "source_sha": "a"*40, "apk_sha256": "b"*64},
        "owner_scope": {"scope_id": "S"},
        "checklist": {"checklist_id": "C", "revision": 2, "owner_responses": [{"x": 1}]},
        "fencing": {"reject_lower_state_epoch": True, "reject_older_beta_version": True, "reject_lower_checklist_revision": True, "owner_silence_is_acceptance": False},
    }
    validate(base)
    newer = json.loads(json.dumps(base)); newer["checklist"]["revision"] = 3; newer["checklist"]["owner_responses"].append({"x": 2}); compare(base, newer)
    bad = json.loads(json.dumps(base)); bad["checklist"]["revision"] = 1
    try:
        compare(base, bad)
    except SystemExit:
        pass
    else:
        fail("SELFTEST_REVISION_ROLLBACK_NOT_CAUGHT")
    print("owner_acceptance_ledger_guard_selftest=PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-ref")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return
    current = load_text((ROOT / LEDGER).read_text())
    validate(current)
    if args.base_ref:
        old_text = git_show(args.base_ref)
        if old_text:
            old = load_text(old_text)
            validate(old)
            compare(old, current)
    print("owner_acceptance_ledger_guard=PASS")


if __name__ == "__main__":
    main()
