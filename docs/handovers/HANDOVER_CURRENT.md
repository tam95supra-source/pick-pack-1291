---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-08-26T18:25:30+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: feature/beta77-owner-fixes-20260826
working_head_sha: bff5b4de9db1cdbbd2e2a880723923cc891e1300
archive_file: docs/handovers/HANDOVER_20260826-182530_beta77-ota-live-pass.md
base_or_live_version: 0.4.2-beta.77
target_version: 0.4.2-beta.77
task_state: WAIT_FOR_OWNER_NEW_SCOPE
next_action: WAIT_FOR_OWNER_NEW_SCOPE
---

# BÀN GIAO CANONICAL — BETA77 OTA LIVE PASS

## 1. Kết quả / DoD
- **BETA77 OTA LIVE PASS**.
- OTA / Drive / public bytes / LIVE readback khớp exact candidate.
- Stable không publish và readback trước/sau không đổi.
- `main`, signer, authority, provider không đổi.
- Không rebuild, resign, version bump, Beta78, GAS canonical rerun hoặc Service/PDA rerun.
- Không còn blocker OWNER trong scope Beta77.

## 2. LIVE / exact locked identity
- Source: `43579d1f7f01816cddbdbbcce0a2f19d95d16d91`.
- Candidate run/artifact: `32953924512` / `9601304499`.
- Version: `0.4.2-beta.77`.
- versionCode: `83`.
- Package: `vn.pickpack1291.app.beta.publicbeta`.
- SHA256: `6ce7838f6f0725ca98b4f3d9237d38aec60092f4488b2795a32ae3f9d24371fb`.
- Size: `13196165` bytes.
- Signer: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.

## 3. Visual receipt — PASS, không rerun
- Final HUMAN visual run/artifact: `32960147493` / `9603638990`.
- Receipt commit: `847378116153befe7b10a29951df43913e864636`.
- HUMAN PASS: `320x568`, `360x640`, `480x800`.
- Visual dùng exact candidate; không Android build/sign trong visual.
- Lỗi gốc ban đầu `UI hierarchy unavailable` là harness defect do hard dependency UiAutomation, không phải APK. Đường PASS: UiAutomation optional; route/activity/window + screenshot evidence; không rebuild APK.

## 4. Canonical backend PASS — không rerun
- GAS: run `32932894375`, Apps Script version `194`, artifact `9593853159`, digest `sha256:2b939d18e7db7e74925771516925716f6a4c98e1c7ed3a2c92c9418a0e86fcc1`.
- Service/PDA LIVE: run `32953215533`, artifact `9600983380`, worker version `0cd7e517-a03b-4dae-80e3-8acb0f437c84`, digest `sha256:b4da9784cd70eb7b2384c901c0e404104091fed208225032efa4417b4bf9ec36`.

## 5. Publish / LIVE evidence
- Exact publish/readback run/job: `32962971229` / `98159194235`.
- Release evidence artifact: `9604622754`, artifact ZIP digest `sha256:2440f01c8571cf38d7f02a7043f438b204f6b660b1ebf604b154bce99c91bc3e`.
- Drive APK ID: `1N2y2VtsQVs2PNTKsEQP6Bl4eIbNBpAz1`.
- Drive checksum ID: `15YbzW_xs2MVur3t3jSJoApS_AMUAg0R3`.
- OTA URL points to Drive APK above.
- Beta-after readback: `available=true`, Beta77/code83, SHA/size exact candidate.
- Beta77 current-version readback: `available=false` with Beta77/code83/size contract, as expected for current version.
- Drive transport/checksum/public bytes: exact SHA `6ce7838f6f0725ca98b4f3d9237d38aec60092f4488b2795a32ae3f9d24371fb`, size `13196165`.
- Release receipt: `ops/beta77-release-result.json`, verdict `PASS`, persisted by connector commit `5fd1e234f6107b05ef6f75be4818bd96ed21549a`.
- `CURRENT_STATE.md` promoted to Beta77 LIVE by commit `bff5b4de9db1cdbbd2e2a880723923cc891e1300`.

## 6. Stable / main / authority invariants
- Stable before/after: `available=false`, `reason=NO_APK`.
- Stable identity remains `0.1.0-stable`, versionCode `1`.
- Fresh-read `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`, unchanged.
- Signer unchanged: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Service change: `NONE`.
- Authority change: `NONE`.
- Provider unchanged.

## 7. Failure / root cause / đường PASS đã dùng
- Publish materializer gặp các lỗi deterministic kế thừa Beta76: semantic version cascade, stale candidate/visual receipt IDs, legacy `service_change` metadata gate, và final assertion còn kiểm `compat76` sau khi route đã nâng thành `compat77`.
- Từng lỗi được sửa đúng verifier/materializer; exact APK bytes giữ nguyên.
- Run cuối `32962971229` đã hoàn thành production publish + LIVE verification rồi mới đỏ ở bước cuối `git push` receipt vì workflow chỉ có `contents: read`; log có local commit `ops: record Beta77 OTA PASS`, sau đó GitHub 403 cho bot.
- Đây là receipt-persistence harness failure sau PASS, không được rerun publish. Receipt/state được persist bằng GitHub connector.
- Cấm lặp: không coi workflow đỏ sau PASS receipt là release failure; kiểm evidence trước rồi chỉ sửa persistence/permission harness nếu scope sau cần.

## 8. File / commit đã đổi ở closeout
- `tools/publish_beta77_ota.sh`: sửa materializer/verifier deterministic, không sửa Android source.
- `.github/workflows/beta-release.yml`: deterministic trigger cho exact publish; workflow không được cấp quyền Stable/main.
- `ops/beta77-release-result.json`: PASS receipt, commit `5fd1e234f6107b05ef6f75be4818bd96ed21549a`.
- `CURRENT_STATE.md`: Beta77 OTA LIVE PASS, commit `bff5b4de9db1cdbbd2e2a880723923cc891e1300`.
- `docs/handovers/HANDOVER_CURRENT.md` + archive này: READY closeout.

## 9. Workspace / CI / external state
- Active branch: `feature/beta77-owner-fixes-20260826`.
- Functional/state working head before handoff writes: `bff5b4de9db1cdbbd2e2a880723923cc891e1300`.
- Active workflow allowlist giữ nguyên: `app-fast-check.yml`, `beta-release.yml`.
- Beta77 là LIVE base cho scope tiếp theo.
- Evidence artifact có OAuth response phục vụ CI; không đưa token/secret vào repo hoặc bàn giao.

## 10. Blocker / quyền
- Blocker OWNER: **NONE**.
- Không cần OWNER cấp thêm quyền để chốt Beta77.

## 11. NEXT_ACTION
`WAIT_FOR_OWNER_NEW_SCOPE`
