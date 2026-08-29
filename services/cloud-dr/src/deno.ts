import { handle, type DrRuntimeEnv } from "./handler";
const required=(k:string)=>{const v=Deno.env.get(k);if(!v)throw new Error("MISSING_"+k);return v};
const env:DrRuntimeEnv={TURSO_DATABASE_URL:required("TURSO_DATABASE_URL"),TURSO_AUTH_TOKEN:required("TURSO_AUTH_TOKEN"),SERVICE_TOKEN_SECRET:required("SERVICE_TOKEN_SECRET"),SERVICE_GENERATION:required("SERVICE_GENERATION"),DISCOVERY_URL:required("DISCOVERY_URL"),DR_WRITER_MODE:Deno.env.get("DR_WRITER_MODE")||"PASSIVE"};
Deno.serve((r)=>handle(r,env));
