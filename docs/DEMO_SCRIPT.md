# CareerProof AI Judge Presentation

CareerProof includes two guided presentation modes. Both are generated from the same verified `/api/judge-demo` payload used by the live product.

- **Full presentation:** 7 minutes 50 seconds
- **Quick pitch:** 4 minutes 25 seconds
- **Video limit:** under 10 minutes

## Before presenting

1. Start the server and open the public or local site.
2. Use 100 percent browser zoom.
3. Click the top-bar reset control.
4. Open **Guided Demo** from the left navigation.
5. Confirm the Full demo and Quick pitch durations are visible.
6. Keep autoplay off while speaking unless a hands-free run is required.
7. Wake a free public deployment before judging because free hosts may sleep while idle.

The demonstration profile is fictional. Labor-market values are bundled official records or clearly labeled CareerProof-derived metrics.

# Full presentation — 7:50

## 0:00–0:35 — A real decision, not another career quiz

**Judge category:** Problem and usefulness

> Students are being asked to make expensive, long-term career decisions while the labor market and AI are changing quickly. CareerProof turns that uncertainty into a decision the user can inspect, challenge, and act on.

Show the core question and verified coverage:

- 830 occupations
- 36,168 state occupation records
- 5,917 degree-career relationships
- 8 official source families

Use **Open the live home dashboard** only when the judges request the underlying workspace.

## 0:35–1:20 — AI interprets, the user approves

**Judge categories:** Data and AI quality, trust and safety

> The model never gets permission to invent a salary or rank a career by itself. It interprets the student's request into structured fields, then pauses for human review. The user can correct the goal, constraints, and weights before code calculates anything.

Point out:

- Electronics, programming, and law
- Python, Arduino, writing, and problem solving
- Bachelor’s degree hard ceiling
- Maryland preference
- $90,000 salary target
- Eight user-controlled weights normalized to 100 percent

## 1:20–2:25 — The Path Builder calculates a defensible recommendation

**Judge categories:** Working prototype, data and AI quality

> After the user confirms the interpretation, controlled retrieval identifies relevant occupations. Code applies hard feasibility gates first, then calculates eight visible score components from bundled official data. Electrical Engineers ranks first for this profile, but the raw values and contributions remain visible.

Show:

- Electrical Engineers as the top result
- Median wage and projected growth
- Eight transparent score components
- The number of careers removed by the bachelor’s-degree hard gate
- The visible CareerProof formula

## 2:25–3:15 — The recommendation explains how it could be wrong

**Judge category:** Trust and safety

> A trustworthy recommendation should not only defend itself. It should reveal its weakest evidence, missing information, assumptions, strongest challenger, and the conditions that would change the result.

Show:

- Weakest score components
- Missing or limited evidence
- Strongest challenger
- Counterfactual ranking changes
- The question the user should ask before committing

## 3:15–4:20 — Compare tradeoffs, not just scores

**Judge categories:** Working prototype, data and AI quality

> Compare Lab keeps wages, growth, openings, education, resilience, and feasibility visible. A professional-degree path can be blocked by the user's bachelor’s ceiling even when it has attractive pay. Changing priorities recalculates the ranking instead of hiding a fixed answer.

Show:

- Electrical Engineers
- Nuclear Engineers
- Lawyers as a blocked professional-degree path
- The plain-language tradeoff summary
- Scenario-based ranking changes

## 4:20–5:15 — Every important answer carries proof

**Judge categories:** Trust and safety, data and AI quality

> CareerProof combines published state wages with regional price levels to answer where an electrical engineer's pay may go furthest. The Evidence Passport exposes the source rows, formula, data vintages, source confidence, decision confidence, and limitations.

Point out:

- BLS state wage records
- BEA Regional Price Parities
- Cost-of-living calculation
- Rows used and excluded
- Source confidence and decision confidence
- Evidence ID and source-vintage warning

## 5:15–5:50 — When the data cannot prove it, CareerProof refuses

**Judge category:** Trust and safety

Question:

```text
Which bachelor's degree guarantees the highest salary after becoming a lawyer?
```

> The bundled data cannot establish that causal guarantee. CareerProof refuses the claim, explains the missing relationship, and suggests questions the evidence can answer instead.

This is the planned failure case. Do not apologize for the refusal. It demonstrates the product boundary.

## 5:50–6:35 — The analysis becomes a practical plan

**Judge categories:** Problem and usefulness, working prototype

> CareerProof does not stop at a ranked list. It creates a primary path, safer backup, high-upside option, fast-entry option, and a labeled roadmap that separates official requirements, common O*NET skills, and CareerProof recommendations.

Show:

- Primary path
- Backup path
- High-upside option
- Fast-entry option
- Learn, build, and prepare actions
- Saved plan and decision journal

## 6:35–7:20 — A simple architecture keeps the result inspectable

**Judge category:** Architecture clarity

> The architecture is intentionally simple: user request, editable interpretation, validated plan, deterministic calculation, evidence and control, then a human decision. User text and model output are never executed as arbitrary Python or unrestricted SQL.

Show the six stages:

1. User request
2. AI interpretation
3. Validated plan
4. Deterministic analysis
5. Evidence and control
6. Human decision

## 7:20–7:50 — Close against the rubric

**Judge category:** Demo and storytelling

> CareerProof solves one focused problem with a working end-to-end product. It uses AI for interpretation, code for reproducible calculations, official data for evidence, visible controls for trust, and a practical plan for the user. AI interprets. Code calculates. Evidence verifies. You decide.

Pause on the six rubric categories. End without opening another page.

# Quick pitch — 4:25

Quick mode includes these six stages:

1. Problem and usefulness — 0:35
2. Editable AI interpretation — 0:45
3. Verified Path Builder result — 1:05
4. Evidence Passport and cost-of-living answer — 0:55
5. Unsupported-question refusal — 0:35
6. Rubric close — 0:30

Use Quick mode for a short live judging slot. Use Full mode for the final under-10-minute presentation video.

# Presentation controls

- Click any timeline step to jump directly to it.
- Use the left and right arrow keys to navigate.
- Press Space to toggle autoplay.
- Press Escape to close Judge Mode.
- **Open live feature** launches the workspace matching the current stage.
- **Reset** restores the verified demonstration profile and returns to stage one.
- Full and Quick modes both restart their timer when selected.

# Failure recovery

- If a public free host is waking up, wait for the health check and refresh once.
- If a live feature is opened, return to Guided Demo and select the desired timeline step.
- If a value looks different after editing the profile, click Reset before continuing.
- If the browser zoom is not 100 percent, reset it before presenting.
- Keep the local server available as a backup to the public URL.
