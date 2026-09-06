package vn.pickpack1291.app.beta

import android.content.Context
import org.json.JSONObject
import java.util.concurrent.Executors

/**
 * Foreground facade for the shared R5 day reconciler.
 * Realtime/status wakes are coalesced here; actual day sync is single-flight in M2DayReconciler.
 */
class OperationalSyncEngine(
    context: Context,
    @Suppress("UNUSED_PARAMETER") private val api: BetaApiClient,
    private val store: OperationalDataStore,
    private val listener: (Set<String>) -> Unit,
) {
    private data class Manifest(
        val businessDate: String,
        val retentionEpoch: Long,
        val revisions: Map<String, Long>,
    )

    private val app = context.applicationContext
    private val reconciler = M2DayReconciler(app, store)
    private val lock = Any()
    private var inFlight = false
    private var pending: Manifest? = null

    fun reconcile(
        businessDate: String,
        retentionFloor: String,
        retentionEpoch: Long,
        dayRevisions: JSONObject,
    ) {
        if (businessDate.isBlank()) return
        val revisions = LinkedHashMap<String, Long>()
        val keys = dayRevisions.keys()
        while (keys.hasNext()) {
            val date = keys.next().trim()
            if (date.isNotBlank()) revisions[date] = dayRevisions.optLong(date, 0L)
        }
        val exactWindow = revisions.entries
            .sortedByDescending { it.key }
            .take(7)
            .associateTo(LinkedHashMap()) { it.key to it.value }
        if (exactWindow.isEmpty()) return
        val canonicalBusinessDate = if (businessDate in exactWindow) businessDate else exactWindow.keys.first()
        val manifest = Manifest(canonicalBusinessDate, retentionEpoch, exactWindow)
        synchronized(lock) {
            if (inFlight) {
                pending = manifest
                return
            }
            inFlight = true
        }
        SYNC_EXECUTOR.execute { process(manifest) }
    }

    private fun process(manifest: Manifest) {
        try {
            val result = reconciler.reconcile(manifest.businessDate, manifest.retentionEpoch, manifest.revisions)
            if (result.changedDates.isNotEmpty()) listener(result.changedDates)
        } finally {
            finish()
        }
    }

    private fun finish() {
        val next: Manifest?
        synchronized(lock) {
            next = pending
            pending = null
            inFlight = false
        }
        if (next != null) {
            synchronized(lock) { inFlight = true }
            SYNC_EXECUTOR.execute { process(next) }
        }
    }

    companion object {
        private val SYNC_EXECUTOR = Executors.newSingleThreadExecutor { runnable ->
            Thread(runnable, "pp-operational-sync").apply { isDaemon = true }
        }
    }
}
