package vn.pickpack1291.app.beta

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

internal object LanRecoveryClient {
    fun reconcile(context:Context,done:(Boolean,String?)->Unit){
        val app=context.applicationContext
        val store=OperationalDataStore(app)
        val pending=store.pendingLanReplicas(100)
        if(pending.isEmpty()){done(true,null);return}
        val events=JSONArray();pending.forEach{events.put(it.body)}
        BetaApiClient(app).call("lan_replay_batch",JSONObject().put("events",events)){r->
            if(!r.ok){done(false,r.error?:"LAN_REPLAY_FAILED");return@call}
            val results=r.json?.optJSONArray("results")?:JSONArray()
            val seen=HashSet<String>();var retry=false
            for(i in 0 until results.length()){
                val x=results.optJSONObject(i)?:continue
                val id=x.optString("local_event_id");if(id.isBlank())continue;seen.add(id)
                when(x.optString("status")){
                    "CONFIRMED","DUPLICATE"->store.markLanReplicaCanonical(id,x.optString("status"))
                    "REVIEW_REQUIRED"->store.markLanReplicaCanonical(id,"REVIEW_REQUIRED",x.optString("error_code"))
                    "REJECTED"->if(x.optBoolean("retryable",false)){store.markLanReplicaCanonical(id,"RETRY",x.optString("error_code"));retry=true}else store.markLanReplicaCanonical(id,"REJECTED",x.optString("error_code"))
                    else->{store.markLanReplicaCanonical(id,"RETRY","LAN_REPLAY_RESULT_INVALID");retry=true}
                }
            }
            pending.filter{it.eventId !in seen}.forEach{store.markLanReplicaCanonical(it.eventId,"RETRY","LAN_REPLAY_RESULT_MISSING");retry=true}
            if(!retry&&store.pendingLanReplicaCount()>0)reconcile(app,done) else done(!retry,if(retry)"LAN_REPLAY_RETRY_REQUIRED" else null)
        }
    }
}
