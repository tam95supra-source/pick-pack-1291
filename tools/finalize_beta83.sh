#!/usr/bin/env bash
set -Eeuo pipefail

R=ops/beta-release-request.json
PUB=/tmp/beta-publish-final/receipt.json
PDA=/tmp/beta-pda-final/receipt.json
test -f "$PUB" -a -f "$PDA"

VERSION=$(jq -r '.version_name' "$R")
CODE=$(jq -r '.version_code' "$R")
PKG=$(jq -r '.package' "$R")
PREV=$(jq -r '.base_version' "$R")
BETA_NO="${VERSION##*.}"
BETA_STATUS="BETA${BETA_NO}_PASS_LIVE"
SOURCE=$(jq -r '.source_sha' "$R")
SHA=$(jq -r '.apk_sha256' "$R")
SIZE=$(jq -r '.apk_size' "$R")
SIGNER=$(jq -r '.signer_sha256' "$R")

jq -e --arg v "$VERSION" --arg p "$PKG" --arg h "$SHA" --argjson z "$SIZE" '
  .status=="PASS" and .version_name==$v and .package==$p and .apk_sha256==$h and .apk_size==$z and
  .ota_exact_bytes==true and .ota_transport=="GITHUB_RELEASE" and .google_drive_apk=="FORBIDDEN" and
  .stable_unchanged==true and .main_unchanged==true and .authority_change=="NONE"
' "$PUB" >/dev/null

jq -e --arg v "$VERSION" --arg p "$PKG" --arg h "$SHA" --argjson z "$SIZE" --arg s "$SIGNER" '
  .status=="PASS" and .version_name==$v and .package==$p and .apk_sha256==$h and .apk_size==$z and .signer_sha256==$s and
  .ota_transport=="GITHUB_RELEASE" and .google_drive_apk=="FORBIDDEN" and
  .ota_from_base==true and .ota_download_exact==true and .installed_exact_bytes==true and .installed_and_opened==true and
  .stable_unchanged==true and .main_unchanged==true and .authority_change=="NONE"
' "$PDA" >/dev/null

jq -e '.human_visual_pass==true and .visual_matrix=="PASS" and .pda_functional_pre_ota=="PASS" and .fast_check=="PASS" and
       .apk_transport=="GITHUB_RELEASE_ONLY" and .google_drive_apk=="FORBIDDEN"' "$R" >/dev/null

MAIN=$(jq -r '.main_sha' "$PDA")
OTA_URL=$(jq -r '.apk_url' "$PUB")
OTA_TRANSPORT=$(jq -r '.ota_transport' "$PUB")
[[ "$OTA_URL" == https://github.com/*/releases/download/* ]]
test "$OTA_TRANSPORT" = "GITHUB_RELEASE"

AUTH_MODE=$(jq -r '.authority.mode' "$PDA")
AUTH_SCOPE=$(jq -r '.authority.scope' "$PDA")
AUTH_EPOCH=$(jq -r '.authority.authority_epoch' "$PDA")
AUTH_GEN=$(jq -r '.authority.service_generation' "$PDA")
BRANCH="$GITHUB_REF_NAME"
CANDIDATE_SOURCE=$(jq -r '.candidate_source_sha // .source_sha' "$R")
git fetch origin "$BRANCH" --quiet
git diff --quiet "$SOURCE" "origin/$BRANCH" -- service google-apps-script
git diff --quiet "$CANDIDATE_SOURCE" "origin/$BRANCH" -- app
git rebase "origin/$BRANCH"
jq -e --arg v "$VERSION" --arg p "$PKG" --arg source "$SOURCE" --arg candidate "$CANDIDATE_SOURCE" --arg h "$SHA" '
  .stage=="PUBLISH" and .version_name==$v and .package==$p and .source_sha==$source and
  .candidate_source_sha==$candidate and .apk_sha256==$h and .candidate_locked==true and
  .stable_publish=="FORBIDDEN" and .authority_change=="NONE"
' "$R" >/dev/null

NOW=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
STAMP=$(date -u '+%Y%m%d-%H%M%S')
ARCH="docs/handovers/HANDOVER_${STAMP}_beta${BETA_NO}-pass-live.md"

jq '.stage="pass_live" | .mode="PASS_LIVE_EXACT_BYTES_GITHUB_RELEASE_ONLY" | .publish_run_id=env.GITHUB_RUN_ID |
    .live=true | .technical_pass_status="PASS" | .owner_acceptance="PENDING" |
    .ota_readback_status="PASS" | .ota_readback_run_id=(env.GITHUB_RUN_ID|tonumber) |
    .apk_transport="GITHUB_RELEASE_ONLY" | .google_drive_apk="FORBIDDEN" |
    .next_action="WAIT_FOR_OWNER_ACCEPTANCE_NUMBERED_CHECKLIST"' "$R" > /tmp/request.json
mv /tmp/request.json ops/beta-release-request.json

cat > CURRENT_STATE.md <<EOF
# CURRENT STATE — PICK PACK 1291

- updated_at: $NOW
- status: $BETA_STATUS
- continuity_branch: $BRANCH
- source_sha: $SOURCE
- beta_live: $VERSION (versionCode $CODE)
- package: $PKG
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
- beta_ota: exact $VERSION PASS via GitHub Release
- beta_ota_url: $OTA_URL
- apk_transport: GITHUB_RELEASE_ONLY
- google_drive_apk: FORBIDDEN
- stable: unchanged
- main_sha: $MAIN
- authority: $AUTH_MODE / $AUTH_SCOPE / epoch $AUTH_EPOCH / generation $AUTH_GEN
- next_action: WAIT_FOR_OWNER_ACCEPTANCE_NUMBERED_CHECKLIST
EOF

mkdir -p docs/handovers
cat > docs/handovers/HANDOVER_CURRENT.md <<EOF
# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: $NOW
- owner: Nguyễn Văn Tâm
- branch: $BRANCH
- release_trigger_sha: $GITHUB_SHA
- archive_file: $ARCH

## Mục tiêu + DoD
Release $VERSION Technical PASS/LIVE cho scope $(jq -r '.scope' "$R"); toàn bộ pre-OTA + GitHub Release exact bytes + OTA install/readback + finalizer PASS; OWNER acceptance còn PENDING.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: $VERSION / versionCode $CODE / package $PKG.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run $(jq -r '.candidate_run_id' "$R"); artifact $(jq -r '.candidate_artifact_id' "$R"); source $SOURCE; SHA256 $SHA; size $SIZE; signer $SIGNER.
- Fast Check: PASS run $(jq -r '.fast_check_run_id' "$R").
- Service: $(jq -r '.service_gate' "$R").
- Visual/PDA pre-OTA: PASS run $(jq -r '.verify_run_id' "$R"), artifact $(jq -r '.verify_artifact_id' "$R").
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- 3 ô Mạng / Đồng bộ / Dịch vụ ghim trên cùng ở mọi màn scope: PASS.
- QR nhân sự local fast-path giữ nguyên; functional + service regression PASS.
- Điểm danh chỉ chấp nhận ACTIVE session đúng business_date hiện tại; ACTIVE phiên cũ bị chặn: PASS.
- Cảnh báo chưa điểm danh ở trên cùng Nghiệp vụ; USER không thấy/deep-link được Lịch sử: PASS.
- GitHub Release asset exact bytes khớp candidate SHA256/size; OTA tải trực tiếp từ GitHub Release: PASS.
- OTA $PREV → $VERSION: download/install exact SHA/size/version/package/signer và mở app: PASS.
- Google Drive APK: FORBIDDEN từ Beta97; không backup/staging/mirror/upload/download/rollback/phân phối APK qua Drive.

## Lỗi/root cause/PASS path
- VERIFY_ONLY harness cũ đếm text guard HISTORY cứng; sửa verifier semantics và exact candidate PASS.
- Publish cũ có luồng Drive APK song song và DriveApp/public APK bị Google chặn; loại bỏ toàn bộ Drive dependency khỏi Beta APK pipeline.
- Canonical Beta APK path: GitHub Actions exact candidate → GitHub Release exact asset → GAS manifest GitHub URL → OTA install/readback → finalizer.
- Rollback canonical: exact LIVE baseline GitHub Actions/GitHub Release → atomic Beta manifest restore; không dùng Drive APK.
- Candidate được build/sign đúng một lần; mọi recovery dùng exact locked bytes, không rebuild/resign.

## Blocker
Không có.

## Invariants
- Stable/main/signer/authority không đổi.
- APK Beta release/OTA/rollback = GITHUB_RELEASE_ONLY.
- Google Drive không được dùng cho APK; GSheet/GAS nghiệp vụ không bị xóa/thay authority.

## NEXT_ACTION
WAIT_FOR_OWNER_ACCEPTANCE_NUMBERED_CHECKLIST
EOF

cp docs/handovers/HANDOVER_CURRENT.md "$ARCH"

jq -n --arg version "$VERSION" --argjson code "$CODE" --arg package "$PKG" \
  --arg name "pick-pack-1291-public-beta-$VERSION.apk" --arg url "$OTA_URL" --arg sha "$SHA" \
  --argjson size "$SIZE" --arg at "$NOW" \
  --arg notes "$(jq -r '.release_notes|if type=="array" then join(" ") else "" end' "$R")" '{
    source:"GITHUB_RELEASE",channel:"BETA",version_name:$version,version_code:$code,package:$package,
    apk_name:$name,apk_url:$url,sha256:$sha,size:$size,published_at:$at,notes:$notes,
    mandatory:false,retention:10,google_drive_apk:"FORBIDDEN"
  }' > ops/beta-ota-current.json

mapfile -t OLD < <(find docs/handovers -maxdepth 1 -type f -name 'HANDOVER_20????????-??????_*.md'|sort)
if (( ${#OLD[@]} > 5 )); then
  for file in "${OLD[@]:0:${#OLD[@]}-5}"; do rm -f "$file"; done
fi

git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add CURRENT_STATE.md ops/beta-release-request.json ops/beta-ota-current.json docs/handovers
git commit -m "[skip ci] finalize $VERSION PASS/LIVE GitHub Release only"
FINAL=$(git rev-parse HEAD)
git push origin "HEAD:$BRANCH"
git fetch origin "$BRANCH" --quiet
test "$(git rev-parse "origin/$BRANCH")" = "$FINAL"
test "$(git show "origin/$BRANCH:CURRENT_STATE.md"|grep -c "$BETA_STATUS")" = 1
test "$(git show "origin/$BRANCH:CURRENT_STATE.md"|grep -c 'google_drive_apk: FORBIDDEN')" = 1
test "$(git show "origin/$BRANCH:docs/handovers/HANDOVER_CURRENT.md"|grep -c 'status: READY')" = 1
test "$(git show "origin/$BRANCH:ops/beta-ota-current.json"|jq -r '.source')" = "GITHUB_RELEASE"
test "$(git show "origin/$BRANCH:ops/beta-ota-current.json"|jq -r '.google_drive_apk')" = "FORBIDDEN"

mkdir -p /tmp/beta-final
jq -n --arg status PASS --arg version "$VERSION" --argjson code "$CODE" --arg package "$PKG" \
  --arg source "$SOURCE" --arg sha "$SHA" --argjson size "$SIZE" --arg signer "$SIGNER" \
  --arg url "$OTA_URL" --arg commit "$FINAL" --arg main "$MAIN" --arg at "$NOW" '{
    status:$status,version_name:$version,version_code:$code,package:$package,source_sha:$source,
    apk_sha256:$sha,apk_size:$size,signer_sha256:$signer,apk_url:$url,
    ota_transport:"GITHUB_RELEASE",google_drive_apk:"FORBIDDEN",
    handoff_commit_sha:$commit,main_sha:$main,stable_unchanged:true,authority_change:"NONE",
    readback:true,finalized_at:$at
  }' > /tmp/beta-final/receipt.json
cat /tmp/beta-final/receipt.json
