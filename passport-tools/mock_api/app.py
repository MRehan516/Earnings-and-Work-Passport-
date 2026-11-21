import time
import hmac
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from fastapi import FastAPI, Depends, HTTPException, Header, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="RideCo Partner Mock API", version="1.0.0")

# In-memory token store & rate limit store
VALID_CLIENT_ID = "rideco_client_123"
VALID_CLIENT_SECRET = "secret_rideco_xyz"
WEBHOOK_SECRET = b"rideco_webhook_secret_key_456"

tokens_db: Dict[str, Dict[str, Any]] = {}
request_log: Dict[str, List[float]] = {}
RATE_LIMIT_CALLS = 10
RATE_LIMIT_WINDOW_SECS = 2.0

class TokenRequest(BaseModel):
    grant_type: str
    client_id: str
    client_secret: str
    refresh_token: Optional[str] = None

SAMPLE_EARNINGS = [
    {
        "external_id": "RC-45-001",
        "week_start": "2026-11-02",
        "week_end": "2026-11-08",
        "gross": 9500.0,
        "deductions": 700.0,
        "net": 8800.0,
        "payout_date": "2026-11-10",
        "status": "paid"
    },
    {
        "external_id": "RC-46-001",
        "week_start": "2026-11-09",
        "week_end": "2026-11-15",
        "gross": 12000.0,
        "deductions": 1000.0,
        "net": 11000.0,
        "payout_date": "2026-11-17",
        "status": "paid"
    }
]

@app.post("/oauth/token")
def oauth_token(req: TokenRequest):
    if req.grant_type == "client_credentials":
        if req.client_id != VALID_CLIENT_ID or req.client_secret != VALID_CLIENT_SECRET:
            raise HTTPException(status_code=400, detail="Invalid client credentials")
        
        token = f"tok_{int(time.time())}_{hash(req.client_id)}"
        refresh_token = f"ref_{int(time.time())}"
        # 5 minute expiry (300 seconds)
        expires_at = time.time() + 300
        tokens_db[token] = {"expires_at": expires_at, "client_id": req.client_id}
        
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 300,
            "refresh_token": refresh_token
        }
    elif req.grant_type == "refresh_token":
        token = f"tok_{int(time.time())}_refreshed"
        expires_at = time.time() + 300
        tokens_db[token] = {"expires_at": expires_at, "client_id": req.client_id}
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 300
        }
    else:
        raise HTTPException(status_code=400, detail="Unsupported grant_type")

def verify_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization.split("Bearer ")[1].strip()
    
    if token not in tokens_db:
        raise HTTPException(status_code=401, detail="Invalid or unknown token")
    
    tok_info = tokens_db[token]
    if time.time() > tok_info["expires_at"]:
        raise HTTPException(status_code=401, detail="Token has expired")
    
    return token

@app.get("/v1/partner/earnings")
def get_earnings(
    request: Request,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    token: str = Depends(verify_token)
):
    # Rate limiting check
    client_ip = request.client.host if request.client else "default"
    now = time.time()
    call_times = request_log.setdefault(client_ip, [])
    # Filter out timestamps older than window
    request_log[client_ip] = [t for t in call_times if now - t < RATE_LIMIT_WINDOW_SECS]
    if len(request_log[client_ip]) >= RATE_LIMIT_CALLS:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Call backoff."},
            headers={"Retry-After": "1"}
        )
    request_log[client_ip].append(now)

    # Filter and paginate
    filtered = SAMPLE_EARNINGS
    if from_date:
        filtered = [x for x in filtered if x["week_start"] >= from_date]
    if to_date:
        filtered = [x for x in filtered if x["week_end"] <= to_date]

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paged_items = filtered[start_idx:end_idx]

    return {
        "items": paged_items,
        "page": page,
        "per_page": per_page,
        "total": len(filtered)
    }

def create_webhook_payload(event_type: str, data: Dict[str, Any], event_id: str) -> Tuple[str, str]:
    payload = json.dumps({
        "event_id": event_id,
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data
    }, sort_keys=True)
    
    signature = hmac.new(WEBHOOK_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return payload, signature
