#!/usr/bin/env bash
set -Eeuo pipefail
: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN required}"
: "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID required}"
LIMITS="${PROVIDER_LIMITS:-config/provider_free_limits.json}"

node - "$LIMITS" <<'NODE'
const fs=require("fs"),x=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
const verified=Date.parse(String(x.verified_at||"")+"T00:00:00Z"),maxAge=Number(x.max_age_days);
if(x.schema_version!==1||!Number.isFinite(verified)||!Number.isInteger(maxAge)||maxAge<1)throw new Error("PROVIDER_LIMIT_AUTHORITY_INVALID");
const age=Date.now()-verified;
if(age < -86400000 || age > maxAge*86400000)throw new Error("PROVIDER_LIMIT_AUTHORITY_STALE");
for(const k of ["d1_database_bytes","d1_account_bytes","d1_database_count"]){
  const n=Number(x.cloudflare_workers_free?.[k]);
  if(!Number.isInteger(n)||n<1)throw new Error("CF_D1_LIMIT_INVALID:"+k);
}
console.log("provider_limit_authority=PASS");
NODE

MAX_DBS=$(jq -er '.cloudflare_workers_free.d1_database_count' "$LIMITS")
DB_LIMIT=$(jq -er '.cloudflare_workers_free.d1_database_bytes' "$LIMITS")
ACCOUNT_LIMIT=$(jq -er '.cloudflare_workers_free.d1_account_bytes' "$LIMITS")
API="https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID"
AUTH=(-H "Authorization: Bearer $CLOUDFLARE_API_TOKEN")

curl -fsS "${AUTH[@]}" "$API/d1/database?per_page=100" > /tmp/d1-inventory.json
jq -e '.success==true and (.result|type=="array")' /tmp/d1-inventory.json >/dev/null
COUNT=$(jq '.result|length' /tmp/d1-inventory.json)
(( COUNT <= MAX_DBS )) || { echo "D1_DATABASE_COUNT_EXCEEDS_AUTHORITY:$COUNT/$MAX_DBS"; exit 31; }

TOTAL=0
while IFS= read -r row; do
  decoded=$(printf '%s' "$row" | base64 --decode)
  name=$(jq -r '.[0]' <<<"$decoded")
  id=$(jq -r '.[1]' <<<"$decoded")
  [[ -n "$id" ]] || { echo "D1_ID_MISSING:$name"; exit 32; }
  enc=$(jq -rn --arg v "$id" '$v|@uri')
  curl -fsS "${AUTH[@]}" "$API/d1/database/$enc" > /tmp/d1-one.json
  jq -e '.success==true' /tmp/d1-one.json >/dev/null
  bytes=$(jq -r '.result.file_size // 0' /tmp/d1-one.json)
  [[ "$bytes" =~ ^[0-9]+$ ]] || { echo "D1_SIZE_INVALID:$name"; exit 33; }
  (( bytes <= DB_LIMIT )) || { echo "D1_DATABASE_BYTES_EXCEED_AUTHORITY:$name:$bytes/$DB_LIMIT"; exit 34; }
  TOTAL=$((TOTAL+bytes))
done < <(jq -r '.result[]|[(.name//"UNKNOWN"),(.uuid//.id//"")]|@base64' /tmp/d1-inventory.json)

(( TOTAL <= ACCOUNT_LIMIT )) || { echo "D1_ACCOUNT_BYTES_EXCEED_AUTHORITY:$TOTAL/$ACCOUNT_LIMIT"; exit 35; }
SLOT=false
(( COUNT < MAX_DBS )) && SLOT=true
jq -n --argjson count "$COUNT" --argjson max "$MAX_DBS" --argjson bytes "$TOTAL" --argjson accountMax "$ACCOUNT_LIMIT" --arg slot "$SLOT"   '{status:"PASS",quota_authority:"config/provider_free_limits.json",d1_database_count:$count,d1_database_max:$max,d1_account_bytes:$bytes,d1_account_max:$accountMax,stable_d1_slot_available:($slot=="true")}' > /tmp/provider-capacity-inventory.json
cat /tmp/provider-capacity-inventory.json
