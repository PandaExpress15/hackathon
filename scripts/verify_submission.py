from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "PREEXISTING_WORK.md",
    "SUBMISSION_CHECKLIST.md", "app.py", "requirements.txt", "pyproject.toml",
    "templates/app.html", "static/app.css", "static/app.js",
    "docs/DATA_SOURCES.md", "docs/QUESTION_CATALOG.md", "docs/ARCHITECTURE.md",
    "docs/LIMITATIONS.md", "docs/DEMO_SCRIPT.md", "data/metadata/data_catalog.json",
    "data/processed/occupations.csv", "data/processed/state_wages.csv",
    "data/processed/census_degree_earnings_2024.csv", "scripts/build_official_data.py",
    "scripts/run_demo_checks.py", "scripts/smoke_test_app.py", "scripts/build_submission.py",
]

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
]


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str]) -> None:
    print("$", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    failures: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).exists():
            failures.append(f"Missing required file: {relative}")

    forbidden = list(ROOT.rglob("job_postings.csv")) + list(ROOT.rglob("generate_dataset.py"))
    if forbidden:
        failures.append("Synthetic job-posting files remain in the package")

    if (ROOT / ".env").exists():
        failures.append("A .env file must not be included")

    catalog_path = ROOT / "data/metadata/data_catalog.json"
    if catalog_path.exists():
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        if len(catalog.get("sources", [])) < 6:
            failures.append("Data catalog must list all six source families")
        for relative, metadata in catalog.get("raw_file_checksums", {}).items():
            path = ROOT / relative
            if not path.exists():
                failures.append(f"Catalog raw file missing: {relative}")
            elif hash_file(path) != metadata.get("sha256"):
                failures.append(f"Checksum mismatch: {relative}")
        for key, metadata in catalog.get("processed_file_checksums", {}).items():
            path = ROOT / metadata.get("path", "")
            if not path.exists():
                failures.append(f"Catalog processed file missing: {key}")
            elif hash_file(path) != metadata.get("sha256"):
                failures.append(f"Processed checksum mismatch: {key}")

    text_suffixes = {".py", ".md", ".txt", ".html", ".css", ".js", ".toml", ".json", ".yml", ".yaml"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        if any(part in {".git", ".venv", "dist"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                failures.append(f"Potential secret pattern found in {path.relative_to(ROOT)}")
        if path.name not in {"SUBMISSION_CHECKLIST.md", "verify_submission.py"} and re.search(r"<TEAM_|<PUBLIC_GITHUB_URL>|<YOUTUBE_URL>", text):
            failures.append(f"Unresolved submission placeholder outside checklist: {path.relative_to(ROOT)}")

    if failures:
        print("\nSTATIC VERIFICATION FAILED")
        for failure in failures:
            print("-", failure)
        return 1

    run([sys.executable, "-m", "compileall", "-q", "src", "app.py", "scripts"])
    if subprocess.run(["node", "--check", "static/app.js"], cwd=ROOT).returncode != 0:
        print("JavaScript syntax validation failed")
        return 1
    run([sys.executable, "-m", "pytest", "-q"])
    run([sys.executable, "scripts/run_demo_checks.py"])
    run([sys.executable, "scripts/smoke_test_app.py"])
    print("\nSUBMISSION VERIFICATION PASSED")
    print("- Official source files and checksums verified")
    print("- No synthetic job-posting dataset found")
    print("- Python, JavaScript, tests, demo checks, and server smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
