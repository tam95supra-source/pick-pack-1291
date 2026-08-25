#!/usr/bin/env python3
import hashlib, html, json, os, sqlite3, struct, subprocess, time, zlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PKG='vn.pickpack1291.app.beta.publicbeta'
ACT='vn.pickpack1291.app.beta.OperationsActivity'
EXPECTED_VERSION='0.4.2-beta.75'
EXPECTED_CODE='81'
OUT=Path('/tmp/visual')
ADB_TIMEOUT=18
MATRIX=[('320x568','160',(320,568)),('360x640','160',(360,640)),('480x800','240',(480,800))]

def run(args,check=True,text=True,timeout=ADB_TIMEOUT,**kw):
    if isinstance(args,str): args=['bash','-lc',args]
    return subprocess.run(args,check=check,text=text,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,**kw)

def adb(*args,check=True,text=True,timeout=ADB_TIMEOUT): return run(['adb',*args],check=check,text=text,timeout=timeout)
def record(name,data):
    OUT.mkdir(parents=True,exist_ok=True);p=OUT/name
    if isinstance(data,bytes):p.write_bytes(data)
    else:p.write_text(str(data),encoding='utf-8')

def prefs_xml(values):
    rows=["<?xml version='1.0' encoding='utf-8' standalone='yes' ?>",'<map>']
    for k,v in values.items():rows.append(f'<string name="{html.escape(k)}">{html.escape(str(v))}</string>')
    rows.append('</map>');return '\n'.join(rows)

def find_aapt():
    for p in sorted((Path(os.environ['ANDROID_HOME'])/'build-tools').glob('*/aapt'),reverse=True):
        if p.is_file():return str(p)
    raise RuntimeError('aapt not found')

def verify_candidate(apk):
    b=Path(apk).read_bytes();sha=hashlib.sha256(b).hexdigest();size=len(b)
    assert sha==os.environ['EXPECTED_SHA'];assert size==int(os.environ['EXPECTED_SIZE'])
    badging=run([find_aapt(),'dump','badging',apk]).stdout.splitlines()[0]
    assert f"name='{PKG}'" in badging and f"versionCode='{EXPECTED_CODE}'" in badging and f"versionName='{EXPECTED_VERSION}'" in badging
    record('candidate-identity.txt',f'sha256={sha}\nsize={size}\n{badging}\n')

def assignment(aid,typ,rid): return {'assignment_id':aid,'resource_type':typ,'resource_id':rid,'state':'ACTIVE'}
def position(key,label): return {'position_key':key,'position_label':label,'state':'ACTIVE'}

def make_db(path,date):
    if path.exists():path.unlink()
    db=sqlite3.connect(path);c=db.cursor();c.execute('PRAGMA user_version=3')
    c.execute('CREATE TABLE day_snapshot(business_date TEXT PRIMARY KEY NOT NULL,day_revision INTEGER NOT NULL,snapshot_json TEXT NOT NULL,saved_at INTEGER NOT NULL)')
    c.execute('CREATE INDEX idx_day_snapshot_saved ON day_snapshot(saved_at)')
    c.execute('CREATE TABLE sync_meta(meta_key TEXT PRIMARY KEY NOT NULL,meta_value TEXT NOT NULL)')
    c.execute('CREATE TABLE mutation_outbox(event_id TEXT PRIMARY KEY NOT NULL,body_json TEXT NOT NULL,exclusive INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL,attempt_count INTEGER NOT NULL DEFAULT 0,next_attempt_at INTEGER NOT NULL,queued_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,last_error TEXT)')
    c.execute('CREATE INDEX idx_mutation_outbox_due ON mutation_outbox(status,next_attempt_at,queued_at)')
    c.execute('CREATE TABLE local_history(event_id TEXT PRIMARY KEY NOT NULL,body_json TEXT NOT NULL,status TEXT NOT NULL,last_error TEXT,queued_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)')
    c.execute('CREATE INDEX idx_local_history_queued ON local_history(queued_at DESC)')
    s1={'session_id':'visual-s1','mnv':'30011','business_date':date,'shift':'Ca 2','state':'ACTIVE','pda_serial':'NLS-MT90-0012345','pda_enter_status':'Nguyên vẹn','enter_at':f'{date}T10:10:00Z','version':4,'main_position_v64':'Pick','positions_v64':[position('PICK','Pick')],'resource_assignments_v64':[assignment('a-pda-1','PDA','NLS-MT90-0012345')]}
    s2={'session_id':'visual-s2','mnv':'30050','business_date':date,'shift':'Ca 2','state':'ACTIVE','pda_serial':'NLS-MT90-0067890','pda_enter_status':'Màn hình xước nhẹ','user_pick':'HY1.OUT.01','pack_table':'D2','user_pack':'PACK02','enter_at':f'{date}T10:15:00Z','version':8,'main_position_v64':'Pick','positions_v64':[position('PICK','Pick'),position('PACK','Pack')],'resource_assignments_v64':[assignment('a-pda-2','PDA','NLS-MT90-0067890'),assignment('a-pick-2','USER_PICK','HY1.OUT.01'),assignment('a-table-2','PACK_TABLE','D2'),assignment('a-pack-2','USER_PACK','PACK02')]}
    s3={'session_id':'visual-used','mnv':'30060','business_date':date,'shift':'Ca 1','state':'ENDED','pda_serial':'NLS-MT90-0099999','pda_enter_status':'Nguyên vẹn','user_pick':'HY1.OUT.02','pack_table':'D3','user_pack':'PACK03','enter_at':f'{date}T01:00:00Z','exit_at':f'{date}T08:00:00Z','version':3}
    before={'shift':'Ca 2','positions_v64':[position('PICK','Pick')],'resource_assignments_v64':[assignment('old-table','PACK_TABLE','D1')],'pack_table':'D1'}
    after={'shift':'Ca 2','positions_v64':[position('PICK','Pick'),position('PACK','Pack')],'resource_assignments_v64':[assignment('new-table','PACK_TABLE','D2')],'pack_table':'D2'}
    change={'event_id':'visual-change-1','event_type':'RESOURCE_CHANGE','session_id':'visual-s2','mnv':'30050','actor':'Điều phối Beta75','committed_at':f'{date}T11:20:00Z','payload_json':json.dumps({'session_id':'visual-s2','mnv':'30050','before':before,'after':after,'operations':[{'op':'REPLACE_RESOURCE','assignment_id':'old-table','resource_type':'PACK_TABLE','new_resource_id':'D2'}]},ensure_ascii=False)}
    snap={'ok':True,'business_date':date,'day_revision':7,'sessions':[s1,s2,s3],'events':[change],'labor':[]}
    c.execute('INSERT INTO day_snapshot VALUES(?,?,?,?)',(date,7,json.dumps(snap,ensure_ascii=False),int(time.time()*1000)));c.execute('INSERT INTO sync_meta VALUES(?,?)',('business_date',date));db.commit();db.close()

def seed_fixture():
    adb('shell','am','force-stop',PKG,check=False)
    probe=adb('shell','stat','-c','%u:%g',f'/data/user/0/{PKG}',check=False).stdout.strip()
    if ':' not in probe:
        adb('shell','am','start','-W','-n',f'{PKG}/{ACT}','--es','module','BUSINESS','--es','login','0987654321','--es','name','TamNV','--es','role','ADMIN',check=False)
        time.sleep(.5);adb('shell','am','force-stop',PKG,check=False);probe=adb('shell','stat','-c','%u:%g',f'/data/user/0/{PKG}',check=False).stdout.strip()
    assert ':' in probe, probe
    uid,gid=probe.split(':',1);date=datetime.now(ZoneInfo('Asia/Bangkok')).strftime('%Y-%m-%d')
    auth=OUT/'pick_pack_auth_session_v2.xml';auth.write_text(prefs_xml({'token':'beta75-visual-offline-token','login_id':'0987654321','display_name':'TamNV','role':'ADMIN','position':'PickPack1291','email':'visual@example.invalid'}),encoding='utf-8')
    master={'ok':True,'master_revision':9,'staff':[{'mnv':'30011','full_name':'Nguyễn Văn A','main_position':'Pick','supplier':'NLV','department':'Pick Pack','site':'1291','warehouse':'HY1'},{'mnv':'30050','full_name':'Trần Thị B','main_position':'Pick','supplier':'NTH','department':'Pick Pack','site':'1291','warehouse':'HY1'},{'mnv':'30060','full_name':'Lê Văn C','main_position':'Pack','supplier':'NLV','department':'Pick Pack','site':'1291','warehouse':'HY1'},{'mnv':'30099','full_name':'Phạm Thị D','main_position':'Pick','supplier':'NLV','department':'Pick Pack','site':'1291','warehouse':'HY1'}],'pdas':[{'serial':'NLS-MT90-0012345','last5':'12345','status':'Nguyên vẹn'},{'serial':'NLS-MT90-0067890','last5':'67890','status':'Màn hình xước nhẹ'},{'serial':'NLS-MT90-0099999','last5':'99999','status':'Nguyên vẹn'}],'pda_statuses':['Nguyên vẹn','Màn hình xước nhẹ','Lỗi quét mã'],'user_picks':['HY1.OUT.01','HY1.OUT.02','HY1.OUT.03'],'pack_bundles':[{'table':'D1','user_pack':'PACK01'},{'table':'D2','user_pack':'PACK02'},{'table':'D3','user_pack':'PACK03'}]}
    master_xml=OUT/'pp1291_master_cache.xml';master_xml.write_text(prefs_xml({'snapshot':json.dumps(master,ensure_ascii=False,separators=(',',':'))}),encoding='utf-8')
    db=OUT/'pp_operational_45d.db';make_db(db,date)
    adb('shell','mkdir','-p',f'/data/user/0/{PKG}/shared_prefs',f'/data/user/0/{PKG}/databases')
    for local,dst in [(auth,f'/data/user/0/{PKG}/shared_prefs/pick_pack_auth_session_v2.xml'),(master_xml,f'/data/user/0/{PKG}/shared_prefs/pp1291_master_cache.xml'),(db,f'/data/user/0/{PKG}/databases/pp_operational_45d.db')]:
        tmp='/data/local/tmp/'+local.name;adb('push',str(local),tmp);adb('shell','cp',tmp,dst);adb('shell','chown',f'{uid}:{gid}',dst);adb('shell','chmod','600',dst)
    record('fixture.txt',f'date={date} uid={uid} gid={gid} active=30011,30050 used=30060 not_entered=30099 pack_tables=D1,D2,D3')

def png_pixels(path):
    data=Path(path).read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n';pos=8;idat=[];width=height=ctype=depth=interlace=None
    while pos<len(data):
        n=struct.unpack('>I',data[pos:pos+4])[0];typ=data[pos+4:pos+8];chunk=data[pos+8:pos+8+n];pos+=12+n
        if typ==b'IHDR':width,height,depth,ctype,_,_,interlace=struct.unpack('>IIBBBBB',chunk)
        elif typ==b'IDAT':idat.append(chunk)
        elif typ==b'IEND':break
    assert depth==8 and interlace==0;channels={0:1,2:3,4:2,6:4}[ctype];raw=zlib.decompress(b''.join(idat));stride=width*channels;rows=[];prev=bytearray(stride);off=0
    def paeth(a,b,c):p=a+b-c;pa=abs(p-a);pb=abs(p-b);pc=abs(p-c);return a if pa<=pb and pa<=pc else (b if pb<=pc else c)
    for _ in range(height):
        f=raw[off];off+=1;cur=bytearray(raw[off:off+stride]);off+=stride
        for i in range(stride):
            a=cur[i-channels] if i>=channels else 0;b=prev[i];c=prev[i-channels] if i>=channels else 0
            if f==1:cur[i]=(cur[i]+a)&255
            elif f==2:cur[i]=(cur[i]+b)&255
            elif f==3:cur[i]=(cur[i]+((a+b)//2))&255
            elif f==4:cur[i]=(cur[i]+paeth(a,b,c))&255
            elif f!=0:raise AssertionError(f'png filter {f}')
        rows.append(cur);prev=cur
    return width,height,channels,rows

def validate_png(path,wh):
    p=Path(path);assert p.stat().st_size>4000;w,h,c,rows=png_pixels(p);assert (w,h)==wh;vals=[]
    for y in range(0,h,max(1,h//24)):
        for x in range(0,w,max(1,w//24)):
            px=rows[y][x*c:(x+1)*c];rgb=[px[0]]*3 if c<3 else px[:3];vals.append(sum(rgb)/3)
    assert vals and max(vals)>12

def gate(tag):
    a=adb('shell','dumpsys','activity','activities',check=False).stdout;w=adb('shell','dumpsys','window','windows',check=False).stdout;record(f'{tag}-activity.txt',a[-12000:]);record(f'{tag}-window.txt',w[-12000:]);assert PKG in a and 'OperationsActivity' in a and PKG in w

def shot(d,tag,wh):
    data=adb('exec-out','screencap','-p',text=False).stdout;p=OUT/d/f'{tag}.png';p.write_bytes(data);validate_png(p,wh)

def start_module(d,module):
    adb('shell','am','force-stop',PKG,check=False)
    r=adb('shell','am','start','-W','-n',f'{PKG}/{ACT}','--es','module',module,'--es','login','0987654321','--es','name','TamNV','--es','role','ADMIN','--es','position','PickPack1291','--es','email','visual@example.invalid',check=False)
    record(f'{d}-{module.lower()}-start.txt',r.stdout);assert 'Error:' not in r.stdout;time.sleep(1.0);gate(f'{d}-{module.lower()}')

def open_exchange(d,wh):
    seed_fixture();start_module(d,'PDA_EXCHANGE');time.sleep(.8);shot(d,'10-pda-exchange',wh)

def open_employee(d,wh,mnv,tag):
    seed_fixture();start_module(d,'BUSINESS');shot(d,f'20-{tag}-business',wh)
    w,h=wh;adb('shell','input','tap',str(max(40,w//4)),str(int(h*.31)));time.sleep(.7);shot(d,f'21-{tag}-scan',wh)
    adb('shell','input','text',mnv);adb('shell','input','keyevent','66');time.sleep(1.0);gate(f'{d}-{tag}-employee');shot(d,f'22-{tag}-employee',wh)

def employee_dialog(d,wh,mnv,tag,tabs):
    open_employee(d,wh,mnv,tag)
    for _ in range(tabs): adb('shell','input','keyevent','61');time.sleep(.15)
    adb('shell','input','keyevent','66');time.sleep(.6);shot(d,f'23-{tag}-dialog',wh);adb('shell','input','keyevent','4');time.sleep(.2)

def timeline_view(d,wh):
    open_employee(d,wh,'30050','timeline');w,h=wh
    adb('shell','input','swipe',str(w//2),str(int(h*.72)),str(w//2),str(int(h*.30)),'420');time.sleep(.5);shot(d,'24-timeline-scrolled',wh)

def main():
    OUT.mkdir(parents=True,exist_ok=True);verify_candidate(os.environ['APK']);adb('wait-for-device');adb('shell','svc','wifi','disable',check=False);adb('shell','svc','data','disable',check=False);rows=[]
    try:
        for size,density,wh in MATRIX:
            d=f'{size}x{density}';(OUT/d).mkdir(parents=True,exist_ok=True);adb('shell','wm','size',size);adb('shell','wm','density',density);time.sleep(.7)
            open_exchange(d,wh)
            open_employee(d,wh,'30011','fixed-account')
            employee_dialog(d,wh,'30011','add',1)
            employee_dialog(d,wh,'30050','edit',2)
            employee_dialog(d,wh,'30050','delete',3)
            timeline_view(d,wh)
            open_employee(d,wh,'30099','not-entered')
            rows.append(f'{d}: pda_exchange+employee+add+edit+delete+timeline+not_entered captured; route_window=PASS png=PASS human_markers=REQUIRED')
    except Exception as e:
        record('failure.txt',repr(e));record('logcat-tail.txt',adb('logcat','-d','-t','300',check=False).stdout);raise
    record('runtime-summary.txt','\n'.join(rows)+'\n');print('\n'.join(rows))
if __name__=='__main__':main()
