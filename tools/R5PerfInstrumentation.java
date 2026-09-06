package vn.pickpack1291.verify;

import android.app.Activity;
import android.app.Application;
import android.app.Instrumentation;
import android.app.UiAutomation;
import android.content.Context;
import android.content.Intent;
import android.graphics.Rect;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.accessibility.AccessibilityNodeInfo;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONObject;

/** R5 exact-candidate local realtime latency gate. Network is disabled by the caller. */
public final class R5PerfInstrumentation extends Instrumentation {
  private static final String PKG="vn.pickpack1291.app.beta.publicbeta";
  private static final String ACT="vn.pickpack1291.app.beta.OperationsActivity";
  private UiAutomation ui;
  private Context target;
  private volatile Activity currentActivity;

  @Override public void onCreate(Bundle b){super.onCreate(b);start();}
  @Override public void onStart(){
    try{
      target=getTargetContext();ui=getUiAutomation();
      Application app=(Application)target.getApplicationContext();
      app.registerActivityLifecycleCallbacks(new Application.ActivityLifecycleCallbacks(){
        @Override public void onActivityCreated(Activity a,Bundle b){}
        @Override public void onActivityStarted(Activity a){}
        @Override public void onActivityResumed(Activity a){if(PKG.equals(a.getPackageName()))currentActivity=a;}
        @Override public void onActivityPaused(Activity a){}
        @Override public void onActivityStopped(Activity a){}
        @Override public void onActivitySaveInstanceState(Activity a,Bundle b){}
        @Override public void onActivityDestroyed(Activity a){if(currentActivity==a)currentActivity=null;}
      });
      runGate();
    }catch(Throwable t){Bundle x=new Bundle();x.putString("error",t.getClass().getSimpleName()+":"+String.valueOf(t.getMessage()));finish(1,x);}
  }

  private static void require(boolean v,String msg){if(!v)throw new IllegalStateException(msg);}
  private AccessibilityNodeInfo root(){return ui.getRootInActiveWindow();}
  private static String textOf(AccessibilityNodeInfo n){CharSequence t=n.getText();if(t!=null&&!t.toString().trim().isEmpty())return t.toString().trim();CharSequence d=n.getContentDescription();return d==null?"":d.toString().trim();}
  private AccessibilityNodeInfo clickable(AccessibilityNodeInfo n){for(AccessibilityNodeInfo x=n;x!=null;x=x.getParent())if(x.isClickable())return x;return null;}
  private AccessibilityNodeInfo findText(String needle){
    AccessibilityNodeInfo r=root();if(r==null)return null;String q=needle.trim().toUpperCase(Locale.ROOT);ArrayDeque<AccessibilityNodeInfo> dq=new ArrayDeque<>();dq.add(r);
    while(!dq.isEmpty()){AccessibilityNodeInfo n=dq.removeFirst();if(textOf(n).toUpperCase(Locale.ROOT).contains(q))return n;for(int i=0;i<n.getChildCount();i++){AccessibilityNodeInfo c=n.getChild(i);if(c!=null)dq.addLast(c);}}
    return null;
  }
  private AccessibilityNodeInfo waitText(String text,long timeout){long end=SystemClock.uptimeMillis()+timeout;while(SystemClock.uptimeMillis()<end){AccessibilityNodeInfo n=findText(text);if(n!=null)return n;SystemClock.sleep(10L);}throw new IllegalStateException("TEXT_TIMEOUT:"+text);}
  private AccessibilityNodeInfo findEditable(){
    AccessibilityNodeInfo r=root();if(r==null)return null;ArrayDeque<AccessibilityNodeInfo> dq=new ArrayDeque<>();dq.add(r);
    while(!dq.isEmpty()){AccessibilityNodeInfo n=dq.removeFirst();String cls=String.valueOf(n.getClassName());CharSequence h=n.getHintText();String hint=h==null?"":h.toString().toUpperCase(Locale.ROOT);if((n.isEditable()||cls.contains("EditText"))&&(hint.contains("MÃ NHÂN VIÊN")||hint.contains("SCAN")))return n;for(int i=0;i<n.getChildCount();i++){AccessibilityNodeInfo c=n.getChild(i);if(c!=null)dq.addLast(c);}}
    return null;
  }
  private void clickText(String text){AccessibilityNodeInfo n=waitText(text,12000L),c=clickable(n);require(c!=null,"CLICK_MISSING:"+text);if(!c.performAction(AccessibilityNodeInfo.ACTION_CLICK)){Rect b=new Rect();c.getBoundsInScreen(b);require(!b.isEmpty(),"CLICK_BOUNDS_EMPTY:"+text);try{ui.executeShellCommand("input tap "+b.centerX()+" "+b.centerY()).close();}catch(Exception e){throw new RuntimeException(e);}}}

  private void seedAuth(){
    target.getSharedPreferences("pick_pack_auth_session_v2",Context.MODE_PRIVATE).edit().putString("token","r5-perf-local").putString("login_id","r5_perf").putString("display_name","R5 Perf").putString("role","SUPERADMIN").putString("position","TEST").putString("email","verify@example.invalid").commit();
    target.getSharedPreferences("pp_m2_service_transport",Context.MODE_PRIVATE).edit().putString("service_token","offline-r5-perf").putString("discovery_json","{\"ok\":true,\"authority_mode\":\"SERVICE_PRIMARY\",\"service_url\":\"http://127.0.0.1:1\"}").putLong("discovery_at",System.currentTimeMillis()).commit();
  }
  private void seedData(String mnv)throws Exception{
    String today=LocalDate.now(ZoneId.of("Asia/Ho_Chi_Minh")).toString();ClassLoader cl=target.getClassLoader();
    JSONObject master=new JSONObject().put("ok",true).put("master_revision",129001L).put("staff",new JSONArray().put(new JSONObject().put("mnv",mnv).put("full_name","R5 Perf Employee").put("phone","0900000129").put("start_date","06/09/2026").put("main_position","PICK").put("supplier","TEST").put("department","OPS").put("site","1291").put("warehouse","HY1"))).put("pdas",new JSONArray()).put("pda_statuses",new JSONArray().put("Tốt")).put("user_picks",new JSONArray()).put("pack_bundles",new JSONArray());
    Class<?> mc=cl.loadClass("vn.pickpack1291.app.beta.MasterDataCache");Object mo=mc.getField("INSTANCE").get(null);mc.getMethod("save",Context.class,JSONObject.class).invoke(mo,target,master);
    JSONObject session=new JSONObject().put("session_id","r5-perf-active").put("mnv",mnv).put("business_date",today).put("shift","Ca 1").put("state","ACTIVE").put("enter_at",today+"T01:00:00Z").put("exit_at","").put("version",1).put("work_choice","PICK").put("positions_v64",new JSONArray().put(new JSONObject().put("position_key","PICK").put("position_label","Pick").put("state","ACTIVE"))).put("resource_assignments_v64",new JSONArray());
    JSONObject day=new JSONObject().put("business_date",today).put("day_revision",129001L).put("sessions",new JSONArray().put(session)).put("events",new JSONArray()).put("labor",new JSONArray());
    Class<?> sc=cl.loadClass("vn.pickpack1291.app.beta.OperationalDataStore");Object store=sc.getConstructor(Context.class).newInstance(target);sc.getMethod("saveDay",JSONObject.class).invoke(store,day);
  }
  private Activity openBusiness(){
    Intent i=new Intent();i.setClassName(target,ACT);i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_CLEAR_TASK);i.putExtra("module","BUSINESS");i.putExtra("login","r5_perf");i.putExtra("name","R5 Perf");i.putExtra("role","SUPERADMIN");i.putExtra("position","TEST");i.putExtra("email","verify@example.invalid");target.startActivity(i);
    long end=SystemClock.uptimeMillis()+12000L;while(SystemClock.uptimeMillis()<end){Activity a=currentActivity;AccessibilityNodeInfo r=root();if(a!=null&&ACT.equals(a.getClass().getName())&&r!=null&&PKG.equals(String.valueOf(r.getPackageName())))return a;SystemClock.sleep(20L);}throw new IllegalStateException("ACTIVITY_TIMEOUT");
  }
  private void openEmployee(String mnv){
    clickText("Quét QR nhân sự");long end=SystemClock.uptimeMillis()+12000L;AccessibilityNodeInfo n=null;while(SystemClock.uptimeMillis()<end&&(n=findEditable())==null)SystemClock.sleep(10L);require(n!=null,"EMPLOYEE_INPUT_MISSING");Bundle b=new Bundle();b.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,mnv);require(n.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT,b),"SET_MNV_FAILED");try{ui.executeShellCommand("input keyevent 66").close();}catch(Exception e){throw new RuntimeException(e);}waitText("THÔNG TIN CA",12000L);AccessibilityNodeInfo timeline=waitText("DIỄN BIẾN CÔNG VIỆC TRONG CA",12000L);timeline.performAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_SHOW_ON_SCREEN.getId());SystemClock.sleep(100L);
  }

  private long patchOnce(Object store,Method apply,Field callbackField,String date,String mnv,int i)throws Exception{
    String marker="R5-PERF-"+i;JSONObject before=new JSONObject().put("user_pack","PACK-OLD");JSONObject after=new JSONObject().put("user_pack",marker);JSONObject payload=new JSONObject().put("session_id","r5-perf-active").put("mnv",mnv).put("mutation_kind","EDIT").put("before",before).put("after",after);
    JSONObject event=new JSONObject().put("event_id","r5-perf-event-"+i).put("event_type","RESOURCE_CHANGE").put("session_id","r5-perf-active").put("mnv",mnv).put("actor",marker).put("committed_at",date+"T01:25:00Z").put("payload_json",payload.toString());JSONArray items=new JSONArray().put(new JSONObject().put("compat_event",event));
    Activity a=currentActivity;require(a!=null,"ACTIVITY_LOST");Object callback=callbackField.get(a);require(callback!=null,"REALTIME_CALLBACK_MISSING");Set<String> changed=new HashSet<>();changed.add(date);
    long start=SystemClock.elapsedRealtimeNanos();Object ok=apply.invoke(store,date,129002L+i,items);require(Boolean.TRUE.equals(ok),"DAY_DELTA_APPLY_FAILED:"+i);final Throwable[] failure=new Throwable[1];runOnMainSync(new Runnable(){@Override public void run(){try{callback.getClass().getMethod("invoke",Object.class).invoke(callback,changed);}catch(Throwable t){failure[0]=t;}}});if(failure[0]!=null)throw new IllegalStateException("UI_CALLBACK_FAILED",failure[0]);
    long deadline=SystemClock.uptimeMillis()+2000L;while(SystemClock.uptimeMillis()<deadline){if(findText("Người thực hiện: "+marker)!=null)return (SystemClock.elapsedRealtimeNanos()-start)/1_000_000L;SystemClock.sleep(2L);}throw new IllegalStateException("UI_MARKER_TIMEOUT:"+marker);
  }

  private void runGate()throws Exception{
    String mnv="981820081";seedAuth();seedData(mnv);Activity a=openBusiness();openEmployee(mnv);String date=LocalDate.now(ZoneId.of("Asia/Ho_Chi_Minh")).toString();Class<?> sc=target.getClassLoader().loadClass("vn.pickpack1291.app.beta.OperationalDataStore");Object store=sc.getConstructor(Context.class).newInstance(target);Method apply=sc.getMethod("applyDayDelta",String.class,long.class,JSONArray.class);Field cb=a.getClass().getDeclaredField("employeeTimelineRealtimeRefresh");cb.setAccessible(true);
    for(int i=0;i<10;i++)patchOnce(store,apply,cb,date,mnv,i);
    long[] ms=new long[50];for(int i=0;i<ms.length;i++)ms[i]=patchOnce(store,apply,cb,date,mnv,100+i);Arrays.sort(ms);long p50=ms[24],p95=ms[47],p99=ms[49],max=ms[49];require(p95<=100L,"R5_LOCAL_UI_P95_EXCEEDED:"+p95);
    Bundle out=new Bundle();out.putString("r5_local_ui_status","PASS");out.putLong("r5_local_ui_p50_ms",p50);out.putLong("r5_local_ui_p95_ms",p95);out.putLong("r5_local_ui_p99_ms",p99);out.putLong("r5_local_ui_max_ms",max);out.putInt("r5_local_ui_samples",ms.length);out.putString("r5_local_ui_measurement","applyDayDelta_plus_employeeTimelineRealtimeRefresh_to_accessibility_visible");System.out.println("R5_LOCAL_UI_P95_PASS p50="+p50+" p95="+p95+" p99="+p99+" max="+max+" samples="+ms.length);finish(0,out);
  }
}
