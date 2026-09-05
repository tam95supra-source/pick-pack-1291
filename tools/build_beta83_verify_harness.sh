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
# Beta125 retains an additional human-inspection screenshot immediately after EMPLOYEE -> Back -> SCAN.
sed -i 's/"320x568":((320,568),21)/"320x568":((320,568),22)/g' tools/beta83_verify_matrix.sh
grep -Fq '"320x568":((320,568),22)' tools/beta83_verify_matrix.sh
# Beta121 localized status-detail labels.
sed -i 's/waitText("Loại kết nối",false,false,10000L);/waitText("Kiểu kết nối",false,false,10000L);/g' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
sed -i 's/waitText("Authority",false,false,10000L);/waitText("Chế độ quyền hiện tại",false,false,10000L);/g' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
# Beta121 settings regrouped the former resilience center.
sed -i 's/TRUNG TÂM KIỂM THỬ RESILIENCE/KIỂM THỬ KỸ THUẬT/g' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
# OWNER Beta123 removed report scope control.
sed -i 's/waitText("Phạm vi báo cáo",true,false,12000L);/require(navState().contains("screen=REPORT,displayed=REPORT"),"REPORT_SCREEN_STATE_INVALID:"+navState()); require(findText("Phạm vi báo cáo",true,false)==null,"REPORT_SCOPE_CONTROL_MUST_BE_REMOVED");/g' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
# Beta125 navigation frame exact semantic assertion.
python3 - "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text(encoding='utf-8')
old='''    AccessibilityNodeInfo qrBack=findText("QUÉT QR NHÂN SỰ",true,false);\n    require(qrBack!=null,"BETA125_BACK_NAV_VISUAL_DIAG:"+navBefore+"=>"+navAfter+";texts="+visibleTextSummary());\n    mark("post_scan_activity_back_beta124");'''
new='''    require(navAfter.contains("screen=SCAN,displayed=SCAN"),"BETA125_BACK_NAV_STATE_NOT_SCAN:"+navBefore+"=>"+navAfter);\n    require(findEditable()!=null,"BETA125_BACK_SCAN_INPUT_MISSING:"+navAfter+";texts="+visibleTextSummary());\n    require(findText("THÔNG TIN CA",true,false)==null,"BETA125_BACK_EMPLOYEE_UI_STILL_VISIBLE:"+navAfter);\n    require(findText("Danh sách QR vào / ra",true,false)==null,"BETA125_BACK_ROSTER_REOPENED:"+navAfter);\n    mark("post_scan_activity_back_beta124");\n\n    open("BUSINESS");\n    waitText("Quét QR nhân sự",true,true,10000L);\n    clickText("Quét QR nhân sự",true,12000L);'''
if old not in s: raise SystemExit('BETA125_BACK_DIAGNOSTIC_ASSERTION_NOT_FOUND')
s=s.replace(old,new,1)
# Beta126: report must expose the exact owner section and remove rejected summary rows.
needle='''    waitText("Thâm niên",true,false,12000L);\n    require(findText("Site 1291 •",false,false)==null,"REPORT_SCOPE_TEXT_MUST_BE_REMOVED");'''
repl='''    waitText("Thâm niên",true,false,12000L);\n    waitText("NHÂN SỰ PICK & PACK THỰC TẾ SAU KHI LOẠI TRỪ HỖ TRỢ",true,false,12000L);\n    require(findText("Tổng nhân sự",true,false)==null,"BETA126_REPORT_TOTAL_MUST_BE_REMOVED");\n    require(findText("Khấu trừ công nhật",true,false)==null,"BETA126_REPORT_DEDUCTION_SUMMARY_MUST_BE_REMOVED");\n    require(findText("Site 1291 •",false,false)==null,"REPORT_SCOPE_TEXT_MUST_BE_REMOVED");'''
if needle not in s: raise SystemExit('BETA126_REPORT_ASSERT_ANCHOR_NOT_FOUND')
s=s.replace(needle,repl)
# Beta127: visual assertions must prove required text is actually rendered.
report_anchor='    waitText("Thâm niên",true,false,12000L);\n    waitText("NHÂN SỰ PICK & PACK THỰC TẾ SAU KHI LOẠI TRỪ HỖ TRỢ",true,false,12000L);'
report_repl='    waitText("BÁO CÁO TÌNH HÌNH NHÂN SỰ",true,false,12000L);\n    waitText("Thâm niên",true,false,12000L);\n    waitText("CHI TIẾT CÔNG NHẬT",true,false,12000L);\n    waitText("NHÂN SỰ PICK & PACK THỰC TẾ SAU KHI LOẠI TRỪ HỖ TRỢ",true,false,12000L);'
if report_anchor not in s: raise SystemExit('BETA127_REPORT_VISIBLE_ANCHOR_NOT_FOUND')
s=s.replace(report_anchor,report_repl,1)
settings_anchor='    waitText("THÔNG TIN ỨNG DỤNG",true,false,10000L);\n'
if settings_anchor not in s: raise SystemExit('BETA127_SETTINGS_VISIBLE_ANCHOR_NOT_FOUND')
s=s.replace(settings_anchor,settings_anchor+'    waitText("XÓA DỮ LIỆU ỨNG DỤNG",true,false,10000L);\n    require(findText("ĐẶT LẠI DỮ LIỆU",true,false)==null,"BETA127_OLD_RESET_LABEL_VISIBLE");\n',1)
# Beta126: labor home must expose bulk edit in addition to create/finish.
needle2='''    waitText("Chi tiết công nhật theo ngày",true,false,10000L);\n    waitText("Scan / Nhập mã nhân viên",true,false,10000L);'''
repl2='''    waitText("Chi tiết công nhật theo ngày",true,false,10000L);\n    waitText("SỬA NHIỀU",true,false,10000L);\n    waitText("Scan / Nhập mã nhân viên",true,false,10000L);'''
if needle2 not in s: raise SystemExit('BETA126_LABOR_ASSERT_ANCHOR_NOT_FOUND')
s=s.replace(needle2,repl2)
p.write_text(s,encoding='utf-8')
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
grep -Fq 'BETA126_REPORT_TOTAL_MUST_BE_REMOVED' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
grep -Fq 'BETA126_REPORT_DEDUCTION_SUMMARY_MUST_BE_REMOVED' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
grep -Fq 'waitText("BÁO CÁO TÌNH HÌNH NHÂN SỰ"' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
grep -Fq 'waitText("CHI TIẾT CÔNG NHẬT"' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
grep -Fq 'waitText("XÓA DỮ LIỆU ỨNG DỤNG"' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
grep -Fq 'BETA127_OLD_RESET_LABEL_VISIBLE' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
grep -Fq 'waitText("SỬA NHIỀU"' "$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java"
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
