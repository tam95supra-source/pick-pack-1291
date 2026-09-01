package vn.pickpack1291.app.beta

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest
import java.util.UUID

class DocumentDraftStore(context:Context){
    data class Draft(
        val ownerLogin:String,
        val sourceKind:String,
        val capturedAt:String,
        val idempotencyKey:String,
        val image:DocumentImageProcessor.ProcessedImage,
        val updatedAt:Long
    )

    private val root=File(context.filesDir,"document-draft-v1").apply{mkdirs()}

    fun save(ownerLogin:String,sourceKind:String,capturedAt:String,idempotencyKey:String,image:DocumentImageProcessor.ProcessedImage):Draft=synchronized(lock){
        val account=accountDir(ownerLogin)?:throw IllegalStateException("DOCUMENT_DRAFT_DIR_UNAVAILABLE")
        val generation=UUID.randomUUID().toString()
        val bytesTmp=File(account,"$generation.jpg.tmp")
        val bytesFile=File(account,"$generation.jpg")
        bytesTmp.outputStream().use{out->out.write(image.bytes);runCatching{out.fd.sync()}}
        if(!bytesTmp.renameTo(bytesFile)){bytesTmp.delete();throw IllegalStateException("DOCUMENT_DRAFT_BYTES_COMMIT_FAILED")}
        val now=System.currentTimeMillis()
        val meta=JSONObject()
            .put("owner_login",ownerLogin.trim()).put("source_kind",sourceKind).put("captured_at",capturedAt)
            .put("idempotency_key",idempotencyKey).put("sha256",image.sha256).put("md5",image.md5)
            .put("dhash64",image.dhash64).put("dhash64_variants",JSONArray(image.dhash64Variants))
            .put("width",image.width).put("height",image.height).put("mime_type",image.mimeType)
            .put("byte_size",image.bytes.size).put("updated_at",now)
        val metaTmp=File(account,"$generation.json.tmp")
        val metaFile=File(account,"$generation.json")
        metaTmp.writeText(meta.toString(),Charsets.UTF_8)
        if(!metaTmp.renameTo(metaFile)){bytesFile.delete();metaTmp.delete();throw IllegalStateException("DOCUMENT_DRAFT_META_COMMIT_FAILED")}
        val pointerTmp=File(account,"current.tmp")
        pointerTmp.writeText(generation,Charsets.UTF_8)
        runCatching{FileOutputStream(pointerTmp,true).use{it.fd.sync()}}
        val pointer=File(account,"current")
        val previous=pointer.takeIf{it.isFile}?.readText(Charsets.UTF_8)?.trim().orEmpty()
        if(pointer.exists())pointer.delete()
        if(!pointerTmp.renameTo(pointer)){pointerTmp.delete();bytesFile.delete();metaFile.delete();throw IllegalStateException("DOCUMENT_DRAFT_POINTER_COMMIT_FAILED")}
        account.listFiles()?.filter{file->
            val name=file.name
            name!="current"&&!name.startsWith(generation+".")&&!name.endsWith(".tmp")&&(previous.isBlank()||!name.startsWith(previous+"."))
        }?.forEach{it.delete()}
        if(previous.isNotBlank()&&previous!=generation){
            File(account,"$previous.jpg").delete()
            File(account,"$previous.json").delete()
        }
        Draft(ownerLogin.trim(),sourceKind,capturedAt,idempotencyKey,image,now)
    }

    fun load(ownerLogin:String):Draft?=synchronized(lock){
        val account=accountDir(ownerLogin,false)?:return null
        cleanupTemps(account)
        val generation=File(account,"current").takeIf{it.isFile}?.readText(Charsets.UTF_8)?.trim().orEmpty()
        if(generation.isBlank())return null
        val metaFile=File(account,"$generation.json")
        val bytesFile=File(account,"$generation.jpg")
        if(!metaFile.isFile||!bytesFile.isFile)return null
        runCatching{
            val j=JSONObject(metaFile.readText(Charsets.UTF_8))
            val owner=j.getString("owner_login")
            if(owner!=ownerLogin.trim())return null
            val bytes=bytesFile.readBytes()
            if(bytes.size!=j.getInt("byte_size"))return null
            val sha=digest("SHA-256",bytes)
            if(sha!=j.getString("sha256"))return null
            val arr=j.optJSONArray("dhash64_variants")
            val variants=mutableListOf<String>()
            if(arr!=null)for(i in 0 until arr.length())arr.optString(i).takeIf{it.matches(Regex("[0-9a-fA-F]{16}"))}?.lowercase()?.let(variants::add)
            val primary=j.getString("dhash64").lowercase()
            if(variants.isEmpty())variants.add(primary)
            Draft(
                ownerLogin=owner,
                sourceKind=j.getString("source_kind"),
                capturedAt=j.getString("captured_at"),
                idempotencyKey=j.getString("idempotency_key"),
                image=DocumentImageProcessor.ProcessedImage(
                    bytes=bytes,sha256=sha,md5=j.getString("md5"),dhash64=primary,
                    dhash64Variants=variants.distinct().take(4),
                    width=j.getInt("width"),height=j.getInt("height"),mimeType=j.optString("mime_type","image/jpeg")
                ),
                updatedAt=j.getLong("updated_at")
            )
        }.getOrNull()
    }

    fun remove(ownerLogin:String)=synchronized(lock){accountDir(ownerLogin,false)?.deleteRecursively()}

    private fun accountDir(ownerLogin:String,create:Boolean=true):File?{
        val key=digest("SHA-256",ownerLogin.trim().lowercase().toByteArray(Charsets.UTF_8)).take(24)
        val dir=File(root,key)
        if(create)dir.mkdirs()
        return dir.takeIf{it.isDirectory}
    }
    private fun cleanupTemps(dir:File){
        val cutoff=System.currentTimeMillis()-24*60*60*1000L
        dir.listFiles()?.filter{it.name.endsWith(".tmp")&&it.lastModified()<cutoff}?.forEach{it.delete()}
    }
    private fun digest(algorithm:String,bytes:ByteArray)=MessageDigest.getInstance(algorithm).digest(bytes)
        .joinToString(""){(it.toInt() and 0xff).toString(16).padStart(2,'0')}

    companion object{private val lock=Any()}
}
