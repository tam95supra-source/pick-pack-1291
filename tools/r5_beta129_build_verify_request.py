#!/usr/bin/env python3
import json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'ops/beta-release-request.json'
r=json.loads(p.read_text(encoding='utf-8'))
scope=json.loads((ROOT/'ops/OWNER_SCOPE_CURRENT.json').read_text(encoding='utf-8'))
assert scope['scope_id']=='OWNER_20260906_R5_QUOTA_REALTIME' and scope['revision']==5
req=next(x for x in scope['requirements'] if x['requirement_id']=='R5-15')
assert req['state']=='LOCKED_REQUIREMENT_PENDING_FIX'
assert r['stage']=='pass_live' and r['version_name']=='0.4.2-beta.128' and r['version_code']==134 and r['live'] is True
assert r['candidate_locked'] is True and r['human_visual_pass'] is True

source_sha=subprocess.check_output(['git','rev-list','-1','HEAD','--','app','service','google-apps-script'],cwd=ROOT,text=True).strip()
assert len(source_sha)==40
gradle=(ROOT/'app/build.gradle.kts').read_text(encoding='utf-8')
assert 'versionCode = 135' in gradle and 'versionName = "0.4.2-beta.129"' in gradle
assert subprocess.run(['git','diff','--quiet',source_sha,'HEAD','--','app','service','google-apps-script'],cwd=ROOT).returncode==0

old=dict(r)
r.update({
  'stage':'BUILD_VERIFY','mode':'BUILD_VERIFY_EXACT_SOURCE_R5','version_name':'0.4.2-beta.129','version_code':135,
  'base_version':old['version_name'],'base_version_code':old['version_code'],'base_source_sha':old['source_sha'],
  'base_candidate_source_sha':old.get('candidate_source_sha',old['source_sha']),'base_apk_sha256':old['apk_sha256'],'base_apk_size':old['apk_size'],
  'source_sha':source_sha,'candidate_source_sha':source_sha,'package':old['package'],'signer_sha256':old['signer_sha256'],
  'candidate_locked':False,'release_lock_status':'BUILD_VERIFY_PENDING','rebuild':False,'resign':False,'live':False,
  'stable_publish':'FORBIDDEN','authority_change':'NONE',
  'release_notes':[
    'Realtime theo delta/revision: không full reload ở đường đồng bộ bình thường.',
    'PDA dùng một bộ điều phối sync; wake/push được coalesce và outbox nền có trạng thái terminal.',
    'Google Sheets batch có ACK fence; tác vụ phụ dùng quota circuit động và dirty/due scheduling.',
    'Beta129 bổ sung gate đo local UI p95 trên exact signed candidate.'
  ],
  'base_candidate_run_id':old['candidate_run_id'],'base_candidate_artifact_id':old['candidate_artifact_id'],'base_candidate_artifact_name':old['candidate_artifact_name'],
  'service_gate_required':True,'service_gate_status':'PENDING','fast_check':'PENDING','human_visual_pass':False,
  'human_visual_sizes':[],'human_visual_screenshot_count':0,'human_visual_evidence':'','visual_matrix':'PENDING','pda_functional_pre_ota':'PENDING',
  'back_api36':'PENDING','device_regression_status':'PENDING','service_discovery_status':'PENDING','runtime_dod_status':'PENDING',
  'technical_pass_status':'PENDING','owner_acceptance':'PENDING','ota_readback_status':'PENDING','apk_transport':'GITHUB_RELEASE_ONLY','google_drive_apk':'FORBIDDEN',
  'execution_nonce':'beta129-r5-build-verify-20260906-01','next_action':'RUN_BETA129_R5_BUILD_VERIFY','owner_scope':scope['scope_id'],
  'owner_scope_source':'Canonical ops/OWNER_SCOPE_CURRENT.json revision 5','owner_scope_semantics_sha256':scope['semantics_sha256'],
  'owner_scope_sha256':scope['scope_sha256'],'owner_command_ledger_head':scope['ledger_head_event_sha256'],'owner_checklist':[],
  'owner_checklist_revision':5,'technical_pass_requirement_numbers':[],
})
for key in [
  'candidate_run_id','candidate_artifact_id','candidate_artifact_name','apk_sha256','apk_size','service_gate_run_id','service_gate_artifact_id',
  'service_gate_artifact_name','service_gate_inherited_reason','fast_check_run_id','verify_run_id','verify_artifact_id','verify_artifact_name',
  'pda_functional_run_id','pda_functional_artifact_id','back_api36_run_id','back_api36_artifact_id','device_regression_run_id',
  'device_regression_artifact_id','service_discovery_run_id','runtime_dod_run_id','runtime_dod_artifact_id','runtime_dod_artifact_name','publish_run_id','ota_readback_run_id'
]: r.pop(key,None)

p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'BETA129_BUILD_VERIFY_REQUEST_READY','source_sha':source_sha,'base_source_sha':r['base_source_sha'],'scope':r['owner_scope']},ensure_ascii=False))
