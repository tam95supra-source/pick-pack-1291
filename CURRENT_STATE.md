# CURRENT STATE — 2026-08-25

## LIVE — BETA

- Status: **Beta72 OTA LIVE PASS**
- Version: `0.4.2-beta.72`
- versionCode: `78`
- Package: `vn.pickpack1291.app.beta.publicbeta`
- Lineage: Beta68 golden base → Beta71 LIVE → OWNER session/resource fixes → Beta72. Beta69/Beta70 source is not a base.
- Android source SHA: `73d5432df09c33cda6554090838e5f55e41761ae`
- Candidate run/artifact: `32808558173` / `9549037310`
- Visual run/artifact: `32812834075` / `9550496243`
- Release run/evidence artifact: `32813298916` / `9550565538`
- APK SHA-256: `fdeb006122f065591e82fe912a4a615c9c42a149568c2fc32f7d5b35db353caf`
- APK size: `13114245`
- Signer SHA-256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`
- Drive file: `1tmIdYOE2lGe2igksVLZ2m3JNLWuVyR9v`
- OTA source: `GOOGLE_DRIVE`; published exact locked bytes.
- Human visual inspection: **PASS**, 42 ảnh tại 320x568, 360x640, 480x800.
- Visual checks: Pick bắt buộc PDA; User Pick + Phát lại cùng dòng; Pack ràng buộc Bàn Pack → User Pack; User Pack + Phát lại cùng dòng; user cố định hiển thị đầy đủ trong tóm tắt phiên; vuốt quay lại màn cha; không overlap/layout overflow.
- Rebuild/resign sau candidate lock: **không**.
- Receipt: `ops/beta72-release-result.json`.

## LOCKED / UNCHANGED

- Stable publish: **FORBIDDEN**, feed trước/sau giống hệt: `available=false`, `reason=NO_APK`.
- Stable source identity trong candidate: `0.1.0-stable`, versionCode `1`.
- `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`, unchanged.
- Signer: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`, unchanged.
- Service/GAS business source change: **NONE**. Helper vận chuyển tạm đã được restore exact.

## SUPERSEDED / ABANDONED

- Beta69: bỏ hẳn khỏi active lineage; không phát hành, không làm base.
- Beta70: không làm base.
- Beta71: live cũ đã được Beta72 thay thế; giữ làm historical release evidence.
- Các visual harness failure trước run `32812834075` là harness/fixture evidence, không phải APK và không tạo candidate mới.

## ACTIVE DEVELOPMENT BASE

- Dùng nhánh `release/beta71-clean-from-beta68-20260825` và trạng thái Beta72 LIVE ở trên cho công việc tiếp theo.
- Android source identity tiếp tục khóa tại `73d5432df09c33cda6554090838e5f55e41761ae` cho Beta72 đã phát hành.
- Chỉ hai workflow active trên nhánh sạch: `app-fast-check.yml`, `beta-release.yml`.
