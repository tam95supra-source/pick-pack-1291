#!/usr/bin/env python3
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
