package vn.pickpack1291.app.beta

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

class DocumentUploadEngine(context:Context, private val api:BetaApiClient) {
    // Beta108 final Android gate marker: durable queue bytes, account-scoped retry and persisted Drive completion state are APK source.
    enum class Status{SUCCESS,EXACT_DUPLICATE_RESOLVED,SIMILAR_REVIEW_REQUIRED,RETRY,BLOCKED,ACCOUNT_MISMATCH}
    data class Outcome(val status:Status,val code:String?,val documentId:String?)

    private val app=context.applicationContext
    private val client=DocumentServiceClient(app){api.token}
    private val store=DocumentPendingStore(app)
    private val cache=DocumentMediaCache(app)

    fun runOne(input:DocumentPendingStore.Item):Outcome=synchronized(uploadLock){
        var item=store.find(input.pendingId)?:return Outcome(Status.SUCCESS,"ALREADY_REMOVED",input.documentId)
        val currentLogin=api.restoredAccount()?.optString("login_id").orEmpty()
        if(currentLogin.isBlank()||currentLogin!=item.ownerLogin){
            return Outcome(Status.ACCOUNT_MISMATCH,"DOCUMENT_PENDING_ACCOUNT_MISMATCH",item.documentId)
        }
        val bytes=runCatching{store.bytes(item)}.getOrElse{
            store.update(item,lastError="DOCUMENT_PENDING_BYTES_MISSING",incrementRetry=true)
            return Outcome(Status.BLOCKED,"DOCUMENT_PENDING_BYTES_MISSING",item.documentId)
        }

        if(!item.documentId.isNullOrBlank()&&!item.driveFileId.isNullOrBlank()){
            val complete=client.post("/v1/documents/complete",JSONObject()
                .put("document_id",item.documentId)
                .put("drive_file_id",item.driveFileId))
            if(complete.ok){
                val id=complete.json?.optJSONObject("document")?.optString("document_id").orEmpty().ifBlank{item.documentId!!}
                cache.put(id,bytes);store.remove(item.pendingId)
                return Outcome(Status.SUCCESS,null,id)
            }
            if(complete.error=="DOCUMENT_ALREADY_COMPLETE_CONFLICT"||complete.error=="DOCUMENT_DRIVE_VERIFY_FAILED"){
                store.update(item,lastError=complete.error,incrementRetry=true)
                return Outcome(Status.BLOCKED,complete.error,item.documentId)
            }
            item=store.update(item,lastError=complete.error?:"DOCUMENT_COMPLETE_RETRY",incrementRetry=true)
            return Outcome(Status.RETRY,complete.error,item.documentId)
        }

        val payload=JSONObject()
            .put("category_id",item.categoryId).put("mime_type",item.mimeType).put("byte_size",item.byteSize)
            .put("sha256",item.sha256).put("md5",item.md5).put("dhash64",item.dhash64)
            .put("dhash64_variants",JSONArray(item.dhash64Variants))
            .put("width",item.width).put("height",item.height).put("source_kind",item.sourceKind)
            .put("captured_at",item.capturedAt).put("idempotency_key",item.idempotencyKey).put("allow_similar",item.allowSimilar)
            .put("group_id",item.groupId).put("group_mode",item.groupMode).put("page_index",item.pageIndex).put("page_count",item.pageCount).put("note",item.note)
        val session=client.post("/v1/documents/upload-session",payload)
        if(!session.ok){
            return when(session.error){
                "DOCUMENT_EXACT_DUPLICATE"->{
                    store.remove(item.pendingId)
                    Outcome(Status.EXACT_DUPLICATE_RESOLVED,session.error,item.documentId)
                }
                "DOCUMENT_SIMILAR_IMAGE"->{
                    store.update(item,lastError=session.error)
                    Outcome(Status.SIMILAR_REVIEW_REQUIRED,session.error,item.documentId)
                }
                "DOCUMENT_CATEGORY_NOT_FOUND","DOCUMENT_IDEMPOTENCY_CONFLICT"->{
                    store.update(item,lastError=session.error,incrementRetry=true)
                    Outcome(Status.BLOCKED,session.error,item.documentId)
                }
                else->{
                    store.update(item,lastError=session.error?:"DOCUMENT_UPLOAD_SESSION_RETRY",incrementRetry=true)
                    Outcome(Status.RETRY,session.error,item.documentId)
                }
            }
        }
        if(session.json?.optBoolean("already_complete",false)==true){
            val id=session.json.optJSONObject("document")?.optString("document_id").orEmpty().ifBlank{item.documentId.orEmpty()}
            if(id.isNotBlank())cache.put(id,bytes)
            store.remove(item.pendingId)
            return Outcome(Status.SUCCESS,null,id.takeIf{it.isNotBlank()})
        }
        val doc=session.json?.optJSONObject("document")
        val documentId=doc?.optString("document_id").orEmpty()
        val uploadUrl=session.json?.optString("upload_url").orEmpty()
        if(documentId.isBlank()||uploadUrl.isBlank()){
            store.update(item,lastError="DOCUMENT_UPLOAD_SESSION_INVALID",incrementRetry=true)
            return Outcome(Status.RETRY,"DOCUMENT_UPLOAD_SESSION_INVALID",item.documentId)
        }
        item=store.update(item,documentId=documentId,lastError=null)
        val drive=client.uploadToDrive(uploadUrl,bytes,item.mimeType)
        val driveId=drive.json?.optString("id").orEmpty()
        if(!drive.ok||driveId.isBlank()){
            store.update(item,lastError=drive.error?:"DRIVE_UPLOAD_RETRY",incrementRetry=true)
            return Outcome(Status.RETRY,drive.error,documentId)
        }
        item=store.update(item,driveFileId=driveId,lastError=null)
        val complete=client.post("/v1/documents/complete",JSONObject().put("document_id",documentId).put("drive_file_id",driveId))
        if(!complete.ok){
            store.update(item,lastError=complete.error?:"DOCUMENT_COMPLETE_RETRY",incrementRetry=true)
            return Outcome(Status.RETRY,complete.error,documentId)
        }
        cache.put(documentId,bytes)
        store.remove(item.pendingId)
        return Outcome(Status.SUCCESS,null,documentId)
    }

    fun allowSimilarAndRetry(pendingId:String):Outcome{
        val item=store.find(pendingId)?:return Outcome(Status.SUCCESS,"ALREADY_REMOVED",null)
        val allowed=store.update(item,allowSimilar=true,lastError=null)
        return runOne(allowed)
    }

    companion object{private val uploadLock=Any()}
}
