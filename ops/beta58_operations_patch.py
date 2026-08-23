from pathlib import Path
import re

p=Path("app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt")
s=p.read_text(encoding="utf-8")
if "S59_BETA58_SHIFT_RECONCILIATION_HOME" in s:
    print("OperationsActivity already patched")
    raise SystemExit(0)

def one(old,new,label):
    global s
    n=s.count(old)
    if n!=1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {n}")
    s=s.replace(old,new,1)

one(
'''                when (screenState) {
                    "LISTS" -> listsScreen()
                    "REPORT" -> reportScreen()
                    "HISTORY" -> historyScreen()
                }''',
'''                when (screenState) {
                    "BUSINESS" -> businessHome()
                    "LISTS" -> listsScreen()
                    "REPORT" -> reportScreen()
                    "HISTORY" -> historyScreen()
                }''',
"foreground business refresh")

one(
'''        val root=baseRoot("NGHIỆP VỤ");val body=body()
        val cards=listOf(''',
'''        val root=baseRoot("NGHIỆP VỤ");val body=body()
        addBusinessShiftReconciliation(body)
        val cards=listOf(''',
"business placement")

helper='''    // S59_BETA58_SHIFT_RECONCILIATION_HOME: below status chips, above business cards; empty shifts stay hidden.
    private fun addBusinessShiftReconciliation(body:LinearLayout){
        val day=operationalStore.loadDay(operationalStore.businessDate())?:return
        val sessions=day.optJSONArray("sessions")?:JSONArray()
        val byShift=linkedMapOf<String,MutableList<JSONObject>>(
            "Ca 1" to mutableListOf(), "Ca HC" to mutableListOf(), "Ca 2" to mutableListOf()
        )
        for(i in 0 until sessions.length()){
            val ses=sessions.optJSONObject(i)?:continue
            val shift=ses.optString("shift").trim().ifBlank{"Chưa xác định"}
            byShift.getOrPut(shift){mutableListOf()}.add(JSONObject(ses.toString()))
        }
        val visible=byShift.mapNotNull{(shift,rows)->
            val entered=rows.filter{it.optString("enter_at").isNotBlank()||it.optString("state").uppercase() in setOf("ACTIVE","ENDED")}
            if(entered.isEmpty())null else shift to entered
        }
        if(visible.isEmpty())return
        body.addView(section("ĐỐI SOÁT VÀO / RA"))
        visible.forEach{(shift,entered)->
            val exited=entered.filter{it.optString("exit_at").isNotBlank()||it.optString("state").equals("ENDED",true)}
            val pending=entered.filter{it.optString("state").equals("ACTIVE",true)&&it.optString("exit_at").isBlank()}
            val button=smallButton("$shift  •  Vào ${entered.size}  •  Ra ${exited.size}  •  Chưa ra ${pending.size}",if(pending.isNotEmpty())orange else teal)
            button.setOnClickListener{
                if(pending.isEmpty()){
                    TopNotice.show(this,"$shift không có nhân sự đã vào nhưng chưa ra.",TopNotice.Kind.SUCCESS)
                }else{
                    val labels=pending.map{ses->
                        val mnv=ses.optString("mnv").trim()
                        val emp=MasterDataCache.employee(this,mnv)
                        val display=emp?.optString("full_name").orEmpty().ifBlank{ses.optJSONObject("employee_snapshot")?.optString("full_name").orEmpty()}
                        "$mnv • ${display.ifBlank{"Chưa có tên"}}"
                    }
                    AlertDialog.Builder(this)
                        .setTitle("$shift • ${pending.size} nhân sự chưa ra")
                        .setItems(labels.toTypedArray()){_,which->
                            pending.getOrNull(which)?.optString("mnv")?.takeIf{it.isNotBlank()}?.let(::loadEmployee)
                        }
                        .setNegativeButton("Đóng",null)
                        .show()
                }
            }
            body.addView(button,matchWrap());body.addView(gap(5))
        }
        body.addView(gap(4))
    }

'''
one('    private fun employeeScan() {\n',helper+'    private fun employeeScan() {\n',"helper insertion")

pattern=re.compile(r'\n\s*// S58_BETA57_SHIFT_DISCREPANCY: canonical selected-day Vao/Ra/Chua-ra drilldown\..*?\n\s*val box=column\(bg\);body\.addView\(box,matchWrap\(\)\)',re.S)
m=pattern.search(s)
if not m:
    raise SystemExit("report discrepancy block not found")
s=s[:m.start()]+'\n        val box=column(bg);body.addView(box,matchWrap())'+s[m.end():]
s=s.replace(';renderShiftDiscrepancy()','')
if 'renderShiftDiscrepancy' in s:
    raise SystemExit("residual report discrepancy renderer")

one(
'''        if(ServiceFaultInjection.cloudflareDisabled(this)){return if(mode=="GOOGLE_FALLBACK"&&!ServiceFaultInjection.googleDisabled(this))"Google Drive" else "OFFLINE"}''',
'''        if(ServiceFaultInjection.cloudflareDisabled(this)){return if(!ServiceFaultInjection.googleDisabled(this))"Google Drive" else "OFFLINE"}''',
"fault injection provider label")

p.write_text(s,encoding="utf-8")
print("Beta58 OperationsActivity patch applied")
