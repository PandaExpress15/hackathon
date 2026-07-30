# CareerProof AI Judge Demo Cheat Sheet

Use this beside the recording or live judging screen. The bundled dataset must remain active unless the judge specifically asks to see upload validation.

## Before the demo

```bash
python scripts/verify_submission.py
python app.py
```

Confirm that verification passes, open the local URL, and clear the local audit log.

## Core message

> AI interprets the question. Code calculates the answer. Evidence proves it.

Target users: students, recent graduates, career counselors, and workforce-development teams.

## Main success case

**Question**

```text
What are the ten most requested skills for remote jobs?
```

**Expected result**

- 223 remote postings used
- Project Management: 122 postings
- Azure: 121 postings
- Git: 119 postings
- High confidence: 89/100
- Evidence ID: `CP-88B4ACE97069E1CF`

**Show**

1. `Verified by code`
2. Chart and result table
3. Five-step proof line
4. Calculation details and validated query plan
5. Masked source rows
6. Downloaded proof-bundle JSON

## Evidence Passport verification

1. Download the proof-bundle JSON from the main success case.
2. Open **Trust Center**.
3. Upload the JSON under **Evidence Passport Verifier**.
4. Select **Verify Evidence Passport**.
5. Point out that CareerProof:
   - recomputes the content-addressed Evidence ID
   - confirms the dataset fingerprint
   - reruns the validated plan against the active data
   - detects changed or non-reproducible results

## Second success case

**Question**

```text
Which companies have the most internship opportunities?
```

**Expected result**

- 114 internship postings used
- Great Lakes Data Cooperative: 12
- Blue Ridge Analytics: 11
- Harborlight HealthTech: 10
- Evidence ID: `CP-F1A4DCCA9F027DBE`

## Safe refusal case

**Question**

```text
Which company has the happiest employees?
```

**Expected behavior**

- Status: `Safe refusal`
- The dataset has no employee-satisfaction field
- No invented employer ranking
- Refusal Coach suggests nearby answerable questions
- Evidence ID: `CP-7AEBDAFC270C6B2F`

## Unique features to name

- Evidence Passport and replay verifier
- Refusal Coach
- Career Signal Lab
- Scenario Compare
- Cleaning Ledger
- Privacy Shield
- Masked local audit log
- HTML, CSV, JSON, PPTX, and PDF submission assets

## Trust points

- No arbitrary Python, SQL, `eval`, or `exec`
- Structured Pydantic query plans
- Field, metric, filter, and operation allowlists
- PII masking before UI, report, export, proof, or log
- Minimum salary sample sizes
- Confidence based on evidence, not model tone
- Unsupported and discriminatory questions are blocked
- No API key required

## Current QA evidence

- 62 automated tests pass
- 12 of 12 judge-ready demo checks pass
- Real Gradio server smoke test passes with HTTP 200
- Final packaging script extracts the ZIP and reruns tests, demo checks, and the smoke test

## Required limitation statement

> This dataset is synthetic and was generated for demonstration and evaluation. It does not represent current real-world hiring conditions.

CareerProof does not predict hiring, rank employer quality, establish causation, or forecast future job volume.

## Fast recovery

- If a question was edited incorrectly, click the matching judge-ready question button.
- If an upload causes an error, select **Restore bundled demo**.
- If a filter returns no rows, clear the Explore filters and apply again.
- If a proof file is missing, rerun the remote-skills question and download a fresh proof bundle.
