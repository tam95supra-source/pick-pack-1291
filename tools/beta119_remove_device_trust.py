#!/usr/bin/env python3
from pathlib import Path

R = Path(__file__).resolve().parents[1]

def read(p): return (R / p).read_text(encoding="utf-8")
def write(p, s): (R / p).write_text(s, encoding="utf-8")
def rep(s, old, new, label):
    n=s.count(old)
    if n!=1: raise SystemExit(f"BETA119_TWO_METHOD_PATCH_FAIL:{label}:count={n}")
    return s.replace(old,new,1)

# Android client: no device binding; server is authority for HHmm window.
p="app/src/main/java/vn/pickpack1291/app/beta/BetaApiClient.kt"; s=read(p)
s=rep(s,'    private val superadminDeviceTrust by lazy { SuperadminDeviceTrust(appContext) }\n','',"remove trust property")
s=rep(s,'''    private fun hmacB64u(secret: String, value: String): String {\n        val mac = Mac.getInstance("HmacSHA256")\n        mac.init(SecretKeySpec(secret.toByteArray(Charsets.UTF_8), "HmacSHA256"))\n        return b64u(mac.doFinal(value.toByteArray(Charsets.UTF_8)))\n    }\n\n''','',"remove trust hmac helper")
s=rep(s,'''            if (result.ok) {\n                result.json?.optString("device_trust_secret")?.takeIf { it.isNotBlank() }?.let { superadminDeviceTrust.replace(it) }\n                acceptLoginResult(result)\n            }''','''            if (result.ok) acceptLoginResult(result)''',"otp no device bind")
s=rep(s,'''        if (!isSuperadminTimeInput(password)) return null\n        val trust = superadminDeviceTrust.load() ?: return Result(\n            false, 401, JSONObject().put("ok", false).put("error", "SUPERADMIN_OTP_REQUIRED"), "SUPERADMIN_OTP_REQUIRED"\n        )\n        val challenge = post(JSONObject().apply {\n            put("action", "superadmin_time_challenge")\n            put("login_id", login)\n        }, authenticated = false)\n        if (!challenge.ok) return challenge\n        val cj = challenge.json ?: return Result(false, -1, null, "SUPERADMIN_CHALLENGE_EMPTY")\n        val challengeValue = cj.getString("challenge")\n        val proof = hmacB64u(trust, "PP_SA_TIME_V1|$challengeValue|$login|$deviceId|$password")\n        val result = post(JSONObject().apply {\n            put("action", "superadmin_time_login")\n            put("login_id", login)\n            put("challenge_id", cj.getString("challenge_id"))\n            put("time_input", password)\n            put("device_proof", proof)\n        }, authenticated = false)''','''        if (!isSuperadminTimeInput(password)) return null\n        val result = post(JSONObject().apply {\n            put("action", "superadmin_time_login")\n            put("login_id", login)\n            put("time_input", password)\n        }, authenticated = false)''',"direct time auth")
write(p,s)

# UI: remove trusted-device wording; explain exactly two SUPERADMIN methods.
p="app/src/main/java/vn/pickpack1291/app/beta/MainActivity.kt"; s=read(p)
s=s.replace('            raw.contains("SUPERADMIN_OTP_REQUIRED") -> "Thiết bị này chưa được tin cậy. Hãy dùng mật khẩu một lần gửi qua email để đăng nhập và liên kết thiết bị."\n','')
needle='            raw.contains("INVALID_CREDENTIALS") -> "Sai tài khoản hoặc mật khẩu."\n'
if needle in s and 'SUPERADMIN_SPECIAL_AUTH_REQUIRED' not in s:
    s=s.replace(needle,'            raw.contains("SUPERADMIN_SPECIAL_AUTH_REQUIRED") -> "SUPERADMIN chỉ dùng mật khẩu theo giờ hoặc mật khẩu một lần 8 số."\n'+needle,1)
write(p,s)

# GAS V2: direct server-side time validation; OTP rotates only OTP, never device trust.
p="google-apps-script/SUPERADMIN_AUTH_V2.gs"; s=read(p)
s=rep(s,"function ppSaDeviceStateKey_(login,device){return 'PP_SUPERADMIN_DEVICE_'+ppSha256Hex_(ppEnvironmentId_()+'|'+String(login||'')+'|'+String(device||'')).slice(0,40);}\n",'',"remove device key")
start=s.index('function ppSaTimeChallenge_(body){')
end=s.index('function ppSaTimeMatches_(value){')
s=s[:start]+s[end:]
old='''function ppSaTimeLogin_(body){\n  if(!ppSaRateConsume_('TIME_LOGIN',body,8,600))return {ok:false,error:'LOGIN_TEMP_LOCKED'};\n  const login=String(body.login_id||'').trim(),a=ppSaAccount_(login),c=ppSaTakeTimeChallenge_(body),device=ppDeviceId_(body),input=String(body.time_input||''),proof=String(body.device_proof||'');\n  if(!a||!c||!ppSaTimeMatches_(input)){return {ok:false,error:'INVALID_CREDENTIALS'};}\n  const secret=String(PropertiesService.getScriptProperties().getProperty(ppSaDeviceStateKey_(login,device))||'');\n  const expected=secret?ppSaHmacB64u_(secret,'PP_SA_TIME_V1|'+c.challenge+'|'+login+'|'+device+'|'+input):'';\n  if(!secret||!proof||!ppSaEq_(expected,proof))return {ok:false,error:'INVALID_CREDENTIALS'};\n  ppSaRateClear_('TIME_LOGIN',body);return ppSaIssueSession_(a,body,{auth_method:'SUPERADMIN_TIME'});\n}\n'''
new='''function ppSaTimeLogin_(body){\n  if(!ppSaRateConsume_('TIME_LOGIN',body,8,600))return {ok:false,error:'LOGIN_TEMP_LOCKED'};\n  const login=String(body.login_id||'').trim(),a=ppSaAccount_(login),input=String(body.time_input||'');\n  if(!a||!ppSaTimeMatches_(input))return {ok:false,error:'INVALID_CREDENTIALS'};\n  ppSaRateClear_('TIME_LOGIN',body);return ppSaIssueSession_(a,body,{auth_method:'SUPERADMIN_TIME'});\n}\n'''
s=rep(s,old,new,"server direct time")
old='''    const next=ppSaNewOtpStateUnlocked_(login),device=ppDeviceId_(body),deviceKey=ppSaDeviceStateKey_(login,device),oldDevice=props.getProperty(deviceKey),deviceSecret=ppB64u_(ppRandom_(32));\n    props.setProperty(key,JSON.stringify(next.state));props.setProperty(deviceKey,deviceSecret);\n    try{ppSaSendOtp_(a,next.otp,'MÃ KẾ TIẾP SAU KHI ĐĂNG NHẬP');}\n    catch(err){props.setProperty(key,raw);if(oldDevice===null)props.deleteProperty(deviceKey);else props.setProperty(deviceKey,oldDevice);throw err;}\n    ppSaRateClear_('OTP_LOGIN',body);return ppSaIssueSession_(a,body,{auth_method:'SUPERADMIN_OTP',device_trust_secret:deviceSecret,otp_rotated:true});'''
new='''    const next=ppSaNewOtpStateUnlocked_(login);\n    props.setProperty(key,JSON.stringify(next.state));\n    try{ppSaSendOtp_(a,next.otp,'MÃ KẾ TIẾP SAU KHI ĐĂNG NHẬP');}\n    catch(err){props.setProperty(key,raw);throw err;}\n    ppSaRateClear_('OTP_LOGIN',body);return ppSaIssueSession_(a,body,{auth_method:'SUPERADMIN_OTP',otp_rotated:true});'''
s=rep(s,old,new,"otp no device bind")
write(p,s)

# API routes: no time challenge; legacy static password is forbidden for SUPERADMIN.
p="google-apps-script/PICK_PACK_API.gs"; s=read(p)
s=s.replace("    if (action === 'superadmin_time_challenge') return ppJson_(ppSaTimeChallenge_(body));\n",'')
old="  const login=String(body.login_id||'').trim(), id=String(body.challenge_id||''), proof=String(body.proof||''), c=ppTakeChallenge_(id,'LOGIN',login);let a=ppAccount_(login),cred=a?ppCredentialParts_(a.verifier):null;\n  if(!c||!a||a.status!=='ACTIVE'||!cred||(cred.algorithm==='reset_sha256'&&cred.expires_at<=Date.now())||!ppVerifyProof_(cred.key,c.challenge,proof))return {ok:false,error:'INVALID_CREDENTIALS'};"
new="  const login=String(body.login_id||'').trim(), id=String(body.challenge_id||''), proof=String(body.proof||''), c=ppTakeChallenge_(id,'LOGIN',login);let a=ppAccount_(login),cred=a?ppCredentialParts_(a.verifier):null;\n  if(a&&String(a.role||'').toUpperCase()==='SUPERADMIN')return {ok:false,error:'SUPERADMIN_SPECIAL_AUTH_REQUIRED'};\n  if(!c||!a||a.status!=='ACTIVE'||!cred||(cred.algorithm==='reset_sha256'&&cred.expires_at<=Date.now())||!ppVerifyProof_(cred.key,c.challenge,proof))return {ok:false,error:'INVALID_CREDENTIALS'};"
s=rep(s,old,new,"disable superadmin legacy password")
write(p,s)

# Remove obsolete Android trust implementation and old re-applicable patch workflow/script.
for q in [
  "app/src/main/java/vn/pickpack1291/app/beta/SuperadminDeviceTrust.kt",
  "tools/beta119_apply_superadmin_auth.py",
  ".github/workflows/beta119-apply-superadmin-auth.yml",
]:
    f=R/q
    if f.exists(): f.unlink()

# Release notes/build comments.
p="app/build.gradle.kts"; s=read(p); s=s.replace('trusted-device HHmm ±5 auth','HHmm ±5 time auth'); write(p,s)
p="app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt"; s=read(p)
s=s.replace('SUPERADMIN trên thiết bị đã liên kết có thể dùng chuỗi tối đa 20 ký tự chứa giờ HHmm thực tế trong khoảng ±5 phút.','SUPERADMIN có thể dùng chuỗi tối đa 20 ký tự chứa giờ HHmm thực tế trong khoảng ±5 phút, không ràng buộc thiết bị.')
s=s.replace('Thiết bị mới dùng mật khẩu một lần 8 chữ số gửi email; mỗi mã chỉ dùng một lần và sau khi dùng thành công hệ thống tự phát sinh/gửi mã kế tiếp.','Cách thứ hai là mật khẩu một lần 8 chữ số gửi email; mỗi mã chỉ dùng một lần và sau khi dùng thành công hệ thống tự phát sinh/gửi mã kế tiếp.')
s=s.replace('Đăng nhập bằng giờ không phát sinh email OTP mới; bí mật liên kết thiết bị được bảo vệ bằng Android Keystore và dữ liệu runtime riêng tư phía server.','Đăng nhập bằng giờ không phát sinh email OTP mới; kiểm tra HHmm ±5 phút và giới hạn độ dài được thực hiện lại phía server.')
s=s.replace('Không lưu mật khẩu, OTP, session token, Gmail OAuth secret hoặc device trust secret trong GitHub public/log/artifact/handoff.','Không lưu mật khẩu, OTP, session token hoặc Gmail OAuth secret trong GitHub public/log/artifact/handoff.')
write(p,s)

# Policy: OWNER explicitly removed trusted-device requirement.
p="docs/CONTROL_PLANE_AUTH_SECURITY_POLICY.md"; s=read(p)
start=s.index('### 4.1 Trusted-device time-window method')
end=s.index('### 4.2 Email one-time password')
sec='''### 4.1 Time-window method (no device binding)\n\nOWNER requirement updated 2026-09-04: SUPERADMIN has exactly two credential methods; device trust/binding is not used.\n\n- Method 1 accepts an input of 1..20 characters when the string contains at least one exact `HHmm` value in the server's current time window ±5 minutes. Arbitrary prefix/suffix characters are allowed.\n- Validation is server-side using the configured Vietnam business timezone and must handle midnight wrap correctly. Client-side matching is only a routing hint, never authority.\n- No device binding, device secret, trusted-device state or Android Keystore dependency is part of this method.\n- Successful time-window login does not rotate or send the email OTP.\n- Failed attempts are rate-limited server-side; the submitted time string must not be logged or persisted.\n- Legacy/static SUPERADMIN password login is disabled so SUPERADMIN has exactly the two OWNER-approved methods.\n\nSecurity note: current time is not secret. This method therefore provides materially less authentication secrecy than a device-bound credential. OWNER explicitly selected this tradeoff; public GitHub must still contain no actual password/OTP/token/secret values.\n\n'''
s=s[:start]+sec+s[end:]
s=s.replace('Login by trusted-device time method does not rotate/send OTP.','Login by time-window method does not rotate/send OTP.')
s=s.replace('6. Trusted device: arbitrary string length <=20 containing valid ±5-minute `HHmm` + valid device challenge succeeds.\n7. Same time string from an untrusted device fails.\n8. Time outside ±5 minutes fails, including midnight-boundary cases.\n9. Valid 8-digit OTP succeeds once; replay fails.\n10. Successful OTP use creates/sends a new OTP; trusted-time login does not.\n11. Secret-bearing fields never appear in audit/log/receipt/public repo output.', '6. Arbitrary string length <=20 containing valid ±5-minute `HHmm` succeeds for active SUPERADMIN without device binding.\n7. Time outside ±5 minutes fails, including midnight-boundary cases; inputs over 20 characters fail.\n8. Legacy/static SUPERADMIN password login fails, proving exactly two SUPERADMIN methods remain.\n9. Valid 8-digit OTP succeeds once; replay fails.\n10. Successful OTP use creates/sends a new OTP; time-window login does not.\n11. Secret-bearing fields never appear in audit/log/receipt/public repo output.')
write(p,s)

# Rewrite deterministic auth contract for exactly-two-method semantics.
write("tools/beta119_superadmin_auth_contract.py", r'''#!/usr/bin/env python3
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
must('versionCode = 125' in gradle and 'versionName = "0.4.2-beta.119"' in gradle,"BETA119_IDENTITY")
must('const val VERSION_NAME = "0.4.2-beta.119"' in notes,"RELEASE_NOTES_IDENTITY")
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
print("beta119_superadmin_auth_contract=PASS session_persistence=PASS time_window_no_device_bind=PASS exactly_two_superadmin_methods=PASS otp_single_use_rotation=PASS public_secret_fence=PASS")
''')
print("beta119_remove_device_trust=PASS")
