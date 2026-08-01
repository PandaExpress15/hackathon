from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "THIRD_PARTY_NOTICES.md",
    "PREEXISTING_WORK.md",
    "SUBMISSION_CHECKLIST.md",
    "JUDGING_ALIGNMENT.md",
    "app.py",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "templates/app.html",
    "static/app.css",
    "static/app.js",
    "docs/ARCHITECTURE.md",
    "docs/architecture.svg",
    "docs/DATA_SOURCES.md",
    "docs/QUESTION_CATALOG.md",
    "docs/LIMITATIONS.md",
    "docs/SECURITY_AND_SAFETY.md",
    "docs/DEMO_SCRIPT.md",
    "docs/DESIGN_SYSTEM.md",
    "docs/PRESENTATION.md",
    "docs/PRESENTATION.html",
    "docs/JUDGE_DIAGNOSTIC.md",
    "docs/TESTING_REPORT.md",
    "docs/FINAL_98_BUILD_REPORT.md",
    "docs/RESILIENCE_MODEL_CARD.md",
    "docs/browser_acceptance_results.json",
    "docs/final_98_build_manifest.json",
    "docs/assets/careerproof-home.png",
    "docs/assets/careerproof-path-builder.png",
    "docs/assets/careerproof-compare.png",
    "docs/assets/careerproof-mobile.png",
    "data/README.md",
    "data/LICENSE.md",
    "data/metadata/data_catalog.json",
    "data/metadata/question_catalog.json",
    "data/processed/occupations.csv",
    "data/processed/state_wages.csv",
    "data/processed/census_degree_earnings_2024.csv",
    "data/processed/regional_price_parities_2024.csv",
    "data/processed/degree_career_crosswalk.csv",
    "scripts/build_official_data.py",
    "scripts/build_advanced_data.py",
    "scripts/run_demo_checks.py",
    "scripts/judge_diagnostic.py",
    "scripts/smoke_test_app.py",
    "scripts/browser_acceptance.py",
    "scripts/build_submission.py",
]

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
]

CRITICAL_TODO_PATTERNS = [
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r"\bFIXME\b", re.IGNORECASE),
    re.compile(r"placeholder screen", re.IGNORECASE),
    re.compile(r"lorem ipsum", re.IGNORECASE),
]

TODO_ALLOWED = {
    "SUBMISSION_CHECKLIST.md",
    "verify_submission.py",
}


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
        path = ROOT / relative
        if not path.exists():
            failures.append(f"Missing required file: {relative}")
        elif path.is_file() and path.stat().st_size == 0:
            failures.append(f"Required file is empty: {relative}")

    forbidden = list(ROOT.rglob("job_postings.csv")) + list(ROOT.rglob("generate_dataset.py"))
    if forbidden:
        failures.append("Synthetic job-posting files remain in the package")

    if (ROOT / ".env").exists():
        failures.append("A .env file must not be included")

    catalog_path = ROOT / "data/metadata/data_catalog.json"
    if catalog_path.exists():
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        if len(catalog.get("sources", [])) < 8:
            failures.append("Data catalog must list all eight source families")
        source_ids = {source.get("id") for source in catalog.get("sources", [])}
        expected_sources = {
            "bls-oews-national-2025",
            "bls-oews-state-2025",
            "bls-projections-2024-2034",
            "bls-oews-education-2025",
            "onet-30-3",
            "census-acs-b15013-2024",
            "bea-rpp-2024",
            "nces-cip-soc-2020-2018",
        }
        missing_sources = sorted(expected_sources - source_ids)
        if missing_sources:
            failures.append(f"Catalog source families missing: {', '.join(missing_sources)}")
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

    browser_results_path = ROOT / "docs/browser_acceptance_results.json"
    if browser_results_path.exists():
        try:
            browser_results = json.loads(browser_results_path.read_text(encoding="utf-8"))
            summary = browser_results.get("summary", {})
            if int(summary.get("total", 0)) < 33:
                failures.append("Browser acceptance report does not contain the full 33-check suite")
            if int(summary.get("failed", 1)) != 0 or int(summary.get("passed", 0)) != int(summary.get("total", -1)):
                failures.append("Browser acceptance report contains a failed check")
            if browser_results.get("console_errors"):
                failures.append("Browser acceptance report contains console errors")
            if browser_results.get("page_errors"):
                failures.append("Browser acceptance report contains page errors")
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            failures.append(f"Browser acceptance report is invalid: {exc}")

    text_suffixes = {".py", ".md", ".txt", ".html", ".css", ".js", ".toml", ".json", ".yml", ".yaml"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        relative = path.relative_to(ROOT)
        if any(part in {".git", ".venv", "dist", "__pycache__", ".pytest_cache"} for part in relative.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                failures.append(f"Potential secret pattern found in {relative}")
        if path.name not in TODO_ALLOWED:
            for pattern in CRITICAL_TODO_PATTERNS:
                if pattern.search(text):
                    failures.append(f"Critical placeholder marker found in {relative}: {pattern.pattern}")
                    break
        if path.name not in {"SUBMISSION_CHECKLIST.md", "verify_submission.py"} and re.search(r"<TEAM_|<PUBLIC_GITHUB_URL>|<YOUTUBE_URL>", text):
            failures.append(f"Unresolved submission placeholder outside checklist: {relative}")

    app_html = ROOT / "templates/app.html"
    app_css = ROOT / "static/app.css"
    app_js = ROOT / "static/app.js"
    if app_html.exists() and app_css.exists() and app_js.exists():
        html = app_html.read_text(encoding="utf-8")
        css = app_css.read_text(encoding="utf-8")
        js = app_js.read_text(encoding="utf-8")
        visual_markers = {
            "campaign line": "Plan your future with AI" in html,
            "custom suit logo": "brand-emblem" in html,
            "official source label": "Official sources only" in html,
            "Judge Mode": "judge" in html.lower() and "judge" in js.lower(),
            "reduced motion": "prefers-reduced-motion" in css,
            "home dashboard": 'id="workspace-home"' in html,
            "resilience model": "resilience" in html.lower() and "resilience" in js.lower(),
            "recommendation challenge": "challenge" in html.lower() or "challenge" in js.lower(),
            "demo reset": 'id="resetDemo"' in html and "resetExperience" in js,
        }
        for label, present in visual_markers.items():
            if not present:
                failures.append(f"Visual product marker missing: {label}")

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

    # Run the two data-heavy quality suites in this process so they share the
    # cached official DataStore rather than loading every source twice.
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import run_demo_checks
    import judge_diagnostic
    import smoke_test_app

    if run_demo_checks.main() != 0:
        print("Demonstration and advanced workflow checks failed")
        return 1
    if judge_diagnostic.main() != 0:
        print("Judge diagnostic failed")
        return 1
    if smoke_test_app.main() != 0:
        print("Server smoke test failed")
        return 1

    print("\nSUBMISSION VERIFICATION PASSED")
    print("- Eight official source families and all catalog checksums verified")
    print("- No synthetic job-posting dataset or credential file found")
    print("- Python, JavaScript, tests, natural-language checks, advanced workflows, judge diagnostic, and server smoke test passed")
    print("- The generated 33-check Chromium acceptance report is complete and error-free")
    print("- Career Intelligence workspaces, trust controls, visual identity, documentation, and packaging assets are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
