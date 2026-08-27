#!/usr/bin/env bash
set -Eeuo pipefail

EXPECTED_SIGNER=d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e
for v in SIGNING_KEY_B64 SIGNING_STORE_PASSWORD SIGNING_KEY_PASSWORD SIGNING_ALIAS; do
  test -n "${!v:-}"
done

SDK="${ANDROID_HOME:-/usr/local/lib/android/sdk}"
if [[ ! -f "$SDK/platforms/android-36/android.jar" ]]; then
  yes | "$SDK/cmdline-tools/latest/bin/sdkmanager" --licenses >/dev/null || true
  "$SDK/cmdline-tools/latest/bin/sdkmanager" 'platforms;android-36' 'build-tools;36.0.0'
fi
BT="$SDK/build-tools/36.0.0"
test -x "$BT/d8" -a -x "$BT/aapt" -a -x "$BT/apksigner"

W=/tmp/beta81-harness
rm -rf "$W"
mkdir -p "$W/src/vn/pickpack1291/verify" "$W/classes" "$W/dex"
sed   -e 's/Beta80 OTA exact candidate/Beta81 OTA exact candidate/g'   -e 's/putInt("version_code",86)/putInt("version_code",87)/g'   tools/Beta80VerifyInstrumentation.java > "$W/src/vn/pickpack1291/verify/Beta80VerifyInstrumentation.java"
cp tools/Beta81LocalChecksInstrumentation.java "$W/src/vn/pickpack1291/verify/"

javac -encoding UTF-8 -source 8 -target 8 -cp "$SDK/platforms/android-36/android.jar"   -d "$W/classes"   "$W/src/vn/pickpack1291/verify/Beta80VerifyInstrumentation.java"   "$W/src/vn/pickpack1291/verify/Beta81LocalChecksInstrumentation.java"

mapfile -t CLASSES < <(find "$W/classes" -type f -name '*.class' -print | sort)
test "${#CLASSES[@]}" -ge 3
"$BT/d8" --lib "$SDK/platforms/android-36/android.jar" --output "$W/dex" "${CLASSES[@]}"

cat > "$W/AndroidManifest.xml" <<'XML'
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="vn.pickpack1291.verify">
  <uses-sdk android:minSdkVersion="29" android:targetSdkVersion="36"/>
  <application android:label="Beta81 Verify"/>
  <instrumentation
      android:name=".Beta80VerifyInstrumentation"
      android:targetPackage="vn.pickpack1291.app.beta.publicbeta"
      android:functionalTest="true"
      android:handleProfiling="false"/>
  <instrumentation
      android:name=".Beta81LocalChecksInstrumentation"
      android:targetPackage="vn.pickpack1291.app.beta.publicbeta"
      android:functionalTest="true"
      android:handleProfiling="false"/>
</manifest>
XML

"$BT/aapt" package -f -M "$W/AndroidManifest.xml" -I "$SDK/platforms/android-36/android.jar" -F "$W/harness-unsigned.apk"
(cd "$W/dex" && "$BT/aapt" add "$W/harness-unsigned.apk" classes.dex >/dev/null)

KS="$W/release.jks"
printf '%s' "$SIGNING_KEY_B64" | base64 -d > "$KS"
printf '%s' "$SIGNING_STORE_PASSWORD" > "$W/store.pass"
printf '%s' "$SIGNING_KEY_PASSWORD" > "$W/key.pass"
"$BT/apksigner" sign   --ks "$KS" --ks-key-alias "$SIGNING_ALIAS"   --ks-pass "file:$W/store.pass" --key-pass "file:$W/key.pass"   --out /tmp/beta81-verify-harness.apk "$W/harness-unsigned.apk"
"$BT/apksigner" verify --print-certs /tmp/beta81-verify-harness.apk > "$W/cert.txt"
CERT=$(grep -m1 'Signer #1 certificate SHA-256 digest:' "$W/cert.txt" | sed 's/.*digest: //' | tr 'A-F' 'a-f' | tr -d ':[:space:]')
test "$CERT" = "$EXPECTED_SIGNER"
rm -f "$KS" "$W/store.pass" "$W/key.pass"

echo "ANDROID_SDK_ROOT=$SDK" >> "$GITHUB_ENV"
echo "VERIFY_HARNESS_APK=/tmp/beta81-verify-harness.apk" >> "$GITHUB_ENV"
