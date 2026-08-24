#!/usr/bin/env python3
from pathlib import Path
src=Path('tools/run_beta69_locked_visual_v4.py').read_text(encoding='utf-8')

old="""def dump(path):
    adb('shell','uiautomator','dump','/sdcard/window.xml',check=False); data=adb('exec-out','cat','/sdcard/window.xml',text=False).stdout
    Path(path).write_bytes(data); return ET.fromstring(data)
"""
new="""def dump(path):
    target='/data/local/tmp/beta69-window.xml'
    last=''
    for attempt in range(5):
        adb('shell','rm','-f',target,check=False)
        r=adb('shell','uiautomator','dump',target,check=False)
        last=r.stdout
        c=adb('exec-out','cat',target,check=False,text=False)
        data=c.stdout if isinstance(c.stdout,(bytes,bytearray)) else str(c.stdout).encode()
        if data.lstrip().startswith(b'<?xml') or data.lstrip().startswith(b'<hierarchy'):
            Path(path).write_bytes(data)
            return ET.fromstring(data)
        time.sleep(.5)
    diag=adb('shell','dumpsys','window','windows',check=False).stdout
    record('uiautomator-dump-failure.txt','uiautomator='+last+'\\nwindow='+diag[-12000:])
    raise RuntimeError('uiautomator hierarchy unavailable after retries: '+repr(last))
"""
if old not in src: raise SystemExit('v4 dump anchor missing')
src=src.replace(old,new,1)

old="""def screenshot(d,tag):
    data=adb('exec-out','screencap','-p',text=False).stdout; p=OUT/d/f'{tag}.png'; p.write_bytes(data)
    root=dump(OUT/d/f'{tag}.xml'); (OUT/d/f'{tag}.txt').write_text(all_text(root),encoding='utf-8')
def start_home():
    adb('shell','am','force-stop',PKG,check=False); r=adb('shell','am','start','-W','-n',f'{PKG}/{ACT}',check=False); record('last-start.txt',r.stdout); time.sleep(2); expect('Mạng'); expect('Đồng bộ'); expect('Dịch vụ')
"""
new="""def raw_screenshot(d,tag):
    data=adb('exec-out','screencap','-p',text=False).stdout; p=OUT/d/f'{tag}.png'; p.write_bytes(data)
def screenshot(d,tag):
    data=adb('exec-out','screencap','-p',text=False).stdout; p=OUT/d/f'{tag}.png'; p.write_bytes(data)
    root=dump(OUT/d/f'{tag}.xml'); (OUT/d/f'{tag}.txt').write_text(all_text(root),encoding='utf-8')
def start_home():
    adb('shell','am','force-stop',PKG,check=False); r=adb('shell','am','start','-W','-n',f'{PKG}/{ACT}',check=False); record('last-start.txt',r.stdout); time.sleep(2)
"""
if old not in src: raise SystemExit('v4 screenshot/start_home anchor missing')
src=src.replace(old,new,1)

old="""    reset_home(); expect('Ca 1'); screenshot(d,'01-home-warning-a'); time.sleep(.75); screenshot(d,'02-home-warning-b')
"""
new="""    adb('shell','settings','put','global','animator_duration_scale','1',check=False)
    reset_home(); raw_screenshot(d,'01-home-warning-a'); time.sleep(.75); raw_screenshot(d,'02-home-warning-b')
    if (OUT/d/'01-home-warning-a.png').read_bytes()==(OUT/d/'02-home-warning-b.png').read_bytes():
        time.sleep(.45); raw_screenshot(d,'02-home-warning-b')
    adb('shell','settings','put','global','animator_duration_scale','0',check=False)
    adb('shell','settings','put','global','window_animation_scale','0',check=False)
    adb('shell','settings','put','global','transition_animation_scale','0',check=False)
    time.sleep(.5); expect('Ca 1'); expect('Mạng'); expect('Đồng bộ'); expect('Dịch vụ')
"""
if old not in src: raise SystemExit('v4 matrix home anchor missing')
src=src.replace(old,new,1)

old="record('failure.txt',repr(e)+'\\n\\nUI:\\n'+(ui_text() if True else ''))"
new="\n  try: _ui=ui_text()\n  except Exception as _ue: _ui='<ui unavailable: '+repr(_ue)+'>'\n  record('failure.txt',repr(e)+'\\n\\nUI:\\n'+_ui)"
if old not in src: raise SystemExit('v4 failure anchor missing')
src=src.replace(old,new,1)

exec(compile(src,'tools/run_beta69_locked_visual_v5.materialized.py','exec'),{'__name__':'__main__','__file__':'tools/run_beta69_locked_visual_v5.materialized.py'})
