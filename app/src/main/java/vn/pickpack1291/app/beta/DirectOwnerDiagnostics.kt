package vn.pickpack1291.app.beta

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Sanitized rolling journal for direct Service owner/session calls that do not pass through the durable outbox.
 * Never stores password, bearer, token, cookie, verifier, secrets or arbitrary request bodies.
 */
object DirectOwnerDiagnostics {
    private const val PREFS = "pp1291_direct_owner_diag"
    private const val KEY_ROWS = "rows"
    private const val MAX_ROWS = 24

    @Synchronized
    fun record(context: Context, action: String, payload: JSONObject, result: BetaApiClient.Result) {
        val prefs = context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val rows = runCatching { JSONArray(prefs.getString(KEY_ROWS, "[]")) }.getOrDefault(JSONArray())
        val next = JSONArray()
        val row = JSONObject()
            .put("at", System.currentTimeMillis())
            .put("action", safe(action, 64))
            .put("ok", result.ok)
            .put("code", result.code)
            .put("error", safe(result.error, 120))
            .put("mnv", safe(payload.optString("mnv"), 80))
            .put("session_id", safe(payload.optString("session_id"), 180))
            .put("mutation_kind", safe(payload.optString("mutation_kind"), 32))
            .put("resource_type", safe(payload.optString("resource_type"), 40))
            .put("resource_id", safe(payload.optString("resource_id"), 120))
        next.put(row)
        val start = (rows.length() - (MAX_ROWS - 1)).coerceAtLeast(0)
        for (i in start until rows.length()) rows.optJSONObject(i)?.let(next::put)
        prefs.edit().putString(KEY_ROWS, next.toString()).apply()
    }

    fun snapshotLines(context: Context): List<String> {
        val prefs = context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val rows = runCatching { JSONArray(prefs.getString(KEY_ROWS, "[]")) }.getOrDefault(JSONArray())
        val out = mutableListOf<String>()
        out += "direct_owner_rows=${rows.length()}"
        for (i in 0 until rows.length()) {
            val x = rows.optJSONObject(i) ?: continue
            val prefix = "direct_owner[$i]"
            out += "$prefix.at=${formatAt(x.optLong("at"))}"
            out += "$prefix.action=${safe(x.optString("action"),64)}"
            out += "$prefix.ok=${x.optBoolean("ok")}"
            out += "$prefix.code=${x.optInt("code")}"
            out += "$prefix.error=${safe(x.optString("error"),120)}"
            out += "$prefix.mnv=${safe(x.optString("mnv"),80)}"
            out += "$prefix.session_id=${safe(x.optString("session_id"),180)}"
            out += "$prefix.mutation_kind=${safe(x.optString("mutation_kind"),32)}"
            out += "$prefix.resource_type=${safe(x.optString("resource_type"),40)}"
            out += "$prefix.resource_id=${safe(x.optString("resource_id"),120)}"
        }
        return out
    }

    @Synchronized
    fun clear(context: Context) {
        context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply()
    }

    private fun formatAt(value: Long): String = if (value <= 0L) "—" else
        SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSSZ", Locale.US).format(Date(value))

    private fun safe(value: String?, max: Int): String = value.orEmpty()
        .replace("\n", " ")
        .replace("\r", " ")
        .replace(Regex("(?i)(password|token|cookie|authorization|secret|verifier)\\s*[:=]\\s*[^,; ]+"), "$1=[REDACTED]")
        .take(max)
}
