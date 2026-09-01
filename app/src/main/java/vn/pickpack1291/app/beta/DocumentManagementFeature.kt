package vn.pickpack1291.app.beta

import android.app.Activity
import android.app.AlertDialog
import android.content.res.ColorStateList
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.*
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.UUID
import java.util.concurrent.Executors

object DocumentManagementFeature {
    private data class Selected(
        val image:DocumentImageProcessor.ProcessedImage,
        val sourceKind:String,
        val capturedAt:String,
        val idempotencyKey:String
    )

    class Controller(
        private val activity:Activity,
        private val api:BetaApiClient,
        private val login:String,
        private val displayName:String,
        private val actualRole:String,
        private val onCamera:()->Unit,
        private val onGallery:()->Unit
    ){
        private val client=DocumentServiceClient(activity){api.token}
        private val executor=Executors.newSingleThreadExecutor()
        private val density=activity.resources.displayMetrics.density
        private val teal get()=ThemeManager.primary(activity)
        private val navy get()=ThemeManager.primaryDark(activity)
        private val ink=Color.rgb(24,44,42)
        private val muted=Color.rgb(100,116,139)
        private val red=Color.rgb(218,45,53)
        private val green=Color.rgb(36,153,85)
        private var selected:Selected?=null
        private var categoryIds=listOf<String>()
        private var categoryNames=listOf<String>()
        private lateinit var categorySpinner:Spinner
        private lateinit var preview:ImageView
        private lateinit var previewMeta:TextView
        private lateinit var uploadButton:Button
        private lateinit var recordsHost:LinearLayout
        private lateinit var emptyText:TextView
        @Volatile private var disposed=false
        @Volatile private var busy=false

        private fun dp(v:Int)=(v*density).toInt()
        private fun bg(fill:Int=Color.WHITE,r:Int=12,stroke:Int=Color.argb(72,Color.red(teal),Color.green(teal),Color.blue(teal)))=
            GradientDrawable().apply{setColor(fill);cornerRadius=dp(r).toFloat();setStroke(dp(1),stroke)}
        private fun text(value:String,size:Float,color:Int=ink,bold:Boolean=false)=TextView(activity).apply{
            text=value;textSize=size;setTextColor(color);typeface=if(bold)Typeface.DEFAULT_BOLD else Typeface.DEFAULT
        }
        private fun column()=LinearLayout(activity).apply{orientation=LinearLayout.VERTICAL;setBackgroundColor(Color.WHITE)}
        private fun row()=LinearLayout(activity).apply{orientation=LinearLayout.HORIZONTAL;setBackgroundColor(Color.WHITE);gravity=Gravity.CENTER_VERTICAL}
        private fun gap(v:Int)=Space(activity).apply{layoutParams=ViewGroup.LayoutParams(1,dp(v))}
        private fun button(label:String,color:Int)=Button(activity).apply{
            text=label;textSize=10.5f;setTextColor(Color.WHITE);typeface=Typeface.DEFAULT_BOLD;isAllCaps=false
            setPadding(dp(6),0,dp(6),0);background=GradientDrawable().apply{setColor(color);cornerRadius=dp(10).toFloat()}
        }
        private fun postUi(block:()->Unit){if(!disposed)activity.runOnUiThread{if(!disposed)block()}}
        private fun error(message:String)=TopNotice.show(activity,message,TopNotice.Kind.ERROR)
        private fun success(message:String)=TopNotice.show(activity,message,TopNotice.Kind.SUCCESS)
        private fun warning(message:String)=TopNotice.show(activity,message,TopNotice.Kind.WARNING)

        fun build():View{
            val root=column()
            val scroll=ScrollView(activity).apply{isFillViewport=true}
            val body=column().apply{setPadding(dp(10),dp(8),dp(10),dp(24))}
            scroll.addView(body,ViewGroup.LayoutParams(-1,-2))
            root.addView(scroll,LinearLayout.LayoutParams(-1,0,1f))

            body.addView(text("Ảnh được nén trên máy rồi tải thẳng lên Google Drive. Service chỉ lưu thông tin biên bản và dấu vân tay chống trùng.",9.6f,muted))
            body.addView(gap(3))
            body.addView(text("Người tải: ${displayName.ifBlank{login}}",9.2f,ink,true))
            body.addView(gap(9))

            val categoryBox=column().apply{background=bg();setPadding(dp(10),dp(9),dp(10),dp(10))}
            categoryBox.addView(text("Loại biên bản",10f,muted,true))
            categoryBox.addView(gap(4))
            categorySpinner=Spinner(activity).apply{minimumHeight=dp(46);setPadding(dp(8),dp(3),dp(8),dp(3));background=bg()}
            categoryBox.addView(categorySpinner,LinearLayout.LayoutParams(-1,dp(46)))
            categoryBox.addView(gap(6))
            val categoryActions=row()
            val add=button("Thêm",teal)
            val edit=button("Sửa",navy)
            val remove=button("Xóa",red)
            categoryActions.addView(add,LinearLayout.LayoutParams(0,dp(42),1f).apply{marginEnd=dp(3)})
            categoryActions.addView(edit,LinearLayout.LayoutParams(0,dp(42),1f).apply{marginStart=dp(3);marginEnd=dp(3)})
            categoryActions.addView(remove,LinearLayout.LayoutParams(0,dp(42),1f).apply{marginStart=dp(3)})
            categoryBox.addView(categoryActions,LinearLayout.LayoutParams(-1,-2))
            categoryBox.addView(gap(5))
            categoryBox.addView(text("Sửa/Xóa đang khóa chờ OWNER chốt quy tắc cho dữ liệu cũ. File đã tải lên không tự đổi tên.",8.8f,muted))
            body.addView(categoryBox,LinearLayout.LayoutParams(-1,-2))
            body.addView(gap(10))

            val imageBox=column().apply{background=bg();setPadding(dp(10),dp(9),dp(10),dp(10))}
            imageBox.addView(text("Ảnh biên bản",10f,muted,true))
            imageBox.addView(gap(6))
            val sourceActions=row()
            val camera=button("Chụp ảnh",teal)
            val gallery=button("Chọn từ máy",navy)
            sourceActions.addView(camera,LinearLayout.LayoutParams(0,dp(44),1f).apply{marginEnd=dp(4)})
            sourceActions.addView(gallery,LinearLayout.LayoutParams(0,dp(44),1f).apply{marginStart=dp(4)})
            imageBox.addView(sourceActions,LinearLayout.LayoutParams(-1,-2))
            imageBox.addView(gap(8))
            preview=ImageView(activity).apply{
                adjustViewBounds=true;scaleType=ImageView.ScaleType.FIT_CENTER;setBackgroundColor(Color.rgb(248,250,252))
                contentDescription="Ảnh biên bản đã chọn";visibility=View.GONE
            }
            imageBox.addView(preview,LinearLayout.LayoutParams(-1,dp(190)))
            previewMeta=text("Chưa chọn ảnh.",9.4f,muted)
            imageBox.addView(previewMeta)
            imageBox.addView(gap(8))
            uploadButton=button("Tải biên bản lên",green).apply{isEnabled=false;alpha=.4f}
            imageBox.addView(uploadButton,LinearLayout.LayoutParams(-1,dp(46)))
            body.addView(imageBox,LinearLayout.LayoutParams(-1,-2))
            body.addView(gap(12))

            val listHead=row()
            listHead.addView(text("Biên bản đã tải",11.5f,navy,true),LinearLayout.LayoutParams(0,-2,1f))
            val refresh=button("Làm mới",navy)
            listHead.addView(refresh,LinearLayout.LayoutParams(dp(90),dp(38)))
            body.addView(listHead,LinearLayout.LayoutParams(-1,-2));body.addView(gap(6))
            emptyText=text("Đang tải danh sách...",9.5f,muted).apply{setPadding(dp(4),dp(8),dp(4),dp(8))}
            body.addView(emptyText)
            recordsHost=column()
            body.addView(recordsHost,LinearLayout.LayoutParams(-1,-2))

            add.setOnClickListener{showAddCategory()}
            edit.setOnClickListener{warning("Sửa loại biên bản đang chờ OWNER chốt: tên hiển thị đổi nhưng file cũ không đổi tên.")}
            remove.setOnClickListener{warning("Xóa loại biên bản đang chờ OWNER chốt theo phương án ẩn/ngừng sử dụng, không xóa ảnh cũ.")}
            camera.setOnClickListener{if(!busy)onCamera()}
            gallery.setOnClickListener{if(!busy)onGallery()}
            uploadButton.setOnClickListener{uploadSelected(false)}
            refresh.setOnClickListener{refreshDocuments()}
            refreshCategories()
            refreshDocuments()
            return root
        }

        fun dispose(){disposed=true;executor.shutdownNow()}
        fun onImageSelected(uri:Uri,sourceKind:String){
            if(disposed||busy)return
            busy=true
            postUi{previewMeta.text="Đang tối ưu ảnh...";uploadButton.isEnabled=false;uploadButton.alpha=.4f}
            executor.execute{
                try{
                    val image=DocumentImageProcessor.process(activity,uri)
                    selected=Selected(image,sourceKind,Instant.now().toString(),UUID.randomUUID().toString())
                    postUi{
                        val bmp=BitmapFactory.decodeByteArray(image.bytes,0,image.bytes.size)
                        preview.setImageBitmap(bmp);preview.visibility=View.VISIBLE
                        previewMeta.text="${image.width} × ${image.height} • ${formatBytes(image.bytes.size.toLong())} • đã tạo dấu vân tay chống trùng"
                        uploadButton.isEnabled=categoryIds.isNotEmpty();uploadButton.alpha=if(uploadButton.isEnabled)1f else .4f
                    }
                }catch(t:Throwable){
                    postUi{error("Không đọc được ảnh: ${t.message?:"IMAGE_READ_FAILED"}");previewMeta.text="Chưa chọn ảnh."}
                }finally{
                    if(sourceKind=="CAMERA")runCatching{activity.contentResolver.delete(uri,null,null)}
                    busy=false
                }
            }
        }

        private fun refreshCategories(){
            executor.execute{
                val result=client.get("/v1/documents/categories")
                postUi{
                    if(!result.ok){categoryIds=emptyList();categoryNames=emptyList();categorySpinner.adapter=ArrayAdapter(activity,android.R.layout.simple_spinner_dropdown_item,listOf("Chưa có loại biên bản"));warning(messageFor(result.error));return@postUi}
                    val arr=result.json?.optJSONArray("items")?:JSONArray()
                    val ids=mutableListOf<String>();val names=mutableListOf<String>()
                    for(i in 0 until arr.length()){
                        val o=arr.optJSONObject(i)?:continue
                        val id=o.optString("category_id").trim();val name=o.optString("display_name").trim()
                        if(id.isNotBlank()&&name.isNotBlank()){ids.add(id);names.add(name)}
                    }
                    categoryIds=ids;categoryNames=names
                    categorySpinner.adapter=ArrayAdapter(activity,android.R.layout.simple_spinner_dropdown_item,if(names.isEmpty())listOf("Chưa có loại biên bản") else names)
                    uploadButton.isEnabled=selected!=null&&ids.isNotEmpty();uploadButton.alpha=if(uploadButton.isEnabled)1f else .4f
                }
            }
        }
        private fun showAddCategory(){
            val input=EditText(activity).apply{hint="Ví dụ: Biên bản bàn giao";setSingleLine(true);setPadding(dp(12),dp(8),dp(12),dp(8));background=bg()}
            val wrap=column().apply{setPadding(dp(16),dp(6),dp(16),0);addView(input,LinearLayout.LayoutParams(-1,dp(48)))}
            AlertDialog.Builder(activity).setTitle("Thêm loại biên bản").setView(wrap).setNegativeButton("Hủy",null).setPositiveButton("Thêm"){_,_->
                val name=input.text.toString().trim()
                if(name.isBlank()){warning("Nhập tên loại biên bản.");return@setPositiveButton}
                executor.execute{
                    val result=client.post("/v1/documents/categories",JSONObject().put("operation","CREATE").put("display_name",name))
                    postUi{if(result.ok){success("Đã thêm loại biên bản.");refreshCategories()}else error(messageFor(result.error))}
                }
            }.show()
        }

        private fun uploadSelected(allowSimilar:Boolean){
            val item=selected?:return
            val index=categorySpinner.selectedItemPosition
            val categoryId=categoryIds.getOrNull(index)?:run{warning("Hãy thêm/chọn loại biên bản.");return}
            if(busy)return
            busy=true
            postUi{uploadButton.isEnabled=false;uploadButton.text="Đang kiểm tra ảnh..."}
            executor.execute{
                val payload=JSONObject()
                    .put("category_id",categoryId).put("mime_type",item.image.mimeType).put("byte_size",item.image.bytes.size)
                    .put("sha256",item.image.sha256).put("md5",item.image.md5).put("dhash64",item.image.dhash64)
                    .put("width",item.image.width).put("height",item.image.height).put("source_kind",item.sourceKind)
                    .put("captured_at",item.capturedAt).put("idempotency_key",item.idempotencyKey).put("allow_similar",allowSimilar)
                val session=client.post("/v1/documents/upload-session",payload)
                if(!session.ok){
                    busy=false
                    postUi{
                        uploadButton.isEnabled=true;uploadButton.text="Tải biên bản lên"
                        when(session.error){
                            "DOCUMENT_EXACT_DUPLICATE"->warning("Ảnh này đã tồn tại trong Quản lý biên bản. Hệ thống đã chặn tải trùng.")
                            "DOCUMENT_SIMILAR_IMAGE"->showSimilarConfirm()
                            else->error(messageFor(session.error))
                        }
                    }
                    return@execute
                }
                if(session.json?.optBoolean("already_complete",false)==true){
                    selected=null;busy=false
                    postUi{clearSelected();success("Biên bản đã được ghi nhận trước đó.");refreshDocuments()}
                    return@execute
                }
                val document=session.json?.optJSONObject("document")
                val documentId=document?.optString("document_id").orEmpty()
                val uploadUrl=session.json?.optString("upload_url").orEmpty()
                if(documentId.isBlank()||uploadUrl.isBlank()){
                    busy=false;postUi{uploadButton.isEnabled=true;uploadButton.text="Tải biên bản lên";error("Service không cấp được phiên tải Drive.")};return@execute
                }
                postUi{uploadButton.text="Đang tải thẳng lên Drive..."}
                val drive=client.uploadToDrive(uploadUrl,item.image.bytes,item.image.mimeType)
                val driveId=drive.json?.optString("id").orEmpty()
                if(!drive.ok||driveId.isBlank()){
                    busy=false;postUi{uploadButton.isEnabled=true;uploadButton.text="Thử tải lại";error(messageFor(drive.error))};return@execute
                }
                postUi{uploadButton.text="Đang xác nhận..."}
                val complete=client.post("/v1/documents/complete",JSONObject().put("document_id",documentId).put("drive_file_id",driveId))
                busy=false
                postUi{
                    uploadButton.text="Tải biên bản lên"
                    if(!complete.ok){uploadButton.isEnabled=true;error(messageFor(complete.error));return@postUi}
                    selected=null;clearSelected();success("Đã tải biên bản lên Google Drive.");refreshDocuments()
                }
            }
        }
        private fun showSimilarConfirm(){
            AlertDialog.Builder(activity)
                .setTitle("Phát hiện ảnh có thể trùng")
                .setMessage("Dấu vân tay ảnh gần giống một biên bản đã có. Anh/chị vẫn muốn tải ảnh này lên?")
                .setNegativeButton("Hủy",null)
                .setPositiveButton("Vẫn tải lên"){_,_->uploadSelected(true)}
                .show()
        }
        private fun clearSelected(){
            preview.setImageDrawable(null);preview.visibility=View.GONE;previewMeta.text="Chưa chọn ảnh."
            uploadButton.isEnabled=false;uploadButton.alpha=.4f
        }

        private fun refreshDocuments(){
            executor.execute{
                val result=client.get("/v1/documents?limit=60")
                postUi{
                    recordsHost.removeAllViews()
                    if(!result.ok){emptyText.visibility=View.VISIBLE;emptyText.text="Không tải được danh sách: ${messageFor(result.error)}";return@postUi}
                    val arr=result.json?.optJSONArray("items")?:JSONArray()
                    if(arr.length()==0){emptyText.visibility=View.VISIBLE;emptyText.text="Chưa có biên bản nào.";return@postUi}
                    emptyText.visibility=View.GONE
                    for(i in 0 until arr.length())recordsHost.addView(recordCard(arr.optJSONObject(i)?:continue),LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(7)})
                }
            }
        }
        private fun recordCard(o:JSONObject):View{
            val card=column().apply{background=bg();setPadding(dp(10),dp(8),dp(10),dp(8))}
            val top=row()
            top.addView(text(o.optString("category_name","Biên bản"),10.8f,navy,true),LinearLayout.LayoutParams(0,-2,1f))
            val view=button("Xem ảnh",teal)
            top.addView(view,LinearLayout.LayoutParams(dp(84),dp(36)))
            card.addView(top)
            card.addView(gap(3))
            val who=o.optString("uploader_name").ifBlank{o.optString("uploader_id")}
            card.addView(text("$who • ${formatTime(o.optString("completed_at").ifBlank{o.optString("created_at")})}",9.3f,ink))
            card.addView(text("${o.optInt("width")}×${o.optInt("height")} • ${formatBytes(o.optLong("byte_size"))}",8.8f,muted))
            view.setOnClickListener{viewDocument(o.optString("document_id"))}
            return card
        }
        private fun viewDocument(documentId:String){
            if(busy)return
            busy=true
            executor.execute{
                val result=client.getMedia(documentId)
                busy=false
                postUi{
                    if(!result.ok||result.bytes==null){error(messageFor(result.error));return@postUi}
                    val bmp=BitmapFactory.decodeByteArray(result.bytes,0,result.bytes.size)
                    if(bmp==null){error("Không hiển thị được ảnh.");return@postUi}
                    val image=ImageView(activity).apply{setImageBitmap(bmp);adjustViewBounds=true;scaleType=ImageView.ScaleType.FIT_CENTER;setPadding(dp(4),dp(4),dp(4),dp(4))}
                    val scroll=ScrollView(activity).apply{addView(image,ViewGroup.LayoutParams(-1,-2))}
                    AlertDialog.Builder(activity).setTitle("Ảnh biên bản").setView(scroll).setPositiveButton("Đóng",null).show()
                }
            }
        }
        private fun formatTime(value:String):String=runCatching{
            Instant.parse(value).atZone(ZoneId.of("Asia/Ho_Chi_Minh")).format(DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm"))
        }.getOrDefault(value.ifBlank{"-"})
        private fun formatBytes(bytes:Long):String=when{
            bytes>=1024*1024->String.format("%.1f MB",bytes/1024.0/1024.0)
            bytes>=1024->String.format("%.0f KB",bytes/1024.0)
            else->"$bytes B"
        }
        private fun messageFor(code:String?):String=when(code){
            "DOCUMENT_DRIVE_OAUTH_REQUIRED"->"Tài khoản Google của Service chưa được cấp quyền Drive. Cần OWNER cấp quyền một lần rồi tiếp tục."
            "DOCUMENT_DRIVE_UNAVAILABLE","DOCUMENT_DRIVE_VERIFY_UNAVAILABLE"->"Google Drive đang không sẵn sàng. Ảnh vẫn còn trên máy, có thể thử tải lại."
            "DOCUMENT_CATEGORY_EXISTS"->"Loại biên bản này đã tồn tại."
            "DOCUMENT_CATEGORY_NOT_FOUND"->"Loại biên bản không còn khả dụng. Hãy làm mới danh mục."
            "SERVICE_DISCOVERY_UNAVAILABLE","SERVICE_SESSION_UNAVAILABLE"->"Chưa kết nối được Service."
            "DRIVE_UPLOAD_NETWORK"->"Mạng bị gián đoạn khi tải ảnh lên Google Drive. Có thể thử lại."
            null,""->"Có lỗi chưa xác định."
            else->code.replace('_',' ')
        }
    }
}
