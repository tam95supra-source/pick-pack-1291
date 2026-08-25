---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-08-25T17:49:00+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: release/beta71-clean-from-beta68-20260825
working_head_sha: f6f3ffd42ea0486ae4b840b552d5cc6ffc24d76e
archive_file: docs/handovers/HANDOVER_20260825-174900_beta73-live-pass-session-transfer.md
base_or_live_version: 0.4.2-beta.73
target_version: 0.4.2-beta.73
task_state: PASS
next_action: WAIT_FOR_OWNER_NEW_SCOPE
---

# BÀN GIAO PHIÊN — BETA73 OTA LIVE PASS / CHỜ SCOPE MỚI

## 1. Yêu cầu OWNER và Definition of Done
- OWNER yêu cầu chuyển phiên chat sau khi Beta73 đã hoàn tất.
- Trạng thái được bàn giao phải đủ để phiên mới đọc canonical rồi thực thi yêu cầu mới, không rà lại phần đã PASS.
- DoD hiện tại: Beta73 OTA LIVE PASS, Drive/LIVE readback khớp, CURRENT_STATE đã cập nhật, handoff READY.

## 2. Trạng thái canonical hiện tại
### LIVE
- Beta `0.4.2-beta.73`, versionCode `79`, package `vn.pickpack1291.app.beta.publicbeta` — **OTA LIVE PASS**.
- Candidate run/artifact: `32820317675` / `9552942024`.
- APK SHA256: `ad037c1a17d245f90ead59539c5595cc5df6a568b8657ce636cc43d101175fd2`.
- APK size: `13130629` bytes.
- Signer SHA256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Drive APK ID: `1YbOScnsvPH4mQbyekKQc-EzlF1glG9be`; checksum ID: `1n6n40syMn3eHiJtcJojr6_FBokF4V9jR`.
- Release run: `32837337470`; release evidence artifact `9559169643`.
- Visual final run/artifact: `32834871019` / `9558250565`; HUMAN PASS 320x568, 360x640, 480x800.
- Visual receipt: `ops/beta73-visual-inspection.json`, receipt commit `60792ff27b4aa2f741318a7f65280ccd1f6c1890`.
- Release receipt: `ops/beta73-release-result.json`.

### LOCKED / UNCHANGED
- Stable: `0.1.0-stable`, code `1`, không publish.
- `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`, unchanged.
- Signer/authority/provider/Worker không đổi; Worker deploy `NONE`.
- Beta72 là SUPERSEDED; Beta73 là LIVE canonical.

## 3. Việc đã hoàn tất
| Hạng mục | Trạng thái | Evidence |
|---|---|---|
| Exact candidate | PASS | run `32820317675`, artifact `9552942024`, SHA/size/signer ở mục 2 |
| Settings visual matrix | PASS | run `32834871019`, artifact `9558250565`, HUMAN PASS đủ 3 size |
| Publish exact bytes | PASS | run `32837337470` |
| Drive/OTA/LIVE readback | PASS | `ops/beta73-release-result.json`; Drive ID/SHA/size exact |
| Forgot-password preview | PASS | live GAS readback; không lưu email nhạy cảm |
| Stable/main isolation | PASS | Stable unchanged; main SHA unchanged |
| CURRENT_STATE | PASS | ghi Beta73 OTA LIVE PASS |

## 4. Thay đổi trong phiên
- Android source Beta73 không bị sửa sau candidate lock; không rebuild/resign sau lock.
- Visual Settings gate đã chuyển khỏi UiAutomation API29 sang direct route + dumpsys + real PNG + human pixels.
- Publisher dùng exact artifact, Drive BẢN THỬ NGHIỆM và rollback GAS an toàn; temporary upload route đã loại bỏ sau publish.
- `CURRENT_STATE.md` và handoff đã chuyển canonical LIVE từ Beta72 sang Beta73.

## 5. Lỗi đã gặp và đường PASS
| Fingerprint | Root cause | Cách PASS đã biết | Cách cấm lặp |
|---|---|---|---|
| Settings visual treo | API29 UiAutomation/accessibility bridge treo | `am start -W` + `dumpsys activity/window` + PNG thật + human inspection | Không dùng lại UiAutomation/uiautomator cho Settings API29 |
| Lower Settings framing sai | Swipe cố định làm `NHẬT KÝ` khuất | capture từng bước scroll; frame `scroll-2` PASS | Không tin automation nếu ảnh human sai |
| Publish shallow receipt | checkout depth 1 không có historical receipt commit | fetch exact receipt commit trước verify | Không giả định shallow checkout có receipt |
| OTA previous version_code | Beta72 live contract thiếu field code | verifier theo live contract; Beta73 compat trả code79 | Không ép legacy field không tồn tại |
| Publisher materialization syntax | nested quote trong generated harness | syntax/materialization preflight trước production write | Không trigger publish khi generated source chưa compile/syntax PASS |

## 6. Trạng thái workspace/CI/external
- Active continuity branch: `release/beta71-clean-from-beta68-20260825`.
- Working head trước handoff này: `f6f3ffd42ea0486ae4b840b552d5cc6ffc24d76e`.
- Không có build/visual/publish run cần theo dõi; Beta73 đã terminal PASS.
- External fresh-read cuối: Drive Beta73 đúng file/size/public-reader; main unchanged; Stable unchanged.
- Một nhánh `__noop` đã phát sinh ngoài active continuity do thao tác connector trong lúc chuẩn bị handoff; không chứa thay đổi riêng, không thuộc lineage/LIVE và **không được dùng làm base**.

## 7. Việc còn lại
- **NONE trong scope Beta73 — DoD đã PASS.**
- Chờ yêu cầu mới của OWNER; không tự phát sinh test/build/release/cleanup.

## 8. NEXT_ACTION — điểm tiếp tục chính xác
`WAIT_FOR_OWNER_NEW_SCOPE`

Khi OWNER ghi yêu cầu mới: đọc canonical này → `AGENTS.md` → chỉ mở file/failure domain trực tiếp liên quan → thực thi ngay theo scope mới.

## 9. Blocker và quyền
- NONE — không thiếu quyền/MFA/approval cho trạng thái hiện tại.

## 10. Invariants không được phá
- Beta73 LIVE exact bytes khóa tại SHA256 `ad037c1a17d245f90ead59539c5595cc5df6a568b8657ce636cc43d101175fd2`, size `13130629`.
- Không rebuild/resign/rerun visual/release Beta73 khi bytes/source không đổi.
- Không tạo Beta74 nếu OWNER chưa có Android source scope mới.
- Stable/main/signer/authority/provider không đổi nếu OWNER chưa explicit.
- Không dùng nhánh `__noop` làm continuity/base.

## 11. Resume contract
- Phiên mới bắt buộc đọc `docs/handovers/HANDOVER_CURRENT.md` trước.
- Nếu OWNER có yêu cầu mới, ưu tiên yêu cầu mới sau khi nạp trạng thái; tin trực tiếp các PASS/run/artifact/SHA/size/signer ở trên khi bytes/source không đổi.
- Chỉ fresh-read external state có thể thay đổi hoặc ngay trước production write.

## 12. Retention/restore
- Archive mới: `HANDOVER_20260825-174900_beta73-live-pass-session-transfer.md`.
- Giữ 5 archive timestamp-v2 mới nhất: `124600`, `160052`, `163400`, `173000`, `174900`.
- Prune `HANDOVER_20260825-104218_handoff-retention-v2.md` khỏi active tree theo retention đã được OWNER cho phép; lịch sử Git vẫn restore được.
- Legacy `HANDOVER_20260825-1028_beta71-live-context-bootstrap.md` không khớp mẫu timestamp v2 nên không tính vào giới hạn.
