---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-08-25T19:02:49+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: release/beta71-clean-from-beta68-20260825
working_head_sha: 2dff582273f0fdba9c650a7999fe5192b73565b0
archive_file: docs/handovers/HANDOVER_20260825-190249_beta74-ota-live-pass.md
base_or_live_version: 0.4.2-beta.74
target_version: 0.4.2-beta.74
task_state: PASS
next_action: WAIT_FOR_OWNER_NEW_SCOPE
---

# BÀN GIAO PHIÊN — BETA74 OTA LIVE PASS

## 1. Yêu cầu OWNER và Definition of Done
- Scope cuối của OWNER: chốt Beta74 OTA từ exact candidate đã khóa; request đã ở `stage: publish`; không trigger duplicate khi publish run còn tồn tại; không rebuild/resign/version bump, không chạy lại visual, không sửa Android source, không đổi Stable/main/signer/authority.
- DoD bắt buộc: exact publish PASS → OTA/Drive/LIVE readback khớp version/code/package/SHA/size/signer → Beta73 client thấy Beta74 `available=true` → Beta74 client không thấy bản mới hơn → Stable/main/signer/authority unchanged → release receipt + `CURRENT_STATE.md` + handoff READY.
- Kết quả: **PASS toàn bộ**.

## 2. Trạng thái canonical hiện tại
### LIVE
- Beta: `0.4.2-beta.74`, versionCode `80` — **OTA LIVE PASS**.
- Package: `vn.pickpack1291.app.beta.publicbeta`.
- Android source SHA: `cfb4dbca116f7c47a598bc398bdbe1251ad2bad8`.
- Candidate run/artifact: `32842363597` / `9561088652`.
- APK SHA256: `37cadd74088179f1e17872c7474622681941cc5f546807cea769517d9f98b017`.
- Size: `13130629` bytes.
- Signer SHA256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Visual artifact: `9561153695`; receipt commit `fe0582614804ef767732ddd7ddfa779aecb48c8a`; HUMAN PASS đủ `320x568`, `360x640`, `480x800`.
- Final publish run: `32845025048` — SUCCESS.
- Release evidence artifact: `9561988451`; digest `sha256:0e6c98e20b3a0dcd9f321d3f560e454fd0a519afb1433a655bf8a48bbbcc67b6`.
- Release receipt: `ops/beta74-release-result.json`, commit `b304733bb03c42e1cdeeffddaa2fcdab394524fb`, verdict `PASS`.
- Drive APK ID: `1Dq3uLxBRYWOa5ImYu8BX2VngC1ccoqkr`.
- Drive checksum ID: `1uXauZVKSJdO71N88FfZT39Pgght5LaNL`.
- OTA URL: `https://drive.usercontent.google.com/download?id=1Dq3uLxBRYWOa5ImYu8BX2VngC1ccoqkr&export=download&confirm=t`.
- Fresh Drive readback: file `pick-pack-1291-public-beta-0.4.2-beta.74.apk`, MIME APK, size `13130629`; authenticated Drive download SHA256 exact `37cadd74088179f1e17872c7474622681941cc5f546807cea769517d9f98b017`.
- OTA readback từ final publisher: Beta73 client `available=true`, version `0.4.2-beta.74`, code `80`, SHA/size/URL exact; Beta74 client `available=false`, version `0.4.2-beta.74`, code `80`.

### SUPERSEDED
- Beta73: **SUPERSEDED by Beta74**.
- Beta73 previous SHA256: `ad037c1a17d245f90ead59539c5595cc5df6a568b8657ce636cc43d101175fd2`.

### LOCKED / UNCHANGED
- Stable: `0.1.0-stable`, versionCode `1`; publish **FORBIDDEN**; final publisher so sánh feed trước/sau giống nhau (`available=false`, `reason=NO_APK`).
- `main`: fresh-read sau publish `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`, unchanged.
- Signer unchanged: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Worker/Service change: `NONE`.
- Authority change: `NONE`.
- GAS production change: `OTA_VERSION_COMPAT_BETA74` only; temporary exact-Drive upload helper đã bị loại bỏ; forgot-password preview hiện hữu được giữ nguyên.
- Architecture/provider unchanged: Android/Web-PWA ↔ Cloudflare Worker ↔ D1; GAS/GSheet fallback/replica/OTA theo canonical; không thêm provider/authority.

## 3. Việc đã hoàn tất
| Hạng mục | Trạng thái | Evidence |
|---|---|---|
| Android Beta74 source fix | PASS | source `cfb4dbca116f7c47a598bc398bdbe1251ad2bad8` |
| Candidate build/sign exact | PASS | run `32842363597`, artifact `9561088652`, SHA/size/signer ở mục 2 |
| Human visual matrix | PASS | artifact `9561153695`, receipt `fe0582614804ef767732ddd7ddfa779aecb48c8a`, 320/360/480 PASS |
| Original publish-run identification | PASS | run `32843213718`, request publish exact lock; candidate/visual stages skipped |
| Retry budget trên original publish job | EXHAUSTED / SUPERSEDED | attempts 1–3 đều cùng `drive-transport: UNAUTHORIZED`; evidence artifacts `9561315359`, `9561750118`, `9561853459` |
| Harness root-cause fix | PASS | commit `489a6a69f1eba6357b50001bf384adc79142466b`: giữ original publisher exact, chỉ khôi phục GAS propagation windows 6/8 |
| Fixed publish-only workflow | PASS | commit `36289583f9b5d6ab6f1803fef614d0b0c5a6d4c1`; không build/sign/visual |
| Exact publish | PASS | run `32845025048` SUCCESS |
| Release receipt | PASS | `ops/beta74-release-result.json`, commit `b304733bb03c42e1cdeeffddaa2fcdab394524fb` |
| Drive exact-byte readback | PASS | ID `1Dq3uLxBRYWOa5ImYu8BX2VngC1ccoqkr`, size `13130629`, SHA exact |
| OTA client readbacks | PASS | Beta73→Beta74 available; Beta74→no newer; code80/SHA/size exact |
| Stable isolation | PASS | Stable before/after unchanged |
| main isolation | PASS | fresh-read `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb` |
| CURRENT_STATE | PASS | commit `2dff582273f0fdba9c650a7999fe5192b73565b0` ghi Beta74 OTA LIVE PASS và Beta73 SUPERSEDED |

## 4. Thay đổi trong phiên
- `app/build.gradle.kts`, `OperationsActivity.kt`, `PdaLocalProjection.kt`: source Beta74 tại commit `cfb4dbca116f7c47a598bc398bdbe1251ad2bad8`; sau candidate lock không sửa Android source.
- `ops/beta74-visual-inspection.json`: HUMAN visual receipt commit `fe0582614804ef767732ddd7ddfa779aecb48c8a`.
- `tools/publish_beta74_ota.sh`: original exact publisher commit `65e243b89af2df891a4f45f30f491073a8e5b3a4`; harness recovery commit `489a6a69f1eba6357b50001bf384adc79142466b` chỉ thay propagation window khi materialize publisher gốc từ exact SHA `85b58348209e97c93957d45275a2fc031c764d48`.
- `.github/workflows/beta-release.yml`: commit `36289583f9b5d6ab6f1803fef614d0b0c5a6d4c1` chuyển fixed workflow sang publish-only exact Beta74; không tạo file workflow mới.
- `ops/beta74-release-result.json`: run `32845025048` push receipt commit `b304733bb03c42e1cdeeffddaa2fcdab394524fb`.
- `CURRENT_STATE.md`: commit `2dff582273f0fdba9c650a7999fe5192b73565b0`.
- Production LIVE thay đổi duy nhất: Beta OTA Beta73 → Beta74; GAS thêm compatibility versionCode Beta74. Stable/main/signer/Worker/Service authority không đổi.

## 5. Lỗi đã gặp và đường PASS
| Fingerprint | Root cause | Cách PASS đã biết | Cách cấm lặp |
|---|---|---|---|
| App báo/hiển thị mismatch dù mutation vừa thành công | Local projection có thể lấy phiên cũ của cùng MNV; UI gọi snapshot khi `session_id` rỗng; identical realtime state dựng lại full tree | Beta74 `preferSession`: ACTIVE/mới nhất; chỉ snapshot khi session ID nonblank; local-pending ưu tiên; render signature bỏ full rebuild nếu dữ liệu không đổi | Không sửa backend/authority cho lỗi UI này; không gọi `session_resource_snapshot` với blank session ID |
| Publish run `32843213718` attempts 1–3 `drive-transport: UNAUTHORIZED` | GAS deployment chưa propagate temporary pre-auth upload route trong window 3 lần; không phải candidate/Drive bytes/signature | Giữ exact artifact; harness dùng đường PASS Beta73: helper propagation 6 lần, OTA propagation 8 lần; final run `32845025048` PASS | Không rerun old 3-attempt publisher; không rebuild/resign/revisual để chữa transport harness |
| Workflow rerun pin old head SHA | GitHub rerun job dùng workflow/script tại original run SHA, nên harness commit mới không áp dụng | Sửa **fixed existing workflow** sang publish-only và trigger bởi workflow-file change, request không đổi; validate exact lock trước write | Không sửa request chỉ để trigger; không tạo candidate/workflow mới |

## 6. Trạng thái workspace/CI/external
- Active branch: `release/beta71-clean-from-beta68-20260825`.
- Working head trước handoff: `2dff582273f0fdba9c650a7999fe5192b73565b0`.
- Final release run: `32845025048` — **SUCCESS**; không workflow release pending cần theo dõi.
- Candidate/visual bytes không đổi từ lock; không rebuild/resign/revisual sau lock.
- Fresh external sau publish: Drive metadata/bytes exact; `main` unchanged; Stable readback trong final publisher unchanged; OTA Beta73/Beta74 readback PASS.
- External authority: receipt `authority_change=NONE`, `service_change=NONE`; GAS change chỉ OTA compat Beta74.
- Local workspace: thao tác qua GitHub/Drive connectors; không có uncommitted local source được dùng làm authority.

## 7. Việc còn lại
- **NONE — Beta74 OTA DoD PASS toàn bộ.**
- Không housekeeping tự phát ngoài retention handoff đã được OWNER duyệt.

## 8. NEXT_ACTION — điểm tiếp tục chính xác
`WAIT_FOR_OWNER_NEW_SCOPE`

## 9. Blocker và quyền
- **NONE** — không thiếu quyền/MFA/approval cho scope Beta74 đã hoàn tất.

## 10. Invariants không được phá
- Không rebuild/resign/revisual Beta74 đã LIVE chỉ để kiểm tra lại khi bytes/input không đổi.
- Không đổi Stable/main/signer/authority/provider nếu OWNER chưa yêu cầu.
- Beta74 exact LIVE identity phải giữ version/code/package/SHA/size/signer/Drive IDs ở mục 2.
- Beta73 là SUPERSEDED, không promote ngược hoặc dùng lại làm LIVE nếu OWNER không ra lệnh restore cụ thể.
- Tin các PASS/run/artifact/hash/version/evidence ở handoff này khi source/artifact bytes không đổi; chỉ fresh-read external state có thể đổi trước production write tương lai.

## 11. Resume contract
- Phiên mới đọc `docs/handovers/HANDOVER_CURRENT.md` trước và coi file này là canonical READY.
- Nếu OWNER đưa scope mới: nạp trạng thái trên, đọc `AGENTS.md`, rồi chỉ đọc file/NEXT_ACTION liên quan failure domain; không crawl repo và không rerun gate đã PASS.
- Nếu OWNER chưa có scope mới: vì `task_state: PASS` và NEXT_ACTION là `WAIT_FOR_OWNER_NEW_SCOPE`, chỉ xác nhận đã nạp snapshot và chờ.

## 12. Retention/restore
- Sau archive này, giữ 5 timestamp archive mới nhất trong active tree.
- Prune theo retention OWNER đã duyệt: `HANDOVER_20260825-1028_beta71-live-context-bootstrap.md` và `HANDOVER_20260825-124600_beta72-live-pass.md` (hai bản cũ nhất vượt giới hạn).
- 5 archive giữ lại: `HANDOVER_20260825-160052_beta73-visual-retry-cap-blocked.md`, `HANDOVER_20260825-163400_beta73-uiautomation-bridge-blocked.md`, `HANDOVER_20260825-173000_beta73-ota-live-pass.md`, `HANDOVER_20260825-174900_beta73-live-pass-session-transfer.md`, `HANDOVER_20260825-190249_beta74-ota-live-pass.md`.
- Bản đã prune vẫn restore được qua Git history; cấm rewrite history.
