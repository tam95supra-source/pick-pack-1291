#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def verify(stable, beta_old, beta_current, expected):
    if not (stable.get("ok") is True and stable.get("channel") == "STABLE" and stable.get("available") is False):
        raise RuntimeError("OTA_RECOVERY_STABLE_GUARD_FAILED")
    if not (
        beta_old.get("ok") is True
        and beta_old.get("channel") == "BETA"
        and beta_old.get("source") == "GITHUB_RELEASE"
        and beta_old.get("available") is True
        and beta_old.get("version_name") == expected["version_name"]
        and beta_old.get("version_code") == expected["version_code"]
        and beta_old.get("package") == expected["package"]
        and beta_old.get("sha256") == expected["sha256"]
        and beta_old.get("size") == expected["size"]
        and beta_old.get("apk_url") == expected["apk_url"]
    ):
        raise RuntimeError("OTA_RECOVERY_BETA_BASELINE_FAILED")
    if not (
        beta_current.get("ok") is True
        and beta_current.get("channel") == "BETA"
        and beta_current.get("source") == "GITHUB_RELEASE"
        and beta_current.get("available") is False
        and beta_current.get("version_name") == expected["version_name"]
        and beta_current.get("version_code") == expected["version_code"]
        and beta_current.get("package") == expected["package"]
    ):
        raise RuntimeError("OTA_RECOVERY_CURRENT_VERSION_FAILED")
    return {"status": "PASS", "contract": "OTA_BASELINE_RECOVERY_EXACT_READBACK_V1"}


def self_test():
    exp = {
        "version_name": "0.4.2-beta.120",
        "version_code": 126,
        "package": "vn.pickpack1291.app.beta.publicbeta",
        "sha256": "a" * 64,
        "size": 123,
        "apk_url": "https://github.com/o/r/releases/download/v0.4.2-beta.120-publicbeta/a.apk",
    }
    stable = {"ok": True, "channel": "STABLE", "available": False}
    old = {"ok": True, "channel": "BETA", "source": "GITHUB_RELEASE", "available": True, **exp}
    current = {"ok": True, "channel": "BETA", "source": "GITHUB_RELEASE", "available": False, **exp}
    verify(stable, old, current, exp)
    bad = dict(old); bad["sha256"] = "b" * 64
    try:
        verify(stable, bad, current, exp)
    except RuntimeError as exc:
        if str(exc) != "OTA_RECOVERY_BETA_BASELINE_FAILED":
            raise
    else:
        raise RuntimeError("SELF_TEST_FAIL_CLOSED_MISSING")
    print(json.dumps({"status": "PASS", "self_test": "OTA_BASELINE_RECOVERY_FAIL_CLOSED"}))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--stable")
    p.add_argument("--beta-old")
    p.add_argument("--beta-current")
    p.add_argument("--expected")
    p.add_argument("--out")
    a = p.parse_args()
    if a.self_test:
        self_test(); return
    for name in ("stable", "beta_old", "beta_current", "expected", "out"):
        if not getattr(a, name):
            raise RuntimeError("MISSING_ARGUMENT:" + name)
    result = verify(
        json.loads(Path(a.stable).read_text()),
        json.loads(Path(a.beta_old).read_text()),
        json.loads(Path(a.beta_current).read_text()),
        json.loads(Path(a.expected).read_text()),
    )
    Path(a.out).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
