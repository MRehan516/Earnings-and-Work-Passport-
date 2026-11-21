---
name: passport-matching
description: Apply payment-matching, duplicate and classification rules when writing or changing reconciliation code or tests for the Earnings and Work Passport.
---
# Rules
1. Candidate bank credit: abs(amount - expected) <= 1 rupee.
2. Platform payout window: +/-3 days of payout date. Client payment: +/-7 days of stated payment date, or 0 to 30 days after the invoice if none stated.
3. One bank credit matches one income record only.
4. Same file hash or same event key = one evidence item, counted once.
5. Unmatched credits are unclassified and never count as work income.
6. Conflicts mark the record disputed and cannot be overridden.
7. Every rule needs a test.
