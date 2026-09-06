#!/usr/bin/env bash
set -Eeuo pipefail

: "${BASE_SERVICE_SOURCE_SHA:?BASE_SERVICE_SOURCE_SHA_REQUIRED}"
: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN_REQUIRED}"
: "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID_REQUIRED}"

D=${R5_RECOVERY_DIR:-/tmp/r5-exact-base-service-recovery}
rm -rf "$D" && mkdir -p "$D"
BASE="$BASE_SERVICE_SOURCE_SHA"
git cat-file -e "$BASE^{commit}"
test "$(jq -r '.base_source_sha' ops/beta-release-request.json)" = "$BASE"
test "$(jq -r '.live' ops/beta-release-request.json)" = false

rm -rf service
git checkout "$BASE" -- service
git diff --quiet "$BASE" -- service
npm --prefix service install --include=dev --ignore-scripts --no-audit --no-fund
test -d service/node_modules/fflate
test -x service/node_modules/.bin/wrangler
npm --prefix service run check

curl -fsS -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/scripts" > "$D/scripts.json"
curl -fsS -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/subdomain" > "$D/subdomain.json"
SUBDOMAIN=$(jq -er '.result.subdomain' "$D/subdomain.json")
: > "$D/healthy.tsv"
while IFS= read -r name; do
  [[ "$name" == pick-pack-1291* || "$name" == pickpack* ]] || continue
  url="https://${name}.${SUBDOMAIN}.workers.dev"
  http=$(curl -sS --connect-timeout 10 --max-time 20 -o "$D/health-${name}.json" -w '%{http_code}' "$url/health" || printf 000)
  if [[ "$http" =~ ^2 ]] && jq -e '.ok==true and .environment=="production" and .environment_id=="BETA" and .service_audience=="PICK_PACK_1291_BETA" and .authority.mode=="SERVICE_PRIMARY" and .authority.scope=="PRODUCTION"' "$D/health-${name}.json" >/dev/null 2>&1; then
    printf '%s\t%s\n' "$name" "$url" >> "$D/healthy.tsv"
  fi
done < <(jq -r '.result[]? | .id // empty' "$D/scripts.json")
[[ $(wc -l < "$D/healthy.tsv") -eq 1 ]] || { echo LIVE_BETA_WORKER_MATCH_FAILED >&2; exit 4; }
IFS=$'\t' read -r WORKER_NAME SERVICE_URL < "$D/healthy.tsv"
echo "::add-mask::$SERVICE_URL"

curl -fsS -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/scripts/$WORKER_NAME/settings" > "$D/worker-settings.json"
D1_ID=$(jq -er '.result.bindings[] | select(.name=="DB" and (.type|ascii_downcase|contains("d1"))) | (.id // .database_id)' "$D/worker-settings.json" | head -n1)
echo "::add-mask::$D1_ID"

cd service
W=./node_modules/.bin/wrangler
test -x "$W"
LIST=$($W d1 list --json)
printf '%s' "$LIST" > "$D/d1-list.json"
D1_NAME=$(node -e 'const a=JSON.parse(process.argv[1]),id=process.argv[2];const x=a.find(v=>(v.uuid||v.id)===id);process.stdout.write(String(x?.name||""))' "$LIST" "$D1_ID")
test -n "$D1_NAME" || { echo LIVE_D1_BINDING_RESOLVE_FAILED >&2; exit 5; }
echo "::add-mask::$D1_NAME"

AUTH_BEFORE=$($W d1 execute "$D1_NAME" --remote --command "SELECT authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state WHERE singleton_id=1;" --json)
printf '%s' "$AUTH_BEFORE" > "$D/authority-before.json"
GEN=$(node -e 'const j=JSON.parse(process.argv[1]),r=j?.[0]?.results?.[0];if(!r||r.mode!=="SERVICE_PRIMARY"||r.scope!=="PRODUCTION")process.exit(2);process.stdout.write(String(r.service_generation||""))' "$AUTH_BEFORE")
EPOCH=$(node -e 'const j=JSON.parse(process.argv[1]);process.stdout.write(String(j?.[0]?.results?.[0]?.authority_epoch??""))' "$AUTH_BEFORE")
test -n "$GEN" -a -n "$EPOCH"
jq -e --arg gen "$GEN" --argjson epoch "$EPOCH" '.ok==true and .environment_id=="BETA" and .service_audience=="PICK_PACK_1291_BETA" and (.generation|tostring)==$gen and .authority.authority_epoch==$epoch and .authority.mode=="SERVICE_PRIMARY" and .authority.scope=="PRODUCTION"' "$D/health-$WORKER_NAME.json" >/dev/null

python3 - "$D1_ID" "$D1_NAME" "$GEN" "$WORKER_NAME" <<'PY'
from pathlib import Path
import sys
d1_id,d1_name,generation,name=sys.argv[1:]
p=Path('wrangler.jsonc'); s=p.read_text(encoding='utf-8')
repls={
  '"name": "pick-pack-1291-service-m1-staging"':f'"name": "{name}"',
  '"SERVICE_GENERATION": "m2-precutover-20260819-001"':f'"SERVICE_GENERATION": "{generation}"',
  '"database_name": "pick-pack-1291-m1-staging"':f'"database_name": "{d1_name}"',
  '"database_id": "__M1_D1_DATABASE_ID__"':f'"database_id": "{d1_id}"',
}
for old,new in repls.items():
    if old not in s: raise SystemExit('LIVE_CONFIG_ANCHOR_MISSING:'+old)
    s=s.replace(old,new,1)
Path('wrangler.live.jsonc').write_text(s,encoding='utf-8')
PY

$W d1 migrations apply "$D1_NAME" --remote --config wrangler.live.jsonc 2>&1 | tee "$D/migrations.log"
$W deploy --config wrangler.live.jsonc 2>&1 | tee "$D/deploy.log"
curl -fsS --retry 4 --retry-all-errors --retry-delay 1 "$SERVICE_URL/health" > "$D/health-after.json"
jq -e --arg gen "$GEN" --argjson epoch "$EPOCH" '.ok==true and .environment=="production" and .environment_id=="BETA" and .service_audience=="PICK_PACK_1291_BETA" and (.generation|tostring)==$gen and .authority.mode=="SERVICE_PRIMARY" and .authority.scope=="PRODUCTION" and .authority.authority_epoch==$epoch' "$D/health-after.json" >/dev/null
AUTH_AFTER=$($W d1 execute "$D1_NAME" --remote --config wrangler.live.jsonc --command "SELECT authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state WHERE singleton_id=1;" --json)
printf '%s' "$AUTH_AFTER" > "$D/authority-after.json"
node - <<'NODE' "$D/authority-before.json" "$D/authority-after.json"
const fs=require('fs'); const a=JSON.parse(fs.readFileSync(process.argv[2],'utf8'))[0].results[0],b=JSON.parse(fs.readFileSync(process.argv[3],'utf8'))[0].results[0];
if(a.authority_epoch!==b.authority_epoch||a.mode!==b.mode||a.scope!==b.scope||a.service_generation!==b.service_generation)throw new Error('AUTHORITY_RECOVERY_DRIFT');
NODE
printf '%s\n' '{"status":"PASS","recovery":"EXACT_BASE_SERVICE","source_sha":"'"$BASE"'"}' > "$D/receipt.json"
echo exact_base_service_recovery=PASS
