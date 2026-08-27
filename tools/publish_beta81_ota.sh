#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_SHA=963ed28a90d2bb3e4a950ae8100fef15edfa86c5
CANDIDATE_RUN=33073351925
CANDIDATE_ARTIFACT_ID=9646920908
VISUAL_ARTIFACT_ID=9647045177
SERVICE_ARTIFACT_ID=9646805806
EXPECTED_SIGNER=d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e
TARGET_VERSION=0.4.2-beta.81
TARGET_CODE=87
PREV_VERSION=0.4.2-beta.80
PREV_SHA=1210bf57ff3bb48a723aa40d2efc8ec922c5e632e4c1d9928bf4dbe843654a69
PREV_SIZE=13196221
BETA_FOLDER_ID=1WMXI-8-Z1mbY2v11noYFHe_eoMNiNZXg
SERVICE_URL=https://pickpack.1291.workers.dev
E=/tmp/beta81-publish
APK=/tmp/beta81-candidate/pick-pack-1291-public-beta-0.4.2-beta.81.apk
META=/tmp/beta81-candidate/release-meta.json
mkdir -p "$E"

for n in GH_TOKEN GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN GAS_DEPLOYMENT_ID GITHUB_REPOSITORY GITHUB_API_URL; do
  test -n "${!n:-}"
done
test -f "$APK" -a -f "$META"

jq -e --arg source "$SOURCE_SHA" --arg signer "$EXPECTED_SIGNER" '
  .version_name=="0.4.2-beta.81" and
  .version_code==87 and
  .package=="vn.pickpack1291.app.beta.publicbeta" and
  .source_sha==$source and
  .build_run==33073351925 and
  .signer_sha256==$signer and
  .candidate_locked==true and
  .stable_publish=="FORBIDDEN" and
  .service_run==33073351925 and
  .authority_change=="NONE"
' "$META" >/dev/null

APK_SHA=$(jq -r '.apk_sha256' "$META")
APK_SIZE=$(jq -r '.apk_size' "$META")
test "$APK_SHA" != null -a "${#APK_SHA}" -eq 64
test "$APK_SIZE" -gt 1000000
test "$(sha256sum "$APK" | awk '{print $1}')" = "$APK_SHA"
test "$(stat -c '%s' "$APK")" = "$APK_SIZE"

check_artifact(){
  local id="$1" name="$2" digest="$3"
  curl -fsS -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json'     "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/actions/artifacts/$id" > "$E/artifact-$id.json"
  jq -e --arg n "$name" --arg d "$digest" --argjson id "$id"     '.id==$id and .name==$n and .digest==$d and .expired==false' "$E/artifact-$id.json" >/dev/null
}
check_artifact 9646920908 beta81-candidate-33073351925 sha256:16b79ea2fef49c7a1091cb1f02a2a9e0dce7708aabbe51c830cee3f67b9b95e2
check_artifact 9647045177 beta81-visual-33073351925 sha256:ca119c02e7e4133892b337245205bd3a06bd4635fd435f20a74ae7a1cb2d54b7
check_artifact 9646805806 beta81-service-live-33073351925 sha256:e5503a019509a2c8a31bf7a169c4fd15c07581f9aa4a3bef7e42135ad5e4c3ec

git diff --quiet "$SOURCE_SHA" HEAD -- app service google-apps-script
git diff --check "$SOURCE_SHA" HEAD

MAIN_BEFORE=$(curl -fsSL --connect-timeout 15 --max-time 30   -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json'   "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/branches/main" | jq -r '.commit.sha')
test -n "$MAIN_BEFORE" -a "$MAIN_BEFORE" != null
curl -fsSL --connect-timeout 15 --max-time 30 "$SERVICE_URL/v1/authority" > "$E/authority-before.json"
jq -e '.ok==true and .authority.mode=="SERVICE_PRIMARY" and .authority.scope=="PRODUCTION"' "$E/authority-before.json" >/dev/null

RAW=$(printf '%s' "$GAS_DEPLOYMENT_ID" | tr -d '\r\n\t ')
DEPLOYMENT_ID="$RAW"
if [[ "$RAW" == *"/s/"* ]]; then
  DEPLOYMENT_ID="${RAW#*/s/}"
  DEPLOYMENT_ID="${DEPLOYMENT_ID%%/*}"
fi
test -n "$DEPLOYMENT_ID"
GAS_URL="https://script.google.com/macros/s/$DEPLOYMENT_ID/exec"
echo "::add-mask::$DEPLOYMENT_ID"
echo "::add-mask::$GAS_URL"

read_update(){
  local channel="$1" current="$2" out="$3" attempt
  for attempt in 0 1 2; do
    if curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL"       -d "{\"action\":\"update_check\",\"channel\":\"$channel\",\"current_version\":\"$current\"}" > "$out"       && jq -e --arg ch "$channel" '.ok==true and .channel==$ch and (.available==true or .available==false)' "$out" >/dev/null 2>&1; then
      return 0
    fi
    [[ "$attempt" -lt 2 ]] || break
    sleep $((2 + attempt * 4))
  done
  jq -c . "$out" 2>/dev/null >&2 || true
  return 1
}

read_update STABLE 0.1.0-stable "$E/stable-before.json"
jq -e '.ok==true and .channel=="STABLE" and .available==false and .reason=="NO_APK"' "$E/stable-before.json" >/dev/null
read_update BETA "0.4.2-beta.79" "$E/beta-before.json"

TARGET_ALREADY=0
if jq -e --arg h "$APK_SHA" --argjson z "$APK_SIZE"   '.ok==true and .channel=="BETA" and .available==true and .version_name=="0.4.2-beta.81" and .sha256==$h and .size==$z and ((.apk_url//"")|length)>0'   "$E/beta-before.json" >/dev/null 2>&1; then
  TARGET_ALREADY=1
else
  jq -e --arg h "$PREV_SHA" --argjson z "$PREV_SIZE"     '.ok==true and .channel=="BETA" and .available==true and .version_name=="0.4.2-beta.80" and .sha256==$h and .size==$z and ((.apk_url//"")|length)>0'     "$E/beta-before.json" >/dev/null
fi

FILE_ID=""
APK_URL=""
if [[ "$TARGET_ALREADY" == 1 ]]; then
  APK_URL=$(jq -r '.apk_url' "$E/beta-before.json")
  FILE_ID=$(python3 -c 'import sys,urllib.parse as u; q=u.parse_qs(u.urlparse(sys.argv[1]).query); print((q.get("id") or [""])[0])' "$APK_URL")
  test -n "$FILE_ID"
else
  TOKEN_JSON=$(curl -fsS --connect-timeout 15 --max-time 30 https://oauth2.googleapis.com/token     -H 'Content-Type: application/x-www-form-urlencoded'     --data-urlencode "client_id=$GOOGLE_OAUTH_CLIENT_ID"     --data-urlencode "client_secret=$GOOGLE_OAUTH_CLIENT_SECRET"     --data-urlencode "refresh_token=$GOOGLE_OAUTH_REFRESH_TOKEN"     --data-urlencode grant_type=refresh_token)
  ACCESS_TOKEN=$(jq -r '.access_token // empty' <<<"$TOKEN_JSON")
  test -n "$ACCESS_TOKEN"
  echo "::add-mask::$ACCESS_TOKEN"

  DRIVE_OK=0
  for attempt in 0 1 2; do
    HTTP=$(curl -sS --connect-timeout 15 --max-time 30 -o "$E/drive-folder.json" -w '%{http_code}'       -H "Authorization: Bearer $ACCESS_TOKEN"       "https://www.googleapis.com/drive/v3/files/$BETA_FOLDER_ID?fields=id,name,mimeType" || printf 000)
    if [[ "$HTTP" == 200 ]] && jq -e --arg id "$BETA_FOLDER_ID" '.id==$id' "$E/drive-folder.json" >/dev/null 2>&1; then
      DRIVE_OK=1
      break
    fi
    [[ "$attempt" -lt 2 ]] || break
    sleep $((2 + attempt * 4))
  done
  test "$DRIVE_OK" = 1

  APK_NAME=pick-pack-1291-public-beta-0.4.2-beta.81.apk
  Q="'$BETA_FOLDER_ID' in parents and name='$APK_NAME' and trashed=false"
  curl -fsS --get --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN"     --data-urlencode "q=$Q" --data-urlencode 'fields=files(id,name,size,modifiedTime)'     https://www.googleapis.com/drive/v3/files > "$E/drive-search.json"
  COUNT=$(jq '.files|length' "$E/drive-search.json")
  while read -r id; do
    [[ -n "$id" ]] || continue
    curl -fsS --connect-timeout 15 --max-time 120 -H "Authorization: Bearer $ACCESS_TOKEN"       "https://www.googleapis.com/drive/v3/files/$id?alt=media" -o "$E/existing.apk" || continue
    if [[ "$(sha256sum "$E/existing.apk" | awk '{print $1}')" == "$APK_SHA" && "$(stat -c '%s' "$E/existing.apk")" == "$APK_SIZE" ]]; then
      FILE_ID="$id"
      break
    fi
  done < <(jq -r '.files[]?.id' "$E/drive-search.json")
  if [[ -z "$FILE_ID" && "$COUNT" -gt 0 ]]; then
    echo BETA81_NAME_COLLISION_NONEXACT >&2
    exit 31
  fi
  if [[ -z "$FILE_ID" ]]; then
    META_JSON=$(jq -nc --arg n "$APK_NAME" --arg p "$BETA_FOLDER_ID" '{name:$n,parents:[$p]}')
    curl -fsS --connect-timeout 15 --max-time 120 -X POST       -H "Authorization: Bearer $ACCESS_TOKEN"       -F "metadata=$META_JSON;type=application/json;charset=UTF-8"       -F "file=@$APK;type=application/vnd.android.package-archive"       'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,size' > "$E/drive-upload.json"
    FILE_ID=$(jq -r '.id // empty' "$E/drive-upload.json")
    test -n "$FILE_ID"
  fi
  echo "::add-mask::$FILE_ID"
  DESC="Beta81 exact OTA; SHA256 $APK_SHA; candidate run 33073351925; artifact 9646920908; signer $EXPECTED_SIGNER"
  jq -nc --arg d "$DESC" '{description:$d}' > "$E/drive-meta.json"
  curl -fsS --connect-timeout 15 --max-time 30 -X PATCH     -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json'     --data-binary @"$E/drive-meta.json"     "https://www.googleapis.com/drive/v3/files/$FILE_ID?fields=id,name,size,description" > "$E/drive-meta-out.json"

  curl -fsS --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN"     "https://www.googleapis.com/drive/v3/files/$FILE_ID/permissions?fields=permissions(id,type,role)" > "$E/permissions.json"
  if ! jq -e '.permissions[]? | select(.type=="anyone" and .role=="reader")' "$E/permissions.json" >/dev/null; then
    curl -fsS --connect-timeout 15 --max-time 30 -X POST       -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json'       -d '{"type":"anyone","role":"reader"}'       "https://www.googleapis.com/drive/v3/files/$FILE_ID/permissions?fields=id,type,role" > "$E/permission-created.json"
  fi

  for u in     "https://drive.usercontent.google.com/download?id=$FILE_ID&export=download&confirm=t"     "https://drive.google.com/uc?export=download&id=$FILE_ID"; do
    rm -f "$E/public.apk"
    if curl -fsSL --retry 2 --retry-delay 2 --connect-timeout 15 --max-time 120 "$u" -o "$E/public.apk"       && [[ "$(sha256sum "$E/public.apk" | awk '{print $1}')" == "$APK_SHA" ]]       && [[ "$(stat -c '%s' "$E/public.apk")" == "$APK_SIZE" ]]; then
      APK_URL="$u"
      break
    fi
  done
  test -n "$APK_URL"
fi

echo "::add-mask::$FILE_ID"
echo "::add-mask::$APK_URL"
curl -fsSL --retry 2 --retry-delay 2 --connect-timeout 15 --max-time 120 "$APK_URL" -o "$E/ota-readback.apk"
test "$(sha256sum "$E/ota-readback.apk" | awk '{print $1}')" = "$APK_SHA"
test "$(stat -c '%s' "$E/ota-readback.apk")" = "$APK_SIZE"
cmp -s "$APK" "$E/ota-readback.apk"

PASS=0
for attempt in 0 1 2; do
  read_update BETA "$PREV_VERSION" "$E/beta-after.json" || true
  if jq -e --arg h "$APK_SHA" --argjson z "$APK_SIZE"     '.ok==true and .channel=="BETA" and .available==true and .version_name=="0.4.2-beta.81" and .sha256==$h and .size==$z and ((.apk_url//"")|length)>0'     "$E/beta-after.json" >/dev/null 2>&1; then
    PASS=1
    break
  fi
  [[ "$attempt" -lt 2 ]] && sleep $((2 + attempt * 4))
done
test "$PASS" = 1
RETURNED_URL=$(jq -r '.apk_url' "$E/beta-after.json")
curl -fsSL --retry 2 --retry-delay 2 --connect-timeout 15 --max-time 120 "$RETURNED_URL" -o "$E/ota-contract-readback.apk"
test "$(sha256sum "$E/ota-contract-readback.apk" | awk '{print $1}')" = "$APK_SHA"
test "$(stat -c '%s' "$E/ota-contract-readback.apk")" = "$APK_SIZE"
cmp -s "$APK" "$E/ota-contract-readback.apk"

read_update BETA "$TARGET_VERSION" "$E/beta-current-target.json"
jq -e '.ok==true and .channel=="BETA" and .available==false and .version_name=="0.4.2-beta.81"' "$E/beta-current-target.json" >/dev/null
read_update STABLE 0.1.0-stable "$E/stable-after.json"
jq -e '.ok==true and .channel=="STABLE" and .available==false and .reason=="NO_APK"' "$E/stable-after.json" >/dev/null
jq -S . "$E/stable-before.json" > "$E/stable-before.canon"
jq -S . "$E/stable-after.json" > "$E/stable-after.canon"
cmp -s "$E/stable-before.canon" "$E/stable-after.canon"

MAIN_AFTER=$(curl -fsSL --connect-timeout 15 --max-time 30   -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json'   "$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/branches/main" | jq -r '.commit.sha')
test "$MAIN_AFTER" = "$MAIN_BEFORE"
curl -fsSL --connect-timeout 15 --max-time 30 "$SERVICE_URL/v1/authority" > "$E/authority-after.json"
jq -e --slurpfile b "$E/authority-before.json" '
  .ok==true and
  .authority.mode==$b[0].authority.mode and
  .authority.scope==$b[0].authority.scope and
  .authority.authority_epoch==$b[0].authority.authority_epoch and
  .authority.service_generation==$b[0].authority.service_generation
' "$E/authority-after.json" >/dev/null

jq -n   --arg version "$TARGET_VERSION" --argjson code "$TARGET_CODE" --arg source "$SOURCE_SHA"   --arg h "$APK_SHA" --argjson z "$APK_SIZE" --arg signer "$EXPECTED_SIGNER"   --arg file "$FILE_ID" --arg url "$RETURNED_URL" --arg main "$MAIN_AFTER"   --argjson target_already "$TARGET_ALREADY"   --slurpfile beta "$E/beta-after.json" --slurpfile current "$E/beta-current-target.json"   --slurpfile stable "$E/stable-after.json" --slurpfile auth "$E/authority-after.json"   '{
    status:"PASS",channel:"BETA",version_name:$version,version_code:$code,
    package:"vn.pickpack1291.app.beta.publicbeta",source_sha:$source,
    candidate_run:33073351925,candidate_artifact:9646920908,
    visual_artifact:9647045177,service_artifact:9646805806,
    apk_sha256:$h,apk_size:$z,signer_sha256:$signer,
    drive_file_id:$file,apk_url:$url,ota_exact_bytes:true,
    publish_mode:(if $target_already==1 then "REUSED_ALREADY_LIVE_EXACT" else "PUBLISHED_EXACT_BYTES" end),
    beta_readback:$beta[0],target_current_readback:$current[0],
    stable_readback:$stable[0],stable_unchanged:true,
    main_sha:$main,main_unchanged:true,authority:$auth[0].authority,
    authority_change:"NONE",gas_code_changed:false
  }' > "$E/receipt.json"
jq -e '.status=="PASS" and .ota_exact_bytes==true and .stable_unchanged==true and .main_unchanged==true and .authority_change=="NONE"' "$E/receipt.json" >/dev/null

echo "apk_sha=$APK_SHA" >> "$GITHUB_OUTPUT"
echo "apk_size=$APK_SIZE" >> "$GITHUB_OUTPUT"
echo "drive_file_id=$FILE_ID" >> "$GITHUB_OUTPUT"
printf '%s' "$RETURNED_URL" | base64 -w0 | sed 's/^/apk_url_b64=/' >> "$GITHUB_OUTPUT"
cat "$E/receipt.json"
