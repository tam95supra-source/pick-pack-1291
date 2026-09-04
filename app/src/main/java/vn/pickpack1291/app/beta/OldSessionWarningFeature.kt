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
import java.util.UUID

object OldSessionWarningFeature {
    const val WARNING_TEXT = "CẢNH BÁO: CÓ PHIÊN CŨ CHƯA BẮN RA"
    @Volatile private var activeRefresh:(()->Unit)?=null
    fun onRealtime(){activeRefresh?.invoke()}
    private data class Item(val sessionId:String,val mnv:String,val name:String,val date:String,val shift:String,val pda:String,val enterAt:String)

    fun build(activity:Activity,api:BetaApiClient,actualRole:String,confirmTime:(String,()->Unit)->Unit,onOpen:(JSONObject)->Unit):View{
        val d=activity.resources.displayMetrics.density
        fun dp(v:Int)=(v*d).toInt()
        fun round(color:Int,r:Int)=GradientDrawable().apply{setColor(color);cornerRadius=dp(r).toFloat()}
        fun txt(v:String,size:Float,color:Int,bold:Boolean=false)=TextView(activity).apply{text=v;textSize=size;setTextColor(color);typeface=if(bold)Typeface.DEFAULT_BOLD else Typeface.DEFAULT}
        fun dash(v:Any?):String=(v?.toString().orEmpty()).trim().ifBlank{"—"}
        val root=ReviewAlertUi.warningContainer(activity)
        val button=ReviewAlertUi.button(activity,WARNING_TEXT,ReviewAlertUi.Tone.WARNING)
        root.addView(button,ReviewAlertUi.fixedHeightParams(activity))
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
        fun reload(){
            api.call("old_active_sessions"){r->activity.runOnUiThread{if(r.ok)apply(parse(r.json?.optJSONArray("items")?:JSONArray()))}}
        }
        fun showList(){
            if(items.isEmpty())return
            val list=LinearLayout(activity).apply{orientation=LinearLayout.VERTICAL;setPadding(dp(10),dp(8),dp(10),dp(8))}
            var dialog:AlertDialog?=null
            if(actualRole.uppercase()=="SUPERADMIN"){
                val bulk=Button(activity).apply{
                    text="RA CA TẤT CẢ HỢP LỆ";textSize=10f;setTextColor(Color.WHITE);typeface=Typeface.DEFAULT_BOLD;isAllCaps=false;background=round(Color.rgb(180,35,45),9)
                    setOnClickListener{
                        dialog?.dismiss()
                        confirmTime("ra ca tất cả phiên cũ hợp lệ"){
                            isEnabled=false
                            val rootKey=UUID.randomUUID().toString();val failedIds=linkedSetOf<String>();var totalExited=0
                            fun runChunk(){
                                val payload=JSONObject().put("idempotency_key",rootKey).put("exclude_session_ids",JSONArray(failedIds.toList()))
                                api.call("old_active_sessions_bulk_exit",payload){r->activity.runOnUiThread{
                                    if(!r.ok){isEnabled=true;TopNotice.show(activity,r.error?:"Không ra ca hàng loạt được.",TopNotice.Kind.ERROR);reload();return@runOnUiThread}
                                    totalExited+=r.json?.optInt("exited",0)?:0
                                    val failedBatch=r.json?.optJSONArray("failed")?:JSONArray();for(i in 0 until failedBatch.length()){failedBatch.optJSONObject(i)?.optString("session_id")?.takeIf{it.isNotBlank()}?.let{failedIds.add(it)}}
                                    if(r.json?.optBoolean("has_more",false)==true){runChunk();return@runOnUiThread}
                                    isEnabled=true
                                    val skipped=r.json?.optInt("skipped_labor",0)?:0;val failed=failedIds.size
                                    TopNotice.show(activity,"Đã ra ca $totalExited phiên • bỏ qua công nhật $skipped${if(failed>0)" • lỗi $failed" else ""}.",if(failed>0)TopNotice.Kind.WARNING else TopNotice.Kind.SUCCESS)
                                    val remaining=r.json?.optJSONArray("items")?:JSONArray();apply(parse(remaining))
                                }}
                            }
                            runChunk()
                        }
                    }
                }
                list.addView(bulk,LinearLayout.LayoutParams(-1,dp(42)).apply{bottomMargin=dp(7)})
            }
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
        activeRefresh={activity.runOnUiThread{apply(local())}}
        root.addOnAttachStateChangeListener(object:View.OnAttachStateChangeListener{
            override fun onViewAttachedToWindow(v:View)=Unit
            override fun onViewDetachedFromWindow(v:View){if(activeRefresh!=null)activeRefresh=null}
        })
        reload()
        return root
    }
}
