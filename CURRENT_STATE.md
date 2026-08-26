# CURRENT STATE — 2026-08-27

## LIVE — BETA

- Status: **BETA78 OTA LIVE PASS**.
- Version: `0.4.2-beta.78`.
- versionCode: `84`.
- Package: `vn.pickpack1291.app.beta.publicbeta`.
- Android/candidate source SHA: `9f5d309e13bce62381784d3e53b019bf80d5dfbe`.
- Candidate run/artifact: `32978373007` / `9610518473`.
- APK SHA-256: `73ebd3015f214f168af484433b3591b6ed85e784280e9a9f7e38a405291f2c6b`.
- APK size: `13196165` bytes.
- Signer SHA-256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Visual artifact: `9610678167`; HUMAN PASS `320x568`, `360x640`, `480x800`.
- Final OTA run/job: `33018048229` / `98341294224` — **SUCCESS**.
- Final OTA receipt artifact: `9625382187`; digest `sha256:e6c7b803af6a132b7df111af746423fcc7f312fb926a2934990691df1a6fe2d0`.
- Drive Beta APK ID: `196jnKIIobImlA57TuDO7f-aJC0andzet`.
- Drive Beta checksum ID: `1CPSIyjiNMwZHWYXp2kf7Edr9hZ3WgNxe`.
- OTA URL: `https://drive.usercontent.google.com/download?id=196jnKIIobImlA57TuDO7f-aJC0andzet&export=download&confirm=t`.
- OTA readback: `available=true`, version `0.4.2-beta.78`, versionCode `84`, SHA/size/URL exact candidate; public downloaded bytes compared byte-for-byte with locked candidate: **PASS**.
- Drive readback: APK `pick-pack-1291-public-beta-0.4.2-beta.78.apk`, MIME APK, size `13196165`, located in folder **BẢN THỬ NGHIỆM** `1WMXI-8-Z1mbY2v11noYFHe_eoMNiNZXg`.

## BETA78 FUNCTIONAL PASS INHERITED

- Service run/artifact: `32977566159` / `9610145160`.
- Historical old-session exact identity: `3/3_SERVICE_D1_EXACT`.
- Outbound/Drop Receive: `CRUD_DUP_GSHEET_PASS`.
- Apps Script production version: `194`; final OTA closeout did **not** change GAS code.
- Service authority remains `SERVICE_PRIMARY / PRODUCTION`, epoch `9`, service generation `m2-prod-reset-20260823-001`; authority change: **NONE**.

## LOCKED / UNCHANGED

- Stable: `0.1.0-stable`, versionCode `1`; OTA `available=false`, `reason=NO_APK`; publish **FORBIDDEN/UNCHANGED**.
- `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`, fresh-read unchanged.
- Signer unchanged: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Provider/authority unchanged.
- Beta77 is **SUPERSEDED by Beta78**.

## RELEASE / RECOVERY PATH

- Latest failed OTA verifier run `32988058753` failed at Drive-folder metadata call with HTTP 403 after live Beta OTA already pointed to exact Beta78 bytes.
- Root cause classified as transport/verifier path, not APK or release bytes.
- Minimal PASS path: `tools/publish_beta78_ota.sh` now detects exact target already LIVE and performs readback-only verification of OTA bytes + Stable/main/authority invariants; no Drive/GAS rewrite, no rebuild/resign/version bump.
- Final run `33018048229` succeeded with `publish_mode=REUSED_ALREADY_LIVE_EXACT`.

## ACTIVE DEVELOPMENT BASE

- Active branch: `feature/beta78-old-session-outbound-service-20260826`.
- Runtime/code closeout head: `ff7945d4101ead794418b6cf8100ca14733b0837`.
- LIVE base for next scope: **Beta78**.
- Active workflow allowlist remains `app-fast-check.yml`, `beta-release.yml`.
