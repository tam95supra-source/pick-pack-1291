#!/usr/bin/env python3
"""Regression for false realtime PASS after subtracting DNS/TCP/TLS duration."""
import json
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "tools/r5_service_convergence_gate.sh").read_text()
start = '  python3 - "$out" <<\'PY\'\n'
assert source.count(start) == 1
code = source.split(start, 1)[1].split("\nPY\n", 1)[0]

for name, raw_ms, adjusted_ms, expected_pass in [
    ("measured_below_limit", 500, 200, True),
    ("transport_subtraction_cannot_pass", 1500, 200, False),
]:
    with tempfile.TemporaryDirectory(prefix="r5-receipt-regression-") as directory:
        out = Path(directory)
        # Deliberately synthetic test input. Never persisted as runtime evidence.
        out.joinpath("samples.tsv").write_text("".join(
            f"{n//5+1}\t{n%5+1}\t{'PDA' if n%5<3 else 'WEB'}\t{raw_ms}\t{adjusted_ms}\t{raw_ms-adjusted_ms}\t1\t1\t1\n"
            for n in range(50)))
        out.joinpath("status-rows.txt").write_text("1\n" * 10)
        result = subprocess.run(["python3", "-c", code, directory], capture_output=True, text=True)
        assert (result.returncode == 0) == expected_pass, (name, result.stderr)
        receipt = json.loads(out.joinpath("receipt.json").read_text())
        assert receipt["remote_convergence_ms"]["p95"] == raw_ms
        assert receipt["remote_convergence_ms"]["transport_setup_excluded"] is False
        assert receipt["full_technical_dod_pass"] is False
        assert receipt["normalized_max_day"]["classification"] == "EXTRAPOLATED_MODEL_NOT_MEASURED_1540_EVENT_DAY"
        assert receipt["status"] == ("PASS" if expected_pass else "FAIL")
        print(f"{name}=PASS")

