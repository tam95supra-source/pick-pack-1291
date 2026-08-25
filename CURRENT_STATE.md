# CURRENT STATE — 2026-08-25

## LIVE — BETA

- Status: **Beta74 OTA LIVE PASS**
- Version: `0.4.2-beta.74`
- versionCode: `80`
- Package: `vn.pickpack1291.app.beta.publicbeta`
- Lineage: Beta68 golden base → Beta71 → Beta72 → Beta73 → Beta74. Beta69/Beta70 source is not a base.
- Android source SHA: `cfb4dbca116f7c47a598bc398bdbe1251ad2bad8`
- Candidate run/artifact: `32842363597` / `9561088652`
- Visual artifact: `9561153695`; receipt commit `fe0582614804ef767732ddd7ddfa779aecb48c8a`; HUMAN PASS `320x568`, `360x640`, `480x800`.
- Final release run/evidence artifact: `32845025048` / `9561988451`.
- Release evidence digest: `sha256:0e6c98e20b3a0dcd9f321d3f560e454fd0a519afb1433a655bf8a48bbbcc67b6`.
- APK SHA-256: `37cadd74088179f1e17872c7474622681941cc5f546807cea769517d9f98b017`.
- APK size: `13130629` bytes.
- Signer SHA-256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Signer proof: published/Drive bytes SHA exact locked signed candidate; no rebuild/resign after candidate lock.
- Drive APK ID: `1Dq3uLxBRYWOa5ImYu8BX2VngC1ccoqkr`.
- Drive checksum ID: `1uXauZVKSJdO71N88FfZT39Pgght5LaNL`.
- OTA source: `GOOGLE_DRIVE`.
- OTA URL: `https://drive.usercontent.google.com/download?id=1Dq3uLxBRYWOa5ImYu8BX2VngC1ccoqkr&export=download&confirm=t`.
- OTA readback: Beta73 client sees `available=true`, version `0.4.2-beta.74`, versionCode `80`, SHA/size exact; Beta74 client sees `available=false`, version `0.4.2-beta.74`, versionCode `80`.
- Fresh Drive readback after publish: name `pick-pack-1291-public-beta-0.4.2-beta.74.apk`, MIME APK, size `13130629`; downloaded authenticated Drive bytes SHA-256 exact `37cadd74088179f1e17872c7474622681941cc5f546807cea769517d9f98b017`.
- Receipt: `ops/beta74-release-result.json`, verdict `PASS`.

## BETA74 FIX SCOPE

- Local projection ưu tiên đúng phiên `ACTIVE`/mới nhất của MNV thay vì phiên cũ trong ngày.
- Không gọi `session_resource_snapshot` khi `session_id` rỗng, loại false `SESSION_NOT_FOUND` sau thao tác hợp lệ.
- Giữ local-pending cho tới authority ack; tránh dựng lại toàn cây employee khi dữ liệu không đổi để giảm hiện tượng màn hình tự refresh.
- Service/Worker source/authority không đổi.

## LOCKED / UNCHANGED

- Stable publish: **FORBIDDEN**; feed trước/sau publish giống nhau: `available=false`, `reason=NO_APK`.
- Stable source identity: `0.1.0-stable`, versionCode `1`.
- `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`, fresh-read unchanged sau publish.
- Signer: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`, unchanged.
- Worker/Service change: **NONE**.
- Authority change: **NONE**.
- GAS production change: `OTA_VERSION_COMPAT_BETA74` only; temporary exact-Drive upload helper removed after publish; existing forgot-password preview preserved.
- Provider: unchanged.

## SUPERSEDED / ABANDONED

- Beta69: bỏ khỏi active lineage; không phát hành, không làm base.
- Beta70: không làm base.
- Beta71: historical only.
- Beta72: superseded.
- **Beta73: SUPERSEDED by Beta74**; previous SHA `ad037c1a17d245f90ead59539c5595cc5df6a568b8657ce636cc43d101175fd2`.
- Beta74 publish run `32843213718` attempts 1–3: superseded harness attempts; exact candidate không đổi. Root failure `drive-transport: UNAUTHORIZED` do GAS deployment propagation window quá ngắn.

## RELEASE HARNESS PASS PATH

- Exact artifact remained `9561088652`; no rebuild/resign/revisual.
- Deterministic harness recovery restored proven GAS propagation windows from Beta73: helper readback `6` attempts; OTA readback `8` attempts.
- Fixed `beta-release.yml` ran publish-only; final run `32845025048` SUCCESS.
- Không lặp identical retry của old 3-attempt publisher; không tạo candidate/workflow mới.

## ACTIVE DEVELOPMENT BASE

- Nhánh continuity: `release/beta71-clean-from-beta68-20260825`.
- LIVE base cho scope tiếp theo: Beta74 ở trên.
- Android source identity phát hành Beta74: `cfb4dbca116f7c47a598bc398bdbe1251ad2bad8`.
- Active workflow allowlist: `app-fast-check.yml`, `beta-release.yml`.
