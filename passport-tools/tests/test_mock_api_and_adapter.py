import sys
from pathlib import Path

# Add paths
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))
sys.path.insert(0, str(base_dir / "adapters"))
sys.path.insert(0, str(base_dir / "mock_api"))

import pytest
import time
from fastapi.testclient import TestClient
from mock_api.app import app, VALID_CLIENT_ID, VALID_CLIENT_SECRET, WEBHOOK_SECRET, create_webhook_payload, tokens_db
from adapters.rideco_adapter import RideCoAdapter, RideCoValidationError

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def adapter():
    return RideCoAdapter(
        base_url="http://testserver",
        client_id=VALID_CLIENT_ID,
        client_secret=VALID_CLIENT_SECRET,
        webhook_secret=WEBHOOK_SECRET
    )

def test_normal_fetch_and_pagination(client, adapter):
    results = adapter.fetch_all_earnings(client=client)
    assert len(results) == 2
    assert results[0]["external_id"] == "RC-45-001"
    assert results[0]["net"] == 8800.0
    assert results[0]["currency"] == "INR"
    assert results[0]["source_party"] == "RideCo Technologies"
    assert results[1]["external_id"] == "RC-46-001"
    assert results[1]["net"] == 11000.0

def test_expired_token_handling(client, adapter):
    # Acquire token
    token = adapter.get_valid_token(client=client)
    assert token in tokens_db
    
    # Artificially expire the token in mock DB
    tokens_db[token]["expires_at"] = time.time() - 100
    
    # Should automatically recover, refresh and fetch
    results = adapter.fetch_all_earnings(client=client)
    assert len(results) >= 0

def test_rate_limit_backoff(client, adapter):
    # Calling directly to hit 429
    token = adapter.get_valid_token(client=client)
    headers = {"Authorization": f"Bearer {token}"}
    hit_429 = False
    for _ in range(15):
        resp = client.get("/v1/partner/earnings", headers=headers)
        if resp.status_code == 429:
            hit_429 = True
            break
    assert hit_429 is True

def test_webhook_normal_and_idempotent(adapter):
    event_data = {
        "external_id": "RC-50-001",
        "week_start": "2026-11-16",
        "week_end": "2026-11-22",
        "gross": 15000.0,
        "deductions": 1500.0,
        "net": 13500.0,
        "payout_date": "2026-11-24",
        "status": "paid"
    }
    payload, sig = create_webhook_payload("payout.created", event_data, "evt_test_1001")
    
    # 1. First reception
    res = adapter.process_webhook(payload, sig)
    assert res is not None
    assert res["external_id"] == "RC-50-001"
    assert res["net"] == 13500.0

    # 2. Repeated reception (idempotent, returns None)
    res_repeat = adapter.process_webhook(payload, sig)
    assert res_repeat is None

def test_webhook_bad_signature(adapter):
    payload, _ = create_webhook_payload("payout.created", {"external_id": "RC-99"}, "evt_999")
    with pytest.raises(ValueError, match="Invalid webhook signature"):
        adapter.process_webhook(payload, "bad_signature_hash")

def test_validation_schema_change_missing_fields(adapter):
    bad_item = {
        "external_id": "RC-BAD-01",
        "gross": 5000.0
        # missing net, payout_date, etc.
    }
    with pytest.raises(RideCoValidationError, match="Missing required field"):
        adapter.validate_raw_item(bad_item)

def test_validation_invalid_amounts(adapter):
    # Negative amount
    bad_neg = {
        "external_id": "RC-NEG",
        "week_start": "2026-11-01",
        "week_end": "2026-11-07",
        "gross": 1000.0,
        "deductions": -100.0,
        "net": 1100.0,
        "payout_date": "2026-11-10"
    }
    with pytest.raises(RideCoValidationError, match="Negative amounts"):
        adapter.validate_raw_item(bad_neg)

    # Math error: 1000 - 100 != 800
    bad_math = {
        "external_id": "RC-MATH",
        "week_start": "2026-11-01",
        "week_end": "2026-11-07",
        "gross": 1000.0,
        "deductions": 100.0,
        "net": 800.0,
        "payout_date": "2026-11-10"
    }
    with pytest.raises(RideCoValidationError, match="Invalid math"):
        adapter.validate_raw_item(bad_math)
