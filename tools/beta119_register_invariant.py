#!/usr/bin/env python3
from pathlib import Path

R=Path(__file__).resolve().parents[1]
y=R/'qa/stable_invariants.yml'
s=y.read_text(encoding='utf-8')
marker='  - id: SUPERADMIN-AUTH-002\n'
if marker not in s:
    if not s.endswith('\n'): s+='\n'
    s+='''\n  - id: SUPERADMIN-AUTH-002\n    status: LOCKED_REQUIREMENT_PENDING_FIX\n    scope: superadmin-auth\n    rule: "SUPERADMIN preserves valid session across app update/restart and has exactly two credential methods: a 1..20 character string containing server-current HHmm within +/-5 minutes with no device binding, or an exactly 8-digit single-use email OTP; successful OTP use sends the next OTP; time login does not rotate OTP; legacy/static SUPERADMIN password login is forbidden."\n    technical_candidate: "0.4.2-beta.119"\n    regression_minimum: [session_update_persistence, time_hhmm_plus_minus_5, arbitrary_prefix_suffix_max20, midnight_wrap, no_device_binding, legacy_superadmin_password_rejected, otp_exact_8_digits, otp_single_use_replay_rejected, otp_rotate_and_email_next, time_login_no_otp_rotation, non_superadmin_password_unchanged, public_secret_fence]\n    regression_case: "qa/beta119_superadmin_auth_regression.md + tools/beta119_superadmin_auth_contract.py + .github/workflows/superadmin-auth-regression.yml"\n    owner_acceptance: "PENDING"\n'''
    y.write_text(s,encoding='utf-8')

m=R/'docs/STABLE_INVARIANTS.md'
t=m.read_text(encoding='utf-8')
heading='## SUPERADMIN-AUTH-002 — PENDING OWNER ACCEPTANCE'
if heading not in t:
    if not t.endswith('\n'): t+='\n'
    t+='''\n\n## SUPERADMIN-AUTH-002 — PENDING OWNER ACCEPTANCE\n\n- Status: `LOCKED_REQUIREMENT_PENDING_FIX` until Beta119 Technical DoD PASS; then `TECHNICAL_PASS_AWAITING_OWNER` until OWNER explicitly accepts.\n- Preserve a valid SUPERADMIN session across in-place app update/restart; explicit logout/revocation/401 remains authoritative.\n- Exactly two SUPERADMIN credential methods: (1) input 1..20 characters containing server-current `HHmm` within ±5 minutes, arbitrary prefix/suffix and no device binding; (2) exactly 8 random decimal digits delivered by email and single-use.\n- Successful OTP use atomically rotates and emails the next OTP. Time-window login does not rotate/send OTP. Legacy/static SUPERADMIN password login is disabled.\n- Public GitHub/log/artifact/handoff must never contain plaintext password/OTP/session/Gmail OAuth secret or an offline-usable verifier.\n- Regression: `qa/beta119_superadmin_auth_regression.md`, `tools/beta119_superadmin_auth_contract.py`, `.github/workflows/superadmin-auth-regression.yml`.\n'''
    m.write_text(t,encoding='utf-8')
print('beta119_register_invariant=PASS')
