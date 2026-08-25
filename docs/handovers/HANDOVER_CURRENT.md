---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-08-25T10:42:18+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: release/beta71-clean-from-beta68-20260825
working_head_sha: 6245e87e0cd4b162466268dd7764a4b2e6d5055d
archive_file: docs/handovers/HANDOVER_20260825-104218_handoff-retention-v2.md
base_or_live_version: 0.4.2-beta.71
task_state: PASS
next_action: WAIT_FOR_OWNER_NEW_SCOPE
---

# BÀN GIAO PHIÊN — BETA71 LIVE VÀ HANDOFF RETENTION V2

## 1. Yêu cầu OWNER và Definition of Done

Yêu cầu đã xử lý:

1. Bỏ Beta69/Beta70 khỏi active lineage; dùng Beta68 golden làm gốc, thực hiện yêu cầu OWNER và phát hành Beta71.
2. Tối ưu cấu hình áp dụng ở cấp dự án, không lặp prompt mỗi chat.
3. Viết lại bối cảnh AI với vai trò chuyên môn, lỗi thường gặp và đúng đường PASS; cấm retry cách đã biết sai.
4. Khi OWNER yêu cầu chuyển phiên, AI phải tự tạo file bàn giao đầy đủ để phiên mới tiếp tục mà không rà soát lại phần đã PASS.
5. Bổ sung prompt first-chat và khóa chống AI tự dừng/làm lệch phạm vi.
6. Mỗi lần chuyển chat phải tự tạo handoff trong repo, giữ canonical + tối đa 5 archive gần nhất; phiên mới không có yêu cầu vẫn tự nạp bản mới nhất.

Definition of Done hiện tại:

- Beta71 OTA LIVE PASS bằng exact locked APK: PASS.
- Sáu yêu cầu OWNER + PDA local current-holder: PASS.
- Stable/main/signer/GAS business source không đổi: PASS.
- Cấu hình repo-native, Project context, lỗi → PASS, handoff protocol và anti-stop gate: PASS.
- Protocol/schema v2, AGENTS, Project context và first-chat prompt áp đúng cơ chế tự nạp mới nhất + retention 5 archive: PASS.
- Canonical + archive handoff mới tồn tại, cùng nội dung, không có secret và active tree không quá 5 archive: PASS sau commit hai file này.

Phạm vi bị cấm nếu OWNER chưa yêu cầu: Stable publish, merge/ghi `main`, đổi signer, đổi provider/authority/kiến trúc, thêm workflow per-version, rebuild/re-sign candidate đã khóa, xóa bằng chứng lịch sử.

## 2. Trạng thái canonical hiện tại

### LIVE

- Version: `0.4.2-beta.71`; versionCode: `77`.
- Package: `vn.pickpack1291.app.beta.publicbeta`.
- Lineage: Beta68 golden → OWNER fixes → Beta71. Beta69/Beta70 không phải base.
- App source SHA: `3db26ccc781f98601f16778d3e5f5a00cb019c13`.
- Candidate run/artifact: `32798498529` / `9545736575`.
- Visual run/artifact: `32799493283` / `9546071678`.
- Release run/evidence artifact: `32801206323` / `9546548065`.
- APK SHA-256: `5a8e29f5d50ac31010ebe2cd6e6096ffdd8bcd2b354007a7448878ae6eefec3b`.
- APK size: `13114245`.
- Signer SHA-256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Drive APK file ID: `1wPTVlSblaBlu0w5Zk-3hXj9hqeZlzQRD`.
- Rebuild sau candidate lock: `false`.
- Receipt: `ops/beta71-release-result.json`.

### LOCKED / UNCHANGED

- Stable: publish `FORBIDDEN`; feed trước/sau `available=false`, `reason=NO_APK`.
- `main`: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`, unchanged.
- Service/GAS business source: `NONE`; helper transport tạm đã restore exact.
- Active branch: `release/beta71-clean-from-beta68-20260825`.
- Chỉ hai workflow active: `app-fast-check.yml`, `beta-release.yml`.

### KIẾN TRÚC / AUTHORITY

Android/Web-PWA ↔ Cloudflare Worker ↔ D1; Durable Objects/WebSocket realtime; GSheet/GAS replica/fallback/DR/OTA; Android local projection/offline. Một official write authority với fencing/idempotency/anti-duplicate/audit.

## 3. Việc đã hoàn tất

| Hạng mục | Trạng thái | Evidence |
|---|---|---|
| Nhánh sạch từ Beta68, loại workflow rác | PASS | `e2ff0aa3cbab94e0983d672ece5ae54181bf480e` |
| App source OWNER fixes | PASS | source `3db26ccc781f98601f16778d3e5f5a00cb019c13` |
| Candidate compile/sign/isolation | PASS | run `32798498529`, artifact `9545736575` |
| Human visual 36 ảnh, 3 kích thước | PASS | run `32799493283`, artifact `9546071678`, `ops/beta71-visual-inspection.json` |
| OTA public bytes/readback/no-update | PASS | run `32801206323`, artifact `9546548065` |
| Stable/main unchanged | PASS | `ops/beta71-release-result.json` |
| Trạng thái LIVE canonical | PASS | `CURRENT_STATE.md`, commit `cfdddae4560bcb723566a87e3a078988ee1dac44` |
| Release known-pass playbook | PASS | `docs/BUILD_RELEASE_PLAYBOOK.md`, commit `e31d6f699a5176aeaaae216572f05bed37c7f88f` |
| OTA schema pass path | PASS | `docs/AI_EXECUTION_STANDARD.md`, commit `f8bc13b2876478c78c0ab8d914e6f347603511b1` |
| Reusable locked publisher | PASS | `.github/workflows/beta-release.yml`, commit `5429002335b0b32110df2836a8638a28ac0cb237` |
| Repo-native AI routing | PASS | `AGENTS.md`, auto-resume commit `8851b52e773531bb72b6b9a15a7824cc22a96900` |
| ChatGPT Project context | PASS | `docs/CHATGPT_PROJECT_CONTEXT_V2.md`, retention sync commit `74bfe1aba35352ec8dab2f192d4961bd16251e58` |
| Handoff schema/protocol v2 | PASS | `docs/CHAT_HANDOFF_PROTOCOL.md`, commit `568a849606c28d9cf2bbe6b6c497970604d93ecc` |
| First-chat prompt tự nạp latest | PASS | `docs/FIRST_CHAT_PROMPT.md`, commit `6245e87e0cd4b162466268dd7764a4b2e6d5055d` |

## 4. Thay đổi trong phiên

Các file cấu hình/trạng thái quan trọng đã tạo hoặc cập nhật:

- `AGENTS.md`: authority, vai trò, anti-stop, anti-drift, chuyển phiên bắt buộc.
- `.codex/config.toml` và `.codex/agents/*.toml`: reasoning/verbosity và vai trò áp dụng cấp dự án.
- `docs/CHATGPT_PROJECT_CONTEXT_V2.md`: context rút gọn để đặt một lần trong Project instructions.
- `docs/AI_EXECUTION_STANDARD.md`: deterministic/transient/harness và fingerprint → đường PASS.
- `docs/BUILD_RELEASE_PLAYBOOK.md`: luồng hai workflow, build một lần, exact OTA contract.
- `docs/CHAT_HANDOFF_PROTOCOL.md`: schema v2, canonical + tối đa 5 archive, fallback latest và restore qua Git history.
- `docs/FIRST_CHAT_PROMPT.md`: prompt phiên đầu tự đọc canonical, fallback archive mới nhất và route theo task state.
- `CURRENT_STATE.md`: Beta71 LIVE exact.
- `.github/workflows/app-fast-check.yml`, `.github/workflows/beta-release.yml`: active workflow allowlist.
- `tools/publish_beta71_ota.sh`: idempotent exact publish/readback và restore GAS.

Production/live change duy nhất trong phạm vi: thay Beta70 live bằng exact Beta71 đã khóa. Không promote Stable, không đổi `main`, không đổi signer hoặc GAS business logic.

## 5. Lỗi đã gặp và đường PASS

| Fingerprint | Root cause | Cách PASS đã biết | Cách cấm lặp |
|---|---|---|---|
| Beta69/70 không build được, hàng loạt run | 236 workflow lịch sử + YAML lỗi gây run explosion | Nhánh sạch từ Beta68, chỉ giữ 2 workflow | Không retry từng workflow; không tạo observer/finalizer |
| Candidate timeline trống | Matcher local history không nhận event-shaped rows/session | Sửa schema compatibility + session matching; giữ exact regression | Không vá lỗi cascade hoặc chồng script mới |
| Visual fail trong khi APK launch đúng | Harness/fixture/parser | Sửa harness, dùng lại exact candidate | Không rebuild/re-sign APK |
| Publish preflight thấy Beta70 thay Beta68 | Live state đã đổi nhưng Beta70 exact fingerprint được biết | Chấp nhận đúng fingerprint để supersede, không dùng source Beta70 | Không lấy Beta70 làm base |
| Feed không có `version_code` | Verifier dùng schema cũ | Với `available=true`, kiểm tra version/SHA/size/URL thực | Không kết luận APK lỗi |
| No-update không có `sha256`/URL | Contract `available=false` cố ý rút gọn | Kiểm tra source/channel/version/size; identity đã khóa bằng live download | Không rebuild hoặc ép trường không tồn tại |
| Push/receipt race | Nhiều writer/observer | Một concurrency writer, receipt cuối | Không tạo status commit song song |

Retry budget: deterministic = 0; transient transport = tối đa 2 lần có backoff và giữ nguyên bytes.

## 6. Trạng thái workspace/CI/external

- Remote branch: mọi thay đổi công việc/cấu hình đã commit tới `6245e87e0cd4b162466268dd7764a4b2e6d5055d` trước handoff.
- Không có source Android chưa commit trong phiên này.
- Không có build/release workflow đang pending.
- Release run cuối: `32801206323` — PASS.
- Fresh-read OTA/Stable cuối trong evidence release lúc 2026-08-25 khoảng 09:24 +07:00.
- Fresh-read `main` cuối: vẫn `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`.
- ChatGPT Project UI có thể vẫn giữ context cũ nếu OWNER chưa đồng bộ bản V2 mới; Codex repo-native đã áp dụng qua `AGENTS.md`.

## 7. Việc còn lại

### Blocking

- `NONE` — phạm vi hiện tại đã PASS.

### OWNER/UI one-time

- Nếu ChatGPT Project instructions đang dùng bản cũ, đồng bộ một lần nội dung giữa “BẮT ĐẦU” và “KẾT THÚC” từ `docs/CHATGPT_PROJECT_CONTEXT_V2.md`.

### Công việc dự án tiếp theo

- Chưa có yêu cầu tính năng mới. Không tự phát sinh việc.
- Khi OWNER giao yêu cầu mới, dùng Beta71 LIVE/active branch ở trên làm điểm xuất phát, trừ khi OWNER chỉ định khác.

## 8. NEXT_ACTION — điểm tiếp tục chính xác

`WAIT_FOR_OWNER_NEW_SCOPE`

Phiên mới phải tự đọc `HANDOVER_CURRENT.md` ngay cả khi prompt không có yêu cầu. Nếu canonical thiếu/không READY, chọn archive timestamp READY mới nhất; không hỏi OWNER và không crawl repo.

- Có `YÊU CẦU MỚI`: nạp trạng thái này, ánh xạ scope + DoD rồi thực thi ngay theo `AGENTS.md`.
- Không có yêu cầu mới: vì `task_state: PASS`, chỉ trả lời một câu “Đã nạp bàn giao Beta71 LIVE, sẵn sàng nhận yêu cầu mới”; không chạy tool khác và không tự phát sinh việc.

Expected result: không recap dài, không đọc log cũ, không rerun build/visual/OTA đã PASS.

Fallback đọc file: archive READY có timestamp lớn nhất, hiện là `HANDOVER_20260825-104218_handoff-retention-v2.md`. Retry đọc tối đa 1 lần.
## 9. Blocker và quyền

- Blocker hiện tại: `NONE`.
- Không cần OWNER cung cấp secret/MFA để nạp bàn giao.
- Không ghi secret, OAuth token, keystore password hoặc signed URL tạm trong handoff.

## 10. Invariants không được phá

- Không dùng Beta69/Beta70 làm base.
- Không rebuild/re-sign exact Beta71 đã phát hành.
- Không tạo workflow per-version/observer/status/finalizer.
- Không publish Stable hoặc ghi `main` nếu OWNER chưa explicit.
- Không đổi signer, authority, provider hoặc kiến trúc.
- Không chạy lại gate PASS khi input/source/artifact bytes không đổi.
- Không tự thêm tính năng/refactor/experiment ngoài yêu cầu OWNER.
- Không tự final khi còn action hợp lệ trong scope; chỉ dừng theo ba điều kiện trong `AGENTS.md`.
- Không giữ quá 5 archive handoff timestamp trong active tree; chỉ prune archive cũ nhất, không rewrite history.

## 11. Resume contract

Phiên mới tự chọn snapshot theo thứ tự: canonical READY → archive timestamp READY mới nhất. Lệnh OWNER mới nhất luôn ưu tiên; nếu không có lệnh mới thì route theo `task_state`/`NEXT_ACTION`. Tin exact ID/hash/PASS khi input không đổi; chỉ fresh-read external state có thể đổi sau `created_at` hoặc trước production write. Không đọc lại lịch sử và không yêu cầu OWNER kể lại.

## 12. Retention/restore

- Canonical: `docs/handovers/HANDOVER_CURRENT.md`.
- Archive mới: `docs/handovers/HANDOVER_20260825-104218_handoff-retention-v2.md`.
- Archive trước: `docs/handovers/HANDOVER_20260825-1028_beta71-live-context-bootstrap.md`.
- Active count sau handoff: `2/5`; pruned trong lần này: `NONE`.
- Khi archive thứ 6 xuất hiện, xóa bản timestamp cũ nhất khỏi active tree. Muốn restore một trong 5 bản: lấy nội dung archive đã chọn ghi lại vào canonical bằng commit bình thường. Bản cũ hơn vẫn có thể lấy từ Git history; cấm rewrite history.
