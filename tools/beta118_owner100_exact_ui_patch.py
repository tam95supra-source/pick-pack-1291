#!/usr/bin/env python3
import json,re
from pathlib import Path

src_path=Path('tools/Beta83UiChecksInstrumentation.java')
src=src_path.read_text(encoding='utf-8')
receipt=json.loads(Path('ops/beta118-owner-seed-100-sessions-receipt.json').read_text(encoding='utf-8'))
items=receipt['items']
assert receipt['status']=='PASS' and receipt['count']==100 and len(items)==100
assert len({x['mnv'] for x in items})==100 and len({x['session_id'] for x in items})==100

def j(s): return json.dumps(str(s),ensure_ascii=False)
rows=',\n      '.join('{'+','.join(j(x[k]) for k in ('mnv','position','shift','session_id'))+'}' for x in items)
counts={k:sum(1 for x in items if x['shift'].strip().casefold()==k.casefold()) for k in ('CA 1','CA HC','CA 2')}
assert sum(counts.values())==100

needle='else if("service-discovery".equals(mode))runServiceDiscoveryCacheRegression(true);'
assert needle in src
src=src.replace(needle,'else if("owner100".equals(mode))runOwner100Exact();\n      '+needle,1)

start=src.index('  private void verifyOwner100SessionProjection(')
end=src.index('  private void runChecks()',start)
method=f'''  private Set<String> ownerSeedMnvsInTree(){{
    Set<String> out=new HashSet<>();AccessibilityNodeInfo r=root();if(r==null)return out;
    ArrayDeque<AccessibilityNodeInfo> q=new ArrayDeque<>();q.add(r);
    while(!q.isEmpty()){{AccessibilityNodeInfo n=q.removeFirst();String t=textOf(n);
      if(t.startsWith("OWNER-SEED • ")){{String[] p=t.split(" • ");if(p.length>=3)out.add(p[1].trim());}}
      for(int i=0;i<n.getChildCount();i++){{AccessibilityNodeInfo c=n.getChild(i);if(c!=null)q.addLast(c);}}
    }}return out;
  }}
  private void collectViewTexts(android.view.View v,Set<String> out){{
    if(v instanceof android.widget.TextView){{CharSequence t=((android.widget.TextView)v).getText();if(t!=null)out.add(t.toString().trim());}}
    if(v instanceof android.view.ViewGroup){{android.view.ViewGroup g=(android.view.ViewGroup)v;for(int i=0;i<g.getChildCount();i++)collectViewTexts(g.getChildAt(i),out);}}
  }}
  private Set<String> activityViewTexts(Activity a){{
    Set<String> out=java.util.Collections.synchronizedSet(new HashSet<String>());
    runOnMainSync(new Runnable(){{@Override public void run(){{collectViewTexts(a.getWindow().getDecorView(),out);}}}});return new HashSet<>(out);
  }}
  private static String canonicalOwnerShift(String raw){{String v=raw.trim();if(v.equalsIgnoreCase("CA 1"))return "Ca 1";if(v.equalsIgnoreCase("CA HC"))return "Ca HC";if(v.equalsIgnoreCase("CA 2"))return "Ca 2";return v;}}

  private void runOwner100Exact()throws Exception{{
    seedAuth();seedService();
    String today=LocalDate.now(ZoneId.of("Asia/Ho_Chi_Minh")).toString();
    require({j(receipt['business_date'])}.equals(today),"OWNER100_BUSINESS_DATE_MISMATCH:"+today);
    String[][] rows=new String[][]{{
      {rows}
    }};
    Set<String> expectedAll=new HashSet<>();Set<String> expectedSessions=new HashSet<>();JSONArray sessions=new JSONArray();
    java.util.Map<String,Set<String>> expectedByShift=new java.util.LinkedHashMap<>();
    expectedByShift.put("Ca 1",new HashSet<String>());expectedByShift.put("Ca HC",new HashSet<String>());expectedByShift.put("Ca 2",new HashSet<String>());
    java.util.Map<String,String> expectedPosition=new java.util.HashMap<>();
    for(String[] x:rows){{String mnv=x[0],pos=x[1],shift=x[2],sid=x[3];String c=canonicalOwnerShift(shift);
      require(expectedAll.add(mnv),"OWNER100_DUP_MNV:"+mnv);require(expectedSessions.add(sid),"OWNER100_DUP_SESSION:"+sid);expectedByShift.get(c).add(mnv);expectedPosition.put(mnv,pos);
      JSONObject snap=new JSONObject().put("supplier","OWNER-SEED").put("full_name","OWNER "+mnv).put("main_position",pos);
      sessions.put(new JSONObject().put("session_id",sid).put("mnv",mnv).put("business_date",today).put("shift",shift).put("state","ACTIVE")
        .put("enter_at",today+"T01:00:00Z").put("exit_at","").put("version",1).put("employee_snapshot",snap));
    }}
    require(expectedAll.size()==100&&expectedSessions.size()==100,"OWNER100_EXPECTED_SET_NOT_100");
    Class<?> storeClass=target.getClassLoader().loadClass("vn.pickpack1291.app.beta.OperationalDataStore");
    Object store=storeClass.getConstructor(Context.class).newInstance(target);Method saveDay=storeClass.getMethod("saveDay",JSONObject.class);
    saveDay.invoke(store,new JSONObject().put("business_date",today).put("day_revision",118100L).put("sessions",sessions).put("events",new JSONArray()).put("labor",new JSONArray()));

    Activity a=open("BUSINESS");
    for(java.util.Map.Entry<String,Set<String>> e:expectedByShift.entrySet())waitText(e.getKey()+" – "+e.getValue().size()+"/0",true,false,12000L);
    Set<String> actualAll=new HashSet<>();
    for(java.util.Map.Entry<String,Set<String>> e:expectedByShift.entrySet()){{
      String shift=e.getKey();int n=e.getValue().size();clickText(shift+" – "+n+"/0",true,12000L);waitText(shift+" • Vào "+n+" / Ra 0",true,false,12000L);
      SystemClock.sleep(600L);Set<String> actual=ownerSeedMnvsInTree();
      require(actual.equals(e.getValue()),"OWNER100_REVIEW_SET_DIFF:"+shift+":expected="+e.getValue().size()+":actual="+actual.size());actualAll.addAll(actual);
      clickText("Đóng",true,8000L);SystemClock.sleep(250L);
    }}
    Set<String> expectedMinus=new HashSet<>(expectedAll);expectedMinus.removeAll(actualAll);Set<String> actualMinus=new HashSet<>(actualAll);actualMinus.removeAll(expectedAll);
    require(expectedMinus.isEmpty(),"OWNER100_EXPECTED_MINUS_UI:"+expectedMinus);require(actualMinus.isEmpty(),"OWNER100_UI_MINUS_EXPECTED:"+actualMinus);require(actualAll.size()==100,"OWNER100_UI_UNIQUE_NOT_100:"+actualAll.size());

    Method detail=a.getClass().getDeclaredMethod("showCurrentDayShiftStaff",String.class,String.class,java.util.List.class,String.class);detail.setAccessible(true);
    for(java.util.Map.Entry<String,Set<String>> e:expectedByShift.entrySet()){{
      String shift=e.getKey();java.util.ArrayList<JSONObject> group=new java.util.ArrayList<>();for(int i=0;i<sessions.length();i++){{JSONObject s=sessions.getJSONObject(i);if(canonicalOwnerShift(s.getString("shift")).equals(shift))group.add(s);}}
      final Throwable[] failure=new Throwable[1];runOnMainSync(new Runnable(){{@Override public void run(){{try{{detail.invoke(a,today,shift,group,"ALL");}}catch(Throwable t){{failure[0]=t;}}}}}});if(failure[0]!=null)throw new IllegalStateException("OWNER100_DETAIL_RENDER_FAILED",failure[0]);
      long until=SystemClock.uptimeMillis()+10000L;Set<String> texts=new HashSet<>();while(SystemClock.uptimeMillis()<until){{SystemClock.sleep(250L);texts=activityViewTexts(a);int found=0;for(String mnv:e.getValue())if(texts.contains("MNV: "+mnv+" • "+expectedPosition.get(mnv)))found++;if(found==e.getValue().size())break;}}
      for(String mnv:e.getValue())require(texts.contains("MNV: "+mnv+" • "+expectedPosition.get(mnv)),"OWNER100_POSITION_UI_MISSING:"+mnv+":"+expectedPosition.get(mnv));
      require(texts.contains("Trong ca ("+e.getValue().size()+")"),"OWNER100_ACTIVE_COUNT_MISSING:"+shift);require(texts.contains("Đã ra ca (0)"),"OWNER100_EXIT_ZERO_MISSING:"+shift);
    }}
    Bundle done=new Bundle();done.putString("owner100_exact_ui","PASS");done.putString("expected_count","100");done.putString("actual_count",String.valueOf(actualAll.size()));done.putString("expected_minus_actual","0");done.putString("actual_minus_expected","0");done.putString("positions","PASS");done.putString("in_only","PASS");finish(0,done);
  }}

  private void verifyOwner100SessionProjection(String mnv,String mnv2,String mnv3)throws Exception{{runOwner100Exact();}}

'''
src=src[:start]+method+src[end:]
src_path.write_text(src,encoding='utf-8')
print('BETA118_OWNER100_EXACT_UI_PATCH_READY',len(items),counts)
