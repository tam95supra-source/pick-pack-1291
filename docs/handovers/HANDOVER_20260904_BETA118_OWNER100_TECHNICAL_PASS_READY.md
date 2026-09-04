# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-04T04:41:01Z
- owner: Nguyễn Văn Tâm
- project: APK PICK PACK 1291
- branch: release/beta118-owner-realtime-bulk-exit-20260904
- candidate_source_sha: 81944b8519cfb7995d78a5c1070c4af3ee2150be
- archive_file: docs/handovers/HANDOVER_20260904_BETA118_OWNER100_TECHNICAL_PASS_READY.md

## Authority / release state
- LIVE BETA remains 0.4.2-beta.117 / versionCode 123.
- Beta118 is LOCKED CANDIDATE only: 0.4.2-beta.118 / versionCode 124 / package vn.pickpack1291.app.beta.publicbeta.
- Candidate run/artifact: 33833810807 / 9922669910.
- Exact APK SHA256: 5216f0eb09f187aed9cb71dcc21cd145fdc3ba7ea7852c74ffe6f85dea2b478f; size 14429173; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Stable/main/signer/authority unchanged. Beta118 publish/OTA remains FORBIDDEN until OWNER accepts blocker checklist.

## Blocker 100 session — Technical PASS
- Root cause: owner-seeded shifts were uppercase CA 1/CA HC/CA 2 while reconciliation grouping was case-sensitive. Canonical D1/event/outbox set was already exact 100.
- Diagnosis 33829110432 / artifact 9921008888: canonical=100, event=100, outbox=100; expected-minus-canonical=0; canonical-minus-expected=0; raw pre-fix review=0; normalized review=100; seed-set SHA256 cc5c5dabfdf2cbf4a89cfef74d8fbe2a9274769582ead27fb6391fcb35f303e6.
- Minimal product fix: ae80424706de74c72dea460e82bdd429090944cc, case-insensitive canonical shift projection; no destructive D1 reseed/rewrite.
- Exact Android UI gate 33836246626 / artifact 9923402264: expected_minus_actual=0, actual_minus_expected=0, positions=PASS, in_only=PASS.
- Local-first/realtime gate 33837587706 / artifact 9923826221: 2 rows immediate 341ms, retained after 1.8s, third row 41ms, warning initial 10ms and update 19ms; PASS.
- Visual + direct PDA functional API29: step PASS run 33835144144 / artifact 9923142675.
- Android 16/API36 Back: PASS run 33835843259 / artifact 9923339401.
- Candidate + exact Service source: PASS run 33833810807.

## Invariant state
- REVIEW-100-SESSIONS-001 = TECHNICAL_PASS_AWAITING_OWNER.
- Do NOT mark ACTIVE_PASS until Nguyễn Văn Tâm explicitly accepts all three checklist items.
- Do NOT resume Beta118 publish/OTA before that OWNER acceptance.

## OWNER checklist
1. Rà soát hiển thị đúng chính xác 100 người expected.
2. Ba bucket Ca 1 / Ca HC / Ca 2 + vị trí/in-only đúng.
3. Không extra/duplicate/missing/wrong-source.

## NEXT_ACTION
OWNER_CHECKLIST_1_TO_3
