# CURRENT STATE — 2026-08-26

## LIVE — BETA

- Status: **BETA77 OTA LIVE PASS**
- Version: `0.4.2-beta.77`
- versionCode: `83`
- Package: `vn.pickpack1291.app.beta.publicbeta`
- Android source SHA: `43579d1f7f01816cddbdbbcce0a2f19d95d16d91`.
- Candidate run/artifact: `32953924512` / `9601304499`.
- APK SHA-256: `6ce7838f6f0725ca98b4f3d9237d38aec60092f4488b2795a32ae3f9d24371fb`.
- APK size: `13196165` bytes.
- Signer SHA-256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Final HUMAN visual run/artifact: `32960147493` / `9603638990`; receipt commit `847378116153befe7b10a29951df43913e864636`; HUMAN PASS `320x568`, `360x640`, `480x800`.
- Exact-byte publish/readback run: `32962971229`, job `98159194235`.
- Release evidence artifact: `9604622754`.
- Drive APK ID: `1N2y2VtsQVs2PNTKsEQP6Bl4eIbNBpAz1`.
- Drive checksum ID: `15YbzW_xs2MVur3t3jSJoApS_AMUAg0R3`.
- OTA URL: `https://drive.usercontent.google.com/download?id=1N2y2VtsQVs2PNTKsEQP6Bl4eIbNBpAz1&export=download&confirm=t`.
- OTA readback: previous Beta client sees Beta77 `available=true`; Beta77 current-version readback returns `available=false` while retaining version/code/size contract.
- Drive transport/checksum/public bytes: exact candidate SHA-256 `6ce7838f6f0725ca98b4f3d9237d38aec60092f4488b2795a32ae3f9d24371fb`, size `13196165`.
- Release receipt: `ops/beta77-release-result.json`, verdict `PASS`.
- Workflow itself ended red only after PASS receipt was locally committed: `github-actions[bot]` had `contents: read`, so final `git push` receipt returned 403. Production publish and LIVE verification had already completed; receipt was persisted afterward through the GitHub connector without rerunning publish.

## BETA77 SCOPE

- Nhận hàng Rớt: vị trí đúng; rỗng hiển thị `Chưa có vị trí`; OWNER có Tạo / Sửa / Xóa.
- Quét QR nhân sự: dữ liệu rỗng hiển thị `-`; giữ phiên PDA ACTIVE cùng ngày/xuyên ngày theo scope đã chốt.
- Đổi / Trả PDA và luồng ra sớm hiển thị đúng.
- Visual harness không còn bắt buộc UiAutomation hierarchy; exact APK không rebuild/resign trong quá trình sửa harness/release.

## CANONICAL PASS — KHÔNG RERUN

- GAS: run `32932894375`, Apps Script version `194`, artifact `9593853159`, digest `sha256:2b939d18e7db7e74925771516925716f6a4c98e1c7ed3a2c92c9418a0e86fcc1`.
- Service/PDA LIVE: run `32953215533`, artifact `9600983380`, worker version `0cd7e517-a03b-4dae-80e3-8acb0f437c84`, digest `sha256:b4da9784cd70eb7b2384c901c0e404104091fed208225032efa4417b4bf9ec36`.

## LOCKED / UNCHANGED

- Stable publish: **FORBIDDEN**; before/after readback both `available=false`, `reason=NO_APK`.
- Stable source identity remains `0.1.0-stable`, versionCode `1`.
- `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`, fresh-read unchanged after Beta77 publish.
- Signer unchanged: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Worker/Service change: **NONE**.
- Authority change: **NONE**.
- Provider unchanged.
- No rebuild, resign, version bump, Beta78, GAS canonical rerun, or Service/PDA rerun.

## SUPERSEDED

- **Beta76: SUPERSEDED by Beta77**; previous SHA `7018977f28d09434de27e6c6e90a7a51ec11c77831285d7e466c7aeeeeef9ee2`, size `13179781`.
- Beta69/Beta70: ABANDONED.
- Beta71–Beta75: historical/superseded.

## RELEASE / RECOVERY PATH

- Original visual failure `320x568-employee-home: UI hierarchy unavailable` was visual-harness-only; UiAutomation hard dependency was removed and final HUMAN matrix passed with exact candidate.
- Publish materializer deterministic defects were fixed without APK rebuild: semantic Beta76→Beta77 shift, stale receipt identities, legacy candidate metadata gate, and inherited final `compat76` assertion after route promotion to `compat77`.
- Run `32962971229` completed exact Drive transport, OTA compatibility update and LIVE/readback verification. Its only terminal failure was repository receipt push permission after PASS; no release retry was needed.

## ACTIVE DEVELOPMENT BASE

- Working/continuity branch: `feature/beta77-owner-fixes-20260826`.
- LIVE base for next scope: Beta77 above.
- Android source identity: `43579d1f7f01816cddbdbbcce0a2f19d95d16d91`.
- Active workflow allowlist: `app-fast-check.yml`, `beta-release.yml`.
