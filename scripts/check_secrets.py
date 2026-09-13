#!/usr/bin/env python3
"""Secret scan script for repository validation."""

import os
import re
import sys

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY-----"),
    re.compile(r"ghp_[0-9a-zA-Z]{36}"),
    re.compile(r"eyJhbGciOi[0-9a-zA-Z._-]{20,}"),
    re.compile(r"sk-[0-9a-zA-Z]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]

IGNORE_DIRS = {
    ".git",
    "archive",
    "node_modules",
    ".venv",
    ".next",
    ".dart_tool",
    "build",
    "__pycache__",
}


def scan_repository() -> int:
    violations = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            path = os.path.join(root, f)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    for line_no, line in enumerate(fh, start=1):
                        for pattern in SECRET_PATTERNS:
                            if pattern.search(line):
                                violations.append((path, line_no, line.strip()[:60]))
            except Exception:
                pass

    if violations:
        print(f"[!] Found {len(violations)} secret violations:")
        for path, line_no, snippet in violations:
            print(f"  {path}:{line_no} -> {snippet}")
        return 1

    print("[+] Secret scan PASSED: Zero exposed secrets found in repository.")
    return 0


if __name__ == "__main__":
    sys.exit(scan_repository())
