#!/usr/bin/env python3
import hashlib
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

import stable_private_provision as sp

ROOT = pathlib.Path(__file__).resolve().parents[1]
RECEIPT = pathlib.Path('/tmp/stable-primary-gas-recovery-receipt.json')


def digest(obj):
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def webapp_snapshot(token, script_id, deployment_id):
    dep = sp.req_json(f'{sp.API_SCRIPT}/{script_id}/deployments/{deployment_id}', token=token)
    eps = []
    for ep in dep.get('entryPoints', []) or []:
        if ep.get('entryPointType') != 'WEB_APP':
            continue
        web = ep.get('webApp') or {}
        cfg = web.get('entryPointConfig') or {}
        eps.append({
            'url': str(web.get('url') or ''),
            'access': str(cfg.get('access') or ''),
            'executeAs': str(cfg.get('executeAs') or ''),
        })
    if len(eps) != 1:
        raise RuntimeError('STABLE_PRIMARY_WEBAPP_ENTRYPOINT_NOT_UNIQUE')
    ep = eps[0]
    return {
        'deployment_id': str(dep.get('deploymentId') or deployment_id),
        'version': (dep.get('deploymentConfig') or {}).get('versionNumber'),
        **ep,
    }


def stable_runtime_snapshot(req):
    dbs = sp.d1_inventory()
    matches = [x for x in dbs if x.get('name') == req['target_d1_name']]
    if len(matches) != 1:
        raise RuntimeError('STABLE_D1_IDENTITY_NOT_UNIQUE')
    d1_id = str(matches[0].get('uuid') or matches[0].get('id') or '')
    enc = sp.urllib.parse.quote(req['target_worker_name'], safe='')
    raw = sp.cf(f'/workers/scripts/{enc}/settings').get('result') or {}
    selected = []
    allowed_text = {
        'ENVIRONMENT_ID', 'SERVICE_AUDIENCE', 'SERVICE_GENERATION', 'GAS_API_URL',
        'OUTBOUND_GAS_API_URL', 'DR_GAS_API_URL', 'DR_TARGET_ID',
        'GOOGLE_SOURCE_SHEET_ID', 'GOOGLE_OUTBOUND_SHEET_ID',
    }
    for b in raw.get('bindings', []) or []:
        item = {'name': b.get('name'), 'type': b.get('type')}
        if b.get('type') == 'plain_text' and b.get('name') in allowed_text:
            item['text'] = b.get('text')
        if b.get('type') == 'd1':
            item['id'] = b.get('id')
        selected.append(item)
    return {
        'd1_id': d1_id,
        'worker_settings_hash': digest({
            'bindings': sorted(selected, key=lambda x: (str(x.get('name')), str(x.get('type')))),
            'compatibility_date': raw.get('compatibility_date'),
        }),
    }


def get_stable(url):
    last = None
    for attempt in range(1, 7):
        try:
            with urllib.request.urlopen(url, timeout=35) as r:
                body = r.read().decode('utf-8', 'replace')
                try:
                    payload = json.loads(body) if body.strip() else {}
                except Exception:
                    payload = {'raw': body[:300]}
                if r.status == 200 and payload.get('ok') is True and payload.get('environment_id') == 'STABLE':
                    return {'http': 200, 'attempt': attempt, 'environment_id': 'STABLE', 'ok': True}
                last = f'HTTP_{r.status}:{json.dumps(payload, ensure_ascii=False)[:300]}'
        except urllib.error.HTTPError as e:
            last = f'HTTP_{e.code}'
        except Exception as e:
            last = type(e).__name__ + ':' + str(e)[:200]
        time.sleep(5)
    raise RuntimeError('STABLE_PRIMARY_GET_NOT_RECOVERED:' + str(last))


def main():
    req = json.loads((ROOT / 'ops/stable-private-provision-request.json').read_text())
    if req.get('environment') != 'STABLE' or req.get('stable_public_activation') is not False:
        raise RuntimeError('STABLE_REQUEST_FAIL_CLOSED')
    if req.get('lifecycle_target') != 'READY_NOT_LIVE':
        raise RuntimeError('STABLE_LIFECYCLE_NOT_PRIVATE')

    token = sp.oauth()
    print('::add-mask::' + token)
    sid = req['stable_primary_sheet_id']
    contract_before = sp.contract_map(token, sid)
    script_id = str(contract_before.get('gas_script_id') or '')
    deployment_id = str(contract_before.get('gas_deployment_id') or '')
    web_url = str(contract_before.get('gas_web_url') or '')
    if not script_id or not deployment_id or not web_url:
        raise RuntimeError('STABLE_PRIMARY_GAS_ID_MISSING')

    deployment_before = webapp_snapshot(token, script_id, deployment_id)
    if deployment_before['deployment_id'] != deployment_id or deployment_before['url'] != web_url:
        raise RuntimeError('STABLE_PRIMARY_DEPLOYMENT_ID_URL_DRIFT')
    if deployment_before['access'] != 'ANYONE_ANONYMOUS' or deployment_before['executeAs'] != 'USER_DEPLOYING':
        raise RuntimeError('STABLE_PRIMARY_WEBAPP_POLICY_DRIFT')

    runtime_before = stable_runtime_snapshot(req)
    contract_hash_before = digest(contract_before)
    source_files = sp.gas_files('primary')
    source_hash = digest(source_files)

    # OWNER-approved narrow recovery: same Script project, same deployment ID, same canonical source.
    # No Sheet write, D1 SQL, Worker deploy/binding write, authority change, or Stable public activation.
    sp.req_json(f'{sp.API_SCRIPT}/{script_id}/content', 'PUT', token, {'files': source_files})
    version = sp.req_json(
        f'{sp.API_SCRIPT}/{script_id}/versions', 'POST', token,
        {'description': 'Stable primary private recovery - OWNER approved - READY_NOT_LIVE'},
    ).get('versionNumber')
    if not isinstance(version, int):
        raise RuntimeError('STABLE_PRIMARY_RECOVERY_VERSION_MISSING')
    sp.req_json(
        f'{sp.API_SCRIPT}/{script_id}/deployments/{deployment_id}', 'PUT', token,
        {'deploymentConfig': {
            'scriptId': script_id,
            'versionNumber': version,
            'manifestFileName': 'appsscript',
            'description': 'Stable primary READY_NOT_LIVE - recovery',
        }},
    )

    deployment_after = webapp_snapshot(token, script_id, deployment_id)
    if deployment_after['deployment_id'] != deployment_id or deployment_after['url'] != web_url:
        raise RuntimeError('STABLE_PRIMARY_RECOVERY_CHANGED_ID_URL')
    if deployment_after['access'] != 'ANYONE_ANONYMOUS' or deployment_after['executeAs'] != 'USER_DEPLOYING':
        raise RuntimeError('STABLE_PRIMARY_RECOVERY_POLICY_DRIFT')

    live = get_stable(web_url)
    contract_after = sp.contract_map(token, sid)
    runtime_after = stable_runtime_snapshot(req)
    if digest(contract_after) != contract_hash_before:
        raise RuntimeError('STABLE_PRIMARY_RECOVERY_SHEET_CONTRACT_CHANGED')
    if runtime_after != runtime_before:
        raise RuntimeError('STABLE_PRIMARY_RECOVERY_D1_OR_WORKER_CHANGED')

    receipt = {
        'status': 'PASS',
        'phase': 'STABLE_PRIVATE_PRIMARY_GAS_RECOVERY',
        'owner_authorized': True,
        'stable_public_activation': False,
        'lifecycle': 'READY_NOT_LIVE',
        'script_id_unchanged': True,
        'deployment_id_unchanged': True,
        'web_url_unchanged': True,
        'webapp_policy': 'ANYONE_ANONYMOUS/USER_DEPLOYING',
        'new_version': version,
        'source_hash': source_hash,
        'live_get': live,
        'sheet_contract_changed': False,
        'd1_changed': False,
        'worker_changed': False,
        'authority_changed': False,
        'beta_touched': False,
        'runtime_identity': runtime_after,
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n')
    print('STABLE_PRIMARY_GAS_RECOVERY_PASS')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        RECEIPT.write_text(json.dumps({
            'status': 'FAIL',
            'phase': 'STABLE_PRIVATE_PRIMARY_GAS_RECOVERY',
            'error': str(e)[:1200],
            'stable_public_activation': False,
        }, indent=2, ensure_ascii=False) + '\n')
        print('STABLE_PRIMARY_GAS_RECOVERY_ERROR:' + str(e)[:1600], file=sys.stderr)
        sys.exit(1)
