# CareerProof AI Checkpoint Pack

This file is a ready-to-use response guide for the three official hackathon checkpoints in the participant guide.

## Checkpoint 1: Idea validation

**Official time:** Thursday, July 30 at 6:00 PM

### 30-second explanation

CareerProof AI helps students, recent graduates, and career counselors ask questions about job-posting data without trusting unsupported chatbot claims. A local AI model interprets the question, but deterministic Pandas code calculates every factual answer. Each result includes a chart, table, calculation steps, masked source rows, a data-based confidence score, and an Evidence Passport.

### Problem and user

- **User:** Students and early-career job seekers, plus counselors who support them
- **Problem:** Job listings are difficult to summarize reliably, and a normal chatbot may invent a plausible answer
- **Input:** Bundled synthetic job-posting data or a user CSV/XLSX upload
- **Output:** Code-verified answer with visible evidence
- **Trust mechanism:** PII masking, structured query allowlists, safe refusal, confidence labels, audit logging, and a verifiable Evidence Passport

### Minimum end-to-end demo

1. Load the bundled dataset.
2. Ask: `What are the ten most requested skills for remote jobs?`
3. Show the verified answer, chart, result table, and masked evidence.
4. Ask: `Which company has the happiest employees?`
5. Show the unsupported-question refusal.

### Why it fits Track 2

- It uses a dataset with more than 30 rows.
- It answers more than three questions from actual data.
- Calculations come from code, not generated prose.
- Every supported answer includes evidence.
- Unsupported questions are refused instead of guessed.

## Checkpoint 2: Architecture review

**Official time:** Friday, July 31 at 10:00 AM

### One-minute architecture explanation

The user selects the bundled dataset or uploads CSV/XLSX data. CareerProof maps the columns into a canonical schema, validates the values, records cleaning actions, and fingerprints the cleaned dataset. Sensitive fields are masked before display or export.

A local TF-IDF and logistic-regression model classifies the question intent. It does not calculate the answer. A rule-assisted router creates a typed Pydantic `QueryPlan`. An allowlist validator checks every field, metric, filter, and operation. Deterministic Pandas code executes the approved plan. The app then creates the answer, chart, evidence table, confidence score, Evidence ID, report, and masked audit record.

Downloaded proof bundles can be re-uploaded. The verifier recomputes the Evidence ID and, when the active dataset matches, reruns the validated plan to confirm that the result reproduces.

### Architecture questions and answers

| Judge question | CareerProof answer |
|---|---|
| What is the input? | Bundled synthetic job-posting CSV/XLSX data or a user upload |
| What does AI do? | Classifies intent and helps map the question to an approved plan |
| What does code do? | Performs every factual count, grouping, percentage, trend, and salary calculation |
| How do you know it is correct? | Visible plan, formula, source rows, result table, dataset fingerprint, and replayable Evidence Passport |
| What is the safety layer? | Allowlisted execution, PII masking, confidence rules, refusal behavior, and local audit logging |
| What happens when data is insufficient? | The system returns insufficient evidence or refuses the unsupported conclusion |

### Failure cases already covered

- Missing or malformed uploads
- Empty and header-only files
- Files above row or column limits
- Requests for raw recruiter contacts
- Prompt-injection and arbitrary-code instructions
- Protected-attribute questions
- Unsupported employer-quality or future-outcome questions
- Small salary comparison groups
- Tampered proof bundles

## Checkpoint 3: Submission readiness

**Official time:** Friday, July 31 at 3:00 PM

### Completion status

- Working local app
- Bundled dataset and formatted workbook
- Supported and unsupported demo questions
- Visible trust controls
- Automated tests
- Application launch smoke test
- README and setup instructions
- Architecture diagram and explanation
- Presentation PPTX and PDF
- Demo script and recording guide
- Data, dependency, privacy, limitation, and pre-existing-work disclosures
- Submission verifier
- Reproducible ZIP builder and checksum manifest

### Commands to show

```bash
python -m pip install -r requirements.txt
python app.py
pytest -q
python scripts/run_demo_checks.py
python scripts/smoke_test_app.py
python scripts/verify_submission.py
python scripts/build_submission.py
```

### Manual items that remain outside the codebase

- Fill in team number and team-member names.
- Push the final Git history to a public repository.
- Record and upload the presentation video.
- Add the public GitHub and YouTube links to the submission checklist.
- Upload the final ZIP and complete the official submission form.

## Deadline plan

The participant guide lists a soft deadline on Friday, July 31 at 6:00 PM and a hard deadline on Saturday, August 1 at 10:00 AM. Submit an early working version by the soft deadline, then use the remaining time only for verified fixes, documentation, and final packaging.
