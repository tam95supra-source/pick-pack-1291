#!/usr/bin/env python3
import hashlib, html, json, os, re, struct, subprocess, sys, time, zlib
from pathlib import Path

PKG='vn.pickpack1291.app.beta.publicbeta'
ACT='vn.pickpack1291.app.beta.OperationsActivity'
EXPECTED_VERSION='0.4.2-beta.73'
EXPECTED_CODE='79'
OUT=Path('/tmp/visual')
ADB_TIMEOUT=15
MATRIX=[('320x568','160',(320,568)),('360x640','160',(360,640)),('480x800','240',(480,800))]

FORBIDDEN_SETTINGS_GATE=('am instrument','UiAutomation','uiautomator')

def run(args,check=True,text=True,timeout=ADB_TIMEOUT,**kw):
    if isinstance(args,str): args=['bash','-lc',args]
    return subprocess.run(args,check=check,text=text,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,**kw)

def adb(*args,check=True,text=True,timeout=ADB_TIMEOUT):
    return run(['adb',*args],check=check,text=text,timeout=timeout)

def record(name,data):
    OUT.mkdir(parents=True,exist_ok=True)
    p=OUT/name
    if isinstance(data,bytes): p.write_bytes(data)
    else: p.write_text(str(data),encoding='utf-8')

def find_aapt():
    root=Path(os.environ['ANDROID_HOME'])/'build-tools'
    for p in sorted(root.glob('*/aapt'),reverse=True):
        if p.is_file(): return str(p)
    raise RuntimeError('aapt not found')

def preflight():
    src=Path(__file__).read_text(encoding='utf-8')
    compile(src,'run_beta73_visual.materialized.py','exec')
    settings_path='\n'.join(line for line in src.splitlines() if 'settings_' in line or 'Settings' in line or "module','SETTINGS" in line)
    bad=[x for x in FORBIDDEN_SETTINGS_GATE if x in settings_path]
    assert not bad, bad
    assert 'timeout=ADB_TIMEOUT' in src
    assert "dumpsys','activity','activities'" in src
    assert "dumpsys','window','windows'" in src
    assert src.count("rawshot(d,'16-settings-top')")==1
    assert src.count("rawshot(d,'17-settings-storage-update-log')")==1
    result={
        'py_compile':'PASS',
        'materialized_compile':'PASS',
        'standalone_materialized_source':True,
        'settings_gate':'dumpsys_activity+dumpsys_window+human_pixels',
        'adb_timeout_seconds':ADB_TIMEOUT,
        'forbidden_settings_gate_absent':True,
        'matrix':[x[0] for x in MATRIX],
        'source_sha256':hashlib.sha256(src.encode()).hexdigest(),
    }
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))

def prefs_xml(values):
    rows=["<?xml version='1.0' encoding='utf-8' standalone='yes' ?>",'<map>']
    for k,v in values.items():
        rows.append(f'<string name="{html.escape(k)}">{html.escape(str(v))}</string>')
    rows.append('</map>')
    return '\n'.join(rows)

def seed_auth():
    adb('root',check=False); adb('wait-for-device')
    adb('shell','am','force-stop',PKG,check=False)
    adb('shell','mkdir','-p',f'/data/user/0/{PKG}/shared_prefs')
    uid=adb('shell','stat','-c','%u',f'/data/user/0/{PKG}').stdout.strip()
    gid=adb('shell','stat','-c','%g',f'/data/user/0/{PKG}').stdout.strip()
    auth=OUT/'pick_pack_auth_session_v2.xml'
    auth.write_text(prefs_xml({
        'token':'beta73-visual-offline-token',
        'login_id':'tamnv2',
        'display_name':'Nguyen Van Tam',
        'role':'ADMIN',
        'position':'Chuyen vien Pick Pack 1291',
        'email':'visual@example.invalid',
    }),encoding='utf-8')
    dst=f'/data/user/0/{PKG}/shared_prefs/pick_pack_auth_session_v2.xml'
    tmp='/data/local/tmp/'+auth.name
    adb('push',str(auth),tmp)
    adb('shell','cp',tmp,dst)
    adb('shell','chown',f'{uid}:{gid}',dst)
    adb('shell','chmod','600',dst)
    record('auth-fixture.txt',f'uid={uid} gid={gid} login=tamnv2 role=ADMIN')

def verify_candidate(apk):
    b=Path(apk).read_bytes(); sha=hashlib.sha256(b).hexdigest(); size=len(b)
    expected_sha=os.environ['EXPECTED_SHA']; expected_size=int(os.environ['EXPECTED_SIZE'])
    assert sha==expected_sha,(sha,expected_sha)
    assert size==expected_size,(size,expected_size)
    aapt=find_aapt(); badging=run([aapt,'dump','badging',apk]).stdout.splitlines()[0]
    assert f"name='{PKG}'" in badging,badging
    assert f"versionCode='{EXPECTED_CODE}'" in badging,badging
    assert f"versionName='{EXPECTED_VERSION}'" in badging,badging
    record('candidate-identity.txt',f'sha256={sha}\nsize={size}\n{badging}\n')

def png_pixels(path):
    data=Path(path).read_bytes()
    assert data[:8]==b'\x89PNG\r\n\x1a\n'
    pos=8; idat=[]; width=height=ctype=depth=interlace=None
    while pos < len(data):
        n=struct.unpack('>I',data[pos:pos+4])[0]; typ=data[pos+4:pos+8]; chunk=data[pos+8:pos+8+n]; pos+=12+n
        if typ==b'IHDR': width,height,depth,ctype,_,_,interlace=struct.unpack('>IIBBBBB',chunk)
        elif typ==b'IDAT': idat.append(chunk)
        elif typ==b'IEND': break
    assert depth==8 and interlace==0,(depth,interlace)
    channels={0:1,2:3,4:2,6:4}[ctype]
    raw=zlib.decompress(b''.join(idat)); stride=width*channels
    rows=[]; prev=bytearray(stride); off=0
    def paeth(a,b,c):
        p=a+b-c; pa=abs(p-a); pb=abs(p-b); pc=abs(p-c)
        return a if pa<=pb and pa<=pc else (b if pb<=pc else c)
    for _ in range(height):
        f=raw[off]; off+=1; cur=bytearray(raw[off:off+stride]); off+=stride
        for i in range(stride):
            a=cur[i-channels] if i>=channels else 0; b=prev[i]; c=prev[i-channels] if i>=channels else 0
            if f==1: cur[i]=(cur[i]+a)&255
            elif f==2: cur[i]=(cur[i]+b)&255
            elif f==3: cur[i]=(cur[i]+((a+b)//2))&255
            elif f==4: cur[i]=(cur[i]+paeth(a,b,c))&255
            elif f!=0: raise AssertionError(f'png filter {f}')
        rows.append(cur); prev=cur
    return width,height,channels,rows

def validate_png(path,expected_wh):
    p=Path(path); data=p.read_bytes(); assert len(data)>4000,(p,len(data))
    w,h,c,rows=png_pixels(p); assert (w,h)==expected_wh,(p,(w,h),expected_wh)
    samples=[]
    step_y=max(1,h//24); step_x=max(1,w//24)
    for y in range(0,h,step_y):
        row=rows[y]
        for x in range(0,w,step_x):
            px=row[x*c:(x+1)*c]
            if c==1: rgb=[px[0]]*3
            elif c==2: rgb=[px[0]]*3
            else: rgb=px[:3]
            samples.append(sum(rgb)/3)
    assert samples and max(samples)>12,(p,'black-or-empty')

def rawshot(d,tag,wh):
    data=adb('exec-out','screencap','-p',text=False).stdout
    p=OUT/d/f'{tag}.png'; p.write_bytes(data)
    validate_png(p,wh)

def route_gate(tag):
    activity=adb('shell','dumpsys','activity','activities',check=False).stdout
    window=adb('shell','dumpsys','window','windows',check=False).stdout
    record(f'{tag}-activity.txt',activity[-12000:]); record(f'{tag}-window.txt',window[-12000:])
    activity_lines='\n'.join(x for x in activity.splitlines() if PKG in x or 'ResumedActivity' in x or 'topResumedActivity' in x)
    window_lines='\n'.join(x for x in window.splitlines() if PKG in x or 'mCurrentFocus' in x or 'mFocusedApp' in x)
    assert PKG in activity_lines and 'OperationsActivity' in activity_lines,activity_lines[-3000:]
    assert PKG in window_lines and 'OperationsActivity' in window_lines,window_lines[-3000:]

def open_settings(d,wh):
    W,H=wh
    adb('shell','am','force-stop',PKG,check=False)
    r=adb('shell','am','start','-W','-n',f'{PKG}/{ACT}','--es','module','SETTINGS','--es','login','tamnv2','--es','name','Nguyen Van Tam','--es','role','ADMIN','--es','position','Chuyen vien Pick Pack 1291','--es','email','visual@example.invalid',check=False)
    record(f'{d}-settings-start.txt',r.stdout)
    assert 'Error:' not in r.stdout and 'Status: timeout' not in r.stdout,r.stdout
    time.sleep(1.2)
    route_gate(f'{d}-settings-top-route')
    time.sleep(.6)
    rawshot(d,'16-settings-top',wh)
    swipe_count=4 if wh==(360,640) else 3
    for _ in range(swipe_count):
        adb('shell','input','swipe',str(int(W*.50)),str(int(H*.70)),str(int(W*.50)),str(int(H*.25)),'430',check=False)
        time.sleep(.25)
    time.sleep(.6)
    route_gate(f'{d}-settings-lower-route')
    rawshot(d,'17-settings-storage-update-log',wh)

def main():
    if '--preflight' in sys.argv:
        preflight(); return
    OUT.mkdir(parents=True,exist_ok=True)
    apk=os.environ['APK']
    verify_candidate(apk)
    adb('wait-for-device')
    seed_auth()
    rows=[]
    try:
        for size,density,wh in MATRIX:
            d=f'{size}x{density}'; (OUT/d).mkdir(parents=True,exist_ok=True)
            adb('shell','wm','size',size); adb('shell','wm','density',density); time.sleep(.8)
            open_settings(d,wh)
            rows.append(f'{d}: settings_top=PASS settings_lower=PASS route_window=PASS png=PASS human_markers=REQUIRED')
    except Exception as exc:
        record('failure.txt',repr(exc))
        record('logcat-tail.txt',adb('logcat','-d','-t','200',check=False).stdout)
        raise
    record('runtime-summary.txt','\n'.join(rows)+'\n')
    print('\n'.join(rows))

if __name__=='__main__':
    main()
