package vn.pickpack1291.app.beta

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.util.UUID

class DocumentDraftStore(context:Context){
    data class Draft(
        val ownerLogin:String,
        val sourceKind:String,
        val capturedAt:String,
        val idempotencyKey:String,
        val image:DocumentImageProcessor.ProcessedImage,
        val note:String,
        val updatedAt:Long
    )

    private val root=File(context.filesDir,"document-draft-v1").apply{mkdirs()}

    /** Backward-compatible single-draft replace. */
    fun save(ownerLogin:String,sourceKind:String,capturedAt:String,idempotencyKey:String,image:DocumentImageProcessor.ProcessedImage,note:String=""):Draft=synchronized(lock){
        remove(ownerLogin)
        appendUnlocked(ownerLogin,sourceKind,capturedAt,idempotencyKey,image,note)
    }

    /** Durable append used by Beta110 multi-image selection. */
    fun append(ownerLogin:String,sourceKind:String,capturedAt:String,idempotencyKey:String,image:DocumentImageProcessor.ProcessedImage,note:String=""):Draft=synchronized(lock){
        val existing=loadAllUnlocked(ownerLogin)
        existing.firstOrNull{it.idempotencyKey==idempotencyKey}?.let{return it}
        appendUnlocked(ownerLogin,sourceKind,capturedAt,idempotencyKey,image,note)
    }

    fun load(ownerLogin:String):Draft?=synchronized(lock){loadAllUnlocked(ownerLogin).firstOrNull()}
    fun loadAll(ownerLogin:String):List<Draft> = synchronized(lock){loadAllUnlocked(ownerLogin)}
    fun remove(ownerLogin:String)=synchronized(lock){accountDir(ownerLogin,false)?.deleteRecursively()}
    fun removeItems(ownerLogin:String,keys:Set<String>)=synchronized(lock){
        val account=accountDir(ownerLogin,false)?:return@synchronized
        val ids=manifestIds(account);val keep=mutableListOf<String>()
        for(id in ids){
            val meta=runCatching{JSONObject(File(account,"$id.json").readText(Charsets.UTF_8))}.getOrNull()
            if(meta?.optString("idempotency_key") in keys){File(account,"$id.json").delete();File(account,"$id.jpg").delete()} else keep.add(id)
        }
        writeManifest(account,keep)
    }
    fun updateNote(ownerLogin:String,key:String,note:String)=synchronized(lock){
        val account=accountDir(ownerLogin,false)?:return@synchronized
        for(id in manifestIds(account)){
            val file=File(account,"$id.json");val j=runCatching{JSONObject(file.readText(Charsets.UTF_8))}.getOrNull()?:continue
            if(j.optString("idempotency_key")==key){j.put("note",note.trim().take(240)).put("updated_at",System.currentTimeMillis());file.writeText(j.toString(),Charsets.UTF_8);break}
        }
    }

    private fun appendUnlocked(ownerLogin:String,sourceKind:String,capturedAt:String,idempotencyKey:String,image:DocumentImageProcessor.ProcessedImage,note:String=""):Draft{
        val account=accountDir(ownerLogin)?:throw IllegalStateException("DOCUMENT_DRAFT_DIR_UNAVAILABLE")
        cleanupTemps(account)
        val existingIds=manifestIds(account).toMutableList()
        if(existingIds.size>=MAX_ITEMS)throw IllegalStateException("DOCUMENT_DRAFT_ITEM_LIMIT")
        val existingBytes=existingIds.sumOf{generation->
            runCatching{JSONObject(File(account,"$generation.json").readText(Charsets.UTF_8)).optLong("byte_size",0L)}.getOrDefault(0L)
        }
        if(existingBytes+image.bytes.size>MAX_BYTES)throw IllegalStateException("DOCUMENT_DRAFT_STORAGE_LIMIT")
        val generation=UUID.randomUUID().toString()
        val bytesTmp=File(account,"$generation.jpg.tmp")
        val bytesFile=File(account,"$generation.jpg")
        bytesTmp.outputStream().use{out->out.write(image.bytes);runCatching{out.fd.sync()}}
        try{atomicReplace(bytesTmp,bytesFile)}catch(t:Throwable){bytesTmp.delete();throw IllegalStateException("DOCUMENT_DRAFT_BYTES_COMMIT_FAILED",t)}
        val now=System.currentTimeMillis()
        val meta=JSONObject()
            .put("owner_login",ownerLogin.trim()).put("source_kind",sourceKind).put("captured_at",capturedAt)
            .put("idempotency_key",idempotencyKey).put("sha256",image.sha256).put("md5",image.md5)
            .put("dhash64",image.dhash64).put("dhash64_variants",JSONArray(image.dhash64Variants))
            .put("width",image.width).put("height",image.height).put("mime_type",image.mimeType)
            .put("byte_size",image.bytes.size).put("note",note.trim().take(240)).put("updated_at",now)
        val metaTmp=File(account,"$generation.json.tmp")
        val metaFile=File(account,"$generation.json")
        metaTmp.writeText(meta.toString(),Charsets.UTF_8)
        try{atomicReplace(metaTmp,metaFile)}catch(t:Throwable){bytesFile.delete();metaTmp.delete();throw IllegalStateException("DOCUMENT_DRAFT_META_COMMIT_FAILED",t)}
        try{
            existingIds.add(generation)
            writeManifest(account,existingIds)
        }catch(t:Throwable){
            bytesFile.delete();metaFile.delete();throw t
        }
        return Draft(ownerLogin.trim(),sourceKind,capturedAt,idempotencyKey,image,note.trim().take(240),now)
    }

    private fun loadAllUnlocked(ownerLogin:String):List<Draft>{
        val account=accountDir(ownerLogin,false)?:return emptyList()
        cleanupTemps(account)
        val ids=manifestIds(account)
        val out=mutableListOf<Draft>()
        for(generation in ids){
            val metaFile=File(account,"$generation.json")
            val bytesFile=File(account,"$generation.jpg")
            if(!metaFile.isFile||!bytesFile.isFile)continue
            val draft=runCatching{
                val j=JSONObject(metaFile.readText(Charsets.UTF_8))
                val owner=j.getString("owner_login")
                if(owner!=ownerLogin.trim())return@runCatching null
                val bytes=bytesFile.readBytes()
                if(bytes.size!=j.getInt("byte_size"))return@runCatching null
                val sha=digest("SHA-256",bytes)
                if(sha!=j.getString("sha256"))return@runCatching null
                val arr=j.optJSONArray("dhash64_variants");val variants=mutableListOf<String>()
                if(arr!=null)for(i in 0 until arr.length())arr.optString(i).takeIf{it.matches(Regex("[0-9a-fA-F]{16}"))}?.lowercase()?.let(variants::add)
                val primary=j.getString("dhash64").lowercase();if(variants.isEmpty())variants.add(primary)
                Draft(
                    ownerLogin=owner,sourceKind=j.getString("source_kind"),capturedAt=j.getString("captured_at"),
                    idempotencyKey=j.getString("idempotency_key"),
                    image=DocumentImageProcessor.ProcessedImage(
                        bytes=bytes,sha256=sha,md5=j.getString("md5"),dhash64=primary,
                        dhash64Variants=variants.distinct().take(4),width=j.getInt("width"),height=j.getInt("height"),
                        mimeType=j.optString("mime_type","image/jpeg")
                    ),note=j.optString("note"),updatedAt=j.getLong("updated_at")
                )
            }.getOrNull()
            if(draft!=null)out.add(draft)
        }
        return out.sortedBy{it.updatedAt}
    }

    private fun manifestIds(account:File):List<String>{
        val manifest=File(account,"manifest.json")
        if(manifest.isFile){
            return runCatching{
                val a=JSONObject(manifest.readText(Charsets.UTF_8)).optJSONArray("generations")?:JSONArray()
                (0 until a.length()).mapNotNull{a.optString(it).takeIf{x->x.matches(Regex("[0-9a-fA-F-]{16,80}"))}}.distinct()
            }.getOrDefault(emptyList())
        }
        // One-time compatibility with Beta108 single pointer.
        val legacy=File(account,"current").takeIf{it.isFile}?.readText(Charsets.UTF_8)?.trim().orEmpty()
        if(legacy.isNotBlank()){
            runCatching{writeManifest(account,listOf(legacy))}
            return listOf(legacy)
        }
        return emptyList()
    }

    private fun writeManifest(account:File,ids:List<String>){
        val tmp=File(account,"manifest.json.tmp")
        val target=File(account,"manifest.json")
        tmp.writeText(JSONObject().put("generations",JSONArray(ids)).toString(),Charsets.UTF_8)
        runCatching{FileOutputStream(tmp,true).use{it.fd.sync()}}
        try{atomicReplace(tmp,target)}catch(t:Throwable){tmp.delete();throw IllegalStateException("DOCUMENT_DRAFT_MANIFEST_COMMIT_FAILED",t)}
    }

    private fun atomicReplace(source:File,target:File){
        try{
            Files.move(source.toPath(),target.toPath(),StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE)
        }catch(_:Throwable){
            Files.move(source.toPath(),target.toPath(),StandardCopyOption.REPLACE_EXISTING)
        }
    }
    private fun accountDir(ownerLogin:String,create:Boolean=true):File?{
        val key=digest("SHA-256",ownerLogin.trim().lowercase().toByteArray(Charsets.UTF_8)).take(24)
        val dir=File(root,key);if(create)dir.mkdirs();return dir.takeIf{it.isDirectory}
    }
    private fun cleanupTemps(dir:File){
        val cutoff=System.currentTimeMillis()-24*60*60*1000L
        dir.listFiles()?.filter{it.name.endsWith(".tmp")&&it.lastModified()<cutoff}?.forEach{it.delete()}
    }
    private fun digest(algorithm:String,bytes:ByteArray)=MessageDigest.getInstance(algorithm).digest(bytes)
        .joinToString(""){(it.toInt() and 0xff).toString(16).padStart(2,'0')}

    companion object{
        private val lock=Any()
        const val MAX_ITEMS=60
        const val MAX_BYTES=120L*1024L*1024L
    }
}
