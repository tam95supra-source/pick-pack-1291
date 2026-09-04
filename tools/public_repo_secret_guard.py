#!/usr/bin/env python3
import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_FILE_PATTERNS = [
    re.compile(r"(^|/)\.env($|\.)", re.I),
    re.compile(r"\.(jks|keystore|p12|pfx|pem|key)$", re.I),
    re.compile(r"(^|/)(credentials|client_secret|service[-_]?account)([^/]*)\.json$", re.I),
]

DIRECT_PATTERNS = [
    ("PRIVATE_KEY_BLOCK", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("GITHUB_TOKEN", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("GOOGLE_CLIENT_SECRET", re.compile(r"\bGOCSPX-[A-Za-z0-9_-]{20,}\b")),
    ("GOOGLE_REFRESH_TOKEN", re.compile(r"\b1//[A-Za-z0-9_-]{20,}\b")),
    ("SLACK_TOKEN", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("AWS_ACCESS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
]

ASSIGNMENT = re.compile(
    r"(?i)(?:^|[\s,{])[\"']?(?:password|passwd|pwd|otp|refresh_token|client_secret|private_key|service_token|admin_token|bearer_token)[\"']?"
    r"\s*[:=]\s*[\"']([^\"'\r\n]{8,})[\"']"
)
SAFE_VALUES = {
    "FORBIDDEN", "REDACTED", "MASKED", "PLACEHOLDER", "CHANGEME", "EXAMPLE_ONLY",
    "PENDING", "NONE", "NULL", "NOT_SET", "SECRET_STORE_ONLY",
}


def fail(msg: str) -> None:
    raise SystemExit("PUBLIC_REPO_SECRET_GUARD_FAIL:" + msg)


def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.DEVNULL)


def added_files(base_ref: str | None) -> list[str]:
    if not base_ref:
        return []
    try:
        raw = run("git", "diff", "--name-only", "--diff-filter=A", f"{base_ref}..HEAD", "--", ".")
    except Exception:
        fail("BASE_REF_UNREADABLE")
    return [p.strip() for p in raw.splitlines() if p.strip()]


def added_file_guard(base_ref: str | None) -> None:
    for path in added_files(base_ref):
        for pat in FORBIDDEN_FILE_PATTERNS:
            if pat.search(path):
                fail("FORBIDDEN_CREDENTIAL_FILE:" + path)


def added_lines(base_ref: str | None) -> list[tuple[str, str]]:
    if not base_ref:
        return []
    try:
        diff = run("git", "diff", "--unified=0", "--no-color", f"{base_ref}..HEAD", "--", ".")
    except Exception:
        fail("BASE_REF_UNREADABLE")
    out: list[tuple[str, str]] = []
    current = ""
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            continue
        if line.startswith("+") and not line.startswith("+++"):
            out.append((current, line[1:]))
    return out


def safe_assignment_value(value: str) -> bool:
    v = value.strip()
    upper = v.upper()
    if upper in SAFE_VALUES:
        return True
    if any(marker in v for marker in ("${{ secrets.", "${{ env.", "$SECRET", "$TOKEN", "process.env", "os.environ", "getenv(", "secret store", "Secret Store")):
        return True
    if re.fullmatch(r"[A-Z][A-Z0-9_]{2,}", v):
        return True
    return False


def scan_added(base_ref: str | None) -> None:
    for path, line in added_lines(base_ref):
        for name, pat in DIRECT_PATTERNS:
            if pat.search(line):
                fail(f"{name}:{path}")
        m = ASSIGNMENT.search(line)
        if m and not safe_assignment_value(m.group(1)):
            fail("PLAINTEXT_SECRET_ASSIGNMENT:" + path)


def self_test() -> None:
    private_key = dict(DIRECT_PATTERNS)["PRIVATE_KEY_BLOCK"]
    assert private_key.search("-----BEGIN " + "PRIVATE KEY-----")
    assert not safe_assignment_value("actual" + "Secret123")
    assert safe_assignment_value("FORBIDDEN")
    assert safe_assignment_value("${{ secrets.MY_TOKEN }}")
    yaml_sample = "pass" + "word: \"" + "actual" + "Secret123\""
    json_sample = "{\"pass" + "word\": \"" + "actual" + "Secret123\"}"
    assert ASSIGNMENT.search(yaml_sample)
    assert ASSIGNMENT.search(json_sample)
    print("public_repo_secret_guard_selftest=PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-ref")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return
    added_file_guard(args.base_ref)
    scan_added(args.base_ref)
    print("public_repo_secret_guard=PASS")


if __name__ == "__main__":
    main()
