# CareerProof AI Data Sources

CareerProof bundles fixed official snapshots so the hackathon demo remains reproducible and does not depend on live APIs, rate limits, credentials, or third-party availability. All analytical records come from official U.S. government or O*NET datasets. No synthetic labor-market rows are used.

The machine-readable catalog is `data/metadata/data_catalog.json`. It records raw and processed file SHA-256 checksums, byte sizes, and processed row counts.

## 1. BLS Occupational Employment and Wage Statistics, national

- Publisher: U.S. Bureau of Labor Statistics
- Vintage: May 2025
- Authoritative page: https://www.bls.gov/oes/current/oes_nat.htm
- Official download family: https://www.bls.gov/oes/special.requests/oesm25nat.zip
- Bundled raw file: `data/raw/national_M2025_dl.xlsx`
- Processed table: `data/processed/occupations.csv`
- Uses: national employment, mean wage, median wage, hourly wage, and wage percentiles for 830 detailed occupations
- Terms: U.S. federal government public data

The exact workbook was obtained through a public transport mirror because the execution environment could not fetch the official ZIP content type. The application identifies BLS as the authoritative publisher, links to the BLS page, bundles the workbook, and records its checksum. The transport mirror is not treated as the data authority.

## 2. BLS Occupational Employment and Wage Statistics, state

- Publisher: U.S. Bureau of Labor Statistics
- Vintage: May 2025
- Authoritative page: https://www.bls.gov/oes/current/oessrcst.htm
- Official download family: https://www.bls.gov/oes/special.requests/oesm25st.zip
- Bundled raw file: `data/raw/state_M2025_dl.xlsx`
- Processed table: `data/processed/state_wages.csv`
- Uses: state employment, jobs per 1,000, location quotient, mean wage, median wage, and wage percentiles by occupation
- Processed rows: more than 36,000 state-occupation records
- Terms: U.S. federal government public data

Suppressed or unpublished values remain missing and are excluded from rankings with a visible note.

## 3. BLS Employment Projections

- Publisher: U.S. Bureau of Labor Statistics
- Projection window: 2024–2034
- Authoritative page: https://www.bls.gov/emp/data/occupational-data.htm
- Official workbook: https://www.bls.gov/emp/ind-occ-matrix/occupation.xlsx
- Bundled raw file: `data/raw/occupation_2024-2034.xlsx`
- Processed join: `data/processed/occupations.csv`
- Uses: 2024 and 2034 employment, numeric and percentage change, annual-average openings, typical entry education, related work experience, and on-the-job training
- Terms: U.S. federal government public data

Annual openings are projections. They are not current vacancies.

## 4. BLS OEWS estimates by typical entry-level education

- Publisher: U.S. Bureau of Labor Statistics
- Vintage: May 2025
- Authoritative page: https://www.bls.gov/oes/education.htm
- Official workbook: https://www.bls.gov/oes/special-requests/education_2025.xlsx
- Bundled raw file: `data/raw/bls_oes_2025_by_education.xlsx`
- Processed table: `data/processed/education_wages_2025.csv`
- Uses: employment and wage aggregates by typical entry education for the nation, states, and metropolitan areas
- Terms: U.S. federal government public data

These categories describe the education BLS typically assigns for entry into occupations. They do not measure the education of every worker and do not estimate a causal return to education.

## 5. O*NET Database 30.3

- Publisher: O*NET Resource Center, sponsored by the U.S. Department of Labor
- Release: 30.3
- Authoritative page: https://www.onetcenter.org/database.html
- License: Creative Commons Attribution 4.0 International
- Attribution: O*NET® is a trademark of the U.S. Department of Labor, Employment and Training Administration
- Bundled raw files:
  - `onet_occupation_data.csv`
  - `onet_essential_skills.csv`
  - `onet_knowledge.csv`
  - `onet_software_skills.csv`
  - `onet_task_statements.csv`
  - `onet_education.csv`
  - `onet_job_zones.csv`
- Processed tables:
  - `onet_essential_skills.csv`
  - `onet_knowledge.csv`
  - `onet_software_tools.csv`
  - `onet_tasks.csv`
  - `onet_education_responses.csv`

CareerProof maps the base O*NET-SOC code to the corresponding detailed BLS SOC record. O*NET importance ratings and education responses are published occupational descriptors, not CareerProof hiring scores.

## 6. U.S. Census Bureau ACS Detailed Table B15013

- Publisher: U.S. Census Bureau
- Product: 2024 American Community Survey 1-Year Detailed Table B15013
- Title: Median Earnings in the Past 12 Months by Sex by Field of Bachelor's Degree for First Major
- Universe: Population age 25 to 64 with earnings and a bachelor's degree or higher
- Authoritative table: https://data.census.gov/table/ACSDT1Y2024.B15013
- Bundled verified snapshot: `data/processed/census_degree_earnings_2024.csv`
- Uses: national median earnings and 90 percent margin of error for broad first-major field groups
- Terms: U.S. federal government public data

The snapshot includes the national total and 15 broad field groups visible in the official table. It does not contain individual records. The table cannot answer which undergraduate major causes the highest earnings within a specific later occupation such as law.

## Reproducibility

Run:

```bash
python scripts/build_official_data.py
```

This rebuilds normalized tables from the bundled raw source files and regenerates:

- `data/metadata/data_catalog.json`
- Raw-file checksums
- Processed-file checksums
- Processed row counts
- Occupation aliases
- Question catalog

## Data freshness

The interface always displays source vintages. A newer release may become available after the bundled version. A production deployment should implement a scheduled ingestion pipeline, versioned releases, automated schema checks, and a human review before replacing the active snapshot.
