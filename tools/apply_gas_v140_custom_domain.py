#!/usr/bin/env python3
from pathlib import Path

p = Path('google-apps-script/SERVICE_MIGRATION_M2.gs')
s = p.read_text(encoding='utf-8')

if 'PP_M2_CUSTOM_DOMAIN_V140' in s:
    print('GAS v140 custom domain patch already present')
    raise SystemExit(0)

old = "function ppM2ServiceUrl_(){return String(ppM2Props_().getProperty('PP_M2_SERVICE_URL')||'').replace(/\\/+$/,'');}\nfunction ppM2BridgeSecret_(){return String(ppM2Props_().getProperty('PP_M2_GAS_BRIDGE_SECRET')||'');}\nfunction ppM2ValidServiceUrl_(v){return /^https:\\/\\/[A-Za-z0-9._-]+(?:\\.workers\\.dev|\\.pages\\.dev)(?:\\/.*)?$/.test(String(v||''));}"
new = "// PP_M2_CUSTOM_DOMAIN_V140: canonical Service endpoint is the approved custom domain.\nfunction ppM2CanonicalServiceUrl_(v){const raw=String(v||'').replace(/\\/+$/,'');return (raw==='https://pickpack.1291.workers.dev'||raw==='https://pickpack1291.cc.cd')?'https://pickpack1291.cc.cd':raw;}\nfunction ppM2ServiceUrl_(){return ppM2CanonicalServiceUrl_(ppM2Props_().getProperty('PP_M2_SERVICE_URL')||'');}\nfunction ppM2BridgeSecret_(){return String(ppM2Props_().getProperty('PP_M2_GAS_BRIDGE_SECRET')||'');}\nfunction ppM2ValidServiceUrl_(v){const raw=String(v||'').replace(/\\/+$/,'');return raw==='https://pickpack1291.cc.cd'||/^https:\\/\\/[A-Za-z0-9._-]+(?:\\.workers\\.dev|\\.pages\\.dev)(?:\\/.*)?$/.test(raw);}"
if old not in s:
    raise SystemExit('custom-domain function anchor missing')
s = s.replace(old, new, 1)

old = "serviceUrl:String(all.PP_M2_SERVICE_URL||'').replace(/\\/+$/,''),"
new = "serviceUrl:ppM2CanonicalServiceUrl_(all.PP_M2_SERVICE_URL||''),"
if old not in s:
    raise SystemExit('state snapshot serviceUrl anchor missing')
s = s.replace(old, new, 1)

old = "const nextEpoch=Number(body.authority_epoch||0),generation=String(body.service_generation||''),url=String(body.service_url||ppM2ServiceUrl_());"
new = "const nextEpoch=Number(body.authority_epoch||0),generation=String(body.service_generation||''),url=ppM2CanonicalServiceUrl_(String(body.service_url||ppM2ServiceUrl_()));"
if old not in s:
    raise SystemExit('failback url anchor missing')
s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
assert 'PP_M2_CUSTOM_DOMAIN_V140' in s
assert "'https://pickpack1291.cc.cd'" in s
assert 'serviceUrl:ppM2CanonicalServiceUrl_' in s
print('GAS v140 custom domain patch applied')
