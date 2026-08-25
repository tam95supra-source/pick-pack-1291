#!/usr/bin/env python3
import html,json,os,re,shutil,sqlite3,struct,subprocess,sys,time
from pathlib import Path
import xml.etree.ElementTree as ET

PKG='vn.pickpack1291.app.beta.publicbeta'
ACT='vn.pickpack1291.app.beta.OperationsActivity'
EXPECTED_VERSION='0.4.2-beta.71'
EXPECTED_CODE='77'
EXPECTED_SHA=os.environ['EXPECTED_SHA']
EXPECTED_SIZE=int(os.environ['EXPECTED_SIZE'])
APK=os.environ['APK']
OUT=Path('/tmp/visual'); OUT.mkdir(parents=True,exist_ok=True)

def run(args,check=True,text=True,**kw):
    if isinstance(args,str): args=['bash','-lc',args]
    return subprocess.run(args,check=check,text=text,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,**kw)
def adb(*args,check=True,text=True): return run(['adb',*args],check=check,text=text)
def record(name,s): (OUT/name).write_text(str(s),encoding='utf-8')

def find_aapt():
    for p in sorted(Path(os.environ['ANDROID_HOME']).glob('build-tools/*/aapt'),reverse=True):
        if p.is_file(): return str(p)
    raise RuntimeError('aapt not found')

# immutable candidate identity
import hashlib
b=Path(APK).read_bytes(); sha=hashlib.sha256(b).hexdigest(); size=len(b)
assert sha==EXPECTED_SHA,(sha,EXPECTED_SHA); assert size==EXPECTED_SIZE,(size,EXPECTED_SIZE)
aapt=find_aapt(); badging=run([aapt,'dump','badging',APK]).stdout.splitlines()[0]
record('badging.txt',badging)
assert f"name='{PKG}'" in badging,badging
assert f"versionCode='{EXPECTED_CODE}'" in badging,badging
assert f"versionName='{EXPECTED_VERSION}'" in badging,badging

adb('wait-for-device'); adb('root'); adb('wait-for-device')
adb('shell','setprop','persist.sys.timezone','Asia/Bangkok',check=False)
adb('shell','am','force-stop',PKG,check=False)
adb('shell','mkdir','-p',f'/data/user/0/{PKG}/shared_prefs',f'/data/user/0/{PKG}/databases')
uid=adb('shell','stat','-c','%u',f'/data/user/0/{PKG}').stdout.strip()
gid=adb('shell','stat','-c','%g',f'/data/user/0/{PKG}').stdout.strip(); record('app-owner.txt',f'uid={uid} gid={gid}')

# real on-device storage fixture, used only by the emulator; release APK bytes remain untouched.
now=1787610500000
day={'ok':True,'business_date':'2026-08-25','day_revision':71,'sessions':[
 {'session_id':'VIS-42267-A','mnv':'42267','full_name':'Nguyễn Văn Minh','state':'ACTIVE','shift':'Ca 1','enter_at':'2026-08-25T05:05:00+07:00','exit_at':'','pda_serial':'MT90-123456789','work_choice':'Pick','main_position':'Pick / Pack','resource_assignments_v64':[{'assignment_id':'asg-pda','resource_type':'PDA','resource_id':'MT90-123456789','status':'ACTIVE'},{'assignment_id':'asg-pick','resource_type':'USER_PICK','resource_id':'user16','status':'ACTIVE'}],'positions_v64':[{'position_key':'PICK','position_label':'Pick','status':'ACTIVE'}]},
 {'session_id':'VIS-51001-B','mnv':'51001','full_name':'Trần Thị Lan','state':'ENDED','shift':'Ca 1','enter_at':'2026-08-25T05:00:00+07:00','exit_at':'2026-08-25T05:12:00+07:00','pda_serial':'','work_choice':'Pack'}]}
history=[
 {'event_id':'VIS-H-RESOURCE','event_type':'RESOURCE_CHANGE','created_at':'2026-08-25T05:10:00+07:00','updated_at':'2026-08-25T05:10:00+07:00','actor':'tamnv2','actor_name':'Nguyễn Văn Tâm','actor_role':'ADMIN','device_id':'VISUAL-PDA','source':'PDA','status':'ACKED','mnv':'42267','full_name':'Nguyễn Văn Minh','detail':'Sửa thông tin trong ca','payload':{'mnv':'42267','full_name':'Nguyễn Văn Minh','operations':[{'op':'REPLACE_RESOURCE','assignment_id':'asg-pda','resource_type':'PDA','resource_id':'MT90-123456789','new_resource_id':'MT90-987654321','reason':'Đổi thiết bị trong ca','disposition':'AVAILABLE'},{'op':'ADD_POSITION','position_key':'PACK','position_label':'Pack'}],'before':{'pda_serial':'MT90-123456789','work_choice':'Pick'},'after':{'pda_serial':'MT90-987654321','work_choice':'Pick & Pack'}}},
 {'event_id':'VIS-H-ENTER','event_type':'ATTENDANCE_ENTER','created_at':'2026-08-25T05:05:00+07:00','updated_at':'2026-08-25T05:05:00+07:00','actor':'tamnv2','actor_name':'Nguyễn Văn Tâm','actor_role':'ADMIN','device_id':'VISUAL-PDA','source':'PDA','status':'ACKED','mnv':'42267','full_name':'Nguyễn Văn Minh','payload':{'mnv':'42267','full_name':'Nguyễn Văn Minh','shift':'Ca 1','enter_at':'2026-08-25T05:05:00+07:00'}}]
db=OUT/'pp_operational_45d.db'; db.unlink(missing_ok=True); con=sqlite3.connect(db)
con.execute('CREATE TABLE day_snapshot(business_date TEXT PRIMARY KEY NOT NULL,day_revision INTEGER NOT NULL,snapshot_json TEXT NOT NULL,saved_at INTEGER NOT NULL)')
con.execute('CREATE TABLE local_history(event_id TEXT PRIMARY KEY NOT NULL,body_json TEXT NOT NULL,status TEXT NOT NULL,last_error TEXT,queued_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)')
con.execute('CREATE TABLE mutation_outbox(event_id TEXT PRIMARY KEY NOT NULL,body_json TEXT NOT NULL,exclusive INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL,attempt_count INTEGER NOT NULL DEFAULT 0,next_attempt_at INTEGER NOT NULL,queued_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,last_error TEXT)')
con.execute('CREATE TABLE sync_meta(meta_key TEXT PRIMARY KEY NOT NULL,meta_value TEXT NOT NULL)')
con.execute('INSERT INTO day_snapshot VALUES(?,?,?,?)',('2026-08-25',69,json.dumps(day,ensure_ascii=False),now))
for i,h in enumerate(history): con.execute('INSERT INTO local_history VALUES(?,?,?,?,?,?)',(h['event_id'],json.dumps(h,ensure_ascii=False),'ACKED',None,now-i*1000,now-i*1000))
con.commit(); con.close()
master={'ok':True,'master_revision':71,'staff':[{'mnv':'42267','full_name':'Nguyễn Văn Minh','supplier':'NLV','main_position':'Pick / Pack','department':'Pickpack','site':'1291','warehouse':'HY1'},{'mnv':'51001','full_name':'Trần Thị Lan','supplier':'NLV','main_position':'Pack','department':'Pickpack','site':'1291','warehouse':'HY1'}],'pdas':[{'serial':'MT90-123456789','status':'ACTIVE'},{'serial':'MT90-555555555','status':'AVAILABLE'}],'user_picks':['user16','user17'],'pack_bundles':[]}
def prefs(path,values):
    rows=["<?xml version='1.0' encoding='utf-8' standalone='yes' ?>",'<map>']
    for k,v in values.items():
        if isinstance(v,int): rows.append(f'<long name="{html.escape(k)}" value="{v}" />')
        else: rows.append(f'<string name="{html.escape(k)}">{html.escape(str(v))}</string>')
    rows.append('</map>'); Path(path).write_text('\n'.join(rows),encoding='utf-8')
auth=OUT/'pick_pack_auth_session_v2.xml'; cache=OUT/'pp1291_master_cache.xml'
prefs(auth,{'token':'beta71-visual-offline-token','login_id':'tamnv2','display_name':'Nguyễn Văn Tâm','role':'ADMIN','position':'Chuyên viên Pick Pack 1291','email':'visual@example.invalid'})
prefs(cache,{'snapshot':json.dumps(master,ensure_ascii=False),'revision':71,'saved_at':now})
for src,dst in [(db,f'/data/user/0/{PKG}/databases/pp_operational_45d.db'),(auth,f'/data/user/0/{PKG}/shared_prefs/pick_pack_auth_session_v2.xml'),(cache,f'/data/user/0/{PKG}/shared_prefs/pp1291_master_cache.xml')]:
    tmp='/data/local/tmp/'+src.name; adb('push',str(src),tmp); adb('shell','cp',tmp,dst); adb('shell','chown',f'{uid}:{gid}',dst); adb('shell','chmod','600',dst)
adb('shell','settings','put','global','airplane_mode_on','1',check=False)
adb('shell','am','broadcast','-a','android.intent.action.AIRPLANE_MODE','--ez','state','true',check=False)

def dump(path):
    last=b''
    for _ in range(6):
        adb('shell','uiautomator','dump','/sdcard/window.xml',check=False)
        data=adb('exec-out','cat','/sdcard/window.xml',check=False,text=False).stdout
        last=data
        if data.lstrip().startswith(b'<?xml'):
            Path(path).write_bytes(data)
            return ET.fromstring(data)
        time.sleep(.25)
    Path(path).write_bytes(last)
    raise AssertionError('uiautomator returned no XML after bounded retry')
def all_text(root): return '\n'.join((n.attrib.get('text','')+' '+n.attrib.get('content-desc','')).strip() for n in root.iter() if n.attrib.get('text') or n.attrib.get('content-desc'))
def ui_text(): return all_text(dump(OUT/'window.xml'))
def find_bounds(q):
    q=q.casefold(); root=dump(OUT/'window.xml')
    for n in root.iter():
        if q in (n.attrib.get('text','')+' '+n.attrib.get('content-desc','')).casefold():
            m=re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',n.attrib.get('bounds',''))
            if m:return tuple(map(int,m.groups()))
    return None
def tap(q,scroll=False):
    for attempt in range(5 if scroll else 1):
        b=find_bounds(q)
        if b:
            adb('shell','input','tap',str((b[0]+b[2])//2),str((b[1]+b[3])//2)); time.sleep(.7); return True
        if scroll:
            adb('shell','input','swipe','240','650','240','250','350'); time.sleep(.4)
    return False
def tap_any(*qs,scroll=False):
    for q in qs:
        if tap(q,scroll=scroll): return q
    raise AssertionError('tap target missing: '+repr(qs)+'\nUI:\n'+ui_text())
def expect(q):
    t=ui_text();
    if q.casefold() not in t.casefold(): raise AssertionError(f'missing {q!r}\nUI:\n{t}')
def absent(q):
    t=ui_text();
    if q.casefold() in t.casefold(): raise AssertionError(f'unexpected {q!r}\nUI:\n{t}')
def screenshot(d,tag):
    data=adb('exec-out','screencap','-p',text=False).stdout; p=OUT/d/f'{tag}.png'; p.write_bytes(data)
    root=dump(OUT/d/f'{tag}.xml'); (OUT/d/f'{tag}.txt').write_text(all_text(root),encoding='utf-8')
def start_home():
    adb('shell','am','force-stop',PKG,check=False); r=adb('shell','am','start','-W','-n',f'{PKG}/{ACT}',check=False); record('last-start.txt',r.stdout); time.sleep(2); expect('Mạng'); expect('Đồng bộ'); expect('Dịch vụ')
def resumed():
    t=adb('shell','dumpsys','activity','activities').stdout
    if PKG not in '\n'.join(x for x in t.splitlines() if 'mResumedActivity' in x or 'topResumedActivity' in x): raise AssertionError('app not resumed')

def reset_home():
    start_home()
    # always return to top of business screen for reproducible search
    for _ in range(2): adb('shell','input','swipe','240','260','240','720','300',check=False)


def rawshot(d,tag):
    data=adb('exec-out','screencap','-p',text=False).stdout
    p=OUT/d/f'{tag}.png'; p.write_bytes(data)
    assert data[:8]==b'\x89PNG\r\n\x1a\n', (d,tag,'not-png')

def launch_home():
    adb('shell','am','force-stop',PKG,check=False)
    r=adb('shell','am','start','-W','-n',f'{PKG}/{ACT}',check=False)
    record('last-start.txt',r.stdout); time.sleep(2)

def tapxy(x,y,wait=.9):
    adb('shell','input','tap',str(int(x)),str(int(y)),check=False); time.sleep(wait)

def resumed_check(tag):
    t=adb('shell','dumpsys','activity','activities',check=False).stdout
    lines='\n'.join(x for x in t.splitlines() if PKG in x)
    record(f'resumed-{tag}.txt',lines[-8000:])
    assert PKG in lines, tag+' package not present in activity state'

def swipe(x1,y1,x2,y2,ms=420,wait=.9):
    adb('shell','input','swipe',str(int(x1)),str(int(y1)),str(int(x2)),str(int(y2)),str(int(ms)),check=False); time.sleep(wait)

matrix=[('320x568','160',(320,568)),('360x640','160',(360,640)),('480x800','240',(480,800))]
rows=[]
try:
  for size,density,wh in matrix:
    W,H=wh; scale=int(density)/160.0
    d=f'{size}x{density}'; (OUT/d).mkdir(exist_ok=True)
    adb('shell','wm','size',size); adb('shell','wm','density',density); time.sleep(1)

    # 1) Home warning + blink evidence.
    adb('shell','settings','put','global','animator_duration_scale','1',check=False)
    launch_home(); rawshot(d,'01-home-warning-a'); time.sleep(.75); rawshot(d,'02-home-warning-b')

    # 2) Three status cards.
    tapxy(W*0.17,87*scale); rawshot(d,'03-network-detail'); adb('shell','input','keyevent','4',check=False); time.sleep(.5)
    tapxy(W*0.50,87*scale); rawshot(d,'04-sync-detail'); adb('shell','input','keyevent','4',check=False); time.sleep(.5)
    tapxy(W*0.83,87*scale); rawshot(d,'05-service-detail'); adb('shell','input','keyevent','4',check=False); time.sleep(.5)

    # 3) Critical Beta71 defect evidence: airplane/remote failure while local ACTIVE holder exists.
    launch_home(); tapxy(W*0.75,218*scale,2.6); rawshot(d,'06-pda-exchange-local-holder-offline'); resumed_check(d+'-pda')
    swipe(5,H*0.50,W*0.82,H*0.50,460,1.0); rawshot(d,'07-pda-swipe-back-parent'); resumed_check(d+'-pda-swipe-back')

    # 4) History list/detail.
    launch_home(); tapxy(W*0.61,H-102*scale,1.1); rawshot(d,'08-history-list'); resumed_check(d+'-history-list')
    tapxy(W*0.50,255*scale,1.0); rawshot(d,'09-history-detail'); resumed_check(d+'-history-detail')
    swipe(5,H*0.50,W*0.82,H*0.50,460,1.0); rawshot(d,'10-history-swipe-back'); resumed_check(d+'-history-swipe-back')

    # 5) Employee/session screen.
    launch_home(); tapxy(W*0.25,218*scale,.9)
    tapxy(W*0.50,151*scale,.25); adb('shell','input','text','42267',check=False); adb('shell','input','keyevent','66',check=False); time.sleep(1.8)
    rawshot(d,'11-session-header')
    expected_change='Đổi PDA: MT90-123456789 → MT90-987654321'
    for _ in range(5):
        if expected_change.casefold() in ui_text().casefold(): break
        swipe(W*0.50,H*0.74,W*0.50,H*0.30,520,.65)
    expect(expected_change); expect('Thêm vị trí trong ca: Pack')
    rawshot(d,'12-session-timeline'); resumed_check(d+'-timeline')

    imgs=sorted((OUT/d).glob('*.png')); assert len(imgs)==12,(d,len(imgs))
    for f in imgs:
        x=f.read_bytes(); assert x[:8]==b'\x89PNG\r\n\x1a\n'; w,h=struct.unpack('>II',x[16:24]); assert (w,h)==wh,(f,(w,h),wh); assert len(x)>4000,(f,len(x))
    rows.append(f'{d}: screenshots=12 dimensions={W}x{H} exact_beta71=PASS local_active_holder_fixture=MT90-123456789 remote_state=AIRPLANE manual_visual_inspection=REQUIRED')
except Exception as e:
  record('failure.txt',repr(e)); record('logcat-tail.txt',adb('logcat','-d','-t','300',check=False).stdout); raise
record('runtime-summary.txt','\n'.join(rows)+'\n')
print('\n'.join(rows))