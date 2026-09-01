package vn.pickpack1291.app.beta

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.security.MessageDigest

class DocumentCategoryCache(context:Context){
    data class Entry(val id:String,val name:String)
    private val prefs=context.applicationContext.getSharedPreferences("pp1291_document_category_cache_v1",Context.MODE_PRIVATE)

    fun save(ownerLogin:String,entries:List<Entry>){
        val arr=JSONArray()
        entries.forEach{arr.put(JSONObject().put("category_id",it.id).put("display_name",it.name))}
        prefs.edit().putString(key(ownerLogin),arr.toString()).apply()
    }

    fun load(ownerLogin:String):List<Entry>{
        val raw=prefs.getString(key(ownerLogin),null)?:return emptyList()
        val arr=runCatching{JSONArray(raw)}.getOrNull()?:return emptyList()
        val out=mutableListOf<Entry>()
        for(i in 0 until arr.length()){
            val o=arr.optJSONObject(i)?:continue
            val id=o.optString("category_id").trim()
            val name=o.optString("display_name").trim()
            if(id.isNotBlank()&&name.isNotBlank())out.add(Entry(id,name))
        }
        return out.distinctBy{it.id}
    }

    private fun key(ownerLogin:String):String{
        val raw=BuildConfig.ENVIRONMENT_ID+"|"+ownerLogin.trim().lowercase()
        return MessageDigest.getInstance("SHA-256").digest(raw.toByteArray(Charsets.UTF_8))
            .joinToString(""){(it.toInt() and 0xff).toString(16).padStart(2,'0')}.take(32)
    }
}
