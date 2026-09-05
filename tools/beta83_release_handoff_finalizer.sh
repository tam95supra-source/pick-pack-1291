#!/usr/bin/env bash
set -uo pipefail
R=ops/beta-release-request.json
SCOPE=ops/OWNER_SCOPE_CURRENT.json
OUT="/tmp/PICK_PACK_1291_HANDOFF_${GITHUB_RUN_ID}.txt"
VERSION=$(jq -r '.version_name' "$R")

python3 tools/owner_scope_guard.py --bootstrap >/tmp/owner-scope-bootstrap-handoff.json
OWNER_SCOPE=$(jq -r '.scope_id' "$SCOPE")
OWNER_SCOPE_REVISION=$(jq -r '.revision' "$SCOPE")
OWNER_SCOPE_SEMANTICS_SHA=$(jq -r '.semantics_sha256' "$SCOPE")
OWNER_SCOPE_SHA=$(jq -r '.scope_sha256' "$SCOPE")
OWNER_LEDGER=$(jq -r '.owner_command_ledger' "$SCOPE")
OWNER_LEDGER_HEAD=$(jq -r '.ledger_head_event_sha256' "$SCOPE")
OWNER_COUNT=$(jq -r '.requirements|length' "$SCOPE")

test "$(jq -r '.owner_scope // ""' "$R")" = "$OWNER_SCOPE"
test "$(jq -r '.owner_checklist_revision // 0' "$R")" = "$OWNER_SCOPE_REVISION"

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
    test "$OWNER_COUNT" -gt 0
    NEXT="WAIT_FOR_OWNER_ACCEPTANCE_NUMBERED_CHECKLIST_1_TO_${OWNER_COUNT}"
  fi
elif [[ "$ROLL" == success ]]; then NEXT=FIX_POST_PUBLISH_FAILURE_WITH_PREVIOUS_BETA_RESTORED
elif [[ "$PUB" != success ]]; then NEXT=FIX_PUBLISH_FAILURE_KEEP_EXACT_LOCKED_CANDIDATE
else NEXT=FIX_POST_PUBLISH_OTA_VERIFY_KEEP_EXACT_LOCKED_CANDIDATE
fi
{
echo 'Tiếp tục dự án APK PICK PACK 1291 của OWNER Nguyễn Văn Tâm. Đọc HANDOVER_CURRENT, bootstrap canonical OWNER scope/hash/ledger, kế thừa gate PASS nếu input/source/exact bytes không đổi và thực thi NEXT_ACTION đến DoD PASS hoặc blocker OWNER thật.'
echo "PICK PACK 1291 — AUTOMATED $VERSION RELEASE HANDOFF"
echo 'status=READY'
echo "run=$GITHUB_RUN_ID"
echo "branch=$GITHUB_REF_NAME"
echo "stage=$(jq -r '.stage' "$R")"
echo 'owner_scope_file=ops/OWNER_SCOPE_CURRENT.json'
echo "owner_scope_id=$OWNER_SCOPE"
echo "owner_scope_revision=$OWNER_SCOPE_REVISION"
echo "owner_scope_semantics_sha256=$OWNER_SCOPE_SEMANTICS_SHA"
echo "owner_scope_sha256=$OWNER_SCOPE_SHA"
echo "owner_command_ledger=$OWNER_LEDGER"
echo "owner_command_ledger_head=$OWNER_LEDGER_HEAD"
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
