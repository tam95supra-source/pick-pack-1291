#!/usr/bin/env python3
from pathlib import Path

P=Path(__file__).resolve().parents[1]/'app/src/main/java/vn/pickpack1291/app/beta/FullBetaActivity.kt'
t=P.read_text()
start=t.find('    private fun login() {');end=t.find('    private fun openMainShell()',start)
if start<0 or end<0:raise SystemExit('login range missing')
seg=t[start:end]
seg=seg.replace('scaleType=ImageView.ScaleType.CENTER_INSIDE;adjustViewBounds=false','scaleType=ImageView.ScaleType.FIT_CENTER;adjustViewBounds=false',1)
old='''        val copy=TextView(this).apply{text="Copyright 2026 Supra DC Hưng Yên - tamnv2 - Chuyên viên Pick Pack 1291";textSize=9.2f;setTextColor(Color.WHITE);gravity=Gravity.CENTER;typeface=Typeface.DEFAULT_BOLD;setShadowLayer(2f,0f,1f,Color.rgb(0,25,55));setPadding(dp(8),0,dp(8),0)}\n        stage.addView(copy,FrameLayout.LayoutParams((designW*.94f).toInt(),dp(36),Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL).apply{bottomMargin=(designH*.018f).toInt()})\n'''
new='''        val footerAccent=View(this).apply{setBackgroundColor(Color.rgb(230,184,63))}\n        stage.addView(footerAccent,FrameLayout.LayoutParams((designW*.91f).toInt(),dp(1),Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL).apply{bottomMargin=(designH*.057f).toInt()})\n        val copy=TextView(this).apply{\n            val raw="Copyright 2026 Supra DC Hưng Yên - tamnv2 - Chuyên viên Pick Pack 1291";val sp=android.text.SpannableString(raw);val hi="Supra DC Hưng Yên";val p=raw.indexOf(hi);if(p>=0)sp.setSpan(android.text.style.ForegroundColorSpan(Color.rgb(245,198,70)),p,p+hi.length,android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);text=sp\n            textSize=9.2f;setTextColor(Color.WHITE);gravity=Gravity.CENTER;typeface=Typeface.DEFAULT_BOLD;setShadowLayer(2f,0f,1f,Color.rgb(0,25,55));setPadding(dp(8),0,dp(8),0)\n        }\n        stage.addView(copy,FrameLayout.LayoutParams((designW*.94f).toInt(),dp(36),Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL).apply{bottomMargin=(designH*.018f).toInt()})\n'''
if old not in seg:raise SystemExit('copyright anchor missing')
seg=seg.replace(old,new,1)
t=t[:start]+seg+t[end:]
P.write_text(t)
assert 'ImageView.ScaleType.FIT_CENTER' in seg
assert 'footerAccent' in seg and 'SpannableString' in seg
assert 'CENTER_CROP' not in seg and 'FIT_XY' not in seg
print('BETA65_LOGIN_REFERENCE_FINISH_PASS')
