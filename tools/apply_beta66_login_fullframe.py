#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / 'app/src/main/java/vn/pickpack1291/app/beta/FullBetaActivity.kt'
GRADLE = ROOT / 'app/build.gradle.kts'
MANIFEST = ROOT / 'app/src/main/AndroidManifest.xml'

# Beta66 is a product-only login correction on top of the materialized Beta65 baseline.
g = GRADLE.read_text()
old = 'versionCode = 71\n            versionName = "0.4.2-beta.65"'
new = 'versionCode = 72\n            versionName = "0.4.2-beta.66"'
if old not in g:
    if 'versionCode = 72' not in g or 'versionName = "0.4.2-beta.66"' not in g:
        raise SystemExit('Beta66 version anchor missing; materialize Beta65 first')
else:
    g = g.replace(old, new, 1)
GRADLE.write_text(g)

text = FULL.read_text()
start = text.find('    private fun login() {')
end = text.find('    private fun openMainShell()', start)
if start < 0 or end < 0:
    raise SystemExit('login range missing')
seg = text[start:end]

anchor_start = seg.find('        // Reference-stage layout:')
anchor_end = seg.find('        setScreen(root);user.requestFocus()', anchor_start)
if anchor_start < 0 or anchor_end < 0:
    raise SystemExit('materialized Beta65 login layout anchor missing')
anchor_end += len('        setScreen(root);user.requestFocus()')

replacement = r'''        // Beta66 full-frame reference: one logical 2:3 design stage is uniformly scaled
        // against BOTH usable width and usable height. System-bar insets are applied first,
        // so approved artwork, form and footer stay visible without crop or non-uniform stretch.
        val root=FrameLayout(this).apply{
            setBackgroundColor(Color.rgb(5,45,91));clipChildren=true;clipToPadding=true
        }
        val designW=dp(360);val designH=dp(540)
        val stage=FrameLayout(this).apply{
            background=ColorDrawable(Color.rgb(247,238,214));clipChildren=true;clipToPadding=true
            pivotX=designW/2f;pivotY=designH/2f
        }
        root.addView(stage,FrameLayout.LayoutParams(designW,designH,Gravity.CENTER))
        stage.addView(ImageView(this).apply{
            setImageResource(R.drawable.login_vietnam_bg)
            scaleType=ImageView.ScaleType.FIT_CENTER
            adjustViewBounds=false
        },FrameLayout.LayoutParams(-1,-1))

        val cardW=(designW*.76f).toInt().coerceAtLeast(1)
        val top=(designH*.105f).toInt()
        stage.addView(card,FrameLayout.LayoutParams(cardW,-2,Gravity.TOP or Gravity.CENTER_HORIZONTAL).apply{topMargin=top})

        val footerAccent=View(this).apply{setBackgroundColor(Color.rgb(230,184,63))}
        stage.addView(footerAccent,FrameLayout.LayoutParams((designW*.91f).toInt(),dp(1),Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL).apply{bottomMargin=(designH*.066f).toInt()})
        val copy=TextView(this).apply{
            val raw="Copyright 2026 Supra DC Hưng Yên  -  tamnv2  -  Chuyên viên Pick Pack 1291"
            val sp=android.text.SpannableString(raw)
            val hi="Supra DC Hưng Yên";val p=raw.indexOf(hi)
            if(p>=0)sp.setSpan(android.text.style.ForegroundColorSpan(Color.rgb(245,198,70)),p,p+hi.length,android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            text=sp;textSize=9.2f;setTextColor(Color.WHITE);gravity=Gravity.CENTER;typeface=Typeface.DEFAULT_BOLD
            setShadowLayer(2f,0f,1f,Color.rgb(0,25,55));setPadding(dp(8),0,dp(8),0);maxLines=2
        }
        stage.addView(copy,FrameLayout.LayoutParams((designW*.94f).toInt(),dp(42),Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL).apply{bottomMargin=(designH*.014f).toInt()})

        var lastFit=-1f
        fun fitReferenceStage(){
            val availableW=(root.width-root.paddingLeft-root.paddingRight).coerceAtLeast(1)
            val availableH=(root.height-root.paddingTop-root.paddingBottom).coerceAtLeast(1)
            val scale=minOf(availableW/designW.toFloat(),availableH/designH.toFloat())
            if(scale>0f && kotlin.math.abs(scale-lastFit)>.001f){stage.scaleX=scale;stage.scaleY=scale;lastFit=scale}
        }
        root.setOnApplyWindowInsetsListener{_,wi->
            if(android.os.Build.VERSION.SDK_INT>=30){
                val ins=wi.getInsets(android.view.WindowInsets.Type.systemBars())
                root.setPadding(ins.left,ins.top,ins.right,ins.bottom)
            }else{
                @Suppress("DEPRECATION")
                root.setPadding(wi.systemWindowInsetLeft,wi.systemWindowInsetTop,wi.systemWindowInsetRight,wi.systemWindowInsetBottom)
            }
            root.post{fitReferenceStage()};wi
        }
        root.addOnLayoutChangeListener{_,_,_,_,_,_,_,_,_->fitReferenceStage()}
        setScreen(root);root.requestApplyInsets();root.post{fitReferenceStage();user.requestFocus()}
'''

seg = seg[:anchor_start] + replacement + seg[anchor_end:]
text = text[:start] + seg + text[end:]
FULL.write_text(text)

manifest = MANIFEST.read_text()
required_copy = 'Copyright 2026 Supra DC Hưng Yên  -  tamnv2  -  Chuyên viên Pick Pack 1291'
assert required_copy in seg
assert 'ImageView.ScaleType.FIT_CENTER' in seg
assert 'CENTER_CROP' not in seg
assert 'FIT_XY' not in seg
assert 'setOnApplyWindowInsetsListener' in seg
assert 'availableW/designW.toFloat()' in seg and 'availableH/designH.toFloat()' in seg
assert 'minOf(availableW/designW.toFloat(),availableH/designH.toFloat())' in seg
assert 'Ghi nhớ đăng nhập' not in seg
assert 'Đăng nhập bằng tài khoản khác' not in seg
for required in ('Đăng nhập','Quên mật khẩu','Hiện mật khẩu','Đăng ký'):
    assert required in seg, required
assert 'android:name=".FullBetaActivity"' in manifest
assert 'android.intent.action.MAIN' in manifest and 'android.intent.category.LAUNCHER' in manifest
assert 'versionCode = 72' in g and 'versionName = "0.4.2-beta.66"' in g
assert 'versionCode = 1' in g and 'versionName = "0.1.0-stable"' in g
print('BETA66_LOGIN_FULLFRAME_PASS')
