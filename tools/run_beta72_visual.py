#!/usr/bin/env python3
from pathlib import Path

# Reuse the proven Beta71 real-emulator harness and change only Beta72-specific
# identity, fixture data, and owner-requested visual assertions.
src = Path(__file__).with_name('run_beta71_visual.py').read_text(encoding='utf-8')
src = src.replace("EXPECTED_VERSION='0.4.2-beta.71'", "EXPECTED_VERSION='0.4.2-beta.72'", 1)
src = src.replace("EXPECTED_CODE='77'", "EXPECTED_CODE='78'", 1)
src = src.replace("'day_revision':71", "'day_revision':72", 1)
src = src.replace("'master_revision':71", "'master_revision':72", 1)
src = src.replace("'revision':71", "'revision':72", 1)
src = src.replace("'beta71-visual-offline-token'", "'beta72-visual-offline-token'", 1)

src = src.replace(
    "'resource_assignments_v64':[{'assignment_id':'asg-pda','resource_type':'PDA','resource_id':'MT90-123456789','status':'ACTIVE'},{'assignment_id':'asg-pick','resource_type':'USER_PICK','resource_id':'user16','status':'ACTIVE'}]",
    "'resource_assignments_v64':[{'assignment_id':'asg-pda','resource_type':'PDA','resource_id':'MT90-123456789','status':'ACTIVE'}]",
    1,
)
src = src.replace(
    "{'mnv':'51001','full_name':'Trần Thị Lan','supplier':'NLV','main_position':'Pack','department':'Pickpack','site':'1291','warehouse':'HY1'}]",
    "{'mnv':'51001','full_name':'Trần Thị Lan','supplier':'NLV','main_position':'Pack','department':'Pickpack','site':'1291','warehouse':'HY1'},{'mnv':'52002','full_name':'Lê Văn Beta72','supplier':'NLV','main_position':'Pick','department':'Pickpack','site':'1291','warehouse':'HY1'}]",
    1,
)
src = src.replace(
    "'pack_bundles':[]",
    "'pack_bundles':[{'table':'D1','user_pack':'pack01'},{'table':'D1','user_pack':'pack02'},{'table':'D2','user_pack':'pack03'}]",
    1,
)

# Header refresh every 750 ms prevents Android 10 uiautomator from reaching an
# accessibility-idle window. Use the proven raw screenshot/coordinate path and
# leave semantic assertions to source gates + mandatory human pixel inspection.
old = '''    # 5) Employee/session screen.\n    launch_home(); tapxy(W*0.25,218*scale,.9)\n    tapxy(W*0.50,151*scale,.25); adb('shell','input','text','42267',check=False); adb('shell','input','keyevent','66',check=False); time.sleep(1.8)\n    rawshot(d,'11-session-header')\n    for _ in range(4):\n        swipe(W*0.92,H*0.58,W*0.92,H*0.18,560,.65)\n    rawshot(d,'12-session-timeline'); resumed_check(d+'-timeline')\n\n    imgs=sorted((OUT/d).glob('*.png')); assert len(imgs)==12,(d,len(imgs))\n    for f in imgs:\n        x=f.read_bytes(); assert x[:8]==b'\\x89PNG\\r\\n\\x1a\\n'; w,h=struct.unpack('>II',x[16:24]); assert (w,h)==wh,(f,(w,h),wh); assert len(x)>4000,(f,len(x))\n    rows.append(f'{d}: screenshots=12 dimensions={W}x{H} exact_beta71=PASS local_active_holder_fixture=MT90-123456789 remote_state=AIRPLANE manual_visual_inspection=REQUIRED')\n'''
new = '''    # 5) ACTIVE session summary: label:value layout + fixed-user fallback.\n    launch_home(); tapxy(W*0.25,218*scale,.9)\n    tapxy(W*0.50,151*scale,.25); adb('shell','input','text','42267',check=False); adb('shell','input','keyevent','66',check=False); time.sleep(1.8)\n    rawshot(d,'11-session-header-beta72')\n    for _ in range(4):\n        swipe(W*0.92,H*0.58,W*0.92,H*0.18,560,.65)\n    rawshot(d,'12-session-timeline'); resumed_check(d+'-timeline')\n\n    # 6) New-session Pick: two bounded scrolls put the mandatory PDA plus the\n    # complete User Pick + Phát lại row in even the 320x568 viewport.\n    launch_home(); tapxy(W*0.25,218*scale,.9)\n    tapxy(W*0.50,151*scale,.25); adb('shell','input','text','52002',check=False); adb('shell','input','keyevent','66',check=False); time.sleep(1.8)\n    for _ in range(2): swipe(W*0.92,H*0.78,W*0.92,H*0.34,430,.55)\n    rawshot(d,'13-entry-pick-mandatory-pda-user-replay-row'); resumed_check(d+'-entry-pick')\n\n    # 7) Reload, select the middle Pack segment, then use the same two-scroll\n    # window to show Bàn Pack and its bound User Pack + Phát lại row together.\n    launch_home(); tapxy(W*0.25,218*scale,.9)\n    tapxy(W*0.50,151*scale,.25); adb('shell','input','text','52002',check=False); adb('shell','input','keyevent','66',check=False); time.sleep(1.8)\n    tapxy(W*0.50,356*scale,.8)\n    for _ in range(2): swipe(W*0.92,H*0.78,W*0.92,H*0.34,430,.55)\n    rawshot(d,'14-entry-pack-table-bound-user-replay-row'); resumed_check(d+'-entry-pack')\n\n    imgs=sorted((OUT/d).glob('*.png')); assert len(imgs)==14,(d,len(imgs))\n    for f in imgs:\n        x=f.read_bytes(); assert x[:8]==b'\\x89PNG\\r\\n\\x1a\\n'; w,h=struct.unpack('>II',x[16:24]); assert (w,h)==wh,(f,(w,h),wh); assert len(x)>4000,(f,len(x))\n    rows.append(f'{d}: screenshots=14 dimensions={W}x{H} exact_beta72=PASS owner_five_fixes=HUMAN_GATE manual_visual_inspection=REQUIRED')\n'''
if old not in src:
    raise SystemExit('Beta71 visual action anchor drift')
src = src.replace(old, new, 1)
if 'exact_beta71=PASS' in src or "EXPECTED_VERSION='0.4.2-beta.71'" in src:
    raise SystemExit('stale Beta71 visual identity remains')
exec(compile(src, 'run_beta72_visual.materialized.py', 'exec'), {'__name__':'__main__', '__file__':str(Path(__file__).with_name('run_beta71_visual.py'))})
