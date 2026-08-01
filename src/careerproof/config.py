from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
METADATA_DIR = DATA_DIR / "metadata"
STATIC_DIR = ROOT / "static"
TEMPLATES_DIR = ROOT / "templates"
RUNTIME_DIR = DATA_DIR / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

APP_TITLE = "CareerProof AI"
APP_TAGLINE = "Plan your future with AI. Not for AI."
APP_VERSION = "4.0.0-resilience-intelligence"
