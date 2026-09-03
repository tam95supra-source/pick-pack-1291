package vn.pickpack1291.app.beta

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build
import android.os.SystemClock
import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import javax.crypto.Mac
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec
import javax.crypto.spec.SecretKeySpec
import kotlin.math.min

/** S31_SERVICE_FIRST_HOTPATH: SQLite hot path; Service/D1 direct; GAS background authority fallback only. */
class M2ServiceTransport(context: Context) {
    // S54_BETA48_OWNER_10_FIXES
    // retryDateWindowRejects is handled by durable OperationalDataStore selection.
    data class TransportResult(val handled: Boolean, val ok: Boolean, val code: Int, val json: JSONObject?, val error: String?)
    private val app = context.applicationContext
    private val prefs = app.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private val store = OperationalDataStore(app)
    private val connectivity = app.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager

    fun loginFromPassword(loginId: String, password: String) {
        if (ServiceFaultInjection.cloudflareDisabled(app)) return
        if (!hasNetwork()) return
        val d = discover(force = true) ?: return
        if (d.optString("authority_mode") != "SERVICE_PRIMARY") return
        val base = d.optString("service_url").trimEnd('/')
        if (!validServiceUrl(base)) return
        runCatching {
            val challenge = httpJson("$base/v1/auth/challenge", JSONObject().put("login_id", loginId.trim()), null)
            if (!challenge.ok || challenge.json == null) return
            val c = challenge.json
            val proof = proofForPassword(password, c.getString("salt"), c.optInt("iterations", 120_000), c.getString("challenge"))
            val body = JSONObject().put("login_id", loginId.trim()).put("challenge_id", c.getString("challenge_id")).put("proof", proof)
                .put("device_id", M2DeviceIdentity.id(app)).put("device_label", "${Build.MANUFACTURER} ${Build.MODEL}")
            val session = httpJson("$base/v1/auth/login", body, null)
            if (session.ok) {
                val token = session.json?.optString("token").orEmpty()
                if (token.isNotBlank()) prefs.edit().putString(KEY_SERVICE_TOKEN, token).apply()
                closeCircuit()
            }
        }.onFailure { recordFailure() }
    }

    /** Durable SQLite enqueue only. No network/discovery/authority lookup is allowed here. */
    fun operational(action: String, payload: JSONObject): TransportResult {
        if (action !in OPERATIONAL && action !in TECHNICAL) return TransportResult(false, false, 0, null, null)
        val eventId = payload.optString("event_id").ifBlank { java.util.UUID.randomUUID().toString() }
        val requestedDate=payload.optString("business_date").trim()
        val businessDate=if(action=="labor_start"||action=="labor_finish")requestedDate.takeIf{it.matches(Regex("\\d{4}-\\d{2}-\\d{2}"))}?:store.businessDate() else store.businessDate()
        payload.put("event_id",eventId).put("business_date",businessDate)
        val cleanPayload=sanitizeBusinessPayload(JSONObject(payload.toString()))
        val envelope=canonicalEnvelope(action,eventId,businessDate,cleanPayload)
        val request = JSONObject().put("action", action).put("event_id", eventId).put("business_date",businessDate).put("device_id", M2DeviceIdentity.id(app))
            .put("event_envelope",envelope).put("payload",cleanPayload)
        val exclusive = action == "enter" || action == "resource_change"
        store.enqueueMutation(request, exclusive)
        M2WorkScheduler.schedule(app)
        M2ImmediateOutbox.kick(app)
        val mode = cachedDiscoverySnapshot()?.optString("authority_mode").orEmpty()
        val manualLan=LanCoordinator.get(app).globalManualModeEnabled()
        val projection = when { manualLan -> "LAN_MANUAL_PENDING"; !hasNetwork() -> "OFFLINE_LOCAL"; mode == "GOOGLE_FALLBACK" -> "EMERGENCY_LEDGER_PENDING"; else -> "SERVICE_D1_PENDING" }
        return queuedResult(eventId, exclusive, projection)
    }

    /** Legacy Beta99 API retained only for compatibility. Beta100 UI uses isolatedResilienceTest(). */
    fun resilienceProbe(scenario:String):TransportResult =
        operational("resilience_probe",JSONObject()
            .put("scenario",scenario.take(80))
            .put("occurred_at",java.time.Instant.now().toString())
            .put("technical_probe",true))

    /**
     * Beta100 owner-acceptance test path.
     * Uses a dedicated technical-test ledger and never queues into mutation_outbox/local_history,
     * so simulated outages cannot reroute or mutate real operational writes.
     */
    fun isolatedResilienceTest(scenarioCode:String,cancelled:()->Boolean={false}):JSONObject {
        val spec=ResilienceTestScenario.fromCode(scenarioCode)
            ?: return JSONObject().put("status","FAIL").put("error","RESILIENCE_SCENARIO_INVALID")
        val eventId=java.util.UUID.randomUUID().toString()
        val started=System.currentTimeMillis()
        val payload=JSONObject()
            .put("scenario",spec.code)
            .put("occurred_at",java.time.Instant.now().toString())
            .put("technical_probe",true)
            .put("isolated_test",true)
        val businessDate=store.businessDate()
        val envelope=canonicalEnvelope("resilience_probe",eventId,businessDate,payload)
        val body=JSONObject()
            .put("action","resilience_probe")
            .put("event_id",eventId)
            .put("business_date",businessDate)
            .put("device_id",M2DeviceIdentity.id(app))
            .put("event_envelope",envelope)
            .put("payload",payload)
        val checksum=sha256Hex(body.toString())
        val evidence=JSONObject()
            .put("isolated_test_ledger",true)
            .put("business_outbox_touched",false)
            .put("event_checksum",checksum)
            .put("scenario",spec.code)
        store.saveResilienceTest(eventId,spec.code,body,"RUNNING","LOCAL_DURABLE","",evidence)

        fun row():JSONObject?=store.resilienceTest(eventId)
        fun update(status:String,stage:String,error:String="",extra:JSONObject=JSONObject(),attempt:Boolean=false){
            store.updateResilienceTest(eventId,status,stage,error,extra,attempt)
        }
        fun localIntegrity():Boolean{
            val persisted=row()?.optJSONObject("body")?:return false
            val ok=sha256Hex(persisted.toString())==checksum
            update("RUNNING","LOCAL_DURABLE_READBACK","",JSONObject().put("local_durable_readback",ok))
            return ok
        }
        fun serviceSubmit(allowDiscovery:Boolean):JSONObject{
            val discovery=if(allowDiscovery) discoverySnapshot() else cachedDiscoverySnapshot()
            if(discovery==null)return JSONObject().put("ok",false).put("error","SERVICE_DISCOVERY_CACHE_EMPTY")
            if(discovery.optString("authority_mode")!="SERVICE_PRIMARY")
                return JSONObject().put("ok",false).put("error","AUTHORITY_NOT_SERVICE_PRIMARY")
            val base=discovery.optString("service_url").trimEnd('/')
            if(!validServiceUrl(base))return JSONObject().put("ok",false).put("error","SERVICE_URL_INVALID")
            var token=prefs.getString(KEY_SERVICE_TOKEN,null)
            if(token.isNullOrBlank())token=exchangeBackgroundServiceSession(base)
            if(token.isNullOrBlank())return JSONObject().put("ok",false).put("error","SERVICE_SESSION_REAUTH_REQUIRED")
            fun submit(bearer:String)=httpJson("$base/v1/legacy-mutations/batch",JSONObject().put("events",JSONArray().put(body)),bearer)
            var r=submit(token)
            if(r.code==401){
                M2ServiceSessionManager.clearIfSame(app,token)
                val refreshed=exchangeBackgroundServiceSession(base)
                if(!refreshed.isNullOrBlank()){token=refreshed;r=submit(refreshed)}
            }
            if(!r.ok||r.json==null)return JSONObject().put("ok",false).put("code",r.code).put("error",r.error?:"SERVICE_SUBMIT_FAILED")
            val result=r.json.optJSONArray("results")?.optJSONObject(0)
                ?:return JSONObject().put("ok",false).put("error","SERVICE_RESULT_MISSING")
            val status=result.optString("status")
            val ok=status=="CONFIRMED"||status=="DUPLICATE"
            return JSONObject()
                .put("ok",ok).put("code",r.code).put("status",status)
                .put("canonical_event_id",result.optString("canonical_event_id").ifBlank{result.optString("event_id").ifBlank{eventId}})
                .put("error",result.optString("error_code"))
        }
        fun serviceConfirmWithIdempotency(allowDiscovery:Boolean):JSONObject{
            val first=serviceSubmit(allowDiscovery)
            if(!first.optBoolean("ok"))return JSONObject().put("ok",false).put("first",first)
            val second=serviceSubmit(false)
            val secondOk=second.optBoolean("ok")&&(second.optString("status")=="DUPLICATE"||second.optString("canonical_event_id")==first.optString("canonical_event_id"))
            return JSONObject()
                .put("ok",secondOk)
                .put("first_status",first.optString("status"))
                .put("second_status",second.optString("status"))
                .put("canonical_event_id",first.optString("canonical_event_id"))
                .put("idempotency_verified",secondOk)
                .put("error",if(secondOk)"" else second.optString("error").ifBlank{"IDEMPOTENCY_READBACK_FAILED"})
        }
        fun googleCapture():JSONObject{
            val gasToken=app.getSharedPreferences(AUTH_PREFS,Context.MODE_PRIVATE).getString(AUTH_TOKEN,null).orEmpty()
            if(gasToken.isBlank())return JSONObject().put("ok",false).put("error","GAS_AUTH_TOKEN_MISSING")
            val req=JSONObject()
                .put("action","emergency_ledger_capture")
                .put("events",JSONArray().put(envelope))
                .put("_token",gasToken)
                .put("_device_id",M2DeviceIdentity.id(app))
                .put("_app_version",BuildConfig.VERSION_NAME)
                .put("_app_channel",BuildConfig.CHANNEL)
            val r=httpJson(BuildConfig.GSHEET_API_URL,req,null,requireServiceHost=false)
            if(!r.ok)return JSONObject().put("ok",false).put("code",r.code).put("error",r.error?:"GAS_CAPTURE_FAILED")
            val arr=r.json?.optJSONArray("captured")?:JSONArray()
            var found=false
            for(i in 0 until arr.length())if(arr.optJSONObject(i)?.optString("event_id")==eventId)found=true
            return JSONObject().put("ok",found).put("captured",found).put("error",if(found)"" else "GAS_CAPTURE_ACK_MISSING")
        }
        fun googleFinalize():Boolean{
            val gasToken=app.getSharedPreferences(AUTH_PREFS,Context.MODE_PRIVATE).getString(AUTH_TOKEN,null).orEmpty()
            if(gasToken.isBlank())return false
            val req=JSONObject()
                .put("action","emergency_ledger_finalize")
                .put("items",JSONArray().put(JSONObject().put("event_id",eventId).put("status","CONFIRMED").put("canonical_event_id",eventId)))
                .put("_token",gasToken)
                .put("_device_id",M2DeviceIdentity.id(app))
                .put("_app_version",BuildConfig.VERSION_NAME)
                .put("_app_channel",BuildConfig.CHANNEL)
            return runCatching{httpJson(BuildConfig.GSHEET_API_URL,req,null,requireServiceHost=false).ok}.getOrDefault(false)
        }
        fun fail(stage:String,error:String,extra:JSONObject=JSONObject()):JSONObject{
            if(cancelled()){
                val stopped=JSONObject()
                    .put("duration_ms",System.currentTimeMillis()-started)
                    .put("stopped_by_owner",true)
                    .put("isolated_scope_closed",true)
                    .put("business_outbox_touched",false)
                update("CANCELLED","STOPPED_BY_OWNER","",stopped)
                return row()?:JSONObject().put("status","CANCELLED").put("stage","STOPPED_BY_OWNER")
            }
            extra.put("duration_ms",System.currentTimeMillis()-started)
            update("FAIL",stage,error,extra,true)
            return row()?:JSONObject().put("status","FAIL").put("error",error)
        }
        fun stopped():JSONObject{
            val extra=JSONObject()
                .put("duration_ms",System.currentTimeMillis()-started)
                .put("stopped_by_owner",true)
                .put("isolated_scope_closed",true)
                .put("business_outbox_touched",false)
            update("CANCELLED","STOPPED_BY_OWNER","",extra)
            return row()?:JSONObject().put("status","CANCELLED").put("stage","STOPPED_BY_OWNER")
        }
        fun stopIfRequested():JSONObject?=if(cancelled())stopped() else null
        fun pass(stage:String,extra:JSONObject=JSONObject()):JSONObject{
            stopIfRequested()?.let{return it}
            extra.put("duration_ms",System.currentTimeMillis()-started)
            update("PASS",stage,"",extra)
            return row()?:JSONObject().put("status","PASS")
        }

        if(!localIntegrity())return fail("LOCAL_DURABLE_READBACK","LOCAL_TEST_LEDGER_INTEGRITY_FAILED")
        stopIfRequested()?.let{return it}

        return when(spec){
            ResilienceTestScenario.NORMAL_SERVICE_PRIMARY->{
                stopIfRequested()?.let{return it}
                val service=serviceConfirmWithIdempotency(true)
                if(!service.optBoolean("ok"))fail("SERVICE_PRIMARY",service.optString("error"),JSONObject().put("service",service))
                else pass("COMPLETE",JSONObject().put("service",service).put("expected_route","SERVICE_PRIMARY"))
            }
            ResilienceTestScenario.DEVICE_OFFLINE_LOCAL->{
                update("RUNNING","SIMULATED_DEVICE_OFFLINE","",JSONObject().put("network_simulated_offline",true))
                stopIfRequested()?.let{return it}
                val service=serviceConfirmWithIdempotency(true)
                if(!service.optBoolean("ok"))fail("RECOVERY_REPLAY",service.optString("error"),JSONObject().put("service",service))
                else pass("COMPLETE",JSONObject().put("local_only_before_recovery",true).put("recovery_service",service))
            }
            ResilienceTestScenario.SERVICE_UNAVAILABLE_GOOGLE->{
                update("RUNNING","SIMULATED_SERVICE_UNAVAILABLE","TEST_SERVICE_UNAVAILABLE",JSONObject().put("service_blocked",true))
                stopIfRequested()?.let{return it}
                val gas=googleCapture()
                if(!gas.optBoolean("ok"))return fail("GOOGLE_EMERGENCY_CAPTURE",gas.optString("error"),JSONObject().put("google",gas))
                stopIfRequested()?.let{return it}
                val lan=LanCoordinator.get(app)
                val lanEvidence=JSONObject().put("available",lan.canRoute())
                if(lan.canRoute()){
                    val ack=lan.submit(body)
                    lanEvidence.put("handled",ack.handled).put("ok",ack.ok).put("generation",ack.generation).put("error",ack.error?:"")
                }
                update("RUNNING","FALLBACK_CAPTURED","",JSONObject().put("google",gas).put("lan_optional",lanEvidence))
                stopIfRequested()?.let{return it}
                val service=serviceConfirmWithIdempotency(true)
                if(!service.optBoolean("ok"))return fail("RECOVERY_REPLAY",service.optString("error"),JSONObject().put("service",service))
                stopIfRequested()?.let{return it}
                val finalized=googleFinalize()
                pass("COMPLETE",JSONObject().put("recovery_service",service).put("google_finalized",finalized))
            }
            ResilienceTestScenario.SERVICE_TIMEOUT_GOOGLE->{
                update("RUNNING","SIMULATED_SERVICE_TIMEOUT","TEST_SERVICE_TIMEOUT",JSONObject().put("service_timeout_simulated",true))
                stopIfRequested()?.let{return it}
                val gas=googleCapture()
                if(!gas.optBoolean("ok"))return fail("GOOGLE_EMERGENCY_CAPTURE",gas.optString("error"),JSONObject().put("google",gas))
                stopIfRequested()?.let{return it}
                val service=serviceConfirmWithIdempotency(true)
                if(!service.optBoolean("ok"))return fail("RECOVERY_REPLAY",service.optString("error"),JSONObject().put("service",service))
                stopIfRequested()?.let{return it}
                pass("COMPLETE",JSONObject().put("google",gas).put("recovery_service",service).put("google_finalized",googleFinalize()))
            }
            ResilienceTestScenario.GOOGLE_UNAVAILABLE_SERVICE->{
                update("RUNNING","SIMULATED_GOOGLE_UNAVAILABLE","TEST_GOOGLE_UNAVAILABLE",JSONObject().put("google_blocked",true))
                stopIfRequested()?.let{return it}
                val service=serviceConfirmWithIdempotency(false)
                if(!service.optBoolean("ok"))fail("SERVICE_DIRECT_WITH_GOOGLE_DOWN",service.optString("error"),JSONObject().put("service",service))
                else pass("COMPLETE",JSONObject().put("service",service).put("google_path_used",false))
            }
            ResilienceTestScenario.SERVICE_GOOGLE_OFFLINE_LOCAL->{
                update("RUNNING","SIMULATED_SERVICE_GOOGLE_LAN_UNAVAILABLE","TEST_ALL_REMOTE_UNAVAILABLE",
                    JSONObject().put("service_blocked",true).put("google_blocked",true).put("lan_simulated_unavailable",true))
                stopIfRequested()?.let{return it}
                val persisted=localIntegrity()
                if(!persisted)return fail("LOCAL_ONLY","LOCAL_TEST_LEDGER_INTEGRITY_FAILED")
                stopIfRequested()?.let{return it}
                val service=serviceConfirmWithIdempotency(true)
                if(!service.optBoolean("ok"))fail("RECOVERY_REPLAY",service.optString("error"),JSONObject().put("service",service))
                else pass("COMPLETE",JSONObject().put("local_only_verified",true).put("recovery_service",service))
            }
            ResilienceTestScenario.SERVICE_GOOGLE_OFFLINE_LAN->{
                update("RUNNING","SIMULATED_CLOUD_PATHS_UNAVAILABLE","TEST_CLOUD_PATHS_UNAVAILABLE",
                    JSONObject().put("service_blocked",true).put("google_blocked",true))
                stopIfRequested()?.let{return it}
                val lan=LanCoordinator.get(app)
                val deadline=System.currentTimeMillis()+8_000L
                while(!lan.canRouteForTest()&&System.currentTimeMillis()<deadline&&!cancelled())Thread.sleep(250L)
                if(!lan.canRouteForTest()){
                    update("NOT_AVAILABLE","LAN_PREREQUISITE_MISSING","LAN_GLOBAL_TEST_TOPOLOGY_NOT_READY",
                        JSONObject().put("requires_lan_master_backup",true).put("global_test_mode",lan.globalTestModeEnabled()).put("lan_status",lan.status()))
                    return row()?:JSONObject().put("status","NOT_AVAILABLE")
                }
                val ack=lan.submitTest(body)
                if(!ack.handled||!ack.ok)return fail("LAN_FALLBACK",ack.error?:"LAN_SUBMIT_FAILED",
                    JSONObject().put("lan_generation",ack.generation).put("lan_handled",ack.handled))
                update("RUNNING","LAN_DURABLE_ACK","",JSONObject().put("lan_generation",ack.generation).put("lan_ack",true))
                stopIfRequested()?.let{return it}
                val service=serviceConfirmWithIdempotency(true)
                if(!service.optBoolean("ok"))fail("RECOVERY_REPLAY",service.optString("error"),JSONObject().put("service",service))
                else pass("COMPLETE",JSONObject().put("lan_ack",true).put("recovery_service",service))
            }
        }
    }

    private fun canonicalEnvelope(action:String,eventId:String,businessDate:String,payload:JSONObject):JSONObject{
        val auth=app.getSharedPreferences(AUTH_PREFS,Context.MODE_PRIVATE)
        val discovery=cachedDiscoverySnapshot()
        val authority=discovery?.optJSONObject("authority")
        val deviceId=M2DeviceIdentity.id(app)
        val payloadText=payload.toString()
        return JSONObject()
            .put("event_id",eventId)
            .put("idempotency_key",payload.optString("idempotency_key").ifBlank{eventId})
            .put("event_type",action.uppercase())
            .put("schema_version",1)
            .put("actor_mnv",payload.optString("mnv"))
            .put("user_id",auth.getString("login_id","").orEmpty())
            .put("role",auth.getString("role","USER").orEmpty())
            .put("device_id",deviceId)
            .put("app_version",BuildConfig.VERSION_NAME)
            .put("business_date",businessDate)
            .put("device_time",java.time.Instant.now().toString())
            .put("trusted_received_time",JSONObject.NULL)
            .put("device_sequence",nextDeviceSequence())
            .put("depends_on_event_id",payload.optString("depends_on_event_id"))
            .put("session_id",payload.optString("session_id"))
            .put("authority_epoch",authority?.optLong("authority_epoch")?:discovery?.optLong("authority_epoch")?:0L)
            .put("service_generation",authority?.optString("service_generation").orEmpty().ifBlank{discovery?.optString("service_generation").orEmpty()})
            .put("checksum",sha256Hex(payloadText))
            .put("payload",payload)
    }

    private fun sanitizeBusinessPayload(source:JSONObject):JSONObject{
        val out=JSONObject()
        val keys=source.keys()
        while(keys.hasNext()){
            val key=keys.next()
            val folded=key.lowercase()
            if(listOf("password","secret","token","signing","api_key","apikey","credential","verifier","proof").any{folded.contains(it)})continue
            val value=source.opt(key)
            out.put(key,when(value){
                is JSONObject->sanitizeBusinessPayload(value)
                is JSONArray->JSONArray().apply{for(i in 0 until value.length()){val x=value.opt(i);put(if(x is JSONObject)sanitizeBusinessPayload(x) else x)}}
                else->value
            })
        }
        return out
    }

    private fun nextDeviceSequence():Long=synchronized(DEVICE_SEQUENCE_LOCK){
        val n=prefs.getLong(KEY_DEVICE_SEQUENCE,0L)+1L
        prefs.edit().putLong(KEY_DEVICE_SEQUENCE,n).commit()
        n
    }
    private fun sha256Hex(value:String):String=MessageDigest.getInstance("SHA-256").digest(value.toByteArray(Charsets.UTF_8)).joinToString(""){(it.toInt() and 0xff).toString(16).padStart(2,'0')}


    // S31B_PRESERVE_ADMIN_AUDIT / S30_CANONICAL_ADMIN_AUDIT: sanitized admin audit uses the same durable outbox.
    fun audit(action:String,payload:JSONObject){
        if(action !in ADMIN_AUDIT_ACTIONS)return
        val eventId=java.util.UUID.randomUUID().toString()
        val targetId=when(action){
            "staff_upsert","staff_delete"->payload.optString("mnv")
            "account_upsert","account_status","change_email","change_password"->payload.optString("login_id").ifBlank{payload.optString("target_login_id")}
            else->""
        }
        val targetLabel=payload.optString("full_name").ifBlank{payload.optString("display_name")}.take(180)
        val detail=when(action){
            "staff_upsert"->"Thêm / cập nhật hồ sơ nhân sự"
            "staff_delete"->"Xóa hồ sơ nhân sự"
            "account_upsert"->"Tạo / cập nhật tài khoản"
            "account_status"->"Thay đổi trạng thái tài khoản"
            "change_email"->"Thay đổi email tài khoản"
            "change_password"->"Thay đổi mật khẩu"
            else->"Thao tác quản trị"
        }
        val body=JSONObject()
            .put("action","admin_audit")
            // Durable outbox routing type is admin_audit; audit_action is the canonical business audit type.
            // Never put passwords/proofs/verifiers in this body.
            .put("audit_action",action)
            .put("event_id",eventId)
            .put("target_type",if(action.startsWith("staff_"))"STAFF" else "ACCOUNT")
            .put("target_id",targetId.take(180))
            .put("target_label",targetLabel)
            .put("result","OK")
            .put("detail",detail)
            .put("device_id",M2DeviceIdentity.id(app))
            .put("occurred_at",java.time.Instant.now().toString())
        store.enqueueMutation(body,false)
        M2WorkScheduler.schedule(app)
        M2ImmediateOutbox.kick(app)
    }

    fun acknowledgeFallback(eventId: String, ok: Boolean, error: String?) {
        if (eventId.isBlank()) return
        if (ok) store.markEmergencyCaptured(eventId) else if (!error.isNullOrBlank()) store.markMutationRetry(eventId, error, 5_000L)
    }

    /** Direct Service read using cached discovery only. A Service failure is handled, never a GAS fall-through. */
    fun sync(action: String, payload: JSONObject): TransportResult {
        if (action !in SYNC_ACTIONS) return TransportResult(false, false, 0, null, null)
        if (ServiceFaultInjection.cloudflareDisabled(app)) return TransportResult(false,false,-1,null,"TEST_CLOUDFLARE_DISABLED")
        if (!hasNetwork()) return TransportResult(true, false, -1, null, "OFFLINE_LOCAL")
        val discovery = discoverySnapshot() ?: return TransportResult(true, false, 0, null, "DISCOVERY_WARMING")
        val mode = discovery.optString("authority_mode")
        if (mode == "GOOGLE_FALLBACK") return TransportResult(false, false, 0, null, "FENCED_GOOGLE_FALLBACK")
        if (mode != "SERVICE_PRIMARY") return TransportResult(true, false, 0, null, "AUTHORITY_NOT_SERVICE_PRIMARY")
        if (circuitOpen()) return TransportResult(true, false, -1, null, "SERVICE_CIRCUIT_OPEN")
        val base = discovery.optString("service_url").trimEnd('/')
        val token = prefs.getString(KEY_SERVICE_TOKEN, null)
        if (!validServiceUrl(base) || token.isNullOrBlank()) return TransportResult(true, false, 0, null, "SERVICE_SESSION_UNAVAILABLE")
        val request = JSONObject(payload.toString()).put("action", action)
        val started = SystemClock.elapsedRealtime()
        return try {
            val r = if(action=="service_connections") httpGetJson("$base/v1/service/connections",token) else httpJson("$base/v1/legacy-sync", request, token)
            val rtt = (SystemClock.elapsedRealtime() - started).coerceAtLeast(0L)
            val body = (r.json?.let { JSONObject(it.toString()) } ?: JSONObject()).put("_service_rtt_ms", rtt)
            if (r.code >= 500 || r.code == -1) {
                recordFailure(); M2WorkScheduler.schedule(app); TransportResult(true, false, r.code, body, r.error ?: "SERVICE_UNAVAILABLE")
            } else {
                if (r.code == 401) prefs.edit().remove(KEY_SERVICE_TOKEN).apply()
                if (r.ok) closeCircuit()
                TransportResult(true, r.ok, r.code, body, r.error)
            }
        } catch (t: Throwable) {
            val rtt = (SystemClock.elapsedRealtime() - started).coerceAtLeast(0L)
            recordFailure(); M2WorkScheduler.schedule(app)
            TransportResult(true, false, -1, JSONObject().put("_service_rtt_ms", rtt), t.message ?: "SERVICE_READ_NETWORK_ERROR")
        }
    }

    /** Background worker: Service first. GAS may confirm fallback only after 3 consecutive Service failures. */
    /** S39_EMPLOYEE_SESSION_HISTORY: background-only Service session recovery; UI hot path stays SQLite-first. */
    // S44_SESSION_SINGLEFLIGHT_OBSERVABILITY: every immediate/WorkManager trigger shares this lock.
    fun flushOutbox(): Boolean = synchronized(FLUSH_LOCK) {
        val count=runCatching{store.unresolvedMutations(100).size}.getOrDefault(0)
        M2TransportDiagnostics.notePumpStart(app,count)
        val result=runCatching{flushOutboxLocked()}.getOrElse{M2TransportDiagnostics.notePumpEnd(app,false,it.message?:it.javaClass.simpleName);false}
        M2TransportDiagnostics.notePumpEnd(app,result)
        result
    }

    private fun flushOutboxLocked(): Boolean {
        val items=store.unresolvedMutations(100);if(items.isEmpty())return true
        val lan=LanCoordinator.get(app)
        if(lan.globalManualModeEnabled()){
            if(lan.canRoute()){
                items.forEach{item->
                    val ack=lan.submit(item.body)
                    if(ack.handled&&ack.ok)store.markLanConfirmed(item.eventId,ack.generation)
                    else if(item.status!="OFFLINE_PROVISIONAL")store.markMutationRetry(item.eventId,ack.error?:"LAN_MANUAL_NOT_READY",retryDelay(item.attemptCount))
                }
            }else items.filter{it.status!="OFFLINE_PROVISIONAL"}.forEach{store.markMutationRetry(it.eventId,"LAN_MANUAL_NOT_READY",retryDelay(it.attemptCount))}
            return false
        }
        if (!hasNetwork()) return serviceUnavailable(items,"NETWORK_UNAVAILABLE",false)
        if(ServiceFaultInjection.cloudflareDisabled(app))return serviceUnavailable(items,"TEST_CLOUDFLARE_DISABLED",true)
        val discovery=discoverySnapshot()
        if(discovery==null)return serviceUnavailable(items,"SERVICE_DISCOVERY_UNAVAILABLE",true)
        if(discovery.optString("authority_mode")=="GOOGLE_FALLBACK")return serviceUnavailable(items,"GOOGLE_FALLBACK_AUTHORITY",true)
        if(discovery.optString("authority_mode")!="SERVICE_PRIMARY")return serviceUnavailable(items,"AUTHORITY_NOT_SERVICE_PRIMARY",true)
        if(circuitOpen())return serviceUnavailable(items,"SERVICE_CIRCUIT_OPEN",true)
        val base=discovery.optString("service_url").trimEnd('/');if(!validServiceUrl(base))return serviceUnavailable(items,"SERVICE_URL_INVALID",true)
        var token=prefs.getString(KEY_SERVICE_TOKEN,null)
        if(token.isNullOrBlank()){
            token=exchangeBackgroundServiceSession(base)
            if(token.isNullOrBlank())return serviceUnavailable(items,"SERVICE_SESSION_REAUTH_REQUIRED",true)
        }
        fun submit(bearer:String):HttpResult{
            val body=JSONObject().put("events",JSONArray().apply{items.forEach{put(it.body)}})
            val started=System.currentTimeMillis()
            return httpJson("$base/v1/legacy-mutations/batch",body,bearer).also{M2TransportDiagnostics.noteBatch(app,it.code,it.ok,it.error,items.size,System.currentTimeMillis()-started)}
        }
        return try{
            var r=submit(token)
            if(r.code==401){M2ServiceSessionManager.clearIfSame(app,token);val refreshed=exchangeBackgroundServiceSession(base);if(!refreshed.isNullOrBlank())r=submit(refreshed)}
            if(r.code==401)return serviceUnavailable(items,"SERVICE_SESSION_REAUTH_REQUIRED",true)
            if(!r.ok||r.json==null){
                val outage=r.code==-1||r.code==429||r.code>=500||(r.error?:"").uppercase().let{it.contains("QUOTA")||it.contains("FULL")}
                if(outage){recordFailure();return serviceUnavailable(items,r.error?:"HTTP_${r.code}",true)}
                items.forEach{store.markMutationRetry(it.eventId,r.error?:"HTTP_${r.code}",retryDelay(it.attemptCount))}
                return false
            }
            LanCoordinator.get(app).noteServiceStatus(true)
            val results=r.json.optJSONArray("results")?:JSONArray();val byId=items.associateBy{it.eventId};var retryNeeded=false
            val finalized=JSONArray()
            for(i in 0 until results.length()){
                val result=results.optJSONObject(i)?:continue;val eventId=result.optString("local_event_id");val item=byId[eventId]?:continue
                val error=result.optString("error_code").ifBlank{result.optJSONObject("conflict")?.toString().orEmpty()}
                when(result.optString("status")){
                    "CONFIRMED","DUPLICATE"->{store.markMutationSynced(eventId);finalized.put(JSONObject().put("event_id",eventId).put("status",result.optString("status")).put("canonical_event_id",result.optString("event_id").ifBlank{eventId}))}
                    "REVIEW_REQUIRED"->{store.markMutationReviewRequired(eventId,error);finalized.put(JSONObject().put("event_id",eventId).put("status","REVIEW_REQUIRED").put("last_error_code",error))}
                    "REJECTED"->if(result.optBoolean("retryable",false)){store.markMutationRetry(eventId,error.ifBlank{"RETRYABLE_REJECT"},retryDelay(item.attemptCount));retryNeeded=true}else{store.markMutationRejected(eventId,error);finalized.put(JSONObject().put("event_id",eventId).put("status","REJECTED").put("last_error_code",error))}
                    else->{store.markMutationRetry(eventId,"BATCH_RESULT_INVALID",retryDelay(item.attemptCount));retryNeeded=true}
                }
            }
            val returned=HashSet<String>().apply{for(i in 0 until results.length())add(results.optJSONObject(i)?.optString("local_event_id").orEmpty())}
            items.filter{it.eventId !in returned}.forEach{store.markMutationRetry(it.eventId,"BATCH_RESULT_MISSING",retryDelay(it.attemptCount));retryNeeded=true}
            finalizeEmergency(finalized)
            if(!retryNeeded)closeCircuit()
            !retryNeeded
        }catch(x:Throwable){
            recordFailure()
            serviceUnavailable(items,x.message?:"NETWORK",true)
        }
    }

    private fun serviceUnavailable(items:List<OperationalDataStore.PendingMutation>,reason:String,googleReachable:Boolean):Boolean{
        val lan=LanCoordinator.get(app)
        lan.noteServiceStatus(false)
        if(googleReachable&&!ServiceFaultInjection.googleDisabled(app))captureEmergency(items)
        var lanConfirmed=0
        if(lan.canRoute()){
            items.forEach{item->
                val ack=lan.submit(item.body)
                if(ack.handled&&ack.ok){store.markLanConfirmed(item.eventId,ack.generation);lanConfirmed++}
                else if(item.status!="OFFLINE_PROVISIONAL")store.markMutationRetry(item.eventId,ack.error?:reason,retryDelay(item.attemptCount))
            }
        }else{
            items.filter{it.status!="OFFLINE_PROVISIONAL"}.forEach{store.markMutationRetry(it.eventId,reason,retryDelay(it.attemptCount))}
        }
        return false
    }

    private fun exchangeBackgroundServiceSession(base:String):String? = M2ServiceSessionManager.ensure(app,base,force=true)

    private fun discoveryMatchesEnvironment(j:JSONObject):Boolean {
        if(j.optString("environment_id")!=BuildConfig.ENVIRONMENT_ID)return false
        if(j.optString("service_audience")!=BuildConfig.SERVICE_AUDIENCE)return false
        val service=j.optString("service_url").trimEnd('/')
        return service.isBlank()||validServiceUrl(service)
    }

    fun cachedDiscoverySnapshot(): JSONObject? = prefs.getString(KEY_DISCOVERY_JSON, null)
        ?.let { runCatching { JSONObject(it) }.getOrNull() }
        ?.takeIf { discoveryMatchesEnvironment(it) }

    fun discoverySnapshot(force:Boolean=false): JSONObject? = discover(force=force)

    private fun captureEmergency(items:List<OperationalDataStore.PendingMutation>):Boolean{
        if(ServiceFaultInjection.googleDisabled(app))return false
        val pending=items.filter{it.status!="OFFLINE_PROVISIONAL"}
        if(pending.isEmpty())return true
        val gasToken=app.getSharedPreferences(AUTH_PREFS,Context.MODE_PRIVATE).getString(AUTH_TOKEN,null).orEmpty()
        if(gasToken.isBlank())return false
        val events=JSONArray()
        pending.forEach{item->
            val env=item.body.optJSONObject("event_envelope")?:canonicalEnvelope(item.body.optString("action"),item.eventId,item.body.optString("business_date").ifBlank{store.businessDate()},sanitizeBusinessPayload(item.body.optJSONObject("payload")?:JSONObject()))
            events.put(env)
        }
        val req=JSONObject().put("action","emergency_ledger_capture").put("events",events).put("_token",gasToken)
            .put("_device_id",M2DeviceIdentity.id(app)).put("_app_version",BuildConfig.VERSION_NAME).put("_app_channel",BuildConfig.CHANNEL).put("_environment_id",BuildConfig.ENVIRONMENT_ID).put("_service_audience",BuildConfig.SERVICE_AUDIENCE)
        val r=httpJson(BuildConfig.GSHEET_API_URL,req,null,requireServiceHost=false)
        if(!r.ok)return false
        val captured=r.json?.optJSONArray("captured")?:JSONArray()
        val capturedIds=HashSet<String>()
        for(i in 0 until captured.length())captured.optJSONObject(i)?.optString("event_id")?.takeIf{it.isNotBlank()}?.let{capturedIds.add(it)}
        pending.filter{it.eventId in capturedIds}.forEach{store.markEmergencyCaptured(it.eventId)}
        return capturedIds.size==pending.size
    }

    private fun finalizeEmergency(items:JSONArray){
        if(items.length()==0||ServiceFaultInjection.googleDisabled(app))return
        val gasToken=app.getSharedPreferences(AUTH_PREFS,Context.MODE_PRIVATE).getString(AUTH_TOKEN,null).orEmpty()
        if(gasToken.isBlank())return
        val req=JSONObject().put("action","emergency_ledger_finalize").put("items",items).put("_token",gasToken)
            .put("_device_id",M2DeviceIdentity.id(app)).put("_app_version",BuildConfig.VERSION_NAME).put("_app_channel",BuildConfig.CHANNEL).put("_environment_id",BuildConfig.ENVIRONMENT_ID).put("_service_audience",BuildConfig.SERVICE_AUDIENCE)
        runCatching{httpJson(BuildConfig.GSHEET_API_URL,req,null,requireServiceHost=false)}
    }

    private fun queuedResult(eventId: String, exclusive: Boolean, projection: String): TransportResult = TransportResult(true, true, 202,
        JSONObject().put("ok", true).put("queued", true).put("reconciliation_state", "LOCAL_PENDING").put("provisional", exclusive)
            .put("projection", projection).put("result", JSONObject().put("event_id", eventId)), null)

    private fun discover(force: Boolean = false): JSONObject? {
        if(ServiceFaultInjection.googleDisabled(app)) return cachedDiscoverySnapshot()
        val now = System.currentTimeMillis()
        if (!force) {
            val cachedAt = prefs.getLong(KEY_DISCOVERY_AT, 0L)
            val cached = cachedDiscoverySnapshot()
            if (cached != null && now - cachedAt < DISCOVERY_TTL_MS) return cached
        }
        if (!hasNetwork()) return cachedDiscoverySnapshot()
        return try {
            val body = JSONObject().put("action", "service_discovery").put("_device_id", M2DeviceIdentity.id(app)).put("_app_version", BuildConfig.VERSION_NAME).put("_app_channel", BuildConfig.CHANNEL).put("_environment_id", BuildConfig.ENVIRONMENT_ID).put("_service_audience", BuildConfig.SERVICE_AUDIENCE)
            val r = httpJson(BuildConfig.GSHEET_API_URL, body, null, requireServiceHost = false)
            if (!r.ok || r.json == null) return cachedDiscoverySnapshot()
            val j = r.json
            if (!discoveryMatchesEnvironment(j)) return cachedDiscoverySnapshot()
            prefs.edit().putString(KEY_DISCOVERY_JSON, j.toString()).putLong(KEY_DISCOVERY_AT, now).apply(); j.optJSONObject("authority")?.let(store::saveAuthority); j
        } catch (_: Throwable) { cachedDiscoverySnapshot() }
    }

    private fun hasNetwork(): Boolean { val n = connectivity.activeNetwork ?: return false; val c = connectivity.getNetworkCapabilities(n) ?: return false; return c.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) }
    private fun failureCount(): Int = prefs.getInt(KEY_FAILURES, 0)
    private fun circuitOpen(): Boolean = System.currentTimeMillis() < prefs.getLong(KEY_CIRCUIT_UNTIL, 0L)
    private fun recordFailure() { val failures = failureCount() + 1; val e = prefs.edit().putInt(KEY_FAILURES, failures); if (failures >= FALLBACK_PROBE_FAILURES) e.putLong(KEY_CIRCUIT_UNTIL, System.currentTimeMillis() + CIRCUIT_MS); e.apply() }
    private fun closeCircuit() { prefs.edit().putInt(KEY_FAILURES, 0).putLong(KEY_CIRCUIT_UNTIL, 0L).apply() }
    private fun fallbackProbeDue(): Boolean = System.currentTimeMillis() - prefs.getLong(KEY_LAST_FALLBACK_PROBE_AT, 0L) >= FALLBACK_PROBE_MIN_MS
    private fun noteFallbackProbe() { prefs.edit().putLong(KEY_LAST_FALLBACK_PROBE_AT, System.currentTimeMillis()).apply() }
    private fun retryDelay(attempt: Int): Long = min(15 * 60_000L, 5_000L * (1L shl min(attempt, 8)))

    private data class HttpResult(val ok: Boolean, val code: Int, val json: JSONObject?, val error: String?)
    private fun httpJson(endpoint: String, payload: JSONObject, bearer: String?, requireServiceHost: Boolean = true): HttpResult {
        if(requireServiceHost && ServiceFaultInjection.cloudflareDisabled(app)) return HttpResult(false,-1,null,"TEST_CLOUDFLARE_DISABLED")
        if(!requireServiceHost && ServiceFaultInjection.googleDisabled(app)) return HttpResult(false,-1,null,"TEST_GOOGLE_DISABLED")
        if (requireServiceHost && !validServiceUrl(endpoint.substringBefore("/v1/"))) return HttpResult(false, -1, null, "SERVICE_URL_INVALID")
        var conn: HttpURLConnection? = null
        return try {
            conn = (URL(endpoint).openConnection() as HttpURLConnection).apply { requestMethod = "POST"; connectTimeout = if (requireServiceHost) 1_500 else 3_000; readTimeout = if (requireServiceHost) 3_000 else 8_000; doOutput = true; instanceFollowRedirects = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8"); setRequestProperty("Accept", "application/json"); setRequestProperty("User-Agent", "PickPack1291-M2/${BuildConfig.VERSION_NAME}"); setRequestProperty("X-Pick-Pack-Environment",BuildConfig.ENVIRONMENT_ID); setRequestProperty("X-Pick-Pack-Audience",BuildConfig.SERVICE_AUDIENCE); if (!bearer.isNullOrBlank()) setRequestProperty("Authorization", "Bearer $bearer") }
            conn.outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) }; val code = conn.responseCode; val stream = if (code in 200..299) conn.inputStream else conn.errorStream
            val text = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty(); val j = if (text.isBlank()) JSONObject() else JSONObject(text); val ok = code in 200..299 && j.optBoolean("ok", false)
            val error = if (ok) null else j.optJSONObject("error")?.optString("code")?.takeIf { it.isNotBlank() } ?: j.optString("error", "HTTP_$code"); HttpResult(ok, code, j, error)
        } catch (t: Throwable) { HttpResult(false, -1, null, t.message ?: "NETWORK") } finally { conn?.disconnect() }
    }

    private fun httpGetJson(endpoint:String,bearer:String?):HttpResult{
        if(ServiceFaultInjection.cloudflareDisabled(app))return HttpResult(false,-1,null,"TEST_CLOUDFLARE_DISABLED")
        if(!validServiceUrl(endpoint.substringBefore("/v1/")))return HttpResult(false,-1,null,"SERVICE_URL_INVALID")
        var conn:HttpURLConnection?=null
        return try{
            conn=(URL(endpoint).openConnection() as HttpURLConnection).apply{
                requestMethod="GET";connectTimeout=3_000;readTimeout=5_000;instanceFollowRedirects=true
                setRequestProperty("Accept","application/json");setRequestProperty("User-Agent","PickPack1291-M2/${BuildConfig.VERSION_NAME}");setRequestProperty("X-Pick-Pack-Environment",BuildConfig.ENVIRONMENT_ID);setRequestProperty("X-Pick-Pack-Audience",BuildConfig.SERVICE_AUDIENCE)
                if(!bearer.isNullOrBlank())setRequestProperty("Authorization","Bearer $bearer")
            }
            val code=conn.responseCode;val stream=if(code in 200..299)conn.inputStream else conn.errorStream
            val text=stream?.bufferedReader(Charsets.UTF_8)?.use{it.readText()}.orEmpty();val j=if(text.isBlank())JSONObject() else JSONObject(text)
            val ok=code in 200..299&&j.optBoolean("ok",false);val errObj=j.optJSONObject("error")
            HttpResult(ok,code,j,if(ok)null else errObj?.optString("code")?.takeIf{it.isNotBlank()}?:j.optString("error","HTTP_$code"))
        }finally{conn?.disconnect()}
    }

    private fun validServiceUrl(raw: String): Boolean = ServiceEndpointPolicy.allowed(raw)
    private fun proofForPassword(password: String, saltB64: String, iterations: Int, challenge: String): String { val key = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(PBEKeySpec(password.toCharArray(), b64uDecode(saltB64), iterations, 256)).encoded; val mac = Mac.getInstance("HmacSHA256"); mac.init(SecretKeySpec(key, "HmacSHA256")); return b64u(mac.doFinal(challenge.toByteArray(Charsets.UTF_8))) }
    private fun b64u(bytes: ByteArray): String = Base64.encodeToString(bytes, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)
    private fun b64uDecode(v: String): ByteArray = Base64.decode(v, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)

    companion object {
        private val FLUSH_LOCK=Any() // S44_SESSION_SINGLEFLIGHT_OBSERVABILITY
        private val DEVICE_SEQUENCE_LOCK=Any()
        private const val PREFS = "pp_m2_service_transport"; private const val KEY_SERVICE_TOKEN = "service_token"; private const val KEY_DISCOVERY_JSON = "discovery_json"; private const val KEY_DISCOVERY_AT = "discovery_at"; private const val KEY_FAILURES = "service_failures"; private const val KEY_CIRCUIT_UNTIL = "circuit_until"; private const val KEY_LAST_FALLBACK_PROBE_AT = "fallback_probe_at"; private const val KEY_DEVICE_SEQUENCE = "device_sequence"; private const val AUTH_PREFS = "pick_pack_auth_session_v2"; private const val AUTH_TOKEN = "token"; private const val DISCOVERY_TTL_MS = 10 * 60_000L; private const val CIRCUIT_MS = 15_000L; private const val FALLBACK_PROBE_FAILURES = 3; private const val FALLBACK_PROBE_MIN_MS = 30_000L; val ADMIN_AUDIT_ACTIONS = setOf("staff_upsert","staff_delete","account_upsert","account_status","change_email","change_password"); val OPERATIONAL = setOf("enter", "exit", "resource_change", "labor_start", "labor_finish", "meal_checkin", "meal_status"); val TECHNICAL = setOf("resilience_probe"); val SYNC_ACTIONS = setOf("sync_status", "sync_day", "sync_bootstrap", "service_connections")
        fun resetFaultTestCircuit(context:Context){
            context.applicationContext.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit()
                .putInt(KEY_FAILURES,0).putLong(KEY_CIRCUIT_UNTIL,0L).putLong(KEY_LAST_FALLBACK_PROBE_AT,0L).apply()
        }
    }
}

object M2DeviceIdentity { fun id(context: Context): String { val p=context.getSharedPreferences("pp_m2_device",Context.MODE_PRIVATE);p.getString("id",null)?.let{return it}; val androidId=android.provider.Settings.Secure.getString(context.contentResolver,android.provider.Settings.Secure.ANDROID_ID).orEmpty(); val raw=if(androidId.isNotBlank()&&androidId!="9774d56d682e549c")"android-$androidId" else "install-${java.util.UUID.randomUUID()}"; val digest=MessageDigest.getInstance("SHA-256").digest("PickPack1291|$raw".toByteArray()).joinToString(""){(it.toInt()and 0xff).toString(16).padStart(2,'0')}; return "m2-$digest".also{p.edit().putString("id",it).apply()} } }
