#!/usr/bin/env python3
from pathlib import Path
p=Path('app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt')
s=p.read_text(encoding='utf-8')
if 'const val VERSION_NAME = "0.4.2-beta.129"' in s:
    s=s.replace('const val VERSION_NAME = "0.4.2-beta.129"','const val VERSION_NAME = "0.4.2-beta.130"',1)
elif 'const val VERSION_NAME = "0.4.2-beta.130"' not in s:
    raise SystemExit('BETA130_RELEASE_NOTES_VERSION_ANCHOR_MISSING')
needle='        "Realtime: cập nhật theo phần thay đổi, không tải lại toàn bộ màn hình khi dữ liệu nền đồng bộ.",\n'
extra='        "Hiệu năng: diễn biến công việc trong ca chỉ thêm hoặc cập nhật đúng thẻ thay đổi, không dựng lại toàn bộ timeline.",\n'
if extra not in s:
    if needle not in s: raise SystemExit('BETA130_RELEASE_NOTE_ANCHOR_MISSING')
    s=s.replace(needle,needle+extra,1)
p.write_text(s,encoding='utf-8')
print('R5_BETA130_RELEASE_NOTES_PATCH=PASS')
