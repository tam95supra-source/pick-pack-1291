# CURRENT STATE — 2026-08-25

## LIVE — BETA

- Status: **Beta71 OTA LIVE PASS**
- Version: `0.4.2-beta.71`
- versionCode: `77`
- Package: `vn.pickpack1291.app.beta.publicbeta`
- Lineage: Beta68 golden base → OWNER fixes → Beta71. Beta69/Beta70 source is not a base.
- Source SHA: `3db26ccc781f98601f16778d3e5f5a00cb019c13`
- Candidate run/artifact: `32798498529` / `9545736575`
- Visual run/artifact: `32799493283` / `9546071678`
- Release run/evidence artifact: `32801206323` / `9546548065`
- APK SHA-256: `5a8e29f5d50ac31010ebe2cd6e6096ffdd8bcd2b354007a7448878ae6eefec3b`
- APK size: `13114245`
- Signer SHA-256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`
- Drive file: `1wPTVlSblaBlu0w5Zk-3hXj9hqeZlzQRD`
- Human visual inspection: PASS, 36 ảnh tại 320x568, 360x640, 480x800.
- Rebuild sau candidate lock: **không**.
- Receipt: `ops/beta71-release-result.json`.

## LOCKED / UNCHANGED

- Stable publish: **FORBIDDEN**, feed trước/sau giống hệt: `available=false`, `reason=NO_APK`.
- `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`, unchanged.
- Service/GAS business source change: **NONE**. Helper vận chuyển tạm đã được restore exact.

## SUPERSEDED / ABANDONED

- Beta69: bỏ hẳn khỏi active lineage; không phát hành, không làm base.
- Beta70: bản live cũ đã được Beta71 thay thế; không làm base và không khôi phục workflow.
- Nhánh/workflow Beta69/Beta70 chỉ là bằng chứng lịch sử, không phải nguồn sự thật.

## ACTIVE DEVELOPMENT BASE

- Dùng nhánh `release/beta71-clean-from-beta68-20260825` và trạng thái Beta71 LIVE ở trên cho công việc tiếp theo.
- Chỉ hai workflow active trên nhánh sạch: `app-fast-check.yml`, `beta-release.yml`.
