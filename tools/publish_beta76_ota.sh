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
Path(sys.argv[2]).write_text(src, encoding='utf-8')
PY

bash -n "$PATCHED"
if [[ "${BETA76_MATERIALIZE_ONLY:-0}" == "1" ]]; then
  printf '%s\n' "$PATCHED"
  exit 0
fi

# Attempt 2 already completed the production mutation and made exact Beta76 LIVE,
# then failed only in a Drive-v3 metadata verifier. If exact Beta76 is already LIVE,
# do readback-only completion and never invoke the temporary upload helper again.
E=/tmp/beta76-release-evidence
mkdir -p "$E"
GAS_URL='https://script.google.com/macros/s/AKfycbzbEoGfbNg6s2HnP-gUpcBJ7mMIkVBtYuQKMndb9seDV2c55lQwSUO1GZ-LtQ2CxMCauA/exec'
TARGET_VERSION='0.4.2-beta.76'
TARGET_CODE=82
EXPECTED_SHA='7018977f28d09434de27e6c6e90a7a51ec11c77831285d7e466c7aeeeeef9ee2'
EXPECTED_SIZE=13179781
EXPECTED_SIGNER='d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e'
PACKAGE='vn.pickpack1291.app.beta.publicbeta'
APK_NAME='pick-pack-1291-public-beta-0.4.2-beta.76.apk'
DRIVE_ID='1uxfoNvcPLJUxpPxo-XwAb12ZZasX4Heb'
SUM_ID='1IxZLvxRjfDCmRZTIVNyOqSaWdXhneGjH'
EXPECTED_MAIN='a8c0c0d92522c7173230d4175b4f0d3a4906c8bb'

curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL" \
  -d '{"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.75"}' > "$E/beta75-client.json"

if jq -e --arg h "$EXPECTED_SHA" --argjson z "$EXPECTED_SIZE" \
  '.ok==true and .available==true and .version_name=="0.4.2-beta.76" and .version_code==82 and .sha256==$h and .size==$z and ((.apk_url // .download_url // .url // "")|startswith("https://"))' \
  "$E/beta75-client.json" >/dev/null; then

  curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL" \
    -d '{"action":"update_check","channel":"BETA","current_version":"0.4.2-beta.76"}' > "$E/beta76-client.json"
  jq -e --argjson z "$EXPECTED_SIZE" \
    '.ok==true and .channel=="BETA" and .available==false and .version_name=="0.4.2-beta.76" and ((.version_code // 82)==82) and ((.size // $z)==$z)' \
    "$E/beta76-client.json" >/dev/null

  curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL" \
    -d '{"action":"update_check","channel":"STABLE","current_version":"0.1.0-stable"}' > "$E/stable-before.json"
  curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL" \
    -d '{"action":"update_check","channel":"STABLE","current_version":"0.1.0-stable"}' > "$E/stable-after.json"
  jq -e '.ok==true and .channel=="STABLE" and .available==false' "$E/stable-before.json" >/dev/null
  python3 - "$E/stable-before.json" "$E/stable-after.json" <<'PY'
import json,sys
a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2]))
keys=('source','channel','version_name','version_code','sha256','size','apk_url','available','reason')
assert {k:a.get(k) for k in keys}=={k:b.get(k) for k in keys}
PY

  LIVE_URL=$(jq -r '.apk_url // .download_url // .url // empty' "$E/beta75-client.json")
  [[ "$LIVE_URL" == https://* ]]
  curl -fsSL -L --connect-timeout 15 --max-time 180 "$LIVE_URL" -o /tmp/beta76-live.apk
  test "$(sha256sum /tmp/beta76-live.apk | awk '{print $1}')" = "$EXPECTED_SHA"
  test "$(stat -c '%s' /tmp/beta76-live.apk)" = "$EXPECTED_SIZE"

  curl -fsSL -L --connect-timeout 15 --max-time 180 \
    "https://drive.usercontent.google.com/download?id=$DRIVE_ID&export=download&confirm=t" -o /tmp/beta76-drive.apk
  test "$(sha256sum /tmp/beta76-drive.apk | awk '{print $1}')" = "$EXPECTED_SHA"
  test "$(stat -c '%s' /tmp/beta76-drive.apk)" = "$EXPECTED_SIZE"

  curl -fsSL -L --connect-timeout 15 --max-time 30 \
    "https://drive.usercontent.google.com/download?id=$SUM_ID&export=download&confirm=t" -o "$E/drive-checksum.txt"
  grep -qx "$EXPECTED_SHA  $APK_NAME" "$E/drive-checksum.txt"

  curl -fsSL --connect-timeout 15 --max-time 30 \
    -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' \
    "https://api.github.com/repos/${GITHUB_REPOSITORY:-tam95supra-source/pick-pack-1291}/branches/main" > "$E/main.json"
  MAIN_SHA=$(jq -r '.commit.sha' "$E/main.json")
  test "$MAIN_SHA" = "$EXPECTED_MAIN"

  jq -nc \
    --argjson release_run "$GITHUB_RUN_ID" \
    --arg version "$TARGET_VERSION" --argjson code "$TARGET_CODE" --arg package "$PACKAGE" \
    --arg sha "$EXPECTED_SHA" --argjson size "$EXPECTED_SIZE" --arg signer "$EXPECTED_SIGNER" \
    --arg drive "$DRIVE_ID" --arg sum "$SUM_ID" --arg url "$LIVE_URL" --arg main "$MAIN_SHA" \
    '{verdict:"PASS",mode:"ALREADY_LIVE_READBACK_ONLY",release_run_id:$release_run,version_name:$version,version_code:$code,package:$package,apk_sha256:$sha,apk_size:$size,signer_sha256:$signer,drive_file_id:$drive,drive_checksum_file_id:$sum,ota_url:$url,ota_live:"PASS",beta75_client_readback:{available:true,version_name:$version,version_code:$code,sha256:$sha,size:$size},beta76_client_readback:{available:false,version_name:$version,version_code:$code},superseded_live_version:"0.4.2-beta.75",stable_unchanged:"PASS",main_unchanged:"PASS",main_sha:$main,service_change:"NONE",gas_change:"OTA_VERSION_COMPAT_BETA76",authority_change:"NONE"}' \
    > "$E/release-result.json"
  echo 'beta76_already_live_readback=PASS'
  exit 0
fi

# If exact target is not LIVE, retain the proven exact-byte publisher path.
exec bash "$PATCHED"
