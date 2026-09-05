#!/usr/bin/env python3
from pathlib import Path

p=Path(__file__).with_name("beta122_apply_effective_role_pda_source_ui.py")
src=p.read_text(encoding="utf-8")
start=src.index("# Direct route must fail closed for USER, not only bottom-navigation taps.")
end=src.index("# Rebuild bottom navigation", start)
new_block=r'''# Direct routes must fail closed for USER, not only bottom-navigation taps.
old_direct='            "HISTORY"->historyScreen()\n            "SYNC"->syncScreen()'
new_direct='            "HISTORY"->if(isAdmin())historyScreen() else {module="BUSINESS";businessHome()}\n            "SYNC"->syncScreen()'
count=s.count(old_direct)
if count!=2:
    raise SystemExit(f'direct history routes: expected 2 occurrences, got {count}')
s=s.replace(old_direct,new_direct,2)

'''
patched=src[:start]+new_block+src[end:]
ns={"__file__":str(p),"__name__":"__main__"}
exec(compile(patched,str(p),"exec"),ns,ns)
