#!/usr/bin/env python3
from pathlib import Path

p = Path('tools/r5_service_convergence_gate.sh')
s = p.read_text(encoding='utf-8')

old = '''r5_service_convergence_gate(){
  local out="$D/r5-live-measurement"
'''
new = '''r5_service_convergence_gate(){
  local out="$D/r5-live-measurement"
  r5_client_token(){
    case "$1" in
      1) printf '%s' "$R5_TOKEN_1" ;;
      2) printf '%s' "$R5_TOKEN_2" ;;
      3) printf '%s' "$R5_TOKEN_3" ;;
      4) printf '%s' "$R5_TOKEN_4" ;;
      5) printf '%s' "$R5_TOKEN_5" ;;
      *) return 64 ;;
    esac
  }
  for n in R5_TOKEN_1 R5_TOKEN_2 R5_TOKEN_3 R5_TOKEN_4 R5_TOKEN_5; do
    [[ -n "${!n:-}" ]] || { echo "R5_ISOLATED_TOKEN_MISSING:$n" >&2; return 65; }
  done
'''
if s.count(old) != 1:
    raise SystemExit(f'R5_FIVE_SESSION_FUNCTION_ANCHOR:{s.count(old)}')
s = s.replace(old, new, 1)

old = '''    local trial=$1 client=$2 kind=$3 date=$4 cursor=$5 eid=$6 poll_start=$7
    local deadline=$((poll_start+5000)) attempts=0 rows=0 now resp next http body committed commit_ms latency
    resp="$out/t${trial}-c${client}.json"
'''
new = '''    local trial=$1 client=$2 kind=$3 date=$4 cursor=$5 eid=$6 poll_start=$7 token
    local deadline=$((poll_start+5000)) attempts=0 rows=0 now resp next http body committed commit_ms latency
    token=$(r5_client_token "$client")
    resp="$out/t${trial}-c${client}.json"
'''
if s.count(old) != 1:
    raise SystemExit(f'R5_FIVE_SESSION_CLIENT_ANCHOR:{s.count(old)}')
s = s.replace(old, new, 1)

# Only replace the two bearer uses inside r5_client_delta. Status/preflight deliberately use
# the writer token because they are contract setup, while the measured observers use five
# independently authenticated sessions/devices.
start = s.index('  r5_client_delta(){')
end = s.index('\n  # R5 convergence must use a real canonical day mutation.', start)
chunk = s[start:end]
count = chunk.count('-H "Authorization: Bearer $TOKEN"')
if count != 2:
    raise SystemExit(f'R5_FIVE_SESSION_BEARER_ANCHOR:{count}')
chunk = chunk.replace('-H "Authorization: Bearer $TOKEN"', '-H "Authorization: Bearer $token"')
s = s[:start] + chunk + s[end:]

old = "  'status':'PASS','classification':'EXACT_DEPLOYED_SERVICE_REAL_TRANSPORT_5_LOGICAL_CLIENT_FANOUT',\n"
new = "  'status':'PASS','classification':'EXACT_DEPLOYED_SERVICE_REAL_TRANSPORT_5_ISOLATED_AUTH_SESSIONS',\n"
if s.count(old) != 1:
    raise SystemExit(f'R5_FIVE_SESSION_CLASS_ANCHOR:{s.count(old)}')
s = s.replace(old, new, 1)

old = "  'notes':['Same trusted disposable SUPERADMIN fixture is used for all five logical clients; transport routes match the exact Android and Web implementations.','Client topology/orchestrator isolation is independently guarded by the full R5 preprod contract.','Normalized max-day substitutes fresh worst-observed status/delta D1 row costs into the canonical conservative 1540-event structural model.']\n"
new = "  'auth_sessions':{'isolated':True,'pda':3,'web':2,'writer_client':1},\n  'notes':['Five disposable accounts authenticate through the public challenge/login API; clients 1-3 are PDA sessions and clients 4-5 are WEB sessions.','All five measured delta observers are pre-armed before each canonical RESOURCE_CHANGE commit.','Normalized max-day substitutes fresh worst-observed status/delta D1 row costs into the canonical conservative 1540-event structural model.']\n"
if s.count(old) != 1:
    raise SystemExit(f'R5_FIVE_SESSION_NOTE_ANCHOR:{s.count(old)}')
s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('R5_FIVE_ISOLATED_AUTH_SESSIONS_PATCH_PASS')
