#!/usr/bin/env bash
set -Eeuo pipefail
REQ=ops/beta-release-request.json
jq -e '.stage=="BUILD_VERIFY" and .version_name=="0.4.2-beta.82" and .version_code==88 and .stable_publish=="FORBIDDEN" and .authority_change=="NONE" and .human_visual_pass==false' "$REQ" >/dev/null
SOURCE_SHA=$(jq -r '.source_sha' "$REQ");VERSION=$(jq -r '.version_name' "$REQ");CODE=$(jq -r '.version_code' "$REQ");PKG=$(jq -r '.package' "$REQ");EXPECTED_SIGNER=$(jq -r '.signer_sha256' "$REQ")
STATE_SIGNER=$(grep -m1 '^- signer_sha256:' CURRENT_STATE.md | awk '{print $3}')
test "$EXPECTED_SIGNER" = "$STATE_SIGNER"
test "$(git rev-parse "$SOURCE_SHA")" = "$SOURCE_SHA"
git diff --quiet "$SOURCE_SHA" HEAD -- app
git diff --check "$SOURCE_SHA" HEAD
grep -q "versionCode = $CODE" app/build.gradle.kts
grep -q "versionName = \"$VERSION\"" app/build.gradle.kts
grep -q 'versionCode = 1' app/build.gradle.kts
grep -q 'versionName = "0.1.0-stable"' app/build.gradle.kts
! grep -Fq 'RÀ SOÁT VÀO / RA •' app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt
grep -Fq 'HIỂN THỊ CHI TIẾT NHÂN SỰ' app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt
grep -Fq 'SHIFT_STAFF_LIST' app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt
grep -Fq 'basicLogRows' app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt
for v in SIGNING_KEY_B64 SIGNING_STORE_PASSWORD SIGNING_KEY_PASSWORD SIGNING_ALIAS; do test -n "${!v:-}"; done
gradle --no-daemon --build-cache --parallel :app:testBetaDebugUnitTest :app:assembleBetaDebug :app:assembleStableDebug :app:assembleBetaRelease
BT="$ANDROID_SDK_ROOT/build-tools/36.0.0";U=app/build/outputs/apk/beta/release/app-beta-release-unsigned.apk
test -f "$U";"$BT/aapt" dump badging "$U" > /tmp/beta82-badging.txt
grep -q "package: name='$PKG'" /tmp/beta82-badging.txt
grep -q "versionCode='$CODE'" /tmp/beta82-badging.txt
grep -q "versionName='$VERSION'" /tmp/beta82-badging.txt
KS="$RUNNER_TEMP/release.jks";printf '%s' "$SIGNING_KEY_B64" | base64 -d > "$KS"
printf '%s' "$SIGNING_STORE_PASSWORD" > "$RUNNER_TEMP/store.pass";printf '%s' "$SIGNING_KEY_PASSWORD" > "$RUNNER_TEMP/key.pass"
OUT=/tmp/beta82-candidate;rm -rf "$OUT";mkdir -p "$OUT"
APK="$OUT/pick-pack-1291-public-beta-$VERSION.apk"
"$BT/apksigner" sign --ks "$KS" --ks-key-alias "$SIGNING_ALIAS" --ks-pass "file:$RUNNER_TEMP/store.pass" --key-pass "file:$RUNNER_TEMP/key.pass" --out "$APK" "$U"
"$BT/apksigner" verify --verbose --print-certs "$APK" > "$OUT/cert.txt"
CERT=$(grep -m1 'Signer #1 certificate SHA-256 digest:' "$OUT/cert.txt" | sed 's/.*digest: //' | tr 'A-F' 'a-f' | tr -d ':[:space:]')
test "$CERT" = "$EXPECTED_SIGNER"
SHA=$(sha256sum "$APK" | awk '{print $1}');SIZE=$(stat -c '%s' "$APK")
jq -nc --arg version "$VERSION" --argjson code "$CODE" --arg package "$PKG" --arg source "$SOURCE_SHA" --arg sha "$SHA" --argjson size "$SIZE" --arg signer "$EXPECTED_SIGNER" --argjson run "$GITHUB_RUN_ID" '{version_name:$version,version_code:$code,package:$package,source_sha:$source,build_run:$run,apk_sha256:$sha,apk_size:$size,signer_sha256:$signer,candidate_locked:true,stable_publish:"FORBIDDEN",authority_change:"NONE"}' > "$OUT/release-meta.json"
printf '%s  %s\n' "$SHA" "$(basename "$APK")" > "$OUT/SHA256SUMS.txt"
rm -f "$KS" "$RUNNER_TEMP/store.pass" "$RUNNER_TEMP/key.pass"
cat "$OUT/release-meta.json"
