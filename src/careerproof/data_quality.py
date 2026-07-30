"""Utilities for presenting data-quality details."""

from __future__ import annotations

import pandas as pd

from .schema import DataQualityReport


def issues_dataframe(report: DataQualityReport) -> pd.DataFrame:
    rows = [
        {
            "Severity": issue.severity.title(),
            "Code": issue.code,
            "Count": issue.count,
            "Message": issue.message,
            "Columns": ", ".join(issue.columns),
        }
        for issue in report.issues
    ]
    return pd.DataFrame(rows, columns=["Severity", "Code", "Count", "Message", "Columns"])


def cleaning_actions_dataframe(report: DataQualityReport) -> pd.DataFrame:
    rows = [
        {"Action": action.action, "Rows affected": action.count, "What happened": action.detail}
        for action in report.cleaning_actions
    ]
    return pd.DataFrame(rows, columns=["Action", "Rows affected", "What happened"])


def missingness_dataframe(report: DataQualityReport) -> pd.DataFrame:
    frame = pd.DataFrame(
        [{"Field": column, "Missing": count} for column, count in report.missing_by_column.items()]
    )
    if frame.empty:
        return frame
    frame["Percent"] = frame["Missing"] / max(report.cleaned_rows, 1) * 100
    return frame.sort_values(["Missing", "Field"], ascending=[False, True]).reset_index(drop=True)


def quality_report_markdown(report: DataQualityReport) -> str:
    return "\n".join(
        [
            "# CareerProof AI Data Quality Report",
            "",
            f"- Quality score: **{report.quality_score}/100**",
            f"- Raw rows: **{report.raw_rows:,}**",
            f"- Cleaned rows: **{report.cleaned_rows:,}**",
            f"- Duplicate IDs removed: **{report.removed_duplicate_ids:,}**",
            f"- Invalid salary rows excluded: **{report.invalid_salary_rows:,}**",
            f"- Missing salary: **{report.missing_salary_percentage:.1%}**",
            f"- Date range: **{report.date_min or 'Unavailable'}** to **{report.date_max or 'Unavailable'}**",
            "",
            "## Issues",
            *[f"- [{issue.severity.upper()}] {issue.message} ({issue.count})" for issue in report.issues],
            "",
            "## Cleaning actions",
            *[f"- {action.detail} ({action.count})" for action in report.cleaning_actions],
        ]
    )
