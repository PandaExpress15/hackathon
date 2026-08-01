# Security and Safety

## Guardrails

- Pydantic input validation and length limits
- Allowlisted analytical operations
- No arbitrary Python or unrestricted SQL execution
- Escaped user-visible HTML
- No committed credentials or `.env` file
- Official or properly licensed public data only
- Safe refusal for unsupported, discriminatory, guaranteed, causal, or unavailable claims
- Direct versus derived labels
- Source and decision confidence
- Hard-constraint confirmation
- Visible missing values, suppression, and limitations
- Human confirmation before personalized ranking

## Privacy

The demo does not require an account. Saved careers and notes are stored locally in the browser. A safe in-memory fallback is used if local storage is unavailable.

## Unsupported examples

- Guaranteed salary or career outcome
- Employer happiness or culture rankings
- Individual hiring probability
- Discriminatory ranking by protected trait
- Live vacancies not present in the bundle
- Causal claims linking a degree to a specific occupation salary

## Output safety

CareerProof redirects unsupported questions toward analyses the data can verify. It does not hide uncertainty behind a generic confidence badge.
