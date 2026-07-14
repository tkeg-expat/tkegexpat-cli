from __future__ import annotations

import sys

from .api import api_get, api_list
from .auth import get_user_id
from .config import load_credentials
from .countries import id_to_abbr
from .cit import _dot, _reset_dots, _print_kv_table


def _fmt_date(value):
    if not value:
        return "-"
    s = str(value)
    return s.split("T")[0] if "T" in s else s


def _yes_no(value):
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "-"


def _email(u):
    """Pull the login email out of the nested `authentication` blob."""
    auth = u.get("authentication")
    if isinstance(auth, dict):
        email = auth.get("email")
        if isinstance(email, dict):
            return email.get("email") or "-"
    return "-"


def _find_user_entities(uid):
    """Reverse-lookup the current user's team / client entity ids.

    crm / rd / admin link to the user via `portal_user`; client via
    `user_account` (a list — not always API-searchable, so it degrades to '-')."""
    found = {}
    for label, typ in (("CRM Entity", "entity_crm"), ("RD Entity", "entity_rd"), ("Admin Entity", "entity_admin")):
        try:
            rows = api_list(typ, [{"key": "portal_user", "constraint_type": "equals", "value": uid}])
        except Exception:
            rows = []
        found[label] = rows[0]["_id"] if rows else "-"
    try:
        rows = api_list("entity_client", [{"key": "user_account", "constraint_type": "contains", "value": uid}])
        found["Client Entity"] = rows[0]["_id"] if rows else "-"
    except Exception:
        found["Client Entity"] = "-"
    return found


def cmd_user(args):
    """Show the current logged-in user's portal profile.

    Requires a login — the identity comes from the saved credentials' user id,
    so this command is not part of AUTH_EXEMPT.
    """
    if not load_credentials():
        print("Not logged in. Run: tkegexpat login", file=sys.stderr)
        return

    uid = get_user_id()
    if not uid:
        print("Could not determine current user id. Try: logout, then login again.", file=sys.stderr)
        return

    print("  Fetching current user ...")
    try:
        resp = api_get(f"/api/1.1/obj/user/{uid}")
        u = resp.get("response", resp)
    except Exception as e:
        print(f"  Failed to fetch user: {e}", file=sys.stderr)
        return

    if not isinstance(u, dict) or not u.get("_id"):
        print(f"  No user record found for id '{uid}'.", file=sys.stderr)
        return

    print("  Resolving entities ...")
    ent = _find_user_entities(uid)

    _reset_dots()

    name = u.get("user_name") or u.get("tkeg_user_id") or "-"
    print(f"\n{_dot(name)}")

    info = [
        ("Name", u.get("user_name") or "-"),
        ("TKEG User ID", u.get("tkeg_user_id") or "-"),
        ("Email", _email(u)),
        ("User Type", u.get("user_type") or "-"),
        ("Entity", u.get("currenty_entity_name") or "-"),
        ("Jurisdiction", id_to_abbr(u.get("belonging_jurisdiction") or "")),
        ("Language", u.get("language") or "-"),
        ("Currency", u.get("current-currency") or "-"),
        ("Current Country", u.get("current_country_code") or "-"),
        ("Signed Up", _yes_no(u.get("user_signed_up"))),
        ("Disabled", _yes_no(u.get("disabled"))),
        ("Slug", u.get("Slug") or "-"),
        ("User ID (_id)", u.get("_id") or "-"),
        ("CRM Entity", ent["CRM Entity"]),
        ("RD Entity", ent["RD Entity"]),
        ("Admin Entity", ent["Admin Entity"]),
        ("Client Entity", ent["Client Entity"]),
        ("Created", _fmt_date(u.get("Created Date"))),
    ]
    _print_kv_table(info)
    print()
