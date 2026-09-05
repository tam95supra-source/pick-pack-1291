# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-05T02:22:13Z
- owner: Nguyễn Văn Tâm
- branch: beta/current
- live_commit: 10482dbe83fe14121d14d91c760f613e5af15f0a
- registry_commit: 43539850160fa916af25963923de5295157a1902
- technical_receipt: ops/beta122-technical-pass.json

## Mục tiêu + DoD
Beta122 đã Technical PASS/LIVE trên exact locked APK; toàn bộ pre-OTA, publish, OTA install/open/readback và finalize PASS. OWNER acceptance đã có item 1/3 từ Beta121 và được bảo toàn; chỉ item 2/4 còn chờ OWNER nghiệm thu lại sau fix Beta122.

## LIVE / CANDIDATE
- LIVE BETA: 0.4.2-beta.122 / versionCode 128 / package vn.pickpack1291.app.beta.publicbeta.
- Source: fd26d18b0ae81cbc919824141f3670a3fe3b276e.
- Candidate: run 33937101147 / artifact 9960620587.
- APK SHA256: b06d1cf470fa840f53c9641397bf16cdfa3ce5d20651349f4ac3bb6e0ef4b54b / size 14429173.
- Signer: d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- GitHub Release tag: v0.4.2-beta.122-publicbeta; exact asset readback PASS.

## Evidence
- Fast Check: PASS run 33937614821.
- Service gate: inherited PASS run 33929895214 / artifact 9958376646; service/GAS bytes unchanged.
- Visual + PDA functional + API36: PASS run 33937614831 / artifact 9960788555; human PASS 43 screenshots at 320x568, 360x640, 480x800.
- Service discovery/device regression: PASS run 33938053451 / artifact 9960858682.
- Runtime DoD: PASS run 33938184655 / artifact 9960886189.
- Publish exact bytes: PASS terminal run 33938535151 / artifact 9960999680.
- OTA Beta121 → Beta122 install/open/readback: PASS artifact 9961036406; downloaded and installed exact SHA/size/signer/version/package.
- Final receipt: PASS artifact 9961041181; readback=true; stable_unchanged=true; authority_change=NONE.
- beta/current finalized commit: 10482dbe83fe14121d14d91c760f613e5af15f0a.
- main unchanged: 021dac5c6932b3ac5c60ce8fdba562ddf3d9688f.
- Stable remains not public; authority SERVICE_PRIMARY / PRODUCTION / epoch 9 unchanged.
- Google Drive APK: FORBIDDEN; transport GITHUB_RELEASE_ONLY.

## OWNER acceptance / invariants
- Item 1 `UI-STATUS-DETAIL-VI-003`: ACTIVE_PASS — OWNER already OK; preserved.
- Item 2 `SUPERADMIN-EFFECTIVE-ROLE-003`: TECHNICAL_PASS_AWAITING_OWNER — Beta122 fix verified technically; chờ OWNER recheck.
- Item 3 `SETTINGS-REGION-INHOUSE-DROP-001`: ACTIVE_PASS — OWNER already OK; preserved.
- Item 4 `PDA-SOURCE-MASTER-001`: TECHNICAL_PASS_AWAITING_OWNER — Beta122 fix verified technically; chờ OWNER recheck.
- Registry machine-readable: qa/stable_invariants.yml updated and readback PASS.
- Canonical prose: docs/STABLE_INVARIANTS.md updated and readback PASS.

## Blocker
Không có blocker kỹ thuật. Chỉ còn OWNER acceptance item 2/4.

## NEXT_ACTION
WAIT_FOR_OWNER_ACCEPTANCE_ITEMS_2_4
