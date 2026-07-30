"""Application-wide configuration constants."""

from __future__ import annotations

from pathlib import Path

APP_NAME = "CareerProof AI"
APP_TAGLINE = "Ask the job market. See the proof."
VERSION = "1.0.0"
TRACK = "Track 2 - Trustworthy Data Analysis"
SYNTHETIC_DISCLOSURE = (
    "This dataset is synthetic and was generated for demonstration and evaluation. "
    "It does not represent current real-world hiring conditions."
)
TRUST_STATEMENT = "AI interprets the question. Code calculates the answer."

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_PATH = DATA_DIR / "raw" / "job_postings.csv"
RAW_XLSX_PATH = DATA_DIR / "raw" / "job_postings.xlsx"
PROCESSED_DATA_PATH = DATA_DIR / "processed" / "cleaned_job_postings.csv"
AUDIT_LOG_PATH = DATA_DIR / "runtime" / "audit_log.jsonl"
REPORT_TEMPLATE_PATH = PROJECT_ROOT / "templates" / "report.html"

DEFAULT_MIN_GROUP_SIZE = 5
MAX_EVIDENCE_ROWS = 100
MAX_UPLOAD_ROWS = 100_000
MAX_UPLOAD_COLUMNS = 200

SUPPORTED_CURRENCIES = {"USD"}
SUPPORTED_WORK_MODES = {"Remote", "Hybrid", "On-site"}
SUPPORTED_EXPERIENCE_LEVELS = {
    "Internship",
    "Entry Level",
    "Associate",
    "Mid Level",
    "Senior",
}

PII_COLUMNS = {
    "recruiter_name",
    "recruiter_email",
    "recruiter_phone",
    "source_record_id",
}

CORE_ANALYSIS_COLUMNS = {
    "posting_id",
    "date_posted",
    "job_title",
    "normalized_role",
    "role_family",
    "company",
    "city",
    "state",
    "work_mode",
    "experience_level",
    "employment_type",
    "salary_min",
    "salary_max",
    "required_skills",
}
