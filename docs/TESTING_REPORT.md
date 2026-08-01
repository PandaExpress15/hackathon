# Testing Report

Generated from real executions on **2026-08-01T16:39:01+00:00** by `python scripts/run_demo_checks.py`.

## Summary

- Total demonstration and workflow checks passed: **19/19**
- Natural-language and refusal checks: **12/12**
- Advanced workflow checks: **7/7**
- Bundled labor-market and education records: **eight official source families only**
- Synthetic labor-market records: **0**
- Automated unit and integration tests: **83/83 passed** with `pytest -q`
- Chromium browser acceptance checks: **39/39 passed**
- Live judge diagnostic checks: **11/11 passed**
- Browser console errors and page errors: **0**
- Mobile horizontal overflow at 390 pixels: **0 pixels**

## Natural-language and refusal results

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

## Advanced workflow results

| Workflow | Result | Executed evidence |
| --- | --- | --- |
| Official data coverage | PASS | `{"occupations": 830, "state_occupation_rows": 36168, "states_and_districts": 54, "degree_field_groups": 15, "education_geographies": 583, "official_sources": 8, "degree_occupation_links": 5917, "degree_programs": 2142, "price_parity_geographies": 51, "latest_wage_vintage": "May 2025", "projection_window": "2024–2034", "onet_release": "30.3", "census_vintage": "2024 ACS 1-Year", "rpp_vintage": "2024, released 2026", "crosswalk_vintage": "CIP 2020 / SOC 2018"}` |
| Ambiguous question routing | PASS | `{"expected": {"What is the salary for software developers?": "occupation_profile", "Which states pay software developers the most?": "highest_paying_states", "What is the job outlook for software developers?": "occupation_outlook", "What software do software developers use?": "software_tools", "What does a lawyer earn?": "occupation_profile", "What does a political scientist do?": "tasks"}, "actual": {"What is the salary for software developers?": "occupation_profile", "Which states pay software developers the most?": "highest_paying_states", "What is the job outlook for software developers?": "occupation_outlook", "What software do software developers use?": "software_tools", "What does a lawyer earn?": "occupation_profile", "What does a political scientist do?": "tasks"}}` |
| Personalized Path Builder | PASS | `{"results": 6, "top_match": "Electrical Engineers", "formula": "Score = user-weighted interest fit + resilience profile + wage percentile + growth percentile + openings percentile + education fit + location fit + market-stability score. Hard constraints are checked before ranking.", "roadmaps": 6, "score_components": ["education", "growth", "interest_fit", "location", "openings", "resilience", "salary", "stability"], "counterfactual_scenarios": 6, "challenge_panels": 6}` |
| User-controlled Compare Lab | PASS | `{"careers": ["Nuclear Engineers", "Electrical Engineers", "Lawyers"], "salary_first_top": "Electrical Engineers", "openings_first_top": "Electrical Engineers", "scores_changed": true}` |
| Multi-signal Skill Bridge | PASS | `{"overall_score": 58.9, "component_scores": {"skill_importance_readiness": 89.5, "software_overlap": 30.0, "task_similarity": 10.8}, "largest_gaps": 5}` |
| Qualitative Degree Pathways | PASS | `{"degree": null, "linked_occupations": 5, "qualitative_boundary_present": true}` |
| BLS + BEA state opportunity | PASS | `{"states": 53, "top_state": "Texas", "formula": "Opportunity score = 40% purchasing-power wage percentile + 30% employment percentile + 20% location-quotient percentile + 10% inverse employment-estimate RSE."}` |

## Notes

- Values are calculated from bundled official source snapshots.
- Evidence IDs are content-derived and change when the route, query plan, or returned rows change.
- Path Builder, comparison, similarity, and location scores are labeled CareerProof-derived decision aids and expose their formulas.
- Refusal checks confirm that the application does not invent employer happiness, hiring guarantees, or lawyer-specific causal degree outcomes.
- The Chromium suite executes the production template, CSS, JavaScript, and real FastAPI endpoints through `TestClient`.
- Judge Mode tests cover full and quick presentations, narration, rubric proof, timeline navigation, autoplay, reset, live-feature launching, and readability.
