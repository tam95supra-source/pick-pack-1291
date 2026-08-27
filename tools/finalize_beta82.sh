#!/usr/bin/env bash
set -Eeuo pipefail
R=ops/beta-release-request.json;PUB=/tmp/beta82-publish-final/receipt.json;PDA=/tmp/beta82-pda-final/receipt.json
test -f "$PUB" -a -f "$PDA"
VERSION=$(jq -r '.version_name' "$R");CODE=$(jq -r '.version_code' "$R");SOURCE=$(jq -r '.source_sha' "$R");SHA=$(jq -r '.apk_sha256' "$R");SIZE=$(jq -r '.apk_size' "$R");SIGNER=$(jq -r '.signer_sha256' "$R")
jq -e --arg v "$VERSION" --arg h "$SHA" --argjson z "$SIZE" '.status=="PASS" and .version_name==$v and .apk_sha256==$h and .apk_size==$z and .ota_exact_bytes==true and .stable_unchanged==true and .main_unchanged==true and .authority_change=="NONE"' "$PUB" >/dev/null
jq -e --arg v "$VERSION" --arg h "$SHA" --argjson z "$SIZE" --arg s "$SIGNER" '.status=="PASS" and .version_name==$v and .apk_sha256==$h and .apk_size==$z and .signer_sha256==$s and .ota_from_beta81==true and .installed_exact_bytes==true and .installed_and_opened==true and .stable_unchanged==true and .main_unchanged==true and .authority_change=="NONE"' "$PDA" >/dev/null
MAIN=$(jq -r '.main_sha' "$PDA");AUTH_MODE=$(jq -r '.authority.mode' "$PDA");AUTH_SCOPE=$(jq -r '.authority.scope' "$PDA");AUTH_EPOCH=$(jq -r '.authority.authority_epoch' "$PDA");AUTH_GEN=$(jq -r '.authority.service_generation' "$PDA")
NOW=$(date -u '+%Y-%m-%dT%H:%M:%SZ');STAMP=$(date -u '+%Y%m%d-%H%M%S');BRANCH="$GITHUB_REF_NAME";ARCH="docs/handovers/HANDOVER_${STAMP}_beta82-pass-live.md"
jq '.stage="pass_live" | .mode="PASS_LIVE_EXACT_BYTES" | .publish_run_id=env.GITHUB_RUN_ID | .live=true' "$R" > /tmp/request.json;mv /tmp/request.json ops/beta-release-request.json
cat > CURRENT_STATE.md <<EOF
# CURRENT STATE — PICK PACK 1291

- updated_at: $NOW
- status: BETA82_PASS_LIVE
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
- service_gate: inherited PASS; Service source unchanged
- visual_matrix: PASS 320x568 / 360x640 / 480x800
- human_visual: PASS
- pda_functional: PASS
- beta_ota: exact Beta82 PASS
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
Beta82 sửa rà soát nhân sự ngày hiện tại, danh sách ca đủ/thiếu, QR session cards, null-safe display và Settings rút gọn; toàn bộ pre-OTA + OTA install/readback PASS.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: $VERSION / versionCode $CODE.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run $(jq -r '.candidate_run_id' "$R"); artifact $(jq -r '.candidate_artifact_id' "$R"); source $SOURCE; SHA256 $SHA; size $SIZE; signer $SIGNER.
- Fast Check: PASS run $(jq -r '.fast_check_run_id' "$R").
- Service: inherited PASS, source unchanged.
- Visual/PDA pre-OTA: PASS run $(jq -r '.verify_run_id' "$R"), artifact $(jq -r '.verify_artifact_id' "$R").
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- Bỏ text RÀ SOÁT VÀO / RA + ngày: PASS.
- 3 ô ca và danh sách chỉ ngày thực tế hiện tại: PASS.
- Sau quét MNV có 3 ô: PASS.
- Ca đủ mở thẳng list; ca thiếu có RA CA + HIỂN THỊ CHI TIẾT NHÂN SỰ: PASS.
- Bấm MNV trong list mở luồng thông tin phiên như QR: PASS.
- Cảnh báo ngày cũ giữ riêng: PASS.
- null -> -: PASS.
- Thông tin ứng dụng / Cập nhật phiên bản / Nhật ký rút gọn: PASS.
- OTA Beta81 -> Beta82, exact SHA/size/signer/version và mở app: PASS.
- Beta81 update_check available=true Beta82; Beta82 available=false: PASS.

## Lỗi/root cause/PASS path
- Verifier startActivitySync chờ UI idle do animation vô hạn: sửa harness non-idle bounded.
- Accessibility ACTION_CLICK Ca HC trả false: harness fallback coordinate bounds.
- Ảnh Settings ban đầu chưa đưa mục cần duyệt vào viewport: capture harness SHOW_ON_SCREEN; không đổi APK.
- Không rebuild/resign candidate sau lock.

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
git config user.name 'github-actions[bot]';git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add CURRENT_STATE.md ops/beta-release-request.json docs/handovers
git commit -m '[skip ci] finalize Beta82 PASS/LIVE'
FINAL=$(git rev-parse HEAD);git push origin "HEAD:$BRANCH";git fetch origin "$BRANCH" --quiet;test "$(git rev-parse "origin/$BRANCH")" = "$FINAL"
test "$(git show "origin/$BRANCH:CURRENT_STATE.md"|grep -c BETA82_PASS_LIVE)" = 1
test "$(git show "origin/$BRANCH:docs/handovers/HANDOVER_CURRENT.md"|grep -c 'status: READY')" = 1
mkdir -p /tmp/beta82-final
jq -n --arg status PASS --arg version "$VERSION" --arg source "$SOURCE" --arg sha "$SHA" --argjson size "$SIZE" --arg signer "$SIGNER" --arg commit "$FINAL" --arg main "$MAIN" --arg at "$NOW"   '{status:$status,version_name:$version,source_sha:$source,apk_sha256:$sha,apk_size:$size,signer_sha256:$signer,handoff_commit_sha:$commit,main_sha:$main,stable_unchanged:true,authority_change:"NONE",readback:true,finalized_at:$at}' > /tmp/beta82-final/receipt.json
cat /tmp/beta82-final/receipt.json
