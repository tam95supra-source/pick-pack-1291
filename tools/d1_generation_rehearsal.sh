#!/usr/bin/env bash
set -Eeuo pipefail
: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN required}"
: "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID required}"
OUT="${ROLLOVER_REHEARSAL_OUT:-/tmp/beta98-d1-rollover}"
rm -rf "$OUT";mkdir -p "$OUT"
SUFFIX=$(printf '%s' "${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}-$(date +%s)"|sha256sum|cut -c1-10)
SRC="pp1291-rh-$SUFFIX-a";G2="pp1291-rh-$SUFFIX-b";G3="pp1291-rh-$SUFFIX-c"
IDS=()
cleanup(){
  set +e
  for id in "${IDS[@]:-}";do
    [[ -n "$id" ]] && curl -fsS -X DELETE -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/d1/database/$id" >/dev/null || true
  done
}
trap cleanup EXIT

LIST=$(npx wrangler d1 list --json)
COUNT=$(jq 'length'<<<"$LIST")
MAX=$(jq -er '.cloudflare_workers_free.d1_database_count' ../config/provider_free_limits.json)
(( COUNT+3 <= MAX )) || { echo "ROLLOVER_REHEARSAL_DB_QUOTA_GUARD:$COUNT/$MAX" >&2; exit 41; }

create_db(){
  local name="$1" out="$2"
  npx wrangler d1 create "$name" --location apac >"$out" 2>&1
  local id
  id=$(sed -nE 's/.*database_id[[:space:]]*=[[:space:]]*"([0-9a-fA-F-]{36})".*/\1/p' "$out" | tail -n1)
  [[ -n "$id" ]] || id=$(grep -Eo '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}' "$out" | tail -n1 || true)
  [[ -n "$id" ]] || { cat "$out" >&2; echo "ROLLOVER_CREATE_FAILED:$name" >&2; exit 42; }
  IDS+=("$id");printf '%s' "$id"
}
make_cfg(){
  local name="$1" id="$2" out="$3"
  node - "wrangler.jsonc" "$out" "$name" "$id" <<'NODE'
const fs=require('fs');const [input,out,name,id]=process.argv.slice(2);let s=fs.readFileSync(input,'utf8');
s=s.replace(/"name"\s*:\s*"[^"]+"/,'"name": "pp1291-rollover-rehearsal"')
 .replace(/"database_name"\s*:\s*"[^"]+"/,'"database_name": "'+name+'"')
 .replace(/"database_id"\s*:\s*"[^"]+"/,'"database_id": "'+id+'"');
fs.writeFileSync(out,s);
NODE
}
hash_probe(){
  local name="$1" cfg="$2"
  npx wrangler d1 execute "$name" --remote --config "$cfg" --command "SELECT id,generation,payload FROM rollover_probe ORDER BY id;" --json |
    node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{const c=require("crypto"),j=JSON.parse(s),r=j?.[0]?.results||[];process.stdout.write(c.createHash("sha256").update(JSON.stringify(r)).digest("hex"))})'
}
A_ID=$(create_db "$SRC" "$OUT/create-a.json");make_cfg "$SRC" "$A_ID" "$OUT/a.jsonc"
npx wrangler d1 migrations apply "$SRC" --remote --config "$OUT/a.jsonc" >"$OUT/a-migrations.log"
npx wrangler d1 execute "$SRC" --remote --config "$OUT/a.jsonc" --command "CREATE TABLE rollover_probe(id TEXT PRIMARY KEY,generation INTEGER NOT NULL,payload TEXT NOT NULL); INSERT INTO rollover_probe VALUES('e1',1,'alpha'),('e2',1,'beta'); UPDATE authority_state SET authority_epoch=901,authority_seq=2,mode='RECONCILING',scope='STAGING_SHADOW',service_generation='rollover-r1';" --json >"$OUT/a-seed.json"
A_HASH=$(hash_probe "$SRC" "$OUT/a.jsonc")
npx wrangler d1 export "$SRC" --remote --config "$OUT/a.jsonc" --output "$OUT/a.sql" --skip-confirmation >/dev/null

B_ID=$(create_db "$G2" "$OUT/create-b.json");make_cfg "$G2" "$B_ID" "$OUT/b.jsonc"
npx wrangler d1 execute "$G2" --remote --config "$OUT/b.jsonc" --file "$OUT/a.sql" >"$OUT/b-import.log"
B_HASH=$(hash_probe "$G2" "$OUT/b.jsonc")
[[ "$A_HASH" == "$B_HASH" ]] || { echo "ROLLOVER_1_CHECKSUM_MISMATCH" >&2; exit 43; }
B_AUTH=$(npx wrangler d1 execute "$G2" --remote --config "$OUT/b.jsonc" --command "SELECT authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state WHERE singleton_id=1;" --json)
jq -e '.[0].results[0]|.authority_epoch==901 and .authority_seq==2 and .mode=="RECONCILING" and .scope=="STAGING_SHADOW" and .service_generation=="rollover-r1"'<<<"$B_AUTH" >/dev/null
npx wrangler d1 execute "$G2" --remote --config "$OUT/b.jsonc" --command "INSERT INTO rollover_probe VALUES('e3',2,'gamma'); UPDATE authority_state SET authority_seq=3,service_generation='rollover-r2';" --json >"$OUT/b-step2.json"
B2_HASH=$(hash_probe "$G2" "$OUT/b.jsonc")
npx wrangler d1 export "$G2" --remote --config "$OUT/b.jsonc" --output "$OUT/b.sql" --skip-confirmation >/dev/null

C_ID=$(create_db "$G3" "$OUT/create-c.json");make_cfg "$G3" "$C_ID" "$OUT/c.jsonc"
npx wrangler d1 execute "$G3" --remote --config "$OUT/c.jsonc" --file "$OUT/b.sql" >"$OUT/c-import.log"
C_HASH=$(hash_probe "$G3" "$OUT/c.jsonc")
[[ "$B2_HASH" == "$C_HASH" ]] || { echo "ROLLOVER_2_CHECKSUM_MISMATCH" >&2; exit 44; }
C_AUTH=$(npx wrangler d1 execute "$G3" --remote --config "$OUT/c.jsonc" --command "SELECT authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state WHERE singleton_id=1;" --json)
jq -e '.[0].results[0]|.authority_epoch==901 and .authority_seq==3 and .mode=="RECONCILING" and .scope=="STAGING_SHADOW" and .service_generation=="rollover-r2"'<<<"$C_AUTH" >/dev/null
jq -n --arg h1 "$A_HASH" --arg h2 "$B2_HASH" '{status:"PASS",run1:{export_import_checksum:"PASS",checksum:$h1},run2:{without_cleanup_between:"PASS",export_import_checksum:"PASS",checksum:$h2},authority_checkpoint:"PASS",free_quota_guard:"PASS"}' >"$OUT/receipt.json"
cat "$OUT/receipt.json"
