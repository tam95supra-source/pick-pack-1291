package vn.pickpack1291.app.beta

import android.content.Context
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URL

class DocumentServiceClient(context:Context, private val gasTokenProvider:()->String?) {
    data class Result(val ok:Boolean,val code:Int,val json:JSONObject?,val error:String?)
    data class BytesResult(val ok:Boolean,val code:Int,val bytes:ByteArray?,val mimeType:String?,val error:String?)
    private val app=context.applicationContext
    private val transport=M2ServiceTransport(app)

    private fun baseUrl():String?{
        val d=transport.discoverySnapshot()?:return null
        if(d.optString("authority_mode")!="SERVICE_PRIMARY")return null
        return d.optString("service_url").trimEnd('/').takeIf{ServiceEndpointPolicy.allowed(it)}
    }
    private fun bearer(base:String,force:Boolean=false):String?{
        if(!force)M2ServiceSessionManager.current(app)?.takeIf{it.isNotBlank()}?.let{return it}
        return M2ServiceSessionManager.ensure(app,base,gasTokenProvider(),force=true)
    }
    fun get(path:String):Result=request("GET",path,null)
    fun post(path:String,body:JSONObject):Result=request("POST",path,body)

    private fun request(method:String,path:String,body:JSONObject?):Result{
        if(ServiceFaultInjection.cloudflareDisabled(app))return Result(false,-1,null,"TEST_CLOUDFLARE_DISABLED")
        val base=baseUrl()?:return Result(false,503,null,"SERVICE_DISCOVERY_UNAVAILABLE")
        fun run(token:String):Result{
            var conn:HttpURLConnection?=null
            return try{
                conn=(URL(base+path).openConnection() as HttpURLConnection).apply{
                    requestMethod=method;connectTimeout=7_000;readTimeout=18_000;instanceFollowRedirects=true
                    setRequestProperty("Accept","application/json")
                    setRequestProperty("Authorization","Bearer $token")
                    setRequestProperty("X-Pick-Pack-Environment",BuildConfig.ENVIRONMENT_ID)
                    setRequestProperty("X-Pick-Pack-Audience",BuildConfig.SERVICE_AUDIENCE)
                    setRequestProperty("User-Agent","PickPack1291-Documents/${BuildConfig.VERSION_NAME}")
                    if(body!=null){doOutput=true;setRequestProperty("Content-Type","application/json; charset=utf-8")}
                }
                if(body!=null)conn!!.outputStream.use{it.write(body.toString().toByteArray(Charsets.UTF_8))}
                val code=conn!!.responseCode
                val stream=if(code in 200..299)conn!!.inputStream else conn!!.errorStream
                val text=stream?.bufferedReader(Charsets.UTF_8)?.use{it.readText()}.orEmpty()
                val json=runCatching{if(text.isBlank())JSONObject() else JSONObject(text)}.getOrElse{JSONObject()}
                val ok=code in 200..299&&json.optBoolean("ok",false)
                val error=if(ok)null else json.optJSONObject("error")?.optString("code")?.takeIf{it.isNotBlank()}
                    ?:json.optString("error").takeIf{it.isNotBlank()}?:"HTTP_$code"
                Result(ok,code,json,error)
            }catch(t:Throwable){Result(false,-1,null,t.message?:"NETWORK")}finally{conn?.disconnect()}
        }
        var token=bearer(base)?:return Result(false,401,null,"SERVICE_SESSION_UNAVAILABLE")
        var result=run(token)
        if(result.code==401){
            M2ServiceSessionManager.clearIfSame(app,token)
            token=bearer(base,true)?:return result
            result=run(token)
        }
        return result
    }

    fun uploadToDrive(uploadUrl:String,bytes:ByteArray,mimeType:String):Result{
        val url=runCatching{URL(uploadUrl)}.getOrNull()?:return Result(false,400,null,"UPLOAD_URL_INVALID")
        val host=url.host.lowercase()
        if(url.protocol!="https"||!(host=="www.googleapis.com"||host.endsWith(".googleapis.com")))return Result(false,400,null,"UPLOAD_URL_NOT_GOOGLE")
        var conn:HttpURLConnection?=null
        return try{
            conn=(url.openConnection() as HttpURLConnection).apply{
                requestMethod="PUT";connectTimeout=12_000;readTimeout=60_000;doOutput=true;instanceFollowRedirects=true
                setRequestProperty("Content-Type",mimeType)
                setFixedLengthStreamingMode(bytes.size)
            }
            conn.outputStream.use{it.write(bytes)}
            val code=conn.responseCode
            val stream=if(code in 200..299)conn.inputStream else conn.errorStream
            val text=stream?.bufferedReader(Charsets.UTF_8)?.use{it.readText()}.orEmpty()
            val json=runCatching{if(text.isBlank())JSONObject() else JSONObject(text)}.getOrElse{JSONObject()}
            val ok=code in 200..299&&json.optString("id").isNotBlank()
            Result(ok,code,json,if(ok)null else "DRIVE_UPLOAD_HTTP_$code")
        }catch(t:Throwable){Result(false,-1,null,t.message?:"DRIVE_UPLOAD_NETWORK")}finally{conn?.disconnect()}
    }

    fun getMedia(documentId:String,maxBytes:Int=12*1024*1024):BytesResult{
        val base=baseUrl()?:return BytesResult(false,503,null,null,"SERVICE_DISCOVERY_UNAVAILABLE")
        val id=documentId.trim()
        if(!id.matches(Regex("[0-9a-fA-F-]{16,80}")))return BytesResult(false,400,null,null,"DOCUMENT_ID_INVALID")
        fun run(token:String):BytesResult{
            var conn:HttpURLConnection?=null
            return try{
                conn=(URL("$base/v1/documents/$id/media").openConnection() as HttpURLConnection).apply{
                    requestMethod="GET";connectTimeout=7_000;readTimeout=30_000
                    setRequestProperty("Accept","image/*")
                    setRequestProperty("Authorization","Bearer $token")
                    setRequestProperty("X-Pick-Pack-Environment",BuildConfig.ENVIRONMENT_ID)
                    setRequestProperty("X-Pick-Pack-Audience",BuildConfig.SERVICE_AUDIENCE)
                }
                val code=conn!!.responseCode
                if(code !in 200..299){
                    val text=conn!!.errorStream?.bufferedReader(Charsets.UTF_8)?.use{it.readText()}.orEmpty()
                    val j=runCatching{JSONObject(text)}.getOrNull()
                    return BytesResult(false,code,null,null,j?.optJSONObject("error")?.optString("code")?:"HTTP_$code")
                }
                val expected=conn!!.contentLengthLong
                if(expected>maxBytes)return BytesResult(false,413,null,null,"DOCUMENT_MEDIA_TOO_LARGE")
                val out=ByteArrayOutputStream(if(expected in 1..maxBytes.toLong())expected.toInt() else 256*1024)
                val buf=ByteArray(32*1024);var total=0
                conn!!.inputStream.use{input->
                    while(true){
                        val n=input.read(buf);if(n<0)break
                        total+=n;if(total>maxBytes)return BytesResult(false,413,null,null,"DOCUMENT_MEDIA_TOO_LARGE")
                        out.write(buf,0,n)
                    }
                }
                BytesResult(true,code,out.toByteArray(),conn!!.contentType,null)
            }catch(t:Throwable){BytesResult(false,-1,null,null,t.message?:"NETWORK")}finally{conn?.disconnect()}
        }
        var token=bearer(base)?:return BytesResult(false,401,null,null,"SERVICE_SESSION_UNAVAILABLE")
        var result=run(token)
        if(result.code==401){
            M2ServiceSessionManager.clearIfSame(app,token)
            token=bearer(base,true)?:return result
            result=run(token)
        }
        return result
    }
}
