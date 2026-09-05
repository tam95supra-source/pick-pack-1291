from pathlib import Path
p=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
s=p.read_text(encoding='utf-8')
old='''fun submit(){val v=mnv.text.toString().trim();if(v.isBlank()){TopNotice.show(this,"Nhập hoặc quét Mã nhân viên.",TopNotice.Kind.WARNING);return};if(busy)return;busy=true;hideSoftKeyboard(mnv);loadEmployee(v);mnv.postDelayed({busy=false},600)}'''
new='''fun submit(){val v=mnv.text.toString().trim();if(v.isBlank()){TopNotice.show(this,"Nhập hoặc quét Mã nhân viên.",TopNotice.Kind.WARNING);return};if(busy)return;busy=true;hideSoftKeyboard(mnv);preScanStaff.visibility=View.GONE;loadEmployee(v);mnv.postDelayed({busy=false},600)}'''
if 'preScanStaff.visibility=View.GONE' not in s:
    if old not in s: raise SystemExit('employeeScan submit anchor missing')
    s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('BETA123_QR_FIX_APPLIED')
