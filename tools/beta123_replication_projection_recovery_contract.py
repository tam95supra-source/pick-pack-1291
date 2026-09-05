from pathlib import Path

s = Path('service/src/replication.ts').read_text(encoding='utf-8')
checks = {
    'bounded_default_10': 'replicatePending(db:D1Database,env:Env,limit=10)' in s,
    'bounded_hard_cap_10': 'Math.min(limit,10)' in s,
    'attendance_ra_readback': 'verifyIndex.raEvents.has(e.event_id)' in s,
    'attendance_history_readback': 'verifyIndex.historyEvents.has(e.event_id)' in s,
    'incomplete_blocks_ack': 'REPLICATION_OPERATIONAL_INCOMPLETE' in s,
    'ack_fenced_by_claim': "status='INFLIGHT' AND claim_token=?4" in s,
    'ownership_guard': 'REPLICATION_CLAIM_LOST' in s,
    'stale_recovery_not_synced': "SET status='RETRY',claim_token=NULL" in s,
}
failed = [k for k, v in checks.items() if not v]
if failed:
    raise SystemExit('BETA123_PROJECTION_RECOVERY_CONTRACT_FAIL:' + ','.join(failed))
order = [
    s.index('const operational=await replicateOperational'),
    s.index('const verifyIndex=await loadOperationalIndex'),
    s.index('REPLICATION_OPERATIONAL_INCOMPLETE'),
    s.index("SET status='SYNCED',claim_token=NULL", s.index('const operational=await replicateOperational')),
]
if order != sorted(order):
    raise SystemExit('BETA123_PROJECTION_RECOVERY_ORDER_FAIL')
print('BETA123_PROJECTION_RECOVERY_CONTRACT_PASS')
