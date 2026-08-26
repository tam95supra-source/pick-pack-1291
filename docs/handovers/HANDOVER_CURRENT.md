---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-08-26T18:06:00+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: feature/beta77-owner-fixes-20260826
working_head_sha: 441acf2de552e214037e047aa39238ce092516c3
archive_file: null
base_or_live_version: 0.4.2-beta.76
target_version: 0.4.2-beta.77
task_state: IN_PROGRESS
next_action: FIX_BETA77_PUBLISH_MATERIALIZER_COMPAT_ANCHOR_THEN_PUBLISH_EXACT_BYTES_AND_COMPLETE_OTA_LIVE_READBACK
---

# BÀN GIAO CANONICAL — BETA77 IN PROGRESS

## 1. OWNER / DoD
- Hoàn tất Beta77 bằng exact candidate đã khóa; không tạo Beta78, không rebuild/resign/version bump.
- GAS canonical và Service/PDA LIVE đã PASS; cấm rerun.
- Stable publish FORBIDDEN; main/signer/authority/provider phải giữ nguyên.
- Final chỉ khi Beta77 OTA LIVE PASS → OTA/Drive/public bytes/LIVE khớp → Stable/main unchanged → release receipt/CURRENT_STATE/handoff READY.

## 2. LIVE / TARGET / EXACT CANDIDATE
### LIVE
- Beta76: `0.4.2-beta.76`, versionCode `82` — vẫn LIVE cho đến khi Beta77 readback PASS.

### TARGET / LOCKED CANDIDATE
- Source SHA: `43579d1f7f01816cddbdbbcce0a2f19d95d16d91`.
- Candidate run/artifact: `32953924512` / `9601304499`.
- Version: `0.4.2-beta.77`; versionCode `83`.
- Package: `vn.pickpack1291.app.beta.publicbeta`.
- SHA256: `6ce7838f6f0725ca98b4f3d9237d38aec60092f4488b2795a32ae3f9d24371fb`.
- Size: `13196165` bytes.
- Signer SHA256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Candidate job `98131295305`: SUCCESS.
- Original visual job `98132080539`: TERMINAL FAILURE, artifact `9601362376`; root cause `UI hierarchy unavailable`, harness-only, không có bằng chứng APK lỗi.

## 3. Visual harness / HUMAN gate hiện tại
- Hard dependency UiAutomation đã được loại khỏi đường PASS; harness hiện dùng bounded ADB, `am start -W`, activity readback, tọa độ, PNG/IME/pixel evidence.
- Final visual run/artifact: `32960147493` / `9603638990`.
- Visual receipt commit: `847378116153befe7b10a29951df43913e864636`.
- `ops/beta77-visual-inspection.json`: `status=PASS`, `result=HUMAN_VISUAL_PASS`.
- HUMAN PASS đủ `320x568`, `360x640`, `480x800`; đúng Nhận hàng rớt, CRUD OWNER, Scan QR/DO/Số kiện, keyboard không che form/nút; QR nhân sự dùng `-` thay null; PDA/overnight cases đúng.
- Android build/sign trong visual: `false`.

## 4. Canonical gates kế thừa — KHÔNG RERUN
- GAS PASS: run `32932894375`, Apps Script version `194`, artifact `9593853159`, digest `sha256:2b939d18e7db7e74925771516925716f6a4c98e1c7ed3a2c92c9418a0e86fcc1`.
- Service/PDA PASS: run `32953215533`, worker version `0cd7e517-a03b-4dae-80e3-8acb0f437c84`, artifact `9600983380`, digest `sha256:b4da9784cd70eb7b2384c901c0e404104091fed208225032efa4417b4bf9ec36`.

## 5. Publish hiện tại — lỗi gốc mới nhất
- Publish-only run `32960698432`: TERMINAL FAILURE.
- Job `98152164304`, step `Validate publish-only lock and materialized publisher` fail trước production mutation; publish step bị skipped.
- Candidate download trong run này xác minh đúng exact SHA/size.
- Root cause deterministic: `tools/publish_beta77_ota.sh` Python materializer fail tại `assert old_compat in src` (line 57). Inherited Beta76 materialized script sau global Beta76→Beta77 vẫn giữ variable `compat76` nhưng helper đã thành `ppBeta77...`; anchor Beta77 wrapper đang đòi `compat77`, nên không match.
- Đây là publisher/harness anchor defect; không phải APK, GAS canonical hay Service/PDA defect.
- Đường PASS: sửa đúng compat anchor của materializer, `bash -n` + materialize-only preflight PASS, rồi trigger publish-only exact bytes. Không rebuild/resign, không rerun visual, không rerun GAS/Service.

## 6. Workspace / invariants
- Active branch: `feature/beta77-owner-fixes-20260826`.
- Working head trước checkpoint: `441acf2de552e214037e047aa39238ce092516c3`.
- Android source candidate giữ nguyên `43579d...`; các commit sau chỉ harness/receipt/release orchestration.
- Stable/main/signer/authority/provider chưa được phép đổi.
- Cấm poll/rerun run `32953924512` hoặc visual job cũ `98132080539`.
- Cấm tạo Beta78.

## 7. Việc còn lại
1. Sửa deterministic compat anchor trong `tools/publish_beta77_ota.sh`.
2. Preflight: `bash -n`, materialize-only PASS, exact candidate SHA/size/identity PASS, không build/sign/stable/main mutation.
3. Trigger đúng publish-only workflow bằng exact bytes artifact `9601304499`.
4. Nếu transient transport: tối đa 2 retry exact bytes; nếu deterministic thì sửa đúng lỗi gốc, không retry mù.
5. Fresh-read OTA Beta76→Beta77, Beta77 current, Drive/public bytes, checksum, signer/version/code/package, Stable/main unchanged.
6. Ghi `ops/beta77-release-result.json`, cập nhật `CURRENT_STATE.md`, canonical/archive READY sau DoD PASS.

## 8. Blocker
- NONE tại checkpoint này.

## 9. NEXT_ACTION
`FIX_BETA77_PUBLISH_MATERIALIZER_COMPAT_ANCHOR_THEN_PUBLISH_EXACT_BYTES_AND_COMPLETE_OTA_LIVE_READBACK`
