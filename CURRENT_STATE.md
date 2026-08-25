# CURRENT STATE — 2026-08-25

## LIVE — BETA

- Status: **Beta73 OTA LIVE PASS**
- Version: `0.4.2-beta.73`
- versionCode: `79`
- Package: `vn.pickpack1291.app.beta.publicbeta`
- Lineage: Beta68 golden base → Beta71 → Beta72 → OWNER Beta73 session/resource/settings/login fixes. Beta69/Beta70 source is not a base.
- Android source SHA: `2d726828bdd83efe21e9cd41db8d5c06d16f5272`
- Candidate run/artifact: `32820317675` / `9552942024`
- Final Settings visual run/artifact: `32834871019` / `9558250565`
- Release run/evidence artifact: `32837337470` / `9559169643`
- APK SHA-256: `ad037c1a17d245f90ead59539c5595cc5df6a568b8657ce636cc43d101175fd2`
- APK size: `13130629`
- Signer SHA-256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`
- Signer proof: exact published/Drive bytes match locked signed candidate bytes.
- Drive APK: `1YbOScnsvPH4mQbyekKQc-EzlF1glG9be`
- Drive checksum: `1n6n40syMn3eHiJtcJojr6_FBokF4V9jR`
- OTA source: `GOOGLE_DRIVE`; exact locked bytes.
- OTA URL: `https://drive.usercontent.google.com/download?id=1YbOScnsvPH4mQbyekKQc-EzlF1glG9be&export=download&confirm=t`
- OTA readback: Beta72 client sees `available=true`, version `0.4.2-beta.73`, versionCode `79`, SHA/size exact; Beta73 client sees `available=false`, version `0.4.2-beta.73`, versionCode `79`.
- Fresh Drive readback: name `pick-pack-1291-public-beta-0.4.2-beta.73.apk`, size `13130629`, public reader; downloaded bytes SHA-256 exact `ad037c1a...5fd2`.
- Human visual inspection: **PASS** tại `320x568`, `360x640`, `480x800`; Settings top có `ĐỔI MẬT KHẨU`, lower frame có `NHẬT KÝ`; không wrong-screen/crop/overflow. Gate API29 dùng `am start -W + dumpsys activity/window + real PNG + human pixels`, không dùng UiAutomation đã biết treo.
- Forgot-password preview GAS readback: **PASS**; user + trường email tồn tại; không log email nhạy cảm.
- Rebuild/resign sau candidate lock: **không**.
- Receipt: `ops/beta73-release-result.json`.

## LOCKED / UNCHANGED

- Stable publish: **FORBIDDEN**; feed trước/sau giống hệt: `available=false`, `reason=NO_APK`.
- Stable source identity trong candidate: `0.1.0-stable`, versionCode `1`.
- `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`, fresh-read unchanged.
- Signer: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`, unchanged.
- Worker/Service authority change: **NONE**; Worker không deploy.
- GAS change: approved `forgot_password_preview` + OTA Beta versionCode compatibility shim only; temporary exact-Drive upload route removed after publish.
- Authority/provider: unchanged.

## SUPERSEDED / ABANDONED

- Beta69: bỏ khỏi active lineage; không phát hành, không làm base.
- Beta70: không làm base.
- Beta71: historical only.
- Beta72: superseded by Beta73; previous SHA `fdeb006122f065591e82fe912a4a615c9c42a149568c2fc32f7d5b35db353caf`.
- UiAutomation/Instrumentation Settings gate trên API29: superseded do deterministic hang; không dùng lại.

## ACTIVE DEVELOPMENT BASE

- Nhánh continuity: `release/beta71-clean-from-beta68-20260825`.
- LIVE base cho scope tiếp theo: Beta73 ở trên.
- Android source identity phát hành Beta73: `2d726828bdd83efe21e9cd41db8d5c06d16f5272`.
- Active workflow allowlist không đổi: `app-fast-check.yml`, `beta-release.yml`.
