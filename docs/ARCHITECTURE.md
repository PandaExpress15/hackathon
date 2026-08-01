# CareerProof AI Architecture

Version: **4.1.0-presentation-ready**

## Design principle

CareerProof separates interpretation from calculation:

> **AI interprets. Code calculates. Evidence verifies. You decide.**

## End-to-end flow

```text
User profile or natural-language question
        ↓
Input validation and text normalization
        ↓
Controlled interpretation
  - intent
  - occupation and geography entities
  - interests and skills
  - hard constraints
  - user weights
        ↓
Human confirmation or clarification
        ↓
Allowlisted operation and official dataset route
        ↓
Exact SOC, CIP, state, and source joins
        ↓
Deterministic calculation
  - hard feasibility gate
  - percentile normalization
  - weighted score
  - resilience dimensions
  - confidence and data quality
        ↓
Explanation and challenge layer
  - reasons
  - tradeoffs
  - counterfactuals
  - weakest evidence
  - limitations
        ↓
Evidence Passport
        ↓
Human-controlled shortlist, comparison, roadmap, or report
```

## Application layers

### Interface

- Server-rendered HTML shell
- Production CSS design system
- Plain JavaScript application state and interactions
- Responsive layout, keyboard focus, and reduced-motion support

### API

FastAPI endpoints provide:

- Bootstrap and home dashboard
- Profile interpretation
- Path Builder
- Compare Lab
- Skill Bridge
- Career Universe
- Occupation profiles
- Degree pathways
- State opportunity
- Natural-language analysis
- Resilience model card
- Data quality
- Diagnostics
- Judge Mode
- HTML evidence reports

### Data layer

Pandas loads bundled official CSV snapshots. Exact indexes are built for:

- Occupation title and SOC code
- State plus SOC code
- Degree plus SOC relationships
- O*NET skills, knowledge, tasks, and technologies
- State price parity

### Interpretation layer

The controlled parser performs:

- Intent routing
- Occupation resolution
- Geography resolution
- Degree-field resolution
- Salary and education extraction
- Interest and skill extraction
- Hard-constraint detection warnings
- Editable structured profile generation

Explicit form selections remain authoritative. Free text cannot silently override a user’s hard-toggle choice.

### Calculation layer

All factual outputs are calculated by allowlisted Python functions. The application never executes user-generated Python or unrestricted SQL.

Path Builder and Compare Lab use eight inspectable components. Hard constraints are evaluated independently from the weighted score.

### Resilience layer

Career Resilience Profile v1.0 computes six relative percentiles from official occupation and O*NET work content. The full model card, formula, lexicons, and limitations are exposed through the API and user interface.

### Trust layer

- Direct versus derived labels
- Source confidence
- Decision confidence
- Evidence Passports
- Data-vintage warning
- Missing and suppressed value monitoring
- Safe refusal
- Recommendation challenger
- Human confirmation
- Audit-friendly machine-readable diagnostics

## Data lineage

| Output | Source path |
| --- | --- |
| National wage range | BLS OEWS national → SOC code |
| State wage and concentration | BLS OEWS state → state + SOC code |
| Growth and openings | BLS projections → SOC code |
| Skills and tasks | O*NET → SOC code |
| Purchasing-power wage | BLS state wage + BEA RPP → state |
| Degree pathway | NCES/BLS CIP-to-SOC crosswalk → CIP + SOC |
| Broad degree earnings | Census ACS B15013 → degree group |
| Resilience dimensions | Official occupation and O*NET text → transparent lexical signals → occupation percentiles |

## State management

- Current workspace, profile, comparison, and question context live in browser memory.
- Saved careers and decision notes use local browser storage.
- A safe in-memory fallback is used when local storage is unavailable.
- No personal account or cloud persistence is required for the demo.

## Deployment

`app.py` starts Uvicorn and reads the `PORT` environment variable. The app uses bundled data and does not require a live external API, which reduces demo risk.

## Security boundary

- Pydantic validates API input lengths and numeric ranges.
- Source operations are allowlisted.
- User text is escaped before HTML insertion.
- No credentials are stored in source control.
- No arbitrary code execution exists.
- Unsupported causal, guaranteed, discriminatory, employer-specific, or unavailable live-data claims are refused.

## Testing architecture

- Unit and integration tests
- Natural-language regression suite
- Advanced workflow checks
- Judge diagnostic
- Server smoke test
- In-process Chromium acceptance suite
- Submission checksum and secret verification
