from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".config" / "tkegexpat"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
TOKEN_CACHE_FILE = CONFIG_DIR / "token.json"
COUNTRIES_CACHE_FILE = CONFIG_DIR / "countries.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

AUTH_URL = "https://portal.tkegexpat.com/api/1.1/wf/get-red-queen-api"
API_BASE = "https://portal.tkegexpat.com"


def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def save_credentials(email: str, password: str):
    ensure_config_dir()
    data = {"email": email, "password": password}
    CREDENTIALS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.chmod(CREDENTIALS_FILE, 0o600)


def load_credentials() -> Optional[dict]:
    if not CREDENTIALS_FILE.exists():
        return None
    try:
        return json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_token(token: str, expires_at: int, expires_in: int, user_id: Optional[str] = None):
    ensure_config_dir()
    data = {"token": token, "expires_at": expires_at, "expires_in": expires_in}
    if user_id:
        data["user_id"] = user_id
    TOKEN_CACHE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.chmod(TOKEN_CACHE_FILE, 0o600)


def load_token() -> Optional[dict]:
    if not TOKEN_CACHE_FILE.exists():
        return None
    try:
        return json.loads(TOKEN_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return {"language": "en_us"}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"language": "en_us"}


def save_settings(settings: dict):
    ensure_config_dir()
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def clear_credentials():
    if CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()
    if TOKEN_CACHE_FILE.exists():
        TOKEN_CACHE_FILE.unlink()
