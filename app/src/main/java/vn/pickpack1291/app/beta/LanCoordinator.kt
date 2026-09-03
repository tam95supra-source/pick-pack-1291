package vn.pickpack1291.app.beta

import android.content.Context
import android.content.Intent
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.*

internal class LanCoordinator private constructor(context:Context):LanSocketTransport.Listener {
    enum class NodeRole { NONE, PEER, CANDIDATE, MASTER, BACKUP, CLIENT }
    data class Result(val handled:Boolean,val ok:Boolean,val generation:Long,val error:String?=null)
    fun interface StateListener { fun onState(state:LanAuthorityPolicy.HealthState) }

    private val app=context.applicationContext
    private val prefs=app.getSharedPreferences(PREFS,Context.MODE_PRIVATE)
    private val store=OperationalDataStore(app)
    private val discovery=LanDiscovery(app)
    private val socket=LanSocketTransport(M2DeviceIdentity.id(app),accountRole(),this)
    private val timer=Executors.newSingleThreadScheduledExecutor()
    private val io=Executors.newCachedThreadPool()
    private val stateLock=Any()
    private val stateListeners=CopyOnWriteArrayList<StateListener>()
    @Volatile private var cloudConnected=true
    @Volatile private var outageStartedAt=0L
    @Volatile private var recovering=false
    @Volatile private var nodeRole=NodeRole.NONE
    @Volatile private var currentGeneration=prefs.getLong("generation",0L)
    @Volatile private var lanEpoch=prefs.getLong("lan_epoch",0L)
    @Volatile private var leaseUntil=prefs.getLong("lease_until",0L)
    @Volatile private var masterId=prefs.getString("master_device_id","").orEmpty()
    @Volatile private var backupId=prefs.getString("backup_device_id","").orEmpty()
    @Volatile private var lastMasterHeartbeat=0L
    @Volatile private var testModeEnabled=prefs.getBoolean("test_mode_enabled",false)
    @Volatile private var testModeEpoch=prefs.getLong("test_mode_epoch",0L)
    @Volatile private var testModeEnabledBy=prefs.getString("test_mode_enabled_by","").orEmpty()
    private var serverPort=0
    private var unavailableTask:ScheduledFuture<*>?=null
    private var heartbeatTask:ScheduledFuture<*>?=null
    private var presenceTask:ScheduledFuture<*>?=null
    private var takeoverTask:ScheduledFuture<*>?=null

    fun noteServiceStatus(connected:Boolean){
        val now=System.currentTimeMillis()
        synchronized(stateLock){
            cloudConnected=connected
            if(connected){
                outageStartedAt=0L
                unavailableTask?.cancel(false);unavailableTask=null
                if(testModeEnabled){
                    recovering=false
                    if(!isLanActive())startPeerPresence()
                    notifyState()
                }else if(isLanActive()){
                    recovering=true
                    M2ImmediateOutbox.kick(app)
                    notifyState()
                    if(nodeRole==NodeRole.MASTER){
                        LanRecoveryClient.reconcile(app){ok,_->if(ok)completeRecovery()}
                    }
                }else{
                    recovering=false
                    stopPeerPresence()
                }
            }else{
                if(outageStartedAt==0L){outageStartedAt=now;notifyState()}
                val remain=(LanAuthorityPolicy.SERVICE_UNAVAILABLE_AFTER_MS-(now-outageStartedAt)).coerceAtLeast(0L)
                unavailableTask?.cancel(false)
                unavailableTask=timer.schedule({
                    synchronized(stateLock){
                        if(!cloudConnected&&outageAgeMs()>=LanAuthorityPolicy.SERVICE_UNAVAILABLE_AFTER_MS){startPeerPresence();notifyState()}
                    }
                },remain,TimeUnit.MILLISECONDS)
            }
        }
    }

    fun onNetworkChanged(){
        synchronized(stateLock){
            if(testModeEnabled){
                if(!isLanActive())discovery.restartDiscovery(M2DeviceIdentity.id(app),::peerObserved)
            }else if(!cloudConnected&&outageAgeMs()>=LanAuthorityPolicy.SERVICE_UNAVAILABLE_AFTER_MS){
                discovery.restartDiscovery(M2DeviceIdentity.id(app),::peerObserved)
            }
        }
    }

    fun healthState():LanAuthorityPolicy.HealthState =
        LanAuthorityPolicy.healthState(
            connected=cloudConnected,
            outageStartedAt=outageStartedAt,
            now=System.currentTimeMillis(),
            lanReady=serverPort>0&&discovery.snapshot().isNotEmpty(),
            lanActive=isLanActive(),
            recovering=recovering,
            cloudDrActive=prefs.getBoolean("cloud_dr_active",false),
        )

    fun addStateListener(listener:StateListener){stateListeners.addIfAbsent(listener);listener.onState(healthState())}
    fun removeStateListener(listener:StateListener){stateListeners.remove(listener)}
    private fun notifyState(){val state=healthState();stateListeners.forEach{runCatching{it.onState(state)}}}

    fun status():JSONObject=JSONObject()
        .put("health_state",healthState().name)
        .put("node_role",nodeRole.name)
        .put("master_device_id",masterId)
        .put("backup_device_id",backupId)
        .put("generation",currentGeneration)
        .put("lan_epoch",lanEpoch)
        .put("lease_until_ms",leaseUntil)
        .put("outage_ms",outageAgeMs())
        .put("peer_count",discovery.snapshot().size)
        .put("fixed_voter_count",fixedVoters().size)
        .put("test_mode_enabled",testModeEnabled)
        .put("test_mode_epoch",testModeEpoch)
        .put("test_mode_enabled_by",testModeEnabledBy)

    fun applyGlobalTestMode(enabled:Boolean,epoch:Long,enabledBy:String){
        synchronized(stateLock){
            if(epoch<testModeEpoch)return
            testModeEnabled=enabled;testModeEpoch=epoch;testModeEnabledBy=enabledBy
            prefs.edit().putBoolean("test_mode_enabled",enabled).putLong("test_mode_epoch",epoch).putString("test_mode_enabled_by",enabledBy).apply()
            if(!enabled){
                if(cloudConnected)stopLan()
                notifyState()
                return
            }
            val selfLogin=BetaApiClient(app).restoredAccount()?.optString("login_id").orEmpty()
            if(!isLanActive())startPeerPresence()
            if(accountRole()=="SUPERADMIN"&&selfLogin.isNotBlank()&&selfLogin==enabledBy&&nodeRole!=NodeRole.MASTER){
                val generation=maxOf(currentGeneration+1,System.currentTimeMillis())
                becomeMaster(generation,maxOf(lanEpoch+1,epoch),Long.MAX_VALUE)
            }else if(nodeRole !in setOf(NodeRole.MASTER,NodeRole.BACKUP,NodeRole.CLIENT)){
                discovery.restartDiscovery(M2DeviceIdentity.id(app),::peerObserved)
            }
            notifyState()
        }
    }

    fun globalTestModeEnabled():Boolean=testModeEnabled
    fun canRouteForTest():Boolean{
        if(!testModeEnabled||recovering||!isLanActive())return false
        return when(nodeRole){
            NodeRole.MASTER->backupId.isNotBlank()&&socket.hasConnection(backupId)
            NodeRole.BACKUP,NodeRole.CLIENT->masterId.isNotBlank()
            else->false
        }
    }
    fun submitTest(event:JSONObject):Result{
        if(!canRouteForTest())return Result(false,false,currentGeneration,"LAN_TEST_NOT_READY")
        val ack=socket.submit(event)
        return Result(true,ack.ok,ack.generation,ack.error)
    }

    fun requestActivation(userRole:String,callback:(Boolean,String?)->Unit){
        io.execute{
            if(cloudConnected){callback(false,"SERVICE_STILL_AVAILABLE");return@execute}
            if(outageAgeMs()<LanAuthorityPolicy.SERVICE_UNAVAILABLE_AFTER_MS){callback(false,"LAN_NOT_YET_AVAILABLE");return@execute}
            synchronized(stateLock){startPeerPresence()}
            val self=M2DeviceIdentity.id(app)
            val peerPolicy=discovery.snapshot().values.map{LanAuthorityPolicy.Peer(it.deviceId,it.accountRole,it.generation,it.seenAt)}
            val lease=masterId.takeIf{it.isNotBlank()}?.let{LanAuthorityPolicy.Lease(it,backupId,currentGeneration,leaseUntil)}
            if(!LanAuthorityPolicy.candidateAllowed(userRole,self,peerPolicy,System.currentTimeMillis(),lease)){callback(false,"LAN_CANDIDATE_NOT_ELIGIBLE");return@execute}
            nodeRole=NodeRole.CANDIDATE;notifyState()
            val acquired=googleAcquire(userRole)
            if(acquired?.optBoolean("ok",false)==true){
                val l=acquired.optJSONObject("lease")?:JSONObject()
                becomeMaster(l.optLong("generation",currentGeneration+1),l.optLong("lan_epoch",lanEpoch+1),l.optLong("lease_until_ms",System.currentTimeMillis()+LanAuthorityPolicy.MASTER_LEASE_MS))
                callback(true,null)
                return@execute
            }
            if(!hasInternet()||ServiceFaultInjection.googleDisabled(app)){
                val next=offlineElection(userRole)
                if(next>currentGeneration){becomeMaster(next,lanEpoch+1,Long.MAX_VALUE);callback(true,null)}
                else{nodeRole=NodeRole.PEER;callback(false,"LAN_QUORUM_NOT_REACHED")}
            }else{
                nodeRole=NodeRole.PEER
                callback(false,acquired?.optString("error","LAN_GOOGLE_ACQUIRE_FAILED")?:"LAN_GOOGLE_ACQUIRE_FAILED")
            }
        }
    }

    fun submit(event:JSONObject):Result {
        if(!isLanActive()||recovering)return Result(false,false,currentGeneration,"LAN_NOT_ACTIVE")
        val ack=socket.submit(event)
        return Result(true,ack.ok,ack.generation,ack.error)
    }

    fun safeBeforeLogout(callback:(Boolean,String?)->Unit){
        io.execute{
            if(nodeRole!=NodeRole.MASTER){stopLan();callback(true,null);return@execute}
            if(backupId.isBlank()||!socket.hasConnection(backupId)){callback(false,"LAN_BACKUP_REQUIRED_FOR_LOGOUT");return@execute}
            if(hasInternet()&&!ServiceFaultInjection.googleDisabled(app)){
                val response=gasLease("HANDOVER",JSONObject().put("generation",currentGeneration).put("backup_device_id",backupId))
                if(response?.optBoolean("ok",false)==true){
                    val l=response.optJSONObject("lease")?:JSONObject()
                    socket.handoverToBackup(l.optLong("generation",currentGeneration+1),l.optLong("lan_epoch",lanEpoch+1),l.optLong("lease_until_ms",System.currentTimeMillis()+LanAuthorityPolicy.MASTER_LEASE_MS))
                    stopLan();callback(true,null)
                }else callback(false,response?.optString("error","LAN_SAFE_HANDOVER_FAILED")?:"LAN_SAFE_HANDOVER_FAILED")
            }else{
                discovery.restartDiscovery(M2DeviceIdentity.id(app),::peerObserved)
                Thread.sleep(500)
                val voters=fixedVoters();val next=currentGeneration+1
                val votes=collectVotes(backupId,"BACKUP",next,voters)
                if(LanAuthorityPolicy.voteGranted(voters,votes,backupId,next)){
                    socket.handoverToBackup(next,lanEpoch+1,Long.MAX_VALUE);stopLan();callback(true,null)
                }else callback(false,"LAN_SAFE_HANDOVER_QUORUM_REQUIRED")
            }
        }
    }

    fun completeRecovery(){
        synchronized(stateLock){
            if(!recovering)return
            if(nodeRole==NodeRole.MASTER&&hasInternet())gasLease("RELEASE",JSONObject().put("generation",currentGeneration))
            stopLan()
            recovering=false
        }
    }

    fun isLanActive():Boolean=nodeRole in setOf(NodeRole.MASTER,NodeRole.BACKUP,NodeRole.CLIENT)&&masterId.isNotBlank()
    fun canRoute():Boolean{
        if(recovering||!isLanActive())return false
        return when(nodeRole){
            NodeRole.MASTER->backupId.isNotBlank()&&socket.hasConnection(backupId)
            NodeRole.BACKUP,NodeRole.CLIENT->masterId.isNotBlank()
            else->false
        }
    }
    fun outageAgeMs():Long=if(outageStartedAt<=0L)0L else (System.currentTimeMillis()-outageStartedAt).coerceAtLeast(0L)

    private fun startPeerPresence(){
        if(serverPort<=0)serverPort=socket.startServer()
        if(nodeRole==NodeRole.NONE)nodeRole=NodeRole.PEER
        socket.setMode(LanSocketTransport.Mode.PEER)
        discovery.advertise(serverPort,M2DeviceIdentity.id(app),accountRole(),nodeRole.name,currentGeneration)
        discovery.discover(M2DeviceIdentity.id(app),::peerObserved)
        sendPresence()
        if(presenceTask==null||presenceTask?.isCancelled==true){
            presenceTask=timer.scheduleAtFixedRate({if(!cloudConnected||testModeEnabled)sendPresence()},45,45,TimeUnit.SECONDS)
        }
    }

    private fun stopPeerPresence(){
        if(isLanActive()||testModeEnabled)return
        presenceTask?.cancel(false);presenceTask=null
        discovery.close();socket.close();serverPort=0
        nodeRole=NodeRole.NONE
    }

    private fun peerObserved(ep:LanDiscovery.PeerEndpoint){
        if(ep.nodeRole=="MASTER"&&LanAuthorityPolicy.acceptsMasterGeneration(currentGeneration,ep.generation)&&nodeRole !in setOf(NodeRole.MASTER,NodeRole.BACKUP,NodeRole.CLIENT)){
            becomeClient(ep)
        }
    }

    private fun becomeMaster(newGeneration:Long,newEpoch:Long,newLeaseUntil:Long){
        synchronized(stateLock){
            if(newGeneration<currentGeneration)return
            currentGeneration=newGeneration;lanEpoch=newEpoch;leaseUntil=newLeaseUntil
            masterId=M2DeviceIdentity.id(app);backupId="";nodeRole=NodeRole.MASTER;recovering=false
            notifyState()
            if(serverPort<=0)serverPort=socket.startServer()
            socket.setMode(LanSocketTransport.Mode.MASTER)
            persistState()
            discovery.stopDiscovery()
            discovery.advertise(serverPort,masterId,accountRole(),"MASTER",currentGeneration)
            startForeground()
            heartbeatTask?.cancel(false)
            heartbeatTask=timer.scheduleAtFixedRate(::masterHeartbeat,0,LanAuthorityPolicy.HEARTBEAT_MS,TimeUnit.MILLISECONDS)
        }
    }

    private fun becomeClient(ep:LanDiscovery.PeerEndpoint){
        synchronized(stateLock){
            if(!LanAuthorityPolicy.acceptsMasterGeneration(currentGeneration,ep.generation))return
            currentGeneration=ep.generation;masterId=ep.deviceId;nodeRole=NodeRole.CLIENT;recovering=false
            notifyState()
            socket.setMode(LanSocketTransport.Mode.CLIENT)
            if(socket.connectMaster(ep)){
                persistState();discovery.stopDiscovery();startForeground()
            }else{nodeRole=NodeRole.PEER}
        }
    }

    private fun masterHeartbeat(){
        if(nodeRole!=NodeRole.MASTER)return
        val now=System.currentTimeMillis()
        if(hasInternet()&&!ServiceFaultInjection.googleDisabled(app)&&leaseUntil-now<20_000L){
            val response=gasLease("RENEW",JSONObject().put("generation",currentGeneration))
            val l=response?.optJSONObject("lease")
            if(response?.optBoolean("ok",false)==true&&l!=null){
                leaseUntil=l.optLong("lease_until_ms",leaseUntil);lanEpoch=l.optLong("lan_epoch",lanEpoch)
            }else if(response!=null){recovering=true;return}
        }
        socket.heartbeat(lanEpoch,leaseUntil)
        if(backupId.isBlank()){
            socket.connections().firstOrNull()?.let{assignBackup(it)}
        }else if(!socket.hasConnection(backupId)){
            backupId="";socket.clearBackup();persistState()
            if(hasInternet())gasLease("SET_BACKUP",JSONObject().put("generation",currentGeneration).put("backup_device_id",""))
        }
    }

    private fun assignBackup(id:String){
        val voters=fixedVoters().ifEmpty{setOf(M2DeviceIdentity.id(app),id)}
        if(socket.assignBackup(id,voters,lanEpoch,leaseUntil)){
            backupId=id;persistFixedVoters(voters);persistState()
            if(hasInternet())gasLease("SET_BACKUP",JSONObject().put("generation",currentGeneration).put("backup_device_id",id))
        }
    }

    private fun offlineElection(candidateRole:String):Long{
        val self=M2DeviceIdentity.id(app)
        val peerPolicy=discovery.snapshot().values.map{LanAuthorityPolicy.Peer(it.deviceId,it.accountRole,it.generation,it.seenAt)}
        val voters=LanAuthorityPolicy.fixedVoterSet(self,peerPolicy,System.currentTimeMillis())
        persistFixedVoters(voters)
        val next=maxOf(currentGeneration,peerPolicy.maxOfOrNull{it.generation}?:0L)+1
        val votes=collectVotes(self,candidateRole,next,voters).toMutableList()
        votes.add(LanAuthorityPolicy.Vote(self,self,next))
        return if(LanAuthorityPolicy.voteGranted(voters,votes,self,next))next else currentGeneration
    }

    private fun collectVotes(candidate:String,candidateRole:String,next:Long,voters:Set<String>):List<LanAuthorityPolicy.Vote>{
        return voters.filter{it!=M2DeviceIdentity.id(app)}.mapNotNull{id->
            val ep=discovery.snapshot()[id]?:return@mapNotNull null
            if(socket.requestVote(ep,candidate,candidateRole,next))LanAuthorityPolicy.Vote(id,candidate,next)else null
        }
    }

    private fun takeoverIfNeeded(){
        if(nodeRole!=NodeRole.BACKUP||System.currentTimeMillis()-lastMasterHeartbeat<LanAuthorityPolicy.MASTER_MISSED_MS)return
        io.execute{
            if(nodeRole!=NodeRole.BACKUP)return@execute
            if(hasInternet()&&!ServiceFaultInjection.googleDisabled(app)){
                val wait=(leaseUntil-System.currentTimeMillis()).coerceAtLeast(0L)
                if(wait>0)Thread.sleep(wait.coerceAtMost(LanAuthorityPolicy.MASTER_LEASE_MS))
                val response=gasLease("TAKEOVER",JSONObject().put("generation",currentGeneration+1))
                val l=response?.optJSONObject("lease")
                if(response?.optBoolean("ok",false)==true&&l!=null){
                    socket.disconnectMaster()
                    becomeMaster(l.optLong("generation"),l.optLong("lan_epoch"),l.optLong("lease_until_ms"))
                }
            }else{
                discovery.restartDiscovery(M2DeviceIdentity.id(app),::peerObserved);Thread.sleep(500)
                val voters=fixedVoters();val next=currentGeneration+1
                val votes=collectVotes(M2DeviceIdentity.id(app),"BACKUP",next,voters).toMutableList()
                votes.add(LanAuthorityPolicy.Vote(M2DeviceIdentity.id(app),M2DeviceIdentity.id(app),next))
                val lease=LanAuthorityPolicy.Lease(masterId,M2DeviceIdentity.id(app),currentGeneration,0L)
                if(LanAuthorityPolicy.takeoverAllowed(M2DeviceIdentity.id(app),lease,System.currentTimeMillis(),currentGeneration,voters,votes,next)){
                    socket.disconnectMaster();becomeMaster(next,lanEpoch+1,Long.MAX_VALUE)
                }
            }
        }
    }

    private fun googleAcquire(userRole:String):JSONObject?{
        if(!hasInternet()||ServiceFaultInjection.googleDisabled(app))return null
        sendPresence()
        return gasLease("ACQUIRE",JSONObject().put("generation",currentGeneration+1).put("candidate_role",userRole))
    }

    private fun sendPresence(){
        if(ServiceFaultInjection.googleDisabled(app)||!hasInternet())return
        BetaApiClient(app).call("lan_presence",JSONObject().put("device_id",M2DeviceIdentity.id(app))){ }
    }

    private fun gasLease(operation:String,extra:JSONObject):JSONObject?{
        if(ServiceFaultInjection.googleDisabled(app)||!hasInternet())return null
        val latch=CountDownLatch(1);var result:JSONObject?=null
        val payload=JSONObject(extra.toString()).put("operation",operation).put("device_id",M2DeviceIdentity.id(app))
        BetaApiClient(app).call("lan_lease",payload){r->
            result=r.json?:JSONObject().put("ok",false).put("error",r.error?:"LAN_GAS_FAILED")
            latch.countDown()
        }
        latch.await(8,TimeUnit.SECONDS)
        return result
    }

    private fun accountRole():String=BetaApiClient(app).restoredAccount()?.optString("role","USER").orEmpty().ifBlank{"USER"}
    private fun hasInternet():Boolean=runCatching{DeviceNetworkStatus.snapshot(app).hasInternet}.getOrDefault(false)
    private fun startForeground(){runCatching{app.startForegroundService(Intent(app,LanForegroundService::class.java))}}

    private fun persistState(){
        prefs.edit().putLong("generation",currentGeneration).putLong("lan_epoch",lanEpoch).putLong("lease_until",leaseUntil)
            .putString("master_device_id",masterId).putString("backup_device_id",backupId).putString("node_role",nodeRole.name).apply()
    }

    private fun fixedVoters():Set<String>{
        val arr=runCatching{JSONArray(prefs.getString("fixed_voters","[]"))}.getOrDefault(JSONArray())
        val out=linkedSetOf<String>()
        for(i in 0 until arr.length())arr.optString(i).takeIf{it.isNotBlank()}?.let{out.add(it)}
        if(out.isEmpty())out.add(M2DeviceIdentity.id(app))
        return out
    }
    private fun persistFixedVoters(voters:Set<String>){prefs.edit().putString("fixed_voters",JSONArray(voters.toList()).toString()).apply()}

    private fun stopLan(){
        heartbeatTask?.cancel(false);heartbeatTask=null;presenceTask?.cancel(false);presenceTask=null;takeoverTask?.cancel(false);takeoverTask=null
        discovery.close();socket.close();serverPort=0
        nodeRole=NodeRole.NONE;masterId="";backupId="";leaseUntil=0L;recovering=false
        notifyState()
        persistState();runCatching{app.stopService(Intent(app,LanForegroundService::class.java))}
    }

    override fun generation():Long=currentGeneration
    override fun masterDeviceId():String=masterId
    override fun backupDeviceId():String=backupId

    override fun onPeerConnected(deviceId:String,accountRole:String){
        if(nodeRole==NodeRole.MASTER&&backupId.isBlank()&&deviceId!=M2DeviceIdentity.id(app))assignBackup(deviceId)
    }

    override fun onPeerDisconnected(deviceId:String){
        if(nodeRole==NodeRole.MASTER&&backupId==deviceId){backupId="";socket.clearBackup();persistState()}
    }

    override fun onVoteRequest(candidateDeviceId:String,candidateRole:String,generation:Long):Boolean{
        val votedGeneration=prefs.getLong("voted_generation",0L)
        val votedCandidate=prefs.getString("voted_candidate","").orEmpty()
        val knownSuper=accountRole()=="SUPERADMIN"||discovery.snapshot().values.any{it.accountRole=="SUPERADMIN"&&System.currentTimeMillis()-it.seenAt<=LanAuthorityPolicy.PEER_FRESH_MS}
        val eligible=generation>currentGeneration&&(candidateRole=="SUPERADMIN"||(candidateRole=="ADMIN"&&!knownSuper)||candidateRole=="BACKUP")
        val granted=eligible&&(votedGeneration<generation||(votedGeneration==generation&&votedCandidate==candidateDeviceId))
        if(granted)prefs.edit().putLong("voted_generation",generation).putString("voted_candidate",candidateDeviceId).commit()
        return granted
    }

    override fun persistReplica(event:JSONObject,sourceDevice:String,generation:Long,replicaRole:String)=
        store.persistLanReplica(event,sourceDevice,generation,replicaRole)

    override fun onMasterFrame(frame:JSONObject){
        val incoming=frame.optLong("generation",currentGeneration)
        if(!LanAuthorityPolicy.acceptsMasterGeneration(currentGeneration,incoming))return
        currentGeneration=incoming
        masterId=frame.optString("master_device_id",masterId)
        backupId=frame.optString("backup_device_id",backupId)
        lanEpoch=frame.optLong("lan_epoch",lanEpoch)
        leaseUntil=frame.optLong("lease_until_ms",leaseUntil)
        lastMasterHeartbeat=System.currentTimeMillis()
        persistState()
    }

    override fun onBackupAssigned(frame:JSONObject){
        nodeRole=NodeRole.BACKUP
        notifyState()
        currentGeneration=frame.optLong("generation",currentGeneration)
        masterId=frame.optString("master_device_id",masterId)
        lanEpoch=frame.optLong("lan_epoch",lanEpoch)
        leaseUntil=frame.optLong("lease_until_ms",leaseUntil)
        frame.optJSONArray("fixed_voters")?.let{prefs.edit().putString("fixed_voters",it.toString()).apply()}
        persistState();startForeground()
        takeoverTask?.cancel(false)
        takeoverTask=timer.scheduleAtFixedRate(::takeoverIfNeeded,LanAuthorityPolicy.HEARTBEAT_MS,LanAuthorityPolicy.HEARTBEAT_MS,TimeUnit.MILLISECONDS)
    }

    override fun onHandover(frame:JSONObject){
        if(nodeRole!=NodeRole.BACKUP)return
        val next=frame.optLong("generation",currentGeneration+1)
        socket.disconnectMaster()
        becomeMaster(next,frame.optLong("lan_epoch",lanEpoch+1),frame.optLong("lease_until_ms",Long.MAX_VALUE))
    }

    companion object {
        private const val PREFS="pp_lan_runtime_v1"
        @Volatile private var INSTANCE:LanCoordinator?=null
        fun get(context:Context):LanCoordinator=INSTANCE?:synchronized(this){INSTANCE?:LanCoordinator(context).also{INSTANCE=it}}
    }
}
