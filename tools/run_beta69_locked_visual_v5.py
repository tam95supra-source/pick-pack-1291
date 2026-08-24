#!/usr/bin/env python3
from pathlib import Path
src=Path('tools/run_beta69_locked_visual_v4.py').read_text(encoding='utf-8')
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

    # 1) Reconciliation warning + true blink evidence.
    adb('shell','settings','put','global','animator_duration_scale','1',check=False)
    launch_home(); rawshot(d,'01-home-warning-a'); time.sleep(.75); rawshot(d,'02-home-warning-b')

    # 2) All three status cards must expose detailed Vietnamese information.
    tapxy(W*0.17,87*scale); rawshot(d,'03-network-detail'); adb('shell','input','keyevent','4',check=False); time.sleep(.5)
    tapxy(W*0.50,87*scale); rawshot(d,'04-sync-detail'); adb('shell','input','keyevent','4',check=False); time.sleep(.5)
    tapxy(W*0.83,87*scale); rawshot(d,'05-service-detail'); adb('shell','input','keyevent','4',check=False); time.sleep(.5)

    # 3) PDA exchange layout; wait for cache/service fallback result, then validate swipe-back behavior visually.
    launch_home(); tapxy(W*0.75,218*scale,2.6); rawshot(d,'06-pda-exchange'); resumed_check(d+'-pda')
    swipe(5,H*0.50,W*0.82,H*0.50,460,1.0); rawshot(d,'07-pda-swipe-back-parent'); resumed_check(d+'-pda-swipe-back')

    # 4) History list and concrete detail card.
    launch_home(); tapxy(W*0.61,H-102*scale,1.1); rawshot(d,'08-history-list'); resumed_check(d+'-history-list')
    tapxy(W*0.50,255*scale,1.0); rawshot(d,'09-history-detail'); resumed_check(d+'-history-detail')
    swipe(5,H*0.50,W*0.82,H*0.50,460,1.0); rawshot(d,'10-history-swipe-back'); resumed_check(d+'-history-swipe-back')

    # 5) Scan employee and capture work-change timeline after scrolling it into view.
    launch_home(); tapxy(W*0.25,218*scale,.9)
    tapxy(W*0.50,151*scale,.25); adb('shell','input','text','42267',check=False); adb('shell','input','keyevent','66',check=False); time.sleep(1.8)
    rawshot(d,'11-session-header')
    swipe(W*0.50,H*0.73,W*0.50,H*0.34,520,1.0); rawshot(d,'12-session-timeline'); resumed_check(d+'-timeline')

    imgs=sorted((OUT/d).glob('*.png')); assert len(imgs)==12,(d,len(imgs))
    for f in imgs:
        x=f.read_bytes(); assert x[:8]==b'\x89PNG\r\n\x1a\n'; w,h=struct.unpack('>II',x[16:24]); assert (w,h)==wh,(f,(w,h),wh); assert len(x)>4000,(f,len(x))
    rows.append(f'{d}: screenshots=12 dimensions={W}x{H} package_resumed_evidence=RECORDED manual_visual_inspection=REQUIRED')
except Exception as e:
  record('failure.txt',repr(e)); record('logcat-tail.txt',adb('logcat','-d','-t','300',check=False).stdout); raise
record('runtime-summary.txt','\n'.join(rows)+'\n')
print('\n'.join(rows))
'''
exec(compile(prefix+suffix,'tools/run_beta69_locked_visual_v5.materialized.py','exec'),{'__name__':'__main__','__file__':'tools/run_beta69_locked_visual_v5.materialized.py'})
