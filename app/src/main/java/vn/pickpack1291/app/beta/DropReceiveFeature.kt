package vn.pickpack1291.app.beta

import android.app.Activity
import android.app.AlertDialog
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.text.Editable
import android.text.InputType
import android.text.TextWatcher
import android.text.method.DigitsKeyListener
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.widget.*
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

object DropReceiveQrParser {
    data class Parsed(val doNumber:String,val packageCount:Int)
    fun parse(raw:String):Parsed?{
        val parts=raw.split('|')
        if(parts.size<2)return null
        val order=parts.getOrNull(1)?.trim().orEmpty()
        if(order.isBlank())return null
        val tail=parts.lastOrNull().orEmpty()
        val slash=tail.lastIndexOf('/')
        if(slash<0||slash==tail.lastIndex)return null
        val count=tail.substring(slash+1).trim().toIntOrNull()?:return null
        if(count<=0)return null
        return Parsed(order,count)
    }
}

object DropReceiveFeature {
    fun build(activity:Activity,api:BetaApiClient,login:String,displayName:String,actualRole:String,confirmAction:(String,()->Unit)->Unit,onBack:()->Unit):View{
        val density=activity.resources.displayMetrics.density
        fun dp(v:Int)=(v*density).toInt()
        val teal=ThemeManager.primary(activity);val navy=ThemeManager.primaryDark(activity)
        val ink=Color.rgb(24,44,42);val muted=Color.rgb(100,116,139);val red=Color.rgb(218,45,53)
        fun bg(fill:Int=Color.WHITE,r:Int=12,stroke:Int=Color.argb(72,Color.red(teal),Color.green(teal),Color.blue(teal)))=GradientDrawable().apply{setColor(fill);cornerRadius=dp(r).toFloat();setStroke(dp(1),stroke)}
        fun text(value:String,size:Float,color:Int=ink,bold:Boolean=false)=TextView(activity).apply{text=value;textSize=size;setTextColor(color);typeface=if(bold)Typeface.DEFAULT_BOLD else Typeface.DEFAULT}
        fun column()=LinearLayout(activity).apply{orientation=LinearLayout.VERTICAL;setBackgroundColor(Color.WHITE)}
        fun row()=LinearLayout(activity).apply{orientation=LinearLayout.HORIZONTAL;setBackgroundColor(Color.WHITE);gravity=Gravity.CENTER_VERTICAL}
        fun gap(v:Int)=Space(activity).apply{layoutParams=ViewGroup.LayoutParams(1,dp(v))}
        fun input(hintText:String,numeric:Boolean=false)=EditText(activity).apply{hint=hintText;textSize=13f;setTextColor(ink);setHintTextColor(Color.rgb(148,163,184));setPadding(dp(11),dp(8),dp(11),dp(8));minHeight=dp(46);background=bg();setSingleLine(true);if(numeric){inputType=InputType.TYPE_CLASS_NUMBER;keyListener=DigitsKeyListener.getInstance("0123456789")}else inputType=InputType.TYPE_CLASS_TEXT}
        fun button(label:String,color:Int)=Button(activity).apply{text=label;textSize=9.4f;setTextColor(Color.WHITE);typeface=Typeface.DEFAULT_BOLD;isAllCaps=false;setPadding(dp(3),0,dp(3),0);background=GradientDrawable().apply{setColor(color);cornerRadius=dp(10).toFloat()}}
        fun field(label:String,view:View)=column().apply{addView(text(label,9.7f,muted,true));addView(gap(3));addView(view,LinearLayout.LayoutParams(-1,-2))}
        fun error(message:String)=TopNotice.show(activity,message,TopNotice.Kind.ERROR)
        fun success(message:String)=TopNotice.show(activity,message,TopNotice.Kind.SUCCESS)
        fun warning(message:String)=TopNotice.show(activity,message,TopNotice.Kind.WARNING)

        val root=column()
        val bar=row().apply{setPadding(dp(10),dp(7),dp(10),dp(7));background=GradientDrawable(GradientDrawable.Orientation.TL_BR,intArrayOf(navy,ThemeManager.accent(activity))).apply{cornerRadius=0f}}
        bar.addView(ImageView(activity).apply{setImageResource(R.drawable.ic_pp_back);imageTintList=ColorStateList.valueOf(Color.WHITE);setPadding(dp(6),dp(6),dp(6),dp(6));contentDescription="Quay lại";setOnClickListener{onBack()}},LinearLayout.LayoutParams(dp(34),dp(34)))
        bar.addView(text("NHẬN HÀNG RỚT",15f,Color.WHITE,true),LinearLayout.LayoutParams(0,-2,1f).apply{marginStart=dp(5)})
        root.addView(bar,LinearLayout.LayoutParams(-1,-2))

        val body=column().apply{setPadding(dp(10),dp(8),dp(10),dp(18))}
        val normalizedRole=actualRole.uppercase();val actualSuper=normalizedRole=="SUPERADMIN";val canDelete=normalizedRole=="ADMIN"||actualSuper
        val locationSpinner=Spinner(activity).apply{minimumHeight=dp(38);setPadding(dp(7),dp(1),dp(7),dp(1));background=bg()}
        fun iconButton(res:Int,color:Int,desc:String)=ImageButton(activity).apply{setImageResource(res);imageTintList=ColorStateList.valueOf(Color.WHITE);contentDescription=desc;setPadding(dp(10),dp(10),dp(10),dp(10));background=GradientDrawable().apply{setColor(color);cornerRadius=dp(10).toFloat()}}
        val createBtn=iconButton(R.drawable.ic_pp_add,teal,"Tạo vị trí");val editBtn=iconButton(R.drawable.ic_pp_edit,navy,"Sửa vị trí");val deleteBtn=iconButton(R.drawable.ic_pp_delete,red,"Xóa vị trí")
        var canManageLocations=false
        fun applyLocationPermission(allowed:Boolean){canManageLocations=allowed;listOf(createBtn,editBtn,deleteBtn).forEach{it.isEnabled=allowed;it.alpha=if(allowed)1f else .35f}}
        applyLocationPermission(false)
        body.addView(text("Vị trí",9.7f,muted,true));body.addView(gap(3))
        val locationRow=row();locationRow.addView(locationSpinner,LinearLayout.LayoutParams(0,dp(38),1f).apply{marginEnd=dp(4)});locationRow.addView(createBtn,LinearLayout.LayoutParams(dp(44),dp(44)).apply{marginStart=dp(2);marginEnd=dp(2)});locationRow.addView(editBtn,LinearLayout.LayoutParams(dp(44),dp(44)).apply{marginStart=dp(2);marginEnd=dp(2)});locationRow.addView(deleteBtn,LinearLayout.LayoutParams(dp(44),dp(44)).apply{marginStart=dp(2)})
        body.addView(locationRow,LinearLayout.LayoutParams(-1,-2));body.addView(gap(9))

        val qr=input("Scan QR").apply{imeOptions=EditorInfo.IME_ACTION_DONE}
        val order=input("DO");val packages=input("Số kiện",true)
        body.addView(field("Scan QR",qr));body.addView(gap(8))
        val doPackage=row()
        doPackage.addView(field("DO",order),LinearLayout.LayoutParams(0,-2,1f).apply{marginEnd=dp(4)})
        doPackage.addView(field("Số kiện",packages),LinearLayout.LayoutParams(0,-2,1f).apply{marginStart=dp(4)})
        body.addView(doPackage,LinearLayout.LayoutParams(-1,-2));body.addView(gap(10))
        val addBtn=button("Thêm thông tin",teal).apply{textSize=11f};val clearBtn=button("Xóa toàn bộ",red).apply{textSize=11f;isEnabled=actualSuper;alpha=if(actualSuper)1f else .35f}
        val actions=row();actions.addView(addBtn,LinearLayout.LayoutParams(0,dp(46),1f).apply{marginEnd=dp(4)});actions.addView(clearBtn,LinearLayout.LayoutParams(0,dp(46),1f).apply{marginStart=dp(4)});body.addView(actions,LinearLayout.LayoutParams(-1,-2))
        body.addView(gap(10))
        val listHead=row();listHead.addView(text("Danh sách hàng rớt",11f,navy,true),LinearLayout.LayoutParams(0,-2,1f))
        val selectAll=button("Chọn tất cả",navy);val deleteSelected=button("Xóa đã chọn",red).apply{isEnabled=false;alpha=.4f;visibility=if(canDelete)View.VISIBLE else View.GONE}
        listHead.addView(selectAll,LinearLayout.LayoutParams(dp(94),dp(38)).apply{marginEnd=dp(3)});listHead.addView(deleteSelected,LinearLayout.LayoutParams(dp(106),dp(38)))
        body.addView(listHead,LinearLayout.LayoutParams(-1,-2));body.addView(gap(5))
        val dropList=column();body.addView(dropList,LinearLayout.LayoutParams(-1,-2))
        body.addView(gap(8));body.addView(text("Service/D1 xác nhận ngay; Google Sheet được đồng bộ nền qua outbox.",9f,muted,false))

        val scroll=ScrollView(activity).apply{isFillViewport=true;addView(body,ViewGroup.LayoutParams(-1,-2))}
        root.addView(scroll,LinearLayout.LayoutParams(-1,0,1f))

        val locationCache=activity.getSharedPreferences("drop_receive_location_cache",android.content.Context.MODE_PRIVATE)
        var locationItems=listOf<String>()
        var pendingRecordId:String?=null
        val selectedDropIds=linkedSetOf<String>()
        var displayedDropIds=listOf<String>()
        fun selectedLocation():String=if(locationItems.isEmpty())"" else locationItems.getOrNull(locationSpinner.selectedItemPosition).orEmpty()
        fun setLocations(items:List<String>,preferred:String=""){
            val clean=items.map{it.trim()}.filter{it.isNotBlank()}.distinct();locationItems=clean
            val shown=if(clean.isEmpty())listOf("Chưa có vị trí") else clean
            locationSpinner.adapter=ArrayAdapter(activity,android.R.layout.simple_spinner_dropdown_item,shown)
            val index=clean.indexOf(preferred);locationSpinner.setSelection(if(index>=0)index else 0)
        }
        fun cacheLocations(items:List<String>){locationCache.edit().putString("items",JSONArray(items).toString()).apply()}
        fun cachedLocations():List<String>{val raw=locationCache.getString("items","").orEmpty();if(raw.isBlank())return emptyList();return runCatching{val arr=JSONArray(raw);val out=mutableListOf<String>();for(i in 0 until arr.length()){val v=arr.optString(i).trim();if(v.isNotBlank())out.add(v)};out}.getOrDefault(emptyList())}
        fun readItems(json:JSONObject?):List<String>{val arr=json?.optJSONArray("items")?:JSONArray();val out=mutableListOf<String>();for(i in 0 until arr.length()){val v=arr.optString(i).trim();if(v.isNotBlank())out.add(v)};return out}
        fun fmtDropTime(raw:String):String=runCatching{
            java.time.Instant.parse(raw).atZone(java.time.ZoneId.of("Asia/Ho_Chi_Minh")).format(java.time.format.DateTimeFormatter.ofPattern("HH:mm dd/MM/yyyy"))
        }.getOrDefault(raw.ifBlank{"-"})
        fun updateDeleteSelection(){
            deleteSelected.isEnabled=canDelete&&selectedDropIds.isNotEmpty();deleteSelected.alpha=if(deleteSelected.isEnabled)1f else .4f
            deleteSelected.text=if(selectedDropIds.isEmpty())"Xóa đã chọn" else "Xóa ${selectedDropIds.size}"
        }
        fun renderDropList(items:List<JSONObject>){
            val sorted=items.sortedByDescending{runCatching{java.time.Instant.parse(it.optString("created_at")).toEpochMilli()}.getOrDefault(0L)}
            dropList.removeAllViews();displayedDropIds=sorted.map{it.optString("record_id")}.filter{it.isNotBlank()}
            selectedDropIds.retainAll(displayedDropIds.toSet());updateDeleteSelection()
            if(sorted.isEmpty()){dropList.addView(text("Chưa có dữ liệu nhận hàng rớt.",9.7f,muted,false));return}
            sorted.forEach{x->
                val id=x.optString("record_id")
                val card=column().apply{setPadding(dp(8),dp(7),dp(8),dp(7));background=bg()}
                val line=row().apply{gravity=Gravity.CENTER_VERTICAL}
                val check=CheckBox(activity).apply{visibility=if(canDelete)View.VISIBLE else View.GONE;isChecked=id in selectedDropIds;setOnCheckedChangeListener{_,on->if(on)selectedDropIds.add(id)else selectedDropIds.remove(id);updateDeleteSelection()}}
                if(canDelete)line.addView(check,LinearLayout.LayoutParams(dp(34),dp(34)))
                fun cell(value:String,weight:Float,gravityValue:Int=Gravity.START)=text(value,8.9f,ink,true).apply{gravity=gravityValue;maxLines=2;setPadding(dp(3),0,dp(3),0)}
                line.addView(cell(fmtDropTime(x.optString("created_at")),1.18f),LinearLayout.LayoutParams(0,-2,1.18f))
                line.addView(cell(x.optString("location").ifBlank{"-"},.78f),LinearLayout.LayoutParams(0,-2,.78f))
                line.addView(cell("DO: ${x.optString("do_number").ifBlank{"-"}}",1.12f),LinearLayout.LayoutParams(0,-2,1.12f))
                line.addView(cell("Số kiện: ${x.optInt("package_count")}",.92f,Gravity.END),LinearLayout.LayoutParams(0,-2,.92f))
                card.addView(line);dropList.addView(card,LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(5)})
            }
        }
        fun loadDropList(){
            api.call("outbound_drop_list"){r->activity.runOnUiThread{
                if(!r.ok){if(dropList.childCount==0)dropList.addView(text("Chưa tải được danh sách.",9.5f,muted,false));return@runOnUiThread}
                val a=r.json?.optJSONArray("items")?:JSONArray();val items=(0 until a.length()).mapNotNull{a.optJSONObject(it)?.let{j->JSONObject(j.toString())}}
                renderDropList(items)
            }}
        }
        selectAll.visibility=if(canDelete)View.VISIBLE else View.GONE
        selectAll.setOnClickListener{if(!canDelete)return@setOnClickListener;selectedDropIds.clear();selectedDropIds.addAll(displayedDropIds);updateDeleteSelection();loadDropList()}
        deleteSelected.setOnClickListener{
            if(!canDelete){error("Chỉ ADMIN/SUPERADMIN được xóa hàng rớt.");return@setOnClickListener};val ids=selectedDropIds.toList();if(ids.isEmpty())return@setOnClickListener
            confirmAction("xóa ${ids.size} hàng rớt"){
                api.call("outbound_drop_delete",JSONObject().put("record_ids",JSONArray(ids)).put("idempotency_key",UUID.randomUUID().toString())){r->activity.runOnUiThread{
                    if(!r.ok){error(r.error?:"Không xóa được hàng rớt.");return@runOnUiThread}
                    selectedDropIds.clear();success("Đã xóa ${r.json?.optInt("rows_deleted",ids.size)?:ids.size} bản ghi.");loadDropList()
                }}
            }
        }

        fun reloadLocations(preferred:String=""){
            api.call("outbound_location_list"){r->activity.runOnUiThread{
                if(!r.ok){error(r.error?:"Không tải được danh sách vị trí từ Service/D1.");return@runOnUiThread}
                val items=readItems(r.json);applyLocationPermission(r.json?.optBoolean("owner",false)==true);setLocations(items,preferred);cacheLocations(items)
            }}
        }
        fun locationDialog(title:String,initial:String="",save:(String)->Unit){
            val value=input("Tên vị trí").apply{setText(initial);setSelection(text.length)}
            val dialog=AlertDialog.Builder(activity).setTitle(title).setView(value).setNegativeButton("Hủy",null).setPositiveButton("LƯU",null).create()
            dialog.setOnShowListener{dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener{val v=value.text.toString().trim().replace(Regex("\\s+")," ");if(v.isBlank()){error("Vị trí không được để trống.");return@setOnClickListener};dialog.dismiss();save(v)}};dialog.show();value.requestFocus()
        }
        fun mutateLocation(op:String,before:String,after:String){
            val eventId=UUID.randomUUID().toString()
            api.call("outbound_location_mutate",JSONObject().put("operation",op).put("before",before).put("after",after).put("event_id",eventId).put("idempotency_key",eventId)){r->activity.runOnUiThread{
                if(!r.ok){error(r.error?:"Service/D1 chưa xác nhận cập nhật vị trí.");return@runOnUiThread}
                val preferred=if(op=="DELETE")"" else after
                val items=readItems(r.json);applyLocationPermission(r.json?.optBoolean("owner",canManageLocations)==true);setLocations(items,preferred);cacheLocations(items);success("Service/D1 đã xác nhận vị trí; Google Sheet đồng bộ nền.")
            }}
        }
        createBtn.setOnClickListener{if(!canManageLocations)return@setOnClickListener;locationDialog("Tạo vị trí"){v->mutateLocation("CREATE","",v)}}
        editBtn.setOnClickListener{if(!canManageLocations)return@setOnClickListener;val before=selectedLocation();if(before.isBlank()){warning("Chưa có vị trí để sửa.");return@setOnClickListener};locationDialog("Sửa vị trí",before){v->mutateLocation("UPDATE",before,v)}}
        deleteBtn.setOnClickListener{if(!canManageLocations)return@setOnClickListener;val before=selectedLocation();if(before.isBlank()){warning("Chưa có vị trí để xóa.");return@setOnClickListener};AlertDialog.Builder(activity).setTitle("Xóa vị trí?").setMessage("Xóa “$before” khỏi danh sách chọn?").setNegativeButton("Hủy",null).setPositiveButton("XÓA"){_,_->mutateLocation("DELETE",before,"")}.show()}

        fun parseQr(showInvalid:Boolean){
            val raw=qr.text.toString();if(raw.isBlank())return
            val parsed=DropReceiveQrParser.parse(raw)
            if(parsed==null){if(showInvalid)warning("QR không đúng cấu trúc. Có thể nhập tay DO và Số kiện.");return}
            order.setText(parsed.doNumber);packages.setText(parsed.packageCount.toString())
        }
        qr.setOnEditorActionListener{_,id,_->if(id==EditorInfo.IME_ACTION_DONE||id==EditorInfo.IME_ACTION_GO||id==EditorInfo.IME_ACTION_SEARCH){parseQr(true);true}else false}
        qr.setOnKeyListener{_,key,event->if(key==KeyEvent.KEYCODE_ENTER&&event.action==KeyEvent.ACTION_UP){parseQr(true);true}else false}
        qr.addTextChangedListener(object:TextWatcher{override fun beforeTextChanged(s:CharSequence?,st:Int,c:Int,a:Int)=Unit;override fun onTextChanged(s:CharSequence?,st:Int,b:Int,c:Int){val v=s?.toString().orEmpty();if(v.count{it=='|'}>=5&&v.substringAfterLast('|').contains('/'))parseQr(false)};override fun afterTextChanged(s:Editable?)=Unit})

        addBtn.setOnClickListener{
            val location=selectedLocation();val orderNo=order.text.toString().trim();val countText=packages.text.toString().trim();val count=countText.toIntOrNull()
            if(location.isBlank()){warning("Chọn Vị trí.");return@setOnClickListener};if(orderNo.isBlank()){warning("Nhập DO.");return@setOnClickListener};if(count==null||count<=0){warning("Số kiện phải là số nguyên lớn hơn 0.");return@setOnClickListener}
            val id=pendingRecordId?:UUID.randomUUID().toString().also{pendingRecordId=it};addBtn.isEnabled=false;addBtn.text="Đang xác nhận Service..."
            val payload=JSONObject().put("location",location).put("scan_qr",qr.text.toString()).put("do_number",orderNo).put("package_count",count).put("idempotency_key",id)
            api.call("outbound_drop_append",payload){r->activity.runOnUiThread{
                addBtn.isEnabled=true;addBtn.text="Thêm thông tin"
                if(!r.ok){error(r.error?:"Service/D1 chưa xác nhận. Dữ liệu trên form được giữ nguyên để thử lại cùng mã chống trùng.");return@runOnUiThread}
                pendingRecordId=null;qr.setText("");order.setText("");packages.setText("");success("Service/D1 đã nhận đúng một bản ghi; Google Sheet đồng bộ nền.");loadDropList()
            }}
        }

        clearBtn.setOnClickListener{
            if(!actualSuper){error("Chỉ Superadmin được Xóa toàn bộ.");return@setOnClickListener}
            AlertDialog.Builder(activity).setTitle("Xóa toàn bộ dữ liệu?").setMessage("Chỉ xóa các dòng nghiệp vụ trong tab Nhận hàng rớt; không xóa header, Vị trí, quyền hoặc protected ranges.").setNegativeButton("Hủy",null).setPositiveButton("TIẾP TỤC"){_,_->
                val pw=input("Nhập mật khẩu thực tế").apply{inputType=InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD}
                val authDialog=AlertDialog.Builder(activity).setTitle("Xác thực trước khi xóa").setView(pw).setNegativeButton("Hủy",null).setPositiveButton("XÁC THỰC",null).create()
                authDialog.setOnShowListener{val b=authDialog.getButton(AlertDialog.BUTTON_POSITIVE);b.setOnClickListener{val password=pw.text.toString();if(password.isBlank()){error("Nhập mật khẩu thực tế.");return@setOnClickListener};b.isEnabled=false;b.text="Đang xác thực...";api.login(login,password){lr->activity.runOnUiThread{b.isEnabled=true;b.text="XÁC THỰC";if(!lr.ok){error("Không thể xác thực mật khẩu.");return@runOnUiThread};authDialog.dismiss();clearBtn.isEnabled=false;api.call("outbound_drop_clear",JSONObject().put("idempotency_key",UUID.randomUUID().toString())){cr->activity.runOnUiThread{clearBtn.isEnabled=true;if(!cr.ok){error(cr.error?:"Service/D1 chưa xác nhận lệnh xóa.");return@runOnUiThread};success("Service/D1 đã xác nhận xóa; Google Sheet đồng bộ nền.")}}}}}};authDialog.show();pw.requestFocus()
            }.show()
        }

        setLocations(cachedLocations());reloadLocations(selectedLocation());loadDropList()
        return root
    }
}
