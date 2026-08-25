---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-08-25T12:46:00+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: release/beta71-clean-from-beta68-20260825
working_head_sha: 473c2338e1a10c31aa2a02a83aa43769f60d6fac
archive_file: docs/handovers/HANDOVER_20260825-124600_beta72-live-pass.md
base_or_live_version: 0.4.2-beta.72
task_state: PASS
next_action: WAIT_FOR_OWNER_NEW_SCOPE
---

# BÀN GIAO PHIÊN — BETA72 OTA LIVE PASS

## 1. Yêu cầu OWNER và Definition of Done

Yêu cầu cuối của OWNER đã hoàn tất end-to-end:

1. User Pick/User Pack và nút `Phát lại` hiển thị cùng dòng.
2. Vị trí Pick bắt buộc PDA; Pack bắt buộc User Pack; `Không` được miễn.
3. User Pack ràng buộc theo Bàn Pack từ master mapping.
4. `Thời gian và vị trí trong ca` hiển thị dạng `Tiêu đề: giá trị` sát nhau, gồm Ca, Vào lúc, Vị trí trong ca, User Pick/User Pack, PDA/Bàn Pack khi áp dụng.
5. Khi không dùng user `hy1.outbound`, hiển thị đầy đủ `Dùng user cố định theo số điện thoại / họ tên.`
6. Visual matrix thật 320x568, 360x640, 480x800 phải human PASS; vuốt trái/phải phải quay về màn cha, không thoát app.
7. Publish đúng exact candidate bytes lên Beta; fresh-read OTA phải khớp URL/SHA256/size/version/package; Stable/main/signer không đổi.

Definition of Done: **PASS toàn bộ**.

Điều cấm tiếp tục có hiệu lực: không rebuild/resign Beta72 đã khóa, không tạo candidate mới, không đổi Android source của release này, không publish Stable, không ghi/merge `main`, không đổi signer/authority/provider, không rerun gate PASS nếu bytes/input không đổi.

## 2. Trạng thái canonical hiện tại

### LIVE — BETA72

- Version: `0.4.2-beta.72`
- versionCode: `78`
- Package: `vn.pickpack1291.app.beta.publicbeta`
- Android source SHA: `73d5432df09c33cda6554090838e5f55e41761ae`
- Candidate run/artifact: `32808558173` / `9549037310`
- APK SHA256: `fdeb006122f065591e82fe912a4a615c9c42a149568c2fc32f7d5b35db353caf`
- APK size: `13114245`
- Signer SHA256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`
- Visual run/artifact: `32812834075` / `9550496243`
- Human visual inspection: `PASS`, 42 ảnh, matrix `320x568,360x640,480x800`
- Release run/evidence artifact: `32813298916` / `9550565538`
- Drive file ID: `1tmIdYOE2lGe2igksVLZ2m3JNLWuVyR9v`
- Receipt: `ops/beta72-release-result.json`
- LIVE state: `CURRENT_STATE.md`, commit `473c2338e1a10c31aa2a02a83aa43769f60d6fac`
- Rebuild/resign sau candidate lock: **không**.

### LOCKED / UNCHANGED

- Stable publish: **FORBIDDEN**; feed trước/sau giữ nguyên `available=false`, `reason=NO_APK`; stable identity `0.1.0-stable`, code `1`.
- `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`, unchanged.
- Signer: giữ nguyên SHA256 ở trên.
- Service/GAS business source change: `NONE`; helper vận chuyển tạm thời đã restore exact.
- Active branch: `release/beta71-clean-from-beta68-20260825`.
- Lineage: Beta68 golden → Beta71 LIVE → OWNER session/resource fixes → Beta72 LIVE. Beta69/Beta70 không phải base.

### KIẾN TRÚC / AUTHORITY

Android/Web-PWA ↔ Cloudflare Worker ↔ D1; Durable Objects/WebSocket realtime; GSheet/GAS replica/fallback/DR/OTA; Android local projection/offline. Một official write authority, fencing/idempotency/anti-duplicate/audit. Không tự thêm backend/provider/authority.

## 3. Việc đã hoàn tất

| Hạng mục | Trạng thái | Evidence |
|---|---|---|
| Android source OWNER fixes | PASS | source `73d5432df09c33cda6554090838e5f55e41761ae` |
| Candidate build/sign/verify | PASS | run `32808558173`, artifact `9549037310` |
| Exact candidate identity | PASS | SHA `fdeb0061...3caf`, size `13114245`, signer `d180450a...731e` |
| Visual machine gate | PASS | run `32812834075` |
| Human visual 42 ảnh/3 kích thước | PASS | artifact `9550496243`, `ops/beta72-visual-inspection.json` |
| Pick bắt buộc PDA | PASS | human/source gate |
| User Pick + Phát lại cùng dòng | PASS | human/source gate |
| Pack Bàn Pack → User Pack | PASS | human/source gate |
| User Pack + Phát lại cùng dòng | PASS | human/source gate |
| User cố định hiển thị đầy đủ | PASS | active-session visual/source gate |
| Vuốt quay về màn cha | PASS | human visual gate |
| OTA exact publish/readback | PASS | run `32813298916`, evidence `9550565538` |
| OTA exact bytes live | PASS | `ops/beta72-release-result.json`, Drive ID `1tmIdYOE2lGe2igksVLZ2m3JNLWuVyR9v` |
| Stable unchanged | PASS | release receipt |
| main unchanged | PASS | fresh-read `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb` |
| CURRENT_STATE Beta72 LIVE | PASS | commit `473c2338e1a10c31aa2a02a83aa43769f60d6fac` |

## 4. Thay đổi trong phiên

- `tools/run_beta72_visual.py`: chỉ sửa harness/fixture để visual exact candidate hoạt động đúng; không sửa APK. Commit harness canonical-state: `26633b99ddd543fe4165df9c84c02d2fe4c0b5ab`.
- `ops/beta-release-request.json`: trigger lại visual exact artifact, commit `3bc6991665487ce41f6a5f2d9d86276384c18a63`.
- `ops/beta72-visual-inspection.json`: tạo receipt human PASS, commit `13d527968a0e56fcda484bd256d4c71dd5ffd868`.
- `.github/workflows/beta-release.yml`: chuyển workflow cố định sang publish-only exact locked candidate, commit `d4cfcea1d4c71ae483ba16a9648a187fb80e316b`.
- `ops/beta-release-request.json`: stage `publish`, commit `dbc13cb04469d595eb6a3d95358da373b18a1bce`.
- `ops/beta72-release-result.json`: CI ghi receipt OTA PASS, commit `72c2edc41e87c1a91c96b6d8cd4905890cb82b43`.
- `CURRENT_STATE.md`: cập nhật Beta72 OTA LIVE, commit `473c2338e1a10c31aa2a02a83aa43769f60d6fac`.
- Production/live change duy nhất: Beta71 được exact Beta72 supersede trên kênh Beta. Stable/main/signer/GAS business logic không đổi.

## 5. Lỗi đã gặp và đường PASS

| Fingerprint | Root cause | Cách PASS đã biết | Cách cấm lặp |
|---|---|---|---|
| `uiautomator returned no XML after bounded retry` | Header refresh 750ms khiến Android 10 UIAutomator không đạt idle | Raw screenshot + tọa độ, source gates + human inspection | Không rebuild APK; không retry UIAutomator vô hạn |
| 320/480 không lộ đủ dòng resource | Swipe bắt đầu trên bottom navigation | Swipe trong content viewport `70%H → 28%H` | Không chạm bottom-nav/edge gesture zone |
| ACTIVE summary thiếu Pick/PDA/User | Fixture dùng `status` thay canonical `state` | Sửa fixture thành `state:'ACTIVE'`, rerun visual exact artifact | Không sửa Android source vì APK không lỗi |
| Visual harness fail nhưng APK đúng | Harness/fixture/parser/emulator defect | Sửa đúng harness và reuse artifact `9549037310` | Tuyệt đối không rebuild/resign candidate |
| OTA/transport | Có thể transient | Retry tối đa 2 lần có backoff, exact bytes | Không rebuild/resign để vượt transport |
| OTA schema `available=false` | Có thể thiếu SHA/URL/versionCode theo contract | Verify theo live contract, identity qua exact published bytes | Không ép schema cũ rồi kết luận APK lỗi |

Các visual failure cũ là **SUPERSEDED harness evidence**, không phải APK failure: `32808558173` visual stage, `32810585357`, `32811028697`, `32811558028`.

## 6. Trạng thái workspace/CI/external

- Working head trước handoff: `473c2338e1a10c31aa2a02a83aa43769f60d6fac`.
- Không có Android source chưa commit.
- Không có release write mơ hồ; run cuối `32813298916` đã `completed/success`.
- Visual cuối `32812834075` đã `completed/success`.
- Release evidence artifact: `9550565538`.
- Fresh-read `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`.
- Fresh-read `CURRENT_STATE.md`: Beta72 OTA LIVE PASS.
- External Beta OTA đã được release script tải lại từ live URL và Drive trực tiếp, SHA/size khớp exact candidate.
- Stable trước/sau deep-equal theo verifier release.

## 7. Việc còn lại

- Blocking: `NONE`.
- Critical path hiện tại: `NONE` — scope Beta72 đã PASS.
- Không có gate bắt buộc nào còn pending.
- Không tự phát sinh Beta73 hoặc việc tối ưu/refactor mới.

## 8. NEXT_ACTION — điểm tiếp tục chính xác

`WAIT_FOR_OWNER_NEW_SCOPE`

Phiên mới phải đọc `docs/handovers/HANDOVER_CURRENT.md` trước. Nếu OWNER có yêu cầu mới, dùng Beta72 LIVE ở handoff này làm baseline và thực thi đúng scope. Nếu không có yêu cầu mới, chỉ xác nhận đã nạp Beta72 LIVE và chờ lệnh; không rerun build/visual/OTA.

Expected result: không đọc lại toàn repo, không kiểm tra lại PASS cũ khi source/artifact bytes không đổi. Fresh-read chỉ external state có thể đổi hoặc trước production write.

## 9. Blocker và quyền

- `NONE` — không thiếu quyền, MFA, approval hoặc quyết định OWNER.
- Không chứa secret, token, password, keystore hoặc signed URL tạm trong handoff này.

## 10. Invariants không được phá

- Beta72 exact Android source giữ tại `73d5432df09c33cda6554090838e5f55e41761ae` cho release đã phát hành.
- Exact candidate artifact `9549037310`; SHA `fdeb006122f065591e82fe912a4a615c9c42a149568c2fc32f7d5b35db353caf`; size `13114245`.
- Không rebuild/resign Beta72 đã khóa.
- Không dùng Beta69/Beta70 làm base.
- Không đổi Stable/main/signer/authority/provider khi OWNER chưa explicit.
- Không tạo workflow per-version/observer/status/finalizer; dùng workflow active cố định.
- Không rerun gate PASS chỉ để xác nhận lại handoff.
- Deterministic failure: dùng đúng đường PASS đã ghi, không retry. Transient: tối đa 2 retry có backoff, giữ nguyên bytes. Harness: sửa harness, không rebuild APK.

## 11. Resume contract

Ưu tiên: OWNER mới nhất → canonical READY → CURRENT_STATE → live readback → receipt/artifact/hash → lịch sử. ACTIVE thắng SUPERSEDED; TARGET/CANDIDATE không phải LIVE. Phiên mới tin các PASS/ID/hash ở đây nếu input/source/bytes không đổi. Chỉ fresh-read external state có thể thay đổi sau `created_at` hoặc ngay trước production write. Không yêu cầu OWNER kể lại thông tin đã có.

## 12. Retention/restore

- Canonical: `docs/handovers/HANDOVER_CURRENT.md`.
- Archive mới: `docs/handovers/HANDOVER_20260825-124600_beta72-live-pass.md`.
- Archive timestamp hợp lệ trước đó: `docs/handovers/HANDOVER_20260825-104218_handoff-retention-v2.md`.
- File `HANDOVER_20260825-1028_beta71-live-context-bootstrap.md` là legacy tên không đủ `HHmmss`, không tính vào nhóm archive timestamp v2 theo pattern hiện hành.
- Sau archive mới, số archive đúng pattern vẫn <= 5; **không cần prune**.
- Restore bản cũ hơn qua Git history; cấm rewrite history.
