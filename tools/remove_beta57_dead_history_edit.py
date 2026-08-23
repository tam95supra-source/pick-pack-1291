from pathlib import Path

p = Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
s = p.read_text()
start = s.find('\n    private fun historyEditDialog(')
if start >= 0:
    end = s.find('\n\n    // S51B_BETA45_COMPILE_GUARD', start)
    if end < 0:
        raise SystemExit('historyEditDialog end anchor missing')
    s = s[:start] + s[end:]
if 'historyEditDialog(' in s:
    raise SystemExit('historyEditDialog still present')
p.write_text(s)
print('PASS - dead History mutation code removed')
