#!/usr/bin/env python3
from pathlib import Path
p=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
s=p.read_text(encoding='utf-8')
old1='if(pendingUpdate!=null)addVersionChangelog(body,"THAY ĐỔI BẢN MỚI",pendingUpdate.version,pendingUpdate.notes)'
new1='if(pendingUpdate!=null)addVersionChangelog(appRegion,"THAY ĐỔI BẢN MỚI",pendingUpdate.version,pendingUpdate.notes)'
old2='addVersionChangelog(body,"THAY ĐỔI BẢN HIỆN TẠI",BuildConfig.VERSION_NAME,ReleaseNotes.currentText())'
new2='addVersionChangelog(appRegion,"THAY ĐỔI BẢN HIỆN TẠI",BuildConfig.VERSION_NAME,ReleaseNotes.currentText())'
for label,old,new in [('new changelog',old1,new1),('current changelog',old2,new2)]:
    if s.count(old)!=1: raise SystemExit(f'{label}: expected 1 marker, got {s.count(old)}')
    s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')

c=Path('tools/beta121_owner_ui_pda_source_contract.py')
t=c.read_text(encoding='utf-8')
marker='assert \'background=GradientDrawable().apply{setColor(Color.rgb(248,250,252))\' in ops\n'
extra='assert ops.count(\'addVersionChangelog(appRegion,\') >= 2\nassert \'addVersionChangelog(body,"THAY ĐỔI BẢN HIỆN TẠI"\' not in ops\n'
if extra.strip() not in t:
    if t.count(marker)!=1: raise SystemExit('contract marker mismatch')
    t=t.replace(marker,marker+extra,1)
c.write_text(t,encoding='utf-8')
print('BETA121_SETTINGS_REGION_FIX_APPLIED')
