---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-08-25T16:34:00+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: release/beta71-clean-from-beta68-20260825
working_head_sha: d1624406228035af8fead78398e8dba917ff8d80
archive_file: docs/handovers/HANDOVER_20260825-163400_beta73-uiautomation-bridge-blocked.md
base_or_live_version: 0.4.2-beta.72
target_version: 0.4.2-beta.73
task_state: BLOCKED
next_action: OWNER_DECIDE_SETTINGS_VISUAL_GATE_WITHOUT_UIAUTOMATION
---

# BÀN GIAO — BETA73 EXACT CANDIDATE, SETTINGS UIAUTOMATION BRIDGE BLOCKED

## Mục tiêu + DoD
Hoàn tất Beta73 bằng exact candidate, human visual PASS Settings 320x568 / 360x640 / 480x800, publish exact bytes lên Beta, OTA/Drive/LIVE readback khớp; Stable/main/signer/authority không đổi.

## LIVE / TARGET / CANDIDATE
- LIVE vẫn `0.4.2-beta.72`, code `78`; chưa có production write Beta73.
- TARGET `0.4.2-beta.73`, code `79`.
- Locked build run/artifact: `32820317675` / `9552942024`.
- Package: `vn.pickpack1291.app.beta.publicbeta`.
- SHA256: `ad037c1a17d245f90ead59539c5595cc5df6a568b8657ce636cc43d101175fd2`.
- Size: `13130629`.
- Signer: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Android source SHA from candidate metadata: `2d726828bdd83efe21e9cd41db8d5c06d16f5272`.
- Stable identity remains `0.1.0-stable`, code `1`, publish forbidden.
- Worker unchanged/not deployed; repo service source still not proven equal LIVE v64.

## OWNER authorization applied
OWNER superseded old retry-cap blocker: syntax/compile/materialization failures before Settings probe do not count; allowed at most 2 runs that actually enter Settings probe. No rebuild/resign/version bump/Android source/Beta74.

## Materialized preflight
Harness was preflighted before runtime:
- `py_compile` wrappers: PASS.
- generated wrapper/materialized Python compile: PASS.
- exact anchor/replacement counts: PASS.
- `am instrument -w` subprocess timeout: `15s`.
- `subprocess.TimeoutExpired` handled with evidence + fail-fast.
- Settings 320 preflight is before matrix.

## Runtime Settings probe #1 — run 32831697006
- Job: `97751611392`.
- Exact candidate download + SHA/size verify: PASS.
- Route evidence: exact `OperationsActivity` resumed with Settings extras.
- First root error: `PROBE_TIMEOUT tag=settings-preflight-top timeout_seconds=15`.
- Root cause at this stage: recursive AccessibilityNodeInfo traversal never returned under live UI refresh.
- Evidence artifact: `9557050415`.
- Counts as actual Settings-probe run #1.

## Runtime Settings probe #2 — run 32832299643
- Job: `97753478246`.
- Harness changed; no identical retry.
- Recursive traversal removed. UiProbe only calls `findAccessibilityNodeInfosByText("ĐỔI MẬT KHẨU")` and `findAccessibilityNodeInfosByText("NHẬT KÝ")`.
- Exact candidate download + SHA/size verify: PASS.
- Route evidence again proves exact `OperationsActivity` resumed.
- First root error remains: `PROBE_TIMEOUT tag=settings-preflight-top timeout_seconds=15`.
- Evidence artifact: `9557284841`, digest `sha256:e61dcc2c5adbeef4d78624a95982baecc39762d0806dd8ac0b9bcbdafd0b9e1b`.
- Generated `UiProbe.java` in evidence confirms non-recursive targeted marker queries were actually executed by this harness.
- Therefore blocker is now below selector/tree-walk: API29 `Instrumentation -> getUiAutomation()/accessibility bridge` does not return while this app screen is live-refreshing.
- Counts as actual Settings-probe run #2; OWNER-authorized actual-probe budget is exhausted.

## Harness/files changed
- `tools/run_beta73_visual.py`
  - `d3c1b3e16371e70557c56f04333d1b32d5bb1b9d`: replace recursive accessibility walk with bounded marker lookup; blob `95e3c9713b74c7e8796e9e9877a80ac62a2ab060`.
- `ops/beta-release-request.json`
  - `4f86733a83da7200f8ba2e14148761be2deb7433`: actual probe #1.
  - `d1624406228035af8fead78398e8dba917ff8d80`: actual probe #2.
- No Android source change after candidate lock. No build/sign/version change.

## New OWNER blocker — not retry-cap permission
The required semantic-marker gate cannot be implemented with `am instrument -w`/UiAutomation on the current API29 harness: both materially different probe implementations reach the correct Settings activity then block inside the UiAutomation bridge before returning marker data.

One OWNER decision is required: **authorize replacing the failing UiAutomation semantic-marker gate with `dumpsys activity` route proof + raw Settings screenshots + human visual confirmation of the unique visible markers (`ĐỔI MẬT KHẨU` top, `NHẬT KÝ` lower) at 320/360/480, still using exact artifact `9552942024`.** This changes only the visual verification method; APK/source/version/signer/authority stay immutable.

## Resume after OWNER decision
If authorized, use existing visual-only workflow/harness without `am instrument` marker calls: route Settings, raw screenshot top, scroll, raw screenshot lower, then human inspect markers and layout at all three sizes. Only after human PASS: publish exact artifact `9552942024`, fresh-read OTA/Drive/LIVE, verify URL/SHA/size/version/package/signer and Stable/main/signer/authority unchanged, update CURRENT_STATE and PASS handoff.

## Invariants
- Beta73 candidate bytes immutable.
- No rebuild/resign/Beta74/Android source change.
- No blind Worker deploy.
- No publish before human visual PASS.
- Stable/main/signer/authority unchanged unless OWNER explicitly changes scope.

## NEXT_ACTION
`OWNER_DECIDE_SETTINGS_VISUAL_GATE_WITHOUT_UIAUTOMATION`
