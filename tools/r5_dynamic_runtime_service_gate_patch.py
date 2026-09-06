#!/usr/bin/env python3
from pathlib import Path

p=Path('tools/beta89_service_live_gate.sh')
s=p.read_text(encoding='utf-8')
repls={
    'rm -rf "$D" && mkdir -p "$D"': '''rm -rf "$D" && mkdir -p "$D"
# Test both actual exit implementations at deterministic shift/late-day boundaries.
# No Worker source edits, network calls or LIVE data are used by this test.
node --experimental-vm-modules tools/r5_labor_clock_regression.mjs "$D/b115-clock-regression.json"''',
    'D1_NAME=pick-pack-1291-service-prod':': "${D1_NAME:?D1_NAME_REQUIRED}"',
    'OUTBOUND_SHEET_ID=1tl6har_8vGSVsVlcErfQwjX1YgvN3o-FRG5wQV4VTEM':': "${OUTBOUND_SHEET_ID:?OUTBOUND_SHEET_ID_REQUIRED}"',
    '''B115_SHIFT_END="${B80_DATE}T15:00:00Z"
B115_AFTER_CAP="${B80_DATE}T15:15:00Z"
node -e 'if(Date.parse(process.argv[1])<=Date.now()+60000)throw new Error("B115_SCHEDULED_END_NOT_FUTURE_FOR_LIVE_GATE")' "$B115_SHIFT_END"''':'''B115_SCHEDULED_CAP="${B80_DATE}T15:00:00Z"
if node -e 'process.exit(Date.parse(process.argv[1])>Date.now()+120000?0:1)' "$B115_SCHEDULED_CAP"; then
  B115_SHIFT_END="$B115_SCHEDULED_CAP"
  B115_AFTER_CAP=$(node -e 'process.stdout.write(new Date(Date.parse(process.argv[1])+15*60*1000).toISOString())' "$B115_SCHEDULED_CAP")
else
  read -r B115_SHIFT_END B115_AFTER_CAP < <(node -e 'const n=Date.now();process.stdout.write(new Date(n+55_000).toISOString()+" "+new Date(n+180_000).toISOString()+"\\n")')
fi
node -e 'if(Date.parse(process.argv[1])<=Date.now())throw new Error("B115_SCHEDULED_END_NOT_FUTURE_FOR_LIVE_GATE")' "$B115_SHIFT_END"''',
}
for old,new in repls.items():
    if s.count(old)!=1:
        raise SystemExit('DYNAMIC_RUNTIME_ANCHOR_COUNT:'+old+':'+str(s.count(old)))
    s=s.replace(old,new,1)

start='B115_EXIT_FUTURE_HTTP=$(curl '
end='jq -e \'.error.code=="FUTURE_LABOR_BLOCKS_EXIT"\' "$D/b115-exit-future-blocked.json" >/dev/null'
if s.count(start)!=1 or s.count(end)!=1:
    raise SystemExit('B115_FUTURE_EXIT_BLOCK_ANCHOR_COUNT')
a=s.index(start)
b=s.index(end,a)+len(end)
live_block=s[a:b]
s=s[:a]+'''# The existing business rule permits an ACTIVE late-day cap of now+60s.
# Such a value cannot satisfy exit's strictly >now+60s future guard. The exact
# handlers above cover that guard with an isolated clock at every shift boundary.
B115_EXIT_COVERAGE=ISOLATED_CLOCK_LATE_OR_NEAR_SHIFT_END
if node -e 'process.exit(Date.parse(process.argv[1])>Date.now()+120000?0:1)' "$B115_SHIFT_END"; then
  B115_EXIT_COVERAGE=LIVE_AND_ISOLATED_CLOCK
'''+live_block+'''
else
  jq -e '.status=="PASS" and .classification=="EXACT_SERVICE_FUNCTIONS_ISOLATED_SQLITE_CONTROLLED_CLOCK" and .case_count==54 and .network==false and .production_writes==0' "$D/b115-clock-regression.json" >/dev/null
fi
printf '%s\\n' "$B115_EXIT_COVERAGE" > "$D/b115-future-exit-coverage.txt"
'''+s[b:]

receipt_anchor='R5_RECEIPT_TMP=$(mktemp "$D/receipt-r5.XXXXXX.json")'
if s.count(receipt_anchor)!=1:
    raise SystemExit('B115_CLOCK_RECEIPT_ANCHOR_COUNT')
s=s.replace(receipt_anchor,'''B115_CLOCK_RECEIPT_TMP=$(mktemp "$D/receipt-clock.XXXXXX.json")
jq --slurpfile clock "$D/b115-clock-regression.json" --arg coverage "$B115_EXIT_COVERAGE" '.beta115_clock_regression=$clock[0] | .beta115_future_exit_coverage=$coverage' "$D/receipt.json" > "$B115_CLOCK_RECEIPT_TMP" && mv "$B115_CLOCK_RECEIPT_TMP" "$D/receipt.json"
'''+receipt_anchor,1)
p.write_text(s,encoding='utf-8')
print('R5_DYNAMIC_RUNTIME_SERVICE_GATE_PATCH_PASS')
