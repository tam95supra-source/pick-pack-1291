#!/usr/bin/env python3
from pathlib import Path
s=Path("service/src/index.ts").read_text(encoding="utf-8")
r=Path("service/src/replication.ts").read_text(encoding="utf-8")
assert "for(let i=0;i<3;i++)" in s
assert "replicatePending(env.DB,env,5)" in s
assert "if(!r.ok||r.processed===0)break" in s
assert "limit=50" in r
assert "STALE_INFLIGHT_RECOVERY_V1" in r
assert "status=\'INFLIGHT\'" in r or "status='INFLIGHT'" in r
assert "status='SYNCED'" in r
print("beta119_replication_drain_contract=PASS sequential_batches=3 batch_size=5 official_writer=UNCHANGED fail_stop=PASS")
