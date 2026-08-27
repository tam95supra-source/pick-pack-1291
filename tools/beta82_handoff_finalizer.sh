#!/usr/bin/env bash
set -uo pipefail
R=ops/beta-release-request.json;OUT="/tmp/PICK_PACK_1291_HANDOFF_${GITHUB_RUN_ID}.txt"
JOBS=$(curl -fsS -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID/jobs?per_page=100" 2>/dev/null||echo '{"jobs":[]}')
STAGE=$(jq -r '.stage//"UNKNOWN"' "$R" 2>/dev/null||echo UNKNOWN)
PUB=$(jq -r '.jobs[]?|select(.name=="publish")|.conclusion' <<<"$JOBS"|head -n1);PDA=$(jq -r '.jobs[]?|select(.name=="pda-verify")|.conclusion' <<<"$JOBS"|head -n1);FIN=$(jq -r '.jobs[]?|select(.name=="finalize")|.conclusion' <<<"$JOBS"|head -n1);ROLL=$(jq -r '.jobs[]?|select(.name=="rollback-beta81")|.conclusion' <<<"$JOBS"|head -n1)
if [[ "$FIN" == success ]]; then NEXT=WAIT_FOR_OWNER_NEW_SCOPE
elif [[ "$ROLL" == success ]]; then NEXT=FIX_POST_PUBLISH_PDA_FAILURE_ON_EXACT_BETA82_WITH_BETA81_RESTORED
elif [[ "$PUB" != success ]]; then NEXT=FIX_BETA82_PUBLISH_FAILURE_WITHOUT_REBUILDING_CANDIDATE
else NEXT=FIX_BETA82_POST_PUBLISH_OTA_VERIFY_WITHOUT_REBUILDING_CANDIDATE
fi
{
echo 'PICK PACK 1291 — AUTOMATED HANDOFF';echo 'owner=Nguyễn Văn Tâm';echo "run=$GITHUB_RUN_ID";echo "branch=$GITHUB_REF_NAME";echo "stage=$STAGE"
echo "source_sha=$(jq -r '.source_sha' "$R" 2>/dev/null)";echo "candidate_run=$(jq -r '.candidate_run_id' "$R" 2>/dev/null)";echo "candidate_artifact=$(jq -r '.candidate_artifact_id' "$R" 2>/dev/null)"
echo "apk_sha256=$(jq -r '.apk_sha256' "$R" 2>/dev/null)";echo "gate_publish=$PUB";echo "gate_pda=$PDA";echo "gate_finalize=$FIN";echo "gate_rollback=$ROLL";echo "NEXT_ACTION=$NEXT"
} > "$OUT";cat "$OUT"
