package vn.pickpack1291.app.beta

import android.content.Context

/** Rolling QR phase timing stored in SharedPreferences; no per-scan files and no network writes. */
object QrPerformanceDiagnostics {
    private const val PREFS="pp_qr_perf_v95"
    @Synchronized fun recordLocal(context:Context,mnv:String,resolveMs:Long,projectionMs:Long,renderMs:Long,state:String,source:String){
        val p=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE)
        val count=p.getLong("count",0L)+1L
        p.edit()
            .putLong("count",count)
            .putLong("latest_at",System.currentTimeMillis())
            .putString("mnv",mnv.take(40))
            .putLong("resolve_ms",resolveMs.coerceAtLeast(0))
            .putLong("projection_ms",projectionMs.coerceAtLeast(0))
            .putLong("render_ms",renderMs.coerceAtLeast(0))
            .putString("state",state.take(40))
            .putString("source",source.take(80))
            .putLong("local_total_sum",p.getLong("local_total_sum",0L)+(resolveMs+projectionMs+renderMs).coerceAtLeast(0))
            .apply()
    }
    @Synchronized fun recordService(context:Context,mnv:String,totalMs:Long,serviceRttMs:Long?,patched:Boolean,resultCode:Int){
        context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit()
            .putString("service_mnv",mnv.take(40))
            .putLong("service_total_ms",totalMs.coerceAtLeast(0))
            .putLong("service_rtt_ms",serviceRttMs?:-1L)
            .putBoolean("service_patched",patched)
            .putInt("service_code",resultCode)
            .apply()
    }
    fun snapshotLines(context:Context):List<String>{
        val p=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE);val count=p.getLong("count",0L)
        val avg=if(count>0)p.getLong("local_total_sum",0L)/count else -1L
        return listOf(
            "qr_perf.count=$count",
            "qr_perf.latest_at=${p.getLong("latest_at",0L)}",
            "qr_perf.mnv=${p.getString("mnv","").orEmpty()}",
            "qr_perf.resolve_ms=${p.getLong("resolve_ms",-1L)}",
            "qr_perf.projection_ms=${p.getLong("projection_ms",-1L)}",
            "qr_perf.render_ms=${p.getLong("render_ms",-1L)}",
            "qr_perf.local_total_avg_ms=$avg",
            "qr_perf.state=${p.getString("state","").orEmpty()}",
            "qr_perf.source=${p.getString("source","").orEmpty()}",
            "qr_perf.service_total_ms=${p.getLong("service_total_ms",-1L)}",
            "qr_perf.service_rtt_ms=${p.getLong("service_rtt_ms",-1L)}",
            "qr_perf.service_patched=${p.getBoolean("service_patched",false)}",
            "qr_perf.service_code=${p.getInt("service_code",0)}"
        )
    }
}
