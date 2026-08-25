# CURRENT STATE — 2026-08-25

## LIVE — BETA

- Status: **BETA75 OTA LIVE PASS**
- Version: `0.4.2-beta.75`
- versionCode: `81`
- Package: `vn.pickpack1291.app.beta.publicbeta`
- Android source SHA: `e475b8476e99a9230683dbbf6ec266235960ed5b`
- Candidate run/artifact: `32849057694` / `9563625638`.
- Final HUMAN visual run/artifact: `32860235560` / `9568028848`; visual receipt `ops/beta75-visual-inspection.json`, commit `007795a656fa14236ed766b164ca80bb5872fb32`; HUMAN PASS `320x568`, `360x640`, `480x800`.
- Final publish run/evidence artifact: `32865705207` / `9570048273`.
- Release evidence digest: `sha256:09707dc2c8feeab71fdcc8aab74b5628fc713c09d019b9357f49f8aca62439be`.
- APK SHA-256: `6e08dc974281cc7b5428d22cf406179447cdeb95443dc19fa1db2b4d32344913`.
- APK size: `13147013` bytes.
- Signer SHA-256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Drive APK ID: `1A0T5HL2HD-On1Oc4A3G3Rd0qZAlbFwWz`.
- Drive checksum ID: `1okPTtleBKOUb9L-HLbV94ImQqu5iorSv`.
- OTA URL: `https://drive.usercontent.google.com/download?id=1A0T5HL2HD-On1Oc4A3G3Rd0qZAlbFwWz&export=download&confirm=t`.
- Publisher post-write OTA readback: Beta74 client `available=true` → Beta75 VC81 SHA/size exact; Beta75 client `available=false` with version Beta75 VC81.
- Fresh authenticated Drive readback after publish: file `pick-pack-1291-public-beta-0.4.2-beta.75.apk`, MIME APK, size `13147013`; downloaded bytes SHA-256 exact `6e08dc974281cc7b5428d22cf406179447cdeb95443dc19fa1db2b4d32344913`; checksum file matches.
- Release receipt: `ops/beta75-release-result.json`, verdict `PASS`.

## BETA75 FIX SCOPE

- Đổi/Trả PDA: nút hành động riêng, Serial/tình trạng rõ, giao diện gọn; giữ reason list đã chốt.
- Quét QR nhân sự: bỏ dòng Vị trí trong ca trùng; hiển thị PDA Serial/tình trạng.
- Phát lại User: chọn trực tiếp user đã dùng; User Pack theo `Bàn – User`; hỗ trợ `Không dùng hy1.outbound` và tài khoản cố định thực tế.
- Thông tin phiên: chỉ Ca / Time in / Time out.
- Diễn biến trong ca: before → after đúng dữ liệu.
- Thêm/Sửa/Xóa theo ngữ cảnh; bàn Pack không khóa D1.
- Service/Worker authority không đổi.

## LOCKED / UNCHANGED

- Stable publish: **FORBIDDEN**; feed trước/sau giống nhau: `available=false`, `reason=NO_APK`.
- Stable source identity: `0.1.0-stable`, versionCode `1`.
- `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`, fresh-read unchanged sau publish.
- Signer unchanged: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Worker/Service change: **NONE**.
- Authority change: **NONE**.
- GAS production change: `OTA_VERSION_COMPAT_BETA75` only; temporary exact-Drive upload helper removed after publish.
- Provider: unchanged.

## SUPERSEDED / ABANDONED

- Beta69/Beta70: không thuộc active base.
- Beta71/Beta72/Beta73: historical/superseded.
- **Beta74: SUPERSEDED by Beta75**; previous SHA `37cadd74088179f1e17872c7474622681941cc5f546807cea769517d9f98b017`.

## RELEASE HARNESS PASS PATH

- Exact candidate remained artifact `9563625638`; no rebuild/resign/revisual after HUMAN lock.
- Visual harness defects were fixed by isolated probe before final matrix; final matrix `32860235560` HUMAN PASS.
- Publish preflight false failures were harness-only: receipt byte/canonical compare and wrapper self-match grep; both fixed without production write or candidate change.
- Final fixed publish-only run `32865705207` SUCCESS; one transient curl timeout recovered inside proven propagation window; exact bytes preserved.

## ACTIVE DEVELOPMENT BASE

- Continuity branch: `release/beta71-clean-from-beta68-20260825`.
- LIVE base for next scope: Beta75 above.
- Android source identity: `e475b8476e99a9230683dbbf6ec266235960ed5b`.
- Active workflow allowlist: `app-fast-check.yml`, `beta-release.yml`.
