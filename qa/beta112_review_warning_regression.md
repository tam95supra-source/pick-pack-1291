# Beta112 — Unified Review / Warning Regression

OWNER: Nguyễn Văn Tâm
Baseline: Beta111 LIVE. OWNER accepted checklist items 2–7; only UI-REVIEW-WARNING-001 remains pending fix.

## Scope
- One shared UI component for shift reconciliation and business warnings.
- Fixed geometry: 42dp height, 10.5sp text, 10dp radius, 2dp stroke.
- Canonical warning color: foreground rgb(176,0,32), fill rgb(255,226,232).
- Canonical OK review color: foreground rgb(16,112,66), fill rgb(226,248,235).
- Remove Android Button default min-size/font-padding/state animator variance.
- Old-session, meal and labor warnings use exact same WARNING style.
- Shift reconciliation uses only OK or WARNING tone from the same component.

## OWNER-accepted Beta111 scope to preserve
- NAV-HISTORY-BACK-001 ACTIVE_PASS.
- LABOR-EXACT-SESSION-002 ACTIVE_PASS.
- DOCUMENT-BATCH-MODE-TICK-002 ACTIVE_PASS.
- HISTORY-DELETE-CANONICAL-001 ACTIVE_PASS.
- No changes to their business semantics.

## Regression
- tools/beta112_review_warning_contract.py
- review_warning_shared_style_beta112 runtime flag
- 320x568 / 360x640 / 480x800 visual matrix + human inspection
- Beta111 owner scope contracts remain PASS

## Exact candidate
- source: b3009ca701670af487ee8dce3538fe9c3cde4ae5
- candidate: 33596529877 / 9833670469
- APK SHA256: d5de4fea496a1be4926f3acc49f82fb60eb9065de694e075251ca493ce298e76
- size: 14216181
- visual/PDA/API36: 33597157250 / 9833913262 PASS
- screenshots: 42; human visual inspection PASS
