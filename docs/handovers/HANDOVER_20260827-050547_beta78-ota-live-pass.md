---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-08-27T05:05:47+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: feature/beta78-old-session-outbound-service-20260826
working_head_sha: ff7945d4101ead794418b6cf8100ca14733b0837
archive_file: docs/handovers/HANDOVER_20260827-050547_beta78-ota-live-pass.md
base_or_live_version: 0.4.2-beta.78
target_version: 0.4.2-beta.78
task_state: PASS
next_action: WAIT_FOR_OWNER_NEW_SCOPE
---

# BÀN GIAO — BETA78 OTA LIVE PASS

## 1. Mục tiêu + DoD
- Chốt hạ exact checkpoint Beta78 chỉ ở OTA publish/readback; cấm rebuild/resign/rerun Service/candidate/visual.
- DoD: exact locked APK LIVE trên Beta OTA; URL/SHA/size/version exact; tải lại bytes trùng candidate; Stable/main/signer/authority unchanged; state + handoff READY.
- **Kết quả: PASS toàn bộ.**

## 2. LIVE / TARGET / CANDIDATE
### LIVE BETA78
- Version: `0.4.2-beta.78`; versionCode `84`; package `vn.pickpack1291.app.beta.publicbeta`.
- Source SHA: `9f5d309e13bce62381784d3e53b019bf80d5dfbe`.
- Candidate run/artifact: `32978373007` / `9610518473`.
- APK SHA256: `73ebd3015f214f168af484433b3591b6ed85e784280e9a9f7e38a405291f2c6b`.
- Size: `13196165` bytes.
- Signer SHA256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Drive Beta APK ID: `196jnKIIobImlA57TuDO7f-aJC0andzet`.
- Drive checksum ID: `1CPSIyjiNMwZHWYXp2kf7Edr9hZ3WgNxe`.
- Drive Beta folder **BẢN THỬ NGHIỆM**: `1WMXI-8-Z1mbY2v11noYFHe_eoMNiNZXg`.
- OTA URL: `https://drive.usercontent.google.com/download?id=196jnKIIobImlA57TuDO7f-aJC0andzet&export=download&confirm=t`.
- Published timestamp from live readback: `2026-08-26T14:22:01.526Z`.

### VISUAL / SERVICE LOCK
- Visual artifact `9610678167`; HUMAN PASS `320x568`, `360x640`, `480x800`.
- Service run/artifact `32977566159` / `9610145160`.
- Historical exact-session result: `3/3_SERVICE_D1_EXACT`.
- Outbound result: `CRUD_DUP_GSHEET_PASS`.
- Apps Script version `194`; OTA closeout made no GAS code change.

## 3. Final OTA evidence
- Final run: `33018048229` — **SUCCESS**.
- Job: `98341294224` — `publish` SUCCESS.
- Receipt artifact: `9625382187`; digest `sha256:e6c7b803af6a132b7df111af746423fcc7f312fb926a2934990691df1a6fe2d0`.
- Receipt status: `PASS`; publish mode: `REUSED_ALREADY_LIVE_EXACT`.
- Live Beta readback: `available=true`, versionName `0.4.2-beta.78`, normalized/verified versionCode `84`, SHA `73ebd301...`, size `13196165`, exact OTA URL above.
- Public OTA APK downloaded again in final run: SHA256 full exact candidate, size exact, `cmp` byte-for-byte **PASS**.
- Connected Drive fresh-read: exact APK ID/name/MIME/size is inside Beta folder **BẢN THỬ NGHIỆM**; checksum file for Beta78 is present there.
- Stable before/after identical: `available=false`, `reason=NO_APK`.
- Fresh `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`, unchanged.
- Authority: `SERVICE_PRIMARY / PRODUCTION`, epoch `9`, generation `m2-prod-reset-20260823-001`; authority change `NONE`.
- Trigger-only PR `#136` closed without merge.

## 4. File/commit đã đổi
- `tools/publish_beta78_ota.sh`
  - runtime closeout commit: `ff7945d4101ead794418b6cf8100ca14733b0837`.
  - thay đổi chỉ ở verifier/transport: exact-target-already-live -> readback-only; không app/service/GAS source change.
- `CURRENT_STATE.md` updated to Beta78 LIVE in final handoff commit.
- `docs/handovers/HANDOVER_CURRENT.md` + archive này written together in final handoff commit.

## 5. Lỗi + root cause + đường PASS
| Fingerprint | Root cause | Đường PASS | Cấm lặp |
|---|---|---|---|
| Run `32988058753` HTTP 403 tại Drive-folder metadata | OAuth/Drive verifier path không có quyền metadata folder phù hợp, trong khi Beta78 exact APK + OTA đã LIVE | bỏ dependency verifier này khi live feed đã exact; tải public OTA bytes, verify SHA/size/cmp candidate + Stable/main/authority | không retry OAuth/Drive folder call; không rebuild/resign/reupload exact bytes |
| OTA response raw không có `version_code` | live Drive OTA contract cũ không emit field này | chỉ normalize VC84 sau khi public OTA bytes bằng exact locked candidate có release-meta VC84 | không bịa VC nếu bytes/meta không exact |

## 6. Workspace / CI / external state
- Active branch: `feature/beta78-old-session-outbound-service-20260826`.
- Runtime/code closeout head: `ff7945d4101ead794418b6cf8100ca14733b0837`.
- Final OTA run `33018048229`: terminal SUCCESS; không còn run cần poll.
- Exact candidate bytes unchanged từ artifact `9610518473`.
- Stable/main/signer/authority/provider unchanged.
- Blocker: **NONE**.

## 7. Việc còn lại
- **NONE cho scope Beta78.**
- Không cần OWNER thao tác thêm.

## 8. Invariants
- Không rebuild/resign/revisual/rerun Service Beta78 khi source/artifact bytes không đổi.
- Không mutation lại Drive/GAS chỉ để xác minh exact Beta78 đã LIVE; dùng readback.
- Stable/main/signer/authority/provider giữ nguyên nếu OWNER chưa ra scope mới.
- Beta78 LIVE identity phải giữ đúng version/code/package/SHA/size/signer/Drive ID/OTA URL ở mục 2.
- Beta77 là SUPERSEDED.

## 9. NEXT_ACTION
`WAIT_FOR_OWNER_NEW_SCOPE`

## 10. Retention
- Archive mới: `docs/handovers/HANDOVER_20260827-050547_beta78-ota-live-pass.md`.
- Sau khi thêm archive mới, prune timestamp archive cũ nhất `HANDOVER_20260825-190249_beta74-ota-live-pass.md` khỏi active tree; vẫn restore được qua Git history.
