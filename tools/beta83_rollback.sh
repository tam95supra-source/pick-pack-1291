#!/usr/bin/env bash
set -Eeuo pipefail
R=ops/beta-release-request.json;E=/tmp/beta-rollback;rm -rf "$E";mkdir -p "$E";PUB=/tmp/beta-publish/receipt.json;test -f "$PUB"
FILE=$(jq -r '.drive_file_id' "$PUB");test -n "$FILE" -a "$FILE" != null
TOKEN_JSON=$(curl -fsS https://oauth2.googleapis.com/token -H 'Content-Type: application/x-www-form-urlencoded'   --data-urlencode "client_id=$GOOGLE_OAUTH_CLIENT_ID" --data-urlencode "client_secret=$GOOGLE_OAUTH_CLIENT_SECRET"   --data-urlencode "refresh_token=$GOOGLE_OAUTH_REFRESH_TOKEN" --data-urlencode grant_type=refresh_token)
TOKEN=$(jq -r '.access_token//empty' <<<"$TOKEN_JSON");test -n "$TOKEN";echo "::add-mask::$TOKEN";echo "::add-mask::$FILE"
curl -fsS -X DELETE -H "Authorization: Bearer $TOKEN" "https://www.googleapis.com/drive/v3/files/$FILE"
RAW=$(printf '%s' "$GAS_DEPLOYMENT_ID"|tr -d '\r\n\t ');DEP="$RAW";if [[ "$RAW" == *"/s/"* ]]; then DEP="${RAW#*/s/}";DEP="${DEP%%/*}";fi
URL="https://script.google.com/macros/s/$DEP/exec";echo "::add-mask::$URL"
PASS=0
for a in 0 1 2 3; do
  BODY=$(jq -nc --arg current "$(jq -r '.base_probe_version' "$R")" '{action:"update_check",channel:"BETA",current_version:$current}')
  curl -fsSL --connect-timeout 15 --max-time 35 -H 'content-type: application/json' "$URL" --data-binary "$BODY" > "$E/readback.json" || true
  if jq -e --arg v "$(jq -r '.base_version' "$R")" --arg h "$(jq -r '.base_apk_sha256' "$R")" --argjson z "$(jq -r '.base_apk_size' "$R")" '.ok==true and .available==true and .version_name==$v and .sha256==$h and .size==$z' "$E/readback.json" >/dev/null 2>&1; then PASS=1;break;fi
  sleep $((3+a*4))
done
test "$PASS" = 1
jq -n --slurpfile r "$E/readback.json" '{status:"PASS",rollback_base:true,beta_readback:$r[0]}' > "$E/receipt.json";cat "$E/receipt.json"
