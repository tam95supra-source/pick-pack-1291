package vn.pickpack1291.app.beta

import org.junit.Assert.*
import org.junit.Test

class LanAuthorityPolicyTest {
    private val p=LanAuthorityPolicy
    @Test fun healthyIsNormal(){assertEquals(p.HealthState.NORMAL,p.healthState(true,0,100,false,false,false,false))}
    @Test fun shortOutageIsDegraded(){assertEquals(p.HealthState.DEGRADED,p.healthState(false,1000,1000+p.SERVICE_UNAVAILABLE_AFTER_MS-1,false,false,false,false))}
    @Test fun fiveMinuteOutageIsUnavailable(){assertEquals(p.HealthState.SERVICE_UNAVAILABLE,p.healthState(false,1000,1000+p.SERVICE_UNAVAILABLE_AFTER_MS,false,false,false,false))}
    @Test fun readyLanIsAvailable(){assertEquals(p.HealthState.LAN_AVAILABLE,p.healthState(false,1,1+p.SERVICE_UNAVAILABLE_AFTER_MS,true,false,false,false))}
    @Test fun activeLanWinsOutage(){assertEquals(p.HealthState.LAN_ACTIVE,p.healthState(false,1,99,true,true,false,false))}
    @Test fun recoveringWinsLan(){assertEquals(p.HealthState.RECOVERING,p.healthState(false,1,99,true,true,true,false))}
    @Test fun cloudDrWinsAll(){assertEquals(p.HealthState.CLOUD_DR_ACTIVE,p.healthState(false,1,99,true,true,true,true))}
    @Test fun majorityIsStrict(){assertEquals(2,p.majority(3));assertEquals(3,p.majority(4))}
    @Test fun adminBlockedWhenSuperOnline(){val now=100000L;assertFalse(p.candidateAllowed("ADMIN","a",listOf(p.Peer("s","SUPERADMIN",1,now)),now,null))}
    @Test fun superadminAllowed(){val now=100000L;assertTrue(p.candidateAllowed("SUPERADMIN","s",listOf(p.Peer("a","ADMIN",1,now)),now,null))}
    @Test fun firstExistingMasterBlocksSeize(){val now=100000L;val lease=p.Lease("m","b",4,now+1000);assertFalse(p.candidateAllowed("ADMIN","a",emptyList(),now,lease))}
    @Test fun staleSuperDoesNotBlockAdmin(){val now=100000L;assertTrue(p.candidateAllowed("ADMIN","a",listOf(p.Peer("s","SUPERADMIN",1,now-p.PEER_FRESH_MS-1)),now,null))}
    @Test fun minorityCannotElect(){val voters=setOf("a","b","c","d","e");val votes=listOf(p.Vote("a","a",7),p.Vote("b","a",7));assertFalse(p.voteGranted(voters,votes,"a",7))}
    @Test fun majorityElectsExactlyCandidate(){val voters=setOf("a","b","c");val votes=listOf(p.Vote("a","a",7),p.Vote("b","a",7),p.Vote("c","x",7));assertTrue(p.voteGranted(voters,votes,"a",7));assertFalse(p.voteGranted(voters,votes,"x",7))}
    @Test fun backupCannotTakeBeforeLeaseExpiry(){val voters=setOf("b","c","d");val lease=p.Lease("m","b",3,200);val votes=listOf(p.Vote("b","b",4),p.Vote("c","b",4));assertFalse(p.takeoverAllowed("b",lease,199,3,voters,votes,4))}
    @Test fun backupTakeoverNeedsMajorityAndHigherGeneration(){val voters=setOf("b","c","d");val lease=p.Lease("m","b",3,200);val votes=listOf(p.Vote("b","b",4),p.Vote("c","b",4));assertTrue(p.takeoverAllowed("b",lease,201,3,voters,votes,4));assertFalse(p.takeoverAllowed("b",lease,201,4,voters,votes,4))}
    @Test fun oldMasterCannotRetakeNewerGeneration(){assertFalse(p.acceptsMasterGeneration(8,7));assertTrue(p.acceptsMasterGeneration(8,8));assertTrue(p.acceptsMasterGeneration(8,9))}
    @Test fun fixedVoterSetDropsStalePeers(){val now=100000L;val s=p.fixedVoterSet("self",listOf(p.Peer("fresh","USER",1,now),p.Peer("old","USER",1,now-p.PEER_FRESH_MS-1)),now);assertEquals(setOf("self","fresh"),s)}
}
