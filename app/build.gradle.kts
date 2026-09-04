plugins {
    id("com.android.application")
}

fun quotedConfig(value: String): String = value.replace("\\", "\\\\").replace("\"", "\\\"")
fun configValue(name: String): String = providers.gradleProperty(name).orElse(providers.environmentVariable(name)).orElse("").get()

val approvedBetaGsheetApiUrl = "https://script.google.com/macros/s/AKfycbzbEoGfbNg6s2HnP-gUpcBJ7mMIkVBtYuQKMndb9seDV2c55lQwSUO1GZ-LtQ2CxMCauA/exec"
val betaGsheetApiUrl = quotedConfig(providers.gradleProperty("BETA_GSHEET_API_URL").orElse(providers.environmentVariable("BETA_GSHEET_API_URL")).orElse(providers.gradleProperty("GSHEET_API_URL")).orElse(providers.environmentVariable("GSHEET_API_URL")).orElse(approvedBetaGsheetApiUrl).get())
val stableGsheetApiUrl = quotedConfig(providers.gradleProperty("STABLE_GSHEET_API_URL").orElse(providers.environmentVariable("STABLE_GSHEET_API_URL")).orElse("").get())
val betaFirebaseProjectId = quotedConfig(providers.gradleProperty("BETA_FIREBASE_PROJECT_ID").orElse(providers.environmentVariable("BETA_FIREBASE_PROJECT_ID")).orElse(configValue("FIREBASE_PROJECT_ID")).get())
val betaFirebaseAppId = quotedConfig(providers.gradleProperty("BETA_FIREBASE_GOOGLE_APP_ID").orElse(providers.environmentVariable("BETA_FIREBASE_GOOGLE_APP_ID")).orElse(configValue("FIREBASE_GOOGLE_APP_ID")).get())
val betaFirebaseApiKey = quotedConfig(providers.gradleProperty("BETA_FIREBASE_API_KEY").orElse(providers.environmentVariable("BETA_FIREBASE_API_KEY")).orElse(configValue("FIREBASE_API_KEY")).get())
val betaFirebaseSenderId = quotedConfig(providers.gradleProperty("BETA_FIREBASE_GCM_SENDER_ID").orElse(providers.environmentVariable("BETA_FIREBASE_GCM_SENDER_ID")).orElse(configValue("FIREBASE_GCM_SENDER_ID")).get())
val stableFirebaseProjectId = quotedConfig(configValue("STABLE_FIREBASE_PROJECT_ID"))
val stableFirebaseAppId = quotedConfig(configValue("STABLE_FIREBASE_GOOGLE_APP_ID"))
val stableFirebaseApiKey = quotedConfig(configValue("STABLE_FIREBASE_API_KEY"))
val stableFirebaseSenderId = quotedConfig(configValue("STABLE_FIREBASE_GCM_SENDER_ID"))

android {
    namespace = "vn.pickpack1291.app.beta"
    compileSdk = 36

    defaultConfig {
        applicationId = "vn.pickpack1291.app"
        minSdk = 29
        targetSdk = 36
    }

    flavorDimensions += "channel"
    productFlavors {
        create("beta") {
            dimension = "channel"
            applicationId = "vn.pickpack1291.app.beta.publicbeta"
            versionCode = 126
            versionName = "0.4.2-beta.120"
            manifestPlaceholders["appLabel"] = "Pick Pack 1291 Beta"
            buildConfigField("String", "CHANNEL", "\"BETA\"")
            buildConfigField("String", "ENVIRONMENT_ID", "\"BETA\"")
            buildConfigField("String", "SERVICE_AUDIENCE", "\"PICK_PACK_1291_BETA\"")
            buildConfigField("String", "LAN_SERVICE_TYPE", "\"_pp1291b._tcp.\"")
            buildConfigField("String", "TARGET_WEB_ORIGIN", "\"https://beta.pickpack1291.cc.cd\"")
            buildConfigField("String", "GSHEET_API_URL", "\"$betaGsheetApiUrl\"")
            buildConfigField("String", "FIREBASE_PROJECT_ID", "\"$betaFirebaseProjectId\"")
            buildConfigField("String", "FIREBASE_GOOGLE_APP_ID", "\"$betaFirebaseAppId\"")
            buildConfigField("String", "FIREBASE_API_KEY", "\"$betaFirebaseApiKey\"")
            buildConfigField("String", "FIREBASE_GCM_SENDER_ID", "\"$betaFirebaseSenderId\"")
        }
        create("stable") {
            dimension = "channel"
            applicationId = "vn.pickpack1291.app.stable"
            versionCode = 1
            versionName = "0.1.0-stable"
            manifestPlaceholders["appLabel"] = "Pick Pack 1291"
            buildConfigField("String", "CHANNEL", "\"STABLE\"")
            buildConfigField("String", "ENVIRONMENT_ID", "\"STABLE\"")
            buildConfigField("String", "SERVICE_AUDIENCE", "\"PICK_PACK_1291_STABLE\"")
            buildConfigField("String", "LAN_SERVICE_TYPE", "\"_pp1291s._tcp.\"")
            buildConfigField("String", "TARGET_WEB_ORIGIN", "\"https://pickpack1291.cc.cd\"")
            buildConfigField("String", "GSHEET_API_URL", "\"$stableGsheetApiUrl\"")
            buildConfigField("String", "FIREBASE_PROJECT_ID", "\"$stableFirebaseProjectId\"")
            buildConfigField("String", "FIREBASE_GOOGLE_APP_ID", "\"$stableFirebaseAppId\"")
            buildConfigField("String", "FIREBASE_API_KEY", "\"$stableFirebaseApiKey\"")
            buildConfigField("String", "FIREBASE_GCM_SENDER_ID", "\"$stableFirebaseSenderId\"")
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

tasks.register("verifyBetaReleaseNotes") {
    group = "verification"
    description = "Fail when Beta version is bumped without updating the in-app changelog."
    doLast {
        val expected = android.productFlavors.getByName("beta").versionName.orEmpty()
        val notes = file("src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt").readText()
        val marker = "const val VERSION_NAME = \"$expected\""
        check(expected.isNotBlank() && notes.contains(marker)) {
            "ReleaseNotes.VERSION_NAME must match beta versionName $expected"
        }
    }
}
tasks.named("preBuild").configure { dependsOn("verifyBetaReleaseNotes") }

dependencies {
    implementation("androidx.work:work-runtime:2.11.2")
    implementation("com.squareup.okhttp3:okhttp:5.3.0")
    implementation("org.java-websocket:Java-WebSocket:1.6.0")
    implementation("com.google.zxing:core:3.5.3")
    implementation(platform("com.google.firebase:firebase-bom:34.16.0"))
    implementation("com.google.firebase:firebase-messaging")
    testImplementation("junit:junit:4.13.2")
}

// M2 target: Android/PWA <-> Service <-> D1, with GAS as controlled fallback/legacy bridge.
// Firebase is owner-approved only for FCM wake/invalidation; no Firebase Auth/DB/Storage dependency is present.
// Firebase client identifiers are injected at build time and default blank so source never contains project config.
// GSHEET_API_URL remains public discovery/fallback configuration and manual update lookup path; no Service URL is compiled into APK.
// Signing material remains outside this repository and the Android signer is owner-locked.
// Beta120: route SUPERADMIN bulk old-session exit directly to Service and execute bounded canonical chunks to prevent GAS UNKNOWN/request timeout; preserves Beta119 behavior. Stable unchanged.
// Beta119: SUPERADMIN session persistence, HHmm ±5 time auth, 8-digit single-use Gmail OTP rotation, and repository-backed realtime current/acceptance security fencing; preserves Beta118 behavior. Stable unchanged.
// Beta118: SUPERADMIN bulk old-session exit, owner test data, compact document/drop UI follow-up, targeted websocket refresh, and optimistic labor cache; preserves Beta117 accepted semantics. Stable unchanged.
// Beta117: OWNER follow-up document compact/edit/fullscreen, cross-document viewer, dropped-receiving admin layout, large-data rendering, fixed-role labor bulk/per-person ack, true SUPERADMIN LAN mode, compact selects, and stronger transform-only tap feedback; preserves Beta116 ACTIVE_PASS. Stable unchanged.\n// Beta116: document batch UX/notes/viewer, PDA/drop/attendance/QR/labor/report refinements, SUPERADMIN password reset, global isolated LAN test control, and light tap feedback; preserves Beta115 accepted ACTIVE_PASS behavior. Stable unchanged.
// Beta115: owner revisions for labor future-end caps/quarter-hour wrap/deduction/bulk operations, canonical selects, and current-day empty calendar selection; preserves Beta114 accepted ACTIVE_PASS behavior. Stable unchanged.
// Beta114: supersedes locked pre-OTA Beta113; preserves inline roster while restoring ACTIVE_PASS roster filters/drilldown and employee-to-QR tap. Stable unchanged.\n// Beta113: pre-OTA candidate superseded after roster interaction regression; never published.
// Beta112: unified reconciliation/warning UI component; fixed geometry and canonical colors; Beta111 owner-accepted items 2-7 preserved. Stable unchanged.\n// Beta111: owner UI/labor/navigation corrections: actual back stack, exact-session labor authority, non-wrapping wheel time, daily labor list/correction, unified warnings, document tick modes, canonical history-delete cleanup. Stable unchanged.\n// Beta108: durable document pending queue + post-Drive completion resume + bounded 64MB media cache; inherits Beta107 Drive metadata/duplicate design. Category edit/archive remains OWNER-decision fail-closed. Stable unchanged.
// Beta107: Quản lý biên bản stores metadata in Service/D1 while image bytes upload direct to Google Drive; exact + perceptual duplicate detection. Category edit/archive remains OWNER-decision fail-closed. Stable unchanged.
// Beta106: sanitize JSONObject.NULL/\"null\" master fields in NCC roster; preserve Beta105 roster/download-QR scope. Stable remains READY_NOT_LIVE until OWNER release.
// Beta105: NCC-grouped shift staff roster, direct employee QR context, and dynamic GitHub Release download QR. Stable remains READY_NOT_LIVE until OWNER release.
// Beta104: ensure TTL cache branch also passes environment/audience validation before reuse; Beta103 pre-OTA superseded. Stable remains READY_NOT_LIVE.
// Beta103 pre-OTA superseded: invalidate cross-environment stale discovery cache and refresh dynamic BETA Service discovery before live Service session/read/sync/outbox routes. Stable remains READY_NOT_LIVE.
// Beta102: environment/audience fencing across HTTP + GAS fallback and env-scoped LAN/NSD for Beta/Stable isolation. Stable remains READY_NOT_LIVE.
// Beta100: isolated resilience test center + professional clickable Network/Sync/Service details; manual Sync Now retained inside Sync detail. Stable remains isolated and unchanged.
// Beta99: PDA-only change/return preserves unrelated Service-authoritative resources; SUPERADMIN fault injection has deterministic non-business probe evidence + auto recovery. Stable remains isolated and unchanged.
// Beta98: exact current-session PDA exit authority; missing resource snapshot resolves by session_id and legacy pda_serial is ignored. Stable remains isolated and unchanged.\n// Beta97: fix post-meal current-day session eligibility, persistent status header, home attendance warning, and History role visibility; preserves QR core behavior. Stable remains isolated and unchanged.
// Beta96: API29-compatible local meal-attendance cache write; preserves Beta95 service/storage/QR/attendance behavior. Stable remains isolated and unchanged.
// Beta95: bound D1 Free retention/read amplification, local-first employee QR session rendering, and 14-day post-meal attendance. Stable remains isolated and unchanged.
// Beta94: align report columns/thinner borders, verify PDA only when actively assigned at exit, and unify old-session warning text. Stable remains isolated and unchanged.\n// Beta93: resolve authoritative ACTIVE session before exit, block blank session_id requests, and single-flight duplicate exit taps. Stable remains isolated and unchanged.\n// Beta92: Service-authoritative User Pick/User Pack/Pack Table options, no background employee UI reset, and dual user-facing changelogs. Stable remains isolated and unchanged.\n// Beta91: Pack availability consistency/current-session retention + realtime changed-fields-only employee timeline. Stable remains isolated and unchanged.\n// Beta90: complete first-log metadata persistence after acknowledged upload cleanup; inherits Beta89 API36 Back, canonical before/after projection, and same-session PDA validation fixes. Stable remains isolated and unchanged.
// Beta89: superseded pre-OTA; not published because first-log init metadata could still render blank after cleanup.
// Beta88: owner-approved navigation, staff identity, exact audit before/after, reconciliation detail, attendance card, PDA-return projection, and Pick-account display fixes. Stable remains isolated and unchanged.
// Beta87: owner UI/data correctness fixes: action placement, Pack pair validation, editable delete reason, authoritative before/after audit, header sync action, compact timeline, and report cleanup. Stable remains isolated and unchanged.
// Beta86: preserve the current UI while making realtime refresh event-driven and partial to reduce main-thread churn/jank. Stable remains isolated and unchanged.\n// Beta85: correct HHmm numeric validation after Beta84 pre-OTA rejection; keeps Beta84 four owner fixes. Stable remains isolated and unchanged.
// Beta84: pre-OTA candidate only; never published because HHmm validation regression was caught before OTA.
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
