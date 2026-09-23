import hashlib
import hmac
import logging
import os
import secrets
import time

from fastapi import Header, HTTPException, Request, status

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


def _build_hmac_message(method: str, path: str, query: str, timestamp: str, body: bytes) -> str:
    body_hash = hashlib.sha256(body).hexdigest()
    return "\n".join([method.upper(), path, query, timestamp, body_hash])


def _get_first_header(request: Request, *header_names: str) -> str | None:
    for header_name in header_names:
        header_value = request.headers.get(header_name)
        if header_value:
            return header_value
    return None


async def require_internal_hmac(
    request: Request,
    timestamp: str | None = Header(default=None, alias="Request-Timestamp"),
    signature: str | None = Header(default=None, alias="Request-Signature"),
):
   
    timestamp = timestamp or _get_first_header(request, "Request-Timestamp")
    signature = signature or _get_first_header(request, "Request-Signature")

    hmac_secret = os.getenv("INTERNAL_HMAC_KEY") or os.getenv("INTERNAL_HMAC_SECRET")
    if not hmac_secret:
        logger.error("INTERNAL_HMAC_KEY / INTERNAL_HMAC_SECRET is not configured for internal endpoints")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Internal endpoint unavailable.")

    if not timestamp or not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid HMAC signature.")

    try:
        timestamp_value = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid HMAC signature.") from exc

    max_skew_seconds = int(os.getenv("INTERNAL_HMAC_MAX_SKEW_SECONDS", "300"))
    current_time = int(time.time())
    time_diff = abs(current_time - timestamp_value)
    
    if time_diff > max_skew_seconds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Stale HMAC signature.")

    request_body = await request.body()
    
    message = _build_hmac_message(
        request.method,
        request.url.path,
        request.url.query,
        timestamp,
        request_body,
    )
    
    expected_signature = hmac.new(hmac_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()

    if not secrets.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid HMAC signature.")
    