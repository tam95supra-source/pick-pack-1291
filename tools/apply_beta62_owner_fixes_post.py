from pathlib import Path

ROOT=Path('.')
def read(p): return (ROOT/p).read_text(encoding='utf-8')
def write(p,s): (ROOT/p).write_text(s,encoding='utf-8')
def rep(s,a,b,label):
    n=s.count(a)
    if n!=1: raise SystemExit(f'{label}: expected 1 occurrence, got {n}')
    return s.replace(a,b,1)

p=Path('app/src/main/java/vn/pickpack1291/app/beta/BetaApiClient.kt');s=read(p)
old='''        var result=request(bearer)
        if(result.code==401){
            M2ServiceSessionManager.clearIfSame(appContext,bearer)
            val fresh=M2ServiceSessionManager.ensure(appContext,base,token,force=true).orEmpty()
            if(fresh.isNotBlank())result=request(fresh)
        }
        return result'''
new='''        var result=request(bearer)
        if(result.code==401){
            M2ServiceSessionManager.clearIfSame(appContext,bearer)
            val fresh=M2ServiceSessionManager.ensure(appContext,base,token,force=true).orEmpty()
            if(fresh.isNotBlank()){bearer=fresh;result=request(fresh)}
        }
        // One same-idempotency retry is safe for an atomic optimistic race; deterministic lease/validation conflicts remain errors.
        if(action=="session_work_update" && result.code==409 && result.error=="SESSION_WORK_CONFLICT") result=request(bearer)
        return result'''
s=rep(s,old,new,'session conflict retry exact')
write(p,s)

p=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt');s=read(p)
# Every MNV scan entry is one line and uses the exact compact owner-facing hint.
s=rep(s,'private fun mnvInput(h:String)=scanField(h,true,50)','private fun mnvInput(h:String)=scanField(h,true,50).apply{setSingleLine(true);minLines=1;maxLines=1;setHorizontallyScrolling(true)}','one-line mnv helper')
s=s.replace('mnvInput("Mã nhân viên").apply{setText(initialMnv)}','mnvInput("Scan / Nhập mã nhân viên").apply{setText(initialMnv)}')

# Resource home/list: remove explanatory owner/AI notes and PDA subtitle entirely.
s=s.replace('        body.addView(info("Quản lý danh mục tài nguyên dùng chung. USER được xem; ADMIN/SUPERADMIN được thêm, sửa, xóa và cập nhật tình trạng."));body.addView(gap(10))\n','')
s=s.replace('Triple("PDA","DANH SÁCH PDA","PDA")','Triple("PDA","DANH SÁCH PDA","")')
# Natural ordering for numbered resource ids.
s=rep(s,'            if(rows.isEmpty())box.addView(info("Chưa có dữ liệu."))\n            rows.forEach{x->','            rows.sortWith(Comparator{a,b->naturalUserCompare(a.optString("resource_id"),b.optString("resource_id"))})\n            if(rows.isEmpty())box.addView(info("Chưa có dữ liệu."))\n            rows.forEach{x->','resource natural sort')

# Professional business-card balance: vertically center content and trim unused lower space.
s=rep(s,'        gravity=Gravity.CENTER_HORIZONTAL\n        setPadding(dp(8),dp(6),dp(8),dp(5))','        gravity=Gravity.CENTER\n        setPadding(dp(8),dp(6),dp(8),dp(6))','business vertical balance')
s=rep(s,'        addView(businessIconBubble(iconRes),size(dp(52),dp(52)))','        addView(businessIconBubble(iconRes),size(dp(48),dp(48)))','business icon compact')
s=rep(s,'addView(a,LinearLayout.LayoutParams(0,dp(122),1f)','addView(a,LinearLayout.LayoutParams(0,dp(112),1f)','business row a compact')
s=rep(s,'addView(b,LinearLayout.LayoutParams(0,dp(122),1f)','addView(b,LinearLayout.LayoutParams(0,dp(112),1f)','business row b compact')

# Edit permission: replace HHmm knowledge-code with realtime current-password verification; no input hint beyond exact phrase.
old_staff='''    private fun staffEditor(existing:JSONObject?){
        if(!isAdmin())return
        if(existing!=null){val code=input("Mã xác nhận 4 số",true).apply{inputType=InputType.TYPE_CLASS_NUMBER;keyListener=DigitsKeyListener.getInstance("0123456789")};AlertDialog.Builder(this).setTitle("Xác nhận quyền sửa").setMessage("Nhập mã 4 số theo giờ Việt Nam hiện tại (HHmm). Ví dụ 07:42 → 0742.").setView(code).setNegativeButton("Hủy",null).setPositiveButton("TIẾP TỤC"){_,_->val expected=java.time.LocalTime.now(ZoneId.of("Asia/Ho_Chi_Minh")).format(DateTimeFormatter.ofPattern("HHmm"));if(code.text.toString()!=expected){showError("Mã xác nhận không đúng.")}else staffEditorUnlocked(existing)}.show();return}
        staffEditorUnlocked(null)
    }
'''
new_staff='''    private fun staffEditor(existing:JSONObject?){
        if(!isAdmin())return
        if(existing!=null){verifyEditPassword{staffEditorUnlocked(existing)};return}
        staffEditorUnlocked(null)
    }

    private fun verifyEditPassword(after:()->Unit){
        val pw=input("Nhập mật khẩu thực tế",true)
        val dialog=AlertDialog.Builder(this).setTitle("Xác nhận quyền sửa").setMessage("Nhập mật khẩu thực tế").setView(pw).setNegativeButton("Hủy",null).setPositiveButton("XÁC NHẬN",null).create()
        dialog.setOnShowListener{val btn=dialog.getButton(AlertDialog.BUTTON_POSITIVE);btn.setOnClickListener{val value=pw.text.toString();if(value.isBlank()){showError("Nhập mật khẩu thực tế");return@setOnClickListener};btn.isEnabled=false;api.login(login,value){r->runOnUiThread{btn.isEnabled=true;if(!r.ok){showError("Không thể xác thực");return@runOnUiThread};dialog.dismiss();after()}}}}
        dialog.show();pw.requestFocus()
    }
'''
s=rep(s,old_staff,new_staff,'edit password verification')

# Provider label must never claim Google merely because Cloudflare was locally disabled.
s=rep(s,'        if(ServiceFaultInjection.cloudflareDisabled(this)){return if(!ServiceFaultInjection.googleDisabled(this))"Google Drive" else "OFFLINE"}','        if(ServiceFaultInjection.cloudflareDisabled(this))return "Service OFFLINE (test)"','provider test truth')
write(p,s)

print('BETA62_POST_PATCH_APPLIED')
