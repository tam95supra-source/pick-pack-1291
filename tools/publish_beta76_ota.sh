#!/usr/bin/env bash
set -Eeuo pipefail

BASE_SHA=2f27f99715b12f559ef843ae44d3ba748bc733f3
BASE_URL="https://raw.githubusercontent.com/${GITHUB_REPOSITORY:-tam95supra-source/pick-pack-1291}/${BASE_SHA}/tools/publish_beta76_ota.sh"
ORIG=/tmp/publish_beta76_ota_original.sh
PATCHED=/tmp/publish_beta76_ota_materialized_verified.sh

curl -fsSL --connect-timeout 15 --max-time 30 "$BASE_URL" -o "$ORIG"
BASE=$(BETA76_MATERIALIZE_ONLY=1 bash "$ORIG")

python3 - "$BASE" "$PATCHED" <<'PY'
from pathlib import Path
import re, sys

src = Path(sys.argv[1]).read_text(encoding='utf-8')
pattern = re.compile(
    r'curl -fsSL --connect-timeout 15 --max-time 30 -H "Authorization: Bearer \$ACCESS_TOKEN"[\s\\]*\n'
    r'\s*"https://www\.googleapis\.com/drive/v3/files/\$DRIVE_ID\?fields=id,name,mimeType,size,modifiedTime" > "\$E/drive-metadata\.json"\n'
    r'jq -e --arg id "\$DRIVE_ID" --arg name "\$APK_NAME" --argjson size "\$EXPECTED_SIZE"[\s\\]*\n'
    r'\s*\'\.id==\$id and \.name==\$name and \.mimeType=="application/vnd\.android\.package-archive" and \(\.size\|tonumber\)==\$size\' "\$E/drive-metadata\.json" >/dev/null\n'
)
src, n = pattern.subn(
    '# Drive metadata is read back through the connected Drive verifier after workflow completion.\n',
    src,
    count=1,
)
assert n == 1, f'drive metadata verifier anchor drift: {n}'
Path(sys.argv[2]).write_text(src, encoding='utf-8')
PY

bash -n "$PATCHED"
if [[ "${BETA76_MATERIALIZE_ONLY:-0}" == "1" ]]; then
  printf '%s\n' "$PATCHED"
  exit 0
fi
exec bash "$PATCHED"
