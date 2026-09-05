#!/usr/bin/env python3
from pathlib import Path
p=Path('tools/Beta83UiChecksInstrumentation.java')
s=p.read_text(encoding='utf-8')
helper='''  private void invokeActivityBack(){\n    Activity a=currentActivity;\n    require(a!=null&&PKG.equals(a.getPackageName()),"CURRENT_ACTIVITY_MISSING_BACK");\n    runOnMainSync(new Runnable(){@Override public void run(){a.onBackPressed();}});\n    SystemClock.sleep(450L);\n  }\n'''
helper_new=helper+'''\n  private String navState(){\n    try{\n      Activity a=currentActivity;\n      if(a==null)return "activity=null";\n      Class<?> c=a.getClass();\n      Field ss=c.getDeclaredField("screenState");ss.setAccessible(true);\n      Field ds=c.getDeclaredField("displayedScreenState");ds.setAccessible(true);\n      Field bs=c.getDeclaredField("screenBackStack");bs.setAccessible(true);\n      Object raw=bs.get(a);\n      java.util.ArrayDeque<?> dq=(java.util.ArrayDeque<?>)raw;\n      Object top=dq.peekLast();\n      String topState="";\n      if(top!=null){Field ts=top.getClass().getDeclaredField("screenState");ts.setAccessible(true);topState=String.valueOf(ts.get(top));}\n      return "screen="+String.valueOf(ss.get(a))+",displayed="+String.valueOf(ds.get(a))+",stack="+dq.size()+",top="+topState;\n    }catch(Throwable t){return "diag_error="+t.getClass().getSimpleName()+":"+String.valueOf(t.getMessage());}\n  }\n'''
if s.count(helper)!=1: raise SystemExit(f'HELPER_COUNT={s.count(helper)}')
s=s.replace(helper,helper_new,1)
frag='''    mark("post_scan_roster_hidden_beta124");\n    invokeActivityBack();\n    waitText("QUÉT QR NHÂN SỰ",true,false,10000L);\n    mark("post_scan_activity_back_beta124");\n'''
frag_new='''    mark("post_scan_roster_hidden_beta124");\n    String navBefore=navState();\n    invokeActivityBack();\n    String navAfter=navState();\n    AccessibilityNodeInfo qrBack=findText("QUÉT QR NHÂN SỰ",true,false);\n    require(qrBack!=null,"BETA125_BACK_NAV_DIAG:"+navBefore+"=>"+navAfter);\n    mark("post_scan_activity_back_beta124");\n'''
if s.count(frag)!=1: raise SystemExit(f'FRAG_COUNT={s.count(frag)}')
s=s.replace(frag,frag_new,1)
p.write_text(s,encoding='utf-8')
print('beta125_nav_diag_harness=PASS')
