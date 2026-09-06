#!/usr/bin/env python3
from pathlib import Path

p=Path('service/src/index.ts')
t=p.read_text(encoding='utf-8')
old='''  const d=await dayDeltaData(env.DB,e.business_date,Math.max(0,e.authority_seq-1),1),items=Array.isArray(d.items)?d.items as Record<string,unknown>:[],item=items.find(x=>String((x.event as Record<string,unknown>|undefined)?.event_id||"")===e.event_id)??items[0]??{};'''
new='''  const d=await dayDeltaData(env.DB,e.business_date,Math.max(0,e.authority_seq-1),1);
  const items=(Array.isArray(d.items)?d.items:[]) as Record<string,unknown>[];
  const item=items.find((x:Record<string,unknown>)=>String((x.event as Record<string,unknown>|undefined)?.event_id||"")===e.event_id)??items[0]??{};'''
if old not in t:
    raise SystemExit('R5_PHASE1B_GENERATED_CAST_ANCHOR_MISSING')
p.write_text(t.replace(old,new,1),encoding='utf-8')
print('R5_PHASE1B_GENERATED_CAST_FIX_PASS')
