#!/usr/bin/env python3
from pathlib import Path

wrapper=Path(__file__).with_name('run_beta72_visual.py').read_text(encoding='utf-8')
needle="exec(compile(src, 'run_beta72_visual.materialized.py', 'exec'), {'__name__':'__main__', '__file__':str(Path(__file__).with_name('run_beta71_visual.py'))})"
inject=r'''
# Beta73 identity.
src=src.replace("EXPECTED_VERSION='0.4.2-beta.72'","EXPECTED_VERSION='0.4.2-beta.73'",1)
src=src.replace("EXPECTED_CODE='78'","EXPECTED_CODE='79'",1)
src=src.replace("'day_revision':72","'day_revision':73",1)
src=src.replace("'master_revision':72","'master_revision':73",1)
src=src.replace("'revision':72","'revision':73",1)
src=src.replace("'beta72-visual-offline-token'","'beta73-visual-offline-token'",1)
src=src.replace("exact_beta72=PASS owner_five_fixes=HUMAN_GATE","exact_beta73=PASS owner_scope=HUMAN_GATE",1)

src=src.replace(
    "'before':{'pda_serial':'MT90-123456789','work_choice':'Pick'},'after':{'pda_serial':'MT90-987654321','work_choice':'Pick & Pack'}",
    "'before':{'pda_serial':'MT90-123456789','user_pick':'user16','pack_table':'','user_pack':'','work_choice':'Pick'},'after':{'pda_serial':'MT90-987654321','user_pick':'user17','pack_table':'D1','user_pack':'pack02','work_choice':'Pick & Pack'}",
    1,
)

old="\n".join([
"    imgs=sorted((OUT/d).glob('*.png')); assert len(imgs)==14,(d,len(imgs))",
"    for f in imgs:",
"        x=f.read_bytes(); assert x[:8]==b'\\x89PNG\\r\\n\\x1a\\n'; w,h=struct.unpack('>II',x[16:24]); assert (w,h)==wh,(f,(w,h),wh); assert len(x)>4000,(f,len(x))",
"    rows.append(f'{d}: screenshots=14 dimensions={W}x{H} exact_beta73=PASS owner_scope=HUMAN_GATE manual_visual_inspection=REQUIRED')",
]) + "\n"
new="\n".join([
"    # 8) Login branding: temporarily remove auth, capture launcher login, then restore fixture.",
"    auth_dst=f'/data/user/0/{PKG}/shared_prefs/pick_pack_auth_session_v2.xml'",
"    adb('shell','am','force-stop',PKG,check=False); adb('shell','rm','-f',auth_dst,check=False)",
"    adb('shell','am','start','-W','-n',f'{PKG}/vn.pickpack1291.app.beta.FullBetaActivity',check=False); time.sleep(1.5)",
"    rawshot(d,'15-login-logo-only-canonical-copyright')",
"    tmp='/data/local/tmp/'+auth.name; adb('push',str(auth),tmp); adb('shell','cp',tmp,auth_dst); adb('shell','chown',f'{uid}:{gid}',auth_dst); adb('shell','chmod','600',auth_dst)",
"",
"    # 9) Settings: route directly to Settings, then prove the correct screen before capture.",
"    def settings_marker(marker,tag):",
"        last=''",
"        for attempt in range(2):",
"            try:",
"                root=dump(OUT/d/f'{tag}-marker-{attempt+1}.xml'); last=all_text(root)",
"                if marker.casefold() in last.casefold(): return",
"            except Exception as exc:",
"                last=f'{type(exc).__name__}: {exc}'",
"            time.sleep(.35)",
"        raise AssertionError(f'Settings marker missing: {marker!r} ({tag})\\\\n{last[-4000:]}')",
"",
"    adb('shell','am','force-stop',PKG,check=False)",
"    r=adb('shell','am','start','-W','-n',f'{PKG}/{ACT}','--es','module','SETTINGS','--es','login','tamnv2','--es','name','Nguyen Van Tam','--es','role','ADMIN','--es','position','Chuyen vien Pick Pack 1291','--es','email','visual@example.invalid',check=False)",
"    record(f'settings-start-{d}.txt',r.stdout); time.sleep(1.0); resumed_check(d+'-settings-route')",
"    settings_marker('ĐỔI MẬT KHẨU','settings-top'); time.sleep(.45); settings_marker('ĐỔI MẬT KHẨU','settings-top-stable')",
"    rawshot(d,'16-settings-top')",
"",
"    # Scroll only inside content; verify lower Settings marker before the second capture.",
"    for _ in range(5): swipe(W*0.50,H*0.70,W*0.50,H*0.25,430,.35)",
"    settings_marker('NHẬT KÝ','settings-lower'); time.sleep(.45); settings_marker('NHẬT KÝ','settings-lower-stable')",
"    rawshot(d,'17-settings-storage-update-log'); resumed_check(d+'-settings')",
"",
"    imgs=sorted((OUT/d).glob('*.png')); assert len(imgs)==17,(d,len(imgs))",
"    for f in imgs:",
"        x=f.read_bytes(); assert x[:8]==b'\\x89PNG\\r\\n\\x1a\\n'; w,h=struct.unpack('>II',x[16:24]); assert (w,h)==wh,(f,(w,h),wh); assert len(x)>4000,(f,len(x))",
"    rows.append(f'{d}: screenshots=17 dimensions={W}x{H} exact_beta73=PASS owner_scope=HUMAN_GATE manual_visual_inspection=REQUIRED')",
]) + "\n"
if old not in src:
    raise SystemExit('Beta72 screenshot-count anchor drift')
src=src.replace(old,new,1)
'''
if needle not in wrapper:
    raise SystemExit('Beta72 exec anchor drift')
wrapper=wrapper.replace(needle,inject+"\n"+needle,1)
exec(compile(wrapper,'run_beta73_visual.wrapper.py','exec'),{'__name__':'__main__','__file__':str(Path(__file__).with_name('run_beta72_visual.py'))})
