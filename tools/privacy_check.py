#!/usr/bin/env python3
"""Fail a build when tracked files contain likely private finance data or secrets."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_SUFFIXES = {".csv", ".ofx", ".qfx", ".qif", ".xls", ".xlsx", ".pdf", ".db", ".sqlite", ".sqlite3"}
PRIVATE_NAMES = re.compile(r"(?:statement|transaction|expense)[-_ ]?(?:export|data|history)", re.I)
SECRET_PATTERNS = {
    "Supabase secret key": re.compile(r"\bsb_secret_[A-Za-z0-9_-]{12,}"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "service-role JWT": re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
}
DIGIT_RUN = re.compile(r"(?<![\d-])(?:\d{13,19}|(?:\d{4}[ -]){3}\d{1,7})(?![\d-])")
TEXT_SUFFIXES = {
    ".css", ".html", ".js", ".json", ".md", ".mjs", ".py", ".sql",
    ".svg", ".toml", ".ts", ".tsx", ".txt", ".yml", ".yaml",
}


def tracked_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT, text=False
    )
    return [ROOT / item.decode() for item in output.split(b"\0") if item]


def luhn_valid(value: str) -> bool:
    digits = [int(char) for char in value if char.isdigit()]
    if not 13 <= len(digits) <= 19 or len(set(digits)) == 1:
        return False
    total = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        if not path.exists():
            continue
        relative = path.relative_to(ROOT)
        lowered = relative.as_posix().lower()
        if path.suffix.lower() in PRIVATE_SUFFIXES:
            findings.append(f"tracked private-data file type: {relative}")
        if PRIVATE_NAMES.search(path.stem) and not lowered.startswith("test"):
            findings.append(f"tracked private-data filename: {relative}")
        if lowered.startswith(("data/", "public/data/", "web/data/")) and path.suffix.lower() == ".json":
            findings.append(f"public or bundled profile data: {relative}")
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{label}: {relative}")
        for match in DIGIT_RUN.finditer(text):
            compact = re.sub(r"\D", "", match.group(0))
            if len(compact) == 14 and compact.startswith("20"):
                continue  # migration/build timestamp
            if luhn_valid(match.group(0)):
                findings.append(f"possible payment-card number: {relative}")
                break

    hosted_shell = ROOT / "web" / "index.html"
    if hosted_shell.exists():
        shell = hosted_shell.read_text(encoding="utf-8", errors="ignore")
        for marker in ("let DATA = [];", "let STATEMENTS = [];", "let CHEQUING = [];", "let PAYMENTS = [];"):
            if marker not in shell:
                findings.append(f"hosted shell is not demonstrably empty: missing {marker}")
        if "/data/" in shell or "rachel.json" in shell.lower():
            findings.append("hosted shell references a public profile-data path")

    app_output = ROOT / "web" / "app"
    if app_output.exists():
        if any(app_output.rglob("*.map")):
            findings.append("production React source maps are present")
        for path in app_output.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(pattern.search(text) for pattern in SECRET_PATTERNS.values()):
                findings.append(f"secret-like value in React build: {path.relative_to(ROOT)}")
            if "/data/rachel.json" in text.lower():
                findings.append(f"public profile reference in React build: {path.relative_to(ROOT)}")

    if findings:
        print("Privacy check failed:")
        for finding in sorted(set(findings)):
            print(f"- {finding}")
        return 1
    print(f"Privacy check passed ({len(tracked_files())} tracked files scanned).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
