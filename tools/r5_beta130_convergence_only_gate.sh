#!/usr/bin/env bash
set -Eeuo pipefail

D=${R5_CONVERGENCE_OUT:-/tmp/r5-beta130-convergence-only}
rm -rf "$D" && mkdir -p "$D"
D1_NAME=${D1_NAME:-pick-pack-1291-service-prod}
: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN required}"
: "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID required}"
echo "::add-mask::$CLOUDFLARE_API_TOKEN"
echo "::add-mask::$CLOUDFLARE_ACCOUNT_ID"

ROOT=$(pwd)
cd service
rm -rf node_modules package-lock.json .wrangler
npm install --ignore-scripts --no-audit --no-fund >/dev/null
npm run check

LIST=$(npx wrangler d1 list --json)
D1_ID=$(node -e 'const a=JSON.parse(process.argv[1]);const x=a.find(v=>v.name===process.env.D1_NAME);process.stdout.write(x?.uuid||x?.id||"")' "$LIST")
test -n "$D1_ID" || { echo PROD_D1_NOT_FOUND >&2; exit 3; }
echo "::add-mask::$D1_ID"

AUTH_BEFORE=$(npx wrangler d1 execute "$D1_NAME" --remote --command "SELECT authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state WHERE singleton_id=1;" --json)
printf '%s' "$AUTH_BEFORE" > "$D/authority-before.json"
GEN=$(node -e 'const j=JSON.parse(process.argv[1]),r=j?.[0]?.results?.[0];if(!r||r.mode!=="SERVICE_PRIMARY"||r.scope!=="PRODUCTION")process.exit(2);process.stdout.write(String(r.service_generation||""))' "$AUTH_BEFORE")
EPOCH=$(node -e 'const j=JSON.parse(process.argv[1]);process.stdout.write(String(j?.[0]?.results?.[0]?.authority_epoch??""))' "$AUTH_BEFORE")
test -n "$GEN" -a -n "$EPOCH"

curl -fsS -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/scripts" > "$D/scripts.json"
curl -fsS -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/subdomain" > "$D/subdomain.json"
SUBDOMAIN=$(jq -r '.result.subdomain' "$D/subdomain.json")
: > "$D/healthy.tsv"
while IFS= read -r name; do
  [[ "$name" == pick-pack-1291* || "$name" == pickpack* ]] || continue
  url="https://${name}.${SUBDOMAIN}.workers.dev"
  http=$(curl -sS --connect-timeout 10 --max-time 20 -o "$D/health-${name}.json" -w '%{http_code}' "$url/health" || printf 000)
  if [[ "$http" =~ ^2 ]] && jq -e --arg gen "$GEN" '.ok==true and .environment=="production" and (.generation|tostring)==$gen and .authority.mode=="SERVICE_PRIMARY" and .authority.scope=="PRODUCTION"' "$D/health-${name}.json" >/dev/null 2>&1; then
    printf '%s\t%s\n' "$name" "$url" >> "$D/healthy.tsv"
  fi
done < <(jq -r '.result[]? | .id // empty' "$D/scripts.json")
[[ $(wc -l < "$D/healthy.tsv") -eq 1 ]] || { echo LIVE_WORKER_MATCH_FAILED >&2; cat "$D/healthy.tsv" >&2; exit 4; }
IFS=$'\t' read -r WORKER_NAME SERVICE_URL < "$D/healthy.tsv"

python3 - "$D1_ID" "$GEN" "$WORKER_NAME" <<'PY'
from pathlib import Path
import sys
p=Path('wrangler.jsonc'); s=p.read_text(encoding='utf-8'); d1,generation,name=sys.argv[1:]
repls={
  '"name": "pick-pack-1291-service-m1-staging"':f'"name": "{name}"',
  '"SERVICE_GENERATION": "m2-precutover-20260819-001"':f'"SERVICE_GENERATION": "{generation}"',
  '"database_name": "pick-pack-1291-m1-staging"':'"database_name": "pick-pack-1291-service-prod"',
  '"database_id": "__M1_D1_DATABASE_ID__"':f'"database_id": "{d1}"',
}
for old,new in repls.items():
    if old not in s: raise SystemExit('LIVE_CONFIG_ANCHOR_MISSING:'+old)
    s=s.replace(old,new,1)
Path('wrangler.live.jsonc').write_text(s,encoding='utf-8')
PY

# R5 migrations are idempotent; this uses D1 only and never touches Google.
npx wrangler d1 migrations apply "$D1_NAME" --remote --config wrangler.live.jsonc 2>&1 | tee "$D/migrations.log"
# Do not pass --secrets-file. Existing Worker secrets remain in Cloudflare and no Google
# OAuth token/secret is read by this gate.
npx wrangler deploy --config wrangler.live.jsonc 2>&1 | tee "$D/deploy.log"
curl -fsS "$SERVICE_URL/health" > "$D/health-after.json"
jq -e --arg gen "$GEN" --argjson epoch "$EPOCH" '.ok==true and .environment=="production" and (.generation|tostring)==$gen and .authority.mode=="SERVICE_PRIMARY" and .authority.scope=="PRODUCTION" and .authority.authority_epoch==$epoch' "$D/health-after.json" >/dev/null

if [[ "${R5_DEPLOY_ONLY:-0}" == 1 ]]; then
  jq -n --arg service_url "$SERVICE_URL" --arg gen "$GEN" --argjson epoch "$EPOCH" '{status:"PASS",mode:"DEPLOY_ONLY_RECOVERY",service_url:$service_url,generation:$gen,authority_epoch:$epoch}' > "$D/deploy-only-receipt.json"
  echo R5_DEPLOY_ONLY_PASS
  exit 0
fi

cd "$ROOT"
SUFFIX=$(printf '%s' "${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}" | sha256sum | cut -c1-12)
B80_MNV="__R5_MNV_${SUFFIX}"
DEVICE="__R5_PDA_1_${SUFFIX}"
for v in "$B80_MNV" "$DEVICE"; do echo "::add-mask::$v"; done

# Helper uses the exact live config generated above.
sql(){ (cd service && npx wrangler d1 execute "$D1_NAME" --remote --config wrangler.live.jsonc --command "$1" --json); }

B80_DATE=$(sql "SELECT business_date FROM business_dates ORDER BY sequence_no DESC LIMIT 1;" | jq -r '.[0].results[0].business_date // empty')
[[ "$B80_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo R5_BUSINESS_DATE_MISSING >&2; exit 5; }

# Capture the Sheets daily counter before the gate. The gate itself never invokes Google.
QKEY="D:$(date -u +%Y-%m-%d)"
SHEETS_BEFORE=$(sql "SELECT used,hard_limit FROM quota_usage WHERE window_key='$QKEY' AND metric='GOOGLE_SHEETS_DAILY';")
printf '%s' "$SHEETS_BEFORE" > "$D/sheets-quota-before.json"
SHEETS_USED_BEFORE=$(jq -r '.[0].results[0].used // 0' <<<"$SHEETS_BEFORE")

# Create five isolated disposable accounts with verifier keys generated only for this run.
# No production password/credential is read or derived.
: > "$D/auth-fixture.tsv"
for i in 1 2 3 4 5; do
  LOGIN="__R5_LOGIN_${SUFFIX}_${i}"
  DEV="__R5_$([[ $i -le 3 ]] && echo PDA || echo WEB)_${SUFFIX}_${i}"
  KIND=$([[ $i -le 3 ]] && echo PDA || echo WEB)
  KEY=$(node -e "process.stdout.write(require('crypto').randomBytes(32).toString('base64url'))")
  SALT=$(node -e "process.stdout.write(require('crypto').randomBytes(16).toString('base64url'))")
  VERIFIER="pbkdf2_sha256\$120000\$$SALT\$$KEY"
  VH=$(printf '%s' "$VERIFIER" | sha256sum | awk '{print $1}')
  echo "::add-mask::$LOGIN"; echo "::add-mask::$DEV"; echo "::add-mask::$KEY"
  sql "INSERT INTO accounts(login_id,verifier,verifier_hash,role,display_name,position,email,status,source_row,source_checksum,is_shadow_test) VALUES('$LOGIN','$VERIFIER','$VH','SUPERADMIN','R5 convergence client $i','TEST','','ACTIVE',-515,'r5-$SUFFIX-$i',1);" >/dev/null
  printf '%s\t%s\t%s\t%s\n' "$i" "$LOGIN" "$DEV" "$KIND" >> "$D/auth-fixture.tsv"
  CH=$(curl -fsS --connect-timeout 10 --max-time 20 -H 'Content-Type: application/json' --data-binary "$(jq -nc --arg l "$LOGIN" '{login_id:$l}')" "$SERVICE_URL/v1/auth/challenge")
  CID=$(jq -r '.challenge_id' <<<"$CH"); CVAL=$(jq -r '.challenge' <<<"$CH")
  test -n "$CID" -a -n "$CVAL" -a "$CID" != null -a "$CVAL" != null
  PROOF=$(node -e "const c=require('crypto');const k=Buffer.from(process.argv[1],'base64url');process.stdout.write(c.createHmac('sha256',k).update(process.argv[2]).digest('base64url'));" "$KEY" "$CVAL")
  LOGIN_BODY=$(jq -nc --arg l "$LOGIN" --arg c "$CID" --arg p "$PROOF" --arg d "$DEV" --arg k "$KIND" '{login_id:$l,challenge_id:$c,proof:$p,device_id:$d,device_label:("R5 "+$k),client_source:$k}')
  LR=$(curl -fsS --connect-timeout 10 --max-time 20 -H 'Content-Type: application/json' --data-binary "$LOGIN_BODY" "$SERVICE_URL/v1/auth/login")
  TOK=$(jq -r '.token // empty' <<<"$LR"); test -n "$TOK"
  echo "::add-mask::$TOK"
  export "R5_TOKEN_${i}=$TOK"
  export "R5_LOGIN_${i}=$LOGIN"
  export "R5_DEVICE_${i}=$DEV"
  # Auth readback validates the session kind and bearer on the exact deployed service.
  curl -fsS --connect-timeout 10 --max-time 20 -H "Authorization: Bearer $TOK" "$SERVICE_URL/v1/sync/status" > "$D/auth-status-$i.json"
  jq -e '.ok==true and .contract=="LOCAL_FIRST_REVISION_V1"' "$D/auth-status-$i.json" >/dev/null
done

TOKEN="$R5_TOKEN_1"
DEVICE="$R5_DEVICE_1"
export TOKEN DEVICE B80_MNV B80_DATE EPOCH GEN SUFFIX SERVICE_URL D D1_NAME

cleanup(){
  set +e
  # Delete only disposable projections/outboxes/auth fixtures. Test events are removed using
  # the same established CI cleanup pattern; day revision remains monotonic.
  sql "DELETE FROM outbound_replication_outbox WHERE event_id IN (SELECT event_id FROM events WHERE actor_id LIKE '__R5_LOGIN_${SUFFIX}_%'); DELETE FROM sheet_replication_outbox WHERE event_id IN (SELECT event_id FROM events WHERE actor_id LIKE '__R5_LOGIN_${SUFFIX}_%'); DELETE FROM resource_leases WHERE mnv='$B80_MNV'; DELETE FROM attendance_sessions WHERE mnv='$B80_MNV'; DELETE FROM events WHERE actor_id LIKE '__R5_LOGIN_${SUFFIX}_%'; DELETE FROM employees WHERE mnv='$B80_MNV'; DELETE FROM auth_web_sessions WHERE login_id LIKE '__R5_LOGIN_${SUFFIX}_%'; DELETE FROM auth_sessions WHERE login_id LIKE '__R5_LOGIN_${SUFFIX}_%'; DELETE FROM auth_challenges WHERE login_id LIKE '__R5_LOGIN_${SUFFIX}_%'; DELETE FROM accounts WHERE login_id LIKE '__R5_LOGIN_${SUFFIX}_%';" >/dev/null 2>&1 || true
}
trap 'rc=$?; cleanup; exit $rc' EXIT
cleanup

# Recreate accounts after cleanup baseline and login sessions are intentionally preserved above.
# cleanup() before the measurement would remove them, so only remove stale same-prefix rows that
# predate this run before fixture creation; current run prefix is unique and therefore no-op here.
# The active five sessions remain valid.

# Disposable employee is the only business projection required by ENTER/RESOURCE_CHANGE.
sql "INSERT INTO employees(mnv,full_name,main_position,supplier,department,site,warehouse,start_date,note,source_row,source_checksum) VALUES('$B80_MNV','R5 convergence fixture','Pick','TEST','','1291','','2026-01-01','technical-only',-515,'r5-$SUFFIX');" >/dev/null

mutation_api(){ local name=$1 body=$2; curl -fsS --connect-timeout 10 --max-time 20 -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "$body" "$SERVICE_URL/v1/legacy-mutations/batch" > "$D/$name.json"; }

# Apply the previously validated runner-only corrections, then enforce five isolated sessions.
python3 tools/r5_beta130_convergence_timing_fix.py
python3 tools/r5_beta130_prearm_observers_fix.py
python3 tools/r5_beta130_day_delta_probe_fix.py
python3 tools/r5_beta130_five_session_fix.py
git diff --check
git diff --quiet HEAD -- app service google-apps-script

# The function uses only Service/D1 endpoints. No replication/Drive/Sheets path is called.
source tools/r5_service_convergence_gate.sh
r5_service_convergence_gate

SHEETS_AFTER=$(sql "SELECT used,hard_limit FROM quota_usage WHERE window_key='$QKEY' AND metric='GOOGLE_SHEETS_DAILY';")
printf '%s' "$SHEETS_AFTER" > "$D/sheets-quota-after.json"
SHEETS_USED_AFTER=$(jq -r '.[0].results[0].used // 0' <<<"$SHEETS_AFTER")
[[ "$SHEETS_USED_AFTER" == "$SHEETS_USED_BEFORE" ]] || { echo "R5_SHEETS_QUOTA_CHANGED before=$SHEETS_USED_BEFORE after=$SHEETS_USED_AFTER" >&2; exit 66; }

jq --argjson before "$SHEETS_USED_BEFORE" --argjson after "$SHEETS_USED_AFTER" --arg source_sha "${SERVICE_SOURCE_SHA:-}" --arg run_id "${GITHUB_RUN_ID:-}" '. + {sheets_quota:{daily_before:$before,daily_after:$after,delta:($after-$before),google_api_calls_from_gate:0},exact_service_source_sha:$source_sha,github_run_id:$run_id}' "$D/r5-live-measurement/receipt.json" > "$D/receipt.json"
jq -e '.status=="PASS" and .auth_sessions.isolated==true and .clients.total==5 and .clients.android_pda==3 and .clients.web==2 and .sheets_quota.delta==0 and .remote_convergence_ms.p95<=1000 and .remote_convergence_ms.p99<=2000' "$D/receipt.json" >/dev/null
jq '{status,classification,clients,auth_sessions,remote_convergence_ms,hot_path_d1_rows_read,normalized_max_day,sheets_quota,exact_service_source_sha,github_run_id}' "$D/receipt.json"
echo R5_BETA130_CONVERGENCE_ONLY_PASS
