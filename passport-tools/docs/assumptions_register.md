# Assumptions Register

Each assumption is tracked with its risk categorization and validation pathway:

| ID | Assumption | Risk Category | Validation Pathway / Status |
|---|---|---|---|
| **ASM-01** | Multi-platform gig workers have difficulty combining income proof for rent, loans, and credit cards | `User Research Required` | Validated through mini-interviews with delivery riders & cab drivers. |
| **ASM-02** | Freelancer clients will click a lightweight SMS/WhatsApp link to confirm that an invoice was paid | `User Research Required` | Low-friction 1-click confirmation model tested without client login requirement. |
| **ASM-03** | Indian gig platforms (Swiggy, Zomato, Uber) will open public earnings APIs to non-banking third parties | `Partner Dependent` | Assumed **unlikely** in near-term; system architecture is designed around document ingestion + Account Aggregator fallback. |
| **ASM-04** | Bank statements uploaded via CSV/PDF can be reconciled deterministically with platform payouts | `Decision Required` | Confirmed via pure Python matching rules: `abs(amount - expected) <= 1` within 3-day / 7-day windows. |
| **ASM-05** | An AI model (Gemini 3.8 Flash) can extract complex statement formats with zero hallucination | `Official Verification Required` | Tested via `eval_extraction.py`: 100% extraction accuracy achieved when constrained to pure JSON and post-checks. |
| **ASM-06** | Financial institutions and landlords will accept a cryptographic, verifiable read-only link over PDFs | `User Research Required` | Lenders require explainable evidence labels and audit provenance over opaque scores. |
| **ASM-07** | Regulatory approval as an Account Aggregator FIU can be obtained via a registered TSP partner | `Partner Dependent` | Requires partnership with a licensed NBFC/AA entity under RBI guidelines. |
| **ASM-08** | Consent and data deletion can be fully enforced client-side and server-side under DPDP Act 2026 | `Decision Required` | Immediate token revocation and complete data-purge endpoints built into core architecture. |
