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

# Harness recovery: Turso organization/resource-scoped platform tokens may deny the
# account-wide /auth/validate endpoint with 403. Do not weaken the gate: allow only
# 200 or 403 here, then require the existing downstream org/database/capacity checks.
dr=Path('tools/cloud_dr_provider_preflight.sh')
u=dr.read_text(encoding='utf-8')
old_validate='http turso-validate "https://api.turso.tech/v1/auth/validate" "$TURSO_API_TOKEN"'
new_validate='''validate_code=$(curl -sS --connect-timeout 10 --max-time 30 -o "$OUT/turso-validate.json" -w '%{http_code}' \\
  -H "Authorization: Bearer $TURSO_API_TOKEN" -H 'Accept: application/json' \\
  "https://api.turso.tech/v1/auth/validate" || true)
case "$validate_code" in
  200) echo "turso_validate=PASS" ;;
  403)
    printf '{}\\n' > "$OUT/turso-validate.json"
    echo "turso_validate_scope=READ_DENIED continue_with_resource_scoped_proof=true"
    ;;
  *) echo "DR_PREFLIGHT_HTTP_FAILED:turso-validate:$validate_code" >&2; exit 52 ;;
esac'''
if old_validate in u:
    if u.count(old_validate)!=1:
        raise SystemExit(f'turso validate marker count={u.count(old_validate)}')
    u=u.replace(old_validate,new_validate,1)
elif new_validate not in u:
    raise SystemExit('turso validate harness marker missing')
dr.write_text(u,encoding='utf-8')

print('BETA121_SETTINGS_SYNC_DR_HARNESS_FIX_APPLIED')
