#!/usr/bin/env python3
import hashlib, html, os, subprocess, time
from pathlib import Path

PKG='vn.pickpack1291.app.beta.publicbeta'
ACT='vn.pickpack1291.app.beta.OperationsActivity'
LAUNCHER='vn.pickpack1291.app.beta.FullBetaActivity'
APK=os.environ['APK']; EXPECTED_SHA=os.environ['EXPECTED_SHA']; EXPECTED_SIZE=int(os.environ['EXPECTED_SIZE'])
OUT=Path('/tmp/beta76-visual')
SIZES=[(320,568),(360,640),(480,800)]

def run(args,check=True,text=True,timeout=20): return subprocess.run(args,check=check,text=text,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
def adb(*args,check=True,text=True,timeout=20): return run(['adb',*args],check,text,timeout)
def rec(name,data): OUT.mkdir(parents=True,exist_ok=True); p=OUT/name; p.write_bytes(data) if isinstance(data,bytes) else p.write_text(str(data),encoding='utf-8')
def prefs(values):
    rows='\n'.join(f'<string name="{html.escape(k)}">{html.escape(str(v))}</string>' for k,v in values.items())
    return "<?xml version='1.0' encoding='utf-8' standalone='yes' ?>\n<map>\n"+rows+'\n</map>'
def verify_candidate():
    payload=Path(APK).read_bytes(); assert len(payload)==EXPECTED_SIZE,(len(payload),EXPECTED_SIZE); assert hashlib.sha256(payload).hexdigest()==EXPECTED_SHA
    rec('candidate.txt',f'sha256={EXPECTED_SHA}\nsize={EXPECTED_SIZE}\npackage={PKG}\ncandidate_run=32875201581\nartifact_id=9573716441\nandroid_build_or_sign=false\n')
def uid():
    adb('shell','am','force-stop',PKG,check=False); result=adb('shell','stat','-c','%u:%g',f'/data/user/0/{PKG}',check=False).stdout.strip()
    if ':' not in result:
        adb('shell','am','start','-W','-n',f'{PKG}/{LAUNCHER}',check=False); time.sleep(.8); adb('shell','am','force-stop',PKG,check=False); result=adb('shell','stat','-c','%u:%g',f'/data/user/0/{PKG}',check=False).stdout.strip()
    assert ':' in result,result; return result.split(':',1)
def seed():
    u,g=uid(); auth=OUT/'auth.xml'; OUT.mkdir(parents=True,exist_ok=True)
    auth.write_text(prefs({'token':'beta76-visual-offline-token','login_id':'tamnv2','display_name':'Nguyễn Văn Tâm','role':'SUPERADMIN','position':'superadmin','email':'tam95.supra@gmail.com'}),encoding='utf-8')
    dst=f'/data/user/0/{PKG}/shared_prefs/pick_pack_auth_session_v2.xml'; adb('push',str(auth),'/data/local/tmp/auth.xml'); adb('shell','mkdir','-p',f'/data/user/0/{PKG}/shared_prefs'); adb('shell','cp','/data/local/tmp/auth.xml',dst); adb('shell','chown',f'{u}:{g}',dst); adb('shell','chmod','600',dst)
def shot(name,w,h):
    data=adb('exec-out','screencap','-p',text=False).stdout; rec(name,data); assert data[:8]==b'\x89PNG\r\n\x1a\n'; got=(int.from_bytes(data[16:20],'big'),int.from_bytes(data[20:24],'big')); assert got==(w,h),(got,(w,h))
def ime_visible(tag):
    state=adb('shell','dumpsys','input_method',check=False).stdout; rec(f'{tag}-ime-state.txt',state); return 'mInputShown=true' in state or 'mIsInputViewShown=true' in state
def launch_business(tag):
    adb('shell','am','force-stop',PKG,check=False); seed(); adb('shell','am','start','-W','-n',f'{PKG}/{LAUNCHER}',check=False); time.sleep(.8)
    result=adb('shell','am','start','-W','-n',f'{PKG}/{ACT}','--es','module','BUSINESS','--es','login','tamnv2','--es','name','OWNER','--es','role','SUPERADMIN','--es','position','superadmin','--es','email','tam95.supra@gmail.com',check=False).stdout
    rec(f'{tag}-operations-start.txt',result); assert 'Permission Denial' not in result and 'Error type' not in result; time.sleep(.9)
def capture_case(w,h):
    tag=f'{w}x{h}'; adb('shell','wm','size',tag); adb('shell','wm','density','160'); time.sleep(.7); launch_business(tag); shot(f'{tag}-business.png',w,h)
    # mdpi: Nhận hàng Rớt is the second-row left card at the same dp coordinate on all required viewports.
    adb('shell','input','tap','90','300'); time.sleep(5.8); shot(f'{tag}-drop-top.png',w,h)
    act=adb('shell','dumpsys','activity','activities',check=False).stdout; rec(f'{tag}-activity.txt',act[-12000:]); assert PKG in act and 'OperationsActivity' in act
    # Scan QR center. Preserve focus until IME evidence exists.
    adb('shell','input','tap','160','198'); time.sleep(1.1)
    if not ime_visible(tag): adb('shell','input','tap','160','198'); time.sleep(1.1)
    assert ime_visible(tag),f'{tag}: Scan QR focus did not open IME'; shot(f'{tag}-keyboard.png',w,h)
    adb('shell','input','keyevent','4'); time.sleep(.6); shot(f'{tag}-drop-bottom.png',w,h)

def main():
    verify_candidate(); adb('wait-for-device'); adb('shell','svc','wifi','disable',check=False); adb('shell','svc','data','disable',check=False)
    for key in ('window_animation_scale','transition_animation_scale','animator_duration_scale'): adb('shell','settings','put','global',key,'0',check=False)
    for w,h in SIZES: capture_case(w,h)
    rec('matrix.json','{"status":"MATRIX_CAPTURED","candidate_run":32875201581,"artifact_id":9573716441,"sizes":["320x568","360x640","480x800"],"density":160,"android_build_or_sign":false,"requires_human_inspection":true}\n')
    print('BETA76_EXACT_VISUAL_MATRIX_CAPTURED')
if __name__=='__main__': main()
