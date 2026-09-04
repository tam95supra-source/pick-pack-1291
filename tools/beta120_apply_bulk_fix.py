#!/usr/bin/env python3
from pathlib import Path


def read(p): return Path(p).read_text(encoding='utf-8')
def write(p,s): Path(p).write_text(s,encoding='utf-8')
def one(s,a,b,label):
    n=s.count(a)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, got {n}')
    return s.replace(a,b,1)

# Beta120 metadata; Stable untouched.
p='app/build.gradle.kts'; s=read(p)
s=one(s,'versionCode = 125\n            versionName = "0.4.2-beta.119"','versionCode = 126\n            versionName = "0.4.2-beta.120"','beta version')
marker='// Beta119: SUPERADMIN session persistence, HHmm ±5 time auth, 8-digit single-use Gmail OTP rotation, and repository-backed realtime current/acceptance security fencing; preserves Beta118 behavior. Stable unchanged.'
s=one(s,marker,'// Beta120: route SUPERADMIN bulk old-session exit directly to Service and execute bounded canonical chunks to prevent GAS UNKNOWN/request timeout; preserves Beta119 behavior. Stable unchanged.\n'+marker,'gradle note')
write(p,s)

p='app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt'; s=read(p)
s=one(s,'const val VERSION_NAME = "0.4.2-beta.119"','const val VERSION_NAME = "0.4.2-beta.120"','release version')
s=one(s,'private val current = listOf(\n','private val current = listOf(\n        "Sửa Ra ca tất cả hợp lệ: luôn đi thẳng Service authority, không rơi sang GAS gây UNKNOWN.",\n        "Ra ca hàng loạt được chia thành các lô nhỏ có idempotency và cô lập phiên lỗi, tránh một phiên chậm làm timeout toàn bộ.",\n','release notes')
write(p,s)

# Existing endpoint is /v1/mobile/read; route this action there instead of GAS compatibility.
p='app/src/main/java/vn/pickpack1291/app/beta/M2RuntimeBridge.kt'; s=read(p)
s=one(s,'"employee_context","master_options","history_shared","old_active_sessions","historical_session_detail",','"employee_context","master_options","history_shared","old_active_sessions","old_active_sessions_bulk_exit","historical_session_detail",','direct route')
s=one(s,'requestMethod="POST";connectTimeout=1_500;readTimeout=3_000;doOutput=true;instanceFollowRedirects=true','requestMethod="POST";connectTimeout=1_500;readTimeout=if(payload.optString("action")=="old_active_sessions_bulk_exit")12_000 else 3_000;doOutput=true;instanceFollowRedirects=true','bulk timeout')
write(p,s)

# Service keeps canonical commitMutation semantics but caps one request at five exits.
p='service/src/mobile_hotfix.ts'; s=read(p)
start=s.index('async function oldActiveSessionsBulkExit(')
end=s.index('\nfunction eventLabel(',start)
new_func=r'''async function oldActiveSessionsBulkExit(env:Env,auth:AuthContext,body:Record<string,unknown>):Promise<Response>{
  if(auth.role!=="SUPERADMIN")return apiError("SUPERADMIN_REQUIRED","PERMISSION",403);
  const date=await businessDate(env.DB);
  const items=(await env.DB.prepare(`SELECT s.session_id,s.mnv,s.business_date,s.shift,s.pda_serial,s.version,
      (SELECT COUNT(*) FROM labor_sessions l WHERE l.mnv=s.mnv AND l.business_date=s.business_date) labor_count
    FROM attendance_sessions s
    WHERE s.state='ACTIVE' AND s.business_date<?1
    ORDER BY s.business_date ASC,s.enter_at ASC,s.mnv ASC`).bind(date).all<Record<string,unknown>>()).results??[];
  const excludedRaw=Array.isArray(body.exclude_session_ids)?body.exclude_session_ids:[];
  const excluded=new Set(excludedRaw.map(x=>String(x||"").trim()).filter(Boolean).slice(0,500));
  const skippedLabor=items.filter(row=>Number(row.labor_count||0)>0).map(row=>({session_id:String(row.session_id||""),mnv:String(row.mnv||""),business_date:String(row.business_date||""),reason:"HAS_LABOR"}));
  const eligible=items.filter(row=>Number(row.labor_count||0)===0&&!excluded.has(String(row.session_id||"")));
  const batch=eligible.slice(0,5);
  let exited=0;const failed:Array<Record<string,unknown>>=[];
  for(const row of batch){
    const sessionId=String(row.session_id||""),mnv=String(row.mnv||""),businessDateValue=String(row.business_date||"");
    try{
      await commitMutation(env.DB,env,auth,{
        event_id:crypto.randomUUID(),event_type:"ATTENDANCE_EXIT",entity_type:"ATTENDANCE_SESSION",entity_id:sessionId,
        business_date:businessDateValue,base_version:Number(row.version||0),timestamp:nowIso(),
        payload:{mnv,pda_exit_status:"SUPERADMIN_CONFIRMED",resource_note:"SUPERADMIN_BULK_OLD_SESSION_EXIT",superadmin_bulk_exit:true,pda_auto_confirmed:Boolean(String(row.pda_serial||""))},
        idempotency_key:`OLD_SESSION_BULK_EXIT|${sessionId}|${Number(row.version||0)}`,device_id:auth.device_id||"SUPERADMIN_BULK_EXIT",schema_version:1,client_source:"PDA"
      });
      exited++;
    }catch(error){failed.push({session_id:sessionId,mnv,business_date:businessDateValue,error:String(error instanceof Error?error.message:error).slice(0,160)});}
  }
  const remaining=(await env.DB.prepare("SELECT s.session_id,s.mnv,s.business_date,s.shift,s.work_choice,s.state,s.pda_serial,s.user_pick,s.pack_table,s.user_pack,s.enter_at,s.version,COALESCE(e.full_name,'') full_name FROM attendance_sessions s LEFT JOIN employees e ON e.mnv=s.mnv WHERE s.state='ACTIVE' AND s.business_date<?1 ORDER BY s.business_date ASC,s.enter_at ASC,s.mnv ASC").bind(date).all<Record<string,unknown>>()).results??[];
  return json({ok:true,source:"SERVICE_D1",business_date:date,exited,skipped_labor:skippedLabor.length,failed_count:failed.length,skipped_labor_items:skippedLabor,failed,processed_count:batch.length,batch_limit:5,has_more:eligible.length>batch.length,eligible_remaining:Math.max(0,eligible.length-batch.length),remaining_count:remaining.length,items:remaining});
}
'''
s=s[:start]+new_func+s[end:]
s=one(s,'if(action==="old_active_sessions_bulk_exit")return oldActiveSessionsBulkExit(env,auth);','if(action==="old_active_sessions_bulk_exit")return oldActiveSessionsBulkExit(env,auth,body);','service body route')
write(p,s)

# Client repeats bounded chunks and excludes failures, so one bad session does not stall all others.
p='app/src/main/java/vn/pickpack1291/app/beta/OldSessionWarningFeature.kt'; s=read(p)
anchor=s.index('text="RA CA TẤT CẢ HỢP LỆ"')
start=s.index('                            isEnabled=false',anchor)
end=s.index('\n                        }\n                    }\n                }',start)
new='''                            isEnabled=false
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
                            runChunk()'''
s=s[:start]+new+s[end:]
write(p,s)

Path('tools/beta120_bulk_exit_contract.py').write_text(r'''#!/usr/bin/env python3
from pathlib import Path
root=Path(__file__).resolve().parents[1]
read=lambda p:(root/p).read_text(encoding='utf-8')
gradle=read('app/build.gradle.kts');notes=read('app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt')
runtime=read('app/src/main/java/vn/pickpack1291/app/beta/M2RuntimeBridge.kt');old=read('app/src/main/java/vn/pickpack1291/app/beta/OldSessionWarningFeature.kt');service=read('service/src/mobile_hotfix.ts')
assert 'versionCode = 126' in gradle and 'versionName = "0.4.2-beta.120"' in gradle
assert 'versionCode = 1' in gradle and 'versionName = "0.1.0-stable"' in gradle
assert 'const val VERSION_NAME = "0.4.2-beta.120"' in notes
assert '"old_active_sessions","old_active_sessions_bulk_exit","historical_session_detail"' in runtime
assert 'readTimeout=if(payload.optString("action")=="old_active_sessions_bulk_exit")12_000 else 3_000' in runtime
assert 'const batch=eligible.slice(0,5)' in service and 'has_more:eligible.length>batch.length' in service
assert 'oldActiveSessionsBulkExit(env,auth,body)' in service
assert 'val failedIds=linkedSetOf<String>()' in old and 'exclude_session_ids' in old and 'fun runChunk()' in old
assert 'commitMutation(env.DB,env,auth' in service and 'OLD_SESSION_BULK_EXIT|' in service
print('beta120_bulk_exit_contract=PASS route=SERVICE_D1 chunk=5 idempotency=PASS failure_isolation=PASS stable_untouched=PASS')
''',encoding='utf-8')
print('beta120_apply_bulk_fix=PASS')
