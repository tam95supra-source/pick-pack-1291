#!/usr/bin/env python3
from pathlib import Path

root=Path(__file__).resolve().parents[1]
src=(root/"tools/beta_auth_converge.py").read_text(encoding="utf-8")

assert "def repair_sheet_parity_from_d1" in src
assert 'release.get("mode")=="REPAIR_BETA_AUTH_SHEET_PARITY"' in src
start=src.index("def repair_sheet_parity_from_d1")
end=src.index("def stable_reject",start)
block=src[start:end]

for token in [
    "SELECT login_id,role,status,verifier,display_name,position,email,source_row FROM accounts",
    "AUTH_PARITY_REPAIR",
    "BETA_SHEET_VERIFIER_PARITY_FAILED",
    "BETA_D1_CHANGED_DURING_SHEET_PARITY_REPAIR",
    "STABLE_AUTH_CHANGED_DURING_BETA_SHEET_PARITY_REPAIR",
    '"passwords_rotated":False',
    '"d1_mutated":False',
    '"sessions_revoked":False',
]:
    assert token in block, token

for forbidden in ["make_credential(", "INSERT INTO accounts", "UPDATE accounts SET", "DELETE FROM auth_sessions", "DELETE FROM auth_web_sessions", "DELETE FROM auth_challenges"]:
    assert forbidden not in block, forbidden

main=src[src.index("def main()"):src.index('if __name__=="__main__"')]
assert main.index('release.get("mode")=="REPAIR_BETA_AUTH_SHEET_PARITY"') < main.index("make_credential()")

print("beta112_auth_parity_repair_contract=PASS non_rotating=PASS d1_read_only=PASS stable_unchanged_guard=PASS verifier_parity=PASS")
