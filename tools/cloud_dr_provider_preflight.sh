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
  # Organization-scoped tokens can reject account-wide listing. Use repository owner / actor
  # only as lookup candidates and accept one only after Turso direct readback confirms it.
  candidates=()
  if [[ -n "${GITHUB_REPOSITORY:-}" ]]; then
    candidates+=("${GITHUB_REPOSITORY%%/*}")
    candidates+=("${GITHUB_REPOSITORY##*/}")
  fi
  [[ -n "${GITHUB_ACTOR:-}" ]] && candidates+=("$GITHUB_ACTOR")
  for cand in "${candidates[@]}"; do
    [[ -n "$cand" ]] || continue
    code=$(curl -sS --connect-timeout 10 --max-time 30 -o "$OUT/turso-org-candidate.json" -w '%{http_code}' -H "Authorization: Bearer $TURSO_API_TOKEN" -H 'Accept: application/json' "https://api.turso.tech/v1/organizations/$cand" || true)
    if [[ "$code" == 200 ]] && node - "$OUT/turso-org-candidate.json" "$cand" <<'NODE'
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),cand=process.argv[3],o=j.organization||j;
if(String(o.slug||'')!==cand||o.blocked_reads===true||o.blocked_writes===true)process.exit(1);
NODE
    then TURSO_ORG="$cand"; cp "$OUT/turso-org-candidate.json" "$OUT/turso-organization.json"; break; fi
  done
fi

if [[ -z "$TURSO_ORG" ]]; then
  code=$(curl -sS --connect-timeout 10 --max-time 30 -o "$OUT/turso-organizations.json" -w '%{http_code}' -H "Authorization: Bearer $TURSO_API_TOKEN" -H 'Accept: application/json' "https://api.turso.tech/v1/organizations" || true)
  if [[ "$code" == 200 ]]; then
    TURSO_ORG=$(node - "$OUT/turso-organizations.json" <<'NODE'
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),rows=Array.isArray(j)?j:(j.organizations||[]);
const eligible=rows.filter(x=>x.blocked_reads!==true&&x.blocked_writes!==true),o=eligible.find(x=>String(x.type||'')==='personal')||eligible[0];
process.stdout.write(String(o?.slug||'').trim());
NODE
    )
  elif [[ "$code" != 403 ]]; then
    echo "DR_PREFLIGHT_HTTP_FAILED:turso-organizations:$code" >&2;exit 52
  fi
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
  http turso-organization "https://api.turso.tech/v1/organizations/$TURSO_ORG" "$TURSO_API_TOKEN"
  code=$(curl -sS --connect-timeout 10 --max-time 30 -o "$OUT/turso-plans.json" -w '%{http_code}' -H "Authorization: Bearer $TURSO_API_TOKEN" -H 'Accept: application/json' "https://api.turso.tech/v1/organizations/$TURSO_ORG/plans" || true)
  [[ "$code" == 200 ]] || { echo "DR_PREFLIGHT_HTTP_FAILED:turso-plans:$code" >&2;exit 52; }
  node - "$OUT/turso-organization.json" "$OUT/turso-plans.json" "$TURSO_ORG" <<'NODE'
const fs=require('fs'),orgj=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),plansj=JSON.parse(fs.readFileSync(process.argv[3],'utf8')),slug=process.argv[4],o=orgj.organization||orgj;
if(String(o.slug||'')!==slug||o.blocked_reads===true||o.blocked_writes===true||o.overages===true)throw new Error('TURSO_ORG_NOT_SAFE_FREE');
const list=Array.isArray(plansj)?plansj:(plansj.plans||[]),planId=String(o.plan_id||'').toLowerCase();
const exact=list.find(x=>String(x.name||x.id||'').toLowerCase()===planId);
if(exact&&Number(exact.price??exact.monthly_price??0)!==0)throw new Error('TURSO_CURRENT_PLAN_NOT_ZERO_COST:'+planId);
if(!exact&&!list.some(x=>Number(x.price??x.monthly_price??0)===0))throw new Error('TURSO_ZERO_COST_PLAN_NOT_VISIBLE');
console.log('turso_free_plan=PASS plan='+planId);
NODE
  curl -fsS --connect-timeout 10 --max-time 30 -H "Authorization: Bearer $TURSO_API_TOKEN" "https://api.turso.tech/v1/organizations/$TURSO_ORG/databases?limit=100" > "$OUT/turso-databases.json"
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
