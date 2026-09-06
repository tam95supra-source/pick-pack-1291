#!/usr/bin/env python3
from pathlib import Path

p=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
s=p.read_text(encoding='utf-8')
old='''    private fun addSessionTimeline(body:LinearLayout,mnv:String,ses:JSONObject){
        body.addView(section("DIỄN BIẾN CÔNG VIỆC TRONG CA"))
        val items=sessionTimelineItems(mnv,ses)
        if(items.isEmpty()){body.addView(txt("—",10.5f,muted,true).apply{setPadding(dp(10),dp(5),dp(10),dp(5))});return}
        for(e in items){
            val title=sessionEventTitle(e.optString("event_type"),e.optString("label"));val detail=e.optString("detail").trim();val actor=e.optString("actor").ifBlank{"Hệ thống"};val localStatus=e.optString("local_status")
            val card=column(surface).apply{
                setPadding(dp(9),dp(6),dp(9),dp(6));background=outlineBg(surface,12)
                val top=row(surface).apply{gravity=Gravity.CENTER_VERTICAL;addView(txt(title,10.7f,navy,true),LinearLayout.LayoutParams(0,-2,1f));addView(txt(sessionEventTime(e),9.4f,muted,true))};addView(top,matchWrap())
                if(detail.isNotBlank()){addView(gap(2));addView(txt(detail,10f,ink,false))}
                addView(gap(2));val statusText=when(localStatus){"LOCAL_PENDING","PENDING","OFFLINE_PROVISIONAL"->" • Chờ đồng bộ";"RETRY"->" • Chờ gửi lại";"REVIEW_REQUIRED","CONFLICT"->" • Cần kiểm tra";"REJECTED"->" • Bị từ chối";else->""};addView(txt("Người thực hiện: $actor$statusText",9.2f,muted,false))
            }
            body.addView(card,matchWrap());body.addView(gap(3))
        }
    }

    private fun addRealtimeSessionTimeline(body:LinearLayout,mnv:String,ses:JSONObject){
        val host=column(bg)
        val date=ses.optString("business_date").ifBlank{operationalStore.businessDate()}
        var renderedTimelineRevision:Long?=null
        fun renderTimeline(){
            val revision=date.takeIf{it.isNotBlank()}?.let{operationalStore.revision(it)}
            if(renderedTimelineRevision!=null&&revision==renderedTimelineRevision)return
            renderedTimelineRevision=revision
            host.suppressLayout(true)
            try{host.removeAllViews();addSessionTimeline(host,mnv,ses)}finally{host.suppressLayout(false)}
        }
        employeeTimelineRealtimeRefresh={dates->
            if(screenState=="EMPLOYEE"&&liveEmployeeMnv==mnv&&(date.isBlank()||date in dates))renderTimeline()
        }
        renderTimeline()
        body.addView(host,matchWrap())
    }
'''
new='''    private fun sessionTimelineRenderKey(e:JSONObject):String=e.optString("event_id").ifBlank{
        listOf(e.optString("event_type"),e.optString("at_iso").ifBlank{e.optString("at")},e.optString("actor").ifBlank{e.optString("actor_id")},e.optString("detail")).joinToString("|")
    }
    private fun sessionTimelineRenderSignature(e:JSONObject):String=listOf(
        sessionTimelineRenderKey(e),e.optString("event_type"),e.optString("label"),e.optString("detail"),e.optString("actor"),e.optString("local_status"),e.optString("local_error"),e.optString("at_iso"),e.optLong("local_queued_at",0L).toString()
    ).joinToString("\u001f")
    private fun sessionTimelineCard(e:JSONObject):LinearLayout{
        val title=sessionEventTitle(e.optString("event_type"),e.optString("label"));val detail=e.optString("detail").trim();val actor=e.optString("actor").ifBlank{"Hệ thống"};val localStatus=e.optString("local_status")
        return column(surface).apply{
            setPadding(dp(9),dp(6),dp(9),dp(6));background=outlineBg(surface,12)
            val top=row(surface).apply{gravity=Gravity.CENTER_VERTICAL;addView(txt(title,10.7f,navy,true),LinearLayout.LayoutParams(0,-2,1f));addView(txt(sessionEventTime(e),9.4f,muted,true))};addView(top,matchWrap())
            if(detail.isNotBlank()){addView(gap(2));addView(txt(detail,10f,ink,false))}
            addView(gap(2));val statusText=when(localStatus){"LOCAL_PENDING","PENDING","OFFLINE_PROVISIONAL"->" • Chờ đồng bộ";"RETRY"->" • Chờ gửi lại";"REVIEW_REQUIRED","CONFLICT"->" • Cần kiểm tra";"REJECTED"->" • Bị từ chối";else->""};addView(txt("Người thực hiện: $actor$statusText",9.2f,muted,false))
        }
    }
    private fun addSessionTimeline(body:LinearLayout,mnv:String,ses:JSONObject){
        body.addView(section("DIỄN BIẾN CÔNG VIỆC TRONG CA"))
        val items=sessionTimelineItems(mnv,ses)
        if(items.isEmpty()){body.addView(txt("—",10.5f,muted,true).apply{setPadding(dp(10),dp(5),dp(10),dp(5))});return}
        for(e in items){body.addView(sessionTimelineCard(e),matchWrap());body.addView(gap(3))}
    }

    private fun addRealtimeSessionTimeline(body:LinearLayout,mnv:String,ses:JSONObject){
        val host=column(bg)
        val date=ses.optString("business_date").ifBlank{operationalStore.businessDate()}
        var renderedTimelineRevision:Long?=null
        var renderedKeys=emptyList<String>()
        var renderedSignatures=emptyMap<String,String>()
        fun fullRender(items:List<JSONObject>,keys:List<String>,signatures:Map<String,String>){
            host.removeAllViews();host.addView(section("DIỄN BIẾN CÔNG VIỆC TRONG CA"))
            if(items.isEmpty())host.addView(txt("—",10.5f,muted,true).apply{setPadding(dp(10),dp(5),dp(10),dp(5))})
            else for(e in items){host.addView(sessionTimelineCard(e),matchWrap());host.addView(gap(3))}
            renderedKeys=keys;renderedSignatures=signatures
        }
        fun renderTimeline(){
            val revision=date.takeIf{it.isNotBlank()}?.let{operationalStore.revision(it)}
            if(renderedTimelineRevision!=null&&revision==renderedTimelineRevision)return
            val items=sessionTimelineItems(mnv,ses);val keys=items.map(::sessionTimelineRenderKey);val signatures=items.associate{sessionTimelineRenderKey(it) to sessionTimelineRenderSignature(it)}
            host.suppressLayout(true)
            try{
                if(renderedTimelineRevision==null){fullRender(items,keys,signatures)}
                else if(items.isNotEmpty()&&renderedKeys.isNotEmpty()&&keys.size>=renderedKeys.size&&keys.takeLast(renderedKeys.size)==renderedKeys){
                    val added=items.take(keys.size-renderedKeys.size)
                    for(e in added.asReversed()){host.addView(sessionTimelineCard(e),1,matchWrap());host.addView(gap(3),2)}
                    for(i in renderedKeys.indices){val key=renderedKeys[i];val next=signatures[key];if(next!=null&&next!=renderedSignatures[key]){val item=items.firstOrNull{sessionTimelineRenderKey(it)==key}?:continue;val index=1+(added.size+i)*2;host.removeViewAt(index);host.addView(sessionTimelineCard(item),index,matchWrap())}}
                    renderedKeys=keys;renderedSignatures=signatures
                }else if(keys==renderedKeys){
                    for(i in keys.indices){val key=keys[i];if(signatures[key]!=renderedSignatures[key]){val index=1+i*2;host.removeViewAt(index);host.addView(sessionTimelineCard(items[i]),index,matchWrap())}}
                    renderedSignatures=signatures
                }else fullRender(items,keys,signatures)
            }finally{host.suppressLayout(false)}
            renderedTimelineRevision=revision
        }
        employeeTimelineRealtimeRefresh={dates->
            if(screenState=="EMPLOYEE"&&liveEmployeeMnv==mnv&&(date.isBlank()||date in dates))renderTimeline()
        }
        renderTimeline()
        body.addView(host,matchWrap())
    }
'''
if old not in s:
    raise SystemExit('TIMELINE_REALTIME_ANCHOR_MISSING')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')

# Version bump: Android source changed, therefore a new Beta is mandatory.
g=Path('app/build.gradle.kts')
gs=g.read_text(encoding='utf-8')
if 'versionCode = 135' not in gs or 'versionName = "0.4.2-beta.129"' not in gs:
    raise SystemExit('BETA129_VERSION_ANCHOR_MISSING')
gs=gs.replace('versionCode = 135','versionCode = 136',1).replace('versionName = "0.4.2-beta.129"','versionName = "0.4.2-beta.130"',1)
g.write_text(gs,encoding='utf-8')

# Fail closed if the realtime path ever returns to full rebuild on every revision.
s2=p.read_text(encoding='utf-8')
start=s2.index('    private fun addRealtimeSessionTimeline(')
end=s2.index('\n    // S49_BETA43_SESSION_ADMIN_CORRECTIONS',start)
rt=s2[start:end]
assert 'keys.takeLast(renderedKeys.size)==renderedKeys' in rt
assert 'sessionTimelineCard(e),1,matchWrap()' in rt
assert 'else if(keys==renderedKeys)' in rt
assert 'host.removeAllViews();addSessionTimeline' not in rt
print('R5_BETA130_TIMELINE_INCREMENTAL_PATCH=PASS')
