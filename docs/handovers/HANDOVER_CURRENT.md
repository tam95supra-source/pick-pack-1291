# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- task_state: TECHNICAL_PASS_AWAITING_OWNER
- time_utc: 2026-09-02T09:18:37Z
- owner: Nguyễn Văn Tâm
- branch: release/beta112-unified-review-warning
- archive_file: docs/handovers/HANDOVER_20260902-091837_beta112-technical-pass-await-owner.md

## LIVE
- Beta112 LIVE: 0.4.2-beta.112 / versionCode 118 / package vn.pickpack1291.app.beta.publicbeta.
- Exact candidate: source b3009ca701670af487ee8dce3538fe9c3cde4ae5; run 33596529877; artifact 9833670469.
- SHA256 d5de4fea496a1be4926f3acc49f82fb60eb9065de694e075251ca493ce298e76; size 14216181; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- GitHub Release: release 381116427 / asset 540918700 / exact size 14216181.
- Stable/main/signer/authority unchanged.

## Technical DoD
- Fast Check 33612134466 PASS incl Android/debug.
- Service 33588851239 / 9831120144 PASS inherited because service source unchanged.
- Visual/PDA/API36 33597157250 / 9833913262 PASS; 42 screenshots; human visual PASS 320x568 / 360x640 / 480x800.
- Device discovery 33611415963 / 9839191113 PASS.
- Beta auth Sheet parity recovery 33612548361 / 9839580952 PASS; no password rotation, no D1 mutation, no session revocation, Stable unchanged.
- Runtime DoD 33612695867 / 9839670809 PASS; prior 33611682634 BETA_SHEET_AUTH_TARGET_FAILED is SUPERSEDED by parity repair + fresh runtime PASS.
- Terminal 33612994423 PASS; publish 9839800512; OTA/install/readback 9839879502; final 9839890706.
- Technical receipt: ops/beta112-technical-pass.json.
- Release lock: ops/beta112-release-lock.json.

## Scope result
- UI-REVIEW-WARNING-001: TECHNICAL_PASS_AWAITING_OWNER.
- Beta112 uses one shared ReviewAlertUi component for reconciliation + old-session + meal + labor warnings.
- Fixed visual contract: 42dp height / 10.5sp / radius 10dp / stroke 2dp; canonical warning red; canonical OK green; Android default min-size/font-padding/state animator variance removed.
- Beta111 OWNER-accepted items 2–7 remain ACTIVE_PASS; no semantics changed.

## OWNER acceptance
Only one item remains:
1. Rà soát vào/ra và các cảnh báo liên quan phải nhìn đồng nhất về chiều cao, cỡ chữ, bo góc, viền và bố cục; mọi cảnh báo cùng đỏ canonical, rà soát đủ dùng xanh canonical.

Expected reply: `1 OK` or `1 chưa OK: ...`.

## Blocker
Không có.

## NEXT_ACTION
OWNER_ACCEPTANCE_BETA112_ITEM_1_ONLY
