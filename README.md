# CareerProof AI

**Ask the job market. See the proof.**

CareerProof AI is a Track 2 trustworthy-data-analysis website that turns official United States career data into clear, reproducible answers. A lightweight local AI classifier interprets the question. Deterministic Pandas code performs every factual calculation and exposes the source, vintage, table, filters, rows used, limitations, and an Evidence ID.

> **Official data interprets the market. Code proves the answer.**

The bundled edition contains **no synthetic labor-market records**. It uses verified snapshots from the U.S. Bureau of Labor Statistics, U.S. Census Bureau, and O*NET.

## What changed in the official-data edition

- Replaced the synthetic job-posting dataset with real published data.
- Added six selectable source routes.
- Expanded coverage to 830 detailed occupations and more than 36,000 state-occupation records.
- Added mass-communications careers, journalism, public relations, broadcast technology, nuclear engineering, political science, law, health, education, software, and hundreds more.
- Added a searchable unified occupation profile combining pay, employment, outlook, education, skills, knowledge, tasks, tools, and state wage data.
- Added a Census degree-field earnings workspace.
- Added BLS education-level wage comparisons by nation, state, and metropolitan area.
- Preserved the deep navy, emerald, white, and cool-gray visual identity while adding stronger blue information accents.
- Preserved visible evidence, safe refusal, source disclosure, and deterministic calculations.

## Official datasets

| Dataset | Vintage | What CareerProof uses it for |
| --- | --- | --- |
| BLS Occupational Employment and Wage Statistics, national | May 2025 | National employment, mean wages, median wages, and wage percentiles by detailed occupation |
| BLS Occupational Employment and Wage Statistics, state | May 2025 | State employment, wages, jobs per 1,000, and location quotients |
| BLS Employment Projections | 2024–2034 | Employment growth, annual openings, typical education, experience, and training |
| O*NET Database | Release 30.3 | Occupation descriptions, essential skills, knowledge, tasks, software, job zones, and education responses |
| Census ACS Detailed Table B15013 | 2024 1-Year | National median earnings by broad field of first bachelor's degree |
| BLS OEWS estimates by typical entry education | May 2025 | National, state, and metro wage and employment aggregates by typical entry-level education |

Full provenance, authoritative URLs, licenses, retrieval notes, row counts, and SHA-256 checksums are in [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) and [`data/metadata/data_catalog.json`](data/metadata/data_catalog.json).

## Workspaces

### Ask CareerProof

Ask natural-language questions and optionally choose the dataset route. Each supported answer includes:

- Direct answer and plain-language summary
- Result chart and source-backed table
- Official agency, dataset, and vintage
- Visible query plan and deterministic calculation
- Rows considered and rows returned
- Evidence-based confidence label
- Limitations and nearby answerable questions
- Reproducible Evidence ID
- Downloadable HTML evidence report

### Occupation Explorer

Search 830 detailed occupations and open a unified profile containing:

- May 2025 national wage and employment estimates
- 2024–2034 growth and annual openings
- Typical entry education
- O*NET description, skills, knowledge, tasks, tools, and education responses
- Highest-paying states with published estimates

### Question Library

The interface lists questions grouped by the dataset that can answer them. See [`docs/QUESTION_CATALOG.md`](docs/QUESTION_CATALOG.md).

### Data Catalog

Every source is named, dated, linked, licensed, and checksum-recorded. Raw source files and processed analytical tables are bundled for offline demonstration and reproducibility.

### Trust Center

The application makes the trust boundary visible:

1. A local TF-IDF and logistic-regression model classifies the question intent.
2. Deterministic rules identify occupations, states, degree fields, and supported operations.
3. The application builds an allowlisted query plan.
4. Pandas performs the calculation against a specific official snapshot.
5. CareerProof shows the source, evidence, confidence, limitations, and Evidence ID.

No user prompt or model output is executed as Python or SQL.

## Example questions

- Which states pay nuclear engineers the most?
- What skills do public relations specialists need?
- What is the job outlook for political scientists?
- How much do lawyers earn in Maryland?
- What software do broadcast technicians use?
- Compare lawyers and political scientists.
- Which broad bachelor's degree fields have the highest national median earnings?
- Compare communications and engineering degree earnings.
- How do national wages compare by typical entry-level education?
- Which metro areas pay the most for occupations typically requiring a bachelor's degree?

Expected safe-refusal example:

```text
What bachelor's degree should I pursue for the highest pay after becoming a lawyer?
```

The bundled datasets cannot connect an individual's undergraduate major to later earnings specifically as a lawyer. CareerProof refuses the causal claim and separates it into answerable questions about broad degree-field earnings, lawyer education requirements, and lawyer wages and outlook.

## Install on Ubuntu or Linux

Python 3.11 or newer is required.

```bash
sudo apt update
sudo apt install python3-venv python3-full -y
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Open:

```text
http://127.0.0.1:7860
```

No API key is required because verified official snapshots are bundled.

## Test

```bash
python -m pip install -r requirements-dev.txt
pytest -q
python scripts/run_demo_checks.py
python scripts/smoke_test_app.py
python scripts/verify_submission.py
```

## Build the ZIP

```bash
python scripts/build_submission.py
```

Output:

```text
dist/careerproof-ai-official-data.zip
```

## Rebuild processed tables

The raw official source files are bundled in `data/raw/`. Rebuild all normalized analytical tables and checksums with:

```bash
python scripts/build_official_data.py
```

## Repository structure

```text
app.py                         FastAPI and Uvicorn launcher
src/careerproof/               Data store, intent model, query engine, evidence, reporting, and web app
static/                        Responsive custom CSS and vanilla JavaScript
                               with navy, green, and blue design tokens
templates/app.html             Product interface
data/raw/                      Bundled official source snapshots
data/processed/                Normalized analytical CSV files
data/metadata/                 Source catalog, checksums, aliases, and question catalog
scripts/                       Data build, testing, verification, smoke test, and packaging tools
tests/                         Source, query, safety, API, occupation coverage, and UI tests
docs/                          Architecture, sources, limitations, demo, and submission material
```

## Important limitations

- CareerProof is an official **statistical-data explorer**, not a live job board.
- OEWS estimates do not include all workers and may suppress small estimates.
- BLS projections are scenarios, not current vacancies or guarantees.
- State wage rankings do not adjust for cost of living.
- O*NET describes typical occupational work, not every employer or position.
- ACS degree-field earnings are broad associations across all occupations. They do not prove that a major caused higher pay or predict lawyer-specific outcomes.
- Published group estimates do not guarantee an individual's wage, admission, hiring, or career success.

More detail is in [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

## Authoritative source links

- BLS OEWS: https://www.bls.gov/oes/
- BLS Occupational Projections: https://www.bls.gov/emp/data/occupational-data.htm
- O*NET Database: https://www.onetcenter.org/database.html
- Census ACS B15013: https://data.census.gov/table/ACSDT1Y2024.B15013

## License and attribution

Project code is released under the MIT License. BLS and Census data are U.S. federal government public data. O*NET content is used under the Creative Commons Attribution 4.0 International license. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and [`data/LICENSE.md`](data/LICENSE.md).
