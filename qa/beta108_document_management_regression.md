# Beta108 — DOCUMENT-MANAGEMENT-001 regression

Status: TECHNICAL_PASS_AWAITING_OWNER  
Version: 0.4.2-beta.108 / versionCode 114  
Source: 378f1c294641c774cee361ae2bd2cc9fc868ee23  
Exact APK SHA256: bd82ca39ca702a771b435ef67ab626cbc36e9771478981912fa20e588bb9bc6e

## Rule được khóa
- Chụp ảnh trực tiếp hoặc chọn ảnh có sẵn, chọn loại biên bản, tối ưu ảnh trước upload.
- Ảnh upload trực tiếp Google Drive; Service/D1 chỉ lưu metadata/hash/audit, không lưu blob ảnh.
- Exact duplicate phải bị chặn; near-duplicate phải cảnh báo.
- Pending upload phải bền vững qua restart/login/network và retry có account fence.
- Media cache phải có giới hạn.
- Sửa loại biên bản = rename toàn bộ metadata lịch sử + tên file Drive.
- Xóa loại biên bản = hard delete file Drive + dữ liệu nghiệp vụ + danh mục; chỉ giữ receipt kỹ thuật tối thiểu.
- Sửa/Xóa dùng mã xác nhận canonical HHmm giờ Việt Nam ±2 phút; SUPERADMIN giữ re-auth hiện hành.
- Category mutation phải durable/checkpoint/idempotent; upload mới bị fence khi mutation đang chạy.
- Beta/Stable không được cross-write.

## Regression bắt buộc
- drive_direct_upload
- no_d1_blob
- exact_duplicate_block
- perceptual_duplicate_warning
- durable_pending_queue
- post_drive_completion_resume
- bounded_media_cache
- account_scoped_retry
- category_rename_all_metadata
- category_rename_all_drive_files
- category_hard_delete_drive_and_records
- category_mutation_durable_resume
- category_mutation_confirmation_hhmm
- beta_stable_isolation

## Evidence PASS
- Contract/service live: run 33497121749 / artifact 9796321745.
- Visual + direct PDA + API36: run 33497121749 / artifact 9796518681; 39 screenshots; human visual PASS ở 320x568, 360x640, 480x800.
- Fast Check full app: run 33498475427 PASS.
- Exact device stale-discovery regression: run 33498411807 / artifact 9796733630 PASS.
- Runtime DoD: run 33498657720 / artifact 9796803109 PASS.
- Terminal publish/OTA/install/readback/finalize: run 33499528769 PASS.
- Publish artifact 9797165484; PDA artifact 9797234412; final artifact 9797240852.
- OTA 0.4.2-beta.106 → 0.4.2-beta.108 exact SHA/size/version/package/signer + install/open PASS.
- Stable/main/signer/authority unchanged.

## OWNER acceptance
Chưa nghiệm thu. Chỉ chuyển invariant sang ACTIVE_PASS khi OWNER xác nhận OK.
