# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-03T03:08:00Z
- owner: Nguyễn Văn Tâm
- branch: release/beta113-owner-scope-20260902
- release_trigger_sha: 171324926ac58d38b266baa48934273f528b0756
- acceptance_base_sha: 634e878e099ef6b95a852f87d45f44f59ac8f74e
- archive_file: docs/handovers/HANDOVER_20260903-030800_beta115-owner-accepted.md

## Mục tiêu + DoD
Beta115 đã Technical PASS/LIVE và OWNER đã nghiệm thu toàn bộ checklist hiện tại. Phiên mới không làm lại phần đã PASS; chờ OWNER nêu các vấn đề/chỉnh sửa mới rồi map impact → sửa nhỏ nhất → regression → Beta mới nếu Android source đổi.

## LIVE / EXACT EVIDENCE
- LIVE BETA: 0.4.2-beta.115 / versionCode 121 / package vn.pickpack1291.app.beta.publicbeta.
- APK candidate source: 3f343ea1be0dbace5df995e4c81e1cdca9defd24.
- Service source: 429c39f82aacba19351351234f7f66a8d3b655f1.
- Candidate: run 33703823187 / artifact 9874569505.
- APK SHA256: af2c267e2101223387fdf4feb86b6ae315fe17b44c09d89c9f6166a8a73d49e5 / size 14281717.
- Signer: d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Service PASS: run 33707525071 / artifact 9875965938.
- Fast Check PASS: run 33708743727.
- Runtime DoD PASS: run 33708224737 / artifact 9876009359.
- Visual + human PASS 320x568 / 360x640 / 480x800: run 33705116149 / artifact 9875061341.
- Device regression PASS: run 33705707420 / artifact 9875164876.
- Terminal publish/OTA/finalize PASS: run 33709045943 / publish 9876309366 / OTA-install-open-readback 9876353676 / final 9876357969.
- Stable/main/signer/authority: unchanged.
- APK transport: GITHUB_RELEASE_ONLY; Google Drive APK FORBIDDEN.

## OWNER ACCEPTANCE
- COMPLETE lúc 2026-09-03T10:08:00+07:00.
- OWNER xác nhận toàn bộ checklist Beta115 hiện tại OK về mặt lý thuyết/yêu cầu.
- Receipt: `ops/beta115-owner-acceptance.json`.
- Chuyển ACTIVE_PASS:
  - LABOR-MULTI-INTERVAL-003
  - UI-DATA-DATE-SELECT-001
  - UI-FORM-CONSISTENCY-002
- Các ACTIVE_PASS Beta114/Beta115 khác tiếp tục được bảo vệ.
- OWNER đồng thời nói còn nhiều điểm muốn chỉnh sửa, nhưng chưa mô tả trong phiên này. Không suy diễn chúng thành bug/scope; chờ lệnh cụ thể ở phiên mới.

## Quy tắc phiên tiếp theo
1. Đọc `docs/handovers/HANDOVER_CURRENT.md`, `docs/REGRESSION_GUARD_POLICY.md`, `docs/STABLE_INVARIANTS.md`, `CURRENT_STATE.md`.
2. Không làm lại Beta115 gates đã PASS nếu source/input/exact bytes không đổi.
3. Khi OWNER nêu chỉnh sửa mới: map file/domain → ACTIVE_PASS liên quan trước khi change.
4. Nếu Android source đổi, phải ra Beta mới theo release flow đầy đủ; Stable/main/signer/authority không đổi nếu OWNER chưa chốt.
5. Không tự triển khai bất kỳ “vấn đề còn nhiều” nào khi OWNER chưa mô tả cụ thể.

## Blocker
Không có.

## NEXT_ACTION
WAIT_FOR_OWNER_NEW_SCOPE
