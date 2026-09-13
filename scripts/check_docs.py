#!/usr/bin/env python3
"""Documentation integrity validator script."""

import os
import sys

EXPECTED_PREFIXES = [f"{i:02d}" for i in range(29)]


def validate_docs() -> int:
    docs_dir = "docs"
    if not os.path.isdir(docs_dir):
        print(f"[!] Error: {docs_dir} directory not found.")
        return 1

    files = os.listdir(docs_dir)
    missing = []

    for prefix in EXPECTED_PREFIXES:
        match = [f for f in files if f.startswith(f"{prefix}_") and f.endswith(".md")]
        if not match:
            missing.append(prefix)
        else:
            file_path = os.path.join(docs_dir, match[0])
            size = os.path.getsize(file_path)
            if size == 0:
                print(f"[!] Warning: {file_path} is empty.")
                missing.append(prefix)

    manifest_path = os.path.join(docs_dir, "MILESTONE_3_MANIFEST.md")
    if not os.path.isfile(manifest_path) or os.path.getsize(manifest_path) == 0:
        print("[!] Error: docs/MILESTONE_3_MANIFEST.md is missing or empty.")
        return 1

    if missing:
        print(f"[!] Missing or empty documentation files for prefixes: {missing}")
        return 1

    print(f"[+] Documentation validation PASSED: All 29 specifications (00-28) and MILESTONE_3_MANIFEST.md present ({len(files)} total files).")
    return 0


if __name__ == "__main__":
    sys.exit(validate_docs())
