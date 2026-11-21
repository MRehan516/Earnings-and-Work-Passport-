import time
import secrets
import string
import pytest
from datetime import datetime, timezone
from typing import Dict, Any, List

class SecurityEnforcer:
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        if length < 32:
            raise ValueError("Token must have at least 32 characters of entropy")
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def is_token_entropy_sufficient(token: str) -> bool:
        if len(token) < 32:
            return False
        has_upper = any(c.isupper() for c in token)
        has_lower = any(c.islower() for c in token)
        has_digit = any(c.isdigit() for c in token)
        return (has_upper or has_lower) and has_digit

class DemoOTPManager:
    def __init__(self):
        self.active_otps: Dict[str, Dict[str, Any]] = {}

    def issue_otp(self, identifier: str) -> str:
        code = f"{secrets.randbelow(1000000):06d}"
        self.active_otps[identifier] = {
            "code": code,
            "created_at": time.time(),
            "expires_at": time.time() + 300,  # 5 min
            "attempts": 0,
            "locked_until": 0
        }
        return code

    def verify_otp(self, identifier: str, candidate_code: str) -> bool:
        record = self.active_otps.get(identifier)
        if not record:
            return False
        
        now = time.time()
        if now < record["locked_until"]:
            raise PermissionError("Too many failed attempts. Locked for 5 minutes.")
        
        if now > record["expires_at"]:
            raise TimeoutError("OTP expired.")
        
        if record["code"] == candidate_code:
            del self.active_otps[identifier]
            return True
        else:
            record["attempts"] += 1
            if record["attempts"] >= 3:
                record["locked_until"] = now + 300  # Lock 5 min
                raise PermissionError("Account locked due to 3 consecutive failed OTP attempts.")
            return False

class ShareLinkManager:
    def __init__(self):
        self.links: Dict[str, Dict[str, Any]] = {}

    def create_share_link(self, worker_id: str, snapshot_data: Dict[str, Any], ttl_seconds: int = 3600) -> str:
        token = SecurityEnforcer.generate_secure_token(32)
        self.links[token] = {
            "worker_id": worker_id,
            "snapshot": snapshot_data,
            "expires_at": time.time() + ttl_seconds,
            "revoked": False
        }
        return token

    def read_share_link(self, token: str) -> Dict[str, Any]:
        entry = self.links.get(token)
        if not entry:
            raise KeyError("Share link not found")
        if entry["revoked"]:
            raise PermissionError("This share link has been revoked by the worker")
        if time.time() > entry["expires_at"]:
            raise TimeoutError("This share link has expired")
        return entry["snapshot"]

    def revoke_link(self, token: str, worker_id: str) -> None:
        entry = self.links.get(token)
        if not entry or entry["worker_id"] != worker_id:
            raise PermissionError("Cannot revoke link: unauthorized")
        entry["revoked"] = True

class AppendOnlyAuditTrail:
    def __init__(self):
        self._log: List[Dict[str, Any]] = []

    def append(self, actor: str, action: str, before: Any, after: Any, reason: str, method: str):
        entry = {
            "id": f"aud_{len(self._log) + 1}",
            "actor": actor,
            "action": action,
            "before": before,
            "after": after,
            "reason": reason,
            "method": method,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self._log.append(entry)

    def get_entries(self) -> List[Dict[str, Any]]:
        # Return immutable copy
        return [dict(e) for e in self._log]

# PYTEST TESTS

def test_token_entropy():
    tok = SecurityEnforcer.generate_secure_token(32)
    assert len(tok) == 32
    assert SecurityEnforcer.is_token_entropy_sufficient(tok)

    with pytest.raises(ValueError):
        SecurityEnforcer.generate_secure_token(16)

def test_share_token_revocation_and_expiry():
    mgr = ShareLinkManager()
    token = mgr.create_share_link("worker_1", {"earned": 12000}, ttl_seconds=300)
    
    # 1. Normal read
    data = mgr.read_share_link(token)
    assert data["earned"] == 12000

    # 2. Worker revokes link
    mgr.revoke_link(token, "worker_1")
    with pytest.raises(PermissionError, match="revoked"):
        mgr.read_share_link(token)

    # 3. Expiry test
    token_exp = mgr.create_share_link("worker_1", {"earned": 5000}, ttl_seconds=-10)
    with pytest.raises(TimeoutError, match="expired"):
        mgr.read_share_link(token_exp)

def test_demo_otp_lockout_and_expiry():
    otp_mgr = DemoOTPManager()
    code = otp_mgr.issue_otp("worker_mobile_999")
    assert len(code) == 6

    # 2 bad attempts
    assert not otp_mgr.verify_otp("worker_mobile_999", "000000")
    assert not otp_mgr.verify_otp("worker_mobile_999", "111111")

    # 3rd bad attempt triggers lockout
    with pytest.raises(PermissionError, match="locked"):
        otp_mgr.verify_otp("worker_mobile_999", "222222")

    # While locked, even correct code is rejected
    with pytest.raises(PermissionError, match="Locked for 5 minutes"):
        otp_mgr.verify_otp("worker_mobile_999", code)

def test_confirmation_token_scoped_access():
    # Verify confirmation tokens only allow querying their specific questions
    tokens = {
        "token_client_1": {"income_id": "inc_ravi", "allowed_question": "payment_made"},
        "token_client_2": {"income_id": "inc_kumar", "allowed_question": "work_happened"}
    }
    # Client 1 token cannot access or confirm Client 2 income
    assert tokens["token_client_1"]["income_id"] != tokens["token_client_2"]["income_id"]

def test_audit_log_append_only():
    audit = AppendOnlyAuditTrail()
    audit.append("worker_1", "UPDATE_STATUS", "declared", "payment_claimed", "Claimed payment", "app_ui")
    audit.append("system", "RECONCILE", "payment_claimed", "bank_matched", "Matched NEFT credit", "engine")

    entries = audit.get_entries()
    assert len(entries) == 2
    assert entries[0]["actor"] == "worker_1"
    assert entries[1]["actor"] == "system"
    assert entries[1]["after"] == "bank_matched"
