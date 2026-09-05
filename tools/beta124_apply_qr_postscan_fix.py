#!/usr/bin/env python3
from pathlib import Path

root=Path(__file__).resolve().parents[1]
ops_path=root/'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'
gradle_path=root/'app/build.gradle.kts'
notes_path=root/'app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt'

ops=ops_path.read_text(encoding='utf-8')
start=ops.index('    private fun renderEmployee(ctx: JSONObject, masters: JSONObject?) {')
end=ops.index('    private fun sameEmployeeContext', start)
segment=ops[start:end]
needle='        addInlineCurrentShiftStaff(body)\n'
if segment.count(needle)!=1:
    raise SystemExit(f'RENDER_EMPLOYEE_INLINE_ROSTER_ANCHOR_COUNT:{segment.count(needle)}')
segment=segment.replace(needle,'',1)
ops=ops[:start]+segment+ops[end:]
# Pre-scan/no-result list must remain available; only the rendered scan result loses the roster.
if 'val preScanStaff=column(bg);addInlineCurrentShiftStaff(preScanStaff);body.addView(preScanStaff,matchWrap())' not in ops:
    raise SystemExit('PRESCAN_ROSTER_MISSING')
ops_path.write_text(ops,encoding='utf-8')

gradle=gradle_path.read_text(encoding='utf-8')
for old,new in [
    ('versionCode = 129','versionCode = 130'),
    ('versionName = "0.4.2-beta.123"','versionName = "0.4.2-beta.124"'),
]:
    if gradle.count(old)!=1:
        raise SystemExit('GRADLE_ANCHOR_COUNT:'+old+':'+str(gradle.count(old)))
    gradle=gradle.replace(old,new,1)
marker='// Beta123: owner UI/realtime recovery scope:'
if marker not in gradle:
    raise SystemExit('BETA123_COMMENT_ANCHOR_MISSING')
gradle=gradle.replace(marker,'// Beta124: QR scan result no longer appends the full current-shift roster; pre-scan/no-result roster remains available. Inherits Beta123 service recovery and OWNER UI scope; Stable unchanged.\n'+marker,1)
gradle_path.write_text(gradle,encoding='utf-8')

notes=notes_path.read_text(encoding='utf-8')
if notes.count('const val VERSION_NAME = "0.4.2-beta.123"')!=1:
    raise SystemExit('RELEASE_NOTES_VERSION_ANCHOR')
notes=notes.replace('const val VERSION_NAME = "0.4.2-beta.123"','const val VERSION_NAME = "0.4.2-beta.124"',1)
list_anchor='    private val current = listOf(\n'
if list_anchor not in notes:
    raise SystemExit('RELEASE_NOTES_LIST_ANCHOR')
notes=notes.replace(list_anchor,list_anchor+'        "Sau khi quét QR có kết quả chỉ hiển thị đúng nhân sự/phiên vừa quét; danh sách nhân sự trong ca chỉ còn ở màn trước khi quét hoặc luồng danh sách riêng.",\n',1)
notes_path.write_text(notes,encoding='utf-8')

# Contract: the OWNER-superseded behavior must be absent from the result renderer but present pre-scan.
ops2=ops_path.read_text(encoding='utf-8')
render=ops2[ops2.index('    private fun renderEmployee(ctx: JSONObject, masters: JSONObject?) {'):ops2.index('    private fun sameEmployeeContext')]
if 'addInlineCurrentShiftStaff(body)' in render:
    raise SystemExit('POST_SCAN_ROSTER_STILL_PRESENT')
if 'addInlineCurrentShiftStaff(preScanStaff)' not in ops2:
    raise SystemExit('PRESCAN_ROSTER_REMOVED')
print('beta124_qr_postscan_fix=PASS post_scan_roster=ABSENT pre_scan_roster=PRESENT version=0.4.2-beta.124 code=130')
