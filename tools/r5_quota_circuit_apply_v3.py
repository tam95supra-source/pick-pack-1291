#!/usr/bin/env python3
from pathlib import Path

# Apply reviewed v2 circuit patch first.
exec(compile(Path('tools/r5_quota_circuit_apply_v2.py').read_text(encoding='utf-8'),'r5_quota_circuit_apply_v2','exec'),{'__name__':'__main__'})

p=Path('service/src/bootstrap_resumable.ts')
t=p.read_text(encoding='utf-8')
old='import { isAvailableLabel, nowIso, parseVisibleDate, sha256Hex, visibleToIsoTimestamp, workChoice, fold } from "./util";'
new=old+'\nimport { requireSheetsCall } from "./quota_budget";'
if old not in t: raise SystemExit('BOOTSTRAP_IMPORT_ANCHOR_MISSING')
t=t.replace(old,new,1)
old='''  const t=await googleToken(env),id=env.GOOGLE_SOURCE_SHEET_ID;
  const r=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}?fields=properties.title,sheets.properties.title`,{headers:auth(t)});'''
new='''  const t=await googleToken(env),id=env.GOOGLE_SOURCE_SHEET_ID;
  await requireSheetsCall(env.DB,"READ");
  const r=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}?fields=properties.title,sheets.properties.title`,{headers:auth(t)});'''
if old not in t: raise SystemExit('BOOTSTRAP_META_ANCHOR_MISSING')
t=t.replace(old,new,1)
old='''  const range=encodeURIComponent(`${q(spec.name)}!A${start}:AZ${end}`);
  const r=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}/values/${range}?majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE`,{headers:auth(t)});'''
new='''  const range=encodeURIComponent(`${q(spec.name)}!A${start}:AZ${end}`);
  await requireSheetsCall(db,"READ");
  const r=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}/values/${range}?majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE`,{headers:auth(t)});'''
if old not in t: raise SystemExit('BOOTSTRAP_VALUES_ANCHOR_MISSING')
t=t.replace(old,new,1)
p.write_text(t,encoding='utf-8')
print('R5_QUOTA_CIRCUIT_APPLY_V3_PASS')
