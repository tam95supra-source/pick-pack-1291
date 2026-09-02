package vn.pickpack1291.app.beta

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import org.json.JSONArray
import org.json.JSONObject
import java.time.LocalDate
import java.time.ZoneId

/** Isolated 14-day cache for post-meal attendance. Never changes the operational N..N-6 store. */
class MealAttendanceLocalStore(context: Context) {
    private val app=context.applicationContext
    private val helper=Helper(app)

    fun load(date:String):JSONObject?=synchronized(LOCK){
        helper.readableDatabase.query("meal_day_cache",arrayOf("payload_json"),"business_date=?",arrayOf(date),null,null,null).use{c->
            if(!c.moveToFirst())return@synchronized null
            runCatching{JSONObject(c.getString(0))}.getOrNull()
        }
    }

    fun availableDatesWithData():List<String>=synchronized(LOCK){
        val out=mutableListOf<String>()
        helper.readableDatabase.query("meal_day_cache",arrayOf("business_date","payload_json"),null,null,null,null,"business_date DESC").use{c->
            while(c.moveToNext()){
                val payload=runCatching{JSONObject(c.getString(1))}.getOrNull()
                if((payload?.optJSONArray("items")?.length()?:0)>0)out+=c.getString(0)
            }
        }
        out
    }

    fun save(payload:JSONObject){
        val date=payload.optString("business_date").trim()
        if(date.isBlank())return
        synchronized(LOCK){
            val db=helper.writableDatabase
            upsertLocked(db,date,payload.toString())
            pruneLocked(db)
        }
    }

    fun updateItem(date:String,mnv:String,mutate:(JSONObject)->Unit):JSONObject?=synchronized(LOCK){
        val current=load(date)?:return@synchronized null
        val items=current.optJSONArray("items")?:JSONArray().also{current.put("items",it)}
        var found:JSONObject?=null
        for(i in 0 until items.length()){
            val row=items.optJSONObject(i)?:continue
            if(row.optString("mnv")==mnv){mutate(row);found=row;break}
        }
        if(found!=null){
            current.put("cached_optimistic",true)
            upsertLocked(helper.writableDatabase,date,current.toString())
        }
        found?.let{JSONObject(it.toString())}
    }

    fun addProvisional(date:String,item:JSONObject){
        synchronized(LOCK){
            val current=load(date)?:JSONObject().put("ok",true).put("business_date",date).put("current_day",true).put("items",JSONArray())
            val items=current.optJSONArray("items")?:JSONArray().also{current.put("items",it)}
            var exists=false
            for(i in 0 until items.length())if(items.optJSONObject(i)?.optString("mnv")==item.optString("mnv")){exists=true;break}
            if(!exists)items.put(item)
            current.put("cached_optimistic",true)
            save(current)
        }
    }

    fun prune(){
        synchronized(LOCK){pruneLocked(helper.writableDatabase)}
    }

    private fun upsertLocked(db:SQLiteDatabase,date:String,payloadJson:String){
        val values=ContentValues().apply{
            put("business_date",date)
            put("payload_json",payloadJson)
            put("saved_at",System.currentTimeMillis())
        }
        if(db.insertWithOnConflict("meal_day_cache",null,values,SQLiteDatabase.CONFLICT_REPLACE)<0L){
            throw IllegalStateException("MEAL_CACHE_WRITE_FAILED")
        }
    }

    private fun pruneLocked(db:SQLiteDatabase){
        val today=LocalDate.now(ZoneId.of(TZ))
        val floor=today.minusDays(13).toString()
        db.delete("meal_day_cache","business_date<? OR business_date>?",arrayOf(floor,today.toString()))
    }

    private class Helper(context:Context):SQLiteOpenHelper(context,DB_NAME,null,1){
        override fun onCreate(db:SQLiteDatabase){
            db.execSQL("""CREATE TABLE IF NOT EXISTS meal_day_cache(
                business_date TEXT PRIMARY KEY NOT NULL,
                payload_json TEXT NOT NULL,
                saved_at INTEGER NOT NULL
            )""")
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_meal_cache_saved ON meal_day_cache(saved_at)")
        }
        override fun onUpgrade(db:SQLiteDatabase,oldVersion:Int,newVersion:Int)=Unit
    }

    companion object{
        private const val DB_NAME="pp_meal_attendance_14d.db"
        private const val TZ="Asia/Ho_Chi_Minh"
        private val LOCK=Any()
    }
}
