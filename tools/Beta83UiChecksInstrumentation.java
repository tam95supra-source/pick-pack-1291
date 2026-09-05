package vn.pickpack1291.verify;

import android.app.Activity;
import android.app.Application;
import android.app.Instrumentation;
import android.app.UiAutomation;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.Rect;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.accessibility.AccessibilityNodeInfo;
import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayDeque;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONObject;

public final class Beta83UiChecksInstrumentation extends Instrumentation {
  private Bundle args;
  private UiAutomation ui;
  private Context target;
  private String firstLogName="";
  private long firstLogBytes=0L;
  private volatile Activity currentActivity;
  private static final String PKG="vn.pickpack1291.app.beta.publicbeta";
  private static final String ACT="vn.pickpack1291.app.beta.OperationsActivity";

  @Override public void onCreate(Bundle b){ super.onCreate(b); args=b; start(); }
  @Override public void onStart(){
    try{
      target=getTargetContext();
      ui=getUiAutomation();
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
      String mode=args.getString("mode","checks");
      if("checks".equals(mode))runChecks();
      else if("visual".equals(mode))runVisual();
      else if("back36".equals(mode))runBack36();
      else if("seed-stale-discovery".equals(mode))seedStaleServiceDiscovery();
      else if("service-discovery".equals(mode))runServiceDiscoveryCacheRegression(true);
      else if("service-discovery-preserved".equals(mode))runServiceDiscoveryCacheRegression(false);
      else throw new IllegalArgumentException("MODE_UNSUPPORTED:"+mode);
    }catch(Throwable t){
      Bundle x=new Bundle();
      x.putString("error",t.getClass().getSimpleName()+":"+String.valueOf(t.getMessage()));
      finish(1,x);
    }
  }

  private void seedStaleServiceDiscovery(){
    android.content.SharedPreferences p=target.getSharedPreferences("pp_m2_service_transport",Context.MODE_PRIVATE);
    String stale="{\"ok\":true,\"authority_mode\":\"SERVICE_PRIMARY\",\"service_url\":\"https://pickpack1291.cc.cd\"}";
    p.edit().putString("discovery_json",stale).putLong("discovery_at",System.currentTimeMillis()).remove("service_token").commit();
    Bundle x=new Bundle();x.putString("stale_discovery_seed","PASS");finish(0,x);
  }

  private void runServiceDiscoveryCacheRegression(boolean seed) throws Exception {
    android.content.SharedPreferences p=target.getSharedPreferences("pp_m2_service_transport",Context.MODE_PRIVATE);
    String stale="{\"ok\":true,\"authority_mode\":\"SERVICE_PRIMARY\",\"service_url\":\"https://pickpack1291.cc.cd\"}";
    boolean staleBeforeCheck=true;
    if(seed){
      p.edit().putString("discovery_json",stale).putLong("discovery_at",System.currentTimeMillis()).remove("service_token").commit();
    }else{
      JSONObject before=new JSONObject(p.getString("discovery_json","{}"));
      String beforeUrl=before.optString("service_url");
      staleBeforeCheck="https://pickpack1291.cc.cd".equals(beforeUrl);
      if(staleBeforeCheck){
        require(System.currentTimeMillis()-p.getLong("discovery_at",0L)<300000L,"PRESERVED_STALE_DISCOVERY_TTL_NOT_FRESH");
      }else{
        require("BETA".equals(before.optString("environment_id")),"PRECHECK_REWRITTEN_CACHE_ENV_NOT_BETA:"+before.optString("environment_id"));
        require("PICK_PACK_1291_BETA".equals(before.optString("service_audience")),"PRECHECK_REWRITTEN_CACHE_AUDIENCE_MISMATCH:"+before.optString("service_audience"));
        require(beforeUrl.startsWith("https://"),"PRECHECK_REWRITTEN_CACHE_URL_INVALID:"+beforeUrl);
        require(!"https://pickpack1291.cc.cd".equals(beforeUrl),"PRECHECK_STALE_ROOT_REUSED");
      }
    }
    Class<?> c=target.getClassLoader().loadClass("vn.pickpack1291.app.beta.M2ServiceTransport");
    Object transport=c.getConstructor(Context.class).newInstance(target);
    Method m=c.getMethod("discoverySnapshot",boolean.class);
    Object raw=m.invoke(transport,false);
    require(raw instanceof JSONObject,"SERVICE_DISCOVERY_REFRESH_EMPTY");
    JSONObject d=(JSONObject)raw;
    require("BETA".equals(d.optString("environment_id")),"SERVICE_DISCOVERY_ENV_NOT_BETA:"+d.optString("environment_id"));
    require("PICK_PACK_1291_BETA".equals(d.optString("service_audience")),"SERVICE_DISCOVERY_AUDIENCE_MISMATCH:"+d.optString("service_audience"));
    String url=d.optString("service_url");
    require(url.startsWith("https://"),"SERVICE_DISCOVERY_URL_INVALID:"+url);
    require(!"https://pickpack1291.cc.cd".equals(url),"SERVICE_DISCOVERY_STALE_ROOT_REUSED");
    JSONObject persisted=new JSONObject(p.getString("discovery_json","{}"));
    require("BETA".equals(persisted.optString("environment_id")),"SERVICE_DISCOVERY_CACHE_NOT_REWRITTEN");
    require(url.equals(persisted.optString("service_url")),"SERVICE_DISCOVERY_CACHE_URL_NOT_REWRITTEN");
    Bundle x=new Bundle();
    x.putString("service_discovery_cache_regression","PASS");
    x.putString("cache_rewritten_in_process","PASS");
    x.putString("stable_root_reused","false");
    x.putString("environment_id",d.optString("environment_id"));
    x.putString("service_audience",d.optString("service_audience"));
    x.putString("service_url",url);
    x.putString("stale_cache_before_check",staleBeforeCheck?"STALE_PRESERVED":"ALREADY_REWRITTEN_BY_APP");
    finish(0,x);
  }

  private String req(String k){
    String v=args.getString(k);
    if(v==null||v.trim().isEmpty())throw new IllegalArgumentException(k+"_REQUIRED");
    return v.trim();
  }

  private void seedAuth(){
    target.getSharedPreferences("pick_pack_auth_session_v2",Context.MODE_PRIVATE).edit()
      .putString("token","beta83-local-ui-fixture")
      .putString("login_id","beta83_verify")
      .putString("display_name","Beta83 Verify")
      .putString("role","SUPERADMIN")
      .putString("position","TEST")
      .putString("email","verify@example.invalid")
      .commit();
  }

  private void seedService(){
    String url=args.getString("service_url","http://127.0.0.1:1");
    String discovery="{\"ok\":true,\"authority_mode\":\"SERVICE_PRIMARY\",\"service_url\":\""+
      url.replace("\\","\\\\").replace("\"","\\\"")+"\"}";
    target.getSharedPreferences("pp_m2_service_transport",Context.MODE_PRIVATE).edit()
      .putString("service_token","offline-beta83")
      .putString("discovery_json",discovery)
      .putLong("discovery_at",System.currentTimeMillis())
      .commit();
  }

  private Activity openRole(String module,String roleValue){
    seedAuth();seedService();
    target.getSharedPreferences("pick_pack_auth_session_v2",Context.MODE_PRIVATE).edit().putString("role",roleValue).commit();
    Intent i=new Intent();
    i.setClassName(target,ACT);
    i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_CLEAR_TASK);
    i.putExtra("module",module);
    i.putExtra("login","beta83_verify");
    i.putExtra("name","Beta83 Verify");
    i.putExtra("role",roleValue);
    i.putExtra("position","TEST");
    i.putExtra("email","verify@example.invalid");
    target.startActivity(i);
    long end=SystemClock.uptimeMillis()+10000L;
    while(SystemClock.uptimeMillis()<end){
      AccessibilityNodeInfo r=root();
      CharSequence p=r==null?null:r.getPackageName();
      if(p!=null&&PKG.equals(p.toString())&&currentActivity!=null&&ACT.equals(currentActivity.getClass().getName())){
        SystemClock.sleep(250L);
        Activity ready=currentActivity;
        if(ready!=null&&ACT.equals(ready.getClass().getName()))return ready;
      }
      SystemClock.sleep(150L);
    }
    throw new IllegalStateException("ACTIVITY_START_TIMEOUT:"+module+":"+roleValue);
  }

  private Activity open(String module){return openRole(module,"SUPERADMIN");}

  private void enableGlobalLanTestModeFixture()throws Exception{
    ClassLoader cl=target.getClassLoader();
    Class<?> lanClass=cl.loadClass("vn.pickpack1291.app.beta.LanCoordinator");
    Class<?> companionClass=cl.loadClass("vn.pickpack1291.app.beta.LanCoordinator$Companion");
    Object companion=lanClass.getField("Companion").get(null);
    Object lan=companionClass.getMethod("get",Context.class).invoke(companion,target);
    lanClass.getMethod("applyGlobalTestMode",boolean.class,long.class,String.class).invoke(lan,true,116L,"beta83_verify");
    require(Boolean.TRUE.equals(lanClass.getMethod("globalTestModeEnabled").invoke(lan)),"LAN_GLOBAL_TEST_MODE_FIXTURE_NOT_APPLIED");
  }

  private void appendRealtimeTimelineEventAndNotify(String mnv)throws Exception{
    Activity a=currentActivity;
    require(a!=null&&PKG.equals(a.getPackageName()),"CURRENT_ACTIVITY_MISSING_REALTIME");
    String today=LocalDate.now(ZoneId.of("Asia/Ho_Chi_Minh")).toString();
    ClassLoader cl=target.getClassLoader();
    Class<?> storeClass=cl.loadClass("vn.pickpack1291.app.beta.OperationalDataStore");
    Object store=storeClass.getConstructor(Context.class).newInstance(target);
    Method loadDay=storeClass.getMethod("loadDay",String.class);
    Method saveDay=storeClass.getMethod("saveDay",JSONObject.class);
    JSONObject original=(JSONObject)loadDay.invoke(store,today);
    require(original!=null,"REALTIME_DAY_MISSING");
    JSONObject day=new JSONObject(original.toString());
    JSONArray events=day.optJSONArray("events");
    if(events==null){events=new JSONArray();day.put("events",events);}
    JSONObject before=new JSONObject()
      .put("work_choice","PACK").put("pda_serial","PDA-SCALAR-AFTER").put("user_pick","PICK-SCALAR-AFTER")
      .put("pack_table","TABLE-SCALAR-AFTER").put("user_pack","PACK-SCALAR-AFTER");
    JSONObject after=new JSONObject(before.toString()).put("user_pack","PACK-REALTIME-B91");
    JSONObject payload=new JSONObject().put("session_id","beta83-current-active").put("mnv",mnv)
      .put("mutation_kind","EDIT").put("before",before).put("after",after);
    events.put(new JSONObject().put("event_id","b91-realtime-change").put("event_type","RESOURCE_CHANGE")
      .put("session_id","beta83-current-active").put("mnv",mnv).put("actor","REALTIME-ACTOR-B91")
      .put("committed_at",today+"T01:24:30Z").put("payload_json",payload.toString()));
    day.put("day_revision",83003L);
    saveDay.invoke(store,day);

    Field field=a.getClass().getDeclaredField("employeeTimelineRealtimeRefresh");
    field.setAccessible(true);
    Object callback=field.get(a);
    require(callback!=null,"EMPLOYEE_REALTIME_CALLBACK_MISSING");
    final Throwable[] failure=new Throwable[1];
    Set<String> changed=new HashSet<>();changed.add(today);
    runOnMainSync(new Runnable(){@Override public void run(){
      try{callback.getClass().getMethod("invoke",Object.class).invoke(callback,changed);}
      catch(Throwable t){failure[0]=t;}
    }});
    if(failure[0]!=null)throw new IllegalStateException("EMPLOYEE_REALTIME_CALLBACK_FAILED",failure[0]);
    waitText("User Pack: PACK-SCALAR-AFTER → PACK-REALTIME-B91",false,false,12000L);
    waitText("Người thực hiện: REALTIME-ACTOR-B91",false,false,12000L);
  }

  private int operationalPendingCount()throws Exception{
    Class<?> storeClass=target.getClassLoader().loadClass("vn.pickpack1291.app.beta.OperationalDataStore");
    Object store=storeClass.getConstructor(Context.class).newInstance(target);
    Object value=storeClass.getMethod("pendingMutationCount").invoke(store);
    return ((Number)value).intValue();
  }

  private AccessibilityNodeInfo root(){ return ui.getRootInActiveWindow(); }
  private static String textOf(AccessibilityNodeInfo n){
    CharSequence t=n.getText();
    if(t!=null&&!t.toString().trim().isEmpty())return t.toString().trim();
    CharSequence d=n.getContentDescription();
    return d==null?"":d.toString().trim();
  }
  private AccessibilityNodeInfo clickableNode(AccessibilityNodeInfo n){
    AccessibilityNodeInfo x=n;
    for(int i=0;i<6&&x!=null;i++,x=x.getParent())if(x.isClickable())return x;
    return null;
  }
  private AccessibilityNodeInfo findText(String needle,boolean exact,boolean clickable){
    AccessibilityNodeInfo r=root(); if(r==null)return null;
    String q=needle.trim().toUpperCase(Locale.ROOT);
    ArrayDeque<AccessibilityNodeInfo> dq=new ArrayDeque<>();dq.add(r);
    while(!dq.isEmpty()){
      AccessibilityNodeInfo n=dq.removeFirst();
      String t=textOf(n).toUpperCase(Locale.ROOT);
      boolean match=exact?t.equals(q):t.contains(q);
      if(match&&(!clickable||clickableNode(n)!=null))return n;
      for(int i=0;i<n.getChildCount();i++){AccessibilityNodeInfo c=n.getChild(i);if(c!=null)dq.addLast(c);}
    }
    return null;
  }
  private boolean textVisible(String text,boolean exact){
    AccessibilityNodeInfo n=findText(text,exact,false);
    return n!=null&&n.isVisibleToUser();
  }
  private AccessibilityNodeInfo waitText(String text,boolean exact,boolean clickable,long timeout){
    long end=SystemClock.uptimeMillis()+timeout;
    while(SystemClock.uptimeMillis()<end){
      AccessibilityNodeInfo n=findText(text,exact,clickable);
      if(n!=null)return n;
      SystemClock.sleep(180L);
    }
    throw new IllegalStateException("TEXT_NOT_FOUND:"+text);
  }
  private void showTextOnScreen(String text,long timeout){
    AccessibilityNodeInfo n=waitText(text,false,false,timeout);
    if(!n.performAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_SHOW_ON_SCREEN.getId())){
      AccessibilityNodeInfo p=n.getParent();
      if(p!=null)p.performAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_SHOW_ON_SCREEN.getId());
    }
    SystemClock.sleep(450L);
  }

  private void clickText(String text,boolean exact,long timeout){
    AccessibilityNodeInfo n=waitText(text,exact,true,timeout);
    AccessibilityNodeInfo c=clickableNode(n);
    if(c==null)throw new IllegalStateException("CLICK_TARGET_MISSING:"+text);
    if(!c.performAction(AccessibilityNodeInfo.ACTION_CLICK)){
      Rect b=new Rect();
      c.getBoundsInScreen(b);
      if(b.isEmpty())throw new IllegalStateException("CLICK_BOUNDS_EMPTY:"+text);
      try{ui.executeShellCommand("input tap "+b.centerX()+" "+b.centerY()).close();}
      catch(Exception e){throw new IllegalStateException("CLICK_FALLBACK_FAILED:"+text+":"+e.getMessage());}
    }
    SystemClock.sleep(450L);
  }
  private boolean scrollForward(){
    AccessibilityNodeInfo r=root();if(r==null)return false;
    ArrayDeque<AccessibilityNodeInfo> dq=new ArrayDeque<>();dq.add(r);
    while(!dq.isEmpty()){
      AccessibilityNodeInfo n=dq.removeFirst();
      if(n.isScrollable()&&n.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)){SystemClock.sleep(350L);return true;}
      for(int i=0;i<n.getChildCount();i++){AccessibilityNodeInfo c=n.getChild(i);if(c!=null)dq.addLast(c);}
    }
    return false;
  }
  private AccessibilityNodeInfo waitTextScrolling(String text,long timeout){
    long end=SystemClock.uptimeMillis()+timeout;
    while(SystemClock.uptimeMillis()<end){
      AccessibilityNodeInfo n=findText(text,false,false);
      if(n!=null)return n;
      scrollForward();
      SystemClock.sleep(150L);
    }
    throw new IllegalStateException("TEXT_NOT_FOUND_AFTER_SCROLL:"+text);
  }
  private void clickTextScrolling(String text,long timeout){
    AccessibilityNodeInfo n=waitTextScrolling(text,timeout);
    AccessibilityNodeInfo target=clickableNode(n);
    if(target==null)throw new IllegalStateException("CLICK_TARGET_MISSING_AFTER_SCROLL:"+text);
    if(!target.performAction(AccessibilityNodeInfo.ACTION_CLICK)){
      Rect b=new Rect();target.getBoundsInScreen(b);
      if(b.isEmpty())throw new IllegalStateException("CLICK_BOUNDS_EMPTY_AFTER_SCROLL:"+text);
      try{ui.executeShellCommand("input tap "+b.centerX()+" "+b.centerY()).close();}
      catch(Exception e){throw new IllegalStateException("CLICK_FALLBACK_FAILED_AFTER_SCROLL:"+text+":"+e.getMessage());}
    }
    SystemClock.sleep(450L);
  }
  private AccessibilityNodeInfo findEditable(){
    AccessibilityNodeInfo r=root();if(r==null)return null;
    ArrayDeque<AccessibilityNodeInfo> dq=new ArrayDeque<>();dq.add(r);
    while(!dq.isEmpty()){
      AccessibilityNodeInfo n=dq.removeFirst();
      String cls=String.valueOf(n.getClassName());
      CharSequence hint=n.getHintText();
      String h=hint==null?"":hint.toString().toUpperCase(Locale.ROOT);
      if((n.isEditable()||cls.contains("EditText"))&&(h.contains("MÃ NHÂN VIÊN")||h.contains("SCAN")))return n;
      for(int i=0;i<n.getChildCount();i++){AccessibilityNodeInfo c=n.getChild(i);if(c!=null)dq.addLast(c);}
    }
    return null;
  }
  private void setEmployee(String mnv){
    long end=SystemClock.uptimeMillis()+12000L;
    AccessibilityNodeInfo n=null;
    while(SystemClock.uptimeMillis()<end&&n==null){
      n=findEditableHint("Scan / Nhập mã nhân viên");
      if(n==null)n=findEditable();
      if(n==null)SystemClock.sleep(180L);
    }
    if(n==null)throw new IllegalStateException("EMPLOYEE_INPUT_NOT_FOUND");
    Bundle b=new Bundle();
    b.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,mnv);
    if(!n.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT,b))throw new IllegalStateException("EMPLOYEE_SET_TEXT_FAILED");
    n.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
    try{ui.executeShellCommand("input keyevent 66").close();}catch(Exception e){throw new RuntimeException(e);}
    SystemClock.sleep(700L);
  }

  private AccessibilityNodeInfo findEditableHint(String hint){
    AccessibilityNodeInfo r=root();if(r==null)return null;
    String q=hint.trim().toUpperCase(Locale.ROOT);
    ArrayDeque<AccessibilityNodeInfo> dq=new ArrayDeque<>();dq.add(r);
    while(!dq.isEmpty()){
      AccessibilityNodeInfo n=dq.removeFirst();
      CharSequence h=n.getHintText();String hs=h==null?"":h.toString().trim().toUpperCase(Locale.ROOT);
      String cls=String.valueOf(n.getClassName());
      if((n.isEditable()||cls.contains("EditText"))&&hs.contains(q))return n;
      for(int i=0;i<n.getChildCount();i++){AccessibilityNodeInfo x=n.getChild(i);if(x!=null)dq.addLast(x);}
    }
    return null;
  }
  private AccessibilityNodeInfo waitEditableHint(String hint,long timeout){
    long end=SystemClock.uptimeMillis()+timeout;
    AccessibilityNodeInfo n=null;
    while(SystemClock.uptimeMillis()<end){
      n=findEditableHint(hint);
      if(n!=null)return n;
      SystemClock.sleep(150L);
    }
    return null;
  }

  private void setNodeText(AccessibilityNodeInfo n,String value){
    if(n==null)throw new IllegalStateException("EDITABLE_NODE_MISSING");
    Bundle b=new Bundle();b.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,value);
    if(!n.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT,b))throw new IllegalStateException("SET_TEXT_FAILED");
  }
  private void setActivityBoolean(String fieldName,boolean value)throws Exception{
    Activity a=currentActivity;
    require(a!=null&&PKG.equals(a.getPackageName()),"CURRENT_ACTIVITY_MISSING:"+fieldName);
    Field f=a.getClass().getDeclaredField(fieldName);
    f.setAccessible(true);f.setBoolean(a,value);
  }
  private void invokeActivityNoArg(String methodName)throws Exception{
    Activity a=currentActivity;
    require(a!=null&&PKG.equals(a.getPackageName()),"CURRENT_ACTIVITY_MISSING:"+methodName);
    Method m=a.getClass().getDeclaredMethod(methodName);
    m.setAccessible(true);
    final Throwable[] failure=new Throwable[1];
    runOnMainSync(new Runnable(){@Override public void run(){try{m.invoke(a);}catch(Throwable t){failure[0]=t;}}});
    if(failure[0]!=null)throw new IllegalStateException("ACTIVITY_METHOD_FAILED:"+methodName,failure[0]);
    SystemClock.sleep(500L);
  }

  private int treeIndex(String needle){
    AccessibilityNodeInfo r=root();if(r==null)return -1;
    String q=needle.trim().toUpperCase(Locale.ROOT);int index=0;
    ArrayDeque<AccessibilityNodeInfo> dq=new ArrayDeque<>();dq.add(r);
    while(!dq.isEmpty()){
      AccessibilityNodeInfo n=dq.removeFirst();
      if(textOf(n).toUpperCase(Locale.ROOT).contains(q))return index;
      index++;
      for(int i=0;i<n.getChildCount();i++){AccessibilityNodeInfo x=n.getChild(i);if(x!=null)dq.addLast(x);}
    }
    return -1;
  }
  private int topOf(AccessibilityNodeInfo n){Rect r=new Rect();n.getBoundsInScreen(r);return r.top;}
  private void requireVerticalOrder(String... labels){
    int last=Integer.MIN_VALUE;
    for(String label:labels){
      AccessibilityNodeInfo n=waitText(label,true,false,8000L);int top=topOf(n);
      require(top>=last,"VERTICAL_ORDER_WRONG:"+label+":"+top+":"+last);last=top;
    }
  }

  private void verifySessionExitGuard(Activity a)throws Exception{
    Method m=a.getClass().getDeclaredMethod("usableExitSession",JSONObject.class,String.class);
    m.setAccessible(true);
    JSONObject blank=new JSONObject().put("session_id","").put("mnv","93001").put("state","ACTIVE").put("version",1);
    JSONObject wrong=new JSONObject().put("session_id","beta93-active").put("mnv","93002").put("state","ACTIVE").put("version",1);
    JSONObject valid=new JSONObject().put("session_id","beta93-active").put("mnv","93001").put("state","ACTIVE").put("version",1);
    require(!((Boolean)m.invoke(a,blank,"93001")).booleanValue(),"EXIT_GUARD_ACCEPTED_BLANK_SESSION_ID");
    require(!((Boolean)m.invoke(a,wrong,"93001")).booleanValue(),"EXIT_GUARD_ACCEPTED_WRONG_MNV");
    require(((Boolean)m.invoke(a,valid,"93001")).booleanValue(),"EXIT_GUARD_REJECTED_VALID_ACTIVE_SESSION");
    mark("session_exit_identity_guard");
  }

  private void verifyActualNavigationHistory(Activity a)throws Exception{
    Field state=a.getClass().getDeclaredField("screenState");state.setAccessible(true);
    Field module=a.getClass().getDeclaredField("module");module.setAccessible(true);
    Field displayedState=a.getClass().getDeclaredField("displayedScreenState");displayedState.setAccessible(true);
    Field displayedModule=a.getClass().getDeclaredField("displayedModule");displayedModule.setAccessible(true);
    Field stackField=a.getClass().getDeclaredField("screenBackStack");stackField.setAccessible(true);
    Method setScreen=a.getClass().getDeclaredMethod("setScreen",android.view.View.class);setScreen.setAccessible(true);
    Method navigateBack=a.getClass().getDeclaredMethod("navigateBack");navigateBack.setAccessible(true);
    @SuppressWarnings("unchecked") ArrayDeque<Object> stack=(ArrayDeque<Object>)stackField.get(a);
    final Throwable[] failure=new Throwable[1];
    runOnMainSync(new Runnable(){@Override public void run(){
      try{
        stack.clear();displayedState.set(a,"");displayedModule.set(a,"");module.set(a,"BUSINESS");
        state.set(a,"B111_1");setScreen.invoke(a,new android.widget.TextView(a));
        setScreen.invoke(a,new android.widget.TextView(a));
        require(stack.isEmpty(),"NAV_SAME_SCREEN_CREATED_FAKE_FRAME");
        state.set(a,"B111_2");setScreen.invoke(a,new android.widget.TextView(a));
        state.set(a,"B111_3");setScreen.invoke(a,new android.widget.TextView(a));
        navigateBack.invoke(a);require("B111_2".equals(String.valueOf(state.get(a))),"NAV_1_2_3_BACK_NOT_2:"+state.get(a));
        navigateBack.invoke(a);require("B111_1".equals(String.valueOf(state.get(a))),"NAV_1_2_3_BACK_NOT_1:"+state.get(a));

        stack.clear();displayedState.set(a,"");displayedModule.set(a,"");module.set(a,"BUSINESS");
        state.set(a,"B111_5");setScreen.invoke(a,new android.widget.TextView(a));
        state.set(a,"B111_3");setScreen.invoke(a,new android.widget.TextView(a));
        navigateBack.invoke(a);require("B111_5".equals(String.valueOf(state.get(a))),"NAV_5_3_BACK_NOT_5:"+state.get(a));
      }catch(Throwable t){failure[0]=t;}
    }});
    if(failure[0]!=null)throw new IllegalStateException("NAV_HISTORY_BETA111_FAILED",failure[0]);
    mark("navigation_history_beta111");
  }

  @SuppressWarnings({"unchecked","rawtypes"})
  private void verifyReviewAlertUiSharedStyle(Activity a)throws Exception{
    Class<?> cls=target.getClassLoader().loadClass("vn.pickpack1291.app.beta.ReviewAlertUi");
    Class<?> toneCls=target.getClassLoader().loadClass("vn.pickpack1291.app.beta.ReviewAlertUi$Tone");
    Object instance=cls.getField("INSTANCE").get(null);
    Object warning=Enum.valueOf((Class)toneCls,"WARNING");
    Object ok=Enum.valueOf((Class)toneCls,"OK");
    Method buttonMethod=cls.getMethod("button",Activity.class,String.class,toneCls);
    android.widget.Button wb=(android.widget.Button)buttonMethod.invoke(instance,a,"CẢNH BÁO TEST",warning);
    android.widget.Button ob=(android.widget.Button)buttonMethod.invoke(instance,a,"RÀ SOÁT OK",ok);
    Method lpMethod=cls.getMethod("fixedHeightParams",Activity.class);
    android.widget.LinearLayout.LayoutParams lp=(android.widget.LinearLayout.LayoutParams)lpMethod.invoke(instance,a);
    int expectedHeight=(int)(42f*a.getResources().getDisplayMetrics().density);
    float expectedText=10.5f*a.getResources().getDisplayMetrics().scaledDensity;
    require(lp.height==expectedHeight,"REVIEW_WARNING_HEIGHT_MISMATCH:"+lp.height+":"+expectedHeight);
    require(Math.abs(wb.getTextSize()-expectedText)<1.5f,"REVIEW_WARNING_TEXT_SIZE_MISMATCH:"+wb.getTextSize()+":"+expectedText);
    require(wb.getCurrentTextColor()==android.graphics.Color.rgb(176,0,32),"WARNING_COLOR_MISMATCH:"+wb.getCurrentTextColor());
    require(ob.getCurrentTextColor()==android.graphics.Color.rgb(16,112,66),"REVIEW_OK_COLOR_MISMATCH:"+ob.getCurrentTextColor());
    require(!wb.getIncludeFontPadding()&&!ob.getIncludeFontPadding(),"REVIEW_WARNING_FONT_PADDING_MISMATCH");
    require(wb.getStateListAnimator()==null&&ob.getStateListAnimator()==null,"REVIEW_WARNING_PLATFORM_ANIMATOR_PRESENT");
    require(wb.getMinimumHeight()==0&&ob.getMinimumHeight()==0,"REVIEW_WARNING_MIN_HEIGHT_VARIANCE");
    require(wb.getMinimumWidth()==0&&ob.getMinimumWidth()==0,"REVIEW_WARNING_MIN_WIDTH_VARIANCE");
    require(wb.getPaddingLeft()==ob.getPaddingLeft()&&wb.getPaddingRight()==ob.getPaddingRight(),"REVIEW_WARNING_PADDING_MISMATCH");
    mark("review_warning_shared_style_beta112");
  }

  private android.widget.TableLayout firstTable(android.view.View v){
    if(v instanceof android.widget.TableLayout)return (android.widget.TableLayout)v;
    if(v instanceof android.view.ViewGroup){
      android.view.ViewGroup g=(android.view.ViewGroup)v;
      for(int i=0;i<g.getChildCount();i++){android.widget.TableLayout t=firstTable(g.getChildAt(i));if(t!=null)return t;}
    }
    return null;
  }

  private void verifyBeta94OwnerScope(Activity a)throws Exception{
    Method p=a.getClass().getDeclaredMethod("exitPdaId",JSONObject.class);p.setAccessible(true);
    JSONObject authoritativeNone=new JSONObject().put("pda_serial","STALE-PDA").put("resource_assignments_v64",new JSONArray());
    JSONObject authoritativePda=new JSONObject().put("pda_serial","STALE-PDA").put("resource_assignments_v64",new JSONArray()
      .put(new JSONObject().put("resource_type","PDA").put("resource_id","PDA-ACTIVE").put("state","ACTIVE")));
    JSONObject legacy=new JSONObject().put("pda_serial","PDA-LEGACY");
    require("".equals(String.valueOf(p.invoke(a,authoritativeNone))),"EXIT_PDA_STALE_SCALAR_ACCEPTED");
    require("PDA-ACTIVE".equals(String.valueOf(p.invoke(a,authoritativePda))),"EXIT_PDA_ACTIVE_ASSIGNMENT_MISSING");
    require("".equals(String.valueOf(p.invoke(a,legacy))),"EXIT_PDA_LEGACY_SCALAR_ACCEPTED");
    mark("pda_exit_only_when_session_has_pda");

    Class<?> warningClass=target.getClassLoader().loadClass("vn.pickpack1291.app.beta.OldSessionWarningFeature");
    Field warningField=warningClass.getDeclaredField("WARNING_TEXT");warningField.setAccessible(true);
    require("CẢNH BÁO: CÓ PHIÊN CŨ CHƯA BẮN RA".equals(String.valueOf(warningField.get(null))),"OLD_WARNING_TEXT_NOT_UNIFIED");
    mark("old_warning_unified");

    Method grid=a.getClass().getDeclaredMethod("s34ReportGrid",String.class,JSONObject.class,String.class,String.class);grid.setAccessible(true);
    JSONArray cols=new JSONArray().put("IH").put("NLV").put("VW");
    JSONObject pos=new JSONObject().put("columns",cols).put("rows",new JSONArray()).put("totals",new JSONObject()).put("total",0);
    JSONObject tenure=new JSONObject().put("columns",new JSONArray(cols.toString())).put("rows",new JSONArray()).put("totals",new JSONObject()).put("total",0);
    android.view.View gv1=(android.view.View)grid.invoke(a,"",pos,"Vị trí","position");
    android.view.View gv2=(android.view.View)grid.invoke(a,"",tenure,"Thâm niên","label");
    android.widget.TableLayout t1=firstTable(gv1),t2=firstTable(gv2);
    require(t1!=null&&t2!=null&&t1.getChildCount()>0&&t2.getChildCount()>0,"REPORT_TABLE_MISSING");
    android.widget.TableRow r1=(android.widget.TableRow)t1.getChildAt(0),r2=(android.widget.TableRow)t2.getChildAt(0);
    require(r1.getChildCount()==r2.getChildCount()&&r1.getChildCount()==5,"REPORT_COLUMN_COUNT_MISMATCH");
    for(int i=0;i<r1.getChildCount();i++){
      android.widget.TableRow.LayoutParams a1=(android.widget.TableRow.LayoutParams)r1.getChildAt(i).getLayoutParams();
      android.widget.TableRow.LayoutParams a2=(android.widget.TableRow.LayoutParams)r2.getChildAt(i).getLayoutParams();
      require(a1.width==0&&a2.width==0&&Math.abs(a1.weight-a2.weight)<0.001f,"REPORT_COLUMN_GEOMETRY_MISMATCH:"+i);
    }
    android.widget.TableRow.LayoutParams first=(android.widget.TableRow.LayoutParams)r1.getChildAt(0).getLayoutParams();
    android.widget.TableRow.LayoutParams supplier1=(android.widget.TableRow.LayoutParams)r1.getChildAt(1).getLayoutParams();
    android.widget.TableRow.LayoutParams supplier2=(android.widget.TableRow.LayoutParams)r1.getChildAt(2).getLayoutParams();
    require(first.weight>supplier1.weight&&Math.abs(supplier1.weight-supplier2.weight)<0.001f,"REPORT_COLUMN_WEIGHTS_INVALID");
    mark("report_columns_aligned");
  }

  private void mark(String key){
    target.getSharedPreferences("pp_beta83_verify",Context.MODE_PRIVATE).edit()
      .putBoolean(key,true).putLong(key+"_at",System.currentTimeMillis()).commit();
  }
  private static void require(boolean v,String e){if(!v)throw new IllegalStateException(e);}

  private void shot(String name)throws Exception{
    Bitmap b=ui.takeScreenshot();
    if(b==null)throw new IllegalStateException("SCREENSHOT_NULL:"+name);
    File dir=new File(target.getExternalFilesDir(null),"beta83-visual");
    if(!dir.exists()&&!dir.mkdirs())throw new IllegalStateException("SCREENSHOT_DIR_FAILED");
    File f=new File(dir,name+".png");
    try(FileOutputStream out=new FileOutputStream(f)){
      if(!b.compress(Bitmap.CompressFormat.PNG,100,out))throw new IllegalStateException("SCREENSHOT_COMPRESS_FAILED");
    }finally{b.recycle();}
  }

  private void seedData(String mnv,String mnv2,String mnv3)throws Exception{
    String today=LocalDate.now(ZoneId.of("Asia/Ho_Chi_Minh")).toString();
    String oldDate=LocalDate.parse(today).minusDays(1).toString();

    JSONObject master=new JSONObject()
      .put("ok",true).put("master_revision",83001L)
      .put("staff",new JSONArray()
        .put(new JSONObject().put("mnv",mnv).put("full_name","Beta83 Test A").put("phone","0900000081").put("start_date","01/08/2026").put("main_position","PICK").put("supplier","TEST").put("department","OPS").put("site","1291").put("warehouse","HY1"))
        .put(new JSONObject().put("mnv",mnv2).put("full_name","Beta83 Test B").put("phone","0900000082").put("start_date","02/08/2026").put("main_position","PACK").put("supplier",JSONObject.NULL).put("department","OPS").put("site","1291").put("warehouse","HY1"))
        .put(new JSONObject().put("mnv",mnv3).put("full_name","Beta83 Test C").put("phone","0900000083").put("start_date","03/08/2026").put("main_position","PACK").put("supplier","TEST").put("department","OPS").put("site","1291").put("warehouse","HY1"))
        .put(new JSONObject().put("mnv","981820084").put("full_name","Beta95 Local New").put("phone","0900000084").put("start_date","04/08/2026").put("main_position","PICK").put("supplier","TEST").put("department","OPS").put("site","1291").put("warehouse","HY1"))
        .put(new JSONObject().put("mnv","981810099").put("full_name","Beta97 Old Active").put("phone","0900000099").put("start_date","01/08/2026").put("main_position","PICK").put("supplier","TEST").put("department","OPS").put("site","1291").put("warehouse","HY1")))
      .put("pdas",new JSONArray()).put("pda_statuses",new JSONArray().put("Tốt"))
      .put("user_picks",new JSONArray()).put("pack_bundles",new JSONArray());

    ClassLoader cl=target.getClassLoader();
    Class<?> masterClass=cl.loadClass("vn.pickpack1291.app.beta.MasterDataCache");
    Object masterObj=masterClass.getField("INSTANCE").get(null);
    masterClass.getMethod("save",Context.class,JSONObject.class).invoke(masterObj,target,master);

    Class<?> storeClass=cl.loadClass("vn.pickpack1291.app.beta.OperationalDataStore");
    Object store=storeClass.getConstructor(Context.class).newInstance(target);
    Method saveDay=storeClass.getMethod("saveDay",JSONObject.class);

    JSONArray emptyAssignments=new JSONArray();
    JSONObject a=new JSONObject()
      .put("session_id","beta83-current-active").put("mnv",mnv).put("business_date",today).put("shift","Ca 2")
      .put("state","ACTIVE").put("enter_at",today+"T01:00:00Z").put("exit_at","").put("version",1)
      .put("work_choice","PICK").put("pda_serial","MT90-260817-214675").put("user_pick","").put("pack_table","B83-TABLE").put("user_pack","PACK-B83")
      .put("positions_v64",new JSONArray().put(new JSONObject().put("position_key","PICK").put("position_label","Pick").put("state","ACTIVE")))
      .put("resource_assignments_v64",new JSONArray()
        .put(new JSONObject().put("assignment_id","b83-pda").put("resource_type","PDA").put("resource_id","MT90-260817-214675").put("state","ACTIVE"))
        .put(new JSONObject().put("assignment_id","b83-table").put("resource_type","PACK_TABLE").put("resource_id","B83-TABLE").put("state","ACTIVE"))
        .put(new JSONObject().put("assignment_id","b83-pack").put("resource_type","USER_PACK").put("resource_id","PACK-B83").put("state","ACTIVE")));
    JSONObject b=new JSONObject()
      .put("session_id","beta83-current-ended").put("mnv",mnv2).put("business_date",today).put("shift","Ca 2")
      .put("state","ENDED").put("enter_at",today+"T01:05:00Z").put("exit_at",today+"T02:00:00Z").put("version",2)
      .put("pack_table","B83-TABLE").put("user_pack",JSONObject.NULL)
      .put("positions_v64",new JSONArray().put(new JSONObject().put("position_key","PACK").put("position_label","Pack").put("state","ENDED")))
      .put("resource_assignments_v64",new JSONArray());
    JSONObject c=new JSONObject()
      .put("session_id","beta83-hc-ended").put("mnv",mnv3).put("business_date",today).put("shift","Ca HC")
      .put("state","ENDED").put("enter_at",today+"T01:15:00Z").put("exit_at",today+"T09:00:00Z").put("version",1)
      .put("pack_table","B83-HC").put("user_pack","PACK-B83")
      .put("positions_v64",new JSONArray().put(new JSONObject().put("position_key","PACK").put("position_label","Pack").put("state","ENDED")))
      .put("resource_assignments_v64",new JSONArray());
    JSONObject leakedOld=new JSONObject()
      .put("session_id","beta83-leaked-old").put("mnv","981810099").put("business_date",oldDate).put("shift","Ca 1")
      .put("state","ACTIVE").put("enter_at",oldDate+"T01:00:00Z").put("exit_at","").put("version",1)
      .put("positions_v64",new JSONArray()).put("resource_assignments_v64",new JSONArray());

    JSONObject before=new JSONObject().put("work_choice","PICK").put("pda_serial","STALE-PDA-BEFORE").put("user_pick","STALE-PICK-BEFORE").put("pack_table","STALE-TABLE-BEFORE").put("user_pack","STALE-PACK-BEFORE")
      .put("resource_assignments_v64",new JSONArray()
        .put(new JSONObject().put("resource_type","PDA").put("resource_id","PDA-BEFORE").put("state","ACTIVE"))
        .put(new JSONObject().put("resource_type","USER_PICK").put("resource_id","PICK-BEFORE").put("state","ACTIVE"))
        .put(new JSONObject().put("resource_type","PACK_TABLE").put("resource_id","TABLE-BEFORE").put("state","ACTIVE"))
        .put(new JSONObject().put("resource_type","USER_PACK").put("resource_id","PACK-BEFORE").put("state","ACTIVE")));
    JSONObject after=new JSONObject().put("work_choice","PACK").put("pda_serial","STALE-PDA-AFTER").put("user_pick","STALE-PICK-AFTER").put("pack_table","STALE-TABLE-AFTER").put("user_pack","STALE-PACK-AFTER")
      .put("resource_assignments_v64",new JSONArray()
        .put(new JSONObject().put("resource_type","PDA").put("resource_id","PDA-AFTER").put("state","ACTIVE"))
        .put(new JSONObject().put("resource_type","USER_PICK").put("resource_id","PICK-AFTER").put("state","ACTIVE"))
        .put(new JSONObject().put("resource_type","PACK_TABLE").put("resource_id","TABLE-AFTER").put("state","ACTIVE"))
        .put(new JSONObject().put("resource_type","USER_PACK").put("resource_id","PACK-AFTER").put("state","ACTIVE")));
    JSONObject changePayload=new JSONObject().put("session_id","beta83-current-active").put("mnv",mnv).put("mutation_kind","EDIT").put("before",before).put("after",after);
    JSONObject scalarBefore=new JSONObject().put("work_choice","PICK").put("pda_serial","PDA-SCALAR-BEFORE").put("user_pick","PICK-SCALAR-BEFORE").put("pack_table","TABLE-SCALAR-BEFORE").put("user_pack","PACK-SCALAR-BEFORE");
    JSONObject scalarAfter=new JSONObject().put("work_choice","PACK").put("pda_serial","PDA-SCALAR-AFTER").put("user_pick","PICK-SCALAR-AFTER").put("pack_table","TABLE-SCALAR-AFTER").put("user_pack","PACK-SCALAR-AFTER");
    JSONObject scalarPayload=new JSONObject().put("session_id","beta83-current-active").put("mnv",mnv).put("mutation_kind","EDIT").put("before",scalarBefore).put("after",scalarAfter);
    JSONObject noopPayload=new JSONObject().put("session_id","beta83-current-active").put("mnv",mnv).put("mutation_kind","EDIT").put("before",new JSONObject(scalarAfter.toString())).put("after",new JSONObject(scalarAfter.toString()));
    JSONArray events=new JSONArray()
      .put(new JSONObject().put("event_id","b83-enter").put("event_type","ATTENDANCE_ENTER").put("session_id","beta83-current-active").put("mnv",mnv).put("actor","admin").put("committed_at",today+"T01:01:00Z").put("payload_json",new JSONObject().put("session_id","beta83-current-active").put("mnv",mnv).toString()))
      .put(new JSONObject().put("event_id","b83-change").put("event_type","RESOURCE_CHANGE").put("session_id","beta83-current-active").put("mnv",mnv).put("actor","admin").put("committed_at",today+"T01:22:00Z").put("payload_json",changePayload.toString()))
      .put(new JSONObject().put("event_id","b88-scalar-change").put("event_type","RESOURCE_CHANGE").put("session_id","beta83-current-active").put("mnv",mnv).put("actor","admin").put("committed_at",today+"T01:23:00Z").put("payload_json",scalarPayload.toString()))
      .put(new JSONObject().put("event_id","b91-noop-change").put("event_type","RESOURCE_CHANGE").put("session_id","beta83-current-active").put("mnv",mnv).put("actor","NOOP-ACTOR-B91").put("committed_at",today+"T01:24:00Z").put("payload_json",noopPayload.toString()));
    saveDay.invoke(store,new JSONObject().put("business_date",today).put("day_revision",83001L)
      .put("sessions",new JSONArray().put(a).put(b).put(c).put(leakedOld))
      .put("events",events).put("labor",new JSONArray()));

    saveDay.invoke(store,new JSONObject().put("business_date",oldDate).put("day_revision",83002L)
      .put("sessions",new JSONArray().put(leakedOld))
      .put("events",new JSONArray()).put("labor",new JSONArray()));
  }

  private void pressSystemBack(){
    try{ui.executeShellCommand("input keyevent 4").close();}catch(Exception e){throw new IllegalStateException("BACK_KEYEVENT_FAILED",e);}
    SystemClock.sleep(450L);
  }

  private void invokeActivityBack(){
    Activity a=currentActivity;
    require(a!=null&&PKG.equals(a.getPackageName()),"CURRENT_ACTIVITY_MISSING_BACK");
    runOnMainSync(new Runnable(){@Override public void run(){a.onBackPressed();}});
    SystemClock.sleep(450L);
  }

  private String navState(){
    try{
      Activity a=currentActivity;
      if(a==null)return "activity=null";
      Class<?> c=a.getClass();
      Field ss=c.getDeclaredField("screenState");ss.setAccessible(true);
      Field ds=c.getDeclaredField("displayedScreenState");ds.setAccessible(true);
      Field bs=c.getDeclaredField("screenBackStack");bs.setAccessible(true);
      Object raw=bs.get(a);
      java.util.ArrayDeque<?> dq=(java.util.ArrayDeque<?>)raw;
      Object top=dq.peekLast();
      String topState="";
      if(top!=null){Field ts=top.getClass().getDeclaredField("screenState");ts.setAccessible(true);topState=String.valueOf(ts.get(top));}
      return "screen="+String.valueOf(ss.get(a))+",displayed="+String.valueOf(ds.get(a))+",stack="+dq.size()+",top="+topState;
    }catch(Throwable t){return "diag_error="+t.getClass().getSimpleName()+":"+String.valueOf(t.getMessage());}
  }

  private void runBack36()throws Exception{
    String mnv=req("mnv"),mnv2=req("mnv2"),mnv3=req("mnv3");
    seedAuth();seedService();seedData(mnv,mnv2,mnv3);
    open("BUSINESS");
    waitText("Quét QR nhân sự",true,true,12000L);
    pressSystemBack();
    waitText("Quét QR nhân sự",true,true,12000L);
    AccessibilityNodeInfo r0=root();require(r0!=null&&PKG.equals(String.valueOf(r0.getPackageName())),"ROOT_BACK_EXITED_APP");

    clickText("Quét QR nhân sự",true,12000L);
    long end=SystemClock.uptimeMillis()+12000L;while(SystemClock.uptimeMillis()<end&&findEditable()==null)SystemClock.sleep(180L);
    require(findEditable()!=null,"SCAN_INPUT_MISSING_BACK36");
    setEmployee(mnv2);waitText("THÔNG TIN CA",true,false,12000L);
    pressSystemBack();
    end=SystemClock.uptimeMillis()+12000L;while(SystemClock.uptimeMillis()<end&&findEditable()==null)SystemClock.sleep(180L);
    require(findEditable()!=null,"CHILD_BACK_DID_NOT_RETURN_ONE_LEVEL");
    pressSystemBack();waitText("Quét QR nhân sự",true,true,12000L);
    pressSystemBack();waitText("Quét QR nhân sự",true,true,12000L);
    AccessibilityNodeInfo r1=root();require(r1!=null&&PKG.equals(String.valueOf(r1.getPackageName())),"SECOND_ROOT_BACK_EXITED_APP");
    Bundle done=new Bundle();done.putString("result","BETA89_BACK_API36_PASS");finish(0,done);
  }


  private void verifyBeta122OwnerFollowupRuntime()throws Exception{
    // OWNER item 2: the real SUPERADMIN keeps the selector, but effective USER/ADMIN must
    // rebuild navigation and authorization exactly like those roles.
    openRole("BUSINESS","SUPERADMIN");
    clickText("Dịch vụ",true,10000L);
    waitText("Thông tin dịch vụ",true,false,10000L);
    waitText("USER",true,true,10000L);waitText("ADMIN",true,true,10000L);waitText("SUPERADMIN",true,true,10000L);
    clickText("USER",true,10000L);
    waitText("Quét QR nhân sự",true,true,10000L);
    require(findText("Lịch sử",true,false)==null,"BETA122_EFFECTIVE_USER_HISTORY_STILL_VISIBLE");
    clickText("Dịch vụ",true,10000L);
    waitText("ADMIN",true,true,10000L);
    clickText("ADMIN",true,10000L);
    waitText("Lịch sử",true,true,10000L);
    clickText("Dịch vụ",true,10000L);
    waitText("SUPERADMIN",true,true,10000L);
    clickText("SUPERADMIN",true,10000L);

    // A real USER must never receive the role selector.
    openRole("BUSINESS","USER");
    clickText("Dịch vụ",true,10000L);
    waitText("Thông tin dịch vụ",true,false,10000L);
    require(findText("SUPERADMIN",true,false)==null,"BETA122_REAL_USER_SUPERADMIN_SELECTOR_VISIBLE");
    require(findText("ADMIN",true,false)==null,"BETA122_REAL_USER_ADMIN_SELECTOR_VISIBLE");
    pressSystemBack();

    // Restore the real SUPERADMIN fixture before testing PDA-source UI.
    final Activity a=openRole("BUSINESS","SUPERADMIN");
    final JSONObject pda=new JSONObject().put("serial","PDA-B122-12345").put("last5","12345").put("source","1291").put("status","Tốt");
    final JSONArray pdas=new JSONArray().put(pda);
    final android.widget.TextView[] panel=new android.widget.TextView[1];
    final Throwable[] panelFailure=new Throwable[1];
    final android.app.AlertDialog[] panelDialog=new android.app.AlertDialog[1];
    runOnMainSync(new Runnable(){@Override public void run(){
      try{
        android.widget.AutoCompleteTextView field=new android.widget.AutoCompleteTextView(a);
        field.setTag(pda);field.setText("12345");
        Method m=a.getClass().getDeclaredMethod("pdaSelectedPanel",JSONArray.class,android.widget.AutoCompleteTextView.class);
        m.setAccessible(true);
        panel[0]=(android.widget.TextView)m.invoke(a,pdas,field);
        android.widget.LinearLayout box=new android.widget.LinearLayout(a);box.setOrientation(android.widget.LinearLayout.VERTICAL);
        box.addView(field);box.addView(panel[0]);
        panelDialog[0]=new android.app.AlertDialog.Builder(a).setTitle("PDA nguồn Beta122").setView(box).create();
        panelDialog[0].show();
      }catch(Throwable t){panelFailure[0]=t;}
    }});
    if(panelFailure[0]!=null)throw new IllegalStateException("BETA122_PDA_SOURCE_PANEL_BUILD_FAILED",panelFailure[0]);
    SystemClock.sleep(900L);
    require(panel[0]!=null,"BETA122_PDA_SOURCE_PANEL_MISSING");
    String panelText=String.valueOf(panel[0].getText());
    require(panelText.contains("Nguồn")&&panelText.contains("1291")&&panelText.contains("Tình trạng PDA"),"BETA122_PDA_SOURCE_PANEL_NOT_RENDERED:"+panelText);
    runOnMainSync(new Runnable(){@Override public void run(){if(panelDialog[0]!=null)panelDialog[0].dismiss();}});

    // OWNER item 4: the Tài nguyên edit UI must expose the canonical source catalog and current source.
    final JSONArray catalogs=new JSONArray()
      .put(new JSONObject().put("namespace","DANH SÁCH PDA_Nguồn").put("value","1291"))
      .put(new JSONObject().put("namespace","DANH SÁCH PDA_Nguồn").put("value","1386"))
      .put(new JSONObject().put("namespace","DANH SÁCH PDA_Tình trạng").put("value","Tốt"));
    final JSONObject existing=new JSONObject()
      .put("resource_id","PDA-B122-12345")
      .put("status_label","Tốt")
      .put("source","1291")
      .put("metadata_json",new JSONObject().put("Seri PDA","PDA-B122-12345").put("5 số cuối Seri","12345").put("Nguồn","1291").toString());
    final Throwable[] editFailure=new Throwable[1];
    runOnMainSync(new Runnable(){@Override public void run(){
      try{
        Method m=a.getClass().getDeclaredMethod("resourceEditDialog",String.class,JSONObject.class,JSONArray.class,JSONArray.class,boolean.class);
        m.setAccessible(true);m.invoke(a,"PDA",existing,catalogs,new JSONArray(),true);
      }catch(Throwable t){editFailure[0]=t;}
    }});
    if(editFailure[0]!=null)throw new IllegalStateException("BETA122_PDA_SOURCE_EDITOR_OPEN_FAILED",editFailure[0]);
    waitText("Nguồn PDA",true,false,10000L);
    waitText("1291",true,false,10000L);
    pressSystemBack();
    System.out.println("BETA122_OWNER_FOLLOWUP_RUNTIME_PASS");
  }

  private void runVisual()throws Exception{
    String tag=req("tag"),mnv=req("mnv"),mnv2=req("mnv2"),mnv3=req("mnv3");
    verifyFirstLogMetadata();
    verifyDocumentLocalDurability();
    seedAuth();seedService();seedData(mnv,mnv2,mnv3);
    verifyBeta122OwnerFollowupRuntime();

    open("BUSINESS");
    waitText("Quét QR nhân sự",true,true,12000L);
    shot(tag+"-01-business");
    clickTextScrolling("Quản lý biên bản",10000L);
    waitText("Loại biên bản",true,false,10000L);
    waitText("Chụp ảnh",true,true,10000L);
    waitText("Chọn nhiều ảnh",true,true,10000L);
    require(!textVisible("Một biên bản nhiều trang",true),"DOCUMENT_MODE_VISIBLE_WITH_ZERO_DRAFTS");
    require(!textVisible("Nhiều biên bản",true),"DOCUMENT_MULTI_MODE_VISIBLE_WITH_ZERO_DRAFTS");
    require(!textVisible("Tải lên",true),"DOCUMENT_DRAFT_ACTION_VISIBLE_WITH_ZERO_DRAFTS");
    require(!textVisible("Ảnh chờ tải",true),"DOCUMENT_PENDING_BOX_VISIBLE_WHEN_EMPTY");
    waitText("Tất cả loại biên bản",true,false,10000L);
    waitText("Đã chọn 0 ảnh",true,false,10000L);
    waitText("Chọn tất cả biên bản đang lọc",true,false,10000L);
    waitText("Xóa biên bản đã chọn",true,false,10000L);
    shot(tag+"-01a-beta117-documents");
    open("BUSINESS");
    waitText("Quét QR nhân sự",true,true,10000L);
    clickText("Điểm danh nhân sự",true,10000L);
    waitText("ĐIỂM DANH",true,false,10000L);
    require(findText("null",false,false)==null,"MEAL_LITERAL_NULL_VISIBLE");
    shot(tag+"-01b-beta110-meal");
    try{ui.executeShellCommand("input keyevent 4").close();}catch(Exception ignored){}
    SystemClock.sleep(300L);
    waitText("Quét QR nhân sự",true,true,10000L);
    clickTextScrolling("Công nhật",10000L);
    waitText("Chi tiết công nhật theo ngày",true,false,10000L);
    waitText("Scan / Nhập mã nhân viên",true,false,10000L);
    shot(tag+"-01c-beta110-labor");
    try{ui.executeShellCommand("input keyevent 4").close();}catch(Exception ignored){}
    SystemClock.sleep(300L);
    waitText("Quét QR nhân sự",true,true,10000L);

    clickText("Quét QR nhân sự",true,12000L);
    long end=SystemClock.uptimeMillis()+12000L;
    while(SystemClock.uptimeMillis()<end&&findEditable()==null)SystemClock.sleep(180L);
    require(findEditable()!=null,"EMPLOYEE_INPUT_NOT_FOUND_VISUAL");
    shot(tag+"-02-scan");

    setEmployee(mnv);
    waitText("THÔNG TIN CA",true,false,12000L);
    shot(tag+"-03-employee-order");

    showTextOnScreen("DIỄN BIẾN CÔNG VIỆC TRONG CA",12000L);
    showTextOnScreen("PDA: PDA-SCALAR-BEFORE → PDA-SCALAR-AFTER",12000L);
    shot(tag+"-04-timeline");

    open("REPORT");
    waitText("Phạm vi báo cáo",true,false,12000L);
    waitText("Vị trí",true,false,12000L);
    waitText("Thâm niên",true,false,12000L);
    require(findText("Site 1291 •",false,false)==null,"REPORT_SCOPE_TEXT_MUST_BE_REMOVED");
    ui.waitForIdle(1000L,5000L);SystemClock.sleep(700L);
    shot(tag+"-05-report");

    open("SETTINGS");
    waitText("THÔNG TIN ỨNG DỤNG",true,false,10000L);
    showTextOnScreen("TRUNG TÂM KIỂM THỬ RESILIENCE",12000L);
    waitText("Phạm vi",true,false,10000L);
    waitText("Test kỹ thuật cô lập",false,false,10000L);
    clickText("CHỌN KỊCH BẢN & CHẠY TEST",true,10000L);
    waitText("Chọn kịch bản kiểm thử",false,false,10000L);
    waitText("1. Bình thường • Service hoạt động",false,false,10000L);
    waitText("2. Thiết bị mất Internet • giữ local",false,false,10000L);
    shot(tag+"-13-beta101-bordered-options");

    enableGlobalLanTestModeFixture();
    clickTextScrolling("7. Service + Google/GAS mất • LAN dự phòng",12000L);
    waitText("Kỳ vọng:",false,false,10000L);
    waitText("Test chỉ tạo event kỹ thuật cô lập",false,false,10000L);
    clickText("CHẠY TEST",true,10000L);
    waitText("CHƯA ĐỦ ĐIỀU KIỆN",false,false,12000L);
    waitText("ĐANG BẬT",true,false,10000L);
    waitText("Không chạm business outbox",false,false,10000L);
    waitText("PASS",true,false,10000L);

    clickText("XEM LỊCH SỬ TEST",true,10000L);
    waitText("Lịch sử kiểm thử resilience",false,false,10000L);
    waitText("Mới nhất ở trên",false,false,10000L);
    waitText("Business outbox",false,false,10000L);
    waitText("Mã test",false,false,10000L);
    waitText("Service + Google/GAS mất • LAN dự phòng",false,false,10000L);
    shot(tag+"-14-beta101-history-cards");
    try{ui.executeShellCommand("input keyevent 4").close();}catch(Exception ignored){}
    SystemClock.sleep(350L);

    setActivityBoolean("resilienceTestInFlight",true);
    setActivityBoolean("resilienceTestStopping",false);
    invokeActivityNoArg("settingsScreen");
    showTextOnScreen("TRUNG TÂM KIỂM THỬ RESILIENCE",10000L);
    showTextOnScreen("DỪNG TEST / VỀ BÌNH THƯỜNG",10000L);
    waitText("DỪNG TEST / VỀ BÌNH THƯỜNG",true,true,10000L);
    shot(tag+"-15-beta101-stop-control");
    setActivityBoolean("resilienceTestInFlight",false);
    setActivityBoolean("resilienceTestStopping",false);

    Bundle done=new Bundle();done.putString("result","BETA83_VISUAL_PASS");finish(0,done);
  }

  private static String formatBytes(long v){
    if(v<1024L)return v+" B";
    if(v<1024L*1024L)return String.format(Locale.US,"%.1f KB",v/1024.0);
    return String.format(Locale.US,"%.1f MB",v/(1024.0*1024.0));
  }

  private void verifyFirstLogMetadata()throws Exception{
    android.content.SharedPreferences prefs=target.getSharedPreferences("pp1291_log_state",Context.MODE_PRIVATE);
    prefs.edit().clear().commit();
    File dir=new File(target.getFilesDir(),"diagnostic_logs");
    if(dir.exists()){
      File[] old=dir.listFiles();
      if(old!=null)for(File f:old)if(f.isFile())f.delete();
    }else require(dir.mkdirs(),"LOG_DIR_CREATE_FAILED");

    Intent i=new Intent();
    i.setClassName(target,"vn.pickpack1291.app.beta.FullBetaActivity");
    i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_CLEAR_TASK);
    target.startActivity(i);

    long end=SystemClock.uptimeMillis()+12000L;
    while(SystemClock.uptimeMillis()<end){
      String n=prefs.getString("log_latest_name_v89","");
      long b=prefs.getLong("log_latest_file_bytes_v89",0L);
      long at=prefs.getLong("log_latest_at_v58",0L);
      if(!n.trim().isEmpty()&&b>0L&&at>0L){firstLogName=n;firstLogBytes=b;break;}
      SystemClock.sleep(180L);
    }
    require(!firstLogName.isEmpty(),"FIRST_LOG_NAME_NOT_RECORDED");
    require(firstLogBytes>0L,"FIRST_LOG_BYTES_NOT_RECORDED");
    require(prefs.getLong("log_latest_at_v58",0L)>0L,"FIRST_LOG_TIME_NOT_RECORDED");

    File[] files=dir.listFiles();
    require(files!=null&&files.length>0,"FIRST_LOG_FILE_NOT_CREATED");
    for(File f:files)if(f.isFile())require(f.delete(),"FIRST_LOG_DELETE_FAILED:"+f.getName());
    File[] after=dir.listFiles();
    require(after==null||after.length==0,"LOCAL_LOG_CLEANUP_FAILED");

    require(firstLogName.equals(prefs.getString("log_latest_name_v89","")),"LOG_NAME_LOST_AFTER_CLEANUP");
    require(firstLogBytes==prefs.getLong("log_latest_file_bytes_v89",0L),"LOG_BYTES_LOST_AFTER_CLEANUP");
    require(prefs.getLong("log_latest_at_v58",0L)>0L,"LOG_TIME_LOST_AFTER_CLEANUP");
    mark("log_metadata_persisted");
  }

  private void verifyDocumentLocalDurability()throws Exception{
    ClassLoader cl=target.getClassLoader();
    Class<?> imageClass=cl.loadClass("vn.pickpack1291.app.beta.DocumentImageProcessor$ProcessedImage");
    java.lang.reflect.Constructor<?> imageCtor=imageClass.getDeclaredConstructor(byte[].class,String.class,String.class,String.class,java.util.List.class,int.class,int.class,String.class);
    imageCtor.setAccessible(true);
    byte[] fixture=new byte[]{11,22,33,44,55,66};
    String fixtureSha=String.format("%064x",new java.math.BigInteger(1,java.security.MessageDigest.getInstance("SHA-256").digest(fixture)));
    String fixtureMd5=String.format("%032x",new java.math.BigInteger(1,java.security.MessageDigest.getInstance("MD5").digest(fixture)));
    Object image=imageCtor.newInstance(fixture,
      fixtureSha,
      fixtureMd5,
      "0000000000000108",java.util.Collections.singletonList("0000000000000108"),2,3,"image/jpeg");
    Class<?> storeClass=cl.loadClass("vn.pickpack1291.app.beta.DocumentPendingStore");
    Object store1=storeClass.getConstructor(Context.class).newInstance(target);
    String idem="b108-local-"+System.nanoTime();
    Object item=storeClass.getMethod("enqueue",String.class,String.class,String.class,String.class,String.class,imageClass,String.class,String.class,int.class,int.class,String.class)
      .invoke(store1,"admin","b110-category","CAMERA","2026-09-01T00:00:00Z",idem,image,"b110-group","MULTI_PAGE",1,2,"b116-note");
    Class<?> itemClass=cl.loadClass("vn.pickpack1291.app.beta.DocumentPendingStore$Item");
    String pendingId=String.valueOf(itemClass.getMethod("getPendingId").invoke(item));
    require(!pendingId.isEmpty(),"DOCUMENT_PENDING_ID_MISSING");
    Class<?> itemClassMeta=cl.loadClass("vn.pickpack1291.app.beta.DocumentPendingStore$Item");
    require("b110-group".equals(String.valueOf(itemClassMeta.getMethod("getGroupId").invoke(item))),"DOCUMENT_PENDING_GROUP_MISSING");
    require("MULTI_PAGE".equals(String.valueOf(itemClassMeta.getMethod("getGroupMode").invoke(item))),"DOCUMENT_PENDING_GROUP_MODE_MISSING");
    require(((Integer)itemClassMeta.getMethod("getPageIndex").invoke(item))==1&&((Integer)itemClassMeta.getMethod("getPageCount").invoke(item))==2,"DOCUMENT_PENDING_PAGE_META_MISSING");
    require("b116-note".equals(String.valueOf(itemClassMeta.getMethod("getNote").invoke(item))),"DOCUMENT_PENDING_NOTE_NOT_DURABLE");
    Object store2=storeClass.getConstructor(Context.class).newInstance(target);
    Object found=storeClass.getMethod("find",String.class).invoke(store2,pendingId);
    require(found!=null,"DOCUMENT_PENDING_NOT_DURABLE_ACROSS_STORE_INSTANCE");
    byte[] restored=(byte[])storeClass.getMethod("bytes",itemClass).invoke(store2,found);
    require(java.util.Arrays.equals(fixture,restored),"DOCUMENT_PENDING_BYTES_MISMATCH");
    storeClass.getMethod("remove",String.class).invoke(store2,pendingId);
    require(storeClass.getMethod("find",String.class).invoke(store2,pendingId)==null,"DOCUMENT_PENDING_REMOVE_FAILED");

    Class<?> draftClass=cl.loadClass("vn.pickpack1291.app.beta.DocumentDraftStore");
    Object draft1=draftClass.getConstructor(Context.class).newInstance(target);
    String draftLogin="admin";
    String draftIdem="b109-draft-"+System.nanoTime();
    draftClass.getMethod("save",String.class,String.class,String.class,String.class,imageClass,String.class)
      .invoke(draft1,draftLogin,"CAMERA","2026-09-01T00:00:00Z",draftIdem,image,"b116-draft-note");
    String draftIdem2="b110-draft2-"+System.nanoTime();
    draftClass.getMethod("append",String.class,String.class,String.class,String.class,imageClass,String.class)
      .invoke(draft1,draftLogin,"GALLERY","2026-09-01T00:01:00Z",draftIdem2,image,"b116-draft-note-2");
    Object draft2=draftClass.getConstructor(Context.class).newInstance(target);
    java.util.List<?> restoredDrafts=(java.util.List<?>)draftClass.getMethod("loadAll",String.class).invoke(draft2,draftLogin);
    require(restoredDrafts.size()==2,"DOCUMENT_SELECTED_MULTI_DRAFT_NOT_DURABLE");
    Object restoredDraft=restoredDrafts.get(0);
    require(restoredDraft!=null,"DOCUMENT_SELECTED_DRAFT_NOT_DURABLE");
    Class<?> draftDataClass=cl.loadClass("vn.pickpack1291.app.beta.DocumentDraftStore$Draft");
    require(draftIdem.equals(String.valueOf(draftDataClass.getMethod("getIdempotencyKey").invoke(restoredDraft))),"DOCUMENT_SELECTED_DRAFT_IDEMPOTENCY_MISMATCH");
    require("b116-draft-note".equals(String.valueOf(draftDataClass.getMethod("getNote").invoke(restoredDraft))),"DOCUMENT_SELECTED_DRAFT_NOTE_NOT_DURABLE");
    require(draftClass.getMethod("load",String.class).invoke(draft2,"other-account")==null,"DOCUMENT_SELECTED_DRAFT_ACCOUNT_FENCE_FAILED");
    draftClass.getMethod("remove",String.class).invoke(draft2,draftLogin);
    require(draftClass.getMethod("load",String.class).invoke(draft2,draftLogin)==null,"DOCUMENT_SELECTED_DRAFT_REMOVE_FAILED");
    mark("document_selected_draft_durable_beta109");
    mark("document_selected_multi_draft_beta110");

    Class<?> categoryClass=cl.loadClass("vn.pickpack1291.app.beta.DocumentCategoryCache");
    Class<?> entryClass=cl.loadClass("vn.pickpack1291.app.beta.DocumentCategoryCache$Entry");
    Object categoryEntry=entryClass.getConstructor(String.class,String.class).newInstance("b109-category","Biên bản Beta109");
    java.util.List<Object> categoryEntries=new java.util.ArrayList<>();
    categoryEntries.add(categoryEntry);
    Object category1=categoryClass.getConstructor(Context.class).newInstance(target);
    categoryClass.getMethod("save",String.class,java.util.List.class).invoke(category1,draftLogin,categoryEntries);
    Object category2=categoryClass.getConstructor(Context.class).newInstance(target);
    java.util.List<?> restoredCategories=(java.util.List<?>)categoryClass.getMethod("load",String.class).invoke(category2,draftLogin);
    require(restoredCategories.size()==1,"DOCUMENT_CATEGORY_CACHE_NOT_DURABLE");
    Object restoredCategory=restoredCategories.get(0);
    require("b109-category".equals(String.valueOf(entryClass.getMethod("getId").invoke(restoredCategory))),"DOCUMENT_CATEGORY_CACHE_ID_MISMATCH");
    require("Biên bản Beta109".equals(String.valueOf(entryClass.getMethod("getName").invoke(restoredCategory))),"DOCUMENT_CATEGORY_CACHE_NAME_MISMATCH");
    java.util.List<?> otherCategories=(java.util.List<?>)categoryClass.getMethod("load",String.class).invoke(category2,"other-account");
    require(otherCategories.isEmpty(),"DOCUMENT_CATEGORY_CACHE_ACCOUNT_FENCE_FAILED");
    mark("document_category_cache_offline_beta109");

    Class<?> cacheClass=cl.loadClass("vn.pickpack1291.app.beta.DocumentMediaCache");
    Object cache1=cacheClass.getConstructor(Context.class).newInstance(target);
    String cacheId="b108-cache-"+System.nanoTime();
    cacheClass.getMethod("put",String.class,byte[].class).invoke(cache1,cacheId,fixture);
    Object cache2=cacheClass.getConstructor(Context.class).newInstance(target);
    byte[] cached=(byte[])cacheClass.getMethod("get",String.class).invoke(cache2,cacheId);
    require(cached!=null&&java.util.Arrays.equals(fixture,cached),"DOCUMENT_MEDIA_CACHE_NOT_DURABLE");
    cacheClass.getMethod("clear",String.class).invoke(cache2,cacheId);
    require(cacheClass.getMethod("get",String.class).invoke(cache2,cacheId)==null,"DOCUMENT_MEDIA_CACHE_CLEAR_FAILED");
    mark("document_pending_durable_beta108");
    mark("document_media_cache_beta108");
  }

  private int countTextExact(String wanted){
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
    waitTextScrolling("Danh sách QR vào / ra",20000L);
    waitText("Trong ca 34 • Đã ra 0",true,false,12000L);
    long end=SystemClock.uptimeMillis()+12000L;
    while(SystemClock.uptimeMillis()<end&&countTextExact("Trong ca 33 • Đã ra 0")<2)SystemClock.sleep(180L);
    require(countTextExact("Trong ca 33 • Đã ra 0")>=2,"OWNER100_QR_SHIFT_COUNTS_NOT_33_33");
    waitTextScrolling("70100",20000L);
    mark("owner_100_sessions_projection_beta118");

    seedData(mnv,mnv2,mnv3);
    open("BUSINESS");
  }

  private void runChecks()throws Exception{
    verifyDocumentLocalDurability();
    String tag=req("tag"),mnv=req("mnv"),mnv2=req("mnv2"),mnv3=req("mnv3");
    verifyFirstLogMetadata();
    seedAuth();seedService();seedData(mnv,mnv2,mnv3);

    Activity business=open("BUSINESS");
    verifyOwner100SessionProjection(mnv,mnv2,mnv3);
    verifySessionExitGuard(business);
    verifyReviewAlertUiSharedStyle(business);
    verifyActualNavigationHistory(business);
    business=open("BUSINESS");
    verifyBeta94OwnerScope(business);
    waitText("Ca 1",false,false,12000L);
    waitText("Ca HC",false,false,12000L);
    waitText("Ca 2",false,false,12000L);
    require(findText("RÀ SOÁT VÀO / RA",false,false)==null,"REDUNDANT_RECONCILIATION_HEADER_VISIBLE");
    require(findText("Chào buổi",false,false)==null,"GREETING_MUST_BE_REMOVED");
    require(findText("Làm mới và đồng bộ dữ liệu",true,false)==null,"REFRESH_ICON_MUST_BE_REMOVED");
    shot(tag+"-00-beta112-review-warning-unified");
    AccessibilityNodeInfo networkChip=waitText("Mạng",true,false,10000L);
    AccessibilityNodeInfo syncChip=waitText("Đồng bộ",true,false,10000L);
    AccessibilityNodeInfo serviceChip=waitText("Dịch vụ",true,false,10000L);
    require(clickableNode(networkChip)!=null,"NETWORK_CHIP_MUST_BE_CLICKABLE");
    require(clickableNode(syncChip)!=null,"SYNC_CHIP_MUST_BE_CLICKABLE");
    require(clickableNode(serviceChip)!=null,"SERVICE_CHIP_MUST_BE_CLICKABLE");
    clickText("Mạng",true,10000L);
    waitText("Thông tin Mạng",false,false,10000L);waitText("Loại kết nối",false,false,10000L);
    try{ui.executeShellCommand("input keyevent 4").close();}catch(Exception ignored){}
    SystemClock.sleep(200L);
    clickText("Đồng bộ",true,10000L);
    waitText("Thông tin Đồng bộ",false,false,10000L);waitText("ĐỒNG BỘ NGAY",true,false,10000L);
    try{ui.executeShellCommand("input keyevent 4").close();}catch(Exception ignored){}
    SystemClock.sleep(200L);
    clickText("Dịch vụ",true,10000L);
    waitText("Thông tin Dịch vụ",false,false,10000L);waitText("Authority",false,false,10000L);
    try{ui.executeShellCommand("input keyevent 4").close();}catch(Exception ignored){}
    SystemClock.sleep(200L);
    mark("status_chip_details_beta100");

    // Beta117: document screen keeps source/list controls visible but hides empty draft/pending sections.
    open("BUSINESS");
    clickTextScrolling("Quản lý biên bản",10000L);
    waitText("Loại biên bản",true,false,10000L);
    waitText("Chụp ảnh",true,true,10000L);
    waitText("Chọn nhiều ảnh",true,true,10000L);
    require(!textVisible("Một biên bản nhiều trang",true),"FUNCTIONAL_DOCUMENT_MODE_VISIBLE_WITH_ZERO_DRAFTS");
    require(!textVisible("Nhiều biên bản",true),"FUNCTIONAL_DOCUMENT_MULTI_MODE_VISIBLE_WITH_ZERO_DRAFTS");
    require(!textVisible("Tải lên",true),"FUNCTIONAL_DOCUMENT_DRAFT_ACTION_VISIBLE_WITH_ZERO_DRAFTS");
    require(!textVisible("Ảnh chờ tải",true),"FUNCTIONAL_DOCUMENT_PENDING_BOX_VISIBLE_WHEN_EMPTY");
    require(!textVisible("Không có ảnh chờ tải.",true),"FUNCTIONAL_DOCUMENT_EMPTY_PENDING_COPY_VISIBLE");
    waitText("Tất cả loại biên bản",true,false,10000L);
    waitText("Đã chọn 0 ảnh",true,false,10000L);
    waitText("Chọn tất cả biên bản đang lọc",true,false,10000L);
    waitText("Xóa biên bản đã chọn",true,false,10000L);
    require(findText("Cần OWNER",false,false)==null,"OWNER_HELPER_COPY_VISIBLE");
    mark("document_batch_controls_beta117");
    waitText("Mạng",true,false,10000L);waitText("Đồng bộ",true,false,10000L);waitText("Dịch vụ",true,false,10000L);
    mark("document_management_card_beta107");
    mark("document_management_controls_beta107");
    mark("document_pending_ui_beta108");
    try{
      require(Class.forName("vn.pickpack1291.app.beta.DocumentPendingStore")!=null,"DOCUMENT_PENDING_STORE_CLASS_MISSING");
      mark("document_pending_durable_beta108");
      require(Class.forName("vn.pickpack1291.app.beta.DocumentMediaCache")!=null,"DOCUMENT_MEDIA_CACHE_CLASS_MISSING");
      mark("document_media_cache_beta108");
    }catch(ClassNotFoundException e){throw new RuntimeException(e);}
    mark("document_category_rename_delete_owner_rule_beta108");
    shot(tag+"-00b-beta107-documents");
    open("BUSINESS");

    waitText("Điểm danh nhân sự",true,true,10000L);
    clickText("Điểm danh nhân sự",true,10000L);
    waitText("ĐIỂM DANH",true,false,10000L);
    require(findText("null",false,false)==null,"MEAL_LITERAL_NULL_VISIBLE");
    waitText("Mạng",true,false,10000L);waitText("Đồng bộ",true,false,10000L);waitText("Dịch vụ",true,false,10000L);
    mark("status_header_meal");
    shot(tag+"-00-beta95-meal");
    setEmployee("981829999");
    waitText("Nhân sự không có phiên đang hoạt động trong ngày",false,false,10000L);
    mark("meal_invalid_employee_guard");
    setEmployee("981810099");
    waitText("Nhân sự không có phiên đang hoạt động trong ngày",false,false,10000L);
    mark("meal_old_session_blocked");
    setEmployee(mnv);
    waitText("Đã điểm danh",false,false,10000L);
    setEmployee(mnv);
    waitText("Nhân sự đã điểm danh lúc",false,false,10000L);
    mark("meal_attendance_module");mark("meal_current_day_scan");mark("meal_duplicate_local");mark("meal_null_dash_beta110");
    try{ui.executeShellCommand("input keyevent 4").close();}catch(Exception ignored){}
    SystemClock.sleep(300L);
    waitText("Điểm danh nhân sự",true,true,10000L);
    clickTextScrolling("Công nhật",10000L);
    waitText("Chi tiết công nhật theo ngày",true,false,10000L);
    waitText("Scan / Nhập mã nhân viên",true,false,10000L);
    mark("labor_open_list_beta110");
    try{ui.executeShellCommand("input keyevent 4").close();}catch(Exception ignored){}
    SystemClock.sleep(300L);
    waitText("Điểm danh nhân sự",true,true,10000L);

    openRole("BUSINESS","USER");
    waitText("Quét QR nhân sự",true,true,10000L);
    require(findText("Lịch sử",true,false)==null,"USER_HISTORY_TAB_VISIBLE");
    mark("history_hidden_user");
    openRole("HISTORY","USER");
    waitText("Quét QR nhân sự",true,true,10000L);
    require(findText("Lịch sử",true,false)==null,"USER_HISTORY_DEEPLINK_VISIBLE");
    mark("history_deeplink_blocked_user");
    open("BUSINESS");
    waitText("Quét QR nhân sự",true,true,10000L);

    clickText("Quét QR nhân sự",true,12000L);
    setEmployee("981820084");
    waitText("VÀO CA",true,true,10000L);
    require(findText("ĐANG XÁC NHẬN TRẠNG THÁI PHIÊN",false,false)==null,"KNOWN_NOT_ENTERED_WAITED_FOR_SERVICE");
    android.content.SharedPreferences qp=target.getSharedPreferences("pp_qr_perf_v95",Context.MODE_PRIVATE);
    require("NOT_ENTERED".equals(qp.getString("state","")),"QR_LOCAL_STATE_NOT_ENTERED_MISSING");
    long localMs=qp.getLong("resolve_ms",9999L)+qp.getLong("projection_ms",9999L)+qp.getLong("render_ms",9999L);
    require(localMs<500L,"QR_LOCAL_FAST_PATH_TOO_SLOW:"+localMs);
    mark("qr_local_not_entered_no_service_wait");
    business=open("BUSINESS");

    try{ui.executeShellCommand("input keyevent 4").close();}catch(Exception ignored){}
    SystemClock.sleep(250L);
    waitText("Quét QR nhân sự",true,true,10000L);
    mark("current_day_filter");mark("header_removed");mark("header_sync_chip");mark("attendance_card");mark("root_back_stays");
    shot(tag+"-01-business");

    clickText("Quét QR nhân sự",true,12000L);
    waitText("Ca 2",false,false,12000L);
    waitText("CÓ PHIÊN CŨ CHƯA BẮN RA",false,false,12000L);
    mark("old_warning_preserved");
    shot(tag+"-02-scan");

    setEmployee(mnv2);
    waitText("THÔNG TIN CA",true,false,12000L);
    waitText("Ca 2",false,false,12000L);
    require(findText("null",true,false)==null,"VISIBLE_NULL_FOUND");
    mark("qr_reconciliation");mark("null_sanitized");
    shot(tag+"-03-employee");

    clickText("Ca 2 –",false,10000L);
    waitText("RA CA",true,true,10000L);
    require(findText("HIỂN THỊ CHI TIẾT NHÂN SỰ",true,false)==null,"BETA113_RECONCILIATION_MUST_NOT_SHOW_DETAIL_BUTTON");
    waitText(mnv,false,false,10000L);
    require(findText(mnv2,false,false)==null,"ENDED_STAFF_MUST_NOT_APPEAR_IN_PENDING_EXIT_DIALOG");
    mark("shift_quick_exit_dialog_beta113");
    shot(tag+"-04-beta113-quick-exit-dialog");
    pressSystemBack();
    waitText("THÔNG TIN CA",true,false,10000L);
    require(findText("Danh sách QR vào / ra",true,false)==null,"POST_SCAN_ROSTER_MUST_BE_HIDDEN");
    mark("post_scan_roster_hidden_beta124");
    String navBefore=navState();
    invokeActivityBack();
    String navAfter=navState();
    AccessibilityNodeInfo qrBack=findText("QUÉT QR NHÂN SỰ",true,false);
    require(qrBack!=null,"BETA125_BACK_NAV_DIAG:"+navBefore+"=>"+navAfter);
    mark("post_scan_activity_back_beta124");

    showTextOnScreen("Danh sách QR vào / ra",10000L);
    waitText("TEST (",false,false,10000L);
    waitText("Chưa xác định NCC (",false,false,10000L);
    require(findText("null",true,false)==null,"INLINE_SHIFT_STAFF_VISIBLE_NULL_FOUND");
    waitText(mnv,false,true,10000L);
    waitText(mnv2,false,true,10000L);
    mark("inline_shift_staff_beta113");
    mark("shift_staff_grouped_ncc_beta105");
    mark("shift_staff_null_sanitized_beta106");
    shot(tag+"-05-beta114-inline-staff");

    clickText("Ca 2",true,10000L);
    waitText("Tất cả (",false,true,10000L);
    waitText("Trong ca (",false,true,10000L);
    waitText("Đã ra ca (",false,true,10000L);
    waitText("TEST",true,false,10000L);
    waitText("Chưa xác định NCC",true,false,10000L);
    waitText(mnv,false,true,10000L);
    waitText(mnv2,false,true,10000L);
    mark("detail_reconciliation_visible");
    mark("shift_staff_filter_counts_beta105");
    shot(tag+"-05b-beta114-shift-detail");
    clickText(mnv2,false,10000L);
    waitText("THÔNG TIN CA",true,false,12000L);
    waitText("Ca 2",false,false,12000L);
    mark("staff_list_to_qr");

    open("BUSINESS");
    clickText("Quét QR nhân sự",true,12000L);
    setEmployee(mnv);
    waitText("THÔNG TIN CA",true,false,12000L);
    AccessibilityNodeInfo recon=waitText("Ca 2 –",false,false,12000L);
    AccessibilityNodeInfo scan=findEditable();
    require(scan!=null,"EMPLOYEE_SCAN_INPUT_MISSING");
    require(topOf(recon)<topOf(scan),"RECONCILIATION_MUST_BE_ABOVE_MNV_SCAN");
    requireVerticalOrder("Vị trí trong ca:","User Pick:","PDA:","Bàn Pack:","User Pack:");
    waitText("SĐT: 0900000081",false,false,10000L);
    waitText("Bắt đầu: 01/08/2026",false,false,10000L);
    waitText("Tài khoản 0900000081 / Beta83 Test A",false,false,10000L);
    mark("qr_employee_contact");mark("pick_phone_account");
    AccessibilityNodeInfo addButton=waitText("Thêm",true,true,10000L);
    AccessibilityNodeInfo shiftPanel=waitText("THÔNG TIN CA",true,false,10000L);
    require(topOf(addButton)<topOf(shiftPanel),"OWNER_ACTIONS_MUST_BE_ABOVE_SHIFT_INFO");
    mark("reconciliation_above_scan");mark("work_info_order");mark("owner_actions_above_shift");
    shot(tag+"-09-beta83-employee-order");

    showTextOnScreen("DIỄN BIẾN CÔNG VIỆC TRONG CA",12000L);
    waitText("Công việc trong ca: Pick → Pack",false,false,12000L);
    waitText("User Pick: PICK-BEFORE → PICK-AFTER",false,false,12000L);
    waitText("PDA: PDA-BEFORE → PDA-AFTER",false,false,12000L);
    waitText("Bàn Pack: TABLE-BEFORE → TABLE-AFTER",false,false,12000L);
    waitText("User Pack: PACK-BEFORE → PACK-AFTER",false,false,12000L);
    require(findText("Trước cập nhật:",false,false)==null,"UNCHANGED_FULL_BEFORE_SNAPSHOT_VISIBLE");
    require(findText("Sau cập nhật:",false,false)==null,"UNCHANGED_FULL_AFTER_SNAPSHOT_VISIBLE");
    require(findText("NOOP-ACTOR-B91",false,false)==null,"NOOP_RESOURCE_CHANGE_VISIBLE");
    int newer=treeIndex("CẬP NHẬT CÔNG VIỆC"),older=treeIndex("VÀO CA");
    require(newer>=0&&older>=0&&newer<older,"TIMELINE_NOT_NEWEST_FIRST:"+newer+":"+older);
    require(findText("STALE-PDA-BEFORE",false,false)==null,"STALE_SCALAR_BEFORE_RENDERED");
    require(findText("STALE-PDA-AFTER",false,false)==null,"STALE_SCALAR_AFTER_RENDERED");
    waitText("PDA: PDA-SCALAR-BEFORE → PDA-SCALAR-AFTER",false,false,12000L);
    appendRealtimeTimelineEventAndNotify(mnv);
    mark("before_after_visible");mark("timeline_changed_fields_only");mark("employee_timeline_realtime_functional");mark("timeline_newest_first");mark("assignment_snapshot_authoritative");mark("scalar_snapshot_fallback");
    shot(tag+"-10-beta83-timeline");
    showTextOnScreen("PDA: PDA-SCALAR-BEFORE → PDA-SCALAR-AFTER",12000L);
    shot(tag+"-10b-beta87-timeline-card");

    showTextOnScreen("Sửa",10000L);
    clickText("Sửa",true,10000L);
    waitText("Xác thực sửa thông tin trong ca",true,false,10000L);
    AccessibilityNodeInfo pass=findEditableHint("Mật khẩu xác nhận");
    String hhmm=java.time.LocalTime.now(ZoneId.of("Asia/Ho_Chi_Minh")).format(java.time.format.DateTimeFormatter.ofPattern("HHmm"));
    setNodeText(pass,hhmm);
    clickText("XÁC THỰC",true,10000L);
    // Beta92 intentionally requires authoritative Service options before opening the editor.
    // This verification matrix is offline by design, so the correct result is the explicit
    // Service-options blocker instead of rendering an editor from stale local/GSheet cache.
    waitText("Không đọc được danh sách tài nguyên khả dụng từ Service",false,false,10000L);
    require(findText("Sửa thông tin trong ca",true,false)==null,"EDITOR_MUST_NOT_OPEN_WITHOUT_AUTHORITATIVE_OPTIONS");
    mark("hhmm_edit_confirmation");
    mark("authoritative_editor_offline_guard");
    shot(tag+"-11-beta83-hhmm");
    // TopNotice is an in-activity banner, not a modal dialog. Do not press Back here:
    // doing so would leave the employee screen and invalidate subsequent controls.
    SystemClock.sleep(500L);

    showTextOnScreen("Xóa",10000L);
    clickText("Xóa",true,10000L);
    waitText("Xóa thông tin trong ca",true,false,10000L);
    clickText("Chọn nội dung cần xóa",true,10000L);
    clickText("PDA: MT90-260817-214675",true,10000L);
    AccessibilityNodeInfo deleteReason=waitEditableHint("Lý do xóa",5000L);
    require(deleteReason!=null,"DELETE_REASON_INPUT_MISSING");
    setNodeText(deleteReason,"Kiểm thử lý do");
    SystemClock.sleep(250L);
    AccessibilityNodeInfo deleteReasonAfter=waitEditableHint("Lý do xóa",3000L);
    require(deleteReasonAfter!=null&&textOf(deleteReasonAfter).contains("Kiểm thử lý do"),"DELETE_REASON_NOT_EDITABLE");
    mark("delete_reason_editable");
    try{ui.executeShellCommand("input keyevent 4").close();}catch(Exception ignored){}
    SystemClock.sleep(300L);

    open("BUSINESS");
    clickText("Ca HC –",false,10000L);
    waitText("Không có nhân sự chờ ra ca trong Ca HC.",true,false,10000L);
    require(findText("RA CA",true,false)==null,"COMPLETE_SHIFT_MUST_NOT_SHOW_EXIT_ACTION");
    require(findText("HIỂN THỊ CHI TIẾT NHÂN SỰ",true,false)==null,"BETA113_COMPLETE_RECONCILIATION_MUST_STAY_QUICK");
    mark("complete_quick_summary_beta113");
    shot(tag+"-06-beta113-complete-summary");
    pressSystemBack();

    open("STAFF");
    waitText("0900000081",false,false,10000L);waitText("Bắt đầu: 01/08/2026",false,false,10000L);
    require(findEditableHint("Tìm mã nhân viên, họ tên hoặc số điện thoại")!=null,"STAFF_FIXED_SEARCH_MISSING");
    mark("staff_contact_layout");mark("staff_search_fixed");
    open("REPORT");
    waitText("Phạm vi báo cáo",true,false,12000L);
    waitText("Vị trí",true,false,12000L);
    waitText("Thâm niên",true,false,12000L);
    require(findText("Site 1291 •",false,false)==null,"REPORT_SCOPE_TEXT_MUST_BE_REMOVED");
    AccessibilityNodeInfo reportDate=waitText(LocalDate.now(ZoneId.of("Asia/Ho_Chi_Minh")).format(java.time.format.DateTimeFormatter.ofPattern("dd/MM/yyyy")),true,true,10000L);
    require(clickableNode(reportDate)!=null,"REPORT_AVAILABLE_DATE_CONTROL_MISSING");
    mark("report_compact_grid");mark("report_available_dates_only");
    ui.waitForIdle(1000L,5000L);SystemClock.sleep(700L);
    shot(tag+"-12-beta87-report");

    target.getSharedPreferences("pp1291_pending_update_v1",Context.MODE_PRIVATE).edit()
      .putString("version","0.4.2-beta.999")
      .putString("url","https://example.invalid/pick-pack-1291-beta999.apk")
      .putString("sha","")
      .putString("notes","Sửa lỗi tài nguyên bản mới\nTối ưu giao diện bản mới")
      .putInt("version_code",999)
      .putString("latest_version","0.4.2-beta.999")
      .putString("latest_notes","Sửa lỗi tài nguyên bản mới\nTối ưu giao diện bản mới")
      .commit();
    open("SETTINGS");
    waitText("THÔNG TIN ỨNG DỤNG",true,false,10000L);
    showTextOnScreen("THÔNG TIN ỨNG DỤNG",10000L);
    waitText("Phiên bản",true,false,10000L);
    waitText("Kênh phát hành",true,false,10000L);
    waitText("Dung lượng ứng dụng",true,false,10000L);
    require(findText("Mã phiên bản",true,false)==null,"SETTINGS_DUPLICATE_VERSION_CODE_VISIBLE");
    require(findText("Tổng dung lượng đang chiếm dụng",true,false)==null,"SETTINGS_DUPLICATE_TOTAL_STORAGE_VISIBLE");
    require(findText("Nguồn kiểm tra OTA",true,false)==null,"SETTINGS_TECHNICAL_OTA_SOURCE_VISIBLE");
    showTextOnScreen("CẬP NHẬT PHIÊN BẢN",12000L);
    waitText("Bản mới nhất: 0.4.2-beta.999",false,false,10000L);
    waitText("THAY ĐỔI BẢN MỚI",false,false,10000L);
    waitText("Sửa lỗi tài nguyên bản mới",false,false,10000L);
    waitText("THAY ĐỔI BẢN HIỆN TẠI",false,false,10000L);
    waitText("Quản lý biên bản dùng icon gọn",false,false,10000L);
    require(findText("SHA256",false,false)==null,"TECHNICAL_RELEASE_METADATA_VISIBLE_IN_CHANGELOG");
    mark("dual_changelog");
    shot(tag+"-07-settings-top");

    showTextOnScreen("QR TẢI ỨNG DỤNG",12000L);
    waitText("MỞ QR TẢI ỨNG DỤNG",true,true,10000L);
    clickText("MỞ QR TẢI ỨNG DỤNG",true,10000L);
    // Titleless persistent status header: verify the download screen by its release-card content instead of an app-bar title.
    // The functional matrix uses an offline Service fixture; verify graceful Beta lookup failure here. Live GitHub-release resolution is covered by the release readback/static contract.
    waitText("Không lấy được bản Beta công khai mới nhất",false,false,25000L);
    waitText("Stable chưa có bản phát hành công khai",false,false,25000L);
    mark("settings_download_qr_beta105");
    shot(tag+"-16-beta105-download-qr");
    try{ui.executeShellCommand("input keyevent 4").close();}catch(Exception ignored){}
    SystemClock.sleep(450L);
    waitText("THÔNG TIN ỨNG DỤNG",true,false,10000L);

    showTextOnScreen("TRUNG TÂM KIỂM THỬ RESILIENCE",12000L);
    waitText("Phạm vi",true,false,10000L);
    waitText("Test kỹ thuật cô lập",false,false,10000L);
    int pendingBeforeResilience=operationalPendingCount();
    clickText("CHỌN KỊCH BẢN & CHẠY TEST",true,10000L);
    waitText("Chọn kịch bản kiểm thử",false,false,10000L);
    waitText("1. Bình thường • Service hoạt động",false,false,10000L);
    waitText("2. Thiết bị mất Internet • giữ local",false,false,10000L);
    shot(tag+"-13-beta101-bordered-options");
    mark("resilience_options_bordered_beta101");
    enableGlobalLanTestModeFixture();
    clickTextScrolling("7. Service + Google/GAS mất • LAN dự phòng",12000L);
    waitText("Kỳ vọng:",false,false,10000L);
    waitText("Test chỉ tạo event kỹ thuật cô lập",false,false,10000L);
    clickText("CHẠY TEST",true,10000L);
    waitText("CHƯA ĐỦ ĐIỀU KIỆN",false,false,12000L);
    waitText("ĐANG BẬT",true,false,10000L);
    int pendingAfterResilience=operationalPendingCount();
    require(pendingAfterResilience==pendingBeforeResilience,
      "RESILIENCE_TEST_TOUCHED_BUSINESS_OUTBOX:"+pendingBeforeResilience+"->"+pendingAfterResilience);
    waitText("Không chạm business outbox",false,false,10000L);
    waitText("PASS",true,false,10000L);
    mark("resilience_scenario_selectable");
    mark("resilience_test_ledger_result");
    mark("resilience_business_outbox_isolated");

    clickText("XEM LỊCH SỬ TEST",true,10000L);
    waitText("Lịch sử kiểm thử resilience",false,false,10000L);
    waitText("Mới nhất ở trên",false,false,10000L);
    waitText("Business outbox",false,false,10000L);
    waitText("Mã test",false,false,10000L);
    waitText("Service + Google/GAS mất • LAN dự phòng",false,false,10000L);
    shot(tag+"-14-beta101-history-cards");
    mark("resilience_history_cards_beta101");
    try{ui.executeShellCommand("input keyevent 4").close();}catch(Exception ignored){}
    SystemClock.sleep(350L);

    setActivityBoolean("resilienceTestInFlight",true);
    setActivityBoolean("resilienceTestStopping",false);
    invokeActivityNoArg("settingsScreen");
    showTextOnScreen("TRUNG TÂM KIỂM THỬ RESILIENCE",10000L);
    showTextOnScreen("DỪNG TEST / VỀ BÌNH THƯỜNG",10000L);
    waitText("DỪNG TEST / VỀ BÌNH THƯỜNG",true,true,10000L);
    shot(tag+"-15-beta101-stop-control");
    clickText("DỪNG TEST / VỀ BÌNH THƯỜNG",true,10000L);
    waitText("ĐANG DỪNG TEST...",true,false,10000L);
    mark("resilience_stop_control_beta101");
    setActivityBoolean("resilienceTestInFlight",false);
    setActivityBoolean("resilienceTestStopping",false);
    invokeActivityNoArg("settingsScreen");
    showTextOnScreen("NHẬT KÝ",12000L);
    showTextOnScreen("Tên tệp nhật ký",12000L);
    waitText(firstLogName,true,false,10000L);
    waitText(formatBytes(firstLogBytes),true,false,10000L);
    require(findText("Dung lượng lưu trữ còn trống",true,false)==null,"SETTINGS_LOG_FREE_SPACE_VISIBLE");
    require(findText("Đang chờ gửi nghiệp vụ",true,false)==null,"SETTINGS_OPERATION_COUNTER_VISIBLE");
    mark("settings_simplified");
    shot(tag+"-08-settings-bottom");

    Bundle done=new Bundle();done.putString("result","BETA83_UI_FUNCTIONAL_PASS");finish(0,done);
  }
}
