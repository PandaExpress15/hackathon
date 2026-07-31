from __future__ import annotations

import hashlib
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
ZIP_PATH = DIST / "careerproof-ai-official-data.zip"
MANIFEST_PATH = DIST / "submission_manifest.txt"

EXCLUDED_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "dist"}
EXCLUDED_FILES = {".env", ".DS_Store"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def included_files() -> list[Path]:
    files = []
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


def main() -> int:
    subprocess.run([sys.executable, "scripts/verify_submission.py"], cwd=ROOT, check=True)
    DIST.mkdir(exist_ok=True)
    files = included_files()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())

    manifest_lines = [
        "CareerProof AI Official-Data Submission Manifest",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"File count: {len(files)}",
        f"ZIP SHA-256: {sha256_bytes(ZIP_PATH.read_bytes())}",
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
        import shutil
        shutil.rmtree(extract_dir)
    extract_dir.mkdir()
    with zipfile.ZipFile(ZIP_PATH) as archive:
        archive.extractall(extract_dir)
    required = ["README.md", "app.py", "data/processed/occupations.csv", "data/metadata/data_catalog.json"]
    missing = [path for path in required if not (extract_dir / path).exists()]
    if missing:
        raise RuntimeError(f"ZIP extraction missing files: {missing}")
    import shutil
    shutil.rmtree(extract_dir)

    print("\nPACKAGE CREATED")
    print(f"ZIP: {ZIP_PATH}")
    print(f"Size: {ZIP_PATH.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"SHA-256: {sha256_bytes(ZIP_PATH.read_bytes())}")
    print(f"Manifest: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
