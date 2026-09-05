#!/usr/bin/env python3
from pathlib import Path
p=Path('tools/beta83_verify_matrix.sh')
s=p.read_text(encoding='utf-8')
old='''  set -e\n  test "$RC" = 0;grep -Fq 'INSTRUMENTATION_CODE: 0' "$OUT/$TAG-instrument.txt"\n  mkdir -p "$OUT/$TAG"\n  adb pull "/sdcard/Android/data/$PKG/files/beta83-visual/." "$OUT/$TAG/" >/dev/null\n'''
new='''  set -e\n  mkdir -p "$OUT/$TAG"\n  # Pull screenshots before asserting instrumentation success so a failed visual/navigation gate still has human evidence.\n  adb pull "/sdcard/Android/data/$PKG/files/beta83-visual/." "$OUT/$TAG/" >/dev/null 2>&1 || true\n  test "$RC" = 0;grep -Fq 'INSTRUMENTATION_CODE: 0' "$OUT/$TAG-instrument.txt"\n'''
if s.count(old)!=1: raise SystemExit(f'VERIFY_PULL_ANCHOR_COUNT={s.count(old)}')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('beta125_verify_pull_failure_evidence=PASS')
