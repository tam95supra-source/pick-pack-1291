package vn.pickpack1291.app.beta

import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout

object ReviewAlertUi {
    const val HEIGHT_DP=42
    const val RADIUS_DP=10
    const val STROKE_DP=2
    const val TEXT_SP=10.5f

    enum class Tone { OK, WARNING }

    private fun dp(activity:Activity,v:Int)=(v*activity.resources.displayMetrics.density).toInt()

    private fun fg(tone:Tone)=when(tone){
        Tone.OK->Color.rgb(16,112,66)
        Tone.WARNING->Color.rgb(176,0,32)
    }

    private fun fill(tone:Tone)=when(tone){
        Tone.OK->Color.rgb(226,248,235)
        Tone.WARNING->Color.rgb(255,226,232)
    }

    fun button(activity:Activity,text:String,tone:Tone):Button=Button(activity).apply{
        this.text=text
        textSize=TEXT_SP
        typeface=Typeface.DEFAULT_BOLD
        isAllCaps=false
        gravity=Gravity.CENTER
        setSingleLine(true)
        includeFontPadding=false
        minHeight=0
        minimumHeight=0
        minWidth=0
        minimumWidth=0
        setPadding(dp(activity,8),0,dp(activity,8),0)
        elevation=0f
        stateListAnimator=null
        val color=fg(tone)
        setTextColor(color)
        background=GradientDrawable().apply{
            setColor(fill(tone))
            cornerRadius=dp(activity,RADIUS_DP).toFloat()
            setStroke(dp(activity,STROKE_DP),color)
        }
    }

    fun warningContainer(activity:Activity)=LinearLayout(activity).apply{
        orientation=LinearLayout.VERTICAL
        visibility=android.view.View.GONE
        setPadding(0,0,0,dp(activity,4))
    }

    fun fixedHeightParams(activity:Activity)=LinearLayout.LayoutParams(
        LinearLayout.LayoutParams.MATCH_PARENT,
        dp(activity,HEIGHT_DP)
    )
}
