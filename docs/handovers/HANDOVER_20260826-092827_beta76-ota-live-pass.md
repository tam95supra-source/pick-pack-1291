---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-08-26T09:28:27+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: feature/beta76-nhan-hang-rot-20260825
working_head_sha: 1af38202aec4b60ed049a803d4109f403fb27340
archive_file: docs/handovers/HANDOVER_20260826-092827_beta76-ota-live-pass.md
base_or_live_version: 0.4.2-beta.76
target_version: 0.4.2-beta.76
task_state: PASS
next_action: WAIT_FOR_OWNER_NEW_SCOPE
---

# BÀN GIAO — BETA76 OTA LIVE PASS

## 1. Mục tiêu + DoD
- OWNER yêu cầu tiếp tục exact checkpoint Beta76, kiểm tra OAuth token mới và hoàn tất việc pending bằng chính candidate đã khóa.
- DoD: token usable → exact Beta76 publish/readback PASS → Beta76 LIVE → Beta75 SUPERSEDED → Stable/main/signer/authority unchanged → state/receipt/handoff cập nhật.
- **Kết quả: PASS toàn bộ.**

## 2. LIVE / TARGET / CANDIDATE
### LIVE
- Beta: `0.4.2-beta.76`, versionCode `82`, package `vn.pickpack1291.app.beta.publicbeta`.
- Source SHA: `0d81793eabf465716a4fe36038d143b11220667f`.
- Candidate run/artifact: `32875201581` / `9573716441`.
- APK SHA256: `7018977f28d09434de27e6c6e90a7a51ec11c77831285d7e466c7aeeeeef9ee2`.
- Size: `13179781` bytes.
- Signer SHA256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Drive APK ID: `1uxfoNvcPLJUxpPxo-XwAb12ZZasX4Heb`.
- Drive checksum ID: `1IxZLvxRjfDCmRZTIVNyOqSaWdXhneGjH`.
- OTA URL: `https://drive.usercontent.google.com/download?id=1uxfoNvcPLJUxpPxo-XwAb12ZZasX4Heb&export=download&confirm=t`.
- Published timestamp từ feed/Drive: `2026-08-26T02:17:12.735Z`.

### VISUAL LOCK
- Final HUMAN matrix run/artifact: `32906107089` / `9584898561`.
- Artifact digest: `sha256:c02316956d161629d6c8f079171cf51572931fb2ddc3e137b56c9a9429faf7f5`.
- Receipt: `ops/beta76-visual-inspection.json`; commit `aa3123d3b0c20230f441c3db9aaf9d516c9e481e`.
- HUMAN PASS đủ `320x568`, `360x640`, `480x800`; không rebuild/sign sau candidate lock.

### SUPERSEDED / UNCHANGED
- Beta75: **SUPERSEDED by Beta76**; SHA `6e08dc974281cc7b5428d22cf406179447cdeb95443dc19fa1db2b4d32344913`.
- Stable: `0.1.0-stable`, code `1`, feed vẫn `available=false`, `reason=NO_APK`; publish FORBIDDEN.
- `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`, fresh-read unchanged.
- Signer/Worker/Service/authority/provider unchanged.

## 3. Evidence PASS
- OAuth refresh token mới: **PASS**; rerun `32907203640` vượt OAuth và thực hiện được Apps Script/Drive path. Không lưu secret/token vào repo/handoff.
- Production mutation làm Beta76 LIVE xảy ra trong rerun của `32907203640`; lỗi sau đó chỉ là verifier Drive-v3, không phải publish/bytes.
- Final readback-only run `32922737926`: **SUCCESS**.
- Final release evidence artifact: `9590374981`; digest `sha256:1eaabc48b6ef0515572ea629535cacf65886cb88442fcd99ec4c5edeba538fa2`.
- Receipt repo: `ops/beta76-release-result.json`, verdict `PASS`.
- Beta75 client: `available=true` → Beta76 code 82, exact SHA/size.
- Beta76 client: `available=false`, version/code đúng OTA contract.
- Fresh Drive metadata: tên APK đúng, MIME APK, size `13179781`, parent Beta folder, anyone-reader.
- Fresh raw Drive bytes: SHA256 `7018977f...ef9ee2`, size `13179781`.
- Fresh checksum: exact SHA + exact APK filename.
- Stable before/after identical; main fresh-read unchanged.

## 4. File/commit đã đổi
- `tools/publish_beta76_ota.sh`: sửa verifier/readback idempotent; không Android source/build/sign.
  - `74a673abee89053a05c43238e1a1ee4f75df6171`: bỏ dependency verifier Drive API lỗi.
  - `3eea2923fcbf72f18d7a92b1710b01c3ebbf17de`, `2fc567bc64ee920bb1f6e4b1d65a59ee30855f5c`: sửa harness anchor đến preflight PASS.
  - `af9517921e86c7eae5cbe3ff6812d66a583e9133`: cho phép exact target đã LIVE.
  - `b73e012a8db066421bf87209163519369a783e58`: readback-only khi exact Beta76 đã LIVE, cấm lặp production mutation.
- `ops/beta76-release-result.json`: release receipt PASS, commit `d577a21330dad51d283739ff1875f4079366305d`.
- `CURRENT_STATE.md`: Beta76 LIVE PASS, commit `1af38202aec4b60ed049a803d4109f403fb27340`.

## 5. Lỗi + root cause + đường PASS
| Fingerprint | Root cause | Đường PASS | Cấm lặp |
|---|---|---|---|
| `invalid_grant / Token has been expired or revoked` | refresh token OAuth cũ hết hạn/revoked | OWNER cấp refresh token mới đúng client/account; CI đã xác nhận dùng được | không retry token cũ; không đổi client/authority |
| HTTP 403 tại Drive v3 metadata readback | verifier phụ không có đường API phù hợp, trong khi Drive transport/OTA/public bytes đã thành công | dùng connected Drive fresh-read cho metadata; giữ exact public/Drive bytes + checksum verifier | không rebuild/resign; không coi là APK/publish fail |
| rerun sau LIVE trả `UNAUTHORIZED` ở temporary upload helper | publisher không idempotent với exact target đã LIVE | readback-only khi feed đã exact Beta76; không mutation lại | không chạy helper/upload lần nữa khi target exact đã LIVE |
| patch anchor drift | harness patch phụ thuộc chuỗi whitespace | chuyển sang exact URL-block marker; preflight PASS | không retry cùng anchor cũ |

## 6. Workspace / CI / external state
- Active branch: `feature/beta76-nhan-hang-rot-20260825`.
- Working head trước handoff: `1af38202aec4b60ed049a803d4109f403fb27340`.
- Final run `32922737926`: SUCCESS; không còn run cần poll.
- Exact candidate bytes không đổi từ artifact `9573716441`.
- Drive/OTA đang LIVE Beta76; không có partial state cần recovery.
- OAuth app vẫn thuộc client/account hiện có; không đổi provider/authority. Việc Production/domain OAuth dài hạn chưa thuộc scope Beta76 và không được tự thêm.
- Blocker: **NONE**.

## 7. Việc còn lại
- **NONE cho scope Beta76.**
- Không cần OWNER thao tác thêm.

## 8. Invariants
- Không rebuild/resign/revisual Beta76 khi source/artifact bytes không đổi.
- Stable/main/signer/authority/provider giữ nguyên nếu OWNER chưa ra scope mới.
- Beta76 LIVE identity phải giữ đúng version/code/package/SHA/size/signer/Drive IDs ở mục 2.
- Beta75 là SUPERSEDED.
- Không tái chạy publisher mutation chỉ để xác minh exact Beta76 đã LIVE; dùng readback.

## 9. NEXT_ACTION
`WAIT_FOR_OWNER_NEW_SCOPE`

## 10. Retention
- Archive mới: `HANDOVER_20260826-092827_beta76-ota-live-pass.md`.
- Giữ 5 timestamp archive mới nhất sau prune; archive cũ nhất `HANDOVER_20260825-174900_beta73-live-pass-session-transfer.md` được prune khỏi active tree, vẫn restore qua Git history.
