# CareerProof AI Demo Script

Target length: 6 to 8 minutes.

## 0:00-0:35 - Opening

Hello. Our project is CareerProof AI, built for Track 2, Trustworthy Data Analysis.

Students and early-career job seekers can look through hundreds of job listings and still struggle to answer basic questions like which skills appear most often, where entry-level opportunities are concentrated, or whether salary comparisons are based on enough data.

The problem with a normal chatbot is that it can give a confident answer without actually calculating from the dataset. CareerProof AI follows one rule: AI interprets the question. Code calculates the answer.

## 0:35-1:15 - Target user and product

Our target users are high school and college students, recent graduates, career counselors, and workforce-development teams.

The user can use the bundled demonstration dataset or upload a CSV or Excel file. The Data Dock validates the file, maps common column names, checks missing values and invalid records, masks sensitive fields, and creates a dataset fingerprint.

The bundled dataset is synthetic. It contains 654 raw postings and 646 cleaned postings. It is designed for demonstration and does not represent the current job market.

## 1:15-2:00 - Architecture

The workflow is simple.

First, we validate and clean the data while recording every action. Then a small local AI model classifies the question intent. It never writes code and never calculates the numerical answer.

The app creates a structured query plan. An allowlist validator checks every field, filter, metric, and operation. Only then does deterministic Pandas code perform the calculation.

The final result includes a chart, table, masked source rows, calculation details, a confidence score, and an Evidence ID.

## 2:00-4:15 - Main live demo

I will ask: What are the ten most requested skills for remote jobs?

The app returns a Verified by code label. It matched 223 remote postings. Project Management appeared in 122 postings, Azure in 121, and Git in 119.

The confidence score is 89 out of 100. That score is not based on how certain the AI sounds. It is based on usable rows, relevant-field completeness, question-intent clarity, and the data-quality score.

The proof line shows the five stages: question, plan, validation, calculation, and proof.

Now I will open the evidence section. The query plan shows a skill-frequency intent with a Remote work-mode filter. The calculation explains that each skill is counted at most once per posting. The source table shows the matching rows, but recruiter names, emails, phone numbers, and source IDs are masked.

The Evidence ID is CP-88B4ACE97069E1CF. It is created from the dataset fingerprint, privacy-safe validated query plan, and result. If any of those change, the ID changes.

The result can be downloaded as an HTML evidence report, masked source CSV, result CSV, validated query-plan JSON, or proof-bundle JSON. In the Trust Center, that JSON can be re-uploaded. The verifier recomputes the ID. When the active dataset matches, it reruns the validated plan and confirms that the result reproduces. This is stronger than trusting a saved answer on its own.

## 4:15-5:05 - Second success case

Next I will ask: Which companies have the most internship opportunities?

The app matches 114 internship postings. Great Lakes Data Cooperative leads with 12 postings, followed by Blue Ridge Analytics with 11 and Harborlight HealthTech with 10.

Again, the answer is a row count calculated from the dataset, not a model guess.

## 5:05-5:55 - Failure case

Now I will ask: Which company has the happiest employees?

CareerProof refuses the question. It explains that the dataset has no employee-satisfaction field. It does not invent a company ranking. The Refusal Coach suggests nearby questions the dataset can answer.

This same guardrail blocks guaranteed hiring outcomes, future predictions, protected-attribute analysis, requests for raw recruiter contacts, and unsafe code-execution instructions.

## 5:55-6:40 - Unique features

In Explore, Career Signal Lab compares skills a user already has with the strongest required-skill signals for a selected role. It clearly says this is descriptive overlap, not a hiring prediction.

Scenario Compare lets the user compare work modes, experience levels, states, or roles across posting count, salary coverage, median salary midpoint, companies, and top skill.

The Data Quality tab shows a 94 out of 100 quality score, missingness, detected issues, and the cleaning ledger. Nothing is removed silently.

## 6:40-7:15 - Testing and limitations

Before packaging, 62 automated tests passed. They cover calculations, privacy masking, proof tampering, exports, query validation, safe refusal, malformed input, adversarial prompts, and app construction without an API key.

The main limitation is that the included dataset is synthetic and not a live labor-market source. CareerProof does not predict hiring, rank employer quality, or forecast the future.

## 7:15-7:35 - Closing

CareerProof AI demonstrates practical, trustworthy AI. It uses AI where language understanding helps, uses code where correctness matters, and makes the evidence visible to the user.

CareerProof AI. Ask the job market. See the proof.
