# CURRENT STATE — 2026-08-27

## LIVE — BETA

- Status: **BETA79 OTA LIVE PASS**.
- Version: `0.4.2-beta.79`.
- versionCode: `85` (live endpoint omits this field; normalized only after exact public bytes matched locked VC85 candidate).
- Package: `vn.pickpack1291.app.beta.publicbeta`.
- Android/candidate source SHA: `db96999844a31e7fed7d0f072fd0dd123fae1288`.
- Candidate run/artifact: `33020009122` / `9626192148`.
- Visual artifact: `9626266511`; HUMAN PASS `320x568`, `360x640`, `480x800`.
- APK SHA-256: `547e1242a7d0bb057332ce38c46313771da33235fc0e384a908c14207e26e056`.
- APK size: `13196165` bytes.
- Signer SHA-256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Final OTA workflow run/job: `33025774426` attempt 2 / `98367068517` — **SUCCESS**.
- Final OTA receipt artifact: `9628374003`; digest `sha256:b0c39c9ae2e86d0284b4b769532a8f2f5623db25295b613c57a8d6d97c8b3eae`.
- Publish mode: `REUSED_ALREADY_LIVE_EXACT`.
- Drive Beta APK ID: `1Q_5UATzS7vh4aaFtSXY7MwXQVam60n9v`.
- Drive checksum ID: `1aOtKD0LRV4f4anfblAQHdVmlyoiyrmLU`.
- OTA readback: `available=true`, version `0.4.2-beta.79`, exact SHA/size/URL; downloaded public APK matched locked candidate byte-for-byte: **PASS**.
- Google Drive folder: **BẢN THỬ NGHIỆM** `1WMXI-8-Z1mbY2v11noYFHe_eoMNiNZXg`.
- Apps Script deployment readback: version `196`; Beta79 publish did **not** change GAS code.

## BETA79 FUNCTIONAL PASS

- Old-session flow: chọn phiên cũ theo exact `session_id + MNV + business_date` và mở thẳng shared **Quét QR nhân sự** UI.
- Phiên ACTIVE cũ có đầy đủ **Thêm / Sửa / Xóa / Ra ca**; mutation giữ exact `session_id`.
- Historical Service detail inherited PASS: `3/3_SERVICE_D1_EXACT`.
- Service run/artifact inherited: `32977566159` / `9610145160`.
- Nhận hàng Rớt inherited: `CRUD_DUP_GSHEET_PASS`.
- Visual automation + human inspection PASS trên `320x568`, `360x640`, `480x800`.

## LOCKED / UNCHANGED

- Stable: `0.1.0-stable`, versionCode `1`; OTA `available=false`, `reason=NO_APK`; **UNCHANGED**.
- `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`; fresh-read unchanged.
- Authority: `SERVICE_PRIMARY / PRODUCTION`, epoch `9`, seq `94`, service generation `m2-prod-reset-20260823-001`; change: **NONE**.
- Signer unchanged.
- Beta78 is **SUPERSEDED by Beta79**.

## RELEASE / RECOVERY PATH

- Initial publish blocker `403 accessNotConfigured / SERVICE_DISABLED` was resolved after OWNER enabled `drive.googleapis.com` for Google Cloud project `92085750998`.
- First post-enable publish uploaded exact Beta79 bytes successfully, but verifier failed because live OTA JSON omitted `version_code`.
- Verifier was corrected to accept missing `version_code` only after exact SHA/size/public-byte proof.
- A transient GAS readback once returned generic `APP_GSHEET` payload; one bounded retry of the exact candidate succeeded.
- No rebuild, resign, Stable/main/authority change, or Service redeploy occurred.

## ACTIVE DEVELOPMENT BASE

- Active branch: `feature/beta78-old-session-outbound-service-20260826`.
- Functional Beta79 candidate source SHA remains `db96999844a31e7fed7d0f072fd0dd123fae1288`.
- Release harness head: `29a754976b7fc1cfa7743fa9b9d2e9336ca5a454`.
- LIVE base for next scope: **Beta79**.
- Active workflow allowlist remains `app-fast-check.yml`, `beta-release.yml`.
