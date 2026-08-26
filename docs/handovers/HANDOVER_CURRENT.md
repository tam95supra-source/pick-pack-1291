---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-08-26T18:22:00+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: feature/beta77-owner-fixes-20260826
working_head_sha: 3ed136223df4bf782f9a5e4c2c03b19bf71f2514
archive_file: null
base_or_live_version: 0.4.2-beta.76
target_version: 0.4.2-beta.77
task_state: IN_PROGRESS
next_action: FIX_BETA77_COMPAT_FINAL_ASSERT_TO_COMPAT77_THEN_RETRY_EXACT_PUBLISH
---

# BÀN GIAO CANONICAL — BETA77 IN PROGRESS

## 1. DoD / invariants
- Exact candidate only: source `43579d1f7f01816cddbdbbcce0a2f19d95d16d91`, artifact `9601304499`, Beta77 code83, package `vn.pickpack1291.app.beta.publicbeta`, SHA `6ce7838f6f0725ca98b4f3d9237d38aec60092f4488b2795a32ae3f9d24371fb`, size `13196165`, signer `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Visual HUMAN PASS: run/artifact `32960147493` / `9603638990`, receipt `847378116153befe7b10a29951df43913e864636`; không rerun.
- GAS PASS `32932894375` / Apps Script 194 / artifact `9593853159`; Service/PDA PASS `32953215533` / artifact `9600983380`; không rerun.
- Không rebuild/resign/Beta78; Stable/main/signer/authority/provider không đổi.

## 2. Publish progression
- `32960698432`: compat materializer anchor fixed.
- `32961961420`: atomic semantic Beta76→Beta77 shift fixed.
- `32962143541`: stale Beta76 candidate/visual IDs fixed.
- `32962400902`: release-meta legacy `service_change` verifier fixed to canonical `authority_change` + GAS/Service receipts.
- `32962697264`, job `98158343034`: preflight PASS; publisher progressed through exact artifact checks, release-meta copy, OAuth token, then failed Python assertion before GAS mutation. Evidence artifact `9604485879` has 4 files: beta-before Beta76, stable-before NO_APK, exact release-meta, OAuth response. No after/upload evidence.

## 3. Root cause mới nhất
- Read-only GAS canonical artifact `9593853159` confirms live source route is `ppBeta76UpdateCheckCompat_`; helpers Beta73/74/75/76 exist.
- Beta77 materializer correctly creates `compat77` and replaces route `compat76 → compat77`, then creates helper `ppBeta77UpdateCheckCompat_` if absent.
- Inherited final assertion remains `assert compat76 in s and helper_sig in s` because variable name `compat76` is not affected by global `Beta76→Beta77` text replacement.
- Reproduce against canonical GAS source: after transform `compat76 in s = false`, `compat77 in s = true`, `helper77 = true`; legacy final assertion false, corrected assertion true.
- Đây là deterministic publisher assertion defect, không phải GAS/APK defect; chưa production mutation.

## 4. NEXT_ACTION
`FIX_BETA77_COMPAT_FINAL_ASSERT_TO_COMPAT77_THEN_RETRY_EXACT_PUBLISH`
