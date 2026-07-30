# Testing Report

Generated from real executions on **2026-07-30 18:48 UTC** by `python scripts/run_demo_checks.py`.

## Summary

- Demo checks passed: **12/12**
- Supported questions passed: **10/10**
- Expected refusal cases passed: **2/2**
- Automated tests collected: **62**
- Raw dataset rows: **654**
- Cleaned dataset rows: **646**
- Dataset quality score: **94/100**
- Dataset fingerprint: `d1d0cd52e1bda4c6`

The bundled dataset is synthetic. The report describes the supplied demonstration data and does not make claims about the live labor market.

## Demo-check results

| # | Question | Expected | Actual | Rows used | Confidence | Evidence | Chart | Evidence ID | Result |
|---:|---|---|---|---:|---|---:|---:|---|---|
| 1 | Which cities have the most entry-level job postings? | supported | supported | 207 | High confidence (89) | Yes | Yes | `CP-83620259C226639C` | PASS |
| 2 | What are the ten most requested skills for remote jobs? | supported | supported | 223 | High confidence (89) | Yes | Yes | `CP-88B4ACE97069E1CF` | PASS |
| 3 | Which companies have the most internship opportunities? | supported | supported | 114 | High confidence (84) | Yes | Yes | `CP-F1A4DCCA9F027DBE` | PASS |
| 4 | What is the median salary range by experience level? | supported | supported | 540 | High confidence (87) | Yes | Yes | `CP-D66909739666094A` | PASS |
| 5 | How does estimated salary compare between remote, hybrid, and on-site jobs? | supported | supported | 540 | High confidence (82) | Yes | Yes | `CP-FF393D798C518B77` | PASS |
| 6 | What percentage of postings do not disclose salary? | supported | supported | 646 | High confidence (87) | Yes | Yes | `CP-7E97202AA2602B0F` | PASS |
| 7 | How has job-posting volume changed over time? | supported | supported | 645 | High confidence (94) | Yes | Yes | `CP-AADAE22F4EDDE07D` | PASS |
| 8 | Which skills appear most often in electrical engineering and embedded-systems roles? | supported | supported | 129 | High confidence (89) | Yes | Yes | `CP-A5D3E242091F1384` | PASS |
| 9 | Which states have the highest number of entry-level engineering jobs? | supported | supported | 113 | High confidence (84) | Yes | Yes | `CP-1F4F7FDC949EF4CC` | PASS |
| 10 | Which companies have the highest median salary among companies with at least five postings? | supported | supported | 540 | High confidence (87) | Yes | Yes | `CP-821EA4EC479BA66C` | PASS |
| 11 | Which company has the happiest employees? | unsupported | unsupported | 0 | Insufficient evidence (0) | Yes | No | `CP-7AEBDAFC270C6B2F` | PASS |
| 12 | Which job will guarantee that I get hired? | unsupported | unsupported | 0 | Insufficient evidence (0) | Yes | No | `CP-425B839FC93423C6` | PASS |

## Representative verified result

**Question:** What are the ten most requested skills for remote jobs?

**Verified result:** Project Management is the strongest signal in 122 postings

**Rows used:** 223

**Confidence:** High confidence (89/100)

**Evidence ID:** `CP-88B4ACE97069E1CF`

## Representative safe refusal

**Question:** Which company has the happiest employees?

**System behavior:** The dataset cannot support that conclusion

**Evidence ID:** `CP-7AEBDAFC270C6B2F`

The system refused because the dataset does not contain the field required to support the requested conclusion. It did not invent an employer-quality judgment.

## Additional automated tests

Run the full unit and integration suite with:

```bash
pytest -q
```

The current suite contains **62 tests**. The submission verifier runs every test and stops packaging if any test fails.

The suite covers schema validation, cleaning, privacy masking, proof-bundle integrity and replay, intent routing, query validation, deterministic execution, confidence scoring, exports, refusals, adversarial inputs, audit logging, UI construction, and the prohibition on arbitrary code execution.

## Real application launch check

Run the Gradio server smoke test with:

```bash
python scripts/smoke_test_app.py
```

The smoke test launches the real application on a temporary loopback port, waits for HTTP 200, confirms the CareerProof title marker, and shuts the server down. The submission verifier runs this check automatically.

## Pass criteria used by this script

- A supported question must return a nonempty deterministic result table, a calculation/evidence bundle, and a chart.
- An expected refusal must return `unsupported`, include a clear reason, and still generate a traceable proof bundle.
- Every result must have a confidence label and Evidence ID.
