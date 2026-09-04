#!/usr/bin/env python3
from pathlib import Path
p=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
s=p.read_text(encoding='utf-8')
old='body.addView(OldSessionWarningFeature.build(this,api){raw->openHistoricalSession(raw)},matchWrap())'
new='body.addView(OldSessionWarningFeature.build(this,api,role,{label,after->verifyTimePasswordOnly(label,after)}){raw->openHistoricalSession(raw)},matchWrap())'
if s.count(old)!=1:
    raise SystemExit(f'legacy old-session call count={s.count(old)}')
s=s.replace(old,new,1)
if 'OldSessionWarningFeature.build(this,api){' in s:
    raise SystemExit('legacy OldSessionWarningFeature call remains')
p.write_text(s,encoding='utf-8')
print('BETA118_COMPILE_REPAIR_APPLIED')
