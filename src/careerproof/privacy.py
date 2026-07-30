"""Privacy controls for masking sensitive information before display or export."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd

from .config import PII_COLUMNS

EMAIL_RE = re.compile(r"\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\d)")
URL_RE = re.compile(r"https?://[^\s<>'\"]+", re.I)
LONG_ID_RE = re.compile(r"\b(?:[A-Z]{2,}[-_])?[A-Z0-9]{8,}\b", re.I)
SENSITIVE_QUERY_KEYS = {"token", "key", "api_key", "secret", "password", "auth", "email", "phone"}


def mask_email(value: object) -> str:
    text = str(value or "")
    match = EMAIL_RE.search(text)
    if not match:
        return text
    local, domain = match.groups()
    parts = local.split(".")
    masked_parts = []
    for part in parts:
        if not part:
            masked_parts.append("")
        elif len(part) == 1:
            masked_parts.append(part + "*")
        else:
            masked_parts.append(part[0] + "*" * max(3, min(len(part) - 1, 5)))
    masked = ".".join(masked_parts) + "@" + domain
    return text[: match.start()] + masked + text[match.end() :]


def mask_phone(value: object) -> str:
    text = str(value or "")
    match = PHONE_RE.search(text)
    if not match:
        return text
    digits = re.sub(r"\D", "", match.group(0))
    last_four = digits[-4:] if len(digits) >= 4 else "****"
    return text[: match.start()] + f"***-***-{last_four}" + text[match.end() :]


def mask_name(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return ""
    masked: list[str] = []
    for part in text.split(" "):
        if len(part) <= 1:
            masked.append(part + "*")
        else:
            masked.append(part[0] + "*" * min(max(len(part) - 1, 2), 6))
    return " ".join(masked)


def mask_identifier(value: object) -> str:
    text = str(value or "")
    if len(text) <= 4:
        return "****"
    return "ID-****" + text[-4:]


def _sanitize_url(match: re.Match[str]) -> str:
    value = match.group(0)
    try:
        parts = urlsplit(value)
        safe_query = []
        for key, val in parse_qsl(parts.query, keep_blank_values=True):
            safe_query.append((key, "***" if key.casefold() in SENSITIVE_QUERY_KEYS else val))
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(safe_query), parts.fragment))
    except ValueError:
        return "[masked-url]"


def mask_text(value: object) -> str:
    text = str(value or "")
    text = URL_RE.sub(_sanitize_url, text)
    text = EMAIL_RE.sub(lambda m: mask_email(m.group(0)), text)
    text = PHONE_RE.sub(lambda m: mask_phone(m.group(0)), text)
    return text


def _mask_scalar_for_key(value: object, key: str | None = None) -> object:
    """Mask a scalar using the surrounding field name when one is available."""

    if value is None or isinstance(value, (bool, int, float)):
        return value
    normalized = (key or "").casefold()
    if "email" in normalized:
        return mask_email(value)
    if "phone" in normalized:
        return mask_phone(value)
    if normalized in {"recruiter_name", "contact_name", "person_name", "candidate_name"}:
        return mask_name(value)
    if normalized in {"source_record_id"} or normalized.endswith("_external_id"):
        return mask_identifier(value)
    return mask_text(value)


def mask_structure(value: Any, *, key: str | None = None) -> Any:
    """Recursively mask PII in JSON-like data before display, export, or logging.

    Proof bundles and audit records contain nested dictionaries and lists. Applying
    the same privacy rules used for dataframes prevents a user-entered email, phone
    number, or sensitive filter value from leaking through a JSON export.
    """

    if isinstance(value, Mapping):
        return {str(item_key): mask_structure(item_value, key=str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [mask_structure(item, key=key) for item in value]
    return _mask_scalar_for_key(value, key)


def detect_pii_columns(frame: pd.DataFrame) -> list[str]:
    detected: set[str] = set()
    for column in frame.columns:
        normalized = column.casefold()
        if column in PII_COLUMNS or any(token in normalized for token in ["email", "phone", "recruiter", "contact_name", "person_name"]):
            detected.add(column)
            continue
        if frame[column].dtype == object:
            sample = frame[column].dropna().astype(str).head(50)
            if sample.map(lambda value: bool(EMAIL_RE.search(value) or PHONE_RE.search(value))).mean() > 0.10 if len(sample) else False:
                detected.add(column)
    return sorted(detected)


def mask_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    masked = frame.copy()
    for column in masked.columns:
        normalized = column.casefold()
        if normalized in {"recruiter_name", "contact_name", "person_name"} or ("name" in normalized and "company" not in normalized):
            masked[column] = masked[column].map(mask_name)
        elif "email" in normalized:
            masked[column] = masked[column].map(mask_email)
        elif "phone" in normalized:
            masked[column] = masked[column].map(mask_phone)
        elif column in {"source_record_id"} or normalized.endswith("_external_id"):
            masked[column] = masked[column].map(mask_identifier)
        elif masked[column].dtype == object:
            masked[column] = masked[column].map(mask_text)
    return masked


def contains_unmasked_pii(text: str) -> bool:
    return bool(EMAIL_RE.search(text) or PHONE_RE.search(text))
