// SUPERADMIN_AUTH_V2 — Beta119
// Runtime credential material is stored only in Apps Script private ScriptProperties.
// No password, OTP, device trust secret or pepper is persisted in this repository/logs.

function ppSaEq_(a,b){
  a=String(a||'');b=String(b||'');if(a.length!==b.length)return false;
  let d=0;for(let i=0;i<a.length;i++)d|=(a.charCodeAt(i)^b.charCodeAt(i));return d===0;
}
function ppSaHmacB64u_(key,value){return ppB64u_(Utilities.computeHmacSha256Signature(String(value||''),String(key||'')));}
function ppSaAccount_(login){
  const a=ppAccount_(String(login||'').trim());
  return a&&a.status==='ACTIVE'&&String(a.role||'').toUpperCase()==='SUPERADMIN'?a:null;
}
function ppSaIssueSession_(a,body,extra){
  const session=ppBindSession_(a.login_id,ppDeviceId_(body)),token=ppMakeToken_(a,session),out={
    ok:true,token:token,
    account:{login_id:a.login_id,role:a.role,display_name:a.display_name,position:a.position||'',email:a.email||PP.RESET_ADMIN_EMAIL},
    session:{issued_at:session.issued_at,device_label:String(body._device_label||'').slice(0,120)}
  };
  Object.keys(extra||{}).forEach(function(k){out[k]=extra[k];});return out;
}
function ppSaRateKey_(kind,body){return 'PP_SA_RATE_'+kind+'_'+ppSha256Hex_(String(body.login_id||'')+'|'+ppDeviceId_(body)).slice(0,42);}
function ppSaRateConsume_(kind,body,limit,ttl){
  const c=CacheService.getScriptCache(),k=ppSaRateKey_(kind,body),n=Number(c.get(k)||0)+1;c.put(k,String(n),ttl);return n<=limit;
}
function ppSaRateClear_(kind,body){CacheService.getScriptCache().remove(ppSaRateKey_(kind,body));}
function ppSaOtpValue_(){
  let out='';while(out.length<8){const bytes=ppRandom_(16);for(let i=0;i<bytes.length&&out.length<8;i++){const n=(bytes[i]+256)%256;if(n<250)out+=String(n%10);}}
  return out;
}
function ppSaPepperUnlocked_(){
  const p=PropertiesService.getScriptProperties();let v=String(p.getProperty('PP_SUPERADMIN_OTP_PEPPER')||'');
  if(!v){v=ppB64u_(ppRandom_(48));p.setProperty('PP_SUPERADMIN_OTP_PEPPER',v);}return v;
}
function ppSaOtpStateKey_(login){return 'PP_SUPERADMIN_OTP_'+ppSha256Hex_(ppEnvironmentId_()+'|'+String(login||'')).slice(0,40);}
function ppSaOtpVerifier_(pepper,login,generation,otp){return ppSaHmacB64u_(pepper,'PP_SA_OTP_V1|'+String(login||'')+'|'+String(generation||'')+'|'+String(otp||''));}
function ppSaNewOtpStateUnlocked_(login){
  const otp=ppSaOtpValue_(),generation=Utilities.getUuid(),pepper=ppSaPepperUnlocked_();
  return {otp:otp,state:{generation_id:generation,verifier:ppSaOtpVerifier_(pepper,login,generation,otp),issued_at:Date.now()}};
}
function ppSaSendOtp_(a,otp,reason){
  const email=String(a.email||PP.RESET_ADMIN_EMAIL).trim();if(!ppEmailValid_(email))throw new Error('SUPERADMIN_EMAIL_INVALID');
  const subject='PICK PACK 1291 - Mật khẩu một lần SUPERADMIN';
  const body='Tài khoản: '+a.login_id+'\nMật khẩu một lần: '+otp+'\nMã gồm 8 chữ số và chỉ dùng một lần.\nLý do cấp: '+String(reason||'LOGIN')+'\n\nKhông chia sẻ mã này cho người khác.';
  MailApp.sendEmail({to:email,subject:subject,body:body});
}
function ppSaForgotPasswordV2_(body){
  const login=String(body.login_id||'').trim(),a=ppSaAccount_(login);
  if(!a)return ppForgotPassword_(body);
  const generic={ok:true,delivery:'ACCOUNT_EMAIL',message:'RESET_REQUEST_ACCEPTED'};
  if(!ppSaRateConsume_('OTP_SEND',body,1,300))return generic;
  const lock=LockService.getScriptLock();lock.waitLock(10000);
  try{
    const props=PropertiesService.getScriptProperties(),key=ppSaOtpStateKey_(a.login_id),old=props.getProperty(key),next=ppSaNewOtpStateUnlocked_(a.login_id);
    props.setProperty(key,JSON.stringify(next.state));
    try{ppSaSendOtp_(a,next.otp,'YÊU CẦU MÃ MỚI');}
    catch(err){if(old===null)props.deleteProperty(key);else props.setProperty(key,old);throw err;}
    return generic;
  } finally {lock.releaseLock();}
}
function ppSaTimeMatches_(value){
  const input=String(value||'');if(input.length<1||input.length>20)return false;
  const now=Date.now();for(let i=-5;i<=5;i++){const hhmm=Utilities.formatDate(new Date(now+i*60000),PP.TZ,'HHmm');if(input.indexOf(hhmm)>=0)return true;}return false;
}
function ppSaTimeLogin_(body){
  if(!ppSaRateConsume_('TIME_LOGIN',body,8,600))return {ok:false,error:'LOGIN_TEMP_LOCKED'};
  const login=String(body.login_id||'').trim(),a=ppSaAccount_(login),input=String(body.time_input||'');
  if(!a||!ppSaTimeMatches_(input))return {ok:false,error:'INVALID_CREDENTIALS'};
  ppSaRateClear_('TIME_LOGIN',body);return ppSaIssueSession_(a,body,{auth_method:'SUPERADMIN_TIME'});
}
function ppSaOtpLogin_(body){
  if(!ppSaRateConsume_('OTP_LOGIN',body,6,600))return {ok:false,error:'LOGIN_TEMP_LOCKED'};
  const login=String(body.login_id||'').trim(),a=ppSaAccount_(login),otp=String(body.otp||'');
  if(!a||!/^[0-9]{8}$/.test(otp))return {ok:false,error:'INVALID_CREDENTIALS'};
  const lock=LockService.getScriptLock();lock.waitLock(10000);
  try{
    const props=PropertiesService.getScriptProperties(),key=ppSaOtpStateKey_(login),raw=props.getProperty(key);if(!raw)return {ok:false,error:'INVALID_CREDENTIALS'};
    let state=null;try{state=JSON.parse(raw);}catch(_){return {ok:false,error:'INVALID_CREDENTIALS'};}
    const pepper=ppSaPepperUnlocked_(),expected=ppSaOtpVerifier_(pepper,login,state.generation_id,otp);
    if(!ppSaEq_(String(state.verifier||''),expected))return {ok:false,error:'INVALID_CREDENTIALS'};
    const next=ppSaNewOtpStateUnlocked_(login);
    props.setProperty(key,JSON.stringify(next.state));
    try{ppSaSendOtp_(a,next.otp,'MÃ KẾ TIẾP SAU KHI ĐĂNG NHẬP');}
    catch(err){props.setProperty(key,raw);throw err;}
    ppSaRateClear_('OTP_LOGIN',body);return ppSaIssueSession_(a,body,{auth_method:'SUPERADMIN_OTP',otp_rotated:true});
  } finally {lock.releaseLock();}
}
