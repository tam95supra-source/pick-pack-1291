#!/usr/bin/env python3
from pathlib import Path

exec(compile(Path('tools/r5_quota_circuit_apply_v6.py').read_text(encoding='utf-8'),'r5_quota_circuit_apply_v6','exec'),{'__name__':'__main__'})

p=Path('service/src/beta44_owner.ts')
t=p.read_text(encoding='utf-8')
old='import { isStableEnvironment, stableSheetBridge } from "./stable_sheet_bridge";'
new=old+'\nimport { requireSheetsCall } from "./quota_budget";'
if old not in t: raise SystemExit('BETA44_IMPORT_ANCHOR_MISSING')
t=t.replace(old,new,1)
old='''  const token=await googleAccessToken(env),range=`'Danh sách Admin'!A${row}:K${row}`,url=`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(env.GOOGLE_SOURCE_SHEET_ID)}/values/${encodeURIComponent(range)}:clear`;
  const r=await fetch(url,{method:"POST"'''
new='''  const token=await googleAccessToken(env),range=`'Danh sách Admin'!A${row}:K${row}`,url=`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(env.GOOGLE_SOURCE_SHEET_ID)}/values/${encodeURIComponent(range)}:clear`;
  await requireSheetsCall(env.DB,"WRITE");
  const r=await fetch(url,{method:"POST"'''
if old not in t: raise SystemExit('BETA44_CLEAR_ANCHOR_MISSING')
t=t.replace(old,new,1)
p.write_text(t,encoding='utf-8')
print('R5_QUOTA_CIRCUIT_APPLY_V7_PASS')
