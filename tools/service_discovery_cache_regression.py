#!/usr/bin/env python3
from pathlib import Path
transport=Path("app/src/main/java/vn/pickpack1291/app/beta/M2ServiceTransport.kt").read_text(encoding="utf-8")
runtime=Path("app/src/main/java/vn/pickpack1291/app/beta/M2RuntimeBridge.kt").read_text(encoding="utf-8")
def need(text,token,label):
    if token not in text: raise SystemExit("SERVICE_DISCOVERY_CACHE_REGRESSION_FAIL:"+label)
def forbid(text,token,label):
    if token in text: raise SystemExit("SERVICE_DISCOVERY_CACHE_REGRESSION_FAIL:"+label)
need(transport,'if(j.optString("environment_id")!=BuildConfig.ENVIRONMENT_ID)return false',"ENV_CACHE_FENCE")
need(transport,'if(j.optString("service_audience")!=BuildConfig.SERVICE_AUDIENCE)return false',"AUDIENCE_CACHE_FENCE")
need(transport,'?.takeIf { discoveryMatchesEnvironment(it) }',"STALE_CACHE_INVALIDATION")
need(transport,'fun discoverySnapshot(force:Boolean=false): JSONObject? = discover(force=force)',"TTL_FORCE_DISCOVERY")
need(transport,'val cached = cachedDiscoverySnapshot()',"TTL_USES_VALIDATED_CACHE")
forbid(transport,'val cached = prefs.getString(KEY_DISCOVERY_JSON, null)\n            if (cached != null && now - cachedAt < DISCOVERY_TTL_MS)',"TTL_RAW_CACHE_REUSE")
need(transport,'val discovery = discoverySnapshot() ?: return TransportResult(true, false, 0, null, "DISCOVERY_WARMING")',"SYNC_REFRESH")
need(transport,'val discovery=discoverySnapshot()',"OUTBOX_REFRESH")
need(transport,'val discovery=if(allowDiscovery) discoverySnapshot() else cachedDiscoverySnapshot()',"RESILIENCE_REFRESH")
need(runtime,'val d=transport.discoverySnapshot(force=force) ?: return false',"SESSION_REFRESH")
need(runtime,'val discovery=transport.discoverySnapshot() ?: return M2ServiceTransport.TransportResult(true,false,0,null,"DISCOVERY_WARMING")',"DIRECT_READ_REFRESH")
forbid(runtime,'transport.cachedDiscoverySnapshot() ?: transport.discoverySnapshot()',"CACHE_FIRST_SESSION")
forbid(transport+"\n"+runtime,'https://pickpack1291.cc.cd',"STABLE_ROOT_HARDCODE")
forbid(transport+"\n"+runtime,'https://pickpack.1291.workers.dev',"BETA_PROVIDER_HARDCODE")
print("service_discovery_cache_regression=PASS")
