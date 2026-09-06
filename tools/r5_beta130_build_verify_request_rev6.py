#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
request_path = ROOT / 'ops/beta-release-request.json'
request = json.loads(request_path.read_text(encoding='utf-8'))
scope = json.loads((ROOT / 'ops/OWNER_SCOPE_CURRENT.json').read_text(encoding='utf-8'))
parity = json.loads((ROOT / 'config/stable_r5_parity.json').read_text(encoding='utf-8'))

assert scope['scope_id'] == 'OWNER_20260906_R5_QUOTA_REALTIME'
assert scope['revision'] == 6
req = next(x for x in scope['requirements'] if x['requirement_id'] == 'R5-15')
assert req['invariant_id'] == 'QUOTA-REALTIME-DELTA-001'
assert req['state'] == 'LOCKED_REQUIREMENT_PENDING_FIX'
assert parity['status'] == 'READY_NOT_LIVE'
assert parity['deploy_now'] is False
assert parity['activation'] == 'OWNER_PROMOTE_ONLY'
assert parity['environment_id'] == 'STABLE'

# Beta129 never became LIVE. Its VERIFY_ONLY request must continue to point back to
# the public Beta128 rollback base; Beta130 is built from that same LIVE base plus
# the accepted R5 source changes.
assert request['stage'] == 'VERIFY_ONLY'
assert request['version_name'] == '0.4.2-beta.129'
assert request['version_code'] == 135
assert request['live'] is False
assert request['base_version'] == '0.4.2-beta.128'
assert request['base_version_code'] == 134
assert request['base_source_sha'] == '5569d1e931436e02d118ed8ab57f2143de43b9f7'
assert request['base_apk_sha256'] == '04b135c554c6de6aa979b113a3435cec65063c87e79f232d8c8ea28e1d75f4ce'
assert request['base_apk_size'] == 14461941
assert request['stable_publish'] == 'FORBIDDEN'
assert request['authority_change'] == 'NONE'

source_sha = subprocess.check_output(
    ['git', 'rev-list', '-1', 'HEAD', '--', 'app', 'service', 'google-apps-script'],
    cwd=ROOT,
    text=True,
).strip()
assert len(source_sha) == 40
assert subprocess.run(
    ['git', 'diff', '--quiet', source_sha, 'HEAD', '--', 'app', 'service', 'google-apps-script'],
    cwd=ROOT,
).returncode == 0

gradle = (ROOT / 'app/build.gradle.kts').read_text(encoding='utf-8')
notes = (ROOT / 'app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt').read_text(encoding='utf-8')
assert 'versionCode = 136' in gradle
assert 'versionName = "0.4.2-beta.130"' in gradle
assert 'versionCode = 1' in gradle and 'versionName = "0.1.0-stable"' in gradle
assert 'const val VERSION_NAME = "0.4.2-beta.130"' in notes
assert 'chỉ thêm hoặc cập nhật đúng thẻ thay đổi' in notes

rollback = {
    'version_name': request['base_version'],
    'version_code': request['base_version_code'],
    'source_sha': request['base_source_sha'],
    'candidate_source_sha': request.get('base_candidate_source_sha', request['base_source_sha']),
    'apk_sha256': request['base_apk_sha256'],
    'apk_size': request['base_apk_size'],
    'candidate_run_id': request['base_candidate_run_id'],
    'candidate_artifact_id': request['base_candidate_artifact_id'],
    'candidate_artifact_name': request['base_candidate_artifact_name'],
    'live_final_run_id': request.get('base_live_final_run_id'),
    'live_final_artifact_id': request.get('base_live_final_artifact_id'),
    'live_final_artifact_name': request.get('base_live_final_artifact_name'),
}

request.update({
    'stage': 'BUILD_VERIFY',
    'mode': 'BUILD_VERIFY_EXACT_SOURCE_R5_REV6',
    'version_name': '0.4.2-beta.130',
    'version_code': 136,
    'base_version': rollback['version_name'],
    'base_version_code': rollback['version_code'],
    'base_source_sha': rollback['source_sha'],
    'base_candidate_source_sha': rollback['candidate_source_sha'],
    'base_apk_sha256': rollback['apk_sha256'],
    'base_apk_size': rollback['apk_size'],
    'source_sha': source_sha,
    'candidate_source_sha': source_sha,
    'package': request['package'],
    'signer_sha256': request['signer_sha256'],
    'candidate_locked': False,
    'release_lock_status': 'BUILD_VERIFY_PENDING',
    'rebuild': False,
    'resign': False,
    'live': False,
    'stable_publish': 'FORBIDDEN',
    'authority_change': 'NONE',
    'release_notes': [
        'Realtime theo delta/revision: đường đồng bộ bình thường không tải lại toàn bộ màn hình.',
        'PDA dùng một bộ điều phối sync; wake/push được gom và outbox nền có trạng thái terminal.',
        'Google Sheets dùng batch + ACK fence; tác vụ phụ theo quota circuit và dirty/due scheduling.',
        'Timeline nhân sự cập nhật gia tăng theo event_id, không dựng lại toàn bộ danh sách mỗi revision.',
        'Stable được chuẩn bị cùng R5 nhưng giữ READY_NOT_LIVE cho tới lệnh OWNER promote.'
    ],
    'base_candidate_run_id': rollback['candidate_run_id'],
    'base_candidate_artifact_id': rollback['candidate_artifact_id'],
    'base_candidate_artifact_name': rollback['candidate_artifact_name'],
    'base_live_final_run_id': rollback['live_final_run_id'],
    'base_live_final_artifact_id': rollback['live_final_artifact_id'],
    'base_live_final_artifact_name': rollback['live_final_artifact_name'],
    'service_gate_required': True,
    'service_gate_status': 'PENDING',
    'fast_check': 'PENDING',
    'human_visual_pass': False,
    'human_visual_sizes': [],
    'human_visual_screenshot_count': 0,
    'human_visual_evidence': '',
    'visual_matrix': 'PENDING',
    'pda_functional_pre_ota': 'PENDING',
    'back_api36': 'PENDING',
    'device_regression_status': 'PENDING',
    'service_discovery_status': 'PENDING',
    'runtime_dod_status': 'PENDING',
    'technical_pass_status': 'PENDING',
    'owner_acceptance': 'PENDING',
    'ota_readback_status': 'PENDING',
    'apk_transport': 'GITHUB_RELEASE_ONLY',
    'google_drive_apk': 'FORBIDDEN',
    'execution_nonce': 'beta130-r5-rev6-build-verify-20260906-01',
    'next_action': 'RUN_BETA130_R5_BUILD_VERIFY',
    'owner_scope': scope['scope_id'],
    'owner_scope_source': f"Canonical ops/OWNER_SCOPE_CURRENT.json revision {scope['revision']}",
    'owner_scope_semantics_sha256': scope['semantics_sha256'],
    'owner_scope_sha256': scope['scope_sha256'],
    'owner_command_ledger_head': scope['ledger_head_event_sha256'],
    'owner_checklist': [],
    'owner_checklist_revision': scope['revision'],
    'technical_pass_requirement_numbers': [],
    'stable_r5_parity_status': parity['status'],
    'stable_r5_activation': parity['activation'],
})

# Candidate-specific evidence from the rejected Beta129 bytes must not carry forward.
for key in [
    'owner_checklist_id',
    'candidate_run_id', 'candidate_artifact_id', 'candidate_artifact_name',
    'apk_sha256', 'apk_size',
    'service_gate_run_id', 'service_gate_artifact_id', 'service_gate_artifact_name',
    'service_gate_inherited_reason',
    'fast_check_run_id',
    'verify_run_id', 'verify_artifact_id', 'verify_artifact_name',
    'pda_functional_run_id', 'pda_functional_artifact_id',
    'back_api36_run_id', 'back_api36_artifact_id',
    'device_regression_run_id', 'device_regression_artifact_id',
    'service_discovery_run_id',
    'runtime_dod_run_id', 'runtime_dod_artifact_id', 'runtime_dod_artifact_name',
    'publish_run_id', 'ota_readback_run_id',
]:
    request.pop(key, None)

request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({
    'status': 'BETA130_R5_REV6_BUILD_VERIFY_REQUEST_READY',
    'source_sha': source_sha,
    'base_source_sha': request['base_source_sha'],
    'scope_revision': scope['revision'],
    'stable': request['stable_r5_parity_status'],
}, ensure_ascii=False))
