#!/usr/bin/env bash
set -Eeuo pipefail

D=/tmp/beta89-service-live
rm -rf "$D" && mkdir -p "$D"
D1_NAME=pick-pack-1291-service-prod
OUTBOUND_SHEET_ID=1tl6har_8vGSVsVlcErfQwjX1YgvN3o-FRG5wQV4VTEM
for n in CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN; do
  test -n "${!n:-}" || { echo "MISSING_REQUIRED_SECRET:$n" >&2; exit 2; }
done
for n in CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN; do echo "::add-mask::${!n}"; done

cd service
rm -rf /tmp/b95-meal-policy && mkdir -p /tmp/b95-meal-policy
npx tsc src/meal_policy.ts --module commonjs --target es2022 --outDir /tmp/b95-meal-policy --skipLibCheck
node - <<'NODE'
const p=require('/tmp/b95-meal-policy/meal_policy.js');
const now=Date.parse('2026-08-29T05:00:00Z');
function sev(shift,minutes){return p.mealAlert([{mnv:'T',shift,status:'PENDING'}],minutes,now).severity}
for(const [m,want] of [[719,'NONE'],[720,'WARNING'],[749,'WARNING'],[750,'SEVERE']]){
  const got=sev('Ca 1',m);if(got!==want)throw new Error('CA1_ALERT_THRESHOLD:'+m+':'+got+':'+want);
}
for(const [m,want] of [[1139,'NONE'],[1140,'WARNING'],[1169,'WARNING'],[1170,'SEVERE']]){
  const got=sev('Ca 2',m);if(got!==want)throw new Error('CA2_ALERT_THRESHOLD:'+m+':'+got+':'+want);
}
let row={mnv:'L',shift:'Ca 1',status:'LATE_EXPECTED',expected_return_at:new Date(now+60000).toISOString()};
if(p.mealStatusView(row,now)!=='LATE_EXPECTED')throw new Error('LATE_NOT_DUE_WRONG');
if(p.mealAlert([row],750,now).severity!=='NONE')throw new Error('LATE_NOT_DUE_ALERTED');
row={...row,expected_return_at:new Date(now-60000).toISOString()};
if(p.mealStatusView(row,now)!=='OVERDUE_LATE')throw new Error('LATE_OVERDUE_NOT_DERIVED');
if(p.mealAlert([row],750,now).severity!=='SEVERE')throw new Error('LATE_OVERDUE_NOT_ALERTED');
console.log('beta95_meal_policy=PASS ca1_1200_1230=PASS ca2_1900_1930=PASS late_due=PASS');
NODE
LIST=$(npx wrangler d1 list --json)
D1_ID=$(node -e 'const a=JSON.parse(process.argv[1]);const x=a.find(v=>v.name===process.env.D1_NAME);process.stdout.write(x?.uuid||x?.id||"")' "$LIST")
test -n "$D1_ID" || { echo PROD_D1_NOT_FOUND >&2; exit 3; }
echo "::add-mask::$D1_ID"
AUTH_BEFORE=$(npx wrangler d1 execute "$D1_NAME" --remote --command "SELECT authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state WHERE singleton_id=1;" --json)
printf '%s' "$AUTH_BEFORE" > "$D/authority-before.json"
GEN=$(node -e 'const j=JSON.parse(process.argv[1]),r=j?.[0]?.results?.[0];if(!r||r.mode!=="SERVICE_PRIMARY"||r.scope!=="PRODUCTION")process.exit(2);process.stdout.write(String(r.service_generation||""))' "$AUTH_BEFORE")
EPOCH=$(node -e 'const j=JSON.parse(process.argv[1]);process.stdout.write(String(j?.[0]?.results?.[0]?.authority_epoch??""))' "$AUTH_BEFORE")
test -n "$GEN" -a -n "$EPOCH"

# Resolve the single LIVE Worker without changing authority/provider.
curl -fsS -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/scripts" > "$D/scripts.json"
curl -fsS -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/subdomain" > "$D/subdomain.json"
SUBDOMAIN=$(jq -r '.result.subdomain' "$D/subdomain.json")
: > "$D/healthy.tsv"
while IFS= read -r name; do
  [[ "$name" == pick-pack-1291* || "$name" == pickpack* ]] || continue
  url="https://${name}.${SUBDOMAIN}.workers.dev"
  http=$(curl -sS --connect-timeout 10 --max-time 20 -o "$D/health-${name}.json" -w '%{http_code}' "$url/health" || printf 000)
  if [[ "$http" =~ ^2 ]] && jq -e --arg gen "$GEN" '.ok==true and .environment=="production" and (.generation|tostring)==$gen and .authority.mode=="SERVICE_PRIMARY" and .authority.scope=="PRODUCTION"' "$D/health-${name}.json" >/dev/null 2>&1; then printf '%s\t%s\n' "$name" "$url" >> "$D/healthy.tsv"; fi
done < <(jq -r '.result[]? | .id // empty' "$D/scripts.json")
[[ $(wc -l < "$D/healthy.tsv") -eq 1 ]] || { echo LIVE_WORKER_MATCH_FAILED >&2; cat "$D/healthy.tsv" >&2; exit 4; }
IFS=$'\t' read -r WORKER_NAME SERVICE_URL < "$D/healthy.tsv"

python3 - "$D1_ID" "$GEN" "$WORKER_NAME" <<'PY'
from pathlib import Path
import sys
p=Path('wrangler.jsonc');s=p.read_text(encoding='utf-8');d1,generation,name=sys.argv[1:]
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

ROLLOVER_REHEARSAL_OUT="$D/d1-rollover-rehearsal" bash ../tools/d1_generation_rehearsal.sh
npx wrangler d1 migrations apply "$D1_NAME" --remote --config wrangler.live.jsonc 2>&1 | tee "$D/migrations.log"
LIMITS=../config/provider_free_limits.json
node - "$LIMITS" <<'NODE'
const fs=require('fs');const p=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));const age=(Date.now()-Date.parse(p.verified_at+'T00:00:00Z'))/86400000;if(!Number.isFinite(age)||age<0||age>Number(p.max_age_days||0))throw new Error('PROVIDER_LIMITS_STALE');if(!p.sources?.cloudflare_d1)throw new Error('PROVIDER_LIMIT_SOURCE_MISSING');
NODE
DB_LIMIT=$(jq -er '.cloudflare_workers_free.d1_database_bytes' "$LIMITS")
ACCOUNT_LIMIT=$(jq -er '.cloudflare_workers_free.d1_account_bytes' "$LIMITS")
npx wrangler d1 execute "$D1_NAME" --remote --config wrangler.live.jsonc --command "UPDATE runtime_config SET config_value='$DB_LIMIT',updated_at=datetime('now') WHERE config_key='D1_DB_QUOTA_BYTES'; UPDATE runtime_config SET config_value='$ACCOUNT_LIMIT',updated_at=datetime('now') WHERE config_key='D1_ACCOUNT_QUOTA_BYTES';" --json > "$D/runtime-quota-config.json"
jq -e 'all(.[];.success==true)' "$D/runtime-quota-config.json" >/dev/null
WRANGLER_CONFIG=wrangler.live.jsonc BACKUP_OUT_DIR="$D/portable-backup" bash ../tools/portable_backup_verify.sh
WRANGLER_CONFIG=wrangler.live.jsonc PROVIDER_LIMITS="$LIMITS" AUTOPILOT_OUT_DIR="$D/d1-autopilot" bash ../tools/d1_generation_autopilot.sh
curl -fsS -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/d1/database/$D1_ID" > "$D/d1-space-before.json"
DB_BYTES=$(jq -er '.result.file_size | numbers' "$D/d1-space-before.json")
CUTOVER_PERCENT=$(npx wrangler d1 execute "$D1_NAME" --remote --config wrangler.live.jsonc --command "SELECT config_value FROM runtime_config WHERE config_key='CUTOVER_DB_PERCENT';" --json | jq -er '.[0].results[0].config_value|tonumber')
DB_PERCENT=$(awk -v b="$DB_BYTES" -v l="$DB_LIMIT" 'BEGIN{printf "%.4f",(b/l)*100}')
awk -v p="$DB_PERCENT" -v c="$CUTOVER_PERCENT" 'BEGIN{exit !(p<c)}' || { echo "D1_CUTOVER_REQUIRED:$DB_PERCENT" >&2; exit 11; }
# Keep Worker OAuth credentials converged with the same CI authority used by the live Drive probe.
# The temporary JSON lives outside the uploaded evidence directory and is deleted on every exit.
npx wrangler secret list --config wrangler.live.jsonc --format json > "$D/worker-secret-names-before.json"
WORKER_SECRETS_FILE=$(mktemp /tmp/pp1291-worker-google-secrets.XXXXXX.json)
chmod 600 "$WORKER_SECRETS_FILE"
node - "$WORKER_SECRETS_FILE" <<'NODE'
const fs=require('fs');
const out=process.argv[2];
const keys=['GOOGLE_OAUTH_CLIENT_ID','GOOGLE_OAUTH_CLIENT_SECRET','GOOGLE_OAUTH_REFRESH_TOKEN'];
const payload={};
for(const k of keys){
  const v=process.env[k]||'';
  if(!v)throw new Error('WORKER_GOOGLE_SECRET_SOURCE_MISSING:'+k);
  payload[k]=v;
}
fs.writeFileSync(out,JSON.stringify(payload),{mode:0o600});
NODE
trap 'rm -f "${WORKER_SECRETS_FILE:-}"' EXIT
npx wrangler deploy --config wrangler.live.jsonc --secrets-file "$WORKER_SECRETS_FILE" 2>&1 | tee "$D/deploy.log"
rm -f "$WORKER_SECRETS_FILE"
WORKER_SECRETS_FILE=""
trap - EXIT
npx wrangler secret list --config wrangler.live.jsonc --format json > "$D/worker-secret-names-after.json"
jq -e '[.[].name] as $n |
  ($n|index("GOOGLE_OAUTH_CLIENT_ID")!=null) and
  ($n|index("GOOGLE_OAUTH_CLIENT_SECRET")!=null) and
  ($n|index("GOOGLE_OAUTH_REFRESH_TOKEN")!=null)' "$D/worker-secret-names-after.json" >/dev/null
curl -fsS "$SERVICE_URL/health" > "$D/health-after.json"
jq -e --arg gen "$GEN" --argjson epoch "$EPOCH" '.ok==true and .environment=="production" and (.generation|tostring)==$gen and .authority.mode=="SERVICE_PRIMARY" and .authority.scope=="PRODUCTION" and .authority.authority_epoch==$epoch' "$D/health-after.json" >/dev/null

SUFFIX=$(printf '%s' "$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT" | sha256sum | cut -c1-10)
LOGIN="__B78_LOGIN_${SUFFIX}"; DEVICE="__B78_DEVICE_${SUFFIX}"; AUTH_SESSION="__B78_AUTH_${SUFFIX}"; VH="b78_${SUFFIX}_vh"
LOC1="__B78_LOC_${SUFFIX}"; LOC2="__B78_LOC2_${SUFFIX}"; DROP_ID="__B78_DROP_${SUFFIX}"; BASE_ID="__B78_BASE_${SUFFIX}"
EV_CREATE="__B78_LOC_CREATE_${SUFFIX}"; EV_UPDATE="__B78_LOC_UPDATE_${SUFFIX}"; EV_DELETE="__B78_LOC_DELETE_${SUFFIX}"
B80_MNV="__B80_MNV_${SUFFIX}"; B80_PDA="__B80_PDA_${SUFFIX}"; B80_ENTER="__B80_ENTER_${SUFFIX}"; B80_MUTATE="__B80_MUTATE_${SUFFIX}"; B80_EXIT="__B80_EXIT_${SUFFIX}"
B95_LATE="__B95_LATE_${SUFFIX}"; B95_CHECK="__B95_CHECK_${SUFFIX}"; B95_DUP_SCAN="__B95_DUP_SCAN_${SUFFIX}"; B95_OTHER_BAD="__B95_OTHER_BAD_${SUFFIX}"; B95_NO_RETURN="__B95_NO_RETURN_${SUFFIX}"; B95_LATE_EDIT="__B95_LATE_EDIT_${SUFFIX}"
B89_PDA2="__B89_PDA2_${SUFFIX}"; B89_PICK="__B89_PICK_${SUFFIX}"; B89_BLOCKED_PICK="__B89_BLOCKED_PICK_${SUFFIX}"
B89_RETURN="__B89_RETURN_${SUFFIX}"; B89_EXCHANGE="__B89_EXCHANGE_${SUFFIX}"; B89_BLOCKED="__B89_BLOCKED_${SUFFIX}"
B91_TABLE="__B91_TABLE_${SUFFIX}"; B91_PACK="__B91_PACK_${SUFFIX}"; B91_BLOCKED_TABLE="__B91_BLOCKED_TABLE_${SUFFIX}"; B91_BLOCKED_PACK="__B91_BLOCKED_PACK_${SUFFIX}"
B91_ADD="__B91_ADD_${SUFFIX}"; B91_RETAIN="__B91_RETAIN_${SUFFIX}"; B91_BLOCKED="__B91_BLOCKED_${SUFFIX}"
B92_USED_PICK="__B92_USED_PICK_${SUFFIX}"; B92_USED_TABLE="__B92_USED_TABLE_${SUFFIX}"; B92_USED_PACK="__B92_USED_PACK_${SUFFIX}"
B92_BLOCKED_TABLE="__B92_BLOCKED_TABLE_${SUFFIX}"; B92_BLOCKED_PACK="__B92_BLOCKED_PACK_${SUFFIX}"; B92_BLOCKED="__B92_BLOCKED_${SUFFIX}"
B99_PROBE="__B99_RESILIENCE_PROBE_${SUFFIX}"
B110_LABOR_START="__B110_LABOR_START_${SUFFIX}"; B110_LABOR_FINISH="__B110_LABOR_FINISH_${SUFFIX}"
B111_LABOR_ID="__B111_LABOR_${SUFFIX}"; B111_LABOR_START="__B111_LABOR_START_${SUFFIX}"; B111_LABOR_FINISH="__B111_LABOR_FINISH_${SUFFIX}"; B111_LABOR_CORRECT="__B111_LABOR_CORRECT_${SUFFIX}"; B111_BAD_START="__B111_BAD_START_${SUFFIX}"; B111_BAD_FINISH="__B111_BAD_FINISH_${SUFFIX}"; B111_HISTORY_DELETE="__B111_HISTORY_DELETE_${SUFFIX}"
B115_LABOR_A="__B115_LABOR_A_${SUFFIX}"; B115_START_A="__B115_START_A_${SUFFIX}"; B115_FINISH_A="__B115_FINISH_A_${SUFFIX}"
B115_LABOR_B="__B115_LABOR_B_${SUFFIX}"; B115_START_B="__B115_START_B_${SUFFIX}"; B115_FINISH_B="__B115_FINISH_B_${SUFFIX}"
B115_OPEN_CONFLICT="__B115_OPEN_CONFLICT_${SUFFIX}"; B115_CAP_CONFLICT="__B115_CAP_CONFLICT_${SUFFIX}"; B115_OVERLAP_CONFLICT="__B115_OVERLAP_CONFLICT_${SUFFIX}"
B115_PRE_EXIT_CORRECT="__B115_PRE_EXIT_CORRECT_${SUFFIX}"; B115_AFTER_EXIT_BAD="__B115_AFTER_EXIT_BAD_${SUFFIX}"; B115_AFTER_EXIT_OK="__B115_AFTER_EXIT_OK_${SUFFIX}"
DOC_CATEGORY_ID=""
DOC_CATEGORY_NAME="__B107_BIEN_BAN_${SUFFIX}"
DOC_CATEGORY_RENAMED="__B108_RENAMED_${SUFFIX}"
DOC_IDEMPOTENCY="__B107_DOC_${SUFFIX}"
DOC_DUP_IDEMPOTENCY="__B107_DOC_DUP_${SUFFIX}"
DOC_SIMILAR_IDEMPOTENCY="__B109_DOC_SIMILAR_${SUFFIX}"
DOC_GROUP_ID="__B110_DOC_GROUP_${SUFFIX}"; DOC2_IDEMPOTENCY="__B110_DOC2_${SUFFIX}"; DOC_BULK_DELETE_IDEMPOTENCY="__B110_DOC_DELETE_${SUFFIX}"
DOC_RENAME_IDEMPOTENCY="__B108_RENAME_${SUFFIX}"
DOC_DELETE_IDEMPOTENCY="__B108_DELETE_${SUFFIX}"
DOC_DRIVE_ID=""; DOC2_DRIVE_ID=""
DOC_BYTES="$D/b107-document.jpg"; DOC2_BYTES="$D/b110-document-page2.jpg"
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
for v in "$LOGIN" "$DEVICE" "$AUTH_SESSION" "$LOC1" "$LOC2" "$DROP_ID" "$BASE_ID" "$B80_MNV" "$B80_PDA" "$B89_PDA2" "$B89_PICK" "$B89_BLOCKED_PICK" "$B91_TABLE" "$B91_PACK" "$B91_BLOCKED_TABLE" "$B91_BLOCKED_PACK" "$B92_USED_PICK" "$B92_USED_TABLE" "$B92_USED_PACK" "$B92_BLOCKED_TABLE" "$B92_BLOCKED_PACK"; do echo "::add-mask::$v"; done
SERVICE_TOKEN_SECRET=$(printf '%s' "$CLOUDFLARE_ACCOUNT_ID|$GOOGLE_OAUTH_CLIENT_SECRET|pick-pack-1291-m2-service-token-v1" | sha256sum | awk '{print $1}')
echo "::add-mask::$SERVICE_TOKEN_SECRET"
TOKEN=$(node - <<'NODE' "$SERVICE_TOKEN_SECRET" "$LOGIN" "$VH" "$AUTH_SESSION" "$DEVICE"
const c=require('crypto');const [secret,l,v,s,d]=process.argv.slice(2);const p={l,r:'SUPERADMIN',v,s,d,c:'PDA'};const enc=Buffer.from(JSON.stringify(p)).toString('base64url');process.stdout.write(enc+'.'+c.createHmac('sha256',Buffer.from(secret)).update(enc).digest('base64url'));
NODE
)
echo "::add-mask::$TOKEN"

sql(){ npx wrangler d1 execute "$D1_NAME" --remote --config wrangler.live.jsonc --command "$1" --json; }
read_api(){ local name=$1 body=$2; curl -fsS --connect-timeout 10 --max-time 20 -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "$body" "$SERVICE_URL/v1/mobile/read" > "$D/$name.json"; }
mutation_api(){ local name=$1 body=$2; curl -fsS --connect-timeout 10 --max-time 20 -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "$body" "$SERVICE_URL/v1/legacy-mutations/batch" > "$D/$name.json"; }
cleanup_document_drive(){
  set +e
  if [[ -n "${DOC_DRIVE_ID:-}" && -n "${GOOGLE_TOKEN:-}" ]]; then
    curl -sS -o /dev/null -X DELETE -H "Authorization: Bearer $GOOGLE_TOKEN" "https://www.googleapis.com/drive/v3/files/$DOC_DRIVE_ID" || true
    DOC_DRIVE_ID=""
  fi
  if [[ -n "${DOC2_DRIVE_ID:-}" && -n "${GOOGLE_TOKEN:-}" ]]; then
    curl -sS -o /dev/null -X DELETE -H "Authorization: Bearer $GOOGLE_TOKEN" "https://www.googleapis.com/drive/v3/files/$DOC2_DRIVE_ID" || true
    DOC2_DRIVE_ID=""
  fi
  set -e
}
cleanup_document_d1(){
  set +e
  if [[ -n "${DOC_CATEGORY_ID:-}" ]]; then
    sql "DELETE FROM document_delete_items WHERE mutation_id IN (SELECT mutation_id FROM document_delete_mutations WHERE actor_id='$LOGIN'); DELETE FROM document_delete_mutations WHERE actor_id='$LOGIN'; DELETE FROM document_audit WHERE actor_id='$LOGIN' OR target_id IN (SELECT document_id FROM document_records WHERE category_id='$DOC_CATEGORY_ID') OR target_id='$DOC_CATEGORY_ID'; DELETE FROM document_records WHERE category_id='$DOC_CATEGORY_ID'; DELETE FROM document_category_mutation_items WHERE mutation_id IN (SELECT mutation_id FROM document_category_mutations WHERE category_id='$DOC_CATEGORY_ID'); DELETE FROM document_category_mutations WHERE category_id='$DOC_CATEGORY_ID'; DELETE FROM document_categories WHERE category_id='$DOC_CATEGORY_ID';" >/dev/null 2>&1 || true
  fi
  set -e
}
cleanup_d1(){
  cleanup_document_d1
  set +e
  sql "DELETE FROM outbound_replication_outbox WHERE event_id IN (SELECT event_id FROM events WHERE actor_id='$LOGIN'); DELETE FROM sheet_replication_outbox WHERE event_id IN (SELECT event_id FROM events WHERE actor_id='$LOGIN'); DELETE FROM outbound_drop_records WHERE record_id='$DROP_ID'; DELETE FROM outbound_locations WHERE location_key LIKE '__B78%'; DELETE FROM resource_daily_consumption WHERE mnv='$B80_MNV'; DELETE FROM resource_leases WHERE mnv='$B80_MNV'; DELETE FROM post_meal_attendance_audit WHERE mnv='$B80_MNV'; DELETE FROM post_meal_attendance WHERE mnv='$B80_MNV'; DELETE FROM labor_sessions WHERE mnv='$B80_MNV'; DELETE FROM attendance_sessions WHERE mnv='$B80_MNV'; DELETE FROM events WHERE actor_id='$LOGIN'; DELETE FROM resource_pack_map WHERE pack_table IN ('$B91_TABLE','$B91_BLOCKED_TABLE','$B92_USED_TABLE','$B92_BLOCKED_TABLE') OR user_pack IN ('$B91_PACK','$B91_BLOCKED_PACK','$B92_USED_PACK','$B92_BLOCKED_PACK'); DELETE FROM resources WHERE resource_id IN ('$B80_PDA','$B89_PDA2','$B89_PICK','$B89_BLOCKED_PICK','$B91_TABLE','$B91_PACK','$B91_BLOCKED_TABLE','$B91_BLOCKED_PACK','$B92_USED_PICK','$B92_USED_TABLE','$B92_USED_PACK','$B92_BLOCKED_TABLE','$B92_BLOCKED_PACK'); DELETE FROM employees WHERE mnv='$B80_MNV'; DELETE FROM auth_sessions WHERE login_id='$LOGIN'; DELETE FROM accounts WHERE login_id='$LOGIN';" >/dev/null 2>&1
  set -e
}
trap 'rc=$?; cleanup_document_drive; cleanup_d1; exit $rc' EXIT
cleanup_d1
sql "INSERT INTO accounts(login_id,verifier,verifier_hash,role,display_name,position,email,status,source_row,source_checksum,is_shadow_test) VALUES('$LOGIN','b78-test','$VH','SUPERADMIN','Beta78 Test','TEST','tam95.supra@gmail.com','ACTIVE',-78,'b78-test',1); INSERT INTO auth_sessions(login_id,session_id,device_id,issued_at) VALUES('$LOGIN','$AUTH_SESSION','$DEVICE','$NOW'); INSERT INTO employees(mnv,full_name,main_position,supplier,site,start_date,source_row,source_checksum) VALUES('$B80_MNV','Beta80 Session Fixture','Pick','IH','1291','2026-01-01',-80,'b80-fixture'); INSERT INTO resources(resource_type,resource_id,status_label,available,metadata_json,source_row,source_checksum) VALUES('PDA','$B80_PDA','Tốt',1,'{}',-80,'b80-fixture'),('PDA','$B89_PDA2','Tốt',1,'{}',-89,'b89-fixture'),('USER_PICK','$B89_PICK','Hoạt động',1,'{}',-89,'b89-fixture'),('USER_PICK','$B89_BLOCKED_PICK','Không khả dụng',0,'{}',-89,'b89-fixture'),('PACK_TABLE','$B91_TABLE','Khả dụng',1,'{}',-91,'b91-fixture'),('USER_PACK','$B91_PACK','Khả dụng',1,'{}',-91,'b91-fixture'),('PACK_TABLE','$B91_BLOCKED_TABLE','Không khả dụng',0,'{}',-91,'b91-fixture'),('USER_PACK','$B91_BLOCKED_PACK','Khả dụng',1,'{}',-91,'b91-fixture'),('USER_PICK','$B92_USED_PICK','Hoạt động',1,'{}',-92,'b92-fixture'),('PACK_TABLE','$B92_USED_TABLE','Khả dụng',1,'{}',-92,'b92-fixture'),('USER_PACK','$B92_USED_PACK','Khả dụng',1,'{}',-92,'b92-fixture'),('PACK_TABLE','$B92_BLOCKED_TABLE','Khả dụng',1,'{}',-92,'b92-fixture'),('USER_PACK','$B92_BLOCKED_PACK','Không khả dụng',0,'{}',-92,'b92-fixture'); INSERT INTO resource_pack_map(pack_table,shift,user_pack,label,available,source_row,source_checksum) VALUES('$B91_TABLE','Ca 2','$B91_PACK','Ca 2-91',1,-91,'b91-fixture'),('$B91_BLOCKED_TABLE','Ca 2','$B91_BLOCKED_PACK','Ca 2-92',1,-91,'b91-fixture'),('$B92_USED_TABLE','Ca 2','$B92_USED_PACK','Ca 2-93',1,-92,'b92-fixture'),('$B92_BLOCKED_TABLE','Ca 2','$B92_BLOCKED_PACK','Ca 2-94',1,-92,'b92-fixture');" >/dev/null

owner_api(){ local path=$1 name=$2 body=$3; curl -fsS --connect-timeout 10 --max-time 20 -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "$body" "$SERVICE_URL$path" > "$D/$name.json"; }
owner_api_slow(){ local path=$1 name=$2 body=$3; curl -fsS --connect-timeout 10 --max-time 60 -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "$body" "$SERVICE_URL$path" > "$D/$name.json"; }

# Beta99 resilience acceptance probe: canonical Service confirmation with no business projection.
PROBE_BODY="{\"events\":[{\"action\":\"resilience_probe\",\"event_id\":\"$B99_PROBE\",\"device_id\":\"$DEVICE\",\"payload\":{\"scenario\":\"CI_SERVICE_DIRECT\",\"occurred_at\":\"$NOW\",\"technical_probe\":true}}]}"
mutation_api b99-probe "$PROBE_BODY"
jq -e --arg e "$B99_PROBE" '.ok==true and .results[0].local_event_id==$e and .results[0].status=="CONFIRMED" and .results[0].canonical_event_id==$e' "$D/b99-probe.json" >/dev/null
mutation_api b99-probe-duplicate "$PROBE_BODY"
jq -e --arg e "$B99_PROBE" '.ok==true and .results[0].local_event_id==$e and .results[0].status=="DUPLICATE" and .results[0].canonical_event_id==$e' "$D/b99-probe-duplicate.json" >/dev/null
PROBE_DB=$(sql "SELECT event_type,entity_type,entity_id,payload_json FROM events WHERE event_id='$B99_PROBE';")
printf '%s' "$PROBE_DB" > "$D/b99-probe-storage.json"
jq -e '.[0].results[0].event_type=="TECHNICAL_RESILIENCE_PROBE" and .[0].results[0].entity_type=="RESILIENCE_PROBE" and ((.[0].results[0].payload_json|fromjson).action=="resilience_probe")' "$D/b99-probe-storage.json" >/dev/null

# Beta80 exact Service v2 contract: ENTER -> SNAPSHOT -> MUTATE -> EXIT, all on disposable D1 fixture.
owner_api /v1/session/enter-v2 b80-enter "{\"mnv\":\"$B80_MNV\",\"shift\":\"Ca 1\",\"positions\":[{\"position_key\":\"PICK\",\"position_label\":\"Pick\"}],\"resources\":[{\"resource_type\":\"PDA\",\"resource_id\":\"$B80_PDA\",\"pda_enter_status\":\"Tốt\"},{\"resource_type\":\"USER_PICK\",\"resource_id\":\"$B89_PICK\"}],\"idempotency_key\":\"$B80_ENTER\"}"
jq -e --arg m "$B80_MNV" --arg p "$B80_PDA" --arg pick "$B89_PICK" '.ok==true and .session.mnv==$m and .session.state=="ACTIVE" and (.resource_assignments|map(select(.resource_type=="PDA" and .resource_id==$p and .state=="ACTIVE"))|length)==1 and (.resource_assignments|map(select(.resource_type=="USER_PICK" and .resource_id==$pick and .state=="ACTIVE"))|length)==1' "$D/b80-enter.json" >/dev/null
B80_SID=$(jq -r '.session.session_id' "$D/b80-enter.json"); B80_VER=$(jq -r '.session.version' "$D/b80-enter.json"); B80_DATE=$(jq -r '.session.business_date' "$D/b80-enter.json")
test -n "$B80_SID" -a "$B80_SID" != null -a "$B80_VER" -gt 0

owner_api /v1/session/resources/snapshot b80-snapshot "{\"session_id\":\"$B80_SID\",\"mnv\":\"$B80_MNV\"}"
jq -e --arg sid "$B80_SID" --arg p "$B80_PDA" '.ok==true and .source=="SERVICE_D1" and .session.session_id==$sid and (.resource_assignments|map(select(.resource_type=="PDA" and .resource_id==$p))|length)==1' "$D/b80-snapshot.json" >/dev/null

owner_api /v1/session/resources/mutate b80-mutate "{\"session_id\":\"$B80_SID\",\"mnv\":\"$B80_MNV\",\"expected_version\":$B80_VER,\"idempotency_key\":\"$B80_MUTATE\",\"audit_note\":\"Beta80 route gate\",\"operations\":[{\"op\":\"UPDATE_SHIFT\",\"shift\":\"Ca 2\"}]}"
jq -e --arg sid "$B80_SID" '.ok==true and .session.session_id==$sid and .session.shift=="Ca 2" and .session.state=="ACTIVE"' "$D/b80-mutate.json" >/dev/null

# Beta89 regression: a same-session USER_PICK may be marked unavailable while leased; PDA return/exchange must still work.
sql "UPDATE resources SET available=0 WHERE resource_type='USER_PICK' AND resource_id='$B89_PICK';" >/dev/null
B89_VER=$(jq -r '.session.version' "$D/b80-mutate.json")
owner_api /v1/session/resources/mutate b89-return "{\"session_id\":\"$B80_SID\",\"mnv\":\"$B80_MNV\",\"expected_version\":$B89_VER,\"idempotency_key\":\"$B89_RETURN\",\"audit_note\":\"Beta89 return PDA\",\"operations\":[{\"op\":\"REMOVE_RESOURCE\",\"resource_type\":\"PDA\",\"resource_id\":\"$B80_PDA\"}]}"
jq -e --arg sid "$B80_SID" --arg pick "$B89_PICK" --arg old "$B80_PDA" '.ok==true and .session.session_id==$sid and ((.session.pda_serial//"")=="") and .session.user_pick==$pick and ((.event.payload_json|fromjson).before.pda_serial==$old) and (((.event.payload_json|fromjson).after.pda_serial//"")=="") and ((.event.payload_json|fromjson).before.user_pick==$pick) and ((.event.payload_json|fromjson).after.user_pick==$pick)' "$D/b89-return.json" >/dev/null
B89_RETURN_EVENT=$(jq -r '.event.event_id' "$D/b89-return.json"); B89_VER=$(jq -r '.session.version' "$D/b89-return.json")
AUDIT=$(sql "SELECT payload_json FROM events WHERE event_id='$B89_RETURN_EVENT';"); printf '%s' "$AUDIT" > "$D/b89-storage-audit.json"
node - <<'NODE' "$D/b89-storage-audit.json" "$B80_PDA" "$B89_PICK"
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),raw=j?.[0]?.results?.[0]?.payload_json,p=JSON.parse(String(raw||'{}'));if(p.before?.pda_serial!==process.argv[3]||String(p.after?.pda_serial||'')!==''||p.before?.user_pick!==process.argv[4]||p.after?.user_pick!==process.argv[4])throw new Error('B89_STORAGE_AUDIT_MISMATCH:'+JSON.stringify(p));
NODE
owner_api /v1/legacy-sync b89-sync "{\"action\":\"sync_day\",\"business_date\":\"$B80_DATE\"}"
jq -e --arg e "$B89_RETURN_EVENT" --arg old "$B80_PDA" --arg pick "$B89_PICK" '[.day.events[]|select(.event_id==$e)][0] as $x | ($x.payload_json|type)=="string" and (($x.payload_json|fromjson).before.pda_serial==$old) and (((($x.payload_json|fromjson).after.pda_serial)//"")=="") and (($x.payload_json|fromjson).before.user_pick==$pick) and (($x.payload_json|fromjson).after.user_pick==$pick)' "$D/b89-sync.json" >/dev/null

owner_api /v1/session/resources/mutate b89-exchange "{\"session_id\":\"$B80_SID\",\"mnv\":\"$B80_MNV\",\"expected_version\":$B89_VER,\"idempotency_key\":\"$B89_EXCHANGE\",\"audit_note\":\"Beta89 exchange PDA\",\"operations\":[{\"op\":\"ADD_RESOURCE\",\"resource_type\":\"PDA\",\"resource_id\":\"$B89_PDA2\"}]}"
jq -e --arg sid "$B80_SID" --arg p "$B89_PDA2" --arg pick "$B89_PICK" '.ok==true and .session.session_id==$sid and .session.pda_serial==$p and .session.user_pick==$pick' "$D/b89-exchange.json" >/dev/null
B89_VER=$(jq -r '.session.version' "$D/b89-exchange.json")
B89_HTTP=$(curl -sS --connect-timeout 10 --max-time 20 -o "$D/b89-blocked.json" -w '%{http_code}' -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "{\"session_id\":\"$B80_SID\",\"mnv\":\"$B80_MNV\",\"expected_version\":$B89_VER,\"idempotency_key\":\"$B89_BLOCKED\",\"audit_note\":\"Beta89 unavailable assignment guard\",\"operations\":[{\"op\":\"REPLACE_RESOURCE\",\"resource_type\":\"USER_PICK\",\"new_resource_id\":\"$B89_BLOCKED_PICK\"}]}" "$SERVICE_URL/v1/session/resources/mutate")
[[ "$B89_HTTP" == 409 ]]; jq -e '.error.code=="USER_PICK_UNAVAILABLE"' "$D/b89-blocked.json" >/dev/null
owner_api /v1/session/resources/snapshot b89-snapshot "{\"session_id\":\"$B80_SID\",\"mnv\":\"$B80_MNV\"}"
jq -e --arg p "$B89_PDA2" --arg pick "$B89_PICK" '.ok==true and .session.pda_serial==$p and .session.user_pick==$pick' "$D/b89-snapshot.json" >/dev/null
LEASES=$(sql "SELECT COUNT(*) n,COUNT(DISTINCT resource_type||'|'||resource_id) d FROM resource_leases WHERE session_id='$B80_SID' AND ((resource_type='PDA' AND resource_id='$B89_PDA2') OR (resource_type='USER_PICK' AND resource_id='$B89_PICK'));"); printf '%s' "$LEASES" > "$D/b89-leases.json"
node -e 'const j=JSON.parse(process.argv[1]),r=j?.[0]?.results?.[0];if(Number(r?.n)!==2||Number(r?.d)!==2)throw new Error("B89_DUPLICATE_LEASE:"+JSON.stringify(r))' "$LEASES"
echo 'beta89_pda_return_exchange=PASS audit_storage_projection=PASS unavailable_new_assignment=PASS duplicate_leases=PASS'

# Beta91 regression: Pack options and submit must use one availability contract.
# Existing session resources may be retained when master availability changes; a new unavailable table remains blocked.
B91_VER=$(jq -r '.session.version' "$D/b89-exchange.json")
owner_api /v1/session/work b91-pack-add "{\"session_id\":\"$B80_SID\",\"idempotency_key\":\"$B91_ADD\",\"shift\":\"Ca 2\",\"pack_table\":\"$B91_TABLE\",\"user_pack\":\"$B91_PACK\",\"resource_note\":\"Beta91 add pack\"}"
jq -e --arg t "$B91_TABLE" --arg p "$B91_PACK" '.ok==true and .session.pack_table==$t and .session.user_pack==$p' "$D/b91-pack-add.json" >/dev/null
sql "UPDATE resources SET available=0 WHERE (resource_type='PACK_TABLE' AND resource_id='$B91_TABLE') OR (resource_type='USER_PACK' AND resource_id='$B91_PACK');" >/dev/null
B91_VER=$(jq -r '.session.version' "$D/b91-pack-add.json")
owner_api /v1/session/work b91-pack-retain "{\"session_id\":\"$B80_SID\",\"idempotency_key\":\"$B91_RETAIN\",\"shift\":\"Ca 2\",\"resource_note\":\"Beta91 retain existing pack\"}"
jq -e --arg t "$B91_TABLE" --arg p "$B91_PACK" '.ok==true and .session.pack_table==$t and .session.user_pack==$p' "$D/b91-pack-retain.json" >/dev/null
read_api b91-options "{\"action\":\"master_options\",\"mnv\":\"$B80_MNV\"}"
jq -e --arg t "$B91_TABLE" --arg p "$B91_PACK" --arg bt "$B91_BLOCKED_TABLE" '.ok==true and ([.pack_tables[]|select(.table==$t and .user_pack==$p)]|length)==1 and ([.pack_tables[]|select(.table==$bt)]|length)==0' "$D/b91-options.json" >/dev/null
B91_VER=$(jq -r '.session.version' "$D/b91-pack-retain.json")
B91_HTTP=$(curl -sS --connect-timeout 10 --max-time 20 -o "$D/b91-blocked.json" -w '%{http_code}' -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "{\"session_id\":\"$B80_SID\",\"idempotency_key\":\"$B91_BLOCKED\",\"shift\":\"Ca 2\",\"pack_table\":\"$B91_BLOCKED_TABLE\",\"user_pack\":\"$B91_BLOCKED_PACK\"}" "$SERVICE_URL/v1/session/work")
[[ "$B91_HTTP" == 409 ]]
jq -e '.error.code=="PACK_TABLE_UNAVAILABLE"' "$D/b91-blocked.json" >/dev/null
echo 'beta91_pack_contract=PASS current_pair_retained=PASS unavailable_new_table_blocked=PASS'

# Beta92: options shown to Android must be the same D1 availability contract used by submit validation.
sql "INSERT OR REPLACE INTO resource_daily_consumption(business_date,resource_type,resource_id,mnv,first_event_id) VALUES('$B80_DATE','USER_PICK','$B92_USED_PICK','__B92_OTHER__','__B92_USED_PICK_EVENT__'),('$B80_DATE','USER_PACK','$B92_USED_PACK','__B92_OTHER__','__B92_USED_PACK_EVENT__');" >/dev/null
read_api b92-options "{\"action\":\"master_options\",\"mnv\":\"$B80_MNV\"}"
jq -e --arg currentPick "$B89_PICK" --arg blockedPick "$B89_BLOCKED_PICK" --arg usedPick "$B92_USED_PICK" --arg currentTable "$B91_TABLE" --arg currentPack "$B91_PACK" --arg usedTable "$B92_USED_TABLE" --arg usedPack "$B92_USED_PACK" --arg blockedTable "$B92_BLOCKED_TABLE" '
  .ok==true and
  (.user_picks|index($currentPick))!=null and
  (.user_picks|index($blockedPick))==null and
  ([.user_picks_reissue[]|select(.id==$usedPick and .duplicate_user==true)]|length)==1 and
  ([.pack_tables[]|select(.table==$currentTable and .user_pack==$currentPack)]|length)==1 and
  ([.pack_tables_reissue[]|select(.table==$usedTable and .user_pack==$usedPack and .duplicate_user==true)]|length)==1 and
  ([.pack_tables[]|select(.table==$blockedTable)]|length)==0 and
  ([.pack_tables_reissue[]|select(.table==$blockedTable)]|length)==0
' "$D/b92-options.json" >/dev/null
read_api b92-active-context "{\"action\":\"employee_context\",\"mnv\":\"$B80_MNV\",\"include_options\":true}"
jq -e --arg currentPick "$B89_PICK" --arg usedPick "$B92_USED_PICK" '.ok==true and .state=="ACTIVE" and .options.ok==true and (.options.user_picks|index($currentPick))!=null and ([.options.user_picks_reissue[]|select(.id==$usedPick)]|length)==1' "$D/b92-active-context.json" >/dev/null
B92_HTTP=$(curl -sS --connect-timeout 10 --max-time 20 -o "$D/b92-blocked-user-pack.json" -w '%{http_code}' -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "{\"session_id\":\"$B80_SID\",\"idempotency_key\":\"$B92_BLOCKED\",\"shift\":\"Ca 2\",\"pack_table\":\"$B92_BLOCKED_TABLE\",\"user_pack\":\"$B92_BLOCKED_PACK\"}" "$SERVICE_URL/v1/session/work")
[[ "$B92_HTTP" == 409 ]]
jq -e '.error.code=="USER_PACK_UNAVAILABLE"' "$D/b92-blocked-user-pack.json" >/dev/null
echo 'beta92_authoritative_options=PASS active_options=PASS user_pick_unavailable_filtered=PASS user_pack_unavailable_filtered=PASS reissue_authoritative=PASS'


# Beta95: post-meal attendance uses the canonical ledger, current-day write only, idempotent scan and 14-day read window.
mutation_api b95-other-bad "{\"events\":[{\"action\":\"meal_status\",\"event_id\":\"$B95_OTHER_BAD\",\"business_date\":\"$B80_DATE\",\"payload\":{\"mnv\":\"$B80_MNV\",\"status\":\"NO_RETURN\",\"reason_code\":\"Khác\",\"reason_note\":\"\"}}]}"
jq -e '.ok==true and .results[0].status=="REJECTED" and .results[0].error_code=="MEAL_REASON_NOTE_REQUIRED"' "$D/b95-other-bad.json" >/dev/null

mutation_api b95-no-return "{\"events\":[{\"action\":\"meal_status\",\"event_id\":\"$B95_NO_RETURN\",\"business_date\":\"$B80_DATE\",\"payload\":{\"mnv\":\"$B80_MNV\",\"status\":\"NO_RETURN\",\"reason_code\":\"Có việc cá nhân\"}}]}"
jq -e '.ok==true and .results[0].status=="CONFIRMED"' "$D/b95-no-return.json" >/dev/null

B95_EXPECTED1=$(date -u -d '+2 hour' +%Y-%m-%dT%H:%M:%SZ)
mutation_api b95-late "{\"events\":[{\"action\":\"meal_status\",\"event_id\":\"$B95_LATE\",\"business_date\":\"$B80_DATE\",\"payload\":{\"mnv\":\"$B80_MNV\",\"status\":\"LATE_EXPECTED\",\"reason_code\":\"Xin vào muộn\",\"expected_return_at\":\"$B95_EXPECTED1\"}}]}"
jq -e '.ok==true and .results[0].status=="CONFIRMED"' "$D/b95-late.json" >/dev/null

B95_EXPECTED2=$(date -u -d '+1 hour' +%Y-%m-%dT%H:%M:%SZ)
mutation_api b95-late-edit "{\"events\":[{\"action\":\"meal_status\",\"event_id\":\"$B95_LATE_EDIT\",\"business_date\":\"$B80_DATE\",\"payload\":{\"mnv\":\"$B80_MNV\",\"status\":\"LATE_EXPECTED\",\"reason_code\":\"Xin vào muộn\",\"expected_return_at\":\"$B95_EXPECTED2\"}}]}"
jq -e '.ok==true and .results[0].status=="CONFIRMED"' "$D/b95-late-edit.json" >/dev/null
mutation_api b95-late-edit-dup "{\"events\":[{\"action\":\"meal_status\",\"event_id\":\"$B95_LATE_EDIT\",\"business_date\":\"$B80_DATE\",\"payload\":{\"mnv\":\"$B80_MNV\",\"status\":\"LATE_EXPECTED\",\"reason_code\":\"Xin vào muộn\",\"expected_return_at\":\"$B95_EXPECTED2\"}}]}"
jq -e '.ok==true and .results[0].status=="DUPLICATE"' "$D/b95-late-edit-dup.json" >/dev/null
read_api b95-list "{\"action\":\"meal_attendance_list\",\"business_date\":\"$B80_DATE\"}"
jq -e --arg m "$B80_MNV" --arg t "$B95_EXPECTED2" '.ok==true and .retention_days==14 and .current_day==true and ([.items[]|select(.mnv==$m and .status=="LATE_EXPECTED" and .expected_return_at==$t)]|length)==1' "$D/b95-list.json" >/dev/null
B95_EDIT_AUDIT=$(sql "SELECT before_json,after_json FROM post_meal_attendance_audit WHERE event_id='$B95_LATE_EDIT';")
node - <<'NODE' "$B95_EDIT_AUDIT" "$B95_EXPECTED1" "$B95_EXPECTED2"
const j=JSON.parse(process.argv[2]),r=j?.[0]?.results?.[0],b=JSON.parse(String(r?.before_json||'{}')),a=JSON.parse(String(r?.after_json||'{}'));
if(b.expected_return_at!==process.argv[3]||a.expected_return_at!==process.argv[4])throw new Error('B95_LATE_EDIT_AUDIT_MISMATCH:'+JSON.stringify({b,a}));
NODE

mutation_api b95-check "{\"events\":[{\"action\":\"meal_checkin\",\"event_id\":\"$B95_CHECK\",\"business_date\":\"$B80_DATE\",\"payload\":{\"mnv\":\"$B80_MNV\"}}]}"
jq -e '.ok==true and .results[0].status=="CONFIRMED"' "$D/b95-check.json" >/dev/null
mutation_api b95-check-same-event "{\"events\":[{\"action\":\"meal_checkin\",\"event_id\":\"$B95_CHECK\",\"business_date\":\"$B80_DATE\",\"payload\":{\"mnv\":\"$B80_MNV\"}}]}"
jq -e '.ok==true and .results[0].status=="DUPLICATE"' "$D/b95-check-same-event.json" >/dev/null
mutation_api b95-check-distinct "{\"events\":[{\"action\":\"meal_checkin\",\"event_id\":\"$B95_DUP_SCAN\",\"business_date\":\"$B80_DATE\",\"payload\":{\"mnv\":\"$B80_MNV\"}}]}"
jq -e '.ok==true and .results[0].status=="REVIEW_REQUIRED" and .results[0].error_code=="MEAL_ALREADY_CHECKED_IN"' "$D/b95-check-distinct.json" >/dev/null
read_api b95-list-after "{\"action\":\"meal_attendance_list\",\"business_date\":\"$B80_DATE\"}"
jq -e --arg m "$B80_MNV" --arg t "$B95_EXPECTED2" '([.items[]|select(.mnv==$m)][0]) as $x | $x.status=="CHECKED_IN" and ($x.actual_return_at|length)>10 and $x.reason_code=="Xin vào muộn" and $x.expected_return_at==$t' "$D/b95-list-after.json" >/dev/null
B95_COUNTS=$(sql "SELECT (SELECT COUNT(*) FROM events WHERE event_id IN ('$B95_NO_RETURN','$B95_LATE','$B95_LATE_EDIT','$B95_CHECK')) events,(SELECT COUNT(*) FROM post_meal_attendance_audit WHERE mnv='$B80_MNV' AND business_date='$B80_DATE') audits;")
node -e 'const j=JSON.parse(process.argv[1]),x=j?.[0]?.results?.[0];if(Number(x?.events)!==4||Number(x?.audits)!==4)throw new Error("B95_LEDGER_AUDIT_MISMATCH:"+JSON.stringify(x))' "$B95_COUNTS"
B95_FLOOR=$(date -u -d "$B80_DATE -13 days" +%Y-%m-%d)
read_api b95-history-floor "{\"action\":\"meal_attendance_list\",\"business_date\":\"$B95_FLOOR\"}"
jq -e '.ok==true and .retention_days==14 and .current_day==false' "$D/b95-history-floor.json" >/dev/null
B95_TOO_OLD=$(date -u -d "$B80_DATE -14 days" +%Y-%m-%d)
B95_OLD_HTTP=$(curl -sS --connect-timeout 10 --max-time 20 -o "$D/b95-too-old.json" -w '%{http_code}' -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "{\"action\":\"meal_attendance_list\",\"business_date\":\"$B95_TOO_OLD\"}" "$SERVICE_URL/v1/mobile/read")
[[ "$B95_OLD_HTTP" == 403 ]]; jq -e '.error.code=="MEAL_DATE_OUTSIDE_14_DAY_WINDOW"' "$D/b95-too-old.json" >/dev/null
echo 'beta95_meal_attendance=PASS current_write=PASS reasons=PASS idempotency=PASS late_edit_audit=PASS history_14d=PASS'

# Beta110: explicit labor time range + OPEN labor blocks exit until completed.
B110_LABOR_START_AT=$(jq -r '.session.enter_at' "$D/b80-enter.json")
test -n "$B110_LABOR_START_AT" -a "$B110_LABOR_START_AT" != null
B110_START_BODY=$(jq -nc --arg ev "$B110_LABOR_START" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg mnv "$B80_MNV" --arg at "$B110_LABOR_START_AT" '{
  events:[{action:"labor_start",event_id:$ev,device_id:$dev,business_date:$date,payload:{mnv:$mnv,shift:"Ca 2",labor_type:"Beta110 CI",start_at:$at,deduct_staff:false,note:""}}]
}')
mutation_api b110-labor-start "$B110_START_BODY"
jq -e --arg e "$B110_LABOR_START" '.ok==true and .results[0].local_event_id==$e and .results[0].status=="CONFIRMED"' "$D/b110-labor-start.json" >/dev/null
B110_LABOR_DB=$(sql "SELECT labor_id,state,start_at,end_at FROM labor_sessions WHERE labor_id='$B110_LABOR_START';")
printf '%s' "$B110_LABOR_DB" > "$D/b110-labor-open-db.json"
node -e 'const j=JSON.parse(process.argv[1]),r=j?.[0]?.results?.[0];if(!r||r.state!=="OPEN"||r.start_at!==process.argv[2]||r.end_at!=null)throw new Error("B110_LABOR_OPEN_MISMATCH:"+JSON.stringify(r))' "$B110_LABOR_DB" "$B110_LABOR_START_AT"

B110_EXIT_BLOCK_HTTP=$(curl -sS --connect-timeout 10 --max-time 20 -o "$D/b110-exit-blocked.json" -w '%{http_code}' -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "{\"session_id\":\"$B80_SID\",\"mnv\":\"$B80_MNV\",\"pda_exit_status\":\"Tốt\",\"idempotency_key\":\"__B110_EXIT_BLOCK_$SUFFIX\"}" "$SERVICE_URL/v1/session/exit-v2")
[[ "$B110_EXIT_BLOCK_HTTP" == 409 ]]
jq -e '.error.code=="OPEN_LABOR_BLOCKS_EXIT"' "$D/b110-exit-blocked.json" >/dev/null

B110_LABOR_END_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
B110_FINISH_BODY=$(jq -nc --arg ev "$B110_LABOR_FINISH" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg mnv "$B80_MNV" --arg at "$B110_LABOR_END_AT" '{
  events:[{action:"labor_finish",event_id:$ev,device_id:$dev,business_date:$date,payload:{mnv:$mnv,end_at:$at,note:""}}]
}')
mutation_api b110-labor-finish "$B110_FINISH_BODY"
jq -e --arg e "$B110_LABOR_FINISH" '.ok==true and .results[0].local_event_id==$e and .results[0].status=="CONFIRMED"' "$D/b110-labor-finish.json" >/dev/null
B110_LABOR_DONE_DB=$(sql "SELECT state,start_at,end_at FROM labor_sessions WHERE labor_id='$B110_LABOR_START';")
printf '%s' "$B110_LABOR_DONE_DB" > "$D/b110-labor-complete-db.json"
node -e 'const j=JSON.parse(process.argv[1]),r=j?.[0]?.results?.[0];if(!r||r.state!=="COMPLETED"||r.start_at!==process.argv[2]||r.end_at!==process.argv[3])throw new Error("B110_LABOR_COMPLETE_MISMATCH:"+JSON.stringify(r))' "$B110_LABOR_DONE_DB" "$B110_LABOR_START_AT" "$B110_LABOR_END_AT"
echo 'beta110_labor_time_range=PASS open_exit_block=PASS completed_range=PASS'

# Beta111: exact session/business_date/labor_id authority, daily OPEN+COMPLETED list, correction, stale-context rejection.
B111_START_AT="$B110_LABOR_END_AT"
B111_START_BODY=$(jq -nc --arg ev "$B111_LABOR_START" --arg labor "$B111_LABOR_ID" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg sid "$B80_SID" --arg mnv "$B80_MNV" --arg at "$B111_START_AT" '{
  events:[{action:"labor_start",event_id:$ev,device_id:$dev,business_date:$date,payload:{labor_id:$labor,session_id:$sid,mnv:$mnv,shift:"Ca 2",labor_type:"Beta111 exact session CI",start_at:$at,deduct_staff:false,note:""}}]
}')
mutation_api b111-labor-start "$B111_START_BODY"
jq -e --arg e "$B111_LABOR_START" '.ok==true and .results[0].local_event_id==$e and .results[0].status=="CONFIRMED"' "$D/b111-labor-start.json" >/dev/null

read_api b111-context-open "$(jq -nc --arg mnv "$B80_MNV" --arg sid "$B80_SID" '{action:"employee_context",mnv:$mnv,session_id:$sid,include_labor:true,include_options:false}')"
jq -e --arg sid "$B80_SID" --arg labor "$B111_LABOR_ID" --arg date "$B80_DATE" '.ok==true and .source=="SERVICE_D1" and .business_date==$date and .session.session_id==$sid and .state=="ACTIVE" and .active_labor.labor_id==$labor and .active_labor.state=="OPEN"' "$D/b111-context-open.json" >/dev/null

read_api b111-labor-list-open "$(jq -nc --arg date "$B80_DATE" '{action:"labor_list",business_date:$date}')"
jq -e --arg labor "$B111_LABOR_ID" '([.items[]|select(.labor_id==$labor and .state=="OPEN")]|length)==1 and .open_count>=1' "$D/b111-labor-list-open.json" >/dev/null

B111_EXIT_BLOCK_HTTP=$(curl -sS --connect-timeout 10 --max-time 20 -o "$D/b111-exit-blocked.json" -w '%{http_code}' -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "$(jq -nc --arg sid "$B80_SID" --arg mnv "$B80_MNV" --arg idem "__B111_EXIT_BLOCK_$SUFFIX" '{session_id:$sid,mnv:$mnv,pda_exit_status:"Tốt",idempotency_key:$idem}')" "$SERVICE_URL/v1/session/exit-v2")
[[ "$B111_EXIT_BLOCK_HTTP" == 409 ]]
jq -e '.error.code=="OPEN_LABOR_BLOCKS_EXIT"' "$D/b111-exit-blocked.json" >/dev/null


sleep 2
B111_END_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
B111_FINISH_BODY=$(jq -nc --arg ev "$B111_LABOR_FINISH" --arg labor "$B111_LABOR_ID" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg sid "$B80_SID" --arg mnv "$B80_MNV" --arg start "$B111_START_AT" --arg end "$B111_END_AT" '{
  events:[{action:"labor_finish",event_id:$ev,device_id:$dev,business_date:$date,payload:{labor_id:$labor,session_id:$sid,mnv:$mnv,start_at:$start,end_at:$end,note:"Beta111 done"}}]
}')
mutation_api b111-labor-finish "$B111_FINISH_BODY"
jq -e --arg e "$B111_LABOR_FINISH" '.ok==true and .results[0].local_event_id==$e and .results[0].status=="CONFIRMED"' "$D/b111-labor-finish.json" >/dev/null

# Stale-session rejection is tested after closing the current interval so Beta113 max-one-OPEN does not mask the intended invariant.
B111_BAD_START_BODY=$(jq -nc --arg ev "$B111_BAD_START" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg mnv "$B80_MNV" --arg at "$B111_START_AT" '{
  events:[{action:"labor_start",event_id:$ev,device_id:$dev,business_date:$date,payload:{labor_id:("__BAD_LABOR_"+$ev),session_id:"__MISSING_SESSION__",mnv:$mnv,shift:"Ca 2",labor_type:"Beta111 stale session",start_at:$at,deduct_staff:false,note:""}}]
}')
mutation_api b111-bad-session-start "$B111_BAD_START_BODY"
jq -e '.ok==true and .results[0].status=="REVIEW_REQUIRED" and .results[0].error_code=="ATTENDANCE_NOT_ACTIVE"' "$D/b111-bad-session-start.json" >/dev/null


read_api b111-context-done "$(jq -nc --arg mnv "$B80_MNV" --arg sid "$B80_SID" '{action:"employee_context",mnv:$mnv,session_id:$sid,include_labor:true,include_options:false}')"
jq -e --arg sid "$B80_SID" '.ok==true and .session.session_id==$sid and .state=="ACTIVE" and .active_labor==null' "$D/b111-context-done.json" >/dev/null
read_api b111-labor-list-done "$(jq -nc --arg date "$B80_DATE" '{action:"labor_list",business_date:$date}')"
jq -e --arg labor "$B111_LABOR_ID" '([.items[]|select(.labor_id==$labor and .state=="COMPLETED")]|length)==1 and .completed_count>=1' "$D/b111-labor-list-done.json" >/dev/null

B111_CORRECT_START=$(date -u -d "$B111_START_AT + 1 second" +%Y-%m-%dT%H:%M:%SZ)
B111_CORRECT_BODY=$(jq -nc --arg ev "$B111_LABOR_CORRECT" --arg labor "$B111_LABOR_ID" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg sid "$B80_SID" --arg mnv "$B80_MNV" --arg start "$B111_CORRECT_START" --arg end "$B111_END_AT" '{
  events:[{action:"labor_finish",event_id:$ev,device_id:$dev,business_date:$date,payload:{labor_id:$labor,session_id:$sid,mnv:$mnv,start_at:$start,end_at:$end,correction:true,note:"Beta111 corrected"}}]
}')
mutation_api b111-labor-correct "$B111_CORRECT_BODY"
jq -e --arg e "$B111_LABOR_CORRECT" '.ok==true and .results[0].local_event_id==$e and .results[0].status=="CONFIRMED"' "$D/b111-labor-correct.json" >/dev/null
B111_CORRECT_DB=$(sql "SELECT state,start_at,end_at,note,version FROM labor_sessions WHERE labor_id='$B111_LABOR_ID';")
printf '%s' "$B111_CORRECT_DB" > "$D/b111-labor-correct-db.json"
node -e 'const j=JSON.parse(process.argv[1]),r=j?.[0]?.results?.[0];if(!r||r.state!=="COMPLETED"||r.start_at!==process.argv[2]||r.end_at!==process.argv[3]||r.note!=="Beta111 corrected"||Number(r.version)<3)throw new Error("B111_LABOR_CORRECTION_MISMATCH:"+JSON.stringify(r))' "$B111_CORRECT_DB" "$B111_CORRECT_START" "$B111_END_AT"

B111_BAD_FINISH_BODY=$(jq -nc --arg ev "$B111_BAD_FINISH" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg sid "$B80_SID" --arg mnv "$B80_MNV" --arg end "$B111_END_AT" '{
  events:[{action:"labor_finish",event_id:$ev,device_id:$dev,business_date:$date,payload:{labor_id:("__MISSING_LABOR_"+$ev),session_id:$sid,mnv:$mnv,end_at:$end,note:"stale"}}]
}')
mutation_api b111-bad-labor-finish "$B111_BAD_FINISH_BODY"
jq -e '.ok==true and .results[0].status=="REVIEW_REQUIRED" and .results[0].error_code=="LABOR_NOT_OPEN"' "$D/b111-bad-labor-finish.json" >/dev/null

owner_api /v1/history/delete b111-history-delete "$(jq -nc --arg ev "$B99_PROBE" --arg idem "$B111_HISTORY_DELETE" '{event_ids:[$ev],idempotency_key:$idem,reason:"Beta111 canonical delete regression"}')"
jq -e --arg ev "$B99_PROBE" '.ok==true and .deleted_count==1 and (.target_event_ids|index($ev))!=null' "$D/b111-history-delete.json" >/dev/null
B111_HISTORY_MISSING_HTTP=$(curl -sS --connect-timeout 10 --max-time 20 -o "$D/b111-history-delete-missing.json" -w '%{http_code}' -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "$(jq -nc --arg idem "__B111_HISTORY_MISSING_$SUFFIX" '{event_ids:["__LOCAL_ONLY_NONCANONICAL__"],idempotency_key:$idem,reason:"missing"}')" "$SERVICE_URL/v1/history/delete")
[[ "$B111_HISTORY_MISSING_HTTP" == 404 ]]
jq -e '.error.code=="HISTORY_DELETE_TARGET_NOT_FOUND"' "$D/b111-history-delete-missing.json" >/dev/null

echo 'beta111_labor_exact_session=PASS exact_context=PASS daily_open_done=PASS open_exit_redirect_contract=PASS stale_session_reject=PASS stale_labor_reject=PASS completed_correction=PASS history_delete_canonical=PASS history_missing_404=PASS'

# Beta115: future scheduled end, strict cap/overlap/exit reconciliation, boolean deduction and exact MNV+shift report movement.
owner_api /v1/legacy-sync b115-report-before "$(jq -nc --arg date "$B80_DATE" '{action:"sync_day",business_date:$date}')"
B115_AT="$B111_END_AT"
B115_START_A_BODY=$(jq -nc --arg ev "$B115_START_A" --arg labor "$B115_LABOR_A" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg sid "$B80_SID" --arg mnv "$B80_MNV" --arg at "$B115_AT" '{
  events:[{action:"labor_start",event_id:$ev,device_id:$dev,business_date:$date,payload:{labor_id:$labor,session_id:$sid,mnv:$mnv,shift:"Ca 2",labor_type:"Beta115 Support A",start_at:$at,deduct_staff:true,note:"boolean true"}}]
}')
mutation_api b115-labor-start-a "$B115_START_A_BODY"
jq -e --arg e "$B115_START_A" '.ok==true and .results[0].local_event_id==$e and .results[0].status=="CONFIRMED"' "$D/b115-labor-start-a.json" >/dev/null
B115_DEDUCT_DB=$(sql "SELECT labor_id,state,deduct_staff FROM labor_sessions WHERE labor_id='$B115_LABOR_A';")
printf '%s' "$B115_DEDUCT_DB" > "$D/b115-deduct-boolean-db.json"
node -e 'const j=JSON.parse(process.argv[1]),r=j?.[0]?.results?.[0];if(!r||r.state!=="OPEN"||Number(r.deduct_staff)!==1)throw new Error("B115_BOOLEAN_DEDUCT_NOT_PERSISTED:"+JSON.stringify(r))' "$B115_DEDUCT_DB"

B115_OPEN_BODY=$(jq -nc --arg ev "$B115_OPEN_CONFLICT" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg sid "$B80_SID" --arg mnv "$B80_MNV" --arg at "$B115_AT" '{
  events:[{action:"labor_start",event_id:$ev,device_id:$dev,business_date:$date,payload:{labor_id:("__OPEN_"+$ev),session_id:$sid,mnv:$mnv,shift:"Ca 2",labor_type:"Beta115 second open",start_at:$at,deduct_staff:false,note:""}}]
}')
mutation_api b115-open-conflict "$B115_OPEN_BODY"
jq -e '.ok==true and .results[0].status=="REVIEW_REQUIRED" and .results[0].error_code=="LABOR_OTHER_INTERVAL_OPEN"' "$D/b115-open-conflict.json" >/dev/null

B115_FINISH_A_BODY=$(jq -nc --arg ev "$B115_FINISH_A" --arg labor "$B115_LABOR_A" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg sid "$B80_SID" --arg mnv "$B80_MNV" --arg at "$B115_AT" '{
  events:[{action:"labor_finish",event_id:$ev,device_id:$dev,business_date:$date,payload:{labor_id:$labor,session_id:$sid,mnv:$mnv,start_at:$at,end_at:$at,note:"Beta115 A done"}}]
}')
mutation_api b115-labor-finish-a "$B115_FINISH_A_BODY"
jq -e '.ok==true and .results[0].status=="CONFIRMED"' "$D/b115-labor-finish-a.json" >/dev/null

B115_START_B_BODY=$(jq -nc --arg ev "$B115_START_B" --arg labor "$B115_LABOR_B" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg sid "$B80_SID" --arg mnv "$B80_MNV" --arg at "$B115_AT" '{
  events:[{action:"labor_start",event_id:$ev,device_id:$dev,business_date:$date,payload:{labor_id:$labor,session_id:$sid,mnv:$mnv,shift:"Ca 2",labor_type:"Beta115 Support B",start_at:$at,deduct_staff:true,note:"second deducted interval"}}]
}')
mutation_api b115-labor-start-b "$B115_START_B_BODY"
jq -e '.ok==true and .results[0].status=="CONFIRMED"' "$D/b115-labor-start-b.json" >/dev/null

B115_SHIFT_END="${B80_DATE}T15:00:00Z"
B115_AFTER_CAP="${B80_DATE}T15:15:00Z"
node -e 'if(Date.parse(process.argv[1])<=Date.now()+60000)throw new Error("B115_SCHEDULED_END_NOT_FUTURE_FOR_LIVE_GATE")' "$B115_SHIFT_END"
B115_CAP_BODY=$(jq -nc --arg ev "$B115_CAP_CONFLICT" --arg labor "$B115_LABOR_B" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg sid "$B80_SID" --arg mnv "$B80_MNV" --arg start "$B115_AT" --arg end "$B115_AFTER_CAP" '{
  events:[{action:"labor_finish",event_id:$ev,device_id:$dev,business_date:$date,payload:{labor_id:$labor,session_id:$sid,mnv:$mnv,start_at:$start,end_at:$end,note:"beyond shift cap"}}]
}')
mutation_api b115-cap-conflict "$B115_CAP_BODY"
jq -e '.ok==true and .results[0].status=="REVIEW_REQUIRED" and .results[0].error_code=="LABOR_END_AFTER_SHIFT_OR_EXIT"' "$D/b115-cap-conflict.json" >/dev/null

B115_FINISH_B_BODY=$(jq -nc --arg ev "$B115_FINISH_B" --arg labor "$B115_LABOR_B" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg sid "$B80_SID" --arg mnv "$B80_MNV" --arg start "$B115_AT" --arg end "$B115_SHIFT_END" '{
  events:[{action:"labor_finish",event_id:$ev,device_id:$dev,business_date:$date,payload:{labor_id:$labor,session_id:$sid,mnv:$mnv,start_at:$start,end_at:$end,note:"future scheduled end"}}]
}')
mutation_api b115-labor-finish-b "$B115_FINISH_B_BODY"
jq -e '.ok==true and .results[0].status=="CONFIRMED"' "$D/b115-labor-finish-b.json" >/dev/null
B115_MULTI_DB=$(sql "SELECT COUNT(*) AS n,SUM(deduct_staff) AS deducted,SUM(CASE WHEN state='COMPLETED' THEN 1 ELSE 0 END) AS completed FROM labor_sessions WHERE labor_id IN ('$B115_LABOR_A','$B115_LABOR_B');")
printf '%s' "$B115_MULTI_DB" > "$D/b115-multi-deduct-db.json"
node -e 'const j=JSON.parse(process.argv[1]),r=j?.[0]?.results?.[0];if(Number(r?.n)!==2||Number(r?.deducted)!==2||Number(r?.completed)!==2)throw new Error("B115_MULTI_DEDUCT_MISMATCH:"+JSON.stringify(r))' "$B115_MULTI_DB"

B115_OVERLAP_BODY=$(jq -nc --arg ev "$B115_OVERLAP_CONFLICT" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg sid "$B80_SID" --arg mnv "$B80_MNV" --arg at "$B115_AT" '{
  events:[{action:"labor_start",event_id:$ev,device_id:$dev,business_date:$date,payload:{labor_id:("__OVERLAP_"+$ev),session_id:$sid,mnv:$mnv,shift:"Ca 2",labor_type:"Beta115 overlap",start_at:$at,deduct_staff:false,note:""}}]
}')
mutation_api b115-overlap-conflict "$B115_OVERLAP_BODY"
jq -e '.ok==true and .results[0].status=="REVIEW_REQUIRED" and .results[0].error_code=="LABOR_INTERVAL_OVERLAP"' "$D/b115-overlap-conflict.json" >/dev/null

owner_api /v1/legacy-sync b115-report-after "$(jq -nc --arg date "$B80_DATE" '{action:"sync_day",business_date:$date}')"
node - "$D/b115-report-before.json" "$D/b115-report-after.json" <<'NODE'
const fs=require('fs'),before=JSON.parse(fs.readFileSync(process.argv[2],'utf8')).day.report.reports.ca2,after=JSON.parse(fs.readFileSync(process.argv[3],'utf8')).day.report.reports.ca2;
const row=(matrix,key,value)=>(matrix.rows||[]).find(x=>x[key]===value)||{counts:{},total:0};
const bSupport=before.support||{totals:{},rows:[],total:0},aSupport=after.support||{totals:{},rows:[],total:0};
const bSupportIH=Number(bSupport.totals?.IH||0),aSupportIH=Number(aSupport.totals?.IH||0);
const bPicker=Number(row(before.manpower,'position','Picker').counts?.IH||0),aPicker=Number(row(after.manpower,'position','Picker').counts?.IH||0);
const bOld=Number(row(before.picker_tenure,'label','Nhân sự cũ').counts?.IH||0),aOld=Number(row(after.picker_tenure,'label','Nhân sự cũ').counts?.IH||0);
if(Number(aSupport.total)!==Number(bSupport.total)+1||aSupportIH!==bSupportIH+1||aPicker!==bPicker-1||aOld!==bOld-1||Number(aSupport.unique_staff)!==Number(bSupport.unique_staff)+1||row(aSupport,'label','Hỗ trợ bộ phận khác').total<1)throw new Error('B115_REPORT_DEDUCTION_MISMATCH:'+JSON.stringify({bSupport,aSupport,bPicker,aPicker,bOld,aOld}));
NODE

B115_EXIT_FUTURE_HTTP=$(curl -sS --connect-timeout 10 --max-time 20 -o "$D/b115-exit-future-blocked.json" -w '%{http_code}' -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "$(jq -nc --arg sid "$B80_SID" --arg mnv "$B80_MNV" --arg idem "__B115_EXIT_FUTURE_$SUFFIX" '{session_id:$sid,mnv:$mnv,pda_exit_status:"Tốt",idempotency_key:$idem}')" "$SERVICE_URL/v1/session/exit-v2")
[[ "$B115_EXIT_FUTURE_HTTP" == 409 ]]
jq -e '.error.code=="FUTURE_LABOR_BLOCKS_EXIT"' "$D/b115-exit-future-blocked.json" >/dev/null

B115_NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
B115_CORRECT_BODY=$(jq -nc --arg ev "$B115_PRE_EXIT_CORRECT" --arg labor "$B115_LABOR_B" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg sid "$B80_SID" --arg mnv "$B80_MNV" --arg start "$B115_AT" --arg end "$B115_NOW" '{
  events:[{action:"labor_finish",event_id:$ev,device_id:$dev,business_date:$date,payload:{labor_id:$labor,session_id:$sid,mnv:$mnv,start_at:$start,end_at:$end,correction:true,note:"reconciled before exit"}}]
}')
mutation_api b115-pre-exit-correct "$B115_CORRECT_BODY"
jq -e '.ok==true and .results[0].status=="CONFIRMED"' "$D/b115-pre-exit-correct.json" >/dev/null
echo 'beta115_labor_future=PASS scheduled_cap=PASS overlap=PASS one_open=PASS boolean_deduct=PASS multi_interval_unique_support=PASS future_exit_guard=PASS'

B80_EXIT_BODY="{\"session_id\":\"$B80_SID\",\"mnv\":\"$B80_MNV\",\"pda_exit_status\":\"Tốt\",\"idempotency_key\":\"$B80_EXIT\"}"
for attempt in 1 2 3 4; do
  B80_EXIT_HTTP=$(curl -sS --connect-timeout 10 --max-time 20 -o "$D/b80-exit.json" -w '%{http_code}' -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "$B80_EXIT_BODY" "$SERVICE_URL/v1/session/exit-v2" || printf 000)
  if [[ "$B80_EXIT_HTTP" =~ ^2 ]]; then break; fi
  if [[ "$B80_EXIT_HTTP" == 409 ]] && jq -e '.error.code=="SESSION_EXIT_CONFLICT" and .error.retryable==true' "$D/b80-exit.json" >/dev/null 2>&1; then
    sleep "$attempt"
    continue
  fi
  echo "B80_EXIT_FAILED:http=$B80_EXIT_HTTP code=$(jq -r '.error.code // "UNKNOWN"' "$D/b80-exit.json" 2>/dev/null || echo UNKNOWN)" >&2
  exit 31
done
[[ "$B80_EXIT_HTTP" =~ ^2 ]] || { echo "B80_EXIT_CAS_RETRY_EXHAUSTED" >&2; exit 32; }
jq -e --arg sid "$B80_SID" '.ok==true and .session.session_id==$sid and .session.state=="ENDED"' "$D/b80-exit.json" >/dev/null

B80_EXIT_AT=$(jq -r '.session.exit_at' "$D/b80-exit.json")
B115_AFTER_EXIT=$(date -u -d "$B80_EXIT_AT + 1 minute" +%Y-%m-%dT%H:%M:%SZ)
B115_AFTER_EXIT_BAD_BODY=$(jq -nc --arg ev "$B115_AFTER_EXIT_BAD" --arg labor "$B115_LABOR_B" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg sid "$B80_SID" --arg mnv "$B80_MNV" --arg start "$B115_AT" --arg end "$B115_AFTER_EXIT" '{
  events:[{action:"labor_finish",event_id:$ev,device_id:$dev,business_date:$date,payload:{labor_id:$labor,session_id:$sid,mnv:$mnv,start_at:$start,end_at:$end,correction:true,note:"after actual exit"}}]
}')
mutation_api b115-after-exit-bad "$B115_AFTER_EXIT_BAD_BODY"
jq -e '.ok==true and .results[0].status=="REVIEW_REQUIRED" and .results[0].error_code=="LABOR_END_AFTER_SHIFT_OR_EXIT"' "$D/b115-after-exit-bad.json" >/dev/null
B115_AFTER_EXIT_OK_BODY=$(jq -nc --arg ev "$B115_AFTER_EXIT_OK" --arg labor "$B115_LABOR_B" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg sid "$B80_SID" --arg mnv "$B80_MNV" --arg start "$B115_AT" --arg end "$B80_EXIT_AT" '{
  events:[{action:"labor_finish",event_id:$ev,device_id:$dev,business_date:$date,payload:{labor_id:$labor,session_id:$sid,mnv:$mnv,start_at:$start,end_at:$end,correction:true,note:"exact actual exit"}}]
}')
mutation_api b115-after-exit-ok "$B115_AFTER_EXIT_OK_BODY"
jq -e '.ok==true and .results[0].status=="CONFIRMED"' "$D/b115-after-exit-ok.json" >/dev/null
echo 'beta115_actual_exit_cap=PASS exact_exit_allowed=PASS after_exit_rejected=PASS'

owner_api /v1/session/resources/snapshot b80-ended-snapshot "{\"session_id\":\"$B80_SID\",\"mnv\":\"$B80_MNV\"}"
jq -e --arg sid "$B80_SID" '.ok==true and .session.session_id==$sid and .session.state=="ENDED" and (.resource_assignments|all(.state=="USED"))' "$D/b80-ended-snapshot.json" >/dev/null
echo 'beta80_session_v2=ENTER_SNAPSHOT_MUTATE_EXIT_PASS'

# Exact historical session gate: use production identity row, then request all three identity fields.
IDS="'07323dde-0456-45f8-a1d6-942e9f2e602e','03b1337f-08fd-46a1-ab94-8b0700763df3','d94d968a-0cf6-4086-8352-85154a5ec62e'"
HIST=$(sql "SELECT session_id,mnv,business_date FROM attendance_sessions WHERE session_id IN ($IDS) ORDER BY session_id;")
printf '%s' "$HIST" > "$D/historical-identities.json"
node - <<'NODE' "$D/historical-identities.json"
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),r=j?.[0]?.results||[];if(r.length!==3)throw new Error('HISTORICAL_SESSION_ROWS_NOT_3:'+JSON.stringify(r));
NODE
node - <<'NODE' "$D/historical-identities.json" > "$D/historical.tsv"
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));for(const r of j[0].results)console.log([r.session_id,r.mnv,r.business_date].join('\t'));
NODE
while IFS=$'\t' read -r sid mnv bdate; do
  name="historical-${sid:0:8}"
  read_api "$name" "{\"action\":\"historical_session_detail\",\"session_id\":\"$sid\",\"business_date\":\"$bdate\",\"mnv\":\"$mnv\"}"
  jq -e --arg sid "$sid" --arg mnv "$mnv" --arg bdate "$bdate" '.ok==true and .source=="SERVICE_D1" and .hydrated==true and .identity.session_id==$sid and .identity.mnv==$mnv and .identity.business_date==$bdate and .session.session_id==$sid' "$D/$name.json" >/dev/null
done < "$D/historical.tsv"

# OAuth token for conservative Google append+readback baseline and final replica readback.
GOOGLE_TOKEN=$(curl -fsS https://oauth2.googleapis.com/token -d client_id="$GOOGLE_OAUTH_CLIENT_ID" -d client_secret="$GOOGLE_OAUTH_CLIENT_SECRET" -d refresh_token="$GOOGLE_OAUTH_REFRESH_TOKEN" -d grant_type=refresh_token | jq -r '.access_token')
test -n "$GOOGLE_TOKEN" -a "$GOOGLE_TOKEN" != null
echo "::add-mask::$GOOGLE_TOKEN"

# Beta107 document management LIVE contract: Drive scope + direct resumable upload + exact-byte readback + duplicate guard.
DRIVE_SCOPE_HTTP=$(curl -sS --connect-timeout 10 --max-time 20 -o "$D/b107-drive-about.json" -w '%{http_code}' -H "Authorization: Bearer $GOOGLE_TOKEN" "https://www.googleapis.com/drive/v3/about?fields=user(displayName)")
[[ "$DRIVE_SCOPE_HTTP" == 200 ]] || { echo "B107_DRIVE_OAUTH_SCOPE_REQUIRED:http=$DRIVE_SCOPE_HTTP" >&2; cat "$D/b107-drive-about.json" >&2; exit 21; }
printf '%s' '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAACAAIDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD6pooooA//2Q==' | base64 -d > "$DOC_BYTES"
# Add a harmless per-run trailer after JPEG EOI so repeated CI attempts never collide with a stale prior fixture.
printf 'B107-%s' "$SUFFIX" >> "$DOC_BYTES"
DOC_SIZE=$(wc -c < "$DOC_BYTES" | tr -d ' ')
DOC_SHA=$(sha256sum "$DOC_BYTES" | awk '{print $1}')
DOC_MD5=$(md5sum "$DOC_BYTES" | awk '{print $1}')
[[ "$DOC_SIZE" -gt 628 ]]
[[ "$DOC_SHA" =~ ^[0-9a-f]{64}$ && "$DOC_MD5" =~ ^[0-9a-f]{32}$ ]]

owner_api /v1/documents/categories b107-category-create "{\"operation\":\"CREATE\",\"display_name\":\"$DOC_CATEGORY_NAME\"}"
jq -e '.ok==true and (.item.category_id|type=="string")' "$D/b107-category-create.json" >/dev/null
DOC_CATEGORY_ID=$(jq -r '.item.category_id' "$D/b107-category-create.json")
test -n "$DOC_CATEGORY_ID" -a "$DOC_CATEGORY_ID" != null

DOC_SESSION_BODY=$(jq -nc --arg category "$DOC_CATEGORY_ID" --arg sha "$DOC_SHA" --arg md5 "$DOC_MD5" --arg idem "$DOC_IDEMPOTENCY" --arg at "$NOW" --arg group "$DOC_GROUP_ID" --argjson size "$DOC_SIZE" '{
  category_id:$category,mime_type:"image/jpeg",byte_size:$size,sha256:$sha,md5:$md5,
  width:2,height:2,source_kind:"CAMERA",captured_at:$at,idempotency_key:$idem,
  group_id:$group,group_mode:"MULTI_PAGE",page_index:1,page_count:2
}')
DOC_SESSION_HTTP=$(curl -sS --connect-timeout 10 --max-time 30 -o "$D/b107-upload-session.json" -w '%{http_code}' -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "$DOC_SESSION_BODY" "$SERVICE_URL/v1/documents/upload-session")
[[ "$DOC_SESSION_HTTP" =~ ^2 ]] || {
  echo "B107_UPLOAD_SESSION_FAILED:http=$DOC_SESSION_HTTP" >&2
  cat "$D/b107-upload-session.json" >&2
  DOC_DIAG=$(sql "SELECT document_id,status,last_error FROM document_records WHERE category_id='$DOC_CATEGORY_ID' ORDER BY created_at DESC LIMIT 1;")
  printf '%s' "$DOC_DIAG" > "$D/b107-upload-session-d1-diagnostic.json"
  node -e 'const j=JSON.parse(process.argv[1]),r=j?.[0]?.results?.[0];if(r?.last_error)process.stderr.write("B107_DRIVE_DIAGNOSTIC:"+String(r.last_error).replace(/[\r\n]+/g," ").slice(0,500)+"\n")' "$DOC_DIAG"
  exit 23
}
jq -e '.ok==true and .upload_method=="PUT" and (.upload_url|startswith("https://")) and .document.status=="PENDING"' "$D/b107-upload-session.json" >/dev/null
DOC_ID=$(jq -r '.document.document_id' "$D/b107-upload-session.json")
DOC_UPLOAD_URL=$(jq -r '.upload_url' "$D/b107-upload-session.json")
DOC_UPLOAD_HTTP=$(curl -sS --connect-timeout 10 --max-time 60 -o "$D/b107-drive-upload.json" -w '%{http_code}' -X PUT -H 'Content-Type: image/jpeg' --data-binary @"$DOC_BYTES" "$DOC_UPLOAD_URL")
[[ "$DOC_UPLOAD_HTTP" =~ ^2 ]] || { echo "B107_DRIVE_UPLOAD_FAILED:http=$DOC_UPLOAD_HTTP" >&2; cat "$D/b107-drive-upload.json" >&2; exit 22; }
DOC_DRIVE_ID=$(jq -r '.id // empty' "$D/b107-drive-upload.json")
test -n "$DOC_DRIVE_ID"

owner_api /v1/documents/complete b107-complete "{\"document_id\":\"$DOC_ID\",\"drive_file_id\":\"$DOC_DRIVE_ID\"}"
jq -e --arg id "$DOC_ID" '.ok==true and .document.document_id==$id and .document.status=="COMPLETE"' "$D/b107-complete.json" >/dev/null

DOC_DUP_BODY=$(printf '%s' "$DOC_SESSION_BODY" | jq -c --arg idem "$DOC_DUP_IDEMPOTENCY" '.idempotency_key=$idem')
DOC_DUP_HTTP=$(curl -sS --connect-timeout 10 --max-time 20 -o "$D/b107-duplicate.json" -w '%{http_code}' -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "$DOC_DUP_BODY" "$SERVICE_URL/v1/documents/upload-session")
[[ "$DOC_DUP_HTTP" == 409 ]]
jq -e --arg id "$DOC_ID" '.error.code=="DOCUMENT_EXACT_DUPLICATE" and .duplicate.kind=="EXACT" and .duplicate.document.document_id==$id' "$D/b107-duplicate.json" >/dev/null

# Beta109: prove rotation-aware near-similar detection. Primary incoming dHash is intentionally far;
# only a rotated variant is within threshold 16 of the stored complete document fingerprint.
sql "UPDATE document_records SET dhash64='000000000000000f' WHERE document_id='$DOC_ID';" > "$D/b109-similar-seed.json"
DOC_SIMILAR_BODY=$(printf '%s' "$DOC_SESSION_BODY" | jq -c \
  --arg idem "$DOC_SIMILAR_IDEMPOTENCY" \
  '.idempotency_key=$idem
   | .sha256="ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
   | .md5="ffffffffffffffffffffffffffffffff"
   | .dhash64="ffffffffffffffff"
   | .dhash64_variants=["ffffffffffffffff","00000000000000ff"]')
DOC_SIMILAR_HTTP=$(curl -sS --connect-timeout 10 --max-time 20 -o "$D/b109-similar.json" -w '%{http_code}' \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "$DOC_SIMILAR_BODY" \
  "$SERVICE_URL/v1/documents/upload-session")
[[ "$DOC_SIMILAR_HTTP" == 409 ]]
jq -e --arg id "$DOC_ID" '.error.code=="DOCUMENT_SIMILAR_IMAGE"
  and .duplicate.kind=="SIMILAR"
  and .duplicate.document.document_id==$id
  and .duplicate.rotation_aware==true
  and .duplicate.threshold==16
  and (.duplicate.distance|numbers) <= 16' "$D/b109-similar.json" >/dev/null

curl -fsS --connect-timeout 10 --max-time 30 -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/v1/documents/$DOC_ID/media" > "$D/b107-media.jpg"
[[ "$(sha256sum "$D/b107-media.jpg" | awk '{print $1}')" == "$DOC_SHA" ]]

# Beta110: upload second page in the same group, then delete only page 2 and verify reindex 1/1.
cp "$DOC_BYTES" "$DOC2_BYTES"; printf 'B110-PAGE2-%s' "$SUFFIX" >> "$DOC2_BYTES"
DOC2_SIZE=$(wc -c < "$DOC2_BYTES" | tr -d ' '); DOC2_SHA=$(sha256sum "$DOC2_BYTES" | awk '{print $1}'); DOC2_MD5=$(md5sum "$DOC2_BYTES" | awk '{print $1}')
DOC2_SESSION_BODY=$(jq -nc --arg category "$DOC_CATEGORY_ID" --arg sha "$DOC2_SHA" --arg md5 "$DOC2_MD5" --arg idem "$DOC2_IDEMPOTENCY" --arg at "$NOW" --arg group "$DOC_GROUP_ID" --argjson size "$DOC2_SIZE" '{
  category_id:$category,mime_type:"image/jpeg",byte_size:$size,sha256:$sha,md5:$md5,
  width:2,height:2,source_kind:"GALLERY",captured_at:$at,idempotency_key:$idem,
  group_id:$group,group_mode:"MULTI_PAGE",page_index:2,page_count:2,allow_similar:true
}')
owner_api /v1/documents/upload-session b110-page2-session "$DOC2_SESSION_BODY"
jq -e '.ok==true and .document.status=="PENDING" and .document.group_mode=="MULTI_PAGE" and .document.page_index==2 and .document.page_count==2' "$D/b110-page2-session.json" >/dev/null
DOC2_ID=$(jq -r '.document.document_id' "$D/b110-page2-session.json"); DOC2_UPLOAD_URL=$(jq -r '.upload_url' "$D/b110-page2-session.json")
DOC2_UPLOAD_HTTP=$(curl -sS --connect-timeout 10 --max-time 60 -o "$D/b110-page2-drive-upload.json" -w '%{http_code}' -X PUT -H 'Content-Type: image/jpeg' --data-binary @"$DOC2_BYTES" "$DOC2_UPLOAD_URL")
[[ "$DOC2_UPLOAD_HTTP" =~ ^2 ]]
DOC2_DRIVE_ID=$(jq -r '.id // empty' "$D/b110-page2-drive-upload.json"); test -n "$DOC2_DRIVE_ID"
owner_api /v1/documents/complete b110-page2-complete "{\"document_id\":\"$DOC2_ID\",\"drive_file_id\":\"$DOC2_DRIVE_ID\"}"
jq -e '.ok==true and .document.status=="COMPLETE" and .document.page_index==2 and .document.page_count==2' "$D/b110-page2-complete.json" >/dev/null

curl -fsS -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/v1/documents?limit=20&category_id=$DOC_CATEGORY_ID" > "$D/b110-multipage-list.json"
jq -e --arg g "$DOC_GROUP_ID" --arg a "$DOC_ID" --arg b "$DOC2_ID" '
  [.items[]|select(.group_id==$g)] as $x |
  ($x|length)==2 and
  ([$x[]|select(.document_id==$a and .page_index==1 and .page_count==2)]|length)==1 and
  ([$x[]|select(.document_id==$b and .page_index==2 and .page_count==2)]|length)==1
' "$D/b110-multipage-list.json" >/dev/null

owner_api /v1/documents/delete b110-delete-page2 "$(jq -nc --arg id "$DOC2_ID" --arg idem "$DOC_BULK_DELETE_IDEMPOTENCY" '{operation:"START",document_ids:[$id],idempotency_key:$idem}')"
B110_DELETE_MUTATION=$(jq -r '.mutation.mutation_id' "$D/b110-delete-page2.json"); test -n "$B110_DELETE_MUTATION" -a "$B110_DELETE_MUTATION" != null
for _ in $(seq 1 20); do
  state=$(jq -r '.mutation.state' "$D/b110-delete-page2.json")
  [[ "$state" == DONE ]] && break
  owner_api /v1/documents/delete b110-delete-page2 "$(jq -nc --arg id "$B110_DELETE_MUTATION" '{operation:"PROCESS",mutation_id:$id}')"
  sleep 0.2
done
jq -e '.ok==true and .mutation.state=="DONE" and .mutation.processed_items==1' "$D/b110-delete-page2.json" >/dev/null
DOC2_DRIVE_DELETE_HTTP=$(curl -sS --connect-timeout 10 --max-time 20 -o "$D/b110-page2-drive-deleted.json" -w '%{http_code}' -H "Authorization: Bearer $GOOGLE_TOKEN" "https://www.googleapis.com/drive/v3/files/$DOC2_DRIVE_ID?fields=id")
[[ "$DOC2_DRIVE_DELETE_HTTP" == 404 ]]
B110_REINDEX_DB=$(sql "SELECT (SELECT COUNT(*) FROM document_records WHERE document_id='$DOC2_ID') AS deleted_rows,(SELECT page_index FROM document_records WHERE document_id='$DOC_ID') AS page_index,(SELECT page_count FROM document_records WHERE document_id='$DOC_ID') AS page_count,(SELECT COUNT(*) FROM document_delete_items WHERE mutation_id='$B110_DELETE_MUTATION') AS checkpoint_rows,(SELECT COUNT(*) FROM events WHERE event_type='DOCUMENT_DELETE' AND actor_id='$LOGIN') AS history_rows;")
printf '%s' "$B110_REINDEX_DB" > "$D/b110-delete-reindex-db.json"
node -e 'const j=JSON.parse(process.argv[1]),r=j?.[0]?.results?.[0];if(!r||Number(r.deleted_rows)!==0||Number(r.page_index)!==1||Number(r.page_count)!==1||Number(r.checkpoint_rows)!==0||Number(r.history_rows)<1)throw new Error("B110_DELETE_REINDEX_MISMATCH:"+JSON.stringify(r))' "$B110_REINDEX_DB"
DOC2_DRIVE_ID=""
echo 'beta110_document_batch=PASS multipage_group=PASS selected_delete=PASS reindex=PASS history=PASS'

owner_api_slow /v1/documents/categories b108-category-rename "{\"operation\":\"UPDATE\",\"category_id\":\"$DOC_CATEGORY_ID\",\"display_name\":\"$DOC_CATEGORY_RENAMED\",\"idempotency_key\":\"$DOC_RENAME_IDEMPOTENCY\"}"
jq -e '.ok==true and .mutation.operation=="UPDATE" and .mutation.state=="DONE" and .mutation.processed_items==1' "$D/b108-category-rename.json" >/dev/null
DOC_RENAME_DB=$(sql "SELECT c.display_name,c.mutation_state,d.category_name_snapshot,d.file_name FROM document_categories c JOIN document_records d ON d.category_id=c.category_id WHERE c.category_id='$DOC_CATEGORY_ID' AND d.document_id='$DOC_ID';")
printf '%s' "$DOC_RENAME_DB" > "$D/b108-category-rename-db.json"
RENAMED_FILE=$(node -e 'const j=JSON.parse(process.argv[1]),r=j?.[0]?.results?.[0];if(!r||r.display_name!==process.argv[2]||r.category_name_snapshot!==process.argv[2]||r.mutation_state!=="NONE")throw new Error("B108_RENAME_DB_MISMATCH:"+JSON.stringify(r));process.stdout.write(String(r.file_name||""))' "$DOC_RENAME_DB" "$DOC_CATEGORY_RENAMED")
test -n "$RENAMED_FILE"
curl -fsS --connect-timeout 10 --max-time 20 -H "Authorization: Bearer $GOOGLE_TOKEN" "https://www.googleapis.com/drive/v3/files/$DOC_DRIVE_ID?fields=id,name,trashed" > "$D/b108-drive-renamed.json"
jq -e --arg id "$DOC_DRIVE_ID" --arg name "$RENAMED_FILE" '.id==$id and .name==$name and (.trashed|not)' "$D/b108-drive-renamed.json" >/dev/null

curl -fsS --connect-timeout 10 --max-time 20 -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/v1/documents?limit=10" > "$D/b108-list-renamed.json"
jq -e --arg id "$DOC_ID" --arg name "$DOC_CATEGORY_RENAMED" '[.items[]|select(.document_id==$id and .status=="COMPLETE" and .category_name==$name)]|length==1' "$D/b108-list-renamed.json" >/dev/null

owner_api_slow /v1/documents/categories b108-category-delete "{\"operation\":\"DELETE\",\"category_id\":\"$DOC_CATEGORY_ID\",\"idempotency_key\":\"$DOC_DELETE_IDEMPOTENCY\"}"
jq -e '.ok==true and .mutation.operation=="DELETE" and .mutation.state=="DONE" and .mutation.processed_items==1' "$D/b108-category-delete.json" >/dev/null
DOC_DRIVE_DELETE_HTTP=$(curl -sS --connect-timeout 10 --max-time 20 -o "$D/b108-drive-deleted.json" -w '%{http_code}' -H "Authorization: Bearer $GOOGLE_TOKEN" "https://www.googleapis.com/drive/v3/files/$DOC_DRIVE_ID?fields=id,name,trashed")
[[ "$DOC_DRIVE_DELETE_HTTP" == 404 ]]
DOC_DELETE_DB=$(sql "SELECT
  (SELECT COUNT(*) FROM document_records WHERE document_id='$DOC_ID') AS documents,
  (SELECT COUNT(*) FROM document_categories WHERE category_id='$DOC_CATEGORY_ID') AS categories,
  (SELECT COUNT(*) FROM document_audit WHERE target_id IN ('$DOC_ID','$DOC_CATEGORY_ID')) AS business_audit,
  (SELECT COUNT(*) FROM document_category_mutation_items WHERE mutation_id IN (SELECT mutation_id FROM document_category_mutations WHERE category_id='$DOC_CATEGORY_ID')) AS mutation_items,
  (SELECT COUNT(*) FROM document_category_mutations WHERE category_id='$DOC_CATEGORY_ID' AND (old_display_name<>'' OR new_display_name IS NOT NULL OR new_normalized_name IS NOT NULL)) AS retained_names,
  (SELECT COUNT(*) FROM document_category_mutations WHERE category_id='$DOC_CATEGORY_ID' AND state='DONE') AS receipts;")
printf '%s' "$DOC_DELETE_DB" > "$D/b108-category-delete-db.json"
node -e 'const j=JSON.parse(process.argv[1]),r=j?.[0]?.results?.[0];if(Number(r.documents)!==0||Number(r.categories)!==0||Number(r.business_audit)!==0||Number(r.mutation_items)!==0||Number(r.retained_names)!==0||Number(r.receipts)<2)throw new Error("B108_HARD_DELETE_MISMATCH:"+JSON.stringify(r))' "$DOC_DELETE_DB"
DOC_DRIVE_ID=""

cleanup_document_d1
AUTH_FIXTURE=$(sql "SELECT (SELECT COUNT(*) FROM accounts WHERE login_id='$LOGIN') AS account_rows,(SELECT COUNT(*) FROM auth_sessions WHERE login_id='$LOGIN' AND session_id='$AUTH_SESSION') AS session_rows;")
node -e 'const j=JSON.parse(process.argv[1]),r=j?.[0]?.results?.[0];if(Number(r?.account_rows)!==1||Number(r?.session_rows)!==1)throw new Error("B108_SHARED_AUTH_CLEANUP_REGRESSION:"+JSON.stringify(r))' "$AUTH_FIXTURE"
echo 'beta110_document_management=PASS worker_google_secret_sync=PASS drive_scope=PASS resumable_direct=PASS exact_readback=PASS exact_duplicate_guard=PASS rotation_aware_near_similar=PASS multipage_group=PASS selected_delete_reindex=PASS document_history=PASS category_rename_all=PASS category_hard_delete=PASS mutation_receipt_minimal=PASS document_cleanup_only=PASS shared_auth_retained=PASS'

META=$(curl -fsS -H "Authorization: Bearer $GOOGLE_TOKEN" "https://sheets.googleapis.com/v4/spreadsheets/$OUTBOUND_SHEET_ID?fields=sheets.properties(sheetId,title)")
DROP_SHEET_ID=$(printf '%s' "$META" | jq -r '.sheets[]|select(.properties.title=="Nhận hàng rớt")|.properties.sheetId')
test -n "$DROP_SHEET_ID" -a "$DROP_SHEET_ID" != null

BASE_START=$(date +%s%3N)
BASE_RESP=$(curl -fsS -X POST -H "Authorization: Bearer $GOOGLE_TOKEN" -H 'Content-Type: application/json' --data "{\"range\":\"'Nhận hàng rớt'!A:H\",\"majorDimension\":\"ROWS\",\"values\":[[\"__B78_BASE__\",\"26/08/2026\",\"\",\"BASE\",1,\"Beta78 baseline\",\"$NOW\",\"$BASE_ID\"]]}" "https://sheets.googleapis.com/v4/spreadsheets/$OUTBOUND_SHEET_ID/values/'Nh%E1%BA%ADn%20h%C3%A0ng%20r%E1%BB%9Bt'!A:H:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS")
BASE_RANGE=$(printf '%s' "$BASE_RESP" | jq -r '.updates.updatedRange')
BASE_ROW=$(printf '%s' "$BASE_RANGE" | sed -E 's/.*!A([0-9]+):H.*/\1/')
curl -fsS -H "Authorization: Bearer $GOOGLE_TOKEN" "https://sheets.googleapis.com/v4/spreadsheets/$OUTBOUND_SHEET_ID/values/'Nh%E1%BA%ADn%20h%C3%A0ng%20r%E1%BB%9Bt'!A${BASE_ROW}:H${BASE_ROW}" > "$D/baseline-readback.json"
jq -e --arg id "$BASE_ID" '.values[0][7]==$id' "$D/baseline-readback.json" >/dev/null
BASE_END=$(date +%s%3N); BASELINE_MS=$((BASE_END-BASE_START))
# Delete only the baseline row created above.
curl -fsS -X POST -H "Authorization: Bearer $GOOGLE_TOKEN" -H 'Content-Type: application/json' --data "{\"requests\":[{\"deleteDimension\":{\"range\":{\"sheetId\":$DROP_SHEET_ID,\"dimension\":\"ROWS\",\"startIndex\":$((BASE_ROW-1)),\"endIndex\":$BASE_ROW}}}]}" "https://sheets.googleapis.com/v4/spreadsheets/$OUTBOUND_SHEET_ID:batchUpdate" >/dev/null

read_api location-list '{"action":"outbound_location_list"}'
jq -e '.ok==true and .source=="SERVICE_D1" and .owner==true' "$D/location-list.json" >/dev/null
read_api location-create "{\"action\":\"outbound_location_mutate\",\"operation\":\"CREATE\",\"after\":\"$LOC1\",\"event_id\":\"$EV_CREATE\",\"idempotency_key\":\"$EV_CREATE\"}"
jq -e '.ok==true and .source=="SERVICE_D1" and .idempotent==false' "$D/location-create.json" >/dev/null
read_api location-create-dup "{\"action\":\"outbound_location_mutate\",\"operation\":\"CREATE\",\"after\":\"$LOC1\",\"event_id\":\"$EV_CREATE\",\"idempotency_key\":\"$EV_CREATE\"}"
jq -e '.ok==true and .idempotent==true' "$D/location-create-dup.json" >/dev/null
read_api location-update "{\"action\":\"outbound_location_mutate\",\"operation\":\"UPDATE\",\"before\":\"$LOC1\",\"after\":\"$LOC2\",\"event_id\":\"$EV_UPDATE\",\"idempotency_key\":\"$EV_UPDATE\"}"
jq -e '.ok==true and .idempotent==false' "$D/location-update.json" >/dev/null

ACK_START=$(date +%s%3N)
read_api drop-append "{\"action\":\"outbound_drop_append\",\"location\":\"$LOC2\",\"scan_qr\":\"B78|DO-${SUFFIX}|X|1/7\",\"do_number\":\"DO-${SUFFIX}\",\"package_count\":7,\"idempotency_key\":\"$DROP_ID\"}"
ACK_END=$(date +%s%3N); SERVICE_ACK_MS=$((ACK_END-ACK_START))
jq -e '.ok==true and .source=="SERVICE_D1" and .idempotent==false and .replication=="OUTBOX_PENDING"' "$D/drop-append.json" >/dev/null
read_api drop-append-dup "{\"action\":\"outbound_drop_append\",\"location\":\"$LOC2\",\"scan_qr\":\"B78|DO-${SUFFIX}|X|1/7\",\"do_number\":\"DO-${SUFFIX}\",\"package_count\":7,\"idempotency_key\":\"$DROP_ID\"}"
jq -e '.ok==true and .idempotent==true' "$D/drop-append-dup.json" >/dev/null
read_api location-delete "{\"action\":\"outbound_location_mutate\",\"operation\":\"DELETE\",\"before\":\"$LOC2\",\"event_id\":\"$EV_DELETE\",\"idempotency_key\":\"$EV_DELETE\"}"
jq -e '.ok==true' "$D/location-delete.json" >/dev/null

COUNTS=$(sql "SELECT (SELECT COUNT(*) FROM events WHERE idempotency_key='$EV_CREATE') create_events,(SELECT COUNT(*) FROM events WHERE idempotency_key='$DROP_ID') drop_events,(SELECT COUNT(*) FROM outbound_drop_records WHERE record_id='$DROP_ID') drop_rows;")
printf '%s' "$COUNTS" > "$D/duplicate-counts.json"
node -e 'const j=JSON.parse(process.argv[1]),r=j?.[0]?.results?.[0];if(Number(r.create_events)!==1||Number(r.drop_events)!==1||Number(r.drop_rows)!==1)throw new Error("DUPLICATE_GATE_FAILED:"+JSON.stringify(r))' "$COUNTS"

REPL_START=$(date +%s%3N); REPL_OK=0
for _ in $(seq 1 30); do
  O=$(sql "SELECT COUNT(*) pending FROM outbound_replication_outbox o JOIN events e ON e.event_id=o.event_id WHERE e.actor_id='$LOGIN' AND o.status<>'SYNCED';")
  P=$(node -e 'const j=JSON.parse(process.argv[1]);process.stdout.write(String(j?.[0]?.results?.[0]?.pending??99))' "$O")
  if [[ "$P" == 0 ]]; then REPL_OK=1; break; fi
  sleep 4
done
[[ "$REPL_OK" == 1 ]] || { echo OUTBOUND_OUTBOX_NOT_SYNCED >&2; exit 8; }
REPL_END=$(date +%s%3N); REPLICATION_MS=$((REPL_END-REPL_START))

curl -fsS -H "Authorization: Bearer $GOOGLE_TOKEN" "https://sheets.googleapis.com/v4/spreadsheets/$OUTBOUND_SHEET_ID/values/'Nh%E1%BA%ADn%20h%C3%A0ng%20r%E1%BB%9Bt'!A2:H" > "$D/gsheet-drop-readback.json"
DROP_ROW=$(node - <<'NODE' "$D/gsheet-drop-readback.json" "$DROP_ID" "$LOC2" "DO-$SUFFIX"
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),id=process.argv[3],loc=process.argv[4],doNo=process.argv[5];const rows=j.values||[];const i=rows.findIndex(r=>String(r[7]||'')===id);if(i<0)throw new Error('DROP_GSHEET_MISSING');const r=rows[i];if(String(r[0])!==loc||String(r[3])!==doNo||String(r[4])!=='7')throw new Error('DROP_GSHEET_MISMATCH:'+JSON.stringify(r));process.stdout.write(String(i+2));
NODE
)
GSHEET_LOCATION_CLEAN=0
for _ in $(seq 1 10); do
  curl -fsS -H "Authorization: Bearer $GOOGLE_TOKEN" "https://sheets.googleapis.com/v4/spreadsheets/$OUTBOUND_SHEET_ID/values/'V%E1%BB%8B%20tr%C3%AD'!A2:A" > "$D/gsheet-location-readback.json"
  if node - <<'NODE' "$D/gsheet-location-readback.json" "$LOC1" "$LOC2"
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),a=(j.values||[]).flat().map(String);process.exit(a.includes(process.argv[3])||a.includes(process.argv[4])?1:0);
NODE
  then GSHEET_LOCATION_CLEAN=1; break; fi
  sleep 3
done
[[ "$GSHEET_LOCATION_CLEAN" == 1 ]] || { echo TEST_LOCATION_REMAINS_IN_GSHEET >&2; exit 9; }
# Delete only test drop row after readback.
curl -fsS -X POST -H "Authorization: Bearer $GOOGLE_TOKEN" -H 'Content-Type: application/json' --data "{\"requests\":[{\"deleteDimension\":{\"range\":{\"sheetId\":$DROP_SHEET_ID,\"dimension\":\"ROWS\",\"startIndex\":$((DROP_ROW-1)),\"endIndex\":$DROP_ROW}}}]}" "https://sheets.googleapis.com/v4/spreadsheets/$OUTBOUND_SHEET_ID:batchUpdate" >/dev/null

cleanup_d1
CLEAN=$(sql "SELECT (SELECT COUNT(*) FROM accounts WHERE login_id='$LOGIN')+(SELECT COUNT(*) FROM events WHERE actor_id='$LOGIN')+(SELECT COUNT(*) FROM outbound_drop_records WHERE record_id='$DROP_ID')+(SELECT COUNT(*) FROM outbound_locations WHERE location LIKE '__B78%') AS n;")
node -e 'const j=JSON.parse(process.argv[1]);if(Number(j?.[0]?.results?.[0]?.n)!==0)throw new Error("B78_TEST_DATA_REMAINS")' "$CLEAN"
AUTH_AFTER=$(sql "SELECT authority_epoch,mode,scope,service_generation FROM authority_state WHERE singleton_id=1;")
printf '%s' "$AUTH_AFTER" > "$D/authority-after.json"
node - <<'NODE' "$D/authority-before.json" "$D/authority-after.json"
const fs=require('fs'),a=JSON.parse(fs.readFileSync(process.argv[2],'utf8'))?.[0]?.results?.[0],b=JSON.parse(fs.readFileSync(process.argv[3],'utf8'))?.[0]?.results?.[0];for(const k of ['authority_epoch','mode','scope','service_generation'])if(String(a[k])!==String(b[k]))throw new Error('AUTHORITY_INVARIANT_CHANGED:'+k);
NODE

BACKUP_ID=$(jq -r .backup_id "$D/portable-backup/manifest.json")
AUTOPILOT_STATE=$(jq -r .state "$D/d1-autopilot/receipt.json")
ROLLOVER_STATUS=$(jq -r .status "$D/d1-rollover-rehearsal/receipt.json")
jq -n --arg source_sha "${SERVICE_SOURCE_SHA:-$GITHUB_SHA}" --arg service_url "$SERVICE_URL" --arg worker "$WORKER_NAME" --arg generation "$GEN" --arg backup_id "$BACKUP_ID" --arg autopilot "$AUTOPILOT_STATE" --arg rollover "$ROLLOVER_STATUS" --argjson baseline_ms "$BASELINE_MS" --argjson service_ack_ms "$SERVICE_ACK_MS" --argjson replication_ms "$REPLICATION_MS" --argjson d1_bytes "$DB_BYTES" --argjson d1_limit "$DB_LIMIT" '{status:"PASS",source_sha:$source_sha,worker:$worker,service_url:$service_url,generation:$generation,d1:{bytes:$d1_bytes,limit_bytes:$d1_limit,usage_ratio:($d1_bytes/$d1_limit),retention_config_range_days:"45..365",portable_backup:"VERIFIED",backup_id:$backup_id,capacity_autopilot:$autopilot,rollover_rehearsal_2x:$rollover,heavy_repair_interval_minutes:30},beta99:{resilience_probe_service_direct:"PASS",resilience_probe_duplicate:"PASS",business_projection:"NONE"},historical_sessions:["07323dde-0456-45f8-a1d6-942e9f2e602e","03b1337f-08fd-46a1-ab94-8b0700763df3","d94d968a-0cf6-4086-8352-85154a5ec62e"],historical_result:"3/3_SERVICE_D1_EXACT",outbound:{location_crud:"PASS",duplicate:"PASS",gsheet_readback:"PASS",baseline_google_append_readback_ms:$baseline_ms,service_d1_ack_ms:$service_ack_ms,background_replication_ms:$replication_ms,dual_write:false},authority_change:"NONE",beta89:{pda_return:"PASS",pda_exchange:"PASS",same_session_user_pick:"PASS",unavailable_new_assignment:"PASS",duplicate_leases:"PASS",audit_storage_before_after:"PASS",legacy_sync_payload_projection:"PASS"},beta95:{meal_attendance:"PASS",idempotency:"PASS",late_audit:"PASS",history_14d:"PASS",d1_retention:"CONFIG_45_365_BACKUP_GUARDED",repair_scan_interval:"30M"},beta107:{document_management:"PASS",drive_scope:"PASS",resumable_direct_upload:"PASS",exact_byte_readback:"PASS",exact_duplicate_guard:"PASS",category_edit_delete:"OWNER_DECISION_FAIL_CLOSED",cleanup:"PASS"},beta110:{labor_time_range:"PASS",open_exit_block:"PASS",document_batch:"PASS"},beta111:{labor_exact_session:"PASS",daily_open_completed:"PASS",open_exit_block:"PASS",stale_session_reject:"PASS",stale_labor_reject:"PASS",completed_correction:"PASS",history_delete_canonical:"PASS",history_missing_404:"PASS"},test_cleanup:"PASS"}' > "$D/receipt.json"
B115_RECEIPT_TMP=$(mktemp "$D/receipt-beta115.XXXXXX.json")
jq '.beta115={future_scheduled_end:"PASS",shift_and_actual_exit_cap:"PASS",one_open_and_overlap:"PASS",boolean_deduct_write:"PASS",exact_mnv_shift_report_move:"PASS",multi_interval_no_double_count:"PASS",future_exit_reconcile:"PASS"}' "$D/receipt.json" > "$B115_RECEIPT_TMP" && mv "$B115_RECEIPT_TMP" "$D/receipt.json"
jq -e '.status=="PASS" and .historical_result=="3/3_SERVICE_D1_EXACT" and .outbound.duplicate=="PASS" and .outbound.gsheet_readback=="PASS" and (.beta115|to_entries|all(.value=="PASS"))' "$D/receipt.json" >/dev/null
cat "$D/receipt.json"
