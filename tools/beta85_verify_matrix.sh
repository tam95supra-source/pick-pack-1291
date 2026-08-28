#!/usr/bin/env bash
set -Eeuo pipefail
REQ=ops/beta-release-request.json
VERSION=$(jq -r '.version_name' "$REQ");CODE=$(jq -r '.version_code' "$REQ");PKG=$(jq -r '.package' "$REQ")
META=/tmp/beta85-candidate/release-meta.json;APK=/tmp/beta85-candidate/pick-pack-1291-public-beta-$VERSION.apk
test -f "$META" -a -f "$APK" -a -f "$VERIFY_HARNESS_APK"
SHA=$(jq -r '.apk_sha256' "$META");SIZE=$(jq -r '.apk_size' "$META")
REQ_SOURCE=$(jq -r '.source_sha' "$REQ");REQ_SHA=$(jq -r '.apk_sha256' "$REQ");REQ_SIZE=$(jq -r '.apk_size' "$REQ");REQ_SIGNER=$(jq -r '.signer_sha256' "$REQ")
jq -e --arg v "$VERSION" --argjson code "$CODE" --arg pkg "$PKG" --arg src "$REQ_SOURCE" --arg sha "$REQ_SHA" --argjson size "$REQ_SIZE" --arg signer "$REQ_SIGNER" '
  .version_name==$v and .version_code==$code and .package==$pkg and .source_sha==$src and
  .apk_sha256==$sha and .apk_size==$size and .signer_sha256==$signer and
  .candidate_locked==true and .stable_publish=="FORBIDDEN" and .authority_change=="NONE"
' "$META" >/dev/null
test "$SHA" = "$REQ_SHA";test "$SIZE" = "$REQ_SIZE"
test "$(sha256sum "$APK"|awk '{print $1}')" = "$SHA";test "$(stat -c '%s' "$APK")" = "$SIZE"
OUT=/tmp/beta85-verify;rm -rf "$OUT";mkdir -p "$OUT"
adb root >"$OUT/adb-root.txt" 2>&1 || true;timeout 30s adb wait-for-device
test "$(adb shell id -u 2>/dev/null|tr -d '\r')" = 0
adb install -r "$APK" >"$OUT/install-candidate.txt";adb install -r "$VERIFY_HARNESS_APK" >"$OUT/install-harness.txt"
for spec in '320 568 160' '360 640 180' '480 800 240'; do
  read -r W H D <<<"$spec";TAG="${W}x${H}"
  MODE=visual;[[ "$TAG" == "320x568" ]] && MODE=checks
  adb shell wm size "${W}x${H}" >/dev/null;adb shell wm density "$D" >/dev/null
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  adb shell pm clear "$PKG" >/dev/null
  adb shell svc wifi disable >/dev/null 2>&1 || true;adb shell svc data disable >/dev/null 2>&1 || true
  set +e
  timeout 150s adb shell am instrument -w -r -e mode "$MODE" -e tag "$TAG" -e mnv 981820081 -e mnv2 981820082 -e mnv3 981820083 vn.pickpack1291.verify/.Beta85UiChecksInstrumentation >"$OUT/$TAG-instrument.txt" 2>&1
  RC=$?
  set -e
  test "$RC" = 0;grep -Fq 'INSTRUMENTATION_CODE: 0' "$OUT/$TAG-instrument.txt"
  mkdir -p "$OUT/$TAG"
  adb pull "/sdcard/Android/data/$PKG/files/beta85-visual/." "$OUT/$TAG/" >/dev/null
  if [[ "$MODE" == checks ]]; then
    adb shell cat "/data/user/0/$PKG/shared_prefs/pp_beta85_verify.xml" >"$OUT/$TAG-flags.xml"
    for flag in current_day_filter header_removed old_warning_preserved qr_reconciliation null_sanitized incomplete_detail_button staff_list_to_qr complete_direct_list settings_simplified reconciliation_above_scan work_info_order before_after_visible audit_payload_merge timeline_newest_first hhmm_edit_confirmation hhmm_tolerance_no_guidance staff_identity_sort ota_storage_cleanup; do
      grep -Fq "name=\"$flag\" value=\"true\"" "$OUT/$TAG-flags.xml"
    done
  fi
done
python3 - <<'PY'
from pathlib import Path
expected={"320x568":((320,568),11),"360x640":((360,640),4),"480x800":((480,800),4)}
root=Path("/tmp/beta85-verify")
total=0
for tag,(size,count) in expected.items():
    files=sorted((root/tag).glob("*.png"))
    assert len(files)==count,(tag,len(files),count,[p.name for p in files])
    for p in files:
        b=p.read_bytes()
        assert b[:8]==b"\x89PNG\r\n\x1a\n",p
        wh=(int.from_bytes(b[16:20],"big"),int.from_bytes(b[20:24],"big"))
        assert wh==size,(p,wh,size)
        total+=1
(root/"visual-summary.txt").write_text(f"screenshots={total}\nsizes=320x568,360x640,480x800\nhuman_inspection_required=true\n",encoding="utf-8")
PY
jq -nc --arg version "$VERSION" --argjson code "$CODE" --arg sha "$SHA" --argjson size "$SIZE" --argjson run "$GITHUB_RUN_ID" '{status:"PASS",version_name:$version,version_code:$code,apk_sha256:$sha,apk_size:$size,run:$run,functional_pass:true,current_day_only:true,incomplete_and_complete_paths:true,qr_session_cards:true,null_sanitized:true,settings_simplified:true,old_warning_preserved:true,reconciliation_above_scan:true,work_info_order:true,before_after_visible:true,timeline_newest_first:true,hhmm_edit_confirmation:true,hhmm_tolerance_no_guidance:true,staff_identity_sort:true,ota_storage_cleanup:true,audit_payload_merge:true,visual_sizes:["320x568","360x640","480x800"],screenshot_count:19,functional_size:"320x568",human_inspection_required:true}' > "$OUT/receipt.json"
cat "$OUT/receipt.json"
