from __future__ import annotations

from io import StringIO

import pandas as pd
import pytest

from careerproof.config import MAX_UPLOAD_COLUMNS
from careerproof.data_loader import load_dataset


def test_empty_upload_has_clear_validation_message():
    with pytest.raises(ValueError, match="empty or has no readable columns"):
        load_dataset(StringIO(""), display_name="empty.csv")


def test_header_only_upload_is_rejected():
    with pytest.raises(ValueError, match="contains no data rows"):
        load_dataset(StringIO("title,company,skills\n"), display_name="header-only.csv")


def test_excessively_wide_upload_is_rejected():
    columns = {f"unexpected_{index}": ["value"] for index in range(MAX_UPLOAD_COLUMNS + 1)}
    frame = pd.DataFrame(columns)
    with pytest.raises(ValueError, match=f"at most {MAX_UPLOAD_COLUMNS:,} columns"):
        load_dataset(StringIO(frame.to_csv(index=False)), display_name="too-wide.csv")


def test_missing_job_title_is_disclosed_not_silently_hidden():
    bundle = load_dataset(
        StringIO("company,city,skills\nExample Corp,Seattle,Python;SQL\n"),
        display_name="missing-title.csv",
    )
    assert bundle.cleaned.iloc[0]["job_title"] == "Unknown role"
    assert any(issue.code == "missing_job_title" and issue.severity == "error" for issue in bundle.report.issues)
