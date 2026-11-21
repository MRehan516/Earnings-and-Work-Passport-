---
name: passport-platform-formats
description: Standardized data structures and mappings for platform earnings and integrations.
---
# Rules
1. Common integration format:
   {source_type, source_party, external_id, period_start, period_end, gross, deductions, net, currency, payout_date, acquisition_method, retrieved_at, raw_ref}
2. Deduplication key:
   normalize(payer) + period + net + reference.
3. Same file hash or same event key -> duplicate (grouped as single evidence item, counted once).
4. Validation rule:
   Amounts must be positive; abs(gross - deductions - net) <= 1, else flag mismatch.
