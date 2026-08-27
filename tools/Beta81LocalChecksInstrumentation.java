package vn.pickpack1291.verify;

import android.app.Instrumentation;
import android.app.UiAutomation;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.accessibility.AccessibilityNodeInfo;
import java.lang.reflect.Method;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayDeque;
import java.util.Locale;
import org.json.JSONArray;
import org.json.JSONObject;

public final class Beta81LocalChecksInstrumentation extends Instrumentation {
  private Bundle args;
  private UiAutomation ui;
  private Context target;
  private static final String PKG="vn.pickpack1291.app.beta.publicbeta";
  private static final String ACT="vn.pickpack1291.app.beta.OperationsActivity";

  @Override public void onCreate(Bundle b){ super.onCreate(b); args=b; start(); }

  @Override public void onStart(){
    try{
      target=getTargetContext();
      ui=getUiAutomation();
      runChecks();
    }catch(Throwable t){
      Bundle x=new Bundle();
      x.putString("error",t.getClass().getSimpleName()+":"+String.valueOf(t.getMessage()));
      finish(1,x);
    }
  }

  private String req(String k){
    String v=args.getString(k);
    if(v==null||v.trim().isEmpty())throw new IllegalArgumentException(k+"_REQUIRED");
    return v.trim();
  }

  private void seedAuth(){
    target.getSharedPreferences("pick_pack_auth_session_v2",Context.MODE_PRIVATE).edit()
      .putString("token","beta81-local-ui-fixture")
      .putString("login_id",args.getString("login","beta81_verify"))
      .putString("display_name","Beta81 Verify")
      .putString("role","SUPERADMIN")
      .putString("position","TEST")
      .putString("email","verify@example.invalid")
      .commit();
  }

  private void seedService(){
    String token=req("service_token"), url=req("service_url");
    String discovery="{\"ok\":true,\"authority_mode\":\"SERVICE_PRIMARY\",\"service_url\":\""+
      url.replace("\\","\\\\").replace("\"","\\\"")+"\"}";
    target.getSharedPreferences("pp_m2_service_transport",Context.MODE_PRIVATE).edit()
      .putString("service_token",token)
      .putString("discovery_json",discovery)
      .putLong("discovery_at",System.currentTimeMillis())
      .commit();
  }

  private void open(String module){
    Intent i=new Intent();
    i.setClassName(target,ACT);
    i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_CLEAR_TASK);
    i.putExtra("module",module);
    i.putExtra("login",args.getString("login","beta81_verify"));
    i.putExtra("name","Beta81 Verify");
    i.putExtra("role","SUPERADMIN");
    i.putExtra("position","TEST");
    target.startActivity(i);
    long end=SystemClock.uptimeMillis()+10000L;
    while(SystemClock.uptimeMillis()<end){
      AccessibilityNodeInfo r=root();
      CharSequence p=r==null?null:r.getPackageName();
      if(p!=null&&PKG.equals(p.toString()))return;
      SystemClock.sleep(200L);
    }
    throw new IllegalStateException("ACTIVITY_START_TIMEOUT:"+module);
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
    for(int i=0;i<6&&x!=null;i++,x=x.getParent()) if(x.isClickable()) return x;
    return null;
  }

  private AccessibilityNodeInfo findText(String needle,boolean exact,boolean clickable){
    AccessibilityNodeInfo r=root();
    if(r==null)return null;
    String q=needle.trim().toUpperCase(Locale.ROOT);
    ArrayDeque<AccessibilityNodeInfo> dq=new ArrayDeque<>();
    dq.add(r);
    while(!dq.isEmpty()){
      AccessibilityNodeInfo n=dq.removeFirst();
      String t=textOf(n).toUpperCase(Locale.ROOT);
      boolean match=exact?t.equals(q):t.contains(q);
      if(match&&(!clickable||clickableNode(n)!=null))return n;
      for(int i=0;i<n.getChildCount();i++){
        AccessibilityNodeInfo c=n.getChild(i);
        if(c!=null)dq.addLast(c);
      }
    }
    return null;
  }

  private AccessibilityNodeInfo waitText(String text,boolean exact,boolean clickable,long timeout){
    long end=SystemClock.uptimeMillis()+timeout;
    while(SystemClock.uptimeMillis()<end){
      AccessibilityNodeInfo n=findText(text,exact,clickable);
      if(n!=null)return n;
      SystemClock.sleep(200);
    }
    throw new IllegalStateException("TEXT_NOT_FOUND:"+text);
  }

  private void clickText(String text,boolean exact,long timeout){
    AccessibilityNodeInfo n=waitText(text,exact,true,timeout);
    AccessibilityNodeInfo c=clickableNode(n);
    if(c==null||!c.performAction(AccessibilityNodeInfo.ACTION_CLICK))
      throw new IllegalStateException("CLICK_FAILED:"+text);
    SystemClock.sleep(350);
  }

  private AccessibilityNodeInfo findEditable(String hintPart){
    AccessibilityNodeInfo r=root();
    if(r==null)return null;
    String q=hintPart.toUpperCase(Locale.ROOT);
    ArrayDeque<AccessibilityNodeInfo> dq=new ArrayDeque<>();
    dq.add(r);
    while(!dq.isEmpty()){
      AccessibilityNodeInfo n=dq.removeFirst();
      String cls=String.valueOf(n.getClassName());
      CharSequence hint=n.getHintText();
      String h=hint==null?"":hint.toString().toUpperCase(Locale.ROOT);
      if(cls.contains("EditText")&&(h.contains(q)||textOf(n).toUpperCase(Locale.ROOT).contains(q)))return n;
      for(int i=0;i<n.getChildCount();i++){
        AccessibilityNodeInfo c=n.getChild(i);
        if(c!=null)dq.addLast(c);
      }
    }
    return null;
  }

  private void setEmployee(String mnv){
    long end=SystemClock.uptimeMillis()+15000;
    AccessibilityNodeInfo n=null;
    while(SystemClock.uptimeMillis()<end&&n==null){
      n=findEditable("MÃ NHÂN VIÊN");
      if(n==null)n=findEditable("SCAN");
      if(n==null)SystemClock.sleep(200);
    }
    if(n==null)throw new IllegalStateException("EMPLOYEE_INPUT_NOT_FOUND");
    Bundle b=new Bundle();
    b.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,mnv);
    if(!n.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT,b))
      throw new IllegalStateException("EMPLOYEE_SET_TEXT_FAILED");
    n.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
    try{ui.executeShellCommand("input keyevent 66").close();}catch(Exception e){throw new RuntimeException(e);}
    SystemClock.sleep(600);
  }

  private void mark(String key){
    target.getSharedPreferences("pp_beta81_verify",Context.MODE_PRIVATE).edit()
      .putBoolean(key,true).putLong(key+"_at",System.currentTimeMillis()).commit();
  }

  private static void require(boolean value,String error){
    if(!value)throw new IllegalStateException(error);
  }

  private void runChecks() throws Exception {
    String mnv=req("mnv"), mnv2=req("mnv2");
    seedAuth();
    seedService();

    String today=LocalDate.now(ZoneId.of("Asia/Ho_Chi_Minh")).toString();
    String oldDate=LocalDate.parse(today).minusDays(1).toString();

    JSONObject master=new JSONObject()
      .put("ok",true)
      .put("master_revision",81001L)
      .put("staff",new JSONArray()
        .put(new JSONObject().put("mnv",mnv).put("full_name","Beta81 Test A")
          .put("main_position","PICK").put("supplier","TEST").put("department","OPS").put("site","1291").put("warehouse","HY1"))
        .put(new JSONObject().put("mnv",mnv2).put("full_name","Beta81 Test B")
          .put("main_position","PACK").put("supplier","TEST").put("department","OPS").put("site","1291").put("warehouse","HY1")))
      .put("pdas",new JSONArray()
        .put(new JSONObject().put("serial","MT90-B81-OLD").put("status","Tốt"))
        .put(new JSONObject().put("serial","MT90-B81-FREE").put("status","Tốt")))
      .put("pda_statuses",new JSONArray().put("Tốt"))
      .put("user_picks",new JSONArray().put("PICK-B81-OLD").put("PICK-B81-FREE"))
      .put("pack_bundles",new JSONArray()
        .put(new JSONObject().put("table","TABLE-B81-OLD").put("user_pack","PACK-B81-OLD"))
        .put(new JSONObject().put("table","TABLE-B81-FREE").put("user_pack","PACK-B81-FREE")));

    ClassLoader cl=target.getClassLoader();
    Class<?> masterClass=cl.loadClass("vn.pickpack1291.app.beta.MasterDataCache");
    Object masterObj=masterClass.getField("INSTANCE").get(null);
    masterClass.getMethod("save",Context.class,JSONObject.class).invoke(masterObj,target,master);

    Class<?> storeClass=cl.loadClass("vn.pickpack1291.app.beta.OperationalDataStore");
    Object store=storeClass.getConstructor(Context.class).newInstance(target);
    Method saveDay=storeClass.getMethod("saveDay",JSONObject.class);

    JSONObject currentSession=new JSONObject()
      .put("session_id","beta81-current-active").put("mnv",mnv).put("business_date",today)
      .put("shift","Ca 2").put("work_choice","PICK").put("state","ACTIVE")
      .put("enter_at",today+"T12:00:00Z").put("exit_at","").put("version",1);
    saveDay.invoke(store,new JSONObject()
      .put("business_date",today).put("day_revision",81001L)
      .put("sessions",new JSONArray().put(currentSession))
      .put("events",new JSONArray()).put("labor",new JSONArray()));

    mark("phase_before_first_open");
    open("BUSINESS");
    mark("phase_after_first_open");
    waitText("Ca 2 – 1/0",true,false,15000);
    mark("reconciliation_home_1_0");
    clickText("Quét QR nhân sự",true,15000);
    waitText("Ca 2 – 1/0",true,false,15000);
    mark("reconciliation_qr_1_0");

    saveDay.invoke(store,new JSONObject()
      .put("business_date",today).put("day_revision",81002L)
      .put("sessions",new JSONArray()).put("events",new JSONArray()).put("labor",new JSONArray()));
    JSONObject oldSession=new JSONObject()
      .put("session_id","beta81-old-active").put("mnv",mnv).put("business_date",oldDate)
      .put("shift","Ca 2").put("work_choice","PICK").put("state","ACTIVE")
      .put("enter_at",oldDate+"T16:30:00Z").put("exit_at","").put("version",3)
      .put("pda_serial","MT90-B81-OLD").put("user_pick","PICK-B81-OLD")
      .put("pack_table","TABLE-B81-OLD").put("user_pack","PACK-B81-OLD");
    saveDay.invoke(store,new JSONObject()
      .put("business_date",oldDate).put("day_revision",81003L)
      .put("sessions",new JSONArray().put(oldSession))
      .put("events",new JSONArray()).put("labor",new JSONArray()));

    Class<?> projectionClass=cl.loadClass("vn.pickpack1291.app.beta.PdaLocalProjection");
    Object projection=projectionClass.getField("INSTANCE").get(null);
    JSONObject ctx=(JSONObject)projectionClass
      .getMethod("employeeContext",Context.class,String.class)
      .invoke(projection,target,mnv);
    require(ctx!=null&&"ACTIVE".equals(ctx.optString("state")),"ROLLOVER_STATE_NOT_ACTIVE");
    require(today.equals(ctx.optString("business_date")),"ROLLOVER_CONTEXT_DATE_NOT_NEW_DAY");
    JSONObject ses=ctx.optJSONObject("session");
    require(ses!=null&&"beta81-old-active".equals(ses.optString("session_id")),"ROLLOVER_WRONG_SESSION");
    require(oldDate.equals(ses.optString("business_date")),"ROLLOVER_OLD_DATE_LOST");
    mark("rollover_old_active_preserved");

    JSONObject options=(JSONObject)projectionClass
      .getMethod("resourceOptions",Context.class,String.class)
      .invoke(projection,target,mnv2);
    boolean pdaBusy=true;
    JSONArray pdas=options.optJSONArray("pdas");
    for(int i=0;i<(pdas==null?0:pdas.length());i++){
      JSONObject x=pdas.optJSONObject(i);
      if(x!=null&&"MT90-B81-OLD".equals(x.optString("serial")))pdaBusy=false;
    }
    boolean pickBusy=true;
    JSONArray picks=options.optJSONArray("user_picks");
    for(int i=0;i<(picks==null?0:picks.length());i++)
      if("PICK-B81-OLD".equals(picks.optString(i)))pickBusy=false;
    boolean packBusy=true;
    JSONArray packs=options.optJSONArray("pack_tables");
    for(int i=0;i<(packs==null?0:packs.length());i++){
      JSONObject x=packs.optJSONObject(i);
      if(x!=null&&("TABLE-B81-OLD".equals(x.optString("table"))||"PACK-B81-OLD".equals(x.optString("user_pack"))))
        packBusy=false;
    }
    require(pdaBusy&&pickBusy&&packBusy,"OLD_ACTIVE_RESOURCE_RELEASED");
    mark("old_resources_preserved");

    seedService();
    mark("phase_existing_qr_reused");
    setEmployee(mnv);
    waitText("CẢNH BÁO: PHIÊN CA CŨ",false,false,15000);
    waitText("Ra ca",true,true,15000);
    mark("scanned_old_warning");

    Bundle done=new Bundle();
    done.putString("result","BETA81_THREE_FIXES_PASS");
    finish(0,done);
  }
}
