#!/usr/bin/env python3
from urllib.request import urlopen

# Reuse the last known-running Beta73 harness byte-for-byte and patch only
# the Settings semantic probe. The candidate APK remains external/immutable.
BASE_URL='https://raw.githubusercontent.com/tam95supra-source/pick-pack-1291/ebd95abf772ac4982b94d19c521a9861bc12da51/tools/run_beta73_visual.py'
with urlopen(BASE_URL,timeout=20) as r:
    base=r.read().decode('utf-8')

# Root cause from runtime probe #1: full recursive AccessibilityNodeInfo walk
# does not complete under the live header refresh. Query only the two unique
# Settings markers through the accessibility bridge; do not traverse children.
old_walk='StringBuilder sb=new StringBuilder();\\\\n      walk(root,sb);\\\\n      out.putString("stream","PP_UI_PROBE_BEGIN\\\\\\\\n"+sb.toString()+"PP_UI_PROBE_END");'
new_walk='StringBuilder sb=new StringBuilder();\\\\n      if(root!=null){\\\\n        if(root.findAccessibilityNodeInfosByText("ĐỔI MẬT KHẨU").size()>0) sb.append("ĐỔI MẬT KHẨU\\\\\\\\n");\\\\n        if(root.findAccessibilityNodeInfosByText("NHẬT KÝ").size()>0) sb.append("NHẬT KÝ\\\\\\\\n");\\\\n      }\\\\n      out.putString("stream","PP_UI_PROBE_BEGIN\\\\\\\\n"+sb.toString()+"PP_UI_PROBE_END");'
if base.count(old_walk)!=1:
    raise SystemExit(f'java semantic anchor drift: {base.count(old_walk)}')
base=base.replace(old_walk,new_walk,1)

old_probe="r=adb(\\'shell\\',\\'am\\',\\'instrument\\',\\'-w\\',UI_PROBE,check=False)"
new_probe=(
    "try:\\n"
    "        r=run([\\'adb\\',\\'shell\\',\\'am\\',\\'instrument\\',\\'-w\\',UI_PROBE],check=False,timeout=15)\\n"
    "    except subprocess.TimeoutExpired as exc:\\n"
    "        partial=exc.stdout.decode(errors=\\'replace\\') if isinstance(exc.stdout,bytes) else str(exc.stdout or \\'\\')\\n"
    "        evidence=f\\'PROBE_TIMEOUT tag={tag} timeout_seconds=15\\\\n{partial[-3000:]}\\'\\n"
    "        record(f\\'probe-{tag}-timeout.txt\\',evidence)\\n"
    "        adb(\\'shell\\',\\'am\\',\\'force-stop\\',\\'pp.visual.probe\\',check=False)\\n"
    "        raise AssertionError(evidence)\\n"
    "    "
)
if base.count(old_probe)!=1:
    raise SystemExit(f'probe anchor drift: {base.count(old_probe)}')
base=base.replace(old_probe,new_probe,1)

matrix_anchor="src=src.replace(marker,probe+'\\n'+marker,1)"
preflight_code="""
adb('shell','wm','size','320x568'); adb('shell','wm','density','160'); time.sleep(1)
pre='settings-probe-320'; (OUT/pre).mkdir(exist_ok=True)
adb('shell','am','force-stop',PKG,check=False)
r=adb('shell','am','start','-W','-n',f'{PKG}/{ACT}','--es','module','SETTINGS','--es','login','tamnv2','--es','name','Nguyen Van Tam','--es','role','ADMIN','--es','position','Chuyen vien Pick Pack 1291','--es','email','visual@example.invalid',check=False)
record('settings-preflight-start.txt',r.stdout); time.sleep(1.0); resumed_check('settings-preflight-route')
state=adb('shell','dumpsys','activity','activities',check=False).stdout
record('settings-preflight-route.txt',state[-8000:])
assert PKG in state and 'OperationsActivity' in state,'Settings route/activity missing at 320x568'
top=probe_text('settings-preflight-top')
assert 'ĐỔI MẬT KHẨU'.casefold() in top.casefold(),'Settings top marker missing at 320x568'
rawshot(pre,'settings-top')
for _ in range(5): swipe(160,568*0.70,160,568*0.25,430,.35)
low=probe_text('settings-preflight-lower')
assert 'NHẬT KÝ'.casefold() in low.casefold(),'Settings lower marker missing at 320x568'
rawshot(pre,'settings-lower')
record('settings-probe-320-PASS.txt','route=OperationsActivity module=SETTINGS markers=ĐỔI MẬT KHẨU,NHẬT KÝ result=PASS')
"""
replacement="preflight="+repr(preflight_code)+"\n"+"src=src.replace(marker,probe+'\\n'+preflight+'\\n'+marker,1)"
if base.count(matrix_anchor)!=1:
    raise SystemExit(f'matrix anchor drift: {base.count(matrix_anchor)}')
base=base.replace(matrix_anchor,replacement,1)

exec(compile(base,'run_beta73_visual.bounded-wrapper.py','exec'),{'__name__':'__main__','__file__':__file__})
