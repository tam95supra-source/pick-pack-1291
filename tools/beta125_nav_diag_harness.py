#!/usr/bin/env python3
from pathlib import Path
p=Path('tools/Beta83UiChecksInstrumentation.java')
s=p.read_text(encoding='utf-8')
nav='''  private String navState(){\n    try{\n      Activity a=currentActivity;\n      if(a==null)return "activity=null";\n      Class<?> c=a.getClass();\n      Field ss=c.getDeclaredField("screenState");ss.setAccessible(true);\n      Field ds=c.getDeclaredField("displayedScreenState");ds.setAccessible(true);\n      Field bs=c.getDeclaredField("screenBackStack");bs.setAccessible(true);\n      Object raw=bs.get(a);\n      java.util.ArrayDeque<?> dq=(java.util.ArrayDeque<?>)raw;\n      Object top=dq.peekLast();\n      String topState="";\n      if(top!=null){Field ts=top.getClass().getDeclaredField("screenState");ts.setAccessible(true);topState=String.valueOf(ts.get(top));}\n      return "screen="+String.valueOf(ss.get(a))+",displayed="+String.valueOf(ds.get(a))+",stack="+dq.size()+",top="+topState;\n    }catch(Throwable t){return "diag_error="+t.getClass().getSimpleName()+":"+String.valueOf(t.getMessage());}\n  }\n'''
nav_new=nav+'''\n  private String visibleTextSummary(){\n    AccessibilityNodeInfo r=root();if(r==null)return "root=null";\n    StringBuilder b=new StringBuilder();\n    ArrayDeque<AccessibilityNodeInfo> q=new ArrayDeque<>();q.add(r);int count=0;\n    while(!q.isEmpty()&&count<40){\n      AccessibilityNodeInfo n=q.removeFirst();String t=textOf(n);\n      if(t!=null&&!t.trim().isEmpty()){if(b.length()>0)b.append(" | ");b.append(t.replace("\\n"," "));count++;}\n      for(int i=0;i<n.getChildCount();i++){AccessibilityNodeInfo c=n.getChild(i);if(c!=null)q.addLast(c);}\n    }\n    return b.toString();\n  }\n'''
if 'private String visibleTextSummary()' not in s:
    if s.count(nav)!=1: raise SystemExit(f'NAV_HELPER_COUNT={s.count(nav)}')
    s=s.replace(nav,nav_new,1)
frag='''    mark("post_scan_roster_hidden_beta124");\n    String navBefore=navState();\n    invokeActivityBack();\n    String navAfter=navState();\n    AccessibilityNodeInfo qrBack=findText("QUÉT QR NHÂN SỰ",true,false);\n    require(qrBack!=null,"BETA125_BACK_NAV_DIAG:"+navBefore+"=>"+navAfter);\n    mark("post_scan_activity_back_beta124");\n'''
frag_new='''    mark("post_scan_roster_hidden_beta124");\n    String navBefore=navState();\n    invokeActivityBack();\n    SystemClock.sleep(1200L);\n    String navAfter=navState();\n    shot(tag+"-04b-beta125-back-scan");\n    AccessibilityNodeInfo qrBack=findText("QUÉT QR NHÂN SỰ",true,false);\n    require(qrBack!=null,"BETA125_BACK_NAV_VISUAL_DIAG:"+navBefore+"=>"+navAfter+";texts="+visibleTextSummary());\n    mark("post_scan_activity_back_beta124");\n'''
if s.count(frag)!=1: raise SystemExit(f'DIAG_FRAG_COUNT={s.count(frag)}')
s=s.replace(frag,frag_new,1)
p.write_text(s,encoding='utf-8')
print('beta125_nav_visual_diag_harness=PASS')
