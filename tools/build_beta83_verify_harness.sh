#!/usr/bin/env bash
set -Eeuo pipefail
REQ=ops/beta-release-request.json
EXPECTED_SIGNER=$(jq -r '.signer_sha256' "$REQ")
for v in SIGNING_KEY_B64 SIGNING_STORE_PASSWORD SIGNING_KEY_PASSWORD SIGNING_ALIAS; do test -n "${!v:-}"; done
SDK="${ANDROID_HOME:-/usr/local/lib/android/sdk}"
if [[ ! -f "$SDK/platforms/android-36/android.jar" ]]; then
  yes | "$SDK/cmdline-tools/latest/bin/sdkmanager" --licenses >/dev/null || true
  "$SDK/cmdline-tools/latest/bin/sdkmanager" 'platforms;android-36' 'build-tools;36.0.0'
fi
BT="$SDK/build-tools/36.0.0"
W=/tmp/beta83-harness
rm -rf "$W";mkdir -p "$W/src/vn/pickpack1291/verify" "$W/classes" "$W/dex"
sed -e 's/Beta80 OTA exact candidate/Beta83 OTA exact candidate/g' -e 's/putInt("version_code",86)/putInt("version_code",89)/g' tools/Beta80VerifyInstrumentation.java > "$W/src/vn/pickpack1291/verify/Beta80VerifyInstrumentation.java"
cp tools/Beta83UiChecksInstrumentation.java "$W/src/vn/pickpack1291/verify/"
# Beta117 release notes changed legitimately; keep changelog structure checks but do not pin a stale exact sentence.
sed -i '/waitText("Quản lý biên bản dùng icon gọn",false,false,10000L);/d' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
# Owner removed redundant screen title/header areas; verify the attendance module by its functional scan control instead.
sed -i 's/waitText("ĐIỂM DANH",true,false,10000L);/waitText("QUÉT ĐỂ ĐIỂM DANH",true,false,10000L);/g' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
# Beta117 renamed the document-batch marker while preserving the same guarded behavior.
sed -i 's/document_batch_controls_beta110/document_batch_controls_beta117/g' tools/beta83_verify_matrix.sh
# Beta121 deliberately localized status-detail labels. Patch the generated harness only;
# the locked candidate APK must remain byte-for-byte unchanged.
sed -i 's/waitText("Loại kết nối",false,false,10000L);/waitText("Kiểu kết nối",false,false,10000L);/g' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
sed -i 's/waitText("Authority",false,false,10000L);/waitText("Chế độ quyền hiện tại",false,false,10000L);/g' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
# Beta121 settings regrouped the former resilience center under a compact technical-test region.
sed -i 's/TRUNG TÂM KIỂM THỬ RESILIENCE/KIỂM THỬ KỸ THUẬT/g' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
# OWNER Beta123 removed the report-scope control and redundant report heading from the rendered
# chrome. Assert the REPORT navigation state plus report-specific content instead of pinning a
# title string that is intentionally no longer exposed to the user.
sed -i 's/waitText("Phạm vi báo cáo",true,false,12000L);/require(navState().contains("screen=REPORT,displayed=REPORT"),"REPORT_SCREEN_STATE_INVALID:"+navState()); require(findText("Phạm vi báo cáo",true,false)==null,"REPORT_SCOPE_CONTROL_MUST_BE_REMOVED");/g' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
# Beta125 diagnostic proved the app returns EMPLOYEE -> SCAN correctly, but the old harness
# falsely required the BUSINESS-home label "QUÉT QR NHÂN SỰ" after Back. Assert the actual
# SCAN semantics instead: state/displayed SCAN, editable scan control present, employee UI
# gone, and the full QR roster remains hidden. Then open a fresh SCAN flow before the older
# roster/grouping assertions, because post-scan roster suppression is itself a locked rule.
python3 - "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
s=p.read_text(encoding='utf-8')
old='''    AccessibilityNodeInfo qrBack=findText("QUÉT QR NHÂN SỰ",true,false);\n    require(qrBack!=null,"BETA125_BACK_NAV_VISUAL_DIAG:"+navBefore+"=>"+navAfter+";texts="+visibleTextSummary());\n    mark("post_scan_activity_back_beta124");'''
new='''    require(navAfter.contains("screen=SCAN,displayed=SCAN"),"BETA125_BACK_NAV_STATE_NOT_SCAN:"+navBefore+"=>"+navAfter);\n    require(findEditable()!=null,"BETA125_BACK_SCAN_INPUT_MISSING:"+navAfter+";texts="+visibleTextSummary());\n    require(findText("THÔNG TIN CA",true,false)==null,"BETA125_BACK_EMPLOYEE_UI_STILL_VISIBLE:"+navAfter);\n    require(findText("Danh sách QR vào / ra",true,false)==null,"BETA125_BACK_ROSTER_REOPENED:"+navAfter);\n    mark("post_scan_activity_back_beta124");\n\n    open("BUSINESS");\n    waitText("Quét QR nhân sự",true,true,10000L);\n    clickText("Quét QR nhân sự",true,12000L);'''
if old not in s:
    raise SystemExit('BETA125_BACK_DIAGNOSTIC_ASSERTION_NOT_FOUND')
p.write_text(s.replace(old,new,1),encoding='utf-8')
PY
! grep -Fq 'waitText("Loại kết nối"' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
! grep -Fq 'waitText("Authority"' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
! grep -Fq 'TRUNG TÂM KIỂM THỬ RESILIENCE' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
! grep -Fq 'waitText("Phạm vi báo cáo"' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
! grep -Fq 'BETA125_BACK_NAV_VISUAL_DIAG' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
grep -Fq 'waitText("Kiểu kết nối"' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
grep -Fq 'waitText("Chế độ quyền hiện tại"' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
grep -Fq 'KIỂM THỬ KỸ THUẬT' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
grep -Fq 'REPORT_SCREEN_STATE_INVALID' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
grep -Fq 'REPORT_SCOPE_CONTROL_MUST_BE_REMOVED' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
grep -Fq 'BETA125_BACK_NAV_STATE_NOT_SCAN' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
grep -Fq 'BETA125_BACK_SCAN_INPUT_MISSING' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
grep -Fq 'BETA125_BACK_ROSTER_REOPENED' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
grep -Fq 'open("BUSINESS");' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
javac -encoding UTF-8 -source 8 -target 8 -cp "$SDK/platforms/android-36/android.jar" -d "$W/classes" "$W/src/vn/pickpack1291/verify/"*.java
mapfile -t CLASSES < <(find "$W/classes" -type f -name '*.class' -print | sort)
test "${#CLASSES[@]}" -ge 3
"$BT/d8" --lib "$SDK/platforms/android-36/android.jar" --output "$W/dex" "${CLASSES[@]}"
cat > "$W/AndroidManifest.xml" <<'XML'
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="vn.pickpack1291.verify">
  <uses-sdk android:minSdkVersion="29" android:targetSdkVersion="36"/>
  <application android:label="Beta83 Verify"/>
  <instrumentation android:name=".Beta80VerifyInstrumentation" android:targetPackage="vn.pickpack1291.app.beta.publicbeta" android:functionalTest="true" android:handleProfiling="false"/>
  <instrumentation android:name=".Beta83UiChecksInstrumentation" android:targetPackage="vn.pickpack1291.app.beta.publicbeta" android:functionalTest="true" android:handleProfiling="false"/>
</manifest>
XML
"$BT/aapt" package -f -M "$W/AndroidManifest.xml" -I "$SDK/platforms/android-36/android.jar" -F "$W/harness-unsigned.apk"
(cd "$W/dex" && "$BT/aapt" add "$W/harness-unsigned.apk" classes.dex >/dev/null)
KS="$W/release.jks";printf '%s' "$SIGNING_KEY_B64" | base64 -d > "$KS"
printf '%s' "$SIGNING_STORE_PASSWORD" > "$W/store.pass";printf '%s' "$SIGNING_KEY_PASSWORD" > "$W/key.pass"
"$BT/apksigner" sign --ks "$KS" --ks-key-alias "$SIGNING_ALIAS" --ks-pass "file:$W/store.pass" --key-pass "file:$W/key.pass" --out /tmp/beta83-verify-harness.apk "$W/harness-unsigned.apk"
"$BT/apksigner" verify --print-certs /tmp/beta83-verify-harness.apk > "$W/cert.txt"
CERT=$(grep -m1 'Signer #1 certificate SHA-256 digest:' "$W/cert.txt" | sed 's/.*digest: //' | tr 'A-F' 'a-f' | tr -d ':[:space:]')
test "$CERT" = "$EXPECTED_SIGNER"
rm -f "$KS" "$W/store.pass" "$W/key.pass"
echo "ANDROID_SDK_ROOT=$SDK" >> "$GITHUB_ENV"
echo "VERIFY_HARNESS_APK=/tmp/beta83-verify-harness.apk" >> "$GITHUB_ENV"
