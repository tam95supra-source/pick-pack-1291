#!/usr/bin/env bash
set -Eeuo pipefail

# Materialize the proven Beta76 exact-byte publisher, then advance only the
# locked BETA identity and OTA compatibility adapter. This path never builds,
# signs, publishes Stable, moves main, or changes Service/authority.
BASE_SHA=1af38202aec4b60ed049a803d4109f403fb27340
BASE_URL="https://raw.githubusercontent.com/${GITHUB_REPOSITORY:-tam95supra-source/pick-pack-1291}/${BASE_SHA}/tools/publish_beta76_ota.sh"
ORIG=/tmp/publish_beta76_ota_locked.sh
BASE=/tmp/publish_beta76_ota_materialized_for_beta77.sh
TMP=/tmp/publish_beta77_ota_materialized.sh

curl -fsSL --connect-timeout 15 --max-time 30 "$BASE_URL" -o "$ORIG"
BASE_PATH=$(BETA76_MATERIALIZE_ONLY=1 bash "$ORIG")
cp "$BASE_PATH" "$BASE"

python3 - "$BASE" "$TMP" <<'PY'
from pathlib import Path
import re
import sys

src = Path(sys.argv[1]).read_text(encoding='utf-8')

src = src.replace('beta76', 'beta77').replace('Beta76', 'Beta77')
src = src.replace('0.4.2-beta.76', '__BETA77_TARGET__')
src = src.replace('0.4.2-beta.75', '0.4.2-beta.76')
src = src.replace('__BETA77_TARGET__', '0.4.2-beta.77')

replacements = [
    ('TARGET_CODE=82', 'TARGET_CODE=83'),
    ('SOURCE_SHA=0d81793eabf465716a4fe36038d143b11220667f', 'SOURCE_SHA=43579d1f7f01816cddbdbbcce0a2f19d95d16d91'),
    ('SOURCE_RUN_ID=32875201581', 'SOURCE_RUN_ID=32953924512'),
    ('ARTIFACT_ID=9573716441', 'ARTIFACT_ID=9601304499'),
    ('EXPECTED_SHA=7018977f28d09434de27e6c6e90a7a51ec11c77831285d7e466c7aeeeeef9ee2', 'EXPECTED_SHA=6ce7838f6f0725ca98b4f3d9237d38aec60092f4488b2795a32ae3f9d24371fb'),
    ('EXPECTED_SIZE=13179781', 'EXPECTED_SIZE=13196165'),
    ('PREV_CODE=81', 'PREV_CODE=82'),
    ('PREV_SHA=6e08dc974281cc7b5428d22cf406179447cdeb95443dc19fa1db2b4d32344913', 'PREV_SHA=7018977f28d09434de27e6c6e90a7a51ec11c77831285d7e466c7aeeeeef9ee2'),
    ('PREV_SIZE=13147013', 'PREV_SIZE=13179781'),
    ('VISUAL_RUN=32906107089', 'VISUAL_RUN=32960147493'),
    ('VISUAL_ARTIFACT=9584898561', 'VISUAL_ARTIFACT=9603638990'),
    ('aa3123d3b0c20230f441c3db9aaf9d516c9e481e', '847378116153befe7b10a29951df43913e864636'),
]
for old, new in replacements:
    assert old in src, old
    src = src.replace(old, new)

old_compat = '''compat73="    if (action === 'update_check') return ppJson_(ppBeta73UpdateCheckCompat_(ppUpdateCheck_(body)));"
compat74="    if (action === 'update_check') return ppJson_(ppBeta74UpdateCheckCompat_(ppUpdateCheck_(body)));"
compat75="    if (action === 'update_check') return ppJson_(ppBeta75UpdateCheckCompat_(ppUpdateCheck_(body)));"
compat76="    if (action === 'update_check') return ppJson_(ppBeta77UpdateCheckCompat_(ppUpdateCheck_(body)));"
if compat76 not in s:
    if compat75 in s: s=s.replace(compat75,compat76,1)
    elif compat74 in s: s=s.replace(compat74,compat76,1)
    elif compat73 in s: s=s.replace(compat73,compat76,1)
    else:
        assert s.count(plain)==1, 'update_check route anchor drift'
        s=s.replace(plain,compat76,1)'''
new_compat = '''compat73="    if (action === 'update_check') return ppJson_(ppBeta73UpdateCheckCompat_(ppUpdateCheck_(body)));"
compat74="    if (action === 'update_check') return ppJson_(ppBeta74UpdateCheckCompat_(ppUpdateCheck_(body)));"
compat75="    if (action === 'update_check') return ppJson_(ppBeta75UpdateCheckCompat_(ppUpdateCheck_(body)));"
compat76="    if (action === 'update_check') return ppJson_(ppBeta76UpdateCheckCompat_(ppUpdateCheck_(body)));"
compat77="    if (action === 'update_check') return ppJson_(ppBeta77UpdateCheckCompat_(ppUpdateCheck_(body)));"
if compat77 not in s:
    if compat76 in s: s=s.replace(compat76,compat77,1)
    elif compat75 in s: s=s.replace(compat75,compat77,1)
    elif compat74 in s: s=s.replace(compat74,compat77,1)
    elif compat73 in s: s=s.replace(compat73,compat77,1)
    else:
        assert s.count(plain)==1, 'update_check route anchor drift'
        s=s.replace(plain,compat77,1)'''
assert old_compat in src, 'beta77 compat anchor drift'
src = src.replace(old_compat, new_compat, 1)

# The inherited post-patch assertion still references variable compat76. Once
# the live Beta76 route is replaced by compat77, that assertion is necessarily
# false even though the Beta77 route/helper are correct.
legacy_compat_assert = 'assert compat76 in s and helper_sig in s'
assert src.count(legacy_compat_assert) == 1, f'compat final assertion count={src.count(legacy_compat_assert)}'
src = src.replace(legacy_compat_assert, 'assert compat77 in s and helper_sig in s', 1)

for old, new in [
    ("if(version==='0.4.2-beta.77') out.version_code=82;", "if(version==='0.4.2-beta.77') out.version_code=83;"),
    ("else if(version==='0.4.2-beta.76' && (out.version_code===undefined || out.version_code===null)) out.version_code=81;", "else if(version==='0.4.2-beta.76' && (out.version_code===undefined || out.version_code===null)) out.version_code=82;"),
    ('.version_code==82 and .sha256==$h', '.version_code==83 and .sha256==$h'),
    ('((.version_code // 82)==82)', '((.version_code // 83)==83)'),
    ('version_code:82,package:', 'version_code:83,package:'),
]:
    assert old in src, old
    src = src.replace(old, new)

src = src.replace(
    'superseded_live_sha256:"6e08dc974281cc7b5428d22cf406179447cdeb95443dc19fa1db2b4d32344913"',
    'superseded_live_sha256:"7018977f28d09434de27e6c6e90a7a51ec11c77831285d7e466c7aeeeeef9ee2"',
    1,
)

match = re.search(r'notes=".*?"\nhelper=f\'\'\'', src, flags=re.S)
assert match, 'release notes anchor missing'
notes = 'notes="• Nhận hàng Rớt: vị trí đúng, Chưa có vị trí khi rỗng; OWNER có Tạo / Sửa / Xóa.\\n• Quét QR nhân sự hiển thị dấu gạch thay null và giữ nguyên phiên PDA ACTIVE cùng ngày/xuyên ngày.\\n• Đổi / Trả PDA và luồng ra sớm hiển thị đúng; sửa ổn định màn trong lúc snapshot tài nguyên về nền."\nhelper=f\'\'\''
src = src[:match.start()] + notes + src[match.end():]

for old, new in (
    ('32875201581', '32953924512'),
    ('9573716441', '9601304499'),
    ('32906107089', '32960147493'),
    ('9584898561', '9603638990'),
    ('0d81793eabf465716a4fe36038d143b11220667f', '43579d1f7f01816cddbdbbcce0a2f19d95d16d91'),
    ('aa3123d3b0c20230f441c3db9aaf9d516c9e481e', '847378116153befe7b10a29951df43913e864636'),
):
    src = src.replace(old, new)

legacy_meta_tail = '.stable_publish=="FORBIDDEN" and .service_change=="NONE"'
beta77_meta_tail = '.stable_publish=="FORBIDDEN" and .authority_change=="NONE" and .gas_run==32932894375 and .gas_artifact==9593853159 and .service_run==32953215533 and .service_artifact==9600983380'
assert src.count(legacy_meta_tail) == 1, f'legacy candidate-meta gate count={src.count(legacy_meta_tail)}'
src = src.replace(legacy_meta_tail, beta77_meta_tail, 1)

for stale in (
    '32875201581', '9573716441', '32906107089', '9584898561',
    '0d81793eabf465716a4fe36038d143b11220667f',
    '6e08dc974281cc7b5428d22cf406179447cdeb95443dc19fa1db2b4d32344913',
    'aa3123d3b0c20230f441c3db9aaf9d516c9e481e',
):
    assert stale not in src, stale

for forbidden in (
    'assembleBeta', 'assembleStable', 'apksigner', 'jarsigner',
    'signingConfig', 'refs/heads/main', 'stable-release',
):
    assert forbidden not in src, forbidden

for required in (
    'TARGET_VERSION=0.4.2-beta.77',
    'TARGET_CODE=83',
    'SOURCE_SHA=43579d1f7f01816cddbdbbcce0a2f19d95d16d91',
    'SOURCE_RUN_ID=32953924512',
    'ARTIFACT_ID=9601304499',
    'EXPECTED_SHA=6ce7838f6f0725ca98b4f3d9237d38aec60092f4488b2795a32ae3f9d24371fb',
    'EXPECTED_SIZE=13196165',
    'PREV_VERSION=0.4.2-beta.76',
    'PREV_CODE=82',
    'PREV_SHA=7018977f28d09434de27e6c6e90a7a51ec11c77831285d7e466c7aeeeeef9ee2',
    'PREV_SIZE=13179781',
    'VISUAL_RUN=32960147493',
    'VISUAL_ARTIFACT=9603638990',
    '847378116153befe7b10a29951df43913e864636',
    'ops/beta77-release-result.json',
    'ppBeta77UpdateCheckCompat_',
    'assert compat77 in s and helper_sig in s',
    'authority_change=="NONE"',
    'gas_run==32932894375',
    'service_run==32953215533',
):
    assert required in src, required

Path(sys.argv[2]).write_text(src, encoding='utf-8')
PY

bash -n "$TMP"
if [[ "${BETA77_MATERIALIZE_ONLY:-0}" == "1" ]]; then
  printf '%s\n' "$TMP"
  exit 0
fi
exec bash "$TMP"
