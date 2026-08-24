#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
v5=ROOT/'tools/apply_beta69_owner_six_fixes_v5.py'
exec(compile(v5.read_text(),str(v5),'exec'),{'__file__':str(v5),'__name__':'__main__'})
ops_path=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'
ops=ops_path.read_text()
old='''        val display=api.networkStatus()\n        networkStatusText?.text=display'''
new='''        val net=runCatching{DeviceNetworkStatus.snapshot(this)}.getOrNull()\n        networkStatusText?.text=when{\n            net==null->"Đang kiểm tra"\n            !net.hasInternet->"Không Internet"\n            else->transportViHeader(net.transport)\n        }'''
if old in ops:
    ops=ops.replace(old,new,1)
elif new not in ops:
    raise SystemExit('Beta69 compact network helper anchor missing')
ops_path.write_text(ops)
assert 'api.networkStatus()' not in ops
assert 'transportViHeader(net.transport)' in ops
print('BETA69_OWNER_SIX_FIXES_V6_PASS')
