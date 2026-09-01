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
    // Beta108 final owner rule: category UPDATE renames all; DELETE hard-purges; both reuse canonical action confirmation.
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
        private val onGallery:()->Unit,
        private val confirmAction:(String,()->Unit)->Unit
    ){
        private val client=DocumentServiceClient(activity){api.token}
        private val pendingStore=DocumentPendingStore(activity)
        private val draftStore=DocumentDraftStore(activity)
        private val categoryCache=DocumentCategoryCache(activity)
        private val uploadEngine=DocumentUploadEngine(activity,api)
        private val mediaCache=DocumentMediaCache(activity)
        private val executor=Executors.newSingleThreadExecutor()
        private val density=activity.resources.displayMetrics.density
        private val teal get()=ThemeManager.primary(activity)
        private val navy get()=ThemeManager.primaryDark(activity)
        private val ink=Color.rgb(24,44,42)
        private val muted=Color.rgb(100,116,139)
        private val red=Color.rgb(218,45,53)
        private val green=Color.rgb(36,153,85)
        private val selected=mutableListOf<Selected>()
        private val selectedDocumentIds=linkedSetOf<String>()
        private var categoryIds=listOf<String>()
        private var categoryNames=listOf<String>()
        private lateinit var categorySpinner:Spinner
        private lateinit var modeSpinner:Spinner
        private lateinit var filterSpinner:Spinner
        private lateinit var deleteSelectedButton:Button
        private lateinit var selectedDeleteText:TextView
        private var filterCategoryIds=listOf<String>("")
        private var suppressFilter=false
        private lateinit var preview:ImageView
        private lateinit var previewMeta:TextView
        private lateinit var uploadButton:Button
        private lateinit var pendingText:TextView
        private lateinit var retryPendingButton:Button
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
            categoryBox.addView(text("Sửa: đổi tên toàn bộ biên bản và file Drive thuộc loại. Xóa: xóa hẳn ảnh + dữ liệu. Cả hai đều yêu cầu mã xác nhận.",8.8f,muted))
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
            body.addView(gap(10))

            val pendingBox=column().apply{background=bg();setPadding(dp(10),dp(9),dp(10),dp(10))}
            val pendingHead=row()
            pendingHead.addView(text("Ảnh chờ tải",10.5f,navy,true),LinearLayout.LayoutParams(0,-2,1f))
            retryPendingButton=button("Tải lại",navy)
            pendingHead.addView(retryPendingButton,LinearLayout.LayoutParams(dp(86),dp(38)))
            pendingBox.addView(pendingHead)
            pendingBox.addView(gap(4))
            pendingText=text("Đang kiểm tra ảnh chờ...",9.1f,muted)
            pendingBox.addView(pendingText)
            pendingBox.addView(gap(3))
            pendingBox.addView(text("Ảnh chỉ giữ tạm trên máy khi chưa được Drive xác nhận; tải xong sẽ tự xóa. Tối đa 60 ảnh / 120 MB.",8.7f,muted))
            body.addView(pendingBox,LinearLayout.LayoutParams(-1,-2))
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
            edit.setOnClickListener{showRenameCategory()}
            remove.setOnClickListener{showDeleteCategory()}
            camera.setOnClickListener{if(!busy)onCamera()}
            gallery.setOnClickListener{if(!busy)onGallery()}
            uploadButton.setOnClickListener{uploadSelected()}
            retryPendingButton.setOnClickListener{retryPending()}
            refresh.setOnClickListener{refreshDocuments();refreshPending()}
            restoreCachedCategories()
            restoreDraft()
            refreshCategories()
            refreshPending()
            DocumentUploadWorker.schedule(activity)
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
                    val capturedAt=Instant.now().toString()
                    val idempotencyKey=UUID.randomUUID().toString()
                    draftStore.save(login,sourceKind,capturedAt,idempotencyKey,image)
                    selected=Selected(image,sourceKind,capturedAt,idempotencyKey)
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

        private fun applyCategoryEntries(entries:List<DocumentCategoryCache.Entry>){
            categoryIds=entries.map{it.id}
            categoryNames=entries.map{it.name}
            categorySpinner.adapter=ArrayAdapter(activity,android.R.layout.simple_spinner_dropdown_item,if(categoryNames.isEmpty())listOf("Chưa có loại biên bản") else categoryNames)
            uploadButton.isEnabled=selected!=null&&categoryIds.isNotEmpty()
            uploadButton.alpha=if(uploadButton.isEnabled)1f else .4f
        }
        private fun restoreCachedCategories(){
            val cached=categoryCache.load(login)
            if(cached.isNotEmpty())applyCategoryEntries(cached)
            else categorySpinner.adapter=ArrayAdapter(activity,android.R.layout.simple_spinner_dropdown_item,listOf("Đang tải loại biên bản..."))
        }
        private fun restoreDraft(){
            executor.execute{
                val draft=draftStore.load(login)?:return@execute
                selected=Selected(draft.image,draft.sourceKind,draft.capturedAt,draft.idempotencyKey)
                postUi{
                    val bmp=BitmapFactory.decodeByteArray(draft.image.bytes,0,draft.image.bytes.size)
                    if(bmp==null){draftStore.remove(login);selected=null;return@postUi}
                    preview.setImageBitmap(bmp);preview.visibility=View.VISIBLE
                    previewMeta.text="${draft.image.width} × ${draft.image.height} • ${formatBytes(draft.image.bytes.size.toLong())} • đã khôi phục ảnh đang chọn"
                    uploadButton.isEnabled=categoryIds.isNotEmpty();uploadButton.alpha=if(uploadButton.isEnabled)1f else .4f
                }
            }
        }
        private fun refreshCategories(){
            executor.execute{
                val result=client.get("/v1/documents/categories")
                postUi{
                    if(!result.ok){
                        if(categoryIds.isEmpty()){
                            val cached=categoryCache.load(login)
                            if(cached.isNotEmpty())applyCategoryEntries(cached)
                            else categorySpinner.adapter=ArrayAdapter(activity,android.R.layout.simple_spinner_dropdown_item,listOf("Chưa tải được loại biên bản"))
                        }
                        if(categoryIds.isNotEmpty())warning("Mất kết nối Service. Đang dùng danh mục đã lưu trên máy.")
                        else warning(messageFor(result.error))
                        return@postUi
                    }
                    val arr=result.json?.optJSONArray("items")?:JSONArray()
                    val entries=mutableListOf<DocumentCategoryCache.Entry>()
                    for(i in 0 until arr.length()){
                        val o=arr.optJSONObject(i)?:continue
                        val id=o.optString("category_id").trim();val name=o.optString("display_name").trim()
                        if(id.isNotBlank()&&name.isNotBlank())entries.add(DocumentCategoryCache.Entry(id,name))
                    }
                    categoryCache.save(login,entries)
                    applyCategoryEntries(entries)
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

        private fun selectedCategory():Pair<String,String>?{
            val index=categorySpinner.selectedItemPosition
            val id=categoryIds.getOrNull(index)?:return null
            val name=categoryNames.getOrNull(index)?:return null
            return id to name
        }

        private fun showRenameCategory(){
            if(busy)return
            val selectedCategory=selectedCategory()?:run{warning("Chưa có loại biên bản để sửa.");return}
            val input=EditText(activity).apply{
                setText(selectedCategory.second);selectAll();hint="Tên loại biên bản mới";setSingleLine(true)
                setPadding(dp(12),dp(8),dp(12),dp(8));background=bg()
            }
            val wrap=column().apply{setPadding(dp(16),dp(6),dp(16),0);addView(input,LinearLayout.LayoutParams(-1,dp(48)))}
            val dialog=AlertDialog.Builder(activity)
                .setTitle("Sửa loại biên bản")
                .setMessage("Toàn bộ biên bản cũ thuộc loại này sẽ đổi tên hiển thị và đổi tên file trên Google Drive.")
                .setView(wrap).setNegativeButton("Hủy",null).setPositiveButton("Tiếp tục",null).create()
            dialog.setOnShowListener{
                dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener{
                    val newName=input.text.toString().trim().replace(Regex("\\s+")," ")
                    if(newName.length !in 2..80){warning("Tên loại biên bản phải từ 2 đến 80 ký tự.");return@setOnClickListener}
                    if(newName==selectedCategory.second){warning("Tên mới không thay đổi.");return@setOnClickListener}
                    dialog.dismiss()
                    confirmAction("sửa loại biên bản"){
                        startCategoryMutation("UPDATE",selectedCategory.first,newName)
                    }
                }
            }
            dialog.show();input.requestFocus()
        }

        private fun showDeleteCategory(){
            if(busy)return
            val selectedCategory=selectedCategory()?:run{warning("Chưa có loại biên bản để xóa.");return}
            val localPending=pendingStore.list().count{it.ownerLogin==login&&it.categoryId==selectedCategory.first}
            if(localPending>0){
                warning("Loại này còn "+localPending+" ảnh đang chờ tải trên máy. Hãy xử lý ảnh chờ trước khi xóa.")
                return
            }
            AlertDialog.Builder(activity)
                .setTitle("Xóa hẳn loại biên bản?")
                .setMessage("Sẽ xóa vĩnh viễn loại “"+selectedCategory.second+"”, toàn bộ ảnh trên Google Drive và toàn bộ bản ghi biên bản thuộc loại này. Không thể khôi phục.")
                .setNegativeButton("Hủy",null)
                .setPositiveButton("Tiếp tục"){_,_->
                    confirmAction("xóa loại biên bản"){
                        startCategoryMutation("DELETE",selectedCategory.first,null)
                    }
                }.show()
        }

        private fun startCategoryMutation(operation:String,categoryId:String,newName:String?){
            if(busy)return
            busy=true
            postUi{
                categorySpinner.isEnabled=false
                retryPendingButton.isEnabled=false
                uploadButton.isEnabled=false
                success(if(operation=="UPDATE")"Đang đổi tên toàn bộ biên bản..." else "Đang xóa toàn bộ biên bản...")
            }
            executor.execute{
                val idem=UUID.randomUUID().toString()
                val body=JSONObject().put("operation",operation).put("category_id",categoryId).put("idempotency_key",idem)
                if(operation=="UPDATE")body.put("display_name",newName?:"")
                var result=client.post("/v1/documents/categories",body)
                var mutation=result.json?.optJSONObject("mutation")
                var loops=0
                while(result.ok&&mutation?.optString("state")=="RUNNING"&&loops<80&&!disposed){
                    Thread.sleep(350L)
                    val mutationId=mutation.optString("mutation_id")
                    if(mutationId.isBlank())break
                    result=client.post("/v1/documents/categories",JSONObject().put("operation","PROCESS").put("mutation_id",mutationId))
                    mutation=result.json?.optJSONObject("mutation")
                    loops++
                }
                busy=false
                postUi{
                    categorySpinner.isEnabled=true
                    refreshPending()
                    if(!result.ok){
                        error(messageFor(result.error))
                        refreshCategories();refreshDocuments()
                        return@postUi
                    }
                    val state=mutation?.optString("state").orEmpty()
                    when{
                        result.json?.optBoolean("no_change",false)==true->warning("Tên loại biên bản không thay đổi.")
                        state=="DONE"&&operation=="UPDATE"->success("Đã đổi tên toàn bộ biên bản và file trên Google Drive.")
                        state=="DONE"&&operation=="DELETE"->{mediaCache.clearAll();success("Đã xóa hẳn loại biên bản và toàn bộ ảnh liên quan.")}
                        state=="RUNNING"->warning("Hệ thống đang tiếp tục xử lý nền. Có thể rời màn hình; Service sẽ tự hoàn tất.")
                        else->error("Không hoàn tất được thao tác danh mục.")
                    }
                    refreshCategories();refreshDocuments()
                }
            }
        }
        private fun uploadSelected(){
            val selectedItem=selected?:return
            val index=categorySpinner.selectedItemPosition
            val categoryId=categoryIds.getOrNull(index)?:run{warning("Hãy thêm/chọn loại biên bản.");return}
            if(busy)return
            busy=true
            postUi{uploadButton.isEnabled=false;uploadButton.text="Đang lưu ảnh chờ..."}
            executor.execute{
                val pending=try{
                    pendingStore.enqueue(login,categoryId,selectedItem.sourceKind,selectedItem.capturedAt,selectedItem.idempotencyKey,selectedItem.image)
                }catch(t:Throwable){
                    busy=false
                    postUi{
                        uploadButton.isEnabled=true;uploadButton.text="Tải biên bản lên"
                        error(messageFor(t.message))
                        refreshPending()
                    }
                    return@execute
                }
                draftStore.remove(login)
                selected=null
                postUi{clearSelected();refreshPending();uploadButton.text="Đang tải thẳng lên Drive..."}
                val outcome=uploadEngine.runOne(pending)
                busy=false
                postUi{
                    uploadButton.text="Tải biên bản lên"
                    handleUploadOutcome(pending.pendingId,outcome)
                    refreshPending()
                    refreshDocuments()
                }
            }
        }

        private fun handleUploadOutcome(pendingId:String,outcome:DocumentUploadEngine.Outcome){
            when(outcome.status){
                DocumentUploadEngine.Status.SUCCESS->success("Đã tải biên bản lên Google Drive.")
                DocumentUploadEngine.Status.EXACT_DUPLICATE_RESOLVED->warning("Ảnh này đã tồn tại. Hệ thống đã chặn tải trùng và xóa bản chờ.")
                DocumentUploadEngine.Status.SIMILAR_REVIEW_REQUIRED->showSimilarConfirm(pendingId)
                DocumentUploadEngine.Status.RETRY->{
                    DocumentUploadWorker.schedule(activity,true)
                    warning("Đã lưu ảnh vào hàng chờ. Hệ thống sẽ tự tải lại khi mạng/Drive sẵn sàng.")
                }
                DocumentUploadEngine.Status.BLOCKED->error("Ảnh vẫn được giữ trong hàng chờ: "+messageFor(outcome.code))
                DocumentUploadEngine.Status.ACCOUNT_MISMATCH->error("Ảnh chờ thuộc tài khoản khác nên không tự tải.")
            }
        }

        private fun showSimilarConfirm(pendingId:String){
            AlertDialog.Builder(activity)
                .setTitle("Phát hiện ảnh có thể trùng")
                .setMessage("Ảnh gần giống một biên bản đã có. Vẫn tải ảnh này lên hay giữ lại để xem xét?")
                .setNegativeButton("Giữ lại",null)
                .setPositiveButton("Vẫn tải lên"){_,_->retrySimilar(pendingId)}
                .show()
        }

        private fun retrySimilar(pendingId:String){
            if(busy)return
            busy=true
            executor.execute{
                val outcome=uploadEngine.allowSimilarAndRetry(pendingId)
                busy=false
                postUi{
                    handleUploadOutcome(pendingId,outcome)
                    refreshPending();refreshDocuments()
                }
            }
        }

        private fun retryPending(){
            if(busy)return
            val items=pendingStore.list().filter{it.ownerLogin==login}
            if(items.isEmpty()){success("Không có ảnh chờ tải.");refreshPending();return}
            busy=true
            retryPendingButton.isEnabled=false
            executor.execute{
                var retryNeeded=false
                var reviewId:String?=null
                var completed=0
                for(item in items.take(10)){
                    val outcome=uploadEngine.runOne(item)
                    when(outcome.status){
                        DocumentUploadEngine.Status.SUCCESS,DocumentUploadEngine.Status.EXACT_DUPLICATE_RESOLVED->completed++
                        DocumentUploadEngine.Status.SIMILAR_REVIEW_REQUIRED->{reviewId=item.pendingId;break}
                        DocumentUploadEngine.Status.RETRY->retryNeeded=true
                        else->{}
                    }
                }
                if(retryNeeded)DocumentUploadWorker.schedule(activity,true)
                busy=false
                postUi{
                    retryPendingButton.isEnabled=true
                    refreshPending();refreshDocuments()
                    if(reviewId!=null)showSimilarConfirm(reviewId!!)
                    else if(completed>0)success("Đã xử lý "+completed+" ảnh chờ.")
                    else if(retryNeeded)warning("Một số ảnh vẫn đang chờ mạng/Drive.")
                }
            }
        }

        private fun refreshPending(){
            if(!::pendingText.isInitialized)return
            val items=pendingStore.list().filter{it.ownerLogin==login}
            val bytes=items.sumOf{it.byteSize.toLong()}
            val review=items.count{it.lastError=="DOCUMENT_SIMILAR_IMAGE"}
            pendingText.text=if(items.isEmpty())"Không có ảnh chờ tải." else "Đang chờ: "+items.size+" ảnh • "+formatBytes(bytes)+(if(review>0)" • "+review+" ảnh cần xác nhận trùng" else "")
            retryPendingButton.isEnabled=items.isNotEmpty()&&!busy
            retryPendingButton.alpha=if(retryPendingButton.isEnabled)1f else .45f
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
            val id=documentId.trim()
            if(id.isBlank())return
            busy=true
            executor.execute{
                val cached=mediaCache.get(id)
                val bytes=if(cached!=null)cached else{
                    val result=client.getMedia(id)
                    if(!result.ok||result.bytes==null){
                        busy=false
                        postUi{error(messageFor(result.error))}
                        return@execute
                    }
                    mediaCache.put(id,result.bytes)
                    result.bytes
                }
                busy=false
                postUi{
                    val bmp=BitmapFactory.decodeByteArray(bytes,0,bytes.size)
                    if(bmp==null){mediaCache.clear(id);error("Không hiển thị được ảnh.");return@postUi}
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
            "DRIVE_UPLOAD_NETWORK"->"Mạng bị gián đoạn khi tải ảnh lên Google Drive. Ảnh sẽ được giữ trong hàng chờ."
            "DOCUMENT_PENDING_ITEM_LIMIT"->"Hàng chờ đã đủ 60 ảnh. Hãy tải các ảnh đang chờ trước."
            "DOCUMENT_PENDING_STORAGE_LIMIT"->"Hàng chờ đã đạt 120 MB. Hãy tải các ảnh đang chờ trước."
            "DOCUMENT_PENDING_ACCOUNT_MISMATCH"->"Ảnh chờ thuộc tài khoản khác."
            "DOCUMENT_SIMILAR_IMAGE"->"Ảnh có thể trùng và cần xác nhận trước khi tải."
            "DOCUMENT_CATEGORY_MUTATION_IN_PROGRESS"->"Loại biên bản đang được sửa/xóa. Hãy chờ thao tác hiện tại hoàn tất."
            "DOCUMENT_CATEGORY_PENDING_UPLOADS"->"Loại biên bản còn ảnh chưa hoàn tất tải lên. Hãy xử lý ảnh chờ trước."
            "DOCUMENT_CATEGORY_MUTATION_NOT_FOUND"->"Không tìm thấy tiến trình sửa/xóa danh mục."
            null,""->"Có lỗi chưa xác định."
            else->code.replace('_',' ')
        }
    }
}
