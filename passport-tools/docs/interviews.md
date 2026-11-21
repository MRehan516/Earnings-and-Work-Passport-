# Mini-Interviews Register: Ground Truth Research

*Conducted for Earnings & Work Passport (Buildathon Research Task R2)*  
*Methodology: 5-minute structured interviews across 3 user personas: Workers (3), Clients (2), Lenders/Landlords (2).*  
*Privacy Guardrail: No real financial documents or PII collected; synthetic pseudonyms used.*

---

## 🛵 Persona 1: Platform & Gig Workers (3 Interviews)

### Interview W1: Rajesh K. (Ride-Hailing Driver — Uber & Rapido, Bengaluru)
* **What proof he sent & what was rejected:**
  * When applying for a two-wheeler refinancing loan, he sent screenshots of his Uber driver weekly earnings and a 3-month bank statement PDF.
  * The loan officer rejected the screenshots because the bank credits were from a third-party payment gateway (Razorpay/PayU) and didn't clearly say "Uber", and the amount was ₹1,200 less than the gross app screenshot due to platform commissions.
* **Apps & Banks used:**
  * Uses 2 ride apps (Uber, Rapido), a local credit cooperative bank, and Paytm Payments Bank for daily fuel UPI payments.
* **Reaction to Earnings & Work Passport:**
  * Would gladly upload statements if it eliminates arguments with loan agents.
  * **Primary concern:** *"I don't want the bank to see my personal family UPI transfers or how much I spend on personal things—only what I earned."* (Validates our personal transfer filtering and scoped consent sharing).

---

### Interview W2: Deepa S. (Food & Quick-Commerce Delivery Partner — Swiggy & Zepto, Hyderabad)
* **What proof she sent & what was rejected:**
  * Needed to rent a 1-BHK apartment; the landlord asked for salary slips. She showed her Swiggy partner app balance.
  * The landlord refused, demanding "official company stamp or payslip" and delayed the lease by 2 weeks until a relative co-signed.
* **Apps & Banks used:**
  * Swiggy, Zepto, State Bank of India (SBI).
* **Reaction to Earnings & Work Passport:**
  * Loved the idea of an "Income Passport" that aggregates both Swiggy and Zepto into a single monthly total.
  * Emphasized that weekly payouts make monthly income look erratic, so a clean monthly view with evidence labels gives her credibility.

---

### Interview W3: Amit V. (Freelance Graphic Designer & Video Editor, Pune)
* **What proof he sent & what was rejected:**
  * Applied for an unsecured credit card; bank requested 2 years of ITR and Form 16. As a freelance designer earning ₹35,000–₹50,000 across 4 direct clients, he filed ITR-4 (presumptive income), but the credit card was denied due to lack of standard employer verification.
* **Apps & Banks used:**
  * Direct NEFT/IMPS invoices, Razorpay payment links, HDFC Bank.
* **Reaction to Earnings & Work Passport:**
  * Enthusiastic about the **Client Confirmation Link**: *"Right now, a bank won't call 4 different clients to check if I designed their logos. If my clients can click a 1-minute link on WhatsApp to confirm the invoice, that solves my biggest headache."*

---

## 🏢 Persona 2: Freelancer Clients (2 Interviews)

### Interview C1: Sunita M. (Founder, Digital Marketing Agency, Mumbai)
* **Reaction to worker confirmation requests:**
  * Regularly hires freelance copywriters and thumbnail artists on 30-day invoice cycles.
  * Stated she would **100% click a lightweight link** asking: *"Did Amit deliver the social media campaign? Was ₹12,000 paid?"*.
* **Friction thresholds:**
  * Would **refuse** if the app required her to create an account, download an app, or enter corporate tax IDs.
  * A 1-click web interface with an on-screen OTP for mobile confirmation is the exact right friction level.
* **Security & fraud perception:**
  * Appreciated that the link only asks about *her specific invoice* and does not expose the worker's other clients or total income.

---

### Interview C2: Vikram R. (Retail Store Owner, Jaipur)
* **Reaction to worker confirmation requests:**
  * Hires a weekend inventory assistant and pays via UPI.
  * Confirmed he would respond if sent via SMS or WhatsApp, provided it takes less than 30 seconds.
* **Dispute behavior:**
  * Noted that sometimes payments are adjusted for incomplete days (e.g., agreed ₹5,000, but paid ₹4,500 due to 1 day absence).
  * Validated our **"Corrected Amount"** option: if an invoice says ₹5,000 but he paid ₹4,500, he can submit ₹4,500 rather than rejecting the whole record, triggering the app's `DISPUTED` transparent flag.

---

## 🏦 Persona 3: Lenders & Landlords (2 Interviews)

### Interview L1: Ramesh P. (Independent Landlord — 6 Rental Units, Bengaluru)
* **What proof he currently asks for:**
  * Asks for 6 months bank statements, but finds them tedious to read (hundreds of coffee, grocery, and fuel debits).
  * Distrusts loose PDF statements or WhatsApp screenshots because *"anyone can edit a PDF in 2 minutes on their phone."*
* **Reaction to the Passport Report:**
  * Would trust a report if it shows **`SOURCE_MATCHED`** badges confirming the statement was matched to an actual bank credit.
  * Likes that the report highlights discrepancies upfront (e.g. disputed items) rather than hiding them.
* **Feedback on sharing:**
  * Read-only link with an expiration date is much cleaner than receiving 15 screenshots on WhatsApp.

---

### Interview L2: Arvind N. (Branch Credit Officer, Small Finance Bank / Micro-Lender)
* **Current underwriting bottleneck:**
  * Underwriters spend 45–60 minutes per gig worker manually matching weekly app payouts with bank ledger credits.
  * Rejections happen not because gig workers don't earn, but because the cost of manually auditing fragmented weekly income is too high for a small ₹30,000 two-wheeler loan.
* **Reaction to the Passport:**
  * The **5-Tier Evidence Hierarchy** is exactly what credit committees require:
    * *"We will never accept an AI-generated score, but we will accept deterministic matching rules where gross minus deductions equals net, and the bank transaction reference matches."*
  * Commended the **Append-Only Audit Log** and the clear separation between work income and personal transfers (e.g., family remittances).
