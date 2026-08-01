# Changelog

## 4.1.0 — Presentation-Ready Judge Build

### Judge Mode

- Rebuilt Judge Mode as a timed 10-stage presentation
- Added a 7:50 full presentation and a 4:25 quick pitch
- Added visible alignment to all six participant-facing judging categories
- Added presenter narration, proof points, timeline navigation, keyboard controls, autoplay, and one-click reset
- Added live-feature launch controls for Path Builder, Compare Lab, evidence, refusal, Saved Plans, diagnostics, and Home
- Added a verified success case, recommendation challenge, comparison case, evidence case, safe failure case, action plan, architecture explanation, and rubric close

### Readability and interface quality

- Increased general and informational text at normal browser zoom
- Increased navigation, form, table, evidence, and explanation text while preserving responsive layouts
- Added automated browser checks for computed information-text sizes
- Preserved zero horizontal overflow at 390 pixels and reduced-motion support

### Deployment

- Added production `PORT` handling and default `0.0.0.0` binding
- Added `render.yaml`, `Procfile`, `Dockerfile`, and `.dockerignore`
- Added a public deployment guide and health-check instructions

### Testing

- Expanded to 83 unit and integration tests
- Expanded to 39 Chromium browser acceptance checks
- Added browser coverage for full and quick Judge Modes, narration, rubric proof, autoplay, reset, live-feature launching, and readability

## 4.0.0 — Resilience Intelligence Final

### Product

- Rebuilt the interface around the approved premium dark dashboard
- Added dedicated Home dashboard and focused Discover → Compare → Verify → Plan journey
- Added responsive mobile navigation and zero-overflow 390-pixel layout
- Added one-click demo reset and persistent comparison tray

### Path Builder

- Added two-stage editable interpretation
- Added free-text profile parsing with explicit-control authority
- Added hard education, salary, and location feasibility gates
- Expanded scoring from six to eight transparent components
- Added grouped results, career portfolio, near misses, and practical roadmaps
- Added recommendation challenger and counterfactual sensitivity

### AI resilience

- Added Career Resilience Profile v1.0
- Added six documented dimensions and exact formula
- Added matched signals, task examples, AI augmentation potential, and task-impact explanations
- Added full model card and limitations

### Trust

- Expanded Evidence Passports
- Added source-versus-decision confidence
- Added data-quality monitor
- Added persistent source-vintage warning
- Strengthened safe refusal and boundary language

### Intelligence and data

- Added state and degree indexes for faster repeated analysis
- Added token-safe skill extraction
- Added explicit profile interpretation endpoint
- Added home, resilience-model, and data-quality endpoints
- Enhanced occupation, degree, comparison, and location outputs

### Testing

- Expanded to 81 unit and integration tests
- Updated 19 workflow checks for eight-component scoring
- Passed 11 judge diagnostics
- Added 33-check Chromium browser acceptance suite
- Added screenshots and machine-readable browser report

## 3.0.0 — Final Intelligence Build

- Official multi-source career intelligence
- Career Universe
- Path Builder
- Compare Lab
- Skill Bridge
- Degree pathways
- Evidence Passports
- Safe refusal
- Judge Mode
