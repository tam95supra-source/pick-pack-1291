# Beta119 SUPERADMIN auth regression

Scope: `SUPERADMIN_AUTH_002` — TECHNICAL pending OWNER acceptance.

Required checks:

1. Existing valid SUPERADMIN session survives in-place APK update/restart; startup does not clear token/account. Explicit logout/revoke/401 still clears auth.
2. Time method accepts only an active SUPERADMIN when input length is 1..20 and contains an exact server-time `HHmm` candidate within ±5 minutes. Arbitrary prefix/suffix characters are allowed. Midnight wrap must pass correctly.
3. Time input outside ±5 minutes or over 20 characters fails. No device trust/binding/Keystore state is required.
4. Legacy/static SUPERADMIN password login fails with the special-auth requirement, proving there are exactly two SUPERADMIN credential methods.
5. OTP must be exactly 8 decimal digits, cryptographically generated, single-use and rate-limited. Replay of a consumed OTP fails.
6. Successful OTP login atomically rotates to a new OTP and sends that next OTP to the configured SUPERADMIN email. Failed email delivery rolls OTP state back/fails closed.
7. Successful time login does not generate, rotate or email a new OTP.
8. Public-repo guard rejects plaintext passwords, OTPs, tokens, Gmail OAuth secrets and credential files. No auth input is logged/persisted in repo/artifact/receipt.
9. Normal non-SUPERADMIN password challenge/PBKDF2 login remains unchanged.
10. Stable/main/signer/authority remain unchanged.

Automated contract: `tools/beta119_superadmin_auth_contract.py`.
Policy: `docs/CONTROL_PLANE_AUTH_SECURITY_POLICY.md`.
Canonical acceptance pointer: `ops/owner-acceptance-current.json`.
