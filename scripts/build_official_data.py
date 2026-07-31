from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
METADATA = ROOT / "data" / "metadata"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.replace({"*": pd.NA, "#": pd.NA, "**": pd.NA, "—": pd.NA}), errors="coerce")


def soc_base(value: Any) -> str:
    text = str(value).strip()
    return text[:7] if len(text) >= 7 else text


def write_csv(frame: pd.DataFrame, name: str) -> Path:
    path = PROCESSED / name
    frame.to_csv(path, index=False)
    return path


def build_occupations() -> tuple[pd.DataFrame, dict[str, Path]]:
    national_file = RAW / "national_M2025_dl.xlsx"
    projection_file = RAW / "occupation_2024-2034.xlsx"
    education_file = RAW / "bls_oes_2025_by_education.xlsx"

    national = pd.read_excel(national_file, sheet_name="national_M2025_dl")
    national = national.loc[national["O_GROUP"].eq("detailed")].copy()
    numeric_cols = [
        "TOT_EMP", "EMP_PRSE", "H_MEAN", "A_MEAN", "MEAN_PRSE", "H_PCT10",
        "H_PCT25", "H_MEDIAN", "H_PCT75", "H_PCT90", "A_PCT10", "A_PCT25",
        "A_MEDIAN", "A_PCT75", "A_PCT90",
    ]
    for column in numeric_cols:
        national[column] = clean_numeric(national[column])

    national = national.rename(columns={
        "OCC_CODE": "soc_code",
        "OCC_TITLE": "occupation_title",
        "TOT_EMP": "employment_2025",
        "EMP_PRSE": "employment_relative_standard_error",
        "H_MEAN": "hourly_mean_wage_2025",
        "A_MEAN": "annual_mean_wage_2025",
        "MEAN_PRSE": "mean_wage_relative_standard_error",
        "H_PCT10": "hourly_wage_p10_2025",
        "H_PCT25": "hourly_wage_p25_2025",
        "H_MEDIAN": "hourly_median_wage_2025",
        "H_PCT75": "hourly_wage_p75_2025",
        "H_PCT90": "hourly_wage_p90_2025",
        "A_PCT10": "annual_wage_p10_2025",
        "A_PCT25": "annual_wage_p25_2025",
        "A_MEDIAN": "annual_median_wage_2025",
        "A_PCT75": "annual_wage_p75_2025",
        "A_PCT90": "annual_wage_p90_2025",
    })
    national = national[[
        "soc_code", "occupation_title", "employment_2025",
        "employment_relative_standard_error", "hourly_mean_wage_2025",
        "annual_mean_wage_2025", "mean_wage_relative_standard_error",
        "hourly_wage_p10_2025", "hourly_wage_p25_2025", "hourly_median_wage_2025",
        "hourly_wage_p75_2025", "hourly_wage_p90_2025", "annual_wage_p10_2025",
        "annual_wage_p25_2025", "annual_median_wage_2025", "annual_wage_p75_2025",
        "annual_wage_p90_2025",
    ]]

    projections = pd.read_excel(projection_file, sheet_name="Table 1.2", header=1)
    projections = projections.loc[projections["Occupation type"].eq("Line item")].copy()
    projections = projections.rename(columns={
        "2024 National Employment Matrix title": "projection_title",
        "2024 National Employment Matrix code": "soc_code",
        "Employment, 2024": "employment_2024_thousands",
        "Employment, 2034": "employment_2034_thousands",
        "Employment change, numeric, 2024–34": "employment_change_2024_2034_thousands",
        "Employment change, percent, 2024–34": "employment_change_percent_2024_2034",
        "Percent self employed, 2024": "percent_self_employed_2024",
        "Occupational openings, 2024–34 annual average": "annual_openings_2024_2034_thousands",
        "Median annual wage, dollars, 2024[1]": "annual_median_wage_2024",
        "Typical education needed for entry": "typical_entry_education",
        "Work experience in a related occupation": "related_work_experience",
        "Typical on-the-job training needed to attain competency in the occupation": "on_the_job_training",
    })
    projection_columns = [
        "soc_code", "projection_title", "employment_2024_thousands",
        "employment_2034_thousands", "employment_change_2024_2034_thousands",
        "employment_change_percent_2024_2034", "percent_self_employed_2024",
        "annual_openings_2024_2034_thousands", "annual_median_wage_2024",
        "typical_entry_education", "related_work_experience", "on_the_job_training",
    ]
    projections = projections[projection_columns]
    for column in projection_columns[2:9]:
        projections[column] = clean_numeric(projections[column])

    education_map = pd.read_excel(education_file, sheet_name="educ_list", header=2)
    education_map = education_map.rename(columns={
        "OEWS May 2025 Code": "soc_code",
        "Typical entry-level educational requirement": "oews_typical_entry_education",
    })[["soc_code", "oews_typical_entry_education"]]

    onet_occupations = pd.read_csv(RAW / "onet_occupation_data.csv")
    onet_occupations["soc_code"] = onet_occupations["O*NET-SOC Code"].map(soc_base)
    onet_occupations["preferred"] = onet_occupations["O*NET-SOC Code"].str.endswith(".00").astype(int)
    onet_occupations = (
        onet_occupations.sort_values(["soc_code", "preferred"], ascending=[True, False])
        .drop_duplicates("soc_code")
        .rename(columns={"O*NET-SOC Code": "onet_soc_code", "Title": "onet_title", "Description": "description"})
        [["soc_code", "onet_soc_code", "onet_title", "description"]]
    )

    job_zones = pd.read_csv(RAW / "onet_job_zones.csv")
    job_zones["soc_code"] = job_zones["O*NET-SOC Code"].map(soc_base)
    job_zones["preferred"] = job_zones["O*NET-SOC Code"].str.endswith(".00").astype(int)
    job_zones = (
        job_zones.sort_values(["soc_code", "preferred"], ascending=[True, False])
        .drop_duplicates("soc_code")
        .rename(columns={"Job Zone": "onet_job_zone", "Date": "onet_job_zone_date"})
        [["soc_code", "onet_job_zone", "onet_job_zone_date"]]
    )

    combined = national.merge(projections, on="soc_code", how="left")
    combined = combined.merge(education_map, on="soc_code", how="left")
    combined = combined.merge(onet_occupations, on="soc_code", how="left")
    combined = combined.merge(job_zones, on="soc_code", how="left")
    combined["typical_entry_education"] = combined["typical_entry_education"].replace("—", pd.NA)
    combined["typical_entry_education"] = combined["typical_entry_education"].fillna(combined["oews_typical_entry_education"])
    combined["occupation_title_search"] = combined["occupation_title"].str.lower()
    combined["source_vintage"] = "BLS OEWS May 2025 + BLS projections 2024–2034 + O*NET 30.3"

    paths = {"occupations": write_csv(combined, "occupations.csv")}
    return combined, paths


def build_state_wages() -> tuple[pd.DataFrame, Path]:
    state = pd.read_excel(RAW / "state_M2025_dl.xlsx", sheet_name="state_M2025_dl")
    state = state.loc[state["O_GROUP"].eq("detailed")].copy()
    numeric_cols = [
        "TOT_EMP", "EMP_PRSE", "JOBS_1000", "LOC_QUOTIENT", "H_MEAN", "A_MEAN",
        "MEAN_PRSE", "H_MEDIAN", "A_MEDIAN", "A_PCT10", "A_PCT25", "A_PCT75", "A_PCT90",
    ]
    for column in numeric_cols:
        state[column] = clean_numeric(state[column])
    state = state.rename(columns={
        "AREA": "area_code", "AREA_TITLE": "state_name", "PRIM_STATE": "state_abbreviation",
        "OCC_CODE": "soc_code", "OCC_TITLE": "occupation_title", "TOT_EMP": "employment_2025",
        "EMP_PRSE": "employment_relative_standard_error", "JOBS_1000": "jobs_per_1000",
        "LOC_QUOTIENT": "location_quotient", "H_MEAN": "hourly_mean_wage_2025",
        "A_MEAN": "annual_mean_wage_2025", "MEAN_PRSE": "mean_wage_relative_standard_error",
        "H_MEDIAN": "hourly_median_wage_2025", "A_MEDIAN": "annual_median_wage_2025",
        "A_PCT10": "annual_wage_p10_2025", "A_PCT25": "annual_wage_p25_2025",
        "A_PCT75": "annual_wage_p75_2025", "A_PCT90": "annual_wage_p90_2025",
    })
    state = state[[
        "area_code", "state_name", "state_abbreviation", "soc_code", "occupation_title",
        "employment_2025", "employment_relative_standard_error", "jobs_per_1000",
        "location_quotient", "hourly_mean_wage_2025", "annual_mean_wage_2025",
        "mean_wage_relative_standard_error", "hourly_median_wage_2025",
        "annual_median_wage_2025", "annual_wage_p10_2025", "annual_wage_p25_2025",
        "annual_wage_p75_2025", "annual_wage_p90_2025",
    ]]
    state["source_vintage"] = "BLS OEWS May 2025"
    return state, write_csv(state, "state_wages.csv")


def build_onet() -> dict[str, Path]:
    paths: dict[str, Path] = {}

    essential = pd.read_csv(RAW / "onet_essential_skills.csv")
    essential = essential.loc[
        essential["Scale ID"].eq("IM") & essential["Recommend Suppress"].eq("N")
    ].copy()
    essential["soc_code"] = essential["O*NET-SOC Code"].map(soc_base)
    essential = essential.rename(columns={
        "O*NET-SOC Code": "onet_soc_code", "Title": "occupation_title",
        "Element Name": "skill", "Data Value": "importance", "Date": "source_date",
    })[["soc_code", "onet_soc_code", "occupation_title", "skill", "importance", "source_date"]]
    essential = essential.sort_values(["soc_code", "importance"], ascending=[True, False])
    essential["rank"] = essential.groupby("soc_code").cumcount() + 1
    essential = essential.loc[essential["rank"].le(15)]
    paths["essential_skills"] = write_csv(essential, "onet_essential_skills.csv")

    knowledge = pd.read_csv(RAW / "onet_knowledge.csv")
    knowledge = knowledge.loc[
        knowledge["Scale ID"].eq("IM") & knowledge["Recommend Suppress"].eq("N")
    ].copy()
    knowledge["soc_code"] = knowledge["O*NET-SOC Code"].map(soc_base)
    knowledge = knowledge.rename(columns={
        "O*NET-SOC Code": "onet_soc_code", "Title": "occupation_title",
        "Element Name": "knowledge_area", "Data Value": "importance", "Date": "source_date",
    })[["soc_code", "onet_soc_code", "occupation_title", "knowledge_area", "importance", "source_date"]]
    knowledge = knowledge.sort_values(["soc_code", "importance"], ascending=[True, False])
    knowledge["rank"] = knowledge.groupby("soc_code").cumcount() + 1
    knowledge = knowledge.loc[knowledge["rank"].le(15)]
    paths["knowledge"] = write_csv(knowledge, "onet_knowledge.csv")

    software = pd.read_csv(RAW / "onet_software_skills.csv")
    software["soc_code"] = software["O*NET-SOC Code"].map(soc_base)
    software["priority"] = software["In Demand"].eq("Y").astype(int) * 2 + software["Hot Technology"].eq("Y").astype(int)
    software = software.sort_values(["soc_code", "priority", "Workplace Example"], ascending=[True, False, True])
    software = software.drop_duplicates(["soc_code", "Workplace Example"])
    software["rank"] = software.groupby("soc_code").cumcount() + 1
    software = software.loc[software["rank"].le(20)].rename(columns={
        "O*NET-SOC Code": "onet_soc_code", "Title": "occupation_title",
        "Workplace Example": "software_or_tool", "Element Name": "software_category",
        "Hot Technology": "hot_technology", "In Demand": "in_demand",
    })[[
        "soc_code", "onet_soc_code", "occupation_title", "software_or_tool", "software_category",
        "hot_technology", "in_demand", "rank",
    ]]
    paths["software"] = write_csv(software, "onet_software_tools.csv")

    tasks = pd.read_csv(RAW / "onet_task_statements.csv")
    tasks["soc_code"] = tasks["O*NET-SOC Code"].map(soc_base)
    tasks["core_rank"] = tasks["Task Type"].eq("Core").astype(int)
    tasks["Incumbents Responding"] = clean_numeric(tasks["Incumbents Responding"])
    tasks = tasks.sort_values(
        ["soc_code", "core_rank", "Incumbents Responding", "Task ID"],
        ascending=[True, False, False, True],
    )
    tasks["rank"] = tasks.groupby("soc_code").cumcount() + 1
    tasks = tasks.loc[tasks["rank"].le(12)].rename(columns={
        "O*NET-SOC Code": "onet_soc_code", "Title": "occupation_title", "Task": "task",
        "Task Type": "task_type", "Date": "source_date",
    })[["soc_code", "onet_soc_code", "occupation_title", "task", "task_type", "source_date", "rank"]]
    paths["tasks"] = write_csv(tasks, "onet_tasks.csv")

    education_labels = {
        1: "Less than high school diploma",
        2: "High school diploma or equivalent",
        3: "Post-secondary certificate",
        4: "Some college, no degree",
        5: "Associate's degree",
        6: "Bachelor's degree",
        7: "Post-baccalaureate certificate",
        8: "Master's degree",
        9: "Post-master's certificate",
        10: "First professional degree",
        11: "Doctoral degree",
        12: "Post-doctoral training",
    }
    education = pd.read_csv(RAW / "onet_education.csv")
    education = education.loc[
        education["Element Name"].eq("Required Level of Education")
        & education["Scale ID"].eq("RL")
        & education["Recommend Suppress"].eq("N")
    ].copy()
    education["soc_code"] = education["O*NET-SOC Code"].map(soc_base)
    education["education_level"] = education["Category"].map(education_labels)
    education = education.rename(columns={
        "O*NET-SOC Code": "onet_soc_code", "Title": "occupation_title",
        "Data Value": "respondent_share_percent", "Date": "source_date",
    })[[
        "soc_code", "onet_soc_code", "occupation_title", "education_level",
        "respondent_share_percent", "source_date",
    ]]
    education = education.sort_values(["soc_code", "respondent_share_percent"], ascending=[True, False])
    education["rank"] = education.groupby("soc_code").cumcount() + 1
    education = education.loc[education["rank"].le(6)]
    paths["education"] = write_csv(education, "onet_education_responses.csv")
    return paths


def build_degree_earnings() -> tuple[pd.DataFrame, Path]:
    rows = [
        ("All bachelor's degree fields", 79879, 275),
        ("Computers, Mathematics, and Statistics", 102338, 323),
        ("Biological, Agricultural, and Environmental Sciences", 81793, 307),
        ("Physical and Related Sciences", 90385, 735),
        ("Psychology", 66736, 411),
        ("Social Sciences", 86203, 648),
        ("Engineering", 113242, 1070),
        ("Multidisciplinary Studies", 68608, 2365),
        ("Science and Engineering Related Fields", 80701, 177),
        ("Business", 85453, 353),
        ("Education", 60721, 165),
        ("Literature and Languages", 68947, 1162),
        ("Liberal Arts and History", 70996, 484),
        ("Visual and Performing Arts", 60247, 396),
        ("Communications", 72183, 405),
        ("Other", 67499, 625),
    ]
    frame = pd.DataFrame(rows, columns=["bachelors_field_group", "median_earnings_2024", "margin_of_error_90_percent"])
    frame["geography"] = "United States"
    frame["universe"] = "Population age 25 to 64 with earnings and a bachelor's degree or higher"
    frame["dataset"] = "ACS 2024 1-Year Detailed Table B15013"
    frame["source_url"] = "https://data.census.gov/table/ACSDT1Y2024.B15013"
    frame["note"] = "Association by first bachelor's degree field; not a causal estimate or occupation-specific outcome."
    return frame, write_csv(frame, "census_degree_earnings_2024.csv")


def build_education_wages() -> tuple[pd.DataFrame, Path]:
    workbook = RAW / "bls_oes_2025_by_education.xlsx"
    frames = []
    for sheet, geography_type in [
        ("National", "National"),
        ("State", "State"),
        ("Metropolitan Area", "Metropolitan Area"),
    ]:
        frame = pd.read_excel(workbook, sheet_name=sheet)
        frame.columns = [str(column).strip() for column in frame.columns]
        frame["geography_type"] = geography_type
        frame = frame.rename(columns={
            "area": "area_code", "area_name": "geography", "education_category": "education_category",
            "tot_emp": "employment_2025", "pct_total": "share_of_employment_percent",
            "emp_prse": "employment_relative_standard_error", "h_mean": "hourly_mean_wage_2025",
            "a_mean": "annual_mean_wage_2025", "mean_prse": "mean_wage_relative_standard_error",
            "h_median": "hourly_median_wage_2025", "a_median": "annual_median_wage_2025",
            "a_pct10": "annual_wage_p10_2025", "a_pct25": "annual_wage_p25_2025",
            "a_pct75": "annual_wage_p75_2025", "a_pct90": "annual_wage_p90_2025",
        })
        keep = [
            "geography_type", "area_code", "geography", "education_category", "employment_2025",
            "share_of_employment_percent", "employment_relative_standard_error",
            "hourly_mean_wage_2025", "annual_mean_wage_2025", "mean_wage_relative_standard_error",
            "hourly_median_wage_2025", "annual_median_wage_2025", "annual_wage_p10_2025",
            "annual_wage_p25_2025", "annual_wage_p75_2025", "annual_wage_p90_2025",
        ]
        for column in keep[4:]:
            frame[column] = clean_numeric(frame[column])
        frames.append(frame[keep])
    combined = pd.concat(frames, ignore_index=True)
    combined["source_vintage"] = "BLS OEWS May 2025 special education aggregation"
    return combined, write_csv(combined, "education_wages_2025.csv")


def build_question_catalog() -> Path:
    questions = [
        {
            "dataset": "BLS OEWS National",
            "description": "National occupation employment and wage estimates",
            "questions": [
                "What are the 10 highest-paying occupations?",
                "How much do nuclear engineers earn?",
                "How many public relations specialists are employed nationally?",
                "Compare lawyers and political scientists.",
                "What is the pay range for news analysts, reporters, and journalists?",
            ],
        },
        {
            "dataset": "BLS OEWS State",
            "description": "State-level occupation wages, employment, and concentration",
            "questions": [
                "Which states pay nuclear engineers the most?",
                "Which states employ the most public relations specialists?",
                "How much do lawyers earn in Maryland?",
                "Where are political scientists most concentrated?",
                "Compare journalists' median pay in Maryland and Virginia.",
            ],
        },
        {
            "dataset": "BLS Employment Projections",
            "description": "2024 to 2034 growth, openings, and education requirements",
            "questions": [
                "Which occupations are projected to grow fastest from 2024 to 2034?",
                "What is the job outlook for nuclear engineers?",
                "Which occupations have the most annual openings?",
                "What education is typically required for political scientists?",
                "Compare the outlook for public relations specialists and journalists.",
            ],
        },
        {
            "dataset": "O*NET 30.3",
            "description": "Occupation descriptions, skills, knowledge, tasks, tools, and education responses",
            "questions": [
                "What skills do nuclear engineers need?",
                "What tasks do public relations specialists perform?",
                "What software do broadcast technicians use?",
                "What knowledge areas matter most for lawyers?",
                "What does a political scientist do?",
            ],
        },
        {
            "dataset": "Census ACS Degree Earnings",
            "description": "National median earnings by broad field of first bachelor's degree",
            "questions": [
                "Which broad bachelor's degree fields have the highest median earnings?",
                "Compare communications and engineering degree earnings.",
                "How do social sciences and business degree earnings compare?",
                "What are the median earnings for communications degree holders?",
            ],
        },
        {
            "dataset": "BLS Education Wage Aggregates",
            "description": "Employment and wage estimates grouped by typical entry-level education",
            "questions": [
                "How do national wages compare by typical entry-level education?",
                "Which states have the highest median wage for bachelor's-level occupations?",
                "Which metro areas pay the most for occupations typically requiring a bachelor's degree?",
                "How many jobs are in occupations typically requiring a doctoral or professional degree?",
            ],
        },
    ]
    path = METADATA / "question_catalog.json"
    path.write_text(json.dumps(questions, indent=2), encoding="utf-8")
    return path


def build_aliases() -> Path:
    aliases = {
        "attorney": "Lawyers",
        "lawyer": "Lawyers",
        "public relations": "Public Relations Specialists",
        "pr specialist": "Public Relations Specialists",
        "mass communications": "Public Relations Specialists",
        "communications specialist": "Public Relations Specialists",
        "journalist": "News Analysts, Reporters, and Journalists",
        "reporter": "News Analysts, Reporters, and Journalists",
        "broadcast technician": "Broadcast Technicians",
        "nuclear engineer": "Nuclear Engineers",
        "political scientist": "Political Scientists",
        "political science": "Political Scientists",
        "software engineer": "Software Developers",
        "software developer": "Software Developers",
        "registered nurse": "Registered Nurses",
        "mechanical engineer": "Mechanical Engineers",
        "electrical engineer": "Electrical Engineers",
        "data scientist": "Data Scientists",
        "cybersecurity analyst": "Information Security Analysts",
        "teacher": "Secondary School Teachers, Except Special and Career/Technical Education",
    }
    path = METADATA / "occupation_aliases.json"
    path.write_text(json.dumps(aliases, indent=2), encoding="utf-8")
    return path


def build_source_catalog(processed_paths: dict[str, Path]) -> Path:
    sources = [
        {
            "id": "bls-oews-national-2025",
            "title": "Occupational Employment and Wage Statistics: National",
            "agency": "U.S. Bureau of Labor Statistics",
            "vintage": "May 2025",
            "authoritative_url": "https://www.bls.gov/oes/current/oes_nat.htm",
            "download_url": "https://www.bls.gov/oes/special.requests/oesm25nat.zip",
            "local_raw_file": "data/raw/national_M2025_dl.xlsx",
            "license": "U.S. federal government public data",
            "coverage": "National employment and wage estimates for detailed occupations",
        },
        {
            "id": "bls-oews-state-2025",
            "title": "Occupational Employment and Wage Statistics: State",
            "agency": "U.S. Bureau of Labor Statistics",
            "vintage": "May 2025",
            "authoritative_url": "https://www.bls.gov/oes/current/oessrcst.htm",
            "download_url": "https://www.bls.gov/oes/special.requests/oesm25st.zip",
            "local_raw_file": "data/raw/state_M2025_dl.xlsx",
            "license": "U.S. federal government public data",
            "coverage": "State employment, wage, and location-quotient estimates by occupation",
        },
        {
            "id": "bls-projections-2024-2034",
            "title": "Employment Projections: Occupational Projections and Worker Characteristics",
            "agency": "U.S. Bureau of Labor Statistics",
            "vintage": "2024–2034",
            "authoritative_url": "https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm",
            "local_raw_file": "data/raw/occupation_2024-2034.xlsx",
            "license": "U.S. federal government public data",
            "coverage": "Employment growth, annual openings, education, experience, and training",
        },
        {
            "id": "bls-oews-education-2025",
            "title": "OEWS Estimates by Typical Entry-Level Education",
            "agency": "U.S. Bureau of Labor Statistics",
            "vintage": "May 2025",
            "authoritative_url": "https://www.bls.gov/oes/education.htm",
            "download_url": "https://www.bls.gov/oes/special-requests/education_2025.xlsx",
            "local_raw_file": "data/raw/bls_oes_2025_by_education.xlsx",
            "license": "U.S. federal government public data",
            "coverage": "National, state, metro, and industry wage aggregates by typical education",
        },
        {
            "id": "onet-30-3",
            "title": "O*NET Database",
            "agency": "O*NET Resource Center, sponsored by the U.S. Department of Labor",
            "vintage": "30.3",
            "authoritative_url": "https://www.onetcenter.org/database.html",
            "download_url": "https://www.onetcenter.org/database.html#all-files",
            "local_raw_file": "data/raw/onet_occupation_data.csv and related O*NET CSV files",
            "license": "Creative Commons Attribution 4.0 International",
            "coverage": "Occupation descriptions, skills, knowledge, tasks, software, job zones, and education responses",
        },
        {
            "id": "census-acs-b15013-2024",
            "title": "ACS Table B15013: Median Earnings by Field of Bachelor's Degree",
            "agency": "U.S. Census Bureau",
            "vintage": "2024 ACS 1-Year",
            "authoritative_url": "https://data.census.gov/table/ACSDT1Y2024.B15013",
            "local_raw_file": "Bundled verified table snapshot in data/processed/census_degree_earnings_2024.csv",
            "license": "U.S. federal government public data",
            "coverage": "National median earnings for people age 25–64 with earnings and a bachelor's degree or higher",
        },
    ]

    raw_checksums = {}
    for path in sorted(RAW.iterdir()):
        raw_checksums[str(path.relative_to(ROOT))] = {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
    processed_checksums = {}
    for key, path in processed_paths.items():
        processed_checksums[key] = {
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "rows": max(sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore")) - 1, 0),
        }

    catalog = {
        "generated_at": "2026-07-30",
        "product_note": "All bundled analytical records come from official U.S. government or O*NET sources. No synthetic labor-market records are used.",
        "sources": sources,
        "raw_file_checksums": raw_checksums,
        "processed_file_checksums": processed_checksums,
    }
    path = METADATA / "data_catalog.json"
    path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    return path


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    METADATA.mkdir(parents=True, exist_ok=True)
    processed_paths: dict[str, Path] = {}

    occupations, paths = build_occupations()
    processed_paths.update(paths)
    state_wages, path = build_state_wages()
    processed_paths["state_wages"] = path
    processed_paths.update(build_onet())
    degree_earnings, path = build_degree_earnings()
    processed_paths["degree_earnings"] = path
    education_wages, path = build_education_wages()
    processed_paths["education_wages"] = path
    build_question_catalog()
    build_aliases()
    catalog_path = build_source_catalog(processed_paths)

    print(f"Occupations: {len(occupations):,}")
    print(f"State wage rows: {len(state_wages):,}")
    print(f"Degree fields: {len(degree_earnings):,}")
    print(f"Education wage rows: {len(education_wages):,}")
    print(f"Catalog: {catalog_path}")
    for key, path in processed_paths.items():
        print(f"{key}: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
