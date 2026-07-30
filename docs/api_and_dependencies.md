# APIs and Dependencies

## External APIs

CareerProof AI requires no external API. It works fully offline after dependencies are installed.

No live job-board, email, payment, publishing, or proprietary model integration is used.

## Optional environment settings

| Variable | Purpose | Default |
|---|---|---|
| `CAREERPROOF_DEBUG` | Show detailed UI errors during development | `false` |
| `CAREERPROOF_SERVER_NAME` | Local server bind address | `127.0.0.1` |
| `CAREERPROOF_SERVER_PORT` | Local server port | `7860` |

No API key is accepted or required by the current release.

## Data source

The bundled CSV and XLSX files are participant-generated synthetic data. See `data/README.md` and `data/LICENSE.md`.

## Third-party software

See `THIRD_PARTY_NOTICES.md` for packages and licenses.

## Installation files

- `requirements.txt` installs the runtime and verification dependencies used by the simplest local workflow.
- `requirements-dev.txt` includes `requirements.txt` and adds Ruff for linting.
- `pyproject.toml` supports an editable install with the `dev` optional dependency group.
