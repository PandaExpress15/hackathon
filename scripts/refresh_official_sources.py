"""Optional network refresh helper for the fixed source versions used by CareerProof.

The packaged application does not require this script. It is intentionally separate from
runtime so the demo remains reproducible and does not depend on credentials or availability.
"""
from __future__ import annotations

import io
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

DOWNLOADS = {
    "bls_oes_2025_by_education.xlsx": "https://www.bls.gov/oes/special-requests/education_2025.xlsx",
    "occupation_2024-2034.xlsx": "https://www.bls.gov/emp/ind-occ-matrix/occupation.xlsx",
    "onet_occupation_data.csv": "https://www.onetcenter.org/dl_files/database/db_30_3_csv/occupation_data.csv",
    "onet_software_skills.csv": "https://www.onetcenter.org/dl_files/database/db_30_3_csv/software_skills.csv",
    "onet_essential_skills.csv": "https://www.onetcenter.org/dl_files/database/db_30_3_csv/skills.csv",
    "onet_knowledge.csv": "https://www.onetcenter.org/dl_files/database/db_30_3_csv/knowledge.csv",
    "onet_education.csv": "https://www.onetcenter.org/dl_files/database/db_30_3_csv/education_training_experience.csv",
    "onet_job_zones.csv": "https://www.onetcenter.org/dl_files/database/db_30_3_csv/job_zones.csv",
    "onet_task_statements.csv": "https://www.onetcenter.org/dl_files/database/db_30_3_csv/task_statements.csv",
}

OEWS_ZIPS = {
    "national_M2025_dl.xlsx": "https://www.bls.gov/oes/special.requests/oesm25nat.zip",
    "state_M2025_dl.xlsx": "https://www.bls.gov/oes/special.requests/oesm25st.zip",
}


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "CareerProof-AI/2.0 data refresh"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for filename, url in DOWNLOADS.items():
        print(f"Downloading {filename} from {url}")
        (RAW / filename).write_bytes(download(url))
    for target, url in OEWS_ZIPS.items():
        print(f"Downloading {target} from {url}")
        payload = download(url)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            candidates = [name for name in archive.namelist() if name.lower().endswith((".xlsx", ".xls"))]
            if not candidates:
                raise RuntimeError(f"No workbook found in {url}")
            with archive.open(candidates[0]) as source, (RAW / target).open("wb") as destination:
                shutil.copyfileobj(source, destination)
    print("Raw source refresh complete. Review source versions, then run scripts/build_official_data.py and the full test suite.")
    print("Census B15013 is a curated verified table snapshot. Update it only after reviewing the official data.census.gov table and margins of error.")


if __name__ == "__main__":
    main()
