import fs from "node:fs";

const read=p=>fs.readFileSync(p,"utf8");
const must=(ok,msg)=>{if(!ok){console.error("RESILIENCE_GATE_FAIL:"+msg);process.exitCode=1;}};
const ops=read("app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt");
const pda=read("app/src/main/java/vn/pickpack1291/app/beta/SessionPdaAuthority.kt");
const pdaTest=read("app/src/test/java/vn/pickpack1291/app/beta/SessionPdaAuthorityTest.kt");
const pdaOnly=read("app/src/main/java/vn/pickpack1291/app/beta/PdaOnlyMutationPayload.kt");
const pdaOnlyTest=read("app/src/test/java/vn/pickpack1291/app/beta/PdaOnlyMutationPayloadTest.kt");
const fault=read("app/src/main/java/vn/pickpack1291/app/beta/ServiceFaultInjection.kt");
const probePolicy=read("app/src/main/java/vn/pickpack1291/app/beta/ResilienceProbePolicy.kt");
const probeTest=read("app/src/test/java/vn/pickpack1291/app/beta/ResilienceProbePolicyTest.kt");
const serviceIndex=read("service/src/index.ts");
const adminAudit=read("service/src/admin_audit.ts");
const tr=read("app/src/main/java/vn/pickpack1291/app/beta/M2ServiceTransport.kt");
const store=read("app/src/main/java/vn/pickpack1291/app/beta/OperationalDataStore.kt");
const gas=read("google-apps-script/PICK_PACK_API.gs");
const mig=read("service/migrations/0009_resilience_generation_backup.sql");
const maint=read("service/src/d1_maintenance.ts");
const gradle=read("app/build.gradle.kts");
const policy=JSON.parse(read("config/mutation_fallback_policy.json"));

must(gradle.includes('versionCode = 1')&&gradle.includes('versionName = "0.1.0-stable"'),"STABLE_METADATA_CHANGED");
must(gradle.includes('versionCode = 105')&&gradle.includes('versionName = "0.4.2-beta.99"'),"BETA99_METADATA_MISSING");

const exitId=ops.slice(ops.indexOf("private fun exitPdaId"),ops.indexOf("private fun visibleAssignments"));
must(exitId.includes("exitPdaDecision")&&!exitId.includes("pda_serial"),"PDA_EXIT_LEGACY_SCALAR_FALLBACK");
must(ops.includes('api.call("session_resource_snapshot",JSONObject().put("session_id",sessionId).put("mnv",mnv))'),"PDA_EXIT_EXACT_SESSION_SNAPSHOT_MISSING");
must(pda.includes("authoritativeAssignmentsPresent")&&!pda.includes("pda_serial"),"PDA_AUTHORITY_HELPER_INVALID");
must((pdaTest.match(/@Test/g)||[]).length>=10,"PDA_EXIT_MATRIX_LT_10");
must(pdaOnly.includes('"session_id"')&&pdaOnly.includes('"pda_serial"')&&!pdaOnly.includes('"user_pick" to')&&!pdaOnly.includes('"pack_table" to')&&!pdaOnly.includes('"user_pack" to'),"PDA_ONLY_PAYLOAD_REPLAYS_UNRELATED_RESOURCE");
must((pdaOnlyTest.match(/@Test/g)||[]).length>=2&&pdaOnlyTest.includes("changePdaDoesNotReplayUnrelatedResources"),"PDA_ONLY_REGRESSION_MISSING");
must(fault.includes("FAULT_TTL_MS=30*60_000L")&&fault.includes("ResilienceProbePolicy.evaluate")&&fault.includes("endAndRecover"),"FAULT_TEST_NOT_DETERMINISTIC");
must(tr.includes('TECHNICAL = setOf("resilience_probe")')&&tr.includes("fun resilienceProbe"),"RESILIENCE_PROBE_TRANSPORT_MISSING");
must(policy.AUTO_CAPTURE_AND_REPLAY.includes("resilience_probe"),"RESILIENCE_PROBE_FALLBACK_CLASSIFICATION_MISSING");
must(adminAudit.includes('resilience_probe:"TECHNICAL_RESILIENCE_PROBE"')&&serviceIndex.includes('input.action==="resilience_probe"'),"RESILIENCE_PROBE_CANONICAL_SERVICE_MISSING");
must((probeTest.match(/@Test/g)||[]).length>=4&&probePolicy.includes('"DISABLE_BOTH"')&&probePolicy.includes('"OFFLINE_PROVISIONAL"'),"RESILIENCE_PROBE_ACCEPTANCE_MATRIX_MISSING");

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
console.log("resilience_static_gate=PASS pda_matrix=10 pda_partial=PASS fault_probe=PASS emergency_ledger=PASS d1_guard=PASS mutation_inventory=PASS");

const drHandler=read("services/cloud-dr/src/handler.ts");
const drAdapter=read("services/cloud-dr/src/libsql_adapter.ts");
const providerLimits=JSON.parse(read("config/provider_free_limits.json"));
must(drHandler.includes('../../../service/src/core')&&drHandler.includes('../../../service/src/legacy'),"DR_CANONICAL_CORE_REUSE_MISSING");
must(drHandler.includes('DR_WRITER_MODE!=="ACTIVE_WRITE"')&&drHandler.includes("DR_PASSIVE_FENCED"),"DR_WRITER_FENCE_MISSING");
must(drAdapter.includes("@libsql/client/web"),"DR_PROVIDER_ADAPTER_MISSING");
must(providerLimits.cloudflare_workers_free?.d1_database_bytes===524288000,"CF_D1_FREE_DB_LIMIT_MISMATCH");
must(providerLimits.cloudflare_workers_free?.d1_account_bytes===5368709120,"CF_D1_FREE_ACCOUNT_LIMIT_MISMATCH");
must(providerLimits.turso?.required_plan_price_usd===0&&providerLimits.deno?.required_plan_price_usd===0,"DR_FREE_PLAN_GUARD_MISSING");

const gasRes=read("google-apps-script/PICK_PACK_API.gs");
must(gasRes.includes("EMERGENCY EVENT INDEX")&&gasRes.includes("EMERGENCY LEDGER "+'')&&gasRes.includes("ppEmergencyPartitionName_"),"EMERGENCY_LEDGER_PARTITION_MISSING");
must(gasRes.includes("allFinal")&&gasRes.includes("60*86400000"),"EMERGENCY_LEDGER_SAFE_RETENTION_MISSING");
must(gasRes.includes("EMERGENCY_PAYLOAD_TOO_LARGE"),"EMERGENCY_LEDGER_PAYLOAD_GUARD_MISSING");
must(read("app/src/main/java/vn/pickpack1291/app/beta/M2ServiceTransport.kt").includes('capturedIds.size==pending.size'),"EMERGENCY_CAPTURE_PER_EVENT_ACK_MISSING");

const rollover=read("tools/d1_generation_rehearsal.sh");
must(rollover.includes("ROLLOVER_1_CHECKSUM_MISMATCH")&&rollover.includes("ROLLOVER_2_CHECKSUM_MISMATCH"),"D1_ROLLOVER_2X_REHEARSAL_MISSING");
must(rollover.includes("COUNT+3 <= MAX")&&rollover.includes("trap cleanup EXIT"),"D1_ROLLOVER_FREE_QUOTA_OR_CLEANUP_MISSING");

import "./chaos_matrix_contract.mjs";
