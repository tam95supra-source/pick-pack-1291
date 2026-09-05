#!/usr/bin/env python3
from pathlib import Path

ops=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
gradle=Path('app/build.gradle.kts')
notes=Path('app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt')

s=ops.read_text(encoding='utf-8')
old='''        val current=frame.getChildAt(0)\n        if(current!=null&&displayedScreenState.isNotBlank()&&(displayedScreenState!=screenState||displayedModule!=module)){\n'''
new='''        val current=frame.getChildAt(0)\n        val employeeFrameStates=setOf("EMPLOYEE_LOADING","EMPLOYEE","EMPLOYEE_LOOKUP_ERROR")\n        val sameEmployeeFrame=displayedModule==module&&displayedScreenState in employeeFrameStates&&screenState in employeeFrameStates\n        if(current!=null&&displayedScreenState.isNotBlank()&&!sameEmployeeFrame&&(displayedScreenState!=screenState||displayedModule!=module)){\n'''
if s.count(old)!=1: raise SystemExit(f'SETSCREEN_ANCHOR_COUNT={s.count(old)}')
s=s.replace(old,new,1)
# Beta124 regression remains mandatory: no roster re-append from employee result renderer.
render=s[s.index('private fun renderEmployee(ctx: JSONObject'):s.index('private fun sameEmployeeContext')]
if 'addInlineCurrentShiftStaff(body)' in render: raise SystemExit('POST_SCAN_ROSTER_REGRESSION')
ops.write_text(s,encoding='utf-8')

g=gradle.read_text(encoding='utf-8')
for oldv,newv in [('versionCode = 130','versionCode = 131'),('versionName = "0.4.2-beta.124"','versionName = "0.4.2-beta.125"')]:
    if g.count(oldv)!=1: raise SystemExit(f'GRADLE_ANCHOR_COUNT {oldv}={g.count(oldv)}')
    g=g.replace(oldv,newv,1)
marker='// Beta124: QR scan result no longer appends the full current-shift roster; pre-scan/no-result roster remains available. Inherits Beta123 service recovery and OWNER UI scope; Stable unchanged.'
if marker not in g: raise SystemExit('BETA124_COMMENT_ANCHOR_MISSING')
g=g.replace(marker,'// Beta125: employee loading/result/error are one logical navigation frame; Back from scanned employee returns directly to the actual QR scan screen. Preserves Beta124 post-scan roster suppression. Stable unchanged.\n'+marker,1)
gradle.write_text(g,encoding='utf-8')

n=notes.read_text(encoding='utf-8')
if n.count('const val VERSION_NAME = "0.4.2-beta.124"')!=1: raise SystemExit('NOTES_VERSION_ANCHOR')
n=n.replace('const val VERSION_NAME = "0.4.2-beta.124"','const val VERSION_NAME = "0.4.2-beta.125"',1)
needle='''    private val current = listOf(\n        "Sau khi quét QR có kết quả chỉ hiển thị đúng nhân sự/phiên vừa quét; danh sách nhân sự trong ca chỉ còn ở màn trước khi quét hoặc luồng danh sách riêng.",'''
replacement='''    private val current = listOf(\n        "Sửa lịch sử điều hướng QR: màn đang xác nhận/kết quả nhân sự là cùng một bước, Back một lần quay đúng về màn quét trước đó, không mắc ở trạng thái tải trung gian.",\n        "Sau khi quét QR có kết quả chỉ hiển thị đúng nhân sự/phiên vừa quét; danh sách nhân sự trong ca chỉ còn ở màn trước khi quét hoặc luồng danh sách riêng.",'''
if n.count(needle)!=1: raise SystemExit('NOTES_LIST_ANCHOR')
n=n.replace(needle,replacement,1)
notes.write_text(n,encoding='utf-8')
print('beta125_navigation_frame_fix=PASS version=0.4.2-beta.125 code=131 post_scan_roster=ABSENT')
