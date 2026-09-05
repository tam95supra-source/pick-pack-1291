#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
workflow = (ROOT / ".github/workflows/beta-current-sync.yml").read_text()

def must(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit("BETA_CURRENT_SYNC_CONTRACT_FAIL:" + msg)

must('workflows: ["Beta release"]' in workflow, "WORKFLOW_RUN_SOURCE_MISSING")
must("push:" in workflow and "'release/**'" in workflow, "POST_RELEASE_PUSH_SOURCE_MISSING")
must("github.event_name == 'workflow_run'" in workflow and "github.event_name == 'push'" in workflow, "EVENT_SOURCE_SWITCH_MISSING")
must("github.ref_name" in workflow and "workflow_run.head_branch" in workflow, "RELEASE_BRANCH_RESOLUTION_MISSING")
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

print("beta_current_sync_contract=PASS release_complete=PASS post_release_push=PASS monotonic=PASS fast_forward_only=PASS readback=PASS")
