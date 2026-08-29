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
http turso-organizations "https://api.turso.tech/v1/organizations" "$TURSO_API_TOKEN"
TURSO_ORG=$(node - "$OUT/turso-organizations.json" <<'NODE'
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),rows=Array.isArray(j)?j:(j.organizations||[]);
if(!rows.length)throw new Error('TURSO_ORGANIZATION_MISSING');
const eligible=rows.filter(x=>x.blocked_reads!==true&&x.blocked_writes!==true);
if(!eligible.length)throw new Error('TURSO_ORGANIZATION_BLOCKED');
const o=eligible.find(x=>String(x.type||'')==='personal')||eligible[0],slug=String(o.slug||'').trim();if(!slug)throw new Error('TURSO_ORG_SLUG_MISSING');
process.stdout.write(slug);
NODE
)
http turso-plans "https://api.turso.tech/v1/organizations/$TURSO_ORG/plans" "$TURSO_API_TOKEN"
node - "$OUT/turso-organizations.json" "$OUT/turso-plans.json" "$TURSO_ORG" <<'NODE'
const fs=require('fs'),orgs=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),plans=JSON.parse(fs.readFileSync(process.argv[3],'utf8')),slug=process.argv[4];
const rows=Array.isArray(orgs)?orgs:(orgs.organizations||[]),o=rows.find(x=>String(x.slug)===slug);if(!o)throw new Error('TURSO_ORG_READBACK_MISSING');
const planId=String(o.plan_id||'starter'),list=plans.plans||[],p=list.find(x=>String(x.name||'')===planId)||list.find(x=>String(x.name||'')==='starter');
if(!p||Number(p.price)!==0)throw new Error('TURSO_PLAN_NOT_ZERO_COST:'+planId);
console.log('turso_plan=PASS plan='+String(p.name));
NODE
curl -fsS --connect-timeout 10 --max-time 30 -H "Authorization: Bearer $TURSO_API_TOKEN" "https://api.turso.tech/v1/organizations/$TURSO_ORG/databases?limit=100" > "$OUT/turso-databases.json"
pushd services/cloud-dr >/dev/null
TURSO_AUTH_TOKEN="$TURSO_AUTH_TOKEN" TURSO_DATABASES_JSON="$OUT/turso-databases.json" node --input-type=module <<'NODE'
import fs from 'node:fs';import {createClient} from '@libsql/client';
const j=JSON.parse(fs.readFileSync(process.env.TURSO_DATABASES_JSON,'utf8')),rows=j.databases||[];let ok=null,last='';
for(const x of rows){const host=String(x.Hostname||x.hostname||'');if(!host)continue;try{const c=createClient({url:'libsql://'+host,authToken:process.env.TURSO_AUTH_TOKEN});await c.execute('SELECT 1 AS ok');c.close();ok={name:String(x.Name||x.name||''),host};break}catch(e){last=String(e?.message||e).slice(0,120)}}
if(!ok)throw new Error('TURSO_AUTH_TOKEN_NO_DATABASE_MATCH:'+last);
console.log('turso_database_token=PASS database='+ok.name);
NODE
popd >/dev/null

http deno-apps "https://api.deno.com/v2/apps?limit=100" "$DENO_DEPLOY_TOKEN"
node - "$OUT/deno-apps.json" <<'NODE'
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));if(!Array.isArray(j))throw new Error('DENO_APPS_RESPONSE_INVALID');console.log('deno_token=PASS existing_apps='+j.length);
NODE
jq -n '{status:"PASS",secrets:"4/4_VALIDATED",render_token:"PASS",turso_platform_token:"PASS",turso_database_token:"PASS",deno_token:"PASS",no_secret_output:true,no_paid_action:true}' > "$OUT/receipt.json"
cat "$OUT/receipt.json"
