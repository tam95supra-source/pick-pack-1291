package vn.pickpack1291.app.beta

import java.net.InetAddress
import java.net.URL

/** Provider-neutral endpoint guard. The authenticated discovery record selects the provider. */
internal object ServiceEndpointPolicy {
    fun allowed(raw:String):Boolean=runCatching{
        val u=URL(raw)
        if(u.protocol!="https"||u.host.isBlank()||u.userInfo!=null)return false
        if(u.port !in listOf(-1,443))return false
        val host=u.host.lowercase().trimEnd('.')
        if(host=="localhost"||host.endsWith(".localhost"))return false
        if(isIpLiteral(host)&&isPrivateAddress(host))return false
        true
    }.getOrDefault(false)

    private fun isIpLiteral(host:String)=host.matches(Regex("""\d{1,3}(?:\.\d{1,3}){3}"""))||host.contains(":")
    private fun isPrivateAddress(host:String):Boolean=runCatching{
        val a=InetAddress.getByName(host)
        a.isAnyLocalAddress||a.isLoopbackAddress||a.isLinkLocalAddress||a.isSiteLocalAddress||a.isMulticastAddress
    }.getOrDefault(true)
}
