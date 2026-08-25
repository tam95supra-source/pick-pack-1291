#!/usr/bin/env python3
from pathlib import Path
src=Path('tools/run_beta69_locked_visual_v4.py').read_text(encoding='utf-8')
repls={
    "EXPECTED_VERSION='0.4.2-beta.69'":"EXPECTED_VERSION='0.4.2-beta.70'",
    "EXPECTED_CODE='75'":"EXPECTED_CODE='76'",
    "EXPECTED_SHA='251530388165c7a9a8572053238b5d44b47a6747c5e94f270230e65ce68d4cda'":"EXPECTED_SHA='f4113bf8ffb330cd5ebf51f06a5fd211be04323546d28e4e04dec498d1d83899'",
    "'day_revision':69":"'day_revision':70",
    "'master_revision':69":"'master_revision':70",
    "'revision':69":"'revision':70",
    "'beta69-visual-offline-token'":"'beta70-visual-offline-token'",
}
for a,b in repls.items():
    if a not in src: raise SystemExit('fixture anchor missing: '+a)
    src=src.replace(a,b)
if 'matrix=[' not in src: raise SystemExit('v4 matrix anchor missing')
prefix=src.split('matrix=[',1)[0]
suffix=r'''
def rawshot(d,tag):
    data=adb('exec-out','screencap','-p',text=False).stdout
    p=OUT/d/f'{tag}.png'; p.write_bytes(data)
    assert data[:8]==b'\x89PNG\r\n\x1a\n', (d,tag,'not-png')

def launch_home():
    adb('shell','am','force-stop',PKG,check=False)
    r=adb('shell','am','start','-W','-n',f'{PKG}/{ACT}',check=False)
    record('last-start.txt',r.stdout); time.sleep(2)

def tapxy(x,y,wait=.9):
    adb('shell','input','tap',str(int(x)),str(int(y)),check=False); time.sleep(wait)

def resumed_check(tag):
    t=adb('shell','dumpsys','activity','activities',check=False).stdout
    lines='\n'.join(x for x in t.splitlines() if PKG in x)
    record(f'resumed-{tag}.txt',lines[-8000:])
    assert PKG in lines, tag+' package not present in activity state'

def swipe(x1,y1,x2,y2,ms=420,wait=.9):
    adb('shell','input','swipe',str(int(x1)),str(int(y1)),str(int(x2)),str(int(y2)),str(int(ms)),check=False); time.sleep(wait)

matrix=[('320x568','160',(320,568)),('360x640','160',(360,640)),('480x800','240',(480,800))]
rows=[]
try:
  for size,density,wh in matrix:
    W,H=wh; scale=int(density)/160.0
    d=f'{size}x{density}'; (OUT/d).mkdir(exist_ok=True)
    adb('shell','wm','size',size); adb('shell','wm','density',density); time.sleep(1)

    # 1) Home warning + blink evidence.
    adb('shell','settings','put','global','animator_duration_scale','1',check=False)
    launch_home(); rawshot(d,'01-home-warning-a'); time.sleep(.75); rawshot(d,'02-home-warning-b')

    # 2) Three status cards.
    tapxy(W*0.17,87*scale); rawshot(d,'03-network-detail'); adb('shell','input','keyevent','4',check=False); time.sleep(.5)
    tapxy(W*0.50,87*scale); rawshot(d,'04-sync-detail'); adb('shell','input','keyevent','4',check=False); time.sleep(.5)
    tapxy(W*0.83,87*scale); rawshot(d,'05-service-detail'); adb('shell','input','keyevent','4',check=False); time.sleep(.5)

    # 3) Critical Beta70 defect evidence: airplane/remote failure while local ACTIVE holder exists.
    launch_home(); tapxy(W*0.75,218*scale,2.6); rawshot(d,'06-pda-exchange-local-holder-offline'); resumed_check(d+'-pda')
    swipe(5,H*0.50,W*0.82,H*0.50,460,1.0); rawshot(d,'07-pda-swipe-back-parent'); resumed_check(d+'-pda-swipe-back')

    # 4) History list/detail.
    launch_home(); tapxy(W*0.61,H-102*scale,1.1); rawshot(d,'08-history-list'); resumed_check(d+'-history-list')
    tapxy(W*0.50,255*scale,1.0); rawshot(d,'09-history-detail'); resumed_check(d+'-history-detail')
    swipe(5,H*0.50,W*0.82,H*0.50,460,1.0); rawshot(d,'10-history-swipe-back'); resumed_check(d+'-history-swipe-back')

    # 5) Employee/session screen.
    launch_home(); tapxy(W*0.25,218*scale,.9)
    tapxy(W*0.50,151*scale,.25); adb('shell','input','text','42267',check=False); adb('shell','input','keyevent','66',check=False); time.sleep(1.8)
    rawshot(d,'11-session-header')
    swipe(W*0.50,H*0.73,W*0.50,H*0.34,520,1.0); rawshot(d,'12-session-timeline'); resumed_check(d+'-timeline')

    imgs=sorted((OUT/d).glob('*.png')); assert len(imgs)==12,(d,len(imgs))
    for f in imgs:
        x=f.read_bytes(); assert x[:8]==b'\x89PNG\r\n\x1a\n'; w,h=struct.unpack('>II',x[16:24]); assert (w,h)==wh,(f,(w,h),wh); assert len(x)>4000,(f,len(x))
    rows.append(f'{d}: screenshots=12 dimensions={W}x{H} exact_beta70=PASS local_active_holder_fixture=MT90-123456789 remote_state=AIRPLANE manual_visual_inspection=REQUIRED')
except Exception as e:
  record('failure.txt',repr(e)); record('logcat-tail.txt',adb('logcat','-d','-t','300',check=False).stdout); raise
record('runtime-summary.txt','\n'.join(rows)+'\n')
print('\n'.join(rows))
'''
exec(compile(prefix+suffix,'tools/run_beta70_locked_visual_v1.materialized.py','exec'),{'__name__':'__main__','__file__':'tools/run_beta70_locked_visual_v1.materialized.py'})
