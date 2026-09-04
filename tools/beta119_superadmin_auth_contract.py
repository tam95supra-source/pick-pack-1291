#!/usr/bin/env python3
from pathlib import Path
import re
R=Path(__file__).resolve().parents[1]
def read(p): return (R/p).read_text(encoding="utf-8")
def must(v,m):
    if not v: raise SystemExit("BETA119_SUPERADMIN_AUTH_CONTRACT_FAIL:"+m)
main=read("app/src/main/java/vn/pickpack1291/app/beta/MainActivity.kt")
api=read("app/src/main/java/vn/pickpack1291/app/beta/BetaApiClient.kt")
gas=read("google-apps-script/PICK_PACK_API.gs")
sa=read("google-apps-script/SUPERADMIN_AUTH_V2.gs")
gradle=read("app/build.gradle.kts")
notes=read("app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt")
ledger=read("ops/owner-acceptance-current.json")
policy=read("docs/CONTROL_PLANE_AUTH_SECURITY_POLICY.md")
current_sync=read(".github/workflows/beta-current-sync.yml")
security_guard=read(".github/workflows/control-plane-security-guard.yml")
version_code_match=re.search(r'create\("beta"\).*?versionCode\s*=\s*(\d+).*?versionName\s*=\s*"0\.4\.2-beta\.(\d+)"',gradle,re.S)
must(version_code_match is not None and int(version_code_match.group(1))>=125 and int(version_code_match.group(2))>=119,"BETA119_FEATURE_BASELINE_IDENTITY")
notes_version=re.search(r'const val VERSION_NAME = "0\.4\.2-beta\.(\d+)"',notes)
must(notes_version is not None and int(notes_version.group(1))>=119,"RELEASE_NOTES_FEATURE_BASELINE_IDENTITY")
must('versionCode = 1' in gradle and 'versionName = "0.1.0-stable"' in gradle,"STABLE_IDENTITY_CHANGED")
must('val restored = api.restoredAccount()' in main and 'dashboard()' in main,"SESSION_RESTORE_MISSING")
login_block=main[main.index('private fun login()'):main.index('private fun dashboard()')]
must('api.clearToken()' not in login_block,"LOGIN_STILL_CLEARS_TOKEN")
must('GỬI MẬT KHẨU MỘT LẦN / KHÔI PHỤC' in main,"OTP_RECOVERY_UI_MISSING")
must('Regex("^[0-9]{8}$")' in api,"OTP_8_DIGIT_CLIENT_ROUTE_MISSING")
must('value.length !in 1..20' in api and '(-5..5).any' in api and 'DateTimeFormatter.ofPattern("HHmm")' in api,"TIME_WINDOW_CLIENT_MISSING")
must('superadmin_time_login' in api and 'superadmin_otp_login' in api,"SPECIAL_AUTH_CLIENT_ACTIONS_MISSING")
for forbidden in ['superadmin_time_challenge','SuperadminDeviceTrust','device_trust_secret','SUPERADMIN_OTP_REQUIRED']:
    must(forbidden not in api,"CLIENT_DEVICE_TRUST_REMAINS_"+forbidden)
must(not (R/"app/src/main/java/vn/pickpack1291/app/beta/SuperadminDeviceTrust.kt").exists(),"DEVICE_TRUST_FILE_REMAINS")
for action in ['superadmin_time_login','superadmin_otp_login']:
    must("action === '"+action+"'" in gas,"GAS_ROUTE_"+action)
must("superadmin_time_challenge" not in gas,"TIME_CHALLENGE_ROUTE_REMAINS")
must("ppSaForgotPasswordV2_(body)" in gas,"SUPERADMIN_FORGOT_ROUTE_MISSING")
must("SUPERADMIN_SPECIAL_AUTH_REQUIRED" in gas,"LEGACY_SUPERADMIN_PASSWORD_NOT_DISABLED")
must("input.length<1||input.length>20" in sa and "for(let i=-5;i<=5;i++)" in sa and "PP.TZ,'HHmm'" in sa,"SERVER_TIME_WINDOW_MISSING")
for forbidden in ['PP_SUPERADMIN_DEVICE_','device_trust_secret','ppSaTimeChallenge_','device_proof']:
    must(forbidden not in sa,"SERVER_DEVICE_TRUST_REMAINS_"+forbidden)
must("!/^[0-9]{8}$/.test(otp)" in sa and "ppSaOtpValue_" in sa and "n<250" in sa,"SERVER_OTP_8_DIGIT_RANDOM_MISSING")
must("PP_SUPERADMIN_OTP_PEPPER" in sa and "ppSaOtpVerifier_" in sa and "computeHmacSha256Signature" in sa,"OTP_PROTECTED_VERIFIER_MISSING")
must("ppSaSendOtp_(a,next.otp,'MÃ KẾ TIẾP SAU KHI ĐĂNG NHẬP')" in sa,"OTP_ROTATION_EMAIL_MISSING")
must("ppSaRateConsume_('OTP_LOGIN'" in sa and "ppSaRateConsume_('TIME_LOGIN'" in sa,"RATE_LIMIT_MISSING")
must("LockService.getScriptLock()" in sa,"OTP_ATOMIC_LOCK_MISSING")
must('plaintext_password_in_repo' in ledger and 'plaintext_otp_in_repo' in ledger,"LEDGER_SECRET_POLICY_MISSING")
must('no device binding' in policy.lower() and 'exactly two' in policy.lower() and 'HHmm' in policy and 'single-use' in policy,"SECURITY_POLICY_TWO_METHOD_MISSING")
must('refs/heads/beta/current' in current_sync and '--force' not in current_sync,"CURRENT_SYNC_FENCE_MISSING")
must('public_repo_secret_guard.py' in security_guard and 'owner_acceptance_ledger_guard.py' in security_guard,"CONTROL_PLANE_SECURITY_GUARD_MISSING")
for name,text in [("api",api),("gas",sa)]:
    must(not re.search(r'(?i)(?:otp|password)\s*[:=]\s*[\"\']\d{8}[\"\']',text),"LITERAL_OTP_"+name)
print("beta119_superadmin_auth_contract=PASS feature_baseline_preserved=PASS stable_identity=PASS session_persistence=PASS time_window_no_device_bind=PASS exactly_two_superadmin_methods=PASS otp_single_use_rotation=PASS public_secret_fence=PASS")
