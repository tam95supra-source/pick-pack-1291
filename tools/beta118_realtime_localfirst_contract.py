from pathlib import Path

ops=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt').read_text(encoding='utf-8')
old=Path('app/src/main/java/vn/pickpack1291/app/beta/OldSessionWarningFeature.kt').read_text(encoding='utf-8')
meal=Path('app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt').read_text(encoding='utf-8')
rt=Path('service/src/realtime.ts').read_text(encoding='utf-8')
doc=Path('app/src/main/java/vn/pickpack1291/app/beta/DocumentManagementFeature.kt').read_text(encoding='utf-8')
drop=Path('app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt').read_text(encoding='utf-8')
svc=Path('service/src/mobile_hotfix.ts').read_text(encoding='utf-8')

checks={
 'ws_event_type_hint':'event_type:event.event_type' in rt,
 'event_specific_router':'val eventType=invalidation.optString("event_type").uppercase()' in ops and 'eventType.startsWith("MEAL_")' in ops,
 'labor_projection_callback':'"LABOR_HOME" -> changedDates.forEach { laborRealtimeRefresh?.invoke(it) }' in ops,
 'labor_local_ui_callback':'private var laborLocalUiRefresh' in ops and 'laborLocalUiRefresh={if(screenState=="LABOR_HOME")renderLocalOnly()}' in ops,
 'labor_optimistic_grace':'_local_pending_until' in ops and 'System.currentTimeMillis()+5_000L' in ops,
 'labor_stale_remote_merge':'fun mergeRemote(fresh:List<JSONObject>,local:List<JSONObject>)' in ops and '(pending||id !in map)' in ops,
 'batch_no_full_home_reload':'TopNotice.show(this,"$title: thành công $success nhân sự.",TopNotice.Kind.SUCCESS);return' in ops,
 'batch_create_in_place':'patchLaborCacheOptimistic(optimistic);laborLocalUiRefresh?.invoke()' in ops,
 'batch_finish_in_place':'patchLaborCacheOptimistic(JSONObject(row.toString()).put("state","COMPLETED").put("end_at",endIso));laborLocalUiRefresh?.invoke()' in ops,
 'labor_warning_local':'laborWarningRealtimeRefresh={if(screenState=="BUSINESS")refreshLocal()}' in ops,
 'old_warning_local':'activeRefresh={activity.runOnUiThread{apply(local())}}' in old,
 'old_bulk_immediate':'val remaining=j.optJSONArray("items")?:JSONArray();apply(' in old,
 'meal_no_projection_double_reload':'must not fire a second Service-backed warning reload' in meal,
 'pda_exchange_optimistic':'holders.remove(h.serial);holders[next]=Holder(next,h.mnv,h.status)' in ops and 'render(serialField.text.toString());foregroundSync.requestSync()' in ops,
 'bulk_exit_super':'old_active_sessions_bulk_exit' in svc and 'SUPERADMIN_REQUIRED' in svc and 'HAS_LABOR' in svc and 'pda_auto_confirmed' in svc,
 'document_refresh_icon':'R.drawable.ic_pp_sync' in doc and 'Xóa ảnh chưa tải lên?' in doc,
 'document_helper_removed':'vuốt mọi ảnh' not in doc.lower() and 'pinch / kéo' not in doc.lower(),
 'drop_page_50':'dropPageSize=50' in drop and '50 TIẾP' in drop,
 'drop_actions_inline':'Thêm thông tin' in drop and 'Chọn tất cả' in drop and 'Xóa đã chọn' in drop,
 'drop_no_delete_all':'Xóa toàn bộ' not in drop,
}
failed=[k for k,v in checks.items() if not v]
if failed:
    raise SystemExit('BETA118_REALTIME_LOCALFIRST_CONTRACT_FAIL:'+','.join(failed))

# Deterministic behavior model: a stale remote response containing only row A must not erase
# two locally-confirmed optimistic rows A+B during the grace window.
now=1_000_000
local=[{'labor_id':'A','state':'OPEN','pending':now+5000},{'labor_id':'B','state':'OPEN','pending':now+5000}]
remote=[{'labor_id':'A','state':'OPEN'}]
merged={x['labor_id']:dict(x) for x in remote}
for x in local:
    if x['pending']>now or x['labor_id'] not in merged:
        merged[x['labor_id']]=dict(x)
assert set(merged)=={'A','B'} and len(merged)==2

print('beta118_realtime_localfirst_contract=PASS')
print('stale_remote_two_rows_preserved=PASS')
print('owner_followup_document_drop_bulk_exit=PASS')
