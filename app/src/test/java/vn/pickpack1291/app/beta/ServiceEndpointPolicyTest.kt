package vn.pickpack1291.app.beta

import org.junit.Assert.*
import org.junit.Test

class ServiceEndpointPolicyTest {
    @Test fun acceptsCurrentCloudflare(){assertTrue(ServiceEndpointPolicy.allowed("https://pickpack1291.cc.cd"))}
    @Test fun acceptsRenderDr(){assertTrue(ServiceEndpointPolicy.allowed("https://pick-pack-1291-dr.onrender.com"))}
    @Test fun acceptsDenoDr(){assertTrue(ServiceEndpointPolicy.allowed("https://pick-pack-1291-dr.deno.net"))}
    @Test fun rejectsHttp(){assertFalse(ServiceEndpointPolicy.allowed("http://example.com"))}
    @Test fun rejectsUserInfo(){assertFalse(ServiceEndpointPolicy.allowed("https://u:p@example.com"))}
    @Test fun rejectsLocalhost(){assertFalse(ServiceEndpointPolicy.allowed("https://localhost"))}
    @Test fun rejectsPrivateIpv4(){assertFalse(ServiceEndpointPolicy.allowed("https://192.168.1.10"))}
    @Test fun rejectsNonStandardPort(){assertFalse(ServiceEndpointPolicy.allowed("https://example.com:8443"))}
}
