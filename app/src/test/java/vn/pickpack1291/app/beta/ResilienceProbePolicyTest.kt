package vn.pickpack1291.app.beta

import org.junit.Assert.assertEquals
import org.junit.Test

class ResilienceProbePolicyTest {
    @Test fun serviceDownGoogleUpRequiresEmergencyLedgerAck() {
        assertEquals("PASS",ResilienceProbePolicy.evaluate("DISABLE_CLOUDFLARE",true,"OFFLINE_PROVISIONAL","EMERGENCY_LEDGER_CAPTURED",1).state)
        assertEquals("FAIL",ResilienceProbePolicy.evaluate("DISABLE_CLOUDFLARE",true,"CONFIRMED","",1).state)
    }

    @Test fun googleDownServiceUpRequiresServiceConfirmation() {
        assertEquals("PASS",ResilienceProbePolicy.evaluate("DISABLE_GOOGLE",true,"CONFIRMED","",0).state)
        assertEquals("FAIL",ResilienceProbePolicy.evaluate("DISABLE_GOOGLE",true,"OFFLINE_PROVISIONAL","EMERGENCY_LEDGER_CAPTURED",1).state)
    }

    @Test fun bothDownRequiresRetriedLocalDurability() {
        assertEquals("PASS",ResilienceProbePolicy.evaluate("DISABLE_BOTH",true,"RETRY","TEST_CLOUDFLARE_DISABLED",1).state)
        assertEquals("ĐANG KIỂM TRA",ResilienceProbePolicy.evaluate("DISABLE_BOTH",true,"LOCAL_PENDING","",0).state)
        assertEquals("FAIL",ResilienceProbePolicy.evaluate("DISABLE_BOTH",true,"CONFIRMED","",1).state)
    }

    @Test fun normalRequiresReplayToCanonicalService() {
        assertEquals("PASS",ResilienceProbePolicy.evaluate("NORMAL",true,"CONFIRMED","",2).state)
        assertEquals("ĐANG PHỤC HỒI",ResilienceProbePolicy.evaluate("NORMAL",true,"RETRY","NETWORK",2).state)
    }
}
