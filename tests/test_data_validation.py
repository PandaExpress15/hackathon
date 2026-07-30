from __future__ import annotations

from careerproof.config import CORE_ANALYSIS_COLUMNS


def test_sample_dataset_has_more_than_minimum_rows(bundle):
    assert len(bundle.raw) >= 250
    assert len(bundle.cleaned) >= 250


def test_required_analysis_columns_exist(bundle):
    assert CORE_ANALYSIS_COLUMNS.issubset(bundle.cleaned.columns)


def test_dataset_is_deterministic_and_synthetic(bundle):
    assert bundle.fingerprint == "d1d0cd52e1bda4c6"
    assert bundle.is_synthetic is True
    assert bundle.cleaned["synthetic_record"].all()


def test_dates_and_salary_midpoints_are_typed(bundle):
    assert str(bundle.cleaned["date_posted"].dtype).startswith("datetime64")
    salary_rows = bundle.cleaned[bundle.cleaned["salary_midpoint"].notna()]
    assert not salary_rows.empty
    expected = (salary_rows["salary_min"] + salary_rows["salary_max"]) / 2
    assert (salary_rows["salary_midpoint"] == expected).all()
