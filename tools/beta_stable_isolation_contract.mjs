import fs from "node:fs";
const read=p=>fs.readFileSync(p,"utf8");
const must=(x,m)=>{if(!x)throw new Error("ISOLATION_CONTRACT_FAIL:"+m)};
const gradle=read("app/build.gradle.kts");
const manifest=read("app/src/main/AndroidManifest.xml");
const entry=read("service/src/entry_product.ts");
const app=read("service/public/app.js");
const sw=read("service/public/sw.js");
const lan=read("app/src/main/java/vn/pickpack1291/app/beta/LanDiscovery.kt");
const sock=read("app/src/main/java/vn/pickpack1291/app/beta/LanSocketTransport.kt");
const req=JSON.parse(read("ops/stable-private-provision-request.json"));
const promo=JSON.parse(read("ops/promotion-lock-dry-run.json"));

for(const s of [
  'applicationId = "vn.pickpack1291.app.beta.publicbeta"',
  'applicationId = "vn.pickpack1291.app.stable"',
  'ENVIRONMENT_ID", "\\"BETA\\"',
  'ENVIRONMENT_ID", "\\"STABLE\\"',
  'SERVICE_AUDIENCE", "\\"PICK_PACK_1291_BETA\\"',
  'SERVICE_AUDIENCE", "\\"PICK_PACK_1291_STABLE\\"',
  'LAN_SERVICE_TYPE", "\\"_pp1291b._tcp.\\"',
  'LAN_SERVICE_TYPE", "\\"_pp1291s._tcp.\\"',
  'TARGET_WEB_ORIGIN", "\\"https://beta.pickpack1291.cc.cd\\"',
  'TARGET_WEB_ORIGIN", "\\"https://pickpack1291.cc.cd\\"'
]) must(gradle.includes(s),"GRADLE_"+s.replace(/[^A-Za-z0-9]/g,"_").slice(0,60));
must(manifest.includes('android:authorities="${applicationId}.fileprovider"'),"FILEPROVIDER_NOT_APP_SCOPED");
must(!/sharedUserId/i.test(manifest),"SHARED_USER_ID_PRESENT");
must(manifest.includes('android:allowBackup="false"')&&manifest.includes('android:fullBackupContent="false"'),"ANDROID_BACKUP_NOT_FENCED");
must(manifest.includes('android:name=".M2FirebaseMessagingService"')&&manifest.includes('android:exported="false"'),"FCM_SERVICE_EXPORTED");
must(manifest.includes('android:name=".LanForegroundService"')&&manifest.includes('android:exported="false"'),"LAN_SERVICE_EXPORTED");
must((manifest.match(/android:exported="true"/g)||[]).length===1&&manifest.includes('android:name=".FullBetaActivity"'),"EXPORTED_COMPONENT_MATRIX_CHANGED");
must(lan.includes('serviceType=serviceType()')&&lan.includes('setAttribute("env",BuildConfig.ENVIRONMENT_ID)')&&lan.includes('if(environmentId!=BuildConfig.ENVIRONMENT_ID)return'),"NSD_ENV_FENCE_MISSING");
must(sock.includes('put("environment_id",BuildConfig.ENVIRONMENT_ID)')&&sock.includes('ENVIRONMENT_MISMATCH'),"LAN_FRAME_ENV_FENCE_MISSING");
must(entry.includes('const expected=String(env.ENVIRONMENT_ID||"BETA").toUpperCase()'),"SERVER_ENV_NOT_BINDING_DERIVED");
must(entry.includes('got&&got!==expected')&&entry.includes('audience&&audience!==expectedAudience'),"SERVER_MISMATCH_REJECT_MISSING");
must(!entry.includes("ENVIRONMENT_ID=request.headers"),"CLIENT_HEADER_USED_AS_AUTHORITY");
must(app.includes("fetch('/environment.json',{cache:'no-store'})"),"PWA_RUNTIME_ENV_CONFIG_MISSING");
must(app.includes("headers.set('X-Pick-Pack-Environment',env.environment_id)")&&app.includes("headers.set('X-Pick-Pack-Audience',env.service_audience)"),"PWA_ENV_HEADERS_MISSING");
must(!/document\.cookie|cookieStore/i.test(app),"PWA_SHARED_COOKIE_PATH_PRESENT");
must(sw.includes("self.location.host")&&sw.includes("pick-pack-1291-"),"SW_CACHE_NOT_HOST_SCOPED");
must(req.environment==="STABLE"&&req.stable_public_activation===false,"STABLE_PUBLIC_ACTIVATION_NOT_FALSE");
must(promo.stable_promotion_lock.status==="DRY_RUN_READY","PROMOTION_LOCK_NOT_DRY_RUN");
must(promo.stable_promotion_lock.stable.manifest_active===false&&promo.stable_promotion_lock.stable.ota_active===false&&promo.stable_promotion_lock.stable.public_domain_active===false,"STABLE_PROMOTION_DRY_RUN_PUBLIC");
for(const p of ["app/build.gradle.kts","service/src/entry_product.ts","service/public/app.js"]){
  must(!/supabase/i.test(read(p)),"SUPABASE_REFERENCE_"+p);
}
console.log("beta_stable_isolation_contract=PASS package=PASS provider=PASS nsd_lan=PASS pwa=PASS server_fence=PASS stable_ready_not_live=PASS");
