#!/usr/bin/env python3
from pathlib import Path

exec(compile(Path('tools/r5_quota_circuit_apply_v4.py').read_text(encoding='utf-8'),'r5_quota_circuit_apply_v4','exec'),{'__name__':'__main__'})

p=Path('service/src/dr.ts')
t=p.read_text(encoding='utf-8')
old='import { isStableEnvironment, stableSheetBridge } from "./stable_sheet_bridge";'
new=old+'\nimport { requireSheetsCall } from "./quota_budget";'
if old not in t: raise SystemExit('DR_IMPORT_ANCHOR_MISSING')
t=t.replace(old,new,1)
old='''  const id=env.GOOGLE_STAGING_SHEET_ID;
  const clear=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}/values/${encodeURIComponent(a1(name,"A:AZ"))}:clear`,{method:"POST"'''
new='''  const id=env.GOOGLE_STAGING_SHEET_ID;
  await requireSheetsCall(env.DB,"WRITE");
  const clear=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}/values/${encodeURIComponent(a1(name,"A:AZ"))}:clear`,{method:"POST"'''
if old not in t: raise SystemExit('DR_CLEAR_ANCHOR_MISSING')
t=t.replace(old,new,1)
old='''for(let i=0;i<all.length;i+=500){const chunk=all.slice(i,i+500),start=i+1,range=a1(name,`A${start}`);const r=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}/values/${encodeURIComponent(range)}?valueInputOption=RAW`,{method:"PUT"'''
new='''for(let i=0;i<all.length;i+=500){const chunk=all.slice(i,i+500),start=i+1,range=a1(name,`A${start}`);await requireSheetsCall(env.DB,"WRITE");const r=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}/values/${encodeURIComponent(range)}?valueInputOption=RAW`,{method:"PUT"'''
if old not in t: raise SystemExit('DR_WRITE_ANCHOR_MISSING')
t=t.replace(old,new,1)
p.write_text(t,encoding='utf-8')
print('R5_QUOTA_CIRCUIT_APPLY_V5_PASS')
