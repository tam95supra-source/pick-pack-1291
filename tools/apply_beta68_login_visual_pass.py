#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / 'app/src/main/java/vn/pickpack1291/app/beta/FullBetaActivity.kt'

full = FULL.read_text()
start = full.find('    private fun login() {')
end = full.find('    private fun openMainShell()', start)
if start < 0 or end < 0:
    raise SystemExit('FullBetaActivity.login range missing')

login = r'''    private fun login() {
        foregroundSync.stop()
        liveEmployeeMnv = ""
        currentScreen = "LOGIN"
        accountLogin = ""; accountName = ""; accountRole = ""; accountPosition = ""; accountEmail = ""

        window.statusBarColor = Color.rgb(218, 29, 22)
        window.navigationBarColor = Color.rgb(5, 45, 91)
        @Suppress("DEPRECATION")
        window.decorView.systemUiVisibility = 0
        window.setSoftInputMode(android.view.WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN or android.view.WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE)

        val h = resources.configuration.screenHeightDp
        val w = resources.configuration.screenWidthDp
        val compact = h < 650 || w < 360
        val tiny = h < 590 || w < 330

        val user = EditText(this).apply {
            hint = "Tài khoản"; setSingleLine(true); textSize = if(tiny)13f else 14f
            setTextColor(Color.rgb(28,50,77)); setHintTextColor(Color.rgb(125,139,158)); imeOptions = EditorInfo.IME_ACTION_NEXT
            setPadding(dp(12),0,dp(8),0); background = null
            isFocusableInTouchMode = true
        }
        val saved = getPreferences(MODE_PRIVATE).getString("last_login", "").orEmpty()
        if (saved.isNotBlank()) user.setText(saved)

        val pass = EditText(this).apply {
            hint = "Mật khẩu"; setSingleLine(true); textSize = if(tiny)13f else 14f
            setTextColor(Color.rgb(28,50,77)); setHintTextColor(Color.rgb(125,139,158)); imeOptions = EditorInfo.IME_ACTION_DONE
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            setPadding(dp(12),0,dp(4),0); background = null
            isFocusableInTouchMode = true
        }
        var passwordVisible = false
        val eye = ImageButton(this).apply {
            setImageResource(R.drawable.ic_login_eye); setBackgroundColor(Color.TRANSPARENT); contentDescription = "Hiện mật khẩu"
            setPadding(dp(8),dp(8),dp(8),dp(8)); alpha = .82f
            setOnClickListener {
                passwordVisible = !passwordVisible
                val cursor = pass.selectionStart.coerceAtLeast(0)
                pass.inputType = InputType.TYPE_CLASS_TEXT or if(passwordVisible) InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD else InputType.TYPE_TEXT_VARIATION_PASSWORD
                pass.setSelection(cursor.coerceAtMost(pass.text.length)); alpha = if(passwordVisible)1f else .82f
                contentDescription = if(passwordVisible)"Ẩn mật khẩu" else "Hiện mật khẩu"
            }
        }

        fun loginField(iconRes:Int, field:EditText, trailing:View?=null):LinearLayout = row(Color.WHITE).apply {
            gravity = Gravity.CENTER_VERTICAL
            minimumHeight = dp(if(tiny)42 else 46)
            setPadding(dp(9),0,dp(5),0)
            background = GradientDrawable().apply {
                cornerRadius = dp(11).toFloat(); setColor(Color.argb(250,255,255,255)); setStroke(dp(1),Color.rgb(184,198,215))
            }
            addView(ImageView(this@FullBetaActivity).apply { setImageResource(iconRes); scaleType=ImageView.ScaleType.CENTER_INSIDE }, size(dp(24),dp(24)))
            addView(field, LinearLayout.LayoutParams(0,dp(if(tiny)40 else 44),1f))
            if(trailing!=null)addView(trailing,size(dp(40),dp(40)))
        }

        val card = column(Color.WHITE).apply {
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(dp(if(tiny)13 else 16),dp(if(tiny)11 else 14),dp(if(tiny)13 else 16),dp(if(tiny)12 else 15))
            background = GradientDrawable().apply {
                cornerRadius = dp(20).toFloat(); setColor(Color.argb(242,255,255,255)); setStroke(dp(1),Color.argb(105,105,125,150))
            }
            elevation = dp(7).toFloat()
        }
        card.addView(ImageView(this).apply {
            setImageResource(R.drawable.login_supra_logo); adjustViewBounds=true; scaleType=ImageView.ScaleType.FIT_CENTER
        }, size(dp(if(tiny)62 else if(compact)70 else 82),dp(if(tiny)62 else if(compact)70 else 82)))
        card.addView(txt("PICK PACK 1291",if(tiny)15.5f else 17f,Color.rgb(9,62,135),true).center())
        card.addView(txt("Supra DC Hưng Yên",if(tiny)10f else 11f,Color.rgb(74,91,112),true).center())
        card.addView(gap(if(tiny)7 else 10))
        card.addView(loginField(R.drawable.ic_login_user,user),matchWrap())
        card.addView(gap(if(tiny)6 else 8))
        card.addView(loginField(R.drawable.ic_login_lock,pass,eye),matchWrap())

        val forgot = TextView(this).apply {
            text="Quên mật khẩu?"; textSize=if(tiny)10.5f else 11.2f; setTextColor(Color.rgb(12,72,156)); typeface=Typeface.DEFAULT_BOLD
            gravity=Gravity.END; setPadding(dp(4),dp(5),0,dp(if(tiny)5 else 7))
            setOnClickListener {
                val loginId=user.text.toString().trim()
                if(loginId.isBlank()){toast("Nhập đúng tài khoản trước khi chọn Quên mật khẩu.");return@setOnClickListener}
                isEnabled=false;text="Đang gửi yêu cầu..."
                api.forgotPassword(loginId){r->runOnUiThread{
                    isEnabled=true;text="Quên mật khẩu?"
                    if(!r.ok){showError(r.error?:"Không gửi được yêu cầu đặt lại mật khẩu");return@runOnUiThread}
                    TopNotice.show(this@FullBetaActivity,"Nếu tài khoản hợp lệ, mật khẩu mới đã được gửi tới mail đã cấu hình.",TopNotice.Kind.SUCCESS)
                }}
            }
        }
        card.addView(forgot,matchWrap())

        val button = Button(this).apply {
            text="Đăng nhập"; textSize=if(tiny)13.5f else 14.5f; setTextColor(Color.WHITE); typeface=Typeface.DEFAULT_BOLD; isAllCaps=false
            minimumHeight=dp(if(tiny)43 else 47); background=gradient(Color.rgb(17,84,184),Color.rgb(6,57,137),12); elevation=0f
        }
        fun submit(){
            val loginId=user.text.toString().trim(); val password=pass.text.toString()
            if(loginId.isBlank()||password.isBlank()){toast("Nhập tài khoản và mật khẩu.");return}
            button.isEnabled=false;button.text="Đang xác thực..."
            api.login(loginId,password){result->runOnUiThread{
                button.isEnabled=true;button.text="Đăng nhập"
                if(!result.ok){showError(result.error?:"Đăng nhập thất bại");return@runOnUiThread}
                val a=result.json?.optJSONObject("account")?:JSONObject()
                accountLogin=a.optString("login_id",loginId);accountName=a.optString("display_name",accountLogin);accountRole=a.optString("role","USER")
                accountPosition=a.optString("position","");accountEmail=a.optString("email","")
                getPreferences(MODE_PRIVATE).edit().putString("last_login",accountLogin).apply();pass.setText("")
                openMainShell();if(MasterDataCache.revision(this@FullBetaActivity)==0L)refreshMasterCache();LocalLogManager.uploadAutomaticPending(this@FullBetaActivity,api)
            }}
        }
        button.setOnClickListener{submit()}
        user.setOnEditorActionListener{_,id,_->if(id==EditorInfo.IME_ACTION_NEXT){pass.requestFocus();true}else false}
        pass.setOnEditorActionListener{_,id,_->if(id==EditorInfo.IME_ACTION_DONE){submit();true}else false}
        card.addView(button,matchWrap())
        card.addView(gap(if(tiny)5 else 7))
        card.addView(Button(this).apply {
            text="Đăng ký"; textSize=if(tiny)11.5f else 12.5f; setTextColor(Color.rgb(13,73,155)); typeface=Typeface.DEFAULT_BOLD; isAllCaps=false
            minimumHeight=dp(if(tiny)38 else 42)
            background=GradientDrawable().apply{cornerRadius=dp(11).toFloat();setColor(Color.argb(245,255,255,255));setStroke(dp(1),Color.rgb(22,82,168))}
            setOnClickListener{TopNotice.show(this@FullBetaActivity,"Tính năng đăng ký đang được xây dựng.",TopNotice.Kind.INFO)}
        },matchWrap())

        val copyright=txt("Copyright 2026 Supra DC Hưng Yên - tamnv2 - Chuyên viên Pick Pack 1291",if(tiny)7.5f else 8.4f,Color.rgb(55,65,81),false).apply {
            gravity=Gravity.CENTER;maxLines=2;setPadding(dp(5),dp(5),dp(5),0)
        }

        val root=FrameLayout(this).apply {
            setBackgroundColor(Color.rgb(247,238,214))
            isFocusable=true;isFocusableInTouchMode=true
            addView(ImageView(this@FullBetaActivity).apply {
                setImageResource(R.drawable.login_vietnam_bg)
                scaleType=ImageView.ScaleType.FIT_CENTER
                adjustViewBounds=false
            },FrameLayout.LayoutParams(-1,-1))
        }
        val scroll=ScrollView(this).apply { isFillViewport=true;isVerticalScrollBarEnabled=false;isFocusable=false }
        val stage=LinearLayout(this).apply {
            orientation=LinearLayout.VERTICAL;gravity=Gravity.CENTER
            setPadding(dp(if(tiny)10 else 14),dp(if(tiny)8 else 12),dp(if(tiny)10 else 14),dp(if(tiny)8 else 12))
            val maxCard = if(tiny) dp(300) else if(compact) dp(330) else dp(380)
            val available=(resources.displayMetrics.widthPixels-dp(if(tiny)20 else 28)).coerceAtLeast(dp(260))
            addView(card,LinearLayout.LayoutParams(minOf(maxCard,available),-2))
            addView(copyright,LinearLayout.LayoutParams(minOf(maxCard,available),-2))
        }
        scroll.addView(stage,ViewGroup.LayoutParams(-1,-1));root.addView(scroll,FrameLayout.LayoutParams(-1,-1))
        root.setOnApplyWindowInsetsListener{v,i->
            val top:Int;val bottom:Int
            if(Build.VERSION.SDK_INT>=30){val bars=i.getInsets(WindowInsets.Type.systemBars());top=bars.top;bottom=bars.bottom}else{@Suppress("DEPRECATION")val t=i.systemWindowInsetTop;@Suppress("DEPRECATION")val b=i.systemWindowInsetBottom;top=t;bottom=b}
            v.setPadding(0,top,0,bottom);i
        }
        setScreen(root);root.requestApplyInsets();root.requestFocus()
    }

'''

full = full[:start] + login + full[end:]
FULL.write_text(full)
print('BETA68_LOGIN_VISUAL_PASS_PATCH_APPLIED')
