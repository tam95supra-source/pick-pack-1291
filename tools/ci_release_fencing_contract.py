#!/usr/bin/env python3
import json,pathlib,re
R=pathlib.Path(__file__).resolve().parents[1]
def read(p):return (R/p).read_text()
def must(x,m):
    if not x: raise SystemExit("CI_RELEASE_FENCE_FAIL:"+m)
beta=read(".github/workflows/beta-release.yml")
stable=read(".github/workflows/stable-private-provision.yml")
verify=read(".github/workflows/stable-isolation-verify.yml")
prov=read("tools/stable_private_provision.py")
req=json.loads(read("ops/stable-private-provision-request.json"))
promo=json.loads(read("ops/promotion-lock-dry-run.json"))
contract=json.loads(read("config/environment_contracts.json"))
must('.stable_publish=="FORBIDDEN"' in beta,"BETA_STABLE_PUBLISH_GUARD_MISSING")
must("candidate_locked==true" in beta and "human_visual_pass==true" in beta and 'pda_functional_pre_ota=="PASS"' in beta,"BETA_PUBLISH_PREOTA_GUARD_MISSING")
must("rebuild==false" in beta and "resign==false" in beta,"BETA_EXACT_BYTES_GUARD_MISSING")
must('apk_transport=="GITHUB_RELEASE_ONLY"' in beta and 'google_drive_apk=="FORBIDDEN"' in beta,"APK_GITHUB_ONLY_GUARD_MISSING")
must("BETA_RELEASE_TOKEN" in beta,"BETA_RELEASE_TOKEN_SCOPE_MISSING")
publish=read("tools/beta83_publish_ota.sh")
must("BASE_CANDIDATE_SOURCE=$(jq -r '.base_candidate_source_sha // .base_source_sha'" in publish,"BETA_BASE_CANDIDATE_SOURCE_SPLIT_MISSING")
must('ensure_beta_github_release.sh "$PREV" "$BASE_CANDIDATE_SOURCE"' in publish,"BETA_BASE_RELEASE_USES_CANDIDATE_SOURCE_MISSING")
must('ensure_beta_github_release.sh "$PREV" "$BASE_SOURCE"' not in publish,"BETA_BASE_RELEASE_SERVICE_SOURCE_CONFLATION")
must('--arg source "$BASE_SOURCE"' in publish,"BETA_BASE_FINAL_SERVICE_SOURCE_GUARD_MISSING")
must("base_live_final_repo_receipt" in beta and "base_live_final_repo_receipt" in publish,"BETA_BASE_FINAL_REPO_RECEIPT_FALLBACK_MISSING")
must("REPO_TECHNICAL_PASS" in publish and "ota_readback_run_id" in publish and "ota_readback_artifact_id" in publish,"BETA_BASE_FINAL_REPO_RECEIPT_NOT_FAIL_CLOSED")
finalize=read("tools/finalize_beta83.sh")
must('.technical_pass_status="PASS"' in finalize and '.owner_acceptance="PENDING"' in finalize,"BETA_FINALIZER_TECHNICAL_OWNER_STATE_MISSING")
# Current canonical finalizer derives the exact pending requirement IDs from OWNER_SCOPE_CURRENT.
must('WAIT_FOR_OWNER_ACCEPTANCE_REQUIREMENTS_${OWNER_PENDING_NUMBERS}' in finalize and 'TECHNICAL_PASS_AWAITING_OWNER' in finalize,"BETA_FINALIZER_OWNER_NEXT_ACTION_MISSING")
_rebase=finalize.find('git rebase "origin/$BRANCH"')
_commit=finalize.find('git commit -m')
must(_rebase>=0 and _commit>=0 and _rebase<_commit,"BETA_FINALIZER_REBASE_MUST_PRECEDE_COMMIT")
must(finalize.count('git rebase "origin/$BRANCH"')==1,"BETA_FINALIZER_REBASE_COUNT_INVALID")
must("group: beta-release-${{ github.ref }}" in beta,"BETA_CONCURRENCY_SCOPE_MISSING")
must("group: stable-private-provision" in stable and "cancel-in-progress: false" in stable,"STABLE_PROVISION_CONCURRENCY_GUARD_MISSING")
must("group: stable-isolation-verify" in verify and "cancel-in-progress: false" in verify,"STABLE_VERIFY_CONCURRENCY_GUARD_MISSING")
must(req["stable_public_activation"] is False,"STABLE_PUBLIC_ACTIVATION_TRUE")
must(contract["environments"]["STABLE"]["stable_publish_allowed"] is False,"STABLE_CONTRACT_PUBLISH_ALLOWED")
must(promo["stable_promotion_lock"]["owner_promotion_authorization"] is None,"STABLE_OWNER_AUTH_FABRICATED")
must(promo["stable_promotion_lock"]["stable"]["ota_active"] is False and promo["stable_promotion_lock"]["stable"]["manifest_active"] is False,"STABLE_OTA_MANIFEST_ACTIVE")
for marker in ['service_token=b64u(secrets.token_bytes(48))','admin_token=b64u(secrets.token_bytes(48))','bridge=b64u(secrets.token_bytes(48))']:
    must(marker in prov,"STABLE_RUNTIME_SECRET_NOT_EPHEMERAL_"+marker.split("=")[0])
for secret_name in ["SERVICE_TOKEN_SECRET","M1_ADMIN_TOKEN","GAS_BRIDGE_SHARED_SECRET"]:
    must(("secrets."+secret_name) not in beta and ("secrets."+secret_name) not in stable,"STABLE_RUNTIME_SECRET_EXPOSED_TO_GITHUB_"+secret_name)
must('"password_exposed":False' in prov,"STABLE_SECRET_RECEIPT_GUARD_MISSING")
must("! grep -Eqi" in beta and "googleapis" in beta and "/drive" in beta and "DRIVE_FOLDER_ID" in beta,"BETA_DRIVE_NEGATIVE_GUARD_MISSING")
apk_files=["tools/beta83_publish_ota.sh","tools/beta83_rollback.sh","tools/beta83_ota_device_gate.sh","tools/stable_private_apk_verify.sh"]
drive=re.compile(r"(googleapis\\.com/drive|drive\\.google\\.com|drive_file_id|DRIVE_FOLDER_ID)",re.I)
for p in apk_files:
    must(not drive.search(read(p)),"APK_DRIVE_REFERENCE_"+p)
for p in apk_files+["service/src/entry_product.ts","app/build.gradle.kts"]:
    must(not re.search(r"supabase",read(p),re.I),"SUPABASE_REFERENCE_"+p)
must("STABLE_PRIVATE_APK_VERIFY" in beta and "public_release:false" in read("tools/stable_private_apk_verify.sh"),"STABLE_PRIVATE_ONLY_APK_GUARD_MISSING")
print("ci_release_fencing=PASS beta_exact_bytes=PASS stable_publish_fail_closed=PASS runtime_secrets_ephemeral=PASS concurrency_separate=PASS github_apk_only=PASS")
