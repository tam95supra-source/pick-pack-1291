#!/usr/bin/env python3
from pathlib import Path

p = Path('.github/workflows/beta-release.yml')
s = p.read_text()
old = '''          git fetch origin "$RUN_REF"\n          git checkout -B "$RUN_REF" "origin/$RUN_REF"\n          CURRENT_NONCE=$(jq -r '.execution_nonce' ops/beta-release-request.json)\n'''
new = '''          git fetch origin "$RUN_REF"\n          FETCHED_SHA=$(git rev-parse "origin/$RUN_REF")\n          git checkout -B "$RUN_REF" "origin/$RUN_REF"\n          CURRENT_NONCE=$(jq -r '.execution_nonce' ops/beta-release-request.json)\n'''
if old not in s:
    raise SystemExit('MARKER_FETCH_BLOCK_NOT_FOUND_OR_ALREADY_CHANGED')
s = s.replace(old, new, 1)
old2 = '''          git commit -m "ci: observe Beta run $RUN_ID"\n          git push origin HEAD:"$RUN_REF"\n'''
new2 = '''          git commit -m "ci: observe Beta run $RUN_ID"\n          if ! git push --force-with-lease="refs/heads/$RUN_REF:$FETCHED_SHA" origin HEAD:"$RUN_REF"; then\n            REMOTE_SHA=$(git ls-remote origin "refs/heads/$RUN_REF" | awk '{print $1}')\n            if [[ -n "$REMOTE_SHA" && "$REMOTE_SHA" != "$FETCHED_SHA" ]]; then\n              echo "RUN_MARKER_SKIPPED_BRANCH_ADVANCED:$FETCHED_SHA->$REMOTE_SHA"\n            else\n              echo "RUN_MARKER_PUSH_FAILED_WITHOUT_REF_ADVANCE" >&2\n              exit 1\n            fi\n          fi\n'''
if old2 not in s:
    raise SystemExit('MARKER_PUSH_BLOCK_NOT_FOUND_OR_ALREADY_CHANGED')
s = s.replace(old2, new2, 1)
p.write_text(s)

assert 'FETCHED_SHA=$(git rev-parse "origin/$RUN_REF")' in s
assert 'RUN_MARKER_SKIPPED_BRANCH_ADVANCED' in s
assert '--force-with-lease="refs/heads/$RUN_REF:$FETCHED_SHA"' in s
print('beta_release_marker_race_patch=PASS')
