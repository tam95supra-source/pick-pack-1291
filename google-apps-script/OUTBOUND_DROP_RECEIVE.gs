// Beta77 — Nhận hàng rớt. Direct Android -> GAS -> Google Sheets authority.
// This file intentionally does not call Worker/D1/Supabase/service business paths.
const PP_OUTBOUND = Object.freeze({
  SHEET_ID: '1tl6har_8vGSVsVlcErfQwjX1YgvN3o-FRG5wQV4VTEM',
  OWNER_EMAIL: 'tam95.supra@gmail.com',
  LOCATION_SHEET: 'Vị trí',
  DROP_SHEET: 'Nhận hàng rớt',
  HEADERS: ['Vị trí','Ngày','Scan QR','DO','Số kiện','Người cập nhật','Thời gian cập nhật','ID bản ghi']
});

function ppOutboundSs_(){ return SpreadsheetApp.openById(PP_OUTBOUND.SHEET_ID); }
function ppOutboundSheet_(name){
  const sh=ppOutboundSs_().getSheetByName(name);
  if(!sh) throw new Error('OUTBOUND_SHEET_MISSING_'+name);
  return sh;
}
function ppOutboundOwner_(auth){ return !!auth && String(auth.role||'').toUpperCase()==='SUPERADMIN' && ppFold_(auth.email||'')===ppFold_(PP_OUTBOUND.OWNER_EMAIL); }
function ppOutboundNorm_(value){ return String(value||'').trim().replace(/\s+/g,' '); }
function ppOutboundKey_(value){ return ppFold_(ppOutboundNorm_(value)); }
function ppOutboundLocationCache_(){ return CacheService.getScriptCache(); }
function ppOutboundLocationsFromSheet_(sh){
  const last=sh.getLastRow(); if(last<2) return [];
  return sh.getRange(2,1,last-1,1).getDisplayValues().map(function(r){return ppOutboundNorm_(r[0]);}).filter(function(v){return !!v;});
}
function ppOutboundCacheLocations_(items){ try{ ppOutboundLocationCache_().put('PP_OUTBOUND_LOCATIONS_V1',JSON.stringify(items),300); }catch(_){} return items; }
function ppOutboundLocations_(){
  try{ const cached=ppOutboundLocationCache_().get('PP_OUTBOUND_LOCATIONS_V1'); if(cached){ const items=JSON.parse(cached); if(Array.isArray(items)) return items.map(ppOutboundNorm_).filter(Boolean); } }catch(_){}
  return ppOutboundCacheLocations_(ppOutboundLocationsFromSheet_(ppOutboundSheet_(PP_OUTBOUND.LOCATION_SHEET)));
}
function ppOutboundLocationList_(auth){
  return {ok:true,items:ppOutboundLocations_(),owner:ppOutboundOwner_(auth)};
}
function ppOutboundLocationMutate_(auth,body){
  if(!ppOutboundOwner_(auth)) return {ok:false,error:'OUTBOUND_OWNER_REQUIRED'};
  const op=String(body.operation||'').trim().toUpperCase();
  const before=ppOutboundNorm_(body.before||body.location||''), after=ppOutboundNorm_(body.after||body.location||'');
  if(['CREATE','UPDATE','DELETE'].indexOf(op)<0) return {ok:false,error:'OUTBOUND_LOCATION_OPERATION_INVALID'};
  if((op==='CREATE'||op==='UPDATE')&&!after) return {ok:false,error:'OUTBOUND_LOCATION_REQUIRED'};
  if(op!=='CREATE'&&!before) return {ok:false,error:'OUTBOUND_LOCATION_REQUIRED'};
  const sh=ppOutboundSheet_(PP_OUTBOUND.LOCATION_SHEET), values=ppOutboundLocationsFromSheet_(sh), keys=values.map(ppOutboundKey_);
  const beforeIndex=keys.indexOf(ppOutboundKey_(before)), afterIndex=keys.indexOf(ppOutboundKey_(after));
  if(op==='CREATE'){
    if(afterIndex>=0) return {ok:false,error:'OUTBOUND_LOCATION_DUPLICATE'};
    sh.appendRow([after]);
  } else if(op==='UPDATE'){
    if(beforeIndex<0) return {ok:false,error:'OUTBOUND_LOCATION_NOT_FOUND'};
    if(afterIndex>=0 && afterIndex!==beforeIndex) return {ok:false,error:'OUTBOUND_LOCATION_DUPLICATE'};
    sh.getRange(beforeIndex+2,1).setValue(after);
  } else {
    if(beforeIndex<0) return {ok:false,error:'OUTBOUND_LOCATION_NOT_FOUND'};
    sh.deleteRow(beforeIndex+2);
  }
  SpreadsheetApp.flush();
  const readback=ppOutboundLocationsFromSheet_(sh);
  const expected=op==='DELETE' ? readback.map(ppOutboundKey_).indexOf(ppOutboundKey_(before))<0 : readback.map(ppOutboundKey_).indexOf(ppOutboundKey_(after))>=0;
  if(!expected) return {ok:false,error:'OUTBOUND_LOCATION_READBACK_FAILED'};
  ppOutboundCacheLocations_(readback);
  ppHistorySafeAppendS13_({event_type:'OUTBOUND_LOCATION_'+op,label:'Nhận hàng rớt • '+op,actor:auth.login_id,detail:(op==='UPDATE'?before+' → '+after:(op==='DELETE'?before:after)),event_id:String(body.event_id||Utilities.getUuid()),scope:'OUTBOUND'});
  return {ok:true,items:readback,owner:true};
}
function ppOutboundFindRecord_(sh,id){
  const key=String(id||'').trim(); if(!key) return null;
  const last=sh.getLastRow(); if(last<2) return null;
  const found=sh.getRange(2,8,last-1,1).createTextFinder(key).matchEntireCell(true).findNext();
  if(!found) return null;
  const row=found.getRow(); return {row:row,values:sh.getRange(row,1,1,8).getDisplayValues()[0]};
}
function ppOutboundAppend_(auth,body){
  const id=String(body.idempotency_key||body.record_id||'').trim();
  const location=ppOutboundNorm_(body.location), rawQr=String(body.scan_qr||''), orderNo=String(body.do_number||'').trim();
  const countRaw=String(body.package_count||'').trim(), count=Number(countRaw);
  if(!id) return {ok:false,error:'OUTBOUND_IDEMPOTENCY_REQUIRED'};
  if(!location) return {ok:false,error:'OUTBOUND_LOCATION_REQUIRED'};
  if(ppOutboundLocations_().map(ppOutboundKey_).indexOf(ppOutboundKey_(location))<0) return {ok:false,error:'OUTBOUND_LOCATION_INVALID'};
  if(!orderNo || orderNo.length>80) return {ok:false,error:'OUTBOUND_DO_INVALID'};
  if(!/^[0-9]+$/.test(countRaw) || !Number.isInteger(count) || count<=0 || count>999999) return {ok:false,error:'OUTBOUND_PACKAGE_COUNT_INVALID'};
  if(rawQr.length>2000) return {ok:false,error:'OUTBOUND_QR_TOO_LONG'};
  const sh=ppOutboundSheet_(PP_OUTBOUND.DROP_SHEET), existing=ppOutboundFindRecord_(sh,id);
  if(existing) return {ok:true,idempotent:true,row:existing.row,item:existing.values};
  const day=ppBusinessVisible_(), at=ppNowVisible_(), actor=String(auth.display_name||auth.login_id||'').trim() || String(auth.login_id||'').trim();
  const row=[location,day,rawQr,orderNo,count,actor,at,id];
  sh.appendRow(row);
  SpreadsheetApp.flush();
  const written=ppOutboundFindRecord_(sh,id);
  if(!written) return {ok:false,error:'OUTBOUND_APPEND_READBACK_MISSING'};
  const got=written.values;
  if(String(got[0])!==location || String(got[2])!==rawQr || String(got[3])!==orderNo || String(got[4])!==String(count) || String(got[7])!==id) return {ok:false,error:'OUTBOUND_APPEND_READBACK_MISMATCH'};
  ppHistorySafeAppendS13_({event_type:'OUTBOUND_DROP_APPEND',label:'Nhận hàng rớt • Thêm thông tin',actor:auth.login_id,detail:'Vị trí '+location+' • DO '+orderNo+' • Số kiện '+count,event_id:id,scope:'OUTBOUND'});
  return {ok:true,idempotent:false,row:written.row,item:got};
}
function ppOutboundClear_(auth,body){
  if(!auth || String(auth.role||'').toUpperCase()!=='SUPERADMIN') return {ok:false,error:'SUPERADMIN_REQUIRED'};
  const eventId=String(body.idempotency_key||body.event_id||'').trim();
  if(!eventId) return {ok:false,error:'OUTBOUND_IDEMPOTENCY_REQUIRED'};
  if(ppMasterMutationSeen_(eventId)) return {ok:true,idempotent:true,rows_deleted:0};
  const sh=ppOutboundSheet_(PP_OUTBOUND.DROP_SHEET), last=sh.getLastRow(), rows=Math.max(0,last-1);
  if(rows>0) sh.getRange(2,1,rows,8).clearContent();
  SpreadsheetApp.flush();
  const remaining=Math.max(0,sh.getLastRow()-1);
  if(remaining!==0) return {ok:false,error:'OUTBOUND_CLEAR_READBACK_FAILED',remaining:remaining};
  ppMarkMasterMutation_(eventId);
  ppHistorySafeAppendS13_({event_type:'OUTBOUND_DROP_CLEAR',label:'Nhận hàng rớt • Xóa toàn bộ',actor:auth.login_id,detail:'Đã xóa '+rows+' dòng dữ liệu nghiệp vụ; giữ nguyên header, quyền, protected ranges và Vị trí.',event_id:eventId,scope:'OUTBOUND'});
  return {ok:true,idempotent:false,rows_deleted:rows,remaining:0};
}
