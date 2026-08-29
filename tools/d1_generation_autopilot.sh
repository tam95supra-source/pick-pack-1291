#!/usr/bin/env bash
set -Eeuo pipefail
: "${D1_NAME:?D1_NAME required}"
: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN required}"
: "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID required}"
CONFIG="${WRANGLER_CONFIG:-wrangler.live.jsonc}"
LIMITS="${PROVIDER_LIMITS:-../config/provider_free_limits.json}"
OUT="${AUTOPILOT_OUT_DIR:-/tmp/beta89-service-live/d1-autopilot}"
mkdir -p "$OUT"
ln -sfn "$(pwd)/migrations" "$OUT/migrations"
DB_LIMIT=$(jq -er '.cloudflare_workers_free.d1_database_bytes' "$LIMITS")
ACCOUNT_LIMIT=$(jq -er '.cloudflare_workers_free.d1_account_bytes' "$LIMITS")
MAX_DBS=$(jq -er '.cloudflare_workers_free.d1_database_count' "$LIMITS")
read_cfg(){ npx wrangler d1 execute "$D1_NAME" --remote --config "$CONFIG" --command "SELECT config_value FROM runtime_config WHERE config_key='$1';" --json | jq -er '.[0].results[0].config_value|tonumber'; }
WARN=$(read_cfg WARN_DB_PERCENT); PREPARE=$(read_cfg PREPARE_NEXT_DB_PERCENT); CUTOVER=$(read_cfg CUTOVER_DB_PERCENT); OWNER_TOTAL=$(read_cfg OWNER_TOTAL_QUOTA_WARN_PERCENT)
LIST=$(npx wrangler d1 list --json); COUNT=$(jq 'length' <<<"$LIST")
CURRENT_ID=$(jq -r --arg n "$D1_NAME" '.[]|select(.name==$n)|(.uuid//.id//empty)' <<<"$LIST"); test -n "$CURRENT_ID"
TOTAL=0; CURRENT=0
while IFS=$'\t' read -r name id; do
  j=$(curl -fsS -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/d1/database/$id")
  b=$(jq -r '.result.file_size // 0' <<<"$j"); TOTAL=$((TOTAL+b)); [[ "$name" == "$D1_NAME" ]] && CURRENT=$b
done < <(jq -r '.[]|[.name,(.uuid//.id)]|@tsv' <<<"$LIST")
PCT=$(awk -v b="$CURRENT" -v l="$DB_LIMIT" 'BEGIN{printf "%.4f",(b/l)*100}'); TPCT=$(awk -v b="$TOTAL" -v l="$ACCOUNT_LIMIT" 'BEGIN{printf "%.4f",(b/l)*100}')
STATE=$(awk -v p="$PCT" -v w="$WARN" -v q="$PREPARE" -v c="$CUTOVER" 'BEGIN{print p>=c?"CUTOVER_REQUIRED":p>=q?"PREPARE_REQUIRED":p>=w?"WARN":"OK"}')
jq -n --arg state "$STATE" --arg pct "$PCT" --arg tpct "$TPCT" --argjson bytes "$CURRENT" --argjson total "$TOTAL" --argjson count "$COUNT" '{status:"PASS",state:$state,db_percent:($pct|tonumber),account_percent:($tpct|tonumber),db_bytes:$bytes,account_bytes:$total,database_count:$count}' > "$OUT/receipt.json"

if [[ "$STATE" == "PREPARE_REQUIRED" || "$STATE" == "CUTOVER_REQUIRED" ]]; then
  PREPARED=$(npx wrangler d1 execute "$D1_NAME" --remote --config "$CONFIG" --command "SELECT generation_id,db_name FROM d1_generation_registry WHERE status='PREPARED' ORDER BY created_at DESC LIMIT 1;" --json | jq -r '.[0].results[0].db_name // ""')
  if [[ -z "$PREPARED" ]]; then
    (( COUNT < MAX_DBS )) || { echo "D1_PREPARE_BLOCKED_DB_COUNT" >&2; exit 32; }
    awk -v p="$TPCT" -v t="$OWNER_TOTAL" 'BEGIN{exit !(p<t)}' || { echo "D1_PREPARE_BLOCKED_TOTAL_QUOTA" >&2; exit 33; }
    NEXT="pick-pack-1291-service-gen-$(date -u +%Y%m%d%H%M%S)"
    CREATE=$(npx wrangler d1 create "$NEXT" --location apac 2>&1)
    printf '%s\n' "$CREATE" > "$OUT/create-next.log"
    NEXT_ID=$(sed -nE 's/.*database_id[[:space:]]*=[[:space:]]*"([0-9a-fA-F-]{36})".*/\1/p' "$OUT/create-next.log" | tail -n1)
    [[ -n "$NEXT_ID" ]] || NEXT_ID=$(grep -Eo '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}' "$OUT/create-next.log" | tail -n1 || true)
    [[ -n "$NEXT_ID" ]] || { cat "$OUT/create-next.log" >&2; echo D1_PREPARE_CREATE_PARSE_FAILED >&2; exit 34; }
    NEXT_CONFIG="$OUT/wrangler-next.jsonc"
    node - "$CONFIG" "$NEXT_CONFIG" "$NEXT" "$NEXT_ID" <<'NODE'
const fs=require('fs');const [input,out,name,id]=process.argv.slice(2);let s=fs.readFileSync(input,'utf8');s=s.replace(/"database_name"\s*:\s*"[^"]+"/,'"database_name": "'+name+'"').replace(/"database_id"\s*:\s*"[^"]+"/,'"database_id": "'+id+'"');fs.writeFileSync(out,s);
NODE
    npx wrangler d1 migrations apply "$NEXT" --remote --config "$NEXT_CONFIG" > "$OUT/prepare-migrations.log"
    EPOCH=$(npx wrangler d1 execute "$D1_NAME" --remote --config "$CONFIG" --command "SELECT authority_epoch FROM authority_state WHERE singleton_id=1;" --json | jq -r '.[0].results[0].authority_epoch')
    GEN="gen-$(date -u +%Y%m%d%H%M%S)"
    npx wrangler d1 execute "$D1_NAME" --remote --config "$CONFIG" --command "INSERT INTO d1_generation_registry(generation_id,db_binding,db_name,created_at,schema_version,status,authority_epoch) VALUES('$GEN','DB','$NEXT',datetime('now'),9,'PREPARED',$EPOCH);" --json > "$OUT/registry.json"
    jq --arg next "$NEXT" '.prepared_database=$next' "$OUT/receipt.json" > "$OUT/receipt.next" && mv "$OUT/receipt.next" "$OUT/receipt.json"
  fi
fi
if [[ "$STATE" == "CUTOVER_REQUIRED" ]]; then
  echo "D1_CUTOVER_REQUIRED_CONTROLLED_PIPELINE" >&2
  exit 35
fi
cat "$OUT/receipt.json"
