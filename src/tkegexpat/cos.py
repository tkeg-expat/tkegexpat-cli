from __future__ import annotations

import re
import sys

from .api import api_get, api_list
from .countries import id_to_abbr, lookup as country_lookup
from .cit import _dot, _reset_dots, _print_detail_table, _print_kv_table, DIM, RESET
from .product import SERVICE_TYPES, SERVICE_TYPE_TO_CODE, parse_code
from .entities import entity_cell, product_name

# Read-only check-out session (cos) viewer. Mirrors `project` / `project-item`:
#   cos <code> [status]  -> list          cos <id>  -> detail
# check_out_session has NO human id (bubble _id only). session_status option set
# is its own: ARCHIVED / PROJECT / LOST (distinct from project / project-item).

STATUS_OPTIONS = ["ARCHIVED", "PROJECT", "LOST"]
LIST_COLUMNS = ["#", "Date", "Status", "Product", "Unit Price"]
ITEM_COLUMNS = ["#", "Item", "Qty", "Sum"]

_last_sessions = []
_product_cache = {}


def _date(value):
    if not value:
        return "-"
    s = str(value)
    return s.split("T")[0] if "T" in s else s


def _money(value, currency):
    if isinstance(value, (int, float)):
        return f"{value:,.0f} {currency or ''}".strip()
    return "-"


def _prod(pid):
    """Cached product-name resolution (sessions in a country+service share products)."""
    if not pid:
        return "-"
    if pid not in _product_cache:
        _product_cache[pid] = product_name(pid)
    return _product_cache[pid]


def _user(uid):
    if not uid:
        return "-"
    try:
        u = api_get(f"/api/1.1/obj/user/{uid}").get("response", {})
    except Exception:
        return str(uid)
    return u.get("user_name") or u.get("tkeg_user_id") or str(uid)


def _classify_cos_input(raw: str) -> str:
    """'uid' for a Bubble _id, 'code' for <country><service>, else 'invalid'."""
    s = raw.strip()
    if re.fullmatch(r"\d+x\d+", s):
        return "uid"
    if "-" not in s and len(s) >= 4:
        if SERVICE_TYPES.get(s[-2:].lower()) and country_lookup(s[:-2]):
            return "code"
    return "invalid"


def _lookup_cos_by_id(value):
    print(f"  Looking up check-out session by ID: {value} ...")
    try:
        s = api_get(f"/api/1.1/obj/check_out_session/{value}").get("response", {})
    except Exception:
        s = None
    if not s or not s.get("_id"):
        print(f"  No check-out session found with ID '{value}'.", file=sys.stderr)
        return None
    return s


def _row(s, i):
    return {
        "#": str(i),
        "Date": _date(s.get("Created Date")),
        "Status": s.get("session_status") or "-",
        "Product": _prod(s.get("main_product")),
        "Unit Price": _money(s.get("main_product_unit_price"), s.get("marking_currency")),
    }


def cmd_cos(args):
    global _last_sessions
    _last_sessions = []

    from .filters import parse_filters
    positional, extra, ok = parse_filters(args, crm_field="crm_entity", client_field="client_entity")
    if not ok:
        return

    if not positional:
        print("Usage: cos <code> [status]  [--crm <_id>] [--client <_id|tkeg-id>]   |   cos <id>", file=sys.stderr)
        print("  cos usac                                 list US accounting check-out sessions", file=sys.stderr)
        print("  cos usac project --client <tkeg-id>      filtered by status + client", file=sys.stderr)
        print("  cos 1715569179354x662628426944610300     open one session by its _id", file=sys.stderr)
        print(f"\n  status option set: {', '.join(STATUS_OPTIONS)}", file=sys.stderr)
        print(f"  service type codes: {', '.join(sorted(SERVICE_TYPES))}", file=sys.stderr)
        return

    raw = positional[0].strip()
    kind = _classify_cos_input(raw)

    if kind == "uid":
        if extra:
            print(f"  {DIM}(--crm/--client ignored for direct lookup){RESET}")
        s = _lookup_cos_by_id(raw)
        if not s:
            return
        _last_sessions = [s]
        _render_cos_detail(s)
        return True

    if kind == "invalid":
        print(f"'{raw}' is not a <country><service> code or a session _id.", file=sys.stderr)
        return

    country, service_type = parse_code(raw.lower())
    status_filter = " ".join(positional[1:]).lower() if len(positional) > 1 else None
    label = f"{country['abbr']} + {service_type}" + (f" — {status_filter}" if status_filter else "")
    print(f"  Fetching check-out sessions: {label} ...")

    sessions = api_list("check_out_session", [
        {"key": "service_country/region", "constraint_type": "equals", "value": country["_id"]},
        {"key": "service_type", "constraint_type": "equals", "value": service_type},
    ] + extra)
    if status_filter:
        sessions = [s for s in sessions if (s.get("session_status") or "").lower() == status_filter]
    _last_sessions = sessions

    if not sessions:
        print(f"\n  No check-out sessions found for {label}.")
        return True

    print("  Resolving products ...")
    _reset_dots()
    print(f"\n{_dot(f'{label} — Check-out Sessions ({len(sessions)})')}")
    _print_detail_table([_row(s, i) for i, s in enumerate(sessions, 1)], LIST_COLUMNS)
    print(f"\n  {DIM}View full session: view <#>{RESET}\n")
    return True


def cmd_view_cos(args):
    if not _last_sessions:
        print("No check-out session list available. Run 'cos <code>' first.", file=sys.stderr)
        return
    if not args:
        print("Usage: view <#>", file=sys.stderr)
        return
    try:
        idx = int(args[0])
    except ValueError:
        print(f"Invalid number: {args[0]}", file=sys.stderr)
        return
    if idx < 1 or idx > len(_last_sessions):
        print(f"Invalid index. Choose 1-{len(_last_sessions)}.", file=sys.stderr)
        return
    _render_cos_detail(_last_sessions[idx - 1])


def _render_cos_detail(s):
    _reset_dots()
    sid = s["_id"]
    svc = s.get("service_type")
    cur = s.get("marking_currency")

    print("\n" + _dot(_prod(s.get("main_product")) if s.get("main_product") else "Check-out Session"))
    info = [
        ("Session _id", sid),
        ("Status", s.get("session_status") or "-"),
        ("Service", (SERVICE_TYPE_TO_CODE.get(svc, svc) if svc else "-") or "-"),
        ("Country", id_to_abbr(s.get("service_country/region") or "")),
        ("Main Product", _prod(s.get("main_product"))),
        ("Unit Price", _money(s.get("main_product_unit_price"), cur)),
        ("Currency", cur or "-"),
        ("CRM", entity_cell(s.get("crm_entity"), "entity_crm")),
        ("User", _user(s.get("user"))),
        ("Logged In", "Yes" if s.get("user_logged_in") else ("No" if s.get("user_logged_in") is False else "-")),
        ("Created", _date(s.get("Created Date"))),
        ("Converted to Project", _date(s.get("project_converting_date"))),
    ]
    _print_kv_table(info)

    print("\n  Fetching session items ...")
    try:
        items = api_list("check_out_session_item", [
            {"key": "check_out_session", "constraint_type": "equals", "value": sid},
        ])
    except Exception:
        items = []
    print(f"\n{_dot(f'Session Items ({len(items)})')}")
    if not items:
        print("  No session items.")
    else:
        rows = [{
            "#": str(i),
            "Item": _prod(it.get("item")),
            "Qty": str(it.get("item_quantity")) if it.get("item_quantity") is not None else "-",
            "Sum": _money(it.get("sum"), cur),
        } for i, it in enumerate(items, 1)]
        _print_detail_table(rows, ITEM_COLUMNS)
    print()
