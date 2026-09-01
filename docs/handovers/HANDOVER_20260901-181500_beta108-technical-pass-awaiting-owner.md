# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- task_state: TECHNICAL_PASS_AWAITING_OWNER
- time_local: 2026-09-01T18:15:00+07:00
- owner: Nguyễn Văn Tâm
- branch: release/beta108-document-management
- archive_file: docs/handovers/HANDOVER_20260901-181500_beta108-technical-pass-awaiting-owner.md

## Trạng thái
- LIVE BETA: 0.4.2-beta.108 / versionCode 114 / package vn.pickpack1291.app.beta.publicbeta.
- DOCUMENT-MANAGEMENT-001: TECHNICAL_PASS_AWAITING_OWNER.
- Stable/main/signer/authority: unchanged.
- Không có blocker kỹ thuật.

## Exact release evidence
- Source: 378f1c294641c774cee361ae2bd2cc9fc868ee23.
- Candidate: run 33491085275 / artifact 9793922815.
- APK SHA256: bd82ca39ca702a771b435ef67ab626cbc36e9771478981912fa20e588bb9bc6e.
- Size: 14150645.
- Signer: d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Service live: 33497121749 / 9796321745 PASS.
- Visual + direct PDA + API36: 33497121749 / 9796518681 PASS; 39 screenshots; human visual PASS 320x568 / 360x640 / 480x800.
- Fast Check full app: 33498475427 PASS.
- Device regression: 33498411807 / 9796733630 PASS.
- Runtime DoD: 33498657720 / 9796803109 PASS.
- Terminal publish/OTA/install/readback/finalize: 33499528769 PASS.
- Publish / PDA / final artifacts: 9797165484 / 9797234412 / 9797240852.
- OTA 0.4.2-beta.106 -> 0.4.2-beta.108 exact bytes + install/open PASS.
- Technical receipt: ops/beta108-technical-pass.json.
- Regression: qa/beta108_document_management_regression.md.

## Document-management semantics chờ OWNER nghiệm thu
1. Chụp ảnh trực tiếp hoặc chọn ảnh trong máy; chọn loại biên bản; ảnh được tối ưu trước upload.
2. Ảnh lưu trực tiếp Google Drive; Service/D1 chỉ lưu metadata/hash/audit, không lưu blob ảnh.
3. Ảnh trùng tuyệt đối bị chặn; ảnh gần giống có cảnh báo trước khi tiếp tục.
4. Pending upload bền vững và tự retry sau restart/login/network; cache ảnh có giới hạn.
5. Sửa loại biên bản đổi tên toàn bộ metadata lịch sử và toàn bộ tên file Drive liên quan.
6. Xóa loại biên bản xóa hẳn file Drive + dữ liệu nghiệp vụ + danh mục; chỉ giữ receipt kỹ thuật tối thiểu.
7. Sửa/Xóa dùng mã xác nhận HHmm giờ Việt Nam ±2 phút; SUPERADMIN giữ re-auth hiện hành.
8. Mutation durable/checkpoint/idempotent, có fence upload trong lúc xử lý; Beta/Stable không cross-write.

## Recovery đã khóa
- Finalize lần đầu fail do git non-fast-forward, không phải lỗi APK/OTA.
- Đã rollback exact Beta106 trước khi sửa harness.
- Đã vá finalizer bằng fetch + source-drift guard + rebase fencing.
- Republish cùng exact Beta108 bytes; OTA/readback/finalize PASS.
- Không rebuild/resign candidate.

## Invariants
- DOCUMENT-MANAGEMENT-001 chưa ACTIVE_PASS cho tới OWNER OK.
- OTA-BETA-001 và SERVICE-DISCOVERY-001 được reverify trên Beta108.
- Các ACTIVE_PASS khác không đổi semantics.

## NEXT_ACTION
OWNER_ACCEPTANCE_DOCUMENT_MANAGEMENT_001
