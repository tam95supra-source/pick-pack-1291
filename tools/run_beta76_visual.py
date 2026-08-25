#!/usr/bin/env python3
import hashlib, html, os, subprocess, time
from pathlib import Path

PKG='vn.pickpack1291.app.beta.publicbeta'
ACT='vn.pickpack1291.app.beta.OperationsActivity'
LAUNCHER='vn.pickpack1291.app.beta.FullBetaActivity'
APK=os.environ['APK']
EXPECTED_SHA=os.environ['EXPECTED_SHA']
EXPECTED_SIZE=int(os.environ['EXPECTED_SIZE'])
OUT=Path('/tmp/beta76-visual')
ADB_TIMEOUT=20

def run(args,check=True,text=True,timeout=ADB_TIMEOUT):
    return subprocess.run(args,check=check,text=text,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
def adb(*args,check=True,text=True,timeout=ADB_TIMEOUT):
    return run(['adb',*args],check=check,text=text,timeout=timeout)
def rec(name,data):
    OUT.mkdir(parents=True,exist_ok=True);p=OUT/name;p.write_bytes(data) if isinstance(data,bytes) else p.write_text(str(data),encoding='utf-8')
def prefs_xml(values):
    rows=["<?xml version='1.0' encoding='utf-8' standalone='yes' ?>",'<map>']
    for k,v in values.items():rows.append(f'<string name="{html.escape(k)}">{html.escape(str(v))}</string>')
    rows.append('</map>');return '\n'.join(rows)
def verify_candidate():
    b=Path(APK).read_bytes();assert len(b)==EXPECTED_SIZE,(len(b),EXPECTED_SIZE);assert hashlib.sha256(b).hexdigest()==EXPECTED_SHA
    rec('candidate.txt',f'sha256={EXPECTED_SHA}\nsize={EXPECTED_SIZE}\npackage={PKG}\nmode=probe-320x568-coordinate\n')
def ensure_uid():
    adb('shell','am','force-stop',PKG,check=False)
    probe=adb('shell','stat','-c','%u:%g',f'/data/user/0/{PKG}',check=False).stdout.strip()
    if ':' not in probe:
        adb('shell','am','start','-W','-n',f'{PKG}/{LAUNCHER}',check=False);time.sleep(.8);adb('shell','am','force-stop',PKG,check=False)
        probe=adb('shell','stat','-c','%u:%g',f'/data/user/0/{PKG}',check=False).stdout.strip()
    assert ':' in probe,probe;return probe.split(':',1)
def seed_auth():
    uid,gid=ensure_uid();OUT.mkdir(parents=True,exist_ok=True);p=OUT/'pick_pack_auth_session_v2.xml'
    p.write_text(prefs_xml({'token':'beta76-visual-offline-token','login_id':'tamnv2','display_name':'Nguyễn Văn Tâm','role':'SUPERADMIN','position':'superadmin','email':'tam95.supra@gmail.com'}),encoding='utf-8')
    dst=f'/data/user/0/{PKG}/shared_prefs/pick_pack_auth_session_v2.xml';tmp='/data/local/tmp/'+p.name
    adb('push',str(p),tmp);adb('shell','mkdir','-p',f'/data/user/0/{PKG}/shared_prefs');adb('shell','cp',tmp,dst);adb('shell','chown',f'{uid}:{gid}',dst);adb('shell','chmod','600',dst)
def screenshot(name,w=320,h=568):
    data=adb('exec-out','screencap','-p',text=False).stdout;rec(name,data);assert data[:8]==b'\x89PNG\r\n\x1a\n';got=(int.from_bytes(data[16:20],'big'),int.from_bytes(data[20:24],'big'));assert got==(w,h),(got,(w,h))
def launch_business():
    adb('shell','am','force-stop',PKG,check=False);seed_auth()
    first=adb('shell','am','start','-W','-n',f'{PKG}/{LAUNCHER}',check=False,timeout=20).stdout;rec('launcher-start.txt',first);assert 'Permission Denial' not in first and 'Error type' not in first,first;time.sleep(.9)
    r=adb('shell','am','start','-W','-n',f'{PKG}/{ACT}','--es','module','BUSINESS','--es','login','tamnv2','--es','name','OWNER','--es','role','SUPERADMIN','--es','position','superadmin','--es','email','tam95.supra@gmail.com',check=False,timeout=20).stdout;rec('operations-start.txt',r)
    assert 'Permission Denial' not in r and 'Error type' not in r and ('Status: ok' in r or 'Activity:' in r),r;time.sleep(1.0)
def main():
    verify_candidate();adb('wait-for-device');adb('shell','svc','wifi','disable',check=False);adb('shell','svc','data','disable',check=False)
    adb('shell','wm','size','320x568');adb('shell','wm','density','240');time.sleep(.6);launch_business();screenshot('probe-320x568-business.png')
    # 320x568: second-row left card is partially visible above the persistent bottom nav.
    adb('shell','input','tap','80','410');time.sleep(.9);screenshot('probe-320x568-drop-top.png')
    act=adb('shell','dumpsys','activity','activities',check=False).stdout;rec('probe-320x568-activity.txt',act[-12000:]);assert PKG in act and 'OperationsActivity' in act
    # Focus the QR field by fixed frame coordinate to exercise the soft keyboard without UiAutomator idle waits.
    adb('shell','input','tap','160','235');time.sleep(.8);screenshot('probe-320x568-keyboard.png')
    adb('shell','input','keyevent','4');time.sleep(.4)
    for _ in range(3):adb('shell','input','swipe','160','390','160','190','300');time.sleep(.25)
    screenshot('probe-320x568-drop-bottom.png')
    rec('probe.json','{"status":"PROBE_CAPTURED","size":"320x568","route":"coordinate","candidate_run":32875201581,"artifact_id":9573716441,"requires_human_inspection":true}\n')
    print('BETA76_VISUAL_PROBE_CAPTURED')
if __name__=='__main__':main()
