package vn.pickpack1291.app.beta

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
            text="CẢNH BÁO:  CHƯA KẾT THÚC PHIÊN CÁC NGÀY CŨ."
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
