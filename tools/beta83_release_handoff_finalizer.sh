#!/usr/bin/env bash
set -uo pipefail
R=ops/beta-release-request.json
OUT="/tmp/PICK_PACK_1291_HANDOFF_${GITHUB_RUN_ID}.txt"
VERSION=$(jq -r '.version_name' "$R")
JOBS=$(curl -fsS -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID/jobs?per_page=100" 2>/dev/null || echo '{"jobs":[]}')
PUB=$(jq -r '.jobs[]?|select(.name=="publish")|.conclusion' <<<"$JOBS"|head -n1)
PDA=$(jq -r '.jobs[]?|select(.name=="pda-verify")|.conclusion' <<<"$JOBS"|head -n1)
FIN=$(jq -r '.jobs[]?|select(.name=="finalize")|.conclusion' <<<"$JOBS"|head -n1)
ROLL=$(jq -r '.jobs[]?|select(.name=="rollback-beta")|.conclusion' <<<"$JOBS"|head -n1)
if [[ "$FIN" == success ]]; then
  ACCEPT=$(jq -r '.owner_acceptance // "PENDING"' "$R")
  if [[ "$ACCEPT" == "COMPLETE" ]]; then
    NEXT=WAIT_FOR_OWNER_NEW_SCOPE
  else
    COUNT=$(jq -r 'if (.owner_checklist|type)=="array" then (.owner_checklist|length) else 0 end' "$R")
    test "$COUNT" -gt 0
    NEXT="WAIT_FOR_OWNER_ACCEPTANCE_NUMBERED_CHECKLIST_1_TO_${COUNT}"
  fi
elif [[ "$ROLL" == success ]]; then NEXT=FIX_POST_PUBLISH_FAILURE_WITH_PREVIOUS_BETA_RESTORED
elif [[ "$PUB" != success ]]; then NEXT=FIX_PUBLISH_FAILURE_KEEP_EXACT_LOCKED_CANDIDATE
else NEXT=FIX_POST_PUBLISH_OTA_VERIFY_KEEP_EXACT_LOCKED_CANDIDATE
fi
{
echo 'Tiếp tục dự án APK PICK PACK 1291 của OWNER Nguyễn Văn Tâm. Đọc checkpoint dưới đây, kế thừa gate PASS nếu input/source/exact bytes không đổi, không làm lại và thực thi NEXT_ACTION đến DoD PASS hoặc blocker OWNER thật.'
echo "PICK PACK 1291 — AUTOMATED $VERSION RELEASE HANDOFF"
echo 'status=READY'
echo "run=$GITHUB_RUN_ID"
echo "branch=$GITHUB_REF_NAME"
echo "stage=$(jq -r '.stage' "$R")"
echo "source_sha=$(jq -r '.source_sha' "$R")"
echo "candidate_run=$(jq -r '.candidate_run_id' "$R")"
echo "candidate_artifact=$(jq -r '.candidate_artifact_id' "$R")"
echo "apk_sha256=$(jq -r '.apk_sha256' "$R")"
echo "apk_transport=$(jq -r '.apk_transport // "GITHUB_RELEASE_ONLY"' "$R")"
echo "google_drive_apk=$(jq -r '.google_drive_apk // "FORBIDDEN"' "$R")"
echo "publish=$PUB"
echo "pda_verify=$PDA"
echo "rollback=$ROLL"
echo "finalize=$FIN"
echo "NEXT_ACTION=$NEXT"
} > "$OUT"
cat "$OUT"
