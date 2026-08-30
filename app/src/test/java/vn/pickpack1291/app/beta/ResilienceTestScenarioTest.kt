package vn.pickpack1291.app.beta

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

// Beta101 full Android gate anchor: stop/recover semantics + readable history/log contract.
class ResilienceTestScenarioTest {
    @Test fun catalogCoversOwnerFailureDomains(){
        val codes=ResilienceTestScenario.entries.map{it.code}.toSet()
        assertEquals(7,codes.size)
        assertTrue("NORMAL_SERVICE_PRIMARY" in codes)
        assertTrue("DEVICE_OFFLINE_LOCAL" in codes)
        assertTrue("SERVICE_UNAVAILABLE_GOOGLE" in codes)
        assertTrue("SERVICE_TIMEOUT_GOOGLE" in codes)
        assertTrue("GOOGLE_UNAVAILABLE_SERVICE" in codes)
        assertTrue("SERVICE_GOOGLE_OFFLINE_LOCAL" in codes)
        assertTrue("SERVICE_GOOGLE_OFFLINE_LAN" in codes)
    }

    @Test fun everyScenarioHasProfessionalOwnerFacingContract(){
        ResilienceTestScenario.entries.forEach{
            assertTrue(it.label.isNotBlank())
            assertTrue(it.description.length>=20)
            assertTrue(it.expected.length>=20)
        }
    }

    @Test fun cancellationHasOwnerFacingStatusAndRecoveryStage(){
        assertEquals("ĐÃ DỪNG",ResilienceTestCenter.resultVi("CANCELLED"))
        assertTrue(ResilienceTestCenter.stageVi("STOPPED_BY_OWNER").contains("trạng thái vận hành bình thường"))
    }

    @Test fun localOnlyScenarioExplicitlyExcludesRemotePaths(){
        val x=ResilienceTestScenario.SERVICE_GOOGLE_OFFLINE_LOCAL
        assertTrue(x.label.contains("LAN"))
        assertTrue(x.expected.contains("local",ignoreCase=true))
        assertTrue(x.expected.contains("replay",ignoreCase=true))
    }
}
