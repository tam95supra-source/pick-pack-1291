#!/usr/bin/env bash
set -Eeuo pipefail
target=${1:?target source sha required}
git cat-file -e "$target^{commit}"
git rm -r -f --ignore-unmatch service >/dev/null 2>&1 || true
git checkout "$target" -- service
git clean -fd -- service >/dev/null
git diff --quiet "$target" -- service || { echo EXACT_SERVICE_RESTORE_FAILED >&2; exit 91; }
