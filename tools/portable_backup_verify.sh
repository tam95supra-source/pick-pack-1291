#!/usr/bin/env bash
set -Eeuo pipefail
: "${D1_NAME:?D1_NAME required}"
CONFIG="${WRANGLER_CONFIG:-wrangler.live.jsonc}"
OUT="${BACKUP_OUT_DIR:-/tmp/beta89-service-live/portable-backup}"
mkdir -p "$OUT"
SQL="$OUT/database.sql"; SRC="$OUT/source.json"; DB="$OUT/restored.sqlite"; MANIFEST="$OUT/manifest.json"
rm -f "$SQL" "$SRC" "$DB" "$MANIFEST"

npx wrangler d1 export "$D1_NAME" --remote --config "$CONFIG" --output "$SQL" --skip-confirmation >/dev/null
test -s "$SQL"
EXPORT_SHA=$(sha256sum "$SQL" | awk '{print $1}')
SOURCE_QUERY="SELECT COUNT(*) n FROM events; SELECT COUNT(*) n FROM attendance_sessions; SELECT COUNT(*) n FROM labor_sessions; SELECT COUNT(*) n FROM resources; SELECT COUNT(*) n FROM accounts; SELECT COUNT(*) n FROM business_dates; SELECT event_id,authority_epoch,authority_seq,checksum FROM events ORDER BY authority_epoch,authority_seq,event_id; SELECT authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state WHERE singleton_id=1; SELECT MIN(business_date) first_business_date,MAX(business_date) last_business_date FROM business_dates; SELECT event_id first_event FROM events ORDER BY committed_at,event_id LIMIT 1; SELECT event_id last_event FROM events ORDER BY committed_at DESC,event_id DESC LIMIT 1;"
npx wrangler d1 execute "$D1_NAME" --remote --config "$CONFIG" --command "$SOURCE_QUERY" --json > "$SRC"
sqlite3 "$DB" < "$SQL"

node - "$SRC" "$DB" "$MANIFEST" "$EXPORT_SHA" <<'NODE'
const fs=require('fs'),crypto=require('crypto'),cp=require('child_process');
const [srcP,dbP,manP,exportSha]=process.argv.slice(2);
const src=JSON.parse(fs.readFileSync(srcP,'utf8')).map(x=>x.results||[]);
const q=s=>JSON.parse(cp.execFileSync('sqlite3',['-json',dbP,s],{encoding:'utf8'})||'[]');
const dst=[
 q('SELECT COUNT(*) n FROM events'),q('SELECT COUNT(*) n FROM attendance_sessions'),q('SELECT COUNT(*) n FROM labor_sessions'),
 q('SELECT COUNT(*) n FROM resources'),q('SELECT COUNT(*) n FROM accounts'),q('SELECT COUNT(*) n FROM business_dates'),
 q('SELECT event_id,authority_epoch,authority_seq,checksum FROM events ORDER BY authority_epoch,authority_seq,event_id'),
 q('SELECT authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state WHERE singleton_id=1'),
 q('SELECT MIN(business_date) first_business_date,MAX(business_date) last_business_date FROM business_dates'),
 q('SELECT event_id first_event FROM events ORDER BY committed_at,event_id LIMIT 1'),
 q('SELECT event_id last_event FROM events ORDER BY committed_at DESC,event_id DESC LIMIT 1')
];
for(let i=0;i<6;i++)if(Number(src[i]?.[0]?.n)!==Number(dst[i]?.[0]?.n))throw new Error('BACKUP_COUNT_MISMATCH_'+i);
const stable=x=>JSON.stringify(x.map(r=>Object.fromEntries(Object.entries(r).map(([k,v])=>[k,String(v??'')]))));
const hash=x=>crypto.createHash('sha256').update(stable(x)).digest('hex');
const eventChecksum=hash(src[6]||[]);
if(eventChecksum!==hash(dst[6]||[]))throw new Error('BACKUP_EVENT_CHECKSUM_MISMATCH');
if(stable(src[7]||[])!==stable(dst[7]||[]))throw new Error('BACKUP_CHECKPOINT_MISMATCH');
const bd=src[8]?.[0]||{},authority=src[7]?.[0]||{};
if(!bd.first_business_date||!bd.last_business_date)throw new Error('BACKUP_BUSINESS_DATE_RANGE_MISSING');
const counts={events:Number(src[0]?.[0]?.n||0),attendance_sessions:Number(src[1]?.[0]?.n||0),labor_sessions:Number(src[2]?.[0]?.n||0),resources:Number(src[3]?.[0]?.n||0),accounts:Number(src[4]?.[0]?.n||0),business_dates:Number(src[5]?.[0]?.n||0)};
const created=new Date().toISOString();
const m={status:'VERIFIED',created_at:created,source:'CLOUDFLARE_D1',schema_version:9,first_event:String(src[9]?.[0]?.first_event||''),last_event:String(src[10]?.[0]?.last_event||''),first_business_date:String(bd.first_business_date),last_business_date:String(bd.last_business_date),row_counts:counts,table_counts:counts,checksum:exportSha,event_checksum:eventChecksum,checkpoint:{authority_epoch:Number(authority.authority_epoch||0),authority_seq:Number(authority.authority_seq||0),mode:String(authority.mode||''),scope:String(authority.scope||''),service_generation:String(authority.service_generation||'')}};
m.backup_id='d1-'+created.replace(/[-:.TZ]/g,'').slice(0,14)+'-'+exportSha.slice(0,12);
fs.writeFileSync(manP,JSON.stringify(m,null,2)+'\n');
NODE

BACKUP_ID=$(jq -r .backup_id "$MANIFEST"); CREATED=$(jq -r .created_at "$MANIFEST"); FIRST_EVENT=$(jq -r .first_event "$MANIFEST"); LAST_EVENT=$(jq -r .last_event "$MANIFEST"); FIRST_DATE=$(jq -r .first_business_date "$MANIFEST"); LAST_DATE=$(jq -r .last_business_date "$MANIFEST"); CHECKSUM=$(jq -r .checksum "$MANIFEST")
CHECKPOINT=$(jq -c .checkpoint "$MANIFEST" | sed "s/'/''/g"); ROWS=$(jq -c .row_counts "$MANIFEST" | sed "s/'/''/g"); TABLES=$(jq -c .table_counts "$MANIFEST" | sed "s/'/''/g")
npx wrangler d1 execute "$D1_NAME" --remote --config "$CONFIG" --command "INSERT INTO backup_manifests(backup_id,created_at,source,first_event,last_event,first_business_date,last_business_date,row_counts_json,table_counts_json,checksum,schema_version,checkpoint,status,verified_at) VALUES('$BACKUP_ID','$CREATED','CLOUDFLARE_D1','$FIRST_EVENT','$LAST_EVENT','$FIRST_DATE','$LAST_DATE','$ROWS','$TABLES','$CHECKSUM',9,'$CHECKPOINT','VERIFIED','$CREATED') ON CONFLICT(backup_id) DO UPDATE SET status='VERIFIED',verified_at=excluded.verified_at;" --json > "$OUT/register.json"
jq -e '.[0].success==true' "$OUT/register.json" >/dev/null
sqlite3 "$DB" "SELECT COUNT(*) FROM events; SELECT authority_epoch||':'||authority_seq||':'||mode||':'||service_generation FROM authority_state WHERE singleton_id=1;" > "$OUT/representative-read.txt"
test -s "$OUT/representative-read.txt"
echo "portable_backup=PASS"
