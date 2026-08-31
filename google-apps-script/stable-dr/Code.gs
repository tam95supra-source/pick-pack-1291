const DR={OWNER:'tam95.supra@gmail.com',ALLOWED:['Danh mục','LỊCH SỬ NGHIỆP VỤ','DANH SÁCH PDA','DANH SÁCH USER PICK','DANH SÁCH BÀN PACK','DANH SÁCH USER PACK','DANH SÁCH NHÂN SỰ','RA - VÀO TRONG CA','CÔNG NHẬT','Danh sách Admin']};
function json_(x){return ContentService.createTextOutput(JSON.stringify(x)).setMimeType(ContentService.MimeType.JSON);}
function fold_(v){return String(v||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase().trim();}
function sha_(v){return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,String(v||''),Utilities.Charset.UTF_8).map(function(b){return ('0'+((b+256)%256).toString(16)).slice(-2);}).join('');}
function ss_(){const s=SpreadsheetApp.getActiveSpreadsheet();if(!s)throw new Error('BOUND_SHEET_REQUIRED');return s;}
function ownerFile_(token){const id=ss_().getId(),r=UrlFetchApp.fetch('https://www.googleapis.com/drive/v3/files/'+encodeURIComponent(id)+'?fields=id,mimeType,owners(emailAddress)',{muteHttpExceptions:true,headers:{Authorization:'Bearer '+String(token||'')}});if(r.getResponseCode()<200||r.getResponseCode()>=300)return false;let j={};try{j=JSON.parse(r.getContentText()||'{}');}catch(_){return false;}return j.id===id&&j.mimeType==='application/vnd.google-apps.spreadsheet'&&(j.owners||[]).some(function(x){return fold_(x.emailAddress)===fold_(DR.OWNER);});}
function provision_(b){const p=PropertiesService.getScriptProperties(),token=String(b.google_access_token||''),secret=String(b.bridge_secret||'');if(!token||secret.length<32||!ownerFile_(token))return {ok:false,error:'PROVISION_OWNER_PROOF_FAILED'};if(p.getProperty('DR_PROVISIONED')==='1')return p.getProperty('DR_SHEET_ID')===ss_().getId()?{ok:true,idempotent:true,environment_id:'STABLE',kind:'DR'}:{ok:false,error:'PROVISION_LOCK_MISMATCH'};p.setProperties({DR_PROVISIONED:'1',DR_ENV:'STABLE',DR_SHEET_ID:ss_().getId(),DR_BRIDGE_SECRET:secret},false);return {ok:true,idempotent:false,environment_id:'STABLE',kind:'DR',writer_scope:'BOUND_CURRENT_ONLY'};}
function auth_(b){const p=PropertiesService.getScriptProperties(),e=String(p.getProperty('DR_BRIDGE_SECRET')||''),g=String(b._bridge_secret||'');return p.getProperty('DR_PROVISIONED')==='1'&&e.length>=32&&g.length>=32&&sha_(e)===sha_(g)&&String(b._environment_id||'')==='STABLE';}
function runtimeCanary_(b){
  const p=PropertiesService.getScriptProperties(),token=String(b.google_access_token||''),id=String(b.canary_id||''),op=String(b.operation||'').toUpperCase(),ss=ss_();
  if(String(b._environment_id||'')!=='STABLE'||String(b._service_audience||'')!=='PICK_PACK_1291_STABLE')return {ok:false,error:'STABLE_CANARY_ENVIRONMENT_REQUIRED'};
  if(!/^__CI_STABLE_CANARY_[A-Za-z0-9_-]{8,96}$/.test(id)||['UPSERT','CLEANUP'].indexOf(op)<0)return {ok:false,error:'STABLE_CANARY_FIELDS_INVALID'};
  if(!token||!ownerFile_(token))return {ok:false,error:'STABLE_CANARY_OWNER_PROOF_FAILED'};
  const propsOk=p.getProperty('DR_PROVISIONED')==='1'&&p.getProperty('DR_ENV')==='STABLE'&&p.getProperty('DR_SHEET_ID')===ss.getId();if(!propsOk)return {ok:false,error:'STABLE_CANARY_PROPERTIES_MISMATCH'};
  const lock=LockService.getScriptLock();lock.waitLock(10000);
  try{
    const name='__STABLE_RUNTIME_CANARY';let sh=ss.getSheetByName(name);
    if(op==='CLEANUP'){
      if(!sh)return {ok:true,idempotent:true,environment_id:'STABLE',kind:'DR',cleanup:true,properties_ok:true,bound_sheet:true};
      const last=sh.getLastRow();let removed=0;if(last>=2){const vals=sh.getRange(2,1,last-1,1).getDisplayValues();for(let i=vals.length-1;i>=0;i--)if(String(vals[i][0]||'')===id){sh.deleteRow(i+2);removed++;}}
      if(sh.getLastRow()<=1)ss.deleteSheet(sh);SpreadsheetApp.flush();
      return {ok:true,idempotent:removed===0,environment_id:'STABLE',kind:'DR',cleanup:true,removed:removed,properties_ok:true,bound_sheet:true};
    }
    if(!sh){sh=ss.insertSheet(name);sh.getRange(1,1,1,4).setValues([['canary_id','environment_id','kind','created_at']]);sh.hideSheet();}
    const last=sh.getLastRow(),hit=last>=2?sh.getRange(2,1,last-1,1).createTextFinder(id).matchEntireCell(true).findNext():null;
    if(hit)return {ok:true,idempotent:true,environment_id:'STABLE',kind:'DR',row:hit.getRow(),properties_ok:true,bound_sheet:true};
    sh.appendRow([id,'STABLE','DR',new Date().toISOString()]);SpreadsheetApp.flush();
    return {ok:true,idempotent:false,environment_id:'STABLE',kind:'DR',row:sh.getLastRow(),properties_ok:true,bound_sheet:true};
  } finally {lock.releaseLock();}
}
function bridge_(b){if(!auth_(b))return {ok:false,error:'BRIDGE_UNAUTHORIZED'};if(String(b.operation||'')!=='replace_table')return {ok:false,error:'BRIDGE_OPERATION_UNKNOWN'};const name=String(b.sheet||'');if(DR.ALLOWED.indexOf(name)<0)return {ok:false,error:'DR_SHEET_REJECTED'};const headers=Array.isArray(b.headers)?b.headers:[],rows=Array.isArray(b.rows)?b.rows:[],ss=ss_();let sh=ss.getSheetByName(name);if(!sh)sh=ss.insertSheet(name);const cols=Math.max(1,headers.length),needRows=Math.max(100,rows.length+1);if(sh.getMaxColumns()<cols)sh.insertColumnsAfter(sh.getMaxColumns(),cols-sh.getMaxColumns());if(sh.getMaxRows()<needRows)sh.insertRowsAfter(sh.getMaxRows(),needRows-sh.getMaxRows());sh.clearContents();if(headers.length)sh.getRange(1,1,1,headers.length).setValues([headers]);for(let i=0;i<rows.length;i+=400){const chunk=rows.slice(i,i+400);if(chunk.length)sh.getRange(i+2,1,chunk.length,cols).setValues(chunk);}SpreadsheetApp.flush();return {ok:true,sheet:name,row_count:rows.length};}
function doGet(){return json_({ok:true,environment_id:'STABLE',kind:'DR',writer_scope:'BOUND_CURRENT_ONLY',provisioned:PropertiesService.getScriptProperties().getProperty('DR_PROVISIONED')==='1'});}
function doPost(e){try{const b=JSON.parse((e&&e.postData&&e.postData.contents)||'{}');if(b.action==='stable_bound_provision')return json_(provision_(b));if(b.action==='stable_bound_bridge')return json_(bridge_(b));if(b.action==='stable_runtime_canary')return json_(runtimeCanary_(b));return json_({ok:false,error:'UNKNOWN_ACTION'});}catch(err){console.error(String(err&&err.message||err).slice(0,300));return json_({ok:false,error:'BOUND_DR_ERROR'});}}
