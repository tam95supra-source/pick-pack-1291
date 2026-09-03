package vn.pickpack1291.app.beta

import android.app.Activity
import android.app.AlertDialog
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.GridLayout
import android.widget.LinearLayout
import android.widget.TextView
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * Calendar for DISPLAY-ONLY date filters.
 * Dates without real data are visible but disabled/dimmed, except TODAY which is always selectable
 * so the operator can intentionally view an empty current-day state.
 * Do not use for date/time correction or data editing.
 */
object DataDatePickerUi {
    private val iso = DateTimeFormatter.ISO_LOCAL_DATE
    private val title = DateTimeFormatter.ofPattern("MM/yyyy", Locale("vi","VN"))
    private val weekday = listOf("T2","T3","T4","T5","T6","T7","CN")

    fun show(activity:Activity, availableDates:Collection<String>, selectedDate:String?, onSelected:(String)->Unit){
        val dataDates=availableDates.mapNotNull{runCatching{LocalDate.parse(it,iso)}.getOrNull()}.toSortedSet()
        val today=LocalDate.now()
        val selectable=(dataDates+today).toSortedSet()
        val selected=runCatching{selectedDate?.let{LocalDate.parse(it,iso)}}.getOrNull()?.takeIf{it in selectable}
        var month=YearMonth.from(selected?:today)
        val outer=LinearLayout(activity).apply{
            orientation=LinearLayout.VERTICAL
            setPadding(dp(activity,12),dp(activity,8),dp(activity,12),dp(activity,8))
        }
        val header=LinearLayout(activity).apply{orientation=LinearLayout.HORIZONTAL;gravity=Gravity.CENTER_VERTICAL}
        val prev=nav(activity,"‹")
        val monthTitle=text(activity,"",13f,Color.rgb(15,47,77),true).apply{gravity=Gravity.CENTER}
        val next=nav(activity,"›")
        header.addView(prev,LinearLayout.LayoutParams(dp(activity,44),dp(activity,42)))
        header.addView(monthTitle,LinearLayout.LayoutParams(0,dp(activity,42),1f))
        header.addView(next,LinearLayout.LayoutParams(dp(activity,44),dp(activity,42)))
        outer.addView(header,ViewGroup.LayoutParams(-1,-2))
        val grid=GridLayout(activity).apply{columnCount=7;alignmentMode=GridLayout.ALIGN_BOUNDS}
        outer.addView(grid,ViewGroup.LayoutParams(-1,-2))
        val dialog=AlertDialog.Builder(activity).setTitle("Chọn ngày xem dữ liệu").setView(outer).setNegativeButton("Hủy",null).create()

        fun render(){
            grid.removeAllViews()
            monthTitle.text=month.atDay(1).format(title)
            weekday.forEach{w->
                grid.addView(text(activity,w,9.5f,Color.rgb(100,116,139),true).apply{gravity=Gravity.CENTER},
                    GridLayout.LayoutParams().apply{width=0;height=dp(activity,32);columnSpec=GridLayout.spec(GridLayout.UNDEFINED,1f)})
            }
            val first=month.atDay(1)
            val offset=(first.dayOfWeek.value-DayOfWeek.MONDAY.value+7)%7
            repeat(offset){grid.addView(View(activity),GridLayout.LayoutParams().apply{width=0;height=dp(activity,42);columnSpec=GridLayout.spec(GridLayout.UNDEFINED,1f)})}
            for(day in 1..month.lengthOfMonth()){
                val date=month.atDay(day);val hasData=date in dataDates;val enabled=hasData||date==today;val chosen=date==selected
                val cell=text(activity,day.toString(),11.5f,if(enabled)Color.rgb(15,47,77) else Color.rgb(148,163,184),enabled).apply{
                    gravity=Gravity.CENTER
                    isEnabled=enabled
                    alpha=if(enabled)1f else .30f
                    isClickable=enabled
                    background=when{
                        chosen->shape(activity,Color.rgb(226,245,244),Color.rgb(13,148,136),2)
                        enabled->shape(activity,Color.WHITE,Color.rgb(203,213,225),1)
                        else->shape(activity,Color.rgb(248,250,252),Color.TRANSPARENT,0)
                    }
                    if(enabled)setOnClickListener{dialog.dismiss();onSelected(date.format(iso))}
                }
                grid.addView(cell,GridLayout.LayoutParams().apply{
                    width=0;height=dp(activity,42);columnSpec=GridLayout.spec(GridLayout.UNDEFINED,1f)
                    setMargins(dp(activity,2),dp(activity,2),dp(activity,2),dp(activity,2))
                })
            }
            val months=selectable.map{YearMonth.from(it)}.toSet()
            prev.isEnabled=months.any{it<month};prev.alpha=if(prev.isEnabled)1f else .3f
            next.isEnabled=months.any{it>month};next.alpha=if(next.isEnabled)1f else .3f
        }
        prev.setOnClickListener{selectable.map{YearMonth.from(it)}.filter{it<month}.maxOrNull()?.let{month=it;render()}}
        next.setOnClickListener{selectable.map{YearMonth.from(it)}.filter{it>month}.minOrNull()?.let{month=it;render()}}
        render();dialog.show()
    }

    private fun nav(a:Activity,label:String)=Button(a).apply{
        text=label;textSize=18f;isAllCaps=false;setTextColor(Color.rgb(15,47,77));background=shape(a,Color.WHITE,Color.rgb(203,213,225),1);minWidth=0;minimumWidth=0
    }
    private fun text(a:Activity,value:String,size:Float,color:Int,bold:Boolean)=TextView(a).apply{
        text=value;textSize=size;setTextColor(color);typeface=if(bold)Typeface.DEFAULT_BOLD else Typeface.DEFAULT
    }
    private fun shape(a:Activity,fill:Int,stroke:Int,strokeDp:Int)=GradientDrawable().apply{
        setColor(fill);cornerRadius=dp(a,10).toFloat();if(strokeDp>0)setStroke(dp(a,strokeDp),stroke)
    }
    private fun dp(a:Activity,v:Int)=(v*a.resources.displayMetrics.density).toInt()
}
