#!/usr/bin/env python3
from pathlib import Path
p=Path('tools/Beta83UiChecksInstrumentation.java')
s=p.read_text(encoding='utf-8')
anchor='''  private void runChecks()throws Exception{\n'''
method=r'''  private int countTextExact(String wanted){
    AccessibilityNodeInfo r=root();if(r==null)return 0;
    String q=wanted.trim().toUpperCase(Locale.ROOT);int count=0;
    ArrayDeque<AccessibilityNodeInfo> dq=new ArrayDeque<>();dq.add(r);
    while(!dq.isEmpty()){
      AccessibilityNodeInfo n=dq.removeFirst();
      if(textOf(n).toUpperCase(Locale.ROOT).equals(q))count++;
      for(int i=0;i<n.getChildCount();i++){AccessibilityNodeInfo c=n.getChild(i);if(c!=null)dq.addLast(c);}
    }
    return count;
  }

  private void verifyOwner100SessionProjection(String mnv,String mnv2,String mnv3)throws Exception{
    String today=LocalDate.now(ZoneId.of("Asia/Ho_Chi_Minh")).toString();
    Class<?> storeClass=target.getClassLoader().loadClass("vn.pickpack1291.app.beta.OperationalDataStore");
    Object store=storeClass.getConstructor(Context.class).newInstance(target);
    Method saveDay=storeClass.getMethod("saveDay",JSONObject.class);
    JSONArray sessions=new JSONArray();
    String[] shifts={"CA 1","CA HC","CA 2"};
    for(int i=1;i<=100;i++){
      String id=String.format(Locale.US,"owner-ui-%03d",i);
      String worker=String.format(Locale.US,"70%03d",i);
      sessions.put(new JSONObject().put("session_id",id).put("mnv",worker).put("business_date",today)
        .put("shift",shifts[(i-1)%3]).put("state","ACTIVE").put("enter_at",today+"T01:00:00Z")
        .put("exit_at","").put("version",1));
    }
    saveDay.invoke(store,new JSONObject().put("business_date",today).put("day_revision",99001L)
      .put("sessions",sessions).put("events",new JSONArray()).put("labor",new JSONArray()));

    open("BUSINESS");
    waitText("Ca 1 – 34/0",true,false,12000L);
    waitText("Ca HC – 33/0",true,false,12000L);
    waitText("Ca 2 – 33/0",true,false,12000L);
    clickText("Quét QR nhân sự",true,12000L);
    waitText("Danh sách QR vào / ra",true,false,12000L);
    waitText("Trong ca 34 • Đã ra 0",true,false,12000L);
    long end=SystemClock.uptimeMillis()+12000L;
    while(SystemClock.uptimeMillis()<end&&countTextExact("Trong ca 33 • Đã ra 0")<2)SystemClock.sleep(180L);
    require(countTextExact("Trong ca 33 • Đã ra 0")>=2,"OWNER100_QR_SHIFT_COUNTS_NOT_33_33");
    waitTextScrolling("70100",20000L);
    mark("owner_100_sessions_projection_beta118");

    seedData(mnv,mnv2,mnv3);
    open("BUSINESS");
  }

'''
if 'verifyOwner100SessionProjection' not in s:
    if anchor not in s: raise SystemExit('RUNCHECKS_ANCHOR_MISSING')
    s=s.replace(anchor,method+anchor,1)
call='''    verifyOwner100SessionProjection(mnv,mnv2,mnv3);\n'''
call_anchor='''    Activity business=open("BUSINESS");\n'''
if call not in s:
    if call_anchor not in s: raise SystemExit('CALL_ANCHOR_MISSING')
    s=s.replace(call_anchor,call_anchor+call,1)
p.write_text(s,encoding='utf-8')

q=Path('tools/beta83_verify_matrix.sh')
t=q.read_text(encoding='utf-8')
needle=' owner_actions_above_shift before_after_visible'
replace=' owner_actions_above_shift owner_100_sessions_projection_beta118 before_after_visible'
if replace not in t:
    if needle not in t: raise SystemExit('FLAG_ANCHOR_MISSING')
    t=t.replace(needle,replace,1)
q.write_text(t,encoding='utf-8')
print('BETA118_OWNER100_UI_HARNESS_PATCH_APPLIED')
