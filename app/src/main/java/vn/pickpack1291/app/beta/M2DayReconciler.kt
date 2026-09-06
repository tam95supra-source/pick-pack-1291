package vn.pickpack1291.app.beta

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.atomic.AtomicBoolean

/**
 * R5 single logical day reconciler shared by foreground and background wakes.
 * Normal path is revision-indexed delta; full sync_day is a bounded reset only.
 */
class M2DayReconciler(context: Context, private val store: OperationalDataStore = OperationalDataStore(context.applicationContext)) {
    data class Result(val ok: Boolean, val busy: Boolean, val changedDates: Set<String>)

    private val app = context.applicationContext
    private val transport = M2ServiceTransport(app)

    fun reconcile(
        businessDate: String,
        retentionEpoch: Long,
        revisions: Map<String, Long>,
    ): Result {
        if (businessDate.isBlank() || revisions.isEmpty()) return Result(false, false, emptySet())
        if (!RUNNING.compareAndSet(false, true)) return Result(true, true, emptySet())
        val changed = linkedSetOf<String>()
        return try {
            val window = revisions.keys.sortedDescending().take(7)
            store.applyBusinessWindow(window, retentionEpoch)
            store.putMeta("business_date", if (businessDate in window) businessDate else window.first())
            store.putMeta("retention_floor", window.last())
            store.putMeta("retention_epoch", retentionEpoch.toString())

            for (date in window) {
                val remoteRevision = revisions[date] ?: continue
                var localRevision = store.revision(date)
                if (localRevision == remoteRevision) continue

                if (localRevision <= 0L || localRevision > remoteRevision) {
                    if (!resetDay(date)) return Result(false, false, changed)
                    changed += date
                    continue
                }

                var pages = 0
                var reset = false
                while (localRevision < remoteRevision && pages++ < 16) {
                    val delta = transport.sync(
                        "sync_delta",
                        JSONObject().put("business_date", date).put("after_revision", localRevision),
                    )
                    val body = delta.json
                    if (!delta.handled || !delta.ok || body == null || body.optBoolean("reset_required", false)) {
                        reset = true
                        break
                    }
                    val toRevision = body.optLong("to_revision", localRevision)
                    val items = body.optJSONArray("items") ?: JSONArray()
                    if (toRevision <= localRevision || !store.applyDayDelta(date, toRevision, items)) {
                        reset = true
                        break
                    }
                    localRevision = toRevision
                    changed += date
                    if (!body.optBoolean("has_more", false) && localRevision >= remoteRevision) break
                    if (!body.optBoolean("has_more", false) && localRevision < remoteRevision) {
                        reset = true
                        break
                    }
                }
                if (localRevision < remoteRevision) reset = true
                if (reset) {
                    if (!resetDay(date)) return Result(false, false, changed)
                    changed += date
                }
            }
            Result(true, false, changed)
        } catch (_: Throwable) {
            Result(false, false, changed)
        } finally {
            RUNNING.set(false)
        }
    }

    private fun resetDay(date: String): Boolean {
        val day = transport.sync("sync_day", JSONObject().put("business_date", date))
        val snapshot = if (day.handled && day.ok) day.json?.optJSONObject("day") else null
        if (snapshot == null) return false
        store.saveDay(snapshot)
        return true
    }

    companion object {
        private val RUNNING = AtomicBoolean(false)
        fun busy(): Boolean = RUNNING.get()
    }
}
