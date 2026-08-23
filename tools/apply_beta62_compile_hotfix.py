from pathlib import Path

p=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
s=p.read_text(encoding='utf-8')
old='        find.setOnClickListener{hideSoftKeyboard(serialField);refreshList(serialField.text.toString())};bindScannerEnter(serialField){find.performClick()}\n'
new='        bindScannerEnter(serialField){hideSoftKeyboard(serialField);refreshList(serialField.text.toString())}\n'
count=s.count(old)
if count!=1:
    raise SystemExit(f'PDA stale find binding: expected 1 occurrence, got {count}')
s=s.replace(old,new,1)
if 'find.performClick()' in s:
    raise SystemExit('PDA stale find binding still present')
p.write_text(s,encoding='utf-8')
print('BETA62_COMPILE_HOTFIX_APPLIED')
