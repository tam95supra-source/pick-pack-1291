#!/usr/bin/env python3
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/'tools/beta83_publish_ota.sh').read_text(encoding='utf-8')
assert 'BASE_CANDIDATE_SOURCE=$(jq -r' in s
block=s[s.index('if [[ "$BASE_FINAL_KIND" == REPO_TECHNICAL_PASS ]]'):s.index('else\n',s.index('if [[ "$BASE_FINAL_KIND" == REPO_TECHNICAL_PASS ]]'))]
assert '--arg source "$BASE_CANDIDATE_SOURCE"' in block
assert '.candidate_source_sha==$source' in block
r=json.loads((root/'ops/beta-release-request.json').read_text(encoding='utf-8'))
# Release metadata required before any production write.
for k in ('release_notes','base_apk_sha256','base_apk_size','base_candidate_source_sha'):
    assert k in r, k
assert isinstance(r['release_notes'],list) and len(r['release_notes'])>0
assert len(r['base_apk_sha256'])==64 and isinstance(r['base_apk_size'],int)
assert len(r['base_candidate_source_sha'])==40
print('beta118_publish_preflight_contract=PASS')
