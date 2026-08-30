package vn.pickpack1291.app.beta

import android.content.Context
import org.json.JSONObject

/**
 * Device-local fault injection for SUPERADMIN owner acceptance.
 * It never changes LIVE providers/authority globally. Each non-normal mode auto-expires
 * after 30 minutes and uses a non-business resilience_probe to produce observable evidence.
 */
object ServiceFaultInjection {
    enum class Mode(val stored:String,val label:String,val expected:String) {
        NORMAL(
            "NORMAL",
            "Bình thường / phục hồi",
            "Service và Google/GAS hoạt động; probe đã giữ phải replay về Service và thành CONFIRMED."
        ),
        DISABLE_CLOUDFLARE(
            "DISABLE_CLOUDFLARE",
            "Mô phỏng Service chết • Google/GAS còn",
            "Probe không vào Service; phải được Emergency Ledger giữ với trạng thái OFFLINE_PROVISIONAL."
        ),
        DISABLE_GOOGLE(
            "DISABLE_GOOGLE",
            "Mô phỏng Google/GAS lỗi • Service còn",
            "Probe phải đi thẳng Service và thành CONFIRMED; không phụ thuộc Google/GAS."
        ),
        DISABLE_BOTH(
            "DISABLE_BOTH",
            "Mô phỏng Service + Google/GAS cùng lỗi",
            "Probe phải còn bền trong local outbox sau ít nhất một lần retry; không được mất hoặc báo CONFIRMED giả."
        ),
    }

    private const val PREFS="pp_service_fault_injection"
    private const val KEY_MODE="mode"
    private const val KEY_STARTED="started_at"
    private const val KEY_EXPIRES="expires_at"
    private const val KEY_PROBE_EVENT="probe_event_id"
    private const val KEY_PROBE_MODE="probe_mode"
    private const val KEY_PROBE_AT="probe_at"
    private const val FAULT_TTL_MS=30*60_000L

    private fun prefs(context:Context)=context.applicationContext.getSharedPreferences(PREFS,Context.MODE_PRIVATE)

    fun mode(context:Context):Mode {
        val p=prefs(context)
        val raw=p.getString(KEY_MODE,Mode.NORMAL.stored).orEmpty()
        val resolved=Mode.entries.firstOrNull{it.stored==raw}?:Mode.NORMAL
        if(resolved!=Mode.NORMAL){
            val expires=p.getLong(KEY_EXPIRES,0L)
            if(expires>0L&&System.currentTimeMillis()>=expires){
                setMode(context,Mode.NORMAL)
                return Mode.NORMAL
            }
        }
        return resolved
    }

    fun setMode(context:Context,mode:Mode){
        val p=prefs(context)
        val edit=p.edit().putString(KEY_MODE,mode.stored)
        if(mode==Mode.NORMAL)edit.remove(KEY_STARTED).remove(KEY_EXPIRES)
        else {
            val now=System.currentTimeMillis()
            edit.putLong(KEY_STARTED,now).putLong(KEY_EXPIRES,now+FAULT_TTL_MS)
        }
        edit.apply()
        M2ServiceTransport.resetFaultTestCircuit(context)
        M2ImmediateOutbox.kick(context.applicationContext)
    }

    fun runProbe(context:Context):JSONObject {
        val active=mode(context)
        if(active==Mode.NORMAL){
            M2ServiceTransport.resetFaultTestCircuit(context)
            M2ImmediateOutbox.kick(context.applicationContext)
            return testSnapshot(context)
        }
        val result=M2ServiceTransport(context.applicationContext).resilienceProbe(active.stored)
        val eventId=result.json?.optJSONObject("result")?.optString("event_id").orEmpty()
        if(eventId.isNotBlank()){
            prefs(context).edit()
                .putString(KEY_PROBE_EVENT,eventId)
                .putString(KEY_PROBE_MODE,active.stored)
                .putLong(KEY_PROBE_AT,System.currentTimeMillis())
                .apply()
        }
        M2ImmediateOutbox.kick(context.applicationContext)
        return testSnapshot(context)
    }

    fun endAndRecover(context:Context){
        setMode(context,Mode.NORMAL)
        M2ServiceTransport.resetFaultTestCircuit(context)
        M2ImmediateOutbox.kick(context.applicationContext)
    }

    fun testSnapshot(context:Context):JSONObject {
        val p=prefs(context)
        val active=mode(context)
        val probeId=p.getString(KEY_PROBE_EVENT,"").orEmpty()
        val probeMode=Mode.entries.firstOrNull{it.stored==p.getString(KEY_PROBE_MODE,"")}?:Mode.NORMAL
        val row=if(probeId.isBlank())null else OperationalDataStore(context).diagnosticMutation(probeId)
        val status=row?.optString("status").orEmpty()
        val error=row?.optString("last_error").orEmpty()
        val attempts=row?.optInt("attempt_count",0)?:0
        val expected=if(active==Mode.NORMAL&&probeId.isNotBlank())
            "Probe gần nhất phải replay/được xác nhận bởi Service (CONFIRMED)." else active.expected

        var result="CHƯA CHẠY"
        var detail="Chọn một kịch bản rồi bấm CHẠY PROBE."
        if(probeId.isNotBlank()){
            val hardFail=status in setOf("REJECTED","REVIEW_REQUIRED","CONFLICT")
            if(hardFail){
                result="FAIL"
                detail="Probe kết thúc lỗi: ${status.ifBlank{"UNKNOWN"}} • ${error.ifBlank{"không có mã lỗi"}}"
            }else when(active){
                Mode.NORMAL->{
                    if(status=="CONFIRMED"){result="PASS";detail="Phục hồi PASS: probe đã về canonical Service."}
                    else {result="ĐANG PHỤC HỒI";detail="Probe còn ${status.ifBlank{"PENDING"}}; bấm LÀM MỚI sau vài giây."}
                }
                Mode.DISABLE_CLOUDFLARE->{
                    if(status=="OFFLINE_PROVISIONAL"&&error.contains("EMERGENCY_LEDGER_CAPTURED")){
                        result="PASS";detail="Service bị chặn đúng; Emergency Ledger đã ACK và local vẫn giữ replay."
                    }else if(status=="CONFIRMED"){
                        result="FAIL";detail="Probe đã vào Service dù đang bật mô phỏng Service chết."
                    }else {result="ĐANG KIỂM TRA";detail="Đang chờ Emergency Ledger ACK; hiện tại ${status.ifBlank{"PENDING"}}."}
                }
                Mode.DISABLE_GOOGLE->{
                    if(status=="CONFIRMED"){result="PASS";detail="Google/GAS bị chặn nhưng Service vẫn xác nhận probe."}
                    else if(status=="OFFLINE_PROVISIONAL"){result="FAIL";detail="Probe đã đi vào Emergency Ledger dù Google/GAS phải đang bị chặn."}
                    else {result="ĐANG KIỂM TRA";detail="Đang chờ Service xác nhận; hiện tại ${status.ifBlank{"PENDING"}}."}
                }
                Mode.DISABLE_BOTH->{
                    if(status=="CONFIRMED"||status=="OFFLINE_PROVISIONAL"){
                        result="FAIL";detail="Probe đã được cloud xác nhận trong khi cả hai đường phải bị chặn."
                    }else if(attempts>0&&status in setOf("LOCAL_PENDING","PENDING","RETRY","LAN_CONFIRMED")){
                        result="PASS";detail="Không có cloud ACK; probe vẫn được giữ bền local${if(status=="LAN_CONFIRMED")" / LAN" else ""} để replay."
                    }else {result="ĐANG KIỂM TRA";detail="Đang chờ ít nhất một lần retry để chứng minh local durability."}
                }
            }
        }

        val now=System.currentTimeMillis()
        val expires=p.getLong(KEY_EXPIRES,0L)
        return JSONObject()
            .put("mode",active.stored).put("mode_label",active.label)
            .put("expected",expected).put("result",result).put("detail",detail)
            .put("probe_event_id",probeId).put("probe_mode",probeMode.stored)
            .put("probe_status",status.ifBlank{"—"}).put("probe_error",error.ifBlank{"—"})
            .put("attempt_count",attempts)
            .put("started_at",p.getLong(KEY_STARTED,0L))
            .put("probe_at",p.getLong(KEY_PROBE_AT,0L))
            .put("expires_at",expires)
            .put("remaining_minutes",if(active==Mode.NORMAL)0 else ((expires-now).coerceAtLeast(0L)+59_999L)/60_000L)
    }

    fun cloudflareDisabled(context:Context):Boolean=mode(context) in setOf(Mode.DISABLE_CLOUDFLARE,Mode.DISABLE_BOTH)
    fun googleDisabled(context:Context):Boolean=mode(context) in setOf(Mode.DISABLE_GOOGLE,Mode.DISABLE_BOTH)
    fun label(context:Context):String=mode(context).label
}
