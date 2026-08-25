---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-08-25T17:30:00+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: release/beta71-clean-from-beta68-20260825
working_head_sha: 7ced825ed84158ddd16367ca1943556b718c4fd5
archive_file: docs/handovers/HANDOVER_20260825-173000_beta73-ota-live-pass.md
base_or_live_version: 0.4.2-beta.73
target_version: 0.4.2-beta.73
task_state: PASS
next_action: WAIT_FOR_OWNER_NEW_SCOPE
---

# BÀN GIAO PHIÊN — BETA73 OTA LIVE PASS

## 1. Yêu cầu OWNER và Definition of Done
- Scope OWNER: hoàn tất Beta73 bằng exact candidate đã khóa; không rebuild/resign/version bump/Beta74; không quay lại visual sau HUMAN PASS; chỉ publish kênh BETA.
- DoD: Settings human visual PASS `320x568`, `360x640`, `480x800`; publish chính exact artifact; OTA/Drive/LIVE readback đúng URL/SHA256/size/versionName/versionCode/package/signer; Stable/main/signer/authority không đổi; cập nhật CURRENT_STATE và handoff READY.
- Kết quả: **PASS toàn bộ**.

## 2. Trạng thái canonical hiện tại
### LIVE
- Beta: `0.4.2-beta.73`, versionCode `79` — **OTA LIVE PASS**.
- Package: `vn.pickpack1291.app.beta.publicbeta`.
- Android source SHA: `2d726828bdd83efe21e9cd41db8d5c06d16f5272`.
- APK SHA256: `ad037c1a17d245f90ead59539c5595cc5df6a568b8657ce636cc43d101175fd2`.
- Size: `13130629` bytes.
- Signer SHA256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Drive APK ID: `1YbOScnsvPH4mQbyekKQc-EzlF1glG9be`.
- Drive checksum ID: `1n6n40syMn3eHiJtcJojr6_FBokF4V9jR`.
- OTA URL: `https://drive.usercontent.google.com/download?id=1YbOScnsvPH4mQbyekKQc-EzlF1glG9be&export=download&confirm=t`.

### TARGET / CANDIDATE
- TARGET Beta73 đã trở thành LIVE; không còn candidate pending.
- Locked candidate build run/artifact: `32820317675` / `9552942024`.
- Candidate identity đúng tuyệt đối với LIVE bytes ở trên.
- Stable: `0.1.0-stable`, code `1`, publish **FORBIDDEN**.
- `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`, fresh-read unchanged.
- Worker/Service: **không deploy**, authority change `NONE`.

## 3. Việc đã hoàn tất
| Hạng mục | Trạng thái | Evidence |
|---|---|---|
| Exact candidate lock | PASS | run `32820317675`, artifact `9552942024`, SHA/size/signer ở mục 2 |
| Settings visual automation | PASS | final run `32834871019`, artifact `9558250565` |
| Human visual matrix | PASS | `ops/beta73-visual-inspection.json`, receipt commit `60792ff27b4aa2f741318a7f65280ccd1f6c1890`; 320/360/480 đều đúng Settings, có `ĐỔI MẬT KHẨU` và `NHẬT KÝ`, không wrong-screen/crop/overflow |
| Exact publish | PASS | release run `32837337470` |
| Release evidence | PASS | artifact `9559169643`, digest `sha256:aedad6392dd2108db5a46b864a8d01614c586808230417d9393c2dffab004a70` |
| OTA receipt | PASS | `ops/beta73-release-result.json`, blob `b051a997eac482ca2a5c305a4fd9ea09c6931479` |
| Drive readback | PASS | file `1YbOScnsvPH4mQbyekKQc-EzlF1glG9be`, name `pick-pack-1291-public-beta-0.4.2-beta.73.apk`, size `13130629`, anyone-reader; downloaded bytes SHA exact |
| OTA readback | PASS | Beta72 client: available Beta73/code79/SHA/size exact; Beta73 client: available=false, version Beta73/code79 |
| Forgot-password preview | PASS | live GAS readback `{ok:true, login_id, email_field_present:true}`; không lưu email nhạy cảm |
| Stable isolation | PASS | stable-before/stable-after giống nhau trên contract kiểm tra; `available=false`, `reason=NO_APK` |
| main isolation | PASS | fresh-read `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb` |
| CURRENT_STATE | PASS | commit `7ced825ed84158ddd16367ca1943556b718c4fd5` ghi Beta73 OTA LIVE PASS |

## 4. Thay đổi trong phiên
- Android source Beta73 đã được materialize trước candidate lock; **không sửa Android source sau lock**.
- `tools/run_beta73_visual.py`: harness Settings chuyển khỏi UiAutomation sang direct route + dumpsys + ảnh thật; sau đó capture từng bước scroll để human chọn frame đúng.
- `ops/beta73-visual-inspection.json`: receipt HUMAN PASS.
- `tools/publish_beta73_ota.sh`: publisher exact bytes; fresh-read GAS, temporary transport route, rollback bảo vệ, Drive/OTA/live verification.
- `.github/workflows/beta-release.yml`: fixed workflow chuyển sang publish-only, không build/sign/visual.
- `ops/beta-release-request.json`: stage `publish` exact lock.
- `ops/beta73-release-result.json`: release PASS receipt do run `32837337470` push.
- `CURRENT_STATE.md`: Beta73 OTA LIVE PASS commit `7ced825ed84158ddd16367ca1943556b718c4fd5`.
- Production LIVE thay đổi: Beta channel từ Beta72 → Beta73; GAS giữ approved `forgot_password_preview` và OTA versionCode compatibility; temporary exact-upload route đã loại bỏ.
- Stable/main/signer/Worker authority không đổi.

## 5. Lỗi đã gặp và đường PASS
| Fingerprint | Root cause | Cách PASS đã biết | Cách cấm lặp |
|---|---|---|---|
| Settings visual treo ~60 phút | API29 `Instrumentation/UiAutomation` treo trước accessibility tree | OWNER phê duyệt gate `am start -W` + `dumpsys activity/window` + real PNG + human inspection | Không dùng lại UiAutomation/uiautomator cho Settings API29 |
| Visual ảnh lower sai framing | Swipe cố định làm `NHẬT KÝ` bị khuất ở một số size | Chụp từng bước scroll 1–4; human chọn `scroll-2` | Không thử mù cùng tọa độ / không tin automation thay human pixels |
| Publish preflight không đọc receipt commit | checkout depth 1 không chứa commit `60792ff...` | fetch exact receipt commit trước `git rev-parse` | Không giả định shallow checkout có historical receipt |
| Publisher dừng trên Beta72 `version_code` | Live OTA Beta72 hợp lệ nhưng contract cũ không có field `version_code` | verifier chấp nhận absent previous code; Beta73 GAS compat shim trả code 79 | Verifier phải theo contract LIVE, không ép field legacy không tồn tại |
| Publisher materialization SyntaxError | nested triple quote trong harness runtime patch | sửa quote/materialization và `bash -n` preflight trước publish | Syntax/materialization fail không được đi tới production write |

## 6. Trạng thái workspace/CI/external
- Branch: `release/beta71-clean-from-beta68-20260825`.
- Working head công việc trước handoff: `7ced825ed84158ddd16367ca1943556b718c4fd5`.
- Publish run cuối: `32837337470` — SUCCESS.
- Không còn workflow/candidate/publish pending cần theo dõi.
- Fresh Drive: file Beta73 đúng tên/size/parent Beta folder/public-reader; raw download hash exact candidate.
- Fresh main: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb` unchanged.
- Stable feed unchanged.
- Worker/Service deploy: NONE.
- GAS: `forgot_password_preview` live PASS; OTA Beta73 versionCode 79 readback PASS; temporary transport helper absent sau publish.

## 7. Việc còn lại
- **NONE — Beta73 OTA DoD đã PASS toàn bộ.**
- Không housekeeping nào được phép tự phát sinh ngoài retention handoff.

## 8. NEXT_ACTION — điểm tiếp tục chính xác
`WAIT_FOR_OWNER_NEW_SCOPE`

Phiên mới đọc canonical READY này; nếu OWNER chưa có scope mới thì chỉ xác nhận đã nạp trạng thái và chờ lệnh, không tự chạy gate/release/test lại.

## 9. Blocker và quyền
- **NONE — không thiếu quyền/MFA/approval.**
- Quyền publish Beta đã được OWNER cấp và đã sử dụng thành công.

## 10. Invariants không được phá
- Beta73 exact LIVE bytes khóa tại SHA256 `ad037c1a17d245f90ead59539c5595cc5df6a568b8657ce636cc43d101175fd2`, size `13130629`.
- Không rebuild/resign lại Beta73 chỉ để kiểm tra.
- Không tạo Beta74 nếu OWNER chưa có Android source scope mới.
- Stable/main/signer/authority/provider không đổi nếu OWNER chưa explicit.
- Worker không deploy mù khi source repo chưa chứng minh khớp LIVE v64.
- Không dùng lại Settings UiAutomation gate API29 đã deterministic hang.
- Tin candidate/visual/release PASS khi source/input/bytes không đổi; chỉ fresh-read external state khi có lý do hợp lệ.

## 11. Resume contract
- Phiên mới đọc `docs/handovers/HANDOVER_CURRENT.md` trước, rồi `AGENTS.md` nếu có scope mới.
- Có thể tin trực tiếp run/artifact/SHA/size/signer/visual/release receipts ở trên khi bytes/source không đổi; không rerun.
- LIVE canonical hiện là Beta73; Beta72 là SUPERSEDED historical release.
- Nếu external state cần ghi production mới, fresh-read ngay trước write.

## 12. Retention/restore
- Archive mới: `HANDOVER_20260825-173000_beta73-ota-live-pass.md`.
- 5 archive timestamp-v2 active sau bản này: `104218`, `124600`, `160052`, `163400`, `173000`; chưa cần prune.
- Legacy `HANDOVER_20260825-1028_beta71-live-context-bootstrap.md` không khớp mẫu `YYYYMMDD-HHmmss`, không tính retention v2.
- Restore archive cũ qua Git history; cấm rewrite history.
