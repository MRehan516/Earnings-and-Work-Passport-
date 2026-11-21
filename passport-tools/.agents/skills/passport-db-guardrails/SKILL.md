---
name: passport-db-guardrails
description: Guardrails for Firestore and database collections in Earnings and Work Passport.
---
# Database Guardrails
1. Every write to status or amounts must produce an append-only audit_log entry: {actor, old_value, new_value, reason, time, method}.
2. Worker permissions cannot modify verification or confirmed statuses directly.
3. Confirmation request tokens must have >= 32 characters of cryptographic entropy.
4. Demo OTPs expire in 5 minutes with maximum 3 attempts before a 5-minute lockout. Demo OTPs are never logged.
5. Share links are time-limited snapshots and can be immediately revoked. Revoked tokens deny all reads.
