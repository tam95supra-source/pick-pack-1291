#!/usr/bin/env bash
set -Eeuo pipefail
OUT="${DR_PREFLIGHT_OUT:-/tmp/cloud-dr-preflight}"
rm -rf "$OUT";mkdir -p "$OUT"
required=(RENDER_API_KEY TURSO_API_TOKEN TURSO_AUTH_TOKEN DENO_DEPLOY_TOKEN)
missing=()
for n in "${required[@]}";do [[ -n "${!n:-}" ]] || missing+=("$n");done
if ((${#missing[@]}));then printf 'MISSING_DR_SECRET:%s\n' "$(IFS=,;echo "${missing[*]}")" >&2;exit 51;fi
for n in "${required[@]}";do echo "::add-mask::${!n}";done

http(){
  local name="$1" url="$2" token="$3"
  local code
  code=$(curl -sS --connect-timeout 10 --max-time 30 -o "$OUT/$name.json" -w '%{http_code}' -H "Authorization: Bearer $token" -H 'Accept: application/json' "$url" || true)
  [[ "$code" == 200 ]] || { echo "DR_PREFLIGHT_HTTP_FAILED:$name:$code" >&2;exit 52; }
}

http render-services "https://api.render.com/v1/services?limit=100" "$RENDER_API_KEY"
node - "$OUT/render-services.json" <<'NODE'
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));const rows=Array.isArray(j)?j:(j.items||[]);
const matches=rows.map(x=>x.service||x).filter(x=>/pick.?pack.?1291.*dr/i.test(String(x.name||'')));
for(const x of matches){const d=x.serviceDetails||x.service_details||{},plan=String(d.plan||x.plan||'').toLowerCase(),region=String(d.region||x.region||'').toLowerCase();if(plan&&plan!=='free')throw new Error('RENDER_DR_NOT_FREE:'+plan);if(region&&!region.includes('singapore'))throw new Error('RENDER_DR_REGION_NOT_SINGAPORE:'+region);}
console.log('render_token=PASS existing_dr='+matches.length);
NODE

http turso-validate "https://api.turso.tech/v1/auth/validate" "$TURSO_API_TOKEN"

# Prefer explicit non-secret config. Org-scoped Turso platform tokens may intentionally
# return 403 for account-wide organization listing, so derive a candidate without weakening auth.
TURSO_ORG="${TURSO_ORGANIZATION:-}"
if [[ -z "$TURSO_ORG" ]]; then
  TURSO_ORG=$(node - "$OUT/turso-validate.json" "$TURSO_API_TOKEN" <<'NODE'
const fs=require('fs');
const v=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),token=process.argv[3]||'';
let payload={};try{const p=token.split('.')[1];if(p)payload=JSON.parse(Buffer.from(p.replace(/-/g,'+').replace(/_/g,'/'),'base64').toString('utf8'));}catch{}
const candidates=[
  v.organization_slug,v.organizationSlug,v.organization,v.org,
  payload.organization_slug,payload.organizationSlug,payload.organization,payload.org,payload.org_slug,payload.o
].map(x=>String(x||'').trim()).filter(Boolean);
process.stdout.write(candidates[0]||'');
NODE
  )
fi

if [[ -z "$TURSO_ORG" ]]; then
  # An org-scoped platform token can legitimately reject organization metadata.
  # Discover only candidate slugs, then accept a slug solely if Turso allows DB listing for it.
  candidates=()
  if [[ -n "${GITHUB_REPOSITORY:-}" ]]; then
    candidates+=("${GITHUB_REPOSITORY%%/*}" "${GITHUB_REPOSITORY##*/}")
  fi
  [[ -n "${GITHUB_ACTOR:-}" ]] && candidates+=("$GITHUB_ACTOR")

  code=$(curl -sS --connect-timeout 10 --max-time 30 -o "$OUT/turso-api-tokens.json" -w '%{http_code}'     -H "Authorization: Bearer $TURSO_API_TOKEN" -H 'Accept: application/json' "https://api.turso.tech/v1/auth/api-tokens" || true)
  if [[ "$code" == 200 ]]; then
    while IFS= read -r cand; do [[ -n "$cand" ]] && candidates+=("$cand"); done < <(
      node - "$OUT/turso-api-tokens.json" <<'NODE'
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
for(const o of [...new Set((j.tokens||[]).map(x=>String(x.organization||'').trim()).filter(Boolean))])console.log(o);
NODE
    )
  elif [[ "$code" != 403 ]]; then
    echo "DR_PREFLIGHT_HTTP_FAILED:turso-api-tokens:$code" >&2; exit 52
  fi

  # Account-wide listing is another non-authoritative source of candidate slugs.
  code=$(curl -sS --connect-timeout 10 --max-time 30 -o "$OUT/turso-organizations.json" -w '%{http_code}'     -H "Authorization: Bearer $TURSO_API_TOKEN" -H 'Accept: application/json' "https://api.turso.tech/v1/organizations" || true)
  if [[ "$code" == 200 ]]; then
    while IFS= read -r cand; do [[ -n "$cand" ]] && candidates+=("$cand"); done < <(
      node - "$OUT/turso-organizations.json" <<'NODE'
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),rows=Array.isArray(j)?j:(j.organizations||[]);
for(const o of rows)if(o.blocked_reads!==true&&o.blocked_writes!==true&&String(o.slug||'').trim())console.log(String(o.slug).trim());
NODE
    )
  elif [[ "$code" != 403 ]]; then
    echo "DR_PREFLIGHT_HTTP_FAILED:turso-organizations:$code" >&2; exit 52
  fi

  : > "$OUT/turso-candidates-seen.txt"
  for cand in "${candidates[@]}"; do
    [[ -n "$cand" ]] || continue
    grep -Fxq "$cand" "$OUT/turso-candidates-seen.txt" 2>/dev/null && continue
    printf '%s\n' "$cand" >> "$OUT/turso-candidates-seen.txt"
    code=$(curl -sS --connect-timeout 10 --max-time 30 -o "$OUT/turso-db-candidate.json" -w '%{http_code}'       -H "Authorization: Bearer $TURSO_API_TOKEN" -H 'Accept: application/json' "https://api.turso.tech/v1/organizations/$cand/databases?limit=100" || true)
    if [[ "$code" == 200 ]] && jq -e '.databases|type=="array"' "$OUT/turso-db-candidate.json" >/dev/null; then
      TURSO_ORG="$cand"; cp "$OUT/turso-db-candidate.json" "$OUT/turso-databases.json"; break
    fi
  done
fi


# If a database URL is already provisioned, validate the DB credential directly; this is
# sufficient for a passive DR store even when the platform token is org-scoped/opaque.
if [[ -n "${TURSO_DATABASE_URL:-}" ]]; then
  pushd services/cloud-dr >/dev/null
  TURSO_DATABASE_URL="$TURSO_DATABASE_URL" TURSO_AUTH_TOKEN="$TURSO_AUTH_TOKEN" node --input-type=module <<'NODE'
import {createClient} from '@libsql/client';
const c=createClient({url:process.env.TURSO_DATABASE_URL,authToken:process.env.TURSO_AUTH_TOKEN});
const r=await c.execute('SELECT 1 AS ok');c.close();
if(Number(r.rows?.[0]?.ok)!==1)throw new Error('TURSO_DATABASE_AUTH_READBACK_FAILED');
console.log('turso_database_token=PASS source=preprovisioned');
NODE
  popd >/dev/null
  TURSO_DB_AUTH_OK=1
else
  TURSO_DB_AUTH_OK=0
fi

if [[ -n "$TURSO_ORG" ]]; then
  ZERO_COST_PLANS=$(jq -cr '.turso.accepted_zero_cost_plan_ids // ["free","starter"]' config/provider_free_limits.json)
  sub_code=$(curl -sS --connect-timeout 10 --max-time 30 -o "$OUT/turso-subscription.json" -w '%{http_code}'     -H "Authorization: Bearer $TURSO_API_TOKEN" -H 'Accept: application/json' "https://api.turso.tech/v1/organizations/$TURSO_ORG/subscription" || true)
  if [[ "$sub_code" == 200 ]]; then
    node - "$OUT/turso-subscription.json" "$ZERO_COST_PLANS" <<'NODE'
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),allowed=new Set(JSON.parse(process.argv[3]).map(x=>String(x).toLowerCase())),s=j.subscription||j;
const plan=String(s.plan||s.name||'').toLowerCase();
if(!plan||!allowed.has(plan)||s.overages===true)throw new Error('TURSO_CURRENT_SUBSCRIPTION_NOT_ZERO_COST:'+plan);
console.log('turso_subscription=PASS plan='+plan+' overages=false');
NODE
  else
    # Organization-scoped tokens may reject /subscription while still allowing the
    # canonical organization readback. Turso's organization object exposes current
    # plan_id and overages, which is sufficient for the zero-cost guard.
    org_code=$(curl -sS --connect-timeout 10 --max-time 30 -o "$OUT/turso-organization.json" -w '%{http_code}' \
      -H "Authorization: Bearer $TURSO_API_TOKEN" -H 'Accept: application/json' \
      "https://api.turso.tech/v1/organizations/$TURSO_ORG" || true)
    if [[ "$org_code" != 200 ]]; then
      echo "TURSO_BILLING_METADATA_UNAVAILABLE:subscription=$sub_code:organization=$org_code" >&2
      exit 54
    fi
    node - "$OUT/turso-organization.json" "$ZERO_COST_PLANS" <<'NODE'
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),allowed=new Set(JSON.parse(process.argv[3]).map(x=>String(x).toLowerCase())),o=j.organization||j;
const plan=String(o.plan_id||o.plan||'').toLowerCase(),overages=o.overages===true;
if(!plan||!allowed.has(plan)||overages)throw new Error('TURSO_ORGANIZATION_NOT_ZERO_COST:'+plan+':overages='+overages);
console.log('turso_subscription=PASS source=organization plan='+plan+' overages=false');
NODE
  fi
  [[ -f "$OUT/turso-databases.json" ]] || curl -fsS --connect-timeout 10 --max-time 30     -H "Authorization: Bearer $TURSO_API_TOKEN" "https://api.turso.tech/v1/organizations/$TURSO_ORG/databases?limit=100" > "$OUT/turso-databases.json"
elif [[ "$TURSO_DB_AUTH_OK" != 1 ]]; then
  echo "TURSO_PLATFORM_TOKEN_VALID_BUT_ORG_SCOPE_UNRESOLVED" >&2
  exit 53
fi

if [[ "$TURSO_DB_AUTH_OK" != 1 ]]; then
  [[ -f "$OUT/turso-databases.json" ]] || { echo "TURSO_DATABASE_LIST_UNAVAILABLE" >&2; exit 53; }
  pushd services/cloud-dr >/dev/null
  TURSO_AUTH_TOKEN="$TURSO_AUTH_TOKEN" TURSO_DATABASES_JSON="$OUT/turso-databases.json" node --input-type=module <<'NODE'
import fs from 'node:fs';import {createClient} from '@libsql/client';
const j=JSON.parse(fs.readFileSync(process.env.TURSO_DATABASES_JSON,'utf8')),rows=j.databases||[];let ok=null,last='';
for(const x of rows){const host=String(x.Hostname||x.hostname||'');if(!host)continue;try{const c=createClient({url:'libsql://'+host,authToken:process.env.TURSO_AUTH_TOKEN});const r=await c.execute('SELECT 1 AS ok');c.close();if(Number(r.rows?.[0]?.ok)!==1)continue;ok={name:String(x.Name||x.name||''),host};break}catch(e){last=String(e?.message||e).slice(0,120)}}
if(!ok)throw new Error('TURSO_AUTH_TOKEN_NO_DATABASE_MATCH:'+last);
console.log('turso_database_token=PASS database='+ok.name);
NODE
  popd >/dev/null
fi

http deno-apps "https://api.deno.com/v2/apps?limit=100" "$DENO_DEPLOY_TOKEN"
node - "$OUT/deno-apps.json" <<'NODE'
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),rows=Array.isArray(j)?j:(j.items||j.apps||[]);if(!Array.isArray(rows))throw new Error('DENO_APPS_RESPONSE_INVALID');console.log('deno_token=PASS existing_apps='+rows.length);
NODE
jq -n '{status:"PASS",secrets:"4/4_VALIDATED",render_token:"PASS",turso_platform_token:"PASS",turso_database_token:"PASS",deno_token:"PASS",no_secret_output:true,no_paid_action:true}' > "$OUT/receipt.json"
cat "$OUT/receipt.json"
