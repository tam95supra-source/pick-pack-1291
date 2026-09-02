package vn.pickpack1291.app.beta

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteDatabaseLockedException
import android.database.sqlite.SQLiteOpenHelper
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Calendar
import java.util.Locale
import java.util.TimeZone
import java.util.concurrent.ConcurrentHashMap

/**
 * Device-side operational store for the Service-provided business window N..N-6.
 *
 * The historical DB filename is intentionally retained so an installed Beta upgrades in place and
 * cannot lose a durable mutation outbox. Retention is semantic, not filename-based: applyBusinessWindow
 * prunes day snapshots to the exact Service business sequence while leaving pending mutations intact.
 */
class OperationalDataStore(context: Context) {
    // S54_BETA48_OWNER_10_FIXES
    private val app = context.applicationContext
    // S32_LOCAL_HISTORY_FLUSH_FIX: persistent local event ledger + canonical merge support.
    private val helper = helper(context.applicationContext)

    data class PendingMutation(
        val eventId: String,
        val body: JSONObject,
        val exclusive: Boolean,
        val status: String,
        val attemptCount: Int,
        val queuedAt: Long,
    )

    fun saveDay(snapshot: JSONObject) = withDbLock {
        val date = snapshot.optString("business_date").trim()
        if (date.isBlank()) return@withDbLock
        val copy = JSONObject(snapshot.toString())
        val values = ContentValues().apply {
            put("business_date", date)
            put("day_revision", copy.optLong("day_revision", 0L))
            put("snapshot_json", copy.toString())
            put("saved_at", System.currentTimeMillis())
        }
        val db = writableDb()
        db.beginTransaction()
        try {
            db.insertWithOnConflict("day_snapshot", null, values, SQLiteDatabase.CONFLICT_REPLACE)
            db.setTransactionSuccessful()
        } finally { db.endTransaction() }
        MEMORY[date] = copy
    }

    fun saveDays(days: Iterable<JSONObject>) = withDbLock {
        val copies = days.mapNotNull { day ->
            val date = day.optString("business_date").trim()
            if (date.isBlank()) null else date to JSONObject(day.toString())
        }
        if (copies.isEmpty()) return@withDbLock
        val now = System.currentTimeMillis()
        val db = writableDb()
        db.beginTransaction()
        try {
            for ((date, copy) in copies) {
                val values = ContentValues().apply {
                    put("business_date", date)
                    put("day_revision", copy.optLong("day_revision", 0L))
                    put("snapshot_json", copy.toString())
                    put("saved_at", now)
                }
                db.insertWithOnConflict("day_snapshot", null, values, SQLiteDatabase.CONFLICT_REPLACE)
            }
            db.setTransactionSuccessful()
        } finally { db.endTransaction() }
        copies.forEach { (date, copy) -> MEMORY[date] = copy }
    }

    fun loadDay(date: String): JSONObject? {
        MEMORY[date]?.let { return JSONObject(it.toString()) }
        return withDbLock {
            readableDb().query("day_snapshot", arrayOf("snapshot_json"), "business_date=?", arrayOf(date), null, null, null, "1").use { c ->
                if (!c.moveToFirst()) return@withDbLock null
                val parsed = runCatching { JSONObject(c.getString(0)) }.getOrNull() ?: return@withDbLock null
                MEMORY[date] = parsed
                JSONObject(parsed.toString())
            }
        }
    }

    fun availableDates(): List<String> = withDbLock {
        val out = ArrayList<String>()
        readableDb().query("day_snapshot", arrayOf("business_date"), null, null, null, null, "business_date DESC").use { c -> while (c.moveToNext()) out += c.getString(0) }
        out
    }

    fun historyWindowDates():List<String>{
        val cal=Calendar.getInstance(TimeZone.getTimeZone(TZ));val out=ArrayList<String>(7)
        repeat(7){out+=isoDate(cal.time);cal.add(Calendar.DAY_OF_MONTH,-1)}
        return out
    }

    fun storageBytes():Long{
        val main=app.getDatabasePath(DB_NAME);val base=main.absolutePath
        return listOf(main,java.io.File(base+"-wal"),java.io.File(base+"-shm"),java.io.File(base+"-journal")).filter{it.exists()}.sumOf{it.length()}
    }

    fun revisions(): Map<String, Long> = withDbLock {
        val out = LinkedHashMap<String, Long>()
        readableDb().query("day_snapshot", arrayOf("business_date", "day_revision"), null, null, null, null, "business_date DESC").use { c -> while (c.moveToNext()) out[c.getString(0)] = c.getLong(1) }
        out
    }

    fun revision(date: String): Long = revisions()[date] ?: 0L

    /** Apply the exact canonical Service business window. No calendar comparison/subtraction. */
    fun applyBusinessWindow(remoteDates: List<String>, retentionEpoch: Long) = withDbLock {
        val exact = remoteDates.map { it.trim() }.filter { it.isNotBlank() }.distinct().take(7)
        if (exact.isEmpty()) return@withDbLock
        val db = writableDb()
        val local = ArrayList<String>()
        db.query("day_snapshot", arrayOf("business_date"), null, null, null, null, null).use { c -> while (c.moveToNext()) local += c.getString(0) }
        db.beginTransaction()
        try {
            local.filter { it !in exact }.forEach { date -> db.delete("day_snapshot", "business_date=?", arrayOf(date)) }
            val window = JSONArray().apply { exact.forEach { put(it) } }.toString()
            db.insertWithOnConflict("sync_meta", null, ContentValues().apply { put("meta_key", "business_window"); put("meta_value", window) }, SQLiteDatabase.CONFLICT_REPLACE)
            db.insertWithOnConflict("sync_meta", null, ContentValues().apply { put("meta_key", "retention_epoch"); put("meta_value", retentionEpoch.toString()) }, SQLiteDatabase.CONFLICT_REPLACE)
            db.setTransactionSuccessful()
        } finally { db.endTransaction() }
        MEMORY.keys.filter { it !in exact }.forEach { MEMORY.remove(it) }
        pruneResolvedLocked(db)
    }

    /** Legacy helpers retained for binary/source compatibility; exact-window code should use applyBusinessWindow. */
    fun dropBefore(retentionFloor: String) = withDbLock {
        if (retentionFloor.isBlank()) return@withDbLock
        writableDb().delete("day_snapshot", "business_date < ?", arrayOf(retentionFloor))
        MEMORY.keys.filter { it < retentionFloor }.forEach { MEMORY.remove(it) }
    }

    fun dropDatesNotIn(remoteDates: Set<String>, retentionFloor: String) = withDbLock {
        if (remoteDates.isEmpty()) return@withDbLock
        val db = writableDb()
        val local = ArrayList<String>()
        db.query("day_snapshot", arrayOf("business_date"), null, null, null, null, null).use { c -> while (c.moveToNext()) local += c.getString(0) }
        db.beginTransaction()
        try {
            local.filter { it !in remoteDates }.forEach { date -> db.delete("day_snapshot", "business_date=?", arrayOf(date)); MEMORY.remove(date) }
            db.setTransactionSuccessful()
        } finally { db.endTransaction() }
    }

    fun putMeta(key: String, value: String) = withDbLock {
        val values = ContentValues().apply { put("meta_key", key); put("meta_value", value) }
        writableDb().insertWithOnConflict("sync_meta", null, values, SQLiteDatabase.CONFLICT_REPLACE)
    }

    fun meta(key: String): String? = withDbLock {
        readableDb().query("sync_meta", arrayOf("meta_value"), "meta_key=?", arrayOf(key), null, null, null, "1").use { c -> if (c.moveToFirst()) c.getString(0) else null }
    }

    fun saveAuthority(authority: JSONObject) {
        putMeta("authority_epoch", authority.optLong("authority_epoch", 0L).toString())
        putMeta("authority_seq", authority.optLong("authority_seq", 0L).toString())
        putMeta("authority_mode", authority.optString("mode"))
        putMeta("service_generation", authority.optString("service_generation"))
    }

    fun authorityEpoch(): Long = meta("authority_epoch")?.toLongOrNull() ?: 0L
    fun authoritySeq(): Long = meta("authority_seq")?.toLongOrNull() ?: 0L
    fun authorityMode(): String = meta("authority_mode") ?: "OFFLINE_LOCAL"
    fun serviceGeneration(): String = meta("service_generation") ?: ""

    fun enqueueMutation(event: JSONObject, exclusive: Boolean) = withDbLock {
        val eventId = event.optString("event_id").trim()
        require(eventId.isNotBlank()) { "EVENT_ID_REQUIRED" }
        val now = System.currentTimeMillis()
        val outboxValues = ContentValues().apply {
            put("event_id", eventId)
            put("body_json", event.toString())
            put("exclusive", if (exclusive) 1 else 0)
            put("status", "LOCAL_PENDING")
            put("attempt_count", 0)
            put("next_attempt_at", now)
            put("queued_at", now)
            put("updated_at", now)
        }
        val historyValues = ContentValues().apply {
            put("event_id", eventId)
            put("body_json", event.toString())
            put("status", "LOCAL_PENDING")
            put("last_error", "")
            put("queued_at", now)
            put("updated_at", now)
        }
        val db = writableDb()
        db.beginTransaction()
        try {
            db.insertWithOnConflict("mutation_outbox", null, outboxValues, SQLiteDatabase.CONFLICT_IGNORE)
            db.insertWithOnConflict("local_history", null, historyValues, SQLiteDatabase.CONFLICT_IGNORE)
            db.setTransactionSuccessful()
        } finally { db.endTransaction() }
    }

    // S40_OWNER_LOCAL_FIRST_REPAIR: worker sees all unresolved events; WorkManager owns retry backoff.
    fun unresolvedMutations(limit: Int = 500): List<PendingMutation> = withDbLock {
        val out=ArrayList<PendingMutation>()
        readableDb().query(
            "mutation_outbox",
            arrayOf("event_id","body_json","exclusive","status","attempt_count","queued_at"),
            "status IN ('LOCAL_PENDING','PENDING','RETRY','OFFLINE_PROVISIONAL','LAN_CONFIRMED')",
            null,null,null,"queued_at ASC",limit.coerceIn(1,500).toString(),
        ).use { c ->
            while(c.moveToNext()) runCatching{JSONObject(c.getString(1))}.getOrNull()?.let{body->
                out+=PendingMutation(c.getString(0),body,c.getInt(2)==1,c.getString(3),c.getInt(4),c.getLong(5))
            }
        }
        out
    }

    fun pendingMutations(limit: Int = 100): List<PendingMutation> = withDbLock {
        val out = ArrayList<PendingMutation>()
        val now = System.currentTimeMillis().toString()
        readableDb().query(
            "mutation_outbox",
            arrayOf("event_id", "body_json", "exclusive", "status", "attempt_count", "queued_at"),
            "status IN ('LOCAL_PENDING','PENDING','RETRY','OFFLINE_PROVISIONAL','LAN_CONFIRMED') AND next_attempt_at <= ?",
            arrayOf(now), null, null, "queued_at ASC", limit.coerceIn(1, 500).toString(),
        ).use { c ->
            while (c.moveToNext()) {
                runCatching { JSONObject(c.getString(1)) }.getOrNull()?.let { body ->
                    out += PendingMutation(c.getString(0), body, c.getInt(2) == 1, c.getString(3), c.getInt(4), c.getLong(5))
                }
            }
        }
        out
    }

    /**
     * S27_PROJECTION_ACK_GAP: visible local projection includes ordinary pending writes plus
     * CONFIRMED writes whose ACK is newer than the currently stored day snapshot. This closes the
     * ACK-to-next-snapshot gap without ever making a confirmed write eligible for network resend.
     * Once reconcile saves a snapshot after the ACK, the confirmed overlay disappears.
     */
    fun projectionMutations(limit: Int = 500): List<PendingMutation> = withDbLock {
        val out = ArrayList<PendingMutation>()
        val now = System.currentTimeMillis().toString()
        readableDb().query(
            "mutation_outbox",
            arrayOf("event_id", "body_json", "exclusive", "status", "attempt_count", "queued_at", "updated_at"),
            "status IN ('LOCAL_PENDING','PENDING','RETRY','OFFLINE_PROVISIONAL','LAN_CONFIRMED') OR status='CONFIRMED'",
            null, null, null, "queued_at ASC", limit.coerceIn(1, 1000).toString(),
        ).use { c ->
            while (c.moveToNext()) {
                val body = runCatching { JSONObject(c.getString(1)) }.getOrNull() ?: continue
                val status = c.getString(3)
                if (status == "CONFIRMED") {
                    val payload = body.optJSONObject("payload") ?: body
                    val date = payload.optString("business_date").ifBlank { body.optString("business_date") }
                    if (date.isBlank()) continue
                    val ackAt = c.getLong(6)
                    val snapshotSavedAt = readableDb().query(
                        "day_snapshot", arrayOf("saved_at"), "business_date=?", arrayOf(date), null, null, null, "1"
                    ).use { sc -> if (sc.moveToFirst()) sc.getLong(0) else 0L }
                    if (snapshotSavedAt >= ackAt) continue
                }
                out += PendingMutation(c.getString(0), body, c.getInt(2) == 1, status, c.getInt(4), c.getLong(5))
            }
        }
        out
    }

    /** Persistent local actions, including pending/retry/rejected/reviewed rows. */
    fun localHistory(limit: Int = 500): List<JSONObject> = withDbLock {
        val out = ArrayList<JSONObject>()
        readableDb().query(
            "local_history",
            arrayOf("event_id", "body_json", "status", "last_error", "queued_at", "updated_at"),
            null, null, null, null, "queued_at DESC", limit.coerceIn(1, 2000).toString(),
        ).use { c ->
            while (c.moveToNext()) {
                val body = runCatching { JSONObject(c.getString(1)) }.getOrNull() ?: JSONObject()
                out += JSONObject()
                    .put("event_id", c.getString(0))
                    .put("body", body)
                    .put("status", c.getString(2))
                    .put("error", c.getString(3) ?: "")
                    .put("queued_at", c.getLong(4))
                    .put("updated_at", c.getLong(5))
            }
        }
        out
    }

    // S34_OWNER_SIX_REQUESTS: full durable local History for global search/filter.
    fun localHistoryAll(): List<JSONObject> = withDbLock {
        val out = ArrayList<JSONObject>()
        readableDb().query(
            "local_history",
            arrayOf("event_id", "body_json", "status", "last_error", "queued_at", "updated_at"),
            null, null, null, null, "queued_at DESC", null,
        ).use { c ->
            while (c.moveToNext()) {
                val body = runCatching { JSONObject(c.getString(1)) }.getOrNull() ?: JSONObject()
                out += JSONObject()
                    .put("event_id", c.getString(0))
                    .put("body", body)
                    .put("status", c.getString(2))
                    .put("error", c.getString(3) ?: "")
                    .put("queued_at", c.getLong(4))
                    .put("updated_at", c.getLong(5))
            }
        }
        out
    }

    /**
     * SUPERADMIN history removal is a presentation/audit cleanup, not a business-rule rewrite.
     * Local terminal failures may be removed from both history and the already-terminal outbox.
     * Pending business mutations keep their durable outbox row, so deleting the History card
     * cannot silently cancel a real attendance/labor write.
     */
    fun deleteLocalHistory(eventIds:Collection<String>):Int = withDbLock {
        val ids=eventIds.map{it.trim()}.filter{it.isNotBlank()}.distinct()
        if(ids.isEmpty())return@withDbLock 0
        val db=writableDb();var removed=0
        db.beginTransaction()
        try{
            for(id in ids){
                val status=db.query("local_history",arrayOf("status"),"event_id=?",arrayOf(id),null,null,null,"1").use{q->if(q.moveToFirst())q.getString(0).orEmpty().uppercase() else ""}
                if(status in setOf("REJECTED","REVIEW_REQUIRED","CONFLICT","FAILED","ERROR")){
                    db.delete("mutation_outbox","event_id=? AND status IN ('REJECTED','REVIEW_REQUIRED','CONFLICT','FAILED','ERROR')",arrayOf(id))
                }
                removed+=db.delete("local_history","event_id=?",arrayOf(id))
            }
            db.setTransactionSuccessful()
        }finally{db.endTransaction()}
        removed
    }

    /** Permanently rejected out-of-window rows are audit/history, never network backlog. */
    fun retryDateWindowRejects():Int = 0

    fun markMutationSynced(eventId: String) = markMutationResolved(eventId, "CONFIRMED", "")
    fun markMutationRejected(eventId: String, error: String) = markMutationResolved(eventId, "REJECTED", error)
    fun markMutationReviewRequired(eventId: String, error: String) = markMutationResolved(eventId, "REVIEW_REQUIRED", error)

    /** LAN ACK is provisional. The exact event remains in outbox until canonical Service confirms it. */
    fun markLanConfirmed(eventId:String,generation:Long)=withDbLock{
        val now=System.currentTimeMillis();val db=writableDb();db.beginTransaction()
        try{
            db.execSQL("UPDATE mutation_outbox SET status='LAN_CONFIRMED',next_attempt_at=?,last_error=?,updated_at=? WHERE event_id=? AND status NOT IN ('CONFIRMED','REJECTED','REVIEW_REQUIRED')",arrayOf(now+30_000L,"LAN_GENERATION_$generation",now,eventId))
            db.execSQL("UPDATE local_history SET status='LAN_CONFIRMED',last_error=?,updated_at=? WHERE event_id=? AND status NOT IN ('CONFIRMED','REJECTED','REVIEW_REQUIRED')",arrayOf("LAN_GENERATION_$generation",now,eventId))
            db.setTransactionSuccessful()
        }finally{db.endTransaction()}
    }

    data class LanPersistResult(val ok:Boolean,val error:String?=null)

    /** Master/backup persist exact event bytes before ACK. Exclusive resource keys are fenced locally. */
    fun persistLanReplica(body:JSONObject,sourceDevice:String,generation:Long,replicaRole:String):LanPersistResult=withDbLock{
        val eventId=body.optString("event_id").trim()
        if(eventId.isBlank())return@withDbLock LanPersistResult(false,"LAN_EVENT_ID_REQUIRED")
        val payload=body.optJSONObject("payload")?:JSONObject()
        val action=body.optString("action").trim()
        val mnv=payload.optString("mnv").trim()
        val now=System.currentTimeMillis();val db=writableDb();db.beginTransaction()
        try{
            val existing=db.rawQuery("SELECT body_json FROM lan_event_replicas WHERE event_id=?",arrayOf(eventId)).use{c->if(c.moveToFirst())c.getString(0)else null}
            if(existing!=null){
                if(existing!=body.toString())return@withDbLock LanPersistResult(false,"LAN_EVENT_ID_PAYLOAD_MISMATCH")
                db.setTransactionSuccessful();return@withDbLock LanPersistResult(true)
            }
            if(action=="exit"&&mnv.isNotBlank())db.delete("lan_resource_reservations","mnv=?",arrayOf(mnv))
            val keys=linkedSetOf<String>()
            if(action=="enter"||action=="resource_change"){
                listOf("pda_serial" to "PDA","user_pick" to "USER_PICK","pack_table" to "PACK_TABLE","user_pack" to "USER_PACK").forEach{(field,type)->
                    val v=payload.optString(field).trim();if(v.isNotBlank())keys.add("$type|$v")
                }
            }
            for(key in keys){
                val owner=db.rawQuery("SELECT event_id,mnv FROM lan_resource_reservations WHERE resource_key=?",arrayOf(key)).use{c->if(c.moveToFirst())Pair(c.getString(0),c.getString(1))else null}
                if(owner!=null&&owner.first!=eventId&&owner.second!=mnv)return@withDbLock LanPersistResult(false,"LAN_RESOURCE_CONFLICT:$key")
            }
            db.execSQL("INSERT INTO lan_event_replicas(event_id,body_json,source_device,generation,replica_role,stored_at) VALUES(?,?,?,?,?,?)",arrayOf(eventId,body.toString(),sourceDevice,generation,replicaRole,now))
            for(key in keys)db.execSQL("INSERT OR REPLACE INTO lan_resource_reservations(resource_key,event_id,mnv,generation,updated_at) VALUES(?,?,?,?,?)",arrayOf(key,eventId,mnv,generation,now))
            db.setTransactionSuccessful();LanPersistResult(true)
        }finally{db.endTransaction()}
    }

    fun lanReplica(eventId:String):JSONObject?=withDbLock{
        readableDb().rawQuery("SELECT body_json FROM lan_event_replicas WHERE event_id=?",arrayOf(eventId)).use{c->if(c.moveToFirst())runCatching{JSONObject(c.getString(0))}.getOrNull() else null}
    }

    fun lanReplicaCount():Int=withDbLock{readableDb().rawQuery("SELECT COUNT(*) FROM lan_event_replicas",null).use{c->if(c.moveToFirst())c.getInt(0)else 0}}

    data class LanReplica(val eventId:String,val body:JSONObject,val generation:Long)

    fun pendingLanReplicas(limit:Int=100):List<LanReplica> = withDbLock {
        val out=ArrayList<LanReplica>()
        readableDb().query("lan_event_replicas",arrayOf("event_id","body_json","generation"),"canonical_status IN ('PENDING','RETRY')",null,null,null,"stored_at ASC",limit.coerceIn(1,500).toString()).use{c->
            while(c.moveToNext())runCatching{JSONObject(c.getString(1))}.getOrNull()?.let{out+=LanReplica(c.getString(0),it,c.getLong(2))}
        }
        out
    }

    fun pendingLanReplicaCount():Int=withDbLock{
        readableDb().rawQuery("SELECT COUNT(*) FROM lan_event_replicas WHERE canonical_status IN ('PENDING','RETRY')",null).use{c->if(c.moveToFirst())c.getInt(0)else 0}
    }

    fun markLanReplicaCanonical(eventId:String,status:String,error:String="")=withDbLock{
        writableDb().execSQL("UPDATE lan_event_replicas SET canonical_status=?,canonical_error=?,canonical_at=? WHERE event_id=?",arrayOf(status,error.take(1200),System.currentTimeMillis(),eventId))
    }

    /** Google Emergency Ledger ACK is provisional capture only; the local event remains replayable. */
    fun markEmergencyCaptured(eventId:String)=withDbLock{
        val now=System.currentTimeMillis();val db=writableDb();db.beginTransaction()
        try{
            db.execSQL("UPDATE mutation_outbox SET status='OFFLINE_PROVISIONAL',next_attempt_at=?,last_error='EMERGENCY_LEDGER_CAPTURED',updated_at=? WHERE event_id=? AND status NOT IN ('CONFIRMED','REJECTED','REVIEW_REQUIRED')",arrayOf(now+15_000L,now,eventId))
            db.execSQL("UPDATE local_history SET status='OFFLINE_PROVISIONAL',last_error='EMERGENCY_LEDGER_CAPTURED',updated_at=? WHERE event_id=? AND status NOT IN ('CONFIRMED','REJECTED','REVIEW_REQUIRED')",arrayOf(now,eventId))
            db.setTransactionSuccessful()
        }finally{db.endTransaction()}
    }

    private fun markMutationResolved(eventId: String, status: String, error: String) = withDbLock {
        val now = System.currentTimeMillis()
        val db = writableDb()
        db.beginTransaction()
        try {
            db.execSQL(
                "UPDATE mutation_outbox SET status=?,last_error=?,updated_at=? WHERE event_id=?",
                arrayOf(status, error.take(1200), now, eventId),
            )
            db.execSQL(
                "UPDATE local_history SET status=?,last_error=?,updated_at=? WHERE event_id=?",
                arrayOf(status, error.take(1200), now, eventId),
            )
            db.setTransactionSuccessful()
        } finally { db.endTransaction() }
    }

    fun markMutationRetry(eventId: String, error: String, delayMs: Long) = withDbLock {
        val now = System.currentTimeMillis()
        val db = writableDb()
        db.beginTransaction()
        try {
            db.execSQL(
                "UPDATE mutation_outbox SET status='RETRY',attempt_count=attempt_count+1,next_attempt_at=?,last_error=?,updated_at=? WHERE event_id=?",
                arrayOf(now + delayMs.coerceIn(1_000L, 15 * 60_000L), error.take(600), now, eventId),
            )
            db.execSQL(
                "UPDATE local_history SET status='RETRY',last_error=?,updated_at=? WHERE event_id=?",
                arrayOf(error.take(1200), now, eventId),
            )
            db.setTransactionSuccessful()
        } finally { db.endTransaction() }
    }

    /** Compatibility mapping: old CONFLICT becomes the owner-visible REVIEW_REQUIRED state. */
    fun markMutationConflict(eventId: String, error: String) = markMutationReviewRequired(eventId, error)

    fun diagnosticMutation(eventId:String):JSONObject? = withDbLock {
        if(eventId.isBlank())return@withDbLock null
        readableDb().query(
            "mutation_outbox",
            arrayOf("event_id","body_json","exclusive","status","attempt_count","next_attempt_at","queued_at","updated_at","last_error"),
            "event_id=?",arrayOf(eventId),null,null,null,"1"
        ).use{c->
            if(!c.moveToFirst())return@withDbLock null
            val body=runCatching{JSONObject(c.getString(1))}.getOrDefault(JSONObject())
            return@withDbLock JSONObject()
                .put("event_id",c.getString(0)).put("action",body.optString("action"))
                .put("exclusive",c.getInt(2)!=0).put("status",c.getString(3))
                .put("attempt_count",c.getInt(4)).put("next_attempt_at",c.getLong(5))
                .put("queued_at",c.getLong(6)).put("updated_at",c.getLong(7))
                .put("last_error",c.getString(8)?:"")
        }
    }

    /** Beta100: isolated technical-test ledger. Never consumed by the production mutation worker. */
    fun saveResilienceTest(eventId:String,scenario:String,body:JSONObject,status:String,stage:String,error:String="",evidence:JSONObject=JSONObject())=withDbLock{
        require(eventId.isNotBlank()){"EVENT_ID_REQUIRED"}
        val now=System.currentTimeMillis()
        val values=ContentValues().apply{
            put("event_id",eventId);put("scenario",scenario);put("body_json",body.toString())
            put("status",status);put("stage",stage);put("attempt_count",0);put("last_error",error.take(1200))
            put("evidence_json",evidence.toString());put("created_at",now);put("updated_at",now)
        }
        writableDb().insertWithOnConflict("resilience_test_events",null,values,SQLiteDatabase.CONFLICT_REPLACE)
    }

    fun updateResilienceTest(eventId:String,status:String,stage:String,error:String="",evidence:JSONObject?=null,incrementAttempt:Boolean=false)=withDbLock{
        val now=System.currentTimeMillis()
        val db=writableDb()
        val current=readableDb().query("resilience_test_events",arrayOf("evidence_json","attempt_count"),"event_id=?",arrayOf(eventId),null,null,null,"1").use{q->
            if(q.moveToFirst())Pair(q.getString(0),q.getInt(1)) else Pair("{}",0)
        }
        val merged=runCatching{JSONObject(current.first)}.getOrDefault(JSONObject())
        if(evidence!=null){
            val keys=evidence.keys();while(keys.hasNext()){val k=keys.next();merged.put(k,evidence.opt(k))}
        }
        db.execSQL(
            "UPDATE resilience_test_events SET status=?,stage=?,attempt_count=?,last_error=?,evidence_json=?,updated_at=? WHERE event_id=?",
            arrayOf(status,stage,current.second+(if(incrementAttempt)1 else 0),error.take(1200),merged.toString(),now,eventId)
        )
    }

    fun resilienceTest(eventId:String):JSONObject?=withDbLock{
        readableDb().query(
            "resilience_test_events",
            arrayOf("event_id","scenario","body_json","status","stage","attempt_count","last_error","evidence_json","created_at","updated_at"),
            "event_id=?",arrayOf(eventId),null,null,null,"1"
        ).use{q->
            if(!q.moveToFirst())return@withDbLock null
            JSONObject()
                .put("event_id",q.getString(0)).put("scenario",q.getString(1))
                .put("body",runCatching{JSONObject(q.getString(2))}.getOrDefault(JSONObject()))
                .put("status",q.getString(3)).put("stage",q.getString(4)).put("attempt_count",q.getInt(5))
                .put("last_error",q.getString(6)?:"")
                .put("evidence",runCatching{JSONObject(q.getString(7))}.getOrDefault(JSONObject()))
                .put("created_at",q.getLong(8)).put("updated_at",q.getLong(9))
        }
    }

    fun latestResilienceTest():JSONObject?=withDbLock{
        readableDb().query(
            "resilience_test_events",
            arrayOf("event_id"),null,null,null,null,"updated_at DESC","1"
        ).use{q->if(q.moveToFirst())resilienceTest(q.getString(0))else null}
    }

    fun resilienceTestHistory(limit:Int=12):JSONArray=withDbLock{
        val out=JSONArray()
        readableDb().query(
            "resilience_test_events",
            arrayOf("event_id"),null,null,null,null,"updated_at DESC",limit.coerceIn(1,50).toString()
        ).use{q->while(q.moveToNext()){resilienceTest(q.getString(0))?.let(out::put)}}
        out
    }

    // S44: bounded safe diagnostics; body payload is intentionally NOT emitted.
    fun diagnosticOutbox(limit:Int=50): JSONArray = withDbLock {
        val out=JSONArray()
        readableDb().query("mutation_outbox",arrayOf("event_id","body_json","exclusive","status","attempt_count","next_attempt_at","queued_at","updated_at","last_error"),null,null,null,null,"queued_at ASC",limit.coerceIn(1,100).toString()).use{c->
            while(c.moveToNext()){
                val body=runCatching{JSONObject(c.getString(1))}.getOrDefault(JSONObject())
                out.put(JSONObject()
                    .put("event_id",c.getString(0)).put("action",body.optString("action")).put("exclusive",c.getInt(2)!=0)
                    .put("status",c.getString(3)).put("attempt_count",c.getInt(4)).put("next_attempt_at",c.getLong(5))
                    .put("queued_at",c.getLong(6)).put("updated_at",c.getLong(7)).put("last_error",c.getString(8)?:""))
            }
        }
        out
    }

    data class MutationStatusCounts(val pending:Int,val review:Int,val rejected:Int,val confirmed:Int)

    fun mutationStatusCounts():MutationStatusCounts = withDbLock {
        var pending=0;var review=0;var rejected=0;var confirmed=0
        readableDb().rawQuery("SELECT status,COUNT(*) FROM mutation_outbox GROUP BY status",null).use { c ->
            while(c.moveToNext()){
                val count=c.getInt(1)
                when(c.getString(0)){
                    "LOCAL_PENDING","PENDING","RETRY","OFFLINE_PROVISIONAL","LAN_CONFIRMED"->pending+=count
                    "REVIEW_REQUIRED"->review+=count
                    "REJECTED"->rejected+=count
                    "CONFIRMED"->confirmed+=count
                }
            }
        }
        MutationStatusCounts(pending,review,rejected,confirmed)
    }

    fun pendingMutationCount(): Int = mutationStatusCounts().pending

    fun conflicts(limit: Int = 100): List<JSONObject> = withDbLock {
        val out = ArrayList<JSONObject>()
        readableDb().query("mutation_outbox", arrayOf("event_id","body_json","status","last_error","updated_at"), "status IN ('REVIEW_REQUIRED','REJECTED','CONFLICT')", null, null, null, "updated_at DESC", limit.coerceIn(1,500).toString()).use { c ->
            while (c.moveToNext()) out += JSONObject()
                .put("event_id",c.getString(0))
                .put("body",runCatching{JSONObject(c.getString(1))}.getOrNull())
                .put("status",if(c.getString(2)=="CONFLICT")"REVIEW_REQUIRED" else c.getString(2))
                .put("error",c.getString(3))
                .put("updated_at",c.getLong(4))
        }
        out
    }

    fun businessDate(): String = isoDate(Date())
    fun latestBusinessDate(): String = meta("business_date")?.takeIf { it.isNotBlank() } ?: availableDates().firstOrNull() ?: businessDate()
    fun previousBusinessDate(): String = availableDates().drop(1).firstOrNull() ?: latestBusinessDate()

    private fun pruneResolvedLocked(db: SQLiteDatabase) {
        val now = System.currentTimeMillis()
        db.delete("mutation_outbox", "status='CONFIRMED' AND updated_at < ?", arrayOf((now - 7L * 86_400_000L).toString()))
        db.delete("mutation_outbox", "status IN ('REJECTED','REVIEW_REQUIRED') AND updated_at < ?", arrayOf((now - 30L * 86_400_000L).toString()))
    }

    private fun readableDb(): SQLiteDatabase = openWithRetry { helper.readableDatabase }
    private fun writableDb(): SQLiteDatabase = openWithRetry { helper.writableDatabase }

    private fun <T> openWithRetry(block: () -> T): T {
        var last: SQLiteDatabaseLockedException? = null
        repeat(4) { attempt ->
            try { return block() } catch (e: SQLiteDatabaseLockedException) {
                last = e
                if (attempt < 3) Thread.sleep((40L shl attempt).coerceAtMost(320L))
            }
        }
        throw last ?: IllegalStateException("SQLITE_OPEN_FAILED")
    }

    private fun isoDate(date: Date): String = SimpleDateFormat("yyyy-MM-dd", Locale.US).apply { timeZone = TimeZone.getTimeZone(TZ) }.format(date)

    private class DbHelper(context: Context) : SQLiteOpenHelper(context, DB_NAME, null, DB_VERSION) {
        init { setWriteAheadLoggingEnabled(false) }
        override fun onCreate(db: SQLiteDatabase) { createV1(db); createV2(db); createV3(db); createV4(db); createV5(db); createV6(db) }
        override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
            // Never drop day_snapshot, mutation_outbox, or local_history during an installed-Beta upgrade.
            if (oldVersion < 2) createV2(db)
            if (oldVersion < 3) createV3(db)
            if (oldVersion < 4) createV4(db)
            if (oldVersion < 5) createV5(db)
            if (oldVersion < 6) createV6(db)
        }
        private fun createV1(db: SQLiteDatabase) {
            db.execSQL("""CREATE TABLE IF NOT EXISTS day_snapshot(
                business_date TEXT PRIMARY KEY NOT NULL,
                day_revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                saved_at INTEGER NOT NULL
            )""".trimIndent())
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_day_snapshot_saved ON day_snapshot(saved_at)")
            db.execSQL("""CREATE TABLE IF NOT EXISTS sync_meta(
                meta_key TEXT PRIMARY KEY NOT NULL,
                meta_value TEXT NOT NULL
            )""".trimIndent())
        }
        private fun createV2(db: SQLiteDatabase) {
            db.execSQL("""CREATE TABLE IF NOT EXISTS mutation_outbox(
                event_id TEXT PRIMARY KEY NOT NULL,
                body_json TEXT NOT NULL,
                exclusive INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                next_attempt_at INTEGER NOT NULL,
                queued_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                last_error TEXT
            )""".trimIndent())
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_mutation_outbox_due ON mutation_outbox(status,next_attempt_at,queued_at)")
        }
        private fun createV3(db: SQLiteDatabase) {
            db.execSQL("""CREATE TABLE IF NOT EXISTS local_history(
                event_id TEXT PRIMARY KEY NOT NULL,
                body_json TEXT NOT NULL,
                status TEXT NOT NULL,
                last_error TEXT,
                queued_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )""".trimIndent())
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_local_history_queued ON local_history(queued_at DESC)")
            // Preserve all already-existing outbox rows when upgrading Beta27 -> Beta28.
            db.execSQL("""INSERT OR IGNORE INTO local_history(event_id,body_json,status,last_error,queued_at,updated_at)
                SELECT event_id,body_json,status,COALESCE(last_error,''),queued_at,updated_at FROM mutation_outbox
            """.trimIndent())
        }
        private fun createV4(db:SQLiteDatabase){
            db.execSQL("""CREATE TABLE IF NOT EXISTS lan_event_replicas(
                event_id TEXT PRIMARY KEY NOT NULL,
                body_json TEXT NOT NULL,
                source_device TEXT NOT NULL,
                generation INTEGER NOT NULL,
                replica_role TEXT NOT NULL,
                stored_at INTEGER NOT NULL
            )""".trimIndent())
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_lan_event_generation ON lan_event_replicas(generation,stored_at)")
            db.execSQL("""CREATE TABLE IF NOT EXISTS lan_resource_reservations(
                resource_key TEXT PRIMARY KEY NOT NULL,
                event_id TEXT NOT NULL,
                mnv TEXT NOT NULL,
                generation INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )""".trimIndent())
            db.execSQL("""CREATE TABLE IF NOT EXISTS lan_meta(
                meta_key TEXT PRIMARY KEY NOT NULL,
                meta_value TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            )""".trimIndent())
        }
        private fun createV5(db:SQLiteDatabase){
            runCatching{db.execSQL("ALTER TABLE lan_event_replicas ADD COLUMN canonical_status TEXT NOT NULL DEFAULT 'PENDING'")}
            runCatching{db.execSQL("ALTER TABLE lan_event_replicas ADD COLUMN canonical_error TEXT NOT NULL DEFAULT ''")}
            runCatching{db.execSQL("ALTER TABLE lan_event_replicas ADD COLUMN canonical_at INTEGER NOT NULL DEFAULT 0")}
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_lan_event_canonical ON lan_event_replicas(canonical_status,stored_at)")
        }
        private fun createV6(db:SQLiteDatabase){
            db.execSQL("""CREATE TABLE IF NOT EXISTS resilience_test_events(
                event_id TEXT PRIMARY KEY NOT NULL,
                scenario TEXT NOT NULL,
                body_json TEXT NOT NULL,
                status TEXT NOT NULL,
                stage TEXT NOT NULL,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT NOT NULL DEFAULT '',
                evidence_json TEXT NOT NULL DEFAULT '{}',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )""".trimIndent())
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_resilience_test_updated ON resilience_test_events(updated_at DESC)")
        }

    }

    companion object {
        // Legacy filename retained intentionally for in-place migration; semantics are exact N..N-6.
        private const val DB_NAME = "pp_operational_45d.db"
        private const val DB_VERSION = 6
        private const val TZ = "Asia/Ho_Chi_Minh"
        private val DB_LOCK = Any()
        private val MEMORY = ConcurrentHashMap<String, JSONObject>()
        @Volatile private var HELPER: DbHelper? = null
        private fun helper(context: Context): DbHelper = HELPER ?: synchronized(DB_LOCK) { HELPER ?: DbHelper(context.applicationContext).also { HELPER = it } }
        private inline fun <T> withDbLock(block: () -> T): T = synchronized(DB_LOCK) { block() }
    }
}
