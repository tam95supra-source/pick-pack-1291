import { handle, type DrRuntimeEnv } from "./handler";
const required=(k:string)=>{const v=Deno.env.get(k);if(!v)throw new Error("MISSING_"+k);return v};
const optional=(k:string)=>Deno.env.get(k)||"";
const environmentId=required("ENVIRONMENT_ID").toUpperCase();
const scoped=(k:string)=>environmentId==="STABLE"?required(k):optional(k);
const env:DrRuntimeEnv={TURSO_DATABASE_URL:required("TURSO_DATABASE_URL"),TURSO_AUTH_TOKEN:required("TURSO_AUTH_TOKEN"),SERVICE_TOKEN_SECRET:required("SERVICE_TOKEN_SECRET"),SERVICE_GENERATION:required("SERVICE_GENERATION"),DISCOVERY_URL:required("DISCOVERY_URL"),DR_WRITER_MODE:Deno.env.get("DR_WRITER_MODE")||"PASSIVE",ENVIRONMENT_ID:environmentId,SERVICE_AUDIENCE:required("SERVICE_AUDIENCE"),GAS_API_URL:required("GAS_API_URL"),OUTBOUND_GAS_API_URL:scoped("OUTBOUND_GAS_API_URL"),DR_GAS_API_URL:scoped("DR_GAS_API_URL"),DR_TARGET_ID:scoped("DR_TARGET_ID"),DR_MAX_REQUESTS_PER_MINUTE:required("DR_MAX_REQUESTS_PER_MINUTE"),DR_MAX_MUTATIONS_PER_BATCH:required("DR_MAX_MUTATIONS_PER_BATCH"),DR_KILL_SWITCH:required("DR_KILL_SWITCH")};
Deno.serve((r)=>handle(r,env));
