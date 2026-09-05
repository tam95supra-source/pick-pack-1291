#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "tools/beta128_owner_r3_patch.py"


def repair_attendance_boundary(s: str) -> str:
    start_marker = "    # Scheduled time-boundary refresh must bypass the no-op signature because status semantics can change with clock time.\n"
    end_marker = "    write(p, s)\n\n\ndef patch_operations()"
    start = s.find(start_marker)
    end = s.find(end_marker, start)
    if start < 0 or end < 0:
        raise SystemExit(f"BETA128_APPLY_FAIL:attendance-boundary-markers:start={start}:end={end}")
    replacement = '''    # Scheduled time-boundary refresh must bypass the no-op signature because status semantics can change with clock time.\n    s = replace_once(\n        s,\n        '                val nowDay=today()\\n                if(selected.isBefore(nowDay))load(nowDay) else {render();remoteLoad()}',\n        '                val nowDay=today()\\n                lastRenderSignature=""\\n                if(selected.isBefore(nowDay))load(nowDay) else {render();remoteLoad()}',\n        "attendance-boundary-force-render",\n    )\n'''
    return s[:start] + replacement + s[end:]


def repair_invariant_markdown_parser(s: str) -> str:
    start_marker = '    d = "docs/STABLE_INVARIANTS.md"\n'
    end_marker = '\n\ndef update_scope(new_name: str, new_code: int) -> None:\n'
    start = s.find(start_marker)
    end = s.find(end_marker, start)
    if start < 0 or end < 0:
        raise SystemExit(f"BETA128_APPLY_FAIL:docs-invariant-markers:start={start}:end={end}")
    replacement = '''    d = "docs/STABLE_INVARIANTS.md"\n    md = read(d)\n    for inv in ids:\n        pattern = rf'(?ms)^### {re.escape(inv)}(?: — [^\\n]+)?\\n.*?(?=^### |\\Z)'\n        m = re.search(pattern, md)\n        if not m:\n            raise SystemExit(f"BETA128_R3_PATCH_FAIL:docs-invariant:{inv}")\n        block = m.group(0)\n        block = re.sub(\n            rf'(?m)^### {re.escape(inv)}(?: — [^\\n]+)?$',\n            f'### {inv} — LOCKED_REQUIREMENT_PENDING_FIX',\n            block,\n            count=1,\n        )\n        if "OWNER failure 2026-09-05 R3" not in block:\n            block = block.rstrip() + '\\n- OWNER failure 2026-09-05 R3: UI vẫn có nhấp nháy/reload-like; cần sửa và re-verify trước khi ACTIVE_PASS lại.\\n\\n'\n        md = md[:m.start()] + block + md[m.end():]\n    if "### DROP-LAYOUT-INPUT-004" not in md:\n        md += (\n            '\\n### DROP-LAYOUT-INPUT-004 — LOCKED_REQUIREMENT_PENDING_FIX\\n'\n            '- Scope: Nhận hàng Rớt / UI nhập liệu + bảng\\n'\n            '- Rule: Thu gọn Chọn/Vị trí/Số kiện để ưu tiên cột Thời gian hiển thị đầy đủ; không lặp tiêu đề Scan QR/DO/Số kiện khi hint đã đủ nghĩa; ô nhập phải nổi bật, dễ nhìn.\\n'\n            '- Regression: 320x568 / 360x640 / 480x800; thời gian không ellipsis; không label lặp; input border/fill rõ; CRUD/pagination cũ không regress.\\n'\n            '- Authority: OWNER command CMD-20260905-003.\\n'\n        )\n    write(d, md)\n'''
    return s[:start] + replacement + s[end:]


def main() -> None:
    s = PATCH.read_text(encoding="utf-8")
    s = repair_attendance_boundary(s)
    s = repair_invariant_markdown_parser(s)
    PATCH.write_text(s, encoding="utf-8")
    subprocess.run(["python3", "-m", "py_compile", "tools/beta128_owner_r3_patch.py", "tools/beta128_owner_r3_contract.py"], cwd=ROOT, check=True)
    subprocess.run(["python3", "tools/beta128_owner_r3_patch.py"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
