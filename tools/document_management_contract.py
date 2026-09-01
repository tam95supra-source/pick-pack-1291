#!/usr/bin/env python3
from pathlib import Path
import json

root=Path(__file__).resolve().parents[1]
read=lambda p:(root/p).read_text(encoding="utf-8")

migration=read("service/migrations/0010_document_management.sql")
mutation_migration=read("service/migrations/0011_document_category_full_mutation.sql")
batch_migration=read("service/migrations/0012_document_batch_bulk_delete.sql")
service=read("service/src/document_management.ts")
entry=read("service/src/entry_product.ts")
activity=read("app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt")
feature=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentManagementFeature.kt")
image=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentImageProcessor.kt")
client=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentServiceClient.kt")
pending=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentPendingStore.kt")
draft=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentDraftStore.kt")
category_cache=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentCategoryCache.kt")
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
assert "SIMILAR_DHASH_DISTANCE=16" in service and "MAX_DHASH_VARIANTS=4" in service and "hammingHex64" in service
assert "dhash64_variants" in service and "rotation_aware:true" in service
assert "CATEGORY_MUTATION_BATCH=5" in service
assert "CATEGORY_RENAME_ALL" in service and "renameDriveFile" in service
assert "deleteDriveFile" in service and "processDocumentCategoryMutations" in service
assert "DOCUMENT_CATEGORY_PENDING_UPLOADS" in service and "DOCUMENT_CATEGORY_MUTATION_IN_PROGRESS" in service
assert "category_name_snapshot" in service and "fileName=prior?.file_name" in service
assert "mutation_state" in mutation_migration and "document_category_mutations" in mutation_migration and "document_category_mutation_items" in mutation_migration
assert "md5Checksum" in service and "DOCUMENT_DRIVE_VERIFY_FAILED" in service
assert "/v1/documents/upload-session" in entry and "documentMedia" in entry
assert "/v1/documents/delete" in entry and "documentDeleteMutate" in entry
assert all(x in batch_migration for x in ["group_id TEXT","group_mode TEXT","page_index INTEGER","page_count INTEGER","document_delete_mutations","document_delete_items"])
assert all(x in service for x in ["group_id","MULTI_PAGE","MULTI_DOCUMENT","processDocumentDeleteMutations","DOCUMENT_DELETE_SELECTED","flushDocumentAuditHistory"])
assert 'category_name:job.old_display_name' not in service, "hard delete receipt must not retain deleted category name"
assert 'DELETE FROM document_delete_items WHERE mutation_id=?1' in service, "bulk delete checkpoints must be purged after completion"
assert 'VALUES(?1,?2,?3,NULL,NULL,NULL' in service, "bulk delete checkpoint must not persist names"

assert 'businessCard(R.drawable.ic_pp_document,"Quản lý biên bản","",isAdmin()){documentManagementScreen()}' in activity
assert "ACTION_IMAGE_CAPTURE" in activity and "ACTION_OPEN_DOCUMENT" in activity
assert "Intent.EXTRA_ALLOW_MULTIPLE" in activity and "onImagesSelected(uris" in activity
assert "DocumentImageProcessor.process" in feature
assert "DocumentPendingStore(activity)" in feature and "DocumentUploadEngine(activity,api)" in feature
assert "DocumentDraftStore(activity)" in feature and "DocumentCategoryCache(activity)" in feature
assert "restoreCachedCategories()" in feature and "restoreDraft()" in feature
assert "draftStore.append(login" in feature and "draftStore.remove(login)" in feature
assert "Đang dùng danh mục đã lưu trên máy" in feature
assert 'confirmAction("sửa loại biên bản")' in feature and 'confirmAction("xóa loại biên bản")' in feature
assert 'startCategoryMutation("UPDATE"' in feature and 'startCategoryMutation("DELETE"' in feature
assert "localPending>0" in feature and "mediaCache.clearAll()" in feature
assert "DocumentMediaCache(activity)" in feature and "DocumentUploadWorker.schedule(activity" in feature
assert "pendingStore.enqueue" in feature and "uploadEngine.runOne" in feature
assert all(x in feature for x in ["Một biên bản nhiều trang","Nhiều biên bản","filterSpinner","selectedDocumentIds","deleteSelectedRecords","/v1/documents/delete"])
assert "mediaCache.get" in feature and "mediaCache.put" in feature

assert "MAX_EDGE=2400" in image and 'digest("SHA-256"' in image and "dhash64Variants" in image
assert "dhashVariants(bitmap)" in image and "postRotate(angle)" in image and "90f,180f,270f" in image
assert "uploadToDrive" in client and "UPLOAD_URL_NOT_GOOGLE" in client

assert 'File(context.filesDir,"document-pending-v1")' in pending
assert "MAX_ITEMS=60" in pending and "MAX_BYTES=120L*1024L*1024L" in pending
assert '"document_id"' in pending and '"drive_file_id"' in pending and '"dhash64_variants"' in pending
assert "DOCUMENT_PENDING_BYTES_MISSING" in pending
assert "listUnlocked().firstOrNull{it.idempotencyKey==idempotencyKey}" in pending

assert 'File(context.filesDir,"document-draft-v1")' in draft
assert '"manifest.json.tmp"' in draft and '"manifest.json"' in draft
assert "DOCUMENT_DRAFT_BYTES_COMMIT_FAILED" in draft and "DOCUMENT_DRAFT_MANIFEST_COMMIT_FAILED" in draft
assert "loadAll(ownerLogin:String)" in draft and "append(ownerLogin:String" in draft
assert 'if(owner!=ownerLogin.trim())return@runCatching null' in draft and 'digest("SHA-256",bytes)' in draft
assert "dhash64Variants=variants.distinct().take(4)" in draft

assert 'pp1291_document_category_cache_v1' in category_cache
assert 'BuildConfig.ENVIRONMENT_ID+"|"+ownerLogin.trim().lowercase()' in category_cache
assert '"category_id"' in category_cache and '"display_name"' in category_cache

assert "if(!item.documentId.isNullOrBlank()&&!item.driveFileId.isNullOrBlank())" in engine
assert 'store.update(item,driveFileId=driveId' in engine
assert 'store.update(item,documentId=documentId' in engine
assert "EXACT_DUPLICATE_RESOLVED" in engine and "SIMILAR_REVIEW_REQUIRED" in engine
assert "ACCOUNT_MISMATCH" in engine and '"dhash64_variants"' in engine

assert "NetworkType.CONNECTED" in worker
assert "BackoffPolicy.EXPONENTIAL" in worker
assert "ExistingWorkPolicy.KEEP" in worker and "ExistingWorkPolicy.REPLACE" in worker

assert 'File(context.cacheDir,"document-media-v1")' in cache
assert "MAX_FILES=60" in cache and "MAX_BYTES=64L*1024L*1024L" in cache
assert "sortedByDescending{it.lastModified()}" in cache

assert 'cache-path name="document_camera"' in paths
assert 'versionCode = 1' in gradle and 'versionName = "0.1.0-stable"' in gradle
assert f'versionCode = {request["version_code"]}' in gradle
assert f'versionName = "{request["version_name"]}"' in gradle
assert request["version_name"].startswith("0.4.2-beta.") and isinstance(request["version_code"],int)
assert request["stable_publish"]=="FORBIDDEN" and request["authority_change"]=="NONE"
print("document_management_contract=PASS durable_queue=PASS multi_select_draft=PASS multipage_group=PASS multi_document_group=PASS bulk_delete_resume=PASS canonical_history=PASS post_drive_resume=PASS bounded_cache=PASS rotation_similar=PASS offline_category_cache=PASS rename_all=PASS hard_delete=PASS confirmation_reuse=PASS")
