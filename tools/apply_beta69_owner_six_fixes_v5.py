#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
v4=ROOT/'tools/apply_beta69_owner_six_fixes_v4.py'
src=v4.read_text()
start=src.find("section6=r'''# 6) Timeline correctness for the active Beta65 session model.")
close=src.find("\n'''\nsrc=src[:s6]+section6",start)
if start<0 or close<0:
    raise SystemExit('Beta69 v4 section6 delimiter anchor missing')
src=src[:start]+src[start:].replace("section6=r'''# 6) Timeline correctness for the active Beta65 session model.","section6=r\"\"\"# 6) Timeline correctness for the active Beta65 session model.",1)
# Recompute close after opening delimiter replacement and convert only section6 closing delimiter.
close=src.find("\n'''\nsrc=src[:s6]+section6",start)
if close<0: raise SystemExit('Beta69 v4 section6 closing delimiter missing')
src=src[:close]+src[close:].replace("\n'''\nsrc=src[:s6]+section6","\n\"\"\"\nsrc=src[:s6]+section6",1)
ns={'__file__':str(v4),'__name__':'__main__'}
exec(compile(src,str(v4),'exec'),ns)
print('BETA69_OWNER_SIX_FIXES_V5_PASS')
