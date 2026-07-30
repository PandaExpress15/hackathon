"""Dataset loading helpers for bundled and user-provided CSV files."""

from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from .config import MAX_UPLOAD_COLUMNS, MAX_UPLOAD_ROWS, PROCESSED_DATA_PATH, RAW_DATA_PATH
from .data_cleaning import clean_job_data, dataframe_fingerprint
from .schema import DatasetBundle


def _read_tabular(source: str | Path | bytes | BinaryIO) -> pd.DataFrame:
    if isinstance(source, bytes):
        source = BytesIO(source)
    if isinstance(source, (str, Path)):
        path = Path(source)
        suffix = path.suffix.lower()
        try:
            if suffix == ".csv":
                return pd.read_csv(path)
            if suffix in {".xlsx", ".xlsm"}:
                return pd.read_excel(path)
        except pd.errors.EmptyDataError as exc:
            raise ValueError("The uploaded file is empty or has no readable columns.") from exc
        raise ValueError("Only CSV and XLSX files are supported.")

    name = getattr(source, "name", "").lower()
    if name.endswith((".xlsx", ".xlsm")):
        return pd.read_excel(source)
    try:
        return pd.read_csv(source)
    except pd.errors.EmptyDataError as exc:
        raise ValueError("The uploaded file is empty or has no readable columns.") from exc
    except UnicodeDecodeError:
        if hasattr(source, "seek"):
            source.seek(0)
        content = source.read().decode("latin-1")
        try:
            return pd.read_csv(StringIO(content))
        except pd.errors.EmptyDataError as exc:
            raise ValueError("The uploaded file is empty or has no readable columns.") from exc


def _validate_upload_shape(raw: pd.DataFrame) -> None:
    if raw.empty:
        raise ValueError("The uploaded file contains no data rows.")
    if len(raw.columns) > MAX_UPLOAD_COLUMNS:
        raise ValueError(
            f"The uploaded file has {len(raw.columns):,} columns. "
            f"CareerProof accepts at most {MAX_UPLOAD_COLUMNS:,} columns per upload."
        )
    if len(raw) > MAX_UPLOAD_ROWS:
        raise ValueError(
            f"The uploaded file has {len(raw):,} rows. "
            f"CareerProof accepts at most {MAX_UPLOAD_ROWS:,} rows per upload."
        )


def load_dataset(
    source: str | Path | bytes | BinaryIO = RAW_DATA_PATH,
    *,
    display_name: str | None = None,
    persist_processed: bool = False,
) -> DatasetBundle:
    raw = _read_tabular(source)
    _validate_upload_shape(raw)
    cleaned, report = clean_job_data(raw)
    fingerprint = dataframe_fingerprint(cleaned)
    if persist_processed:
        PROCESSED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        cleaned.to_csv(PROCESSED_DATA_PATH, index=False)
    if display_name:
        inferred_name = display_name
    elif isinstance(source, (str, Path)):
        inferred_name = Path(source).name
    else:
        inferred_name = getattr(source, "name", None) or "Uploaded dataset"
    is_synthetic = bool(cleaned.get("synthetic_record", pd.Series(False, index=cleaned.index)).all()) if not cleaned.empty else False
    return DatasetBundle(
        raw=raw,
        cleaned=cleaned,
        report=report,
        fingerprint=fingerprint,
        display_name=str(inferred_name),
        is_synthetic=is_synthetic,
    )


def load_bundled_dataset() -> DatasetBundle:
    return load_dataset(RAW_DATA_PATH, display_name="CareerProof synthetic job postings", persist_processed=True)
