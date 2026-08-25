#!/usr/bin/env python3
import hashlib, html, json, os, sqlite3, struct, subprocess, time, zlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PKG='vn.pickpack1291.app.beta.publicbeta'
ACT='vn.pickpack1291.app.beta.OperationsActivity'
APK=os.environ['APK']
EXPECTED_SHA='6e08dc974281cc7b5428d22cf406179447cdeb95443dc19fa1db2b4d32344913'
EXPECTED_SIZE=13147013
OUT=Path('/tmp/probe')
WH=(480,800)
ADB_TIMEOUT=18

def run(args,check=True,text=True,timeout=ADB_TIMEOUT):
    return subprocess.run(args,check=check,text=text,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
def adb(*args,check=True,text=True,timeout=ADB_TIMEOUT):
    return run(['adb',*args],check=check,text=text,timeout=timeout)
def rec(name,data):
    OUT.mkdir(parents=True,exist_ok=True)
    p=OUT/name
    p.write_bytes(data) if isinstance(data,bytes) else p.write_text(str(data),encoding='utf-8')

def prefs_xml(values):
    rows=["<?xml version='1.0' encoding='utf-8' standalone='yes' ?>",'<map>']
    for k,v in values.items():
        rows.append(f'<string name="{html.escape(k)}">{html.escape(str(v))}</string>')
    rows.append('</map>')
    return '\n'.join(rows)

def verify_candidate():
    b=Path(APK).read_bytes()
    assert len(b)==EXPECTED_SIZE, len(b)
    assert hashlib.sha256(b).hexdigest()==EXPECTED_SHA
    rec('candidate.txt',f'sha256={EXPECTED_SHA}\nsize={EXPECTED_SIZE}\npackage={PKG}\n')

def make_db(path,date):
    if path.exists(): path.unlink()
    db=sqlite3.connect(path); c=db.cursor()
    c.execute('PRAGMA user_version=3')
    c.execute('CREATE TABLE day_snapshot(business_date TEXT PRIMARY KEY NOT NULL,day_revision INTEGER NOT NULL,snapshot_json TEXT NOT NULL,saved_at INTEGER NOT NULL)')
    c.execute('CREATE INDEX idx_day_snapshot_saved ON day_snapshot(saved_at)')
    c.execute('CREATE TABLE sync_meta(meta_key TEXT PRIMARY KEY NOT NULL,meta_value TEXT NOT NULL)')
    c.execute('CREATE TABLE mutation_outbox(event_id TEXT PRIMARY KEY NOT NULL,body_json TEXT NOT NULL,exclusive INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL,attempt_count INTEGER NOT NULL DEFAULT 0,next_attempt_at INTEGER NOT NULL,queued_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,last_error TEXT)')
    c.execute('CREATE INDEX idx_mutation_outbox_due ON mutation_outbox(status,next_attempt_at,queued_at)')
    c.execute('CREATE TABLE local_history(event_id TEXT PRIMARY KEY NOT NULL,body_json TEXT NOT NULL,status TEXT NOT NULL,last_error TEXT,queued_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)')
    c.execute('CREATE INDEX idx_local_history_queued ON local_history(queued_at DESC)')
    sess={'session_id':'probe-s1','mnv':'30011','business_date':date,'shift':'Ca 2','state':'ACTIVE','pda_serial':'NLS-MT90-0012345','pda_enter_status':'Nguyên vẹn','enter_at':f'{date}T10:10:00Z','version':4,'main_position_v64':'Pick','positions_v64':[{'position_key':'PICK','position_label':'Pick','state':'ACTIVE'}],'resource_assignments_v64':[{'assignment_id':'a-pda-1','resource_type':'PDA','resource_id':'NLS-MT90-0012345','state':'ACTIVE'}]}
    snap={'ok':True,'business_date':date,'day_revision':7,'sessions':[sess],'events':[],'labor':[]}
    c.execute('INSERT INTO day_snapshot VALUES(?,?,?,?)',(date,7,json.dumps(snap,ensure_ascii=False),int(time.time()*1000)))
    c.execute('INSERT INTO sync_meta VALUES(?,?)',('business_date',date))
    db.commit(); db.close()

def seed():
    adb('shell','am','force-stop',PKG,check=False)
    probe=adb('shell','stat','-c','%u:%g',f'/data/user/0/{PKG}',check=False).stdout.strip()
    if ':' not in probe:
        adb('shell','am','start','-W','-n',f'{PKG}/{ACT}','--es','module','BUSINESS','--es','login','0987654321','--es','name','TamNV','--es','role','ADMIN',check=False)
        time.sleep(.6); adb('shell','am','force-stop',PKG,check=False)
        probe=adb('shell','stat','-c','%u:%g',f'/data/user/0/{PKG}',check=False).stdout.strip()
    assert ':' in probe, probe
    uid,gid=probe.split(':',1)
    date=datetime.now(ZoneInfo('Asia/Bangkok')).strftime('%Y-%m-%d')
    auth=OUT/'pick_pack_auth_session_v2.xml'
    auth.write_text(prefs_xml({'token':'beta75-probe-offline-token','login_id':'0987654321','display_name':'TamNV','role':'ADMIN','position':'PickPack1291','email':'probe@example.invalid'}),encoding='utf-8')
    master={'ok':True,'master_revision':9,'staff':[{'mnv':'30011','full_name':'Nguyễn Văn A','main_position':'Pick','supplier':'NLV','department':'Pick Pack','site':'1291','warehouse':'HY1'}],'pdas':[{'serial':'NLS-MT90-0012345','last5':'12345','status':'Nguyên vẹn'}],'pda_statuses':['Nguyên vẹn','Màn hình xước nhẹ','Lỗi quét mã'],'user_picks':['HY1.OUT.01','HY1.OUT.02','HY1.OUT.03'],'pack_bundles':[{'table':'D1','user_pack':'PACK01'},{'table':'D2','user_pack':'PACK02'},{'table':'D3','user_pack':'PACK03'}]}
    mx=OUT/'pp1291_master_cache.xml'
    mx.write_text(prefs_xml({'snapshot':json.dumps(master,ensure_ascii=False,separators=(',',':'))}),encoding='utf-8')
    db=OUT/'pp_operational_45d.db'; make_db(db,date)
    adb('shell','mkdir','-p',f'/data/user/0/{PKG}/shared_prefs',f'/data/user/0/{PKG}/databases')
    for local,dst in [(auth,f'/data/user/0/{PKG}/shared_prefs/pick_pack_auth_session_v2.xml'),(mx,f'/data/user/0/{PKG}/shared_prefs/pp1291_master_cache.xml'),(db,f'/data/user/0/{PKG}/databases/pp_operational_45d.db')]:
        tmp='/data/local/tmp/'+local.name
        adb('push',str(local),tmp); adb('shell','cp',tmp,dst); adb('shell','chown',f'{uid}:{gid}',dst); adb('shell','chmod','600',dst)

def png_pixels(data):
    assert data[:8]==b'\x89PNG\r\n\x1a\n'
    pos=8; idat=[]; w=h=ctype=depth=interlace=None
    while pos<len(data):
        n=struct.unpack('>I',data[pos:pos+4])[0]; typ=data[pos+4:pos+8]; chunk=data[pos+8:pos+8+n]; pos+=12+n
        if typ==b'IHDR': w,h,depth,ctype,_,_,interlace=struct.unpack('>IIBBBBB',chunk)
        elif typ==b'IDAT': idat.append(chunk)
        elif typ==b'IEND': break
    assert depth==8 and interlace==0
    ch={0:1,2:3,4:2,6:4}[ctype]; raw=zlib.decompress(b''.join(idat)); stride=w*ch
    rows=[]; prev=bytearray(stride); off=0
    def paeth(a,b,c):
        p=a+b-c; pa=abs(p-a); pb=abs(p-b); pc=abs(p-c)
        return a if pa<=pb and pa<=pc else (b if pb<=pc else c)
    for _ in range(h):
        f=raw[off]; off+=1; cur=bytearray(raw[off:off+stride]); off+=stride
        for i in range(stride):
            a=cur[i-ch] if i>=ch else 0; b=prev[i]; c=prev[i-ch] if i>=ch else 0
            if f==1: cur[i]=(cur[i]+a)&255
            elif f==2: cur[i]=(cur[i]+b)&255
            elif f==3: cur[i]=(cur[i]+((a+b)//2))&255
            elif f==4: cur[i]=(cur[i]+paeth(a,b,c))&255
            elif f!=0: raise AssertionError(f'filter={f}')
        rows.append(cur); prev=cur
    return w,h,ch,rows

def screenshot(name):
    data=adb('exec-out','screencap','-p',text=False).stdout
    w,h,_,_=png_pixels(data); assert (w,h)==WH,(w,h)
    rec(name,data); return data

def find_action_row(data):
    w,h,ch,rows=png_pixels(data)
    per=[]
    for y in range(int(h*.30),int(h*.86)):
        counts=[0,0,0]; sx=[0,0,0]
        for x in range(w):
            px=rows[y][x*ch:(x+1)*ch]; r,g,b=(px[0],px[0],px[0]) if ch<3 else (px[0],px[1],px[2])
            cls=None
            if 15<=r<=65 and 70<=g<=135 and 180<=b<=245: cls=0
            elif 10<=r<=55 and 35<=g<=90 and 120<=b<=200: cls=1
            elif 175<=r<=230 and 85<=g<=145 and b<=45: cls=2
            if cls is not None: counts[cls]+=1; sx[cls]+=x
        if min(counts)>=max(28,int(w*.055)):
            xs=[sx[i]//counts[i] for i in range(3)]
            if xs[0] < xs[1] < xs[2]: per.append((y,counts,xs))
    if not per: return None
    bands=[]
    for item in per:
        if bands and item[0]==bands[-1][-1][0]+1: bands[-1].append(item)
        else: bands.append([item])
    bands=[b for b in bands if len(b)>=7]
    if not bands: return None
    band=max(bands,key=len); mid=band[len(band)//2]
    return (mid[2][0], mid[0])

def main():
    OUT.mkdir(parents=True,exist_ok=True); verify_candidate()
    adb('wait-for-device'); adb('shell','svc','wifi','disable',check=False); adb('shell','svc','data','disable',check=False)
    adb('shell','wm','size','480x800'); adb('shell','wm','density','240'); time.sleep(.6)
    seed()
    r=adb('shell','am','start','-W','-n',f'{PKG}/{ACT}','--es','module','BUSINESS','--es','login','0987654321','--es','name','TamNV','--es','role','ADMIN','--es','position','PickPack1291','--es','email','probe@example.invalid',check=False)
    rec('start.txt',r.stdout); assert 'Error:' not in r.stdout; time.sleep(1)
    adb('shell','input','tap','120','248'); time.sleep(.5)
    adb('shell','input','text','30011'); adb('shell','input','keyevent','66'); time.sleep(1)
    win=adb('shell','dumpsys','window','windows',check=False).stdout
    if 'InputMethod' in win and 'isOnScreen=true' in win:
        adb('shell','input','keyevent','4'); time.sleep(.4)
    before=None; target=None
    for i in range(5):
        data=screenshot(f'probe-before-{i}.png')
        target=find_action_row(data)
        if target:
            before=data; rec('action-target.txt',f'x={target[0]} y={target[1]} attempt={i}\n'); break
        adb('shell','input','swipe','240','620','240','350','360'); time.sleep(.45)
    assert target is not None,'action row not found'
    adb('shell','input','tap',str(target[0]),str(target[1])); time.sleep(.8)
    after=screenshot('probe-480-add-dialog.png')
    bw,bh,bc,br=png_pixels(before); aw,ah,ac,ar=png_pixels(after)
    changed=sampled=0
    for y in range(0,800,3):
        for x in range(0,480,3):
            bp=br[y][x*bc:(x+1)*bc]; ap=ar[y][x*ac:(x+1)*ac]
            bv=[bp[0]]*3 if bc<3 else bp[:3]; av=[ap[0]]*3 if ac<3 else ap[:3]
            sampled+=1
            if sum(abs(int(av[j])-int(bv[j])) for j in range(3))>=60: changed+=1
    ratio=changed/max(1,sampled)
    rec('probe-result.txt',f'ratio={ratio:.4f}\nexpected=Them thong tin trong ca modal\n')
    assert ratio>=.10, ratio
    a=adb('shell','dumpsys','activity','activities',check=False).stdout
    w=adb('shell','dumpsys','window','windows',check=False).stdout
    rec('activity.txt',a[-12000:]); rec('window.txt',w[-16000:])
    assert PKG in a and 'OperationsActivity' in a and PKG in w
    print('PROBE_AUTOMATION_PASS')
if __name__=='__main__': main()
