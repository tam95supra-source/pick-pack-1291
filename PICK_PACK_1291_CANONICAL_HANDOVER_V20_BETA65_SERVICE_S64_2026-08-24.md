# PICK PACK 1291 — CANONICAL HANDOVER V20

**Status:** Beta65 FINAL RELEASE PASS / Service S64 production truth  
**Date:** 2026-08-24 (+07:00)  
**Supersedes current-state V19 for live release state.** Historical V19 remains evidence, but V20 is the current canonical continuation point.

---

## 1. PRECEDENCE AND EXECUTION RULES

Apply precedence in this order:

1. Newest direct OWNER instruction.
2. This V20 canonical handover.
3. Fresh live evidence.
4. Immutable release/deploy receipts, exact hashes and artifact identity.
5. Current repository documentation after staleness check.
6. V19 as historical predecessor.
7. Older evidence only for history/rollback.

Operational execution rules remain locked:

- Do not stop for ordinary technical failures. Diagnose, fix, retry/resume and use an authorized alternate path.
- Ask OWNER only for a genuinely missing permission/manual action with no authorized alternate, a paid/destructive action, Stable/signer change, or unresolved business-rule conflict.
- Fresh-read before risky mutation.
- Do not repeat a PASS stage when exact source/artifact/hash/live inputs still match.
- Once one exact signed candidate is locked, downstream Drive/GAS/OTA/GitHub failures must reuse the exact bytes. Do not rebuild/resign merely to bypass transport.
- PDA physical acceptance remains OWNER-managed and is not a release blocker.

---

## 2. CURRENT PUBLIC BETA — BETA65 FINAL

Beta65 is the current released Public Beta.

- versionName: `0.4.2-beta.65`
- versionCode: `71`
- package: `vn.pickpack1291.app.beta.publicbeta`
- exact product source SHA: `1e8fb8255f26ad58c9719d99c27c08ef5d597cbf`
- source validation run: `32697993454` — PASS
- signed run: `32701275784`
- signed job: `97353121085`
- immutable Actions artifact ID: `9510636863`
- Actions artifact digest: `sha256:ee95fb681dd6f49d7290cb4eb989ea550d22c99290dd49005b7cbe44451bce92`
- APK: `pick-pack-1291-public-beta-0.4.2-beta.65.apk`
- exact APK SHA256: `be728cd8d20d6033becbfb169db89565f6078a681d47bc9079f98f9f5758e1da`
- exact APK byte size: `13097861`
- signer SHA256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`

Important evidence correction:

- An earlier temporary evidence lock used a wrong `be728eea...` value.
- Direct download of artifact `9510636863`, its internal receipt and `SHA256SUMS-0.4.2-beta.65.txt` proved the actual APK hash is `be728cd8...e1da` above.
- This was an evidence correction only. The immutable APK was not rebuilt or resigned.

Next Android source after this release MUST be **Beta66+ / VC72+**.

---

## 3. GOOGLE DRIVE / GAS / OTA — FINAL PASS

Google Drive Beta publication:

- Beta folder ID: `1WMXI-8-Z1mbY2v11noYFHe_eoMNiNZXg`
- Beta65 APK file ID: `1F2Xu0PQ7tiIWcNDlz9yUTsXBee6RWP39`
- Beta65 checksum file ID: `12iSOQ-AwToKY74ylGa4Wb5iVnQXdF8RC`
- public Drive exact-byte readback: PASS
- exact readback SHA256: `be728cd8d20d6033becbfb169db89565f6078a681d47bc9079f98f9f5758e1da`
- exact readback size: `13097861`

GAS endpoint:

`https://script.google.com/macros/s/AKfycbzbEoGfbNg6s2HnP-gUpcBJ7mMIkVBtYuQKMndb9seDV2c55lQwSUO1GZ-LtQ2CxMCauA/exec`

Final OTA gates:

- GAS BETA target = `0.4.2-beta.65`: PASS
- GAS OTA source = `GOOGLE_DRIVE`: PASS
- Beta64 -> Beta65 update available: PASS
- OTA downloaded bytes match exact Beta65 SHA/size: PASS
- Beta65 -> Beta65 self no-update: PASS
- Stable self no-update: PASS
- Stable route before/after unchanged: PASS

Google OAuth lesson remains canonical:

- An Actions OAuth token may exchange successfully yet lack Drive API scope and return `ACCESS_TOKEN_SCOPE_INSUFFICIENT`.
- This is not automatically an OWNER blocker when the authorized Google Drive connector is available.
- After candidate lock, use the connector/alternate authorized transport with the same exact candidate bytes rather than rebuilding.
- Large Drive APK anonymous downloads may return the virus-warning confirmation page; verifier must follow the `download-form` confirmation flow before hashing actual APK bytes.

---

## 4. GITHUB PRERELEASE BACKUP — FINAL PASS

GitHub prerelease:

- tag: `v0.4.2-beta.65-publicbeta`
- GitHub release ID: `375548474`
- prerelease exact APK readback: PASS
- prerelease APK SHA256: `be728cd8d20d6033becbfb169db89565f6078a681d47bc9079f98f9f5758e1da`
- prerelease APK size: `13097861`

### Release-carrier exception

The current GitHub App token could not create the release tag directly on product source `1e8fb825...` because that product commit contains a workflow change and the token does not have GitHub `workflows` permission. GitHub rejected direct tag creation with:

`refusing to allow a GitHub App to create or update workflow ... without workflows permission`

This was solved without altering product source or APK bytes:

- release-carrier branch: `release-carrier/beta65-20260824`
- metadata-only release carrier SHA: `9692bf0631a58b3949427c91d1286837d4d008af`
- tag target = release carrier SHA
- signed APK metadata and GitHub release notes pin the real product source SHA `1e8fb825...`
- immutable artifact ID/hash/signer/package/version remain the authoritative product identity.

This release-carrier pattern is a release transport workaround only. It MUST NOT be interpreted as changing Android product source. For future releases, first try the direct product-source tag. Use a metadata carrier only when the same GitHub workflow-permission restriction is freshly proven.

No old release retention/deletion cleanup was run as part of this workaround.

---

## 5. STABLE HARD LOCK — UNCHANGED

Stable remains:

- version: `0.1.0-stable`
- versionCode: `1`
- package: `vn.pickpack1291.app.stable`
- status: `UNTOUCHED`
- publication: `FORBIDDEN` without separate explicit OWNER instruction

Permanent rules:

- Never bump or publish Stable as a shortcut for Beta work.
- Never change/regenerate signer for convenience.
- Never merge release/evidence PRs to Stable/main merely to complete a Beta release.
- Main is not a release scratch branch.
- Never expose signing files, OAuth refresh tokens, admin/service/bridge secrets.

Beta65 final release verification proved Stable isolation and Stable self no-update PASS.

---

## 6. CURRENT SERVICE — S64

Canonical production service endpoints:

- custom domain: `https://pickpack1291.cc.cd`
- compatibility URL: `https://pickpack.1291.workers.dev`
- Worker/service name: `pickpack`

Last proven S64 deployment identity:

- Service S64 source SHA: `11008a747b54bcc80e09ec13fb674be37efd831b`
- Cloudflare version: `78d832e7-bbc6-4d34-8562-19aa32d2493c`
- authority: `SERVICE_PRIMARY / PRODUCTION`
- replication: `HEALTHY`
- pending replication: `0`

The detached historical Worker `pick-pack-1291-service` must not be recreated.

Production authority architecture remains locked:

`Android/Web <-> Service Worker/D1/Event Ledger <-> Google replica/report/DR`

Under `SERVICE_PRIMARY`:

- Service D1/Event Ledger is canonical for operational mutations/history/audit.
- Google remains master/catalog/config authority plus operational replica/report/DR as already approved.
- Ordinary Service timeout/5xx/network failure does NOT authorize direct PDA business writes to Google.
- Google business fallback is legal only through the official control-plane transition to `GOOGLE_FALLBACK` with epoch/generation fencing.
- Event IDs, idempotency and audit remain mandatory.
- No LAN relay/leader redesign and no per-device direct GSheet operational-write redesign is approved.

S63 ownership-order fix must remain preserved under S64:

1. If a resource lease belongs to the current active session, it is valid.
2. If another session holds it, reject as `${type}_IN_USE`.
3. Only if there is no holder and free-list says unavailable, reject `${type}_UNAVAILABLE`.

Do not restore availability-before-same-session-ownership validation.

---

## 7. BETA65 BUSINESS/UI LOGIC THAT MUST NOT REGRESS

### Login

- Full-frame responsive design, constrained by both width and height so the whole designed frame remains visible.
- Vietnam/Supra visual language only from the approved OWNER-derived asset.
- Cultural elements allowed: Vietnam flag, correct Vietnam map, standardized Đông Sơn drum motif, Hồ Gươm/Tháp Rùa, cầu Thê Húc, lotus.
- Do not invent đình/chùa/cổng/other architecture.
- Copyright remains: `Copyright 2026 Supra DC Hưng Yên  -  tamnv2  -  Chuyên viên Pick Pack 1291`.

### Employee scan callback fencing

An async response for an older scanned employee must never reset or overwrite a newer employee currently being viewed/edited. Reset/re-render is legal only when both employee identity and lookup generation still match the initiating context.

This applies to attendance exit/reset and add/edit/delete work callbacks.

### Session timeline

- Prefer exact `session_id` equality whenever available.
- Legacy events without `session_id` may be included only if timestamp falls inside the current session enter-to-exit window.
- Apply the same scope to canonical and local pending/queued events.
- Never build current-session timeline by MNV alone.

### Attendance business date

Session business date follows the entry session:

- Example: enter `05:00 15/08`, exit `03:00 16/08` => belongs to `15/08`.
- A subsequent new entry after that exit belongs to `16/08`, not the old `15/08` session.

### Work display

Derive displayed work from actual recorded resources, not stale `work_choice`:

- Pick iff `pda_serial` or `user_pick` exists.
- Pack iff `pack_table` or `user_pack` exists.
- none => `Làm theo vị trí chính`
- Pick => `Làm theo vị trí chính & Pick`
- Pack => `Làm theo vị trí chính & Pack`
- both => `Làm theo vị trí chính & Pick & Pack`

### Suggestions and Add/Edit freedom

- `Vị trí chính` provides a suggestion for `Vị trí trong ca`; it is not a hard lock.
- Pick provides a Pick suggestion; Pack provides a Pack suggestion.
- Add/Edit must allow changing user/resource freely to otherwise valid options.
- Never lock editing to the previous Pack table, previous location, or only users associated with the old selection.
- User/resource choice depends on the operator action and current session reality; do not impose a false permanent user lock across shifts merely because the same user ID was previously used.

### Mistaken resource issuance

When an issued resource is confirmed as assigned by mistake and has not actually been used, return it to `AVAILABLE` immediately. Do not wait for shift exit.

### User reissue

- Normal Pick/Pack dropdowns contain unused users only.
- `Phát lại user pick` opens a separate used-Pick-user selector.
- `Phát lại user pack` opens a separate used-Pack-user selector.
- Do not merge used users into the normal unused list.
- Only the selected used user is reapplied; preserve duplicate/reissue payload semantics (`duplicate_user`, `PHÁT LẠI USER`).

### Resource/session flexibility

- Session logic supports the approved in-shift work/resource changes without falsely binding Pack User to an old Pack table or binding new selections to the previous resource set.
- User Pack and Pack table are independent business selections except where an explicit current rule validates a real conflict/resource constraint.
- Same-session resource ownership must be accepted before free-list availability checks.

### App information

Display actual app cache size from `cacheDir + codeCacheDir` through the human-readable formatter. Do not hardcode or substitute APK size.

---

## 8. RELEASE PIPELINE / RESUME MODEL

Canonical release stages:

`R0 fresh truth -> R1 pin product source -> R2 business/security/static gates -> R3 compile -> R4 lock one signed candidate -> R5 Service/GAS prerequisites -> R6 Drive exact bytes/readback -> R7 previous->target OTA + self no-update -> R8 Stable isolation -> R9 GitHub prerelease + final health -> R10 receipt + cumulative handover`

Failure rules:

- Before R4, a source/compile defect may require source fix and rebuild.
- After R4, transport/publish failures MUST reuse the immutable candidate and resume at the failed downstream stage.
- Credential/connector/runtime failure requires an alternate authorized path where available.
- Do not turn routine transport failure into an OWNER blocker.

Beta65 completed this model with one immutable candidate. The Google Drive connector and GitHub release-carrier were authorized alternate transport paths; neither changed APK bytes.

---

## 9. CURRENT BRANCH / PR SAFETY MAP

- Product Beta65 branch: `agent/beta65-session-resource-login-parity-20260824`
- Beta65 product/evidence PR #123: do not merge as a Stable/main release shortcut.
- Release carrier: `release-carrier/beta65-20260824`
- CI/evidence base: `ci/beta65-final-release-base-20260824`
- Temporary release/evidence PRs #124 and #125 were closed unmerged.
- PR #126 is release/evidence-only and must be closed unmerged after final handover cleanup.

Evidence/release branches are not product merge authorization.

Do not rewrite shared production history or force-push for cosmetic cleanup.

---

## 10. FINAL BETA65 RELEASE RECEIPT

Canonical receipt path on CI evidence branch:

`ops/BETA65_FINAL_RELEASE_RECEIPT.txt`

Final receipt records:

- exact product source SHA
- exact signed run/job/artifact
- version/package
- exact APK SHA/size/signer
- Drive IDs and readback PASS
- GAS PASS
- Beta64 -> Beta65 OTA PASS
- Beta65 self no-update PASS
- Stable isolation/identity PASS
- GitHub prerelease ID/tag/readback PASS
- final production health PASS
- Stable publication FORBIDDEN
- verdict PASS

GitHub release ID: `375548474`.

---

## 11. FINAL RELEASE STATE

`SOURCE_PASS`
+ `TEST_PASS`
+ `COMPILE_PASS`
+ `SIGNED_ARTIFACT_PASS`
+ `SIGNED_IDENTITY_PASS`
+ `DRIVE_PASS`
+ `DRIVE_READBACK_EXACT_PASS`
+ `GAS_PASS`
+ `OTA_BETA64_TO_BETA65_PASS`
+ `BETA65_SELF_NO_UPDATE_PASS`
+ `STABLE_ISOLATION_PASS`
+ `GITHUB_PRERELEASE_PASS`
+ `FINAL_HEALTH_PASS`
+ `RECEIPT_PASS`
+ `HANDOVER_PASS`

**BETA65 = DONE.**

For the next Android product change, start at **Beta66 / VC72 or later** after fresh-read. Do not reopen Beta65 product bytes for transport cleanup.
