#!/usr/bin/env python3
"""Verify CareerProof AI and create the final reproducible submission ZIP."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = PROJECT_ROOT / "dist"
ZIP_PATH = DIST_DIR / "careerproof-ai-submission.zip"
MANIFEST_PATH = DIST_DIR / "submission_manifest.txt"

EXCLUDED_DIRS = {
    ".git",
    ".presentation_work",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "presentation",
    "presentation_pdf_render",
}
EXCLUDED_NAMES = {
    ".env",
    ".DS_Store",
    "audit_log.jsonl",
    "presentation_montage.png",
    "presentation_pdf_montage.png",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def should_include(path: Path) -> bool:
    rel = path.relative_to(PROJECT_ROOT)
    if any(part in EXCLUDED_DIRS for part in rel.parts):
        return False
    if path.name in EXCLUDED_NAMES or path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if path.name.startswith(".env") and path.name != ".env.example":
        return False
    if rel.parts[:2] == ("data", "runtime") and path.name != "README.md":
        return False
    return path.is_file()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout.strip()


def verify() -> None:
    print("[1/4] Running static submission preflight...", flush=True)
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/verify_submission.py",
            "--require-clean",
            "--skip-tests",
        ],
        cwd=PROJECT_ROOT,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit("Submission verification failed. ZIP was not created.")
    print("[1/4] Static submission preflight passed.", flush=True)


def build_manifest(files: list[Path]) -> str:
    lines = [
        "CareerProof AI Submission Manifest",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Git commit: {git_commit()}",
        f"File count: {len(files)}",
        "",
        "SHA-256                                                          Bytes        Path",
        "----------------------------------------------------------------  -----------  ----",
    ]
    for path in files:
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        lines.append(f"{sha256(path)}  {path.stat().st_size:11d}  {rel}")
    return "\n".join(lines) + "\n"


def inspect_zip(expected_files: list[Path]) -> None:
    with zipfile.ZipFile(ZIP_PATH) as archive:
        names = archive.namelist()
        expected = {path.relative_to(PROJECT_ROOT).as_posix() for path in expected_files}
        actual = {name for name in names if name != "submission_manifest.txt"}
        missing = expected - actual
        forbidden = [
            name
            for name in names
            if name.startswith(".git/")
            or "/.git/" in name
            or "__pycache__" in name
            or name.endswith(".pyc")
            or name == ".env"
            or name.endswith("/.env")
            or name.endswith("audit_log.jsonl")
        ]
        if missing:
            raise RuntimeError("ZIP is missing files: " + ", ".join(sorted(missing)))
        if forbidden:
            raise RuntimeError("ZIP contains forbidden paths: " + ", ".join(sorted(forbidden)))
        if "submission_manifest.txt" not in names:
            raise RuntimeError("ZIP is missing its internal manifest.")
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"ZIP CRC validation failed at {bad}.")


def run_packaged_command(root: Path, command: list[str], *, timeout: int = 240) -> str:
    """Run a packaged-project check without relying on inherited output pipes.

    The smoke test starts and stops a local web process. Writing subprocess output to
    a temporary file avoids a rare pipe-inheritance deadlock when nested child
    processes are exercised under captured output.
    """

    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src") + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as log:
        try:
            completed = subprocess.run(
                command,
                cwd=root,
                env=env,
                text=True,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Extracted-package command timed out after {timeout}s: "
                + " ".join(command)
            ) from exc
        log.seek(0)
        output = log.read().strip()
    if completed.returncode != 0:
        tail = "\n".join(output.splitlines()[-50:])
        raise RuntimeError(
            f"Extracted-package command failed: {' '.join(command)}\n{tail}"
        )
    return output


def verify_extracted_package() -> None:
    """Extract the final archive and exercise the same files a judge will receive."""

    print("[3/4] Extracting and retesting the packaged project...", flush=True)
    with tempfile.TemporaryDirectory(prefix="careerproof-package-") as temp_dir:
        extracted = Path(temp_dir) / "careerproof-ai"
        extracted.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(ZIP_PATH) as archive:
            archive.extractall(extracted)

        required = [
            extracted / "app.py",
            extracted / "README.md",
            extracted / "src" / "careerproof" / "ui.py",
            extracted / "data" / "raw" / "job_postings.csv",
            extracted / "docs" / "presentation.pptx",
        ]
        missing = [str(path.relative_to(extracted)) for path in required if not path.is_file()]
        if missing:
            raise RuntimeError(
                "Extracted package is missing required files: " + ", ".join(missing)
            )

        test_output = run_packaged_command(
            extracted, [sys.executable, "-m", "pytest", "-q"], timeout=300
        )
        demo_output = run_packaged_command(
            extracted, [sys.executable, "scripts/run_demo_checks.py", "--no-write"], timeout=300
        )
        smoke_output = run_packaged_command(
            extracted, [sys.executable, "scripts/smoke_test_app.py"], timeout=120
        )

        test_summary = test_output.splitlines()[-1] if test_output else "pytest passed"
        demo_summary = next(
            (line for line in reversed(demo_output.splitlines()) if line.startswith("Result:")),
            "demo checks passed",
        )
        smoke_summary = next(
            (line for line in smoke_output.splitlines() if "smoke test:" in line.casefold()),
            "application smoke test passed",
        )
        print("[3/4] Extracted-package QA: PASS")
        print(f"  {test_summary}")
        print(f"  {demo_summary}")
        print(f"  {smoke_summary}")


def main() -> int:
    verify()
    print("[2/4] Building ZIP and checksum manifest...", flush=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(
        (path for path in PROJECT_ROOT.rglob("*") if should_include(path)),
        key=lambda path: path.relative_to(PROJECT_ROOT).as_posix(),
    )
    manifest = build_manifest(files)
    MANIFEST_PATH.write_text(manifest, encoding="utf-8")

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(
        ZIP_PATH,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in files:
            archive.write(path, path.relative_to(PROJECT_ROOT).as_posix())
        archive.writestr("submission_manifest.txt", manifest)

    inspect_zip(files)
    print("[2/4] ZIP structure and CRC checks passed.", flush=True)
    verify_extracted_package()
    print("[4/4] CareerProof AI package created")
    print(f"ZIP: {ZIP_PATH}")
    print(f"ZIP bytes: {ZIP_PATH.stat().st_size:,}")
    print(f"ZIP SHA-256: {sha256(ZIP_PATH)}")
    print(f"Git commit: {git_commit()}")
    print(f"Manifest: {MANIFEST_PATH}")
    print(f"Packaged files: {len(files)} + internal manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
