# Architecture

```text
User question
    |
    v
Local intent classifier
TF-IDF + logistic regression
    |
    v
Entity matching
SOC occupation · state · degree field · education category
    |
    v
Allowlisted query plan
No generated Python or SQL
    |
    v
Deterministic Pandas calculation
Versioned official snapshot
    |
    v
Evidence package
Answer · chart · table · calculation · source · vintage · limitations · Evidence ID
```

## Trust boundary

The classifier can help route language, but it never owns a number. The query engine selects from explicit operations such as sorting published wage fields, filtering an exact SOC and state, comparing two Census field estimates, or ranking BLS projections. It does not execute free-form code.

## Main components

- `data_store.py` loads normalized official tables and builds searchable indexes.
- `intent.py` trains a local question-intent classifier.
- `query_engine.py` validates the supported question family and runs deterministic Pandas operations.
- `evidence.py` creates the calculation record and content-addressed Evidence ID.
- `reporting.py` exports a portable HTML evidence report.
- `webapp.py` exposes FastAPI routes and serves the custom interface.
- `app.html`, `app.css`, and `app.js` implement the responsive product UI.

## Evidence ID

The Evidence ID is a SHA-256-derived identifier based on the question, route, query plan, source IDs, and returned rows. A change to the calculation or result changes the ID.

## Deployment boundary

The hackathon package runs locally with bundled snapshots and no credentials. A production deployment would add authentication, encrypted storage, scheduled source refreshes, schema-drift alerts, source-version approval, monitoring, and retention controls.
