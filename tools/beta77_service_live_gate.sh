#!/usr/bin/env bash
set -Eeuo pipefail

D=/tmp/beta77-service-live
rm -rf "$D" && mkdir -p "$D"
D1_NAME=pick-pack-1291-service-prod
WORKER_NAME=pick-pack-1291-service

for n in CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID GOOGLE_OAUTH_CLIENT_SECRET; do
  test -n "${!n:-}" || { echo "MISSING_REQUIRED_SECRET:$n" >&2; exit 2; }
done

echo "::add-mask::$CLOUDFLARE_API_TOKEN"
echo "::add-mask::$CLOUDFLARE_ACCOUNT_ID"
echo "::add-mask::$GOOGLE_OAUTH_CLIENT_SECRET"

cd service
npx wrangler --version

LIST=$(npx wrangler d1 list --json)
D1_ID=$(node -e 'const a=JSON.parse(process.argv[1]);const x=a.find(v=>v.name===process.env.D1_NAME);process.stdout.write(x?.uuid||x?.id||"")' "$LIST")
test -n "$D1_ID" || { echo 'PROD_D1_NOT_FOUND' >&2; exit 3; }
echo "::add-mask::$D1_ID"

AUTH_BEFORE=$(npx wrangler d1 execute "$D1_NAME" --remote --command "SELECT authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state WHERE singleton_id=1;" --json)
printf '%s' "$AUTH_BEFORE" > "$D/authority-before.json"
node - <<'NODE' "$D/authority-before.json"
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));const r=j?.[0]?.results?.[0];
if(!r||r.mode!=='SERVICE_PRIMARY'||r.scope!=='PRODUCTION'||!r.service_generation) throw new Error('PRODUCTION_AUTHORITY_NOT_READY');
process.stdout.write(String(r.service_generation));
NODE
SERVICE_GENERATION=$(node -e 'const j=JSON.parse(process.argv[1]);const r=j?.[0]?.results?.[0];process.stdout.write(String(r?.service_generation||""))' "$AUTH_BEFORE")
AUTH_EPOCH_BEFORE=$(node -e 'const j=JSON.parse(process.argv[1]);process.stdout.write(String(j?.[0]?.results?.[0]?.authority_epoch??""))' "$AUTH_BEFORE")
AUTH_SEQ_BEFORE=$(node -e 'const j=JSON.parse(process.argv[1]);process.stdout.write(String(j?.[0]?.results?.[0]?.authority_seq??""))' "$AUTH_BEFORE")
test -n "$SERVICE_GENERATION" && test -n "$AUTH_EPOCH_BEFORE" && test -n "$AUTH_SEQ_BEFORE"

python3 - "$D1_ID" "$SERVICE_GENERATION" <<'PY'
from pathlib import Path
import sys
p=Path('wrangler.jsonc')
s=p.read_text(encoding='utf-8')
d1,generation=sys.argv[1:]
repls={
  '"name": "pick-pack-1291-service-m1-staging"':'"name": "pick-pack-1291-service"',
  '"SERVICE_GENERATION": "m2-precutover-20260819-001"':f'"SERVICE_GENERATION": "{generation}"',
  '"database_name": "pick-pack-1291-m1-staging"':'"database_name": "pick-pack-1291-service-prod"',
  '"database_id": "__M1_D1_DATABASE_ID__"':f'"database_id": "{d1}"',
}
for old,new in repls.items():
    if old not in s: raise SystemExit('LIVE_CONFIG_ANCHOR_MISSING:'+old)
    s=s.replace(old,new,1)
Path('wrangler.live.jsonc').write_text(s,encoding='utf-8')
PY

# Deploy exact Beta77 service source to the existing production Worker and D1 only.
# Existing Worker secrets are preserved; this gate does not transition authority or create resources.
npx wrangler deploy --config wrangler.live.jsonc 2>&1 | tee "$D/deploy.log"
SERVICE_URL=$(grep -Eo 'https://[A-Za-z0-9._-]+\.workers\.dev' "$D/deploy.log" | tail -1 || true)
test -n "$SERVICE_URL" || { echo 'SERVICE_URL_NOT_FOUND' >&2; exit 4; }

echo "SERVICE_URL=$SERVICE_URL"
curl -fsS --retry 2 --retry-delay 2 --connect-timeout 15 --max-time 30 "$SERVICE_URL/health" > "$D/health.json"
node - <<'NODE' "$D/health.json" "$SERVICE_GENERATION" "$AUTH_EPOCH_BEFORE"
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
if(!j.ok||j.service!=='pick-pack-1291-service'||j.environment!=='production')throw new Error('LIVE_HEALTH_BAD');
if(String(j.generation)!==process.argv[3])throw new Error('GENERATION_CHANGED');
if(String(j.authority?.authority_epoch)!==process.argv[4]||j.authority?.mode!=='SERVICE_PRIMARY'||j.authority?.scope!=='PRODUCTION')throw new Error('AUTHORITY_CHANGED_ON_DEPLOY');
NODE

SUFFIX=$(printf '%s' "$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT" | sha256sum | cut -c1-10)
LOGIN="__B77_LOGIN_${SUFFIX}"
MNV_A="__B77_A_${SUFFIX}"
MNV_B="__B77_B_${SUFFIX}"
PDA="__B77_PDA_${SUFFIX}"
DEVICE="__B77_DEVICE_${SUFFIX}"
AUTH_SESSION="__B77_AUTH_${SUFFIX}"
OLD_SESSION="__B77_OLD_${SUFFIX}"
CUR_SESSION="__B77_CUR_${SUFFIX}"
EVENT_ID="__B77_RACE_EVT_${SUFFIX}"
IDEM="__B77_RACE_IDEM_${SUFFIX}"
TODAY=$(TZ=Asia/Bangkok date +%F)
YESTERDAY=$(TZ=Asia/Bangkok date -d 'yesterday' +%F)
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)

for v in "$LOGIN" "$MNV_A" "$MNV_B" "$PDA" "$DEVICE" "$AUTH_SESSION" "$OLD_SESSION" "$CUR_SESSION" "$EVENT_ID" "$IDEM"; do echo "::add-mask::$v"; done

SERVICE_TOKEN_SECRET=$(printf '%s' "$CLOUDFLARE_ACCOUNT_ID|$GOOGLE_OAUTH_CLIENT_SECRET|pick-pack-1291-m2-service-token-v1" | sha256sum | awk '{print $1}')
echo "::add-mask::$SERVICE_TOKEN_SECRET"
VERIFIER_HASH="b77_${SUFFIX}_vh"
TOKEN=$(node - <<'NODE' "$SERVICE_TOKEN_SECRET" "$LOGIN" "$VERIFIER_HASH" "$AUTH_SESSION" "$DEVICE"
const c=require('crypto');const secret=process.argv[2],payload={l:process.argv[3],r:'USER',v:process.argv[4],s:process.argv[5],d:process.argv[6],c:'PDA'};
const enc=Buffer.from(JSON.stringify(payload)).toString('base64url');const sig=c.createHmac('sha256',Buffer.from(secret)).update(enc).digest('base64url');process.stdout.write(enc+'.'+sig);
NODE
)
echo "::add-mask::$TOKEN"

sql(){ npx wrangler d1 execute "$D1_NAME" --remote --config wrangler.live.jsonc --command "$1" --json >/dev/null; }
read_api(){
  local name=$1 body=$2
  curl -fsS --connect-timeout 15 --max-time 30 -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json; charset=utf-8' --data-binary "$body" "$SERVICE_URL/v1/mobile/read" > "$D/$name.json"
}
cleanup(){
  set +e
  sql "DELETE FROM resource_leases WHERE resource_id='$PDA' OR mnv IN ('$MNV_A','$MNV_B'); DELETE FROM attendance_sessions WHERE mnv IN ('$MNV_A','$MNV_B'); DELETE FROM sheet_replication_outbox WHERE event_id='$EVENT_ID'; DELETE FROM mutation_assertions WHERE event_id='$EVENT_ID'; DELETE FROM events WHERE event_id='$EVENT_ID' OR idempotency_key='$IDEM'; DELETE FROM auth_sessions WHERE login_id='$LOGIN'; DELETE FROM accounts WHERE login_id='$LOGIN'; DELETE FROM employees WHERE mnv IN ('$MNV_A','$MNV_B'); DELETE FROM resources WHERE resource_type='PDA' AND resource_id='$PDA';" >/dev/null 2>&1
  set -e
}
trap 'rc=$?; cleanup; exit $rc' EXIT

cleanup
sql "INSERT INTO accounts(login_id,verifier,verifier_hash,role,display_name,position,email,status,source_row,source_checksum,is_shadow_test) VALUES('$LOGIN','b77-test','$VERIFIER_HASH','USER','Beta77 Test','TEST','','ACTIVE',-77,'b77-test',1); INSERT INTO auth_sessions(login_id,session_id,device_id,issued_at) VALUES('$LOGIN','$AUTH_SESSION','$DEVICE','$NOW'); INSERT INTO employees(mnv,full_name,source_row,source_checksum) VALUES('$MNV_A','Beta77 A',-77,'b77-test'),('$MNV_B','Beta77 B',-77,'b77-test'); INSERT INTO resources(resource_type,resource_id,status_label,available,metadata_json,source_row,source_checksum) VALUES('PDA','$PDA','TỐT',1,'{}',-77,'b77-test');"

read_api free "{\"action\":\"master_options\",\"mnv\":\"$MNV_A\"}"
node - <<'NODE' "$D/free.json" "$PDA"
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));if(!j.ok||!Array.isArray(j.pdas)||!j.pdas.some(x=>x.serial===process.argv[3]))throw new Error('FREE_PDA_NOT_VISIBLE');
NODE

sql "INSERT INTO attendance_sessions(session_id,mnv,business_date,shift,work_choice,state,pda_serial,enter_at,entered_by,version,updated_at) VALUES('$OLD_SESSION','$MNV_B','$YESTERDAY','TEST','PICK','ACTIVE','$PDA','$NOW','$LOGIN',1,'$NOW'); INSERT INTO resource_leases(resource_type,resource_id,session_id,mnv,business_date,acquired_event_id,acquired_at) VALUES('PDA','$PDA','$OLD_SESSION','$MNV_B','$YESTERDAY','__B77_DIRECT_OLD','$NOW');"
read_api old_busy "{\"action\":\"master_options\",\"mnv\":\"$MNV_A\"}"
read_api old_warning '{"action":"old_active_sessions"}'
node - <<'NODE' "$D/old_busy.json" "$D/old_warning.json" "$PDA" "$MNV_B" "$YESTERDAY"
const fs=require('fs'),o=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),w=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
if(!o.ok||o.pdas.some(x=>x.serial===process.argv[4]))throw new Error('CROSS_DAY_ACTIVE_PDA_LEAK');
if(!w.ok||!Array.isArray(w.items)||!w.items.some(x=>x.mnv===process.argv[5]&&x.business_date===process.argv[6]))throw new Error('OLD_ACTIVE_WARNING_MISSING');
NODE

sql "DELETE FROM resource_leases WHERE resource_type='PDA' AND resource_id='$PDA'; UPDATE attendance_sessions SET state='ENDED',exit_at='$NOW',exited_by='$LOGIN',version=2,updated_at='$NOW' WHERE session_id='$OLD_SESSION';"
read_api old_released "{\"action\":\"master_options\",\"mnv\":\"$MNV_A\"}"
node - <<'NODE' "$D/old_released.json" "$PDA"
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));if(!j.ok||!j.pdas.some(x=>x.serial===process.argv[3]))throw new Error('ENDED_OLD_PDA_NOT_RELEASED');
NODE

sql "INSERT INTO attendance_sessions(session_id,mnv,business_date,shift,work_choice,state,pda_serial,enter_at,entered_by,version,updated_at) VALUES('$CUR_SESSION','$MNV_B','$TODAY','TEST','PICK','ACTIVE','$PDA','$NOW','$LOGIN',1,'$NOW'); INSERT INTO resource_leases(resource_type,resource_id,session_id,mnv,business_date,acquired_event_id,acquired_at) VALUES('PDA','$PDA','$CUR_SESSION','$MNV_B','$TODAY','__B77_DIRECT_CUR','$NOW');"
read_api current_busy "{\"action\":\"master_options\",\"mnv\":\"$MNV_A\"}"
node - <<'NODE' "$D/current_busy.json" "$PDA"
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));if(!j.ok||j.pdas.some(x=>x.serial===process.argv[3]))throw new Error('CURRENT_ACTIVE_PDA_LEAK');
NODE

RACE_BODY=$(node - <<'NODE' "$EVENT_ID" "$MNV_A" "$TODAY" "$PDA" "$IDEM" "$DEVICE" "$NOW"
const [event_id,mnv,business_date,pda,idempotency_key,device_id,timestamp]=process.argv.slice(2);
process.stdout.write(JSON.stringify({event_id,event_type:'ATTENDANCE_ENTER',entity_type:'ATTENDANCE',entity_id:'__B77_RACE_SESSION_'+event_id,business_date,base_version:0,timestamp,payload:{mnv,shift:'TEST',work_choice:'PICK',pda_serial:pda},idempotency_key,device_id,schema_version:1,client_source:'PDA'}));
NODE
)
RACE_HTTP=$(curl -sS --connect-timeout 15 --max-time 30 -o "$D/race.json" -w '%{http_code}' -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json; charset=utf-8' --data-binary "$RACE_BODY" "$SERVICE_URL/v1/mutations")
printf '%s' "$RACE_HTTP" > "$D/race.http"
[[ "$RACE_HTTP" == 409 ]]
node - <<'NODE' "$D/race.json"
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));if(j?.error?.code!=='EXCLUSIVE_RESOURCE_CONFLICT')throw new Error('RACE_GATE_NOT_ENFORCED:'+JSON.stringify(j));
NODE

sql "DELETE FROM resource_leases WHERE resource_type='PDA' AND resource_id='$PDA'; UPDATE attendance_sessions SET state='ENDED',exit_at='$NOW',exited_by='$LOGIN',version=2,updated_at='$NOW' WHERE session_id='$CUR_SESSION';"
read_api current_released "{\"action\":\"master_options\",\"mnv\":\"$MNV_A\"}"
node - <<'NODE' "$D/current_released.json" "$PDA"
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));if(!j.ok||!j.pdas.some(x=>x.serial===process.argv[3]))throw new Error('EARLY_RETURN_PDA_NOT_RELEASED');
NODE

cleanup
CLEAN=$(npx wrangler d1 execute "$D1_NAME" --remote --config wrangler.live.jsonc --command "SELECT (SELECT COUNT(*) FROM accounts WHERE login_id='$LOGIN')+(SELECT COUNT(*) FROM employees WHERE mnv IN ('$MNV_A','$MNV_B'))+(SELECT COUNT(*) FROM resources WHERE resource_id='$PDA')+(SELECT COUNT(*) FROM attendance_sessions WHERE mnv IN ('$MNV_A','$MNV_B'))+(SELECT COUNT(*) FROM resource_leases WHERE resource_id='$PDA')+(SELECT COUNT(*) FROM events WHERE event_id='$EVENT_ID' OR idempotency_key='$IDEM') AS n;" --json)
printf '%s' "$CLEAN" > "$D/cleanup.json"
node -e 'const j=JSON.parse(process.argv[1]);if(Number(j?.[0]?.results?.[0]?.n)!==0)throw new Error("TEST_DATA_REMAINS")' "$CLEAN"

AUTH_AFTER=$(npx wrangler d1 execute "$D1_NAME" --remote --config wrangler.live.jsonc --command "SELECT authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state WHERE singleton_id=1;" --json)
printf '%s' "$AUTH_AFTER" > "$D/authority-after.json"
node - <<'NODE' "$D/authority-before.json" "$D/authority-after.json"
const fs=require('fs'),a=JSON.parse(fs.readFileSync(process.argv[2],'utf8'))?.[0]?.results?.[0],b=JSON.parse(fs.readFileSync(process.argv[3],'utf8'))?.[0]?.results?.[0];
for(const k of ['authority_epoch','authority_seq','mode','scope','service_generation'])if(String(a?.[k])!==String(b?.[k]))throw new Error('AUTHORITY_STATE_CHANGED:'+k);
NODE

jq -n --arg service_url "$SERVICE_URL" --arg source_sha "$GITHUB_SHA" --arg generation "$SERVICE_GENERATION" --argjson authority_epoch "$AUTH_EPOCH_BEFORE" --argjson authority_seq "$AUTH_SEQ_BEFORE" '{status:"PASS",source_sha:$source_sha,service_url:$service_url,generation:$generation,authority_epoch:$authority_epoch,authority_seq:$authority_seq,production_authority_unchanged:true,free_pda_visible:true,cross_day_active_pda_hidden:true,old_active_warning:true,ended_old_pda_released:true,current_active_pda_hidden:true,race_gate:"EXCLUSIVE_RESOURCE_CONFLICT",early_return_pda_released:true,test_data_cleanup:true}' > "$D/receipt.json"
trap - EXIT
rm -f wrangler.live.jsonc
echo 'beta77_service_live_gate=PASS'
