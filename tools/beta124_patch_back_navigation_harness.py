#!/usr/bin/env python3
from pathlib import Path
p=Path('tools/Beta83UiChecksInstrumentation.java')
s=p.read_text(encoding='utf-8')
helper='''  private void pressSystemBack(){\n    try{ui.executeShellCommand("input keyevent 4").close();}catch(Exception e){throw new IllegalStateException("BACK_KEYEVENT_FAILED",e);}\n    SystemClock.sleep(450L);\n  }\n'''
helper_new=helper+'''\n  private void invokeActivityBack(){\n    Activity a=currentActivity;\n    require(a!=null&&PKG.equals(a.getPackageName()),"CURRENT_ACTIVITY_MISSING_BACK");\n    runOnMainSync(new Runnable(){@Override public void run(){a.onBackPressed();}});\n    SystemClock.sleep(450L);\n  }\n'''
if s.count(helper)!=1: raise SystemExit(f'HELPER_COUNT={s.count(helper)}')
s=s.replace(helper,helper_new,1)
frag='''    require(findText("Danh sách QR vào / ra",true,false)==null,"POST_SCAN_ROSTER_MUST_BE_HIDDEN");\n    mark("post_scan_roster_hidden_beta124");\n    pressSystemBack();\n    waitText("QUÉT QR NHÂN SỰ",true,false,10000L);\n'''
frag_new='''    require(findText("Danh sách QR vào / ra",true,false)==null,"POST_SCAN_ROSTER_MUST_BE_HIDDEN");\n    mark("post_scan_roster_hidden_beta124");\n    invokeActivityBack();\n    waitText("QUÉT QR NHÂN SỰ",true,false,10000L);\n    mark("post_scan_activity_back_beta124");\n'''
if s.count(frag)!=1: raise SystemExit(f'FRAG_COUNT={s.count(frag)}')
s=s.replace(frag,frag_new,1)
p.write_text(s,encoding='utf-8')

m=Path('tools/beta83_verify_matrix.sh')
t=m.read_text(encoding='utf-8')
needle='post_scan_roster_hidden_beta124 inline_shift_staff_beta113'
repl='post_scan_roster_hidden_beta124 post_scan_activity_back_beta124 inline_shift_staff_beta113'
if t.count(needle)!=1: raise SystemExit(f'MATRIX_COUNT={t.count(needle)}')
t=t.replace(needle,repl,1)
m.write_text(t,encoding='utf-8')
print('beta124_back_navigation_harness=PASS')
