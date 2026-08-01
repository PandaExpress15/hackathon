# CareerProof Career Resilience Profile Model Card

Version: **1.0.0**  
Build: **CareerProof AI 4.1.0**

## Purpose

The Career Resilience Profile helps users compare occupational work characteristics that may remain important as AI changes work. It does not predict whether an occupation will disappear. It does not produce an official government rating. It is a transparent CareerProof-derived decision aid built from bundled official work-profile data.

## Intended use

Use the model to:

- Compare the kinds of human and real-world advantages described in official occupation profiles
- Explain why a career receives a stronger or weaker resilience result
- Test how a career ranking changes when resilience receives more or less weight
- Surface task examples that AI may augment, reduce, or leave human-led
- Support a broader career decision together with pay, outlook, education, location, and user fit

Do not use the model to:

- Guarantee that a career cannot be replaced
- Predict individual job security
- Make hiring, admissions, licensing, or employment decisions
- Infer a person’s ability, protected traits, or future income
- Replace professional career advising or direct employer research

## Official input fields

The model uses:

- Occupation title and description
- O*NET task statements
- O*NET essential skills
- O*NET knowledge areas
- O*NET job zone
- BLS typical entry education for the credential dimension

The current bundle uses O*NET release 30.3 and 830 detailed occupations.

## Dimensions and weights

| Dimension | Weight | What it represents |
| --- | ---: | --- |
| Human trust | 18% | Counseling, teaching, persuasion, leadership, negotiation, and relationship work |
| Physical-world complexity | 18% | Installation, repair, inspection, equipment, field, and unpredictable physical work |
| High-stakes judgment | 20% | Safety, diagnosis, legal, ethical, approval, investigation, and technical accountability |
| Creativity and adaptation | 16% | Original design, strategy, research, innovation, and unfamiliar problem-solving |
| Credential and regulatory barrier | 12% | Licensing, professional authority, regulated practice, education, and job-zone signals |
| Inverse routine-automation exposure | 16% | Lower relative presence of repetitive information-processing, scheduling, data-entry, and standardized-document tasks |

AI augmentation potential is shown separately and does not increase the overall resilience score.

## Exact formula

```text
Overall resilience =
  0.18 × human trust percentile
+ 0.18 × physical-world complexity percentile
+ 0.20 × high-stakes judgment percentile
+ 0.16 × creativity and adaptation percentile
+ 0.12 × credential and regulatory barrier percentile
+ 0.16 × (100 − routine automation exposure percentile)
```

## How a dimension score is calculated

1. CareerProof searches the official occupation description, O*NET tasks, skills, and knowledge text for the published model lexicon.
2. Repeated hits are compressed with a logarithmic transformation so one profile cannot dominate through repeated wording alone.
3. The credential dimension also uses published entry-education and job-zone signals.
4. Each raw dimension is converted to a percentile across all 830 occupations.
5. The interface displays the matched signals and task evidence behind the score.

A percentile is a relative position within the bundled dataset. A score of 75 does **not** mean a 75% probability of job survival.

## Task-impact explanation

Published O*NET task statements are routed into three explanatory categories using visible keyword rules:

- Tasks AI may reduce
- Tasks AI may augment
- Tasks likely to remain human-led

These categories are examples of possible task-level change. They are not forecasts of job loss, productivity, or replacement.

## Transparency controls

Every displayed resilience profile includes:

- Model version
- Overall score and qualitative label
- Six dimension scores
- Exact weights
- Matched lexical signals
- Official task examples
- AI augmentation potential
- Limitations and boundary statement

The full lexicons are also returned by `/api/resilience-model` and displayed in the Evidence Center.

## Sensitivity testing

CareerProof recalculates recommendations under six presets:

- Balance everything
- Maximize income
- Maximize AI resilience
- Maximize opportunity
- Minimize education burden
- Prioritize location

The interface reports when a different career becomes the top result. This exposes how dependent the recommendation is on the user’s priorities.

## Validation performed

- Reproducible scores across repeated runs
- Dimension values constrained to 0–100
- Six dimensions and weights sum to 100%
- Evidence shown for displayed occupations
- Hard constraints tested independently from resilience
- Model endpoint, Path Builder, Compare Lab, occupation profile, and browser presentation tested
- Normal and failure cases covered in unit, integration, workflow, and Chromium acceptance tests

## Known limitations

- Keyword presence cannot capture every nuance of a task.
- A national occupation profile cannot represent every employer, specialty, or work setting.
- Work content changes over time and may lag emerging technology.
- Credential signals do not prove that a license is legally required in every state.
- Higher education may reflect entry burden rather than true resilience.
- Physical and interpersonal work can also be automated or reorganized.
- The model does not include proprietary automation forecasts.
- The model does not establish causation.

## Human-control statement

The Career Resilience Profile is one adjustable component in a larger decision. The user chooses its weight, reviews the interpretation, sees hard-constraint conflicts, challenges the recommendation, and makes the final decision.
