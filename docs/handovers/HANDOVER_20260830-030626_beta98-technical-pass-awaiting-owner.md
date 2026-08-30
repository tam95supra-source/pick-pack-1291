# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-08-30T03:06:26Z
- owner: Nguyễn Văn Tâm
- branch: release/beta97-qr-meal-alert-role-20260829
- release_trigger_sha: 219ccc89afa281fb454078ad0870770847d032e8
- technical_state: TECHNICAL_PASS_AWAITING_OWNER

## LIVE / CANDIDATE
- LIVE BETA: 0.4.2-beta.98 / versionCode 104 / package vn.pickpack1291.app.beta.publicbeta.
- Exact locked candidate: source 154473b3dcc17c8badcfe345108e59ac3ba6e830 / run 33279188816 / artifact 9722490457.
- APK SHA256 b3085fe35f9bd2f8bed499dc7afcede5f210abdd8021ba379bccad7b795fba4b / size 13544437 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Stable/main/signer/authority/provider unchanged.

## TERMINAL PASS
- Verify/visual/PDA pre-OTA: PASS run 33281633060 / artifact 9723200175.
- Publish + GAS manifest: PASS run 33289302031 / publish artifact 9725453858.
- GAS deployment reused exact target version 201; deployment readback version 201 PASS.
- GitHub Release exact asset SHA/size PASS; Google Drive APK remains FORBIDDEN.
- OTA Beta97 → Beta98 download/install exact bytes + version/package/signer + app open: PASS job 99198065682 / artifact 9725475763.
- Finalizer PASS job 99198266111 / final artifact 9725478850.
- Terminal workflow run 33289302031: SUCCESS.
- Registry-only fast check after Technical PASS state update: PASS run 33289479913.

## REGRESSION / INVARIANTS
- Existing OWNER-accepted UI/QR/attendance/history/OTA invariants remain ACTIVE_PASS and were reverified on Beta98.
- PDA-EXIT-001: TECHNICAL_PASS_AWAITING_OWNER.
- INFRA-RESILIENCE-001: TECHNICAL_PASS_AWAITING_OWNER.
- No new item promoted to ACTIVE_PASS without OWNER acceptance.

## GAS FAILURE RECOVERY CLOSED
- Initial blocker: GAS 200-version limit.
- OWNER deleted old unreferenced history version.
- Retry exposed eventual-consistency readback; harness fixed to wait deployment convergence and reuse exact existing target version.
- Dynamic published_at no longer prevents safe reuse of an otherwise exact release contract.
- No candidate rebuild/resign occurred.

## OWNER ACCEPTANCE
Pending. OWNER should reply by numbered checklist; only confirmed items become ACTIVE_PASS.

## NEXT_ACTION
WAIT_FOR_OWNER_ACCEPTANCE_BETA98_NUMBERED_CHECKLIST
