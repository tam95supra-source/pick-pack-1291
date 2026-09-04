#!/usr/bin/env python3
from pathlib import Path

p = Path('google-apps-script/PICK_PACK_API.gs')
s = p.read_text()

func = r'''function ppStableRuntimeCanary_(body){
  if(ppEnvironmentId_()!=='STABLE'||ppServiceAudience_()!=='PICK_PACK_1291_STABLE')return {ok:false,error:'STABLE_CANARY_ENVIRONMENT_REQUIRED'};
  const token=String((body||{}).google_access_token||''),id=String((body||{}).canary_id||'').trim(),op=String((body||{}).operation||'').toUpperCase();
  if(!/^__CI_STABLE_CANARY_[A-Za-z0-9_-]{8,96}$/.test(id)||['UPSERT','CLEANUP'].indexOf(op)<0)return {ok:false,error:'STABLE_CANARY_FIELDS_INVALID'};
  const ss=ppSs_();if(!token||!ppStableOwnerFile_(token,ss.getId(),'application/vnd.google-apps.spreadsheet'))return {ok:false,error:'STABLE_CANARY_OWNER_PROOF_FAILED'};
  const p=PropertiesService.getScriptProperties(),propsOk=p.getProperty('PP_STABLE_PROVISIONED')==='1'&&p.getProperty('PP_ENVIRONMENT_ID')==='STABLE'&&p.getProperty('PP_SERVICE_AUDIENCE')==='PICK_PACK_1291_STABLE'&&p.getProperty('PP_SHEET_ID')===ss.getId();
  if(!propsOk)return {ok:false,error:'STABLE_CANARY_PROPERTIES_MISMATCH'};
  const lock=LockService.getScriptLock();lock.waitLock(10000);
  try{
    const name='__STABLE_RUNTIME_CANARY';let sh=ss.getSheetByName(name);
    if(op==='CLEANUP'){
      if(!sh)return {ok:true,idempotent:true,operation:'CLEANUP',environment_id:'STABLE',kind:'PRIMARY',cleanup:true,properties_ok:true,bound_sheet:true};
      const last=sh.getLastRow();let removed=0;
      if(last>=2){const vals=sh.getRange(2,1,last-1,1).getDisplayValues();for(let i=vals.length-1;i>=0;i--){if(String(vals[i][0]||'')===id){sh.deleteRow(i+2);removed++;}}}
      if(sh.getLastRow()<=1)ss.deleteSheet(sh);SpreadsheetApp.flush();
      return {ok:true,idempotent:removed===0,operation:'CLEANUP',environment_id:'STABLE',kind:'PRIMARY',removed:removed,cleanup:true,properties_ok:true,bound_sheet:true};
    }
    if(!sh){sh=ss.insertSheet(name);sh.getRange(1,1,1,4).setValues([['canary_id','environment_id','kind','created_at']]);sh.hideSheet();}
    const last=sh.getLastRow(),hit=last>=2?sh.getRange(2,1,last-1,1).createTextFinder(id).matchEntireCell(true).findNext():null;
    if(hit)return {ok:true,idempotent:true,operation:'UPSERT',environment_id:'STABLE',kind:'PRIMARY',row:hit.getRow(),properties_ok:true,bound_sheet:true};
    sh.appendRow([id,'STABLE','PRIMARY',ppNowIso_()]);SpreadsheetApp.flush();
    return {ok:true,idempotent:false,operation:'UPSERT',environment_id:'STABLE',kind:'PRIMARY',row:sh.getLastRow(),properties_ok:true,bound_sheet:true};
  } finally {lock.releaseLock();}
}
'''
route = "    if (action === 'stable_runtime_canary') return ppJson_(ppStableRuntimeCanary_(body));\n"

changed = False
if 'function ppStableRuntimeCanary_(body)' not in s:
    marker = 'function ppStableAdminBootstrap_(body){'
    if marker not in s:
        raise SystemExit('RESTORE_MARKER_FUNCTION_MISSING')
    s = s.replace(marker, func + marker, 1)
    changed = True

if "action === 'stable_runtime_canary'" not in s:
    marker = "    if (action === 'stable_admin_bootstrap') return ppJson_(ppStableAdminBootstrap_(body));\n"
    if marker not in s:
        raise SystemExit('RESTORE_MARKER_ROUTE_MISSING')
    s = s.replace(marker, marker + route, 1)
    changed = True

if s.count('function ppStableRuntimeCanary_(body)') != 1:
    raise SystemExit('CANARY_FUNCTION_NOT_UNIQUE')
if s.count("action === 'stable_runtime_canary'") != 1:
    raise SystemExit('CANARY_ROUTE_NOT_UNIQUE')

p.write_text(s)
print('stable_primary_canary_source=' + ('RESTORED' if changed else 'ALREADY_PRESENT'))
