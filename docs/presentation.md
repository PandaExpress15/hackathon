# CareerProof AI Presentation

## Slide 1 - Title

**CareerProof AI**

Ask the job market. See the proof.

Track 2 - Trustworthy Data Analysis

> AI interprets the question. Code calculates the answer.

**Dataset disclosure:** This dataset is synthetic and was generated for demonstration and evaluation. It does not represent current real-world hiring conditions.

---

## Slide 2 - The problem

Students and early-career job seekers face hundreds of listings but struggle to calculate:

- Which skills employers request most
- Where entry-level opportunities are concentrated
- Which employers post internships
- How salary patterns compare
- Whether an answer is supported by enough data

A normal chatbot can sound confident without calculating from the supplied dataset.

**Target users:** students, recent graduates, career counselors, and workforce-development teams.

---

## Slide 3 - The product

CareerProof AI turns a CSV or XLSX file into a transparent question-answering dashboard.

1. Ask a question in normal language.
2. Inspect the structured query plan.
3. See the deterministic calculation.
4. Review the chart, result table, and masked source rows.
5. Download an Evidence Passport.

Bundled demo snapshot:

- 654 raw synthetic postings
- 646 cleaned postings
- 94/100 data-quality score
- 84% complete salary coverage
- 10 judge-ready supported questions

---

## Slide 4 - Trustworthy architecture

**Dataset → Validation → Privacy → Local AI → QueryPlan → Pandas → Evidence**

- Local TF-IDF and logistic regression identify intent.
- AI does not calculate or invent numbers.
- Pydantic creates a structured query plan.
- Field, metric, filter, and operation allowlists block unsafe plans.
- Pandas performs deterministic calculations.
- Confidence comes from sample size, completeness, intent clarity, and quality.
- Unsupported questions are refused.

---

## Slide 5 - Live result with proof

Question:

**What are the ten most requested skills for remote jobs?**

Verified result:

- 223 remote postings matched
- Project Management appeared in 122 postings
- Azure appeared in 121
- Git appeared in 119
- High confidence: 89/100
- Evidence ID: `CP-88B4ACE97069E1CF`

Every skill is counted at most once per posting.

---

## Slide 6 - Unique features

### Evidence Passport
Fingerprint the dataset, privacy-safe validated query plan, and result. Re-upload the proof bundle to recompute the Evidence ID. When the active dataset matches, CareerProof reruns the validated plan and confirms that the result reproduces.

### Refusal Coach
Refuse unsupported conclusions and suggest nearby answerable questions.

### Career Signal Lab
Compare a user's skills with frequent role-level signals without predicting hiring.

### Scenario Compare
Compare work modes, experience levels, states, or roles.

### Cleaning Ledger
Show every data-cleaning action instead of silently altering records.

---

## Slide 7 - Safe failure is a feature

Question:

**Which company has the happiest employees?**

Response:

> The dataset cannot support that conclusion. The dataset has no employee-satisfaction field.

The app also blocks:

- Guaranteed hiring outcomes
- Future predictions
- Protected-attribute analysis
- Raw recruiter contacts
- Arbitrary code execution

Automated validation: **62 tests passed** before final packaging.

---

## Slide 8 - Value, limitations, and next steps

### Value

- Makes job-posting analysis usable for students and counselors
- Shows proof behind every supported conclusion
- Demonstrates practical AI with visible trust controls
- Runs locally without a paid API

### Limitations

- This dataset is synthetic and was generated for demonstration and evaluation. It does not represent current real-world hiring conditions.
- It is not a live labor-market tracker.
- It does not predict hiring or rank employer quality
- Salary comparisons require complete ranges and minimum samples

### Next steps

- Add licensed live datasets
- Add authenticated team workspaces
- Compare snapshots over time
- Add administrator-approved schema mappings

**CareerProof AI: ask the data, inspect the proof, trust the process.**
