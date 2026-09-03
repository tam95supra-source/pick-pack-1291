# CURRENT STATE — PICK PACK 1291

- updated_at: 2026-09-03T23:53:00Z
- status: BETA116_PASS_LIVE__BETA117_PRE_OTA_BLOCKED_PROTECTED_STABLE_GAS
- owner_acceptance: PARTIAL_BETA116_9_OF_11_ACCEPTED
- continuity_branch: release/beta117-owner-followup-performance-20260904

## LIVE authority
- beta_live: 0.4.2-beta.116 (versionCode 122)
- live_source_sha: cf01dab16e1c62091561ca008a355a8f49326581
- package: vn.pickpack1291.app.beta.publicbeta
- live_candidate_run: 33767353642
- live_candidate_artifact: 9898290631
- live_apk_sha256: a346d4554e07fc37552c9d8876179860677fc93923a3bd42f9b3f97f5e11f235
- live_apk_size: 14347253
- signer_sha256: d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e
- authority: SERVICE_PRIMARY / PRODUCTION / generation m2-prod-reset-20260823-001
- apk_transport: GITHUB_RELEASE_ONLY
- google_drive_apk: FORBIDDEN
- stable_public: false / READY_NOT_LIVE
- Stable/main/signer/authority: unchanged

## Beta117 exact candidate — PRE OTA
- version: 0.4.2-beta.117 / versionCode 123
- candidate_source_sha: d8ea2c2f31549647e8676b40dc536d2b1b80e6e5
- candidate_run: 33800745880
- candidate_artifact: 9911117214
- apk_sha256: b3454574547eece69ea44c51b2f88da93dd142eb5d1afb82e7fbd0f293cc0d87
- apk_size: 14396405
- candidate_locked: true
- rebuild: false
- resign: false
- live: false

## Beta117 gates
- service: PASS inherited exact unchanged Service bytes from run 33797938890 / artifact 9910299408
- visual_matrix: PASS run 33816769626 / artifact 9916961610
- human_visual: PASS 43 screenshots at 320x568 / 360x640 / 480x800; receipt ops/beta117-human-visual-receipt.json
- pda_functional_pre_ota: PASS
- back_api36: PASS
- beta_auth: PASS run 33817394774 / artifact 9917295154; Stable auth state unchanged
- service_discovery_device_regression: PASS run 33818941214 / artifact 9917593203
- fast_check: PASS run 33819263208
- runtime_dod: BLOCKED — Stable private GAS primary deployment metadata/policy/url readback is valid but live GET returns HTTP 404 twice; failed run 33819263277, latest failed artifact 9917714789
- beta_domain: PENDING
- release_lock_final: PENDING
- beta_ota: NOT_PUBLISHED

## Protected blocker
- Beta116 historical runtime DoD 33778605857 / 9902663700 PASS showed Stable primary/outbound/dr GAS all HTTP 200.
- Beta117 auth PASS proves Stable D1 and Stable Sheet hashes unchanged during Beta auth migration.
- Current Runtime DoD calls Apps Script deployment readback before GET; deployment ID, exact web URL, access=ANYONE_ANONYMOUS and executeAs=USER_DEPLOYING validate, then Stable primary GET returns HTTP 404 on original run and exact retry.
- Unchanged retry is exhausted. Fix/redeploy of Stable private GAS is a protected Stable action and was not performed automatically.

## OWNER acceptance carry-over
- Beta116 accepted: 1,2,3,5,7,8,9,10,11.
- Beta116 pending: 4,6.
- Do not promote pending items to ACTIVE_PASS without OWNER confirmation.

- next_action: OWNER_AUTHORIZE_STABLE_PRIVATE_GAS_PRIMARY_RECOVERY_THEN_RERUN_RUNTIME_DOD
