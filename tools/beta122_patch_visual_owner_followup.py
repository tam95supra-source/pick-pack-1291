#!/usr/bin/env python3
from pathlib import Path

p=Path('tools/Beta83UiChecksInstrumentation.java')
s=p.read_text(encoding='utf-8')
marker='BETA122_OWNER_FOLLOWUP_RUNTIME_PASS'
if marker in s:
    print('BETA122_VISUAL_OWNER_FOLLOWUP_ALREADY_PATCHED')
    raise SystemExit(0)

anchor='''  private void runVisual()throws Exception{\n    String tag=req("tag"),mnv=req("mnv"),mnv2=req("mnv2"),mnv3=req("mnv3");\n    verifyFirstLogMetadata();\n    verifyDocumentLocalDurability();\n    seedAuth();seedService();seedData(mnv,mnv2,mnv3);'''
if anchor not in s:
    raise SystemExit('runVisual anchor missing')

helper=r'''
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

'''
s=s.replace('  private void runVisual()throws Exception{',helper+'  private void runVisual()throws Exception{',1)
s=s.replace(anchor,anchor+'\n    verifyBeta122OwnerFollowupRuntime();',1)
p.write_text(s,encoding='utf-8')
print('BETA122_VISUAL_OWNER_FOLLOWUP_PATCH_APPLIED')
