#!/usr/bin/env python3
from pathlib import Path

DOMAIN = 'pickpack1291.cc.cd'
files = [
    Path('app/src/main/java/vn/pickpack1291/app/beta/M2RuntimeBridge.kt'),
    Path('app/src/main/java/vn/pickpack1291/app/beta/M2ServiceTransport.kt'),
]

for p in files:
    s = p.read_text(encoding='utf-8')
    if f'url.host == "{DOMAIN}"' in s or f'u.host == "{DOMAIN}"' in s:
        print(f'{p}: custom domain already present')
        continue
    if p.name == 'M2RuntimeBridge.kt':
        old = '(url.host.endsWith(".workers.dev") || url.host.endsWith(".pages.dev"))'
        new = f'(url.host == "{DOMAIN}" || url.host.endsWith(".workers.dev") || url.host.endsWith(".pages.dev"))'
    else:
        old = '(u.host.endsWith(".workers.dev") || u.host.endsWith(".pages.dev") || u.host == "localhost")'
        new = f'(u.host == "{DOMAIN}" || u.host.endsWith(".workers.dev") || u.host.endsWith(".pages.dev") || u.host == "localhost")'
    if s.count(old) != 1:
        raise SystemExit(f'{p}: validator anchor expected once, got {s.count(old)}')
    p.write_text(s.replace(old, new, 1), encoding='utf-8')
    print(f'{p}: patched')

runtime = files[0].read_text(encoding='utf-8')
transport = files[1].read_text(encoding='utf-8')
assert f'url.host == "{DOMAIN}"' in runtime
assert f'u.host == "{DOMAIN}"' in transport
assert '.workers.dev' in runtime and '.workers.dev' in transport
assert '.pages.dev' in runtime and '.pages.dev' in transport
print('Beta63 canonical custom Service domain allowlist: PASS')
