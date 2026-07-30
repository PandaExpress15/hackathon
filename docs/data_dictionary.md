# Data Dictionary

This dataset is synthetic and was generated for demonstration and evaluation. It does not represent current real-world hiring conditions.

The bundled file contains **654 raw rows** and **646 rows after recorded cleaning actions**. The cleaned dataset fingerprint is `d1d0cd52e1bda4c6`.

## Fields

| Field | Logical type | May be missing | Sensitive | Description |
|---|---|---:|---:|---|
| `posting_id` | string | No | No | Unique posting identifier. Duplicate IDs are removed from analysis while the cleaning action is recorded. |
| `date_posted` | date | No | No | Posting date. Invalid values become missing rather than being guessed. |
| `job_title` | string | No | No | Display title for the fictional job posting. |
| `normalized_role` | category | No | No | Canonical role name used for filtering and comparisons. |
| `role_family` | category | No | No | Broader role grouping such as Engineering, Data, Software, Cybersecurity, or IT. |
| `company` | category | No | No | Fictional employer name. |
| `industry` | category | No | No | Fictional employer industry. |
| `city` | category | No | No | Posting city. |
| `state` | category | No | No | Two-letter state abbreviation. |
| `country` | category | No | No | Country code. Bundled records use the United States. |
| `work_mode` | category | No | No | Remote, Hybrid, On-site, or Unknown after validation. |
| `experience_level` | category | No | No | Internship, Entry Level, Associate, Mid Level, or Senior. |
| `employment_type` | category | No | No | Full-time, Part-time, Internship, or Contract. |
| `salary_min` | currency | Yes | No | Lower annual salary endpoint in USD. Invalid ranges are excluded from salary calculations. |
| `salary_max` | currency | Yes | No | Upper annual salary endpoint in USD. Invalid ranges are excluded from salary calculations. |
| `salary_period` | category | No | No | Salary period. Bundled records use annual salary. |
| `salary_currency` | category | No | No | Salary currency. Supported calculations use USD. |
| `required_skills` | semicolon-separated list | Yes | No | Required skills used for skill-frequency analysis. |
| `preferred_skills` | semicolon-separated list | No | No | Preferred or bonus skills. |
| `education_requirement` | category | Yes | No | Minimum education wording for the fictional posting. |
| `years_experience_required` | integer | No | No | Stated years of required experience. |
| `remote_eligible` | boolean | No | No | Whether the posting permits remote work. |
| `description_excerpt` | string | No | No | Synthetic short description excerpt. |
| `recruiter_name` | string | No | Yes | Fictional recruiter name. Masked in the interface, exports, reports, and audit logs. |
| `recruiter_email` | string | No | Yes | Fictional address on reserved example domains. Masked before display or export. |
| `recruiter_phone` | string | Yes | Yes | Fictional 555 number. Masked before display or export. |
| `source_type` | category | No | No | Synthetic source label used for provenance testing. |
| `source_record_id` | string | No | Yes | Synthetic source identifier. Treated as sensitive and masked. |
| `synthetic_record` | boolean | No | No | Disclosure flag confirming the record is synthetic. |
| `salary_midpoint` | currency, derived | Yes | No | Derived only when both salary endpoints are valid: (salary_min + salary_max) / 2. |
| `salary_disclosed` | boolean, derived | No | No | True only when both salary endpoints are valid and available. |

## Validation rules

- Required analysis fields must map to the canonical schema before a question can run.
- Posting IDs must be unique in the cleaned analysis frame.
- Dates are parsed explicitly. Invalid dates are left missing and reported.
- Salary values must be nonnegative, use a supported currency, and satisfy `salary_min <= salary_max`.
- Salary comparisons use only rows with both valid endpoints and always display sample sizes.
- Company salary rankings require at least five usable postings per company.
- Unknown work-mode or experience-level values are surfaced as quality issues rather than silently reclassified.
- Evidence tables and exports mask all fields classified as sensitive.

## Cleaning summary for the bundled dataset

- Duplicate posting IDs removed: **8**
- Invalid dates reported: **1**
- Invalid salary rows excluded from salary analysis: **3**
- Missing salary rows after cleaning: **106 (16.4%)**
- Detected sensitive columns: **recruiter_email, recruiter_name, recruiter_phone, source_record_id**
- Data-quality score: **94/100**

## Dataset provenance

The participant team generated the dataset with `scripts/generate_dataset.py` using a fixed random seed. All people, companies, job postings, emails, phone numbers, and source identifiers are fictional. Reserved example domains and fictional 555 numbers are used to avoid introducing real contact information.
