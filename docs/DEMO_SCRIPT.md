# Official-Data Demo Script

Target length: 6 to 8 minutes.

## Opening

CareerProof AI is a trustworthy career-data assistant. The original concept proved calculations against a synthetic dataset. This version replaces those records with official BLS, Census, and O*NET data.

The promise remains simple: AI interprets the question. Code calculates the answer. The user can inspect the source and proof.

## Source overview

Show the Data Catalog. Point out May 2025 BLS wage data, 2024–2034 BLS projections, O*NET 30.3, 2024 ACS degree earnings, and the BLS education aggregation. Mention that every raw file and processed table has a checksum.

## Success case 1

Ask:

```text
Which states pay nuclear engineers the most?
```

Show the result, state ranking, source vintage, rows considered, calculation, limitations, and Evidence ID. Explain that states without a published estimate are excluded rather than guessed.

## Success case 2

Ask:

```text
What skills do public relations specialists need?
```

Show that the route changes to O*NET 30.3. Explain that O*NET importance ratings are published occupational descriptors, not an AI hiring score.

## Broad coverage

Open Occupation Explorer and search:

- public relations
- journalist
- nuclear engineer
- political scientist
- lawyer

Show that the same interface covers mass communications, policy, law, science, and engineering.

## Degree data

Ask:

```text
Compare communications and engineering degree earnings.
```

Show the Census estimates and 90 percent margins of error. State that the result is an association across all occupations.

## Safe refusal

Ask:

```text
What bachelor's degree should I pursue for the highest pay after becoming a lawyer?
```

CareerProof refuses to combine separate datasets into an unsupported causal claim. It suggests three supported questions instead.

## Close

CareerProof is not asking the user to trust a chatbot. It gives the user official data, a reproducible calculation, and the limits needed to interpret the result responsibly.
