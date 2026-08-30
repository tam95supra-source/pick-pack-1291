package vn.pickpack1291.app.beta

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

enum class ResilienceTestScenario(
    val code:String,
    val label:String,
    val description:String,
    val expected:String,
){
    NORMAL_SERVICE_PRIMARY(
        "NORMAL_SERVICE_PRIMARY",
        "Bình thường • Service hoạt động",
        "Đối chứng đường chuẩn khi không có sự cố.",
        "Probe phải được Service xác nhận và gửi lặp cùng event_id phải idempotent."
    ),
    DEVICE_OFFLINE_LOCAL(
        "DEVICE_OFFLINE_LOCAL",
        "Thiết bị mất Internet • giữ local",
        "Giả lập PDA không có Internet, không gọi Service/Google/LAN ở pha sự cố.",
        "Event kỹ thuật phải tồn tại bền local; khi mạng phục hồi phải replay đúng 1 canonical event."
    ),
    SERVICE_UNAVAILABLE_GOOGLE(
        "SERVICE_UNAVAILABLE_GOOGLE",
        "Service mất • Google/GAS còn",
        "Giả lập Service không truy cập được nhưng Google/GAS Emergency Ledger vẫn sẵn sàng.",
        "Google/GAS phải capture event; LAN có thể ACK nếu đang sẵn sàng; sau phục hồi Service phải xác nhận cùng event_id."
    ),
    SERVICE_TIMEOUT_GOOGLE(
        "SERVICE_TIMEOUT_GOOGLE",
        "Service timeout/chậm • Google/GAS còn",
        "Giả lập Service timeout thay vì hard-down.",
        "Event phải đi đường Emergency Ledger và replay về Service sau phục hồi."
    ),
    GOOGLE_UNAVAILABLE_SERVICE(
        "GOOGLE_UNAVAILABLE_SERVICE",
        "Google/GAS lỗi • Service còn",
        "Giả lập Google/GAS không truy cập được trong khi Service vẫn hoạt động.",
        "Probe phải được Service xác nhận trực tiếp, không phụ thuộc Google/GAS."
    ),
    SERVICE_GOOGLE_OFFLINE_LOCAL(
        "SERVICE_GOOGLE_OFFLINE_LOCAL",
        "Service + Google/GAS + LAN đều mất • giữ local",
        "Giả lập mọi đường remote không khả dụng.",
        "Event phải tồn tại bền local và replay chính xác khi Service phục hồi."
    ),
    SERVICE_GOOGLE_OFFLINE_LAN(
        "SERVICE_GOOGLE_OFFLINE_LAN",
        "Service + Google/GAS mất • LAN dự phòng",
        "Giả lập cloud path mất nhưng LAN Master/backup còn.",
        "LAN phải ACK bền; sau cloud recovery cùng event_id phải hội tụ về canonical Service."
    );

    companion object{
        fun fromCode(code:String)=entries.firstOrNull{it.code==code}
    }
}

object ResilienceTestCenter {
    fun scenarios():List<ResilienceTestScenario> = ResilienceTestScenario.entries

    fun latest(context:Context):JSONObject? = OperationalDataStore(context).latestResilienceTest()

    fun history(context:Context,limit:Int=12):JSONArray =
        OperationalDataStore(context).resilienceTestHistory(limit)

    fun run(context:Context,scenario:ResilienceTestScenario):JSONObject =
        M2ServiceTransport(context.applicationContext).isolatedResilienceTest(scenario.code)

    fun resultVi(raw:String):String = when(raw.uppercase()){
        "PASS"->"PASS"
        "FAIL"->"FAIL"
        "NOT_AVAILABLE"->"CHƯA ĐỦ ĐIỀU KIỆN"
        "RUNNING"->"ĐANG KIỂM TRA"
        else->if(raw.isBlank())"CHƯA CHẠY" else raw
    }

    fun stageVi(raw:String):String = when(raw.uppercase()){
        "LOCAL_DURABLE"->"Đã ghi test event vào local ledger"
        "LOCAL_DURABLE_READBACK"->"Đã đọc lại local ledger"
        "SIMULATED_DEVICE_OFFLINE"->"Đang giả lập thiết bị mất Internet"
        "SIMULATED_SERVICE_UNAVAILABLE"->"Đang giả lập Service mất"
        "SIMULATED_SERVICE_TIMEOUT"->"Đang giả lập Service timeout"
        "SIMULATED_GOOGLE_UNAVAILABLE"->"Đang giả lập Google/GAS lỗi"
        "SIMULATED_SERVICE_GOOGLE_LAN_UNAVAILABLE"->"Đang giả lập tất cả đường remote mất"
        "SIMULATED_CLOUD_PATHS_UNAVAILABLE"->"Đang giả lập cloud path mất"
        "FALLBACK_CAPTURED"->"Emergency Ledger đã capture"
        "LAN_DURABLE_ACK"->"LAN đã ACK bền"
        "RECOVERY_REPLAY"->"Đang replay khi Service phục hồi"
        "SERVICE_PRIMARY"->"Đang kiểm tra Service chính"
        "SERVICE_DIRECT_WITH_GOOGLE_DOWN"->"Đang kiểm tra Service khi Google/GAS lỗi"
        "LAN_FALLBACK"->"Đang kiểm tra LAN dự phòng"
        "LAN_PREREQUISITE_MISSING"->"Thiếu điều kiện LAN Master/backup"
        "COMPLETE"->"Hoàn tất"
        else->if(raw.isBlank())"—" else raw
    }

    fun snapshotLines(context:Context):List<String>{
        val x=latest(context)?:return listOf("resilience_test.latest=NONE")
        val e=x.optJSONObject("evidence")?:JSONObject()
        return listOf(
            "resilience_test.event_id=${x.optString("event_id")}",
            "resilience_test.scenario=${x.optString("scenario")}",
            "resilience_test.status=${x.optString("status")}",
            "resilience_test.stage=${x.optString("stage")}",
            "resilience_test.attempt_count=${x.optInt("attempt_count")}",
            "resilience_test.last_error=${x.optString("last_error").take(180)}",
            "resilience_test.local_durable=${e.optBoolean("local_durable_readback",false)}",
            "resilience_test.business_outbox_touched=${e.optBoolean("business_outbox_touched",false)}",
            "resilience_test.google_captured=${e.optJSONObject("google")?.optBoolean("captured",false)?:false}",
            "resilience_test.lan_ack=${e.optBoolean("lan_ack",false)}",
            "resilience_test.duration_ms=${e.optLong("duration_ms",0L)}",
        )
    }
}
