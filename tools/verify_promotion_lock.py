#!/usr/bin/env python3
import json,pathlib,re,sys
root=pathlib.Path(__file__).resolve().parents[1]
x=json.loads((root/"ops/promotion-lock-dry-run.json").read_text())
b=x["beta_acceptance_lock"]; s=x["stable_promotion_lock"]
assert b["lock_type"]=="BETA_ACCEPTANCE_LOCK" and b["status"]=="DRY_RUN_OWNER_ACCEPTANCE_REQUIRED"
assert b["owner_acceptance_ref"] is None
assert re.fullmatch(r"[0-9a-f]{40}",b["source_sha"])
assert re.fullmatch(r"[0-9a-f]{64}",b["beta"]["apk_sha256"]) and re.fullmatch(r"[0-9a-f]{64}",b["beta"]["signer_sha256"])
assert s["lock_type"]=="STABLE_PROMOTION_LOCK" and s["status"]=="DRY_RUN_READY"
assert s["accepted_source_sha"]==b["source_sha"]
assert s["owner_promotion_authorization"] is None
assert s["stable"]["release_channel"]=="STABLE"
assert s["stable"]["manifest_active"] is False and s["stable"]["ota_active"] is False and s["stable"]["public_domain_active"] is False
assert all(v is False for v in s["isolation"].values())
allowed={"application_id","app_label","icon_badge","release_channel","version","domain_binding","api_binding","credential_ref","datastore_binding","sheet_binding","backup_binding","ota_binding","notification_binding"}
assert set(s["environment_only_diff"])<=allowed
print("PROMOTION_LOCK_DRY_RUN_PASS")
