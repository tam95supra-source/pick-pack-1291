#!/usr/bin/env bash
set -uo pipefail

SOURCE_SHA=963ed28a90d2bb3e4a950ae8100fef15edfa86c5
EXPECTED_SIGNER=d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e
BRANCH=feature/beta78-old-session-outbound-service-20260826
OUT="/tmp/PICK_PACK_1291_HANDOFF_${GITHUB_RUN_ID}.txt"
META=/tmp/beta81-handoff-candidate/release-meta.json

APK_SHA=UNKNOWN
APK_SIZE=UNKNOWN
SIGNER="$EXPECTED_SIGNER"
if [[ -f "$META" ]]; then
  APK_SHA=$(jq -r '.apk_sha256 // "UNKNOWN"' "$META")
  APK_SIZE=$(jq -r '.apk_size // "UNKNOWN"' "$META")
  SIGNER=$(jq -r '.signer_sha256 // "'"$EXPECTED_SIGNER"'"' "$META")
fi

JOBS=$(curl -fsS -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json'   "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID/jobs?per_page=100" 2>/dev/null || echo '{"jobs":[]}')
ARTS=$(curl -fsS -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json'   "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID/artifacts?per_page=100" 2>/dev/null || echo '{"artifacts":[]}')

FIRST_ERROR=NONE
FAIL_JOB=$(jq -r '.jobs[] | select(.conclusion=="failure") | .id' <<<"$JOBS" | head -n1)
if [[ -n "$FAIL_JOB" ]]; then
  curl -fsSL -H "Authorization: Bearer $GH_TOKEN"     "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/actions/jobs/$FAIL_JOB/logs" > /tmp/beta81-first-fail.log 2>/dev/null || true
  FIRST_ERROR=$(grep -m1 -E '##\[error\]|FAILED|FAILURE|ERROR:' /tmp/beta81-first-fail.log | head -c 500)
  [[ -n "$FIRST_ERROR" ]] || FIRST_ERROR="JOB_${FAIL_JOB}_FAILED"
elif [[ "${PUBLISH_RESULT:-}" == cancelled || "${PDA_RESULT:-}" == cancelled || "${FINALIZE_RESULT:-}" == cancelled ]]; then
  FIRST_ERROR=WORKFLOW_CANCELLED
fi

if [[ "${FINALIZE_RESULT:-}" == success ]]; then
  NEXT_ACTION=WAIT_FOR_OWNER_NEW_SCOPE
elif [[ "${PUBLISH_RESULT:-}" != success ]]; then
  NEXT_ACTION=FIX_PUBLISH_FAILURE_AND_RERUN_RELEASE_WORKFLOW_USING_EXACT_CANDIDATE_9646920908
elif [[ "${PDA_RESULT:-}" != success ]]; then
  NEXT_ACTION=FIX_PDA_VERIFY_FAILURE_DOMAIN_AND_RERUN_WITHOUT_REBUILDING_OR_RESIGNING_CANDIDATE_9646920908
else
  NEXT_ACTION=FIX_FINALIZE_STATE_HANDOFF_FAILURE_WITHOUT_RERUNNING_PASSED_PUBLISH_OR_PDA_GATES
fi

git fetch origin "$BRANCH" --quiet >/dev/null 2>&1 || true
LIVE=UNKNOWN
if git show "origin/$BRANCH:CURRENT_STATE.md" >/tmp/beta81-current-live.txt 2>/dev/null; then
  LIVE=$(grep -m1 '^- beta_live:' /tmp/beta81-current-live.txt | sed 's/^- beta_live:[[:space:]]*//')
fi

FORBIDDEN='candidate:PASS_NO_RERUN; visual:PASS_NO_RERUN; service-live:PASS_NO_RERUN'
[[ "${PUBLISH_RESULT:-}" == success ]] && FORBIDDEN="$FORBIDDEN; publish:PASS_NO_RERUN"
[[ "${PDA_RESULT:-}" == success ]] && FORBIDDEN="$FORBIDDEN; pda-verify:PASS_NO_RERUN"

{
  echo 'PICK PACK 1291 — AUTOMATED HANDOFF'
  echo 'project_id=PICK_PACK_1291'
  echo 'owner=Nguyễn Văn Tâm'
  echo "repo=$GITHUB_REPOSITORY"
  echo "run=$GITHUB_RUN_ID"
  echo "branch=$GITHUB_REF_NAME"
  echo "workflow_commit=$GITHUB_SHA"
  echo "source_sha=$SOURCE_SHA"
  echo 'candidate_run=33073351925'
  echo 'candidate_artifact_id=9646920908'
  echo 'visual_artifact_id=9647045177'
  echo 'service_artifact_id=9646805806'
  echo "apk_sha256=$APK_SHA"
  echo "apk_size=$APK_SIZE"
  echo "signer_sha256=$SIGNER"
  echo "live=$LIVE"
  echo "gate_publish=${PUBLISH_RESULT:-UNKNOWN}"
  echo "gate_pda_verify=${PDA_RESULT:-UNKNOWN}"
  echo "gate_finalize=${FINALIZE_RESULT:-UNKNOWN}"
  echo "jobs=$(jq -c '[.jobs[]|{id,name,status,conclusion}]' <<<"$JOBS")"
  echo "run_artifacts=$(jq -c '[.artifacts[]|{id,name,size_in_bytes,digest}]' <<<"$ARTS")"
  echo "first_root_error=$FIRST_ERROR"
  echo "forbidden_rerun_gates=$FORBIDDEN"
  echo "NEXT_ACTION=$NEXT_ACTION"
} > "$OUT"

test "$(grep -c '^NEXT_ACTION=' "$OUT")" = 1
cat "$OUT"
