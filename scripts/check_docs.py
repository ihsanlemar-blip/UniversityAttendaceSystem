#!/usr/bin/env python3
"""Documentation integrity validator script."""

import os
import sys

EXPECTED_PREFIXES = [f"{i:02d}" for i in range(61)]


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

    for m_num in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19):
        manifest = os.path.join(docs_dir, f"MILESTONE_{m_num}_MANIFEST.md")
        if not os.path.isfile(manifest) or os.path.getsize(manifest) == 0:
            print(f"[!] Error: docs/MILESTONE_{m_num}_MANIFEST.md is missing or empty.")
            return 1

    if missing:
        print(f"[!] Missing or empty documentation files for prefixes: {missing}")
        return 1

    print(
        f"[+] Documentation validation PASSED: All 61 specifications (00-60), "
        f"and manifests (M3 through M19) present ({len(files)} total files)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(validate_docs())
