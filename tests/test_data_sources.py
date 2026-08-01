from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from careerproof.config import ROOT
from careerproof.data_store import get_store


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def test_core_datasets_have_real_rows() -> None:
    store = get_store()
    assert len(store.occupations) == 830
    assert len(store.state_wages) > 30000
    assert len(store.skills) > 5000
    assert len(store.degree_earnings) == 16
    assert len(store.education_wages) > 4000
    assert len(store.degree_crosswalk) > 5000
    assert len(store.rpp) == 51


def test_catalog_has_official_source_families() -> None:
    store = get_store()
    agencies = " ".join(source["agency"] for source in store.catalog["sources"])
    assert "Bureau of Labor Statistics" in agencies
    assert "Census Bureau" in agencies
    assert "O*NET" in agencies
    assert "Bureau of Economic Analysis" in agencies
    assert "National Center for Education Statistics" in agencies
    assert len(store.catalog["sources"]) >= 8


def test_catalog_explicitly_discloses_no_synthetic_records() -> None:
    note = get_store().catalog["product_note"].lower()
    assert "no synthetic labor-market records" in note


def test_raw_checksums_match_files() -> None:
    catalog = get_store().catalog
    for relative, metadata in catalog["raw_file_checksums"].items():
        path = ROOT / relative
        assert path.exists()
        assert file_hash(path) == metadata["sha256"]
        assert path.stat().st_size == metadata["bytes"]


def test_census_degree_values_match_bundled_official_snapshot() -> None:
    store = get_store()
    values = dict(zip(store.degree_earnings["bachelors_field_group"], store.degree_earnings["median_earnings_2024"]))
    assert values["Engineering"] == 113242
    assert values["Communications"] == 72183
    assert values["Social Sciences"] == 86203
    assert values["All bachelor's degree fields"] == 79879


def test_no_synthetic_job_posting_dataset_is_bundled() -> None:
    forbidden = list(ROOT.rglob("job_postings.csv")) + list(ROOT.rglob("generate_dataset.py"))
    assert forbidden == []


def test_processed_files_have_source_vintage() -> None:
    occupations = pd.read_csv(ROOT / "data/processed/occupations.csv", nrows=5)
    states = pd.read_csv(ROOT / "data/processed/state_wages.csv", nrows=5)
    assert occupations["source_vintage"].notna().all()
    assert states["source_vintage"].notna().all()
