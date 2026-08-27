package vn.pickpack1291.verify;

import android.app.Activity;
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
import java.lang.reflect.Method;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayDeque;
import java.util.Locale;
import org.json.JSONArray;
import org.json.JSONObject;

public final class Beta82UiChecksInstrumentation extends Instrumentation {
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
      String mode=args.getString("mode","checks");
      if(!"checks".equals(mode))throw new IllegalArgumentException("MODE_UNSUPPORTED:"+mode);
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
      .putString("token","beta82-local-ui-fixture")
      .putString("login_id","beta82_verify")
      .putString("display_name","Beta82 Verify")
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
      .putString("service_token","offline-beta82")
      .putString("discovery_json",discovery)
      .putLong("discovery_at",System.currentTimeMillis())
      .commit();
  }

  private Activity open(String module){
    seedAuth();seedService();
    Intent i=new Intent();
    i.setClassName(target,ACT);
    i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_CLEAR_TASK);
    i.putExtra("module",module);
    i.putExtra("login","beta82_verify");
    i.putExtra("name","Beta82 Verify");
    i.putExtra("role","SUPERADMIN");
    i.putExtra("position","TEST");
    i.putExtra("email","verify@example.invalid");
    target.startActivity(i);
    long end=SystemClock.uptimeMillis()+10000L;
    while(SystemClock.uptimeMillis()<end){
      AccessibilityNodeInfo r=root();
      CharSequence p=r==null?null:r.getPackageName();
      if(p!=null&&PKG.equals(p.toString())){
        SystemClock.sleep(250L);
        return null;
      }
      SystemClock.sleep(150L);
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
    while(SystemClock.uptimeMillis()<end&&n==null){n=findEditable();if(n==null)SystemClock.sleep(180L);}
    if(n==null)throw new IllegalStateException("EMPLOYEE_INPUT_NOT_FOUND");
    Bundle b=new Bundle();
    b.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,mnv);
    if(!n.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT,b))throw new IllegalStateException("EMPLOYEE_SET_TEXT_FAILED");
    n.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
    try{ui.executeShellCommand("input keyevent 66").close();}catch(Exception e){throw new RuntimeException(e);}
    SystemClock.sleep(700L);
  }

  private void mark(String key){
    target.getSharedPreferences("pp_beta82_verify",Context.MODE_PRIVATE).edit()
      .putBoolean(key,true).putLong(key+"_at",System.currentTimeMillis()).commit();
  }
  private static void require(boolean v,String e){if(!v)throw new IllegalStateException(e);}

  private void shot(String name)throws Exception{
    Bitmap b=ui.takeScreenshot();
    if(b==null)throw new IllegalStateException("SCREENSHOT_NULL:"+name);
    File dir=new File(target.getExternalFilesDir(null),"beta82-visual");
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
      .put("ok",true).put("master_revision",82001L)
      .put("staff",new JSONArray()
        .put(new JSONObject().put("mnv",mnv).put("full_name","Beta82 Test A").put("main_position","PICK").put("supplier","TEST").put("department","OPS").put("site","1291").put("warehouse","HY1"))
        .put(new JSONObject().put("mnv",mnv2).put("full_name","Beta82 Test B").put("main_position","PACK").put("supplier",JSONObject.NULL).put("department","OPS").put("site","1291").put("warehouse","HY1"))
        .put(new JSONObject().put("mnv",mnv3).put("full_name","Beta82 Test C").put("main_position","PACK").put("supplier","TEST").put("department","OPS").put("site","1291").put("warehouse","HY1")))
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
      .put("session_id","beta82-current-active").put("mnv",mnv).put("business_date",today).put("shift","Ca 2")
      .put("state","ACTIVE").put("enter_at",today+"T01:00:00Z").put("exit_at","").put("version",1)
      .put("positions_v64",new JSONArray().put(new JSONObject().put("position_key","PICK").put("position_label","Pick").put("state","ACTIVE")))
      .put("resource_assignments_v64",emptyAssignments);
    JSONObject b=new JSONObject()
      .put("session_id","beta82-current-ended").put("mnv",mnv2).put("business_date",today).put("shift","Ca 2")
      .put("state","ENDED").put("enter_at",today+"T01:05:00Z").put("exit_at",today+"T02:00:00Z").put("version",2)
      .put("pack_table","B82-TABLE").put("user_pack",JSONObject.NULL)
      .put("positions_v64",new JSONArray().put(new JSONObject().put("position_key","PACK").put("position_label","Pack").put("state","ENDED")))
      .put("resource_assignments_v64",new JSONArray());
    JSONObject c=new JSONObject()
      .put("session_id","beta82-hc-ended").put("mnv",mnv3).put("business_date",today).put("shift","Ca HC")
      .put("state","ENDED").put("enter_at",today+"T01:15:00Z").put("exit_at",today+"T09:00:00Z").put("version",1)
      .put("pack_table","B82-HC").put("user_pack","PACK-B82")
      .put("positions_v64",new JSONArray().put(new JSONObject().put("position_key","PACK").put("position_label","Pack").put("state","ENDED")))
      .put("resource_assignments_v64",new JSONArray());
    JSONObject leakedOld=new JSONObject()
      .put("session_id","beta82-leaked-old").put("mnv","981810099").put("business_date",oldDate).put("shift","Ca 1")
      .put("state","ACTIVE").put("enter_at",oldDate+"T01:00:00Z").put("exit_at","").put("version",1)
      .put("positions_v64",new JSONArray()).put("resource_assignments_v64",new JSONArray());

    saveDay.invoke(store,new JSONObject().put("business_date",today).put("day_revision",82001L)
      .put("sessions",new JSONArray().put(a).put(b).put(c).put(leakedOld))
      .put("events",new JSONArray()).put("labor",new JSONArray()));

    saveDay.invoke(store,new JSONObject().put("business_date",oldDate).put("day_revision",82002L)
      .put("sessions",new JSONArray().put(leakedOld))
      .put("events",new JSONArray()).put("labor",new JSONArray()));
  }

  private void runChecks()throws Exception{
    String tag=req("tag"),mnv=req("mnv"),mnv2=req("mnv2"),mnv3=req("mnv3");
    seedAuth();seedService();seedData(mnv,mnv2,mnv3);

    open("BUSINESS");
    waitText("Ca 1 – 0/0",true,false,12000L);
    waitText("Ca HC – 1/1",true,false,12000L);
    waitText("Ca 2 – 2/1",true,false,12000L);
    require(findText("RÀ SOÁT VÀO / RA",false,false)==null,"REDUNDANT_RECONCILIATION_HEADER_VISIBLE");
    mark("current_day_filter");mark("header_removed");
    shot(tag+"-01-business");

    clickText("Quét QR nhân sự",true,12000L);
    waitText("Ca 2 – 2/1",true,false,12000L);
    waitText("CHƯA KẾT THÚC PHIÊN CÁC NGÀY CŨ",false,false,12000L);
    mark("old_warning_preserved");
    shot(tag+"-02-scan");

    setEmployee(mnv2);
    waitText("THÔNG TIN CA",true,false,12000L);
    waitText("Ca 2 – 2/1",true,false,12000L);
    require(findText("null",true,false)==null,"VISIBLE_NULL_FOUND");
    mark("qr_reconciliation");mark("null_sanitized");
    shot(tag+"-03-employee");

    clickText("Ca 2 – 2/1",true,10000L);
    waitText("HIỂN THỊ CHI TIẾT NHÂN SỰ",true,true,10000L);
    waitText("RA CA",true,true,10000L);
    mark("incomplete_detail_button");
    shot(tag+"-04-incomplete-dialog");

    clickText("HIỂN THỊ CHI TIẾT NHÂN SỰ",true,10000L);
    waitText(mnv,false,true,10000L);
    waitText(mnv2,false,true,10000L);
    shot(tag+"-05-staff-list");
    clickText(mnv2,false,10000L);
    waitText("THÔNG TIN CA",true,false,12000L);
    waitText("Ca 2 – 2/1",true,false,12000L);
    mark("staff_list_to_qr");

    open("BUSINESS");
    clickText("Ca HC – 1/1",true,10000L);
    waitText(mnv3,false,true,10000L);
    require(findText("HIỂN THỊ CHI TIẾT NHÂN SỰ",true,false)==null,"COMPLETE_SHIFT_SHOULD_OPEN_LIST_DIRECTLY");
    mark("complete_direct_list");
    shot(tag+"-06-complete-list");

    open("SETTINGS");
    waitText("THÔNG TIN ỨNG DỤNG",true,false,10000L);
    showTextOnScreen("THÔNG TIN ỨNG DỤNG",10000L);
    waitText("Phiên bản",true,false,10000L);
    waitText("Kênh phát hành",true,false,10000L);
    waitText("Dung lượng ứng dụng",true,false,10000L);
    require(findText("Mã phiên bản",true,false)==null,"SETTINGS_DUPLICATE_VERSION_CODE_VISIBLE");
    require(findText("Tổng dung lượng đang chiếm dụng",true,false)==null,"SETTINGS_DUPLICATE_TOTAL_STORAGE_VISIBLE");
    require(findText("Nguồn kiểm tra OTA",true,false)==null,"SETTINGS_TECHNICAL_OTA_SOURCE_VISIBLE");
    shot(tag+"-07-settings-top");
    showTextOnScreen("NHẬT KÝ",12000L);
    showTextOnScreen("Tên tệp nhật ký",12000L);
    require(findText("Dung lượng lưu trữ còn trống",true,false)==null,"SETTINGS_LOG_FREE_SPACE_VISIBLE");
    require(findText("Đang chờ gửi nghiệp vụ",true,false)==null,"SETTINGS_OPERATION_COUNTER_VISIBLE");
    mark("settings_simplified");
    shot(tag+"-08-settings-bottom");

    Bundle done=new Bundle();done.putString("result","BETA82_UI_FUNCTIONAL_PASS");finish(0,done);
  }
}
