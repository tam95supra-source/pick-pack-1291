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
    record('last-start.txt',r.stdout)
    time.sleep(2)

def tapxy(x,y,wait=.9):
    adb('shell','input','tap',str(int(x)),str(int(y)),check=False); time.sleep(wait)

def resumed_check(tag):
    t=adb('shell','dumpsys','activity','activities',check=False).stdout
    record(f'resumed-{tag}.txt','\n'.join(x for x in t.splitlines() if PKG in x)[-8000:])

matrix=[('320x568','160',(320,568)),('360x640','160',(360,640)),('480x800','240',(480,800))]
rows=[]
try:
  for size,density,wh in matrix:
    W,H=wh; scale=int(density)/160.0
    d=f'{size}x{density}'; (OUT/d).mkdir(exist_ok=True)
    adb('shell','wm','size',size); adb('shell','wm','density',density); time.sleep(1)

    # Home discrepancy warning: keep real animation enabled and capture two phases.
    adb('shell','settings','put','global','animator_duration_scale','1',check=False)
    launch_home(); rawshot(d,'01-home-warning-a'); time.sleep(.75); rawshot(d,'02-home-warning-b')

    # Network detail from top-left status card.
    tapxy(W*0.17,87*scale); rawshot(d,'03-network-detail'); resumed_check(d+'-network')
    adb('shell','input','keyevent','4',check=False); time.sleep(.7)

    # PDA exchange from top-right business card.
    launch_home(); tapxy(W*0.75,218*scale); rawshot(d,'04-pda-exchange'); resumed_check(d+'-pda')
    adb('shell','input','keyevent','4',check=False); time.sleep(.7); rawshot(d,'05-back-parent')

    # History tab and first visible history item/detail.
    launch_home(); tapxy(W*0.61,H-102*scale); time.sleep(1.0); rawshot(d,'06-history-list'); resumed_check(d+'-history-list')
    tapxy(W*0.50,154*scale); time.sleep(.9); rawshot(d,'07-history-detail'); resumed_check(d+'-history-detail')
    adb('shell','input','keyevent','4',check=False); time.sleep(.6)

    # Employee scan and in-shift timeline. QR card center, then scan field.
    launch_home(); tapxy(W*0.25,218*scale); time.sleep(.8)
    tapxy(W*0.50,151*scale,.25); adb('shell','input','text','42267',check=False); adb('shell','input','keyevent','66',check=False); time.sleep(1.6)
    rawshot(d,'08-session-timeline'); resumed_check(d+'-timeline')

    imgs=sorted((OUT/d).glob('*.png')); assert len(imgs)==8,(d,len(imgs))
    for f in imgs:
        x=f.read_bytes(); assert x[:8]==b'\x89PNG\r\n\x1a\n'; w,h=struct.unpack('>II',x[16:24]); assert (w,h)==wh,(f,(w,h),wh); assert len(x)>4000,(f,len(x))
    rows.append(f'{d}: screenshots=8 dimensions={W}x{H} package_resumed_evidence=RECORDED manual_visual_inspection=REQUIRED')
except Exception as e:
  record('failure.txt',repr(e))
  record('logcat-tail.txt',adb('logcat','-d','-t','300',check=False).stdout)
  raise
record('runtime-summary.txt','\n'.join(rows)+'\n')
print('\n'.join(rows))
'''
exec(compile(prefix+suffix,'tools/run_beta69_locked_visual_v5.materialized.py','exec'),{'__name__':'__main__','__file__':'tools/run_beta69_locked_visual_v5.materialized.py'})
