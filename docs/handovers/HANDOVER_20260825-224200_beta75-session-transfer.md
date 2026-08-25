---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-08-25T22:42:00+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: release/beta71-clean-from-beta68-20260825
working_head_sha: c5b45b8bb7dec35a868d7c425866cfce28ce9eae
archive_file: docs/handovers/HANDOVER_20260825-224200_beta75-session-transfer.md
base_or_live_version: 0.4.2-beta.75
target_version: 0.4.2-beta.75
task_state: PASS
next_action: WAIT_FOR_OWNER_NEW_SCOPE
---

# BÀN GIAO PHIÊN — BETA75 OTA LIVE PASS

## 1. Yêu cầu OWNER và Definition of Done
- OWNER đã yêu cầu phát hành exact Beta75 và chỉ kết thúc khi exact bytes publish PASS → OTA/Drive/LIVE readback khớp → Stable/main/signer/authority unchanged → state/handoff READY.
- Scope Beta75 đã hoàn tất toàn bộ; OWNER hiện yêu cầu chuyển phiên chat.
- Cấm tự rebuild/resign/revisual/version bump/Beta76 hoặc đổi Stable/main/signer/authority khi chưa có scope OWNER mới.

## 2. Trạng thái canonical hiện tại
### LIVE
- Beta: `0.4.2-beta.75`, versionCode `81` — **BETA75 OTA LIVE PASS**.
- Package: `vn.pickpack1291.app.beta.publicbeta`.
- Android source SHA: `e475b8476e99a9230683dbbf6ec266235960ed5b`.
- Candidate run/artifact: `32849057694` / `9563625638`.
- APK SHA256: `6e08dc974281cc7b5428d22cf406179447cdeb95443dc19fa1db2b4d32344913`.
- Size: `13147013` bytes.
- Signer SHA256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Probe HUMAN PASS: run `32859450233`, artifact `9567602636`.
- Final HUMAN visual matrix: run `32860235560`, artifact `9568028848`; receipt `ops/beta75-visual-inspection.json`, receipt commit `007795a656fa14236ed766b164ca80bb5872fb32`; PASS đủ `320x568`, `360x640`, `480x800`.
- Final publish run: `32865705207` — SUCCESS.
- Release evidence artifact: `9570048273`; digest `sha256:09707dc2c8feeab71fdcc8aab74b5628fc713c09d019b9357f49f8aca62439be`.
- Release receipt: `ops/beta75-release-result.json`, verdict `PASS`.
- Drive APK ID: `1A0T5HL2HD-On1Oc4A3G3Rd0qZAlbFwWz`; checksum ID: `1okPTtleBKOUb9L-HLbV94ImQqu5iorSv`.
- OTA URL: `https://drive.usercontent.google.com/download?id=1A0T5HL2HD-On1Oc4A3G3Rd0qZAlbFwWz&export=download&confirm=t`.
- Beta74 client thấy Beta75 `available=true`; Beta75 client không thấy bản mới hơn theo contract.

### SUPERSEDED
- Beta74: **SUPERSEDED by Beta75**; SHA cũ `37cadd74088179f1e17872c7474622681941cc5f546807cea769517d9f98b017`.

### LOCKED / UNCHANGED
- Stable: `0.1.0-stable`, versionCode `1`; publish **FORBIDDEN**; feed trước/sau unchanged.
- `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`, fresh-read unchanged sau publish.
- Signer unchanged: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Worker/Service change: `NONE`; authority change: `NONE`; provider unchanged.
- GAS production change: chỉ OTA version compatibility Beta75; temporary Drive upload helper đã được gỡ sau publish.

## 3. Việc đã hoàn tất
| Hạng mục | Trạng thái | Evidence |
|---|---|---|
| Beta75 Android source | PASS | `e475b8476e99a9230683dbbf6ec266235960ed5b` |
| Candidate compile/sign/upload | PASS | run `32849057694`, artifact `9563625638` |
| Final HUMAN visual matrix | PASS | run `32860235560`, artifact `9568028848`, receipt commit `007795a...` |
| Publish exact bytes | PASS | run `32865705207` SUCCESS |
| OTA readback | PASS | Beta74→Beta75 available; Beta75→no newer |
| Drive metadata/bytes/checksum | PASS | exact SHA `6e08...4913`, size `13147013` |
| Stable isolation | PASS | unchanged |
| main isolation | PASS | `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb` |
| CURRENT_STATE | PASS | Beta75 LIVE |

## 4. Thay đổi trong phiên
- `tools/publish_beta75_ota.sh`: publisher exact-byte Beta75 từ đường PASS Beta74.
- `.github/workflows/beta-release.yml`: fixed active publish-only workflow, không build/sign/visual.
- `ops/beta-release-request.json`: stage publish exact Beta75.
- `ops/beta75-release-result.json`: release receipt PASS.
- `CURRENT_STATE.md`: Beta75 LIVE PASS, Beta74 SUPERSEDED.
- Production LIVE change duy nhất: Beta OTA Beta74 → Beta75.
- Trong thao tác bàn giao này có một ref phụ vô tình được tạo: `release/beta71-clean-from-beta68-20260825-handoff-temp` tại SHA `c5b45b8bb7dec35a868d7c425866cfce28ce9eae`; **không phải ACTIVE, không có divergence nội dung, không dùng làm continuity**. Active branch vẫn là `release/beta71-clean-from-beta68-20260825`.

## 5. Lỗi đã gặp và đường PASS
| Fingerprint | Root cause | Cách PASS đã biết | Cấm lặp |
|---|---|---|---|
| Beta75 compile: `Unresolved reference ColorDrawable` | thiếu import Kotlin | thêm đúng import, compile/sign candidate PASS | không xử lý cascade/refactor |
| Visual sai dialog/IME | harness selector/fixture/keyboard | sửa harness only, exact APK giữ nguyên, HUMAN PASS | không rebuild/revisual mù |
| Publish preflight fail | gate harness tự bắt blacklist/receipt byte compare | jq exact receipt identity + kiểm tra materialized publisher | không rebuild/resign |
| `curl (28)` trong publisher | transient transport/propagation | giữ exact bytes, dùng propagation window proven | không tạo candidate/Beta76 |

## 6. Trạng thái workspace/CI/external
- Active branch: `release/beta71-clean-from-beta68-20260825`.
- Working head trước handoff mới: `c5b45b8bb7dec35a868d7c425866cfce28ce9eae`.
- Final release run `32865705207`: SUCCESS; không còn workflow cần theo dõi.
- Exact candidate bytes không đổi sau lock.
- External state đã fresh-read sau publish: Drive/public bytes exact; OTA LIVE PASS; Stable/main/signer/authority unchanged.
- Blocker: NONE.

## 7. Việc còn lại
- **NONE — Beta75 OTA DoD PASS toàn bộ.**
- Chờ OWNER ra scope mới.

## 8. NEXT_ACTION — điểm tiếp tục chính xác
`WAIT_FOR_OWNER_NEW_SCOPE`

## 9. Blocker và quyền
- **NONE** — không thiếu quyền/MFA/approval cho scope đã hoàn tất.

## 10. Invariants không được phá
- Không rebuild/resign/revisual Beta75 đã LIVE khi source/artifact bytes không đổi.
- Không đổi Stable/main/signer/authority/provider khi OWNER chưa ra lệnh mới.
- Beta75 LIVE identity phải giữ đúng version/code/package/SHA/size/signer/Drive IDs ở mục 2.
- Beta74 là SUPERSEDED.
- Tin các PASS/run/artifact/hash/version/evidence ở handoff này khi input/source/bytes không đổi; chỉ fresh-read external state có thể đổi.

## 11. Resume contract
- Phiên mới đọc `docs/handovers/HANDOVER_CURRENT.md` trước.
- Nếu `status: READY`, dùng file này làm canonical; không crawl repo/rerun gate PASS.
- Có yêu cầu OWNER mới: ưu tiên yêu cầu mới và chỉ đọc đúng failure domain liên quan.
- Không có scope mới: vì `task_state: PASS` và `NEXT_ACTION: WAIT_FOR_OWNER_NEW_SCOPE`, chỉ xác nhận đã nạp snapshot và chờ.

## 12. Retention/restore
- Archive mới: `HANDOVER_20260825-224200_beta75-session-transfer.md`.
- Giữ đúng 5 timestamp archive mới nhất sau prune: `HANDOVER_20260825-173000_beta73-ota-live-pass.md`, `HANDOVER_20260825-174900_beta73-live-pass-session-transfer.md`, `HANDOVER_20260825-190249_beta74-ota-live-pass.md`, `HANDOVER_20260825-223058_beta75-ota-live-pass.md`, `HANDOVER_20260825-224200_beta75-session-transfer.md`.
- Prune `HANDOVER_20260825-163400_beta73-uiautomation-bridge-blocked.md` khỏi active tree theo retention đã được OWNER duyệt; vẫn restore được qua Git history.
