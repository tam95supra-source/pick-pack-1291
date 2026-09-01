---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-09-01T13:11:24+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: beta/current
working_head_sha: c4e7fba630f33b698b53078245d1f3800d6c595f
archive_file: docs/handovers/HANDOVER_20260901-131124_beta106-technical-pass-awaiting-owner.md
base_or_live_version: 0.4.2-beta.106
task_state: PASS
next_action: WAIT_FOR_OWNER_BETA106_ACCEPTANCE
---

# BÀN GIAO PHIÊN

## 1. Yêu cầu OWNER và Definition of Done
- Hoàn tất scope danh sách nhân sự theo ca + QR tải ứng dụng, sửa mọi lỗi phát hiện, build/release Beta và chỉ dừng khi toàn bộ Technical DoD PASS.
- DoD kỹ thuật đã PASS. OWNER chưa nghiệm thu scope Beta106; không tự chuyển invariant mới sang ACTIVE_PASS.

## 2. Trạng thái canonical hiện tại
- Beta LIVE: 0.4.2-beta.106 / versionCode 112 / package `vn.pickpack1291.app.beta.publicbeta`.
- Product source: `57e02d45b436c6bcb64bc5731671044af7c7c86d`.
- Exact APK: SHA256 `ea5bdf9696d9dae77f02fab815df6435a8317a66178bdb4c36bc051aa5bcd000` / size 14068725 / signer `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Canonical continuity: `beta/current`.
- Stable: unchanged / READY_NOT_LIVE / public=false / manifest=false / OTA=false.
- main unchanged: `021dac5c6932b3ac5c60ce8fdba562ddf3d9688f`.
- Authority unchanged: SERVICE_PRIMARY / PRODUCTION / epoch 9 / generation m2-prod-reset-20260823-001.

## 3. Việc đã hoàn tất
| Hạng mục | Trạng thái | Evidence |
|---|---|---|
| Beta106 candidate build/sign | PASS | run 33473965249 / artifact 9787581956 |
| Visual + PDA pre-OTA + API36 | PASS | run 33473965249 / artifact 9787692571 |
| Human visual 320x568 / 360x640 / 480x800 | PASS | 36 screenshots / ops/beta106-human-visual-receipt.json |
| Fast Check final | PASS | run 33476011598 |
| Exact device regression | PASS | run 33474768649 / artifact 9787794484 |
| Runtime DoD | PASS | run 33475078900 / artifact 9787884925 |
| GitHub Release exact publish | PASS | terminal run 33476108449 / publish artifact 9788246064 |
| OTA Beta104 → Beta106 + install/readback | PASS | run 33476108449 / PDA artifact 9788292824 |
| Finalize canonical release | PASS | run 33476108449 / final artifact 9788296923 |
| Handoff finalizer | PASS | artifact 9788299919 |
| Stable/main/signer/authority unchanged | PASS | terminal readback 33476108449 |

## 4. Thay đổi trong phiên
- `OperationsActivity.kt`: chuẩn hóa JSON null/chuỗi "null" ở supplier/master; NCC thiếu hiển thị `Chưa xác định NCC`.
- Beta version tăng thành 0.4.2-beta.106 / code 112 vì Android source đổi sau candidate Beta105.
- Regression mới: `SHIFT-STAFF-DOWNLOAD-QR-NULL-001` / `qa/beta106_shift_staff_null_regression.md`.
- Harness post-OTA được sửa để chấp nhận cả stale cache được rewrite lúc explicit check hoặc app rewrite sớm khi startup, miễn final cache đúng BETA và không reuse Stable root.
- Runtime verifier được tách khỏi promotion lock lịch sử khi chạy pre-OTA; promotion mode vẫn giữ OWNER lock.
- LIVE production thay đổi duy nhất: Beta manifest/GitHub Release chuyển từ Beta104 sang exact Beta106. Stable/main/authority không đổi.

## 5. Lỗi đã gặp và đường PASS
| Fingerprint | Root cause | Cách PASS đã biết | Cách cấm lặp |
|---|---|---|---|
| Beta105 roster hiển thị `null` | JSONObject.NULL → optString thành literal "null" | sanitize master text; fallback `Chưa xác định NCC` | regression no-visible-null bắt buộc |
| BETA_ACCEPTANCE_LOCK_SOURCE_INVALID | runtime verifier buộc pre-OTA Beta mới khớp historical promotion lock Beta104 | chỉ enforce source/metadata lock trong promotion mode | giữ self-test promotion/pre-OTA |
| Post-publish PDA fail run 33475493287 | harness đòi stale URL phải còn sau khi app đã tự rewrite đúng canonical Beta Service | rollback Beta104 PASS, sửa harness, republish cùng exact bytes | không rebuild APK; kiểm tra final cache semantics thay vì thời điểm rewrite |
| Harness syntax patch tạm lỗi | boolean đặt giữa if/else | sửa cú pháp trước CI; Fast Check 33476011598 PASS | không dùng result trước CI PASS |

## 6. Trạng thái workspace/CI/external
- `beta/current` đã fast-forward non-force tới checkpoint Beta106 PASS/LIVE.
- Terminal release run 33476108449: publish PASS / pda-verify PASS / finalize PASS / rollback skipped.
- Beta manifest hiện tại: 0.4.2-beta.106 qua GitHub Release.
- Stable/main/signer/authority readback giữ nguyên.
- Không có production write đang mơ hồ hoặc run release đang chờ.

## 7. Việc còn lại
- Chỉ còn OWNER nghiệm thu scope Beta106 mới.
- BETA-STABLE-AUDIT-001 và INFRA-RESILIENCE-001 giữ nguyên trạng thái/deferred trước đó; không tự mở lại.
- Stable chưa phát hành; không promotion Stable trong scope này.

## 8. NEXT_ACTION — điểm tiếp tục chính xác
- `WAIT_FOR_OWNER_BETA106_ACCEPTANCE`.
- OWNER nghiệm thu checklist Beta106; nếu mục nào chưa OK thì sửa đúng mục đó và giữ các mục OWNER đã OK.
- Nếu toàn bộ OK: đổi `SHIFT-STAFF-DOWNLOAD-QR-001` từ TECHNICAL_PASS_AWAITING_OWNER → ACTIVE_PASS, cập nhật registry/handoff; không tự phát hành Stable nếu OWNER chưa ra lệnh riêng.

## 9. Blocker và quyền
- NONE — không thiếu quyền/MFA/manual approval ở trạng thái hiện tại.
- OWNER acceptance là gate nghiệp vụ bắt buộc, không phải blocker kỹ thuật.

## 10. Invariants không được phá
- Các invariant ACTIVE_PASS hiện hành giữ nguyên semantics.
- `OTA-BETA-001`: GitHub Release exact bytes only; Google Drive APK FORBIDDEN.
- `SERVICE-DISCOVERY-001`: final cache/routing phải environment-scoped BETA, không reuse Stable root.
- Stable/main/signer/authority không đổi.
- `SHIFT-STAFF-DOWNLOAD-QR-001` hiện TECHNICAL_PASS_AWAITING_OWNER, chưa ACTIVE_PASS.

## 11. Resume contract
- Phiên mới đọc `beta/current:docs/handovers/HANDOVER_CURRENT.md` trước.
- Kế thừa toàn bộ evidence PASS trên nếu exact source/bytes/input không đổi.
- Chỉ fresh-read state có thể thay đổi hoặc ngay trước production write.
- Đúng một resume point: `WAIT_FOR_OWNER_BETA106_ACCEPTANCE`.

## 12. Retention/restore
- Archive mới: `docs/handovers/HANDOVER_20260901-131124_beta106-technical-pass-awaiting-owner.md`.
- Giữ tối đa 5 archive đúng mẫu timestamp theo CHAT_HANDOFF_PROTOCOL; archive cũ quá hạn được prune khỏi active tree, lịch sử Git vẫn phục hồi được.
