#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ops = (ROOT / "app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt").read_text(encoding="utf-8")
gas = (ROOT / "google-apps-script/PICK_PACK_API.gs").read_text(encoding="utf-8")
service = (ROOT / "service/src/mobile_hotfix.ts").read_text(encoding="utf-8")
android = "\n".join(
    p.read_text(encoding="utf-8", errors="ignore")
    for p in (ROOT / "app/src/main/java").rglob("*.kt")
)

# PDA-SOURCE-MASTER-001 — version-independent semantic guard.
# Android must expose/persist the source while preserving the PDA identity.
assert 'add("Nguồn PDA",sourceSp)' in ops
assert 'm.put("Seri PDA",key).put("5 số cuối Seri",last).put("Nguồn",source)' in ops
assert '.put("resource_id",key)' in ops

# Canonical source catalog must remain represented in Android source/config.
for source in ("1291", "1386", "1368", "1399", "Inbound", "Outbound"):
    assert source in android, source

# GAS and Service round-trip the same source field instead of dropping it.
assert "source:r['Nguồn']||''" in gas
assert 'source:String(m["Nguồn"]||m["source"]||"")' in service

print("PDA_SOURCE_MASTER_INVARIANT_CONTRACT_PASS")
