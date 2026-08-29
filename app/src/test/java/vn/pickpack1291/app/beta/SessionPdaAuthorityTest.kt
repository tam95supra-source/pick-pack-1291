package vn.pickpack1291.app.beta

import org.junit.Assert.*
import org.junit.Test

class SessionPdaAuthorityTest {
    private fun d(authoritative:Boolean,active:List<String> = emptyList())=
        SessionPdaAuthority.decide(authoritative,active)

    @Test fun currentSessionActivePdaRequiresCheck(){ assertTrue(d(true,listOf("PDA-01")).requiresCheck) }
    @Test fun currentSessionNeverHadPdaDoesNotCheck(){ assertFalse(d(true).requiresCheck) }
    @Test fun returnedPdaDoesNotCheck(){ assertFalse(d(true).requiresCheck) }
    @Test fun staleEmployeeScalarCannotCreatePdaCheck(){ assertFalse(d(true).requiresCheck) }
    @Test fun oldSessionPdaCannotAffectCurrentNoPda(){ assertFalse(d(true).requiresCheck) }
    @Test fun staleLocalCacheCannotOverrideAuthoritativeNoPda(){ assertFalse(d(true).requiresCheck) }
    @Test fun oldGoogleFallbackPdaCannotAffectNewSession(){ assertFalse(d(true).requiresCheck) }
    @Test fun missingSnapshotRequiresExactSessionResolve(){ assertTrue(d(false).needsSnapshot) }
    @Test fun lanAuthoritativeNoPdaDoesNotCheck(){ assertFalse(d(true).requiresCheck) }
    @Test fun cloudOrLanFailoverAuthoritativeNoPdaDoesNotResurrectStalePda(){ assertNull(d(true).activePdaId) }
}
