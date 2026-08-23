package vn.pickpack1291.app.beta

import android.content.Context
import android.database.sqlite.SQLiteDatabase

/**
 * Beta57 owner reset fence.
 *
 * 1) Every newly queued mutation is stamped at INSERT time with the authority epoch/generation
 *    that existed when the business action was durably queued.
 * 2) When Service generation changes, unresolved rows from the previous generation are removed
 *    from the network outbox but retained in local_history as RESET_DISCARDED audit records.
 *
 * This prevents a pre-reset Beta queue from being replayed into a fresh Service authority epoch.
 */
object M2ResetFence {
    private const val DB_NAME = "pp_operational_45d.db"

    fun install(context: Context) {
        val app = context.applicationContext
        runCatching { OperationalDataStore(app).authorityEpoch() }
        val file = app.getDatabasePath(DB_NAME)
        if (!file.exists()) return

        var db: SQLiteDatabase? = null
        try {
            db = SQLiteDatabase.openDatabase(file.absolutePath, null, SQLiteDatabase.OPEN_READWRITE)
            db.execSQL(
                """
                CREATE TRIGGER IF NOT EXISTS pp_beta57_outbox_authority_fence
                AFTER INSERT ON mutation_outbox
                WHEN instr(NEW.body_json, '"authority_epoch"') = 0
                BEGIN
                  UPDATE mutation_outbox
                  SET body_json =
                    '{"authority_epoch":' ||
                    COALESCE((SELECT meta_value FROM sync_meta WHERE meta_key='authority_epoch'),'0') ||
                    ',"service_generation":"' ||
                    replace(COALESCE((SELECT meta_value FROM sync_meta WHERE meta_key='service_generation'),''),'"','') ||
                    '",' || substr(NEW.body_json,2)
                  WHERE event_id = NEW.event_id;
                END
                """.trimIndent()
            )
            db.execSQL(
                """
                CREATE TRIGGER IF NOT EXISTS pp_beta57_generation_reset_fence
                AFTER UPDATE OF meta_value ON sync_meta
                WHEN NEW.meta_key='service_generation'
                 AND OLD.meta_value<>NEW.meta_value
                BEGIN
                  UPDATE local_history
                  SET status='RESET_DISCARDED',
                      last_error='AUTHORITY_GENERATION_CHANGED',
                      updated_at=CAST(strftime('%s','now') AS INTEGER)*1000
                  WHERE event_id IN (
                    SELECT event_id FROM mutation_outbox
                    WHERE status IN ('LOCAL_PENDING','PENDING','RETRY','OFFLINE_PROVISIONAL')
                  );

                  DELETE FROM mutation_outbox
                  WHERE status IN ('LOCAL_PENDING','PENDING','RETRY','OFFLINE_PROVISIONAL');

                  DELETE FROM day_snapshot;
                END
                """.trimIndent()
            )
        } finally {
            runCatching { db?.close() }
        }
    }
}
