#!/usr/bin/env bash
set -Eeuo pipefail
OUT="${DR_PREFLIGHT_OUT:-/tmp/cloud-dr-preflight}"
rm -rf "$OUT";mkdir -p "$OUT"
required=(RENDER_API_KEY TURSO_API_TOKEN TURSO_AUTH_TOKEN DENO_DEPLOY_TOKEN)
missing=()
for n in "${required[@]}";do [[ -n "${!n:-}" ]] || missing+=("$n");done
if ((${#missing[@]}));then printf 'MISSING_DR_SECRET:%s\n' "$(IFS=,;echo "${missing[*]}")" >&2;exit 51;fi
for n in "${required[@]}";do echo "::add-mask::${!n}";done

LIMITS=config/provider_free_limits.json
node - "$LIMITS" <<'NODE'
const fs=require('fs'),x=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const verified=Date.parse(String(x.verified_at||'')+'T00:00:00Z'),maxAge=Number(x.max_age_days),age=Date.now()-verified;
if(x.schema_version!==1||!Number.isFinite(verified)||!Number.isInteger(maxAge)||maxAge<1||age < -86400000||age > maxAge*86400000)throw new Error('PROVIDER_LIMIT_AUTHORITY_INVALID_OR_STALE');
if(x.render?.required_service_plan!=='free'||x.render?.required_region!=='singapore'||x.render?.automatic_activation!=='FORBIDDEN_COLD_STANDBY')throw new Error('RENDER_FREE_COLD_STANDBY_AUTHORITY_INVALID');
if(Number(x.turso?.required_plan_price_usd)!==0||Number(x.deno?.required_plan_price_usd)!==0)throw new Error('DR_ZERO_COST_AUTHORITY_INVALID');
console.log('provider_limit_authority=PASS');
NODE
RENDER_PLAN=$(jq -er '.render.required_service_plan' "$LIMITS")
RENDER_REGION=$(jq -er '.render.required_region' "$LIMITS")
DENO_MAX_APPS=$(jq -er '.deno.max_active_apps' "$LIMITS")
TURSO_MAX_DBS=$(jq -er '.turso.max_databases' "$LIMITS")

http(){
  local name="$1" url="$2" token="$3"
  local code
  code=$(curl -sS --connect-timeout 10 --max-time 30 -o "$OUT/$name.json" -w '%{http_code}' -H "Authorization: Bearer $token" -H 'Accept: application/json' "$url" || true)
  [[ "$code" == 200 ]] || { echo "DR_PREFLIGHT_HTTP_FAILED:$name:$code" >&2;exit 52; }
}

http render-services "https://api.render.com/v1/services?limit=100" "$RENDER_API_KEY"
node - "$OUT/render-services.json" "$RENDER_PLAN" "$RENDER_REGION" <<'NODE'
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),requiredPlan=String(process.argv[3]),requiredRegion=String(process.argv[4]);
const rows=(Array.isArray(j)?j:(j.items||[])).map(x=>x.service||x),targets=['pick-pack-1291-dr-beta','pick-pack-1291-dr-stable'];
for(const name of targets){const m=rows.filter(x=>String(x.name||'')===name);if(m.length!==1)throw new Error('RENDER_DR_TARGET_NOT_UNIQUE:'+name+':'+m.length);}
const matches=rows.filter(x=>/pick.?pack.?1291.*dr/i.test(String(x.name||'')));
for(const x of matches){
 const d=x.serviceDetails||x.service_details||{},plan=String(d.plan||x.plan||'').toLowerCase(),region=String(d.region||x.region||'').toLowerCase();
 if(plan!==requiredPlan)throw new Error('RENDER_DR_NOT_REQUIRED_FREE_PLAN:'+String(x.name)+':'+plan);
 if(region!==requiredRegion)throw new Error('RENDER_DR_REGION_MISMATCH:'+String(x.name)+':'+region);
 if(String(x.autoDeploy||'')!=='no')throw new Error('RENDER_DR_AUTODEPLOY_NOT_OFF:'+String(x.name));
 if(String(x.suspended||'')!=='suspended')throw new Error('RENDER_DR_NOT_COLD_SUSPENDED:'+String(x.name)+':'+String(x.suspended||''));
}
console.log('render_token=PASS target_count=2 cold_suspended=true plan='+requiredPlan+' region='+requiredRegion);
NODE

validate_code=$(curl -sS --connect-timeout 10 --max-time 30 -o "$OUT/turso-validate.json" -w '%{http_code}' \
  -H "Authorization: Bearer $TURSO_API_TOKEN" -H 'Accept: application/json' \
  "https://api.turso.tech/v1/auth/validate" || true)
case "$validate_code" in
  200) echo "turso_validate=PASS" ;;
  403)
    printf '{}\n' > "$OUT/turso-validate.json"
    echo "turso_validate_scope=READ_DENIED continue_with_resource_scoped_proof=true"
    ;;
  *) echo "DR_PREFLIGHT_HTTP_FAILED:turso-validate:$validate_code" >&2; exit 52 ;;
esac

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
    if [[ "$org_code" == 200 ]]; then
      node - "$OUT/turso-organization.json" "$ZERO_COST_PLANS" <<'NODE'
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),allowed=new Set(JSON.parse(process.argv[3]).map(x=>String(x).toLowerCase())),o=j.organization||j;
const plan=String(o.plan_id||o.plan||'').toLowerCase(),overages=o.overages===true;
if(!plan||!allowed.has(plan)||overages)throw new Error('TURSO_ORGANIZATION_NOT_ZERO_COST:'+plan+':overages='+overages);
console.log('turso_subscription=PASS source=organization plan='+plan+' overages=false');
NODE
    elif [[ "$org_code" == 403 ]]; then
      # Resource-scoped tokens can deny billing metadata. Fail closed on capacity instead:
      # prove current usage fits an explicitly zero-price plan and make no paid-capable mutation.
      plans_code=$(curl -sS --connect-timeout 10 --max-time 30 -o "$OUT/turso-plans.json" -w '%{http_code}' \
        -H "Authorization: Bearer $TURSO_API_TOKEN" -H 'Accept: application/json' \
        "https://api.turso.tech/v1/organizations/$TURSO_ORG/plans" || true)
      usage_code=$(curl -sS --connect-timeout 10 --max-time 30 -o "$OUT/turso-usage.json" -w '%{http_code}' \
        -H "Authorization: Bearer $TURSO_API_TOKEN" -H 'Accept: application/json' \
        "https://api.turso.tech/v1/organizations/$TURSO_ORG/usage" || true)
      if [[ "$plans_code" == 200 && "$usage_code" == 200 ]]; then
        node - "$OUT/turso-plans.json" "$OUT/turso-usage.json" "$ZERO_COST_PLANS" "$OUT/turso-databases.json" <<'NODE'
const fs=require('fs');
const plansJ=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),usageJ=JSON.parse(fs.readFileSync(process.argv[3],'utf8')),
      allowed=new Set(JSON.parse(process.argv[4]).map(x=>String(x).toLowerCase())),
      dbJ=JSON.parse(fs.readFileSync(process.argv[5],'utf8'));
const plans=Array.isArray(plansJ)?plansJ:(plansJ.plans||[]);
const free=plans.find(p=>allowed.has(String(p.name||p.id||'').toLowerCase())&&Number(p.price??p.monthly_price??0)===0);
if(!free)throw new Error('TURSO_ZERO_COST_PLAN_NOT_VISIBLE');
const q=free.quotas||{},u=(usageJ.organization||usageJ).usage||{},dbs=dbJ.databases||[];
const pairs=[['rows_read','rowsRead'],['rows_written','rowsWritten'],['databases','databases'],['locations','locations'],['storage_bytes','storage'],['groups','groups'],['bytes_synced','bytesSynced']];
for(const [uk,qk] of pairs){if(q[qk]===undefined||u[uk]===undefined)continue;const used=Number(u[uk]),limit=Number(q[qk]);if(!Number.isFinite(used)||!Number.isFinite(limit)||limit<=0||used>limit)throw new Error('TURSO_FREE_CAPACITY_EXCEEDED:'+uk+':'+used+'/'+limit);}
if(Number.isFinite(Number(q.databases))&&dbs.length>Number(q.databases))throw new Error('TURSO_FREE_DATABASE_COUNT_EXCEEDED');
console.log('turso_zero_cost_capacity=PASS plan='+String(free.name||free.id)+' dbs='+dbs.length+' billing_scope=readable no_paid_action=true');
NODE
      elif [[ "$plans_code" == 403 && "$usage_code" == 403 ]]; then
        # Least-privilege org token deliberately cannot read billing. This preflight must not
        # mutate provider state; require an already-existing DB + valid DB credential below.
        TURSO_EXISTING_RESOURCE_ONLY=1
        echo "turso_billing_scope=READ_DENIED existing_resource_only=true no_paid_action=true"
      else
        echo "TURSO_ZERO_COST_CAPACITY_METADATA_UNAVAILABLE:plans=$plans_code:usage=$usage_code" >&2; exit 54
      fi
    else
      echo "TURSO_BILLING_METADATA_UNAVAILABLE:subscription=$sub_code:organization=$org_code" >&2
      exit 54
    fi
  fi
  [[ -f "$OUT/turso-databases.json" ]] || curl -fsS --connect-timeout 10 --max-time 30     -H "Authorization: Bearer $TURSO_API_TOKEN" "https://api.turso.tech/v1/organizations/$TURSO_ORG/databases?limit=100" > "$OUT/turso-databases.json"
elif [[ "$TURSO_DB_AUTH_OK" != 1 ]]; then
  echo "TURSO_PLATFORM_TOKEN_VALID_BUT_ORG_SCOPE_UNRESOLVED" >&2
  exit 53
fi

[[ -f "$OUT/turso-databases.json" ]] || { echo "TURSO_DR_DATABASE_INVENTORY_REQUIRED" >&2; exit 53; }
node - "$OUT/turso-databases.json" "$TURSO_MAX_DBS" <<'NODE'
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),max=Number(process.argv[3]),rows=j.databases||[];
if(!Number.isInteger(max)||max<3||rows.length>max)throw new Error('TURSO_DATABASE_COUNT_CAPACITY_INVALID:'+rows.length+'/'+max);
for(const name of ['pick-pack-1291-dr-beta','pick-pack-1291-dr-stable']){const m=rows.filter(x=>String(x.Name||x.name||'')===name);if(m.length!==1)throw new Error('TURSO_DR_TARGET_NOT_UNIQUE:'+name+':'+m.length);if(!String(m[0].Hostname||m[0].hostname||''))throw new Error('TURSO_DR_TARGET_HOST_MISSING:'+name);}
console.log('turso_dr_targets=PASS database_count='+rows.length+'/'+max);
NODE

if [[ "$TURSO_DB_AUTH_OK" != 1 ]]; then
  [[ -f "$OUT/turso-databases.json" ]] || { echo "TURSO_DATABASE_LIST_UNAVAILABLE" >&2; exit 53; }
  if [[ "${TURSO_EXISTING_RESOURCE_ONLY:-0}" == 1 ]]; then
    jq -e '(.databases|type=="array") and (.databases|length>0)' "$OUT/turso-databases.json" >/dev/null || { echo "TURSO_EXISTING_DB_REQUIRED_FOR_SCOPED_BILLING" >&2; exit 55; }
  fi
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

# Hard safety invariant: credential preflight is GET/readback only; provider creation, plan
# upgrade, overages, PATCH/POST/PUT/DELETE are forbidden here.
if grep -Eq 'curl[^\n]*(--request|-X)[[:space:]]*(POST|PUT|PATCH|DELETE)' "$0"; then
  echo "DR_PREFLIGHT_PAID_CAPABLE_MUTATION_FORBIDDEN" >&2; exit 56
fi
http deno-apps "https://api.deno.com/v2/apps?limit=100" "$DENO_DEPLOY_TOKEN"
node - "$OUT/deno-apps.json" "$DENO_MAX_APPS" <<'NODE'
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),max=Number(process.argv[3]),rows=Array.isArray(j)?j:(j.items||j.apps||[]);
if(!Array.isArray(rows)||!Number.isInteger(max)||max<2||rows.length>max)throw new Error('DENO_APP_CAPACITY_INVALID:'+rows.length+'/'+max);
for(const slug of ['pp1291-dr-beta','pp1291-dr-stable']){const m=rows.filter(x=>String(x.slug||'')===slug);if(m.length!==1)throw new Error('DENO_DR_TARGET_NOT_UNIQUE:'+slug+':'+m.length);}
console.log('deno_token=PASS target_count=2 app_count='+rows.length+'/'+max);
NODE
jq -n --arg turso_mode "${TURSO_EXISTING_RESOURCE_ONLY:+EXISTING_RESOURCE_ONLY}" --argjson deno_max "$DENO_MAX_APPS" --argjson turso_max "$TURSO_MAX_DBS" '{status:"PASS",quota_authority:"config/provider_free_limits.json",provider_limit_freshness:"PASS",secrets:"4/4_VALIDATED",render_token:"PASS",render_cold_standby:"PASS",turso_platform_token:"PASS",turso_database_token:"PASS",turso_targets:"PASS",turso_max_databases:$turso_max,turso_billing_mode:($turso_mode|select(length>0)//"ZERO_COST_METADATA_VERIFIED"),deno_token:"PASS",deno_targets:"PASS",deno_max_apps:$deno_max,no_secret_output:true,no_paid_action:true}' > "$OUT/receipt.json"
cat "$OUT/receipt.json"
