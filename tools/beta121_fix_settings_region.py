#!/usr/bin/env python3
from pathlib import Path

p=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
s=p.read_text(encoding='utf-8')

pairs=[
    ('new changelog',
     'if(pendingUpdate!=null)addVersionChangelog(body,"THAY ĐỔI BẢN MỚI",pendingUpdate.version,pendingUpdate.notes)',
     'if(pendingUpdate!=null)addVersionChangelog(appRegion,"THAY ĐỔI BẢN MỚI",pendingUpdate.version,pendingUpdate.notes)'),
    ('current changelog',
     'addVersionChangelog(body,"THAY ĐỔI BẢN HIỆN TẠI",BuildConfig.VERSION_NAME,ReleaseNotes.currentText())',
     'addVersionChangelog(appRegion,"THAY ĐỔI BẢN HIỆN TẠI",BuildConfig.VERSION_NAME,ReleaseNotes.currentText())'),
]
for label,old,new in pairs:
    if old in s:
        if s.count(old)!=1:
            raise SystemExit(f'{label}: expected 1 old marker, got {s.count(old)}')
        s=s.replace(old,new,1)
    elif new not in s:
        raise SystemExit(f'{label}: neither old nor new marker found')

old='''        dialog=AlertDialog.Builder(this).setTitle(title).setView(host).setPositiveButton("ĐÓNG",null).create()
        dialog?.show()'''
new='''        val builder=AlertDialog.Builder(this).setTitle(title).setView(host).setPositiveButton("ĐÓNG",null)
        if(normalized=="SYNC")builder.setNeutralButton("ĐỒNG BỘ NGAY"){_,_->manualRefreshFromHeader(syncStatusText?:host)}
        dialog=builder.create()
        dialog?.show()'''
if old in s:
    if s.count(old)!=1:
        raise SystemExit(f'sync dialog: expected 1 old marker, got {s.count(old)}')
    s=s.replace(old,new,1)
elif new not in s:
    raise SystemExit('sync dialog: neither old nor new marker found')
p.write_text(s,encoding='utf-8')

c=Path('tools/beta121_owner_ui_pda_source_contract.py')
t=c.read_text(encoding='utf-8')
settings_marker='assert \'background=GradientDrawable().apply{setColor(Color.rgb(248,250,252))\' in ops\n'
settings_extra='assert ops.count(\'addVersionChangelog(appRegion,\') >= 2\nassert \'addVersionChangelog(body,"THAY ĐỔI BẢN HIỆN TẠI"\' not in ops\n'
if settings_extra.strip() not in t:
    if t.count(settings_marker)!=1:
        raise SystemExit('settings contract marker mismatch')
    t=t.replace(settings_marker,settings_marker+settings_extra,1)

sync_marker='assert "Thông tin mạng" in ops and "Thông tin đồng bộ" in ops and "Thông tin dịch vụ" in ops\n'
sync_extra='assert \'setNeutralButton("ĐỒNG BỘ NGAY")\' in ops and \'manualRefreshFromHeader(syncStatusText?:host)\' in ops\n'
if sync_extra.strip() not in t:
    if t.count(sync_marker)!=1:
        raise SystemExit('sync contract marker mismatch')
    t=t.replace(sync_marker,sync_marker+sync_extra,1)
c.write_text(t,encoding='utf-8')
print('BETA121_SETTINGS_SYNC_FIX_APPLIED')
