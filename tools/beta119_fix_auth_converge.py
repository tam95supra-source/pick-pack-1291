#!/usr/bin/env python3
from pathlib import Path

p=Path('tools/beta_auth_converge.py')
s=p.read_text()
old='''    login="adminbeta";password=creds[login][0];device="auth-migrate-"+b64u(secrets.token_bytes(8))
    c=gas_post(beta["gas"],{"action":"login_challenge","login_id":login,"_device_id":device,"_app_channel":"BETA","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA"})
    if c.get("ok") is not True:raise RuntimeError("ADMINBETA_GAS_CHALLENGE_FAILED:"+str(c.get("error")))
    pr=proof(password,str(c["salt"]),int(c.get("iterations",120000)),str(c["challenge"]))
    print("::add-mask::"+pr)
    g=gas_post(beta["gas"],{"action":"login","login_id":login,"challenge_id":c["challenge_id"],"proof":pr,"_device_id":device,"_device_label":"CI AUTH MIGRATION","_app_channel":"BETA","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA"})
    if g.get("ok") is not True or (g.get("account") or {}).get("role")!="SUPERADMIN":raise RuntimeError("ADMINBETA_GAS_LOGIN_FAILED")
    gas_token=str(g.get("token",""));print("::add-mask::"+gas_token)
'''
new='''    # Beta119: SUPERADMIN has exactly two credential methods. Static password proof is
    # intentionally forbidden; use the owner-approved server-time HHmm +/-5 method.
    login="adminbeta";device="auth-migrate-"+b64u(secrets.token_bytes(8))
    from datetime import datetime
    from zoneinfo import ZoneInfo
    hhmm=datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%H%M")
    time_input="ci"+hhmm+"auth"
    g=gas_post(beta["gas"],{"action":"superadmin_time_login","login_id":login,"time_input":time_input,"_device_id":device,"_device_label":"CI AUTH MIGRATION","_app_channel":"BETA","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA"})
    if g.get("ok") is not True or (g.get("account") or {}).get("role")!="SUPERADMIN" or g.get("auth_method")!="SUPERADMIN_TIME":
        raise RuntimeError("ADMINBETA_GAS_TIME_LOGIN_FAILED:"+str(g.get("error") or "UNKNOWN")[:120])
    gas_token=str(g.get("token",""));print("::add-mask::"+gas_token)

    # Preserve regression coverage for ordinary ADMIN password/challenge login.
    admin_login="admintest";admin_password=creds[admin_login][0];admin_device="auth-admin-"+b64u(secrets.token_bytes(8))
    c=gas_post(beta["gas"],{"action":"login_challenge","login_id":admin_login,"_device_id":admin_device,"_app_channel":"BETA","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA"})
    if c.get("ok") is not True:raise RuntimeError("ADMINTEST_GAS_CHALLENGE_FAILED:"+str(c.get("error")))
    pr=proof(admin_password,str(c["salt"]),int(c.get("iterations",120000)),str(c["challenge"]))
    print("::add-mask::"+pr)
    admin_g=gas_post(beta["gas"],{"action":"login","login_id":admin_login,"challenge_id":c["challenge_id"],"proof":pr,"_device_id":admin_device,"_device_label":"CI AUTH MIGRATION ADMIN","_app_channel":"BETA","_environment_id":"BETA","_service_audience":"PICK_PACK_1291_BETA"})
    if admin_g.get("ok") is not True or (admin_g.get("account") or {}).get("role")!="ADMIN":raise RuntimeError("ADMINTEST_GAS_LOGIN_FAILED")
    admin_token=str(admin_g.get("token",""));print("::add-mask::"+admin_token)
'''
if old not in s:
    raise SystemExit('BETA119_AUTH_CONVERGE_OLD_BLOCK_NOT_FOUND')
s=s.replace(old,new,1)
s=s.replace('''"replacement_first":{"adminbeta_gas_login":"PASS","adminbeta_service_exchange":"PASS","legacy_disabled_after_adminbeta_verified":True},''','''"replacement_first":{"adminbeta_gas_time_login":"PASS","admintest_standard_password_login":"PASS","adminbeta_service_exchange":"PASS","legacy_disabled_after_adminbeta_verified":True},''',1)
s=s.replace('''"owner_recovery":"Use Forgot Password for adminbeta; generated CI bootstrap passwords are intentionally not persisted."''','''"owner_recovery":"SUPERADMIN uses HHmm +/-5 or 8-digit one-time email OTP; generated CI bootstrap passwords are intentionally not persisted."''',1)
s=s.replace('''"adminbeta_login":"PASS"''','''"adminbeta_time_login":"PASS","admintest_standard_login":"PASS"''',1)
p.write_text(s)
assert 'superadmin_time_login' in s
assert 'admintest_standard_password_login' in s
assert 'ADMINBETA_GAS_TIME_LOGIN_FAILED' in s
print('beta119_auth_converge_patch=PASS')
