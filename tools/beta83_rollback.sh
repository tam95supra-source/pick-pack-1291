#!/usr/bin/env bash
set -Eeuo pipefail
R=ops/beta-release-request.json;E=/tmp/beta-rollback;rm -rf "$E";mkdir -p "$E";PUB=/tmp/beta-publish/receipt.json;test -f "$PUB"
for n in GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN GAS_SCRIPT_ID GAS_DEPLOYMENT_ID; do test -n "${!n:-}"; done
FILE=$(jq -r '.drive_file_id' "$PUB");test -n "$FILE" -a "$FILE" != null
PREV=$(jq -r '.base_version' "$R");BASE_CODE=$(jq -r '.base_version_code' "$R");BASE_SHA=$(jq -r '.base_apk_sha256' "$R");BASE_SIZE=$(jq -r '.base_apk_size' "$R")
TOKEN_JSON=$(curl -fsS https://oauth2.googleapis.com/token -H 'Content-Type: application/x-www-form-urlencoded' --data-urlencode "client_id=$GOOGLE_OAUTH_CLIENT_ID" --data-urlencode "client_secret=$GOOGLE_OAUTH_CLIENT_SECRET" --data-urlencode "refresh_token=$GOOGLE_OAUTH_REFRESH_TOKEN" --data-urlencode grant_type=refresh_token)
ACCESS_TOKEN=$(jq -r '.access_token//empty' <<<"$TOKEN_JSON");test -n "$ACCESS_TOKEN";export ACCESS_TOKEN;echo "::add-mask::$ACCESS_TOKEN";echo "::add-mask::$FILE"
FQ="name='BẢN THỬ NGHIỆM' and mimeType='application/vnd.google-apps.folder' and trashed=false"
curl -fsS --get -H "Authorization: Bearer $ACCESS_TOKEN" --data-urlencode "q=$FQ" --data-urlencode 'fields=files(id,name)' https://www.googleapis.com/drive/v3/files > "$E/folders.json"
test "$(jq '.files|length' "$E/folders.json")" = 1
FOLDER=$(jq -r '.files[0].id' "$E/folders.json");echo "::add-mask::$FOLDER"
BASE_APK_NAME="pick-pack-1291-public-beta-$PREV.apk";BQ="'$FOLDER' in parents and name='$BASE_APK_NAME' and trashed=false"
curl -fsS --get -H "Authorization: Bearer $ACCESS_TOKEN" --data-urlencode "q=$BQ" --data-urlencode 'fields=files(id,name,size)' https://www.googleapis.com/drive/v3/files > "$E/base-files.json"
test "$(jq '.files|length' "$E/base-files.json")" = 1
BASE_FILE=$(jq -r '.files[0].id' "$E/base-files.json");test "$(jq -r '.files[0].size' "$E/base-files.json")" = "$BASE_SIZE";echo "::add-mask::$BASE_FILE"
curl -fsS -H "Authorization: Bearer $ACCESS_TOKEN" "https://www.googleapis.com/drive/v3/files/$BASE_FILE?alt=media&acknowledgeAbuse=true" -o "$E/base-auth.apk"
test "$(sha256sum "$E/base-auth.apk"|awk '{print $1}')" = "$BASE_SHA";test "$(stat -c '%s' "$E/base-auth.apk")" = "$BASE_SIZE"
BASE_URL=""
for u in "https://drive.usercontent.google.com/download?id=$BASE_FILE&export=download&confirm=t" "https://drive.google.com/uc?export=download&id=$BASE_FILE"; do
  if curl -fsSL --retry 2 --retry-delay 2 --connect-timeout 15 --max-time 120 "$u" -o "$E/base-public.apk" \
    && [[ "$(sha256sum "$E/base-public.apk"|awk '{print $1}')" == "$BASE_SHA" ]] && [[ "$(stat -c '%s' "$E/base-public.apk")" == "$BASE_SIZE" ]]; then BASE_URL="$u";break;fi
done
test -n "$BASE_URL";echo "::add-mask::$BASE_URL"
printf '%s\n' "Khôi phục hợp đồng OTA exact $PREV" > "$E/base-notes.txt"
python3 tools/gas_ota_static_contract.py --version "$PREV" --version-code "$BASE_CODE" --sha256 "$BASE_SHA" --size "$BASE_SIZE" --apk-url "$BASE_URL" --published-at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --notes-file "$E/base-notes.txt" --receipt "$E/gas-contract.json" --description "Pick Pack 1291 rollback exact baseline OTA contract"

RAW=$(printf '%s' "$GAS_DEPLOYMENT_ID"|tr -d '\r\n\t ');DEP="$RAW";if [[ "$RAW" == *"/s/"* ]]; then DEP="${RAW#*/s/}";DEP="${DEP%%/*}";fi
URL="https://script.google.com/macros/s/$DEP/exec";echo "::add-mask::$URL"
BASE_PROBE=$(jq -r '.base_probe_version // empty' "$R")
if [[ -z "$BASE_PROBE" || "$BASE_PROBE" == null ]]; then
  BASE_PROBE=$(python3 - "$PREV" <<'PY'
import re,sys
m=re.search(r'^(.*beta\.)(\d+)$',sys.argv[1]);assert m and int(m.group(2))>0
print(m.group(1)+str(int(m.group(2))-1))
PY
)
fi
PASS=0
for a in 0 1 2 3; do
  BODY=$(jq -nc --arg current "$BASE_PROBE" '{action:"update_check",channel:"BETA",current_version:$current}')
  curl -fsSL --connect-timeout 15 --max-time 35 -H 'content-type: application/json' "$URL" --data-binary "$BODY" > "$E/readback.json" || true
  if jq -e --arg v "$PREV" --arg h "$BASE_SHA" --argjson z "$BASE_SIZE" '.ok==true and .available==true and .version_name==$v and .sha256==$h and .size==$z' "$E/readback.json" >/dev/null 2>&1; then PASS=1;break;fi
  sleep $((3+a*4))
done
test "$PASS" = 1
if [[ "$(jq -r '.uploaded_new // false' "$PUB")" == true && "$FILE" != "$BASE_FILE" ]]; then
  curl -fsS -X DELETE -H "Authorization: Bearer $ACCESS_TOKEN" "https://www.googleapis.com/drive/v3/files/$FILE"
fi
jq -n --slurpfile r "$E/readback.json" --slurpfile c "$E/gas-contract.json" '{status:"PASS",rollback_base:true,manifest_restored_before_cleanup:true,beta_readback:$r[0],gas_contract:$c[0]}' > "$E/receipt.json";cat "$E/receipt.json"
