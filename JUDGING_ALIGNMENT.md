# Judging Alignment

## Problem and usefulness - 25%

**Problem:** Students and early-career job seekers face large sets of job listings but cannot easily calculate reliable patterns. General chatbots may sound certain without using the actual data.

**Evidence in the project:**

- Clear target users and problem statement in `README.md`
- Natural-language questions in the `Ask the Data` tab
- Career Signal Lab for transparent role-skill overlap
- Scenario Compare for practical comparisons
- Refusal Coach for questions the data cannot answer

## Working prototype - 25%

- End-to-end CSV/XLSX upload, validation, question, calculation, evidence, and export workflow
- Bundled 654-row demonstration dataset
- Ten judge-ready supported questions
- Charts, tables, masked source rows, query plans, and downloadable reports
- Six interface tabs plus a global Data Dock
- Complete local launch command: `python app.py`

## Data and AI quality - 15%

- Local TF-IDF plus logistic-regression intent classifier
- Rule-assisted entity extraction grounded in dataset values
- Pydantic `QueryPlan` schema
- Field, metric, filter, and operation allowlists
- Deterministic Pandas calculations
- Salary midpoint formula and minimum group-size rules
- Transparent data-quality score and cleaning ledger
- Automated tests and scripted demo checks

## Trust and safety - 15%

- PII detection and masking in interface, logs, reports, and downloads
- Unsupported-question refusal
- Protected-attribute and unsafe-code blocks
- Data-based confidence scoring
- Evidence Passport with a reproducible Evidence ID and a proof-bundle verifier that reruns the validated plan when the active dataset matches
- Local audit log with masked questions
- Adversarial and failure-case tests
- No arbitrary model-generated Python or SQL

## Architecture clarity - 10%

- Simple input-to-output diagram in `docs/architecture.svg`
- Clear separation of AI interpretation from calculation
- Small modules for loading, cleaning, routing, validation, execution, privacy, evidence, confidence, reporting, and audit
- One-minute explanation in `docs/architecture.md`

## Demo and storytelling - 10%

- Presentation deck in `docs/presentation.pptx` and `docs/presentation.pdf`
- Seven-minute script in `docs/demo_script.md`
- Success case using remote-job skill frequency
- Second success case using internship opportunities
- Visible refusal case using employee happiness
- Practical value, synthetic-data disclosure, and limitations included in the closing
