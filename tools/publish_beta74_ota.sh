#!/usr/bin/env bash
set -Eeuo pipefail

# Beta74 publish harness recovery: keep the original locked publisher semantics/bytes,
# only restore the proven Beta73 propagation windows for GAS deployment visibility.
BASE_SHA=85b58348209e97c93957d45275a2fc031c764d48
BASE_URL="https://raw.githubusercontent.com/${GITHUB_REPOSITORY}/${BASE_SHA}/tools/publish_beta74_ota.sh"
TMP=/tmp/publish_beta74_ota_materialized.sh
curl -fsSL --connect-timeout 15 --max-time 30 "$BASE_URL" -o "$TMP.base"
python3 - "$TMP.base" "$TMP" <<'PY'
from pathlib import Path
import sys
src=Path(sys.argv[1]).read_text(encoding='utf-8')
needle='for i in 1 2 3; do'
assert src.count(needle)==2, src.count(needle)
src=src.replace(needle,'for i in 1 2 3 4 5 6; do',1)
src=src.replace(needle,'for i in 1 2 3 4 5 6 7 8; do',1)
Path(sys.argv[2]).write_text(src,encoding='utf-8')
PY
bash -n "$TMP"
exec bash "$TMP"
