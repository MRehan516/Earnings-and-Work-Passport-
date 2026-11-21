---
name: passport-status-transitions
description: Enforce who may change party, relationship and payment statuses; use when writing status-change code, UI logic or tests.
---
# Rules
1. The worker can never set contact_verified, counterparty_acknowledged, payer_confirmed or any evidence label.
2. Only the counterparty (via a one-time link) can acknowledge a relationship or confirm work, amount or payment, and only for the question shown.
3. Only rules can set bank_matched or upgrade an evidence label.
4. Ended or disputed changes by the worker need a reason and a step-up check.
5. Status history is append-only; never overwrite.
6. An OTP proves control of a channel only; never treat it as identity or truth.
