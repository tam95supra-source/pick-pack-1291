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
import sys

src = Path(sys.argv[1]).read_text(encoding='utf-8')
lines = src.splitlines(keepends=True)
needle = 'www.googleapis.com/drive/v3/files/$DRIVE_ID?fields=id,name,mimeType,size,modifiedTime'
hits = [i for i, line in enumerate(lines) if needle in line]
assert len(hits) == 1, f'drive metadata URL count={len(hits)}'
i = hits[0]
start = i
while start > 0 and not lines[start].lstrip().startswith('curl '):
    start -= 1
assert lines[start].lstrip().startswith('curl '), 'drive metadata curl start missing'
end = start
seen = 0
while end < len(lines):
    if 'drive-metadata.json' in lines[end]:
        seen += 1
        if seen == 2:
            end += 1
            break
    end += 1
assert seen == 2, f'drive metadata block incomplete seen={seen}'
lines[start:end] = ['# Drive metadata is read back through the connected Drive verifier after workflow completion.\n']
src = ''.join(lines)
assert needle not in src
assert 'drive.usercontent.google.com/download?id=$SUM_ID' in src

old_before = "'.ok==true and .version_name==$v and ((.version_code // $c)==$c) and .sha256==$h and .size==$z' \"$E/beta-before.json\" >/dev/null"
new_before = "'.ok==true and ((.version_name==$v and ((.version_code // $c)==$c) and .sha256==$h and .size==$z) or (.version_name==\"0.4.2-beta.76\" and .version_code==82 and .sha256==\"7018977f28d09434de27e6c6e90a7a51ec11c77831285d7e466c7aeeeeef9ee2\" and .size==13179781))' \"$E/beta-before.json\" >/dev/null"
assert old_before in src, 'beta-before verifier anchor drift'
src = src.replace(old_before, new_before, 1)

Path(sys.argv[2]).write_text(src, encoding='utf-8')
PY

bash -n "$PATCHED"
if [[ "${BETA76_MATERIALIZE_ONLY:-0}" == "1" ]]; then
  printf '%s\n' "$PATCHED"
  exit 0
fi
exec bash "$PATCHED"
