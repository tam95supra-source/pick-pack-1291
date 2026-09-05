#!/usr/bin/env python3
from pathlib import Path

p=Path(__file__).with_name("beta122_apply_effective_role_pda_source_ui.py")
src=p.read_text(encoding="utf-8")

# Canonical source has two direct HISTORY routes; guard both.
start=src.index("# Direct route must fail closed for USER, not only bottom-navigation taps.")
end=src.index("# Rebuild bottom navigation", start)
route_block=r'''# Direct routes must fail closed for USER, not only bottom-navigation taps.
old_direct='            "HISTORY"->historyScreen()\n            "SYNC"->syncScreen()'
new_direct='            "HISTORY"->if(isAdmin())historyScreen() else {module="BUSINESS";businessHome()}\n            "SYNC"->syncScreen()'
count=s.count(old_direct)
if count!=2:
    raise SystemExit(f'direct history routes: expected 2 occurrences, got {count}')
s=s.replace(old_direct,new_direct,2)

'''
src=src[:start]+route_block+src[end:]

# Canonical pdaSelectedPanel is immediately followed by naturalUserCompare.
pstart=src.index("panel_pat=re.compile")
pend=src.index("# Autocomplete labels show source alongside serial/status.", pstart)
panel_section=src[pstart:pend]
count=panel_section.count("private fun pdaInput")
if count!=2:
    raise SystemExit(f'PDA panel patcher boundary occurrences expected 2 got {count}')
panel_section=panel_section.replace("private fun pdaInput","private fun naturalUserCompare",2)
src=src[:pstart]+panel_section+src[pend:]

# A replacement string passed directly to re.sub interprets \\n again and produced
# physical newlines inside Kotlin quoted strings. Returning it from a function keeps
# the literal Kotlin \\n escape exactly as intended.
old="s,nsub=panel_pat.subn(panel_new,s,count=1)"
new="s,nsub=panel_pat.subn(lambda _m: panel_new,s,count=1)"
if src.count(old)!=1:
    raise SystemExit(f'panel subn form expected 1 got {src.count(old)}')
src=src.replace(old,new,1)

ns={"__file__":str(p),"__name__":"__main__"}
exec(compile(src,str(p),"exec"),ns,ns)
