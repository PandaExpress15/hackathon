# Architecture

## One-minute explanation

CareerProof AI accepts a bundled or uploaded CSV/XLSX file. It maps common column names into a canonical job-posting schema, validates the values, and records every cleaning action. Sensitive recruiter fields are classified and masked before display or export.

When the user asks a question, a small local TF-IDF and logistic-regression model identifies the analysis intent. The model does not calculate the answer. A rule-assisted router creates a Pydantic `QueryPlan` containing only approved fields, filters, aggregations, sort order, result limit, chart type, and minimum sample size.

The validator rejects sensitive columns, missing fields, unknown metrics, and unsupported operations. Valid plans are executed by deterministic Pandas functions. The result then receives a chart, table, masked source preview, calculation explanation, data-based confidence score, Evidence ID, downloadable report, and local audit event.

If the question requests unavailable data, protected attributes, private contacts, future prediction, guaranteed hiring, or unsafe code execution, the system refuses and suggests nearby answerable questions.

## Component responsibilities

| Component | Responsibility |
|---|---|
| `data_loader.py` | Read CSV/XLSX and return a dataset bundle |
| `data_cleaning.py` | Map schema, validate values, calculate quality, and record actions |
| `privacy.py` | Detect and mask names, emails, phones, IDs, and sensitive URL parameters |
| `intent_model.py` | Local question-intent classification only |
| `entities.py` | Extract allowlisted filters from question text and dataset values |
| `question_router.py` | Create a structured `QueryPlan` or safe refusal |
| `query_validator.py` | Enforce allowed fields, metrics, and safety rules |
| `query_executor.py` | Perform deterministic Pandas calculations |
| `confidence.py` | Score evidence, completeness, intent clarity, and dataset quality |
| `evidence.py` | Build reproducible proof bundles, recompute Evidence IDs, and replay plans against the active dataset |
| `reporting.py` | Produce masked HTML, CSV, and JSON exports |
| `audit.py` | Store a local, masked event log |
| `ui.py` | Present the working Gradio interface |

## Why this is trustworthy

The architecture prevents the language model from writing or running code. Every numerical statement comes from an allowlisted executor. The system exposes the plan and source evidence so a judge or user can inspect the full path from question to result. Downloaded proof bundles can also be re-uploaded. CareerProof recomputes the Evidence ID and, when the active dataset fingerprint matches, reruns the validated plan to confirm that the result reproduces.
