package vn.pickpack1291.app.beta

import android.content.Context
import org.json.JSONObject

/**
 * Beta100 compatibility shim.
 *
 * Beta99 used device-global fault flags that could affect real operational traffic.
 * Owner-acceptance testing is now isolated in ResilienceTestCenter; production transport
 * must never be blocked by a test selection.
 */
@Deprecated("Use ResilienceTestCenter")
object ServiceFaultInjection {
    enum class Mode(val stored:String,val label:String,val expected:String) {
        NORMAL("NORMAL","Bình thường","Không có fault injection trên traffic nghiệp vụ."),
        DISABLE_CLOUDFLARE("DISABLE_CLOUDFLARE","Legacy • Service off","Đã vô hiệu hóa từ Beta100."),
        DISABLE_GOOGLE("DISABLE_GOOGLE","Legacy • Google off","Đã vô hiệu hóa từ Beta100."),
        DISABLE_BOTH("DISABLE_BOTH","Legacy • cả hai off","Đã vô hiệu hóa từ Beta100."),
    }

    fun mode(context:Context):Mode = Mode.NORMAL
    fun setMode(context:Context,mode:Mode) = Unit
    fun runProbe(context:Context):JSONObject =
        JSONObject().put("status","MIGRATED").put("message","Use ResilienceTestCenter")
    fun endAndRecover(context:Context) = Unit
    fun testSnapshot(context:Context):JSONObject =
        JSONObject().put("mode","NORMAL").put("result","MIGRATED").put("detail","Resilience tests are isolated from business traffic.")
    fun cloudflareDisabled(context:Context):Boolean = false
    fun googleDisabled(context:Context):Boolean = false
    fun label(context:Context):String = Mode.NORMAL.label
}
