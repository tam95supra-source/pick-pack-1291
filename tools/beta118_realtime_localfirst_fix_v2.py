from pathlib import Path
import runpy

# The v1 harness applies all OperationsActivity edits before stopping on an exact-spacing
# mismatch in OldSessionWarningFeature. Preserve those deterministic edits, then finish the
# remaining three files with exact current-source matches.
try:
    runpy.run_path('tools/beta118_realtime_localfirst_fix.py', run_name='__main__')
except SystemExit as exc:
    msg=str(exc)
    if not msg.startswith('old warning projection local refresh:'):
        raise


def replace_once(text:str,old:str,new:str,label:str)->str:
    n=text.count(old)
    if n!=1:
        raise SystemExit(f'{label}: expected exactly 1 match, got {n}')
    return text.replace(old,new,1)

old_path=Path('app/src/main/java/vn/pickpack1291/app/beta/OldSessionWarningFeature.kt')
old=old_path.read_text(encoding='utf-8')
old=replace_once(old,'        activeRefresh={activity.runOnUiThread{reload()}}\n','        activeRefresh={activity.runOnUiThread{apply(local())}}\n','old warning projection local refresh v2')
old=replace_once(
    old,
    '                                TopNotice.show(activity,"Đã ra ca $exited phiên • bỏ qua công nhật $skipped${if(failed>0)" • lỗi $failed" else ""}.",if(failed>0)TopNotice.Kind.WARNING else TopNotice.Kind.SUCCESS)\n                                reload()\n',
    '                                TopNotice.show(activity,"Đã ra ca $exited phiên • bỏ qua công nhật $skipped${if(failed>0)" • lỗi $failed" else ""}.",if(failed>0)TopNotice.Kind.WARNING else TopNotice.Kind.SUCCESS)\n                                val remaining=r.json?.optJSONArray("items")?:JSONArray();apply(parse(remaining))\n',
    'old bulk exit immediate warning v2',
)
old_path.write_text(old,encoding='utf-8')

meal_path=Path('app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt')
meal=meal_path.read_text(encoding='utf-8')
meal=replace_once(
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
    'meal duplicate refresh suppression v2',
)
meal_path.write_text(meal,encoding='utf-8')

rt_path=Path('service/src/realtime.ts')
rt=rt_path.read_text(encoding='utf-8')
rt=replace_once(
    rt,
    '    return this.invalidate({type:"DAY_CHANGED",business_date:event.business_date,day_revision:event.authority_seq,authority_epoch:event.authority_epoch,authority_seq:event.authority_seq,service_generation:event.service_generation,event_id:event.event_id,entity_type:event.entity_type,entity_id:event.entity_id,new_version:event.new_version});\n',
    '    return this.invalidate({type:"DAY_CHANGED",business_date:event.business_date,day_revision:event.authority_seq,authority_epoch:event.authority_epoch,authority_seq:event.authority_seq,service_generation:event.service_generation,event_id:event.event_id,event_type:event.event_type,entity_type:event.entity_type,entity_id:event.entity_id,new_version:event.new_version});\n',
    'realtime event type hint v2',
)
rt_path.write_text(rt,encoding='utf-8')
print('BETA118_REALTIME_LOCALFIRST_FIX_V2_APPLIED')
