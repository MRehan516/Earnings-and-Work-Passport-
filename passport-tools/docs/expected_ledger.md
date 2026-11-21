# Expected Results for Demo Data v2

| Item | Expected Label | Expected Statuses | Counted In Total As |
|---|---|---|---|
| **RideCo w46** (Gross ₹12,000; Net ₹11,000) | `source_matched` | `platform_payout` + `bank_matched` | Received ₹11,000, counted once |
| **RideCo photo duplicate** (RC-46-001) | *Grouped duplicate* | `duplicate` | Not added again (₹0) |
| **Ravi INV-102** (₹12,000) | `source_matched` | `counterparty_acknowledged` + `payer_confirmed` + `bank_matched` | Received ₹12,000 |
| **Kumar INV-103** (₹5,000 claimed vs ₹4,500 client) | `disputed` | `counterparty_acknowledged` (work) + `amount_disputed` + no bank match | Claimed/disputed ₹5,000 vs ₹4,500 |
| **Cash tips** (₹800) | `self_declared` | `declared` | Self-declared ₹800 |
| **UPI MEENA RAO** (₹3,000) | `not an income` | `unclassified` (flagged *possible personal transfer*) | Not counted as income (₹0) |
| **Simulated RideCo 2–8 Nov** (Net ₹8,800) | `source_verified_simulated` | `platform report`, no bank match | Reported ₹8,800 (always displayed with the word *Simulated*) |

---

## Benchmark Summary Headline
> **Received and bank-matched:** ₹23,000  
> **Claimed but unpaid / disputed:** ₹5,000 (client confirmed ₹4,500)  
> **Self-declared:** ₹800  
> **Not counted (unclassified transfer):** ₹3,000  
> **Simulated reported (unmatched payout):** ₹8,800  
