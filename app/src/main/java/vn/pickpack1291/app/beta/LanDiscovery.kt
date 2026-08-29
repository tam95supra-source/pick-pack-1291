package vn.pickpack1291.app.beta

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.net.wifi.WifiManager
import android.os.Build
import java.util.concurrent.ConcurrentHashMap

internal class LanDiscovery(context:Context) {
    data class PeerEndpoint(
        val deviceId:String,
        val host:String,
        val port:Int,
        val accountRole:String,
        val nodeRole:String,
        val generation:Long,
        val seenAt:Long,
    )

    private val app=context.applicationContext
    private val manager=app.getSystemService(Context.NSD_SERVICE) as NsdManager
    private val endpoints=ConcurrentHashMap<String,PeerEndpoint>()
    private var registration:NsdManager.RegistrationListener?=null
    private var discovery:NsdManager.DiscoveryListener?=null
    private var multicast:WifiManager.MulticastLock?=null
    private var onPeer:((PeerEndpoint)->Unit)?=null

    fun snapshot():Map<String,PeerEndpoint> = endpoints.toMap()

    fun advertise(port:Int,deviceId:String,accountRole:String,nodeRole:String,generation:Long) {
        stopAdvertising()
        val info=NsdServiceInfo().apply {
            serviceName="PP1291-"+deviceId.takeLast(10)
            serviceType=SERVICE_TYPE
            setPort(port)
            setAttribute("device",deviceId)
            setAttribute("role",accountRole)
            setAttribute("node",nodeRole)
            setAttribute("gen",generation.toString())
        }
        val listener=object:NsdManager.RegistrationListener {
            override fun onServiceRegistered(serviceInfo:NsdServiceInfo)=Unit
            override fun onRegistrationFailed(serviceInfo:NsdServiceInfo,errorCode:Int)=Unit
            override fun onServiceUnregistered(serviceInfo:NsdServiceInfo)=Unit
            override fun onUnregistrationFailed(serviceInfo:NsdServiceInfo,errorCode:Int)=Unit
        }
        registration=listener
        runCatching{manager.registerService(info,NsdManager.PROTOCOL_DNS_SD,listener)}
    }

    fun discover(selfDeviceId:String,onPeer:(PeerEndpoint)->Unit) {
        if(discovery!=null)return
        this.onPeer=onPeer
        if(Build.VERSION.SDK_INT<33) {
            val wifi=app.getSystemService(Context.WIFI_SERVICE) as WifiManager
            multicast=wifi.createMulticastLock("pp1291-lan-nsd").apply {
                setReferenceCounted(false)
                runCatching{acquire()}
            }
        }
        val listener=object:NsdManager.DiscoveryListener {
            override fun onDiscoveryStarted(serviceType:String)=Unit
            override fun onDiscoveryStopped(serviceType:String)=Unit
            override fun onStartDiscoveryFailed(serviceType:String,errorCode:Int){stopDiscovery()}
            override fun onStopDiscoveryFailed(serviceType:String,errorCode:Int)=Unit
            override fun onServiceLost(serviceInfo:NsdServiceInfo){
                attr(serviceInfo,"device").takeIf{it.isNotBlank()}?.let{endpoints.remove(it)}
            }
            @Suppress("DEPRECATION")
            override fun onServiceFound(serviceInfo:NsdServiceInfo) {
                val advertised=attr(serviceInfo,"device")
                if(advertised==selfDeviceId)return
                runCatching {
                    manager.resolveService(serviceInfo,object:NsdManager.ResolveListener {
                        override fun onResolveFailed(serviceInfo:NsdServiceInfo,errorCode:Int)=Unit
                        override fun onServiceResolved(resolved:NsdServiceInfo) {
                            val id=attr(resolved,"device").ifBlank{advertised}
                            if(id.isBlank()||id==selfDeviceId)return
                            val host=resolved.host?.hostAddress.orEmpty()
                            if(host.isBlank()||resolved.port<=0)return
                            val ep=PeerEndpoint(
                                deviceId=id,
                                host=host,
                                port=resolved.port,
                                accountRole=attr(resolved,"role").ifBlank{"USER"},
                                nodeRole=attr(resolved,"node").ifBlank{"PEER"},
                                generation=attr(resolved,"gen").toLongOrNull()?:0L,
                                seenAt=System.currentTimeMillis(),
                            )
                            endpoints[id]=ep
                            this@LanDiscovery.onPeer?.invoke(ep)
                        }
                    })
                }
            }
        }
        discovery=listener
        runCatching{manager.discoverServices(SERVICE_TYPE,NsdManager.PROTOCOL_DNS_SD,listener)}
    }

    fun restartDiscovery(selfDeviceId:String,onPeer:(PeerEndpoint)->Unit){stopDiscovery();discover(selfDeviceId,onPeer)}

    fun stopDiscovery() {
        val listener=discovery
        if(listener!=null)runCatching{manager.stopServiceDiscovery(listener)}
        discovery=null
        onPeer=null
        runCatching{multicast?.release()}
        multicast=null
    }

    fun stopAdvertising() {
        val listener=registration
        if(listener!=null)runCatching{manager.unregisterService(listener)}
        registration=null
    }

    fun close(){stopDiscovery();stopAdvertising();endpoints.clear()}

    private fun attr(info:NsdServiceInfo,key:String):String =
        runCatching{info.attributes[key]?.toString(Charsets.UTF_8).orEmpty()}.getOrDefault("")

    companion object { const val SERVICE_TYPE="_pp1291._tcp." }
}
