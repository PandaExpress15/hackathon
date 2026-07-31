# Testing Report

Generated from real executions on **2026-07-31T02:33:50+00:00** by `python scripts/run_demo_checks.py`.

## Summary

- Demo checks passed: **12/12**
- Bundled labor-market records: **official BLS, Census, and O*NET data only**
- Synthetic labor-market records: **0**
- Automated unit and integration tests: run with `pytest -q`

## Demo results

| # | Question | Expected | Actual | Dataset | Rows | Confidence | Evidence ID | Result |
| ---: | --- | --- | --- | --- | ---: | --- | --- | --- |
| 1 | Which states pay nuclear engineers the most? | supported | supported | BLS OEWS State | 10 | High (93) | `CP-8AB3A4CA16751859` | PASS |
| 2 | What skills do public relations specialists need? | supported | supported | O*NET 30.3 | 10 | High (92) | `CP-5D1B3E1D4BF57EE2` | PASS |
| 3 | Which broad bachelor's degree fields have the highest median earnings? | supported | supported | Census ACS Degree Earnings | 10 | High (91) | `CP-427CD1EED3B4C51A` | PASS |
| 4 | What is the job outlook for political scientists? | supported | supported | BLS Employment Projections | 1 | High (95) | `CP-00BF1ACB2C17532F` | PASS |
| 5 | How much do lawyers earn in Maryland? | supported | supported | BLS OEWS State | 1 | High (94) | `CP-6F3EECA6C4DFEFB8` | PASS |
| 6 | Compare lawyers and political scientists. | supported | supported | Unified BLS occupation profile | 2 | High (94) | `CP-3BBC37EAB72D8F63` | PASS |
| 7 | What tasks do public relations specialists perform? | supported | supported | O*NET 30.3 | 10 | High (92) | `CP-7D8778C4E706359A` | PASS |
| 8 | What software do broadcast technicians use? | supported | supported | O*NET 30.3 | 12 | High (92) | `CP-EBD4207B292771C0` | PASS |
| 9 | How do national wages compare by typical entry-level education? | supported | supported | BLS Education Wage Aggregates | 8 | High (94) | `CP-B65B3657D5DEC9A3` | PASS |
| 10 | Which states have the highest median wage for bachelor's-level occupations? | supported | supported | BLS Education Wage Aggregates | 10 | High (93) | `CP-0ED5ECB174B9AFF4` | PASS |
| 11 | What bachelor's degree should I pursue for the highest pay after becoming a lawyer? | refused | refused | Trust boundary | 0 | Insufficient evidence (0) | `CP-9A89C9CCE4A423DB` | PASS |
| 12 | Which company has the happiest employees? | refused | refused | Trust boundary | 0 | Insufficient evidence (0) | `CP-FE25157F656F4282` | PASS |

## Notes

- Values are calculated from the bundled official source snapshots.
- Evidence IDs are content-derived and change when the question route, query plan, or returned rows change.
- Refusal checks confirm that the application does not invent employer happiness, hiring guarantees, or lawyer-specific causal degree outcomes.
