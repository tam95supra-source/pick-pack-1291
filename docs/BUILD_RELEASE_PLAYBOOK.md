# BUILD / RELEASE PLAYBOOK — APK PICK PACK 1291

Status: ACTIVE / authoritative

## 1. Branch model

- `beta/current`: canonical Beta development + project continuity.
- Feature/release branch phải base từ `beta/current`.
- `main`: Stable/protected; chỉ cập nhật khi OWNER promote Stable.
- Không dùng default branch để suy ra authority; đọc explicit `beta/current` cho tới khi default branch được đổi.

## 2. Nguồn sự thật

OWNER → HANDOVER_CURRENT READY → CURRENT_STATE → live readback → receipt/artifact/hash → lịch sử.

Version, package, run/artifact, domain, service, Sheet/GAS, provider và LIVE state là dữ liệu động; luôn đọc current state/request/readback thay vì hardcode.

## 3. Beta flow

1. Base từ `beta/current`.
2. Map impacted invariants.
3. Sửa source nhỏ nhất.
4. App fast/static + impacted regression.
5. Build/sign candidate đúng một lần.
6. Khóa exact identity: source SHA, versionName, versionCode, package, run/artifact, SHA256, size, signer.
7. Service/regression theo impact.
8. Visual 320×568 / 360×640 / 480×800 + human.
9. PDA functional trên exact candidate trực tiếp.
10. Release lock.
11. Publish exact bytes lên GitHub Release.
12. Beta manifest/OTA → install/readback/finalize.
13. Cập nhật invariants/state/handoff và `beta/current`.

APK Google Drive bị cấm.

## 4. Stable promotion flow

Chỉ chạy sau lệnh OWNER chốt exact Beta.

1. Khóa accepted Beta source/change set và evidence.
2. Promotion dry-run phải PASS.
3. Build Stable từ exact accepted source bằng Stable flavor/config; không dùng lại file APK Beta.
4. Apply schema/config/service/Web changes tương ứng sang Stable; **không copy Beta business data/account/session/cache/log/outbox**.
5. Verify Stable package, signer, service, D1, Sheet/GAS, auth/data isolation, Web/PWA, DR và regression.
6. Stable release lock.
7. Chỉ sau mọi gate PASS mới mở Stable public domain/manifest/OTA.
8. Install/readback Stable.
9. Nếu fail sau publish: rollback Stable riêng.
10. Sau first real Stable release OWNER mới nghiệm thu checklist Beta/Stable đang pending.

## 5. Web

- Beta Web dùng source phát triển trên Beta và binding BETA.
- Stable Web lấy exact accepted Beta Web source nhưng deploy với binding/domain STABLE.
- Cookie/cache/Service Worker phải host/environment scoped.
- Không dùng cùng account/session/data store giữa hai environment.

## 6. Candidate lock và kế thừa PASS

Không rebuild/resign sau lock. Nếu source/input/exact bytes không đổi thì kế thừa gate PASS; chỉ fresh-read external state có thể đổi hoặc trước production write.

## 7. Lỗi

- Deterministic → sửa root cause.
- Transient → retry exact artifact.
- Harness → sửa harness.
- Stable/main drift ngoài lệnh OWNER → dừng production write và recover, không tự promote.

Chi tiết error handling: `docs/AI_EXECUTION_STANDARD.md`.
