from __future__ import annotations

import json
import time
import urllib.request
from typing import Optional, Tuple

from .config import AUTH_URL, load_credentials, load_token, save_token

REFRESH_BUFFER = 60  # refresh 60s before actual expiry


def _extract_token(data: dict) -> Tuple[Optional[str], Optional[int]]:
    token = None
    expires_in = None

    for key in ("token", "api_token", "apiToken", "access_token", "accessToken"):
        if key in data and data[key]:
            token = data[key]
            break

    raw_response = data.get("response") if isinstance(data, dict) else None
    if token is None and isinstance(raw_response, dict):
        for key in ("token", "api_token", "apiToken", "access_token", "accessToken"):
            if key in raw_response and raw_response[key]:
                token = raw_response[key]
                break
        expires_in = raw_response.get("expires") or raw_response.get("expires_in")

    if expires_in is None:
        expires_in = data.get("expires") or data.get("expires_in")

    return token, int(expires_in) if expires_in else None


def fetch_token(email: str, password: str) -> dict:
    payload = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = urllib.request.Request(AUTH_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "tkegexpat-cli/0.1.0")

    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        data = json.loads(body)

    token, expires_in = _extract_token(data)
    if not token:
        raise RuntimeError(f"Token not found in response: {data}")

    now = int(time.time())
    expires_at = now + (expires_in or 0)
    save_token(token, expires_at, expires_in or 0)
    return {"token": token, "expires_at": expires_at, "source": "live"}


def get_token() -> Optional[dict]:
    cached = load_token()
    if cached:
        now = int(time.time())
        expires_at = cached.get("expires_at", 0)
        if now < expires_at - REFRESH_BUFFER:
            return {
                "token": cached["token"],
                "expires_at": expires_at,
                "expires_in": max(0, expires_at - now),
                "source": "cache",
            }

    creds = load_credentials()
    if not creds:
        return None

    try:
        return fetch_token(creds["email"], creds["password"])
    except Exception:
        return None


def require_token() -> str:
    result = get_token()
    if result:
        return result["token"]
    raise RuntimeError("Not logged in. Run: tkegexpat login")
