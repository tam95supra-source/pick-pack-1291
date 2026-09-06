#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
workflow = (ROOT / ".github/workflows/beta-current-sync.yml").read_text()

def must(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit("BETA_CURRENT_SYNC_CONTRACT_FAIL:" + msg)

must('workflows: ["Beta release"]' in workflow, "WORKFLOW_RUN_SOURCE_MISSING")
must("types: [completed]" in workflow, "WORKFLOW_RUN_COMPLETION_MISSING")
must("push:" not in workflow, "STALE_PASS_LIVE_PUSH_TRIGGER_FORBIDDEN")
must("github.event.workflow_run.conclusion == 'success'" in workflow, "SUCCESS_ONLY_FENCE_MISSING")
must("workflow_run.head_branch" in workflow and "startsWith(github.event.workflow_run.head_branch, 'release/')" in workflow, "RELEASE_BRANCH_FENCE_MISSING")
must("github.ref_name" not in workflow, "PUSH_BRANCH_FALLBACK_FORBIDDEN")
must("group: beta-current-sync" in workflow and "cancel-in-progress: false" in workflow, "GLOBAL_CONCURRENCY_MISSING")
must("jq -r '.stage // empty'" in workflow and '"pass_live"' in workflow, "PASS_LIVE_FENCE_MISSING")
must("technical_pass_status" in workflow and '"PASS"' in workflow, "TECHNICAL_PASS_FENCE_MISSING")
must("TARGET_NO < CURRENT_NO" in workflow and "TARGET_NO == CURRENT_NO" in workflow, "MONOTONIC_VERSION_FENCE_MISSING")
must("git merge-base --is-ancestor" in workflow, "FAST_FORWARD_ANCESTRY_GUARD_MISSING")
must("refs/heads/beta/current" in workflow, "CURRENT_REF_WRITE_MISSING")
must("--force" not in workflow and "-f origin" not in workflow, "FORCE_PUSH_FORBIDDEN")
must("CURRENT_SYNC_RACE_NEWER_CURRENT" in workflow, "RACE_NEWER_VERSION_GUARD_MISSING")
must("git show origin/beta/current:CURRENT_STATE.md" in workflow, "CURRENT_STATE_READBACK_MISSING")
must("git show origin/beta/current:ops/beta-ota-current.json" in workflow, "OTA_STATE_READBACK_MISSING")
must('"GITHUB_RELEASE"' in workflow, "GITHUB_RELEASE_AUTHORITY_READBACK_MISSING")

# Regression: a stale PASS_LIVE file carried on a newly pushed release branch must not be able
# to invoke this writer at all. Only the successful Beta release workflow_run is authoritative.
must("event_name == 'push'" not in workflow, "PUSH_EVENT_WRITER_PATH_FORBIDDEN")
must("'release/**'" not in workflow, "RELEASE_WILDCARD_PUSH_TRIGGER_FORBIDDEN")

print("beta_current_sync_contract=PASS release_complete_only=PASS stale_pass_live_push=BLOCKED monotonic=PASS fast_forward_only=PASS readback=PASS")
