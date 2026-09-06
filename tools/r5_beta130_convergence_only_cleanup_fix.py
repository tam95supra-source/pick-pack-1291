#!/usr/bin/env python3
from pathlib import Path

p = Path('tools/r5_beta130_convergence_only_gate.sh')
s = p.read_text(encoding='utf-8')

anchor = '''# Create five isolated disposable accounts with verifier keys generated only for this run.
# No production password/credential is read or derived.
: > "$D/auth-fixture.tsv"
'''
replacement = '''# Create five isolated disposable accounts with verifier keys generated only for this run.
# No production password/credential is read or derived.
cleanup(){
  set +e
  sql "DELETE FROM outbound_replication_outbox WHERE event_id IN (SELECT event_id FROM events WHERE actor_id LIKE '__R5_LOGIN_${SUFFIX}_%'); DELETE FROM sheet_replication_outbox WHERE event_id IN (SELECT event_id FROM events WHERE actor_id LIKE '__R5_LOGIN_${SUFFIX}_%'); DELETE FROM resource_leases WHERE mnv='$B80_MNV'; DELETE FROM attendance_sessions WHERE mnv='$B80_MNV'; DELETE FROM events WHERE actor_id LIKE '__R5_LOGIN_${SUFFIX}_%'; DELETE FROM employees WHERE mnv='$B80_MNV'; DELETE FROM auth_web_sessions WHERE login_id LIKE '__R5_LOGIN_${SUFFIX}_%'; DELETE FROM auth_sessions WHERE login_id LIKE '__R5_LOGIN_${SUFFIX}_%'; DELETE FROM auth_challenges WHERE login_id LIKE '__R5_LOGIN_${SUFFIX}_%'; DELETE FROM accounts WHERE login_id LIKE '__R5_LOGIN_${SUFFIX}_%';" >/dev/null 2>&1 || true
}
trap 'rc=$?; cleanup; exit $rc' EXIT
cleanup
: > "$D/auth-fixture.tsv"
'''
if s.count(anchor) != 1:
    raise SystemExit(f'R5_CLEANUP_EARLY_ANCHOR:{s.count(anchor)}')
s = s.replace(anchor, replacement, 1)

old = '''cleanup(){
  set +e
  # Delete only disposable projections/outboxes/auth fixtures. Test events are removed using
  # the same established CI cleanup pattern; day revision remains monotonic.
  sql "DELETE FROM outbound_replication_outbox WHERE event_id IN (SELECT event_id FROM events WHERE actor_id LIKE '__R5_LOGIN_${SUFFIX}_%'); DELETE FROM sheet_replication_outbox WHERE event_id IN (SELECT event_id FROM events WHERE actor_id LIKE '__R5_LOGIN_${SUFFIX}_%'); DELETE FROM resource_leases WHERE mnv='$B80_MNV'; DELETE FROM attendance_sessions WHERE mnv='$B80_MNV'; DELETE FROM events WHERE actor_id LIKE '__R5_LOGIN_${SUFFIX}_%'; DELETE FROM employees WHERE mnv='$B80_MNV'; DELETE FROM auth_web_sessions WHERE login_id LIKE '__R5_LOGIN_${SUFFIX}_%'; DELETE FROM auth_sessions WHERE login_id LIKE '__R5_LOGIN_${SUFFIX}_%'; DELETE FROM auth_challenges WHERE login_id LIKE '__R5_LOGIN_${SUFFIX}_%'; DELETE FROM accounts WHERE login_id LIKE '__R5_LOGIN_${SUFFIX}_%';" >/dev/null 2>&1 || true
}
trap 'rc=$?; cleanup; exit $rc' EXIT
cleanup

# Recreate accounts after cleanup baseline and login sessions are intentionally preserved above.
# cleanup() before the measurement would remove them, so only remove stale same-prefix rows that
# predate this run before fixture creation; current run prefix is unique and therefore no-op here.
# The active five sessions remain valid.

'''
if s.count(old) != 1:
    raise SystemExit(f'R5_CLEANUP_LATE_ANCHOR:{s.count(old)}')
s = s.replace(old, '', 1)

p.write_text(s, encoding='utf-8')
print('R5_CONVERGENCE_FIXTURE_CLEANUP_PATCH_PASS')
