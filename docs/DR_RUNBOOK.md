# DR RUNBOOK — APK PICK PACK 1291

Status: IMPLEMENTED_PENDING_FULL_TECHNICAL_GATE
All commands/actions must use current runtime discovery/config; do not hardcode a historic LIVE endpoint.

## 1. Normal
Expected writer: SERVICE_PRIMARY. Verify /health authority, generation, D1 binding, replication pending, and Google discovery before production write.

## 2. Short Service outage
- Do not transfer authority.
- App keeps SQLite outbox.
- Capture same canonical envelope to Emergency Ledger when Google is available.
- CAPTURED is provisional.
- On Service recovery replay same IDs; finalize Google only after canonical result.
- If Service + Google are down, keep local durable state and show non-success/provisional status.

## 3. LAN activation after >5 min
- Start outage-scoped discovery.
- Prefer SUPERADMIN candidate; if none online, eligible ADMIN may acquire.
- Google-accessible path uses LAN AUTHORITY FENCE lease.
- Google-unavailable path requires fixed-voter majority; one vote per generation.
- Master must have a connected designated backup before accepting/ACKing LAN writes.
- Client event: client -> Master durable store -> backup durable replica -> ACK.
- Backup takeover only after lease expiry/master-missed threshold or safe handover.
- Returning old Master follows current generation; it does not seize authority.

## 4. LAN failback
- Mark RECOVERING.
- Stop new unsafe authority promotion.
- Replay LAN replicas/outbox to Service canonical endpoints in event/dependency order.
- CONFIRMED/DUPLICATE finalize; REVIEW_REQUIRED/REJECTED remain auditable.
- Verify pending=0 and canonical checkpoint/readback.
- Release Google LAN lease, stop LAN FGS/discovery, return NORMAL.

## 5. D1 capacity
At >=80% prepare next generation if Free quota permits.
At >=85% or forecast trigger, run only the controlled cutover path after:
1. current authority/readback;
2. pending outbox drain/checkpoint;
3. portable backup VERIFIED;
4. next generation READY;
5. exact-source config prepared.
Cutover must fence writes, copy/verify, update epoch/generation, deploy exact source against next DB, verify health/readback, mark old generation READ_ONLY_HISTORY. On any failure restore previous DB + SERVICE_PRIMARY before reopening.

Two consecutive rollover rehearsals on temporary D1 databases must PASS before enabling production cutover.

## 6. Cloud DR
Preferred cloud DR chain per OWNER scope:
1. Render + Turso;
2. if Render unavailable, Deno + same portable Turso contract.
Both remain PASSIVE until controlled activation.
Activation prerequisites: provider Free-plan preflight, current canonical backup/checkpoint, fencing, DR datastore checksum/count match, canonical core contract test, new authority generation.
Failback: fence DR writer, replay after checkpoint into Cloudflare, compare count/hash/idempotency/authority, then activate Cloudflare and set DR PASSIVE. Never run both writers.

## 7. Google failure
If Google fails while Service/D1 is healthy: continue canonical Service; retain Google replication outbox.
If both Google and Service fail: local durable only / LAN if safe quorum is available; no fake success.

## 8. Portable restore
Run tools/portable_backup_verify.sh. PASS only if empty restore, table counts, event checksum, authority checkpoint and representative read all match. Do not call a replica a backup.

## 9. Release
Android source change requires a new Beta. Pre-OTA order:
candidate/sign -> service + infra/DR + stable invariants -> visual 320x568/360x640/480x800 + human -> PDA functional exact APK -> release lock.
Then GitHub Release exact bytes -> Beta manifest -> OTA install/readback -> finalize. Google Drive APK is forbidden. Stable/main/signer unchanged.

## 10. Recovery evidence
Every drill records source SHA, run/job/artifact, authority epoch/generation, counts/checksums, provider state, result and cleanup. Failed temporary test resources must be removed.
