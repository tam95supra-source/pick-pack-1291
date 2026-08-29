#!/usr/bin/env bash
set -Eeuo pipefail
test "$#" -eq 8
VERSION="$1";SOURCE="$2";APK="$3";SHA="$4";SIZE="$5";NOTES_FILE="$6";ASSET_NAME="$7";OUT="$8"
for n in GH_TOKEN GITHUB_REPOSITORY; do test -n "${!n:-}"; done
test -f "$APK" -a -f "$NOTES_FILE";test "$(sha256sum "$APK"|awk '{print $1}')" = "$SHA";test "$(stat -c '%s' "$APK")" = "$SIZE"
TAG="v$VERSION-publicbeta"
CREATED=false;UPLOADED=false
if gh release view "$TAG" --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1; then
  REF=$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$TAG")
  TYPE=$(jq -r '.object.type' <<<"$REF");TAG_SHA=$(jq -r '.object.sha' <<<"$REF")
  if [[ "$TYPE" == tag ]]; then TAG_SHA=$(gh api "repos/$GITHUB_REPOSITORY/git/tags/$TAG_SHA" --jq '.object.sha');fi
  test "$TAG_SHA" = "$SOURCE"
else
  gh release create "$TAG" --repo "$GITHUB_REPOSITORY" --target "$SOURCE" --title "Pick Pack 1291 $VERSION" --notes-file "$NOTES_FILE" --prerelease
  CREATED=true
fi
REL=$(gh api "repos/$GITHUB_REPOSITORY/releases/tags/$TAG")
ASSET_ID=$(jq -r --arg n "$ASSET_NAME" '.assets[]?|select(.name==$n)|.id' <<<"$REL"|head -n1)
TMP=$(mktemp -d);trap 'rm -rf "$TMP"' EXIT
if [[ -z "$ASSET_ID" ]]; then
  cp "$APK" "$TMP/$ASSET_NAME"
  gh release upload "$TAG" "$TMP/$ASSET_NAME" --repo "$GITHUB_REPOSITORY"
  UPLOADED=true
  REL=$(gh api "repos/$GITHUB_REPOSITORY/releases/tags/$TAG")
fi
COUNT=$(jq --arg n "$ASSET_NAME" '[.assets[]?|select(.name==$n)]|length' <<<"$REL");test "$COUNT" = 1
URL=$(jq -r --arg n "$ASSET_NAME" '.assets[]|select(.name==$n)|.browser_download_url' <<<"$REL")
REMOTE_SIZE=$(jq -r --arg n "$ASSET_NAME" '.assets[]|select(.name==$n)|.size' <<<"$REL")
test "$REMOTE_SIZE" = "$SIZE";[[ "$URL" == https://github.com/*/releases/download/* ]];echo "::add-mask::$URL"
curl -fsSL --retry 2 --retry-delay 2 --connect-timeout 15 --max-time 180 "$URL" -o "$TMP/readback.apk"
test "$(sha256sum "$TMP/readback.apk"|awk '{print $1}')" = "$SHA";test "$(stat -c '%s' "$TMP/readback.apk")" = "$SIZE";cmp -s "$APK" "$TMP/readback.apk"
jq -n --arg tag "$TAG" --arg url "$URL" --arg source "$SOURCE" --arg h "$SHA" --argjson z "$SIZE" --argjson created "$CREATED" --argjson uploaded "$UPLOADED" '{status:"PASS",tag:$tag,apk_url:$url,target_source_sha:$source,sha256:$h,size:$z,release_created:$created,asset_uploaded:$uploaded,exact_public_readback:true}' > "$OUT"
cat "$OUT"
