package vn.pickpack1291.app.beta

import android.content.Context
import java.io.File

class DocumentMediaCache(context:Context) {
    private val dir=File(context.cacheDir,"document-media-v1").apply{mkdirs()}

    fun get(documentId:String):ByteArray?=synchronized(lock){
        val f=file(documentId)
        if(!f.isFile)return null
        if(f.length()<=0L||f.length()>MAX_SINGLE_BYTES){f.delete();return null}
        f.setLastModified(System.currentTimeMillis())
        runCatching{f.readBytes()}.getOrNull()
    }
    fun put(documentId:String,bytes:ByteArray)=synchronized(lock){
        if(bytes.isEmpty()||bytes.size>MAX_SINGLE_BYTES)return
        val f=file(documentId)\n        val tmp=File(dir,safe(documentId)+".jpg.tmp")
        tmp.outputStream().use{it.write(bytes)}
        if(!tmp.renameTo(f)){tmp.delete();return}
        f.setLastModified(System.currentTimeMillis())
        prune()
    }
    fun clear(documentId:String)=synchronized(lock){file(documentId).delete()}
    fun clearAll()=synchronized(lock){dir.listFiles()?.forEach{it.delete()}}

    private fun prune(){
        val files=dir.listFiles()?.filter{it.isFile&&it.name.endsWith(".jpg")}?.sortedByDescending{it.lastModified()}.orEmpty()
        var total=0L
        files.forEachIndexed{index,f->
            total+=f.length()
            if(index>=MAX_FILES||total>MAX_BYTES)f.delete()
        }
        dir.listFiles()?.filter{it.name.endsWith(".tmp")&&System.currentTimeMillis()-it.lastModified()>60*60*1000L}?.forEach{it.delete()}
    }
    private fun file(id:String)=File(dir,safe(id)+".jpg")
    private fun safe(id:String)=id.replace(Regex("[^A-Za-z0-9_-]"),"_").take(96)

    companion object{
        private val lock=Any()
        const val MAX_FILES=60
        const val MAX_BYTES=64L*1024L*1024L
        const val MAX_SINGLE_BYTES=12*1024*1024
    }
}
