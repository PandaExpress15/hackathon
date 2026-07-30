"""Schema mapping, validation, and transparent cleaning for uploaded job data."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Iterable

import numpy as np
import pandas as pd

from .config import PII_COLUMNS, SUPPORTED_EXPERIENCE_LEVELS, SUPPORTED_WORK_MODES
from .schema import CleaningAction, DataIssue, DataQualityReport

COLUMN_ALIASES: dict[str, set[str]] = {
    "posting_id": {"posting_id", "job_id", "id", "listing_id", "requisition_id"},
    "date_posted": {"date_posted", "posted_date", "posting_date", "date", "created_at"},
    "job_title": {"job_title", "title", "position", "position_title", "role_title"},
    "normalized_role": {"normalized_role", "role", "job_role", "occupation"},
    "role_family": {"role_family", "job_family", "category", "career_field"},
    "company": {"company", "company_name", "employer", "organization"},
    "industry": {"industry", "sector"},
    "city": {"city", "job_city"},
    "state": {"state", "province", "region", "job_state"},
    "country": {"country", "nation"},
    "location": {"location", "job_location"},
    "work_mode": {"work_mode", "work_arrangement", "remote_type", "workplace_type"},
    "experience_level": {"experience_level", "seniority", "level", "career_level"},
    "employment_type": {"employment_type", "job_type", "type"},
    "salary_min": {"salary_min", "min_salary", "minimum_salary", "salary_from"},
    "salary_max": {"salary_max", "max_salary", "maximum_salary", "salary_to"},
    "salary_period": {"salary_period", "pay_period"},
    "salary_currency": {"salary_currency", "currency"},
    "required_skills": {"required_skills", "skills", "skills_required", "requirements"},
    "preferred_skills": {"preferred_skills", "nice_to_have", "preferred_qualifications"},
    "education_requirement": {"education_requirement", "education", "degree_requirement"},
    "years_experience_required": {"years_experience_required", "years_experience", "experience_years"},
    "remote_eligible": {"remote_eligible", "is_remote", "remote"},
    "description_excerpt": {"description_excerpt", "description", "job_description", "summary"},
    "recruiter_name": {"recruiter_name", "contact_name", "recruiter"},
    "recruiter_email": {"recruiter_email", "contact_email", "email"},
    "recruiter_phone": {"recruiter_phone", "contact_phone", "phone"},
    "source_type": {"source_type", "source", "source_name"},
    "source_record_id": {"source_record_id", "source_id", "external_id"},
    "synthetic_record": {"synthetic_record", "is_synthetic"},
}

ROLE_KEYWORDS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"embedded|firmware|iot", re.I), "Embedded Systems Engineer", "Electrical & Hardware Engineering"),
    (re.compile(r"electrical|power systems|electrical design", re.I), "Electrical Engineer", "Electrical & Hardware Engineering"),
    (re.compile(r"automation|controls|plc", re.I), "Automation Engineer", "Electrical & Hardware Engineering"),
    (re.compile(r"cyber|security operations|soc analyst|information security", re.I), "Cybersecurity Analyst", "Cybersecurity"),
    (re.compile(r"network|infrastructure", re.I), "Network Engineer", "Information Technology"),
    (re.compile(r"support|help desk|desktop", re.I), "IT Support Specialist", "Information Technology"),
    (re.compile(r"product analyst|product data", re.I), "Product Analyst", "Data & Analytics"),
    (re.compile(r"data analyst|reporting analyst|business data", re.I), "Data Analyst", "Data & Analytics"),
    (re.compile(r"junior developer|web developer|associate software|entry-level developer", re.I), "Junior Developer", "Software Engineering"),
    (re.compile(r"software|backend|full stack|application developer", re.I), "Software Engineer", "Software Engineering"),
]

WORK_MODE_MAP = {
    "remote": "Remote",
    "fully remote": "Remote",
    "work from home": "Remote",
    "hybrid": "Hybrid",
    "on-site": "On-site",
    "onsite": "On-site",
    "in office": "On-site",
}

EXPERIENCE_MAP = {
    "intern": "Internship",
    "internship": "Internship",
    "entry": "Entry Level",
    "entry level": "Entry Level",
    "entry-level": "Entry Level",
    "new grad": "Entry Level",
    "junior": "Entry Level",
    "associate": "Associate",
    "mid": "Mid Level",
    "mid level": "Mid Level",
    "mid-level": "Mid Level",
    "senior": "Senior",
    "sr": "Senior",
}


def normalize_column_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", str(value).strip().lower())
    return value.strip("_")


def map_columns(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    normalized = {column: normalize_column_name(column) for column in frame.columns}
    reverse_alias: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            reverse_alias[normalize_column_name(alias)] = canonical

    rename: dict[str, str] = {}
    mapping: dict[str, str] = {}
    occupied: set[str] = set()
    for original, normalized_name in normalized.items():
        canonical = reverse_alias.get(normalized_name, normalized_name)
        if canonical in occupied:
            canonical = normalized_name
        rename[original] = canonical
        mapping[original] = canonical
        occupied.add(canonical)
    return frame.rename(columns=rename).copy(), mapping


def _infer_role(title: object) -> tuple[str, str]:
    text = str(title or "")
    for pattern, role, family in ROLE_KEYWORDS:
        if pattern.search(text):
            return role, family
    return "Other", "Other"


def _normalize_skills(value: object) -> str:
    if value is None or (isinstance(value, float) and math_is_nan(value)):
        return ""
    raw = re.split(r"\s*(?:\||;|,|\n)\s*", str(value))
    cleaned: list[str] = []
    seen: set[str] = set()
    for skill in raw:
        skill = re.sub(r"\s+", " ", skill).strip()
        if not skill:
            continue
        key = skill.casefold()
        if key not in seen:
            cleaned.append(skill)
            seen.add(key)
    return " | ".join(cleaned)


def math_is_nan(value: float) -> bool:
    return bool(np.isnan(value))


def _near_duplicate_count(frame: pd.DataFrame) -> int:
    columns = [c for c in ["job_title", "company", "city", "state", "date_posted"] if c in frame]
    if len(columns) < 3 or frame.empty:
        return 0
    keys = frame[columns].fillna("").astype(str).agg("|".join, axis=1)
    counts = Counter(keys)
    return sum(max(count - 1, 0) for count in counts.values())


def _quality_score(
    cleaned: pd.DataFrame,
    raw_rows: int,
    duplicate_count: int,
    invalid_count: int,
    required_columns: Iterable[str],
) -> int:
    if raw_rows == 0:
        return 0
    completeness = 1.0 - float(cleaned[list(required_columns)].isna().mean().mean()) if required_columns else 1.0
    duplicate_penalty = min(duplicate_count / raw_rows, 0.15)
    invalid_penalty = min(invalid_count / raw_rows, 0.20)
    size_score = min(len(cleaned) / 100.0, 1.0)
    score = 100 * (0.55 * completeness + 0.20 * size_score + 0.25 * (1 - duplicate_penalty - invalid_penalty))
    if duplicate_count:
        score -= 2.5
    if invalid_count:
        score -= 3.5
    return int(max(0, min(round(score), 100)))


def clean_job_data(frame: pd.DataFrame) -> tuple[pd.DataFrame, DataQualityReport]:
    raw_rows = len(frame)
    mapped, schema_mapping = map_columns(frame)
    work = mapped.copy()
    issues: list[DataIssue] = []
    actions: list[CleaningAction] = []

    if "location" in work.columns:
        location_parts = work["location"].fillna("").astype(str).str.split(",", n=1, expand=True)
        if "city" not in work:
            work["city"] = location_parts[0].str.strip()
            actions.append(CleaningAction(action="derived_city", count=int(work["city"].ne("").sum()), detail="Derived city from the location column."))
        if "state" not in work and location_parts.shape[1] > 1:
            work["state"] = location_parts[1].str.strip().str[:2].str.upper()
            actions.append(CleaningAction(action="derived_state", count=int(work["state"].ne("").sum()), detail="Derived state from the location column."))

    if "job_title" not in work:
        work["job_title"] = "Unknown role"
        issues.append(DataIssue(severity="error", code="missing_job_title", message="The upload did not contain a recognizable job-title column.", columns=["job_title"]))
    if "company" not in work:
        work["company"] = "Unknown company"
        issues.append(DataIssue(severity="warning", code="missing_company", message="Company was missing and was filled with 'Unknown company'.", columns=["company"]))

    if "posting_id" not in work:
        work["posting_id"] = [f"UPLOAD-{i + 1:06d}" for i in range(len(work))]
        actions.append(CleaningAction(action="generated_posting_ids", count=len(work), detail="Generated stable row identifiers because no posting ID was supplied."))
    work["posting_id"] = work["posting_id"].astype(str).str.strip()
    blank_ids = work["posting_id"].eq("") | work["posting_id"].eq("nan")
    if blank_ids.any():
        for idx in work.index[blank_ids]:
            work.at[idx, "posting_id"] = f"UPLOAD-{idx + 1:06d}"
        actions.append(CleaningAction(action="filled_blank_posting_ids", count=int(blank_ids.sum()), detail="Filled blank posting identifiers."))

    duplicate_id_mask = work.duplicated(subset=["posting_id"], keep="first")
    removed_duplicate_ids = int(duplicate_id_mask.sum())
    if removed_duplicate_ids:
        work = work.loc[~duplicate_id_mask].copy()
        issues.append(DataIssue(severity="warning", code="duplicate_posting_id", message="Duplicate posting IDs were removed from analysis, keeping the first occurrence.", count=removed_duplicate_ids, columns=["posting_id"]))
        actions.append(CleaningAction(action="removed_duplicate_posting_ids", count=removed_duplicate_ids, detail="Kept the first row for each duplicated posting ID."))

    exact_subset = [c for c in work.columns if c not in {"posting_id", "source_record_id"}]
    exact_mask = work.duplicated(subset=exact_subset, keep="first") if exact_subset else pd.Series(False, index=work.index)
    removed_exact = int(exact_mask.sum())
    if removed_exact:
        work = work.loc[~exact_mask].copy()
        issues.append(DataIssue(severity="warning", code="exact_duplicate", message="Exact duplicate records were removed from analysis.", count=removed_exact))
        actions.append(CleaningAction(action="removed_exact_duplicates", count=removed_exact, detail="Removed duplicate rows after excluding row identifiers."))

    if "date_posted" not in work:
        work["date_posted"] = pd.NaT
        issues.append(DataIssue(severity="warning", code="missing_date_posted", message="Posting dates were not available; trend questions will be refused.", columns=["date_posted"]))
    parsed_dates = pd.to_datetime(work["date_posted"], errors="coerce")
    invalid_dates = int(parsed_dates.isna().sum() - work["date_posted"].isna().sum())
    work["date_posted"] = parsed_dates
    if invalid_dates:
        issues.append(DataIssue(severity="warning", code="invalid_dates", message="Invalid posting dates were converted to missing values.", count=invalid_dates, columns=["date_posted"]))
        actions.append(CleaningAction(action="coerced_invalid_dates", count=invalid_dates, detail="Invalid dates became missing instead of being guessed."))

    inferred = work["job_title"].map(_infer_role)
    if "normalized_role" not in work:
        work["normalized_role"] = inferred.map(lambda item: item[0])
        actions.append(CleaningAction(action="inferred_roles", count=len(work), detail="Mapped job titles into a small allowlisted role taxonomy."))
    else:
        work["normalized_role"] = work["normalized_role"].fillna("").astype(str).str.strip()
        missing_role = work["normalized_role"].eq("")
        work.loc[missing_role, "normalized_role"] = inferred[missing_role].map(lambda item: item[0])
    if "role_family" not in work:
        role_to_family = {role: family for _, role, family in ROLE_KEYWORDS}
        work["role_family"] = work["normalized_role"].map(role_to_family).fillna(inferred.map(lambda item: item[1]))
    else:
        work["role_family"] = work["role_family"].fillna("Other")

    defaults: dict[str, object] = {
        "industry": "Unknown",
        "city": "Unknown",
        "state": "Unknown",
        "country": "United States",
        "employment_type": "Unknown",
        "salary_period": "year",
        "salary_currency": "USD",
        "preferred_skills": "",
        "education_requirement": "Unknown",
        "years_experience_required": np.nan,
        "remote_eligible": False,
        "description_excerpt": "",
        "recruiter_name": "",
        "recruiter_email": "",
        "recruiter_phone": "",
        "source_type": "uploaded_csv",
        "source_record_id": "",
        "synthetic_record": False,
    }
    for column, default in defaults.items():
        if column not in work:
            work[column] = default

    if "work_mode" not in work:
        work["work_mode"] = "Unknown"
        issues.append(DataIssue(severity="warning", code="missing_work_mode", message="Work mode was not available; related questions may be refused.", columns=["work_mode"]))
    normalized_modes = work["work_mode"].fillna("").astype(str).str.strip().str.casefold().map(WORK_MODE_MAP)
    unknown_modes_mask = normalized_modes.isna() & work["work_mode"].fillna("").astype(str).str.strip().ne("")
    unknown_work_modes = int(unknown_modes_mask.sum())
    work["work_mode"] = normalized_modes.fillna("Unknown")
    if unknown_work_modes:
        issues.append(DataIssue(severity="warning", code="unknown_work_modes", message="Unrecognized work-mode values were labeled Unknown.", count=unknown_work_modes, columns=["work_mode"]))

    if "experience_level" not in work:
        work["experience_level"] = "Unknown"
        issues.append(DataIssue(severity="warning", code="missing_experience", message="Experience level was not available; related questions may be refused.", columns=["experience_level"]))
    normalized_exp = work["experience_level"].fillna("").astype(str).str.strip().str.casefold().map(EXPERIENCE_MAP)
    original_valid = work["experience_level"].isin(SUPPORTED_EXPERIENCE_LEVELS)
    normalized_exp.loc[original_valid] = work.loc[original_valid, "experience_level"]
    unknown_exp_mask = normalized_exp.isna() & work["experience_level"].fillna("").astype(str).str.strip().ne("")
    unknown_experience = int(unknown_exp_mask.sum())
    work["experience_level"] = normalized_exp.fillna("Unknown")
    if unknown_experience:
        issues.append(DataIssue(severity="warning", code="unknown_experience", message="Unrecognized experience levels were labeled Unknown.", count=unknown_experience, columns=["experience_level"]))

    for salary_column in ["salary_min", "salary_max"]:
        if salary_column not in work:
            work[salary_column] = np.nan
        work[salary_column] = pd.to_numeric(work[salary_column], errors="coerce")
    invalid_salary = (
        (work["salary_min"] < 0)
        | (work["salary_max"] < 0)
        | (work["salary_min"].notna() & work["salary_max"].notna() & (work["salary_min"] > work["salary_max"]))
    )
    invalid_salary_rows = int(invalid_salary.sum())
    if invalid_salary_rows:
        work.loc[invalid_salary, ["salary_min", "salary_max"]] = np.nan
        issues.append(DataIssue(severity="warning", code="invalid_salary", message="Invalid salary ranges were excluded from salary analysis rather than repaired by guessing.", count=invalid_salary_rows, columns=["salary_min", "salary_max"]))
        actions.append(CleaningAction(action="excluded_invalid_salary_ranges", count=invalid_salary_rows, detail="Set invalid salary endpoints to missing values."))

    both_present = work["salary_min"].notna() & work["salary_max"].notna()
    work["salary_midpoint"] = np.where(both_present, (work["salary_min"] + work["salary_max"]) / 2.0, np.nan)
    work["salary_disclosed"] = both_present

    if "required_skills" not in work:
        work["required_skills"] = ""
        issues.append(DataIssue(severity="warning", code="missing_skills", message="Required skills were not available; skill questions will be refused.", columns=["required_skills"]))
    work["required_skills"] = work["required_skills"].map(_normalize_skills)
    work["preferred_skills"] = work["preferred_skills"].map(_normalize_skills)

    for column in ["company", "city", "state", "country", "industry", "employment_type"]:
        work[column] = work[column].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")

    work["remote_eligible"] = work["work_mode"].isin({"Remote", "Hybrid"})
    work["synthetic_record"] = work["synthetic_record"].fillna(False).astype(bool)

    near_duplicates = _near_duplicate_count(work)
    if near_duplicates:
        issues.append(DataIssue(severity="info", code="near_duplicates", message="Potential near-duplicate listings are retained and disclosed for review.", count=near_duplicates))

    missing_by_column: dict[str, int] = {}
    for column in work.columns:
        missing_mask = work[column].isna()
        if work[column].dtype == object:
            missing_mask = missing_mask | work[column].fillna("").astype(str).str.strip().eq("")
        missing_by_column[column] = int(missing_mask.sum())
    missing_salary_rows = int((~work["salary_disclosed"]).sum())
    missing_salary_percentage = float(missing_salary_rows / len(work)) if len(work) else 0.0
    pii_detected = [column for column in work.columns if column in PII_COLUMNS or any(token in column for token in ["email", "phone", "contact_name", "recruiter_name"])]

    required_for_score = [c for c in ["job_title", "company", "date_posted", "normalized_role", "required_skills"] if c in work]
    quality_score = _quality_score(work, raw_rows, removed_duplicate_ids + removed_exact, invalid_dates + invalid_salary_rows, required_for_score)

    date_non_null = work["date_posted"].dropna()
    report = DataQualityReport(
        raw_rows=raw_rows,
        cleaned_rows=len(work),
        removed_duplicate_ids=removed_duplicate_ids,
        removed_exact_duplicates=removed_exact,
        near_duplicate_candidates=near_duplicates,
        invalid_dates=invalid_dates,
        invalid_salary_rows=invalid_salary_rows,
        unknown_work_modes=unknown_work_modes,
        unknown_experience_levels=unknown_experience,
        missing_salary_rows=missing_salary_rows,
        missing_salary_percentage=missing_salary_percentage,
        missing_by_column=missing_by_column,
        columns_detected=list(work.columns),
        pii_columns_detected=sorted(pii_detected),
        date_min=date_non_null.min().date().isoformat() if not date_non_null.empty else None,
        date_max=date_non_null.max().date().isoformat() if not date_non_null.empty else None,
        quality_score=quality_score,
        schema_mapping=schema_mapping,
        issues=issues,
        cleaning_actions=actions,
    )
    return work.reset_index(drop=True), report


def dataframe_fingerprint(frame: pd.DataFrame) -> str:
    if frame.empty:
        return hashlib.sha256(b"empty").hexdigest()[:16]
    stable = frame.copy()
    for column in stable.columns:
        if pd.api.types.is_datetime64_any_dtype(stable[column]):
            stable[column] = stable[column].dt.strftime("%Y-%m-%dT%H:%M:%S")
    stable = stable.sort_values(by=["posting_id"] if "posting_id" in stable else list(stable.columns)[:1])
    payload = stable.to_csv(index=False, na_rep="<NA>", lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]
