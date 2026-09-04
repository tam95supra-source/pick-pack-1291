#!/usr/bin/env python3
from pathlib import Path
s=Path("service/src/index.ts").read_text(encoding="utf-8")
r=Path("service/src/replication.ts").read_text(encoding="utf-8")
assert "REPLICATION_RECOVERY_ENABLED" in s
assert "REPLICATION_RECOVERY_TOKEN_SHA256" in s
assert "x-replication-recovery-token" in s
assert "replicatePending(env.DB,env,ra?1:50)" in s
assert "replicatePending(env.DB,env,1)" in s
assert "Date.now()-5*60*1000" in r
assert "status='SYNCED'" in r
print("beta119_fenced_recovery_contract=PASS scheduled_batch=1 recovery_limit=1 stale=5m")
