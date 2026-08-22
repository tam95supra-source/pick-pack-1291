from pathlib import Path

p=Path('app/src/main/java/vn/pickpack1291/app/beta/M2ServiceTransport.kt')
s=p.read_text()

repls=[
('if (ServiceFaultInjection.cloudflareDisabled(app)) return TransportResult(true,false,-1,null,"TEST_CLOUDFLARE_DISABLED")','if (ServiceFaultInjection.cloudflareDisabled(app)) return TransportResult(false,false,-1,null,"TEST_CLOUDFLARE_DISABLED")'),
('''if(ServiceFaultInjection.cloudflareDisabled(app)){\n            // Fault injection simulates provider loss only. Do not bypass the authority fence or\n            // manufacture a Google write authority while production still says SERVICE_PRIMARY.\n            return false\n        }''','''if(ServiceFaultInjection.cloudflareDisabled(app)){\n            // S58_BETA55_GOOGLE_FALLBACK: Cloudflare unavailable -> GAS/Google Sheets.\n            // Only disabling both providers is OFFLINE.\n            return flushFallbackItems(store.unresolvedMutations(100))\n        }'''),
('''if(circuitOpen()){\n            if(failureCount()>=FALLBACK_PROBE_FAILURES&&fallbackProbeDue()){val confirmed=discover(force=true);noteFallbackProbe();if(confirmed?.optString("authority_mode")=="GOOGLE_FALLBACK")return flushFallbackItems(items)}\n            return false\n        }''','''if(circuitOpen()){\n            if(failureCount()>=FALLBACK_PROBE_FAILURES)return flushFallbackItems(items)\n            return false\n        }'''),
('''if(!r.ok||r.json==null){if(r.code>=500||r.code==-1)recordFailure();if(failureCount()>=FALLBACK_PROBE_FAILURES&&fallbackProbeDue()){val confirmed=discover(force=true);noteFallbackProbe();if(confirmed?.optString("authority_mode")=="GOOGLE_FALLBACK")return flushFallbackItems(items)};items.forEach{store.markMutationRetry(it.eventId,r.error?:"HTTP_${r.code}",retryDelay(it.attemptCount))};return false}''','''if(!r.ok||r.json==null){if(r.code>=500||r.code==-1)recordFailure();if((r.code>=500||r.code==-1)&&failureCount()>=FALLBACK_PROBE_FAILURES)return flushFallbackItems(items);items.forEach{store.markMutationRetry(it.eventId,r.error?:"HTTP_${r.code}",retryDelay(it.attemptCount))};return false}'''),
('''}catch(x:Throwable){recordFailure();items.forEach{store.markMutationRetry(it.eventId,x.message?:"NETWORK",retryDelay(it.attemptCount))};false}''','''}catch(x:Throwable){recordFailure();if(failureCount()>=FALLBACK_PROBE_FAILURES)return flushFallbackItems(items);items.forEach{store.markMutationRetry(it.eventId,x.message?:"NETWORK",retryDelay(it.attemptCount))};false}'''),
('recordFailure(); M2WorkScheduler.schedule(app); TransportResult(true, false, r.code, body, r.error ?: "SERVICE_UNAVAILABLE")','recordFailure(); M2WorkScheduler.schedule(app); TransportResult(false, false, r.code, body, r.error ?: "SERVICE_UNAVAILABLE")'),
('TransportResult(true, false, -1, JSONObject().put("_service_rtt_ms", rtt), t.message ?: "SERVICE_READ_NETWORK_ERROR")','TransportResult(false, false, -1, JSONObject().put("_service_rtt_ms", rtt), t.message ?: "SERVICE_READ_NETWORK_ERROR")'),
]
for old,new in repls:
    if new in s: continue
    if old not in s: raise SystemExit('missing anchor: '+old[:80])
    s=s.replace(old,new,1)
p.write_text(s)

p=Path('app/src/main/java/vn/pickpack1291/app/beta/M2RuntimeBridge.kt')
s=p.read_text()
repls=[
('if(ServiceFaultInjection.cloudflareDisabled(app)){recordServicePending("TEST_CLOUDFLARE_DISABLED");return false}','if(ServiceFaultInjection.cloudflareDisabled(app)){recordFallback("TEST_CLOUDFLARE_DISABLED");return false}'),
('''        val discovery = transport.cachedDiscoverySnapshot()\n            ?: return M2ServiceTransport.TransportResult(true, false, 0, null, "DISCOVERY_WARMING")''','''        if(ServiceFaultInjection.cloudflareDisabled(app)){\n            recordFallback("TEST_CLOUDFLARE_DISABLED")\n            return M2ServiceTransport.TransportResult(false,false,-1,null,"TEST_CLOUDFLARE_DISABLED")\n        }\n        val discovery = transport.cachedDiscoverySnapshot()\n            ?: return M2ServiceTransport.TransportResult(true, false, 0, null, "DISCOVERY_WARMING")'''),
('''recordServicePending(response.error ?: "SERVICE_READ_${response.code}")\n                M2WorkScheduler.schedule(app)\n                M2ServiceTransport.TransportResult(true, false, response.code, response.json, response.error)''','''recordFallback(response.error ?: "SERVICE_READ_${response.code}")\n                M2WorkScheduler.schedule(app)\n                M2ServiceTransport.TransportResult(false, false, response.code, response.json, response.error)'''),
('''recordServicePending(t.message ?: "SERVICE_READ_NETWORK")\n            M2WorkScheduler.schedule(app)\n            M2ServiceTransport.TransportResult(true, false, -1, null, t.message)''','''recordFallback(t.message ?: "SERVICE_READ_NETWORK")\n            M2WorkScheduler.schedule(app)\n            M2ServiceTransport.TransportResult(false, false, -1, null, t.message)'''),
]
for old,new in repls:
    if new in s: continue
    if old not in s: raise SystemExit('missing runtime anchor: '+old[:80])
    s=s.replace(old,new,1)

old='''        val route = prefs.getString(KEY_LAST_ROUTE, null) ?: when {\n            mode == "GOOGLE_FALLBACK" -> "GOOGLE_FALLBACK"\n            mode == "SERVICE_PRIMARY" && tokenPresent -> "SERVICE_D1_DIRECT"\n            mode == "SERVICE_PRIMARY" -> "SERVICE_D1_PENDING"\n            else -> "UNRESOLVED"\n        }'''
new='''        val cfOff=ServiceFaultInjection.cloudflareDisabled(app)\n        val googleOff=ServiceFaultInjection.googleDisabled(app)\n        val route = when {\n            cfOff && googleOff -> "OFFLINE"\n            cfOff && !googleOff -> "GOOGLE_FALLBACK"\n            else -> prefs.getString(KEY_LAST_ROUTE, null) ?: when {\n                mode == "GOOGLE_FALLBACK" -> "GOOGLE_FALLBACK"\n                mode == "SERVICE_PRIMARY" && tokenPresent -> "SERVICE_D1_DIRECT"\n                mode == "SERVICE_PRIMARY" -> "SERVICE_D1_PENDING"\n                else -> "UNRESOLVED"\n            }\n        }'''
if new not in s:
    if old not in s: raise SystemExit('missing status route')
    s=s.replace(old,new,1)
s=s.replace('"GOOGLE_FALLBACK" -> "Google dự phòng"','"GOOGLE_FALLBACK" -> "Google Drive / GSheet dự phòng"\n            "OFFLINE" -> "OFFLINE"',1)
s=s.replace('.put("provider", if (mode == "GOOGLE_FALLBACK") "Google dự phòng" else if (url.isNotBlank()) "Cloudflare" else "—")','.put("provider", when(route){"GOOGLE_FALLBACK"->"Google Drive";"OFFLINE"->"OFFLINE";else->if(url.isNotBlank())"Cloudflare" else "—"})',1)
p.write_text(s)
print('S58_BETA55_GOOGLE_FALLBACK')
