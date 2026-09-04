# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-04T08:21:17Z
- owner: Nguyễn Văn Tâm
- branch: beta/current
- live_release_branch: release/beta118-owner-realtime-bulk-exit-20260904
- release_trigger_sha: 7b8335c223243abd4948eb1923d06bcd085e88e1
- archive_file: docs/handovers/HANDOVER_20260904-082117_owner-current-auth-acceptance-security.md

## LIVE public hiện hành
- LIVE BETA: 0.4.2-beta.118 / versionCode 124 / package vn.pickpack1291.app.beta.publicbeta.
- Exact LIVE source: 81944b8519cfb7995d78a5c1070c4af3ee2150be.
- Candidate: 33833810807 / 9922669910.
- Verify visual/PDA: 33835144144 / 9923142675 PASS; human visual PASS 320x568 / 360x640 / 480x800.
- Terminal release: 33842367960 PASS.
- APK SHA256: 5216f0eb09f187aed9cb71dcc21cd145fdc3ba7ea7852c74ffe6f85dea2b478f / size 14429173.
- Signer: d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- OTA: GitHub Release exact bytes PASS.
- Stable/main/signer/authority: unchanged.

## OWNER scope mới — 2026-09-04
Scope ID: `OWNER_20260904_CURRENT_AUTH_ACCEPTANCE_SECURITY`.
Status: `LOCKED_REQUIREMENT_PENDING_FIX`.
Canonical machine ledger: `ops/owner-acceptance-current.json`.
Policy: `docs/CONTROL_PLANE_AUTH_SECURITY_POLICY.md`.

### 1. beta/current phải luôn là Beta public mới nhất
Root cause đã xác minh: Beta release finalizer chỉ commit/push CURRENT_STATE/HANDOVER về release branch, không advance default branch `beta/current`. Vì vậy Beta117/Beta118 đã public nhưng `beta/current` vẫn có thể đứng Beta116.

Đã xử lý control-plane:
- fast-forward `beta/current` từ Beta116 lineage lên Beta118 lineage, không force, không mất lịch sử acceptance;
- readback hiện đúng Beta118;
- thêm `.github/workflows/beta-current-sync.yml`: sau Beta release success/PASS_LIVE, chỉ fast-forward `beta/current`, có monotonic Beta fence, same-version divergence fail-closed, race-newer guard và readback CURRENT_STATE + OTA;
- regression contract: `tools/beta_current_sync_contract.py`.

### 2. SUPERADMIN auth
Root cause logout sau update/process restart đã xác minh ở Android hiện hành: `MainActivity.onCreate()` gọi `login()`, và `login()` gọi `api.clearToken()` dù `BetaApiClient` đã có persisted token + `restoredAccount()`. Vì vậy app tự phá session local trước khi có cơ hội restore.

OWNER usability target đã khóa:
- input tối đa 20 ký tự;
- chuỗi có HHmm thực tế trong ±5 phút được chấp nhận theo phương thức thời gian;
- OTP Gmail đúng 8 chữ số ngẫu nhiên, single-use;
- dùng OTP thành công thì consume + phát sinh/gửi OTP kế tiếp;
- login bằng phương thức thời gian không rotate/gửi OTP mới.

Security refinement bắt buộc:
- HHmm ±5 KHÔNG được là universal standalone SUPERADMIN credential vì giờ hiện tại không phải bí mật;
- time-window method chỉ hoạt động trên thiết bị SUPERADMIN đã trusted/bound, xác thực challenge bằng device-bound key; private key ở Android Keystore;
- máy mới/untrusted dùng OTP Gmail;
- validation server-side;
- OTP plaintext chỉ tồn tại tạm thời lúc tạo/gửi; repo/log/artifact/receipt không được chứa;
- verifier OTP dùng protected verifier với server pepper lưu secret store, không bare hash 8-digit OTP.

Android/service auth implementation CHƯA đổi trong scope control-plane hiện tại. Android source đổi tiếp theo phải là Beta119+ và đi đủ release gate.

### 3. Checklist / acceptance realtime chống stale chat
Đã tạo canonical `ops/owner-acceptance-current.json` với:
- monotonic `state_epoch`;
- public Beta identity;
- scope ID;
- checklist ID + revision;
- OWNER responses append-only;
- reject older Beta / lower state_epoch / lower checklist revision;
- OWNER silence != acceptance.

Guard:
- `tools/owner_acceptance_ledger_guard.py` chặn rollback state/checklist và cắt lịch sử OWNER response;
- `.github/workflows/control-plane-security-guard.yml` chạy ledger guard trên push/PR.

Chat/memory/handoff chỉ dùng để tìm authority. Acceptance canonical lấy từ ledger + stable invariant registry.

### 4. Public GitHub secret protection
Repo public. Đã khóa policy cấm plaintext password/OTP/password proof/session token/Gmail OAuth secret/private key/signer/admin credential trong tracked files, Actions logs, artifacts, handoffs, receipts.

Guard:
- `tools/public_repo_secret_guard.py` chặn credential file mới, private key blocks, common token prefixes và plaintext secret assignments trong diff mới;
- `.github/workflows/control-plane-security-guard.yml` chạy fail-closed trên push/PR.

Nếu credential thật từng xuất hiện public GitHub thì xóa ở commit mới không đủ; phải rotate/revoke credential đó.

## Blocker
Không có blocker OWNER ở control-plane. SUPERADMIN auth implementation là công việc kỹ thuật kế tiếp và sẽ tạo Beta119 vì chạm Android source.

## NEXT_ACTION
IMPLEMENT_SUPERADMIN_AUTH_AND_OWNER_ACCEPTANCE_FENCING_WITH_REGRESSION_IN_BETA119
