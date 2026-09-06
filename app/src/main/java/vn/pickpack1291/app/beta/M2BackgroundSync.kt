package vn.pickpack1291.app.beta

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URLEncoder
import java.net.URL

/**
 * Background catch-up invoked by WorkManager after FCM/network recovery.
 * The same M2DayReconciler used by foreground owns revision/delta/reset semantics.
 */
object M2BackgroundSync {
    private val masterNamespaces = listOf("employees", "catalogs", "pda", "user_pick", "pack_table", "user_pack")

    fun catchUp(context: Context): Boolean {
        val app = context.applicationContext
        val transport = M2ServiceTransport(app)
        val statusResult = transport.sync("sync_status", JSONObject())
        if (!statusResult.handled || !statusResult.ok || statusResult.json == null) return false
        val status = statusResult.json
        val store = OperationalDataStore(app)

        val dayRevisions = status.optJSONObject("day_revisions") ?: JSONObject()
        val revisions = LinkedHashMap<String, Long>()
        val keys = dayRevisions.keys()
        while (keys.hasNext()) {
            val date = keys.next().trim()
            if (date.isNotBlank()) revisions[date] = dayRevisions.optLong(date, 0L)
        }
        val ordered = revisions.entries.sortedByDescending { it.key }.take(7).associateTo(LinkedHashMap()) { it.key to it.value }
        if (ordered.isEmpty()) return false

        status.optJSONObject("authority")?.let(store::saveAuthority)
        val businessDate = status.optString("business_date").ifBlank { ordered.keys.first() }
        val retentionEpoch = status.optLong("retention_epoch", store.authorityEpoch())
        val result = M2DayReconciler(app, store).reconcile(businessDate, retentionEpoch, ordered)

        refreshMasterIfChanged(app, transport.cachedDiscoverySnapshot())
        return result.ok || result.busy
    }

    private fun refreshMasterIfChanged(context: Context, discovery: JSONObject?) {
        val d = discovery ?: return
        if (d.optString("authority_mode") != "SERVICE_PRIMARY") return
        val base = d.optString("service_url").trimEnd('/')
        val token = context.getSharedPreferences("pp_m2_service_transport", Context.MODE_PRIVATE).getString("service_token", null).orEmpty()
        if (base.isBlank() || token.isBlank()) return
        val status = getJson("$base/v1/sync/status", token) ?: return
        val revisions = status.optJSONObject("master_revisions") ?: return
        val localRev = context.getSharedPreferences("pp_m2_master_revision", Context.MODE_PRIVATE)
        val changed = masterNamespaces.filter { revisions.optLong(it, 0L) != localRev.getLong(it, -1L) }
        if (changed.isEmpty()) return

        val snapshot = MasterDataCache.snapshot(context)?.let { JSONObject(it.toString()) } ?: JSONObject()
        snapshot.put("ok", true)
        var maxRevision = snapshot.optLong("master_revision", 0L)

        for (namespace in changed) {
            val url = "$base/v1/delta/master?namespace=${URLEncoder.encode(namespace, "UTF-8")}&after_revision=0"
            val delta = getJson(url, token) ?: return
            val rows = delta.optJSONArray("rows") ?: JSONArray()
            when (namespace) {
                "employees" -> snapshot.put("staff", JSONArray(rows.toString()))
                "catalogs" -> snapshot.put("catalogs", JSONArray(rows.toString()))
                "pda" -> snapshot.put("pdas", resourceRows(rows, "PDA"))
                "user_pick" -> snapshot.put("user_picks", resourceRows(rows, "USER_PICK"))
                "user_pack" -> snapshot.put("user_packs", resourceRows(rows, "USER_PACK"))
                "pack_table" -> snapshot.put("pack_bundles", JSONArray(rows.toString()))
            }
            maxRevision = maxOf(maxRevision, revisions.optLong(namespace, 0L))
        }
        snapshot.put("master_revision", maxRevision)
        MasterDataCache.save(context, snapshot)

        val edit = localRev.edit()
        changed.forEach { edit.putLong(it, revisions.optLong(it, 0L)) }
        edit.apply()
    }

    private fun resourceRows(rows: JSONArray, type: String): JSONArray = JSONArray().apply {
        for (i in 0 until rows.length()) {
            val source = rows.optJSONObject(i) ?: continue
            val row = JSONObject(source.toString())
            val id = source.optString("resource_id")
            val metadata = runCatching { JSONObject(source.optString("metadata_json", "{}")) }.getOrNull()
            if (metadata != null) {
                val keys = metadata.keys()
                while (keys.hasNext()) {
                    val key = keys.next()
                    if (!row.has(key)) row.put(key, metadata.opt(key))
                }
            }
            when (type) {
                "PDA" -> { if (!row.has("serial")) row.put("serial", id); if (!row.has("pda")) row.put("pda", id) }
                "USER_PICK" -> if (!row.has("user_pick")) row.put("user_pick", id)
                "USER_PACK" -> if (!row.has("user_pack")) row.put("user_pack", id)
            }
            put(row)
        }
    }

    private fun getJson(endpoint: String, bearer: String): JSONObject? {
        var conn: HttpURLConnection? = null
        return try {
            conn = (URL(endpoint).openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"; connectTimeout = 4_000; readTimeout = 8_000
                setRequestProperty("Accept", "application/json")
                setRequestProperty("Authorization", "Bearer $bearer")
            }
            if (conn.responseCode !in 200..299) return null
            val text = conn.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            JSONObject(text).takeIf { it.optBoolean("ok", false) }
        } catch (_: Throwable) { null } finally { conn?.disconnect() }
    }
}
