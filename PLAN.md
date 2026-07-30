# CareerProof AI Build Plan

This plan records the implementation path used for the hackathon project. The completed repository follows the participant guide's priority: a working end-to-end product first, then visible evidence, trust controls, testing, and submission assets.

## 1. Define

- Track: Track 2, Trustworthy Data Analysis
- Users: students, early-career job seekers, career counselors, and workforce-development teams
- Problem: job-posting questions are difficult to answer across large datasets, while general chatbots can invent unsupported results
- Core promise: **AI interprets the question. Code calculates the answer.**

## 2. Core workflow

- Generate a deterministic synthetic job-posting dataset
- Load CSV or XLSX files
- Map fields into a canonical schema
- Validate and clean the data without silently hiding changes
- Translate supported natural-language questions into structured query plans
- Execute deterministic Pandas calculations
- Display an answer, chart, table, sample size, calculation steps, and source rows

## 3. Trust layer

- Mask recruiter names, emails, phone numbers, and source IDs
- Validate every query plan against field, metric, filter, and operation allowlists
- Refuse unsupported, unsafe, private, predictive, or discriminatory questions
- Assign confidence from data completeness, usable row count, model certainty, and quality issues
- Generate an Evidence Passport ID for each result and replay exported proofs against the active dataset
- Record local masked audit events

## 4. Product depth

- Data Quality dashboard and Cleaning Ledger
- Scenario Compare
- Career Signal Lab
- Refusal Coach
- HTML report and evidence exports
- Dataset upload and reset controls
- Six-tab Gradio interface with a judge-ready demo path

## 5. Quality assurance

- Unit and integration tests
- Adversarial input tests
- Ten supported demo questions and two expected refusal cases
- Submission verification script and application launch smoke test
- Reproducible ZIP build, extracted-package retest, and checksum manifest
- Presentation, architecture diagram, demo script, disclosures, and judging alignment

## 6. Final manual steps

- Fill in team details
- Create or update the public GitHub repository
- Push the repository and commit history
- Record and upload the presentation video
- Upload the final ZIP and submit the official form
