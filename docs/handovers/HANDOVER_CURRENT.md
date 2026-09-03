# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-03T23:53:00Z
- owner: Nguyễn Văn Tâm
- branch: release/beta117-owner-followup-performance-20260904
- archive_file: docs/handovers/archive/HANDOVER_20260903-235300_beta117-pre-ota-stable-gas-primary-404.md

## Mục tiêu + trạng thái
Beta117 đã có exact locked candidate và đã PASS Service, visual 3 kích thước + human inspection, PDA functional, API36 Back, Beta auth, service-discovery/device regression và Fast Check. Chưa OTA vì Runtime DoD đang fail ở Stable private GAS primary HTTP 404. Beta116 vẫn LIVE.

## LIVE
- Beta116: 0.4.2-beta.116 / code 122 / source cf01dab16e1c62091561ca008a355a8f49326581.
- APK: a346d4554e07fc37552c9d8876179860677fc93923a3bd42f9b3f97f5e11f235 / 14347253 bytes.
- Stable/main/signer/authority unchanged.

## Beta117 exact candidate
- 0.4.2-beta.117 / code 123 / package vn.pickpack1291.app.beta.publicbeta.
- source: d8ea2c2f31549647e8676b40dc536d2b1b80e6e5.
- candidate: run 33800745880 / artifact 9911117214.
- SHA256: b3454574547eece69ea44c51b2f88da93dd142eb5d1afb82e7fbd0f293cc0d87 / size 14396405.
- signer: d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- locked=true; rebuild=false; resign=false; live=false.

## PASS evidence
- Service inherited unchanged: 33797938890 / 9910299408.
- Visual + PDA + API36: 33816769626 / 9916961610 PASS.
- Human visual: PASS 43 ảnh thật, 320x568 / 360x640 / 480x800; `ops/beta117-human-visual-receipt.json`.
- Beta auth: 33817394774 / 9917295154 PASS; Stable D1/Sheet unchanged.
- Device/service-discovery: 33818941214 / 9917593203 PASS.
- Fast Check: 33819263208 PASS.

## Blocker
- Runtime DoD first failed only because request thiếu device-regression provenance; đã sửa.
- Runtime DoD run 33819263277 sau đó fail `STABLE_GAS_GET_FAILED:primary:404`; exact job retry cũng fail cùng lỗi, latest failed artifact 9917714789.
- Apps Script deployment readback trước GET vẫn xác nhận deployment ID, exact URL và policy hợp lệ. Vì vậy đây không phải stale hardcode/harness.
- Beta116 runtime 33778605857 / 9902663700 trước đó PASS cả Stable GAS primary/outbound/dr HTTP 200.
- Sửa/redeploy Stable private GAS là protected Stable action; chưa thực hiện.

## OWNER acceptance carry-over
- Beta116 accepted: 1,2,3,5,7,8,9,10,11.
- Pending: 4,6; vẫn TECHNICAL_PASS_AWAITING_OWNER.

## NEXT_ACTION
OWNER_AUTHORIZE_STABLE_PRIVATE_GAS_PRIMARY_RECOVERY_THEN_RERUN_RUNTIME_DOD
