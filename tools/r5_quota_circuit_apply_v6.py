#!/usr/bin/env python3
from pathlib import Path

exec(compile(Path('tools/r5_quota_circuit_apply_v5.py').read_text(encoding='utf-8'),'r5_quota_circuit_apply_v5','exec'),{'__name__':'__main__'})

p=Path('service/src/bootstrap.ts')
t=p.read_text(encoding='utf-8')
old='import { isAvailableLabel, nowIso, parseVisibleDate, sha256Hex, visibleToIsoTimestamp, workChoice, fold } from "./util";'
new=old+'\nimport { requireSheetsCall } from "./quota_budget";'
if old not in t: raise SystemExit('BOOTSTRAP_LEGACY_IMPORT_ANCHOR_MISSING')
t=t.replace(old,new,1)
old='''  const t=await token(env),id=env.GOOGLE_SOURCE_SHEET_ID;
  const metaR=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}?fields=properties.title,sheets.properties.title`,{headers:auth(t)});'''
new='''  const t=await token(env),id=env.GOOGLE_SOURCE_SHEET_ID;
  await requireSheetsCall(env.DB,"READ");
  const metaR=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}?fields=properties.title,sheets.properties.title`,{headers:auth(t)});'''
if old not in t: raise SystemExit('BOOTSTRAP_LEGACY_META_ANCHOR_MISSING')
t=t.replace(old,new,1)
old='''  const params=EXPECTED.map(x=>`ranges=${encodeURIComponent(`${q(x.name)}!A:AZ`)}`).join("&");
  const valuesR=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}/values:batchGet?majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE&${params}`,{headers:auth(t)});'''
new='''  const params=EXPECTED.map(x=>`ranges=${encodeURIComponent(`${q(x.name)}!A:AZ`)}`).join("&");
  await requireSheetsCall(env.DB,"READ");
  const valuesR=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}/values:batchGet?majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE&${params}`,{headers:auth(t)});'''
if old not in t: raise SystemExit('BOOTSTRAP_LEGACY_VALUES_ANCHOR_MISSING')
t=t.replace(old,new,1)
p.write_text(t,encoding='utf-8')
print('R5_QUOTA_CIRCUIT_APPLY_V6_PASS')
