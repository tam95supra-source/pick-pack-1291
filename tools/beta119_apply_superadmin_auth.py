#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"BETA119_PATCH_FAIL:{label}:count={count}")
    return text.replace(old, new, 1)


# 1) Preserve authenticated session across APK/process restart; explicit logout/401 remains authoritative.
p = "app/src/main/java/vn/pickpack1291/app/beta/MainActivity.kt"
s = read(p)
s = replace_once(
    s,
    '''        LocalLogManager.createDailyIfNeeded(this)\n        login()\n    }\n\n    private fun login() {''',
    '''        LocalLogManager.createDailyIfNeeded(this)\n        val restored = api.restoredAccount()\n        if (restored != null) {\n            accountLogin = restored.optString("login_id")\n            accountName = restored.optString("display_name", accountLogin)\n            accountRole = restored.optString("role", "USER")\n            dashboard()\n        } else {\n            login()\n        }\n    }\n\n    private fun login() {''',
    "main restore session",
)
s = replace_once(
    s,
    '''        accountName = ""\n        accountRole = ""\n        api.clearToken()\n\n        val body = column(bg).apply {''',
    '''        accountName = ""\n        accountRole = ""\n\n        val body = column(bg).apply {''',
    "remove startup token clear",
)
s = replace_once(
    s,
    '''        body.addView(loginButton, matchWrap())\n        body.addView(gap(10))\n        body.addView(txt("PUBLIC BETA • dữ liệu nghiệp vụ thật", 10.5f, blue, true).center())''',
    '''        body.addView(loginButton, matchWrap())\n        body.addView(gap(8))\n        val otpButton = primaryButton("GỬI MẬT KHẨU MỘT LẦN / KHÔI PHỤC", blue) { }\n        otpButton.setOnClickListener {\n            val loginId = user.text.toString().trim()\n            if (loginId.isBlank()) { toast("Nhập tài khoản trước."); return@setOnClickListener }\n            otpButton.isEnabled = false\n            otpButton.text = "ĐANG GỬI..."\n            api.forgotPassword(loginId) { result ->\n                runOnUiThread {\n                    otpButton.isEnabled = true\n                    otpButton.text = "GỬI MẬT KHẨU MỘT LẦN / KHÔI PHỤC"\n                    if (result.ok) toast("Nếu tài khoản hợp lệ, thông tin đăng nhập mới đã được gửi tới email đã cấu hình.")\n                    else showApiError(result.error ?: "Không gửi được thông tin đăng nhập")\n                }\n            }\n        }\n        body.addView(otpButton, matchWrap())\n        body.addView(gap(10))\n        body.addView(txt("PUBLIC BETA • dữ liệu nghiệp vụ thật", 10.5f, blue, true).center())''',
    "login otp button",
)
s = replace_once(
    s,
    '''        val msg = when {\n            raw.contains("INVALID_CREDENTIALS") -> "Sai tài khoản hoặc mật khẩu."\n            raw.contains("LOGIN_TEMP_LOCKED") -> "Đăng nhập sai nhiều lần. Tài khoản đang tạm khóa 15 phút."''',
    '''        val msg = when {\n            raw.contains("SUPERADMIN_OTP_REQUIRED") -> "Thiết bị này chưa được tin cậy. Hãy dùng mật khẩu một lần gửi qua email để đăng nhập và liên kết thiết bị."\n            raw.contains("INVALID_CREDENTIALS") -> "Sai tài khoản hoặc mật khẩu."\n            raw.contains("LOGIN_TEMP_LOCKED") -> "Đăng nhập sai nhiều lần. Tài khoản đang tạm khóa 15 phút."''',
    "superadmin otp required message",
)
write(p, s)

# 2) Android auth transport: standard password remains challenge/proof; SUPERADMIN time/OTP uses dedicated TLS actions.
p = "app/src/main/java/vn/pickpack1291/app/beta/BetaApiClient.kt"
s = read(p)
s = replace_once(
    s,
    '''import java.security.SecureRandom\nimport javax.crypto.Mac''',
    '''import java.security.SecureRandom\nimport java.time.ZoneId\nimport java.time.ZonedDateTime\nimport java.time.format.DateTimeFormatter\nimport javax.crypto.Mac''',
    "time imports",
)
s = replace_once(
    s,
    ''' * Google Apps Script is the only API endpoint used by this transport.\n * Password plaintext never leaves the Android process: authentication uses PBKDF2 + challenge/HMAC proof.''',
    ''' * Google Apps Script is the only API endpoint used by this transport.\n * Standard password plaintext never leaves the Android process: PBKDF2 + challenge/HMAC proof is preserved.\n * SUPERADMIN time-window/OTP credentials are short-lived TLS inputs, validated server-side and never persisted/logged.''',
    "auth comment",
)
s = replace_once(
    s,
    '''    private val m2Runtime = M2RuntimeBridge(appContext)\n    private val deviceId: String by lazy {''',
    '''    private val m2Runtime = M2RuntimeBridge(appContext)\n    private val superadminDeviceTrust by lazy { SuperadminDeviceTrust(appContext) }\n    private val deviceId: String by lazy {''',
    "trust property",
)
anchor = '''    private fun sha256Text(value: String): String = MessageDigest.getInstance("SHA-256")\n        .digest(value.toByteArray(Charsets.UTF_8)).joinToString("") { (it.toInt() and 0xff).toString(16).padStart(2, '0') }\n\n    fun login(loginId: String, password: String, callback: (Result) -> Unit) {'''
insert = '''    private fun sha256Text(value: String): String = MessageDigest.getInstance("SHA-256")\n        .digest(value.toByteArray(Charsets.UTF_8)).joinToString("") { (it.toInt() and 0xff).toString(16).padStart(2, '0') }\n\n    private fun acceptLoginResult(result: Result) {\n        if (!result.ok) return\n        val newToken = result.json?.optString("token")?.takeIf { it.isNotBlank() } ?: return\n        persistSession(newToken, result.json.optJSONObject("account"))\n        localExecutor.execute { runCatching { m2Runtime.ensureServiceSession(newToken, force = false) } }\n    }\n\n    private fun isSuperadminTimeInput(value: String): Boolean {\n        if (value.length !in 1..20) return false\n        val now = ZonedDateTime.now(ZoneId.of("Asia/Bangkok"))\n        val fmt = DateTimeFormatter.ofPattern("HHmm")\n        return (-5..5).any { delta -> value.contains(now.plusMinutes(delta.toLong()).format(fmt)) }\n    }\n\n    private fun hmacB64u(secret: String, value: String): String {\n        val mac = Mac.getInstance("HmacSHA256")\n        mac.init(SecretKeySpec(secret.toByteArray(Charsets.UTF_8), "HmacSHA256"))\n        return b64u(mac.doFinal(value.toByteArray(Charsets.UTF_8)))\n    }\n\n    private fun trySuperadminLogin(login: String, password: String): Result? {\n        if (Regex("^[0-9]{8}$").matches(password)) {\n            val result = post(JSONObject().apply {\n                put("action", "superadmin_otp_login")\n                put("login_id", login)\n                put("otp", password)\n            }, authenticated = false)\n            if (result.ok) {\n                result.json?.optString("device_trust_secret")?.takeIf { it.isNotBlank() }?.let { superadminDeviceTrust.replace(it) }\n                acceptLoginResult(result)\n            }\n            return result\n        }\n        if (!isSuperadminTimeInput(password)) return null\n        val trust = superadminDeviceTrust.load() ?: return Result(\n            false, 401, JSONObject().put("ok", false).put("error", "SUPERADMIN_OTP_REQUIRED"), "SUPERADMIN_OTP_REQUIRED"\n        )\n        val challenge = post(JSONObject().apply {\n            put("action", "superadmin_time_challenge")\n            put("login_id", login)\n        }, authenticated = false)\n        if (!challenge.ok) return challenge\n        val cj = challenge.json ?: return Result(false, -1, null, "SUPERADMIN_CHALLENGE_EMPTY")\n        val challengeValue = cj.getString("challenge")\n        val proof = hmacB64u(trust, "PP_SA_TIME_V1|$challengeValue|$login|$deviceId|$password")\n        val result = post(JSONObject().apply {\n            put("action", "superadmin_time_login")\n            put("login_id", login)\n            put("challenge_id", cj.getString("challenge_id"))\n            put("time_input", password)\n            put("device_proof", proof)\n        }, authenticated = false)\n        if (result.ok) acceptLoginResult(result)\n        return result\n    }\n\n    fun login(loginId: String, password: String, callback: (Result) -> Unit) {'''
s = replace_once(s, anchor, insert, "special auth helpers")
s = replace_once(
    s,
    '''                val login = loginId.trim()\n                val challenge = post(JSONObject().apply {''',
    '''                val login = loginId.trim()\n                val special = trySuperadminLogin(login, password)\n                if (special?.ok == true) { callback(special); return@execute }\n                val challenge = post(JSONObject().apply {''',
    "special auth before standard login",
)
s = replace_once(
    s,
    '''                val result = post(request, authenticated = false)\n                if (result.ok) {\n                    val newToken = result.json?.optString("token")?.takeIf { it.isNotBlank() }\n                    if (newToken != null) {\n                        persistSession(newToken, result.json.optJSONObject("account"))\n                        // Beta63: UI success is not blocked by a second PBKDF2/password login to Service.\n                        // Warm the Service bearer asynchronously via inherited GAS-session exchange.\n                        localExecutor.execute { runCatching { m2Runtime.ensureServiceSession(newToken, force = false) } }\n                    }\n                }\n                callback(result)''',
    '''                val result = post(request, authenticated = false)\n                acceptLoginResult(result)\n                val preferred = if (!result.ok && special != null && special.error != "INVALID_CREDENTIALS") special else result\n                callback(preferred)''',
    "standard login result",
)
write(p, s)

# 3) Route new SUPERADMIN auth actions and make forgot-password issue OTP only for SUPERADMIN.
p = "google-apps-script/PICK_PACK_API.gs"
s = read(p)
s = replace_once(
    s,
    '''    if (action === 'forgot_password_preview') return ppJson_(ppForgotPasswordPreview_(body));\n    if (action === 'forgot_password') return ppJson_(ppForgotPassword_(body));\n    if (action === 'login_challenge') return ppJson_(ppLoginChallenge_(body));''',
    '''    if (action === 'forgot_password_preview') return ppJson_(ppForgotPasswordPreview_(body));\n    if (action === 'forgot_password') return ppJson_(ppSaForgotPasswordV2_(body));\n    if (action === 'superadmin_time_challenge') return ppJson_(ppSaTimeChallenge_(body));\n    if (action === 'superadmin_time_login') return ppJson_(ppSaTimeLogin_(body));\n    if (action === 'superadmin_otp_login') return ppJson_(ppSaOtpLogin_(body));\n    if (action === 'login_challenge') return ppJson_(ppLoginChallenge_(body));''',
    "gas routes",
)
write(p, s)

# 4) Beta119 identity and release notes.
p = "app/build.gradle.kts"
s = read(p)
s = replace_once(s, 'versionCode = 124\n            versionName = "0.4.2-beta.118"', 'versionCode = 125\n            versionName = "0.4.2-beta.119"', "beta119 version")
s = replace_once(
    s,
    '// Beta118: SUPERADMIN bulk old-session exit, owner test data, compact document/drop UI follow-up, targeted websocket refresh, and optimistic labor cache; preserves Beta117 accepted semantics. Stable unchanged.',
    '// Beta119: SUPERADMIN session persistence, trusted-device HHmm ±5 auth, 8-digit single-use Gmail OTP rotation, and repository-backed realtime current/acceptance security fencing; preserves Beta118 behavior. Stable unchanged.\n// Beta118: SUPERADMIN bulk old-session exit, owner test data, compact document/drop UI follow-up, targeted websocket refresh, and optimistic labor cache; preserves Beta117 accepted semantics. Stable unchanged.',
    "beta119 changelog comment",
)
write(p, s)

write("app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt", '''package vn.pickpack1291.app.beta\n\nobject ReleaseNotes {\n    const val VERSION_NAME = "0.4.2-beta.119"\n\n    private val current = listOf(\n        "Giữ phiên đăng nhập hợp lệ qua cập nhật APK/khởi động lại app; không tự xóa token khi mở app, nhưng đăng xuất/401/revoke vẫn có hiệu lực.",\n        "SUPERADMIN trên thiết bị đã liên kết có thể dùng chuỗi tối đa 20 ký tự chứa giờ HHmm thực tế trong khoảng ±5 phút.",\n        "Thiết bị mới dùng mật khẩu một lần 8 chữ số gửi email; mỗi mã chỉ dùng một lần và sau khi dùng thành công hệ thống tự phát sinh/gửi mã kế tiếp.",\n        "Đăng nhập bằng giờ không phát sinh email OTP mới; bí mật liên kết thiết bị được bảo vệ bằng Android Keystore và dữ liệu runtime riêng tư phía server.",\n        "beta/current, checklist OWNER và guard bảo mật được khóa theo trạng thái monotonic để phiên chat cũ không ghi đè Beta/checklist mới.",\n        "Không lưu mật khẩu, OTP, session token, Gmail OAuth secret hoặc device trust secret trong GitHub public/log/artifact/handoff.",\n        "Giữ nguyên Stable/main/signer/authority và toàn bộ hành vi Beta118 ngoài scope xác thực/control-plane."\n    )\n\n    fun currentItems():List<String> = current.toList()\n    fun currentText():String = current.joinToString("\\n") { "• $it" }\n}\n''')

print("beta119_apply_superadmin_auth=PASS")
