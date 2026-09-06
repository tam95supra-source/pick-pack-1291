#!/usr/bin/env bash
set -Eeuo pipefail

: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN_REQUIRED}"
: "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID_REQUIRED}"
: "${GITHUB_WORKSPACE:?GITHUB_WORKSPACE_REQUIRED}"

D=${R5_RUNTIME_DIR:-/tmp/r5-beta-live-runtime}
rm -rf "$D" && mkdir -p "$D"

curl -fsS -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/scripts" > "$D/scripts.json"
curl -fsS -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/subdomain" > "$D/subdomain.json"
SUBDOMAIN=$(jq -er '.result.subdomain' "$D/subdomain.json")
: > "$D/beta.tsv"
while IFS= read -r name; do
  [[ "$name" == pick-pack-1291* || "$name" == pickpack* ]] || continue
  url="https://${name}.${SUBDOMAIN}.workers.dev"
  http=$(curl -sS --connect-timeout 10 --max-time 20 -o "$D/health-${name}.json" -w '%{http_code}' "$url/health" || printf 000)
  if [[ "$http" =~ ^2 ]] && jq -e '.ok==true and .environment=="production" and .environment_id=="BETA" and .service_audience=="PICK_PACK_1291_BETA" and .authority.mode=="SERVICE_PRIMARY" and .authority.scope=="PRODUCTION"' "$D/health-${name}.json" >/dev/null 2>&1; then
    printf '%s\t%s\n' "$name" "$url" >> "$D/beta.tsv"
  fi
done < <(jq -r '.result[]? | .id // empty' "$D/scripts.json")
[[ $(wc -l < "$D/beta.tsv") -eq 1 ]] || { echo BETA_LIVE_WORKER_MATCH_FAILED >&2; exit 4; }
IFS=$'\t' read -r WORKER_NAME SERVICE_URL < "$D/beta.tsv"
echo "::add-mask::$SERVICE_URL"

curl -fsS -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/scripts/$WORKER_NAME/settings" > "$D/settings.json"
D1_ID=$(jq -er '.result.bindings[] | select(.name=="DB" and (.type|ascii_downcase|contains("d1"))) | (.id // .database_id)' "$D/settings.json" | head -n1)
OUTBOUND_SHEET_ID=$(jq -er '.result.bindings[] | select(.name=="GOOGLE_OUTBOUND_SHEET_ID") | (.text // .value)' "$D/settings.json" | head -n1)
test -n "$D1_ID" -a -n "$OUTBOUND_SHEET_ID"
echo "::add-mask::$D1_ID"
echo "::add-mask::$OUTBOUND_SHEET_ID"

W="$GITHUB_WORKSPACE/service/node_modules/.bin/wrangler"
test -x "$W"
LIST=$($W d1 list --json)
printf '%s' "$LIST" > "$D/d1-list.json"
D1_NAME=$(node -e 'const a=JSON.parse(process.argv[1]),id=process.argv[2];const x=a.find(v=>(v.uuid||v.id)===id);process.stdout.write(String(x?.name||""))' "$LIST" "$D1_ID")
test -n "$D1_NAME" || { echo BETA_LIVE_D1_BINDING_RESOLVE_FAILED >&2; exit 5; }
echo "::add-mask::$D1_NAME"

HEALTH="$D/health-$WORKER_NAME.json"
GEN=$(jq -er '.generation|tostring' "$HEALTH")
EPOCH=$(jq -er '.authority.authority_epoch' "$HEALTH")
[[ "$GEN" != "" && "$EPOCH" =~ ^[0-9]+$ ]]

if [[ -n "${GITHUB_ENV:-}" ]]; then
  printf 'D1_NAME=%s\nOUTBOUND_SHEET_ID=%s\nR5_BETA_WORKER_NAME=%s\nR5_BETA_SERVICE_URL=%s\nR5_BETA_GENERATION=%s\nR5_BETA_AUTHORITY_EPOCH=%s\n' \
    "$D1_NAME" "$OUTBOUND_SHEET_ID" "$WORKER_NAME" "$SERVICE_URL" "$GEN" "$EPOCH" >> "$GITHUB_ENV"
fi
jq -n --arg worker "$WORKER_NAME" --arg generation "$GEN" --argjson authority_epoch "$EPOCH" '{status:"PASS",environment_id:"BETA",service_audience:"PICK_PACK_1291_BETA",worker:$worker,generation:$generation,authority_epoch:$authority_epoch}' > "$D/receipt.json"
echo r5_beta_live_runtime_resolve=PASS
