---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-08-25T22:30:58+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: release/beta71-clean-from-beta68-20260825
working_head_sha: ac6da56b93bda051b187f48622ebc1dc9867976b
archive_file: docs/handovers/HANDOVER_20260825-223058_beta75-ota-live-pass.md
base_or_live_version: 0.4.2-beta.75
target_version: 0.4.2-beta.75
task_state: PASS
next_action: WAIT_FOR_OWNER_NEW_SCOPE
---

# BÀN GIAO PHIÊN — BETA75 OTA LIVE PASS

## 1. Yêu cầu OWNER và Definition of Done
- OWNER yêu cầu hoàn tất Beta75 từ exact candidate đã khóa và phát hành kênh BETA; cấm rebuild/resign/version bump/Beta76, cấm quay lại visual sau HUMAN PASS, cấm đổi Stable/main/signer/authority.
- DoD: HUMAN visual PASS → publish exact bytes → OTA/Drive/LIVE readback khớp → Stable/main/signer/authority unchanged → receipt + CURRENT_STATE + handoff READY.
- Kết quả: **PASS toàn bộ**.

## 2. Trạng thái canonical hiện tại
### LIVE
- Beta: `0.4.2-beta.75`, versionCode `81` — **OTA LIVE PASS**.
- Package: `vn.pickpack1291.app.beta.publicbeta`.
- Android source SHA: `e475b8476e99a9230683dbbf6ec266235960ed5b`.
- Candidate run/artifact: `32849057694` / `9563625638`.
- APK SHA256: `6e08dc974281cc7b5428d22cf406179447cdeb95443dc19fa1db2b4d32344913`.
- Size: `13147013` bytes.
- Signer SHA256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Probe HUMAN PASS: run `32859450233`, artifact `9567602636`.
- Final visual: run `32860235560`, artifact `9568028848`; receipt `ops/beta75-visual-inspection.json`, commit `007795a656fa14236ed766b164ca80bb5872fb32`; HUMAN PASS đủ `320x568`, `360x640`, `480x800`.
- Final publish run: `32865705207` — SUCCESS.
- Release evidence artifact: `9570048273`; digest `sha256:09707dc2c8feeab71fdcc8aab74b5628fc713c09d019b9357f49f8aca62439be`.
- Release receipt: `ops/beta75-release-result.json`, verdict `PASS`; final readback receipt commit `2f305eb5324aaff9ff54aad8ef6cadd21b08e944`.
- Drive APK ID: `1A0T5HL2HD-On1Oc4A3G3Rd0qZAlbFwWz`; checksum ID: `1okPTtleBKOUb9L-HLbV94ImQqu5iorSv`.
- OTA URL: `https://drive.usercontent.google.com/download?id=1A0T5HL2HD-On1Oc4A3G3Rd0qZAlbFwWz&export=download&confirm=t`.
- Publisher post-write OTA readback: Beta74 client `available=true`, target Beta75 VC81, SHA/size exact; Beta75 client `available=false`, version Beta75 VC81.
- Fresh authenticated Drive readback after publish: name `pick-pack-1291-public-beta-0.4.2-beta.75.apk`, MIME APK, size `13147013`; downloaded bytes SHA exact; checksum file exact.

### SUPERSEDED
- Beta74: **SUPERSEDED by Beta75**; previous SHA `37cadd74088179f1e17872c7474622681941cc5f546807cea769517d9f98b017`.

### LOCKED / UNCHANGED
- Stable: `0.1.0-stable`, versionCode `1`; publish **FORBIDDEN**; feed before/after identical `available=false`, `reason=NO_APK`.
- `main`: fresh-read `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`, unchanged.
- Signer unchanged: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Worker/Service change: `NONE`; authority change: `NONE`; provider unchanged.
- GAS production change: `OTA_VERSION_COMPAT_BETA75` only; temporary exact-Drive upload helper removed after publish.

## 3. Việc đã hoàn tất
| Hạng mục | Trạng thái | Evidence |
|---|---|---|
| Beta75 Android source | PASS | `e475b8476e99a9230683dbbf6ec266235960ed5b` |
| Candidate compile/sign/upload | PASS | run `32849057694`, artifact `9563625638`, exact SHA/size/signer ở mục 2 |
| Probe visual lỗi cuối | PASS | run `32859450233`, artifact `9567602636` |
| Final HUMAN visual matrix | PASS | run `32860235560`, artifact `9568028848`, receipt commit `007795a...` |
| Exact publish-only preflight | PASS | run `32865705207`, lock receipt + exact bytes + materialized publisher |
| Exact publish | PASS | run `32865705207` SUCCESS |
| OTA client readback | PASS | Beta74→Beta75 available; Beta75→no newer |
| Drive metadata/bytes/checksum fresh-read | PASS | ID `1A0T5...`, size/SHA exact; checksum ID `1okPT...` exact |
| Stable isolation | PASS | Stable before/after identical |
| main isolation | PASS | fresh-read `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb` |
| CURRENT_STATE | PASS | commit `ac6da56b93bda051b187f48622ebc1dc9867976b` |

## 4. Thay đổi trong phiên
- Android Beta75 source tại commit `e475b8476e99a9230683dbbf6ec266235960ed5b`; sau candidate lock không sửa source/rebuild/resign.
- `tools/run_beta75_visual.py` và fixed `.github/workflows/beta-release.yml`: chỉ sửa visual harness trong failure domain, exact APK giữ nguyên.
- `ops/beta75-visual-inspection.json`: receipt commit `007795a656fa14236ed766b164ca80bb5872fb32`.
- `tools/publish_beta75_ota.sh`: exact-byte publisher Beta75 từ đường PASS Beta74, commit `7f2d92b83fe73ce09ca246dea2122017d3f57006`.
- `.github/workflows/beta-release.yml`: publish-only fixed workflow; final preflight fix commit `3ab1ac75e840c0f364f5376651ef0a5171eaf6d4`.
- `ops/beta-release-request.json`: stage publish exact Beta75, commit `3b7cf919fa5ac6cfd5e36e55a705fe2180683360`.
- `ops/beta75-release-result.json`: publisher receipt then final fresh-read correction commit `2f305eb5324aaff9ff54aad8ef6cadd21b08e944`.
- `CURRENT_STATE.md`: Beta75 LIVE commit `ac6da56b93bda051b187f48622ebc1dc9867976b`.
- Production LIVE change duy nhất: Beta OTA Beta74 → Beta75; Stable/main/signer/Worker/Service authority không đổi.

## 5. Lỗi đã gặp và đường PASS
| Fingerprint | Root cause | Cách PASS đã biết | Cách cấm lặp |
|---|---|---|---|
| Compile đầu Beta75: `Unresolved reference ColorDrawable` | thiếu import Kotlin | thêm đúng `android.graphics.drawable.ColorDrawable`, compile/sign candidate sau đó PASS | không xử lý cascade, không refactor ngoài scope |
| Visual automation PASS nhưng ảnh sai dialog/IME | harness selector/fixture/keyboard, không phải APK | probe riêng đúng frame/kích thước, sửa harness, HUMAN PASS probe rồi mới final matrix | không full-matrix mù; không UiAutomation/Instrumentation/uiautomator API29 |
| Publish preflight fail trước candidate download | harness receipt compare và wrapper grep tự bắt chính blacklist string | validate receipt tại exact commit bằng jq identity; kiểm tra blacklist trên **materialized publisher** | không rebuild/resign/revisual để chữa preflight |
| Một `curl (28)` trong final publisher | transient propagation/transport | proven propagation windows 6/8 giữ exact bytes; run vẫn SUCCESS | không tạo candidate/Beta76; retry exact bytes trong budget |

## 6. Trạng thái workspace/CI/external
- Active branch: `release/beta71-clean-from-beta68-20260825`.
- Working head trước handoff: `ac6da56b93bda051b187f48622ebc1dc9867976b`.
- Final release run `32865705207`: **SUCCESS**; không còn release run cần theo dõi.
- Exact candidate bytes không đổi sau lock.
- Fresh external at `2026-08-25T22:30:58+07:00`: Drive metadata/bytes/checksum exact; main unchanged; publisher post-write OTA + Stable readback PASS.
- Blocker: NONE.

## 7. Việc còn lại
- **NONE — Beta75 OTA DoD PASS toàn bộ.**
- Không housekeeping tự phát ngoài handoff retention đã được OWNER duyệt.

## 8. NEXT_ACTION — điểm tiếp tục chính xác
`WAIT_FOR_OWNER_NEW_SCOPE`

## 9. Blocker và quyền
- **NONE** — không thiếu quyền/MFA/approval cho scope Beta75 đã hoàn tất.

## 10. Invariants không được phá
- Không rebuild/resign/revisual Beta75 đã LIVE chỉ để kiểm tra lại khi source/artifact bytes không đổi.
- Không đổi Stable/main/signer/authority/provider nếu OWNER chưa ra lệnh mới.
- Beta75 LIVE identity phải giữ đúng version/code/package/SHA/size/signer/Drive IDs ở mục 2.
- Beta74 là SUPERSEDED; không promote ngược nếu OWNER không ra lệnh restore cụ thể.
- Tin PASS/run/artifact/hash/version/evidence ở handoff này khi inputs/bytes không đổi; chỉ fresh-read external state có thể đổi.

## 11. Resume contract
- Phiên mới đọc `docs/handovers/HANDOVER_CURRENT.md` trước; nếu READY thì dùng làm canonical.
- Có yêu cầu OWNER mới: ưu tiên yêu cầu mới, chỉ đọc đúng failure domain/NEXT_ACTION liên quan; không crawl repo/rerun gate PASS.
- Không có scope mới: vì task_state PASS và NEXT_ACTION `WAIT_FOR_OWNER_NEW_SCOPE`, chỉ xác nhận đã nạp snapshot và chờ.

## 12. Retention/restore
- Archive mới: `HANDOVER_20260825-223058_beta75-ota-live-pass.md`.
- Giữ 5 timestamp archive mới nhất; prune `HANDOVER_20260825-160052_beta73-visual-retry-cap-blocked.md` khỏi active tree vì là bản thứ 6/cũ nhất.
- Các archive giữ lại sau prune: `HANDOVER_20260825-163400_beta73-uiautomation-bridge-blocked.md`, `HANDOVER_20260825-173000_beta73-ota-live-pass.md`, `HANDOVER_20260825-174900_beta73-live-pass-session-transfer.md`, `HANDOVER_20260825-190249_beta74-ota-live-pass.md`, `HANDOVER_20260825-223058_beta75-ota-live-pass.md`.
- Bản prune vẫn restore được qua Git history; cấm rewrite history.
