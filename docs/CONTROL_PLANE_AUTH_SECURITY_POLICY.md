# CONTROL PLANE / AUTH / OWNER ACCEPTANCE SECURITY POLICY — PICK PACK 1291

OWNER: Nguyễn Văn Tâm
Status: OWNER scope locked 2026-09-04; implementation pending where stated.

## 1. Public Beta current state

1. `beta/current` is the default continuity branch and must identify the newest public LIVE Beta.
2. `CURRENT_STATE.md` and `ops/beta-ota-current.json` on `beta/current` must agree on version identity.
3. A successful `Beta release` PASS/LIVE is followed by `.github/workflows/beta-current-sync.yml`, which may only fast-forward `beta/current`; force-push is forbidden.
4. Monotonic fence: an older Beta may never overwrite a newer current Beta. Same-version divergent histories fail closed.
5. Readback after update must confirm `CURRENT_STATE.md`, `ops/beta-ota-current.json`, version and GitHub Release authority.
6. A new session must treat a mismatch between public LIVE/readback and `beta/current` as a control-plane bug and repair/reconcile it before using CURRENT as release authority.

## 2. OWNER checklist / acceptance state

Canonical machine-readable pointer: `ops/owner-acceptance-current.json`.

Rules:
- Every current scope has a monotonic `state_epoch`.
- Every OWNER checklist has `checklist_id` + monotonically increasing `revision`.
- Acceptance write must match the active release/scope/checklist revision exactly.
- Lower `state_epoch`, older Beta, or lower checklist revision is rejected; Beta116/117 cannot replace Beta118+ state.
- OWNER silence is never acceptance.
- Technical PASS creates checklist state; OWNER replies update item state; only Technical PASS + OWNER OK becomes `ACTIVE_PASS` in stable invariants.
- Historical receipts are append-only. `current` is only a pointer/projection to the newest valid state.
- Chat, memory and handoff text are navigation aids, not the canonical acceptance ledger.

## 3. SUPERADMIN session persistence

Root requirement: an app version update must not itself log SUPERADMIN out or invalidate the account password.

Implementation contract:
- Do not clear a valid auth token merely because the app process starts or the APK version changed.
- Restore persisted session/account first; server validation/revocation remains authoritative.
- Logout, explicit revoke, expired/invalid server session, uninstall/key loss, or security recovery may require login again.
- Regression must include in-place APK update with a valid SUPERADMIN session and prove the session remains usable without password reset.

## 4. SUPERADMIN login methods

### 4.1 Time-window method (no device binding)

OWNER requirement updated 2026-09-04: SUPERADMIN has exactly two credential methods; device trust/binding is not used.

- Method 1 accepts an input of 1..20 characters when the string contains at least one exact `HHmm` value in the server's current time window ±5 minutes. Arbitrary prefix/suffix characters are allowed.
- Validation is server-side using the configured Vietnam business timezone and must handle midnight wrap correctly. Client-side matching is only a routing hint, never authority.
- No device binding, device secret, trusted-device state or Android Keystore dependency is part of this method.
- Successful time-window login does not rotate or send the email OTP.
- Failed attempts are rate-limited server-side; the submitted time string must not be logged or persisted.
- Legacy/static SUPERADMIN password login is disabled so SUPERADMIN has exactly the two OWNER-approved methods.

Security note: current time is not secret. This method therefore provides materially less authentication secrecy than a device-bound credential. OWNER explicitly selected this tradeoff; public GitHub must still contain no actual password/OTP/token/secret values.

### 4.2 Email one-time password

- OTP is exactly 8 decimal digits generated with a cryptographically secure random source.
- OTP is single-use.
- On successful OTP login, atomically mark the used OTP consumed, generate the next OTP, store only its protected verifier, and send the new plaintext OTP to the configured SUPERADMIN recovery Gmail address.
- Login by time-window method does not rotate/send OTP.
- Manual resend/recovery rotates the previous unused OTP and invalidates it.
- Rate-limit failed OTP attempts and login attempts server-side.
- Plaintext OTP exists only transiently during generation/email delivery and is never persisted in repo, logs, receipts or artifacts.

Protected storage recommendation for an 8-digit OTP:
- store `HMAC-SHA256(server_pepper, otp || account || otp_generation_id)` or an equivalently protected verifier in the private runtime datastore;
- keep `server_pepper` only in the runtime secret store;
- never store a bare SHA hash of an 8-digit OTP in a public or exportable repository artifact.

## 5. Secrets and public GitHub

Repository is public. The following are forbidden in tracked files, Git history additions, Actions logs, uploaded artifacts, handoffs and receipts:
- plaintext account passwords;
- plaintext OTP values;
- password verifier/proof material sufficient for offline guessing;
- session/bearer tokens;
- Gmail OAuth refresh/client secrets;
- signing keys, keystores, private keys;
- Cloud/service administrative tokens or database credentials.

Allowed in repo:
- secret variable names;
- public identifiers/URLs that are intentionally non-secret;
- schemas, algorithms and security policy;
- hashes of release APK bytes and non-secret evidence.

Runtime secret placement:
- use the active provider's secret store / private script properties / equivalent private runtime secret facility;
- CI may reference secret names but must not print values;
- do not use a public GitHub file as runtime credential storage.

If a secret is ever committed to public GitHub, deletion in a later commit is insufficient. Treat it as compromised, rotate/revoke it, then remove it from active code/history exposure as appropriate.

## 6. Required regression gates

At minimum:
1. New public Beta PASS/LIVE automatically advances `beta/current` exactly once; older release cannot roll it back.
2. Same-version divergent current state fails closed.
3. New chat/session reading `beta/current` obtains latest public Beta identity.
4. OWNER checklist revision N+1 cannot be overwritten by N; older Beta acceptance cannot overwrite newer release state.
5. In-place APK update preserves valid SUPERADMIN session.
6. Arbitrary string length <=20 containing valid ±5-minute `HHmm` succeeds for active SUPERADMIN without device binding.
7. Time outside ±5 minutes fails, including midnight-boundary cases; inputs over 20 characters fail.
8. Legacy/static SUPERADMIN password login fails, proving exactly two SUPERADMIN methods remain.
9. Valid 8-digit OTP succeeds once; replay fails.
10. Successful OTP use creates/sends a new OTP; time-window login does not.
11. Secret-bearing fields never appear in audit/log/receipt/public repo output.

This policy changes only by explicit OWNER instruction. Security implementation may strengthen authentication without weakening the OWNER usability targets above.
