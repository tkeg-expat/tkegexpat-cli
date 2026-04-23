from __future__ import annotations

import json
import os
import sys
import time
from typing import Optional

from .config import COUNTRIES_CACHE_FILE, ensure_config_dir

CACHE_MAX_AGE = 86400  # re-sync after 24h

_cache = None


def _load_local() -> Optional[dict]:
    if not COUNTRIES_CACHE_FILE.exists():
        return None
    try:
        data = json.loads(COUNTRIES_CACHE_FILE.read_text(encoding="utf-8"))
        return data
    except Exception:
        return None


def _save_local(countries: list, fetched_at: int):
    ensure_config_dir()
    by_abbr = {}
    for c in countries:
        abbr = (c.get("abbreviation") or "").upper()
        if abbr:
            by_abbr[abbr] = {
                "_id": c["_id"],
                "name": c.get("common-name-NEW2") or "",
                "abbr": abbr,
                "slug": c.get("Slug") or abbr.lower(),
            }
    payload = {"fetched_at": fetched_at, "count": len(by_abbr), "countries": by_abbr}
    COUNTRIES_CACHE_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.chmod(COUNTRIES_CACHE_FILE, 0o600)
    return payload


def _fetch_from_api(token: str) -> list:
    from .api import api_list
    return api_list("info_country")


def sync(token: str, force: bool = False):
    global _cache
    local = _load_local()
    now = int(time.time())

    if not force and local:
        age = now - local.get("fetched_at", 0)
        if age < CACHE_MAX_AGE:
            _cache = local
            return

    try:
        records = _fetch_from_api(token)
        _cache = _save_local(records, now)
    except Exception as e:
        if local:
            _cache = local
            print(f"Warning: country sync failed ({e}), using local cache.", file=sys.stderr)
        else:
            print(f"Error: could not fetch countries: {e}", file=sys.stderr)
            sys.exit(1)


def lookup(abbr: str) -> Optional[dict]:
    global _cache
    if _cache is None:
        _cache = _load_local()
    if _cache is None:
        return None
    return _cache.get("countries", {}).get(abbr.upper())


def get_all() -> dict:
    global _cache
    if _cache is None:
        _cache = _load_local()
    if _cache is None:
        return {}
    return _cache.get("countries", {})
