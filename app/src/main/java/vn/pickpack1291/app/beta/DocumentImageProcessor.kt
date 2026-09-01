package vn.pickpack1291.app.beta

import android.content.Context
import android.graphics.Bitmap
import android.graphics.ImageDecoder
import android.graphics.Matrix
import android.net.Uri
import java.io.ByteArrayOutputStream
import java.security.MessageDigest
import kotlin.math.max
import kotlin.math.roundToInt

object DocumentImageProcessor {
    data class ProcessedImage(
        val bytes:ByteArray,
        val sha256:String,
        val md5:String,
        val dhash64:String,
        val dhash64Variants:List<String>,
        val width:Int,
        val height:Int,
        val mimeType:String="image/jpeg"
    )
    private const val MAX_EDGE=2400
    private const val TARGET_BYTES=2_000_000

    fun process(context:Context,uri:Uri):ProcessedImage{
        val source=ImageDecoder.createSource(context.contentResolver,uri)
        val bitmap=ImageDecoder.decodeBitmap(source){decoder,info,_->
            val w=info.size.width.coerceAtLeast(1);val h=info.size.height.coerceAtLeast(1)
            val longest=max(w,h)
            if(longest>MAX_EDGE){
                val scale=MAX_EDGE.toDouble()/longest.toDouble()
                decoder.setTargetSize((w*scale).roundToInt().coerceAtLeast(1),(h*scale).roundToInt().coerceAtLeast(1))
            }
            decoder.allocator=ImageDecoder.ALLOCATOR_SOFTWARE
        }
        try{
            val bytes=compress(bitmap)
            val dhashes=dhashVariants(bitmap)
            return ProcessedImage(
                bytes=bytes,
                sha256=digest("SHA-256",bytes),
                md5=digest("MD5",bytes),
                dhash64=dhashes.first(),
                dhash64Variants=dhashes,
                width=bitmap.width,
                height=bitmap.height
            )
        }finally{bitmap.recycle()}
    }
    private fun compress(bitmap:Bitmap):ByteArray{
        var last=ByteArray(0)
        for(quality in intArrayOf(82,76,70)){
            val out=ByteArrayOutputStream()
            if(!bitmap.compress(Bitmap.CompressFormat.JPEG,quality,out))throw IllegalStateException("DOCUMENT_IMAGE_COMPRESS_FAILED")
            last=out.toByteArray()
            if(last.size<=TARGET_BYTES)break
        }
        return last
    }
    private fun digest(algorithm:String,bytes:ByteArray)=MessageDigest.getInstance(algorithm).digest(bytes)
        .joinToString(""){(it.toInt() and 0xff).toString(16).padStart(2,'0')}
    private fun dhashVariants(bitmap:Bitmap):List<String>{
        val out=linkedSetOf<String>()
        out.add(dhash(bitmap))
        for(angle in floatArrayOf(90f,180f,270f)){
            val rotated=Bitmap.createBitmap(bitmap,0,0,bitmap.width,bitmap.height,Matrix().apply{postRotate(angle)},true)
            try{out.add(dhash(rotated))}finally{if(rotated!==bitmap)rotated.recycle()}
        }
        return out.toList()
    }
    private fun dhash(bitmap:Bitmap):String{
        val tiny=Bitmap.createScaledBitmap(bitmap,9,8,true)
        try{
            var value=0UL
            var bit=0
            for(y in 0 until 8){
                for(x in 0 until 8){
                    val a=tiny.getPixel(x,y);val b=tiny.getPixel(x+1,y)
                    fun lum(c:Int)=((android.graphics.Color.red(c)*299)+(android.graphics.Color.green(c)*587)+(android.graphics.Color.blue(c)*114))/1000
                    if(lum(a)>lum(b))value=value or (1UL shl bit)
                    bit++
                }
            }
            return value.toString(16).padStart(16,'0')
        }finally{tiny.recycle()}
    }
}
