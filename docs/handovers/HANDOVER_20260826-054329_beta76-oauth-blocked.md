---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-08-26T05:43:29+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: feature/beta76-nhan-hang-rot-20260825
working_head_sha: 2f27f99715b12f559ef843ae44d3ba748bc733f3
archive_file: docs/handovers/HANDOVER_20260826-054329_beta76-oauth-blocked.md
base_or_live_version: 0.4.2-beta.75
target_version: 0.4.2-beta.76
task_state: BLOCKED
next_action: OWNER cập nhật GitHub Actions repository secret GOOGLE_OAUTH_REFRESH_TOKEN bằng refresh token mới của đúng OAuth client/account hiện có, sau đó rerun failed jobs của run 32907203640
---

# BÀN GIAO PHIÊN — BETA76 HUMAN VISUAL PASS / PUBLISH BLOCKED BY REVOKED OAUTH

## 1. Yêu cầu OWNER và Definition of Done
- Chốt exact Beta76 từ candidate đã khóa; không rebuild, resign, version bump hoặc tạo Beta77.
- Chỉ publish kênh BETA sau HUMAN visual PASS; Stable/main/signer/authority phải giữ nguyên.
- DoD: HUMAN VISUAL PASS → exact Beta76 publish PASS → OTA/Drive/LIVE readback khớp → state/handoff READY.
- Trạng thái tại handoff: HUMAN visual đã PASS; publish bị chặn trước mọi production write bởi Google OAuth refresh token trong GitHub secret đã expired/revoked.

## 2. Trạng thái canonical hiện tại
### LIVE
- Beta vẫn là `0.4.2-beta.75`, versionCode `81`, package `vn.pickpack1291.app.beta.publicbeta`.
- Beta75 APK SHA256 `6e08dc974281cc7b5428d22cf406179447cdeb95443dc19fa1db2b4d32344913`, size `13147013` bytes.
- Drive APK ID `1A0T5HL2HD-On1Oc4A3G3Rd0qZAlbFwWz`; checksum ID `1okPTtleBKOUb9L-HLbV94ImQqu5iorSv`.

### TARGET / EXACT CANDIDATE
- Source SHA: `0d81793eabf465716a4fe36038d143b11220667f`.
- Candidate run/artifact: `32875201581` / `9573716441`.
- Version: `0.4.2-beta.76`; versionCode `82`.
- Package: `vn.pickpack1291.app.beta.publicbeta`.
- APK SHA256: `7018977f28d09434de27e6c6e90a7a51ec11c77831285d7e466c7aeeeeef9ee2`.
- Size: `13179781` bytes.
- Signer SHA256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Beta76 chưa LIVE; Beta75 chưa SUPERSEDED.

### LOCKED / UNCHANGED
- Stable: `0.1.0-stable`, versionCode `1`; publish **FORBIDDEN**.
- `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`.
- Signer giữ nguyên như trên; authority/provider/Worker/Service không đổi.
- Không build/sign task trong fixed release workflow; publisher chỉ nhận exact artifact `9573716441`.

## 3. Việc đã hoàn tất
| Hạng mục | Trạng thái | Evidence |
|---|---|---|
| Sheet/permission | PASS | Trusted gate từ checkpoint; không rerun |
| App/logic | PASS | Trusted gate từ checkpoint; source `0d81793e...` |
| Exact Beta76 candidate | PASS / LOCKED | run `32875201581`, artifact `9573716441`, exact identity ở mục 2 |
| Visual v3 requested run | FAIL harness only | run `32876275428`, job `97894807095`; APK identity preflight PASS; `uiautomator hierarchy unavailable after 2 attempts` |
| Focused visual probe | HUMAN PASS | run `32905776490`, artifact `9584789120`, digest `sha256:41cfb2eba0a0fb76bba204513a040eabdde870c417d952d61443c14e89fee4b8` |
| Final HUMAN visual matrix | PASS / LOCKED | run `32906107089`, artifact `9584898561`, digest `sha256:c02316956d161629d6c8f079171cf51572931fb2ddc3e137b56c9a9429faf7f5`; receipt `ops/beta76-visual-inspection.json`, commit `aa3123d3b0c20230f441c3db9aaf9d516c9e481e` |
| Visual `320x568` | HUMAN PASS | đúng màn/thẻ Nhận hàng Rớt; select + Tạo/Sửa/Xóa; QR/DO/Số kiện + keyboard; đủ hai nút cuối |
| Visual `360x640` | HUMAN PASS | không cắt/chồng/tràn; đúng navigation; không loading/wrong-screen |
| Visual `480x800` | HUMAN PASS | không cắt/chồng/tràn; đúng navigation; không loading/wrong-screen |
| Publish-only request/workflow | PASS | request commit `1d63b5410084f839af5cddfe30a8e3d73392c6a7`; workflow commit `babc4a7395cdb77e6b785766a12a6888c45bc54b` |
| Publisher exact-byte materialization | PASS | `tools/publish_beta76_ota.sh`, commit `91bc4a142d6faa781317ccb69282e03234feba04`; OAuth evidence patch `2f27f99715b12f559ef843ae44d3ba748bc733f3` |
| Publish preflight | PASS | run `32907203640`, job `97993767955`: exact artifact/receipt/publish-only/no build-sign/no Stable-main write đều PASS |
| Production write | NONE | publisher dừng tại OAuth refresh trước GAS/Drive mutation |
| External Drive read-only verification | PASS | Beta folder chỉ còn Beta75 APK/checksum; không có Beta76 ghi dở |

## 4. Thay đổi trong phiên
- Sửa harness visual theo đúng failure domain route/wait/IME/density; không sửa hoặc rebuild APK.
- Tạo `ops/beta76-visual-inspection.json` khóa HUMAN PASS exact candidate.
- Chuyển `.github/workflows/beta-release.yml` và `ops/beta-release-request.json` sang publish-only exact Beta76.
- Tạo `tools/publish_beta76_ota.sh` từ đường publisher Beta75 đã chứng minh, thêm exact identity/visual/stable-main guards, retry transport tối đa 2 lần và Drive/OTA/LIVE readback.
- Thêm OAuth response evidence tại commit `2f27f99715b12f559ef843ae44d3ba748bc733f3` để phân loại deterministic blocker.
- Production/live change: **NONE**; `CURRENT_STATE.md` giữ Beta75 LIVE là đúng.

## 5. Lỗi đã gặp và đường PASS
| Fingerprint | Root cause | Cách PASS đã biết | Cách cấm lặp |
|---|---|---|---|
| Visual v1/v2/v3 hierarchy/route/IME failures | harness selector, stale tap, density reset, keyboard guard; không phải APK | sửa đúng harness, probe HUMAN PASS rồi full matrix exact artifact HUMAN PASS | không rebuild APK; không retry cùng harness; không quay lại visual sau receipt lock |
| Publish run `32907043551` HTTP 400 | OAuth refresh failure; body chưa được lưu | thêm response-body evidence, rerun chẩn đoán cùng exact bytes | không coi HTTP 400 là transport transient |
| Publish run `32907203640`: `invalid_grant` / `Token has been expired or revoked.` | GitHub secret `GOOGLE_OAUTH_REFRESH_TOKEN` hết hạn hoặc bị thu hồi | OWNER thay secret bằng refresh token mới của đúng OAuth client/account hiện có rồi rerun failed jobs của chính run | không retry token cũ; không rebuild/resign; không upload Drive riêng gây partial publish |

## 6. Trạng thái workspace/CI/external
- Active branch: `feature/beta76-nhan-hang-rot-20260825`.
- Working head trước handoff: `2f27f99715b12f559ef843ae44d3ba748bc733f3`; fresh compare với branch: identical.
- Publish run đầu `32907043551`, job `97993295843`: FAILURE tại OAuth; evidence artifact `9585182268`, digest `sha256:c4e739f42d9721fc99b8faf154e5f7379a84f210bc28040438933953b2c292a9`.
- Publish diagnostic run hiện hữu `32907203640`, job `97993767955`: FAILURE deterministic tại OAuth; evidence artifact `9585229111`, digest `sha256:c58a89a47bc933dd07c8958a0b67fe966305be4c2acfb7a2647b8adf21f22d6b`.
- `oauth-token.json`: `invalid_grant`, `Token has been expired or revoked.`; không chứa secret.
- Không workflow đang chạy/pending cần poll; không có production write mơ hồ.
- Google Drive connector chỉ được dùng read-only để xác minh; connector không có Apps Script/GAS deploy nên không dùng upload riêng.
- Beta75 vẫn LIVE; Stable/main/signer/authority unchanged.

## 7. Việc còn lại
- Blocked critical path: refresh quyền OAuth của publisher, rerun **chính run hiện hữu** `32907203640`, poll terminal, rồi hoàn tất OTA/Drive/public bytes/LIVE/Stable/main/signer/authority readback.
- Nếu publish SUCCESS: ghi `ops/beta76-release-result.json`, cập nhật `CURRENT_STATE.md` và handoff PASS/archive READY, commit/push/readback.
- Không có visual, build, sign, candidate hoặc version work còn lại.

## 8. NEXT_ACTION — điểm tiếp tục chính xác
Sau khi OWNER xác nhận đã cập nhật secret, gọi GitHub Actions **rerun failed jobs** cho run `32907203640` trên repo `tam95supra-source/pick-pack-1291`; expected: exact preflight PASS rồi publish exact artifact `9573716441`. Nếu transport/Drive/GAS/OTA transient thì dùng retry budget đã tích hợp (tối đa 2 lần, giữ nguyên bytes); nếu verifier deterministic thì chỉ sửa publisher/verifier.

## 9. Blocker và quyền
- **OWNER action required:** cập nhật repository secret `GOOGLE_OAUTH_REFRESH_TOKEN` trong GitHub Actions bằng refresh token mới của đúng Google OAuth client/account hiện có, có quyền Apps Script API và Drive.
- Không gửi token trong chat và không đổi tên secret/client/authority.
- Sau cập nhật chỉ cần báo `đã cập nhật secret`; phiên tiếp theo dùng đúng NEXT_ACTION ở mục 8.

## 10. Invariants không được phá
- Không rebuild/resign/version bump/Beta77; exact APK identity ở mục 2 là bất biến.
- Không tạo visual hoặc publish workflow run trùng; dùng rerun failed jobs của run `32907203640`.
- Không quay lại visual: final receipt run `32906107089` / artifact `9584898561` đã HUMAN PASS và khóa.
- Stable publish FORBIDDEN; không ghi Stable/main; không đổi signer/authority/provider.
- Không upload Beta76 riêng qua Drive connector vì thiếu GAS OTA update sẽ tạo partial production state.
- Không retry refresh token cũ đã deterministic `invalid_grant`.
- Tin Sheet/permission, app/logic, exact candidate và HUMAN visual PASS khi source/artifact/receipt không đổi.

## 11. Resume contract
- Phiên mới đọc canonical READY này trước; vì `task_state: BLOCKED`, chỉ yêu cầu đúng OWNER action ở mục 9 nếu chưa được xác nhận.
- Khi OWNER xác nhận secret đã cập nhật, fresh-read run `32907203640`, rerun failed jobs trên chính run đó và tiếp tục đến terminal; không dispatch workflow mới.
- Sau publish SUCCESS phải fresh-read OTA Beta feed, Drive metadata, public bytes, LIVE Beta, Stable feed, main, signer và authority trước khi cập nhật state/handoff PASS.
- Chỉ Beta76 LIVE khi version/code/package/SHA/size/signer khớp exact lock, Beta75 client thấy available=true, Beta76 client không thấy bản mới hơn, Beta75 là SUPERSEDED và mọi invariant unchanged.

## 12. Retention/restore
- Archive mới: `HANDOVER_20260826-054329_beta76-oauth-blocked.md`.
- Giữ đúng 5 archive mới nhất: `HANDOVER_20260826-054329_beta76-oauth-blocked.md`, `HANDOVER_20260825-224200_beta75-session-transfer.md`, `HANDOVER_20260825-223058_beta75-ota-live-pass.md`, `HANDOVER_20260825-190249_beta74-ota-live-pass.md`, `HANDOVER_20260825-174900_beta73-live-pass-session-transfer.md`.
- Prune `HANDOVER_20260825-173000_beta73-ota-live-pass.md` khỏi active tree theo retention đã được OWNER duyệt; vẫn restore được qua Git history, không rewrite history.
