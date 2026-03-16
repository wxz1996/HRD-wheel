import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from fastapi import Header, HTTPException, WebSocket, status

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

DEMO_ACCOUNT = os.getenv("HRT_DEMO_ACCOUNT", "demo")
DEMO_PASSWORD = os.getenv("HRT_DEMO_PASSWORD", "demo123")
TOKEN_SECRET = os.getenv("HRT_TOKEN_SECRET", "change-this-secret-in-production")
TOKEN_TTL_SECONDS = int(os.getenv("HRT_TOKEN_TTL_SECONDS", "43200"))
STREAM_TOKEN_TTL_SECONDS = int(os.getenv("HRT_STREAM_TOKEN_TTL_SECONDS", "900"))


def get_allowed_origins() -> list[str]:
    raw = os.getenv("HRT_ALLOWED_ORIGINS", "")
    if not raw.strip():
        return DEFAULT_ALLOWED_ORIGINS
    return [x.strip() for x in raw.split(",") if x.strip()]


def verify_login_credentials(account: str, password: str) -> bool:
    return hmac.compare_digest(account, DEMO_ACCOUNT) and hmac.compare_digest(password, DEMO_PASSWORD)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + padding)


def issue_token(account: str, role: str = "operator") -> str:
    now = int(time.time())
    payload = {
        "sub": account,
        "role": role,
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
    }
    return _issue_signed_token(payload)


def issue_video_stream_token(account: str) -> str:
    now = int(time.time())
    payload = {
        "sub": account,
        "scope": "video:stream",
        "iat": now,
        "exp": now + STREAM_TOKEN_TTL_SECONDS,
    }
    return _issue_signed_token(payload)


def _issue_signed_token(payload: dict[str, Any]) -> str:
    payload_raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    payload_enc = _b64url_encode(payload_raw)
    sig = hmac.new(TOKEN_SECRET.encode("utf-8"), payload_enc.encode("utf-8"), hashlib.sha256).digest()
    return f"{payload_enc}.{_b64url_encode(sig)}"


def verify_token(token: str | None) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    payload_enc, sig_enc = token.split(".", 1)
    expected_sig = hmac.new(
        TOKEN_SECRET.encode("utf-8"),
        payload_enc.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    try:
        actual_sig = _b64url_decode(sig_enc)
    except Exception:
        return None
    if not hmac.compare_digest(actual_sig, expected_sig):
        return None
    try:
        payload = json.loads(_b64url_decode(payload_enc).decode("utf-8"))
    except Exception:
        return None
    if int(payload.get("exp", 0)) <= int(time.time()):
        return None
    return payload


def require_token_string(token: str | None) -> dict[str, Any]:
    claims = verify_token(token)
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token")
    return claims


def require_stream_token_string(token: str | None) -> dict[str, Any]:
    claims = require_token_string(token)
    scope = str(claims.get("scope", ""))
    role = str(claims.get("role", ""))
    if scope == "video:stream" or role:
        return claims
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid stream token")


def require_auth(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing authorization header")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid authorization scheme")
    claims = verify_token(parts[1].strip())
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token")
    return claims


async def authenticate_websocket(ws: WebSocket) -> dict[str, Any] | None:
    token = ws.query_params.get("token")
    claims = verify_token(token)
    if not claims:
        await ws.close(code=4401, reason="Unauthorized")
        return None
    await ws.accept()
    return claims


def apply_security_headers(headers: Any) -> None:
    headers["X-Content-Type-Options"] = "nosniff"
    headers["X-Frame-Options"] = "DENY"
    headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    headers["Permissions-Policy"] = "camera=(), microphone=()"
    headers["Cache-Control"] = "no-store"
