package vn.pickpack1291.app.beta

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build

class LanForegroundService:Service(){
    override fun onCreate(){
        super.onCreate()
        val channelId="pp1291_lan"
        if(Build.VERSION.SDK_INT>=26){
            (getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager)
                .createNotificationChannel(NotificationChannel(channelId,"Pick Pack LAN",NotificationManager.IMPORTANCE_LOW))
        }
        val notification=Notification.Builder(this,channelId)
            .setSmallIcon(android.R.drawable.stat_sys_upload)
            .setContentTitle("Pick Pack 1291 • LAN đang hoạt động")
            .setContentText("Duy trì kết nối Master/backup trong mạng nội bộ")
            .setOngoing(true).build()
        if(Build.VERSION.SDK_INT>=29)startForeground(1291,notification,android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE)
        else startForeground(1291,notification)
    }
    override fun onStartCommand(intent:Intent?,flags:Int,startId:Int)=START_STICKY
    override fun onBind(intent:Intent?)=null
}
