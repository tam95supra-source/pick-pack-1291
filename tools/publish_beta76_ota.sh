#!/usr/bin/env bash
set -Eeuo pipefail

BASE=$(BETA75_MATERIALIZE_ONLY=1 bash tools/publish_beta75_ota.sh)
TMP=/tmp/publish_beta76_ota_materialized.sh

python3 - "$BASE" "$TMP" <<'PY'
from pathlib import Path
import re
import sys

src = Path(sys.argv[1]).read_text(encoding='utf-8')

# Move versioned paths, temporary GAS route/helper names and labels to Beta76.
src = src.replace('beta75', 'beta76').replace('Beta75', 'Beta76')

# Shift semantic versions without cascading replacements.
src = src.replace('0.4.2-beta.75', '__BETA76_TARGET__')
src = src.replace('0.4.2-beta.74', '0.4.2-beta.75')
src = src.replace('0.4.2-beta.73', '0.4.2-beta.74')
src = src.replace('__BETA76_TARGET__', '0.4.2-beta.76')

replacements = [
    ('TARGET_CODE=81', 'TARGET_CODE=82'),
    ('SOURCE_SHA=e475b8476e99a9230683dbbf6ec266235960ed5b', 'SOURCE_SHA=0d81793eabf465716a4fe36038d143b11220667f'),
    ('SOURCE_RUN_ID=32849057694', 'SOURCE_RUN_ID=32875201581'),
    ('ARTIFACT_ID=9563625638', 'ARTIFACT_ID=9573716441'),
    ('EXPECTED_SHA=6e08dc974281cc7b5428d22cf406179447cdeb95443dc19fa1db2b4d32344913', 'EXPECTED_SHA=7018977f28d09434de27e6c6e90a7a51ec11c77831285d7e466c7aeeeeef9ee2'),
    ('EXPECTED_SIZE=13147013', 'EXPECTED_SIZE=13179781'),
    ('PREV_CODE=80', 'PREV_CODE=81'),
    ('PREV_SHA=37cadd74088179f1e17872c7474622681941cc5f546807cea769517d9f98b017', 'PREV_SHA=6e08dc974281cc7b5428d22cf406179447cdeb95443dc19fa1db2b4d32344913'),
    ('PREV_SIZE=13130629', 'PREV_SIZE=13147013'),
    ('VISUAL_RUN=32860235560', 'VISUAL_RUN=32906107089'),
    ('VISUAL_ARTIFACT=9568028848', 'VISUAL_ARTIFACT=9584898561'),
]
for old, new in replacements:
    assert old in src, old
    src = src.replace(old, new, 1)

# The live GAS route is Beta75. Upgrade it atomically to Beta76 while retaining
# older-route fallbacks for recovery from a stale deployment.
old_compat = '''compat73="    if (action === 'update_check') return ppJson_(ppBeta73UpdateCheckCompat_(ppUpdateCheck_(body)));"
compat74="    if (action === 'update_check') return ppJson_(ppBeta74UpdateCheckCompat_(ppUpdateCheck_(body)));"
compat75="    if (action === 'update_check') return ppJson_(ppBeta76UpdateCheckCompat_(ppUpdateCheck_(body)));"
if compat75 not in s:
    if compat74 in s: s=s.replace(compat74,compat75,1)
    elif compat73 in s: s=s.replace(compat73,compat75,1)
    else:
        assert s.count(plain)==1, 'update_check route anchor drift'
        s=s.replace(plain,compat75,1)'''
new_compat = '''compat73="    if (action === 'update_check') return ppJson_(ppBeta73UpdateCheckCompat_(ppUpdateCheck_(body)));"
compat74="    if (action === 'update_check') return ppJson_(ppBeta74UpdateCheckCompat_(ppUpdateCheck_(body)));"
compat75="    if (action === 'update_check') return ppJson_(ppBeta75UpdateCheckCompat_(ppUpdateCheck_(body)));"
compat76="    if (action === 'update_check') return ppJson_(ppBeta76UpdateCheckCompat_(ppUpdateCheck_(body)));"
if compat76 not in s:
    if compat75 in s: s=s.replace(compat75,compat76,1)
    elif compat74 in s: s=s.replace(compat74,compat76,1)
    elif compat73 in s: s=s.replace(compat73,compat76,1)
    else:
        assert s.count(plain)==1, 'update_check route anchor drift'
        s=s.replace(plain,compat76,1)'''
assert old_compat in src
src = src.replace(old_compat, new_compat, 1)
src = src.replace('assert compat75 in s and helper_sig in s', 'assert compat76 in s and helper_sig in s', 1)

src = src.replace(
    "if(version==='0.4.2-beta.76') out.version_code=81;",
    "if(version==='0.4.2-beta.76') out.version_code=82;",
    1,
)
src = src.replace(
    "else if(version==='0.4.2-beta.75' && (out.version_code===undefined || out.version_code===null)) out.version_code=80;",
    "else if(version==='0.4.2-beta.75' && (out.version_code===undefined || out.version_code===null)) out.version_code=81;",
    1,
)
src = src.replace('.version_code==81 and .sha256==$h', '.version_code==82 and .sha256==$h', 1)
src = src.replace('((.version_code // 81)==81)', '((.version_code // 82)==82)', 1)
src = src.replace('version_code:81,package:', 'version_code:82,package:', 1)

old_visual = 'and .visual.android_build_or_sign_in_visual==false and .human_inspection["320x568"].no_wrong_route_loading_crop_overlap==true and .human_inspection["360x640"].no_wrong_route_loading_crop_overlap==true and .human_inspection["480x800"].no_wrong_route_loading_crop_overlap==true and .human_inspection["320x568"].pda_exchange_two_explicit_actions==true and .human_inspection["360x640"].pda_exchange_two_explicit_actions==true and .human_inspection["480x800"].pda_exchange_two_explicit_actions==true and .human_inspection["480x800"].add_dialog_correct==true'
new_visual = 'and .visual.android_build_or_sign_in_visual==false and .human_inspection["320x568"].drop_receive_screen_correct==true and .human_inspection["360x640"].drop_receive_screen_correct==true and .human_inspection["480x800"].drop_receive_screen_correct==true and .human_inspection["320x568"].owner_crud_buttons_visible==true and .human_inspection["360x640"].owner_crud_buttons_visible==true and .human_inspection["480x800"].owner_crud_buttons_visible==true and .human_inspection["320x568"].keyboard_qr_not_obscured==true and .human_inspection["360x640"].keyboard_qr_not_obscured==true and .human_inspection["480x800"].keyboard_qr_not_obscured==true and .human_inspection["320x568"].add_clear_actions_visible==true and .human_inspection["360x640"].add_clear_actions_visible==true and .human_inspection["480x800"].add_clear_actions_visible==true and .human_inspection["320x568"].no_wrong_route_loading_crop_overlap==true and .human_inspection["360x640"].no_wrong_route_loading_crop_overlap==true and .human_inspection["480x800"].no_wrong_route_loading_crop_overlap==true'
assert old_visual in src
src = src.replace(old_visual, new_visual, 1)

src = src.replace(
    '.candidate_run_id==32849057694 and .candidate_artifact_id==9563625638 and .locked_package=="vn.pickpack1291.app.beta.publicbeta" and .locked_signer_sha256=="d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e" and .visual_receipt_commit=="007795a656fa14236ed766b164ca80bb5872fb32" and .final_visual_run_id==32860235560 and .final_visual_artifact_id==9568028848',
    '.candidate_run_id==32875201581 and .candidate_artifact_id==9573716441 and .locked_package=="vn.pickpack1291.app.beta.publicbeta" and .locked_signer_sha256=="d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e" and .visual_receipt_commit=="aa3123d3b0c20230f441c3db9aaf9d516c9e481e" and .final_visual_run_id==32906107089 and .final_visual_artifact_id==9584898561',
    1,
)

match = re.search(r'notes=".*?"\nhelper=f\'\'\'', src, flags=re.S)
assert match
notes = 'notes="• Nhận hàng rớt: chọn Vị trí; OWNER có Tạo / Sửa / Xóa.\\\\n• Scan QR tự tách DO và Số kiện; vẫn cho nhập tay khi QR sai.\\\\n• Thêm thông tin ghi trực tiếp Google Apps Script / Google Sheet với idempotency và readback.\\\\n• Xóa toàn bộ chỉ dành cho superadmin, giữ nguyên header, tab, quyền và danh sách Vị trí."\nhelper=f\'\'\''
src = src[:match.start()] + notes + src[match.end():]

src = src.replace(
    'superseded_live_sha256:"37cadd74088179f1e17872c7474622681941cc5f546807cea769517d9f98b017"',
    'superseded_live_sha256:"6e08dc974281cc7b5428d22cf406179447cdeb95443dc19fa1db2b4d32344913"',
    1,
)

# Initial attempt plus no more than two transient retries.
src = src.replace('for i in 1 2 3 4 5 6; do', 'for i in 1 2 3; do', 1)
src = src.replace('for i in 1 2 3 4 5 6 7 8; do', 'for i in 1 2 3; do', 1)

# Add authenticated Drive metadata/checksum readback beside the already proven
# public and Drive-byte SHA/size checks.
anchor = '''test "$(stat -c '%s' /tmp/beta76-drive.apk)" = "$EXPECTED_SIZE"

curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL"'''
insertion = '''test "$(stat -c '%s' /tmp/beta76-drive.apk)" = "$EXPECTED_SIZE"
curl -fsSL --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://www.googleapis.com/drive/v3/files/$DRIVE_ID?fields=id,name,mimeType,size,modifiedTime" > "$E/drive-metadata.json"
jq -e --arg id "$DRIVE_ID" --arg name "$APK_NAME" --argjson size "$EXPECTED_SIZE" \
  '.id==$id and .name==$name and .mimeType=="application/vnd.android.package-archive" and (.size|tonumber)==$size' "$E/drive-metadata.json" >/dev/null
curl -fsSL -L --connect-timeout 15 --max-time 30 \
  "https://drive.usercontent.google.com/download?id=$SUM_ID&export=download&confirm=t" -o "$E/drive-checksum.txt"
grep -qx "$EXPECTED_SHA  $APK_NAME" "$E/drive-checksum.txt"

curl -fsSL --connect-timeout 15 --max-time 30 -H 'content-type: application/json' "$GAS_URL"'''
assert anchor in src
src = src.replace(anchor, insertion, 1)

for stale in (
    '32849057694', '9563625638', '32860235560', '9568028848',
    'e475b8476e99a9230683dbbf6ec266235960ed5b',
    '37cadd74088179f1e17872c7474622681941cc5f546807cea769517d9f98b017',
    '007795a656fa14236ed766b164ca80bb5872fb32',
):
    assert stale not in src, stale
for forbidden in (
    'assembleBeta', 'assembleStable', 'apksigner', 'jarsigner',
    'signingConfig', 'refs/heads/main', 'stable-release',
):
    assert forbidden not in src, forbidden
for required in (
    'TARGET_VERSION=0.4.2-beta.76',
    'TARGET_CODE=82',
    'SOURCE_RUN_ID=32875201581',
    'ARTIFACT_ID=9573716441',
    'EXPECTED_SHA=7018977f28d09434de27e6c6e90a7a51ec11c77831285d7e466c7aeeeeef9ee2',
    'EXPECTED_SIZE=13179781',
    'PREV_VERSION=0.4.2-beta.75',
    'PREV_CODE=81',
    'PREV_SIZE=13147013',
    'VISUAL_RUN=32906107089',
    'VISUAL_ARTIFACT=9584898561',
    'ops/beta76-release-result.json',
    'ppBeta76UpdateCheckCompat_',
    'aa3123d3b0c20230f441c3db9aaf9d516c9e481e',
):
    assert required in src, required

Path(sys.argv[2]).write_text(src, encoding='utf-8')
PY

bash -n "$TMP"
if [[ "${BETA76_MATERIALIZE_ONLY:-0}" == "1" ]]; then
  printf '%s\n' "$TMP"
  exit 0
fi
exec bash "$TMP"
