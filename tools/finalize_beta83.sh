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
- service_gate: $(jq -r '.service_gate_inherited' "$R")
- visual_matrix: PASS 320x568 / 360x640 / 480x800
- human_visual: PASS
- pda_functional_pre_ota: PASS
- beta_ota: exact $VERSION PASS
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
- Service: $(jq -r '.service_gate_inherited' "$R").
- Visual/PDA pre-OTA: PASS run $(jq -r '.verify_run_id' "$R"), artifact $(jq -r '.verify_artifact_id' "$R").
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- 3 ô rà soát nhân sự nằm trên ô quét MNV: PASS.
- Thứ tự công việc: Vị trí → User Pick → PDA → Bàn Pack → User Pack: PASS.
- RESOURCE_CHANGE hiển thị dữ liệu Trước cập nhật / Sau cập nhật khi service có snapshot; bản ghi cũ fallback rõ ràng: PASS.
- Diễn biến trong ca sắp xếp mới nhất → cũ nhất: PASS.
- Sửa/xóa và các thao tác chỉnh sửa được gate bằng mật khẩu HHmm hiện tại theo Asia/Ho_Chi_Minh: PASS.
- SUPERADMIN thực tế được phép dùng thêm mật khẩu tài khoản cố định qua login verification; không hardcode secret: PASS.
- OTA baseline → $VERSION exact bytes, SHA/size/signer/version và mở app: PASS.

## Lỗi/root cause/PASS path
- Scope Beta86: bỏ polling UI 750 ms, chuyển refresh realtime sang event-driven/partial; không đổi backend/authority.
- Candidate được build/sign đúng một lần từ exact source đã khóa; release harness nhận version từ request.
- Fast Check exact source PASS; verifier stale HH:mm đã được sửa sang HHmm và chạy VERIFY_ONLY trên exact locked candidate.
- Không rebuild/resign candidate sau khi lock.

## Blocker
Không có.

## Invariants
Stable/main/signer/authority không đổi; không thêm provider/backend/authority.

## NEXT_ACTION
WAIT_FOR_OWNER_NEW_SCOPE
EOF
cp docs/handovers/HANDOVER_CURRENT.md "$ARCH"
mapfile -t OLD < <(find docs/handovers -maxdepth 1 -type f -name 'HANDOVER_20????????-??????_*.md'|sort)
if (( ${#OLD[@]} > 5 )); then for f in "${OLD[@]:0:${#OLD[@]}-5}"; do rm -f "$f"; done;fi
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add CURRENT_STATE.md ops/beta-release-request.json docs/handovers
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
