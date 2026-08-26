#!/usr/bin/env python3
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"{path}: anchor count {count}, expected 1\nANCHOR:\n{old[:500]}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")


def ensure_contains(path: str, needle: str) -> None:
    if needle not in Path(path).read_text(encoding="utf-8"):
        raise SystemExit(f"{path}: missing required marker: {needle}")


# Beta metadata only; Stable is invariant.
replace_once(
    "app/build.gradle.kts",
    '            versionCode = 82\n            versionName = "0.4.2-beta.76"',
    '            versionCode = 83\n            versionName = "0.4.2-beta.77"',
)
replace_once(
    "app/build.gradle.kts",
    '// Beta76: direct GAS/Sheets Nhận hàng rớt workflow; Stable remains isolated and unchanged.',
    '// Beta77: owner fixes for Nhận hàng rớt latency/CRUD, cross-day active PDA visibility, old-session warning, and employee render stability. Stable remains isolated and unchanged.\n// Beta76: direct GAS/Sheets Nhận hàng rớt workflow; Stable remains isolated and unchanged.',
)

# Direct Service read for old ACTIVE sessions.
replace_once(
    "app/src/main/java/vn/pickpack1291/app/beta/M2RuntimeBridge.kt",
    '        val DIRECT_READS = setOf("employee_context", "master_options", "history_shared")',
    '        val DIRECT_READS = setOf("employee_context", "master_options", "history_shared", "old_active_sessions")',
)

# Service read-model must honor leases globally, not just the current business date.
replace_once(
    "service/src/mobile_hotfix.ts",
    '  const leaseRows=(await db.prepare("SELECT resource_type,resource_id,mnv FROM resource_leases WHERE business_date=?1").bind(date).all<{resource_type:string;resource_id:string;mnv:string}>()).results??[];',
    '  const leaseRows=(await db.prepare("SELECT resource_type,resource_id,mnv FROM resource_leases").all<{resource_type:string;resource_id:string;mnv:string}>()).results??[];',
)
replace_once(
    "service/src/mobile_hotfix.ts",
    '  const current=await db.prepare("SELECT pda_serial,user_pick,pack_table,user_pack FROM attendance_sessions WHERE business_date=?1 AND mnv=?2 AND state=\'ACTIVE\'").bind(date,mnv).first<{pda_serial:string|null;user_pick:string|null;pack_table:string|null;user_pack:string|null}>();',
    '  const current=await db.prepare("SELECT pda_serial,user_pick,pack_table,user_pack FROM attendance_sessions WHERE mnv=?1 AND state=\'ACTIVE\' ORDER BY business_date DESC,enter_at DESC LIMIT 1").bind(mnv).first<{pda_serial:string|null;user_pick:string|null;pack_table:string|null;user_pack:string|null}>();',
)
replace_once(
    "service/src/mobile_hotfix.ts",
    '  const session=await env.DB.prepare("SELECT session_id,mnv,business_date,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,pda_enter_status,pda_exit_status,resource_note,enter_at,exit_at,entered_by,exited_by,version FROM attendance_sessions WHERE business_date=?1 AND mnv=?2").bind(date,mnv).first<Record<string,unknown>>();\n  const state=!session?"NOT_ENTERED":String(session.state)==="ACTIVE"?"ACTIVE":"ENDED";',
    '  const currentSession=await env.DB.prepare("SELECT session_id,mnv,business_date,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,pda_enter_status,pda_exit_status,resource_note,enter_at,exit_at,entered_by,exited_by,version FROM attendance_sessions WHERE business_date=?1 AND mnv=?2").bind(date,mnv).first<Record<string,unknown>>();\n  const activeSession=await env.DB.prepare("SELECT session_id,mnv,business_date,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,pda_enter_status,pda_exit_status,resource_note,enter_at,exit_at,entered_by,exited_by,version FROM attendance_sessions WHERE mnv=?1 AND state=\'ACTIVE\' ORDER BY business_date DESC,enter_at DESC LIMIT 1").bind(mnv).first<Record<string,unknown>>();\n  const session=activeSession??currentSession;\n  const state=!session?"NOT_ENTERED":String(session.state)==="ACTIVE"?"ACTIVE":"ENDED";',
)
replace_once(
    "service/src/mobile_hotfix.ts",
    'function eventLabel(type:string):string{return type==="ATTENDANCE_ENTER"?"Vào ca":type==="ATTENDANCE_EXIT"?"Ra ca":type==="RESOURCE_CHANGE"?"Đổi tài nguyên":type==="LABOR_START"?"Bắt đầu công nhật":type==="LABOR_FINISH"?"Hoàn thành công nhật":type;} ',
    '''async function oldActiveSessions(env:Env):Promise<Response>{
  const date=await businessDate(env.DB);
  const items=(await env.DB.prepare("SELECT s.session_id,s.mnv,s.business_date,s.shift,s.work_choice,s.state,s.pda_serial,s.user_pick,s.pack_table,s.user_pack,s.enter_at,s.version,COALESCE(e.full_name,'') full_name FROM attendance_sessions s LEFT JOIN employees e ON e.mnv=s.mnv WHERE s.state='ACTIVE' AND s.business_date<?1 ORDER BY s.business_date ASC,s.enter_at ASC,s.mnv ASC").bind(date).all<Record<string,unknown>>()).results??[];
  return json({ok:true,source:"SERVICE_D1",business_date:date,count:items.length,items});
}

function eventLabel(type:string):string{return type==="ATTENDANCE_ENTER"?"Vào ca":type==="ATTENDANCE_EXIT"?"Ra ca":type==="RESOURCE_CHANGE"?"Đổi tài nguyên":type==="LABOR_START"?"Bắt đầu công nhật":type==="LABOR_FINISH"?"Hoàn thành công nhật":type;} ''',
)
replace_once(
    "service/src/mobile_hotfix.ts",
    '  if(action==="history_shared")return sharedHistory(env,body);\n  if(action==="runtime_status")return json({ok:true,source:"SERVICE_D1",authority:await currentAuthority(env.DB),service_generation:env.SERVICE_GENERATION});',
    '  if(action==="history_shared")return sharedHistory(env,body);\n  if(action==="old_active_sessions")return oldActiveSessions(env);\n  if(action==="runtime_status")return json({ok:true,source:"SERVICE_D1",authority:await currentAuthority(env.DB),service_generation:env.SERVICE_GENERATION});',
)

# Nhận hàng rớt: authority comes from server response; location selection has no fake placeholder.
replace_once(
    "app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt",
    'object DropReceiveFeature {\n    private const val OWNER_LOGIN="tamnv2"\n',
    'object DropReceiveFeature {\n',
)
replace_once(
    "app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt",
    '        val owner=login==OWNER_LOGIN\n        val actualSuper=actualRole.uppercase()=="SUPERADMIN"\n        val locationSpinner=Spinner(activity).apply{minimumHeight=dp(46);setPadding(dp(8),dp(3),dp(8),dp(3));background=bg()}\n        val createBtn=button("Tạo",teal);val editBtn=button("Sửa",navy);val deleteBtn=button("Xóa",red)\n        listOf(createBtn,editBtn,deleteBtn).forEach{it.isEnabled=owner;it.alpha=if(owner)1f else .35f}',
    '        val actualSuper=actualRole.uppercase()=="SUPERADMIN"\n        val locationSpinner=Spinner(activity).apply{minimumHeight=dp(46);setPadding(dp(8),dp(3),dp(8),dp(3));background=bg()}\n        val createBtn=button("Tạo",teal);val editBtn=button("Sửa",navy);val deleteBtn=button("Xóa",red)\n        var canManageLocations=false\n        fun applyLocationPermission(allowed:Boolean){canManageLocations=allowed;listOf(createBtn,editBtn,deleteBtn).forEach{it.isEnabled=allowed;it.alpha=if(allowed)1f else .35f}}\n        applyLocationPermission(false)',
)
replace_once(
    "app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt",
    '        body.addView(locationRow,LinearLayout.LayoutParams(-1,-2));if(!owner){body.addView(gap(3));body.addView(text("Danh sách vị trí chỉ OWNER được Tạo / Sửa / Xóa.",9f,muted,false))}',
    '        body.addView(locationRow,LinearLayout.LayoutParams(-1,-2))',
)
replace_once(
    "app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt",
    '''        var locationItems=listOf<String>()
        var pendingRecordId:String?=null
        fun selectedLocation():String=locationItems.getOrNull(locationSpinner.selectedItemPosition-1).orEmpty()
        fun setLocations(items:List<String>,preferred:String=""){
            val clean=items.map{it.trim()}.filter{it.isNotBlank()}.distinct()
            locationItems=clean
            locationSpinner.adapter=ArrayAdapter(activity,android.R.layout.simple_spinner_dropdown_item,(listOf("Chọn vị trí")+clean))
            val index=clean.indexOf(preferred);if(index>=0)locationSpinner.setSelection(index+1)
        }''',
    '''        val locationCache=activity.getSharedPreferences("drop_receive_location_cache",android.content.Context.MODE_PRIVATE)
        var locationItems=listOf<String>()
        var pendingRecordId:String?=null
        fun selectedLocation():String=if(locationItems.isEmpty())"" else locationItems.getOrNull(locationSpinner.selectedItemPosition).orEmpty()
        fun setLocations(items:List<String>,preferred:String=""){
            val clean=items.map{it.trim()}.filter{it.isNotBlank()}.distinct()
            locationItems=clean
            val shown=if(clean.isEmpty())listOf("Chưa có vị trí") else clean
            locationSpinner.adapter=ArrayAdapter(activity,android.R.layout.simple_spinner_dropdown_item,shown)
            val index=clean.indexOf(preferred);locationSpinner.setSelection(if(index>=0)index else 0)
        }
        fun cacheLocations(items:List<String>){locationCache.edit().putString("items",JSONArray(items).toString()).apply()}
        fun cachedLocations():List<String>{val raw=locationCache.getString("items","").orEmpty();if(raw.isBlank())return emptyList();return runCatching{val arr=JSONArray(raw);val out=mutableListOf<String>();for(i in 0 until arr.length()){val v=arr.optString(i).trim();if(v.isNotBlank())out.add(v)};out}.getOrDefault(emptyList())}''',
)
replace_once(
    "app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt",
    '''        fun reloadLocations(preferred:String=""){
            api.call("outbound_location_list"){r->activity.runOnUiThread{
                if(!r.ok){error(r.error?:"Không tải được danh sách vị trí từ Google Sheet.");return@runOnUiThread}
                setLocations(readItems(r.json),preferred)
            }}
        }''',
    '''        fun reloadLocations(preferred:String=""){
            api.call("outbound_location_list"){r->activity.runOnUiThread{
                if(!r.ok){error(r.error?:"Không tải được danh sách vị trí từ Google Sheet.");return@runOnUiThread}
                val items=readItems(r.json);applyLocationPermission(r.json?.optBoolean("owner",false)==true);setLocations(items,preferred);cacheLocations(items)
            }}
        }''',
)
replace_once(
    "app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt",
    '                val preferred=if(op=="DELETE")"" else after\n                setLocations(readItems(r.json),preferred);success("Đã cập nhật danh sách vị trí.")',
    '                val preferred=if(op=="DELETE")"" else after\n                val items=readItems(r.json);applyLocationPermission(r.json?.optBoolean("owner",canManageLocations)==true);setLocations(items,preferred);cacheLocations(items);success("Đã cập nhật danh sách vị trí.")',
)
replace_once(
    "app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt",
    '''        createBtn.setOnClickListener{if(!owner)return@setOnClickListener;locationDialog("Tạo vị trí"){v->mutateLocation("CREATE","",v)}}
        editBtn.setOnClickListener{if(!owner)return@setOnClickListener;val before=selectedLocation();if(before.isBlank()){warning("Chọn vị trí cần sửa.");return@setOnClickListener};locationDialog("Sửa vị trí",before){v->mutateLocation("UPDATE",before,v)}}
        deleteBtn.setOnClickListener{if(!owner)return@setOnClickListener;val before=selectedLocation();if(before.isBlank()){warning("Chọn vị trí cần xóa.");return@setOnClickListener};AlertDialog.Builder(activity).setTitle("Xóa vị trí?").setMessage("Xóa “$before” khỏi danh sách chọn?").setNegativeButton("Hủy",null).setPositiveButton("XÓA"){_,_->mutateLocation("DELETE",before,"")}.show()}''',
    '''        createBtn.setOnClickListener{if(!canManageLocations)return@setOnClickListener;locationDialog("Tạo vị trí"){v->mutateLocation("CREATE","",v)}}
        editBtn.setOnClickListener{if(!canManageLocations)return@setOnClickListener;val before=selectedLocation();if(before.isBlank()){warning("Chưa có vị trí để sửa.");return@setOnClickListener};locationDialog("Sửa vị trí",before){v->mutateLocation("UPDATE",before,v)}}
        deleteBtn.setOnClickListener{if(!canManageLocations)return@setOnClickListener;val before=selectedLocation();if(before.isBlank()){warning("Chưa có vị trí để xóa.");return@setOnClickListener};AlertDialog.Builder(activity).setTitle("Xóa vị trí?").setMessage("Xóa “$before” khỏi danh sách chọn?").setNegativeButton("Hủy",null).setPositiveButton("XÓA"){_,_->mutateLocation("DELETE",before,"")}.show()}''',
)
replace_once(
    "app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt",
    '        setLocations(emptyList());reloadLocations()\n        return root',
    '        setLocations(cachedLocations());reloadLocations(selectedLocation())\n        return root',
)

# GAS: cache the tiny location master, avoid repeated spreadsheet scans/forced flush/readback scans.
replace_once(
    "google-apps-script/OUTBOUND_DROP_RECEIVE.gs",
    "function ppOutboundKey_(value){ return ppFold_(ppOutboundNorm_(value)); }\nfunction ppOutboundLocations_(){\n  const sh=ppOutboundSheet_(PP_OUTBOUND.LOCATION_SHEET), last=sh.getLastRow();\n  if(last<2) return [];\n  return sh.getRange(2,1,last-1,1).getDisplayValues().map(function(r){return ppOutboundNorm_(r[0]);}).filter(function(v){return !!v;});\n}",
    "function ppOutboundKey_(value){ return ppFold_(ppOutboundNorm_(value)); }\nfunction ppOutboundLocationCache_(){ return CacheService.getScriptCache(); }\nfunction ppOutboundLocationsFromSheet_(sh){\n  const last=sh.getLastRow(); if(last<2) return [];\n  return sh.getRange(2,1,last-1,1).getDisplayValues().map(function(r){return ppOutboundNorm_(r[0]);}).filter(function(v){return !!v;});\n}\nfunction ppOutboundCacheLocations_(items){ try{ ppOutboundLocationCache_().put('PP_OUTBOUND_LOCATIONS_V1',JSON.stringify(items),300); }catch(_){} return items; }\nfunction ppOutboundLocations_(){\n  try{ const cached=ppOutboundLocationCache_().get('PP_OUTBOUND_LOCATIONS_V1'); if(cached){ const items=JSON.parse(cached); if(Array.isArray(items)) return items.map(ppOutboundNorm_).filter(Boolean); } }catch(_){}\n  return ppOutboundCacheLocations_(ppOutboundLocationsFromSheet_(ppOutboundSheet_(PP_OUTBOUND.LOCATION_SHEET)));\n}",
)
replace_once(
    "google-apps-script/OUTBOUND_DROP_RECEIVE.gs",
    '  const sh=ppOutboundSheet_(PP_OUTBOUND.LOCATION_SHEET), values=ppOutboundLocations_(), keys=values.map(ppOutboundKey_);',
    '  const sh=ppOutboundSheet_(PP_OUTBOUND.LOCATION_SHEET), values=ppOutboundLocationsFromSheet_(sh), keys=values.map(ppOutboundKey_);',
)
replace_once(
    "google-apps-script/OUTBOUND_DROP_RECEIVE.gs",
    '''  SpreadsheetApp.flush();
  const readback=ppOutboundLocations_();
  const expected=op==='DELETE' ? readback.map(ppOutboundKey_).indexOf(ppOutboundKey_(before))<0 : readback.map(ppOutboundKey_).indexOf(ppOutboundKey_(after))>=0;
  if(!expected) return {ok:false,error:'OUTBOUND_LOCATION_READBACK_FAILED'};''',
    '''  const readback=ppOutboundLocationsFromSheet_(sh);
  const expected=op==='DELETE' ? readback.map(ppOutboundKey_).indexOf(ppOutboundKey_(before))<0 : readback.map(ppOutboundKey_).indexOf(ppOutboundKey_(after))>=0;
  if(!expected) return {ok:false,error:'OUTBOUND_LOCATION_READBACK_FAILED'};
  ppOutboundCacheLocations_(readback);''',
)
replace_once(
    "google-apps-script/OUTBOUND_DROP_RECEIVE.gs",
    '''  const row=[location,day,rawQr,orderNo,count,actor,at,id];
  sh.appendRow(row); SpreadsheetApp.flush();
  const readback=ppOutboundFindRecord_(sh,id);
  if(!readback) return {ok:false,error:'OUTBOUND_APPEND_READBACK_FAILED'};
  const got=readback.values;
  if(String(got[0])!==location || String(got[2])!==rawQr || String(got[3])!==orderNo || String(got[4])!==String(count) || String(got[7])!==id) return {ok:false,error:'OUTBOUND_APPEND_READBACK_MISMATCH'};
  ppHistorySafeAppendS13_({event_type:'OUTBOUND_DROP_APPEND',label:'Nhận hàng rớt • Thêm thông tin',actor:auth.login_id,detail:'Vị trí '+location+' • DO '+orderNo+' • Số kiện '+count,event_id:id,scope:'OUTBOUND'});
  return {ok:true,idempotent:false,row:readback.row,item:got};''',
    '''  const row=[location,day,rawQr,orderNo,count,actor,at,id];
  sh.appendRow(row);
  const rowNo=sh.getLastRow(), got=sh.getRange(rowNo,1,1,8).getDisplayValues()[0];
  if(String(got[0])!==location || String(got[2])!==rawQr || String(got[3])!==orderNo || String(got[4])!==String(count) || String(got[7])!==id) return {ok:false,error:'OUTBOUND_APPEND_READBACK_MISMATCH'};
  ppHistorySafeAppendS13_({event_type:'OUTBOUND_DROP_APPEND',label:'Nhận hàng rớt • Thêm thông tin',actor:auth.login_id,detail:'Vị trí '+location+' • DO '+orderNo+' • Số kiện '+count,event_id:id,scope:'OUTBOUND'});
  return {ok:true,idempotent:false,row:rowNo,item:got};''',
)

# OperationsActivity: warning goes above reconciliation; semantic render signature ignores changing option arrays.
replace_once(
    "app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt",
    '        val root=baseRoot("NGHIỆP VỤ");val body=body().apply{setPadding(dp(8),dp(6),dp(8),dp(76))}\n        addBusinessShiftReconciliation(body)',
    '        val root=baseRoot("NGHIỆP VỤ");val body=body().apply{setPadding(dp(8),dp(6),dp(8),dp(76))}\n        body.addView(OldSessionWarningFeature.build(this,api){mnv->loadEmployee(mnv)},matchWrap())\n        addBusinessShiftReconciliation(body)',
)
replace_once(
    "app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt",
    '        if(state=="NOT_ENTERED"&&masters!=null)parts.add(masters.toString())\n',
    '',
)
replace_once(
    "app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt",
    '    private fun dash(v:String)=v.takeIf{it.isNotBlank()&&it!="null"}?:"—"',
    '    private fun dash(v:String)=v.trim().takeIf{it.isNotBlank()&&!it.equals("null",true)}?:"-"',
)

# New isolated warning component; no navigation/state authority changes.
warning = r'''package vn.pickpack1291.app.beta

import android.app.Activity
import android.app.AlertDialog
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.animation.AlphaAnimation
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONArray
import org.json.JSONObject

object OldSessionWarningFeature {
    private data class Item(val mnv:String,val name:String,val date:String,val shift:String,val pda:String,val enterAt:String)

    fun build(activity:Activity,api:BetaApiClient,onOpen:(String)->Unit):View{
        val d=activity.resources.displayMetrics.density
        fun dp(v:Int)=(v*d).toInt()
        fun round(color:Int,r:Int)=GradientDrawable().apply{setColor(color);cornerRadius=dp(r).toFloat()}
        fun txt(v:String,size:Float,color:Int,bold:Boolean=false)=TextView(activity).apply{text=v;textSize=size;setTextColor(color);typeface=if(bold)Typeface.DEFAULT_BOLD else Typeface.DEFAULT}
        val root=LinearLayout(activity).apply{orientation=LinearLayout.VERTICAL;visibility=View.GONE;setPadding(0,0,0,dp(6))}
        val button=Button(activity).apply{
            text="CẢNH BÁO: CHƯA KẾT THÚC PHIÊN CÁC NGÀY CŨ."
            textSize=10.2f;setTextColor(Color.WHITE);typeface=Typeface.DEFAULT_BOLD;isAllCaps=false;gravity=Gravity.CENTER
            background=round(Color.rgb(139,0,0),11);minHeight=dp(46);setPadding(dp(8),dp(5),dp(8),dp(5))
        }
        root.addView(button,LinearLayout.LayoutParams(-1,-2))
        var items=listOf<Item>()
        fun parse(arr:JSONArray):List<Item>{val out=mutableListOf<Item>();for(i in 0 until arr.length()){val x=arr.optJSONObject(i)?:continue;val mnv=x.optString("mnv").trim();if(mnv.isBlank())continue;out+=Item(mnv,x.optString("full_name").trim(),x.optString("business_date").trim(),x.optString("shift").trim(),x.optString("pda_serial").trim(),x.optString("enter_at").trim())};return out}
        fun local():List<Item>{
            val store=OperationalDataStore(activity);val today=store.businessDate();val out=mutableListOf<Item>()
            for(date in store.availableDates().filter{it<today}){val sessions=store.loadDay(date)?.optJSONArray("sessions")?:continue;for(i in 0 until sessions.length()){val s=sessions.optJSONObject(i)?:continue;if(!s.optString("state").equals("ACTIVE",true))continue;val mnv=s.optString("mnv").trim();if(mnv.isBlank())continue;val e=MasterDataCache.employee(activity,mnv);out+=Item(mnv,e?.optString("full_name").orEmpty(),date,s.optString("shift"),s.optString("pda_serial"),s.optString("enter_at"))}}
            return out.distinctBy{it.mnv+"|"+it.date}
        }
        fun apply(next:List<Item>){items=next;root.visibility=if(items.isEmpty())View.GONE else View.VISIBLE;if(items.isNotEmpty()&&button.animation==null)button.startAnimation(AlphaAnimation(1f,.55f).apply{duration=760;repeatMode=android.view.animation.Animation.REVERSE;repeatCount=android.view.animation.Animation.INFINITE})}
        fun showList(){
            if(items.isEmpty())return
            val list=LinearLayout(activity).apply{orientation=LinearLayout.VERTICAL;setPadding(dp(10),dp(8),dp(10),dp(8))}
            var dialog:AlertDialog?=null
            items.forEach{item->
                val card=LinearLayout(activity).apply{orientation=LinearLayout.VERTICAL;setPadding(dp(10),dp(8),dp(10),dp(8));background=GradientDrawable().apply{setColor(Color.WHITE);cornerRadius=dp(10).toFloat();setStroke(dp(1),Color.rgb(220,226,230))};setOnClickListener{dialog?.dismiss();onOpen(item.mnv)}}
                card.addView(txt("${item.mnv} • ${item.name.ifBlank{"-"}}",11.5f,Color.rgb(24,44,42),true))
                card.addView(txt("Ngày ${item.date.ifBlank{"-"}} • ${item.shift.ifBlank{"-"}} • PDA ${item.pda.ifBlank{"-"}}",9.5f,Color.rgb(100,116,139),false))
                card.addView(Button(activity).apply{text="MỞ PHIÊN";textSize=9.5f;setTextColor(Color.WHITE);typeface=Typeface.DEFAULT_BOLD;isAllCaps=false;background=round(Color.rgb(139,0,0),8);setOnClickListener{dialog?.dismiss();onOpen(item.mnv)}},LinearLayout.LayoutParams(-1,dp(38)).apply{topMargin=dp(5)})
                list.addView(card,LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(6)})
            }
            dialog=AlertDialog.Builder(activity).setTitle("Phiên ngày cũ chưa kết thúc (${items.size})").setView(ScrollView(activity).apply{addView(list)}).setNegativeButton("Đóng",null).create();dialog?.show()
        }
        button.setOnClickListener{showList()}
        apply(local())
        api.call("old_active_sessions"){r->activity.runOnUiThread{if(r.ok){apply(parse(r.json?.optJSONArray("items")?:JSONArray()))}}}
        return root
    }
}
'''
wp=Path("app/src/main/java/vn/pickpack1291/app/beta/OldSessionWarningFeature.kt")
if wp.exists() and wp.read_text(encoding="utf-8") != warning:
    raise SystemExit("OldSessionWarningFeature.kt already exists with unexpected content")
wp.write_text(warning, encoding="utf-8")

# Safety assertions.
ensure_contains("app/build.gradle.kts", 'versionCode = 83')
ensure_contains("app/build.gradle.kts", 'versionName = "0.4.2-beta.77"')
ensure_contains("app/build.gradle.kts", 'versionCode = 1')
ensure_contains("app/build.gradle.kts", 'versionName = "0.1.0-stable"')
ensure_contains("service/src/mobile_hotfix.ts", "SELECT resource_type,resource_id,mnv FROM resource_leases")
ensure_contains("service/src/mobile_hotfix.ts", 'action==="old_active_sessions"')
ensure_contains("app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt", 'listOf("Chưa có vị trí")')
ensure_contains("app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt", 'OldSessionWarningFeature.build')
print("BETA77_OWNER_FIXES_MATERIALIZED")
