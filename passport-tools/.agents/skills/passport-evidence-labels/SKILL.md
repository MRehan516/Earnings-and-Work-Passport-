---
name: passport-evidence-labels
description: Strict five-label evidence hierarchy rules for Earnings and Work Passport.
---
# Rules
1. Five strict labels:
   - self_declared: Manual entry without document or bank match.
   - document_extracted: AI-read and worker-confirmed.
   - source_matched: Reconciled with bank/UPI credit by deterministic rules.
   - source_verified_simulated: Imported from simulated platform API (always explicitly displayed with the word Simulated).
   - disputed: Conflict or dispute flag (always wins over other statuses).
2. Client confirmation adds relationship or payment status, but does not upgrade an evidence label by itself.
3. No label is ever upgraded by AI confidence. Upgrades happen only via deterministic code rules.
