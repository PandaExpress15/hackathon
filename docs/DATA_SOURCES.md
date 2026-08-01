# CareerProof AI Data Sources

CareerProof bundles public official snapshots so the demonstration does not depend on a live external API.

## Source catalog

| ID | Agency | Dataset | Vintage | Use |
| --- | --- | --- | --- | --- |
| `bls-oews-national-2025` | U.S. Bureau of Labor Statistics | Occupational Employment and Wage Statistics, national | May 2025 | National employment and wage distribution |
| `bls-oews-state-2025` | U.S. Bureau of Labor Statistics | Occupational Employment and Wage Statistics, state | May 2025 | State wages, employment, concentration, and estimate quality |
| `bls-projections-2024-2034` | U.S. Bureau of Labor Statistics | Employment Projections | 2024–2034 | Growth, openings, education, experience, and training |
| `bls-oews-education-2025` | U.S. Bureau of Labor Statistics | OEWS by typical entry education | May 2025 | Education-level wage comparisons by geography |
| `onet-30-3` | O*NET / U.S. Department of Labor | O*NET Database | 30.3 | Descriptions, skills, knowledge, tasks, technologies, education responses, and job zones |
| `census-acs-b15013-2024` | U.S. Census Bureau | ACS B15013 | 2024 1-Year | Broad bachelor’s-field median earnings and margins of error |
| `bea-rpp-2024` | U.S. Bureau of Economic Analysis | Regional Price Parities | 2024 | State price-level adjustment |
| `nces-cip-soc-2020-2018` | NCES and BLS | CIP-to-SOC crosswalk | CIP 2020 / SOC 2018 | Qualitative degree-to-occupation relationships |

Authoritative URLs, licenses, retrieval notes, file names, row counts, and SHA-256 checksums are stored in `data/metadata/data_catalog.json`.

## Verified processed coverage

- 830 occupations
- 36,168 state occupation rows
- 5,917 degree-to-occupation links
- 2,142 unique instructional programs
- 51 price parity geographies
- 15 detailed broad degree-field groups plus total
- 583 education-wage geographies

## Data categories

### Direct official values

Published fields such as median wage, wage percentiles, employment, growth, annual openings, education, skill importance, task statements, price parity, and degree crosswalk relationships.

### Transformed official values

Documented filters, unit conversions, sorts, percentiles, and purchasing-power adjustments.

### CareerProof-derived values

Transparent decision scores, market stability, Career Resilience Profile, transition similarity, state opportunity score, and user-weighted rankings.

Derived values are never labeled as government ratings.

## Data quality

The application monitors:

- Missing wages
- Suppressed state records
- Missing projection fields
- Small employment bases
- Missing O*NET components
- Weak or absent degree crosswalk relationships
- Missing preferred-state coverage
- Source-vintage differences

## Source-vintage warning

The sources describe different measurement periods. May 2025 wages, 2024–2034 projections, O*NET 30.3 work content, 2024 ACS earnings, 2024 BEA prices, and the CIP 2020/SOC 2018 crosswalk are useful together as decision context but should not be interpreted as one synchronized snapshot.

## Licensing and attribution

- BLS, Census, BEA, and NCES public data remain subject to agency terms.
- O*NET content is used under Creative Commons Attribution 4.0.
- The application code is MIT licensed.

See `data/LICENSE.md` and `THIRD_PARTY_NOTICES.md`.
