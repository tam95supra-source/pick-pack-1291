# CURRENT STATE — PICK PACK 1291

- updated_at: 2026-08-30T12:00:45Z
- status: BETA101_PASS_LIVE
- continuity_branch: release/beta97-qr-meal-alert-role-20260829
- source_sha: d918de9fe0b132b60c5c4f515395e541da47daf2
- beta_live: 0.4.2-beta.101 (versionCode 107)
- package: vn.pickpack1291.app.beta.publicbeta
- candidate_run: 33307618230
- candidate_artifact: 9731018588
- verify_run: 33309271079
- verify_artifact: 9731526178
- apk_sha256: e29eab9402d847ac5f141f2a51ee164b235d46c3a075a46df4dff69ced0c3097
- apk_size: 13577205
- signer_sha256: d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e
- terminal_run: 33310230934
- fast_check: PASS
- service_gate: PASS_INHERITED_JOB_99202629701_EXACT_SERVICE_SOURCE_UNCHANGED
- visual_matrix: PASS 320x568 / 360x640 / 480x800
- human_visual: PASS
- pda_functional_pre_ota: PASS
- beta_ota: exact 0.4.2-beta.101 PASS via GitHub Release
- beta_ota_url: https://github.com/tam95supra-source/pick-pack-1291/releases/download/v0.4.2-beta.101-publicbeta/pick-pack-1291-public-beta-0.4.2-beta.101.apk
- apk_transport: GITHUB_RELEASE_ONLY
- google_drive_apk: FORBIDDEN
- stable: unchanged
- main_sha: 021dac5c6932b3ac5c60ce8fdba562ddf3d9688f
- authority: SERVICE_PRIMARY / PRODUCTION / epoch 9 / generation m2-prod-reset-20260823-001
- next_action: WAIT_FOR_OWNER_BETA101_ITEM_6_RETEST_AFTER_GAS206

- publish_verifier_fast_check: PASS run 33310187636 (receipt-driven screenshot evidence; legacy 26 + Beta101 35 + negative regressions)
- owner_acceptance_item_6: NOT_OK_2026-08-30_RETEST_REQUIRED

- owner_manual_resilience_log: manual-20260830-201252-c8f14b0b-884c-4be0-ae4c-6fb45b299c7f.json
- gas_resilience_readback_before: FAIL run 33313877854; deployment 205 missing emergency-ledger + LAN routes/functions
- gas_resilience_repair: PASS run 33314072135; deployment 205 -> 206; ppUpdateCheck unchanged; authority change NONE
- gas_resilience_readback_after: PASS run 33314115931
- gas_resilience_deployment: 206
- release_pipeline_gas_contract_guard: PASS Fast Check run 33314181358
- resilience_test_fidelity: NORMAL service = live path; Google fallback = safe live path drill after GAS206; device/offline/local cases = isolated simulation + real recovery, not physical outage; LAN = requires real active multi-device topology
