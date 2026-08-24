#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'tools/apply_beta69_owner_six_fixes.py'
src=base.read_text()
start=src.find('# 3) Mismatched attendance reconciliation gets a prominent blinking warning; matching state stays calm.')
end=src.find('# 4) Professional PDA exchange presentation; active/session authority from Beta68 is untouched.',start)
if start<0 or end<0:
    raise SystemExit('Beta69 v1 attendance patch section missing')
replacement=r'''# 3) Live source uses one reconciliation button per shift. Blink only the shift button when Vào != Ra.
recon_button='val button=reconciliationButton("$shift – ${entered.size}/${exited.size}",entered.size==exited.size)'
recon_blink=recon_button+'\n            if(entered.size!=exited.size){button.contentDescription="Cảnh báo đối soát $shift chưa khớp: vào ${entered.size}, ra ${exited.size}";button.startAnimation(android.view.animation.AlphaAnimation(1f,0.28f).apply{duration=650L;repeatMode=android.view.animation.Animation.REVERSE;repeatCount=android.view.animation.Animation.INFINITE})}'
ops = replace_once(ops,recon_button,recon_blink,'Shift reconciliation blinking warning')

'''
src=src[:start]+replacement+src[end:]
# Update the v1 regression assertion to match the live shift-button implementation.
src=src.replace("assert 'CẢNH BÁO: Đối soát vào / ra ca chưa khớp' in ops and 'Animation.INFINITE' in ops", "assert 'Cảnh báo đối soát $shift chưa khớp' in ops and 'Animation.INFINITE' in ops")
ns={'__file__':str(base),'__name__':'__main__'}
exec(compile(src,str(base),'exec'),ns)
print('BETA69_OWNER_SIX_FIXES_V3_PASS')
