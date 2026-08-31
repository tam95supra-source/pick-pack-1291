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
const testCenter=read("app/src/main/java/vn/pickpack1291/app/beta/ResilienceTestCenter.kt");
const testCenterTest=read("app/src/test/java/vn/pickpack1291/app/beta/ResilienceTestScenarioTest.kt");
const logs=read("app/src/main/java/vn/pickpack1291/app/beta/LocalLogManager.kt");
const serviceIndex=read("service/src/index.ts");
const adminAudit=read("service/src/admin_audit.ts");
const tr=read("app/src/main/java/vn/pickpack1291/app/beta/M2ServiceTransport.kt");
const store=read("app/src/main/java/vn/pickpack1291/app/beta/OperationalDataStore.kt");
const gas=read("google-apps-script/PICK_PACK_API.gs");
const mig=read("service/migrations/0009_resilience_generation_backup.sql");
const maint=read("service/src/d1_maintenance.ts");
const gradle=read("app/build.gradle.kts");
const releaseRequest=JSON.parse(read("ops/beta-release-request.json"));
const policy=JSON.parse(read("config/mutation_fallback_policy.json"));

const flavorBlock=(text,name,nextName)=>{
  const start=text.indexOf('create("'+name+'")');
  if(start<0)return "";
  const end=nextName?text.indexOf('create("'+nextName+'")',start+1):-1;
  return text.slice(start,end<0?text.length:end);
};
const releaseMetadataErrors=(gradleText,req)=>{
  const errors=[];
  const stable=flavorBlock(gradleText,"stable",null),beta=flavorBlock(gradleText,"beta","stable");
  if(!stable.includes('versionCode = 1')||!stable.includes('versionName = "0.1.0-stable"'))errors.push("STABLE_METADATA_CHANGED");
  if(!req||typeof req.version_name!=="string"||!/^0\.4\.2-beta\.\d+$/.test(req.version_name))errors.push("BETA_RELEASE_VERSION_INVALID");
  if(!Number.isInteger(req?.version_code)||req.version_code<1)errors.push("BETA_RELEASE_CODE_INVALID");
  if(req?.package!=="vn.pickpack1291.app.beta.publicbeta")errors.push("BETA_RELEASE_PACKAGE_INVALID");
  if(!beta.includes('applicationId = "'+(req?.package||"")+'"'))errors.push("BETA_PACKAGE_METADATA_MISMATCH");
  if(!beta.includes('versionCode = '+String(req?.version_code)))errors.push("BETA_VERSION_CODE_METADATA_MISMATCH");
  if(!beta.includes('versionName = "'+String(req?.version_name||"")+'"'))errors.push("BETA_VERSION_NAME_METADATA_MISMATCH");
  return errors;
};
const releaseMetadataSelfTest=()=>{
  const base={version_name:"0.4.2-beta.999",version_code:1005,package:"vn.pickpack1291.app.beta.publicbeta"};
  const fixture='create("beta") { applicationId = "vn.pickpack1291.app.beta.publicbeta"\n versionCode = 1005\n versionName = "0.4.2-beta.999" }\ncreate("stable") { versionCode = 1\n versionName = "0.1.0-stable" }';
  if(releaseMetadataErrors(fixture,base).length)throw new Error("RELEASE_METADATA_SELFTEST_POSITIVE");
  for(const bad of [
    {...base,version_name:""},
    {...base,version_code:1006},
    {...base,package:"vn.pickpack1291.app.beta.WRONG"}
  ])if(releaseMetadataErrors(fixture,bad).length===0)throw new Error("RELEASE_METADATA_SELFTEST_NEGATIVE");
};
releaseMetadataSelfTest();
for(const e of releaseMetadataErrors(gradle,releaseRequest))must(false,e);

const exitId=ops.slice(ops.indexOf("private fun exitPdaId"),ops.indexOf("private fun visibleAssignments"));
must(exitId.includes("exitPdaDecision")&&!exitId.includes("pda_serial"),"PDA_EXIT_LEGACY_SCALAR_FALLBACK");
must(ops.includes('api.call("session_resource_snapshot",JSONObject().put("session_id",sessionId).put("mnv",mnv))'),"PDA_EXIT_EXACT_SESSION_SNAPSHOT_MISSING");
must(pda.includes("authoritativeAssignmentsPresent")&&!pda.includes("pda_serial"),"PDA_AUTHORITY_HELPER_INVALID");
must((pdaTest.match(/@Test/g)||[]).length>=10,"PDA_EXIT_MATRIX_LT_10");
must(pdaOnly.includes('"session_id"')&&pdaOnly.includes('"pda_serial"')&&!pdaOnly.includes('"user_pick" to')&&!pdaOnly.includes('"pack_table" to')&&!pdaOnly.includes('"user_pack" to'),"PDA_ONLY_PAYLOAD_REPLAYS_UNRELATED_RESOURCE");
must((pdaOnlyTest.match(/@Test/g)||[]).length>=2&&pdaOnlyTest.includes("changePdaDoesNotReplayUnrelatedResources"),"PDA_ONLY_REGRESSION_MISSING");
must(fault.includes("Beta100 compatibility shim")&&fault.includes("fun cloudflareDisabled(context:Context):Boolean = false")&&fault.includes("fun googleDisabled(context:Context):Boolean = false"),"LEGACY_FAULT_FLAGS_CAN_STILL_TOUCH_BUSINESS_TRAFFIC");
must(tr.includes('TECHNICAL = setOf("resilience_probe")')&&tr.includes("fun isolatedResilienceTest"),"RESILIENCE_ISOLATED_TRANSPORT_MISSING");
must(store.includes("resilience_test_events")&&store.includes("Never consumed by the production mutation worker"),"RESILIENCE_ISOLATED_DURABLE_LEDGER_MISSING");
must(testCenter.includes("SERVICE_UNAVAILABLE_GOOGLE")&&testCenter.includes("SERVICE_GOOGLE_OFFLINE_LOCAL")&&testCenter.includes("SERVICE_GOOGLE_OFFLINE_LAN")&&testCenter.includes("DEVICE_OFFLINE_LOCAL"),"RESILIENCE_SCENARIO_CATALOG_INCOMPLETE");
must((testCenterTest.match(/@Test/g)||[]).length>=4,"RESILIENCE_SCENARIO_REGRESSION_MISSING");
must(testCenter.includes('"CANCELLED"->"ĐÃ DỪNG"')&&testCenter.includes('"STOPPED_BY_OWNER"'),"RESILIENCE_STOP_STATUS_MISSING");
must(tr.includes('cancelled:()->Boolean={false}')&&tr.includes('isolated_scope_closed')&&tr.includes('"CANCELLED","STOPPED_BY_OWNER"'),"RESILIENCE_TRANSPORT_CANCEL_PATH_MISSING");
must(ops.includes('"DỪNG TEST / VỀ BÌNH THƯỜNG"')&&ops.includes("stopResilienceTest()"),"RESILIENCE_STOP_BUTTON_MISSING");
must(ops.includes('setStroke(dp(2)')&&ops.includes('"Lịch sử kiểm thử resilience"')&&ops.includes('"Mới nhất ở trên'),"RESILIENCE_HISTORY_CARDS_MISSING");
must(testCenter.includes("resilience_test.history_count=")&&testCenter.includes("resilience_test.history[$i].scenario="),"RESILIENCE_FULL_HISTORY_DIAGNOSTIC_MISSING");
must(ops.includes('showHeaderStatusDetail("NETWORK")')&&ops.includes('showHeaderStatusDetail("SYNC")')&&ops.includes('showHeaderStatusDetail("SERVICE")'),"STATUS_CHIPS_NOT_ALL_CLICKABLE");
must(ops.includes('setNeutralButton("ĐỒNG BỘ NGAY")')&&ops.includes("manualRefreshFromHeader"),"SYNC_DETAIL_MANUAL_SYNC_MISSING");
must(logs.includes("ResilienceTestCenter.snapshotLines"),"RESILIENCE_MANUAL_LOG_EVIDENCE_MISSING");
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
console.log("resilience_static_gate=PASS release_metadata=CONTRACT_DRIVEN release_metadata_negative_regression=PASS pda_matrix=10 pda_partial=PASS isolated_resilience_center=PASS resilience_stop_history=PASS status_chip_details=PASS emergency_ledger=PASS d1_guard=PASS mutation_inventory=PASS");

const drHandler=read("services/cloud-dr/src/handler.ts");
const drAdapter=read("services/cloud-dr/src/libsql_adapter.ts");
const providerLimits=JSON.parse(read("config/provider_free_limits.json"));
must(drHandler.includes('../../../service/src/core')&&drHandler.includes('../../../service/src/legacy'),"DR_CANONICAL_CORE_REUSE_MISSING");
must(drHandler.includes('DR_WRITER_MODE!=="ACTIVE_WRITE"')&&drHandler.includes("DR_PASSIVE_FENCED"),"DR_WRITER_FENCE_MISSING");
must(drAdapter.includes("@libsql/client/web"),"DR_PROVIDER_ADAPTER_MISSING");
must(providerLimits.schema_version===1,"PROVIDER_LIMIT_SCHEMA_INVALID");
const verifiedAt=Date.parse(String(providerLimits.verified_at||"")+"T00:00:00Z"),maxAgeDays=Number(providerLimits.max_age_days),limitAge=Date.now()-verifiedAt;
must(Number.isFinite(verifiedAt)&&Number.isInteger(maxAgeDays)&&maxAgeDays>=1&&limitAge>=-86400000&&limitAge<=maxAgeDays*86400000,"PROVIDER_LIMIT_AUTHORITY_STALE");
for(const k of ["d1_database_bytes","d1_account_bytes","d1_database_count"])must(Number.isInteger(providerLimits.cloudflare_workers_free?.[k])&&providerLimits.cloudflare_workers_free[k]>0,"CF_D1_LIMIT_INVALID_"+k);
must(providerLimits.render?.required_service_plan==="free"&&providerLimits.render?.required_region==="singapore"&&providerLimits.render?.automatic_activation==="FORBIDDEN_COLD_STANDBY","RENDER_FREE_COLD_STANDBY_GUARD_MISSING");
must(providerLimits.turso?.required_plan_price_usd===0&&Number.isInteger(providerLimits.turso?.max_databases)&&providerLimits.turso.max_databases>=3,"TURSO_FREE_PLAN_GUARD_MISSING");
must(providerLimits.deno?.required_plan_price_usd===0&&Number.isInteger(providerLimits.deno?.max_active_apps)&&providerLimits.deno.max_active_apps>=2&&providerLimits.deno?.automatic_activation==="CONTROLLED_ONLY","DENO_FREE_PLAN_GUARD_MISSING");

const gasRes=read("google-apps-script/PICK_PACK_API.gs");
must(gasRes.includes("EMERGENCY EVENT INDEX")&&gasRes.includes("EMERGENCY LEDGER "+'')&&gasRes.includes("ppEmergencyPartitionName_"),"EMERGENCY_LEDGER_PARTITION_MISSING");
must(gasRes.includes("allFinal")&&gasRes.includes("60*86400000"),"EMERGENCY_LEDGER_SAFE_RETENTION_MISSING");
must(gasRes.includes("EMERGENCY_PAYLOAD_TOO_LARGE"),"EMERGENCY_LEDGER_PAYLOAD_GUARD_MISSING");
must(read("app/src/main/java/vn/pickpack1291/app/beta/M2ServiceTransport.kt").includes('capturedIds.size==pending.size'),"EMERGENCY_CAPTURE_PER_EVENT_ACK_MISSING");

const rollover=read("tools/d1_generation_rehearsal.sh");
must(rollover.includes("ROLLOVER_1_CHECKSUM_MISMATCH")&&rollover.includes("ROLLOVER_2_CHECKSUM_MISMATCH"),"D1_ROLLOVER_2X_REHEARSAL_MISSING");
must(rollover.includes("COUNT+3 <= MAX")&&rollover.includes("trap cleanup EXIT"),"D1_ROLLOVER_FREE_QUOTA_OR_CLEANUP_MISSING");

import "./chaos_matrix_contract.mjs";
