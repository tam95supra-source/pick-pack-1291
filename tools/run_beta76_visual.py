#!/usr/bin/env python3
import hashlib, html, os, re, subprocess, time, xml.etree.ElementTree as ET
from pathlib import Path

PKG='vn.pickpack1291.app.beta.publicbeta'
ACT='vn.pickpack1291.app.beta.OperationsActivity'
LAUNCHER='vn.pickpack1291.app.beta.FullBetaActivity'
APK=os.environ['APK']
EXPECTED_SHA=os.environ['EXPECTED_SHA']
EXPECTED_SIZE=int(os.environ['EXPECTED_SIZE'])
OUT=Path('/tmp/beta76-visual')
SIZES=[(320,568),(360,640),(480,800)]
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
    rec('candidate.txt',f'sha256={EXPECTED_SHA}\nsize={EXPECTED_SIZE}\npackage={PKG}\n')
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
def dump_xml(name):
    target='/data/local/tmp/beta76-window.xml';last=''
    for attempt in range(2):
        adb('shell','rm','-f',target,check=False)
        r=adb('shell','uiautomator','dump',target,check=False,timeout=15);raw=adb('shell','cat',target,check=False,timeout=8).stdout;last=f'dump={r.stdout}\ncat={raw}'
        if '<hierarchy' in raw:rec(name,raw);return raw
        time.sleep(.7*(attempt+1))
    rec(name+'.error.txt',last);raise AssertionError('uiautomator hierarchy unavailable after 2 attempts')
def parse_bounds(value):
    m=re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',value or '');return tuple(map(int,m.groups())) if m else None
def find_nodes(raw,text=None,clazz=None):
    try:root=ET.fromstring(raw)
    except Exception:return []
    out=[]
    for n in root.iter('node'):
        if text is not None and text.lower() not in (n.attrib.get('text','')+' '+n.attrib.get('content-desc','')).lower():continue
        if clazz is not None and n.attrib.get('class')!=clazz:continue
        b=parse_bounds(n.attrib.get('bounds'))
        if b:out.append((n,b))
    return out
def tap_node(raw,text,clazz=None,last=False):
    nodes=find_nodes(raw,text,clazz);assert nodes,f'node not found: {text} {clazz}';_,b=nodes[-1 if last else 0];adb('shell','input','tap',str((b[0]+b[2])//2),str((b[1]+b[3])//2));return b
def screenshot(name,wh):
    data=adb('exec-out','screencap','-p',text=False).stdout;rec(name,data);assert data[:8]==b'\x89PNG\r\n\x1a\n';w=int.from_bytes(data[16:20],'big');h=int.from_bytes(data[20:24],'big');assert (w,h)==wh,((w,h),wh)
def launch_business():
    adb('shell','am','force-stop',PKG,check=False);seed_auth()
    first=adb('shell','am','start','-W','-n',f'{PKG}/{LAUNCHER}',check=False,timeout=20).stdout;rec('launcher-start.txt',first);assert 'Permission Denial' not in first and 'Error type' not in first,first;time.sleep(.8)
    r=adb('shell','am','start','-W','-n',f'{PKG}/{ACT}','--es','module','BUSINESS','--es','login','tamnv2','--es','name','Nguyễn Văn Tâm','--es','role','SUPERADMIN','--es','position','superadmin','--es','email','tam95.supra@gmail.com',check=False,timeout=20).stdout;rec('operations-start.txt',r)
    assert 'Permission Denial' not in r and 'Error type' not in r and ('Status: ok' in r or 'Activity:' in r),r;time.sleep(1.0)
def open_drop():
    raw=dump_xml('business.xml');tap_node(raw,'Nhận hàng Rớt');time.sleep(.7);raw=dump_xml('drop.xml');assert 'NHẬN HÀNG RỚT' in raw or 'Nhận hàng Rớt' in raw
    for label in ('Vị trí','Tạo','Sửa','Xóa','Scan QR','DO','Số kiện','Thêm thông tin','Xóa toàn bộ'):assert label in raw,label
    return raw
def visible(raw,text,wh):
    return any(b[2]>0 and b[0]<wh[0] and b[3]>0 and b[1]<wh[1] and b[2]>b[0] and b[3]>b[1] for _,b in find_nodes(raw,text))
def one_size(w,h):
    wh=(w,h);tag=f'{w}x{h}';adb('shell','wm','size',f'{w}x{h}');adb('shell','wm','density','240');time.sleep(.5);launch_business();raw=open_drop();screenshot(f'{tag}-top.png',wh);rec(f'{tag}-top.xml',raw)
    for label in ('Vị trí','Tạo','Sửa','Xóa','Scan QR','DO','Số kiện'):assert visible(raw,label,wh),f'{tag} top missing {label}'
    edits=find_nodes(raw,'Scan QR','android.widget.EditText')
    if edits:
        _,b=edits[0];adb('shell','input','tap',str((b[0]+b[2])//2),str((b[1]+b[3])//2));time.sleep(.7);screenshot(f'{tag}-keyboard.png',wh);rec(f'{tag}-keyboard.xml',dump_xml(f'{tag}-keyboard-dump.xml'));adb('shell','input','keyevent','4');time.sleep(.4)
    for _ in range(3):adb('shell','input','swipe',str(w//2),str(int(h*.72)),str(w//2),str(int(h*.34)),'320');time.sleep(.25)
    bottom=dump_xml(f'{tag}-bottom.xml');screenshot(f'{tag}-bottom.png',wh);assert visible(bottom,'Thêm thông tin',wh),f'{tag} bottom missing add';assert visible(bottom,'Xóa toàn bộ',wh),f'{tag} bottom missing clear'
    act=adb('shell','dumpsys','activity','activities',check=False).stdout;assert PKG in act and 'OperationsActivity' in act,f'{tag} wrong activity';rec(f'{tag}-activity.txt',act[-12000:])
def main():
    verify_candidate();adb('wait-for-device');adb('shell','svc','wifi','disable',check=False);adb('shell','svc','data','disable',check=False)
    for w,h in SIZES:one_size(w,h)
    rec('matrix.json','{"status":"AUTOMATION_PASS","sizes":["320x568","360x640","480x800"],"focus":["Nhận hàng Rớt","Vị trí","QR","DO","Số kiện","keyboard","Thêm thông tin","Xóa toàn bộ","navigation"]}\n');print('BETA76_VISUAL_AUTOMATION_PASS')
if __name__=='__main__':main()
