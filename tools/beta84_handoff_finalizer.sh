#!/usr/bin/env bash
set -uo pipefail
R=ops/beta-release-request.json
OUT="/tmp/PICK_PACK_1291_HANDOFF_${GITHUB_RUN_ID}.txt"
JOBS=$(curl -fsS -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID/jobs?per_page=100" 2>/dev/null || echo '{"jobs":[]}')
CAND=$(jq -r '.jobs[]?|select(.name=="candidate")|.conclusion' <<<"$JOBS"|head -n1)
VERIFY=$(jq -r '.jobs[]?|select(.name=="visual-pda-verify")|.conclusion' <<<"$JOBS"|head -n1)
if [[ "$CAND" != success ]]; then NEXT=FIX_BETA84_CANDIDATE_FAILURE
elif [[ "$VERIFY" != success ]]; then NEXT=FIX_BETA84_VERIFY_FAILURE_KEEP_LOCKED_CANDIDATE_IF_BYTES_VALID
else NEXT=HUMAN_INSPECT_BETA84_VISUALS_THEN_PUBLISH_EXACT_LOCKED_CANDIDATE_IF_PASS
fi
{
echo 'Tiếp tục dự án APK PICK PACK 1291 của OWNER Nguyễn Văn Tâm. Đọc checkpoint dưới đây, kế thừa gate PASS nếu input/source/exact bytes không đổi, không làm lại và thực thi NEXT_ACTION đến DoD PASS hoặc blocker OWNER thật.'
echo 'PICK PACK 1291 — AUTOMATED BETA84 PRE-OTA HANDOFF'
echo 'status=READY'
echo "run=$GITHUB_RUN_ID"
echo "branch=$GITHUB_REF_NAME"
echo "source_sha=$(jq -r '.source_sha' "$R")"
echo "version=$(jq -r '.version_name' "$R")"
echo "version_code=$(jq -r '.version_code' "$R")"
echo "fast_check=$(jq -r '.fast_check' "$R")"
echo "fast_check_run=$(jq -r '.fast_check_run_id' "$R")"
echo "service_gate=$(jq -r '.service_gate_inherited' "$R")"
echo "candidate=$CAND"
echo "verify=$VERIFY"
echo "stable_publish=FORBIDDEN"
echo "authority_change=NONE"
echo "NEXT_ACTION=$NEXT"
} > "$OUT"
cat "$OUT"
