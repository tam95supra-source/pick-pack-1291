from pathlib import Path

MARKER='S59_BETA56_AUTO_OTA'

def once(s,old,new,label):
    if new in s:return s
    if old not in s:raise SystemExit('missing anchor: '+label)
    return s.replace(old,new,1)

# UpdateManager: silent automatic check with network throttle and offer cooldown.
p=Path('app/src/main/java/vn/pickpack1291/app/beta/UpdateManager.kt')
s=p.read_text()
old='''object UpdateManager {\n    private var busy = false\n\n    fun openManual(activity: Activity) {'''
new='''object UpdateManager {\n    // S59_BETA56_AUTO_OTA: automatic foreground OTA detection for both BETA and STABLE channels.\n    private var busy = false\n    private var automaticBusy = false\n    private const val PREFS = "pp_update_manager"\n    private const val KEY_LAST_AUTO_CHECK_AT = "last_auto_check_at"\n    private const val KEY_LAST_OFFER_VERSION = "last_offer_version"\n    private const val KEY_LAST_OFFER_AT = "last_offer_at"\n    private const val AUTO_CHECK_INTERVAL_MS = 15L * 60L * 1000L\n    private const val SAME_OFFER_COOLDOWN_MS = 2L * 60L * 60L * 1000L\n\n    fun checkAutomatic(activity: Activity) {\n        if (automaticBusy || busy || activity.isFinishing || activity.isDestroyed) return\n        val prefs = activity.getSharedPreferences(PREFS, Context.MODE_PRIVATE)\n        val now = System.currentTimeMillis()\n        val lastCheck = prefs.getLong(KEY_LAST_AUTO_CHECK_AT, 0L)\n        if (lastCheck > 0L && now - lastCheck < AUTO_CHECK_INTERVAL_MS) return\n        prefs.edit().putLong(KEY_LAST_AUTO_CHECK_AT, now).apply()\n        automaticBusy = true\n        BetaApiClient(activity.applicationContext).updateCheck(BuildConfig.CHANNEL, BuildConfig.VERSION_NAME) { result ->\n            activity.runOnUiThread {\n                automaticBusy = false\n                if (activity.isFinishing || activity.isDestroyed || !result.ok) return@runOnUiThread\n                val j = result.json ?: return@runOnUiThread\n                if (!j.optBoolean("available", false)) return@runOnUiThread\n                val version = j.optString("version_name").trim()\n                val url = j.optString("apk_url").trim()\n                val sha = j.optString("sha256").trim()\n                val notes = j.optString("notes").trim().take(4000)\n                if (version.isBlank() || url.isBlank() || version == BuildConfig.VERSION_NAME) return@runOnUiThread\n                val lastVersion = prefs.getString(KEY_LAST_OFFER_VERSION, "").orEmpty()\n                val lastOfferAt = prefs.getLong(KEY_LAST_OFFER_AT, 0L)\n                val offerNow = System.currentTimeMillis()\n                if (lastVersion == version && lastOfferAt > 0L && offerNow - lastOfferAt < SAME_OFFER_COOLDOWN_MS) return@runOnUiThread\n                prefs.edit().putString(KEY_LAST_OFFER_VERSION, version).putLong(KEY_LAST_OFFER_AT, offerNow).apply()\n                showRelease(activity, version, url, sha, notes)\n            }\n        }\n    }\n\n    fun openManual(activity: Activity) {'''
s=once(s,old,new,'UpdateManager object')
s=s.replace('''Sau đó quay lại ứng dụng và bấm KIỂM TRA CẬP NHẬT lại; ứng dụng sẽ không tự kiểm tra.''','''Sau đó quay lại ứng dụng. Ứng dụng sẽ tự kiểm tra lại khi vào foreground; bạn cũng có thể bấm KIỂM TRA CẬP NHẬT trong Cài đặt.''')
p.write_text(s)

# Launcher: auto-check while login screen is visible. Logged-in path immediately opens OperationsActivity,
# which performs its own foreground check.
p=Path('app/src/main/java/vn/pickpack1291/app/beta/FullBetaActivity.kt')
s=p.read_text()
old='''    override fun onStart() {\n        super.onStart()\n        if (api.token != null) foregroundSync.start()\n    }'''
new='''    override fun onStart() {\n        super.onStart()\n        if (api.token != null) foregroundSync.start()\n        else UpdateManager.checkAutomatic(this) // S59_BETA56_AUTO_OTA\n    }'''
s=once(s,old,new,'FullBeta onStart')
p.write_text(s)

# Main operational activity: one throttled automatic OTA check whenever app returns to foreground.
p=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
s=p.read_text()
old='''    override fun onStart() {\n        super.onStart()\n        PpForegroundGate.enter()'''
new='''    override fun onStart() {\n        super.onStart()\n        UpdateManager.checkAutomatic(this) // S59_BETA56_AUTO_OTA\n        PpForegroundGate.enter()'''
s=once(s,old,new,'Operations onStart')
p.write_text(s)

# Bump only Beta; Stable metadata remains immutable.
p=Path('app/build.gradle.kts')
s=p.read_text()
s=once(s,'versionCode = 61\n            versionName = "0.4.2-beta.55"','versionCode = 62\n            versionName = "0.4.2-beta.56"','Beta metadata')
if '// Beta56:' not in s:
    s=s.replace('// Beta55: restores Cloudflare -> Google/GAS fallback, truthful fault-test routing, Beta54 resilience retained.','// Beta55: restores Cloudflare -> Google/GAS fallback, truthful fault-test routing, Beta54 resilience retained.\n// Beta56: automatic foreground OTA detection for Beta and Stable channels; manual check retained.')
p.write_text(s)

print(MARKER)
