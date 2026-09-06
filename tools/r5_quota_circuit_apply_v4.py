#!/usr/bin/env python3
from pathlib import Path

exec(compile(Path('tools/r5_quota_circuit_apply_v3.py').read_text(encoding='utf-8'),'r5_quota_circuit_apply_v3','exec'),{'__name__':'__main__'})

p=Path('service/src/beta47_history_audit.ts')
t=p.read_text(encoding='utf-8')
old='import { isStableEnvironment, stableSheetBridge } from "./stable_sheet_bridge";'
new=old+'\nimport { requireSheetsCall } from "./quota_budget";'
if old not in t: raise SystemExit('HISTORY_IMPORT_ANCHOR_MISSING')
t=t.replace(old,new,1)
old='''}const range=`${q("LỊCH SỬ NGHIỆP VỤ")}!K2:K`,r=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(env.GOOGLE_SOURCE_SHEET_ID)}/values/${encodeURIComponent(range)}?majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE`,{headers:{authorization:`Bearer ${t}`}});'''
new='''}await requireSheetsCall(env.DB,"READ");const range=`${q("LỊCH SỬ NGHIỆP VỤ")}!K2:K`,r=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(env.GOOGLE_SOURCE_SHEET_ID)}/values/${encodeURIComponent(range)}?majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE`,{headers:{authorization:`Bearer ${t}`}});'''
if old not in t: raise SystemExit('HISTORY_READ_ANCHOR_MISSING')
t=t.replace(old,new,1)
old='''}const range=`${q("LỊCH SỬ NGHIỆP VỤ")}!A:M`,r=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(env.GOOGLE_SOURCE_SHEET_ID)}/values/${encodeURIComponent(range)}:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS`,{method:"POST"'''
new='''}await requireSheetsCall(env.DB,"WRITE");const range=`${q("LỊCH SỬ NGHIỆP VỤ")}!A:M`,r=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(env.GOOGLE_SOURCE_SHEET_ID)}/values/${encodeURIComponent(range)}:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS`,{method:"POST"'''
if old not in t: raise SystemExit('HISTORY_WRITE_ANCHOR_MISSING')
t=t.replace(old,new,1)
p.write_text(t,encoding='utf-8')
print('R5_QUOTA_CIRCUIT_APPLY_V4_PASS')
