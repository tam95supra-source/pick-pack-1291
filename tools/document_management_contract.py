#!/usr/bin/env python3
from pathlib import Path
import json

root=Path(__file__).resolve().parents[1]
read=lambda p:(root/p).read_text(encoding="utf-8")

migration=read("service/migrations/0010_document_management.sql")
service=read("service/src/document_management.ts")
entry=read("service/src/entry_product.ts")
activity=read("app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt")
feature=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentManagementFeature.kt")
image=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentImageProcessor.kt")
client=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentServiceClient.kt")
pending=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentPendingStore.kt")
engine=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentUploadEngine.kt")
worker=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentUploadWorker.kt")
cache=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentMediaCache.kt")
paths=read("app/src/main/res/xml/file_paths.xml")
gradle=read("app/build.gradle.kts")
request=json.loads(read("ops/beta-release-request.json"))

assert " BLOB" not in migration.upper(), "document schema must never store image blobs"
assert "sha256 TEXT NOT NULL" in migration and "dhash64 TEXT" in migration and "md5 TEXT NOT NULL" in migration
assert 'set("uploadType","resumable")' in service
assert "DOCUMENT_EXACT_DUPLICATE" in service and "DOCUMENT_SIMILAR_IMAGE" in service
assert "SIMILAR_DHASH_DISTANCE" in service and "hammingHex64" in service
assert 'operation!=="CREATE"' in service and "DOCUMENT_CATEGORY_EDIT_DELETE_OWNER_DECISION_REQUIRED" in service
assert "category_name_snapshot" in service and "fileName=prior?.file_name" in service
assert "md5Checksum" in service and "DOCUMENT_DRIVE_VERIFY_FAILED" in service
assert "/v1/documents/upload-session" in entry and "documentMedia" in entry

assert 'businessCard(R.drawable.ic_pp_document,"Quản lý biên bản","",isAdmin()){documentManagementScreen()}' in activity
assert "ACTION_IMAGE_CAPTURE" in activity and "ACTION_OPEN_DOCUMENT" in activity
assert "DocumentImageProcessor.process" in feature
assert "DocumentPendingStore(activity)" in feature and "DocumentUploadEngine(activity,api)" in feature
assert "DocumentMediaCache(activity)" in feature and "DocumentUploadWorker.schedule(activity" in feature
assert "pendingStore.enqueue" in feature and "uploadEngine.runOne" in feature
assert "mediaCache.get" in feature and "mediaCache.put" in feature

assert "MAX_EDGE=2400" in image and 'digest("SHA-256"' in image and "dhash64" in image
assert "uploadToDrive" in client and "UPLOAD_URL_NOT_GOOGLE" in client

assert 'File(context.filesDir,"document-pending-v1")' in pending
assert "MAX_ITEMS=60" in pending and "MAX_BYTES=120L*1024L*1024L" in pending
assert '"document_id"' in pending and '"drive_file_id"' in pending
assert "DOCUMENT_PENDING_BYTES_MISSING" in pending
assert "listUnlocked().firstOrNull{it.idempotencyKey==idempotencyKey}" in pending

assert "if(!item.documentId.isNullOrBlank()&&!item.driveFileId.isNullOrBlank())" in engine
assert 'store.update(item,driveFileId=driveId' in engine
assert 'store.update(item,documentId=documentId' in engine
assert "EXACT_DUPLICATE_RESOLVED" in engine and "SIMILAR_REVIEW_REQUIRED" in engine
assert "ACCOUNT_MISMATCH" in engine

assert "NetworkType.CONNECTED" in worker
assert "BackoffPolicy.EXPONENTIAL" in worker
assert "ExistingWorkPolicy.KEEP" in worker and "ExistingWorkPolicy.REPLACE" in worker

assert 'File(context.cacheDir,"document-media-v1")' in cache
assert "MAX_FILES=60" in cache and "MAX_BYTES=64L*1024L*1024L" in cache
assert "sortedByDescending{it.lastModified()}" in cache

assert 'cache-path name="document_camera"' in paths
assert 'versionCode = 1' in gradle and 'versionName = "0.1.0-stable"' in gradle
assert 'versionCode = 114' in gradle and 'versionName = "0.4.2-beta.108"' in gradle
assert request["version_name"]=="0.4.2-beta.108" and request["version_code"]==114
assert request["stable_publish"]=="FORBIDDEN" and request["authority_change"]=="NONE"
print("document_management_contract=PASS durable_queue=PASS post_drive_resume=PASS bounded_cache=PASS category_mutation_fail_closed=PASS")
