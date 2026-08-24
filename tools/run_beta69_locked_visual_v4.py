#!/usr/bin/env python3
import html,json,os,re,shutil,sqlite3,struct,subprocess,sys,time
from pathlib import Path
import xml.etree.ElementTree as ET

PKG='vn.pickpack1291.app.beta.publicbeta'
ACT='vn.pickpack1291.app.beta.OperationsActivity'
EXPECTED_VERSION='0.4.2-beta.69'
EXPECTED_CODE='75'
EXPECTED_SHA='251530388165c7a9a8572053238b5d44b47a6747c5e94f270230e65ce68d4cda'
EXPECTED_SIZE=13114245
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
day={'ok':True,'business_date':'2026-08-25','day_revision':69,'sessions':[
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
master={'ok':True,'master_revision':69,'staff':[{'mnv':'42267','full_name':'Nguyễn Văn Minh','supplier':'NLV','main_position':'Pick / Pack','department':'Pickpack','site':'1291','warehouse':'HY1'},{'mnv':'51001','full_name':'Trần Thị Lan','supplier':'NLV','main_position':'Pack','department':'Pickpack','site':'1291','warehouse':'HY1'}],'pdas':[{'serial':'MT90-123456789','status':'ACTIVE'},{'serial':'MT90-555555555','status':'AVAILABLE'}],'user_picks':['user16','user17'],'pack_bundles':[]}
def prefs(path,values):
    rows=["<?xml version='1.0' encoding='utf-8' standalone='yes' ?>",'<map>']
    for k,v in values.items():
        if isinstance(v,int): rows.append(f'<long name="{html.escape(k)}" value="{v}" />')
        else: rows.append(f'<string name="{html.escape(k)}">{html.escape(str(v))}</string>')
    rows.append('</map>'); Path(path).write_text('\n'.join(rows),encoding='utf-8')
auth=OUT/'pick_pack_auth_session_v2.xml'; cache=OUT/'pp1291_master_cache.xml'
prefs(auth,{'token':'beta69-visual-offline-token','login_id':'tamnv2','display_name':'Nguyễn Văn Tâm','role':'ADMIN','position':'Chuyên viên Pick Pack 1291','email':'visual@example.invalid'})
prefs(cache,{'snapshot':json.dumps(master,ensure_ascii=False),'revision':69,'saved_at':now})
for src,dst in [(db,f'/data/user/0/{PKG}/databases/pp_operational_45d.db'),(auth,f'/data/user/0/{PKG}/shared_prefs/pick_pack_auth_session_v2.xml'),(cache,f'/data/user/0/{PKG}/shared_prefs/pp1291_master_cache.xml')]:
    tmp='/data/local/tmp/'+src.name; adb('push',str(src),tmp); adb('shell','cp',tmp,dst); adb('shell','chown',f'{uid}:{gid}',dst); adb('shell','chmod','600',dst)
adb('shell','settings','put','global','airplane_mode_on','1',check=False)
adb('shell','am','broadcast','-a','android.intent.action.AIRPLANE_MODE','--ez','state','true',check=False)

def dump(path):
    adb('shell','uiautomator','dump','/sdcard/window.xml',check=False); data=adb('exec-out','cat','/sdcard/window.xml',text=False).stdout
    Path(path).write_bytes(data); return ET.fromstring(data)
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

matrix=[('320x568','160',(320,568)),('360x640','160',(360,640)),('480x800','240',(480,800))]
rows=[]
try:
  for size,density,wh in matrix:
    d=f'{size}x{density}'; (OUT/d).mkdir(exist_ok=True)
    adb('shell','wm','size',size); adb('shell','wm','density',density); time.sleep(1)
    reset_home(); expect('Ca 1'); screenshot(d,'01-home-warning-a'); time.sleep(.75); screenshot(d,'02-home-warning-b')
    tap_any('Mạng'); screenshot(d,'03-network-detail'); expect('Internet'); adb('shell','input','keyevent','4'); time.sleep(.4)
    reset_home(); tap_any('Đổi / Trả PDA','Đổi / Trả',scroll=True); screenshot(d,'04-pda-exchange'); expect('MT90-123456789'); absent('MT90-555555555')
    adb('shell','input','keyevent','4'); time.sleep(.6); resumed(); expect('Mạng'); screenshot(d,'05-back-parent')
    tap_any('Lịch sử',scroll=True); time.sleep(.7); screenshot(d,'06-history-list'); expect('Nguyễn Văn Tâm')
    tap_any('Nguyễn Văn Tâm','Sửa thông tin','tài nguyên',scroll=True); screenshot(d,'07-history-detail'); expect('Ai thực hiện'); expect('Nội dung thay đổi')
    adb('shell','input','keyevent','4'); time.sleep(.4)
    tap_any('Nghiệp vụ',scroll=False) if find_bounds('Nghiệp vụ') else None; time.sleep(.4)
    if not tap('Scan / Nhập mã nhân viên',scroll=True): tap_any('QUÉT QR NHÂN SỰ','Quét QR nhân sự',scroll=True); tap_any('Scan / Nhập mã nhân viên',scroll=True)
    adb('shell','input','text','42267'); adb('shell','input','keyevent','66'); time.sleep(1.5); screenshot(d,'08-session-timeline'); expect('Diễn biến trong ca'); absent('REPLACE_RESOURCE'); resumed()
    imgs=sorted((OUT/d).glob('*.png')); assert len(imgs)>=8,(d,len(imgs))
    for f in imgs:
        x=f.read_bytes(); assert x[:8]==b'\x89PNG\r\n\x1a\n'; w,h=struct.unpack('>II',x[16:24]); assert (w,h)==wh,(f,(w,h),wh); assert len(x)>4000,(f,len(x))
    assert (OUT/d/'01-home-warning-a.png').read_bytes()!=(OUT/d/'02-home-warning-b.png').read_bytes(),d+' blink frames identical'
    rows.append(f'{d}: screenshots={len(imgs)} dimensions={wh[0]}x{wh[1]} runtime_assertions=PASS')
except Exception as e:
  record('failure.txt',repr(e)+'\n\nUI:\n'+(ui_text() if True else ''))
  adb('logcat','-d','-t','300',check=False).stdout and record('logcat-tail.txt',adb('logcat','-d','-t','300',check=False).stdout)
  raise
record('runtime-summary.txt','\n'.join(rows)+'\n')
print('\n'.join(rows))
