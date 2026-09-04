#!/usr/bin/env python3
from pathlib import Path

root=Path(__file__).resolve().parents[1]
p=root/'tools/beta83_publish_ota.sh'
s=p.read_text(encoding='utf-8')
old='''if [[ "$BASE_FINAL_KIND" == REPO_TECHNICAL_PASS ]]; then
  jq -e --arg v "$PREV" --arg source "$BASE_SOURCE" --arg h "$BASE_SHA" --argjson z "$BASE_SIZE" --arg signer "$SIGNER" '\n    .status=="PASS" and .version_name==$v and .candidate_source_sha==$source and .apk_sha256==$h and .apk_size==$z and\n'''
new='''if [[ "$BASE_FINAL_KIND" == REPO_TECHNICAL_PASS ]]; then
  jq -e --arg v "$PREV" --arg source "$BASE_CANDIDATE_SOURCE" --arg h "$BASE_SHA" --argjson z "$BASE_SIZE" --arg signer "$SIGNER" '\n    .status=="PASS" and .version_name==$v and .candidate_source_sha==$source and .apk_sha256==$h and .apk_size==$z and\n'''
if old not in s:
    raise SystemExit('BETA118_PUBLISH_PREFLIGHT_EXPECTED_BLOCK_NOT_FOUND')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('BETA118_PUBLISH_PREFLIGHT_REPAIR_APPLIED')
