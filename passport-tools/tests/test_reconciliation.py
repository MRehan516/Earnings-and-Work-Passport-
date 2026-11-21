import json
import csv
import pytest
from pathlib import Path
from reconciliation import ReconciliationEngine, StatusTransitions, PermissionError

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

@pytest.fixture
def sample_data():
    with open(DATA_DIR / "expected.json", "r", encoding="utf-8") as f:
        expected = json.load(f)
    
    bank_credits = []
    with open(DATA_DIR / "bank_statement.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bank_credits.append(row)
            
    return expected, bank_credits

def test_full_reconciliation_flow(sample_data):
    expected, bank_credits = sample_data
    
    # Setup income records
    income_records = [
        # RideCo Statement w46
        {
            "id": "inc_rc_46",
            "payer": expected["rideco_w46.pdf"]["payer"],
            "platform": expected["rideco_w46.pdf"]["platform"],
            "reference": expected["rideco_w46.pdf"]["reference"],
            "source_type": "platform",
            "period_start": expected["rideco_w46.pdf"]["period_start"],
            "period_end": expected["rideco_w46.pdf"]["period_end"],
            "gross": expected["rideco_w46.pdf"]["gross_amount"],
            "deductions": expected["rideco_w46.pdf"]["deductions"],
            "net": expected["rideco_w46.pdf"]["net_amount"],
            "payout_date": expected["rideco_w46.pdf"]["record_date"],
            "worker_confirmed": True,
            "acquisition_method": "upload"
        },
        # Photo duplicate of RideCo w46
        {
            "id": "inc_rc_46_photo",
            "payer": expected["rideco_w46_photo.png"]["payer"],
            "platform": expected["rideco_w46_photo.png"]["platform"],
            "reference": expected["rideco_w46_photo.png"]["reference"],
            "source_type": "platform",
            "period_start": expected["rideco_w46_photo.png"]["period_start"],
            "period_end": expected["rideco_w46_photo.png"]["period_end"],
            "gross": expected["rideco_w46_photo.png"]["gross_amount"],
            "deductions": expected["rideco_w46_photo.png"]["deductions"],
            "net": expected["rideco_w46_photo.png"]["net_amount"],
            "payout_date": expected["rideco_w46_photo.png"]["record_date"],
            "worker_confirmed": True,
            "acquisition_method": "upload"
        },
        # Ravi INV-102
        {
            "id": "inc_ravi_102",
            "payer": expected["invoice_ravi_102.pdf"]["payer"],
            "client_name": expected["invoice_ravi_102.pdf"]["client_name"],
            "reference": expected["invoice_ravi_102.pdf"]["reference"],
            "source_type": "client",
            "invoice_amount": expected["invoice_ravi_102.pdf"]["invoice_amount"],
            "record_date": expected["invoice_ravi_102.pdf"]["record_date"],
            "worker_confirmed": True,
            "acquisition_method": "upload"
        },
        # Kumar INV-103 (with dispute: client confirmed 4500 vs invoice 5000)
        {
            "id": "inc_kumar_103",
            "payer": expected["invoice_kumar_103.pdf"]["payer"],
            "client_name": expected["invoice_kumar_103.pdf"]["client_name"],
            "reference": expected["invoice_kumar_103.pdf"]["reference"],
            "source_type": "client",
            "invoice_amount": 5000.0,
            "client_confirmed_amount": 4500.0,  # Dispute!
            "record_date": expected["invoice_kumar_103.pdf"]["record_date"],
            "worker_confirmed": True,
            "acquisition_method": "upload"
        },
        # Simulated RideCo 2-8 Nov
        {
            "id": "inc_rc_45_sim",
            "payer": expected["rideco_w45_api.json"]["payer"],
            "platform": expected["rideco_w45_api.json"]["platform"],
            "reference": expected["rideco_w45_api.json"]["reference"],
            "source_type": "platform",
            "period_start": expected["rideco_w45_api.json"]["period_start"],
            "period_end": expected["rideco_w45_api.json"]["period_end"],
            "gross": expected["rideco_w45_api.json"]["gross_amount"],
            "deductions": expected["rideco_w45_api.json"]["deductions"],
            "net": expected["rideco_w45_api.json"]["net_amount"],
            "payout_date": expected["rideco_w45_api.json"]["record_date"],
            "acquisition_method": "simulated_api"
        }
    ]

    result = ReconciliationEngine.match_credits(income_records, bank_credits)

    # 1. Deduplication check: photo duplicate is detected and grouped, not added twice
    assert len(result["duplicates"]) == 1
    assert result["duplicates"][0]["id"] == "inc_rc_46_photo"
    assert len(result["deduped_incomes"]) == 4

    # 2. RideCo w46 matches 11,000 credit
    rc_match = next((m for m in result["matches"] if m["income"]["id"] == "inc_rc_46"), None)
    assert rc_match is not None
    assert float(rc_match["credit"]["credit"]) == 11000.0
    assert rc_match["income"]["evidence_label"] == "source_matched"
    assert rc_match["income"]["payment_status"] == "bank_matched"

    # 3. Ravi 12,000 matches NEFT RAVI credit
    ravi_match = next((m for m in result["matches"] if m["income"]["id"] == "inc_ravi_102"), None)
    assert ravi_match is not None
    assert float(ravi_match["credit"]["credit"]) == 12000.0
    assert ravi_match["income"]["evidence_label"] == "source_matched"

    # 4. Kumar becomes disputed due to amount discrepancy (5000 vs 4500)
    kumar_inc = next((inc for inc in result["deduped_incomes"] if inc["id"] == "inc_kumar_103"), None)
    assert kumar_inc is not None
    assert kumar_inc["evidence_label"] == "disputed"
    assert kumar_inc["payment_status"] == "disputed"

    # 5. Simulated RideCo 8800 is source_verified_simulated and has NO bank credit
    sim_inc = next((inc for inc in result["deduped_incomes"] if inc["id"] == "inc_rc_45_sim"), None)
    assert sim_inc is not None
    assert sim_inc["evidence_label"] == "source_verified_simulated"
    assert not any(m["income"]["id"] == "inc_rc_45_sim" for m in result["matches"])

    # 6. Meena Rao 3000 is unclassified and flagged as possible personal transfer
    meena = next((c for c in result["unclassified_credits"] if "MEENA RAO" in c.get("descriptor", "")), None)
    assert meena is not None
    assert meena["classification"] == "unclassified"
    assert meena.get("flag") == "possible personal transfer"

def test_boundary_conditions():
    inc = {
        "id": "inc_boundary",
        "payer": "Test Platform",
        "platform": "Test Platform",
        "source_type": "platform",
        "net": 1000.0,
        "payout_date": "2026-11-10",
        "acquisition_method": "upload",
        "worker_confirmed": True
    }

    # Amount off by 1 rupee passes
    res_1 = ReconciliationEngine.match_credits([inc], [{"date": "2026-11-10", "descriptor": "Test Platform", "credit": "1001.0"}])
    assert len(res_1["matches"]) == 1

    # Amount off by 2 rupees fails
    res_2 = ReconciliationEngine.match_credits([inc], [{"date": "2026-11-10", "descriptor": "Test Platform", "credit": "1002.0"}])
    assert len(res_2["matches"]) == 0

    # 3 days difference passes
    res_3 = ReconciliationEngine.match_credits([inc], [{"date": "2026-11-13", "descriptor": "Test Platform", "credit": "1000.0"}])
    assert len(res_3["matches"]) == 1

    # 4 days difference fails for platform payout
    res_4 = ReconciliationEngine.match_credits([inc], [{"date": "2026-11-14", "descriptor": "Test Platform", "credit": "1000.0"}])
    assert len(res_4["matches"]) == 0

def test_status_transitions_and_permissions():
    # Worker cannot set payer_confirmed
    with pytest.raises(PermissionError):
        StatusTransitions.worker_change_payment_status("declared", "payer_confirmed")

    # Worker cannot set contact_verified
    with pytest.raises(PermissionError):
        StatusTransitions.worker_change_party_contact_status("added_by_worker", "contact_verified")

    # Worker cannot set counterparty_acknowledged
    with pytest.raises(PermissionError):
        StatusTransitions.worker_change_relationship_status("worker_declared", "counterparty_acknowledged")

    # Archiving party requires step-up and reason
    with pytest.raises(PermissionError):
        StatusTransitions.worker_change_party_contact_status("added_by_worker", "archived", reason="", step_up_verified=False)
    
    # With reason and step_up, archiving succeeds
    res = StatusTransitions.worker_change_party_contact_status("added_by_worker", "archived", reason="No longer active", step_up_verified=True)
    assert res == "archived"

    # Counterparty confirms payment via link
    cp_resp = StatusTransitions.counterparty_confirm("payment_made", "yes")
    assert cp_resp["payment_status"] == "payer_confirmed"

    # Counterparty reports corrected amount
    cp_dispute = StatusTransitions.counterparty_confirm("payment_made", "corrected_amount", corrected_amount=4500.0)
    assert cp_dispute["payment_status"] == "disputed"
    assert cp_dispute["corrected_amount"] == 4500.0
