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
# Failure receipt must not recursively call a broken UI dump.
old2="record('failure.txt',repr(e)+'\\n\\nUI:\\n'+(ui_text() if True else ''))"
new2="\n  try: _ui=ui_text()\n  except Exception as _ue: _ui='<ui unavailable: '+repr(_ue)+'>'\n  record('failure.txt',repr(e)+'\\n\\nUI:\\n'+_ui)"
if old2 not in src: raise SystemExit('v4 failure anchor missing')
src=src.replace(old2,new2,1)
exec(compile(src,'tools/run_beta69_locked_visual_v5.materialized.py','exec'),{'__name__':'__main__','__file__':'tools/run_beta69_locked_visual_v5.materialized.py'})
