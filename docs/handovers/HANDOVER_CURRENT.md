# PICK PACK 1291 — HANDOFF SCHEMA V3

- schema_version: 3
- status: READY
- time_local: 2026-09-06T22:46:37+07:00
- owner: Nguyễn Văn Tâm
- branch: release/beta130-r5-rev6-20260906
- working_head_sha: d83fff4c2c35c42c44f9f9190d585ae850a89270
- exact_candidate_source_sha: d5442338e7413d46a8344a3682f7e08276309630
- archive_file: docs/handovers/HANDOVER_20260906-2246_r5-beta130-service-harness-late-day.md
- owner_scope_file: ops/OWNER_SCOPE_CURRENT.json
- owner_scope_id: OWNER_20260906_R5_QUOTA_REALTIME
- owner_scope_revision: 6
- owner_scope_semantics_sha256: 218f12a7194d0c0f877db6f081e6cda314493097764f2dcfa0410036e9de5f1e
- owner_scope_sha256: 205600c9cfa96a6dc3a0a3293e2b8e74dcde16d3f198daf1ce7675008250f260
- owner_command_ledger: ops/owner-command-ledger.jsonl
- owner_command_ledger_head: 175b83ff1669986448b8855f5e8da71b4c161f92e8ccda63dadb5e0c7480b281
- governance_policy: docs/OWNER_SCOPE_PROTOCOL.md

## Authority
- Không chép lại checklist/yêu cầu OWNER trong handoff.
- Phiên tiếp quản bắt buộc đọc HANDOVER_CURRENT, REGRESSION_GUARD_POLICY, STABLE_INVARIANTS, CURRENT_STATE, OWNER_SCOPE_CURRENT + ledger head và bootstrap canonical guard trước change.
- Chat/memory/file prompt chỉ dùng để tìm canonical repo; requirement thực tế lấy từ ops/OWNER_SCOPE_CURRENT.json.

## LIVE / TARGET
- LIVE BETA vẫn là 0.4.2-beta.128 (versionCode 134), exact source 5569d1e931436e02d118ed8ab57f2143de43b9f7.
- Exact Beta130 candidate 0.4.2-beta.130 (versionCode 136) đã khóa nhưng CHƯA LIVE: candidate run 34031376706, artifact 9988766781, APK SHA256 f6011a2088350c7ec0062caf2af0762eedfd14be68f03bdbc41f06a104070287, size 14478325, signer giữ nguyên.
- Stable chưa public/LIVE; R5 Stable parity chỉ READY_NOT_LIVE. Cấm deploy/public Stable nếu chưa có lệnh OWNER promote.
- Stable/main/signer/authority không đổi.

## Evidence cốt lõi
- OWNER scope rev6 bootstrap PASS; semantics/snapshot/ledger pointers giữ nguyên.
- Fast Check exact candidate: run 34040244296 PASS toàn bộ.
- Service candidate bytes không đổi: d5442338e7413d46a8344a3682f7e08276309630.
- Các service regression trước điểm lỗi trong run 34042735653 PASS: backup/restore, quota guard, D1 capacity, Beta89, Beta91, Beta92, Beta95, Beta110, Beta111.
- Run 34042735653 artifact 9992232216: Beta115 cap conflict trả đúng LABOR_END_AFTER_SHIFT_OR_EXIT; future labor finish được CONFIRMED; sau đó b115-exit-future-blocked lại ATTENDANCE_EXIT thành công, nên harness fail.
- Nguyên nhân hiện tại là fixture/harness phụ thuộc thời điểm cuối ngày: laborEndCap cho ACTIVE khi scheduled shift đã qua dùng now+60s, trong khi exit guard cũng so với Date.now()+60s; vì vậy fixture tạo end_at gần tương lai không thể còn >60s tại lúc exit. Không phải bằng chứng business implementation R5 sai.
- Sau fail, canonical automatic recovery exact Beta128 PASS; LIVE không bị bỏ ở candidate fail.

## Không được làm lại
- Không rebuild/resign APK Beta130 khi app/service exact bytes không đổi.
- Không rerun Fast Check 34040244296.
- Không nới P95/P99/quota threshold và không bỏ regression để lấy PASS.
- Không OTA trước khi mọi gate pre-OTA PASS.

## Blocker
Không có blocker OWNER. Đây là harness failure tự xử lý được.

## NEXT_ACTION
FIX_B115_LATE_DAY_FUTURE_EXIT_HARNESS_AND_RERUN_EXACT_SERVICE_GATE_ONLY
