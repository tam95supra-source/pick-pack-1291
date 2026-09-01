#!/usr/bin/env python3
from pathlib import Path

root=Path(__file__).resolve().parents[1]
migration=(root/"service/migrations/0010_document_management.sql").read_text()
service=(root/"service/src/document_management.ts").read_text()
entry=(root/"service/src/entry_product.ts").read_text()
activity=(root/"app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt").read_text()
feature=(root/"app/src/main/java/vn/pickpack1291/app/beta/DocumentManagementFeature.kt").read_text()
image=(root/"app/src/main/java/vn/pickpack1291/app/beta/DocumentImageProcessor.kt").read_text()
paths=(root/"app/src/main/res/xml/file_paths.xml").read_text()
gradle=(root/"app/build.gradle.kts").read_text()

assert " BLOB" not in migration.upper(), "document schema must never store image blobs"
assert "sha256 TEXT NOT NULL" in migration and "dhash64 TEXT" in migration and "md5 TEXT NOT NULL" in migration
assert "uploadType\",\"resumable" in service or 'set("uploadType","resumable")' in service
assert "DOCUMENT_EXACT_DUPLICATE" in service and "DOCUMENT_SIMILAR_IMAGE" in service
assert "SIMILAR_DHASH_DISTANCE" in service and "hammingHex64" in service
assert 'operation!==\"CREATE\"' in service and "DOCUMENT_CATEGORY_EDIT_DELETE_OWNER_DECISION_REQUIRED" in service
assert "category_name_snapshot" in service and "fileName=prior?.file_name" in service
assert "md5Checksum" in service and "DOCUMENT_DRIVE_VERIFY_FAILED" in service
assert "/v1/documents/upload-session" in entry and "documentMedia" in entry
assert 'businessCard(R.drawable.ic_pp_document,\"Quản lý biên bản\",\"\",isAdmin()){documentManagementScreen()}' in activity
assert "ACTION_IMAGE_CAPTURE" in activity and "ACTION_OPEN_DOCUMENT" in activity
assert "DocumentImageProcessor.process" in feature and "uploadToDrive" in feature
assert "DOCUMENT_EXACT_DUPLICATE" in feature and "DOCUMENT_SIMILAR_IMAGE" in feature
assert "MAX_EDGE=2400" in image and 'digest("SHA-256"' in image and "dhash64" in image
assert 'cache-path name="document_camera"' in paths
assert 'versionCode = 1' in gradle and 'versionName = "0.1.0-stable"' in gradle
release_request=(root/"ops/beta-release-request.json").read_text()
assert '"version_name": "0.4.2-beta.106"' in release_request and '"version_code": 112' in release_request
assert 'versionCode = 112' in gradle and 'versionName = "0.4.2-beta.106"' in gradle
print("document_management_contract=PASS")
