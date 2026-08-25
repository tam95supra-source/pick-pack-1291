#!/usr/bin/env python3
import hashlib, html, os, subprocess, time
from pathlib import Path
PKG='vn.pickpack1291.app.beta.publicbeta';ACT='vn.pickpack1291.app.beta.OperationsActivity';LAUNCHER='vn.pickpack1291.app.beta.FullBetaActivity'
APK=os.environ['APK'];EXPECTED_SHA=os.environ['EXPECTED_SHA'];EXPECTED_SIZE=int(os.environ['EXPECTED_SIZE']);OUT=Path('/tmp/beta76-visual')
def run(a,check=True,text=True,timeout=20):return subprocess.run(a,check=check,text=text,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
def adb(*a,check=True,text=True,timeout=20):return run(['adb',*a],check,text,timeout)
def rec(n,d):OUT.mkdir(parents=True,exist_ok=True);p=OUT/n;p.write_bytes(d) if isinstance(d,bytes) else p.write_text(str(d),encoding='utf-8')
def prefs(v):return "<?xml version='1.0' encoding='utf-8' standalone='yes' ?>\n<map>\n"+'\n'.join(f'<string name="{html.escape(k)}">{html.escape(str(x))}</string>' for k,x in v.items())+'\n</map>'
def verify():
 b=Path(APK).read_bytes();assert len(b)==EXPECTED_SIZE;assert hashlib.sha256(b).hexdigest()==EXPECTED_SHA;rec('candidate.txt',f'sha256={EXPECTED_SHA}\nsize={EXPECTED_SIZE}\npackage={PKG}\n')
def uid():
 adb('shell','am','force-stop',PKG,check=False);x=adb('shell','stat','-c','%u:%g',f'/data/user/0/{PKG}',check=False).stdout.strip()
 if ':' not in x: adb('shell','am','start','-W','-n',f'{PKG}/{LAUNCHER}',check=False);time.sleep(.8);adb('shell','am','force-stop',PKG,check=False);x=adb('shell','stat','-c','%u:%g',f'/data/user/0/{PKG}',check=False).stdout.strip()
 assert ':' in x;return x.split(':',1)
def seed():
 u,g=uid();p=OUT/'auth.xml';OUT.mkdir(parents=True,exist_ok=True);p.write_text(prefs({'token':'beta76-visual-offline-token','login_id':'tamnv2','display_name':'Nguyễn Văn Tâm','role':'SUPERADMIN','position':'superadmin','email':'tam95.supra@gmail.com'}),encoding='utf-8');dst=f'/data/user/0/{PKG}/shared_prefs/pick_pack_auth_session_v2.xml';adb('push',str(p),'/data/local/tmp/auth.xml');adb('shell','mkdir','-p',f'/data/user/0/{PKG}/shared_prefs');adb('shell','cp','/data/local/tmp/auth.xml',dst);adb('shell','chown',f'{u}:{g}',dst);adb('shell','chmod','600',dst)
def shot(n):
 d=adb('exec-out','screencap','-p',text=False).stdout;rec(n,d);assert d[:8]==b'\x89PNG\r\n\x1a\n';assert (int.from_bytes(d[16:20],'big'),int.from_bytes(d[20:24],'big'))==(320,568)
def launch():
 adb('shell','am','force-stop',PKG,check=False);seed();adb('shell','am','start','-W','-n',f'{PKG}/{LAUNCHER}',check=False);time.sleep(.9);r=adb('shell','am','start','-W','-n',f'{PKG}/{ACT}','--es','module','BUSINESS','--es','login','tamnv2','--es','name','OWNER','--es','role','SUPERADMIN','--es','position','superadmin','--es','email','tam95.supra@gmail.com',check=False).stdout;rec('operations-start.txt',r);assert 'Permission Denial' not in r and 'Error type' not in r;time.sleep(1)
def main():
 verify();adb('wait-for-device');adb('shell','svc','wifi','disable',check=False);adb('shell','svc','data','disable',check=False);adb('shell','wm','size','320x568');adb('shell','wm','density','240');time.sleep(.5);launch();shot('business.png');adb('shell','input','swipe','160','340','160','205','320');time.sleep(.5);shot('business-scrolled.png');adb('shell','input','tap','80','285');time.sleep(5.8);shot('drop-top.png');adb('shell','input','tap','160','275');time.sleep(.8);shot('keyboard.png');adb('shell','input','keyevent','4');time.sleep(.5);adb('shell','input','swipe','160','390','160','190','320');time.sleep(.3);adb('shell','input','swipe','160','390','160','190','320');time.sleep(.3);shot('drop-bottom.png');rec('probe.json','{"status":"PROBE_CAPTURED","size":"320x568","candidate_run":32875201581,"artifact_id":9573716441,"requires_human_inspection":true}\n');print('BETA76_VISUAL_PROBE_CAPTURED')
if __name__=='__main__':main()
