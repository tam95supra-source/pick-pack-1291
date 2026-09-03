package vn.pickpack1291.app.beta

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

class DocumentPendingStore(context:Context) {
    data class Item(
        val pendingId:String,
        val ownerLogin:String,
        val categoryId:String,
        val sourceKind:String,
        val capturedAt:String,
        val idempotencyKey:String,
        val sha256:String,
        val md5:String,
        val dhash64:String,
        val dhash64Variants:List<String>,
        val width:Int,
        val height:Int,
        val mimeType:String,
        val byteSize:Int,
        val createdAt:Long,
        val updatedAt:Long,
        val documentId:String?,
        val driveFileId:String?,
        val allowSimilar:Boolean,
        val lastError:String?,
        val retryCount:Int,
        val groupId:String,
        val groupMode:String,
        val pageIndex:Int,
        val pageCount:Int,
        val note:String
    )
    class CapacityException(message:String):IllegalStateException(message)

    private val dir=File(context.filesDir,"document-pending-v1").apply{mkdirs()}

    fun enqueue(
        ownerLogin:String,
        categoryId:String,
        sourceKind:String,
        capturedAt:String,
        idempotencyKey:String,
        image:DocumentImageProcessor.ProcessedImage,
        groupId:String=idempotencyKey,
        groupMode:String="SINGLE",
        pageIndex:Int=1,
        pageCount:Int=1,
        note:String=""
    ):Item=synchronized(lock){
        listUnlocked().firstOrNull{it.idempotencyKey==idempotencyKey}?.let{return it}
        val current=listUnlocked()
        val total=current.sumOf{it.byteSize.toLong()}
        if(current.size>=MAX_ITEMS)throw CapacityException("DOCUMENT_PENDING_ITEM_LIMIT")
        if(total+image.bytes.size>MAX_BYTES)throw CapacityException("DOCUMENT_PENDING_STORAGE_LIMIT")
        val id=UUID.randomUUID().toString()
        val bytesFile=bytesFile(id)
        val temp=File(dir,id+".jpg.tmp")
        temp.outputStream().use{out->out.write(image.bytes);runCatching{out.fd.sync()}}
        if(!temp.renameTo(bytesFile)){temp.delete();throw IllegalStateException("DOCUMENT_PENDING_BYTES_COMMIT_FAILED")}
        val now=System.currentTimeMillis()
        val item=Item(
            pendingId=id,ownerLogin=ownerLogin.trim(),categoryId=categoryId,sourceKind=sourceKind,
            capturedAt=capturedAt,idempotencyKey=idempotencyKey,sha256=image.sha256,md5=image.md5,
            dhash64=image.dhash64,dhash64Variants=image.dhash64Variants,width=image.width,height=image.height,mimeType=image.mimeType,
            byteSize=image.bytes.size,createdAt=now,updatedAt=now,documentId=null,driveFileId=null,
            allowSimilar=false,lastError=null,retryCount=0,
            groupId=groupId.trim().ifBlank{idempotencyKey},groupMode=groupMode.trim().uppercase().ifBlank{"SINGLE"},
            pageIndex=pageIndex.coerceAtLeast(1),pageCount=pageCount.coerceAtLeast(1),note=note.trim().take(240)
        )
        try{writeMeta(item)}catch(t:Throwable){bytesFile.delete();throw t}
        item
    }

    fun list():List<Item> = synchronized(lock){listUnlocked()}
    fun count():Int=synchronized(lock){listUnlocked().size}
    fun totalBytes():Long=synchronized(lock){listUnlocked().sumOf{it.byteSize.toLong()}}
    fun find(pendingId:String):Item?=synchronized(lock){readMeta(metaFile(pendingId))}
    fun bytes(item:Item):ByteArray=synchronized(lock){
        val f=bytesFile(item.pendingId)
        if(!f.isFile)throw IllegalStateException("DOCUMENT_PENDING_BYTES_MISSING")
        val b=f.readBytes()
        if(b.size!=item.byteSize)throw IllegalStateException("DOCUMENT_PENDING_BYTES_SIZE_MISMATCH")
        b
    }
    fun update(
        item:Item,
        documentId:String?=item.documentId,
        driveFileId:String?=item.driveFileId,
        allowSimilar:Boolean=item.allowSimilar,
        lastError:String?=item.lastError,
        incrementRetry:Boolean=false
    ):Item=synchronized(lock){
        val latest=readMeta(metaFile(item.pendingId))?:item
        val next=latest.copy(
            documentId=documentId,
            driveFileId=driveFileId,
            allowSimilar=allowSimilar,
            lastError=lastError,
            retryCount=latest.retryCount+(if(incrementRetry)1 else 0),
            updatedAt=System.currentTimeMillis()
        )
        writeMeta(next);next
    }
    fun remove(pendingId:String)=synchronized(lock){
        metaFile(pendingId).delete()
        bytesFile(pendingId).delete()
    }

    private fun listUnlocked():List<Item>{
        cleanupTemps()
        return dir.listFiles()?.asSequence()
            ?.filter{it.isFile&&it.name.endsWith(".json")}
            ?.mapNotNull{readMeta(it)}
            ?.sortedBy{it.createdAt}
            ?.toList().orEmpty()
    }
    private fun metaFile(id:String)=File(dir,id+".json")
    private fun bytesFile(id:String)=File(dir,id+".jpg")
    private fun writeMeta(item:Item){
        val f=metaFile(item.pendingId)
        val tmp=File(dir,item.pendingId+".json.tmp")
        tmp.writeText(toJson(item).toString(),Charsets.UTF_8)
        if(!tmp.renameTo(f)){tmp.delete();throw IllegalStateException("DOCUMENT_PENDING_META_COMMIT_FAILED")}
    }
    private fun readMeta(f:File):Item?=runCatching{
        val j=JSONObject(f.readText(Charsets.UTF_8))
        Item(
            pendingId=j.getString("pending_id"),ownerLogin=j.getString("owner_login"),
            categoryId=j.getString("category_id"),sourceKind=j.getString("source_kind"),
            capturedAt=j.getString("captured_at"),idempotencyKey=j.getString("idempotency_key"),
            sha256=j.getString("sha256"),md5=j.getString("md5"),dhash64=j.optString("dhash64"),
            dhash64Variants=run{
                val a=j.optJSONArray("dhash64_variants")
                val out=mutableListOf<String>()
                if(a!=null)for(k in 0 until a.length())a.optString(k).takeIf{it.matches(Regex("[0-9a-fA-F]{16}"))}?.lowercase()?.let(out::add)
                if(out.isEmpty()&&j.optString("dhash64").isNotBlank())out.add(j.optString("dhash64").lowercase())
                out.distinct().take(4)
            },
            width=j.getInt("width"),height=j.getInt("height"),mimeType=j.getString("mime_type"),
            byteSize=j.getInt("byte_size"),createdAt=j.getLong("created_at"),updatedAt=j.getLong("updated_at"),
            documentId=j.optString("document_id").takeIf{it.isNotBlank()},
            driveFileId=j.optString("drive_file_id").takeIf{it.isNotBlank()},
            allowSimilar=j.optBoolean("allow_similar",false),lastError=j.optString("last_error").takeIf{it.isNotBlank()},
            retryCount=j.optInt("retry_count",0),
            groupId=j.optString("group_id").ifBlank{j.getString("idempotency_key")},
            groupMode=j.optString("group_mode","SINGLE").ifBlank{"SINGLE"},
            pageIndex=j.optInt("page_index",1).coerceAtLeast(1),
            pageCount=j.optInt("page_count",1).coerceAtLeast(1),note=j.optString("note")
        )
    }.getOrNull()
    private fun toJson(i:Item)=JSONObject()
        .put("pending_id",i.pendingId).put("owner_login",i.ownerLogin).put("category_id",i.categoryId)
        .put("source_kind",i.sourceKind).put("captured_at",i.capturedAt).put("idempotency_key",i.idempotencyKey)
        .put("sha256",i.sha256).put("md5",i.md5).put("dhash64",i.dhash64).put("dhash64_variants",JSONArray(i.dhash64Variants)).put("width",i.width).put("height",i.height)
        .put("mime_type",i.mimeType).put("byte_size",i.byteSize).put("created_at",i.createdAt).put("updated_at",i.updatedAt)
        .put("document_id",i.documentId?:"").put("drive_file_id",i.driveFileId?:"").put("allow_similar",i.allowSimilar)
        .put("last_error",i.lastError?:"").put("retry_count",i.retryCount)
        .put("group_id",i.groupId).put("group_mode",i.groupMode).put("page_index",i.pageIndex).put("page_count",i.pageCount).put("note",i.note)
    private fun cleanupTemps(){
        val cutoff=System.currentTimeMillis()-24*60*60*1000L
        dir.listFiles()?.filter{it.name.endsWith(".tmp")&&it.lastModified()<cutoff}?.forEach{it.delete()}
    }

    companion object{
        private val lock=Any()
        const val MAX_ITEMS=60
        const val MAX_BYTES=120L*1024L*1024L
    }
}
