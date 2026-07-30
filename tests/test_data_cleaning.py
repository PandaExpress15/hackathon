from __future__ import annotations

from io import StringIO

import pandas as pd

from careerproof.data_cleaning import clean_job_data
from careerproof.data_loader import load_dataset


def test_duplicate_ids_are_reported_and_removed(bundle):
    assert bundle.report.removed_duplicate_ids == 8
    assert bundle.cleaned["posting_id"].is_unique


def test_invalid_salaries_are_excluded_not_guessed(bundle):
    assert bundle.report.invalid_salary_rows == 3
    assert not (bundle.cleaned["salary_min"].dropna() < 0).any()
    valid_both = bundle.cleaned[["salary_min", "salary_max"]].dropna()
    assert (valid_both["salary_min"] <= valid_both["salary_max"]).all()


def test_cleaning_ledger_discloses_actions(bundle):
    actions = {item.action for item in bundle.report.cleaning_actions}
    assert "removed_duplicate_posting_ids" in actions
    assert "excluded_invalid_salary_ranges" in actions


def test_flexible_upload_maps_common_aliases():
    csv = StringIO(
        "id,title,employer,posted_date,location,skills,min_salary,max_salary,remote_type,seniority\n"
        "1,Junior Data Analyst,Example Corp,2026-07-01,Seattle WA,SQL;Excel,50000,65000,remote,new grad\n"
    )
    bundle = load_dataset(csv, display_name="alias.csv")
    row = bundle.cleaned.iloc[0]
    assert row["job_title"] == "Junior Data Analyst"
    assert row["company"] == "Example Corp"
    assert row["normalized_role"] == "Data Analyst"
    assert row["work_mode"] == "Remote"
    assert row["experience_level"] == "Entry Level"
    assert row["required_skills"] == "SQL | Excel"


def test_empty_skills_are_visible_as_missing():
    frame = pd.DataFrame({"title": ["Software Engineer"], "company": ["A"], "skills": [""]})
    cleaned, report = clean_job_data(frame)
    assert cleaned.loc[0, "required_skills"] == ""
    assert report.missing_by_column["required_skills"] == 1
