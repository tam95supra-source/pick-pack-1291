#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ops = (ROOT / "app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt").read_text(encoding="utf-8")
gas = (ROOT / "google-apps-script/PICK_PACK_API.gs").read_text(encoding="utf-8")
service = (ROOT / "service/src/mobile_hotfix.ts").read_text(encoding="utf-8")

# PDA-SOURCE-MASTER-001 — version-independent semantic guard.
# Android must expose/persist the source while preserving the PDA identity.
assert 'add("Nguồn PDA",sourceSp)' in ops
assert 'm.put("Seri PDA",key).put("5 số cuối Seri",last).put("Nguồn",source)' in ops
assert '.put("resource_id",key)' in ops
assert 'val existingSource=meta.optString("Nguồn").ifBlank{existing?.optString("source").orEmpty()}' in ops

# The allowed source catalog is dynamic master data, not an Android hardcoded business rule.
# Guard the canonical namespace/read path and that the UI consumes those returned values.
assert 'val ns="DANH SÁCH PDA_Nguồn"' in ops
assert 'if(out.isEmpty())out.addAll(catalogValues(ns))' in ops
assert 'val sourceOptions=mutableListOf("—").apply{addAll(resourcePdaSourceValues(catalogs))}' in ops

# GAS and Service round-trip the same source field instead of dropping it.
assert "source:r['Nguồn']||''" in gas
assert 'source:String(m["Nguồn"]||m["source"]||"")' in service

print("PDA_SOURCE_MASTER_INVARIANT_CONTRACT_PASS")
