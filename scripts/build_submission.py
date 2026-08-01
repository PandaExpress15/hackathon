from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT.parent
DIST = ROOT / "dist"
ZIP_PATH = OUTPUT_DIR / "careerproof-ai-revamped-final.zip"
MANIFEST_PATH = OUTPUT_DIR / "careerproof-ai-revamped-final.sha256.txt"

EXCLUDED_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "dist", "node_modules"}
EXCLUDED_FILES = {".env", ".DS_Store"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def included_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.name in EXCLUDED_FILES or path.suffix in EXCLUDED_SUFFIXES:
            continue
        if relative.as_posix().startswith("data/runtime/") and path.name != ".gitkeep":
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_checked(command: list[str], *, cwd: Path, label: str) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    print(f"\n[{label}] $ {' '.join(command)}")
    subprocess.run(command, cwd=cwd, env=env, check=True)


def validate_extracted_submission(extract_dir: Path) -> None:
    required = [
        "README.md",
        "app.py",
        "JUDGING_ALIGNMENT.md",
        "data/processed/occupations.csv",
        "data/processed/regional_price_parities_2024.csv",
        "data/processed/degree_career_crosswalk.csv",
        "data/metadata/data_catalog.json",
        "docs/PRESENTATION_READY_BUILD_REPORT.md",
        "docs/presentation_ready_build_manifest.json",
        "docs/FINAL_98_BUILD_REPORT.md",
        "docs/RESILIENCE_MODEL_CARD.md",
        "docs/CAREERPROOF_5_REDESIGN_REPORT.md",
        "docs/redesign-previews/01-home.png",
        "docs/redesign-previews/03b-career-universe-profile.png",
        "scripts/capture_redesign_previews.py",
        "docs/TESTING_REPORT.md",
        "docs/PRESENTATION.html",
        "docs/architecture.svg",
        "docs/browser_acceptance_results.json",
        "docs/DEPLOYMENT.md",
        "docs/final_98_build_manifest.json",
        "docs/assets/careerproof-home.png",
        "docs/assets/careerproof-path-builder.png",
        "docs/assets/careerproof-compare.png",
        "docs/assets/careerproof-mobile.png",
        "docs/assets/careerproof-judge-mode.png",
        "Dockerfile",
        ".dockerignore",
        "Procfile",
        "render.yaml",
        "scripts/browser_acceptance.py",
        "scripts/write_release_manifest.py",
        "scripts/verify_submission.py",
    ]
    missing = [path for path in required if not (extract_dir / path).exists()]
    if missing:
        raise RuntimeError(f"Extracted ZIP is missing required files: {missing}")

    # Run the complete verifier from the clean extracted artifact. This repeats
    # the unit, integration, workflow, diagnostic, syntax, source-integrity,
    # secret, placeholder, and server-smoke checks against the exact ZIP copy.
    run_checked([sys.executable, "scripts/verify_submission.py"], cwd=extract_dir, label="extracted ZIP verification")

    # Re-run the real Chromium acceptance suite against the extracted source so
    # the package itself is confirmed to preserve the full interactive product.
    run_checked([sys.executable, "scripts/browser_acceptance.py"], cwd=extract_dir, label="extracted ZIP browser acceptance")


def main() -> int:
    skip_source_verify = "--skip-source-verify" in sys.argv
    if skip_source_verify:
        print("\n[source-tree verification] skipped by explicit build flag; use only after running verify_submission.py separately")
    else:
        run_checked([sys.executable, "scripts/verify_submission.py"], cwd=ROOT, label="source-tree verification")

    run_checked([sys.executable, "scripts/write_release_manifest.py"], cwd=ROOT, label="release manifest")

    DIST.mkdir(exist_ok=True)
    for stale in [ZIP_PATH, MANIFEST_PATH]:
        if stale.exists():
            stale.unlink()

    files = included_files()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())

    zip_hash = sha256_bytes(ZIP_PATH.read_bytes())
    manifest_lines = [
        "CareerProof AI 5.0 Revamped Submission Manifest",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "Application version: 5.0.0-revamped",
        f"File count: {len(files)}",
        f"ZIP bytes: {ZIP_PATH.stat().st_size}",
        f"ZIP SHA-256: {zip_hash}",
        "Data policy: eight official source families; zero synthetic labor-market records",
        "Validation target: 83 tests, 19 workflows, 11 judge diagnostics, 39 Chromium checks",
        "",
        "SHA-256                                                          Bytes        Path",
        "----------------------------------------------------------------  -----------  ----",
    ]
    for path in files:
        data = path.read_bytes()
        manifest_lines.append(f"{sha256_bytes(data)}  {len(data):11d}  {path.relative_to(ROOT).as_posix()}")
    MANIFEST_PATH.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

    extract_dir = DIST / "verify_extract"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True)
    with zipfile.ZipFile(ZIP_PATH) as archive:
        archive.extractall(extract_dir)

    try:
        validate_extracted_submission(extract_dir)
    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)

    print("\nPACKAGE CREATED")
    print(f"ZIP: {ZIP_PATH}")
    print(f"Size: {ZIP_PATH.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"SHA-256: {zip_hash}")
    print(f"Manifest: {MANIFEST_PATH}")
    print(f"Files: {len(files)}")
    print("The clean extracted ZIP passed the complete verifier and 39-check Chromium browser suite.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
