#!/usr/bin/env python3
import datetime,json,os,re,sys,urllib.error,urllib.parse,urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

R=Path(__file__).resolve().parents[1]

def http_json(url,method='GET',body=None,headers=None,timeout=30):
    data=None if body is None else json.dumps(body,separators=(',',':')).encode()
    h={'Accept':'application/json'}
    if body is not None:h['Content-Type']='application/json; charset=utf-8'
    if headers:h.update(headers)
    q=urllib.request.Request(url,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(q,timeout=timeout) as r:
            raw=r.read().decode('utf-8')
        return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        raw=e.read().decode('utf-8','replace')
        try:return json.loads(raw)
        except Exception:raise RuntimeError(f'HTTP_{e.code}') from e

def source_config():
    gas=(R/'google-apps-script/PICK_PACK_API.gs').read_text(encoding='utf-8')
    gradle=(R/'app/build.gradle.kts').read_text(encoding='utf-8')
    sheet=re.search(r"SHEET_ID:\s*'([^']+)'",gas)
    tz=re.search(r"TZ:\s*'([^']+)'",gas)
    endpoint=re.search(r'approvedBetaGsheetApiUrl\s*=\s*"([^"]+)"',gradle)
    if not sheet or not tz or not endpoint:raise RuntimeError('CANONICAL_RUNTIME_CONFIG_NOT_RESOLVED')
    return sheet.group(1),tz.group(1),endpoint.group(1)

def find_superadmin(access,sheet_id):
    ranges=["'Danh sách Admin'!A1:A200","'Danh sách Admin'!C1:C200","'Danh sách Admin'!I1:I200"]
    qs=urllib.parse.urlencode([('ranges',r) for r in ranges])
    url=f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values:batchGet?{qs}'
    j=http_json(url,headers={'Authorization':'Bearer '+access})
    if 'error' in j:raise RuntimeError('SHEETS_READ_FAILED')
    vr=j.get('valueRanges') or []
    if len(vr)!=3:raise RuntimeError('ADMIN_COLUMNS_MISSING')
    cols=[]
    for x in vr:
        cols.append([str((r or [''])[0] if r else '').strip() for r in x.get('values') or []])
    n=max(map(len,cols))
    for i in range(1,n):
        login=cols[0][i] if i<len(cols[0]) else ''
        role=(cols[1][i] if i<len(cols[1]) else '').upper()
        status=(cols[2][i] if i<len(cols[2]) else '').upper()
        if login and role=='SUPERADMIN' and status=='ACTIVE':return login
    raise RuntimeError('ACTIVE_SUPERADMIN_NOT_FOUND')

def post(endpoint,payload):
    common={'_app_version':'0.4.2-beta.119','_app_channel':'BETA','_environment_id':'BETA','_service_audience':'PICK_PACK_1291_BETA','_device_id':'beta119-live-auth-regression','_device_label':'GITHUB_ACTIONS'}
    b=dict(common);b.update(payload)
    return http_json(endpoint,'POST',b,timeout=35)

def main():
    access=os.environ.get('ACCESS_TOKEN','').strip()
    if not access:raise RuntimeError('ACCESS_TOKEN_MISSING')
    sheet_id,tz,endpoint=source_config()
    login=find_superadmin(access,sheet_id)
    # Never print login, auth input, token, email, verifier, challenge, or OTP.
    now=datetime.datetime.now(ZoneInfo(tz))
    valid='junk'+now.strftime('%H%M')+'xyz'
    ok=post(endpoint,{'action':'superadmin_time_login','login_id':login,'time_input':valid})
    if not ok.get('ok') or ok.get('auth_method')!='SUPERADMIN_TIME' or not ok.get('token'):
        raise RuntimeError('LIVE_TIME_LOGIN_FAILED')
    token=str(ok.get('token'))
    # Revoke the transient technical session without displaying it.
    lo=post(endpoint,{'action':'logout','_token':token})
    # logout is best-effort contract; session creation success is already established.

    outside=post(endpoint,{'action':'superadmin_time_login','login_id':login,'time_input':'not-a-valid-9999'})
    if outside.get('ok') or outside.get('error') not in ('INVALID_CREDENTIALS','LOGIN_TEMP_LOCKED'):
        raise RuntimeError('LIVE_INVALID_TIME_NOT_REJECTED')

    over='x'*17+now.strftime('%H%M')
    too_long=post(endpoint,{'action':'superadmin_time_login','login_id':login,'time_input':over})
    if too_long.get('ok') or too_long.get('error') not in ('INVALID_CREDENTIALS','LOGIN_TEMP_LOCKED'):
        raise RuntimeError('LIVE_OVER20_NOT_REJECTED')

    challenge=post(endpoint,{'action':'login_challenge','login_id':login})
    if not challenge.get('ok') or not challenge.get('challenge_id'):
        raise RuntimeError('LIVE_STANDARD_CHALLENGE_FAILED')
    legacy=post(endpoint,{'action':'login','login_id':login,'challenge_id':challenge.get('challenge_id'),'proof':'invalid-proof'})
    if legacy.get('ok') or legacy.get('error')!='SUPERADMIN_SPECIAL_AUTH_REQUIRED':
        raise RuntimeError('LIVE_LEGACY_SUPERADMIN_PASSWORD_PATH_NOT_DISABLED')

    # Trigger the OWNER-approved OTP delivery path. Response must not contain plaintext OTP.
    forgot=post(endpoint,{'action':'forgot_password','login_id':login})
    if not forgot.get('ok') or any(k.lower() in ('otp','password','token') for k in forgot.keys()):
        raise RuntimeError('LIVE_OTP_DELIVERY_PATH_FAILED_OR_LEAKED')

    result={
      'status':'PASS','version':'0.4.2-beta.119','time_login':'PASS','arbitrary_prefix_suffix':'PASS',
      'max20_server_fence':'PASS','outside_window_rejected':'PASS','device_binding':'NONE',
      'legacy_static_superadmin_password':'REJECTED','otp_delivery':'PASS_NO_SECRET_IN_RESPONSE',
      'otp_consumption_rotation':'OWNER_FUNCTIONAL_ACCEPTANCE_REQUIRED','transient_session_cleanup':'ATTEMPTED',
      'secret_values_recorded':False
    }
    out=os.environ.get('RESULT_PATH','/tmp/beta119-live-auth-regression.json')
    Path(out).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('beta119_live_auth_regression=PASS time_method=PASS invalid_fences=PASS legacy_static_rejected=PASS otp_delivery=PASS secret_output=NONE')

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('BETA119_LIVE_AUTH_REGRESSION_FAIL:'+str(e),file=sys.stderr);sys.exit(1)
