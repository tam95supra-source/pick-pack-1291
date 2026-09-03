package vn.pickpack1291.app.beta

import android.app.Activity
import android.app.AlertDialog
import android.content.res.ColorStateList
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.content.Context
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
    private class ZoomSwipeImageView(context:Context,private val onPrev:()->Unit,private val onNext:()->Unit):ImageView(context){
        private var zoom=1f
        private val scale=android.view.ScaleGestureDetector(context,object:android.view.ScaleGestureDetector.SimpleOnScaleGestureListener(){
            override fun onScale(d:android.view.ScaleGestureDetector):Boolean{
                zoom=(zoom*d.scaleFactor).coerceIn(1f,5f);scaleX=zoom;scaleY=zoom;pivotX=d.focusX;pivotY=d.focusY;return true
            }
        })
        private val gesture=android.view.GestureDetector(context,object:android.view.GestureDetector.SimpleOnGestureListener(){
            override fun onDown(e:android.view.MotionEvent)=true
            override fun onFling(e1:android.view.MotionEvent?,e2:android.view.MotionEvent,velocityX:Float,velocityY:Float):Boolean{
                if(zoom>1.05f||e1==null||kotlin.math.abs(e2.x-e1.x)<90f)return false
                if(e2.x<e1.x)onNext() else onPrev();return true
            }
        })
        init{scaleType=ScaleType.FIT_CENTER;isClickable=true}
        override fun onTouchEvent(e:android.view.MotionEvent):Boolean{scale.onTouchEvent(e);gesture.onTouchEvent(e);return true}
        fun resetZoom(){zoom=1f;scaleX=1f;scaleY=1f;translationX=0f;translationY=0f}
    }

    // Category mutation semantics and batch grouping remain owner-locked.
    private data class Selected(
        val image:DocumentImageProcessor.ProcessedImage,
        val sourceKind:String,
        val capturedAt:String,
        val idempotencyKey:String,
        var note:String=""
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
        private val selectedDraftKeys=linkedSetOf<String>()
        private var categoryIds=listOf<String>()
        private var categoryNames=listOf<String>()
        private lateinit var categorySpinner:Spinner
        private lateinit var multiPageCheck:CheckBox
        private lateinit var multiDocumentCheck:CheckBox
        private lateinit var filterSpinner:Spinner
        private lateinit var deleteSelectedButton:Button
        private lateinit var selectedDeleteText:TextView
        private var filterCategoryIds=listOf<String>("")
        private var suppressFilter=false
        private lateinit var selectedHost:LinearLayout
        private lateinit var selectAllDraftButton:Button
        private lateinit var deleteDraftButton:Button
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
        private fun iconButton(res:Int,color:Int,desc:String)=ImageButton(activity).apply{
            setImageResource(res);imageTintList=ColorStateList.valueOf(Color.WHITE);contentDescription=desc
            setPadding(dp(10),dp(10),dp(10),dp(10));background=GradientDrawable().apply{setColor(color);cornerRadius=dp(10).toFloat()}
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


            val categoryBox=column().apply{background=bg();setPadding(dp(10),dp(9),dp(10),dp(10))}
            categoryBox.addView(text("Loại biên bản",10f,muted,true));categoryBox.addView(gap(4))
            categorySpinner=Spinner(activity).apply{minimumHeight=dp(46);setPadding(dp(8),dp(3),dp(8),dp(3));background=bg()}
            val categoryActions=row()
            val add=iconButton(R.drawable.ic_pp_add,teal,"Thêm loại biên bản")
            val edit=iconButton(R.drawable.ic_pp_edit,navy,"Sửa loại biên bản")
            val remove=iconButton(R.drawable.ic_pp_delete,red,"Xóa loại biên bản")
            categoryActions.addView(categorySpinner,LinearLayout.LayoutParams(0,dp(46),1f).apply{marginEnd=dp(4)})
            categoryActions.addView(add,LinearLayout.LayoutParams(dp(44),dp(44)).apply{marginStart=dp(2);marginEnd=dp(2)})
            categoryActions.addView(edit,LinearLayout.LayoutParams(dp(44),dp(44)).apply{marginStart=dp(2);marginEnd=dp(2)})
            categoryActions.addView(remove,LinearLayout.LayoutParams(dp(44),dp(44)).apply{marginStart=dp(2)})
            categoryBox.addView(categoryActions,LinearLayout.LayoutParams(-1,-2))
            body.addView(categoryBox,LinearLayout.LayoutParams(-1,-2))
            body.addView(gap(10))

            val imageBox=column().apply{background=bg();setPadding(dp(10),dp(9),dp(10),dp(10))}
            imageBox.addView(text("Ảnh biên bản",10f,muted,true))
            imageBox.addView(gap(5))
            val modeRow=row()
            var modeSync=false
            multiPageCheck=CheckBox(activity).apply{
                text="Một biên bản nhiều trang";textSize=10.2f;setTextColor(ink);isChecked=true;isEnabled=false
            }
            multiDocumentCheck=CheckBox(activity).apply{
                text="Nhiều biên bản";textSize=10.2f;setTextColor(ink);isEnabled=false
            }
            multiPageCheck.setOnCheckedChangeListener{_,checked->
                if(modeSync)return@setOnCheckedChangeListener
                modeSync=true
                if(checked)multiDocumentCheck.isChecked=false else if(!multiDocumentCheck.isChecked)multiPageCheck.isChecked=true
                modeSync=false
            }
            multiDocumentCheck.setOnCheckedChangeListener{_,checked->
                if(modeSync)return@setOnCheckedChangeListener
                modeSync=true
                if(checked)multiPageCheck.isChecked=false else if(!multiPageCheck.isChecked)multiDocumentCheck.isChecked=true
                modeSync=false
            }
            modeRow.addView(multiPageCheck,LinearLayout.LayoutParams(0,dp(42),1.15f))
            modeRow.addView(multiDocumentCheck,LinearLayout.LayoutParams(0,dp(42),.85f))
            imageBox.addView(modeRow,LinearLayout.LayoutParams(-1,dp(42)))
            imageBox.addView(gap(5))
            val sourceActions=row()
            val camera=button("Chụp ảnh",teal)
            val gallery=button("Chọn nhiều ảnh",navy)
            sourceActions.addView(camera,LinearLayout.LayoutParams(0,dp(44),1f).apply{marginEnd=dp(4)})
            sourceActions.addView(gallery,LinearLayout.LayoutParams(0,dp(44),1f).apply{marginStart=dp(4)})
            imageBox.addView(sourceActions,LinearLayout.LayoutParams(-1,-2))
            imageBox.addView(gap(8))
            val selectedScroll=HorizontalScrollView(activity).apply{isHorizontalScrollBarEnabled=false}
            selectedHost=row().apply{setPadding(dp(3),dp(3),dp(3),dp(3))}
            selectedScroll.addView(selectedHost,ViewGroup.LayoutParams(-2,dp(108)))
            imageBox.addView(selectedScroll,LinearLayout.LayoutParams(-1,dp(108)))
            previewMeta=text("0 ảnh",9.4f,muted);imageBox.addView(previewMeta);imageBox.addView(gap(5))
            val draftActions=row()
            selectAllDraftButton=button("Chọn tất cả",navy).apply{isEnabled=false;alpha=.4f}
            deleteDraftButton=button("Xóa ảnh chọn",red).apply{isEnabled=false;alpha=.4f}
            draftActions.addView(selectAllDraftButton,LinearLayout.LayoutParams(0,dp(38),1f).apply{marginEnd=dp(3)})
            draftActions.addView(deleteDraftButton,LinearLayout.LayoutParams(0,dp(38),1f).apply{marginStart=dp(3)})
            imageBox.addView(draftActions,LinearLayout.LayoutParams(-1,dp(38)))
            imageBox.addView(gap(8))
            uploadButton=button("Tải lên",green).apply{isEnabled=false;alpha=.4f}
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
            body.addView(pendingBox,LinearLayout.LayoutParams(-1,-2))
            body.addView(gap(12))

            val listHead=row()
            listHead.addView(text("Biên bản đã tải",11.5f,navy,true),LinearLayout.LayoutParams(0,-2,1f))
            val refresh=button("Làm mới",navy)
            listHead.addView(refresh,LinearLayout.LayoutParams(dp(90),dp(38)))
            body.addView(listHead,LinearLayout.LayoutParams(-1,-2));body.addView(gap(5))
            filterSpinner=Spinner(activity).apply{minimumHeight=dp(42);setPadding(dp(8),0,dp(8),0);background=bg()}
            filterCategoryIds=listOf("")+categoryIds
            filterSpinner.adapter=ArrayAdapter(activity,android.R.layout.simple_spinner_dropdown_item,listOf("Tất cả loại biên bản")+categoryNames)
            body.addView(filterSpinner,LinearLayout.LayoutParams(-1,dp(42)));body.addView(gap(5))
            val selectionRow=row()
            selectedDeleteText=text("Đã chọn 0 ảnh",9.3f,muted,true)
            val selectAllUploaded=button("Chọn tất cả",navy)
            deleteSelectedButton=button("Xóa đã chọn",red).apply{isEnabled=false;alpha=.4f}
            selectionRow.addView(selectedDeleteText,LinearLayout.LayoutParams(0,-2,1f))
            selectionRow.addView(selectAllUploaded,LinearLayout.LayoutParams(dp(94),dp(38)).apply{marginEnd=dp(3)})
            selectionRow.addView(deleteSelectedButton,LinearLayout.LayoutParams(dp(108),dp(38)))
            body.addView(selectionRow);body.addView(gap(5))
            emptyText=text("Đang tải...",9.5f,muted).apply{setPadding(dp(4),dp(8),dp(4),dp(8))}
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
            selectAllDraftButton.setOnClickListener{selectedDraftKeys.clear();selectedDraftKeys.addAll(selected.map{it.idempotencyKey});renderSelectedPreview()}
            deleteDraftButton.setOnClickListener{
                val keys=selectedDraftKeys.toSet();if(keys.isNotEmpty()){
                    draftStore.removeItems(login,keys);selected.removeAll{it.idempotencyKey in keys};selectedDraftKeys.clear();renderSelectedPreview()
                }
            }
            deleteSelectedButton.setOnClickListener{deleteSelectedRecords()}
            selectAllUploaded.setOnClickListener{
                selectedDocumentIds.clear()
                for(i in 0 until recordsHost.childCount){
                    val group=recordsHost.getChildAt(i)
                    group.findViewWithTag<View>("document_check_all_marker")
                }
                val category=selectedFilterId()
                val path=if(category.isBlank())"/v1/documents?limit=100" else "/v1/documents?limit=100&category_id="+java.net.URLEncoder.encode(category,"UTF-8")
                executor.execute{val result=client.get(path);postUi{if(result.ok){val a=result.json?.optJSONArray("items")?:JSONArray();for(i in 0 until a.length())a.optJSONObject(i)?.optString("document_id")?.takeIf{it.isNotBlank()}?.let(selectedDocumentIds::add);refreshDocumentsWithSelection()}}}
            }
            filterSpinner.onItemSelectedListener=object:AdapterView.OnItemSelectedListener{
                override fun onNothingSelected(parent:AdapterView<*>?)=Unit
                override fun onItemSelected(parent:AdapterView<*>?,view:View?,position:Int,id:Long){if(!suppressFilter)refreshDocuments()}
            }
            restoreCachedCategories()
            restoreDraft()
            refreshCategories()
            refreshPending()
            DocumentUploadWorker.schedule(activity)
            refreshDocuments()
            return root
        }

        fun dispose(){disposed=true;executor.shutdownNow()}
        fun onImageSelected(uri:Uri,sourceKind:String)=onImagesSelected(listOf(uri),sourceKind)

        fun onImagesSelected(uris:List<Uri>,sourceKind:String){
            if(disposed||busy)return
            val input=uris.distinctBy{it.toString()}.take((60-selected.size).coerceAtLeast(0))
            if(input.isEmpty()){warning("Đã đạt tối đa 60 ảnh đang chọn.");return}
            busy=true
            postUi{previewMeta.text="Đang xử lý ${input.size} ảnh...";uploadButton.isEnabled=false;uploadButton.alpha=.4f}
            executor.execute{
                var added=0;var firstError:String?=null
                for(uri in input){
                    try{
                        val image=DocumentImageProcessor.process(activity,uri)
                        val capturedAt=Instant.now().toString();val idempotencyKey=UUID.randomUUID().toString()
                        draftStore.append(login,sourceKind,capturedAt,idempotencyKey,image)
                        selected.add(Selected(image,sourceKind,capturedAt,idempotencyKey,""));added++
                    }catch(t:Throwable){if(firstError==null)firstError=t.message?:"IMAGE_READ_FAILED"}
                    finally{if(sourceKind=="CAMERA")runCatching{activity.contentResolver.delete(uri,null,null)}}
                }
                busy=false
                postUi{
                    renderSelectedPreview()
                    if(firstError!=null)warning("Có ảnh không đọc được: $firstError")
                    if(added==0&&firstError!=null)error("Không thêm được ảnh.")
                }
            }
        }

        private fun renderSelectedPreview(){
            selectedHost.removeAllViews()
            selected.forEachIndexed{index,item->
                val box=column().apply{setPadding(dp(2),dp(2),dp(2),dp(2));background=bg(Color.rgb(248,250,252),8)}
                val opts=BitmapFactory.Options().apply{inSampleSize=8;inPreferredConfig=android.graphics.Bitmap.Config.RGB_565}
                val bmp=BitmapFactory.decodeByteArray(item.image.bytes,0,item.image.bytes.size,opts)
                val thumb=ImageView(activity).apply{setImageBitmap(bmp);scaleType=ImageView.ScaleType.CENTER_CROP;contentDescription="Xem ảnh ${index+1}";setOnClickListener{showSelectedViewer(index)}}
                box.addView(thumb,LinearLayout.LayoutParams(dp(70),dp(62)))
                val foot=row()
                val check=CheckBox(activity).apply{isChecked=item.idempotencyKey in selectedDraftKeys;setOnCheckedChangeListener{_,on->if(on)selectedDraftKeys.add(item.idempotencyKey)else selectedDraftKeys.remove(item.idempotencyKey);updateDraftSelection()}}
                foot.addView(check,LinearLayout.LayoutParams(dp(34),dp(34)))
                foot.addView(text(if(item.note.isBlank())"${index+1}" else "${index+1} • note",8.2f,navy,true).apply{gravity=Gravity.CENTER},LinearLayout.LayoutParams(dp(54),dp(34)))
                box.addView(foot,LinearLayout.LayoutParams(dp(88),dp(34)))
                selectedHost.addView(box,LinearLayout.LayoutParams(dp(92),dp(102)).apply{marginEnd=dp(3)})
            }
            val total=selected.sumOf{it.image.bytes.size.toLong()}
            previewMeta.text=if(selected.isEmpty())"0 ảnh" else "${selected.size} ảnh • ${formatBytes(total)}"
            if(::multiPageCheck.isInitialized){
                val enabled=selected.size>1;multiPageCheck.isEnabled=enabled;multiDocumentCheck.isEnabled=enabled
                if(!enabled){multiPageCheck.isChecked=true;multiDocumentCheck.isChecked=false}
            }
            uploadButton.isEnabled=selected.isNotEmpty()&&categoryIds.isNotEmpty()&&!busy;uploadButton.alpha=if(uploadButton.isEnabled)1f else .4f
            updateDraftSelection()
        }
        private fun updateDraftSelection(){
            if(!::deleteDraftButton.isInitialized)return
            selectAllDraftButton.isEnabled=selected.isNotEmpty();selectAllDraftButton.alpha=if(selected.isNotEmpty())1f else .4f
            deleteDraftButton.isEnabled=selectedDraftKeys.isNotEmpty();deleteDraftButton.alpha=if(selectedDraftKeys.isNotEmpty())1f else .4f
            deleteDraftButton.text=if(selectedDraftKeys.isEmpty())"Xóa ảnh chọn" else "Xóa ${selectedDraftKeys.size} ảnh"
        }
        private fun showSelectedViewer(start:Int){
            if(start !in selected.indices)return
            var index=start
            val host=column().apply{setPadding(dp(8),dp(6),dp(8),dp(4))}
            lateinit var image:ZoomSwipeImageView
            val page=text("",9.5f,navy,true).apply{gravity=Gravity.CENTER}
            val note=EditText(activity).apply{hint="Chú thích ngắn";setSingleLine(false);maxLines=3;background=bg();setPadding(dp(9),dp(7),dp(9),dp(7))}
            fun render(){
                val item=selected[index];val bmp=BitmapFactory.decodeByteArray(item.image.bytes,0,item.image.bytes.size)
                image.resetZoom();image.setImageBitmap(bmp);page.text="Ảnh ${index+1}/${selected.size}";note.setText(item.note)
            }
            image=ZoomSwipeImageView(activity,{if(index>0){index--;render()}},{if(index<selected.lastIndex){index++;render()}})
            host.addView(image,LinearLayout.LayoutParams(-1,dp(360)));host.addView(page);host.addView(gap(5));host.addView(note,LinearLayout.LayoutParams(-1,-2))
            val dialog=AlertDialog.Builder(activity).setTitle("Xem ảnh đã chọn • vuốt / pinch zoom").setView(host).setNegativeButton("Đóng",null).setPositiveButton("LƯU CHÚ THÍCH",null).create()
            dialog.setOnShowListener{dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener{val v=note.text.toString().trim().take(240);selected[index].note=v;draftStore.updateNote(login,selected[index].idempotencyKey,v);renderSelectedPreview();page.text="Đã lưu • Ảnh ${index+1}/${selected.size}"}}
            dialog.show();render()
        }

        private fun applyCategoryEntries(entries:List<DocumentCategoryCache.Entry>){
            val previousCategory=selectedCategory()?.first
            val previousFilter=if(::filterSpinner.isInitialized)filterCategoryIds.getOrNull(filterSpinner.selectedItemPosition).orEmpty() else ""
            categoryIds=entries.map{it.id};categoryNames=entries.map{it.name}
            categorySpinner.adapter=ArrayAdapter(activity,android.R.layout.simple_spinner_dropdown_item,if(categoryNames.isEmpty())listOf("Chưa có loại biên bản") else categoryNames)
            val categoryIndex=previousCategory?.let{categoryIds.indexOf(it)}?.takeIf{it>=0}?:0
            if(categoryIds.isNotEmpty())categorySpinner.setSelection(categoryIndex)
            if(::filterSpinner.isInitialized){
                filterCategoryIds=listOf("")+categoryIds
                suppressFilter=true
                filterSpinner.adapter=ArrayAdapter(activity,android.R.layout.simple_spinner_dropdown_item,listOf("Tất cả loại biên bản")+categoryNames)
                filterSpinner.setSelection(filterCategoryIds.indexOf(previousFilter).takeIf{it>=0}?:0)
                suppressFilter=false
            }
            renderSelectedPreview()
        }
        private fun restoreCachedCategories(){
            val cached=categoryCache.load(login)
            if(cached.isNotEmpty())applyCategoryEntries(cached)
            else categorySpinner.adapter=ArrayAdapter(activity,android.R.layout.simple_spinner_dropdown_item,listOf("Đang tải loại biên bản..."))
        }
        private fun restoreDraft(){
            executor.execute{
                val drafts=draftStore.loadAll(login)
                if(drafts.isEmpty())return@execute
                selected.clear();selected.addAll(drafts.map{Selected(it.image,it.sourceKind,it.capturedAt,it.idempotencyKey,it.note)})
                postUi{renderSelectedPreview()}
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
            val batch=selected.toList();if(batch.isEmpty())return
            val categoryId=categoryIds.getOrNull(categorySpinner.selectedItemPosition)?:run{warning("Chọn loại biên bản.");return}
            if(busy)return
            busy=true;postUi{uploadButton.isEnabled=false;uploadButton.text="Đang lưu..."}
            executor.execute{
                val mode=when{batch.size<=1->"SINGLE";multiDocumentCheck.isChecked->"MULTI_DOCUMENT";else->"MULTI_PAGE"}
                val sharedGroup="batch-"+batch.first().idempotencyKey
                val queued=mutableListOf<DocumentPendingStore.Item>();var enqueueError:String?=null
                batch.forEachIndexed{index,item->
                    if(enqueueError==null){
                        val groupId=if(mode=="MULTI_PAGE")sharedGroup else "doc-"+item.idempotencyKey
                        try{
                            val pageIndex=if(mode=="MULTI_PAGE")index+1 else 1
                            val pageCount=if(mode=="MULTI_PAGE")batch.size else 1
                            queued+=pendingStore.enqueue(login,categoryId,item.sourceKind,item.capturedAt,item.idempotencyKey,item.image,groupId,mode,pageIndex,pageCount,item.note)
                        }catch(t:Throwable){enqueueError=t.message?:"DOCUMENT_PENDING_SAVE_FAILED"}
                    }
                }
                if(enqueueError!=null){
                    busy=false;postUi{uploadButton.text="Tải lên";error(messageFor(enqueueError));refreshPending();renderSelectedPreview()};return@execute
                }
                draftStore.remove(login);selected.clear()
                var completed=0;var exact=0;var retry=false;var blocked=0;var reviewId:String?=null
                for(item in queued){
                    val outcome=uploadEngine.runOne(item)
                    when(outcome.status){
                        DocumentUploadEngine.Status.SUCCESS->completed++
                        DocumentUploadEngine.Status.EXACT_DUPLICATE_RESOLVED->exact++
                        DocumentUploadEngine.Status.SIMILAR_REVIEW_REQUIRED->if(reviewId==null)reviewId=item.pendingId
                        DocumentUploadEngine.Status.RETRY->{retry=true;DocumentUploadWorker.schedule(activity,true)}
                        else->blocked++
                    }
                }
                busy=false
                postUi{
                    uploadButton.text="Tải lên";clearSelected();refreshPending();refreshDocuments()
                    when{
                        reviewId!=null->showSimilarConfirm(reviewId!!)
                        completed>0&&retry->warning("Đã tải $completed ảnh; còn ảnh chờ tải.")
                        completed>0->success("Đã tải $completed ảnh.")
                        exact>0&&blocked==0&&!retry->warning("Ảnh trùng đã được chặn.")
                        retry->warning("Ảnh đang chờ tải.")
                        blocked>0->error("Có ảnh chưa thể xử lý.")
                    }
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
            selectedHost.removeAllViews();previewMeta.text="0 ảnh"
            if(::multiPageCheck.isInitialized){
                multiPageCheck.isEnabled=false;multiDocumentCheck.isEnabled=false
                multiPageCheck.isChecked=true;multiDocumentCheck.isChecked=false
            }
            uploadButton.isEnabled=false;uploadButton.alpha=.4f
        }
        private fun selectedFilterId():String=if(::filterSpinner.isInitialized)filterCategoryIds.getOrNull(filterSpinner.selectedItemPosition).orEmpty() else ""
        private fun refreshDocumentsWithSelection(){refreshDocuments(clearSelection=false)}
        private fun refreshDocuments(clearSelection:Boolean=true){
            val category=selectedFilterId()
            val path=if(category.isBlank())"/v1/documents?limit=100" else "/v1/documents?limit=100&category_id="+java.net.URLEncoder.encode(category,"UTF-8")
            executor.execute{
                val result=client.get(path)
                postUi{
                    recordsHost.removeAllViews();if(clearSelection)selectedDocumentIds.clear();updateDeleteSelection()
                    if(!result.ok){emptyText.visibility=View.VISIBLE;emptyText.text=messageFor(result.error);return@postUi}
                    val arr=result.json?.optJSONArray("items")?:JSONArray()
                    if(arr.length()==0){emptyText.visibility=View.VISIBLE;emptyText.text="Chưa có biên bản.";return@postUi}
                    emptyText.visibility=View.GONE
                    val groups=linkedMapOf<String,MutableList<JSONObject>>()
                    for(i in 0 until arr.length()){
                        val item=arr.optJSONObject(i)?:continue
                        val key=item.optString("group_id").takeIf{it.isNotBlank()}?:item.optString("document_id")
                        groups.getOrPut(key){mutableListOf()}.add(item)
                    }
                    groups.values.forEach{items->
                        recordsHost.addView(recordGroupCard(items.sortedBy{it.optInt("page_index",1)}),LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(5)})
                    }
                }
            }
        }
        private fun recordGroupCard(items:List<JSONObject>):View{
            val first=items.firstOrNull()?:return Space(activity)
            val card=column().apply{background=bg();setPadding(dp(8),dp(7),dp(8),dp(7))}
            val category=first.optString("category_name").takeUnless{it.isBlank()||it.equals("null",true)}?:"-"
            val who=first.optString("uploader_name").ifBlank{first.optString("uploader_id")}.takeUnless{it.equals("null",true)}?:"-"
            val head=row()
            head.addView(text(category,10.5f,navy,true),LinearLayout.LayoutParams(0,-2,1f))
            head.addView(text(if(items.size>1)"${items.size} trang" else "1 ảnh",8.8f,muted,true))
            card.addView(head)
            card.addView(text("$who • ${formatTime(first.optString("completed_at").ifBlank{first.optString("created_at")})}",8.8f,muted))
            card.addView(gap(4))
            items.forEach{item->
                val id=item.optString("document_id")
                val pages=item.optInt("page_count",1).coerceAtLeast(1)
                val page=item.optInt("page_index",1).coerceAtLeast(1)
                val line=row().apply{setBackgroundColor(Color.rgb(248,250,252));setPadding(dp(2),dp(2),dp(2),dp(2))}
                val check=CheckBox(activity).apply{
                    isChecked=id in selectedDocumentIds
                    setOnCheckedChangeListener{_,on->if(on)selectedDocumentIds.add(id)else selectedDocumentIds.remove(id);updateDeleteSelection()}
                }
                line.addView(check,LinearLayout.LayoutParams(dp(38),dp(38)))
                val label=if(pages>1)"Trang $page/$pages" else "Ảnh"
                val note=item.optString("note").trim()
                line.addView(text("$label • ${item.optInt("width")}×${item.optInt("height")} • ${formatBytes(item.optLong("byte_size"))}${if(note.isBlank())"" else "\n"+note}",8.9f,ink,true).apply{maxLines=3},LinearLayout.LayoutParams(0,-2,1f))
                val view=button("Xem",teal)
                line.addView(view,LinearLayout.LayoutParams(dp(60),dp(34)))
                val idx=items.indexOf(item);view.setOnClickListener{viewDocumentGroup(items,idx)}
                card.addView(line);card.addView(gap(3))
            }
            return card
        }
        private fun updateDeleteSelection(){
            if(!::selectedDeleteText.isInitialized)return
            selectedDeleteText.text="Đã chọn ${selectedDocumentIds.size} ảnh"
            deleteSelectedButton.isEnabled=selectedDocumentIds.isNotEmpty()&&!busy
            deleteSelectedButton.alpha=if(deleteSelectedButton.isEnabled)1f else .4f
        }
        private fun deleteSelectedRecords(){
            val ids=selectedDocumentIds.toList();if(ids.isEmpty()||busy)return
            confirmAction("xóa ${ids.size} ảnh biên bản"){startDeleteRecords(ids)}
        }
        private fun startDeleteRecords(ids:List<String>){
            if(busy)return;busy=true;postUi{deleteSelectedButton.isEnabled=false}
            executor.execute{
                var result=client.post("/v1/documents/delete",JSONObject().put("operation","START").put("document_ids",JSONArray(ids)).put("idempotency_key",UUID.randomUUID().toString()))
                var mutation=result.json?.optJSONObject("mutation");var loops=0
                while(result.ok&&mutation?.optString("state")=="RUNNING"&&loops<100&&!disposed){
                    Thread.sleep(300L);val mutationId=mutation.optString("mutation_id");if(mutationId.isBlank())break
                    result=client.post("/v1/documents/delete",JSONObject().put("operation","PROCESS").put("mutation_id",mutationId));mutation=result.json?.optJSONObject("mutation");loops++
                }
                busy=false
                postUi{
                    when{
                        result.ok&&mutation?.optString("state")=="DONE"->{ids.forEach{mediaCache.clear(it)};success("Đã xóa ${mutation.optInt("processed_items",ids.size)} ảnh.")}
                        result.ok&&mutation?.optString("state")=="RUNNING"->warning("Đang tiếp tục xóa.")
                        else->error(messageFor(result.error?:mutation?.optString("last_error")))
                    }
                    selectedDocumentIds.clear();updateDeleteSelection();refreshDocuments()
                }
            }
        }
        private fun viewDocumentGroup(items:List<JSONObject>,start:Int){
            if(busy||items.isEmpty())return;busy=true
            executor.execute{
                val bytes=mutableListOf<ByteArray>();var errorCode:String?=null
                for(item in items){
                    val id=item.optString("document_id")
                    val cached=mediaCache.get(id)
                    val data=cached?:client.getMedia(id).let{r->if(!r.ok||r.bytes==null){errorCode=r.error;null}else{mediaCache.put(id,r.bytes);r.bytes}}
                    if(data==null)break else bytes.add(data)
                }
                busy=false
                postUi{
                    if(errorCode!=null||bytes.size!=items.size){error(messageFor(errorCode));return@postUi}
                    var index=start.coerceIn(0,bytes.lastIndex)
                    val host=column().apply{setPadding(dp(8),dp(6),dp(8),dp(4))}
                    lateinit var image:ZoomSwipeImageView
                    val page=text("",9.5f,navy,true).apply{gravity=Gravity.CENTER}
                    val note=text("",9.4f,ink,false).apply{setPadding(dp(8),dp(5),dp(8),dp(5));background=bg(Color.rgb(248,250,252),8)}
                    fun render(){
                        val bmp=BitmapFactory.decodeByteArray(bytes[index],0,bytes[index].size)
                        image.resetZoom();image.setImageBitmap(bmp);page.text="Trang ${index+1}/${bytes.size}";note.text=items[index].optString("note").ifBlank{"Không có chú thích"}
                    }
                    image=ZoomSwipeImageView(activity,{if(index>0){index--;render()}},{if(index<bytes.lastIndex){index++;render()}})
                    host.addView(image,LinearLayout.LayoutParams(-1,dp(390)));host.addView(page);host.addView(gap(4));host.addView(note,LinearLayout.LayoutParams(-1,-2))
                    AlertDialog.Builder(activity).setTitle("Biên bản • vuốt trang / pinch zoom").setView(host).setPositiveButton("Đóng",null).show();render()
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
            "DOCUMENT_DRIVE_OAUTH_REQUIRED"->"Drive chưa được cấp quyền."
            "DOCUMENT_DRIVE_UNAVAILABLE","DOCUMENT_DRIVE_VERIFY_UNAVAILABLE"->"Drive chưa sẵn sàng."
            "DOCUMENT_CATEGORY_EXISTS"->"Loại biên bản đã tồn tại."
            "DOCUMENT_CATEGORY_NOT_FOUND"->"Loại biên bản không tồn tại."
            "SERVICE_DISCOVERY_UNAVAILABLE","SERVICE_SESSION_UNAVAILABLE"->"Service ngoại tuyến."
            "DRIVE_UPLOAD_NETWORK"->"Mạng gián đoạn. Ảnh đã được giữ."
            "DOCUMENT_PENDING_ITEM_LIMIT","DOCUMENT_DRAFT_ITEM_LIMIT"->"Đã đạt giới hạn 60 ảnh."
            "DOCUMENT_PENDING_STORAGE_LIMIT","DOCUMENT_DRAFT_STORAGE_LIMIT"->"Đã đạt giới hạn 120 MB."
            "DOCUMENT_PENDING_ACCOUNT_MISMATCH"->"Ảnh thuộc tài khoản khác."
            "DOCUMENT_SIMILAR_IMAGE"->"Ảnh gần giống cần xác nhận."
            "DOCUMENT_CATEGORY_MUTATION_IN_PROGRESS"->"Loại biên bản đang được xử lý."
            "DOCUMENT_CATEGORY_PENDING_UPLOADS"->"Còn ảnh đang chờ tải."
            "DOCUMENT_CATEGORY_MUTATION_NOT_FOUND"->"Không tìm thấy tiến trình."
            "DOCUMENT_DELETE_MUTATION_NOT_FOUND"->"Không tìm thấy tiến trình xóa."
            null,""->"Không thực hiện được."
            else->code.replace('_',' ')
        }
    }
}
