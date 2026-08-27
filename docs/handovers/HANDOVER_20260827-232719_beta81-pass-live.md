# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time: 2026-08-27T23:27:19+0700
- owner: Nguyễn Văn Tâm
- branch: feature/beta78-old-session-outbound-service-20260826
- working_head_sha: 8780c83cc7d9b0d32531bb35dbcd4beb772357bc
- archive_file: docs/handovers/HANDOVER_20260827-232719_beta81-pass-live.md

## Mục tiêu + DoD
Hoàn tất Beta81 bằng exact candidate 9646920908: OTA LIVE, hash/size/signer khớp, ba lỗi Beta81 PASS trên bản cài từ OTA; Stable/main/signer/authority không đổi.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.81 / versionCode 87.
- TARGET: PASS/LIVE hoàn tất.
- CANDIDATE LOCKED: run 33073351925; artifact 9646920908; source 963ed28a90d2bb3e4a950ae8100fef15edfa86c5; SHA256 f796bf8db5ec4575bb9d6d0880650c49abc682fe07c68aed916270f2afea3789; size 13196221; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Visual: artifact 9647045177 PASS.
- Service evidence: artifact 9646805806 PASS.
- Stable: unchanged.
- main: 021dac5c6932b3ac5c60ce8fdba562ddf3d9688f; only OWNER-approved .github/workflows/beta-release.yml change from pre-publish main, unchanged during recovery.
- authority: SERVICE_PRIMARY / PRODUCTION / epoch 9 / generation m2-prod-reset-20260823-001 unchanged.

## Evidence / locked identity
- Terminal workflow run: 33093042245.
- pda-verify job: 98590681116 SUCCESS.
- Exact OTA from Beta80 -> Beta81 + Android PackageInstaller: PASS.
- Installed base APK SHA/size/signer equals exact candidate: PASS.
- Rà soát chỉ tính RA khi ENDED + exit_at, Ca 2 1/0 cảnh báo: PASS.
- QR nhân viên có rà soát ngày hiện tại + cảnh báo phiên cũ: PASS.
- Qua 24:00 giữ prior-day ACTIVE và khóa PDA/User không giải phóng nhầm: PASS.
- Final receipt artifact: beta81-final-33093042245.

## File / commit đã đổi
- .github/workflows/beta-release.yml: Beta81 exact publish/device gates + always() TXT finalizer.
- tools/publish_beta81_ota.sh, tools/build_beta81_verify_harness.sh, tools/Beta81LocalChecksInstrumentation.java, tools/beta81_pda_device_gate.sh: release/harness only.
- ops/beta-release-request.json, CURRENT_STATE.md và handoff canonical/archive do finalize cập nhật.
- Không rebuild/resign candidate Beta81.

## Lỗi + root cause + đường PASS / cấm lặp
- Hai run 33076098876 và 33076266568 không tạo job vì workflow YAML heredoc/validation; không tác động APK/OTA.
- Đường PASS: đưa logic lớn ra tools, workflow tối giản; exact candidate giữ nguyên.
- Cấm lặp candidate/visual/service run 33073351925 khi source/artifact không đổi.

## Workspace / CI / external state
- Beta81 OTA readback PASS; Stable/main/authority unchanged.
- Exact candidate bytes giữ nguyên từ artifact 9646920908.

## Việc còn lại
Không còn việc trong scope Beta81.

## Blocker / quyền
Không có blocker OWNER.

## Invariants
Không đổi Stable/main/signer/authority; không rebuild/resign exact candidate; không thêm backend/provider/authority.

## NEXT_ACTION
WAIT_FOR_OWNER_NEW_SCOPE
