#!/usr/bin/env bash
set -Eeuo pipefail
SRC=tools/Beta83UiChecksInstrumentation.java
BACKUP="$RUNNER_TEMP/Beta83UiChecksInstrumentation.java.orig"
cp "$SRC" "$BACKUP"
restore(){ cp "$BACKUP" "$SRC" 2>/dev/null || true; }
trap restore EXIT
python3 - "$SRC" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text(encoding='utf-8')
needle='    shot(tag+"-01-business");'
insert='''    shot(tag+"-01-business");
    clickTextScrolling("Nhận hàng Rớt",10000L);
    waitText("Thêm thông tin",true,true,10000L);
    waitText("Vị trí",true,false,10000L);
    shot(tag+"-01d-beta128-drop");
    try{ui.executeShellCommand("input keyevent 4").close();}catch(Exception ignored){}
    SystemClock.sleep(300L);
    waitText("Quét QR nhân sự",true,true,10000L);'''
count=s.count(needle)
if count!=2:
    raise SystemExit(f'DROP_VISUAL_BUSINESS_ANCHOR_COUNT:{count}')
s=s.replace(needle,insert)
p.write_text(s,encoding='utf-8')
PY
bash tools/build_beta83_verify_harness.sh
# build_beta83_verify_harness.sh already raises the 320 checks baseline by one for Beta125.
# This gate adds one Drop screenshot to each size, so align the ephemeral expected matrix only.
sed -i \
  -e 's/"320x568":((320,568),22)/"320x568":((320,568),23)/g' \
  -e 's/"360x640":((360,640),11)/"360x640":((360,640),12)/g' \
  -e 's/"480x800":((480,800),11)/"480x800":((480,800),12)/g' \
  tools/beta83_verify_matrix.sh
grep -Fq '"320x568":((320,568),23)' tools/beta83_verify_matrix.sh
grep -Fq '"360x640":((360,640),12)' tools/beta83_verify_matrix.sh
grep -Fq '"480x800":((480,800),12)' tools/beta83_verify_matrix.sh
echo BETA128_DROP_VISUAL_HARNESS_READY
