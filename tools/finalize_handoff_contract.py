#!/usr/bin/env python3
from pathlib import Path
p=Path(__file__).with_name('finalize_beta83.sh').read_text(encoding='utf-8')
assert "OWNER_SCOPE=$(jq -r '.owner_scope" in p
assert "SERVICE_STATUS=$(jq -r '.service_gate_status" in p
assert "$(jq -r '.scope' \"$R\")" not in p
assert "$(jq -r '.service_gate' \"$R\")" not in p
assert 'test "$OWNER_SCOPE" != "null"' in p
assert 'test "$SERVICE_STATUS" != "null"' in p
assert "grep -c 'null'" in p
assert 'WAIT_FOR_OWNER_ACCEPTANCE_NUMBERED_CHECKLIST' in p
print('FINALIZE_HANDOFF_CANONICAL_METADATA_CONTRACT_PASS')
