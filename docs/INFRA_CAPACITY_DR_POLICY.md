# INFRA CAPACITY + DR POLICY — APK PICK PACK 1291

OWNER: Nguyễn Văn Tâm
Status: IMPLEMENTED_PENDING_FULL_TECHNICAL_GATE
Canonical authority: runtime authority record; currently SERVICE_PRIMARY / PRODUCTION until a fenced transition is verified.

## Invariants
- Exactly one official writer. Timeout/5xx does not transfer authority.
- Canonical business rules live in Service core and are reused by compatible adapters; provider-specific state cannot become a business rule.
- Every mutation is idempotent and uses the canonical envelope: event/idempotency/schema/actor-role/device/app/business-date/time/sequence/dependency/session/epoch/generation/checksum/sanitized payload.
- Password/token/secret/signer/API credential material is forbidden from event ledger, Google emergency ledger, logs and portable backup metadata.
- Local durable outbox is written before network. Google CAPTURED is provisional only.
- Local events are not deleted merely because Google captured them.
- Google is ledger-first/projection-second and is not the primary business engine while SERVICE_PRIMARY is active.
- No blind dual-write. Fencing + checkpoint + idempotent replay are mandatory.
- No Supabase. APK distribution/rollback is GitHub Release only; Google Drive APK is forbidden.

## D1 capacity
Runtime config keys:
- WARN_DB_PERCENT=70
- PREPARE_NEXT_DB_PERCENT=80
- CUTOVER_DB_PERCENT=85
- OWNER_TOTAL_QUOTA_WARN_PERCENT=80
- RETENTION_DAYS in [45,365]
- provider quotas loaded from config/provider_free_limits.json and freshness-gated.

Generation registry permits exactly one ACTIVE_WRITE generation. Older generations become READ_ONLY_HISTORY. PREPARED generations are created only when Free quota/count guards allow it.

At PREPARE threshold: create next generation, apply schema, verify readiness; do not cut over.
At CUTOVER/forecast threshold: short writer fence, drain/checkpoint, verified portable backup, copy/verify required state, bump service_generation/authority_epoch, switch exact DB binding, readback, old generation read-only. Failed cutover must restore old writer before returning failure.

Retention may remove an operational business date only when a VERIFIED backup covers it and there is no active/open session or pending replication event for that date.

## Backup
Replica/retention/sharding is not backup. Portable backup PASS requires:
- D1 SQL export;
- restore into empty SQLite-compatible database;
- table row counts;
- canonical event checksum;
- authority checkpoint compare;
- representative read;
- immutable manifest and VERIFIED registration.
Production purge is forbidden without a covering VERIFIED manifest.

## Short Service outage
<5 minutes:
1. retain durable local event;
2. retry Service by same event_id;
3. on timeout/5xx/unreachable/quota, capture same sanitized envelope in Google Emergency Ledger if available;
4. UI remains provisional;
5. canonical Service replay finalizes APPLIED/DUPLICATE/REVIEW_REQUIRED/REJECTED.

Emergency Ledger is monthly-partitioned with a global idempotency index. A partition may be retired only when every indexed event is canonical-final and the partition is older than retention guard.

## Long Service outage / LAN
After continuous outage >=5 minutes, user warning exposes LAN activation.
Authority order:
- online SUPERADMIN may acquire;
- otherwise first eligible ADMIN may acquire;
- technical BACKUP may take over only from its designated Master under lease/quorum rules and never inherits ADMIN/SUPERADMIN business permission.

LAN contract:
- one Master + one backup;
- WebSocket/delta, mDNS only during outage/LAN discovery; no continuous normal polling;
- Master durably persists before replication and does not ACK client until backup replica ACK;
- generation/lan_epoch/lease fencing;
- Master reappearance never automatically steals authority;
- safe logout requires handover when Master;
- Service recovery enters RECOVERING, replays to canonical Service, then releases LAN.

## Cloud DR
Provider adapter must reuse canonical Service core. Turso/libSQL is the storage adapter. Render and Deno are passive/fenced unless DR_WRITER_MODE=ACTIVE_WRITE after controlled activation.
DR provider change must preserve event/idempotency/schema/authority metadata. Free-plan guard is mandatory.

## Owner notification
Do not alert merely because one D1 approaches its per-DB limit when safe rollover is available.
Alert OWNER only for total Free quota forecast insufficiency, provider/permission failure that prevents automatic protection, destructive/protected action, or newly required cost.
