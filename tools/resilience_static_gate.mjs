import fs from "node:fs";

const read=p=>fs.readFileSync(p,"utf8");
const must=(ok,msg)=>{if(!ok){console.error("RESILIENCE_GATE_FAIL:"+msg);process.exitCode=1;}};
const ops=read("app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt");
const pda=read("app/src/main/java/vn/pickpack1291/app/beta/SessionPdaAuthority.kt");
const pdaTest=read("app/src/test/java/vn/pickpack1291/app/beta/SessionPdaAuthorityTest.kt");
const tr=read("app/src/main/java/vn/pickpack1291/app/beta/M2ServiceTransport.kt");
const store=read("app/src/main/java/vn/pickpack1291/app/beta/OperationalDataStore.kt");
const gas=read("google-apps-script/PICK_PACK_API.gs");
const mig=read("service/migrations/0009_resilience_generation_backup.sql");
const maint=read("service/src/d1_maintenance.ts");
const gradle=read("app/build.gradle.kts");
const policy=JSON.parse(read("config/mutation_fallback_policy.json"));

must(gradle.includes('versionCode = 1')&&gradle.includes('versionName = "0.1.0-stable"'),"STABLE_METADATA_CHANGED");
must(gradle.includes('versionCode = 104')&&gradle.includes('versionName = "0.4.2-beta.98"'),"BETA98_METADATA_MISSING");

const exitId=ops.slice(ops.indexOf("private fun exitPdaId"),ops.indexOf("private fun visibleAssignments"));
must(exitId.includes("exitPdaDecision")&&!exitId.includes("pda_serial"),"PDA_EXIT_LEGACY_SCALAR_FALLBACK");
must(ops.includes('api.call("session_resource_snapshot",JSONObject().put("session_id",sessionId).put("mnv",mnv))'),"PDA_EXIT_EXACT_SESSION_SNAPSHOT_MISSING");
must(pda.includes("authoritativeAssignmentsPresent")&&!pda.includes("pda_serial"),"PDA_AUTHORITY_HELPER_INVALID");
must((pdaTest.match(/@Test/g)||[]).length>=10,"PDA_EXIT_MATRIX_LT_10");

for(const x of ["event_id","idempotency_key","event_type","schema_version","actor_mnv","role","device_id","app_version","business_date","device_time","trusted_received_time","device_sequence","depends_on_event_id","session_id","authority_epoch","service_generation","checksum","payload"])must(tr.includes('"'+x+'"'),"ENVELOPE_FIELD_"+x);
must(tr.includes('emergency_ledger_capture')&&tr.includes("captureEmergency")&&store.includes("markEmergencyCaptured"),"EMERGENCY_LEDGER_APP_MISSING");
must(!tr.includes("flushFallbackItems")&&!tr.includes("FALLBACK_OPERATIONAL"),"LEGACY_DIRECT_GAS_BUSINESS_FALLBACK_PRESENT");
must(gas.includes("ppEmergencyLedgerCapture_")&&gas.includes("ppEmergencyLedgerFinalize_")&&gas.includes("ppEmergencyLedgerQuery_"),"EMERGENCY_LEDGER_GAS_MISSING");
must(gas.includes("'CAPTURED'")&&gas.includes("'APPLIED'")&&gas.includes("'DUPLICATE'")&&gas.includes("'REVIEW_REQUIRED'")&&gas.includes("'REJECTED'"),"EMERGENCY_LEDGER_STATUS_MATRIX");

for(const [k,v] of [["WARN_DB_PERCENT","70"],["PREPARE_NEXT_DB_PERCENT","80"],["CUTOVER_DB_PERCENT","85"],["OWNER_TOTAL_QUOTA_WARN_PERCENT","80"],["RETENTION_DAYS","45"]])must(mig.includes("'"+k+"','"+v+"'"),"CAPACITY_CONFIG_"+k);
for(const table of ["d1_generation_registry","backup_manifests","dr_replay_checkpoints","lan_authority_leases"])must(mig.includes("CREATE TABLE IF NOT EXISTS "+table),"MIGRATION_TABLE_"+table);
must(maint.includes("m.status='VERIFIED'")&&maint.includes("Math.max(45,Math.min(365"),"RETENTION_BACKUP_GUARD_MISSING");

const cats=["AUTO_CAPTURE_AND_REPLAY","CAPTURE_THEN_REVIEW_REQUIRED","FORBIDDEN_FALLBACK"];
for(const c of cats)must(Array.isArray(policy[c])&&policy[c].length>0,"MUTATION_INVENTORY_"+c);
const all=cats.flatMap(c=>policy[c]);
must(new Set(all).size===all.length,"MUTATION_INVENTORY_DUPLICATE_CLASSIFICATION");

const forbidden=/supabase/i;
for(const p of ["app/src/main/java/vn/pickpack1291/app/beta/M2ServiceTransport.kt","service/src/entry_product.ts","service/src/d1_maintenance.ts"])must(!forbidden.test(read(p)),"SUPABASE_REFERENCE_"+p);
if(process.exitCode)process.exit(process.exitCode);
console.log("resilience_static_gate=PASS pda_matrix=10 emergency_ledger=PASS d1_guard=PASS mutation_inventory=PASS");
