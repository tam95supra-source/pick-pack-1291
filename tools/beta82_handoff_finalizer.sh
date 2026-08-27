#!/usr/bin/env bash
set -uo pipefail
REQ=ops/beta-release-request.json
STAGE=$(jq -r '.stage // "UNKNOWN"' "$REQ" 2>/dev/null || echo UNKNOWN)
OUT="/tmp/PICK_PACK_1291_HANDOFF_${GITHUB_RUN_ID}.txt"
JOBS=$(curl -fsS -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID/jobs?per_page=100" 2>/dev/null || echo '{"jobs":[]}')
ARTS=$(curl -fsS -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID/artifacts?per_page=100" 2>/dev/null || echo '{"artifacts":[]}')
CAND=$(jq -r '.jobs[]|select(.name=="candidate")|.conclusion' <<<"$JOBS"|head -n1);VERIFY=$(jq -r '.jobs[]|select(.name=="visual-pda-verify")|.conclusion' <<<"$JOBS"|head -n1)
if [[ "$STAGE" == BUILD_VERIFY && "$CAND" == success && "$VERIFY" == success ]]; then NEXT_ACTION=HUMAN_INSPECT_BETA82_VISUAL_THEN_LOCK_EXACT_CANDIDATE; else NEXT_ACTION=FIX_FIRST_FAILED_BETA82_BUILD_VERIFY_DOMAIN_AND_RERUN_WITHOUT_RANDOM_RETRY; fi
{
 echo 'PICK PACK 1291 — AUTOMATED HANDOFF'
 echo 'owner=Nguyễn Văn Tâm'
 echo "repo=$GITHUB_REPOSITORY"
 echo "run=$GITHUB_RUN_ID"
 echo "branch=$GITHUB_REF_NAME"
 echo "workflow_commit=$GITHUB_SHA"
 echo "stage=$STAGE"
 echo "source_sha=$(jq -r '.source_sha' "$REQ" 2>/dev/null)"
 echo "version=$(jq -r '.version_name' "$REQ" 2>/dev/null)"
 echo "jobs=$(jq -c '[.jobs[]|{id,name,status,conclusion}]' <<<"$JOBS")"
 echo "artifacts=$(jq -c '[.artifacts[]|{id,name,size_in_bytes,digest}]' <<<"$ARTS")"
 echo "NEXT_ACTION=$NEXT_ACTION"
} > "$OUT"
test "$(grep -c '^NEXT_ACTION=' "$OUT")" = 1
cat "$OUT"
