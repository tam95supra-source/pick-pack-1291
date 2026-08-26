# CURRENT STATE — 2026-08-26

## LIVE — BETA

- Status: **BETA76 OTA LIVE PASS**
- Version: `0.4.2-beta.76`
- versionCode: `82`
- Package: `vn.pickpack1291.app.beta.publicbeta`
- Android source SHA: `0d81793eabf465716a4fe36038d143b11220667f`.
- Candidate run/artifact: `32875201581` / `9573716441`.
- APK SHA-256: `7018977f28d09434de27e6c6e90a7a51ec11c77831285d7e466c7aeeeeef9ee2`.
- APK size: `13179781` bytes.
- Signer SHA-256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Final HUMAN visual run/artifact: `32906107089` / `9584898561`; receipt `ops/beta76-visual-inspection.json`, commit `aa3123d3b0c20230f441c3db9aaf9d516c9e481e`; HUMAN PASS `320x568`, `360x640`, `480x800`.
- Production mutation that made exact Beta76 LIVE occurred during rerun of `32907203640` after OAuth refresh was repaired; later failure was verifier-only after exact Drive/OTA write.
- Final readback-only release run: `32922737926` — **SUCCESS**.
- Release evidence artifact: `9590374981`; digest `sha256:1eaabc48b6ef0515572ea629535cacf65886cb88442fcd99ec4c5edeba538fa2`.
- Drive APK ID: `1uxfoNvcPLJUxpPxo-XwAb12ZZasX4Heb`.
- Drive checksum ID: `1IxZLvxRjfDCmRZTIVNyOqSaWdXhneGjH`.
- OTA URL: `https://drive.usercontent.google.com/download?id=1uxfoNvcPLJUxpPxo-XwAb12ZZasX4Heb&export=download&confirm=t`.
- OTA readback: Beta75 client thấy Beta76 `available=true`; Beta76 client `available=false` và version/code đúng contract.
- Fresh Drive metadata: file `pick-pack-1291-public-beta-0.4.2-beta.76.apk`, MIME APK, size `13179781`, shared anyone-reader; public/downloaded bytes SHA-256 exact candidate; checksum exact.
- Release receipt: `ops/beta76-release-result.json`, verdict `PASS`.

## BETA76 SCOPE

- Nhận hàng rớt: chọn `Vị trí`; OWNER có Tạo / Sửa / Xóa.
- Scan QR tự tách DO và Số kiện; vẫn hỗ trợ nhập tay khi QR sai.
- Thêm thông tin ghi theo đường GAS/Sheet đã chốt với idempotency/readback.
- Xóa toàn bộ chỉ dành cho superadmin; giữ header/tab/quyền/danh sách Vị trí.
- Sheet/permission và app/logic đã PASS trước candidate lock; không rerun khi bytes không đổi.

## LOCKED / UNCHANGED

- Stable publish: **FORBIDDEN**; fresh readback vẫn `available=false`, `reason=NO_APK`.
- Stable source identity: `0.1.0-stable`, versionCode `1`.
- `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`, fresh-read unchanged.
- Signer unchanged: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Worker/Service change: **NONE**.
- Authority change: **NONE**.
- GAS production change: `OTA_VERSION_COMPAT_BETA76` only; temporary exact-Drive helper không thuộc trạng thái cuối.
- Provider unchanged.

## SUPERSEDED / ABANDONED

- **Beta75: SUPERSEDED by Beta76**; previous SHA `6e08dc974281cc7b5428d22cf406179447cdeb95443dc19fa1db2b4d32344913`.
- Beta69/Beta70: ABANDONED; không thuộc active base.
- Beta71/Beta72/Beta73/Beta74: historical/superseded.

## RELEASE / RECOVERY PATH

- OAuth blocker `invalid_grant` được OWNER sửa bằng refresh token mới của đúng OAuth client/account hiện có; token mới đã được CI sử dụng thành công.
- Exact Beta76 bytes được giữ nguyên toàn bộ; không rebuild/resign/version bump.
- Sau production write, direct Drive-v3 metadata verifier trả 403 dù Drive transport/public bytes/OTA đã thành công; xác định là verifier/harness defect.
- Connected Drive fresh-read xác nhận metadata; publisher được sửa readback-only/idempotent để không lặp production mutation khi exact Beta76 đã LIVE.
- Final run `32922737926` PASS toàn bộ readback-only: OTA, public/Drive bytes, checksum, Stable và main.

## ACTIVE DEVELOPMENT BASE

- Working branch tại release closeout: `feature/beta76-nhan-hang-rot-20260825`.
- Continuity branch mặc định của dự án vẫn `release/beta71-clean-from-beta68-20260825` cho tới khi OWNER ra scope mới/handoff mới chỉ định khác.
- LIVE base cho scope tiếp theo: Beta76 ở trên.
- Android source identity: `0d81793eabf465716a4fe36038d143b11220667f`.
- Active workflow allowlist: `app-fast-check.yml`, `beta-release.yml`.
