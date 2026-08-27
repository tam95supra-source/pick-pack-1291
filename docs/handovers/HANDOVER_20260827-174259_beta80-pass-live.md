# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time: 2026-08-27T17:42:58+0700
- owner: Nguyễn Văn Tâm
- branch: feature/beta78-old-session-outbound-service-20260826
- working_head_sha: 7082f547ca9f4ca3de0cd0d7cdef5e253d4e6e2b
- archive_file: docs/handovers/HANDOVER_20260827-174259_beta80-pass-live.md

## Mục tiêu + DoD
Hoàn tất Beta80 bằng exact locked APK; OTA cài thật; FileProvider/PackageInstaller PASS; chuỗi Vào ca -> mở đúng session_id -> Sửa -> Bắn ra không NOT_FOUND; Stable/main/signer/authority không đổi; receipt terminal thật.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.80 / versionCode 86.
- TARGET: PASS/LIVE hoàn tất.
- CANDIDATE LOCKED: artifact 9629377960; source 38d6f08aa63600f4ef09fd524428beccebc4bb6f; SHA256 1210bf57ff3bb48a723aa40d2efc8ec922c5e632e4c1d9928bf4dbe843654a69; size 13196221; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Stable: unchanged.
- main: a8c0c0d92522c7173230d4175b4f0d3a4906c8bb unchanged.
- authority: SERVICE_PRIMARY / PRODUCTION / epoch 9 / generation m2-prod-reset-20260823-001 unchanged.

## Evidence / locked identity
- Terminal workflow run: 33063954273.
- pda-verify job: 98489333249 SUCCESS.
- Exact OTA download + Android PackageInstaller + FileProvider self-update: PASS.
- Historical session: business_date 2026-08-26; exact session_id f11e44fb-b7ca-4603-8cd4-d9af6836b9ca; edit + exit; final D1 state ENDED; NOT_FOUND=false; wrong_session=false.
- Final receipt artifact: beta80-final-33063954273 / pda-receipt.json.

## File / commit đã đổi
- .github/workflows/beta-release.yml: fixture dùng live Service challenge/login; finalize needs pda-verify.
- CURRENT_STATE.md và handoff canonical/archive do finalize sinh sau PASS.

## Lỗi + root cause + đường PASS / cấm lặp
- Run 33045490625 / job 98428394466: ATTENDANCE_ENTER_V2_FAILED:401:SERVICE_SESSION_UNAVAILABLE.
- Root cause: fixture tự ký bearer bằng secret suy diễn không phải live Service token; APK không lỗi.
- PASS: tạo verifier hợp lệ, gọi live /v1/auth/challenge + /v1/auth/login để nhận bearer thật; giữ exact Beta80.
- Cấm lặp: không tự suy diễn SERVICE_TOKEN_SECRET; không rebuild/resign APK để sửa lỗi harness auth.

## Workspace / CI / external state
- Exact APK/build/visual/Service/publish bytes không đổi.
- Beta OTA readback PASS; Stable/main/authority unchanged.
- Fixture D1 được cleanup sau gate.

## Việc còn lại
Không còn việc trong scope Beta80.

## Blocker / quyền
Không có blocker OWNER.

## Invariants
Không đổi Stable/main/signer/authority; publish dùng exact bytes; không thêm backend/provider/authority.

## NEXT_ACTION
WAIT_FOR_OWNER_NEW_SCOPE
