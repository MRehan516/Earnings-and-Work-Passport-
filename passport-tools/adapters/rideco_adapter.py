import time
import hmac
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import httpx

class RideCoValidationError(Exception):
    pass

class RideCoAdapter:
    def __init__(self, base_url: str, client_id: str, client_secret: str, webhook_secret: bytes):
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.webhook_secret = webhook_secret
        
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expiry: float = 0.0
        
        # Idempotency caches
        self.seen_external_ids: set = set()
        self.seen_webhook_event_ids: set = set()

    def get_valid_token(self, client: Optional[httpx.Client] = None) -> str:
        now = time.time()
        if self.access_token and now < self.token_expiry - 10:
            return self.access_token
        
        # Need to fetch or refresh
        owns_client = False
        if client is None:
            client = httpx.Client(base_url=self.base_url)
            owns_client = True

        try:
            if self.refresh_token and now >= self.token_expiry:
                body = {
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token
                }
            else:
                body = {
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
            
            resp = client.post("/oauth/token", json=body)
            if resp.status_code != 200:
                raise RuntimeError(f"OAuth token request failed: {resp.status_code} {resp.text}")
            
            data = resp.json()
            self.access_token = data["access_token"]
            self.token_expiry = now + data.get("expires_in", 300)
            if "refresh_token" in data:
                self.refresh_token = data["refresh_token"]
            return self.access_token
        finally:
            if owns_client:
                client.close()

    @staticmethod
    def validate_raw_item(item: Dict[str, Any]) -> None:
        required_fields = ["external_id", "week_start", "week_end", "gross", "deductions", "net", "payout_date"]
        for f in required_fields:
            if f not in item or item[f] is None:
                raise RideCoValidationError(f"Missing required field: {f}")
        
        gross = float(item["gross"])
        deductions = float(item["deductions"])
        net = float(item["net"])

        if gross < 0 or deductions < 0 or net < 0:
            raise RideCoValidationError("Negative amounts are not permitted")
        
        if abs(gross - deductions - net) > 1.0:
            raise RideCoValidationError(f"Invalid math: gross ({gross}) - deductions ({deductions}) != net ({net})")

    @staticmethod
    def map_to_common_format(item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "source_type": "platform",
            "source_party": "RideCo Technologies",
            "external_id": item["external_id"],
            "period_start": item["week_start"],
            "period_end": item["week_end"],
            "gross": float(item["gross"]),
            "deductions": float(item["deductions"]),
            "net": float(item["net"]),
            "currency": "INR",
            "payout_date": item["payout_date"],
            "acquisition_method": "simulated_api",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "raw_ref": f"rideco://earnings/{item['external_id']}"
        }

    def fetch_all_earnings(self, from_date: Optional[str] = None, to_date: Optional[str] = None, client: Optional[httpx.Client] = None) -> List[Dict[str, Any]]:
        owns_client = False
        if client is None:
            client = httpx.Client(base_url=self.base_url)
            owns_client = True

        try:
            page = 1
            per_page = 10
            results = []

            while True:
                token = self.get_valid_token(client=client)
                headers = {"Authorization": f"Bearer {token}"}
                params = {"page": page, "per_page": per_page}
                if from_date:
                    params["from"] = from_date
                if to_date:
                    params["to"] = to_date

                # Retry loop for rate limit (429)
                max_retries = 3
                resp = None
                for attempt in range(max_retries):
                    resp = client.get("/v1/partner/earnings", headers=headers, params=params)
                    if resp.status_code == 429:
                        retry_after = float(resp.headers.get("Retry-After", 1.0))
                        time.sleep(retry_after)
                        continue
                    elif resp.status_code == 401:
                        # Expired token: force refresh and retry
                        self.access_token = None
                        token = self.get_valid_token(client=client)
                        headers["Authorization"] = f"Bearer {token}"
                        continue
                    break

                if resp is None or resp.status_code != 200:
                    raise RuntimeError(f"Earnings request failed: {resp.status_code if resp else 'No response'} {resp.text if resp else ''}")

                body = resp.json()
                items = body.get("items", [])
                if not items:
                    break

                for item in items:
                    ext_id = item.get("external_id")
                    if ext_id in self.seen_external_ids:
                        continue  # Idempotent deduplication
                    
                    self.validate_raw_item(item)
                    mapped = self.map_to_common_format(item)
                    self.seen_external_ids.add(ext_id)
                    results.append(mapped)

                if len(items) < per_page:
                    break
                page += 1

            return results
        finally:
            if owns_client:
                client.close()

    def process_webhook(self, raw_payload: str, signature_header: str) -> Optional[Dict[str, Any]]:
        # 1. Verify HMAC-SHA256 signature
        expected_sig = hmac.new(self.webhook_secret, raw_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, signature_header):
            raise ValueError("Invalid webhook signature")

        data = json.loads(raw_payload)
        event_id = data.get("event_id")
        if not event_id:
            raise ValueError("Missing event_id in webhook")

        # 2. Idempotency by event_id
        if event_id in self.seen_webhook_event_ids:
            return None  # Ignore repeated event

        self.seen_webhook_event_ids.add(event_id)

        # 3. Validate & Map
        item = data.get("data", {})
        self.validate_raw_item(item)
        return self.map_to_common_format(item)
