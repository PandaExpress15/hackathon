# Bundled Data

CareerProof bundles versioned snapshots from eight official source families so the complete demonstration works without an API key or network connection.

## Raw source snapshots

`data/raw/` contains source files from:

- BLS OEWS national estimates
- BLS OEWS state estimates
- BLS Employment Projections
- BLS OEWS estimates by typical entry education
- O*NET occupational files
- NCES/BLS CIP-to-SOC crosswalk

## Verified processed snapshots

`data/processed/` contains normalized analytical tables, including:

- 830 detailed occupations
- 36,168 state-occupation records
- O*NET skills, knowledge, tasks, software, education, and job-zone information
- 2024 Census ACS broad bachelor’s-field earnings
- 51 BEA state and District of Columbia Regional Price Parities
- 5,917 degree-to-occupation links covering 2,142 CIP programs

`data/metadata/data_catalog.json` records provenance, source vintages, licenses, coverage, row counts, and SHA-256 checksums.

No synthetic labor-market, salary, growth, education, or employment records are bundled. Fictional user profiles appear only as clearly labeled demonstration scenarios.

See `docs/DATA_SOURCES.md` for authoritative URLs, licenses, transport notes, transformations, and limitations.
