# ARCHITECTURE GUARDRAILS — APK PICK PACK 1291

Status: ACTIVE / current architecture policy

## 1. Authority

Current dynamic state phải đọc từ `CURRENT_STATE.md`, `config/environment_contracts.json` và live readback. File này chỉ chứa guardrail ổn định, không chứa version/run/provider endpoint động.

## 2. Mô hình bắt buộc

`Android / Web-PWA ↔ Service Core ↔ D1`

Kèm:
- Durable Objects/WebSocket cho realtime khi cần;
- Google Sheets/GAS cho replica, compatibility, fallback, DR và update discovery theo contract;
- Android local projection/outbox/offline;
- provider-neutral adapters ở business core.

Không Supabase. Firebase chỉ FCM wake/invalidation, không Auth/DB/Storage.

## 3. Beta / Stable

- `beta/current` là canonical development branch.
- `main` là Stable/protected branch; không đại diện Beta hiện tại.
- BETA và STABLE phải tách package, environment/audience, account/session, D1, Sheet/GAS, OTA/manifest, LAN/NSD và mutable state.
- Cross-environment write/fallback/auth/session/manifest/data copy bị cấm.
- Stable giữ `READY_NOT_LIVE` cho tới lệnh promotion OWNER.
- Promotion dùng exact accepted Beta source; chỉ cho phép environment-specific diff.

## 4. Data / writer

- Một official writer tại một thời điểm.
- Mutation phải có canonical event/idempotency/fencing/audit.
- Timeout không chứng minh writer chưa commit.
- Legacy/cache/fallback không được tự quyết business rule.
- D1 + outbox phải hội tụ deterministic; reconcile không được tạo duplicate.

## 5. Backup / DR

- Replica/fallback/retention không tự được coi là backup.
- Backup chỉ PASS sau restore thử + compare/checksum.
- DR credentials/state phải environment-scoped.
- Cross-token/cross-restore phải fail closed.
- Provider/account-wide outage có thể vẫn là common-mode availability risk; không được tuyên bố cô lập tuyệt đối nếu provider không hỗ trợ hard isolation.
- Free-first, không tự phát sinh chi phí; quota/circuit-breaker/kill-switch phải theo canonical config.

## 6. Release

- Beta APK: GitHub Release exact bytes only; Google Drive APK forbidden.
- Candidate lock gồm source SHA, run/artifact, version/code/package, SHA256, size, signer.
- Visual thật: 320×568, 360×640, 480×800 + human inspection.
- PDA functional dùng exact candidate trực tiếp trước OTA.
- Sau lock cấm rebuild/resign.
- Stable publish/main/signer/authority chỉ đổi khi OWNER authorization rõ ràng.
- Post-publish Stable failure rollback Stable riêng; không tác động Beta.

## 7. Secrets

Secret/token/password/signer chỉ ở secret store phù hợp. Không plaintext trong repo, Sheet, log, backup hoặc handoff.
