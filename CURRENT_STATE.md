# PICK PACK 1291 — CURRENT STATE

Fresh checkpoint: 2026-08-23 Asia/Ho_Chi_Minh.

- LIVE/GOLDEN: `0.4.2-beta.55` / versionCode `61`.
- Android source restored to the exact pre-Beta56 PR64 base: `fb30b63358e112e74249530ca905702766c03313`.
- Beta package: `vn.pickpack1291.app.beta.publicbeta`.
- OTA behavior: MANUAL ONLY. User must press the update check/update control in the app. No automatic foreground/startup OTA check is allowed.
- Live OTA metadata remains Beta55 and points to GitHub Release `v0.4.2-beta.55-publicbeta`.
- Live Beta55 APK SHA-256: `6428d934a3a86b55c0c3107840e211c6841f82e875b975510174e44e63045c85`.
- Live Beta55 APK size: `13027947` bytes.
- GAS OTA production receipt: manual check PASS, automatic check DISABLED_IN_APP, target self update FALSE, verdict PASS.
- ABANDONED/DENYLIST: `0.4.2-beta.56` / versionCode `62`. Do not release, publish, restore, or use as a baseline. The attempted automatic OTA implementation from PR #64 is explicitly rejected by OWNER.
- Historical ABANDONED/DENYLIST remains: `0.4.2-beta.49` / versionCode `55`; never reuse or publish.
- Stable: `0.1.0-stable` / versionCode `1`, untouched.
- Stabilization branch: `stabilization/beta48-golden-reset-beta50-20260822`.
- Service branch: `agent/service-migration-m2`.
- Protected: do not merge PR #38, PR #52, or PR #63 unless OWNER explicitly changes that decision. Do not touch `main` for this rollback.

Execution rule from this checkpoint: treat Beta55 as the newest approved golden baseline. Any next beta must start from Beta55 and must preserve manual-only OTA unless OWNER explicitly requests a different update mechanism.
