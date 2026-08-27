package vn.pickpack1291.verify;

import android.app.Activity;
import android.app.Instrumentation;
import android.app.UiAutomation;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.os.SystemClock;
import android.util.Base64;
import android.view.accessibility.AccessibilityNodeInfo;
import java.util.ArrayDeque;
import java.util.Locale;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

public final class Beta80VerifyInstrumentation extends Instrumentation {
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
      String mode=req("mode");
      if("ota".equals(mode)) ota();
      else if("fileprovider".equals(mode)) fileprovider();
      else if("enter".equals(mode)) enter();
      else if("historical".equals(mode)) historical();
      else throw new IllegalArgumentException("MODE_UNSUPPORTED:"+mode);
    }catch(Throwable t){
      Bundle x=new Bundle();x.putString("error",t.getClass().getSimpleName()+":"+String.valueOf(t.getMessage()));
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
      .putString("token","beta80-pda-ui-fixture")
      .putString("login_id",args.getString("login","pda_verify"))
      .putString("display_name","Beta80 PDA Verify")
      .putString("role","SUPERADMIN")
      .putString("position","TEST")
      .putString("email","verify@example.invalid")
      .commit();
  }

  private void seedService(){
    String token=req("service_token"), url=req("service_url");
    String discovery="{\"ok\":true,\"authority_mode\":\"SERVICE_PRIMARY\",\"service_url\":\""+url.replace("\\","\\\\").replace("\"","\\\"")+"\"}";
    target.getSharedPreferences("pp_m2_service_transport",Context.MODE_PRIVATE).edit()
      .putString("service_token",token)
      .putString("discovery_json",discovery)
      .putLong("discovery_at",System.currentTimeMillis())
      .commit();
  }

  private Activity open(String module){
    Intent i=new Intent();
    i.setClassName(target,ACT);
    i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_CLEAR_TASK);
    i.putExtra("module",module);
    i.putExtra("login",args.getString("login","pda_verify"));
    i.putExtra("name","Beta80 PDA Verify");
    i.putExtra("role","SUPERADMIN");
    i.putExtra("position","TEST");
    return startActivitySync(i);
  }

  private static String textOf(AccessibilityNodeInfo n){
    CharSequence t=n.getText();
    if(t!=null&&!t.toString().trim().isEmpty())return t.toString().trim();
    CharSequence d=n.getContentDescription();
    return d==null?"":d.toString().trim();
  }

  private AccessibilityNodeInfo root(){ return ui.getRootInActiveWindow(); }

  private AccessibilityNodeInfo findText(String needle, boolean exact, boolean clickable){
    String q=needle.trim().toUpperCase(Locale.ROOT);
    AccessibilityNodeInfo r=root();
    if(r==null)return null;
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

  private AccessibilityNodeInfo findEditable(String hintPart){
    AccessibilityNodeInfo r=root();if(r==null)return null;
    String q=hintPart.toUpperCase(Locale.ROOT);
    ArrayDeque<AccessibilityNodeInfo> dq=new ArrayDeque<>();dq.add(r);
    while(!dq.isEmpty()){
      AccessibilityNodeInfo n=dq.removeFirst();
      String cls=String.valueOf(n.getClassName());
      CharSequence hint=n.getHintText();
      String h=hint==null?"":hint.toString().toUpperCase(Locale.ROOT);
      if((n.isEditable()||cls.contains("EditText")||cls.contains("AutoCompleteTextView"))&&(h.contains(q)||q.isEmpty()))return n;
      for(int i=0;i<n.getChildCount();i++){AccessibilityNodeInfo c=n.getChild(i);if(c!=null)dq.addLast(c);}
    }
    return null;
  }

  private AccessibilityNodeInfo clickableNode(AccessibilityNodeInfo n){
    AccessibilityNodeInfo x=n;
    for(int i=0;i<5&&x!=null;i++,x=x.getParent())if(x.isClickable())return x;
    return null;
  }

  private AccessibilityNodeInfo waitText(String text, boolean exact, boolean clickable, long timeout){
    long end=SystemClock.uptimeMillis()+timeout;
    while(SystemClock.uptimeMillis()<end){
      AccessibilityNodeInfo n=findText(text,exact,clickable);
      if(n!=null)return n;
      SystemClock.sleep(250);
    }
    throw new IllegalStateException("TEXT_NOT_FOUND:"+text);
  }

  private void clickText(String text, boolean exact, long timeout){
    AccessibilityNodeInfo n=waitText(text,exact,true,timeout);
    AccessibilityNodeInfo c=clickableNode(n);
    if(c==null||!c.performAction(AccessibilityNodeInfo.ACTION_CLICK))throw new IllegalStateException("CLICK_FAILED:"+text);
    SystemClock.sleep(350);
  }

  private boolean scrollForward(){
    AccessibilityNodeInfo r=root();if(r==null)return false;
    ArrayDeque<AccessibilityNodeInfo> dq=new ArrayDeque<>();dq.add(r);
    while(!dq.isEmpty()){
      AccessibilityNodeInfo n=dq.removeFirst();
      if(n.isScrollable()&&n.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)){SystemClock.sleep(450);return true;}
      for(int i=0;i<n.getChildCount();i++){AccessibilityNodeInfo c=n.getChild(i);if(c!=null)dq.addLast(c);}
    }
    return false;
  }

  private void clickTextScrolling(String text, boolean exact, long timeout){
    long end=SystemClock.uptimeMillis()+timeout;
    while(SystemClock.uptimeMillis()<end){
      AccessibilityNodeInfo n=findText(text,exact,true);
      if(n!=null){
        AccessibilityNodeInfo c=clickableNode(n);
        if(c!=null&&c.performAction(AccessibilityNodeInfo.ACTION_CLICK)){SystemClock.sleep(350);return;}
      }
      scrollForward();
      SystemClock.sleep(250);
    }
    throw new IllegalStateException("TEXT_NOT_FOUND_AFTER_SCROLL:"+text);
  }

  private void clickActionNear(String identity,String action,long timeout){
    long end=SystemClock.uptimeMillis()+timeout;
    while(SystemClock.uptimeMillis()<end){
      AccessibilityNodeInfo id=findText(identity,false,false);
      if(id!=null){
        AccessibilityNodeInfo a=id;
        for(int up=0;up<5&&a!=null;up++,a=a.getParent()){
          ArrayDeque<AccessibilityNodeInfo> dq=new ArrayDeque<>();dq.add(a);
          while(!dq.isEmpty()){
            AccessibilityNodeInfo n=dq.removeFirst();
            String t=textOf(n).trim();
            if(t.equalsIgnoreCase(action)){
              AccessibilityNodeInfo c=clickableNode(n);
              if(c!=null&&c.performAction(AccessibilityNodeInfo.ACTION_CLICK)){SystemClock.sleep(350);return;}
            }
            for(int i=0;i<n.getChildCount();i++){AccessibilityNodeInfo ch=n.getChild(i);if(ch!=null)dq.addLast(ch);}
          }
        }
      }
      SystemClock.sleep(250);
    }
    throw new IllegalStateException("ACTION_NEAR_IDENTITY_NOT_FOUND:"+identity+":"+action);
  }

  private void setEmployee(String mnv){
    long end=SystemClock.uptimeMillis()+15000;
    AccessibilityNodeInfo n=null;
    while(SystemClock.uptimeMillis()<end && n==null){n=findEditable("MÃ NHÂN VIÊN");if(n==null)n=findEditable("SCAN");if(n==null)SystemClock.sleep(250);}
    if(n==null)throw new IllegalStateException("EMPLOYEE_INPUT_NOT_FOUND");
    Bundle b=new Bundle();b.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,mnv);
    if(!n.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT,b))throw new IllegalStateException("EMPLOYEE_SET_TEXT_FAILED");
    n.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
    try{ui.executeShellCommand("input keyevent 66").close();}catch(Exception e){throw new RuntimeException(e);}
    SystemClock.sleep(500);
  }

  private void mark(String key, boolean value){
    target.getSharedPreferences("pp_beta80_verify",Context.MODE_PRIVATE).edit().putBoolean(key,value).putLong(key+"_at",System.currentTimeMillis()).commit();
  }

  private void ok(String result){
    Bundle b=new Bundle();b.putString("result",result);finish(0,b);
  }

  private void ota(){
    seedAuth();
    String version=req("version"), url=new String(Base64.decode(req("url_b64"),Base64.NO_WRAP),java.nio.charset.StandardCharsets.UTF_8), sha=req("sha");
    target.getSharedPreferences("pp1291_pending_update_v1",Context.MODE_PRIVATE).edit()
      .putString("version",version).putString("url",url).putString("sha",sha).putString("notes","Beta80 OTA exact candidate")
      .putInt("version_code",86).commit();
    open("SETTINGS");
    clickText("TIẾP TỤC CẬP NHẬT",true,15000);
    mark("ota_prompt_entry_clicked",true);
    clickText("TẢI APK",false,30000);
    mark("ota_download_clicked",true);
    long end=SystemClock.uptimeMillis()+90000;
    AccessibilityNodeInfo install=null;
    while(SystemClock.uptimeMillis()<end){
      AccessibilityNodeInfo rr=root();
      String pkg=rr==null?"":String.valueOf(rr.getPackageName()).toLowerCase(Locale.ROOT);
      if(pkg.contains("packageinstaller")){
        for(String t:new String[]{"INSTALL","CÀI ĐẶT","UPDATE","CẬP NHẬT"}){
          AccessibilityNodeInfo n=findText(t,true,true);
          if(n!=null){install=n;break;}
        }
      }
      if(install!=null)break;
      SystemClock.sleep(300);
    }
    if(install==null)throw new IllegalStateException("ANDROID_INSTALL_BUTTON_NOT_FOUND");
    AccessibilityNodeInfo r=root();
    String installerPkg=r==null?"":String.valueOf(r.getPackageName()).toLowerCase(Locale.ROOT);
    if(!installerPkg.contains("packageinstaller"))throw new IllegalStateException("UNEXPECTED_INSTALLER_PACKAGE:"+installerPkg);
    mark("ota_installer_seen",true);
    Bundle st=new Bundle();st.putString("result","INSTALLER_SEEN");sendStatus(0,st);
    AccessibilityNodeInfo c=clickableNode(install);
    if(c==null||!c.performAction(AccessibilityNodeInfo.ACTION_CLICK))throw new IllegalStateException("ANDROID_INSTALL_CLICK_FAILED");
    mark("ota_installer_clicked",true);
    while(true)SystemClock.sleep(1000);
  }

  private void invokeBeta80Download(Activity a,String version,String url,String sha){
    try{
      Class<?> c=target.getClassLoader().loadClass("vn.pickpack1291.app.beta.UpdateManager");
      Field f=c.getField("INSTANCE");
      Object instance=f.get(null);
      Method picked=null;
      for(Method m:c.getDeclaredMethods()){
        if(m.getName().equals("download")&&m.getParameterTypes().length==4){picked=m;break;}
      }
      if(picked==null)throw new IllegalStateException("DOWNLOAD_METHOD_NOT_FOUND");
      final Method m=picked;m.setAccessible(true);
      final Object obj=instance;
      final String v=version,u=url,h=sha;
      runOnMainSync(new Runnable(){public void run(){
        try{m.invoke(obj,a,v,u,h);}catch(Exception e){throw new RuntimeException(e);}
      }});
    }catch(RuntimeException e){throw e;}catch(Exception e){throw new RuntimeException(e);}
  }

  private void fileprovider(){
    seedAuth();
    String version=req("version"), url=new String(Base64.decode(req("url_b64"),Base64.NO_WRAP),java.nio.charset.StandardCharsets.UTF_8), sha=req("sha");
    Activity a=open("SETTINGS");
    invokeBeta80Download(a,version,url,sha);
    mark("fileprovider_download_invoked",true);
    long end=SystemClock.uptimeMillis()+90000;
    AccessibilityNodeInfo install=null;
    while(SystemClock.uptimeMillis()<end){
      AccessibilityNodeInfo rr=root();
      String pkg=rr==null?"":String.valueOf(rr.getPackageName()).toLowerCase(Locale.ROOT);
      if(pkg.contains("packageinstaller")){
        for(String t:new String[]{"INSTALL","CÀI ĐẶT","UPDATE","CẬP NHẬT"}){
          AccessibilityNodeInfo n=findText(t,true,true);
          if(n!=null){install=n;break;}
        }
      }
      if(install!=null)break;
      SystemClock.sleep(300);
    }
    if(install==null)throw new IllegalStateException("FILEPROVIDER_INSTALL_BUTTON_NOT_FOUND");
    AccessibilityNodeInfo r=root();
    String installerPkg=r==null?"":String.valueOf(r.getPackageName()).toLowerCase(Locale.ROOT);
    if(!installerPkg.contains("packageinstaller"))throw new IllegalStateException("UNEXPECTED_FILEPROVIDER_INSTALLER_PACKAGE:"+installerPkg);
    mark("fileprovider_installer_seen",true);
    Bundle st=new Bundle();st.putString("result","FILEPROVIDER_INSTALLER_SEEN");sendStatus(0,st);
    AccessibilityNodeInfo c=clickableNode(install);
    if(c==null||!c.performAction(AccessibilityNodeInfo.ACTION_CLICK))throw new IllegalStateException("FILEPROVIDER_INSTALL_CLICK_FAILED");
    mark("fileprovider_installer_clicked",true);
    while(true)SystemClock.sleep(1000);
  }

  private void enter(){
    String mnv=req("mnv");
    IllegalStateException last=null;
    for(int attempt=0;attempt<3;attempt++){
      seedAuth();seedService();open("BUSINESS");
      clickText("Quét QR nhân sự",true,15000);
      seedService();
      setEmployee(mnv);
      seedService();
      try{
        clickTextScrolling("VÀO CA",true,20000);
        mark("enter_ui_clicked",true);
        SystemClock.sleep(5000);
        ok("ENTER_UI_CLICKED");
        return;
      }catch(IllegalStateException e){
        if(e.getMessage()==null||!e.getMessage().startsWith("TEXT_NOT_FOUND_AFTER_SCROLL:VÀO CA"))throw e;
        last=e;
        SystemClock.sleep(1500);
      }
    }
    throw last==null?new IllegalStateException("ENTER_UI_RETRY_EXHAUSTED"):last;
  }

  private void historical(){
    seedAuth();seedService();open("BUSINESS");
    String mnv=req("mnv");
    clickText("CẢNH BÁO:  CHƯA KẾT THÚC PHIÊN CÁC NGÀY CŨ.",false,20000);
    clickActionNear(mnv,"MỞ ĐÚNG PHIÊN",20000);
    waitText("QUÉT QR NHÂN SỰ",false,false,20000);
    waitText(mnv,false,false,10000);
    seedService();
    waitText("Sửa",true,true,10000);
    waitText("Ra ca",true,true,10000);
    mark("historical_shared_ui",true);

    clickText("Sửa",true,10000);
    seedService();
    clickText("Chọn nội dung cần sửa",true,10000);
    clickText("Ca",true,10000);
    SystemClock.sleep(500);
    clickText("Ca 1",true,10000);
    clickText("Ca 2",true,10000);
    seedService();
    clickText("LƯU",true,10000);
    mark("historical_edit_clicked",true);
    SystemClock.sleep(5000);

    seedService();
    clickText("Ra ca",true,15000);
    mark("historical_exit_clicked",true);
    SystemClock.sleep(5000);
    ok("HISTORICAL_EDIT_EXIT_CLICKED");
  }
}
