package vn.pickpack1291.app.beta

/** Pure acceptance policy so fault-injection evidence can be unit-tested without Android/network. */
object ResilienceProbePolicy {
    data class Verdict(val state:String,val detail:String)

    fun evaluate(mode:String,hasProbe:Boolean,status:String,error:String,attempts:Int):Verdict {
        if(!hasProbe)return Verdict("CHƯA CHẠY","Chọn một kịch bản rồi bấm CHẠY PROBE.")
        if(status in setOf("REJECTED","REVIEW_REQUIRED","CONFLICT"))
            return Verdict("FAIL","Probe kết thúc lỗi: ${status.ifBlank{"UNKNOWN"}} • ${error.ifBlank{"không có mã lỗi"}}")
        return when(mode){
            "NORMAL"->if(status=="CONFIRMED") Verdict("PASS","Phục hồi PASS: probe đã về canonical Service.")
                else Verdict("ĐANG PHỤC HỒI","Probe còn ${status.ifBlank{"PENDING"}}; bấm LÀM MỚI sau vài giây.")
            "DISABLE_CLOUDFLARE"->when{
                status=="OFFLINE_PROVISIONAL"&&error.contains("EMERGENCY_LEDGER_CAPTURED")->Verdict("PASS","Service bị chặn đúng; Emergency Ledger đã ACK và local vẫn giữ replay.")
                status=="CONFIRMED"->Verdict("FAIL","Probe đã vào Service dù đang bật mô phỏng Service chết.")
                else->Verdict("ĐANG KIỂM TRA","Đang chờ Emergency Ledger ACK; hiện tại ${status.ifBlank{"PENDING"}}.")
            }
            "DISABLE_GOOGLE"->when{
                status=="CONFIRMED"->Verdict("PASS","Google/GAS bị chặn nhưng Service vẫn xác nhận probe.")
                status=="OFFLINE_PROVISIONAL"->Verdict("FAIL","Probe đã đi vào Emergency Ledger dù Google/GAS phải đang bị chặn.")
                else->Verdict("ĐANG KIỂM TRA","Đang chờ Service xác nhận; hiện tại ${status.ifBlank{"PENDING"}}.")
            }
            "DISABLE_BOTH"->when{
                status=="CONFIRMED"||status=="OFFLINE_PROVISIONAL"->Verdict("FAIL","Probe đã được cloud xác nhận trong khi cả hai đường phải bị chặn.")
                attempts>0&&status in setOf("LOCAL_PENDING","PENDING","RETRY","LAN_CONFIRMED")->Verdict("PASS","Không có cloud ACK; probe vẫn được giữ bền local${if(status=="LAN_CONFIRMED")" / LAN" else ""} để replay.")
                else->Verdict("ĐANG KIỂM TRA","Đang chờ ít nhất một lần retry để chứng minh local durability.")
            }
            else->Verdict("FAIL","Kịch bản test không hợp lệ.")
        }
    }
}
