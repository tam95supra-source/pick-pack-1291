#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "tools/beta128_owner_r3_patch.py"


def repair_attendance_boundary() -> None:
    s = PATCH.read_text(encoding="utf-8")
    start_marker = "    # Scheduled time-boundary refresh must bypass the no-op signature because status semantics can change with clock time.\n"
    end_marker = "    write(p, s)\n\n\ndef patch_operations()"
    start = s.find(start_marker)
    end = s.find(end_marker, start)
    if start < 0 or end < 0:
        raise SystemExit(f"BETA128_APPLY_FAIL:attendance-boundary-markers:start={start}:end={end}")
    replacement = '''    # Scheduled time-boundary refresh must bypass the no-op signature because status semantics can change with clock time.\n    s = replace_once(\n        s,\n        '                val nowDay=today()\\n                if(selected.isBefore(nowDay))load(nowDay) else {render();remoteLoad()}',\n        '                val nowDay=today()\\n                lastRenderSignature=""\\n                if(selected.isBefore(nowDay))load(nowDay) else {render();remoteLoad()}',\n        "attendance-boundary-force-render",\n    )\n'''
    PATCH.write_text(s[:start] + replacement + s[end:], encoding="utf-8")


def main() -> None:
    repair_attendance_boundary()
    subprocess.run(["python3", "-m", "py_compile", "tools/beta128_owner_r3_patch.py", "tools/beta128_owner_r3_contract.py"], cwd=ROOT, check=True)
    subprocess.run(["python3", "tools/beta128_owner_r3_patch.py"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
