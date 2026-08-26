---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-08-26T18:10:00+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: release/beta71-clean-from-beta68-20260825
working_head_sha: 43579d1f7f01816cddbdbbcce0a2f19d95d16d91
archive_file: PENDING_UNTIL_FINAL_READY_ARCHIVE
target_version: 0.4.2-beta.77
task_state: IN_PROGRESS
next_action: FIX_VISUAL_HARNESS_UIAUTOMATION_HARD_DEPENDENCY_THEN_PROBE_320x568
---

# BÀN GIAO CANONICAL — BETA77 TERMINAL VISUAL HARNESS FAILURE

## OWNER / DoD
Tiếp tục exact Beta77 từ terminal failure đã xác định. Không poll run cũ, không retry mù, không rerun GAS hoặc Service/PDA. Chỉ hoàn tất khi BETA77 OTA LIVE PASS → OTA/Drive/LIVE khớp → Stable/main unchanged → state/handoff READY, hoặc blocker OWNER thật.

## LIVE / TARGET / CANDIDATE
### TARGET
- Beta77 OTA LIVE.

### EXACT CANDIDATE — LOCKED
- Source: `43579d1f7f01816cddbdbbcce0a2f19d95d16d91`
- Artifact: `9601304499`
- Version: `0.4.2-beta.77`
- versionCode: `83`
- Package: `vn.pickpack1291.app.beta.publicbeta`
- SHA256: `6ce7838f6f0725ca98b4f3d9237d38aec60092f4488b2795a32ae3f9d24371fb`
- Size: `13196165`
- Signer: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`
- No rebuild / resign / version bump / Beta78.

### CANONICAL PASS — DO NOT RERUN
- GAS canonical PASS.
- Service/PDA LIVE PASS.

## TERMINAL FAILURE EVIDENCE
- Workflow run `32953924512`: TERMINAL.
- Candidate job `98131295305`: SUCCESS.
- Visual job `98132080539`: FAILURE.
- Candidate artifact `9601304499`.
- Visual failure artifact `9601362376`.
- First/root error: `AssertionError: 320x568-employee-home: UI hierarchy unavailable`.
- Failure path: `tools/run_beta76_visual.py` → `assert_home()` → `visible_texts()` → `dump_ui()` → `uiautomator dump` không trả XML có `<hierarchy>`.
- APK install PASS; chưa có evidence lỗi APK.
- Classification: HARNESS defect. Không poll/retry run cũ.

## ROOT CAUSE / ĐƯỜNG PASS
- Root cause: visual harness phụ thuộc cứng UiAutomation/accessibility hierarchy để xác định UI và điều hướng.
- PASS path: bỏ UiAutomation khỏi mandatory gate; ADB bounded timeout; `am start -W`; verify route bằng `dumpsys activity` + `dumpsys window`; direct route hoặc tọa độ tỷ lệ theo kích thước màn hình; screenshot PNG thật + route/activity/window evidence; UiAutomation optional only.
- Cấm rebuild APK để xử lý visual harness.

## REQUIRED PREFLIGHT
1. `py_compile` harness PASS.
2. Shell syntax PASS.
3. Không còn hard assertion yêu cầu `<hierarchy>`.
4. Exact artifact input phải khớp SHA256 + size ở trên.
5. Android source không đổi.

## PROBE 320x568 REQUIRED
- BUSINESS có thẻ `Quét QR nhân sự`.
- Màn `Quét QR nhân sự`.
- Back về đúng BUSINESS.
- Màn `Nhận hàng rớt`.
- Keyboard mở tại Scan QR nhưng không che form/nút.
- PNG 320x568 thật, không rỗng/đen.
- HUMAN FAIL → sửa route/tọa độ/wait harness only.
- HUMAN PASS → full matrix 320x568, 360x640, 480x800 exact same candidate.

## FULL MATRIX HUMAN GATE
- Đúng màn, không chụp nhầm; không cắt/che/tràn.
- Keyboard không che nút thao tác.
- Nhận hàng rớt đủ select vị trí, Tạo/Sửa/Xoá, Scan QR, DO, Số kiện, nút hành động.
- Quét QR nhân sự đúng dữ liệu và dùng `-` thay `null`.

## AFTER HUMAN PASS
- Lock visual receipt.
- Publish exact bytes artifact `9601304499` lên BETA only.
- Fresh-read OTA, Drive, public bytes, LIVE; đối chiếu SHA256/size/version/code/package/signer.
- Fresh-read Stable/main/signer/authority unchanged.
- Update release receipt, `CURRENT_STATE.md`, canonical handoff và archive READY.

## INVARIANTS
- Stable publish FORBIDDEN.
- Không đổi Stable/main/signer/authority/provider.
- Không GAS/Service/PDA rerun.
- Không poll run `32953924512`.
- Không rerun visual job `98132080539` bằng harness cũ.
- Không final ở probe, automation PASS, pending, hoặc publish chưa readback.

## BLOCKER
- NONE hiện tại.

## NEXT_ACTION
`FIX_VISUAL_HARNESS_UIAUTOMATION_HARD_DEPENDENCY_THEN_PROBE_320x568`
