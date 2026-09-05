#!/usr/bin/env python3
from pathlib import Path

java=Path('tools/Beta83UiChecksInstrumentation.java')
matrix=Path('tools/beta83_verify_matrix.sh')
s=java.read_text(encoding='utf-8')

pre='''    clickText("Quét QR nhân sự",true,12000L);\n    waitText("Danh sách QR vào / ra",true,false,12000L);'''
pre_new='''    clickText("Quét QR nhân sự",true,12000L);\n    waitTextScrolling("Danh sách QR vào / ra",20000L);'''
if s.count(pre)!=1:
    raise SystemExit(f'PRE_SCAN_ANCHOR_COUNT={s.count(pre)}')
s=s.replace(pre,pre_new,1)

post='''    waitText("THÔNG TIN CA",true,false,10000L);\n\n    showTextOnScreen("Danh sách QR vào / ra",10000L);'''
post_new='''    waitText("THÔNG TIN CA",true,false,10000L);\n    require(findText("Danh sách QR vào / ra",true,false)==null,"POST_SCAN_ROSTER_MUST_BE_HIDDEN");\n    mark("post_scan_roster_hidden_beta124");\n    pressSystemBack();\n    waitText("QUÉT QR NHÂN SỰ",true,false,10000L);\n\n    showTextOnScreen("Danh sách QR vào / ra",10000L);'''
if s.count(post)!=1:
    raise SystemExit(f'POST_SCAN_ANCHOR_COUNT={s.count(post)}')
s=s.replace(post,post_new,1)
java.write_text(s,encoding='utf-8')

m=matrix.read_text(encoding='utf-8')
anchor='shift_quick_exit_dialog_beta113 inline_shift_staff_beta113'
replacement='shift_quick_exit_dialog_beta113 post_scan_roster_hidden_beta124 inline_shift_staff_beta113'
if m.count(anchor)!=1:
    raise SystemExit(f'MATRIX_FLAG_ANCHOR_COUNT={m.count(anchor)}')
m=m.replace(anchor,replacement,1)
matrix.write_text(m,encoding='utf-8')
print('beta124_verify_harness_patch=PASS pre_scan_scroll=PASS post_scan_hidden=PASS back_to_roster=PASS')
