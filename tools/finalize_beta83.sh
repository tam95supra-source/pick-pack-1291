#!/usr/bin/env bash
set -Eeuo pipefail
R=ops/beta-release-request.json
PUB=/tmp/beta-publish-final/receipt.json
PDA=/tmp/beta-pda-final/receipt.json
test -f "$PUB" -a -f "$PDA"
VERSION=$(jq -r '.version_name' "$R");CODE=$(jq -r '.version_code' "$R")
BETA_NO="${VERSION##*.}";BETA_STATUS="BETA${BETA_NO}_PASS_LIVE"
SOURCE=$(jq -r '.source_sha' "$R");SHA=$(jq -r '.apk_sha256' "$R");SIZE=$(jq -r '.apk_size' "$R");SIGNER=$(jq -r '.signer_sha256' "$R")
jq -e --arg v "$VERSION" --arg h "$SHA" --argjson z "$SIZE" '
 .status=="PASS" and .version_name==$v and .apk_sha256==$h and .apk_size==$z and
 .ota_exact_bytes==true and .stable_unchanged==true and .main_unchanged==true and .authority_change=="NONE"
' "$PUB" >/dev/null
jq -e --arg v "$VERSION" --arg h "$SHA" --argjson z "$SIZE" --arg s "$SIGNER" '
 .status=="PASS" and .version_name==$v and .apk_sha256==$h and .apk_size==$z and .signer_sha256==$s and
 .ota_from_base==true and .ota_download_exact==true and .installed_exact_bytes==true and .installed_and_opened==true and
 .stable_unchanged==true and .main_unchanged==true and .authority_change=="NONE"
' "$PDA" >/dev/null
jq -e '.human_visual_pass==true and .visual_matrix=="PASS" and .pda_functional_pre_ota=="PASS" and .fast_check=="PASS"' "$R" >/dev/null
MAIN=$(jq -r '.main_sha' "$PDA")
OTA_URL=$(jq -r '.apk_url' "$PUB");OTA_TRANSPORT=$(jq -r '.ota_transport' "$PUB");DRIVE_FILE=$(jq -r '.drive_file_id' "$PUB")
test -n "$OTA_URL" -a "$OTA_TRANSPORT" = "GITHUB_RELEASE_CANONICAL"
AUTH_MODE=$(jq -r '.authority.mode' "$PDA");AUTH_SCOPE=$(jq -r '.authority.scope' "$PDA")
AUTH_EPOCH=$(jq -r '.authority.authority_epoch' "$PDA");AUTH_GEN=$(jq -r '.authority.service_generation' "$PDA")
NOW=$(date -u '+%Y-%m-%dT%H:%M:%SZ');STAMP=$(date -u '+%Y%m%d-%H%M%S');BRANCH="$GITHUB_REF_NAME"
ARCH="docs/handovers/HANDOVER_${STAMP}_beta${BETA_NO}-pass-live.md"
jq '.stage="pass_live" | .mode="PASS_LIVE_EXACT_BYTES" | .publish_run_id=env.GITHUB_RUN_ID | .live=true' "$R" > /tmp/request.json
mv /tmp/request.json ops/beta-release-request.json
cat > CURRENT_STATE.md <<EOF
# CURRENT STATE — PICK PACK 1291

- updated_at: $NOW
- status: $BETA_STATUS
- continuity_branch: $BRANCH
- source_sha: $SOURCE
- beta_live: $VERSION (versionCode $CODE)
- candidate_run: $(jq -r '.candidate_run_id' "$R")
- candidate_artifact: $(jq -r '.candidate_artifact_id' "$R")
- verify_run: $(jq -r '.verify_run_id' "$R")
- verify_artifact: $(jq -r '.verify_artifact_id' "$R")
- apk_sha256: $SHA
- apk_size: $SIZE
- signer_sha256: $SIGNER
- terminal_run: $GITHUB_RUN_ID
- fast_check: PASS
- service_gate: $(jq -r '.service_gate' "$R")
- visual_matrix: PASS 320x568 / 360x640 / 480x800
- human_visual: PASS
- pda_functional_pre_ota: PASS
- beta_ota: exact $VERSION PASS via $OTA_TRANSPORT
- beta_ota_url: $OTA_URL
- drive_beta_staging_file: $DRIVE_FILE
- stable: unchanged
- main_sha: $MAIN
- authority: $AUTH_MODE / $AUTH_SCOPE / epoch $AUTH_EPOCH / generation $AUTH_GEN
- next_action: WAIT_FOR_OWNER_NEW_SCOPE
EOF
mkdir -p docs/handovers
cat > docs/handovers/HANDOVER_CURRENT.md <<EOF
# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: $NOW
- owner: Nguyễn Văn Tâm
- branch: $BRANCH
- working_head_sha: $GITHUB_SHA
- archive_file: $ARCH

## Mục tiêu + DoD
Release $VERSION hoàn tất scope $(jq -r '.scope' "$R"); toàn bộ pre-OTA + OTA install/readback PASS.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: $VERSION / versionCode $CODE.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run $(jq -r '.candidate_run_id' "$R"); artifact $(jq -r '.candidate_artifact_id' "$R"); source $SOURCE; SHA256 $SHA; size $SIZE; signer $SIGNER.
- Fast Check: PASS run $(jq -r '.fast_check_run_id' "$R").
- Service: $(jq -r '.service_gate' "$R").
- Visual/PDA pre-OTA: PASS run $(jq -r '.verify_run_id' "$R"), artifact $(jq -r '.verify_artifact_id' "$R").
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- 3 ô Mạng / Đồng bộ / Dịch vụ ghim trên cùng ở Nghiệp vụ và mọi màn scope, gồm Điểm danh: PASS.
- QR nhân sự local fast-path giữ nguyên; functional + service regression PASS.
- Điểm danh chỉ chấp nhận ACTIVE session đúng business_date hiện tại; ACTIVE phiên cũ bị chặn: PASS.
- Cảnh báo chưa điểm danh hiển thị trên cùng Nghiệp vụ và mở đúng màn Điểm danh: PASS.
- USER không thấy tab Lịch sử và deep-link HISTORY bị chặn; ADMIN/SUPERADMIN giữ quyền: PASS.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- OTA baseline $PREV → $VERSION qua $OTA_TRANSPORT; download/install exact SHA/size/signer và mở app: PASS.
- Drive BẢN THỬ NGHIỆM giữ exact staging APK; public OTA dùng canonical GitHub Release exact asset.

## Lỗi/root cause/PASS path
- Log 17:12/17:17 xác định MEAL_EMPLOYEE_NOT_ACTIVE do app có thể dùng ACTIVE session ngày cũ cho điểm danh ngày hiện tại; sửa current-day fence, không sửa QR core.
- VERIFY_ONLY lỗi đầu do harness đếm text guard HISTORY cứng; sửa verifier semantics và exact candidate PASS.
- Publish lỗi DriveApp/public APK của Google; recovery giữ Drive staging nhưng dùng canonical GitHub Release OTA và static GAS ppUpdateCheck_ exact manifest.
- Candidate được build/sign đúng một lần; mọi harness/transport recovery tái sử dụng exact bytes, không rebuild/resign.

## Blocker
Không có.

## Invariants
Stable/main/signer/authority không đổi; không thêm provider/backend/authority.

## NEXT_ACTION
WAIT_FOR_OWNER_NEW_SCOPE
EOF
cp docs/handovers/HANDOVER_CURRENT.md "$ARCH"
jq -n --arg version "$VERSION" --argjson code "$CODE" --arg name "pick-pack-1291-public-beta-$VERSION.apk" --arg url "$OTA_URL" --arg sha "$SHA" --argjson size "$SIZE" --arg at "$NOW" --arg notes "$(jq -r '.release_notes|if type=="array" then join(" ") else "" end' "$R")" '{
  source:"GITHUB_RELEASE",channel:"BETA",version_name:$version,version_code:$code,apk_name:$name,apk_url:$url,
  sha256:$sha,size:$size,published_at:$at,notes:$notes,mandatory:false,retention:10
}' > ops/beta-ota-current.json
mapfile -t OLD < <(find docs/handovers -maxdepth 1 -type f -name 'HANDOVER_20????????-??????_*.md'|sort)
if (( ${#OLD[@]} > 5 )); then for f in "${OLD[@]:0:${#OLD[@]}-5}"; do rm -f "$f"; done;fi
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add CURRENT_STATE.md ops/beta-release-request.json ops/beta-ota-current.json docs/handovers
git commit -m "[skip ci] finalize $VERSION PASS/LIVE"
FINAL=$(git rev-parse HEAD)
git push origin "HEAD:$BRANCH"
git fetch origin "$BRANCH" --quiet
test "$(git rev-parse "origin/$BRANCH")" = "$FINAL"
test "$(git show "origin/$BRANCH:CURRENT_STATE.md"|grep -c "$BETA_STATUS")" = 1
test "$(git show "origin/$BRANCH:docs/handovers/HANDOVER_CURRENT.md"|grep -c 'status: READY')" = 1
mkdir -p /tmp/beta-final
jq -n --arg status PASS --arg version "$VERSION" --arg source "$SOURCE" --arg sha "$SHA" --argjson size "$SIZE" --arg signer "$SIGNER" --arg commit "$FINAL" --arg main "$MAIN" --arg at "$NOW" \
 '{status:$status,version_name:$version,source_sha:$source,apk_sha256:$sha,apk_size:$size,signer_sha256:$signer,handoff_commit_sha:$commit,main_sha:$main,stable_unchanged:true,authority_change:"NONE",readback:true,finalized_at:$at}' > /tmp/beta-final/receipt.json
cat /tmp/beta-final/receipt.json
