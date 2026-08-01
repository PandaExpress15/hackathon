# CareerProof AI Judging Alignment

Track: **2 — Trustworthy Data Analysis**

## Problem and usefulness — 25%

CareerProof helps students and early-career users choose among careers while AI changes work. It converts a user’s interests, skills, education ceiling, salary target, location, and priorities into an inspectable career portfolio and practical next-step plan.

Implemented evidence:

- Editable goal interpretation
- Hard feasibility gates
- Personalized recommendations
- Career portfolio
- Compare Lab
- Skill Bridge
- Degree and location intelligence
- Saved plans and decision journal

## Working prototype — 25%

The application works end to end with bundled official data and no required live API.

Verified evidence:

- 81 automated tests
- 19 workflow checks
- 11 judge diagnostic checks
- 33 Chromium browser acceptance checks
- Server smoke test
- Mobile, keyboard, reduced-motion, and reset behavior

## Data and AI quality — 15%

Implemented evidence:

- Controlled natural-language interpretation
- Occupation, state, degree, and metric resolution
- TF-IDF retrieval over official occupation and O*NET text
- Exact SOC and CIP joins
- Deterministic calculations
- Eight official source families
- Career Resilience Profile v1.0
- Counterfactual sensitivity testing

## Trust and safety — 15%

Implemented evidence:

- Evidence Passports
- Direct versus transformed versus derived labels
- Source confidence and decision confidence
- Recommendation challenger
- Hard constraints
- Data-quality monitor
- Source-vintage warning
- Safe refusal
- No arbitrary code execution
- Human confirmation and control

## Architecture clarity — 10%

```text
User profile or question
→ controlled interpretation
→ user confirmation
→ allowlisted official-data route
→ deterministic calculation and hard gates
→ explanation, challenge, and evidence
→ human decision
```

## Demo and storytelling — 10%

The final interface follows the approved dark dashboard. Judge Mode tells one focused story from uncertainty to an evidence-backed plan, then demonstrates a supported result and a safe refusal.

## Scoring target

A perfect score cannot be guaranteed. This build is designed to compete in the **98+ range** by maximizing the published rubric rather than adding unfinished complexity.
