# Production Platform Integration Pattern

This document specifies the architectural transition from the educational simulated mock API (`mock_api/app.py` & `adapters/rideco_adapter.py`) to an authorized, production-grade direct platform integration.

## 1. Architectural Boundary

In the prototype:
* Mock Partner API provides simulated OAuth 2.0 client credentials, token expiry, paginated earnings queries, and HMAC-signed webhook dispatches.
* The local adapter translates raw payloads into the **Common Integration Format**:
  ```json
  {
    "source_type": "platform",
    "source_party": "RideCo Technologies",
    "external_id": "RC-45-001",
    "period_start": "2026-11-02",
    "period_end": "2026-11-08",
    "gross": 9500.0,
    "deductions": 700.0,
    "net": 8800.0,
    "currency": "INR",
    "payout_date": "2026-11-10",
    "acquisition_method": "simulated_api",
    "retrieved_at": "2026-11-21T09:50:00Z",
    "raw_ref": "rideco://earnings/RC-45-001"
  }
  ```

## 2. Replacing Mock with Authorized Real Integration

When commercial partner agreements and sandbox credentials are provided by a gig platform:

1. **Authentication Transition**:
   * Switch from simulated client credentials to standard Three-Legged OAuth 2.0 or mTLS as dictated by the enterprise platform partner specifications.
   * Store credentials securely in a cloud KMS / Secrets Vault; never embed keys in mobile clients or commit to code repositories.
2. **Adapter Swapping**:
   * The core domain models and database ingestion routines interact **only** with the `Common Integration Format`.
   * Implement a concrete partner adapter implementing the identical `fetch_all_earnings` and `process_webhook` contracts.
   * `acquisition_method` changes from `"simulated_api"` to `"partner_api"`.
3. **Data Minimization & Provenance**:
   * Store the partner transaction hash or cryptographic receipt reference in `raw_ref` for non-repudiation.
   * Under the Indian DPDP Act rules, purge granular telemetry (e.g., GPS coordinates, rider/customer identifiers, individual delivery trip routes) immediately, retaining solely the financial reconciliation facts: worker ID, period, gross, deductions, net, and payment timestamp.
4. **Idempotency & Resiliency**:
   * Rely on external transaction IDs with database unique constraints to prevent double-counting.
   * Enforce exponential backoff on HTTP 429 and automatic token renewals on HTTP 401.
