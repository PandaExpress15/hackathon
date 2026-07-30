#!/usr/bin/env python3
"""Verify the repository is ready to package for the hackathon submission."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from careerproof.data_loader import load_bundled_dataset  # noqa: E402


@dataclass(slots=True)
class Check:
    name: str
    passed: bool
    detail: str


REQUIRED_FILES = [
    "README.md",
    "PLAN.md",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "LICENSE",
    ".gitignore",
    ".env.example",
    "app.py",
    "data/raw/job_postings.csv",
    "data/raw/job_postings.xlsx",
    "data/README.md",
    "data/LICENSE.md",
    "docs/data_dictionary.md",
    "docs/architecture.svg",
    "docs/architecture.mmd",
    "docs/architecture.md",
    "docs/presentation.md",
    "docs/presentation.html",
    "docs/presentation.pptx",
    "docs/presentation.pdf",
    "docs/demo_script.md",
    "docs/judge_demo_cheatsheet.md",
    "docs/checkpoint_pack.md",
    "docs/video_recording_guide.md",
    "docs/testing_report.md",
    "docs/demo_check_results.json",
    "docs/security_and_privacy.md",
    "docs/limitations.md",
    "docs/submission_description.md",
    "docs/api_and_dependencies.md",
    "docs/assets/screenshots/dashboard.png",
    "JUDGING_ALIGNMENT.md",
    "SUBMISSION_CHECKLIST.md",
    "PREEXISTING_WORK.md",
    "THIRD_PARTY_NOTICES.md",
    "scripts/run_demo_checks.py",
    "scripts/smoke_test_app.py",
    "scripts/verify_submission.py",
    "scripts/build_submission.py",
]

TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".html",
    ".js",
    ".mmd",
    ".css",
    ".sh",
}

SECRET_PATTERNS = {
    "OpenAI-style API key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "GitHub personal access token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "Private key material": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}

CRITICAL_PLACEHOLDER_PATTERN = re.compile(
    r"\b(?:TODO|FIXME|XXX|HACK)\b|NotImplementedError|raise\s+NotImplemented",
    flags=re.IGNORECASE,
)

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "node_modules",
}


def add(checks: list[Check], name: str, passed: bool, detail: str) -> None:
    checks.append(Check(name=name, passed=passed, detail=detail))


def iter_text_files() -> Iterable[Path]:
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(PROJECT_ROOT).parts):
            continue
        if path.suffix.lower() in TEXT_EXTENSIONS or path.name in {"Makefile", ".env.example", ".gitignore"}:
            yield path


def run_command(command: list[str], *, timeout: int = 180) -> tuple[bool, str]:
    """Run a verification command without nested-process pipe deadlocks."""

    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as log:
        try:
            completed = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                text=True,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout}s: {' '.join(command)}"
        log.seek(0)
        output = log.read().strip()
    if len(output) > 3500:
        output = output[-3500:]
    return completed.returncode == 0, output


def verify_required_files(checks: list[Check]) -> None:
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).is_file()]
    add(
        checks,
        "Required submission files",
        not missing,
        "All required files exist." if not missing else "Missing: " + ", ".join(missing),
    )


def verify_dataset(checks: list[Check]) -> None:
    try:
        bundle = load_bundled_dataset()
    except Exception as exc:
        add(checks, "Dataset load", False, f"Dataset could not be loaded: {type(exc).__name__}: {exc}")
        return
    add(checks, "Dataset load", True, f"Loaded {bundle.report.raw_rows:,} raw rows and {bundle.report.cleaned_rows:,} cleaned rows.")
    add(
        checks,
        "Track 2 row minimum",
        bundle.report.raw_rows >= 30,
        f"Bundled dataset contains {bundle.report.raw_rows:,} rows; minimum is 30.",
    )
    add(
        checks,
        "Synthetic-data disclosure flag",
        bundle.is_synthetic,
        "All cleaned bundled rows are marked synthetic." if bundle.is_synthetic else "One or more rows are not marked synthetic.",
    )
    add(
        checks,
        "PII classification",
        bool(bundle.report.pii_columns_detected),
        "Detected sensitive columns: " + ", ".join(bundle.report.pii_columns_detected),
    )


def verify_no_env(checks: list[Check]) -> None:
    forbidden = []
    for path in PROJECT_ROOT.rglob(".env*"):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(PROJECT_ROOT).parts):
            continue
        if path.name != ".env.example":
            forbidden.append(str(path.relative_to(PROJECT_ROOT)))
    add(
        checks,
        "No packaged environment secrets",
        not forbidden,
        "Only .env.example is present." if not forbidden else "Forbidden environment files: " + ", ".join(forbidden),
    )


def verify_secrets(checks: list[Check]) -> None:
    findings: list[str] = []
    for path in iter_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(PROJECT_ROOT)} ({label})")
    add(
        checks,
        "Secret-pattern scan",
        not findings,
        "No common credential patterns detected." if not findings else "Potential secret patterns in: " + ", ".join(findings),
    )


def verify_critical_placeholders(checks: list[Check]) -> None:
    critical_roots = [PROJECT_ROOT / "app.py", PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"]
    findings: list[str] = []
    allowed = {PROJECT_ROOT / "scripts" / "verify_submission.py"}
    for root in critical_roots:
        paths = [root] if root.is_file() else list(root.rglob("*.py"))
        for path in paths:
            if path in allowed:
                continue
            text = path.read_text(encoding="utf-8")
            if CRITICAL_PLACEHOLDER_PATTERN.search(text):
                findings.append(str(path.relative_to(PROJECT_ROOT)))
    add(
        checks,
        "No critical implementation placeholders",
        not findings,
        "No TODO/FIXME/NotImplemented markers found in application code." if not findings else "Markers found in: " + ", ".join(findings),
    )


def verify_disclosures(checks: list[Check]) -> None:
    phrase = "This dataset is synthetic"
    targets = [
        "README.md",
        "data/README.md",
        "docs/data_dictionary.md",
        "docs/presentation.md",
        "docs/presentation.html",
        "templates/report.html",
    ]
    missing = []
    for target in targets:
        path = PROJECT_ROOT / target
        if not path.exists() or phrase.lower() not in path.read_text(encoding="utf-8").lower():
            missing.append(target)
    add(
        checks,
        "Synthetic-data disclosure coverage",
        not missing,
        "Disclosure appears in the app documentation, data documentation, presentation, and report template."
        if not missing
        else "Disclosure phrase missing from: " + ", ".join(missing),
    )


def verify_git_status(checks: list[Check]) -> None:
    git_dir = PROJECT_ROOT / ".git"
    if not git_dir.is_dir():
        add(checks, "Git repository", False, "No local Git repository found.")
        return
    ok, output = run_command(["git", "rev-list", "--count", "HEAD"], timeout=30)
    if not ok:
        add(checks, "Git commit history", False, "Repository has no commits yet.")
        return
    count = int(output.splitlines()[-1])
    add(checks, "Git commit history", count >= 1, f"Local repository contains {count} commit(s).")

def verify_git_clean(checks: list[Check], *, required: bool) -> None:
    if not required:
        return
    ok, output = run_command(
        ["git", "status", "--porcelain", "--untracked-files=all"], timeout=30
    )
    if not ok:
        add(checks, "Git working tree", False, "Could not inspect the Git working tree.")
        return
    dirty = [line for line in output.splitlines() if line.strip()]
    add(
        checks,
        "Git working tree",
        not dirty,
        "Working tree is clean; the ZIP can be tied to the current commit."
        if not dirty
        else "Commit or remove these changes before packaging: " + ", ".join(dirty[:12]),
    )


def verify_python_compilation(checks: list[Check]) -> None:
    ok, output = run_command(
        [sys.executable, "-m", "compileall", "-q", "app.py", "src", "scripts", "tests"],
        timeout=120,
    )
    add(
        checks,
        "Python compilation",
        ok,
        "Application, scripts, and tests compile successfully."
        if ok
        else (output.splitlines()[-1] if output else "Compilation failed."),
    )


def verify_tests(checks: list[Check], *, skip: bool) -> None:
    if skip:
        add(checks, "Automated tests", True, "Skipped by command-line option.")
        add(checks, "Demo checks", True, "Skipped by command-line option.")
        add(checks, "Application launch smoke test", True, "Skipped by command-line option.")
        return
    ok, output = run_command([sys.executable, "-m", "pytest", "-q"], timeout=240)
    detail = output.splitlines()[-1] if output else "No output"
    add(checks, "Automated tests", ok, detail)

    ok, output = run_command([sys.executable, "scripts/run_demo_checks.py", "--no-write"], timeout=240)
    summary_lines = [line for line in output.splitlines() if line.startswith("Result:")]
    detail = summary_lines[-1] if summary_lines else (output.splitlines()[-1] if output else "No output")
    add(checks, "Demo checks", ok, detail)

    ok, output = run_command([sys.executable, "scripts/smoke_test_app.py"], timeout=120)
    detail_lines = [line for line in output.splitlines() if "smoke test:" in line.casefold()]
    detail = detail_lines[-1] if detail_lines else (output.splitlines()[-1] if output else "No output")
    add(checks, "Application launch smoke test", ok, detail)


def print_report(checks: list[Check]) -> int:
    width = max(len(check.name) for check in checks)
    print("CareerProof AI submission verification")
    print("=" * 96)
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"{status:4} | {check.name:<{width}} | {check.detail}")
    print("=" * 96)
    passed = sum(check.passed for check in checks)
    print(f"Summary: {passed}/{len(checks)} checks passed")
    if passed == len(checks):
        print("SUBMISSION VERIFICATION: PASS")
        return 0
    print("SUBMISSION VERIFICATION: FAIL")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest and demo checks.")
    parser.add_argument(
        "--require-clean",
        action="store_true",
        help="Fail unless every tracked and untracked project change is committed.",
    )
    args = parser.parse_args()

    checks: list[Check] = []
    verify_required_files(checks)
    verify_dataset(checks)
    verify_no_env(checks)
    verify_secrets(checks)
    verify_critical_placeholders(checks)
    verify_disclosures(checks)
    verify_git_status(checks)
    verify_git_clean(checks, required=args.require_clean)
    verify_python_compilation(checks)
    verify_tests(checks, skip=args.skip_tests)
    return print_report(checks)


if __name__ == "__main__":
    raise SystemExit(main())
