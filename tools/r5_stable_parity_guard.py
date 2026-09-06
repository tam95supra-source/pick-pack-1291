#!/usr/bin/env python3
import json
from pathlib import Path
def need(c,m):
    if not c: raise SystemExit('R5_STABLE_PARITY_FAIL:'+m)
c=json.loads(Path('config/stable_r5_parity.json').read_text())
need(c['status']=='READY_NOT_LIVE' and c['deploy_now'] is False,'NO_DEPLOY')
need(c['environment_id']=='STABLE' and c['service_audience']=='PICK_PACK_1291_STABLE','IDENTITY')
need(c['shared_runtime_source'] is True,'SHARED_RUNTIME')
b=Path('app/build.gradle.kts').read_text(); need('create("stable")' in b and 'PICK_PACK_1291_STABLE' in b and 'STABLE_GSHEET_API_URL' in b,'ANDROID_STABLE'); need(not Path('app/src/stable').exists(),'SOURCE_FORK')
q=Path('service/src/quota_budget.ts').read_text(); need('quota_usage.used+excluded.used' in q and 'hard_limit=excluded.hard_limit' in q,'QUOTA')
need('day_revision_state' in Path('service/src/core.ts').read_text(),'REVISION'); need('day_revision_state' in Path('service/src/sync_contract.ts').read_text(),'O1'); need('push_wake_outbox' in Path('service/src/push.ts').read_text(),'WAKE')
print('R5_STABLE_PARITY_PASS READY_NOT_LIVE')
