#!/usr/bin/env bash
set -Eeuo pipefail
BASE_SHA=85b58348209e97c93957d45275a2fc031c764d48
BASE_URL="https://raw.githubusercontent.com/${GITHUB_REPOSITORY:-tam95supra-source/pick-pack-1291}/${BASE_SHA}/tools/publish_beta74_ota.sh"
TMP=/tmp/publish_beta75_ota_materialized.sh
curl -fsSL --connect-timeout 15 --max-time 30 "$BASE_URL" -o "$TMP.base"
python3 - "$TMP.base" "$TMP" <<'PY'
from pathlib import Path
import re,sys
src=Path(sys.argv[1]).read_text(encoding='utf-8')
src=src.replace('beta74','beta75').replace('Beta74','Beta75')
repls=[
('TARGET_VERSION=0.4.2-beta.74','TARGET_VERSION=0.4.2-beta.75'),('TARGET_CODE=80','TARGET_CODE=81'),
('SOURCE_SHA=cfb4dbca116f7c47a598bc398bdbe1251ad2bad8','SOURCE_SHA=e475b8476e99a9230683dbbf6ec266235960ed5b'),
('SOURCE_RUN_ID=32842363597','SOURCE_RUN_ID=32849057694'),('ARTIFACT_ID=9561088652','ARTIFACT_ID=9563625638'),
('EXPECTED_SHA=37cadd74088179f1e17872c7474622681941cc5f546807cea769517d9f98b017','EXPECTED_SHA=6e08dc974281cc7b5428d22cf406179447cdeb95443dc19fa1db2b4d32344913'),
('EXPECTED_SIZE=13130629','EXPECTED_SIZE=13147013'),
('APK_NAME=pick-pack-1291-public-beta-0.4.2-beta.74.apk','APK_NAME=pick-pack-1291-public-beta-0.4.2-beta.75.apk'),
('SUM_NAME=SHA256SUMS-0.4.2-beta.74.txt','SUM_NAME=SHA256SUMS-0.4.2-beta.75.txt'),
('PREV_VERSION=0.4.2-beta.73','PREV_VERSION=0.4.2-beta.74'),('PREV_CODE=79','PREV_CODE=80'),
('PREV_SHA=ad037c1a17d245f90ead59539c5595cc5df6a568b8657ce636cc43d101175fd2','PREV_SHA=37cadd74088179f1e17872c7474622681941cc5f546807cea769517d9f98b017'),
('VISUAL_RUN=32842363597','VISUAL_RUN=32860235560'),('VISUAL_ARTIFACT=9561153695','VISUAL_ARTIFACT=9568028848')]
for old,new in repls:
    assert old in src,old; src=src.replace(old,new,1)
src=src.replace('0.4.2-beta.74','0.4.2-beta.75').replace('0.4.2-beta.73','0.4.2-beta.74').replace('0.4.2-beta.72','0.4.2-beta.73')
src=src.replace('PREV_VERSION=0.4.2-beta.75','PREV_VERSION=0.4.2-beta.74',1)
old='''compat73="    if (action === 'update_check') return ppJson_(ppBeta73UpdateCheckCompat_(ppUpdateCheck_(body)));"\ncompat74="    if (action === 'update_check') return ppJson_(ppBeta75UpdateCheckCompat_(ppUpdateCheck_(body)));"\nif compat74 not in s:\n    if compat73 in s: s=s.replace(compat73,compat74,1)\n    else:\n        assert s.count(plain)==1, 'update_check route anchor drift'\n        s=s.replace(plain,compat74,1)'''
new='''compat73="    if (action === 'update_check') return ppJson_(ppBeta73UpdateCheckCompat_(ppUpdateCheck_(body)));"\ncompat74="    if (action === 'update_check') return ppJson_(ppBeta74UpdateCheckCompat_(ppUpdateCheck_(body)));"\ncompat75="    if (action === 'update_check') return ppJson_(ppBeta75UpdateCheckCompat_(ppUpdateCheck_(body)));"\nif compat75 not in s:\n    if compat74 in s: s=s.replace(compat74,compat75,1)\n    elif compat73 in s: s=s.replace(compat73,compat75,1)\n    else:\n        assert s.count(plain)==1, 'update_check route anchor drift'\n        s=s.replace(plain,compat75,1)'''
assert old in src; src=src.replace(old,new,1)
src=src.replace('assert compat74 in s and helper_sig in s','assert compat75 in s and helper_sig in s',1)
src=src.replace("if(version==='0.4.2-beta.75') out.version_code=80;","if(version==='0.4.2-beta.75') out.version_code=81;",1)
src=src.replace("else if(version==='0.4.2-beta.74' && (out.version_code===undefined || out.version_code===null)) out.version_code=79;","else if(version==='0.4.2-beta.74' && (out.version_code===undefined || out.version_code===null)) out.version_code=80;",1)
src=src.replace('.version_code==80 and .sha256==$h','.version_code==81 and .sha256==$h',1)
src=src.replace('((.version_code // 80)==80)','((.version_code // 81)==81)',1)
src=src.replace('version_code:80,package:','version_code:81,package:',1)
old_vis='and .human_inspection["320x568"].nhat_ky_visible==true and .human_inspection["360x640"].nhat_ky_visible==true and .human_inspection["480x800"].nhat_ky_visible==true'
new_vis='and .visual.android_build_or_sign_in_visual==false and .human_inspection["320x568"].no_wrong_route_loading_crop_overlap==true and .human_inspection["360x640"].no_wrong_route_loading_crop_overlap==true and .human_inspection["480x800"].no_wrong_route_loading_crop_overlap==true and .human_inspection["320x568"].pda_exchange_two_explicit_actions==true and .human_inspection["360x640"].pda_exchange_two_explicit_actions==true and .human_inspection["480x800"].pda_exchange_two_explicit_actions==true and .human_inspection["480x800"].add_dialog_correct==true'
assert old_vis in src; src=src.replace(old_vis,new_vis,1)
idx=src.find('"$REQ" >/dev/null'); assert idx>=0; end=idx+len('"$REQ" >/dev/null')
extra='''\njq -e '.candidate_run_id==32849057694 and .candidate_artifact_id==9563625638 and .locked_package=="vn.pickpack1291.app.beta.publicbeta" and .locked_signer_sha256=="d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e" and .visual_receipt_commit=="007795a656fa14236ed766b164ca80bb5872fb32" and .final_visual_run_id==32860235560 and .final_visual_artifact_id==9568028848' "$REQ" >/dev/null'''
src=src[:end]+extra+src[end:]
m=re.search(r'notes=".*?"\nhelper=f\'\'\'',src,flags=re.S); assert m
notes='notes="• Đổi / Trả PDA: nút Đổi PDA và Trả PDA rõ ràng, hiển thị Serial và tình trạng.\\\\n• Phát lại User: chọn trực tiếp User đã dùng; User Pack hiển thị Bàn – User; hỗ trợ Không dùng hy1.outbound.\\\\n• Thêm / Sửa / Xóa theo ngữ cảnh; bàn Pack không khóa D1.\\\\n• Diễn biến trong ca hiển thị đúng trước → sau; thông tin phiên được rút gọn."\nhelper=f\'\'\''
src=src[:m.start()]+notes+src[m.end():]
src=src.replace('superseded_live_sha256:"ad037c1a17d245f90ead59539c5595cc5df6a568b8657ce636cc43d101175fd2"','superseded_live_sha256:"37cadd74088179f1e17872c7474622681941cc5f546807cea769517d9f98b017"',1)
needle='for i in 1 2 3; do'; assert src.count(needle)==2
src=src.replace(needle,'for i in 1 2 3 4 5 6; do',1).replace(needle,'for i in 1 2 3 4 5 6 7 8; do',1)
for stale in ('32842363597','9561088652','9561153695','cfb4dbca116f7c47a598bc398bdbe1251ad2bad8','ad037c1a17d245f90ead59539c5595cc5df6a568b8657ce636cc43d101175fd2'): assert stale not in src,stale
for forbidden in ('assembleBeta','assembleStable','apksigner','jarsigner','signingConfig','refs/heads/main','stable-release'): assert forbidden not in src,forbidden
for required in ('TARGET_VERSION=0.4.2-beta.75','TARGET_CODE=81','SOURCE_RUN_ID=32849057694','ARTIFACT_ID=9563625638','EXPECTED_SHA=6e08dc974281cc7b5428d22cf406179447cdeb95443dc19fa1db2b4d32344913','EXPECTED_SIZE=13147013','PREV_VERSION=0.4.2-beta.74','PREV_CODE=80','VISUAL_RUN=32860235560','VISUAL_ARTIFACT=9568028848','ops/beta75-release-result.json','ppBeta75UpdateCheckCompat_'): assert required in src,required
Path(sys.argv[2]).write_text(src,encoding='utf-8')
PY
bash -n "$TMP"
if [[ "${BETA75_MATERIALIZE_ONLY:-0}" == "1" ]]; then printf '%s\n' "$TMP"; exit 0; fi
exec bash "$TMP"
