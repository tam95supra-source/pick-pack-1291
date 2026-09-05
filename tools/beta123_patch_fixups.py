from pathlib import Path

p=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
s=p.read_text(encoding='utf-8')

def replace_once(old,new,label):
    if old not in s:
        raise SystemExit(f'{label}: anchor missing')
    return s.replace(old,new,1)

# History: keep existing SUPERADMIN permission/password semantics, but wire an explicit
# whole-selected-day action using the same canonical/local rows already rendered by History.
old='''            val choose=row(bg);val selectPage=smallButton("CHỌN TRANG",navy);val clear=smallButton("BỎ CHỌN",muted);val deleteSelected=smallButton("XÓA ĐÃ CHỌN",red)
            choose.addView(selectPage,LinearLayout.LayoutParams(0,dp(40),1f).apply{marginEnd=dp(2)});choose.addView(clear,LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2);marginEnd=dp(2)});choose.addView(deleteSelected,LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2)});selectionBox.addView(gap(5));selectionBox.addView(choose,matchWrap());selectionBox.addView(gap(8))
            selectPage.setOnClickListener{selectedHistoryIds.addAll(currentPageDeleteIds);pageChecks.forEach{it.isChecked=true};updateSelectedCount()}
            clear.setOnClickListener{selectedHistoryIds.clear();pageChecks.forEach{it.isChecked=false};updateSelectedCount()}
            deleteSelected.setOnClickListener{deleteHistoryBulk(selectedHistoryIds.toList())}
'''
new='''            val choose=row(bg);val selectPage=smallButton("CHỌN",navy);val clear=smallButton("BỎ CHỌN",muted);val deleteSelected=smallButton("XÓA ĐÃ CHỌN",red);val deleteAllDate=smallButton("XÓA TOÀN BỘ",red)
            choose.addView(selectPage,LinearLayout.LayoutParams(0,dp(38),.72f).apply{marginEnd=dp(2)});choose.addView(clear,LinearLayout.LayoutParams(0,dp(38),.82f).apply{marginStart=dp(2);marginEnd=dp(2)});choose.addView(deleteSelected,LinearLayout.LayoutParams(0,dp(38),1.18f).apply{marginStart=dp(2);marginEnd=dp(2)});choose.addView(deleteAllDate,LinearLayout.LayoutParams(0,dp(38),1.28f).apply{marginStart=dp(2)});selectionBox.addView(gap(5));selectionBox.addView(choose,matchWrap());selectionBox.addView(gap(8))
            selectPage.setOnClickListener{selectedHistoryIds.addAll(currentPageDeleteIds);pageChecks.forEach{it.isChecked=true};updateSelectedCount()}
            clear.setOnClickListener{selectedHistoryIds.clear();pageChecks.forEach{it.isChecked=false};updateSelectedCount()}
            deleteSelected.setOnClickListener{deleteHistoryBulk(selectedHistoryIds.toList())}
            deleteAllDate.setOnClickListener{
                val priorQuery=query;query=""
                val all=loadRows().filter{eventDate(it,selectedDate)==selectedDate&&it.optString("event_type").uppercase()!="HISTORY_DELETE"}.map{it.optString("event_id")}.filter{it.isNotBlank()}.distinct()
                query=priorQuery
                if(all.isEmpty())TopNotice.show(this,"Ngày đã chọn không có lịch sử để xóa.",TopNotice.Kind.INFO) else deleteHistoryBulk(all)
            }
'''
if old in s:
    s=s.replace(old,new,1)
elif 'val deleteAllDate=smallButton("XÓA TOÀN BỘ",red)' not in s:
    raise SystemExit('history delete-all anchor missing')

# ADMIN/SUPERADMIN local outbox recovery. Normal retry never revives rejected/conflict rows;
# force retry keeps immutable event IDs; permanent delete is enforced by store to terminal rows only.
anchor='''    private fun syncScreen(){
'''
helper='''    private fun showSyncQueueRecoveryDialog(){
        if(!isAdmin()){showError("Chỉ ADMIN/SUPERADMIN được xử lý hàng đợi đồng bộ.");return}
        val items=runCatching{operationalStore.queueRecoveryItems(200)}.getOrDefault(emptyList())
        if(items.isEmpty()){TopNotice.show(this,"Không có dữ liệu cục bộ đang chờ xử lý.",TopNotice.Kind.INFO);return}
        val selected=linkedSetOf<String>()
        val host=column(surface).apply{setPadding(dp(9),dp(5),dp(9),dp(9))}
        val count=txt("Đã chọn 0/${items.size}",9.4f,muted,true)
        val top=row(surface);val all=smallButton("CHỌN TẤT CẢ",navy);val clear=smallButton("BỎ CHỌN",muted)
        top.addView(all,LinearLayout.LayoutParams(0,dp(36),1f).apply{marginEnd=dp(3)});top.addView(clear,LinearLayout.LayoutParams(0,dp(36),1f).apply{marginStart=dp(3)})
        host.addView(top,matchWrap());host.addView(gap(4));host.addView(count);host.addView(gap(5))
        val checks=mutableListOf<CheckBox>()
        items.forEach{x->
            val line=row(surface).apply{gravity=Gravity.CENTER_VERTICAL;setPadding(dp(5),dp(4),dp(5),dp(4));background=outlineBg(surface,9)}
            val cb=CheckBox(this).apply{setOnCheckedChangeListener{_,on->if(on)selected.add(x.eventId)else selected.remove(x.eventId);count.text="Đã chọn ${selected.size}/${items.size}"}}
            checks.add(cb);line.addView(cb,LinearLayout.LayoutParams(dp(38),dp(38)))
            val detail=listOf(x.status,"Thử ${x.attempts} lần",x.lastError.takeIf{it.isNotBlank()}).filterNotNull().joinToString(" • ")
            line.addView(column(surface).apply{addView(txt(x.action,10f,navy,true));addView(txt(detail,8.8f,muted,false).apply{maxLines=2})},LinearLayout.LayoutParams(0,-2,1f))
            host.addView(line,matchWrap());host.addView(gap(3))
        }
        all.setOnClickListener{checks.forEach{it.isChecked=true}}
        clear.setOnClickListener{checks.forEach{it.isChecked=false}}
        val actions=column(surface)
        val retry=primary("THỬ LẠI",teal){}
        val force=primary("CƯỠNG ÉP THỬ LẠI",orange){}
        val remove=primary("XÓA HẲN LỖI ĐÃ DỪNG",red){}
        actions.addView(retry,matchWrap());actions.addView(gap(5));actions.addView(force,matchWrap());actions.addView(gap(5));actions.addView(remove,matchWrap());host.addView(gap(5));host.addView(actions,matchWrap())
        var dialog:AlertDialog?=null
        fun chosen():List<String>{val ids=selected.toList();if(ids.isEmpty())TopNotice.show(this,"Chọn ít nhất một mục.",TopNotice.Kind.WARNING);return ids}
        fun wake(changed:Int,label:String){
            if(changed>0){M2ImmediateOutbox.kick(applicationContext);M2WorkScheduler.schedule(applicationContext)}
            TopNotice.show(this,"$label: $changed mục.",if(changed>0)TopNotice.Kind.SUCCESS else TopNotice.Kind.INFO);dialog?.dismiss();syncScreen()
        }
        retry.setOnClickListener{val ids=chosen();if(ids.isNotEmpty())wake(operationalStore.retryQueue(ids,false),"Đã đưa về hàng chờ thử lại")}
        force.setOnClickListener{val ids=chosen();if(ids.isNotEmpty())AlertDialog.Builder(this).setTitle("Cưỡng ép thử lại?").setMessage("Giữ nguyên Event ID và đưa các lỗi/đối soát đã chọn về hàng chờ để gửi lại. Có thể bị Service từ chối lại nếu dữ liệu không còn hợp lệ.").setNegativeButton("Hủy",null).setPositiveButton("THỬ LẠI"){_,_->wake(operationalStore.retryQueue(ids,true),"Đã cưỡng ép thử lại")}.show()}
        remove.setOnClickListener{val ids=chosen();if(ids.isNotEmpty())AlertDialog.Builder(this).setTitle("Xóa hẳn lỗi đã dừng?").setMessage("Chỉ các mục đã dừng ở trạng thái lỗi/từ chối/xung đột mới bị xóa cục bộ. Mục đang chờ gửi không thể bị xóa bằng thao tác này.").setNegativeButton("Hủy",null).setPositiveButton("XÓA"){_,_->wake(operationalStore.deleteTerminalQueue(ids),"Đã xóa lỗi cục bộ")}.show()}
        dialog=AlertDialog.Builder(this).setTitle("Xử lý hàng đợi đồng bộ").setView(ScrollView(this).apply{addView(host)}).setNegativeButton("ĐÓNG",null).create();dialog?.show()
    }

    private fun syncScreen(){
'''
if 'private fun showSyncQueueRecoveryDialog()' not in s:
    if anchor not in s: raise SystemExit('sync helper anchor missing')
    s=s.replace(anchor,helper,1)

sync_actions='''        val actions=row(bg);val syncNow=smallButton("ĐỒNG BỘ NGAY",teal);val refresh=smallButton("LÀM MỚI",navy);actions.addView(syncNow,LinearLayout.LayoutParams(0,dp(38),1f).apply{marginEnd=dp(4)});actions.addView(refresh,LinearLayout.LayoutParams(0,dp(38),1f).apply{marginStart=dp(4)});body.addView(gap(9));body.addView(actions,matchWrap())
'''
if sync_actions in s and 'XỬ LÝ HÀNG ĐỢI' not in s:
    s=s.replace(sync_actions,sync_actions+'''        if(isAdmin()){body.addView(gap(6));body.addView(primary("XỬ LÝ HÀNG ĐỢI",orange){showSyncQueueRecoveryDialog()},matchWrap())}
''',1)

p.write_text(s,encoding='utf-8')
print('BETA123_FIXUPS_APPLIED')
