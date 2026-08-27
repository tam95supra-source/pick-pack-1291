plugins {
    id("com.android.application")
}

fun quotedConfig(value: String): String = value.replace("\\", "\\\\").replace("\"", "\\\"")
fun configValue(name: String): String = providers.gradleProperty(name).orElse(providers.environmentVariable(name)).orElse("").get()

val approvedGsheetApiUrl = "https://script.google.com/macros/s/AKfycbzbEoGfbNg6s2HnP-gUpcBJ7mMIkVBtYuQKMndb9seDV2c55lQwSUO1GZ-LtQ2CxMCauA/exec"
val gsheetApiUrl = quotedConfig(providers.gradleProperty("GSHEET_API_URL").orElse(providers.environmentVariable("GSHEET_API_URL")).orElse(approvedGsheetApiUrl).get())
val firebaseProjectId = quotedConfig(configValue("FIREBASE_PROJECT_ID"))
val firebaseAppId = quotedConfig(configValue("FIREBASE_GOOGLE_APP_ID"))
val firebaseApiKey = quotedConfig(configValue("FIREBASE_API_KEY"))
val firebaseSenderId = quotedConfig(configValue("FIREBASE_GCM_SENDER_ID"))

android {
    namespace = "vn.pickpack1291.app.beta"
    compileSdk = 36

    defaultConfig {
        applicationId = "vn.pickpack1291.app"
        minSdk = 29
        targetSdk = 36
        buildConfigField("String", "GSHEET_API_URL", "\"$gsheetApiUrl\"")
        buildConfigField("String", "FIREBASE_PROJECT_ID", "\"$firebaseProjectId\"")
        buildConfigField("String", "FIREBASE_GOOGLE_APP_ID", "\"$firebaseAppId\"")
        buildConfigField("String", "FIREBASE_API_KEY", "\"$firebaseApiKey\"")
        buildConfigField("String", "FIREBASE_GCM_SENDER_ID", "\"$firebaseSenderId\"")
    }

    flavorDimensions += "channel"
    productFlavors {
        create("beta") {
            dimension = "channel"
            applicationId = "vn.pickpack1291.app.beta.publicbeta"
            versionCode = 90
            versionName = "0.4.2-beta.84"
            manifestPlaceholders["appLabel"] = "Pick Pack 1291 Beta"
            buildConfigField("String", "CHANNEL", "\"BETA\"")
        }
        create("stable") {
            dimension = "channel"
            applicationId = "vn.pickpack1291.app.stable"
            versionCode = 1
            versionName = "0.1.0-stable"
            manifestPlaceholders["appLabel"] = "Pick Pack 1291"
            buildConfigField("String", "CHANNEL", "\"STABLE\"")
        }
    }

    buildTypes {
        debug { isMinifyEnabled = false }
        release { isMinifyEnabled = false }
    }

    buildFeatures { buildConfig = true }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation("androidx.work:work-runtime:2.11.2")
    implementation("com.squareup.okhttp3:okhttp:5.3.0")
    implementation(platform("com.google.firebase:firebase-bom:34.16.0"))
    implementation("com.google.firebase:firebase-messaging")
    testImplementation("junit:junit:4.13.2")
}

// M2 target: Android/PWA <-> Service <-> D1, with GAS as controlled fallback/legacy bridge.
// Firebase is owner-approved only for FCM wake/invalidation; no Firebase Auth/DB/Storage dependency is present.
// Firebase client identifiers are injected at build time and default blank so source never contains project config.
// GSHEET_API_URL remains public discovery/fallback configuration and manual update lookup path; no Service URL is compiled into APK.
// Signing material remains outside this repository and the Android signer is owner-locked.
// Beta84: prune stale OTA APK downloads, sort reconciliation staff by supplier/MNV/name, HHmm ±2 minute confirmation without guidance text, and merge canonical audit payload shapes. Stable remains isolated and unchanged.
// Beta83: owner session UI ordering/timeline detail + HH:mm privileged action confirmation; actual SUPERADMIN also keeps fixed account-password confirmation. Stable remains isolated and unchanged.
// Beta82: current-day shift reconciliation lists, QR-session reconciliation cards, null-safe display, and simplified Settings information. Stable remains isolated and unchanged.
// Beta80: restore canonical Service v2 session routes and direct FileProvider OTA installer launch. Stable remains isolated and unchanged.
// Beta79: old-session warning opens the exact historical session in the normal QR workflow with full Add/Edit/Delete/Exit actions. Stable remains isolated and unchanged.\n// Beta78: exact historical-session identity/detail + Service/D1 primary Nhận hàng rớt with fenced outbox replication. Stable remains isolated and unchanged.
// Beta77: owner fixes for Nhận hàng rớt latency/CRUD, cross-day active PDA visibility, old-session warning, and employee render stability. Stable remains isolated and unchanged.
// Beta76: direct GAS/Sheets Nhận hàng rớt workflow; Stable remains isolated and unchanged.
// Beta65: multi-position/multi-resource session ownership + reference-stage login parity.
// Beta64 remains immutable previous public baseline.
// Beta64: exact-fit Vietnam/Supra login, MNV callback fencing, separate user reissue chooser,
// current-session timeline filtering, accurate work display, and app cache storage visibility.
// Beta63 remains immutable and is the previous public baseline.
// Beta62 remains immutable historical evidence.
// Beta61 remains immutable historical evidence.
// Beta60 remains immutable historical evidence.
// Beta59 remains immutable historical evidence.
// Beta58 remains immutable historical evidence.
// Beta57 remains immutable; Beta56 remains denylisted/cancelled and VC62 is intentionally skipped.
// Legacy Beta44 candidate-workflow compatibility markers only; actual beta metadata above is authoritative:
// versionCode = 50
// versionName = "0.4.2-beta.44"
