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

probe='def build_ui_probe():\n    sdk=Path(os.environ[\'ANDROID_HOME\'])\n    bt=sorted([p for p in (sdk/\'build-tools\').iterdir() if p.is_dir()],key=lambda p:[int(x) if x.isdigit() else 0 for x in re.split(r\'[^0-9]+\',p.name)],reverse=True)[0]\n    android_jar=sdk/\'platforms\'/\'android-29\'/\'android.jar\'\n    work=OUT/\'ui-probe\'; shutil.rmtree(work,ignore_errors=True); (work/\'classes\').mkdir(parents=True); (work/\'dex\').mkdir()\n    java=work/\'UiProbe.java\'\n    java.write_text(\'package pp.visual.probe;\\nimport android.app.Activity;\\nimport android.app.Instrumentation;\\nimport android.app.UiAutomation;\\nimport android.os.Bundle;\\nimport android.view.accessibility.AccessibilityNodeInfo;\\npublic class UiProbe extends Instrumentation {\\n  @Override public void onStart() {\\n    Bundle out=new Bundle();\\n    try {\\n      UiAutomation ui=getUiAutomation();\\n      AccessibilityNodeInfo root=ui.getRootInActiveWindow();\\n      StringBuilder sb=new StringBuilder();\\n      walk(root,sb);\\n      out.putString("stream","PP_UI_PROBE_BEGIN\\\\n"+sb.toString()+"PP_UI_PROBE_END");\\n      finish(Activity.RESULT_OK,out);\\n    } catch(Throwable t) {\\n      out.putString("stream","PP_UI_PROBE_ERROR:"+t.getClass().getName()+":"+String.valueOf(t.getMessage()));\\n      finish(Activity.RESULT_CANCELED,out);\\n    }\\n  }\\n  private static void walk(AccessibilityNodeInfo n,StringBuilder sb) {\\n    if(n==null)return;\\n    CharSequence t=n.getText(),d=n.getContentDescription();\\n    if(t!=null && t.length()>0)sb.append(t).append(\\\'\\\\n\\\');\\n    if(d!=null && d.length()>0)sb.append(d).append(\\\'\\\\n\\\');\\n    for(int i=0;i<n.getChildCount();i++){AccessibilityNodeInfo c=n.getChild(i);walk(c,sb);if(c!=null)c.recycle();}\\n  }\\n}\\n\',encoding=\'utf-8\')\n    manifest=work/\'AndroidManifest.xml\'\n    manifest.write_text(\'<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="pp.visual.probe"><uses-sdk android:minSdkVersion="23" android:targetSdkVersion="29"/><application android:label="PP Visual Probe"/><instrumentation android:name="pp.visual.probe.UiProbe" android:targetPackage="pp.visual.probe"/></manifest>\',encoding=\'utf-8\')\n    run([\'javac\',\'-source\',\'8\',\'-target\',\'8\',\'-classpath\',str(android_jar),\'-d\',str(work/\'classes\'),str(java)])\n    run([str(bt/\'d8\'),\'--min-api\',\'23\',\'--lib\',str(android_jar),\'--output\',str(work/\'dex\'),str(work/\'classes\'/\'pp\'/\'visual\'/\'probe\'/\'UiProbe.class\')])\n    unsigned=work/\'probe-unsigned.apk\'; signed=work/\'probe.apk\'; ks=work/\'probe.jks\'\n    run([str(bt/\'aapt\'),\'package\',\'-f\',\'-M\',str(manifest),\'-I\',str(android_jar),\'-F\',str(unsigned)])\n    run([\'zip\',\'-q\',\'-j\',str(unsigned),str(work/\'dex\'/\'classes.dex\')])\n    run([\'keytool\',\'-genkeypair\',\'-keystore\',str(ks),\'-storepass\',\'android\',\'-keypass\',\'android\',\'-alias\',\'androiddebugkey\',\'-dname\',\'CN=Android Debug,O=Android,C=US\',\'-keyalg\',\'RSA\',\'-keysize\',\'2048\',\'-validity\',\'10000\',\'-noprompt\'])\n    run([str(bt/\'apksigner\'),\'sign\',\'--ks\',str(ks),\'--ks-key-alias\',\'androiddebugkey\',\'--ks-pass\',\'pass:android\',\'--key-pass\',\'pass:android\',\'--out\',str(signed),str(unsigned)])\n    adb(\'install\',\'-r\',str(signed))\n    return \'pp.visual.probe/.UiProbe\'\n\nUI_PROBE=build_ui_probe()\ndef probe_text(tag):\n    r=adb(\'shell\',\'am\',\'instrument\',\'-w\',UI_PROBE,check=False)\n    record(f\'probe-{tag}.txt\',r.stdout)\n    if \'PP_UI_PROBE_ERROR:\' in r.stdout: raise AssertionError(r.stdout[-3000:])\n    return r.stdout\n'
marker="matrix=[('320x568','160',(320,568)),('360x640','160',(360,640)),('480x800','240',(480,800))]"
if marker not in src:
    raise SystemExit('matrix anchor drift')
src=src.replace(marker,probe+'\n'+marker,1)

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
"            last=probe_text(f'{d}-{tag}-{attempt+1}')",
"            if marker.casefold() in last.casefold(): return",
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
