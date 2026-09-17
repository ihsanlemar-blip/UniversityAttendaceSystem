"""Audit test files against CI shards in .github/workflows/ci.yml."""

import glob
import os
import re
from collections import Counter


def audit_shards():
    test_files = sorted([os.path.basename(f) for f in glob.glob("backend/tests/test_*.py")])
    with open(".github/workflows/ci.yml", "r", encoding="utf-8") as f:
        content = f.read()

    sharded_tests = []
    for match in re.finditer(r'tests:\s*"([^"]+)"', content):
        for path in match.group(1).split():
            sharded_tests.append(os.path.basename(path))

    print(f"Total test files on disk: {len(test_files)}")
    print(f"Total sharded tests in CI: {len(sharded_tests)}")

    missing = set(test_files) - set(sharded_tests)
    print(f"Missing from CI shards ({len(missing)}): {sorted(list(missing))}")

    counts = Counter(sharded_tests)
    duplicates = [t for t, c in counts.items() if c > 1]
    print(f"Duplicates in CI shards ({len(duplicates)}): {sorted(duplicates)}")


if __name__ == "__main__":
    audit_shards()
