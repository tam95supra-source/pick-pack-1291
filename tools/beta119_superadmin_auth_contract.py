#!/usr/bin/env python3
from pathlib import Path
import re

R = Path(__file__).resolve().parents[1]

def read(p): return (R / p).read_text(encoding="utf-8")
def must(v, m):
    if not v: raise SystemExit("BETA119_SUPERADMIN_AUTH_CONTRACT_FAIL:" + m)

main = read("app/src/main/java/vn/pickpack1291/app/beta/MainActivity.kt")
api = read("app/src/main/java/vn/pickpack1291/app/beta/BetaApiClient.kt")
trust = read("app/src/main/java/vn/pickpack1291/app/beta/SuperadminDeviceTrust.kt")
gas = read("google-apps-script/PICK_PACK_API.gs")
sa = read("google-apps-script/SUPERADMIN_AUTH_V2.gs")
gradle = read("app/build.gradle.kts")
notes = read("app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt")
ledger = read("ops/owner-acceptance-current.json")
policy = read("docs/CONTROL_PLANE_AUTH_SECURITY_POLICY.md")
current_sync = read(".github/workflows/beta-current-sync.yml")
security_guard = read(".github/workflows/control-plane-security-guard.yml")

must('versionCode = 125' in gradle and 'versionName = "0.4.2-beta.119"' in gradle, "BETA119_IDENTITY")
must('const val VERSION_NAME = "0.4.2-beta.119"' in notes, "RELEASE_NOTES_IDENTITY")

must('val restored = api.restoredAccount()' in main and 'dashboard()' in main, "SESSION_RESTORE_MISSING")
login_block = main[main.index('private fun login()'):main.index('private fun dashboard()')]
must('api.clearToken()' not in login_block, "LOGIN_STILL_CLEARS_TOKEN")
must('GỬI MẬT KHẨU MỘT LẦN / KHÔI PHỤC' in main, "OTP_RECOVERY_UI_MISSING")

must('Regex("^[0-9]{8}$")' in api, "OTP_8_DIGIT_CLIENT_ROUTE_MISSING")
must('value.length !in 1..20' in api and '(-5..5).any' in api and 'DateTimeFormatter.ofPattern("HHmm")' in api, "TIME_WINDOW_CLIENT_MISSING")
must('superadmin_time_challenge' in api and 'superadmin_time_login' in api and 'superadmin_otp_login' in api, "SPECIAL_AUTH_CLIENT_ACTIONS_MISSING")
must('device_trust_secret' in api and 'superadminDeviceTrust.replace' in api, "DEVICE_BIND_CLIENT_MISSING")
must('SUPERADMIN_OTP_REQUIRED' in api, "UNTRUSTED_DEVICE_FAIL_CLOSED_MISSING")

for marker in ['AndroidKeyStore','AES/GCM/NoPadding','setRandomizedEncryptionRequired(true)']:
    must(marker in trust, "KEYSTORE_" + marker.replace('/','_'))
must('String(cipher.doFinal' in trust and 'prefs.edit().clear()' in trust, "KEYSTORE_DECRYPT_FAIL_CLOSED")

for action in ['superadmin_time_challenge','superadmin_time_login','superadmin_otp_login']:
    must("action === '" + action + "'" in gas, "GAS_ROUTE_" + action)
must("ppSaForgotPasswordV2_(body)" in gas, "SUPERADMIN_FORGOT_ROUTE_MISSING")
must("input.length<1||input.length>20" in sa and "for(let i=-5;i<=5;i++)" in sa and "PP.TZ,'HHmm'" in sa, "SERVER_TIME_WINDOW_MISSING")
must("!/^[0-9]{8}$/.test(otp)" in sa and "ppSaOtpValue_" in sa, "SERVER_OTP_8_DIGIT_MISSING")
must("n<250" in sa, "OTP_UNBIASED_DIGIT_REJECTION_MISSING")
must("PP_SUPERADMIN_OTP_PEPPER" in sa and "ppSaOtpVerifier_" in sa and "computeHmacSha256Signature" in sa, "OTP_PROTECTED_VERIFIER_MISSING")
must("ppSaSendOtp_(a,next.otp,'MÃ KẾ TIẾP SAU KHI ĐĂNG NHẬP')" in sa, "OTP_ROTATION_EMAIL_MISSING")
must("device_trust_secret:deviceSecret" in sa and "PP_SUPERADMIN_DEVICE_" in sa, "SERVER_DEVICE_TRUST_MISSING")
must("ppSaRateConsume_('OTP_LOGIN'" in sa and "ppSaRateConsume_('TIME_LOGIN'" in sa, "RATE_LIMIT_MISSING")
must("LockService.getScriptLock()" in sa, "OTP_ATOMIC_LOCK_MISSING")

must('plaintext_password_in_repo' in ledger and 'plaintext_otp_in_repo' in ledger, "LEDGER_SECRET_POLICY_MISSING")
must('HHmm' in policy and 'Android Keystore' in policy and 'single-use' in policy, "SECURITY_POLICY_MISSING")
must('refs/heads/beta/current' in current_sync and '--force' not in current_sync, "CURRENT_SYNC_FENCE_MISSING")
must('public_repo_secret_guard.py' in security_guard and 'owner_acceptance_ledger_guard.py' in security_guard, "CONTROL_PLANE_SECURITY_GUARD_MISSING")

# No literal 8-digit SUPERADMIN OTP/password is allowed in new auth implementation.
for name, text in [("api", api), ("gas", sa), ("trust", trust)]:
    must(not re.search(r'(?i)(?:otp|password)\s*[:=]\s*[\"\']\d{8}[\"\']', text), "LITERAL_OTP_" + name)

print("beta119_superadmin_auth_contract=PASS session_persistence=PASS trusted_time_window=PASS otp_single_use_rotation=PASS public_secret_fence=PASS")
