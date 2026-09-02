package vn.pickpack1291.app.beta

import android.content.Context
import android.os.Build
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * S31D_RUNTIME_BRIDGE_COMPILE_FIX
 * Environment-scoped discovery routing for Service-primary direct actions. Cached discovery is accepted only when it matches the current environment/audience.
 * Device-local provider fault injection blocks that provider; it never promotes authority on its own.
 */
class M2RuntimeBridge(context: Context) {
    private val app = context.applicationContext
    private val prefs = app.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private val transport = M2ServiceTransport(app)

    fun ensureServiceSession(gasToken:String?,force:Boolean=false):Boolean {
        if(ServiceFaultInjection.cloudflareDisabled(app)){recordServicePending("TEST_CLOUDFLARE_DISABLED");return false}
        val d=transport.discoverySnapshot(force=force) ?: return false
        val mode=d.optString("authority_mode");val base=d.optString("service_url").trimEnd('/')
        prefs.edit().putString(KEY_AUTHORITY_MODE,mode).putString(KEY_SERVICE_URL,base).apply()
        if(mode!="SERVICE_PRIMARY"||!validServiceUrl(base))return false
        val token=M2ServiceSessionManager.ensure(app,base,gasToken,force)
        if(!token.isNullOrBlank()){prefs.edit().putString(KEY_LAST_ROUTE,"SERVICE_D1_DIRECT").remove(KEY_LAST_ERROR).apply();return true}
        recordServicePending("SESSION_EXCHANGE_FAILED");return false
    }

    fun directRead(action:String,payload:JSONObject,gasToken:String?):M2ServiceTransport.TransportResult {
        if(action !in DIRECT_READS)return M2ServiceTransport.TransportResult(false,false,0,null,null)
        val discovery=transport.discoverySnapshot() ?: return M2ServiceTransport.TransportResult(true,false,0,null,"DISCOVERY_WARMING")
        val mode=discovery.optString("authority_mode")
        if(ServiceFaultInjection.cloudflareDisabled(app)&&mode!="GOOGLE_FALLBACK"){
            recordServicePending("TEST_CLOUDFLARE_DISABLED")
            return M2ServiceTransport.TransportResult(true,false,-1,null,"TEST_CLOUDFLARE_DISABLED")
        }
        val base=discovery.optString("service_url").trimEnd('/')
        prefs.edit().putString(KEY_AUTHORITY_MODE,mode).putString(KEY_SERVICE_URL,base).apply()
        if(mode=="GOOGLE_FALLBACK")return M2ServiceTransport.TransportResult(false,false,0,null,"FENCED_GOOGLE_FALLBACK")
        if(mode!="SERVICE_PRIMARY"||!validServiceUrl(base))return M2ServiceTransport.TransportResult(true,false,0,null,"AUTHORITY_NOT_SERVICE_PRIMARY")
        if(!ensureServiceSession(gasToken))return M2ServiceTransport.TransportResult(true,false,0,null,"SERVICE_SESSION_UNAVAILABLE")

        fun one():HttpResult{
            val currentBase=transport.cachedDiscoverySnapshot()?.optString("service_url").orEmpty().trimEnd('/').ifBlank{base}
            return httpJson("$currentBase/v1/mobile/read",JSONObject(payload.toString()).put("action",action),prefs.getString(KEY_SERVICE_TOKEN,null))
        }
        return try{
            var response=one()
            if(response.code==401&&ensureServiceSession(gasToken,force=true))response=one()
            if(response.code>=500||response.code==-1){
                recordFallback(response.error?:"SERVICE_READ_${response.code}")
                M2WorkScheduler.schedule(app)
                M2ServiceTransport.TransportResult(true,false,response.code,response.json,response.error)
            }else{
                if(response.code==401)prefs.edit().remove(KEY_SERVICE_TOKEN).apply()
                if(response.ok)recordDirect()
                M2ServiceTransport.TransportResult(true,response.ok,response.code,response.json,response.error)
            }
        }catch(t:Throwable){
            recordFallback(t.message?:"SERVICE_READ_NETWORK")
            M2WorkScheduler.schedule(app)
            M2ServiceTransport.TransportResult(true,false,-1,null,t.message)
        }
    }

    fun recoverAndRetryOperational(action:String,payload:JSONObject,gasToken:String?):M2ServiceTransport.TransportResult?=transport.operational(action,payload)

    fun recoverAndRetrySync(action:String,payload:JSONObject,gasToken:String?):M2ServiceTransport.TransportResult?{
        if(!ensureServiceSession(gasToken,force=true))return M2ServiceTransport.TransportResult(true,false,0,null,"SERVICE_SESSION_UNAVAILABLE")
        val result=transport.sync(action,payload)
        if(result.handled&&result.ok)recordDirect()
        return result
    }

    fun recordDirect(){prefs.edit().putString(KEY_LAST_ROUTE,"SERVICE_D1_DIRECT").remove(KEY_LAST_ERROR).apply()}

    fun recordServicePending(reason:String?=null){
        val edit=prefs.edit().putString(KEY_LAST_ROUTE,"SERVICE_D1_PENDING")
        if(!reason.isNullOrBlank())edit.putString(KEY_LAST_ERROR,reason.take(120))
        edit.apply()
    }

    fun recordFallback(reason:String?=null){
        val mode=transport.cachedDiscoverySnapshot()?.optString("authority_mode").orEmpty().ifBlank{prefs.getString(KEY_AUTHORITY_MODE,"").orEmpty()}
        val cfOff=ServiceFaultInjection.cloudflareDisabled(app);val googleOff=ServiceFaultInjection.googleDisabled(app)
        val route=when{
            cfOff&&googleOff->"OFFLINE"
            cfOff&&!googleOff->"SERVICE_D1_BLOCKED_TEST"
            mode=="GOOGLE_FALLBACK"->"GOOGLE_FALLBACK"
            else->"GOOGLE_RELAY_PENDING"
        }
        val edit=prefs.edit().putString(KEY_LAST_ROUTE,route)
        if(!reason.isNullOrBlank())edit.putString(KEY_LAST_ERROR,reason.take(120))
        edit.apply()
    }

    fun status():JSONObject{
        val discovery=transport.cachedDiscoverySnapshot()
        val mode=discovery?.optString("authority_mode").orEmpty().ifBlank{prefs.getString(KEY_AUTHORITY_MODE,"").orEmpty()}
        val url=discovery?.optString("service_url").orEmpty().ifBlank{prefs.getString(KEY_SERVICE_URL,"").orEmpty()}
        val tokenPresent=!prefs.getString(KEY_SERVICE_TOKEN,null).isNullOrBlank()
        val cfOff=ServiceFaultInjection.cloudflareDisabled(app);val googleOff=ServiceFaultInjection.googleDisabled(app)
        val route=when{
            cfOff&&googleOff->"OFFLINE"
            cfOff&&!googleOff&&mode=="GOOGLE_FALLBACK"->"GOOGLE_FALLBACK"
            cfOff&&!googleOff->"SERVICE_D1_BLOCKED_TEST"
            else->prefs.getString(KEY_LAST_ROUTE,null)?:when{
                mode=="GOOGLE_FALLBACK"->"GOOGLE_FALLBACK"
                mode=="SERVICE_PRIMARY"&&tokenPresent->"SERVICE_D1_DIRECT"
                mode=="SERVICE_PRIMARY"->"SERVICE_D1_PENDING"
                else->"UNRESOLVED"
            }
        }
        val label=when(route){
            "SERVICE_D1_DIRECT"->"Cloudflare / D1"
            "SERVICE_D1_PENDING"->"Cloudflare • chờ đồng bộ"
            "GOOGLE_FALLBACK"->"Google Drive / GSheet trực tiếp"
            "SERVICE_D1_BLOCKED_TEST"->"Cloudflare / D1 • đang mô phỏng mất dịch vụ"
            "GOOGLE_RELAY_PENDING"->"Google/GAS dự phòng"
            "OFFLINE"->"OFFLINE"
            else->"Đang xác định"
        }
        val provider=when(route){
            "GOOGLE_FALLBACK"->"Google Drive"
            "GOOGLE_RELAY_PENDING"->"Google/GAS"
            "SERVICE_D1_BLOCKED_TEST"->"Cloudflare"
            "OFFLINE"->"OFFLINE"
            else->if(url.isNotBlank())"Cloudflare" else "—"
        }
        return JSONObject().put("authority_mode",mode).put("service_url",url).put("service_session",tokenPresent).put("route",route).put("label",label).put("provider",provider).put("last_error",prefs.getString(KEY_LAST_ERROR,"").orEmpty()).put("test_mode",ServiceFaultInjection.mode(app).stored)
    }

    fun clear(){prefs.edit().remove(KEY_SERVICE_TOKEN).remove(KEY_LAST_ROUTE).remove(KEY_LAST_ERROR).apply()}

    private data class HttpResult(val ok:Boolean,val code:Int,val json:JSONObject?,val error:String?)

    private fun httpJson(endpoint:String,payload:JSONObject,bearer:String?):HttpResult{
        if(ServiceFaultInjection.cloudflareDisabled(app))return HttpResult(false,-1,null,"TEST_CLOUDFLARE_DISABLED")
        var connection:HttpURLConnection?=null
        return try{
            connection=(URL(endpoint).openConnection() as HttpURLConnection).apply{
                requestMethod="POST";connectTimeout=1_500;readTimeout=3_000;doOutput=true;instanceFollowRedirects=true
                setRequestProperty("Content-Type","application/json; charset=utf-8");setRequestProperty("Accept","application/json");setRequestProperty("User-Agent","PickPack1291-M2Runtime/${BuildConfig.VERSION_NAME}");setRequestProperty("X-Pick-Pack-Environment",BuildConfig.ENVIRONMENT_ID);setRequestProperty("X-Pick-Pack-Audience",BuildConfig.SERVICE_AUDIENCE)
                if(!bearer.isNullOrBlank())setRequestProperty("Authorization","Bearer $bearer")
            }
            val requestBytes=payload.toString().toByteArray(Charsets.UTF_8);SyncDirectionTracker.recordUploadBytes(requestBytes.size.toLong());connection.outputStream.use{it.write(requestBytes)}
            val code=connection.responseCode;val stream=if(code in 200..299)connection.inputStream else connection.errorStream;val text=stream?.bufferedReader(Charsets.UTF_8)?.use{it.readText()}.orEmpty();SyncDirectionTracker.recordDownloadBytes(text.toByteArray(Charsets.UTF_8).size.toLong())
            val json=if(text.isBlank())JSONObject() else JSONObject(text);val ok=code in 200..299&&json.optBoolean("ok",false);val error=if(ok)null else json.optJSONObject("error")?.optString("code")?.takeIf{it.isNotBlank()}?:json.optString("error","HTTP_$code")
            HttpResult(ok,code,json,error)
        }catch(t:Throwable){HttpResult(false,-1,null,t.message?:"NETWORK")}finally{connection?.disconnect()}
    }

    private fun validServiceUrl(raw:String):Boolean=ServiceEndpointPolicy.allowed(raw)

    companion object{
        private const val PREFS="pp_m2_service_transport"
        private const val KEY_SERVICE_TOKEN="service_token"
        private const val KEY_AUTHORITY_MODE="runtime_authority_mode"
        private const val KEY_SERVICE_URL="runtime_service_url"
        private const val KEY_LAST_ROUTE="runtime_last_route"
        private const val KEY_LAST_ERROR="runtime_last_error"
        val DIRECT_READS=setOf(
            "employee_context","master_options","history_shared","old_active_sessions","historical_session_detail",
            "outbound_location_list","outbound_location_mutate","outbound_drop_append","outbound_drop_clear","meal_attendance_list","labor_list"
        )
    }
}
