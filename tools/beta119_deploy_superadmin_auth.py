#!/usr/bin/env python3
import hashlib,json,os,sys,time,urllib.error,urllib.request
from pathlib import Path

API='https://script.googleapis.com/v1/projects'
R=Path(__file__).resolve().parents[1]

def req(url,token,method='GET',body=None):
    data=None if body is None else json.dumps(body).encode()
    h={'Authorization':f'Bearer {token}','Accept':'application/json'}
    if data is not None:h['Content-Type']='application/json; charset=utf-8'
    q=urllib.request.Request(url,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(q,timeout=45) as r:
            raw=r.read().decode('utf-8'); return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'{method} HTTP {e.code}: '+e.read().decode('utf-8','replace')[:700]) from e

def normdep(v):
    v=(v or '').strip(); return v.split('/s/',1)[1].split('/',1)[0] if '/s/' in v else v

def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def clean_files(project): return [{k:f[k] for k in ('name','type','source') if k in f} for f in project.get('files') or []]
def server(project): return '\n'.join(str(f.get('source') or '') for f in project.get('files') or [] if f.get('type')=='SERVER_JS')

def main():
    out=Path(sys.argv[1]); sid=os.environ.get('GAS_SCRIPT_ID','').strip(); token=os.environ.get('ACCESS_TOKEN','').strip(); dep=normdep(os.environ.get('GAS_DEPLOYMENT_ID',''))
    base=os.environ.get('BASE_SOURCE_SHA','').strip(); source=os.environ.get('SOURCE_SHA','').strip()
    if not sid or not token or not dep or len(base)!=40 or len(source)!=40: raise RuntimeError('required env missing')
    import subprocess
    current_api=(R/'google-apps-script/PICK_PACK_API.gs').read_text(encoding='utf-8')
    current_sa=(R/'google-apps-script/SUPERADMIN_AUTH_V2.gs').read_text(encoding='utf-8')
    base_api=subprocess.check_output(['git','show',f'{base}:google-apps-script/PICK_PACK_API.gs'],text=True)
    deployment=req(f'{API}/{sid}/deployments/{dep}',token); old_version=(deployment.get('deploymentConfig') or {}).get('versionNumber')
    if not isinstance(old_version,int): raise RuntimeError('old deployment version missing')
    head=req(f'{API}/{sid}/content',token); old_files=clean_files(head)
    do_posts=[f for f in old_files if f.get('type')=='SERVER_JS' and 'function doPost(' in str(f.get('source') or '')]
    if len(do_posts)!=1: raise RuntimeError(f'expected one live doPost file, got {len(do_posts)}')
    live_api=str(do_posts[0].get('source') or '')
    # Fail closed on unknown production drift. Normalize only final newline.
    if live_api.rstrip()!=base_api.rstrip():
        raise RuntimeError('LIVE_GAS_SOURCE_DRIFT_FROM_BETA118_BASE')
    files=[]; replaced=False; sa_seen=False
    for f in old_files:
        item=dict(f)
        if item.get('type')=='SERVER_JS' and 'function doPost(' in str(item.get('source') or ''):
            item['source']=current_api; replaced=True
        if item.get('type')=='SERVER_JS' and item.get('name')=='SUPERADMIN_AUTH_V2':
            item['source']=current_sa; sa_seen=True
        files.append(item)
    if not replaced: raise RuntimeError('doPost source not replaced')
    if not sa_seen: files.append({'name':'SUPERADMIN_AUTH_V2','type':'SERVER_JS','source':current_sa})
    merged='\n'.join(str(f.get('source') or '') for f in files if f.get('type')=='SERVER_JS')
    for token_text in ["action === 'superadmin_time_login'","action === 'superadmin_otp_login'",'function ppSaTimeLogin_(','function ppSaOtpLogin_(','SUPERADMIN_SPECIAL_AUTH_REQUIRED']:
        if token_text not in merged: raise RuntimeError('auth contract incomplete: '+token_text)
    for forbidden in ['superadmin_time_challenge','device_trust_secret','device_proof','PP_SUPERADMIN_DEVICE_']:
        if forbidden in merged: raise RuntimeError('device trust residue: '+forbidden)
    if 'for(let i=-5;i<=5;i++)' not in merged or 'input.length<1||input.length>20' not in merged or "!/^[0-9]{8}$/.test(otp)" not in merged:
        raise RuntimeError('owner auth semantics incomplete')
    req(f'{API}/{sid}/content',token,'PUT',{'files':files})
    new_version=None; deployed=False
    try:
        v=req(f'{API}/{sid}/versions',token,'POST',{'description':f'Pick Pack Beta119 SUPERADMIN two-method auth source {source}'})
        new_version=int(v['versionNumber'])
        payload={'deploymentConfig':{'scriptId':sid,'versionNumber':new_version,'manifestFileName':'appsscript','description':'Pick Pack 1291 Beta119 SUPERADMIN auth'}}
        req(f'{API}/{sid}/deployments/{dep}',token,'PUT',payload); deployed=True
        for i in range(12):
            d=req(f'{API}/{sid}/deployments/{dep}',token)
            if (d.get('deploymentConfig') or {}).get('versionNumber')==new_version: break
            if i==11: raise RuntimeError('deployment version readback mismatch')
            time.sleep(min(2+i*2,10))
        deployed_content=req(f'{API}/{sid}/content?versionNumber={new_version}',token)
        text=server(deployed_content)
        if sha(current_api) not in [sha(str(f.get('source') or '')) for f in deployed_content.get('files') or [] if f.get('type')=='SERVER_JS']:
            raise RuntimeError('deployed PICK_PACK_API exact source mismatch')
        if sha(current_sa) not in [sha(str(f.get('source') or '')) for f in deployed_content.get('files') or [] if f.get('type')=='SERVER_JS']:
            raise RuntimeError('deployed SUPERADMIN_AUTH_V2 exact source mismatch')
        for x in ["action === 'superadmin_time_login'","action === 'superadmin_otp_login'",'SUPERADMIN_SPECIAL_AUTH_REQUIRED']:
            if x not in text: raise RuntimeError('deployed auth route readback missing')
        data={'status':'PASS','production_write':True,'channel':'BETA','scope':'SUPERADMIN_AUTH_002','source_sha':source,'base_source_sha':base,'previous_deployment_version':old_version,'deployment_version':new_version,'pick_pack_api_sha256':sha(current_api),'superadmin_auth_v2_sha256':sha(current_sa),'device_binding':'FORBIDDEN_BY_OWNER','authority_change':'NONE','stable_write':False}
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8'); print(json.dumps(data))
    except Exception:
        if deployed:
            try:req(f'{API}/{sid}/deployments/{dep}',token,'PUT',{'deploymentConfig':{'scriptId':sid,'versionNumber':old_version,'manifestFileName':'appsscript','description':'Rollback Beta119 auth deploy failure'}})
            except Exception:pass
        try:req(f'{API}/{sid}/content',token,'PUT',{'files':old_files})
        except Exception:pass
        raise

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('BETA119_GAS_AUTH_DEPLOY_ERROR:'+str(e),file=sys.stderr); sys.exit(1)
