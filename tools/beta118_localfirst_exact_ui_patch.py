#!/usr/bin/env python3
from pathlib import Path

p=Path('tools/Beta83UiChecksInstrumentation.java')
s=p.read_text(encoding='utf-8')
needle='else if("service-discovery".equals(mode))runServiceDiscoveryCacheRegression(true);'
assert needle in s
s=s.replace(needle,'else if("localfirst118".equals(mode))runLocalFirst118Exact();\n      '+needle,1)
insert=s.index('  private void runChecks()')
method=r'''
  private void invokePrivateUiCallback(final Activity a,String field)throws Exception{
    final Throwable[] err=new Throwable[1];runOnMainSync(new Runnable(){@Override public void run(){try{
      java.lang.reflect.Field f=a.getClass().getDeclaredField(field);f.setAccessible(true);Object cb=f.get(a);require(cb!=null,"CALLBACK_NULL:"+field);cb.getClass().getMethod("invoke").invoke(cb);
    }catch(Throwable t){err[0]=t;}}});if(err[0]!=null)throw new IllegalStateException("CALLBACK_FAILED:"+field,err[0]);
  }
  private void invokePatchLabor(final Activity a,final JSONObject row)throws Exception{
    final Throwable[] err=new Throwable[1];final Method m=a.getClass().getDeclaredMethod("patchLaborCacheOptimistic",JSONObject.class);m.setAccessible(true);
    runOnMainSync(new Runnable(){@Override public void run(){try{m.invoke(a,row);}catch(Throwable t){err[0]=t;}}});if(err[0]!=null)throw new IllegalStateException("PATCH_LABOR_FAILED",err[0]);
  }
  private JSONObject laborRow(String date,String id,String mnv,String name)throws Exception{return new JSONObject().put("labor_id",id).put("mnv",mnv).put("business_date",date).put("shift","Ca 1").put("labor_type","Công nhật").put("state","OPEN").put("start_at",date+"T01:00:00Z").put("end_at",JSONObject.NULL).put("note","").put("attendance_session_id","lf-session-"+mnv).put("full_name",name).put("supplier","LOCAL").put("position","Pick");}
  private JSONObject laborEvent(String id,String mnv)throws Exception{return new JSONObject().put("event_id","lf-event-"+id).put("event_type","LABOR_START").put("labor_id",id).put("entity_id",id).put("mnv",mnv).put("payload_json","{}");}
  private void saveLaborEvents(String date,int count)throws Exception{
    Class<?> c=target.getClassLoader().loadClass("vn.pickpack1291.app.beta.OperationalDataStore");Object store=c.getConstructor(Context.class).newInstance(target);Method save=c.getMethod("saveDay",JSONObject.class);JSONArray ev=new JSONArray();for(int i=1;i<=count;i++)ev.put(laborEvent("warn-"+i,"98LF"+i));
    save.invoke(store,new JSONObject().put("business_date",date).put("day_revision",118200L+count).put("sessions",new JSONArray()).put("events",ev).put("labor",new JSONArray()));
  }
  private void requireLaborEventsSaved(String date,int count)throws Exception{
    Class<?> c=target.getClassLoader().loadClass("vn.pickpack1291.app.beta.OperationalDataStore");Object store=c.getConstructor(Context.class).newInstance(target);JSONObject day=(JSONObject)c.getMethod("loadDay",String.class).invoke(store,date);require(day!=null,"LABOR_DAY_NOT_SAVED:"+date);JSONArray ev=day.optJSONArray("events");require(ev!=null&&ev.length()==count,"LABOR_EVENT_READBACK_MISMATCH:"+(ev==null?-1:ev.length())+":"+count);
  }
  private void finishActivity(final Activity a){
    runOnMainSync(new Runnable(){@Override public void run(){a.finish();}});long end=SystemClock.uptimeMillis()+3000L;while(SystemClock.uptimeMillis()<end&&currentActivity==a)SystemClock.sleep(100L);require(currentActivity!=a,"ACTIVITY_FINISH_TIMEOUT");SystemClock.sleep(200L);
  }
  private void requireTextStill(String text,long delay)throws Exception{SystemClock.sleep(delay);waitText(text,true,false,1000L);}
  private void runLocalFirst118Exact()throws Exception{
    seedAuth();seedService();String date=LocalDate.now(ZoneId.of("Asia/Ho_Chi_Minh")).toString();
    Activity labor=open("LABOR");
    invokePatchLabor(labor,laborRow(date,"lf-1","98LF001","LOCAL ONE"));
    invokePatchLabor(labor,laborRow(date,"lf-2","98LF002","LOCAL TWO"));
    long t0=SystemClock.uptimeMillis();invokePrivateUiCallback(labor,"laborLocalUiRefresh");
    waitText("Nhân sự: 2 • Đang làm: 2 • Tổng khoảng: 2",true,false,3000L);waitText("98LF001 • LOCAL ONE",true,false,3000L);waitText("98LF002 • LOCAL TWO",true,false,3000L);
    long twoMs=SystemClock.uptimeMillis()-t0;require(twoMs<500L,"LOCAL_TWO_RENDER_SLOW:"+twoMs);
    requireTextStill("Nhân sự: 2 • Đang làm: 2 • Tổng khoảng: 2",1800L);waitText("98LF001 • LOCAL ONE",true,false,1000L);waitText("98LF002 • LOCAL TWO",true,false,1000L);
    invokePatchLabor(labor,laborRow(date,"lf-3","98LF003","LOCAL THREE"));long t1=SystemClock.uptimeMillis();invokePrivateUiCallback(labor,"laborLocalUiRefresh");waitText("Nhân sự: 3 • Đang làm: 3 • Tổng khoảng: 3",true,false,3000L);long threeMs=SystemClock.uptimeMillis()-t1;require(threeMs<500L,"LOCAL_CALLBACK_RENDER_SLOW:"+threeMs);finishActivity(labor);

    saveLaborEvents(date,2);requireLaborEventsSaved(date,2);Activity business=open("BUSINESS");waitText("Quét QR nhân sự",true,false,3000L);long tw0=SystemClock.uptimeMillis();invokePrivateUiCallback(business,"laborWarningRealtimeRefresh");waitText("CẢNH BÁO: 2 CÔNG NHẬT CHƯA HOÀN THÀNH",true,false,3000L);long warningInitialMs=SystemClock.uptimeMillis()-tw0;require(warningInitialMs<500L,"LOCAL_WARNING_INITIAL_SLOW:"+warningInitialMs);
    saveLaborEvents(date,3);requireLaborEventsSaved(date,3);long tw=SystemClock.uptimeMillis();invokePrivateUiCallback(business,"laborWarningRealtimeRefresh");waitText("CẢNH BÁO: 3 CÔNG NHẬT CHƯA HOÀN THÀNH",true,false,3000L);long warningMs=SystemClock.uptimeMillis()-tw;require(warningMs<500L,"LOCAL_WARNING_RENDER_SLOW:"+warningMs);
    Bundle out=new Bundle();out.putString("localfirst_exact_ui","PASS");out.putString("two_rows_immediate","PASS");out.putString("stale_service_did_not_erase_two","PASS");out.putString("realtime_local_callback","PASS");out.putString("warning_local_callback","PASS");out.putString("snapshot_readback","PASS");out.putString("business_screen_confirmed","PASS");out.putString("two_rows_ms",String.valueOf(twoMs));out.putString("three_rows_ms",String.valueOf(threeMs));out.putString("warning_initial_ms",String.valueOf(warningInitialMs));out.putString("warning_ms",String.valueOf(warningMs));finish(0,out);
  }

'''
s=s[:insert]+method+s[insert:]
p.write_text(s,encoding='utf-8')
print('BETA118_LOCALFIRST_EXACT_UI_PATCH_READY')
