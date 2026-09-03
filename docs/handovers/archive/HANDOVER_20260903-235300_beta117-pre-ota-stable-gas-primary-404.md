# PICK PACK 1291 — BETA117 PRE-OTA PROTECTED BLOCKER HANDOFF

- schema_version: 2
- status: READY
- time_utc: 2026-09-03T23:53:00Z
- owner: Nguyễn Văn Tâm
- branch: release/beta117-owner-followup-performance-20260904
- live_beta: 0.4.2-beta.116
- beta117_state: PRE_OTA_BLOCKED_PROTECTED_STABLE_GAS

## Exact Beta117 candidate
- version: 0.4.2-beta.117 / versionCode 123
- package: vn.pickpack1291.app.beta.publicbeta
- candidate_source_sha: d8ea2c2f31549647e8676b40dc536d2b1b80e6e5
- candidate_run: 33800745880
- candidate_artifact: 9911117214
- candidate_artifact_name: beta-candidate-33800745880
- apk_sha256: b3454574547eece69ea44c51b2f88da93dd142eb5d1afb82e7fbd0f293cc0d87
- apk_size: 14396405
- signer: d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e
- candidate_locked: true
- rebuild/resign: false/false
- OTA: NOT_PUBLISHED

## PASS evidence — do not rerun if bytes/inputs unchanged
- Service PASS inherited unchanged bytes: run 33797938890 / artifact 9910299408.
- Visual matrix + PDA functional + API36 PASS: run 33816769626 / artifact 9916961610.
- Human visual PASS: 43 real screenshots, 320x568 / 360x640 / 480x800; `ops/beta117-human-visual-receipt.json`.
- Beta auth PASS: run 33817394774 / artifact 9917295154. Beta token rejected by Stable; Stable D1/Sheet hashes unchanged.
- Service discovery/device regression PASS: run 33818941214 / artifact 9917593203.
- Fast Check PASS: run 33819263208.

## Runtime DoD failure history
1. Run 33819159706 failed `SERVICE_DISCOVERY_DEVICE_EVIDENCE_MISSING`; root cause request provenance omitted device regression run/artifact IDs. Fixed without app/service change.
2. Run 33819263277 then failed `STABLE_GAS_GET_FAILED:primary:404`.
3. Exact runtime job retry on same run failed again `STABLE_GAS_GET_FAILED:primary:404`; latest failed artifact 9917714789.

## Diagnosis
- Runtime verifier reads Stable Sheet `__ENVIRONMENT_CONTRACT` dynamically; no hardcoded Stable GAS URL.
- Apps Script API deployment readback occurs before GET and validates the deployment ID, exact web URL, access policy `ANYONE_ANONYMOUS`, and `USER_DEPLOYING` execution policy.
- Therefore current failure is not missing/stale repo provenance or a stale hardcoded URL: deployment metadata is valid, but the Stable primary web-app endpoint itself returns HTTP 404.
- Beta116 Runtime DoD run 33778605857 / artifact 9902663700 had the same Stable architecture healthy: primary/outbound/dr GAS GET HTTP 200 plus idempotent canary/cleanup PASS.
- Beta117 auth PASS proves Stable D1 and Stable Sheet hashes unchanged during Beta auth work.
- No Stable write/redeploy was performed in Beta117 work.

## Protected boundary
Repair/redeploy/change of Stable private GAS is a protected Stable action. Do not perform it without OWNER authorization. Do not bypass Runtime DoD, do not inherit over a fresh 404, and do not publish Beta117 while this gate is failing.

## LIVE safety
- Beta116 remains LIVE and unchanged.
- Stable public remains false / READY_NOT_LIVE.
- Stable/main/signer/authority unchanged.
- APK transport remains GitHub Release only; Google Drive APK forbidden.

## OWNER acceptance carry-over
- Beta116 accepted: 1,2,3,5,7,8,9,10,11.
- Beta116 pending: 4,6.
- Items 4 and 6 remain TECHNICAL_PASS_AWAITING_OWNER; never auto-promote.

## NEXT_ACTION
OWNER_AUTHORIZE_STABLE_PRIVATE_GAS_PRIMARY_RECOVERY_THEN_RERUN_RUNTIME_DOD
