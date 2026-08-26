---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-08-26T18:12:00+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: feature/beta77-owner-fixes-20260826
working_head_sha: e8b42dedf26bf0d5399b79c4987d1044029c6c1b
archive_file: null
base_or_live_version: 0.4.2-beta.76
target_version: 0.4.2-beta.77
task_state: IN_PROGRESS
next_action: FIX_BETA77_SEMANTIC_VERSION_SHIFT_IN_PUBLISH_MATERIALIZER_THEN_RUN_PUBLISH_ONLY_EXACT_BYTES
---

# BÀN GIAO CANONICAL — BETA77 IN PROGRESS

## 1. OWNER / DoD
- Hoàn tất Beta77 bằng exact candidate đã khóa; không tạo Beta78, không rebuild/resign/version bump.
- GAS canonical và Service/PDA LIVE đã PASS; cấm rerun.
- Stable publish FORBIDDEN; main/signer/authority/provider phải giữ nguyên.
- Final chỉ khi Beta77 OTA LIVE PASS → OTA/Drive/public bytes/LIVE khớp → Stable/main unchanged → release receipt/CURRENT_STATE/handoff READY.

## 2. LIVE / EXACT CANDIDATE
- LIVE hiện tại: Beta76 `0.4.2-beta.76`, versionCode `82`.
- Exact Beta77 source: `43579d1f7f01816cddbdbbcce0a2f19d95d16d91`.
- Candidate run/artifact: `32953924512` / `9601304499`.
- Version/code/package: `0.4.2-beta.77` / `83` / `vn.pickpack1291.app.beta.publicbeta`.
- SHA256: `6ce7838f6f0725ca98b4f3d9237d38aec60092f4488b2795a32ae3f9d24371fb`.
- Size: `13196165` bytes.
- Signer: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.

## 3. Visual/HUMAN — PASS, KHÔNG RERUN
- Original visual job `98132080539` failed vì `UI hierarchy unavailable`; harness-only.
- Hard UiAutomation gate đã được loại.
- Final visual run/artifact `32960147493` / `9603638990`.
- Receipt commit `847378116153befe7b10a29951df43913e864636`.
- `ops/beta77-visual-inspection.json`: HUMAN_VISUAL_PASS đủ 320x568, 360x640, 480x800; build/sign trong visual=false.

## 4. Canonical inherited PASS — KHÔNG RERUN
- GAS: run `32932894375`, Apps Script `194`, artifact `9593853159`, digest `sha256:2b939d18e7db7e74925771516925716f6a4c98e1c7ed3a2c92c9418a0e86fcc1`.
- Service/PDA: run `32953215533`, worker version `0cd7e517-a03b-4dae-80e3-8acb0f437c84`, artifact `9600983380`, digest `sha256:b4da9784cd70eb7b2384c901c0e404104091fed208225032efa4417b4bf9ec36`.

## 5. Publish deterministic failures
### Run 32960698432
- Fail preflight trước production mutation tại `assert old_compat in src`.
- Root cause compat anchor sai shape hậu transform.
- Đã sửa ở commit `5223e46d7393dfbbc7ce04daff5b5ddb00a87257`.

### Run 32961961420
- Terminal failure tại preflight; publish step skipped, chưa production mutation.
- Exact candidate SHA/size/metadata và visual receipt đều PASS trước điểm lỗi.
- Lỗi gốc mới: `AssertionError: if(version==='0.4.2-beta.77') out.version_code=82;` tại Python materializer.
- Root cause: wrapper chỉ đổi `0.4.2-beta.75 → beta.76` nhưng chưa nâng atomic target `0.4.2-beta.76 → beta.77`; do đó target line vẫn Beta76/code82.
- Đường PASS deterministic: dùng placeholder shift `beta.76 -> __BETA77_TARGET__`, `beta.75 -> beta.76`, `__BETA77_TARGET__ -> beta.77`; sau đó các exact code/readback replacements hiện có mới match.
- Cấm retry run với script hiện tại.

## 6. Invariants
- Không poll/rerun run candidate cũ `32953924512` hay visual job cũ.
- Không rebuild/resign/revisual/GAS/Service.
- Stable/main/signer/authority/provider không đổi.
- Chỉ publish exact artifact `9601304499`.

## 7. NEXT_ACTION
`FIX_BETA77_SEMANTIC_VERSION_SHIFT_IN_PUBLISH_MATERIALIZER_THEN_RUN_PUBLISH_ONLY_EXACT_BYTES`
