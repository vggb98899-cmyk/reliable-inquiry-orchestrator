from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
BLOCKED_SUFFIXES = {".sqlite", ".db", ".log", ".xlsx", ".xls", ".csv", ".png", ".jpg", ".bmp"}
PATTERNS = {
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "generic_secret": re.compile(r"(?i)(api[_-]?key|client[_-]?secret|access[_-]?token|password)\s*[:=]\s*['\"][^'\"]{8,}"),
    "private_network": re.compile(r"(?<!\d)(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})(?!\d)"),
    "production_markers": re.compile(
        "(?i)(" + "|".join(("fei" + "shu", "we" + "chat", "ling" + "xing",
                               "erp/" + "msupply", "AI" + "020", "P" + r"O\d{9}")) + ")"
    ),
}


def files():
    for path in ROOT.rglob("*"):
        if path.is_file() and not any(part in EXCLUDED for part in path.parts):
            yield path


def main() -> int:
    findings = []
    for path in files():
        relative = path.relative_to(ROOT)
        if path.suffix.lower() in BLOCKED_SUFFIXES:
            findings.append((str(relative), "blocked_file_type"))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append((str(relative), "unexpected_binary"))
            continue
        for name, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append((str(relative), name))
    for path, category in findings:
        print(f"{category}: {path}")
    print(f"SECURITY_FINDING_COUNT={len(findings)}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
