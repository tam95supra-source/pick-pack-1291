package vn.pickpack1291.app.beta

import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequest
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import java.util.concurrent.TimeUnit

class DocumentUploadWorker(appContext:Context,params:WorkerParameters):Worker(appContext,params){
    override fun doWork():Result{
        val api=BetaApiClient(applicationContext)
        val login=api.restoredAccount()?.optString("login_id").orEmpty()
        if(login.isBlank()||api.token.isNullOrBlank())return Result.success()
        val store=DocumentPendingStore(applicationContext)
        val engine=DocumentUploadEngine(applicationContext,api)
        var retry=false
        store.list().take(MAX_PER_RUN).forEach{item->
            if(item.ownerLogin!=login)return@forEach
            when(engine.runOne(item).status){
                DocumentUploadEngine.Status.RETRY->retry=true
                else->{}
            }
        }
        return if(retry)Result.retry() else Result.success()
    }

    companion object{
        private const val WORK_NAME="document-pending-upload-v1"
        private const val MAX_PER_RUN=5
        fun schedule(context:Context,replace:Boolean=false){
            val request=OneTimeWorkRequest.Builder(DocumentUploadWorker::class.java)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL,30,TimeUnit.SECONDS)
                .build()
            WorkManager.getInstance(context.applicationContext).enqueueUniqueWork(
                WORK_NAME,
                if(replace)ExistingWorkPolicy.REPLACE else ExistingWorkPolicy.KEEP,
                request
            )
        }
    }
}
