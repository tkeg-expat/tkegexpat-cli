from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.parse
from typing import List, Optional

from .auth import get_token
from .config import API_BASE


def _optional_token() -> Optional[str]:
    result = get_token()
    return result["token"] if result else None


def _build_request(path: str, token: Optional[str] = None, params: Optional[dict] = None) -> urllib.request.Request:
    url = API_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    cookie = os.environ.get("TKEGEXPAT_FORWARD_COOKIE")
    if cookie:
        req.add_header("Cookie", cookie)
    elif token:
        req.add_header("Authorization", "Bearer " + token)
    req.add_header("User-Agent", "tkegexpat-cli/0.1.0")
    req.add_header("Accept", "application/json")
    return req


def _request(path: str, token: Optional[str] = None, params: Optional[dict] = None) -> dict:
    req = _build_request(path, token, params)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def api_get(path: str, params: Optional[dict] = None, token: Optional[str] = None) -> dict:
    if token is None:
        token = _optional_token()
    return _request(path, token, params)


def api_list(
    typename: str,
    constraints: Optional[List[dict]] = None,
    limit: int = 100,
    token: Optional[str] = None,
) -> List[dict]:
    if token is None:
        token = _optional_token()
    results = []
    cursor = 0
    while True:
        params = {"cursor": str(cursor), "limit": str(limit)}
        if constraints:
            params["constraints"] = json.dumps(constraints)
        data = _request(f"/api/1.1/obj/{typename}", token, params)
        response = data.get("response", {})
        results.extend(response.get("results", []))
        remaining = response.get("remaining", 0)
        if remaining <= 0:
            break
        cursor += response.get("count", limit)
    return results
