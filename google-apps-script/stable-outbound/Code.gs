const SB={TZ:'Asia/Bangkok',OWNER:'tam95.supra@gmail.com',LOC:'Vị trí',DROP:'Nhận hàng rớt'};
function json_(x){return ContentService.createTextOutput(JSON.stringify(x)).setMimeType(ContentService.MimeType.JSON);}
function fold_(v){return String(v||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase().trim();}
function sha_(v){return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,String(v||''),Utilities.Charset.UTF_8).map(function(b){return ('0'+((b+256)%256).toString(16)).slice(-2);}).join('');}
function ss_(){const s=SpreadsheetApp.getActiveSpreadsheet();if(!s)throw new Error('BOUND_SHEET_REQUIRED');return s;}
function ownerFile_(token){
  const id=ss_().getId(),r=UrlFetchApp.fetch('https://www.googleapis.com/drive/v3/files/'+encodeURIComponent(id)+'?fields=id,mimeType,owners(emailAddress)',{muteHttpExceptions:true,headers:{Authorization:'Bearer '+String(token||'')}});
  if(r.getResponseCode()<200||r.getResponseCode()>=300)return false;let j={};try{j=JSON.parse(r.getContentText()||'{}');}catch(_){return false;}
  return j.id===id&&j.mimeType==='application/vnd.google-apps.spreadsheet'&&(j.owners||[]).some(function(x){return fold_(x.emailAddress)===fold_(SB.OWNER);});
}
function provision_(b){
  const p=PropertiesService.getScriptProperties(),token=String(b.google_access_token||''),secret=String(b.bridge_secret||'');
  if(!token||secret.length<32||!ownerFile_(token))return {ok:false,error:'PROVISION_OWNER_PROOF_FAILED'};
  if(p.getProperty('SB_PROVISIONED')==='1')return p.getProperty('SB_SHEET_ID')===ss_().getId()?{ok:true,idempotent:true,environment_id:'STABLE',kind:'OUTBOUND'}:{ok:false,error:'PROVISION_LOCK_MISMATCH'};
  p.setProperties({SB_PROVISIONED:'1',SB_ENV:'STABLE',SB_KIND:'OUTBOUND',SB_SHEET_ID:ss_().getId(),SB_BRIDGE_SECRET:secret},false);
  return {ok:true,idempotent:false,environment_id:'STABLE',kind:'OUTBOUND',writer_scope:'BOUND_CURRENT_ONLY'};
}
function auth_(b){const p=PropertiesService.getScriptProperties(),e=String(p.getProperty('SB_BRIDGE_SECRET')||''),g=String(b._bridge_secret||'');return p.getProperty('SB_PROVISIONED')==='1'&&e.length>=32&&g.length>=32&&sha_(e)===sha_(g)&&String(b._environment_id||'')==='STABLE';}
function sh_(name){if([SB.LOC,SB.DROP].indexOf(String(name||''))<0)throw new Error('SHEET_REJECTED');const s=ss_().getSheetByName(name);if(!s)throw new Error('SHEET_MISSING');return s;}
function range_(sheet,range){if(!/^([A-Z]{1,2})([0-9]*)(:([A-Z]{1,2})([0-9]*))?$/.test(String(range||'')))throw new Error('RANGE_REJECTED');return sh_(sheet).getRange(range);}
function bridge_(b){
  if(!auth_(b))return {ok:false,error:'BRIDGE_UNAUTHORIZED'};const op=String(b.operation||'');
  if(op==='get_values')return {ok:true,values:range_(b.sheet,b.range).getDisplayValues()};
  if(op==='put_values'){const v=Array.isArray(b.values)?b.values:[];if(v.length)range_(b.sheet,b.range).setValues(v);SpreadsheetApp.flush();return {ok:true};}
  if(op==='append_values'){const v=Array.isArray(b.values)?b.values:[];if(!v.length)return {ok:true};const sh=sh_(b.sheet),first=sh.getLastRow()+1;sh.getRange(first,1,v.length,v[0].length).setValues(v);SpreadsheetApp.flush();return {ok:true,row:first};}
  return {ok:false,error:'BRIDGE_OPERATION_UNKNOWN'};
}
function locations_(){const sh=sh_(SB.LOC),last=sh.getLastRow();return last<2?[]:sh.getRange(2,1,last-1,1).getDisplayValues().map(function(r){return String(r[0]||'').trim();}).filter(Boolean);}
function locKey_(v){return fold_(String(v||'').replace(/\s+/g,' '));}
function findDrop_(id){const sh=sh_(SB.DROP),last=sh.getLastRow();if(last<2)return null;const f=sh.getRange(2,8,last-1,1).createTextFinder(String(id||'')).matchEntireCell(true).findNext();return f?{row:f.getRow(),values:sh.getRange(f.getRow(),1,1,8).getDisplayValues()[0]}:null;}
function business_(b){
  if(!auth_(b))return {ok:false,error:'BRIDGE_UNAUTHORIZED'};const op=String(b.operation||''),actor=b.actor||{},body=b.body||{};
  if(fold_(actor.role)!=='SUPERADMIN'||fold_(actor.email)!==fold_(SB.OWNER))return {ok:false,error:'OUTBOUND_OWNER_REQUIRED'};
  if(op==='outbound_location_list')return {ok:true,items:locations_(),owner:true};
  if(op==='outbound_location_mutate'){
    const action=String(body.operation||'').toUpperCase(),before=String(body.before||body.location||'').trim(),after=String(body.after||body.location||'').trim(),sh=sh_(SB.LOC),items=locations_(),keys=items.map(locKey_),bi=keys.indexOf(locKey_(before)),ai=keys.indexOf(locKey_(after));
    if(['CREATE','UPDATE','DELETE'].indexOf(action)<0)return {ok:false,error:'OUTBOUND_LOCATION_OPERATION_INVALID'};
    if(action==='CREATE'){if(!after)return {ok:false,error:'OUTBOUND_LOCATION_REQUIRED'};if(ai>=0)return {ok:false,error:'OUTBOUND_LOCATION_DUPLICATE'};sh.appendRow([after]);}
    if(action==='UPDATE'){if(bi<0)return {ok:false,error:'OUTBOUND_LOCATION_NOT_FOUND'};if(ai>=0&&ai!==bi)return {ok:false,error:'OUTBOUND_LOCATION_DUPLICATE'};sh.getRange(bi+2,1).setValue(after);}
    if(action==='DELETE'){if(bi<0)return {ok:false,error:'OUTBOUND_LOCATION_NOT_FOUND'};sh.deleteRow(bi+2);}
    SpreadsheetApp.flush();return {ok:true,items:locations_(),owner:true};
  }
  if(op==='outbound_drop_append'){
    const id=String(body.idempotency_key||body.record_id||'').trim(),location=String(body.location||'').trim(),qr=String(body.scan_qr||''),doNo=String(body.do_number||'').trim(),count=Number(body.package_count||0);
    if(!id||!location||!doNo||!Number.isInteger(count)||count<=0)return {ok:false,error:'OUTBOUND_FIELDS_INVALID'};const old=findDrop_(id);if(old)return {ok:true,idempotent:true,row:old.row,item:old.values};
    if(locations_().map(locKey_).indexOf(locKey_(location))<0)return {ok:false,error:'OUTBOUND_LOCATION_INVALID'};
    const sh=sh_(SB.DROP),row=[location,Utilities.formatDate(new Date(),SB.TZ,'dd/MM/yyyy'),qr,doNo,count,String(actor.display_name||actor.login_id||''),Utilities.formatDate(new Date(),SB.TZ,'dd/MM/yyyy HH:mm:ss'),id];sh.appendRow(row);SpreadsheetApp.flush();
    const got=findDrop_(id);return got?{ok:true,idempotent:false,row:got.row,item:got.values}:{ok:false,error:'OUTBOUND_APPEND_READBACK_MISSING'};
  }
  if(op==='outbound_drop_clear'){const sh=sh_(SB.DROP);if(sh.getLastRow()>1)sh.getRange(2,1,sh.getLastRow()-1,8).clearContent();return {ok:true};}
  return {ok:false,error:'OUTBOUND_OPERATION_UNKNOWN'};
}
function doGet(){return json_({ok:true,environment_id:'STABLE',kind:'OUTBOUND',writer_scope:'BOUND_CURRENT_ONLY',provisioned:PropertiesService.getScriptProperties().getProperty('SB_PROVISIONED')==='1'});}
function doPost(e){try{const b=JSON.parse((e&&e.postData&&e.postData.contents)||'{}');if(b.action==='stable_bound_provision')return json_(provision_(b));if(b.action==='stable_bound_bridge')return json_(bridge_(b));if(b.action==='stable_bound_business')return json_(business_(b));return json_({ok:false,error:'UNKNOWN_ACTION'});}catch(err){console.error(String(err&&err.message||err).slice(0,300));return json_({ok:false,error:'BOUND_OUTBOUND_ERROR'});}}
