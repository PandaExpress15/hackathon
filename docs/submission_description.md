# Submission Description

## Project name

CareerProof AI

## One-sentence summary

CareerProof AI lets students and early-career job seekers ask questions about job-posting data and receive code-calculated answers with visible evidence, privacy masking, confidence labels, and safe refusal.

## Problem

Job seekers often face hundreds of listings but cannot easily calculate which skills, locations, employers, work modes, or salary patterns matter. A general AI assistant can produce plausible but unsupported answers.

## Target user

- High school and college students
- Recent graduates
- Early-career job seekers
- Career counselors
- Workforce-development organizations

## Solution

The user uploads a job-posting CSV/XLSX file or uses the bundled synthetic dataset. A local AI classifier interprets the question and creates a structured query plan. Deterministic Pandas code calculates the result. The interface shows the answer, chart, result table, masked source rows, calculation steps, confidence score, and downloadable Evidence Passport.

## AI component

A local TF-IDF plus logistic-regression model classifies question intent. AI is used for interpretation, not numerical calculation. Rule-assisted entity extraction maps words to approved fields and values.

## Data component

The included deterministic synthetic dataset contains 654 raw job postings and 646 cleaned rows. It includes role, employer, location, work mode, experience, salary, skills, date, and fictional recruiter fields. The raw file intentionally contains controlled quality issues for demonstration.

## Trust features

- Deterministic code calculations
- Structured query plans
- Field, metric, and operation allowlists
- PII masking
- Minimum sample sizes
- Unsupported-question refusal
- Protected-attribute block
- Data-based confidence labels
- Evidence ID, downloadable proof bundle, and active-dataset replay verification
- Local, masked audit log
- Automated success, failure, privacy, and adversarial tests

## Technical stack

Python, Gradio, Pandas, NumPy, Plotly, Pydantic, scikit-learn, Jinja2, openpyxl, pytest, and python-dotenv.

## Dataset disclosure

This dataset is synthetic and was generated for demonstration and evaluation. It does not represent current real-world hiring conditions.

## Known limitations

The project does not use live job-board data, predict hiring outcomes, rank employer quality, or forecast the future. Salary analysis requires complete salary ranges, and the question router intentionally supports a focused set of auditable calculations.
