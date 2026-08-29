package vn.pickpack1291.app.beta

internal object LanAuthorityPolicy {
    const val SERVICE_UNAVAILABLE_AFTER_MS = 5 * 60_000L
    const val PEER_FRESH_MS = 45_000L
    const val MASTER_LEASE_MS = 45_000L
    const val HEARTBEAT_MS = 10_000L
    const val MASTER_MISSED_MS = 30_000L

    enum class HealthState { NORMAL, DEGRADED, SERVICE_UNAVAILABLE, LAN_AVAILABLE, LAN_ACTIVE, RECOVERING, CLOUD_DR_ACTIVE }
    data class Peer(val deviceId:String,val role:String,val generation:Long,val lastSeenAt:Long)
    data class Lease(val masterDeviceId:String,val backupDeviceId:String,val generation:Long,val leaseUntil:Long)
    data class Vote(val voterDeviceId:String,val candidateDeviceId:String,val generation:Long)

    fun healthState(
        connected:Boolean,
        outageStartedAt:Long,
        now:Long,
        lanReady:Boolean,
        lanActive:Boolean,
        recovering:Boolean,
        cloudDrActive:Boolean,
    ):HealthState {
        if(cloudDrActive)return HealthState.CLOUD_DR_ACTIVE
        if(recovering)return HealthState.RECOVERING
        if(lanActive)return HealthState.LAN_ACTIVE
        if(connected)return HealthState.NORMAL
        if(outageStartedAt<=0L||now-outageStartedAt<SERVICE_UNAVAILABLE_AFTER_MS)return HealthState.DEGRADED
        return if(lanReady)HealthState.LAN_AVAILABLE else HealthState.SERVICE_UNAVAILABLE
    }

    fun majority(voterCount:Int):Int=(voterCount.coerceAtLeast(1)/2)+1

    fun fixedVoterSet(selfDeviceId:String,peers:Collection<Peer>,now:Long):Set<String> =
        buildSet {
            add(selfDeviceId)
            peers.filter{now-it.lastSeenAt<=PEER_FRESH_MS}.forEach{add(it.deviceId)}
        }

    fun candidateAllowed(
        candidateRole:String,
        candidateDeviceId:String,
        peers:Collection<Peer>,
        now:Long,
        existingLease:Lease?,
    ):Boolean {
        if(candidateRole!="SUPERADMIN"&&candidateRole!="ADMIN")return false
        if(existingLease!=null&&existingLease.masterDeviceId.isNotBlank()&&existingLease.leaseUntil>now&&existingLease.masterDeviceId!=candidateDeviceId)return false
        val superOnline=peers.any{it.role=="SUPERADMIN"&&now-it.lastSeenAt<=PEER_FRESH_MS&&it.deviceId!=candidateDeviceId}
        if(candidateRole=="ADMIN"&&superOnline)return false
        return true
    }

    fun voteGranted(
        voterSet:Set<String>,
        votes:Collection<Vote>,
        candidateDeviceId:String,
        generation:Long,
    ):Boolean {
        if(candidateDeviceId !in voterSet)return false
        val unique= votes.filter{it.generation==generation&&it.candidateDeviceId==candidateDeviceId&&it.voterDeviceId in voterSet}
            .map{it.voterDeviceId}.toSet()
        return unique.size>=majority(voterSet.size)
    }

    fun takeoverAllowed(
        selfDeviceId:String,
        lease:Lease?,
        now:Long,
        localGeneration:Long,
        voterSet:Set<String>,
        votes:Collection<Vote>,
        requestedGeneration:Long,
    ):Boolean {
        if(lease==null||lease.backupDeviceId!=selfDeviceId)return false
        if(requestedGeneration<=maxOf(localGeneration,lease.generation))return false
        if(lease.leaseUntil>now)return false
        return voteGranted(voterSet,votes,selfDeviceId,requestedGeneration)
    }

    fun acceptsMasterGeneration(localGeneration:Long,incomingGeneration:Long):Boolean=incomingGeneration>=localGeneration
}
