package vn.pickpack1291.app.beta

import android.app.Activity
import android.app.AlertDialog
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.view.animation.AlphaAnimation
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONArray
import org.json.JSONObject

object OldSessionWarningFeature {
    const val WARNING_TEXT = "CẢNH BÁO: CÓ PHIÊN CŨ CHƯA BẮN RA"
    private data class Item(val sessionId:String,val mnv:String,val name:String,val date:String,val shift:String,val pda:String,val enterAt:String)

    fun build(activity:Activity,api:BetaApiClient,onOpen:(JSONObject)->Unit):View{
        val d=activity.resources.displayMetrics.density
        fun dp(v:Int)=(v*d).toInt()
        fun round(color:Int,r:Int)=GradientDrawable().apply{setColor(color);cornerRadius=dp(r).toFloat()}
        fun txt(v:String,size:Float,color:Int,bold:Boolean=false)=TextView(activity).apply{text=v;textSize=size;setTextColor(color);typeface=if(bold)Typeface.DEFAULT_BOLD else Typeface.DEFAULT}
        fun dash(v:Any?):String=(v?.toString().orEmpty()).trim().ifBlank{"—"}
        val root=LinearLayout(activity).apply{orientation=LinearLayout.VERTICAL;visibility=View.GONE;setPadding(0,0,0,dp(6))}
        val button=Button(activity).apply{
            text=WARNING_TEXT
            textSize=10.5f;setTextColor(Color.rgb(176,0,32));typeface=Typeface.DEFAULT_BOLD;isAllCaps=false;gravity=Gravity.CENTER
            background=GradientDrawable().apply{setColor(Color.rgb(255,226,232));cornerRadius=dp(10).toFloat();setStroke(dp(2),Color.rgb(176,0,32))};minHeight=dp(42);setPadding(dp(8),0,dp(8),0)
        }
        root.addView(button,LinearLayout.LayoutParams(-1,-2))
        var items=listOf<Item>()
        fun parse(arr:JSONArray):List<Item>{
            val out=mutableListOf<Item>()
            for(i in 0 until arr.length()){
                val x=arr.optJSONObject(i)?:continue
                val sessionId=x.optString("session_id").trim();val mnv=x.optString("mnv").trim();val date=x.optString("business_date").trim()
                if(sessionId.isBlank()||mnv.isBlank()||date.isBlank())continue
                out+=Item(sessionId,mnv,x.optString("full_name").trim(),date,x.optString("shift").trim(),x.optString("pda_serial").trim(),x.optString("enter_at").trim())
            }
            return out.distinctBy{it.sessionId}
        }
        fun local():List<Item>{
            val store=OperationalDataStore(activity);val today=store.businessDate();val out=mutableListOf<Item>()
            for(date in store.availableDates().filter{it<today}){
                val sessions=store.loadDay(date)?.optJSONArray("sessions")?:continue
                for(i in 0 until sessions.length()){
                    val s=sessions.optJSONObject(i)?:continue
                    if(!s.optString("state").equals("ACTIVE",true))continue
                    val sessionId=s.optString("session_id").trim();val mnv=s.optString("mnv").trim()
                    if(sessionId.isBlank()||mnv.isBlank())continue
                    val e=MasterDataCache.employee(activity,mnv)
                    out+=Item(sessionId,mnv,e?.optString("full_name").orEmpty(),date,s.optString("shift"),s.optString("pda_serial"),s.optString("enter_at"))
                }
            }
            return out.distinctBy{it.sessionId}
        }
        fun apply(next:List<Item>){
            items=next;root.visibility=if(items.isEmpty())View.GONE else View.VISIBLE
            if(items.isNotEmpty()&&button.animation==null)button.startAnimation(AlphaAnimation(1f,.55f).apply{duration=760;repeatMode=android.view.animation.Animation.REVERSE;repeatCount=android.view.animation.Animation.INFINITE})
        }
        fun showDetail(item:Item){
            TopNotice.show(activity,"Đang mở đúng phiên ${item.date}…",TopNotice.Kind.INFO)
            val payload=JSONObject().put("session_id",item.sessionId).put("business_date",item.date).put("mnv",item.mnv)
            api.call("historical_session_detail",payload){r->activity.runOnUiThread{
                if(!r.ok){
                    val msg=when(r.error){
                        "HISTORICAL_SESSION_OUTSIDE_RETENTION"->"Phiên ${item.date} đã ngoài phạm vi lưu giữ 45 ngày nên không còn chi tiết để mở."
                        "HISTORICAL_SESSION_NOT_FOUND"->"Không tìm thấy dữ liệu của đúng phiên ${item.sessionId}."
                        else->"Không mở được đúng phiên ${item.date}: ${r.error?:"SERVICE_ERROR"}."
                    }
                    AlertDialog.Builder(activity).setTitle("Không mở được phiên cũ").setMessage(msg).setPositiveButton("Đóng",null).show();return@runOnUiThread
                }
                val j=r.json?:JSONObject()
                val identity=j.optJSONObject("identity")?:JSONObject()
                val session=j.optJSONObject("session")?:JSONObject()
                val exactSessionId=identity.optString("session_id").ifBlank{session.optString("session_id")}.trim()
                val exactMnv=identity.optString("mnv").ifBlank{session.optString("mnv")}.trim()
                val exactDate=identity.optString("business_date").ifBlank{session.optString("business_date")}.trim()
                if(exactSessionId!=item.sessionId||exactMnv!=item.mnv||exactDate!=item.date){
                    AlertDialog.Builder(activity).setTitle("Không mở được phiên cũ").setMessage("Dữ liệu trả về không khớp đúng phiên đã chọn.").setPositiveButton("Đóng",null).show()
                    return@runOnUiThread
                }
                onOpen(j)
            }}
        }
        fun showList(){
            if(items.isEmpty())return
            val list=LinearLayout(activity).apply{orientation=LinearLayout.VERTICAL;setPadding(dp(10),dp(8),dp(10),dp(8))}
            var dialog:AlertDialog?=null
            items.forEach{item->
                val open={dialog?.dismiss();showDetail(item)}
                val card=LinearLayout(activity).apply{orientation=LinearLayout.VERTICAL;setPadding(dp(10),dp(8),dp(10),dp(8));background=GradientDrawable().apply{setColor(Color.WHITE);cornerRadius=dp(10).toFloat();setStroke(dp(1),Color.rgb(220,226,230))};setOnClickListener{open()}}
                card.addView(txt("${item.mnv} • ${item.name.ifBlank{"-"}}",11.5f,Color.rgb(24,44,42),true))
                card.addView(txt("Ngày ${item.date.ifBlank{"-"}} • ${item.shift.ifBlank{"-"}} • PDA ${item.pda.ifBlank{"-"}}",9.5f,Color.rgb(100,116,139),false))
                card.addView(txt("Phiên ${item.sessionId}",8.7f,Color.rgb(100,116,139),false))
                card.addView(Button(activity).apply{text="MỞ ĐÚNG PHIÊN";textSize=9.5f;setTextColor(Color.WHITE);typeface=Typeface.DEFAULT_BOLD;isAllCaps=false;background=round(Color.rgb(139,0,0),8);setOnClickListener{open()}},LinearLayout.LayoutParams(-1,dp(38)).apply{topMargin=dp(5)})
                list.addView(card,LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(6)})
            }
            dialog=AlertDialog.Builder(activity).setTitle("Phiên cũ chưa bắn ra (${items.size})").setView(ScrollView(activity).apply{addView(list)}).setNegativeButton("Đóng",null).create();dialog?.show()
        }
        button.setOnClickListener{showList()}
        apply(local())
        api.call("old_active_sessions"){r->activity.runOnUiThread{if(r.ok)apply(parse(r.json?.optJSONArray("items")?:JSONArray()))}}
        return root
    }
}
