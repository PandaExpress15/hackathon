from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
METADATA = ROOT / "data" / "metadata"

RPP_2024 = {
    "Alabama": 88.823,
    "Alaska": 102.359,
    "Arizona": 100.677,
    "Arkansas": 86.937,
    "California": 110.720,
    "Colorado": 103.052,
    "Connecticut": 103.610,
    "Delaware": 99.808,
    "District of Columbia": 109.901,
    "Florida": 103.414,
    "Georgia": 96.293,
    "Hawaii": 109.951,
    "Idaho": 95.494,
    "Illinois": 99.958,
    "Indiana": 93.329,
    "Iowa": 87.762,
    "Kansas": 90.068,
    "Kentucky": 90.159,
    "Louisiana": 88.207,
    "Maine": 97.050,
    "Maryland": 104.959,
    "Massachusetts": 105.757,
    "Michigan": 96.217,
    "Minnesota": 98.621,
    "Mississippi": 86.953,
    "Missouri": 90.817,
    "Montana": 94.645,
    "Nebraska": 90.103,
    "Nevada": 99.979,
    "New Hampshire": 104.165,
    "New Jersey": 108.805,
    "New Mexico": 92.212,
    "New York": 107.921,
    "North Carolina": 94.326,
    "North Dakota": 88.959,
    "Ohio": 92.774,
    "Oklahoma": 87.843,
    "Oregon": 103.361,
    "Pennsylvania": 97.572,
    "Rhode Island": 102.280,
    "South Carolina": 93.749,
    "South Dakota": 88.586,
    "Tennessee": 91.870,
    "Texas": 97.057,
    "Utah": 98.864,
    "Vermont": 97.958,
    "Virginia": 101.104,
    "Washington": 107.013,
    "West Virginia": 89.497,
    "Wisconsin": 94.095,
    "Wyoming": 92.691,
}

STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA",
    "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_rpp() -> Path:
    rows = []
    for state, value in RPP_2024.items():
        rows.append({
            "state_name": state,
            "state_abbreviation": STATE_ABBR[state],
            "regional_price_parity_2024": value,
            "national_price_level": 100.0,
            "price_level_difference_percent": round(value - 100.0, 3),
            "source_vintage": "BEA Regional Price Parities 2024, released February 2026",
            "source_url": "https://www.bea.gov/data/prices-inflation/regional-price-parities-state-and-metro-area",
            "calculation_note": "Purchasing-power wage = nominal wage * 100 / regional price parity.",
        })
    path = PROCESSED / "regional_price_parities_2024.csv"
    pd.DataFrame(rows).sort_values("state_name").to_csv(path, index=False)
    return path


def clean_code(value: object, digits: int) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    if digits == 6 and "." in text:
        left, right = text.split(".", 1)
        text = f"{left.zfill(2)}.{right.ljust(4, '0')[:4]}"
    return text


def build_crosswalk() -> Path:
    raw_path = RAW / "CIP2020_SOC2018_Crosswalk.xlsx"
    if not raw_path.exists():
        raise FileNotFoundError(f"Missing official NCES crosswalk: {raw_path}")
    frame = pd.read_excel(raw_path, sheet_name="CIP-SOC")
    frame = frame.rename(columns={
        "CIP2020Code": "cip_code",
        "CIP2020Title": "cip_title",
        "SOC2018Code": "soc_code",
        "SOC2018Title": "soc_title",
    })
    frame["cip_code"] = frame["cip_code"].map(lambda value: clean_code(value, 6))
    frame["soc_code"] = frame["soc_code"].astype(str).str.strip()
    frame["cip_title"] = frame["cip_title"].astype(str).str.strip().str.rstrip(".")
    frame["soc_title"] = frame["soc_title"].astype(str).str.strip()
    frame = frame.loc[
        frame["cip_code"].ne("99.9999")
        & frame["cip_title"].ne("NO MATCH")
        & frame["soc_code"].str.match(r"^\d{2}-\d{4}$", na=False)
    ].copy()
    frame["relationship_type"] = "NCES/BLS qualitative CIP-to-SOC crosswalk"
    frame["source_vintage"] = "CIP 2020 to SOC 2018"
    frame["source_url"] = "https://nces.ed.gov/ipeds/cipcode/post3.aspx?y=56"
    frame["limitation"] = "Descriptive conceptual match; not a probability, placement rate, or guaranteed career outcome."
    frame = frame.drop_duplicates(subset=["cip_code", "soc_code"]).sort_values(["cip_title", "soc_title"])
    path = PROCESSED / "degree_career_crosswalk.csv"
    frame.to_csv(path, index=False)
    return path


def update_catalog(rpp_path: Path, crosswalk_path: Path) -> None:
    catalog_path = METADATA / "data_catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    sources = [source for source in catalog.get("sources", []) if source.get("id") not in {"bea-rpp-2024", "nces-cip-soc-2020-2018"}]
    sources.extend([
        {
            "id": "bea-rpp-2024",
            "title": "Regional Price Parities by State",
            "agency": "U.S. Bureau of Economic Analysis",
            "vintage": "2024, released February 2026",
            "authoritative_url": "https://www.bea.gov/data/prices-inflation/regional-price-parities-state-and-metro-area",
            "local_raw_file": "Bundled verified state snapshot in data/processed/regional_price_parities_2024.csv",
            "license": "U.S. federal government public data",
            "coverage": "Relative state price levels used for transparent purchasing-power wage comparisons",
        },
        {
            "id": "nces-cip-soc-2020-2018",
            "title": "CIP 2020 to SOC 2018 Crosswalk",
            "agency": "National Center for Education Statistics and U.S. Bureau of Labor Statistics",
            "vintage": "CIP 2020 / SOC 2018",
            "authoritative_url": "https://nces.ed.gov/ipeds/cipcode/post3.aspx?y=56",
            "download_url": "https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx",
            "local_raw_file": "data/raw/CIP2020_SOC2018_Crosswalk.xlsx",
            "license": "U.S. federal government public data",
            "coverage": "Qualitative links between postsecondary instructional programs and detailed occupations",
        },
    ])
    catalog["sources"] = sources
    catalog["product_note"] = (
        "All bundled labor-market and education relationship records come from official U.S. government or O*NET sources. "
        "CareerProof-derived scores are labeled and expose their formulas. No synthetic labor-market records are used."
    )
    catalog.setdefault("raw_file_checksums", {})["data/raw/CIP2020_SOC2018_Crosswalk.xlsx"] = {
        "bytes": (RAW / "CIP2020_SOC2018_Crosswalk.xlsx").stat().st_size,
        "sha256": sha256(RAW / "CIP2020_SOC2018_Crosswalk.xlsx"),
    }
    for key, path in {
        "regional_price_parities": rpp_path,
        "degree_career_crosswalk": crosswalk_path,
    }.items():
        rows = len(pd.read_csv(path, low_memory=False))
        catalog.setdefault("processed_file_checksums", {})[key] = {
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "rows": rows,
        }
    catalog["generated_at"] = "2026-07-30"
    catalog_path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    rpp_path = build_rpp()
    crosswalk_path = build_crosswalk()
    update_catalog(rpp_path, crosswalk_path)
    print(f"Built {rpp_path.relative_to(ROOT)} ({len(pd.read_csv(rpp_path))} rows)")
    print(f"Built {crosswalk_path.relative_to(ROOT)} ({len(pd.read_csv(crosswalk_path))} rows)")


if __name__ == "__main__":
    main()
