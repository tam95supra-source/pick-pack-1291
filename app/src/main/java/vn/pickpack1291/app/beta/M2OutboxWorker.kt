package vn.pickpack1291.app.beta

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import java.util.concurrent.TimeUnit
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/** Durable mutation delivery may run in background; the SQLite outbox is the source of retry truth. */
class M2OutboxFlushWorker(appContext: Context, params: WorkerParameters) : Worker(appContext, params) {
    override fun doWork(): Result = try {
        if (M2ServiceTransport(applicationContext).flushOutbox()) Result.success() else Result.retry()
    } catch (_: Throwable) { Result.retry() }
}

/** Background FCM/network recovery only. Foreground uses ForegroundSyncCoordinator + the same M2DayReconciler. */
class M2CatchUpWorker(appContext: Context, params: WorkerParameters) : Worker(appContext, params) {
    override fun doWork(): Result {
        if (PpForegroundGate.isForeground()) return Result.success()
        return try {
            val caughtUp = M2BackgroundSync.catchUp(applicationContext)
            M2PushRegistration.flush(applicationContext)
            if (caughtUp) Result.success() else Result.retry()
        } catch (_: Throwable) { Result.retry() }
    }
}

object M2ImmediateOutbox {
    private val running = AtomicBoolean(false)
    private val executor = Executors.newSingleThreadExecutor()

    fun kick(context: Context) {
        M2TransportDiagnostics.noteWake(context,"IMMEDIATE")
        val app = context.applicationContext
        if (!running.compareAndSet(false, true)) return
        executor.execute {
            try {
                if (!M2ServiceTransport(app).flushOutbox()) M2WorkScheduler.scheduleOutbox(app)
            } catch (_: Throwable) {
                M2WorkScheduler.scheduleOutbox(app)
            } finally {
                running.set(false)
            }
        }
    }
}

object M2WorkScheduler {
    private const val FLUSH_UNIQUE = "pick-pack-1291-m2-outbox-flush"
    private const val CATCHUP_UNIQUE = "pick-pack-1291-m2-catchup"

    /** Backward-compatible call sites now mean durable outbox only; catch-up requires an explicit reason. */
    fun schedule(context: Context) = scheduleOutbox(context)

    fun scheduleOutbox(context: Context) {
        M2TransportDiagnostics.noteWake(context,"WORKMANAGER_OUTBOX")
        val app = context.applicationContext
        val constraints = Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()
        val flush = OneTimeWorkRequestBuilder<M2OutboxFlushWorker>()
            .setConstraints(constraints)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.SECONDS)
            .build()
        WorkManager.getInstance(app).enqueueUniqueWork(FLUSH_UNIQUE, ExistingWorkPolicy.REPLACE, flush)
    }

    fun scheduleCatchUp(context: Context) {
        M2TransportDiagnostics.noteWake(context,"WORKMANAGER_CATCHUP")
        val app = context.applicationContext
        val constraints = Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()
        val catchUp = OneTimeWorkRequestBuilder<M2CatchUpWorker>()
            .setConstraints(constraints)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.SECONDS)
            .build()
        WorkManager.getInstance(app).enqueueUniqueWork(CATCHUP_UNIQUE, ExistingWorkPolicy.KEEP, catchUp)
    }
}

object M2ConnectivityMonitor {
    private val started = AtomicBoolean(false)
    fun start(context: Context) {
        if (!started.compareAndSet(false, true)) return
        val app = context.applicationContext
        val cm = app.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        runCatching {
            cm.registerDefaultNetworkCallback(object : ConnectivityManager.NetworkCallback() {
                override fun onAvailable(network: Network) {
                    M2WorkScheduler.scheduleOutbox(app)
                    if (!PpForegroundGate.isForeground()) M2WorkScheduler.scheduleCatchUp(app)
                }
            })
        }.onFailure { started.set(false) }
    }
}
