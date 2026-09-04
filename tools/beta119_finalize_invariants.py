#!/usr/bin/env python3
from pathlib import Path

DOC = Path("docs/STABLE_INVARIANTS.md")
REG = Path("qa/stable_invariants.yml")

DOC_MARK = "### CURRENT_PUBLIC_BETA_001"
DOC_APPEND = r'''

## Beta119 — Technical PASS awaiting OWNER acceptance

### CURRENT_PUBLIC_BETA_001
- Status: TECHNICAL_PASS_AWAITING_OWNER
- Scope: Control plane / Beta current pointer
- Rule: `beta/current` và `CURRENT_STATE.md` phải nhận diện Beta public LIVE mới nhất; Beta/checklist cũ không được ghi đè trạng thái mới hơn.
- Regression: `tools/beta_current_sync_contract.py` + `tools/owner_acceptance_ledger_guard.py`; monotonic Beta/version/checklist fence; fast-forward only; post-sync readback.
- Technical evidence: Beta119 LIVE 0.4.2-beta.119 / source `eeb45df6deae267d93a5fb15701a0a394885a549`; terminal run `33868929441`; release/OTA/finalize PASS; acceptance ledger `BETA119_OWNER_ACCEPTANCE_20260904_R1` revision 1.
- OWNER acceptance: PENDING.

### SUPERADMIN_AUTH_002
- Status: TECHNICAL_PASS_AWAITING_OWNER
- Scope: Auth / SUPERADMIN / Android + GAS
- Rule: phiên đăng nhập hợp lệ phải được giữ qua update/process restart; SUPERADMIN chỉ có 2 credential method: chuỗi 1..20 ký tự chứa `HHmm` thời gian server trong ±5 phút, hoặc OTP Gmail đúng 8 chữ số dùng một lần; OTP dùng thành công tự cấp/gửi mã kế tiếp; time login không rotate/gửi OTP; static SUPERADMIN password login bị vô hiệu; không lưu credential secret plaintext trong GitHub public.
- Regression: `tools/beta119_superadmin_auth_contract.py`; live SUPERADMIN auth run `33865867111`; auth convergence run `33867109026` đồng thời chứng minh ADMIN thường vẫn password/challenge PASS và Stable isolation PASS.
- Technical evidence: Beta119 exact candidate `33864111135/9933396813`; Fast Check `33867108883`; terminal publish/OTA/install/open/readback/finalize `33868929441`; SHA256 `73c072187fb13bab635f27009fda500d0745fced4244a8d8276bc9117f350697`.
- OWNER acceptance: PENDING.

### OWNER_ACCEPTANCE_LEDGER_001
- Status: TECHNICAL_PASS_AWAITING_OWNER
- Scope: Control plane / OWNER acceptance continuity
- Rule: checklist/acceptance phải lưu bền trong GitHub, monotonic theo state epoch + Beta version + checklist revision; chat/memory/handoff chỉ dùng để điều hướng, không được làm authority và không được hồi quy về checklist Beta cũ.
- Regression: `tools/owner_acceptance_ledger_guard.py`; `ops/owner-acceptance-current.json`; lower epoch/Beta/revision rejected; OWNER silence không phải acceptance.
- Technical evidence: Beta119 ledger state epoch `202609041845`, checklist `BETA119_OWNER_ACCEPTANCE_20260904_R1`, revision 1, technical status PASS_LIVE / awaiting OWNER.
- OWNER acceptance: PENDING.
'''

REG_APPEND = r'''

  - id: CURRENT_PUBLIC_BETA_001
    status: TECHNICAL_PASS_AWAITING_OWNER
    scope: control-plane-current
    rule: "beta/current and CURRENT_STATE identify the newest public LIVE Beta; older Beta/checklist state cannot overwrite newer state."
    technical_candidate: "0.4.2-beta.119 / eeb45df6deae267d93a5fb15701a0a394885a549"
    regression_minimum: [monotonic_beta, fast_forward_only, no_force, current_ota_readback, stale_beta_rejected]
    regression_case: "tools/beta_current_sync_contract.py + tools/owner_acceptance_ledger_guard.py"
    technical_evidence: "terminal 33868929441 PASS; release/OTA/install/open/readback/finalize PASS; checklist BETA119_OWNER_ACCEPTANCE_20260904_R1 rev1"
    owner_acceptance: "PENDING"

  - id: SUPERADMIN_AUTH_002
    status: TECHNICAL_PASS_AWAITING_OWNER
    scope: superadmin-auth
    rule: "Valid session survives update/process restart; SUPERADMIN credential methods are HHmm +/-5 embedded in 1..20 chars or 8-digit single-use email OTP; successful OTP sends next OTP; time login does not rotate OTP; static SUPERADMIN password disabled; no plaintext credential secret in public repo."
    technical_candidate: "0.4.2-beta.119 / eeb45df6deae267d93a5fb15701a0a394885a549"
    regression_minimum: [session_restore, time_input_max20, hhmm_plus_minus_5, arbitrary_surrounding_text, midnight_window, otp_exact8, otp_single_use, otp_next_on_success, time_no_otp_rotate, normal_admin_password_login, stable_auth_isolation, public_secret_guard]
    regression_case: "tools/beta119_superadmin_auth_contract.py"
    technical_evidence: "candidate 33864111135/9933396813; live auth 33865867111 PASS; Fast Check 33867108883 PASS; auth convergence 33867109026/9934703912 PASS; terminal 33868929441 PASS; SHA256 73c072187fb13bab635f27009fda500d0745fced4244a8d8276bc9117f350697"
    owner_acceptance: "PENDING"

  - id: OWNER_ACCEPTANCE_LEDGER_001
    status: TECHNICAL_PASS_AWAITING_OWNER
    scope: owner-acceptance-control-plane
    rule: "OWNER checklist and responses are GitHub-backed and monotonic by epoch, Beta version and checklist revision; stale chat/handoff state cannot override newer acceptance state; silence is not acceptance."
    technical_candidate: "0.4.2-beta.119"
    regression_minimum: [epoch_rollback_rejected, beta_rollback_rejected, checklist_revision_rollback_rejected, response_history_not_truncated, owner_silence_false]
    regression_case: "tools/owner_acceptance_ledger_guard.py"
    technical_evidence: "ops/owner-acceptance-current.json epoch 202609041845 / BETA119_OWNER_ACCEPTANCE_20260904_R1 rev1"
    owner_acceptance: "PENDING"
'''


def append_once(path: Path, marker: str, addition: str):
    text = path.read_text()
    if marker in text:
        return False
    path.write_text(text.rstrip() + addition + "\n")
    return True

changed_doc = append_once(DOC, DOC_MARK, DOC_APPEND)
changed_reg = append_once(REG, "- id: CURRENT_PUBLIC_BETA_001", REG_APPEND)

# Fail closed on malformed registry. PyYAML is available on the GitHub runner through repo tooling;
# if not, the structural checks below still prevent an unindented/top-level accidental append.
text = REG.read_text()
for marker in ("  - id: CURRENT_PUBLIC_BETA_001", "  - id: SUPERADMIN_AUTH_002", "  - id: OWNER_ACCEPTANCE_LEDGER_001"):
    if marker not in text:
        raise SystemExit("MISSING_REGISTRY_MARKER:" + marker)
try:
    import yaml
    data = yaml.safe_load(text)
    ids = [x.get("id") for x in data.get("invariants", [])]
    for need in ("CURRENT_PUBLIC_BETA_001", "SUPERADMIN_AUTH_002", "OWNER_ACCEPTANCE_LEDGER_001"):
        if ids.count(need) != 1:
            raise SystemExit("INVARIANT_ID_COUNT:" + need + ":" + str(ids.count(need)))
except ModuleNotFoundError:
    pass

print(f"beta119_finalize_invariants=PASS doc_changed={changed_doc} registry_changed={changed_reg}")
