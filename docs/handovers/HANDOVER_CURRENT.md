# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- task_state: TECHNICAL_PASS_AWAITING_OWNER
- time_utc: 2026-09-03T00:36:00Z
- owner: Nguyễn Văn Tâm
- branch: release/beta113-owner-scope-20260902
- archive_file: docs/handovers/HANDOVER_20260903-003600_beta114-technical-pass-awaiting-owner.md

## LIVE
- Beta114 LIVE: 0.4.2-beta.114 / versionCode 120 / package vn.pickpack1291.app.beta.publicbeta.
- Exact candidate: source 5686da2cc6fdb2bf845456bda9e703eb68e9f1f0; run 33691947969; artifact 9870515268.
- SHA256 cc611efc72a3cd0af413f316b6182adb281d398c189f5bb9d613235722b296bd; size 14232565; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- GitHub Release 381651070 / asset 541964779 exact.
- Terminal 33699803398 PASS; publish 9873117701; OTA/install/readback 9873169722; final 9873176752; handoff 9873180650.
- Stable/main/signer/authority unchanged.

## Gates
- Fast Check 33698830085 PASS.
- Service inherited 33655832542/9856893379 PASS; service bytes unchanged.
- Visual/PDA/API36 33698830042/9872907916 PASS; 43 screenshots; 320x568 / 360x640 / 480x800.
- Device/service-discovery 33697808957/9872457667 PASS.
- Runtime DoD 33698019451/9872504979 PASS; backup/restore PASS; Stable remains private.
- OTA exact GitHub Release bytes installed/opened/read back PASS.

## Owner acceptance
- Beta114 new-scope invariants are TECHNICAL_PASS_AWAITING_OWNER, not ACTIVE_PASS.
- Technical receipt: ops/beta114-technical-pass.json.
- OWNER checklist pending.

## Blocker
Không có.

## NEXT_ACTION
WAIT_FOR_OWNER_ACCEPTANCE_BETA114_CHECKLIST
