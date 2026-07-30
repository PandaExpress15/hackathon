# Limitations

- The bundled data is synthetic and does not represent the current labor market.
- The local question router supports a focused, auditable set of analysis intents rather than unrestricted conversation.
- Salary calculations exclude rows that do not contain both salary endpoints.
- Company salary ranking requires at least five complete salary records per company.
- The app describes associations in the supplied data and does not claim causation.
- Trend analysis is descriptive and does not forecast future job volume.
- Career Signal Match shows skill overlap and is not a hiring score or recommendation engine.
- The system cannot answer questions about employee satisfaction, company culture, job quality, acceptance rates, future outcomes, or protected attributes because those fields are absent or inappropriate.
- The local demonstration stores audit events on disk. A production deployment would require authentication, encrypted storage, access controls, retention limits, monitoring, and a formal privacy policy.
- Column mapping is designed for common job-posting schemas, not every possible vendor export.
