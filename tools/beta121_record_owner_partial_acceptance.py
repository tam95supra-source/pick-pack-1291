#!/usr/bin/env python3
import json,re,sys
from pathlib import Path

root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
now='2026-09-05T08:20:00+07:00'
epoch=202609050820
raw='1 ok 2 anh vẫn thấy lịch sử hiển thị dù về user, anh muốn quyền hạ thực sự như user, admin. Chỉ có phần chọn quyền là tồn tại để chuyển thôi. 3 ok 4 chưa thấy nguồn ở phần thông tin pda cũng như danh sách pda ở tài nguyên, mới cập nhật gsheet chưa cập nhập app à?'
status={
 'UI-STATUS-DETAIL-VI-003':('ACTIVE_PASS','PASS — OWNER item 1 OK, 2026-09-05 08:20 +07:00.'),
 'SUPERADMIN-EFFECTIVE-ROLE-003':('LOCKED_REQUIREMENT_PENDING_FIX','NOT OK — khi hạ về USER vẫn thấy Lịch sử; OWNER yêu cầu toàn bộ quyền nghiệp vụ hạ thực sự như USER/ADMIN, chỉ bộ chọn quyền trong chi tiết Dịch vụ được giữ theo actual SUPERADMIN.'),
 'SETTINGS-REGION-INHOUSE-DROP-001':('ACTIVE_PASS','PASS — OWNER item 3 OK, 2026-09-05 08:20 +07:00.'),
 'PDA-SOURCE-MASTER-001':('LOCKED_REQUIREMENT_PENDING_FIX','NOT OK — Nguồn chưa hiển thị trong thông tin PDA và danh sách PDA ở Tài nguyên; data/GSheet đã có nhưng Android UI/edit chưa hoàn tất.'),
}

def md_update(text):
    for ident,(st,note) in status.items():
        pat=rf'(### {re.escape(ident)}\n)(.*?)(?=\n### |\Z)'
        m=re.search(pat,text,re.S)
        if not m: raise SystemExit('MISSING_MD_'+ident)
        block=m.group(2)
        block=re.sub(r'- Status: [^\n]+',f'- Status: {st}',block,1)
        if '- OWNER acceptance:' in block:
            block=re.sub(r'- OWNER acceptance: [^\n]+',f'- OWNER acceptance: {note}',block,1)
        else:
            block=block.rstrip()+f'\n- OWNER acceptance: {note}\n'
        text=text[:m.start(2)]+block+text[m.end(2):]
    return text

def yaml_update(text):
    for ident,(st,note) in status.items():
        pat=rf'(  - id: {re.escape(ident)}\n)(.*?)(?=\n  - id: |\Z)'
        m=re.search(pat,text,re.S)
        if not m: raise SystemExit('MISSING_YAML_'+ident)
        block=m.group(2)
        block=re.sub(r'    status: [^\n]+',f'    status: {st}',block,1)
        quoted=json.dumps(note,ensure_ascii=False)
        if '    owner_acceptance:' in block:
            block=re.sub(r'    owner_acceptance: [^\n]+',f'    owner_acceptance: {quoted}',block,1)
        else:
            block=block.rstrip()+f'\n    owner_acceptance: {quoted}\n'
        active='true' if st=='ACTIVE_PASS' else 'false'
        if '    active_pass:' in block:
            block=re.sub(r'    active_pass: (?:true|false)',f'    active_pass: {active}',block,1)
        else:
            block=block.rstrip()+f'\n    active_pass: {active}\n'
        text=text[:m.start(2)]+block+text[m.end(2):]
    return text

md=root/'docs/STABLE_INVARIANTS.md'; md.write_text(md_update(md.read_text(encoding='utf-8')),encoding='utf-8')
yml=root/'qa/stable_invariants.yml'; yml.write_text(yaml_update(yml.read_text(encoding='utf-8')),encoding='utf-8')

reqp=root/'ops/beta-release-request.json'; req=json.loads(reqp.read_text(encoding='utf-8'))
assert req['version_name']=='0.4.2-beta.121' and req['technical_pass_status']=='PASS'
req['owner_acceptance']='PARTIAL_ACCEPTANCE_PENDING_FIX'
req['next_action']='FIX_BETA121_OWNER_ITEMS_2_4_IN_BETA122'
reqp.write_text(json.dumps(req,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

old=json.loads((root/'ops/owner-acceptance-current.json').read_text(encoding='utf-8'))
ledger={
 'schema_version':1,'state_epoch':epoch,'channel':'BETA',
 'public_beta':{'version_name':req['version_name'],'version_code':req['version_code'],'source_sha':req['source_sha'],'apk_sha256':req['apk_sha256'],'technical_status':'PASS_LIVE'},
 'owner_scope':{'scope_id':req['owner_scope'],'status':'PARTIAL_ACCEPTANCE_PENDING_FIX','requirements':[
   {'id':'UI-STATUS-DETAIL-VI-003','status':'ACTIVE_PASS','rule':'Status header/detail Vietnamese + icons + manual sync accepted.'},
   {'id':'SUPERADMIN-EFFECTIVE-ROLE-003','status':'LOCKED_REQUIREMENT_PENDING_FIX','rule':'Only role selector may use actual SUPERADMIN; every business surface/action must obey effective USER/ADMIN/SUPERADMIN.'},
   {'id':'SETTINGS-REGION-INHOUSE-DROP-001','status':'ACTIVE_PASS','rule':'Settings grouped regions, Inhouse pending card and drop-receive table accepted.'},
   {'id':'PDA-SOURCE-MASTER-001','status':'LOCKED_REQUIREMENT_PENDING_FIX','rule':'PDA source must be visible/editable in Android PDA information and Resource PDA list using canonical source catalog.'}
 ]},
 'technical_evidence':{'candidate_run_id':req['candidate_run_id'],'candidate_artifact_id':req['candidate_artifact_id'],'fast_check_run_id':req['fast_check_run_id'],'service_visual_pda_run_id':req['verify_run_id'],'device_discovery_run_id':req['device_regression_run_id'],'runtime_dod_run_id':req['runtime_dod_run_id'],'beta_domain_run_id':req['beta_domain_run_id'],'terminal_run_id':int(req['publish_run_id']),'release_lock_receipt':req['release_lock_receipt'],'owner_receipt':'ops/beta121-owner-acceptance-partial.json'},
 'checklist':{'checklist_id':req['owner_checklist_id'],'revision':2,'status':'PARTIAL_ACCEPTANCE_PENDING_FIX','items':[
   {'number':1,'id':'UI-STATUS-DETAIL-VI-003','status':'OWNER_OK','test':'OWNER confirmed item 1 OK.'},
   {'number':2,'id':'SUPERADMIN-EFFECTIVE-ROLE-003','status':'OWNER_NOT_OK','test':'USER simulation still exposes History; effective-role lowering must be real everywhere except selector.'},
   {'number':3,'id':'SETTINGS-REGION-INHOUSE-DROP-001','status':'OWNER_OK','test':'OWNER confirmed item 3 OK.'},
   {'number':4,'id':'PDA-SOURCE-MASTER-001','status':'OWNER_NOT_OK','test':'PDA source missing from Android PDA info and Resource PDA list.'}
 ],'owner_responses':[{'recorded_at':now,'response':raw,'items':{'1':'OK','2':'NOT_OK','3':'OK','4':'NOT_OK'}}]},
 'previous_acceptance':{'version_name':old['public_beta']['version_name'],'state_epoch':old['state_epoch'],'checklist_id':old['checklist']['checklist_id'],'revision':old['checklist']['revision'],'status':old['checklist']['status']},
 'fencing':old['fencing'],'security':old['security'],'next_action':'FIX_BETA121_OWNER_ITEMS_2_4_IN_BETA122'
}
(root/'ops/owner-acceptance-current.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt={'status':'PARTIAL_ACCEPTANCE_PENDING_FIX','version_name':'0.4.2-beta.121','checklist_id':req['owner_checklist_id'],'revision':2,'recorded_at':now,'owner':'Nguyễn Văn Tâm','items':ledger['checklist']['items'],'next_action':ledger['next_action']}
(root/'ops/beta121-owner-acceptance-partial.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for p in [root/'CURRENT_STATE.md',root/'docs/handovers/HANDOVER_CURRENT.md']:
    s=p.read_text(encoding='utf-8')
    s=re.sub(r'(?im)^(- next_action:|NEXT_ACTION\n)\s*[^\n]*',lambda m: (m.group(1)+' FIX_BETA121_OWNER_ITEMS_2_4_IN_BETA122') if m.group(1).startswith('-') else 'NEXT_ACTION\nFIX_BETA121_OWNER_ITEMS_2_4_IN_BETA122',s)
    p.write_text(s,encoding='utf-8')
print('BETA121_OWNER_PARTIAL_ACCEPTANCE_RECORDED')
