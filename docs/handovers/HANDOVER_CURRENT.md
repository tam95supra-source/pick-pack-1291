---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-08-26T18:18:00+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: feature/beta77-owner-fixes-20260826
working_head_sha: d6e04218ab22342d1505184ed99ffc8ca5ec7d92
archive_file: null
base_or_live_version: 0.4.2-beta.76
target_version: 0.4.2-beta.77
task_state: IN_PROGRESS
next_action: FIX_BETA77_RELEASE_META_VERIFIER_CONTRACT_THEN_RETRY_EXACT_PUBLISH
---

# BÀN GIAO CANONICAL — BETA77 IN PROGRESS

## 1. OWNER / DoD
- Hoàn tất Beta77 bằng exact candidate đã khóa; không tạo Beta78, không rebuild/resign/version bump.
- GAS canonical và Service/PDA LIVE đã PASS; cấm rerun.
- Stable publish FORBIDDEN; main/signer/authority/provider phải giữ nguyên.
- Final chỉ khi Beta77 OTA LIVE PASS → OTA/Drive/public bytes/LIVE khớp → Stable/main unchanged → release receipt/CURRENT_STATE/handoff READY.

## 2. LIVE / EXACT CANDIDATE
- LIVE hiện tại: Beta76 `0.4.2-beta.76`, versionCode `82`.
- Exact Beta77 source: `43579d1f7f01816cddbdbbcce0a2f19d95d16d91`.
- Candidate run/artifact: `32953924512` / `9601304499`.
- Version/code/package: `0.4.2-beta.77` / `83` / `vn.pickpack1291.app.beta.publicbeta`.
- SHA256: `6ce7838f6f0725ca98b4f3d9237d38aec60092f4488b2795a32ae3f9d24371fb`.
- Size: `13196165` bytes.
- Signer: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.

## 3. Visual/HUMAN — PASS, KHÔNG RERUN
- Final visual run/artifact `32960147493` / `9603638990`; receipt commit `847378116153befe7b10a29951df43913e864636`.
- HUMAN_VISUAL_PASS đủ `320x568`, `360x640`, `480x800`; Android build/sign trong visual=false.

## 4. Canonical inherited PASS — KHÔNG RERUN
- GAS: run `32932894375`, Apps Script `194`, artifact `9593853159`, digest `sha256:2b939d18e7db7e74925771516925716f6a4c98e1c7ed3a2c92c9418a0e86fcc1`.
- Service/PDA: run `32953215533`, worker version `0cd7e517-a03b-4dae-80e3-8acb0f437c84`, artifact `9600983380`, digest `sha256:b4da9784cd70eb7b2384c901c0e404104091fed208225032efa4417b4bf9ec36`.

## 5. Publish deterministic failures
- `32960698432`: compat anchor defect — fixed.
- `32961961420`: semantic Beta76→Beta77 shift defect — fixed.
- `32962143541`: stale inherited candidate/visual receipt IDs — fixed at `cb5417f274c7e16a4e08914422562f5096ecf0b5`.
- `32962400902`, job `98157421050`: preflight PASS hoàn toàn; publish step bắt đầu rồi fail. Evidence artifact `9604380172`, digest `sha256:5135ba8f0b9a68bb1268ded7ccd1bc04c9791f8735134b65c4a11867998bf7b6` chỉ có `beta-before.json` và `stable-before.json`, chứng minh fail trước OAuth/GAS/Drive mutation.
- Fresh evidence: `beta-before` vẫn Beta76 code82 SHA `7018977f...`, `stable-before` vẫn `NO_APK`.
- Exact artifact `9601304499` đã tải/giải nén ngoài workflow: APK SHA/size/checksum/meta đều đúng.
- Lỗi gốc deterministic: inherited publisher metadata verifier yêu cầu `.service_change=="NONE"`; Beta77 release-meta canonical không có field này mà có `.authority_change=="NONE"` cùng `gas_run/gas_artifact/service_run/service_artifact`. Reproduce: inherited jq rc=1; Beta77 canonical receipt gate rc=0.
- Đường PASS: sửa verifier theo contract Beta77 canonical, bắt buộc authority NONE + GAS run/artifact + Service run/artifact đúng; không sửa APK/meta bytes.

## 6. Invariants
- Không rerun candidate/visual/GAS/Service.
- Không rebuild/resign/version bump.
- Stable/main/signer/authority/provider không đổi.
- Chỉ publish exact artifact `9601304499`.

## 7. NEXT_ACTION
`FIX_BETA77_RELEASE_META_VERIFIER_CONTRACT_THEN_RETRY_EXACT_PUBLISH`
