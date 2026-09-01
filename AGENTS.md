# AGENTS.md — APK PICK PACK 1291

OWNER: Nguyễn Văn Tâm. Làm việc bằng tiếng Việt, ngắn, rõ, evidence-first.

## 1. Branch authority bắt buộc

- `beta/current` = **canonical development + continuity branch** của Beta.
- `main` = **Stable/protected branch**. Không dùng `main` để suy ra Beta LIVE, Beta source hiện tại, handoff hiện tại hoặc trạng thái dự án.
- Mọi feature/release branch mới phải bắt đầu từ `beta/current`, trừ khi OWNER chỉ định khác.
- Sau mỗi checkpoint/handoff kỹ thuật đã PASS và branch là hậu duệ hợp lệ của `beta/current`, finalizer phải fast-forward `beta/current` tới checkpoint đó. Cấm force-update khi lịch sử diverge.
- `main` chỉ được cập nhật trong luồng promotion Stable có lệnh OWNER rõ ràng.
- Cho tới khi repository default branch được đổi sang `beta/current`, mọi phiên phải **explicitly đọc authority từ ref `beta/current`**; không tin default branch.

## 2. Nguồn sự thật

Thứ tự:
1. lệnh OWNER mới nhất;
2. `docs/handovers/HANDOVER_CURRENT.md` trên `beta/current`;
3. archive READY mới nhất nếu canonical lỗi;
4. `CURRENT_STATE.md` trên `beta/current`;
5. live readback;
6. receipt/artifact/hash;
7. lịch sử.

ACTIVE thắng SUPERSEDED. TARGET/CANDIDATE không phải LIVE. Tài liệu lịch sử chỉ là evidence, không tự trở thành authority.

Mỗi phiên mới phải đọc:
- `docs/handovers/HANDOVER_CURRENT.md`
- `docs/REGRESSION_GUARD_POLICY.md`
- `docs/STABLE_INVARIANTS.md`
- `CURRENT_STATE.md`

Chỉ đọc thêm file được handoff/NEXT_ACTION/failure domain dẫn trực tiếp. Không crawl repo.

## 3. Thực thi

Chu trình: `OBSERVE → CHANGE → VERIFY → RECOVER`.

- Sửa nhỏ nhất đúng root cause.
- Deterministic failure: sửa rồi chạy lại impacted gate.
- Transient: retry exact artifact tối đa theo policy; không rebuild.
- Harness failure: sửa harness, không sửa APK để làm test PASS.
- Không dừng ở plan/commit/pending/build/artifact.
- Chỉ final khi Technical DoD PASS, OWNER acceptance hoàn tất, có blocker OWNER thật hoặc bị safety/protected action chặn.

## 4. Kiến trúc

Canonical: Android/Web-PWA ↔ Service ↔ D1; Google Sheets/GAS là replica/fallback/compatibility/DR theo environment contract; local client là projection/offline.

- BETA/STABLE tách environment, audience, app package, account/session, D1, Sheet/GAS, OTA/manifest, LAN/NSD và mutable state.
- Cloud DR có thể dùng các provider đã được OWNER/audit chốt; provider cụ thể phải đọc từ current state/config, không hardcode vào business logic.
- Không Supabase.
- Firebase chỉ được phép cho FCM wake/invalidation; không Firebase Auth/DB/Storage.
- Một official writer, fencing, idempotency, durable outbox, anti-duplicate, audit.
- Stable giữ READY_NOT_LIVE cho tới lệnh promotion riêng.

## 5. Release

### Beta
- Android source đổi → Beta mới, trừ khi OWNER nói chưa build/phát hành.
- Candidate build/sign một lần → service/regression → visual + human → PDA functional → release lock → GitHub Release exact bytes → Beta manifest/OTA → install/readback.
- **APK transport = GITHUB_RELEASE_ONLY. Google Drive APK bị cấm** cho staging/mirror/backup/distribution/rollback.
- Sau lock cấm rebuild/resign.

### Stable
- Chỉ promotion từ **exact Beta source đã OWNER chốt**.
- Stable được build/deploy lại bằng flavor/config/binding Stable riêng; không copy/đổi tên APK Beta.
- Không copy Beta account/session/data/cache/log/queue/outbox sang Stable.
- Web Stable dùng exact accepted Web source với binding/domain Stable riêng.
- Public Stable manifest/OTA/domain/main chỉ được mở trong luồng promotion có OWNER authorization.
- Stable rollback chỉ tác động Stable.

## 6. Regression

Canonical:
- `docs/REGRESSION_GUARD_POLICY.md`
- `docs/STABLE_INVARIANTS.md`
- `qa/stable_invariants.yml`

Không đổi semantics ACTIVE_PASS nếu OWNER chưa chốt. Mọi bugfix phải có regression phù hợp. Trước Beta publish chạy toàn bộ ACTIVE_PASS regression bị tác động.

## 7. Handoff

Protocol: `docs/CHAT_HANDOFF_PROTOCOL.md`.

- Canonical handoff luôn nằm tại `docs/handovers/HANDOVER_CURRENT.md`.
- `docs/HANDOVER_CURRENT.md` là path legacy, không phải authority.
- Mỗi handoff phải có đúng một NEXT_ACTION.
- Nếu checkpoint là canonical continuation mới, cập nhật `beta/current` theo rule mục 1.
- Không rerun gate đã PASS nếu source/input/exact bytes không đổi.
