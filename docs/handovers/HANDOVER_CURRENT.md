# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-08-30T06:06:50Z
- owner: Nguyễn Văn Tâm
- branch: release/beta97-qr-meal-alert-role-20260829
- release_trigger_sha: 70e5a3e6997e2e6dcc59836ce682e089757a7624
- archive_file: docs/handovers/HANDOVER_20260830-060520_beta99-pass-live.md
- txt_checkpoint: docs/handovers/HANDOVER_20260830_BETA99_TECHNICAL_PASS_AWAITING_OWNER_2_6.txt
- technical_state: TECHNICAL_PASS_AWAITING_OWNER_ITEMS_2_6

## LIVE / EXACT CANDIDATE
- LIVE BETA: 0.4.2-beta.99 / versionCode 105 / package vn.pickpack1291.app.beta.publicbeta.
- Exact locked candidate: source 660cac5f937c911364a7726661ed4c4b07d92388 / run 33290900322 / artifact 9725965250.
- APK SHA256 c9cd5c9e93d83250040b2a49be262450eb3f4e947d21516a6c9aaa95d881729b / size 13560821 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Stable/main/signer/authority/provider unchanged.

## TERMINAL PASS
- Fast Check PASS run 33290759871.
- Fresh service-live PASS job 99202629701.
- Exact-candidate visual/PDA/API36 PASS run 33292677865 / job 99206960986 / artifact 9726495444.
- Human visual PASS 26 screenshots / 320x568, 360x640, 480x800.
- Publish PASS run 33295954425 / job 99215545273 / artifact 9727420376.
- GAS deployment version 203 readback PASS.
- OTA Beta98 -> Beta99 exact bytes/version/package/hash/signer/install/open PASS job 99215679390 / artifact 9727443577.
- Finalizer PASS job 99215895273 / final artifact 9727446475.
- Terminal workflow 33295954425 SUCCESS; rollback skipped.

## GAS CLEANUP / POST-PUBLISH READBACK
- OWNER manually deleted 100 Project History versions.
- Read-only verify run 33295925825 PASS: version_count=100, current deployment=201, free slots=100 before publish.
- Beta99 publish created version 203 and switched deployment successfully.
- Post-publish read-only run 33296151806 PASS: version_count=101, range 103..203, referenced/current deployment=[203], free slots estimate=99.
- No further GAS deletion needed now.

## OWNER ACCEPTANCE
- Item 1: OK.
- Item 3: OK.
- Item 4: OK.
- Item 5: OK.
- Item 2: PENDING on Beta99 real device — verify Đổi/Trả PDA no USER_PICK_UNAVAILABLE and PDA current/returned/stale/session-old semantics.
- Item 6: PENDING on Beta99 real device — run fault-injection resilience probe scenarios and confirm PASS/FAIL evidence/recovery.

## INVARIANTS
- Existing OWNER-accepted invariants remain ACTIVE_PASS and reverified Beta99.
- PDA-EXIT-001: TECHNICAL_PASS_AWAITING_OWNER; owner item 1 OK, item 2 pending.
- INFRA-RESILIENCE-001: TECHNICAL_PASS_AWAITING_OWNER; item 6 pending.
- Do not promote either to ACTIVE_PASS without OWNER confirmation.

## NEXT_ACTION
WAIT_FOR_OWNER_ACCEPTANCE_ITEMS_2_AND_6
