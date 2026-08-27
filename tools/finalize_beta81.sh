#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_SHA=963ed28a90d2bb3e4a950ae8100fef15edfa86c5
EXPECTED_SIGNER=d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e
BRANCH=feature/beta78-old-session-outbound-service-20260826
R=/tmp/beta81-pda/receipt.json

for n in GH_TOKEN GITHUB_API_URL GITHUB_REPOSITORY GITHUB_RUN_ID GITHUB_SHA APK_SHA APK_SIZE; do
  test -n "${!n:-}"
done
test -f "$R"

jq -e --arg h "$APK_SHA" --argjson z "$APK_SIZE" --arg signer "$EXPECTED_SIGNER" '
  .status=="PASS" and
  .version_name=="0.4.2-beta.81" and
  .version_code==87 and
  .candidate_artifact==9646920908 and
  .apk_sha256==$h and
  .apk_size==$z and
  .signer_sha256==$signer and
  .ota_from_beta80==true and
  .installed_exact_bytes==true and
  .fixes.reconciliation_ended_exit_only==true and
  .fixes.reconciliation_home_1_0==true and
  .fixes.reconciliation_qr_1_0==true and
  .fixes.scanned_old_session_warning==true and
  .fixes.midnight_rollover_old_active_preserved==true and
  .fixes.old_resources_not_released==true and
  .beta_readback.ok==true and
  .beta_readback.version_name=="0.4.2-beta.81" and
  .beta_readback.sha256==$h and
  .beta_readback.size==$z and
  .stable_unchanged==true and
  .main_unchanged==true and
  .authority.mode=="SERVICE_PRIMARY" and
  .authority.scope=="PRODUCTION" and
  .authority_change=="NONE"
' "$R" >/dev/null

MAIN_FRESH=$(curl -fsSL --connect-timeout 15 --max-time 30   -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json'   "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/branches/main" | jq -r '.commit.sha')
test "$MAIN_FRESH" = "$(jq -r '.main_sha' "$R")"
test "$MAIN_FRESH" = a8c0c0d92522c7173230d4175b4f0d3a4906c8bb

JOBS=$(curl -fsS -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json'   "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID/jobs?per_page=100")
PDA_JOB_ID=$(jq -r '.jobs[] | select(.name=="pda-verify" and .conclusion=="success") | .id' <<<"$JOBS" | head -n1)
test -n "$PDA_JOB_ID" -a "$PDA_JOB_ID" != null

NOW=$(TZ=Asia/Bangkok date '+%Y-%m-%dT%H:%M:%S%z')
STAMP=$(TZ=Asia/Bangkok date '+%Y%m%d-%H%M%S')
ARCHIVE="docs/handovers/HANDOVER_${STAMP}_beta81-pass-live.md"
AUTH_EPOCH=$(jq -r '.authority.authority_epoch' "$R")
AUTH_GEN=$(jq -r '.authority.service_generation' "$R")

cat > ops/beta-release-request.json <<EOF
{
  "stage": "pass_live",
  "mode": "PUBLISH_ONLY_EXACT_BYTES",
  "version_name": "0.4.2-beta.81",
  "version_code": 87,
  "base_version": "0.4.2-beta.80",
  "base_version_code": 86,
  "source_sha": "$SOURCE_SHA",
  "candidate_run_id": 33073351925,
  "candidate_artifact_id": 9646920908,
  "package": "vn.pickpack1291.app.beta.publicbeta",
  "apk_sha256": "$APK_SHA",
  "apk_size": $APK_SIZE,
  "signer_sha256": "$EXPECTED_SIGNER",
  "locked_run_id": 33073351925,
  "locked_artifact_id": 9646920908,
  "locked_sha256": "$APK_SHA",
  "locked_size": $APK_SIZE,
  "locked_signer_sha256": "$EXPECTED_SIGNER",
  "service_run_id": 33073351925,
  "service_artifact_id": 9646805806,
  "final_visual_run_id": 33073351925,
  "final_visual_artifact_id": 9647045177,
  "final_visual_artifact_digest": "sha256:ca119c02e7e4133892b337245205bd3a06bd4635fd435f20a74ae7a1cb2d54b7",
  "stable_publish": "FORBIDDEN",
  "rebuild": false,
  "resign": false,
  "authority_change": "NONE",
  "scope": "beta81-shift-reconciliation-qr-old-session-midnight-rollover",
  "owner": "Nguyen Van Tam"
}
EOF

cat > CURRENT_STATE.md <<EOF
# CURRENT STATE — PICK PACK 1291

- updated_at: $NOW
- status: BETA81_PASS_LIVE
- continuity_branch: $BRANCH
- source_sha: $SOURCE_SHA
- workflow_head_sha: $GITHUB_SHA
- beta_live: 0.4.2-beta.81 (versionCode 87)
- candidate_run: 33073351925
- candidate_artifact: 9646920908
- visual_artifact: 9647045177
- service_artifact: 9646805806
- apk_sha256: $APK_SHA
- apk_size: $APK_SIZE
- signer_sha256: $EXPECTED_SIGNER
- terminal_run: $GITHUB_RUN_ID
- pda_job: $PDA_JOB_ID
- beta81_device_receipt: đối soát ENDED+exit_at; QR có rà soát; cảnh báo phiên cũ; rollover qua 24:00 giữ ACTIVE và không giải phóng PDA/User — PASS
- beta_ota: exact Beta81 PASS
- stable: unchanged
- main_sha: $MAIN_FRESH (unchanged)
- authority: SERVICE_PRIMARY / PRODUCTION / epoch $AUTH_EPOCH / generation $AUTH_GEN (unchanged)
- next_action: WAIT_FOR_OWNER_NEW_SCOPE
EOF

mkdir -p docs/handovers
cat > docs/handovers/HANDOVER_CURRENT.md <<EOF
# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time: $NOW
- owner: Nguyễn Văn Tâm
- branch: $BRANCH
- working_head_sha: $GITHUB_SHA
- archive_file: $ARCHIVE

## Mục tiêu + DoD
Hoàn tất Beta81 bằng exact candidate 9646920908: OTA LIVE, hash/size/signer khớp, ba lỗi Beta81 PASS trên bản cài từ OTA; Stable/main/signer/authority không đổi.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.81 / versionCode 87.
- TARGET: PASS/LIVE hoàn tất.
- CANDIDATE LOCKED: run 33073351925; artifact 9646920908; source $SOURCE_SHA; SHA256 $APK_SHA; size $APK_SIZE; signer $EXPECTED_SIGNER.
- Visual: artifact 9647045177 PASS.
- Service evidence: artifact 9646805806 PASS.
- Stable: unchanged.
- main: $MAIN_FRESH unchanged.
- authority: SERVICE_PRIMARY / PRODUCTION / epoch $AUTH_EPOCH / generation $AUTH_GEN unchanged.

## Evidence / locked identity
- Terminal workflow run: $GITHUB_RUN_ID.
- pda-verify job: $PDA_JOB_ID SUCCESS.
- Exact OTA from Beta80 -> Beta81 + Android PackageInstaller: PASS.
- Installed base APK SHA/size/signer equals exact candidate: PASS.
- Rà soát chỉ tính RA khi ENDED + exit_at, Ca 2 1/0 cảnh báo: PASS.
- QR nhân viên có rà soát ngày hiện tại + cảnh báo phiên cũ: PASS.
- Qua 24:00 giữ prior-day ACTIVE và khóa PDA/User không giải phóng nhầm: PASS.
- Final receipt artifact: beta81-final-$GITHUB_RUN_ID.

## File / commit đã đổi
- .github/workflows/beta-release.yml: Beta81 exact publish/device gates + always() TXT finalizer.
- tools/publish_beta81_ota.sh, tools/build_beta81_verify_harness.sh, tools/Beta81LocalChecksInstrumentation.java, tools/beta81_pda_device_gate.sh: release/harness only.
- ops/beta-release-request.json, CURRENT_STATE.md và handoff canonical/archive do finalize cập nhật.
- Không rebuild/resign candidate Beta81.

## Lỗi + root cause + đường PASS / cấm lặp
- Hai run 33076098876 và 33076266568 không tạo job vì workflow YAML heredoc/validation; không tác động APK/OTA.
- Đường PASS: đưa logic lớn ra tools, workflow tối giản; exact candidate giữ nguyên.
- Cấm lặp candidate/visual/service run 33073351925 khi source/artifact không đổi.

## Workspace / CI / external state
- Beta81 OTA readback PASS; Stable/main/authority unchanged.
- Exact candidate bytes giữ nguyên từ artifact 9646920908.

## Việc còn lại
Không còn việc trong scope Beta81.

## Blocker / quyền
Không có blocker OWNER.

## Invariants
Không đổi Stable/main/signer/authority; không rebuild/resign exact candidate; không thêm backend/provider/authority.

## NEXT_ACTION
WAIT_FOR_OWNER_NEW_SCOPE
EOF

cp docs/handovers/HANDOVER_CURRENT.md "$ARCHIVE"
mapfile -t OLD_ARCHIVES < <(find docs/handovers -maxdepth 1 -type f -name 'HANDOVER_20????????-??????_*.md' | sort)
if (( ${#OLD_ARCHIVES[@]} > 5 )); then
  for f in "${OLD_ARCHIVES[@]:0:${#OLD_ARCHIVES[@]}-5}"; do
    rm -f "$f"
  done
fi

git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add ops/beta-release-request.json CURRENT_STATE.md docs/handovers
git diff --cached --quiet && { echo FINALIZE_STATE_NOT_CHANGED; exit 1; }
git commit -m '[skip ci] finalize Beta81 PASS/LIVE'
FINAL_COMMIT=$(git rev-parse HEAD)
git push origin "HEAD:$BRANCH"
git fetch origin "$BRANCH" --quiet
test "$(git rev-parse "origin/$BRANCH")" = "$FINAL_COMMIT"
test "$(git show "origin/$BRANCH:CURRENT_STATE.md" | grep -c BETA81_PASS_LIVE)" = 1
test "$(git show "origin/$BRANCH:docs/handovers/HANDOVER_CURRENT.md" | grep -c 'status: READY')" = 1

mkdir -p /tmp/beta81-final
jq --argjson run "$GITHUB_RUN_ID" --argjson job "$PDA_JOB_ID"   --arg source "$SOURCE_SHA" --arg commit "$FINAL_COMMIT" --arg finalized "$NOW"   '. + {
    terminal_run_id:$run,
    pda_job_id:$job,
    source_sha:$source,
    handoff_commit_sha:$commit,
    finalized_at:$finalized,
    final_receipt:true,
    readback:true
  }' "$R" > /tmp/beta81-final/receipt.json
jq -e '.status=="PASS" and .final_receipt==true and .readback==true and (.handoff_commit_sha|length)==40'   /tmp/beta81-final/receipt.json >/dev/null
cat /tmp/beta81-final/receipt.json
