#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
scope=json.loads((ROOT/'ops/OWNER_SCOPE_CURRENT.json').read_text(encoding='utf-8'))
current=(ROOT/'CURRENT_STATE.md').read_text(encoding='utf-8')
handoff_path=ROOT/'docs/handovers/HANDOVER_CURRENT.md'
handoff=handoff_path.read_text(encoding='utf-8')
finalizer=(ROOT/'tools/finalize_beta83.sh').read_text(encoding='utf-8')

assert '`python3 tools/owner_scope_guard.py --bootstrap`' not in finalizer
assert '`$OWNER_SCOPE_FILE`' not in finalizer
assert 'OWNER_LOCKED_NUMBERS=' in finalizer
assert 'select(.state=="LOCKED_REQUIREMENT_PENDING_FIX")' in finalizer
assert 'FINALIZER_BLOCKED_LOCKED_REQUIREMENTS_${OWNER_LOCKED_NUMBERS}' in finalizer
assert 'OWNER_PENDING_NUMBERS=' in finalizer
assert 'select(.state=="TECHNICAL_PASS_AWAITING_OWNER")' in finalizer
assert 'WAIT_FOR_OWNER_ACCEPTANCE_REQUIREMENTS_${OWNER_PENDING_NUMBERS}' in finalizer
assert 'refs/heads/beta/current' in finalizer
assert 'FINALIZER_CURRENT_SYNC_PASS' in finalizer
assert 'FINALIZER_CURRENT_SYNC_SKIP_NEWER_CURRENT' in finalizer
assert 'FINALIZER_CURRENT_SYNC_FAIL_NON_FF' in finalizer
assert 'git merge-base --is-ancestor' in finalizer
assert '--force' not in finalizer

sid=scope['scope_id']; rev=scope['revision']; sem=scope['semantics_sha256']; sha=scope['scope_sha256']; ledger=scope['ledger_head_event_sha256']; count=len(scope['requirements'])
locked=[str(x['checklist_number']) for x in scope['requirements'] if x.get('state')=='LOCKED_REQUIREMENT_PENDING_FIX']
pending=[str(x['checklist_number']) for x in scope['requirements'] if x.get('state')=='TECHNICAL_PASS_AWAITING_OWNER']
m=re.search(r'(?m)^- next_action:\s*(.+)$',current); actual_next=m.group(1).strip() if m else ''
if scope.get('scope_status')=='OWNER_ACCEPTANCE_COMPLETE':
    assert not locked and not pending, 'accepted scope still has pending requirements'
    expected_next='WAIT_FOR_OWNER_NEW_SCOPE'
elif locked:
    assert actual_next and not actual_next.startswith('WAIT_FOR_OWNER_ACCEPTANCE_REQUIREMENTS_'), 'locked implementation scope cannot wait for OWNER acceptance'
    expected_next=actual_next
elif pending:
    expected_next='WAIT_FOR_OWNER_ACCEPTANCE_REQUIREMENTS_'+'_'.join(pending)
else:
    expected_next='OWNER_ACCEPTANCE_COMPLETE'

for text,label in ((current,'CURRENT_STATE'),(handoff,'HANDOVER_CURRENT')):
    assert f'- owner_scope_id: {sid}' in text,label
    assert f'- owner_scope_revision: {rev}' in text,label
    assert f'- owner_scope_semantics_sha256: {sem}' in text,label
    assert f'- owner_scope_sha256: {sha}' in text,label
    assert f'- owner_command_ledger_head: {ledger}' in text,label
assert f'- next_action: {expected_next}' in current
assert re.search(rf'(?m)^## NEXT_ACTION\n{re.escape(expected_next)}$',handoff)
assert 'Phiên tiếp quản phải chạy python3 tools/owner_scope_guard.py --bootstrap rồi đọc requirement từ ops/OWNER_SCOPE_CURRENT.json.' in handoff
assert f'Canonical OWNER checklist: ops/OWNER_SCOPE_CURRENT.json, revision {rev}, SHA256 {sha}, {count} requirement(s).' in handoff
assert '## Checklist OWNER nghiệm thu' not in handoff
m=re.search(r'(?m)^- archive_file: (.+)$',handoff); assert m,'archive pointer missing'
archive=ROOT/m.group(1).strip(); assert archive.exists(),archive
archive_text=archive.read_text(encoding='utf-8')
assert f'- owner_scope_sha256: {sha}' in archive_text
assert re.search(rf'(?m)^## NEXT_ACTION\n{re.escape(expected_next)}$',archive_text)
print(json.dumps({'status':'PASS','scope_id':sid,'revision':rev,'scope_sha256':sha,'locked':[int(x) for x in locked],'pending_owner_checklist':[int(x) for x in pending],'next_action':expected_next},ensure_ascii=False))
