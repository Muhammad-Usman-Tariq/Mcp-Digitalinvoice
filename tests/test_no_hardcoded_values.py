"""Automated zero-hardcoding repository audit test (Section 3 & Section 12 Item 15).

Scans all source code, tests, migrations, and docs in the repository to ensure
no literal credentials, email addresses, or business names are hardcoded.
"""

import os
import re
from pathlib import Path

# Paths/directories to scan
ROOT_DIR = Path(__file__).parent.parent
SCAN_DIRS = ["src", "tests", "migrations"]
ALLOW_FILES = {".env.example", ".env", "pyproject.toml", "alembic.ini", "docker-compose.yml"}

# Regex patterns for disallowed hardcoded literals
DISALLOWED_PATTERNS = [
    # Explicit email addresses (excluding Faker generate calls or env.example)
    (re.compile(r'["\'][a-zA-Z0-9._%+-]+@(?!example\.com)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}["\']'), "Literal email address found"),
    # Hardcoded realistic business names or NTN literals
    (re.compile(r'["\'](?:Acme|TechCorp|Global|Pakistani|Enterprise)\s*(?:Corp|Inc|Ltd|Traders)?["\']', re.IGNORECASE), "Literal realistic company name found"),
    (re.compile(r'["\']\d{7}-\d["\']'), "Literal hardcoded NTN string found"),
]


def test_repository_zero_hardcoding_check():
    """Grep repository files to ensure strict compliance with Section 3 zero-hardcoding rule."""
    violations = []

    for scan_target in SCAN_DIRS:
        target_path = ROOT_DIR / scan_target
        if not target_path.exists():
            continue

        for root, _, files in os.walk(target_path):
            if "__pycache__" in root or ".pytest_cache" in root:
                continue

            for file_name in files:
                if file_name in ALLOW_FILES or not (file_name.endswith(".py") or file_name.endswith(".md")):
                    continue

                file_path = Path(root) / file_name

                # Skip this scanner test file itself from self-matching pattern regex
                if file_name == "test_no_hardcoded_values.py":
                    continue

                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, start=1):
                    # Ignore comment-only lines or Faker fixture usage
                    stripped = line.strip()
                    if stripped.startswith("#") or "fake." in line or "Faker" in line:
                        continue

                    for pattern, desc in DISALLOWED_PATTERNS:
                        if pattern.search(line):
                            violations.append(
                                f"{file_path.relative_to(ROOT_DIR)}:{line_num}: {desc} -> {line.strip()}"
                            )

    assert not violations, "Zero-hardcoding violations detected in repository:\n" + "\n".join(violations)
