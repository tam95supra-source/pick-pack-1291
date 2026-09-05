#!/usr/bin/env python3
from pathlib import Path

s=Path('service/src/replication.ts').read_text(encoding='utf-8')
required=[
    "WHERE status='INFLIGHT' AND claim_token=?1 ORDER BY outbox_id",
    'claimed=owned.results??[]',
    'if(!claimed.length)',
    'const assertOwnership=async()=>',
    'REPLICATION_CLAIM_LOST:',
    "UPDATE sheet_replication_outbox SET claimed_at=?1 WHERE status='INFLIGHT' AND claim_token=?2",
    'const ids=claimed.map(x=>x.event_id)',
    'REPLICATION_EVENT_SET_MISMATCH',
    "WHERE outbox_id=?3 AND status='INFLIGHT' AND claim_token=?4",
    'REPLICATION_ACK_FENCE_FAILED:',
    "WHERE outbox_id=?3 AND status='INFLIGHT' AND claim_token=?4",
    "WHERE status='INFLIGHT' AND claim_token=?3",
    'processed:claimed.length',
]
for x in required:
    assert x in s,x
# The old unfenced success/retry writes must be gone from replicatePending.
assert "WHERE outbox_id=?3\").bind(doneAt,checkpoint,x.outbox_id)" not in s
assert "WHERE outbox_id=?3\").bind(retryAt,message.slice(0,1000),x.outbox_id)" not in s
# Stale recovery remains bounded and does not delete records.
assert "Date.now()-15*60*1000" in s
assert "STALE_INFLIGHT_RECOVERED" in s
assert "DELETE FROM sheet_replication_outbox" not in s
print('BETA123_REPLICATION_FENCING_CONTRACT_PASS')
