#!/usr/bin/env python3
from pathlib import Path
import re

p=Path(__file__).with_name('beta122_apply_effective_role_pda_source_ui.py')
src=p.read_text(encoding='utf-8')
replacement='''# Direct routes must fail closed for USER, not only bottom-navigation taps.\nold_direct='            "HISTORY"->historyScreen()\\n            "SYNC"->syncScreen()'\nnew_direct='            "HISTORY"->if(isAdmin())historyScreen() else {module="BUSINESS";businessHome()}\\n            "SYNC"->syncScreen()'\ncount=s.count(old_direct)\nif count!=2:\n    raise SystemExit(f'direct history routes: expected 2 occurrences, got {count}')\ns=s.replace(old_direct,new_direct,2)\n\n# Rebuild bottom navigation'''
patched,n=re.subn(r'# Direct route must fail closed for USER, not only bottom-navigation taps\..*?# Rebuild bottom navigation',replacement,src,count=1,flags=re.S)
if n!=1:
    raise SystemExit(f'patcher r2 transform expected 1 got {n}')
ns={'__file__':str(p),'__name__':'__main__'}
exec(compile(patched,str(p),'exec'),ns,ns)
