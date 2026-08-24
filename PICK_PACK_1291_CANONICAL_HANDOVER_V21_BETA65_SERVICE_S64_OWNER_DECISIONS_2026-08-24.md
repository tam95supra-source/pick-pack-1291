# PICK PACK 1291 — CANONICAL HANDOVER V21
## Beta65 / Service S64 / Owner Decision Consolidation / Strict Continuation

**Status:** CURRENT CANONICAL CONTINUATION TRUTH  
**Generated:** 2026-08-24 15:37 +07:00  
**Live Public Beta:** `0.4.2-beta.65 / VC71` — FINAL RELEASE PASS  
**Live Service:** S64 — `SERVICE_PRIMARY / PRODUCTION`  
**Stable:** `0.1.0-stable / VC1` — `UNTOUCHED`, `PUBLISH FORBIDDEN`  
**Next Android product change:** `Beta66+ / VC72+`

This V21 is cumulative. It keeps all still-valid truth from V20, adds OWNER decisions made after/beside earlier handovers, explicitly supersedes stale alternatives, and embeds a stricter continuation contract so a future AI cannot treat planning, triggering, partial PASS, pending runs, or transport failures as a valid stopping point.

---

# 0. MANDATORY START PROMPT — EXECUTE, DO NOT RETURN A PROGRESS-ONLY ANSWER

When this file is supplied to a new AI/session, the AI MUST follow this section before doing project work.

## 0.1 Required first action

1. Read this V21 top-to-bottom.
2. Read the current live repository/project state needed for the requested task.
3. Fresh-read exact current Beta, Stable, Service, GAS/Drive/OTA state before any risky mutation.
4. Compare live state against this handover; never blindly assume an old receipt is still the current runtime truth.
5. Start execution immediately. Do not answer with only a plan.

## 0.2 Anti-stop / anti-stalling contract

The following are NOT valid completion states:

- `đã trigger`
- `workflow đang chạy`
- `candidate đã build`
- `đang pending`
- `đã tạo PR`
- `đã tạo branch`
- `đã upload artifact`
- `transport đang lỗi`
- `chưa có receipt`
- `chưa public nên vẫn coi bản cũ`
- `tôi không thể xác nhận thêm`
- a diagnosis with no attempted fix
- a progress report that ends while a resolvable stage is still FAIL/PENDING/UNKNOWN

A technical failure is a work item, not a reason to stop.

For every ordinary failure, the AI MUST:

1. diagnose the exact failed stage;
2. preserve any already-PASS immutable evidence;
3. fix the defect if it is source/config/workflow logic;
4. retry idempotently;
5. use another already-authorized path when the first connector/transport/runtime path fails;
6. resume from the failed stage rather than restarting proven stages;
7. keep working until all requested deliverables and mandatory gates are PASS.

The AI MUST NOT voluntarily end the task while a required, technically resolvable item remains incomplete.

## 0.3 Only valid hard blockers

Ask the OWNER only when ALL of the following are true:

- a genuinely required permission/manual approval/MFA/secret entry is missing;
- no connected/authorized alternate path can perform the same operation;
- the missing action cannot be diagnosed, retried, resumed, or replaced idempotently;
- continuing would otherwise require an unauthorized Stable change, signer change, destructive production action, paid provider/action, or a real unresolved business-rule conflict.

Do not classify ordinary `403`, OAuth scope mismatch, CI error, network failure, connector runtime failure, GitHub release transport failure, Drive warning page, stale branch, merge conflict, or failed test as an OWNER blocker until authorized alternate paths have been checked.

If OWNER action truly is required, state exactly:

- the blocked stage;
- the exact error/evidence;
- why no authorized alternate exists;
- the smallest exact OWNER action required;
- the exact resume point after the OWNER action.

Do not ask the OWNER to repeat information already in this handover or current live evidence.

## 0.4 No fake completion

Never declare `PASS`, `DONE`, `PUBLIC`, `DEPLOYED`, or `RELEASED` from intent, a trigger, a workflow start, a branch, a PR, or expected behavior.

A claim is legal only when backed by the exact required live/evidence readback.

If a task is explicitly `complete Beta/release/deploy`, the final answer is legal only after the release/deploy completion criteria are all proven.

## 0.5 Progress updates are not final answers

Short progress updates are allowed while tools are running, but they must not become a substitute for execution.

Do not finish with:
- `I have started...`
- `I will continue...`
- `wait...`
- `once the workflow finishes...`
- `if you want, I can continue...`

If the platform itself forcibly ends a turn, the last persisted checkpoint must contain exact stage, exact immutable IDs/hashes, what is PASS, what is not PASS, and the next executable operation. The next session must resume from that checkpoint rather than re-plan from zero.

---

# 1. PRECEDENCE / AUTHORITY

Apply truth in this order:

1. newest direct OWNER instruction;
2. this V21;
3. fresh live evidence;
4. immutable release/deploy receipts, exact hashes, artifact IDs and signer identity;
5. V20 for still-valid inherited details;
6. repository docs after staleness/conflict check;
7. V19/V18/older handovers for history only.

If an older document conflicts with V21, V21 wins.

## 1.1 Known stale architecture text that MUST NOT override V21

The following old repository text is known stale in architecture sections:

- `AGENTS.md` sections that state `Android App ↔ Google Apps Script ↔ Google Sheets` as the current operational authority and forbid Cloudflare as an approved backend.
- `ARCHITECTURE_GUARDRAILS.md` sections that state Google Sheets is the current operational source of truth and Cloudflare backend is not approved.

Those statements belonged to an earlier architecture stage and are SUPERSEDED by the current approved S64 production architecture:

`Android/Web ↔ Service Worker/D1/Event Ledger ↔ Google replica/report/DR`

Other non-conflicting rules in those documents remain usable, including security, no-secret-in-repo, owner workstation/browser-only constraints, UI/UX rules, idempotency, signing safety, and release discipline.

Do not stop work merely because an old file still contains the superseded architecture.

---

# 2. CURRENT LIVE RELEASE TRUTH — BETA65 FINAL

Public Beta is now Beta65.

- `versionName`: `0.4.2-beta.65`
- `versionCode`: `71`
- package: `vn.pickpack1291.app.beta.publicbeta`
- product source SHA: `1e8fb8255f26ad58c9719d99c27c08ef5d597cbf`
- source validation run: `32697993454` — PASS
- signed run: `32701275784`
- signed job: `97353121085`
- immutable Actions artifact ID: `9510636863`
- APK name: `pick-pack-1291-public-beta-0.4.2-beta.65.apk`
- exact APK SHA256: `be728cd8d20d6033becbfb169db89565f6078a681d47bc9079f98f9f5758e1da`
- exact APK size: `13097861`
- signer SHA256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`

Important evidence correction retained from V20:
- an earlier temporary evidence lock contained a wrong `be728eea...` value;
- the immutable artifact itself was never rebuilt/resigned;
- authoritative APK hash is the exact `be728cd8...e1da` value above.

Next Android product source MUST be `Beta66+ / VC72+`.

Do not reopen or mutate Beta65 product bytes to solve later transport/documentation issues.

---

# 3. BETA65 DRIVE / GAS / OTA / GITHUB FINAL STATE

## Google Drive Beta

- Beta folder ID: `1WMXI-8-Z1mbY2v11noYFHe_eoMNiNZXg`
- Beta65 APK file ID: `1F2Xu0PQ7tiIWcNDlz9yUTsXBee6RWP39`
- checksum file ID: `12iSOQ-AwToKY74ylGa4Wb5iVnQXdF8RC`
- exact public byte readback: PASS
- readback SHA256: `be728cd8d20d6033becbfb169db89565f6078a681d47bc9079f98f9f5758e1da`
- readback size: `13097861`

## GAS endpoint

`https://script.google.com/macros/s/AKfycbzbEoGfbNg6s2HnP-gUpcBJ7mMIkVBtYuQKMndb9seDV2c55lQwSUO1GZ-LtQ2CxMCauA/exec`

## OTA

- Beta64 → Beta65 available: PASS
- OTA target = Beta65: PASS
- OTA source = `GOOGLE_DRIVE`: PASS
- downloaded bytes = exact Beta65 hash/size: PASS
- Beta65 → Beta65 self no-update: PASS
- Stable self no-update: PASS
- Stable route isolation: PASS

## GitHub prerelease

- tag: `v0.4.2-beta.65-publicbeta`
- GitHub release ID: `375548474`
- exact prerelease APK readback: PASS

### Release-carrier exception

Direct tag creation on the product source was rejected because that commit contains workflow changes and the available GitHub App token lacked `workflows` permission.

Authorized workaround used:
- carrier branch: `release-carrier/beta65-20260824`
- metadata-only carrier SHA: `9692bf0631a58b3949427c91d1286837d4d008af`
- release tag points to carrier;
- release notes/receipt pin the real product source SHA;
- artifact/hash/package/version/signer remain authoritative product identity.

Future release:
1. try normal direct product-source tag first;
2. use metadata carrier only if the same workflow-permission restriction is freshly proven;
3. never rebuild/resign merely to bypass GitHub release transport.

---

# 4. STABLE HARD LOCK

Stable remains:

- `0.1.0-stable`
- VC `1`
- package `vn.pickpack1291.app.stable`
- `UNTOUCHED`
- publication `FORBIDDEN` unless separate explicit OWNER instruction

Permanent rules:

- no Stable bump as a Beta shortcut;
- no Stable publish merely because Beta compiled;
- no signer replacement/regeneration;
- no merge of evidence/release PR to main/Stable just to complete release;
- main is not a release scratch branch;
- do not expose signing files, refresh tokens, admin tokens, bridge/service secrets.

---

# 5. CURRENT SERVICE — S64 PRODUCTION AUTHORITY

Canonical endpoints:

- custom domain: `https://pickpack1291.cc.cd`
- compatibility URL: `https://pickpack.1291.workers.dev`
- Worker/service: `pickpack`

Last proven S64 deployment:
- source SHA: `11008a747b54bcc80e09ec13fb674be37efd831b`
- Cloudflare version: `78d832e7-bbc6-4d34-8562-19aa32d2493c`
- authority: `SERVICE_PRIMARY / PRODUCTION`
- replication: `HEALTHY`
- pending replication: `0`

The old detached Worker `pick-pack-1291-service` MUST NOT be recreated.

## 5.1 Approved operational architecture

`Android/Web ↔ Service Worker/D1/Event Ledger ↔ Google replica/report/DR`

Under `SERVICE_PRIMARY`:

- Service D1/Event Ledger is canonical for operational mutations/history/audit.
- Google remains master/catalog/config authority plus operational replica/report/DR.
- Ordinary service timeout/5xx/network failure does NOT authorize direct PDA business writes to Google.
- Google operational fallback is legal only after official control-plane transition to `GOOGLE_FALLBACK` with epoch/generation fencing.
- event IDs, idempotency and audit are mandatory.
- no LAN relay/leader redesign is approved.
- no per-device direct GSheet operational-write redesign is approved.
- no newly invented service-die LAN/GSheet architecture is approved.

Any local pending/offline behavior must reconcile through the approved authority/control-plane model and must not silently create a second operational authority.

## 5.2 S63/S64 same-session lease rule — NEVER REGRESS

Resource validation order:

1. if the lease belongs to the current active session, accept it as valid;
2. if another session holds it, reject as `${type}_IN_USE`;
3. only when no holder exists and free-list says unavailable, reject as `${type}_UNAVAILABLE`.

Never restore availability-before-ownership validation.

---

# 6. SESSION MODEL / BUSINESS DAY — OWNER LOCK

## 6.1 One completed session per business date

For one MNV:

- one completed `VÀO → RA` attendance session is allowed per `business_date`;
- `business_date` is anchored to the ENTER date of that session;
- crossing midnight does not move the open session to the next business date;
- after the previous cross-midnight session is closed, a new ENTER uses the current new date.

Canonical example:

- ENTER `05:00 15/08/2026`
- EXIT `03:00 16/08/2026`
- that session belongs to business date `15/08/2026`
- a subsequent ENTER after the exit belongs to business date `16/08/2026`

Therefore:
- do not create a second completed session for the same MNV and the same business date;
- do not block the legitimate new-day session merely because the previous session physically exited after midnight.

This supersedes any older broad interpretation of `sau RA không được vào lại` that would incorrectly block the next business date.

## 6.2 Session identity

Prefer exact `session_id` for all current-session reads/mutations/history.

S64 uses session-version/CAS semantics for mutable session/resource operations. Mutations must target the exact session/version they were initiated from; stale responses must not overwrite a newer session state.

---

# 7. POSITION / WORK MODEL — OWNER LOCK

## 7.1 Main position is a suggestion, not a lock

`Vị trí chính` only suggests `Vị trí trong ca`.

Examples:
- main position Pick → suggest Pick;
- main position Pack → suggest Pack;
- another main position → suggest that main position as appropriate.

A suggestion is not permission to restrict later Add/Edit choices.

## 7.2 Pick/Pack suggestion

- Pick context → suggest Pick resources/work;
- Pack context → suggest Pack resources/work.

Never convert these suggestions into hard constraints.

## 7.3 Work display derives from actual resources

Do NOT trust stale `work_choice`.

- Pick exists iff `pda_serial` or `user_pick` exists.
- Pack exists iff `pack_table` or `user_pack` exists.

Display:
- none → `Làm theo vị trí chính`
- Pick → `Làm theo vị trí chính & Pick`
- Pack → `Làm theo vị trí chính & Pack`
- both → `Làm theo vị trí chính & Pick & Pack`

## 7.4 Multiple positions/resources

S64 supports the approved multi-position / multi-resource session model.

A session may have multiple distinct assignments/resources over its lifetime. History must preserve each assignment rather than flattening all changes into one lossy `current work` field.

---

# 8. THÊM / SỬA / XÓA — FINAL OWNER STATE MACHINE

This section explicitly supersedes older ambiguous V15/V16 interpretations.

## 8.1 THÊM = create NEW assignment/data, never silently edit existing data

Core rule:
- `THÊM` creates a new assignment/resource record.
- It must not overwrite or mutate an existing assignment as a side effect.

UI guidance:
- if only Pick currently exists → suggest adding Pack;
- if only Pack currently exists → suggest adding Pick;
- if neither Pick nor Pack exists → show Pick and Pack;
- if both already exist → `THÊM` must NOT be globally blocked when the operator needs another distinct assignment/user/resource.

Latest OWNER rule:
- multiple User Pick or multiple User Pack assignments in the same session are allowed when they are distinct new assignments;
- same work type may therefore appear more than once when the newly-added user/resource assignment is genuinely new;
- an exact duplicate of the same assignment is not `new data` and must not be created merely by retry/replay.

This resolves the older conflict:
- `ADD only new data` remains true at assignment identity level;
- it does NOT mean `only one Pick row and one Pack row forever`.

Công nhật remains separate and is NOT part of the Add Pick/Pack state machine.

Important preservation edge case:
- when Pack already exists and adding Pick, the existing Pack assignment/resources must remain intact;
- when Pick already exists and adding Pack, the existing Pick assignment/resources must remain intact.

## 8.2 SỬA = edit an exact existing assignment/resource

- User must select/target the existing data to edit.
- Do not implicitly edit all Pick/Pack rows.
- Edit may change otherwise-valid fields freely, including current position, User Pick/User Pack, PDA, Pack table and the selected assignment's relevant fields.
- Editing is NOT locked to the previous Pack table, previous position or previous User.
- Example: previous Pack table `D1` does not mean Edit may only choose `D1` or only users formerly associated with `D1`.

Pack User and Pack table are independent business selections unless a real explicit conflict rule applies.

When an edit replaces/removes an old resource/user, the old assignment's disposition must be decided correctly (USED vs AVAILABLE) rather than silently freeing or silently locking it.

Công nhật is handled by its separate workflow; do not reuse QR shift SỬA semantics to mutate Công nhật records.

## 8.3 XÓA = delete selected assignment/resource OR entire session

XÓA must allow exact targeting of:
- a selected user;
- a selected position;
- a selected resource;
- a selected work assignment;
- or the whole attendance session.

If deleting the entire attendance session:
- realtime password verification is required;
- prompt wording retained from earlier rule: `Nhập mật khẩu thực tế`;
- operational current-state rows may be removed/tombstoned according to the service model;
- audit/event history must remain append-only and detailed.

Deleting one assignment/resource must not erase unrelated assignments in the same session.

Công nhật deletion remains separate from QR shift delete logic.

---

# 9. RESOURCE DISPOSITION — USED vs AVAILABLE

Whenever replacing/deleting/releasing an issued user/resource, the operator must be able to state the real condition.

## 9.1 Cấp nhầm / chưa sử dụng

UI/business meaning:
`Cấp nhầm / chưa sử dụng`

Canonical disposition:
`AVAILABLE`

Effect:
- assignment becomes void/released as appropriate;
- lease is removed immediately;
- resource/user becomes AVAILABLE immediately;
- do NOT wait until shift exit.

This explicitly supersedes any old `chờ ra ca mới available` behavior.

## 9.2 Đã sử dụng / có sản lượng

UI/business meaning:
`Đã sử dụng / có sản lượng`

Canonical disposition:
`USED`

Effect:
- usage/consumption/history remains preserved;
- do not falsely return it to the normal unused list for that governed business context;
- audit must preserve who used it and in which assignment/session.

Older notes may describe the business meaning as `USED_LOCKED`; the canonical S64 disposition used by current logic is `USED`.

---

# 10. USER PICK / USER PACK / REISSUE — OWNER LOCK

## 10.1 Normal chooser vs reissue chooser

Normal Pick/Pack dropdowns:
- show unused/available users only.

Separate deliberate paths:
- `Phát lại user pick`
- `Phát lại user pack`

Used users MUST NOT be appended into the normal unused list.

Only the explicitly selected used user is reapplied.

UI details retained:
- `Phát lại user pick` and `Phát lại user pack` remain separate actions and should fit cleanly without overflow;
- User lists use natural numeric sorting rather than lexicographic anomalies;
- keep the approved normal/none labels such as `User Pick hy1.outbound` and `Không dùng` where those labels apply.

Preserve reissue semantics:
- `duplicate_user`
- `PHÁT LẠI USER`

## 10.2 Reuse depends on explicit operator action

Do not hard-lock a user globally just because it was used earlier.

Operational reason:
- staff may accidentally run each other's user between shifts;
- example: shift 1 used `user16`; shift 2 may intentionally need to select/reissue `user16` again.

Therefore:
- normal chooser remains clean/unused;
- deliberate reissue remains possible;
- the operator's explicit selection is decisive subject to actual current resource/session conflict rules.

## 10.3 User Pack independent from Pack table

User Pack must not be filtered or locked by selected Pack table.

Forbidden regression:
- filtering User Pack list to only rows whose `table == selected_table`;
- restricting Edit because old table was `D1`.

---

# 11. PDA — CURRENT OWNER REQUIREMENTS

## 11.1 Pick/PDA

Preserve existing approved Pick resource rules unless a newer OWNER instruction changes them.

PDA selection/lookup uses serial identity and validated last-5-digit support.

## 11.2 Đổi / Trả PDA

The screen should immediately show currently-used PDA under the PDA search area.

Search UX:
- remove the separate `Tìm` button;
- typing/input must filter automatically;
- empty search → show all current holders;
- exactly 5 digits → match `serial.takeLast(5) == query`;
- otherwise → full serial exact, case-insensitive;
- do NOT use fuzzy `contains` matching.

Show only PDA that are actually in use/held for the operational list.

Each PDA card:
- emphasize full serial (larger/bold);
- Mã nhân viên;
- Họ tên;
- Vị trí chính;
- Nhà cung cấp;
- Bộ phận;
- Site;
- Kho.

The card/serial area is actionable:
- re-fetch current employee/session context before mutation;
- confirm the PDA is still the active current PDA;
- then open Return/Exchange confirmation.

`Đổi PDA`:
- old PDA → new PDA only;
- preserve shift/work/User Pick/User Pack/Pack table unless the explicit mutation says otherwise.

`Trả PDA`:
- release/clear only PDA resource;
- preserve unrelated session/work/resources.

Exit edge case:
- if the employee is exiting and does not currently hold a PDA, do not force a PDA-return step; continue the normal exit flow.
- do not add redundant explanatory caption text under the current-PDA list if the list/cards already communicate the state.

---

# 12. EMPLOYEE SCAN / ASYNC FENCING — NEVER REGRESS

All employee scan inputs should use compact one-line layout where applicable, with text:

`Scan / Nhập mã nhân viên`

Critical stale-callback rule:

If employee A was scanned, then the operator scans employee B while A's async request is still running, a late callback for A MUST NOT reset or overwrite B.

Reset/re-render is legal only when BOTH:
- employee identity still matches the initiating MNV;
- lookup generation/context still matches.

This applies to:
- attendance exit/reset;
- add/edit work callback;
- delete work callback;
- other employee-context async mutations that could reset the current UI.

---

# 13. SESSION TIMELINE / HISTORY — EXACT SESSION, MULTI-DEVICE

## 13.1 Exact-session timeline

- prefer exact `session_id`;
- legacy event without session_id only if timestamp falls inside current session enter→exit window;
- same filtering for canonical events and local pending/queued events;
- never scope current-session timeline by MNV alone.

## 13.2 History across devices

History is operational history, not `this device only`.

The user must be able to see relevant history generated from different devices/accounts where permitted by the project data model.

Device-local-only filtering must not hide canonical history from other machines.

---

# 14. LOG / NHẬT KÝ — OWNER REQUIREMENT

The Nhật ký/log UI must be more detailed.

When the user taps a log row:
- expand/open full session detail;
- include all fields shown in the current Rà soát Vào–Ra view;
- show file information if a file is attached;
- show file size when available.

Do not show meaningless `0 tệp / 9b` style summaries when actual file/log metadata says otherwise. Derive count/size from real data.

Missing fields can be extended by later OWNER instruction; do not invent unsupported fields.

---

# 15. RA - VÀO TRONG CA / RECONCILIATION DATA

Attendance/session output must carry the approved session resources rather than leaving them blank.

Required session-level fields include:
- Vị trí trong ca;
- Seri PDA;
- User Pick;
- Bàn Pack;
- User Pack.

If multiple distinct values of the same type occurred in one session:
- represent the unique set/list according to the approved sheet/service schema;
- retry/replay must not create duplicate copies of the same value.

`THÔNG TIN USER CỦA NLĐ`-style detail, where still used, must preserve individual user assignments sufficiently for audit/reconciliation rather than collapsing all users into one ambiguous row.

---

# 16. QR / OPERATIONS UI OWNER REQUIREMENTS — PRODUCT LOCK, VERIFY BEFORE CLAIMING IMPLEMENTED

These are OWNER requirements. If a fresh source/live check has not proven them, treat them as `REQUIREMENT / VERIFY`, not automatically as already PASS.

## 16.1 Header / top status

Authenticated shell:
- compact spacing;
- user greeting/account area must not waste vertical space;
- Mạng / Đồng bộ / Dịch vụ status remains user-facing and compact;
- include the refresh icon at the top-right, horizontally aligned with the greeting/account area;
- tapping refresh triggers a fresh sync/read according to the approved sync/authority model.

## 16.2 Reconciliation card placement

Đối soát Vào–Ra:
- placed outside/above the normal Nghiệp vụ work cards, below the Mạng/Đồng bộ/Dịch vụ status area;
- only show when the relevant shift has staff/data;
- format shift summary like `Ca 1 - xx/yy`;
- include a `Tổng` row at table bottom;
- time display uses `HH:mm`;
- support filtering such as all / has time / no time where this view provides that filter.

`RA` action should be visually separated/on its own line from Add/Edit/Delete controls.

## 16.3 Main tab shell

Keep five authenticated tabs in this order:

`Nghiệp vụ – Nhân sự – Lịch sử – Đồng bộ – Cài đặt`

The Nhân sự tab must exist; do not remove it again unless OWNER explicitly changes the five-tab shell.

Swipe from the left edge to the right inside nested views should go back to the previous in-app view rather than unexpectedly exiting the app.

## 16.4 Nghiệp vụ

- Add `Quản lý biên bản` card/item with correct semantic icon.
- Current status: placeholder / chờ xây dựng until separate implementation instruction.
- Remove `Người dùng đang kết nối`.
- Remove `còn xx mục chờ gửi`.

## 16.5 Đồng bộ — separate information domains

Do not mix PDA / Service / Google Sheet facts together.

PDA area:
- app version;
- PDA model;
- PDA serial.

Service area:
- service version;
- service connection/operating state.

Google Sheet area:
- latest sync time;
- latest sync success/failure state.

## 16.6 Cài đặt

`Thông tin ứng dụng` belongs under `Cài đặt`, not under `Tài nguyên`.

App information must show real app cache size calculated from `cacheDir + codeCacheDir` using the human-readable formatter; never substitute APK file size.

## 16.7 QR interaction details

- `Sửa giờ` is a separate action from SỬA công việc/resource; do not conflate time correction with assignment editing.
- Where the existing history view exposes three primary history actions/filters, keep them on one balanced row when screen width allows rather than wasting vertical space.
- Resource/UI errors must not be collapsed to an unhelpful generic `UNKNOWN` when a concrete service/business error is available; surface a user-safe specific result while preserving technical detail in logs.

---

# 17. LOGIN UI — OWNER LOCK

The login screen must match the approved full-frame reference composition and remain fully visible on different display sizes.

Layout:
- scale constrained by both width and height;
- no cropping of the designed frame;
- do not use a crop behavior that cuts off approved content.

Controls:
- Đăng nhập;
- Quên mật khẩu;
- Hiện/ẩn mật khẩu;
- Đăng ký.

Do not add:
- `Đăng nhập bằng tài khoản khác` option as a separate login-screen feature;
- a `Ghi nhớ đăng nhập` checkbox.

This does not cancel the approved persistent authenticated session behavior: the app may keep the authenticated session across app/process closure until logout/security/session replacement rules invalidate it.

Cultural/visual restrictions:
- Vietnam flag;
- correct Vietnam map;
- standardized Đông Sơn drum motif;
- Hồ Gươm/Tháp Rùa;
- cầu Thê Húc;
- lotus;
- no AI-invented đình/chùa/cổng or unrelated architecture.

Copyright exactly:

`Copyright 2026 Supra DC Hưng Yên  -  tamnv2  -  Chuyên viên Pick Pack 1291`

---

# 18. GOOGLE SHEET PRESENTATION REQUIREMENT

For daily operational Google Sheets where this formatting rule applies:

- font: `Times New Roman`
- font size: `13`
- background: white
- text: black
- row 1/header: bold + light-blue background
- keep columns readable/compact and consistent

Formatting is presentation only; it must not change data authority, event identity, idempotency or audit semantics.

---

# 19. UI/UX GENERAL RULES TO PRESERVE

- professional, simple, smooth; avoid ornamental/heavy animation;
- maximize useful content area without cramped spacing;
- semantic icons;
- routine notices use non-blocking top notification queue where approved;
- do not expose developer/API/AI implementation commentary to ordinary users;
- hardware/keyboard Enter/OK should trigger scanner flows without redundant `Kiểm tra` buttons when the same action is already scan-driven;
- launcher/login approved artwork must not be freely redesigned.

---

# 20. RELEASE / BUILD RESUME MODEL — MANDATORY

Canonical stages:

`R0 fresh truth`
→ `R1 pin product source`
→ `R2 business/security/static gates`
→ `R3 compile`
→ `R4 lock ONE signed candidate`
→ `R5 Service/GAS prerequisites`
→ `R6 Drive exact bytes + readback`
→ `R7 previous→target OTA + target self no-update`
→ `R8 Stable isolation`
→ `R9 GitHub prerelease + final health`
→ `R10 final receipt + cumulative handover`

Failure rules:

## Before R4
A real source/compile/signing-input defect may be fixed and rebuilt.

## After R4
The signed candidate is immutable for that release attempt.

Downstream failures:
- Drive;
- GAS;
- OTA;
- GitHub Release;
- connector;
- network;
- OAuth scope;
- public byte readback;
- receipt transport

MUST reuse the same exact signed candidate bytes.

Do not rebuild/resign after R4 merely because transport is difficult.

## PASS reuse

If exact source/artifact/hash/live prerequisite inputs remain unchanged, do not rerun a proven PASS stage merely for ceremony.

Fresh-read the PASS evidence and resume from the first genuinely unresolved stage.

---

# 21. GOOGLE DRIVE / OAUTH TRANSPORT LESSON

A GitHub Actions OAuth exchange may succeed but still produce a token without sufficient Drive API scope and fail with:

`ACCESS_TOKEN_SCOPE_INSUFFICIENT`

That is not automatically an OWNER blocker.

If the connected Google Drive authority can transport the exact locked candidate:
- use it;
- preserve exact bytes;
- continue release.

Large public Drive APK downloads may return a virus-warning HTML confirmation page. Verifier must follow the confirmation form/UUID flow and hash the actual APK, not the warning HTML.

---

# 22. BRANCH / PR SAFETY

Known Beta65 branches:
- product: `agent/beta65-session-resource-login-parity-20260824`
- release carrier: `release-carrier/beta65-20260824`
- CI/evidence: `ci/beta65-final-release-base-20260824`

Product/evidence PR #123 is not Stable/main merge authorization.

Temporary release/evidence PRs must remain unmerged when their purpose is only evidence/transport.

Do not force-push or rewrite shared production history merely for cosmetic cleanup.

This V21 lives on a dedicated handover branch so it does not mutate immutable Beta65 receipt evidence.

---

# 23. SECURITY / OWNER WORKSTATION CONSTRAINTS

- no secrets/tokens/passwords/signing keys in public repo;
- no plaintext credential publication in handover;
- do not ask OWNER to use CMD, PowerShell, Terminal, bash, git, gh, adb, Gradle, Node, keytool, OpenSSL or similar CLI on the company-managed workstation;
- prefer connected tools, browser UI, GitHub Actions/CI and provider UI;
- only require OWNER browser/manual action when a true authorization step cannot be completed by an existing authorized path.

---

# 24. DEFINITION OF DONE — FUTURE AI MUST USE THIS

## Source change task
DONE only when:
- requested logic implemented;
- relevant static/business tests PASS;
- Beta compile PASS;
- Stable isolation/compile gate remains PASS where required;
- no known regression in locked rules.

## Service change task
DONE only when:
- exact service source/deployment identified;
- production deployment/readback is proven;
- authority is correct;
- replication health is proven;
- old detached service is not accidentally revived;
- relevant business API behavior is verified.

## Beta release task
DONE only when:
- source gates PASS;
- exact signed candidate locked;
- identity/package/version/signer/hash/size proven;
- exact candidate published to Drive;
- Drive exact-byte readback PASS;
- GAS target PASS;
- previous→target OTA PASS;
- target self no-update PASS;
- Stable isolation PASS;
- GitHub prerelease/readback PASS if required by release model;
- final service health PASS;
- final receipt written/read back;
- cumulative handover updated.

A triggered workflow, uploaded artifact or successful build alone is NOT a release.

## Documentation/handover task
DONE only when:
- live truth is fresh-read;
- new OWNER decisions are merged;
- superseded decisions are explicitly marked;
- current release/service identities are retained exactly;
- pending requirements are labeled as requirements, not falsely claimed implemented;
- next session can resume without asking OWNER to restate decisions.

---

# 25. CHANGE REGISTER — WHAT V21 ADDS/CLARIFIES OVER V20

1. Strong anti-stop continuation contract with explicit invalid stopping states.
2. Explicit hard-blocker definition and alternate-path requirement.
3. Explicit stale-document override for old GAS/GSheet-only architecture text.
4. Detailed one-session-per-business-date rule with cross-midnight/new-day example.
5. Detailed Add/Edit/Delete state machine.
6. Resolution of old ADD conflict:
   - Add = new assignment, not overwrite;
   - multiple same-type user assignments are allowed when distinct;
   - exact duplicate is not a new assignment.
7. Explicit old-resource disposition on replace/delete.
8. Immediate AVAILABLE for mistaken/unused issuance.
9. USED preservation for genuinely used/production resource.
10. Reissue user remains separate from normal unused list.
11. Explicit operator-selected reuse across shifts; no false global user lock.
12. Pack User independent from Pack table.
13. Add/Edit free choice; no D1/old-table/old-position lock.
14. Detailed PDA Return/Exchange current-holder list and exact last-5 lookup.
15. Multi-device history requirement.
16. Expanded Nhật ký/log requirement.
17. Session-level RA-VÀO fields including Vị trí trong ca and resources.
18. Pending/OWNER UI requirements separated from proven Beta65 release truth.
19. `Quản lý biên bản` placeholder requirement.
20. Remove `Người dùng đang kết nối` and `còn xx mục chờ gửi`.
21. Đồng bộ tab separation for PDA / Service / Google Sheet information.
22. Move `Thông tin ứng dụng` to Cài đặt.
23. Restore/retain Nhân sự tab and five-tab shell.
24. Reconciliation placement/visibility/summary requirements.
25. Google Sheet presentation formatting requirement.
26. Strict definition-of-DONE for source/service/release/handover work.
27. PDA search is automatic with no separate Tìm button; exact last-5/full-serial matching retained.
28. Exit does not force PDA-return workflow when employee holds no PDA.
29. Top-right refresh icon is an explicit requirement, not an optional suggestion.
30. `Sửa giờ` remains separate from work/resource Edit.
31. User/reissue lists retain natural numeric sorting and separate non-overflow reissue actions.

---

# 26. NEXT SESSION START CHECKLIST

A future AI receiving this file should:

1. state that V21 is loaded as canonical continuation truth;
2. fresh-read live state relevant to the new task;
3. do NOT re-release/rebuild Beta65;
4. start Android source work at Beta66+/VC72+;
5. preserve Service S64 unless the new task requires a service change;
6. preserve Stable lock;
7. preserve all Owner business rules in sections 6–18;
8. treat section 16 items as OWNER requirements that must be verified against current source/live state before claiming implemented;
9. execute the new task end-to-end;
10. do not stop at planning/trigger/pending/partial PASS.

---

# 27. FINAL CANONICAL STATE

Beta65 release:
`DONE`

Service:
`S64 / SERVICE_PRIMARY / PRODUCTION`

Replication:
`HEALTHY`

Stable:
`0.1.0-stable / VC1 / UNTOUCHED / PUBLISH FORBIDDEN`

Next Android:
`Beta66+ / VC72+`

This V21 supersedes V20 as the preferred continuation/handover document for future work while preserving V20 and Beta65 receipts as immutable historical evidence.
