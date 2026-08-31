# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-08-31T13:22:00Z
- owner: Nguyễn Văn Tâm
- branch: release/beta102-beta-stable-isolation-20260831
- release_trigger_sha: 379fb80ef0b3ed1a1686b2d06f30d168fdbf17cf
- archive_file: docs/handovers/HANDOVER_20260831-132200_beta104-owner-accepted.md
- technical_dod_status: PASS
- owner_acceptance: COMPLETE_BETA104_CHECKLIST_1_TO_6_OK

## LIVE
- Beta LIVE: 0.4.2-beta.104 / versionCode 110 / vn.pickpack1291.app.beta.publicbeta.
- Source: c31bb1b7ad68e6fd114727d8f08508796013bcef.
- Candidate: run 33384004708 / artifact 9754938692.
- APK SHA256: 523b7ca4fe3463acdec8281d6232f36cd15e8df13a5f25585ca4ff4b82f2d6f1 / size 13593589.
- Terminal release run 33391700817 PASS; publish 9757752307; OTA preserved-data 9757829287; final 9757837384.
- Stable/main/signer/authority unchanged; Stable READY_NOT_LIVE/private/public=false/no OTA.
- APK transport GITHUB_RELEASE_ONLY; Google Drive APK FORBIDDEN.

## OWNER ACCEPTANCE
OWNER Nguyễn Văn Tâm xác nhận Beta104 checklist:
1. OTA giữ data/app state: OK.
2. Service không còn offline do stale discovery cache: OK.
3. Login/session: OK.
4. Read/sync/nghiệp vụ không reuse Stable root: OK.
5. Trạng thái Service online và sử dụng thực tế: OK.
6. Không phát hiện regression mới: OK.

Evidence receipt: ops/beta104-owner-acceptance.json.

## INVARIANTS
- ENV-ISOLATION-001 = ACTIVE_PASS.
- SERVICE-DISCOVERY-001 = ACTIVE_PASS.
- OTA-BETA-001 tiếp tục ACTIVE_PASS, evidence Beta104.
- INFRA-RESILIENCE-001 vẫn DEFERRED_BY_OWNER / non-blocking; không được suy diễn từ checklist mục 6.

## BLOCKER
Không có.

## NEXT_ACTION
WAIT_FOR_OWNER_NEW_SCOPE
