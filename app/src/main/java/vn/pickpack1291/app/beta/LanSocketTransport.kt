package vn.pickpack1291.app.beta

import org.java_websocket.WebSocket
import org.java_websocket.client.WebSocketClient
import org.java_websocket.handshake.ClientHandshake
import org.java_websocket.handshake.ServerHandshake
import org.java_websocket.server.WebSocketServer
import org.json.JSONObject
import java.net.InetSocketAddress
import java.net.URI
import java.util.concurrent.*

internal class LanSocketTransport(
    private val deviceId:String,
    private val accountRole:String,
    private val listener:Listener,
) {
    enum class Mode { PEER, MASTER, BACKUP, CLIENT }
    data class Ack(val ok:Boolean,val generation:Long,val error:String?=null)

    interface Listener {
        fun generation():Long
        fun masterDeviceId():String
        fun backupDeviceId():String
        fun onPeerConnected(deviceId:String,accountRole:String)
        fun onPeerDisconnected(deviceId:String)
        fun onVoteRequest(candidateDeviceId:String,candidateRole:String,generation:Long):Boolean
        fun persistReplica(event:JSONObject,sourceDevice:String,generation:Long,replicaRole:String):OperationalDataStore.LanPersistResult
        fun onMasterFrame(frame:JSONObject)
        fun onBackupAssigned(frame:JSONObject)
        fun onHandover(frame:JSONObject)
    }

    private val remoteWaiters=ConcurrentHashMap<String,CompletableFuture<Ack>>()
    private val localWaiters=ConcurrentHashMap<String,CompletableFuture<Ack>>()
    private val pendingOrigins=ConcurrentHashMap<String,WebSocket>()
    private val connections=ConcurrentHashMap<String,WebSocket>()
    @Volatile private var mode=Mode.PEER
    @Volatile private var server:NodeServer?=null
    @Volatile private var masterClient:MasterClient?=null
    @Volatile private var backupId=""

    fun setMode(next:Mode){mode=next}
    fun mode():Mode=mode
    fun connections():Set<String> = connections.keys.toSet()
    fun hasConnection(id:String)=connections[id]?.isOpen==true
    fun backupDeviceId():String=backupId

    fun startServer():Int {
        server?.let{return it.boundPort()}
        val s=NodeServer();server=s;s.start()
        check(s.started.await(2,TimeUnit.SECONDS)){"LAN_SOCKET_SERVER_START_TIMEOUT"}
        return s.boundPort()
    }

    fun stopServer(){runCatching{server?.stop(500)};server=null;connections.clear();pendingOrigins.clear()}

    fun connectMaster(endpoint:LanDiscovery.PeerEndpoint):Boolean {
        disconnectMaster()
        val c=MasterClient(endpoint);masterClient=c
        return runCatching{c.connectBlocking(2,TimeUnit.SECONDS)}.getOrDefault(false)
    }

    fun disconnectMaster(){runCatching{masterClient?.closeBlocking()};masterClient=null}

    fun assignBackup(id:String,fixedVoters:Collection<String>,lanEpoch:Long,leaseUntil:Long):Boolean {
        val c=connections[id]?:return false
        backupId=id
        c.send(JSONObject()
            .put("type","ROLE")
            .put("role","BACKUP")
            .put("master_device_id",deviceId)
            .put("generation",listener.generation())
            .put("lan_epoch",lanEpoch)
            .put("lease_until_ms",leaseUntil)
            .put("fixed_voters",org.json.JSONArray(fixedVoters.toList()))
            .toString())
        return true
    }

    fun clearBackup(){backupId=""}

    fun heartbeat(lanEpoch:Long,leaseUntil:Long) {
        if(mode!=Mode.MASTER)return
        val frame=JSONObject()
            .put("type","HEARTBEAT")
            .put("master_device_id",deviceId)
            .put("backup_device_id",backupId)
            .put("generation",listener.generation())
            .put("lan_epoch",lanEpoch)
            .put("lease_until_ms",leaseUntil)
            .put("at",System.currentTimeMillis())
            .toString()
        connections.values.forEach{runCatching{it.send(frame)}}
    }

    fun handoverToBackup(generation:Long,lanEpoch:Long,leaseUntil:Long):Boolean {
        val c=connections[backupId]?:return false
        c.send(frame("HANDOVER").put("generation",generation).put("lan_epoch",lanEpoch).put("lease_until_ms",leaseUntil).toString())
        return true
    }

    fun submit(event:JSONObject,timeoutMs:Long=2_500L):Ack {
        return if(mode==Mode.MASTER)submitMaster(event,timeoutMs)
        else masterClient?.submit(event,timeoutMs)?:Ack(false,listener.generation(),"LAN_MASTER_SOCKET_UNAVAILABLE")
    }

    private fun submitMaster(event:JSONObject,timeoutMs:Long):Ack {
        val eventId=event.optString("event_id").trim()
        if(eventId.isBlank())return Ack(false,listener.generation(),"LAN_EVENT_ID_REQUIRED")
        val persisted=listener.persistReplica(event,deviceId,listener.generation(),"MASTER")
        if(!persisted.ok)return Ack(false,listener.generation(),persisted.error)
        val b=connections[backupId]
        if(backupId.isBlank()||b==null||!b.isOpen)return Ack(false,listener.generation(),"LAN_BACKUP_REQUIRED")
        val f=CompletableFuture<Ack>();localWaiters[eventId]=f
        b.send(frame("REPLICA").put("generation",listener.generation()).put("event",event).toString())
        return try{f.get(timeoutMs,TimeUnit.MILLISECONDS)}catch(_:Throwable){localWaiters.remove(eventId);Ack(false,listener.generation(),"LAN_BACKUP_ACK_TIMEOUT")}
    }

    fun requestVote(endpoint:LanDiscovery.PeerEndpoint,candidateDeviceId:String,candidateRole:String,generation:Long):Boolean {
        val result=CompletableFuture<Boolean>()
        val c=object:WebSocketClient(URI("ws://${endpoint.host}:${endpoint.port}")){
            override fun onOpen(handshake:ServerHandshake){
                send(frame("VOTE_REQUEST").put("candidate_device_id",candidateDeviceId).put("candidate_role",candidateRole).put("generation",generation).toString())
            }
            override fun onMessage(message:String){
                val j=runCatching{JSONObject(message)}.getOrNull()?:return
                if(j.optString("type")=="VOTE_RESPONSE")result.complete(j.optBoolean("granted",false))
            }
            override fun onClose(code:Int,reason:String,remote:Boolean){result.complete(false)}
            override fun onError(ex:Exception){result.complete(false)}
        }
        return try{
            if(!c.connectBlocking(1,TimeUnit.SECONDS))return false
            val yes=result.get(1,TimeUnit.SECONDS)
            runCatching{c.closeBlocking()};yes
        }catch(_:Throwable){runCatching{c.close()};false}
    }

    private fun frame(type:String):JSONObject=JSONObject().put("type",type).put("environment_id",BuildConfig.ENVIRONMENT_ID)

    fun close(){disconnectMaster();stopServer();remoteWaiters.values.forEach{it.complete(Ack(false,listener.generation(),"LAN_SOCKET_CLOSED"))};localWaiters.values.forEach{it.complete(Ack(false,listener.generation(),"LAN_SOCKET_CLOSED"))};remoteWaiters.clear();localWaiters.clear()}

    private inner class NodeServer:WebSocketServer(InetSocketAddress(0)) {
        val started=CountDownLatch(1)
        fun boundPort():Int=address.port
        override fun onStart(){connectionLostTimeout=25;started.countDown()}
        override fun onOpen(conn:WebSocket,handshake:ClientHandshake)=Unit
        override fun onError(conn:WebSocket?,ex:Exception)=Unit
        override fun onClose(conn:WebSocket,code:Int,reason:String,remote:Boolean){
            val id=this@LanSocketTransport.connections.entries.firstOrNull{it.value==conn}?.key
            if(id!=null){this@LanSocketTransport.connections.remove(id);listener.onPeerDisconnected(id)}
        }
        override fun onMessage(conn:WebSocket,message:String){
            val j=runCatching{JSONObject(message)}.getOrNull()?:return
            if(j.optString("environment_id")!=BuildConfig.ENVIRONMENT_ID){conn.close(1008,"ENVIRONMENT_MISMATCH");return}
            when(j.optString("type")){
                "HELLO"->{
                    val id=j.optString("device_id").trim()
                    if(id.isBlank())return
                    this@LanSocketTransport.connections[id]=conn
                    listener.onPeerConnected(id,j.optString("account_role","USER"))
                    conn.send(frame("HELLO_ACK").put("master_device_id",listener.masterDeviceId()).put("backup_device_id",listener.backupDeviceId()).put("generation",listener.generation()).toString())
                }
                "VOTE_REQUEST"->{
                    val granted=listener.onVoteRequest(j.optString("candidate_device_id"),j.optString("candidate_role"),j.optLong("generation"))
                    conn.send(frame("VOTE_RESPONSE").put("granted",granted).put("voter_device_id",deviceId).put("generation",j.optLong("generation")).toString())
                }
                "EVENT"->{
                    if(mode!=Mode.MASTER){conn.send(frame("NACK").put("event_id",j.optString("event_id")).put("error","LAN_NOT_MASTER").toString());return}
                    val event=j.optJSONObject("event")?:return
                    val eventId=event.optString("event_id")
                    val persisted=listener.persistReplica(event,j.optString("device_id"),listener.generation(),"MASTER")
                    if(!persisted.ok){conn.send(frame("NACK").put("event_id",eventId).put("error",persisted.error).toString());return}
                    val backup=this@LanSocketTransport.connections[this@LanSocketTransport.backupId]
                    if(this@LanSocketTransport.backupId.isBlank()||backup==null||!backup.isOpen){conn.send(frame("NACK").put("event_id",eventId).put("error","LAN_BACKUP_REQUIRED").toString());return}
                    pendingOrigins[eventId]=conn
                    backup.send(frame("REPLICA").put("generation",listener.generation()).put("event",event).toString())
                }
                "REPLICA_ACK"->{
                    if(mode!=Mode.MASTER)return
                    val eventId=j.optString("event_id")
                    pendingOrigins.remove(eventId)?.send(frame("ACK").put("event_id",eventId).put("generation",listener.generation()).toString())
                    localWaiters.remove(eventId)?.complete(Ack(true,listener.generation(),null))
                }
            }
        }
    }

    private inner class MasterClient(endpoint:LanDiscovery.PeerEndpoint):WebSocketClient(URI("ws://${endpoint.host}:${endpoint.port}")) {
        override fun onOpen(handshake:ServerHandshake){
            send(frame("HELLO").put("device_id",deviceId).put("account_role",accountRole).put("generation",listener.generation()).toString())
        }
        override fun onError(ex:Exception)=Unit
        override fun onClose(code:Int,reason:String,remote:Boolean){
            remoteWaiters.values.forEach{it.complete(Ack(false,listener.generation(),"LAN_MASTER_SOCKET_CLOSED"))};remoteWaiters.clear()
        }
        override fun onMessage(message:String){
            val j=runCatching{JSONObject(message)}.getOrNull()?:return
            if(j.optString("environment_id")!=BuildConfig.ENVIRONMENT_ID){close(1008,"ENVIRONMENT_MISMATCH");return}
            when(j.optString("type")){
                "HELLO_ACK","HEARTBEAT"->listener.onMasterFrame(j)
                "ROLE"->if(j.optString("role")=="BACKUP"){mode=Mode.BACKUP;listener.onBackupAssigned(j)}
                "REPLICA"->{
                    if(mode!=Mode.BACKUP)return
                    val event=j.optJSONObject("event")?:return
                    val generation=j.optLong("generation")
                    val r=listener.persistReplica(event,listener.masterDeviceId(),generation,"BACKUP")
                    if(r.ok)send(frame("REPLICA_ACK").put("event_id",event.optString("event_id")).put("generation",generation).toString())
                }
                "ACK"->remoteWaiters.remove(j.optString("event_id"))?.complete(Ack(true,j.optLong("generation",listener.generation()),null))
                "NACK"->remoteWaiters.remove(j.optString("event_id"))?.complete(Ack(false,listener.generation(),j.optString("error","LAN_NACK")))
                "HANDOVER"->listener.onHandover(j)
            }
        }
        fun submit(event:JSONObject,timeoutMs:Long):Ack {
            if(!isOpen)return Ack(false,listener.generation(),"LAN_MASTER_SOCKET_UNAVAILABLE")
            val id=event.optString("event_id").trim()
            if(id.isBlank())return Ack(false,listener.generation(),"LAN_EVENT_ID_REQUIRED")
            val f=CompletableFuture<Ack>();remoteWaiters[id]=f
            send(frame("EVENT").put("device_id",deviceId).put("event_id",id).put("event",event).toString())
            return try{f.get(timeoutMs,TimeUnit.MILLISECONDS)}catch(_:Throwable){remoteWaiters.remove(id);Ack(false,listener.generation(),"LAN_MASTER_ACK_TIMEOUT")}
        }
    }
}
