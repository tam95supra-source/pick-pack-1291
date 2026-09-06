#!/usr/bin/env bash
set -Eeuo pipefail

# Recovery callers may run this gate after a failed candidate migration. Make the service tree byte-exact to the base commit so candidate-only migrations cannot leak into rollback.
if [[ -n "${BASE_SERVICE_SOURCE_SHA:-}" && -n "${SERVICE_SOURCE_SHA:-}" && "$SERVICE_SOURCE_SHA" == "$BASE_SERVICE_SOURCE_SHA" ]]; then
  bash tools/restore_exact_service_tree.sh "$SERVICE_SOURCE_SHA"
fi

D=/tmp/beta78-service-live
rm -rf "$D" && mkdir -p "$D"
D1_NAME=pick-pack-1291-service-prod
OUTBOUND_SHEET_ID=1tl6har_8vGSVsVlcErfQwjX1YgvN3o-FRG5wQV4VTEM
for n in CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN; do
  test -n "${!n:-}" || { echo "MISSING_REQUIRED_SECRET:$n" >&2; exit 2; }
done
for n in CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN; do echo "::add-mask::${!n}"; done

cd service
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

npx wrangler d1 migrations apply "$D1_NAME" --remote --config wrangler.live.jsonc 2>&1 | tee "$D/migrations.log"
npx wrangler deploy --config wrangler.live.jsonc 2>&1 | tee "$D/deploy.log"
curl -fsS "$SERVICE_URL/health" > "$D/health-after.json"
jq -e --arg gen "$GEN" --argjson epoch "$EPOCH" '.ok==true and .environment=="production" and (.generation|tostring)==$gen and .authority.mode=="SERVICE_PRIMARY" and .authority.scope=="PRODUCTION" and .authority.authority_epoch==$epoch' "$D/health-after.json" >/dev/null

SUFFIX=$(printf '%s' "$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT" | sha256sum | cut -c1-10)
LOGIN="__B78_LOGIN_${SUFFIX}"; DEVICE="__B78_DEVICE_${SUFFIX}"; AUTH_SESSION="__B78_AUTH_${SUFFIX}"; VH="b78_${SUFFIX}_vh"
LOC1="__B78_LOC_${SUFFIX}"; LOC2="__B78_LOC2_${SUFFIX}"; DROP_ID="__B78_DROP_${SUFFIX}"; BASE_ID="__B78_BASE_${SUFFIX}"
EV_CREATE="__B78_LOC_CREATE_${SUFFIX}"; EV_UPDATE="__B78_LOC_UPDATE_${SUFFIX}"; EV_DELETE="__B78_LOC_DELETE_${SUFFIX}"
B80_MNV="__B80_MNV_${SUFFIX}"; B80_PDA="__B80_PDA_${SUFFIX}"; B80_ENTER="__B80_ENTER_${SUFFIX}"; B80_MUTATE="__B80_MUTATE_${SUFFIX}"; B80_EXIT="__B80_EXIT_${SUFFIX}"
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
for v in "$LOGIN" "$DEVICE" "$AUTH_SESSION" "$LOC1" "$LOC2" "$DROP_ID" "$BASE_ID" "$B80_MNV" "$B80_PDA"; do echo "::add-mask::$v"; done
SERVICE_TOKEN_SECRET=$(printf '%s' "$CLOUDFLARE_ACCOUNT_ID|$GOOGLE_OAUTH_CLIENT_SECRET|pick-pack-1291-m2-service-token-v1" | sha256sum | awk '{print $1}')
echo "::add-mask::$SERVICE_TOKEN_SECRET"
TOKEN=$(node - <<'NODE' "$SERVICE_TOKEN_SECRET" "$LOGIN" "$VH" "$AUTH_SESSION" "$DEVICE"
const c=require('crypto');const [secret,l,v,s,d]=process.argv.slice(2);const p={l,r:'SUPERADMIN',v,s,d,c:'PDA'};const enc=Buffer.from(JSON.stringify(p)).toString('base64url');process.stdout.write(enc+'.'+c.createHmac('sha256',Buffer.from(secret)).update(enc).digest('base64url'));
NODE
)
echo "::add-mask::$TOKEN"

sql(){ npx wrangler d1 execute "$D1_NAME" --remote --config wrangler.live.jsonc --command "$1" --json; }
read_api(){ local name=$1 body=$2; curl -fsS --connect-timeout 10 --max-time 20 -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "$body" "$SERVICE_URL/v1/mobile/read" > "$D/$name.json"; }
cleanup_d1(){
  set +e
  sql "DELETE FROM outbound_replication_outbox WHERE event_id IN (SELECT event_id FROM events WHERE actor_id='$LOGIN'); DELETE FROM outbound_drop_records WHERE record_id='$DROP_ID'; DELETE FROM outbound_locations WHERE location_key LIKE '__B78%'; DELETE FROM resource_daily_consumption WHERE mnv='$B80_MNV'; DELETE FROM resource_leases WHERE mnv='$B80_MNV'; DELETE FROM attendance_sessions WHERE mnv='$B80_MNV'; DELETE FROM events WHERE actor_id='$LOGIN'; DELETE FROM resources WHERE resource_id='$B80_PDA'; DELETE FROM employees WHERE mnv='$B80_MNV'; DELETE FROM auth_sessions WHERE login_id='$LOGIN'; DELETE FROM accounts WHERE login_id='$LOGIN';" >/dev/null 2>&1
  set -e
}
trap 'rc=$?; cleanup_d1; exit $rc' EXIT
cleanup_d1
sql "INSERT INTO accounts(login_id,verifier,verifier_hash,role,display_name,position,email,status,source_row,source_checksum,is_shadow_test) VALUES('$LOGIN','b78-test','$VH','SUPERADMIN','Beta78 Test','TEST','tam95.supra@gmail.com','ACTIVE',-78,'b78-test',1); INSERT INTO auth_sessions(login_id,session_id,device_id,issued_at) VALUES('$LOGIN','$AUTH_SESSION','$DEVICE','$NOW'); INSERT INTO employees(mnv,full_name,main_position,source_row,source_checksum) VALUES('$B80_MNV','Beta80 Session Fixture','Pick',-80,'b80-fixture'); INSERT INTO resources(resource_type,resource_id,status_label,available,metadata_json,source_row,source_checksum) VALUES('PDA','$B80_PDA','Tốt',1,'{}',-80,'b80-fixture');" >/dev/null

owner_api(){ local path=$1 name=$2 body=$3; curl -fsS --connect-timeout 10 --max-time 20 -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "$body" "$SERVICE_URL$path" > "$D/$name.json"; }

# Beta80 exact Service v2 contract: ENTER -> SNAPSHOT -> MUTATE -> EXIT, all on disposable D1 fixture.
owner_api /v1/session/enter-v2 b80-enter "{\"mnv\":\"$B80_MNV\",\"shift\":\"Ca 1\",\"positions\":[{\"position_key\":\"PICK\",\"position_label\":\"Pick\"}],\"resources\":[{\"resource_type\":\"PDA\",\"resource_id\":\"$B80_PDA\",\"pda_enter_status\":\"Tốt\"}],\"idempotency_key\":\"$B80_ENTER\"}"
jq -e --arg m "$B80_MNV" --arg p "$B80_PDA" '.ok==true and .session.mnv==$m and .session.state=="ACTIVE" and (.resource_assignments|map(select(.resource_type=="PDA" and .resource_id==$p and .state=="ACTIVE"))|length)==1' "$D/b80-enter.json" >/dev/null
B80_SID=$(jq -r '.session.session_id' "$D/b80-enter.json"); B80_VER=$(jq -r '.session.version' "$D/b80-enter.json")
test -n "$B80_SID" -a "$B80_SID" != null -a "$B80_VER" -gt 0

owner_api /v1/session/resources/snapshot b80-snapshot "{\"session_id\":\"$B80_SID\",\"mnv\":\"$B80_MNV\"}"
jq -e --arg sid "$B80_SID" --arg p "$B80_PDA" '.ok==true and .source=="SERVICE_D1" and .session.session_id==$sid and (.resource_assignments|map(select(.resource_type=="PDA" and .resource_id==$p))|length)==1' "$D/b80-snapshot.json" >/dev/null

owner_api /v1/session/resources/mutate b80-mutate "{\"session_id\":\"$B80_SID\",\"mnv\":\"$B80_MNV\",\"expected_version\":$B80_VER,\"idempotency_key\":\"$B80_MUTATE\",\"audit_note\":\"Beta80 route gate\",\"operations\":[{\"op\":\"UPDATE_SHIFT\",\"shift\":\"Ca 2\"}]}"
jq -e --arg sid "$B80_SID" '.ok==true and .session.session_id==$sid and .session.shift=="Ca 2" and .session.state=="ACTIVE"' "$D/b80-mutate.json" >/dev/null

owner_api /v1/session/exit-v2 b80-exit "{\"session_id\":\"$B80_SID\",\"mnv\":\"$B80_MNV\",\"pda_exit_status\":\"Tốt\",\"idempotency_key\":\"$B80_EXIT\"}"
jq -e --arg sid "$B80_SID" '.ok==true and .session.session_id==$sid and .session.state=="ENDED"' "$D/b80-exit.json" >/dev/null

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
curl -fsS -H "Authorization: Bearer $GOOGLE_TOKEN" "https://sheets.googleapis.com/v4/spreadsheets/$OUTBOUND_SHEET_ID/values/'V%E1%BB%8B%20tr%C3%AD'!A2:A" > "$D/gsheet-location-readback.json"
node - <<'NODE' "$D/gsheet-location-readback.json" "$LOC1" "$LOC2"
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),a=(j.values||[]).flat().map(String);if(a.includes(process.argv[3])||a.includes(process.argv[4]))throw new Error('TEST_LOCATION_REMAINS_IN_GSHEET');
NODE
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

jq -n --arg source_sha "$GITHUB_SHA" --arg service_url "$SERVICE_URL" --arg worker "$WORKER_NAME" --arg generation "$GEN" --argjson baseline_ms "$BASELINE_MS" --argjson service_ack_ms "$SERVICE_ACK_MS" --argjson replication_ms "$REPLICATION_MS" '{status:"PASS",source_sha:$source_sha,worker:$worker,service_url:$service_url,generation:$generation,historical_sessions:["07323dde-0456-45f8-a1d6-942e9f2e602e","03b1337f-08fd-46a1-ab94-8b0700763df3","d94d968a-0cf6-4086-8352-85154a5ec62e"],historical_result:"3/3_SERVICE_D1_EXACT",outbound:{location_crud:"PASS",duplicate:"PASS",gsheet_readback:"PASS",baseline_google_append_readback_ms:$baseline_ms,service_d1_ack_ms:$service_ack_ms,background_replication_ms:$replication_ms,dual_write:false},authority_change:"NONE",test_cleanup:"PASS"}' > "$D/receipt.json"
jq -e '.status=="PASS" and .historical_result=="3/3_SERVICE_D1_EXACT" and .outbound.duplicate=="PASS" and .outbound.gsheet_readback=="PASS"' "$D/receipt.json" >/dev/null
cat "$D/receipt.json"
