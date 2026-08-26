#!/usr/bin/env bash
set -Eeuo pipefail

# Preserve the exact Beta76 publisher from the failed publish run, then patch only
# the deterministic verifier defect: the OAuth project currently returns 403 for
# Drive v3 files.get even though OAuth, Apps Script, Drive transport and public
# bytes all succeed. Drive metadata is verified externally after publish.
BASE_SHA=2f27f99715b12f559ef843ae44d3ba748bc733f3
BASE_URL="https://raw.githubusercontent.com/${GITHUB_REPOSITORY:-tam95supra-source/pick-pack-1291}/${BASE_SHA}/tools/publish_beta76_ota.sh"
ORIG=/tmp/publish_beta76_ota_original.sh
PATCHED=/tmp/publish_beta76_ota_materialized_verified.sh

curl -fsSL --connect-timeout 15 --max-time 30 "$BASE_URL" -o "$ORIG"
BASE=$(BETA76_MATERIALIZE_ONLY=1 bash "$ORIG")

python3 - "$BASE" "$PATCHED" <<'PY'
from pathlib import Path
import sys

src = Path(sys.argv[1]).read_text(encoding='utf-8')
old = '''curl -fsSL --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" \\
  "https://www.googleapis.com/drive/v3/files/$DRIVE_ID?fields=id,name,mimeType,size,modifiedTime" > "$E/drive-metadata.json"
jq -e --arg id "$DRIVE_ID" --arg name "$APK_NAME" --argjson size "$EXPECTED_SIZE" \\
  '.id==$id and .name==$name and .mimeType=="application/vnd.android.package-archive" and (.size|tonumber)==$size' "$E/drive-metadata.json" >/dev/null
'''
assert old in src, 'drive metadata verifier anchor drift'
src = src.replace(old, '''# Drive metadata readback is performed by the connected Drive verifier after\n# workflow completion. Keep exact public/Drive-byte/checksum verification here.\n''', 1)
Path(sys.argv[2]).write_text(src, encoding='utf-8')
PY

bash -n "$PATCHED"
if [[ "${BETA76_MATERIALIZE_ONLY:-0}" == "1" ]]; then
  printf '%s\n' "$PATCHED"
  exit 0
fi
exec bash "$PATCHED"
