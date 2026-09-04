from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected exactly 1 match, got {n}")
    return text.replace(old, new, 1)

ops_path = Path("app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt")
ops = ops_path.read_text(encoding="utf-8")

ops = replace_once(
    ops,
    '    private var laborRealtimeRefresh: ((String) -> Unit)? = null\n    private var laborWarningRealtimeRefresh: (() -> Unit)? = null\n',
    '    private var laborRealtimeRefresh: ((String) -> Unit)? = null\n    private var laborLocalUiRefresh: (() -> Unit)? = null\n    private var laborWarningRealtimeRefresh: (() -> Unit)? = null\n',
    "labor local callback property",
)

ops = replace_once(
    ops,
    '                    "EMPLOYEE" -> employeeTimelineRealtimeRefresh?.invoke(changedDates) // Timeline only; never rebuild the interactive employee form.\n                    "MEAL_ATTENDANCE" -> PostMealAttendanceFeature.onRealtime(changedDates)\n                    "EMPLOYEE_LOADING", "PDA_EXCHANGE" -> Unit\n',
    '                    "EMPLOYEE" -> employeeTimelineRealtimeRefresh?.invoke(changedDates) // Timeline only; never rebuild the interactive employee form.\n                    "LABOR_HOME" -> changedDates.forEach { laborRealtimeRefresh?.invoke(it) }\n                    "MEAL_ATTENDANCE" -> PostMealAttendanceFeature.onRealtime(changedDates)\n                    "EMPLOYEE_LOADING", "PDA_EXCHANGE" -> Unit\n',
    "operational projection refresh labor",
)

ops = replace_once(
    ops,
    '''            override fun onDayInvalidation(invalidation:JSONObject) {
                val date=invalidation.optString("business_date")
                when(screenState){
                    "BUSINESS"->businessFastRealtimeRefresh?.invoke(date)
                    "LABOR_HOME"->laborRealtimeRefresh?.invoke(date)
                    "MEAL_ATTENDANCE"->PostMealAttendanceFeature.onRealtimeFast(date)
                }
            }
''',
    '''            override fun onDayInvalidation(invalidation:JSONObject) {
                val date=invalidation.optString("business_date")
                val eventType=invalidation.optString("event_type").uppercase()
                when(screenState){
                    "BUSINESS"->when{
                        eventType in setOf("ATTENDANCE_ENTER","ATTENDANCE_EXIT","ATTENDANCE_TIME_CORRECTED","ATTENDANCE_EXIT_DELETED")->OldSessionWarningFeature.onRealtime()
                        eventType.startsWith("MEAL_")->PostMealAttendanceFeature.onRealtimeFast(date)
                        eventType in setOf("LABOR_START","LABOR_FINISH")->laborWarningRealtimeRefresh?.invoke()
                        eventType.isBlank()->businessFastRealtimeRefresh?.invoke(date) // compatibility with older invalidation payloads
                    }
                    "LABOR_HOME"->if(eventType.isBlank()||eventType in setOf("LABOR_START","LABOR_FINISH"))laborLocalUiRefresh?.invoke()
                    "MEAL_ATTENDANCE"->if(eventType.isBlank()||eventType.startsWith("MEAL_"))PostMealAttendanceFeature.onRealtimeFast(date)
                }
            }
''',
    "event-specific realtime routing",
)

ops = replace_once(
    ops,
    '                OldSessionWarningFeature.onRealtime();PostMealAttendanceFeature.onRealtime(dates);laborWarningRealtimeRefresh?.invoke()\n',
    '                OldSessionWarningFeature.onRealtime();laborWarningRealtimeRefresh?.invoke()\n',
    "avoid duplicate meal warning reload after day projection",
)

old_warning = '''    private fun laborOpenWarning():View{
        val host=ReviewAlertUi.warningContainer(this)
        val open=reconciliationButton("",false).apply{visibility=View.GONE;setOnClickListener{laborHome()}}
        host.addView(open,ReviewAlertUi.fixedHeightParams(this))
        fun refresh(){
            api.call("labor_list",JSONObject().put("business_date",operationalStore.businessDate())){r->runOnUiThread{
                if(!r.ok)return@runOnUiThread
                val items=r.json?.optJSONArray("items")?:JSONArray();var count=0
                for(i in 0 until items.length())if(items.optJSONObject(i)?.optString("state")?.equals("OPEN",true)==true)count++
                if(count>0){open.text="CẢNH BÁO: $count CÔNG NHẬT CHƯA HOÀN THÀNH";open.visibility=View.VISIBLE;host.visibility=View.VISIBLE}
                else{open.visibility=View.GONE;host.visibility=View.GONE}
            }}
        }
        laborWarningRealtimeRefresh={if(screenState=="BUSINESS")refresh()}
        refresh();return host
    }
'''
new_warning = '''    private fun laborOpenWarning():View{
        val host=ReviewAlertUi.warningContainer(this)
        val open=reconciliationButton("",false).apply{visibility=View.GONE;setOnClickListener{laborHome()}}
        host.addView(open,ReviewAlertUi.fixedHeightParams(this))
        fun applyCount(count:Int){
            if(count>0){open.text="CẢNH BÁO: $count CÔNG NHẬT CHƯA HOÀN THÀNH";open.visibility=View.VISIBLE;host.visibility=View.VISIBLE}
            else{open.visibility=View.GONE;host.visibility=View.GONE}
        }
        fun localCount():Int{
            val date=operationalStore.businessDate();val states=linkedMapOf<String,Boolean>()
            val day=operationalStore.loadDay(date);val events=day?.optJSONArray("events")?:JSONArray()
            for(i in 0 until events.length()){
                val ev=events.optJSONObject(i)?:continue;val type=ev.optString("event_type").uppercase()
                if(type !in setOf("LABOR_START","LABOR_FINISH"))continue
                val p=runCatching{JSONObject(ev.optString("payload_json","{}"))}.getOrDefault(JSONObject());val after=p.optJSONObject("after")?:JSONObject()
                val id=ev.optString("labor_id").ifBlank{p.optString("labor_id")}.ifBlank{after.optString("labor_id")}.ifBlank{ev.optString("entity_id")};if(id.isBlank())continue
                states[id]=type=="LABOR_START"
            }
            val raw=getSharedPreferences("pp_labor_list_cache_v116",MODE_PRIVATE).getString(date,"").orEmpty()
            if(raw.isNotBlank())runCatching{val a=JSONArray(raw);for(i in 0 until a.length()){val x=a.optJSONObject(i)?:continue;val id=x.optString("labor_id");if(id.isNotBlank()&&x.optLong("_local_pending_until",0L)>System.currentTimeMillis())states[id]=x.optString("state").equals("OPEN",true)}}
            return states.values.count{it}
        }
        fun refreshLocal(){applyCount(localCount())}
        laborWarningRealtimeRefresh={if(screenState=="BUSINESS")refreshLocal()}
        refreshLocal()
        api.call("labor_list",JSONObject().put("business_date",operationalStore.businessDate())){r->runOnUiThread{
            if(!r.ok||screenState!="BUSINESS")return@runOnUiThread
            val raw=getSharedPreferences("pp_labor_list_cache_v116",MODE_PRIVATE).getString(operationalStore.businessDate(),"").orEmpty()
            val hasPending=raw.isNotBlank()&&runCatching{val a=JSONArray(raw);(0 until a.length()).any{i->a.optJSONObject(i)?.optLong("_local_pending_until",0L)?.let{it>System.currentTimeMillis()}==true}}.getOrDefault(false)
            if(hasPending)return@runOnUiThread
            val items=r.json?.optJSONArray("items")?:JSONArray();var count=0
            for(i in 0 until items.length())if(items.optJSONObject(i)?.optString("state")?.equals("OPEN",true)==true)count++
            applyCount(count)
        }}
        return host
    }
'''
ops = replace_once(ops, old_warning, new_warning, "labor warning local first")

ops = replace_once(
    ops,
    '''    private fun patchLaborCacheOptimistic(item:JSONObject){
        val date=item.optString("business_date");val laborId=item.optString("labor_id");if(date.isBlank()||laborId.isBlank())return
        val cache=getSharedPreferences("pp_labor_list_cache_v116",MODE_PRIVATE);val raw=cache.getString(date,"").orEmpty();val rows=mutableListOf<JSONObject>()
        if(raw.isNotBlank())runCatching{val a=JSONArray(raw);for(i in 0 until a.length())a.optJSONObject(i)?.let{rows.add(JSONObject(it.toString()))}}
        val at=rows.indexOfFirst{it.optString("labor_id")==laborId};if(at>=0)rows[at]=JSONObject(item.toString()) else rows.add(0,JSONObject(item.toString()))
        cache.edit().putString(date,JSONArray(rows).toString()).apply()
    }
''',
    '''    private fun patchLaborCacheOptimistic(item:JSONObject){
        val date=item.optString("business_date");val laborId=item.optString("labor_id");if(date.isBlank()||laborId.isBlank())return
        val cache=getSharedPreferences("pp_labor_list_cache_v116",MODE_PRIVATE);val raw=cache.getString(date,"").orEmpty();val rows=mutableListOf<JSONObject>()
        if(raw.isNotBlank())runCatching{val a=JSONArray(raw);for(i in 0 until a.length())a.optJSONObject(i)?.let{rows.add(JSONObject(it.toString()))}}
        val optimistic=JSONObject(item.toString()).put("_local_pending_until",System.currentTimeMillis()+5_000L)
        val at=rows.indexOfFirst{it.optString("labor_id")==laborId};if(at>=0)rows[at]=optimistic else rows.add(0,optimistic)
        cache.edit().putString(date,JSONArray(rows).toString()).apply()
    }
''',
    "labor optimistic grace",
)

ops = replace_once(
    ops,
    '''    private fun laborBatchResult(title:String,success:Int,failures:List<String>){
        foregroundSync.requestSync()
        if(failures.isEmpty()){
            TopNotice.show(this,"$title: thành công $success nhân sự.",TopNotice.Kind.SUCCESS);laborHome();return
        }
        AlertDialog.Builder(this).setTitle(title).setMessage("Thành công: $success\\nLỗi: ${failures.size}\\n\\n${failures.take(12).joinToString("\\n")}").setPositiveButton("Đóng"){_,_->laborHome()}.show()
    }
''',
    '''    private fun laborBatchResult(title:String,success:Int,failures:List<String>){
        laborLocalUiRefresh?.invoke();foregroundSync.requestSync()
        if(failures.isEmpty()){
            TopNotice.show(this,"$title: thành công $success nhân sự.",TopNotice.Kind.SUCCESS);return
        }
        AlertDialog.Builder(this).setTitle(title).setMessage("Thành công: $success\\nLỗi: ${failures.size}\\n\\n${failures.take(12).joinToString("\\n")}").setPositiveButton("Đóng"){_,_->laborLocalUiRefresh?.invoke()}.show()
    }
''',
    "batch result in-place",
)

ops = replace_once(
    ops,
    '                            patchLaborCacheOptimistic(optimistic)\n                            if(end==null){next(index+1,ok+1);return@runOnUiThread}\n',
    '                            patchLaborCacheOptimistic(optimistic);laborLocalUiRefresh?.invoke()\n                            if(end==null){next(index+1,ok+1);return@runOnUiThread}\n',
    "batch create immediate render",
)
ops = replace_once(
    ops,
    '                                else{patchLaborCacheOptimistic(JSONObject(optimistic.toString()).put("state","COMPLETED").put("end_at",end));next(index+1,ok+1)}\n',
    '                                else{patchLaborCacheOptimistic(JSONObject(optimistic.toString()).put("state","COMPLETED").put("end_at",end));laborLocalUiRefresh?.invoke();next(index+1,ok+1)}\n',
    "batch create finish immediate render",
)
ops = replace_once(
    ops,
    '                            if(!done.ok){failures.add("$mnv: ${done.error?:"không kết thúc được"}");next(index+1,ok)}\n                            else next(index+1,ok+1)\n',
    '                            if(!done.ok){failures.add("$mnv: ${done.error?:"không kết thúc được"}");next(index+1,ok)}\n                            else{patchLaborCacheOptimistic(JSONObject(row.toString()).put("state","COMPLETED").put("end_at",endIso));laborLocalUiRefresh?.invoke();next(index+1,ok+1)}\n',
    "batch finish immediate render",
)

old_load = '''        fun loadOpen(){
            val cached=cache.getString(selectedLaborDate,"").orEmpty()
            val local=if(cached.isNotBlank())runCatching{val a=JSONArray(cached);(0 until a.length()).mapNotNull{a.optJSONObject(it)?.let{j->JSONObject(j.toString())}}}.getOrDefault(emptyList()) else localRows(selectedLaborDate)
            renderRows(local);reviewFixed(local)
            api.call("labor_list",JSONObject().put("business_date",selectedLaborDate)){r->runOnUiThread{
                if(screenState!="LABOR_HOME")return@runOnUiThread
                if(handleAuth(r))return@runOnUiThread
                if(!r.ok){if(local.isEmpty())openBox.addView(txt("Chưa tải được dữ liệu; sẽ tự cập nhật khi Service sẵn sàng.",9.3f,muted,false));return@runOnUiThread}
                val a=r.json?.optJSONArray("items")?:JSONArray();val fresh=(0 until a.length()).mapNotNull{a.optJSONObject(it)?.let{j->JSONObject(j.toString())}}
                cache.edit().putString(selectedLaborDate,a.toString()).apply();renderRows(fresh);reviewFixed(fresh)
            }}
        }
        laborRealtimeRefresh={date->if(screenState=="LABOR_HOME"&&date==selectedLaborDate)loadOpen()}
'''
new_load = '''        fun cachedRows(date:String):List<JSONObject>{
            val raw=cache.getString(date,"").orEmpty();if(raw.isBlank())return emptyList()
            return runCatching{val a=JSONArray(raw);(0 until a.length()).mapNotNull{a.optJSONObject(it)?.let{j->JSONObject(j.toString())}}}.getOrDefault(emptyList())
        }
        fun mergedLocalRows(date:String):List<JSONObject>{
            val cached=cachedRows(date);val canonical=localRows(date);if(canonical.isEmpty())return cached
            val map=linkedMapOf<String,JSONObject>();cached.forEach{x->x.optString("labor_id").takeIf{it.isNotBlank()}?.let{map[it]=JSONObject(x.toString())}}
            val now=System.currentTimeMillis()
            canonical.forEach{x->val id=x.optString("labor_id");val current=map[id];if(id.isNotBlank()&&(current==null||current.optLong("_local_pending_until",0L)<=now))map[id]=JSONObject(x.toString())}
            return map.values.toList()
        }
        fun renderLocalOnly(){
            val local=mergedLocalRows(selectedLaborDate);renderRows(local);reviewFixed(local)
        }
        fun mergeRemote(fresh:List<JSONObject>,local:List<JSONObject>):List<JSONObject>{
            val map=linkedMapOf<String,JSONObject>();fresh.forEach{x->x.optString("labor_id").takeIf{it.isNotBlank()}?.let{map[it]=JSONObject(x.toString())}}
            val now=System.currentTimeMillis()
            local.forEach{x->val id=x.optString("labor_id");val pending=x.optLong("_local_pending_until",0L)>now;if(id.isNotBlank()&&(pending||id !in map))map[id]=JSONObject(x.toString())}
            return map.values.toList()
        }
        fun loadOpen(){
            val local=mergedLocalRows(selectedLaborDate)
            renderRows(local);reviewFixed(local)
            api.call("labor_list",JSONObject().put("business_date",selectedLaborDate)){r->runOnUiThread{
                if(screenState!="LABOR_HOME")return@runOnUiThread
                if(handleAuth(r))return@runOnUiThread
                if(!r.ok){if(local.isEmpty())openBox.addView(txt("Chưa tải được dữ liệu; sẽ tự cập nhật khi Service sẵn sàng.",9.3f,muted,false));return@runOnUiThread}
                val a=r.json?.optJSONArray("items")?:JSONArray();val fresh=(0 until a.length()).mapNotNull{a.optJSONObject(it)?.let{j->JSONObject(j.toString())}}
                val merged=mergeRemote(fresh,mergedLocalRows(selectedLaborDate));cache.edit().putString(selectedLaborDate,JSONArray(merged).toString()).apply();renderRows(merged);reviewFixed(merged)
            }}
        }
        laborLocalUiRefresh={if(screenState=="LABOR_HOME")renderLocalOnly()}
        laborRealtimeRefresh={date->if(screenState=="LABOR_HOME"&&date==selectedLaborDate)renderLocalOnly()}
'''
ops = replace_once(ops, old_load, new_load, "labor stale remote merge")
ops_path.write_text(ops, encoding="utf-8")

old_path = Path("app/src/main/java/vn/pickpack1291/app/beta/OldSessionWarningFeature.kt")
old = old_path.read_text(encoding="utf-8")
old = replace_once(
    old,
    '            activeRefresh={activity.runOnUiThread{reload()}}\n',
    '            activeRefresh={activity.runOnUiThread{apply(local())}}\n',
    "old warning projection local refresh",
)
old = replace_once(
    old,
    '                            success("Đã ra ca ${j.optInt("exited",0)} phiên • bỏ qua công nhật ${j.optInt("skipped_labor",0)}${if(j.optInt("failed_count",0)>0)" • lỗi ${j.optInt("failed_count",0)}" else ""}")\n                            reload()\n',
    '                            success("Đã ra ca ${j.optInt("exited",0)} phiên • bỏ qua công nhật ${j.optInt("skipped_labor",0)}${if(j.optInt("failed_count",0)>0)" • lỗi ${j.optInt("failed_count",0)}" else ""}")\n                            val remaining=j.optJSONArray("items")?:JSONArray();apply((0 until remaining.length()).mapNotNull{remaining.optJSONObject(it)?.let{q->JSONObject(q.toString())}})\n',
    "old bulk exit immediate warning",
)
old_path.write_text(old, encoding="utf-8")

meal_path = Path("app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt")
meal = meal_path.read_text(encoding="utf-8")
meal = replace_once(
    meal,
    '''    fun onRealtime(changedDates:Set<String>){
        if(activeDate.isNotBlank()&&activeDate in changedDates)activeRefresh?.invoke()
        if(changedDates.isNotEmpty())homeWarningRefresh?.invoke()
    }
''',
    '''    fun onRealtime(changedDates:Set<String>){
        // Foreground websocket already performs the relevant fast refresh. Projection completion
        // must not fire a second Service-backed warning reload.
        if(activeDate.isNotBlank()&&activeDate in changedDates)activeRefresh?.invoke()
    }
''',
    "meal duplicate refresh suppression",
)
meal_path.write_text(meal, encoding="utf-8")

rt_path = Path("service/src/realtime.ts")
rt = rt_path.read_text(encoding="utf-8")
rt = replace_once(
    rt,
    '    return this.invalidate({type:"DAY_CHANGED",business_date:event.business_date,day_revision:event.authority_seq,authority_epoch:event.authority_epoch,authority_seq:event.authority_seq,service_generation:event.service_generation,event_id:event.event_id,entity_type:event.entity_type,entity_id:event.entity_id,new_version:event.new_version});\n',
    '    return this.invalidate({type:"DAY_CHANGED",business_date:event.business_date,day_revision:event.authority_seq,authority_epoch:event.authority_epoch,authority_seq:event.authority_seq,service_generation:event.service_generation,event_id:event.event_id,event_type:event.event_type,entity_type:event.entity_type,entity_id:event.entity_id,new_version:event.new_version});\n',
    "realtime event type hint",
)
rt_path.write_text(rt, encoding="utf-8")

print("BETA118_REALTIME_LOCALFIRST_FIX_APPLIED")
