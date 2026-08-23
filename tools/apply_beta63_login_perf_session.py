#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / "app/src/main/java/vn/pickpack1291/app/beta/FullBetaActivity.kt"
API = ROOT / "app/src/main/java/vn/pickpack1291/app/beta/BetaApiClient.kt"
OPS = ROOT / "app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt"
GRADLE = ROOT / "app/build.gradle.kts"

LOGIN_FUNCTION = r'''    private fun login() {
        foregroundSync.stop()
        liveEmployeeMnv = ""
        currentScreen = "LOGIN"
        accountLogin = ""; accountName = ""; accountRole = ""; accountPosition = ""; accountEmail = ""

        window.statusBarColor = Color.rgb(218, 29, 22)
        window.navigationBarColor = Color.rgb(5, 45, 91)
        @Suppress("DEPRECATION")
        window.decorView.systemUiVisibility = 0

        val compact = resources.configuration.screenHeightDp < 690 || resources.configuration.screenWidthDp < 360
        val veryCompact = resources.configuration.screenHeightDp < 590
        val user = EditText(this).apply {
            hint = "Tài khoản"; setSingleLine(true); textSize = if(compact) 14f else 15f
            setTextColor(Color.rgb(28, 50, 77)); setHintTextColor(Color.rgb(145, 155, 170)); background = null
            setPadding(dp(6), 0, dp(4), 0); imeOptions = EditorInfo.IME_ACTION_NEXT
        }
        val saved = getPreferences(MODE_PRIVATE).getString("last_login", "").orEmpty()
        if (saved.isNotBlank()) user.setText(saved)
        val pass = EditText(this).apply {
            hint = "Mật khẩu"; setSingleLine(true); textSize = if(compact) 14f else 15f
            setTextColor(Color.rgb(28, 50, 77)); setHintTextColor(Color.rgb(145, 155, 170)); background = null
            setPadding(dp(6), 0, dp(4), 0); imeOptions = EditorInfo.IME_ACTION_DONE
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        }

        fun loginField(iconRes: Int, field: EditText, trailing: View? = null): LinearLayout = row(Color.WHITE).apply {
            gravity = Gravity.CENTER_VERTICAL
            minimumHeight = dp(if(compact) 48 else 54)
            setPadding(dp(12), dp(3), dp(8), dp(3))
            background = GradientDrawable().apply {
                shape = GradientDrawable.RECTANGLE
                cornerRadius = dp(11).toFloat()
                setColor(Color.argb(248, 255, 255, 255))
                setStroke(dp(1), Color.rgb(187, 198, 212))
            }
            addView(ImageView(this@FullBetaActivity).apply {
                setImageResource(iconRes); scaleType = ImageView.ScaleType.CENTER_INSIDE
            }, size(dp(27), dp(27)))
            addView(field, LinearLayout.LayoutParams(0, dp(if(compact) 44 else 48), 1f))
            if (trailing != null) addView(trailing, size(dp(42), dp(42)))
        }

        var passwordVisible = false
        val eye = ImageButton(this).apply {
            setImageResource(R.drawable.ic_login_eye); setBackgroundColor(Color.TRANSPARENT); contentDescription = "Hiện mật khẩu"
            setPadding(dp(8), dp(8), dp(8), dp(8)); alpha = 0.82f
            setOnClickListener {
                passwordVisible = !passwordVisible
                val cursor = pass.selectionStart.coerceAtLeast(0)
                pass.inputType = InputType.TYPE_CLASS_TEXT or if(passwordVisible) InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD else InputType.TYPE_TEXT_VARIATION_PASSWORD
                pass.setSelection(cursor.coerceAtMost(pass.text.length)); alpha = if(passwordVisible) 1f else 0.82f
                contentDescription = if(passwordVisible) "Ẩn mật khẩu" else "Hiện mật khẩu"
            }
        }

        val card = column(Color.WHITE).apply {
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(dp(if(compact) 18 else 24), dp(if(compact) 16 else 22), dp(if(compact) 18 else 24), dp(if(compact) 17 else 22))
            background = GradientDrawable().apply {
                shape = GradientDrawable.RECTANGLE; cornerRadius = dp(24).toFloat(); setColor(Color.argb(250,255,255,255))
                setStroke(dp(1), Color.argb(70, 114, 139, 170))
            }
            elevation = dp(11).toFloat()
            clipToOutline = false
        }

        card.addView(ImageView(this).apply {
            setImageResource(R.drawable.login_supra_logo); adjustViewBounds = true; scaleType = ImageView.ScaleType.FIT_CENTER
        }, size(dp(if(compact) 122 else 142), dp(if(compact) 140 else 164)))
        card.addView(txt("Supra DC Hưng Yên", if(compact) 17f else 19f, Color.rgb(17, 75, 151), true).center())
        card.addView(gap(if(compact) 13 else 17))
        card.addView(loginField(R.drawable.ic_login_user, user), matchWrap())
        card.addView(gap(if(compact) 8 else 10))
        card.addView(loginField(R.drawable.ic_login_lock, pass, eye), matchWrap())
        card.addView(gap(4))

        val forgot = TextView(this).apply {
            text = "Quên mật khẩu?"; textSize = if(compact) 11.5f else 12f; setTextColor(Color.rgb(12, 72, 156)); typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.END; setPadding(dp(6), dp(6), 0, dp(7))
            setOnClickListener {
                val loginId = user.text.toString().trim()
                if (loginId.isBlank()) { toast("Nhập đúng tài khoản trước khi chọn Quên mật khẩu."); return@setOnClickListener }
                isEnabled = false; text = "Đang gửi yêu cầu..."
                api.forgotPassword(loginId) { r -> runOnUiThread {
                    isEnabled = true; text = "Quên mật khẩu?"
                    if (!r.ok) { showError(r.error ?: "Không gửi được yêu cầu đặt lại mật khẩu"); return@runOnUiThread }
                    TopNotice.show(this@FullBetaActivity,"Nếu tài khoản hợp lệ, mật khẩu mới đã được gửi tới mail đã cấu hình.",TopNotice.Kind.SUCCESS)
                } }
            }
        }
        card.addView(forgot, matchWrap())
        card.addView(gap(if(compact) 5 else 7))

        val button = Button(this).apply {
            text = "Đăng nhập"; textSize = if(compact) 15f else 16f; setTextColor(Color.WHITE); typeface = Typeface.DEFAULT_BOLD
            isAllCaps = false; minimumHeight = dp(if(compact) 49 else 54); background = gradient(Color.rgb(17, 84, 184), Color.rgb(6, 57, 137), 13)
        }
        fun submit() {
            val login = user.text.toString().trim(); val password = pass.text.toString()
            if (login.isBlank() || password.isBlank()) { toast("Nhập tài khoản và mật khẩu."); return }
            button.isEnabled = false; button.text = "Đang xác thực..."
            api.login(login, password) { result -> runOnUiThread {
                button.isEnabled = true; button.text = "Đăng nhập"
                if (!result.ok) { showError(result.error ?: "Đăng nhập thất bại"); return@runOnUiThread }
                val a = result.json?.optJSONObject("account") ?: JSONObject()
                accountLogin = a.optString("login_id", login)
                accountName = a.optString("display_name", accountLogin)
                accountRole = a.optString("role", "USER")
                accountPosition = a.optString("position", "")
                accountEmail = a.optString("email", "")
                getPreferences(MODE_PRIVATE).edit().putString("last_login", accountLogin).apply()
                pass.setText("")
                openMainShell()
                if (MasterDataCache.revision(this@FullBetaActivity) == 0L) refreshMasterCache()
                LocalLogManager.uploadAutomaticPending(this@FullBetaActivity, api)
            } }
        }
        button.setOnClickListener { submit() }
        user.setOnEditorActionListener { _, actionId, _ -> if(actionId == EditorInfo.IME_ACTION_NEXT){ pass.requestFocus(); true } else false }
        pass.setOnEditorActionListener { _, actionId, _ -> if (actionId == EditorInfo.IME_ACTION_DONE) { submit(); true } else false }
        card.addView(button, matchWrap())
        card.addView(gap(if(compact) 8 else 10))
        card.addView(Button(this).apply {
            text = "Đăng ký"; textSize = if(compact) 13f else 14f; setTextColor(Color.rgb(13, 73, 155)); typeface = Typeface.DEFAULT_BOLD; isAllCaps = false
            minimumHeight = dp(if(compact) 47 else 51)
            background = GradientDrawable().apply { shape = GradientDrawable.RECTANGLE; cornerRadius = dp(12).toFloat(); setColor(Color.argb(246,255,255,255)); setStroke(dp(1), Color.rgb(22, 82, 168)) }
            setOnClickListener { TopNotice.show(this@FullBetaActivity,"Tính năng đăng ký đang được xây dựng.",TopNotice.Kind.INFO) }
        }, matchWrap())

        val root = FrameLayout(this).apply {
            setBackgroundColor(Color.rgb(247, 238, 214))
            addView(ImageView(this@FullBetaActivity).apply {
                setImageResource(R.drawable.login_vietnam_bg); scaleType = ImageView.ScaleType.CENTER_CROP
            }, FrameLayout.LayoutParams(-1, -1))
        }
        val scroll = ScrollView(this).apply { isFillViewport = true; isVerticalScrollBarEnabled = false }
        val stage = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER_HORIZONTAL
            val top = when { veryCompact -> dp(72); compact -> dp(105); else -> dp(155) }
            val bottom = if(veryCompact) dp(28) else dp(88)
            setPadding(dp(16), top, dp(16), bottom)
            addView(card, LinearLayout.LayoutParams(minOf(dp(430), resources.displayMetrics.widthPixels - dp(32)), -2))
        }
        scroll.addView(stage, ViewGroup.LayoutParams(-1, -2)); root.addView(scroll, FrameLayout.LayoutParams(-1, -1))
        setScreen(root)
        user.requestFocus()
    }
'''


def replace_between(text: str, start: str, end: str, replacement: str) -> str:
    i = text.find(start)
    if i < 0:
        raise SystemExit(f"missing start anchor: {start}")
    j = text.find(end, i)
    if j < 0:
        raise SystemExit(f"missing end anchor: {end}")
    return text[:i] + replacement + text[j:]


def replace_first_call_block(text: str, marker: str, replacement: str) -> str:
    i = text.find(marker)
    if i < 0:
        if replacement.strip().splitlines()[0].strip() in text:
            return text
        raise SystemExit(f"missing call marker: {marker}")
    brace = text.find("{", i)
    depth = 0
    quote = None
    escaped = False
    for pos in range(brace, len(text)):
        ch = text[pos]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[:i] + replacement + text[pos + 1:]
    raise SystemExit(f"unclosed call block: {marker}")


full = FULL.read_text()
if "R.drawable.login_vietnam_bg" not in full:
    full = replace_between(full, "    private fun login() {\n", "\n    private fun openMainShell()", LOGIN_FUNCTION,)
FULL.write_text(full)

api = API.read_text()
old_login_tail = '''                if (result.ok) {
                    val newToken = result.json?.optString("token")?.takeIf { it.isNotBlank() }
                    if (newToken != null) persistSession(newToken, result.json.optJSONObject("account"))
                    m2Transport.loginFromPassword(login, password)
                }
                callback(result)'''
new_login_tail = '''                if (result.ok) {
                    val newToken = result.json?.optString("token")?.takeIf { it.isNotBlank() }
                    if (newToken != null) {
                        persistSession(newToken, result.json.optJSONObject("account"))
                        // Beta63: UI success is not blocked by a second PBKDF2/password login to Service.
                        // Warm the Service bearer asynchronously via inherited GAS-session exchange.
                        localExecutor.execute { runCatching { m2Runtime.ensureServiceSession(newToken, force = false) } }
                    }
                }
                callback(result)'''
if old_login_tail in api:
    api = api.replace(old_login_tail, new_login_tail, 1)
elif "m2Transport.loginFromPassword(login, password)" in api:
    raise SystemExit("unexpected BetaApiClient login shape")

if "fun logoutFast()" not in api:
    anchor = '''    fun clearSession() {
        // S24_FCM_LOGOUT_REVOKE_APPLIED: capture current Service session before clearing auth.
        M2PushRegistration.revoke(appContext)
        synchronized(sessionLock) { sharedToken = null }
        prefs.edit().remove(KEY_TOKEN).remove(KEY_LOGIN).remove(KEY_NAME).remove(KEY_ROLE).remove(KEY_POSITION).remove(KEY_EMAIL).apply()
        m2Runtime.clear()
    }
'''
    insert = anchor + '''
    /** Clear local auth immediately; remote GAS logout is best-effort and never blocks navigation. */
    fun logoutFast() {
        val captured = synchronized(sessionLock) { sharedToken }
        clearSession()
        if (captured.isNullOrBlank()) return
        executor.execute {
            runCatching { post(JSONObject().put("action", "logout"), authenticated = true, authTokenOverride = captured) }
        }
    }
'''
    if anchor not in api: raise SystemExit("clearSession anchor drift")
    api = api.replace(anchor, insert, 1)

api = api.replace("    private fun post(payload: JSONObject, authenticated: Boolean): Result {", "    private fun post(payload: JSONObject, authenticated: Boolean, authTokenOverride: String? = null): Result {", 1)
api = api.replace('                val t = sharedToken ?: return Result(false, 401, JSONObject().put("ok", false).put("error", "UNAUTHORIZED"), "UNAUTHORIZED")', '                val t = authTokenOverride ?: synchronized(sessionLock) { sharedToken } ?: return Result(false, 401, JSONObject().put("ok", false).put("error", "UNAUTHORIZED"), "UNAUTHORIZED")', 1)
old_retry = '''        // One same-idempotency retry is safe for an atomic optimistic race; deterministic lease/validation conflicts remain errors.
        if(action=="session_work_update" && result.code==409 && result.error=="SESSION_WORK_CONFLICT") result=request(bearer)
        return result'''
new_retry = '''        // Beta63: bounded same-idempotency retries only for the optimistic authority/session race.
        // Deterministic lease/resource/validation conflicts remain visible errors and are never coerced to success.
        if(action=="session_work_update") {
            var retry=0
            while(result.code==409 && result.error=="SESSION_WORK_CONFLICT" && retry<2) {
                Thread.sleep(if(retry==0) 40L else 120L)
                result=request(bearer)
                retry++
            }
        }
        return result'''
if old_retry in api:
    api = api.replace(old_retry, new_retry, 1)
elif "retry<2" not in api:
    raise SystemExit("session_work_update retry anchor drift")
API.write_text(api)

ops = OPS.read_text()
if 'api.logoutFast()' not in ops:
    replacement = '''api.logoutFast()
            startActivity(android.content.Intent(this, FullBetaActivity::class.java).apply {
                flags = android.content.Intent.FLAG_ACTIVITY_NEW_TASK or android.content.Intent.FLAG_ACTIVITY_CLEAR_TASK
            })
            finish()
            @Suppress("DEPRECATION")
            overridePendingTransition(0, 0)'''
    ops = replace_first_call_block(ops, 'api.call("logout"){', replacement)
OPS.write_text(ops)

gradle = GRADLE.read_text()
gradle = gradle.replace('versionCode = 68\n            versionName = "0.4.2-beta.62"', 'versionCode = 69\n            versionName = "0.4.2-beta.63"', 1)
gradle = gradle.replace('// Beta62: owner UI polish, strict provider fault injection, PDA exchange confirmation, mutation diagnostics and login redesign.', '// Beta63: responsive Vietnam/Supra login, non-blocking auth teardown/warm-up, bounded session-work conflict recovery.\n// Beta62 remains immutable and is the previous public baseline.', 1)
if 'versionCode = 1\n            versionName = "0.1.0-stable"' not in gradle:
    raise SystemExit("Stable identity drift detected")
GRADLE.write_text(gradle)

# Semantic safety assertions: fail closed on drift.
checks = {
    "beta63 version": 'versionName = "0.4.2-beta.63"' in GRADLE.read_text(),
    "stable untouched": 'versionCode = 1\n            versionName = "0.1.0-stable"' in GRADLE.read_text(),
    "Vietnam login background": "R.drawable.login_vietnam_bg" in FULL.read_text(),
    "Supra logo": "R.drawable.login_supra_logo" in FULL.read_text(),
    "fast logout": "api.logoutFast()" in OPS.read_text(),
    "no duplicate password Service login": "m2Transport.loginFromPassword(login, password)" not in API.read_text(),
    "inherited Service warmup": "m2Runtime.ensureServiceSession(newToken, force = false)" in API.read_text(),
    "bounded work retry": "retry<2" in API.read_text(),
}
failed = [k for k,v in checks.items() if not v]
if failed:
    raise SystemExit("Beta63 semantic checks failed: " + ", ".join(failed))
print("Beta63 materialization PASS")
